"""
research/experiments/run_v4_gap_aware_directional_experiment.py
===============================================================
Authoritative experimental study v4 evaluating directional candidates under:
1. Strict Time-Series Continuity & Contiguous Segmentation (zero gap contamination).
2. Exact 24-hour elapsed target duration & gap-safe triple barrier labeling (H=24h, k_tp=1.5, k_sl=1.0).
3. 24-bar chronological embargo/purging prior to split boundaries.
4. Preregistered Single-Position-at-a-Time Portfolio Accounting.
5. Realistic two-sided exchange execution frictions:
   - Coinbase Advanced Spot Tier 1 (Primary Backtest): 80.0 bps commission + 3.0 bps spread + 4.0 bps slippage = 87.0 bps round-trip.
   - Binance Futures Perpetual (Hypothetical Sensitivity): 10.0 bps commission + 1.0 bps spread + 2.0 bps slippage + 2.25 bps funding = 15.25 bps.
6. Calibration against Constant Historical Prevalence Baseline.

Candidates Evaluated:
- Candidate 0: No-Trade Baseline
- Candidate 1: Corrected 24h Momentum Baseline (Single-Position, Gap-Safe)
- Candidate 2: Cost-Aware Return Filter (Ridge Regressor, Gap-Safe)
- Candidate 3: Primary-Side Plus Meta-Label Filter (Logistic Classifier, Gap-Safe)
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Tuple

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss

from engine.continuity_time_series import continuity_engine
from engine.execution_cost_model import ExecutionCostModel


def run_experiment() -> Dict[str, Any]:
    data_path = Path("data/raw/ohlcv.parquet")
    if not data_path.exists():
        raise FileNotFoundError(f"Missing {data_path}")

    # 1. Audit and Segment Continuous Data
    df_raw = pd.read_parquet(data_path)
    df_clean, audit_summary = continuity_engine.audit_and_segment(df_raw)

    # 2. Build Gap-Safe Features within Segments
    df_feat = continuity_engine.build_continuity_features(
        df_clean,
        lookbacks_return=[1, 4, 24],
        volatility_window=24,
        long_vol_window=168
    )

    # 3. Build Gap-Safe Triple-Barrier Labels
    H = 24
    k_tp = 1.5
    k_sl = 1.0
    df_labeled = continuity_engine.build_gap_safe_triple_barrier_labels(
        df_feat,
        horizon_hours=H,
        k_tp=k_tp,
        k_sl=k_sl,
        collision_policy="SL_FIRST_CONSERVATIVE"
    )

    df_labeled["year"] = df_labeled["timestamp"].dt.year

    # 4. Chronological Splits with 24-hour Purging Embargo
    # Train: 2022-01-01 to 2024-12-30 23:00 UTC (purging last 24 hours of 2024)
    # Val: 2025-01-01 to 2025-12-30 23:00 UTC (purging last 24 hours of 2025)
    # Test: 2026-01-01 to end (excluding lookback warmups and horizon gap crossing)
    train_mask = (df_labeled["year"] <= 2024) & df_labeled["tb_label"].notna() & (df_labeled["timestamp"] <= "2024-12-30 23:00:00+00:00")
    val_mask = (df_labeled["year"] == 2025) & df_labeled["tb_label"].notna() & (df_labeled["timestamp"] <= "2025-12-30 23:00:00+00:00")
    test_mask = (df_labeled["year"] == 2026) & df_labeled["tb_label"].notna()

    feature_cols = ["ret_1h", "ret_4h", "ret_24h", "rv_24h", "vol_spread", "hl_ratio_24h"]

    train_df = df_labeled[train_mask].dropna(subset=feature_cols).copy()
    val_df = df_labeled[val_mask].dropna(subset=feature_cols).copy()
    test_df = df_labeled[test_mask].dropna(subset=feature_cols).copy()

    # 5. Verified Cost Schedules
    cb_cost_info = ExecutionCostModel.calculate_round_trip_cost("Coinbase")
    COINBASE_ROUNDTRIP_BPS = cb_cost_info["total_round_trip_bps"]  # 87.0 bps

    bin_cost_info = ExecutionCostModel.calculate_round_trip_cost("Binance_Futures", holding_hours=18.0)
    BINANCE_ROUNDTRIP_BPS = bin_cost_info["total_round_trip_bps"]  # 15.0 - 15.25 bps

    # Helper: Single-Position-at-a-Time Simulator (enforcing segment continuity)
    def simulate_single_position(candidate_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        if len(candidate_df) == 0:
            return pd.DataFrame(), {
                "trades": 0,
                "gross_expectancy_bps": 0.0,
                "net_expectancy_coinbase_bps": 0.0,
                "net_expectancy_binance_hypothetical_bps": 0.0,
                "tp_first_pct": 0.0,
                "sl_first_pct": 0.0,
                "timeout_pct": 0.0,
                "mean_holding_hours": 0.0,
                "economic_verdict": "ABSTAIN_NEUTRAL"
            }

        sp_trades = []
        curr_exit = -1
        for idx, row in candidate_df.iterrows():
            entry_idx = idx + 1
            if entry_idx > curr_exit and entry_idx <= row["tb_exit_index"]:
                sp_trades.append(row)
                curr_exit = row["tb_exit_index"]

        sp_df = pd.DataFrame(sp_trades)
        if len(sp_df) == 0:
            return sp_df, {
                "trades": 0,
                "gross_expectancy_bps": 0.0,
                "net_expectancy_coinbase_bps": 0.0,
                "net_expectancy_binance_hypothetical_bps": 0.0,
                "tp_first_pct": 0.0,
                "sl_first_pct": 0.0,
                "timeout_pct": 0.0,
                "mean_holding_hours": 0.0,
                "economic_verdict": "ABSTAIN_NEUTRAL"
            }

        n_trades = len(sp_df)
        gross_mean_bps = float(sp_df["tb_return"].mean() * 10000.0)
        net_coinbase_bps = gross_mean_bps - COINBASE_ROUNDTRIP_BPS
        net_binance_bps = gross_mean_bps - BINANCE_ROUNDTRIP_BPS
        tp_pct = float((sp_df["tb_outcome"] == "TP_FIRST").mean() * 100.0)
        sl_pct = float(sp_df["tb_outcome"].str.contains("SL").mean() * 100.0)
        to_pct = float((sp_df["tb_outcome"] == "TIMEOUT").mean() * 100.0)
        mean_hold = float(sp_df["tb_holding_hours"].mean())

        verdict = "PASS_MARGINAL" if net_coinbase_bps > 0 else "FAIL_NEGATIVE_AFTER_COSTS"

        return sp_df, {
            "trades": n_trades,
            "gross_expectancy_bps": round(gross_mean_bps, 2),
            "net_expectancy_coinbase_bps": round(net_coinbase_bps, 2),
            "net_expectancy_binance_hypothetical_bps": round(net_binance_bps, 2),
            "tp_first_pct": round(tp_pct, 2),
            "sl_first_pct": round(sl_pct, 2),
            "timeout_pct": round(to_pct, 2),
            "mean_holding_hours": round(mean_hold, 1),
            "economic_verdict": verdict
        }

    results = {}

    # -------------------------------------------------------------
    # CANDIDATE 0: No-Trade Baseline
    # -------------------------------------------------------------
    results["Candidate_0_No_Trade_Baseline"] = {
        "candidate_id": "CAND-0-NO-TRADE",
        "description": "Zero directional exposure benchmark",
        "trades": 0,
        "gross_expectancy_bps": 0.0,
        "net_expectancy_coinbase_bps": 0.0,
        "net_expectancy_binance_hypothetical_bps": 0.0,
        "tp_first_pct": 0.0,
        "sl_first_pct": 0.0,
        "timeout_pct": 0.0,
        "economic_verdict": "ABSTAIN_NEUTRAL"
    }

    # -------------------------------------------------------------
    # CANDIDATE 1: Corrected 24h Momentum Baseline
    # -------------------------------------------------------------
    mom_candidates = test_df[test_df["ret_24h"] > 0]
    _, c1_metrics = simulate_single_position(mom_candidates)
    c1_metrics["candidate_id"] = "CAND-1-MOMENTUM-24H-GAP-SAFE"
    c1_metrics["description"] = "Causal 24h momentum evaluated under gap-safe single-position portfolio accounting"
    results["Candidate_1_Momentum_24h_Baseline"] = c1_metrics

    # -------------------------------------------------------------
    # CANDIDATE 2: Cost-Aware Return Filter (Ridge Regressor)
    # -------------------------------------------------------------
    ridge = Ridge(alpha=100.0, random_state=42)
    ridge.fit(train_df[feature_cols], train_df["tb_return"])

    val_df = val_df.copy()
    val_df["pred_ret"] = ridge.predict(val_df[feature_cols])
    test_df = test_df.copy()
    test_df["pred_ret"] = ridge.predict(test_df[feature_cols])

    # Hurdle chosen from Coinbase round-trip (87.0 bps) or Binance sensitivity (15.25 bps)
    hurdle_ratio = BINANCE_ROUNDTRIP_BPS / 10000.0
    c2_candidates = test_df[test_df["pred_ret"] > hurdle_ratio]
    _, c2_metrics = simulate_single_position(c2_candidates)
    c2_metrics["candidate_id"] = "CAND-2-COST-AWARE-FILTER"
    c2_metrics["description"] = "Selective entry requiring predicted return to exceed roundtrip friction hurdle"
    c2_metrics["hurdle_bps"] = round(hurdle_ratio * 10000.0, 2)
    results["Candidate_2_Cost_Aware_Filter"] = c2_metrics

    # -------------------------------------------------------------
    # CANDIDATE 3: Primary-Side Plus Meta-Label Filter
    # -------------------------------------------------------------
    train_df["y_meta"] = (train_df["tb_return"] > hurdle_ratio).astype(int)
    val_df["y_meta"] = (val_df["tb_return"] > hurdle_ratio).astype(int)
    test_df["y_meta"] = (test_df["tb_return"] > hurdle_ratio).astype(int)

    meta_train = train_df[train_df["ret_24h"] > 0]
    meta_val = val_df[val_df["ret_24h"] > 0]
    meta_test = test_df[test_df["ret_24h"] > 0].copy()

    p_train_prevalence = float(meta_train["y_meta"].mean())
    p_test_prevalence = float(meta_test["y_meta"].mean())

    meta_clf = LogisticRegression(C=0.1, random_state=42, max_iter=200)
    meta_clf.fit(meta_train[feature_cols], meta_train["y_meta"])

    meta_test_probs = meta_clf.predict_proba(meta_test[feature_cols])[:, 1]
    meta_test["meta_prob"] = meta_test_probs

    # Calibration Baselines
    brier_model = float(brier_score_loss(meta_test["y_meta"], meta_test_probs))
    brier_prev_baseline = float(brier_score_loss(meta_test["y_meta"], np.full_like(meta_test_probs, p_train_prevalence)))
    brier_naive_50 = float(brier_score_loss(meta_test["y_meta"], np.full_like(meta_test_probs, 0.50)))

    logloss_model = float(log_loss(meta_test["y_meta"], meta_test_probs))
    logloss_prev_baseline = float(log_loss(meta_test["y_meta"], np.full_like(meta_test_probs, p_train_prevalence)))

    c3_candidates = meta_test[meta_test["meta_prob"] >= 0.45]
    _, c3_metrics = simulate_single_position(c3_candidates)
    c3_metrics["candidate_id"] = "CAND-3-META-LABEL-FILTER"
    c3_metrics["description"] = "24h Momentum filtered by secondary logistic probability model"
    c3_metrics["brier_score_model"] = round(brier_model, 4)
    c3_metrics["brier_score_constant_prevalence_baseline"] = round(brier_prev_baseline, 4)
    c3_metrics["brier_score_naive_50_baseline"] = round(brier_naive_50, 4)
    c3_metrics["log_loss_model"] = round(logloss_model, 4)
    c3_metrics["log_loss_constant_prevalence_baseline"] = round(logloss_prev_baseline, 4)
    c3_metrics["train_positive_class_prevalence"] = round(p_train_prevalence, 4)
    c3_metrics["test_positive_class_prevalence"] = round(p_test_prevalence, 4)
    c3_metrics["decision_threshold"] = 0.45
    results["Candidate_3_Meta_Label_Filter"] = c3_metrics

    # Governed Acceptance Gate
    is_any_passed = any(
        v.get("net_expectancy_coinbase_bps", -999) > 0.0 and v.get("trades", 0) >= 30
        for k, v in results.items()
        if k != "Candidate_0_No_Trade_Baseline"
    )

    manifest = {
        "experiment_id": "EXP-RESEARCH-TO-SIGNAL-V4-GAP-AWARE",
        "timestamp_utc": pd.Timestamp.now("UTC").isoformat(),
        "dataset": "data/raw/ohlcv.parquet",
        "market_provenance": {
            "source_exchange": "Coinbase Advanced",
            "instrument": "BTC-USD",
            "market_type": "SPOT",
            "primary_empirical_backtest": "Coinbase Spot Tier 1 (87.0 bps)",
            "hypothetical_sensitivity_scenario": "Hypothetical Binance USDT-M Futures Perpetual Sensitivity (15.25 bps)"
        },
        "time_series_continuity": {
            "total_input_bars": audit_summary.total_input_rows,
            "continuous_segments_count": len(audit_summary.segments),
            "identified_gaps": audit_summary.gaps,
            "purging_embargo_hours": 24
        },
        "sample_split_bars": {
            "train_bars": len(train_df),
            "val_bars": len(val_df),
            "test_bars": len(test_df)
        },
        "barrier_parameters": {
            "horizon_hours": H,
            "tp_multiplier": k_tp,
            "sl_multiplier": k_sl,
            "collision_policy": "SL_FIRST_CONSERVATIVE"
        },
        "execution_costs": {
            "coinbase_spot_tier1_roundtrip_bps": COINBASE_ROUNDTRIP_BPS,
            "binance_futures_hypothetical_bps": BINANCE_ROUNDTRIP_BPS
        },
        "portfolio_policy": "SINGLE_POSITION_AT_A_TIME",
        "candidates": results,
        "governed_conclusion": "SELECTIVE_PAPER_CANDIDATE_VERIFIED" if is_any_passed else "NO_CANDIDATE_PASSED_PREREGISTERED_GATE",
        "execution_authorization": "DISABLED"
    }

    out_file = Path("experiments/results/research_improvement/v4_gap_aware_directional_manifest.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("Experiment v4 Completed Successfully!")
    print(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    run_experiment()

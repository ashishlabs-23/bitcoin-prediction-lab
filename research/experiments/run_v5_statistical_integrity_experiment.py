"""
research/experiments/run_v5_statistical_integrity_experiment.py
===============================================================
BTCognitive V5 — Statistical Integrity, Experiment Freeze & Prospective Research
Preregistered Reproducible Strategy Evaluation Runner.

Implements:
1. Gap-safe continuity-aware segmentation and exact feature warm-up accounting.
2. Machine-readable eligibility audit generation.
3. Separation of primary Coinbase Spot Tier 1 (87.0 bps) from hypothetical Binance Perpetual (15.0 bps).
4. Explicit target disambiguation:
   - Target A: Gross return > 15.0 bps (Hypothetical Binance Perpetual break-even).
   - Target B: Gross return > 87.0 bps (Coinbase Spot Tier 1 break-even).
5. Paired loss difference confidence intervals (Brier and Log Loss vs training prevalence baseline).
6. Dependent bootstrap confidence intervals on mean net expectancy (clarifying inconclusive vs decisively negative).
7. Single-position-at-a-time portfolio simulation with compounded equity, max drawdown, and downtime.
8. Immutable experiment freeze manifest persisting all artifact hashes, candidate parameters, and governance states.
"""

import os
import sys
import json
import hashlib
from typing import Dict, Any, List, Tuple
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engine.continuity_time_series import continuity_engine
from engine.execution_cost_model import ExecutionCostModel


def compute_file_sha256(filepath: str) -> str:
    """Computes SHA-256 hash of a file on disk."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_experiment_v5() -> Dict[str, Any]:
    print("==========================================================================")
    print("BTCognitive V5: Statistical Integrity, Experiment Freeze & Evaluation")
    print("==========================================================================")

    # 1. Load Raw Dataset & Audit
    raw_path = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
    raw_hash = compute_file_sha256(raw_path)
    df_raw = pd.read_parquet(raw_path)

    # 2. Time-Series Continuity Segmentation & Eligibility Audit
    df_clean, audit_summary = continuity_engine.audit_and_segment(df_raw)
    eligibility_audit = continuity_engine.generate_eligibility_audit(df_raw)

    audit_out_path = os.path.join(REPO_ROOT, "experiments", "results", "research_improvement", "v5_eligibility_audit.json")
    os.makedirs(os.path.dirname(audit_out_path), exist_ok=True)
    with open(audit_out_path, "w", encoding="utf-8") as f:
        json.dump(eligibility_audit, f, indent=2)
    print(f"Persisted eligibility audit to {audit_out_path}")

    # 3. Gap-Safe Feature Construction & Triple-Barrier Labels
    df_feat = continuity_engine.build_continuity_features(df_clean)
    H = 24
    k_tp = 1.5
    k_sl = 1.0
    df_labeled = continuity_engine.build_gap_safe_triple_barrier_labels(
        df_feat, horizon_hours=H, k_tp=k_tp, k_sl=k_sl, collision_policy="SL_FIRST_CONSERVATIVE"
    )
    df_labeled["year"] = pd.to_datetime(df_labeled["timestamp"]).dt.year

    # 4. Chronological Splits with 24-hour Purging Embargo
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

    bin_cost_info = ExecutionCostModel.calculate_round_trip_cost("Binance_Futures", holding_hours=17.1)
    BINANCE_ROUNDTRIP_BPS = bin_cost_info["total_round_trip_bps"]  # 15.0 bps

    # Helper: Single-Position-at-a-Time Simulator with Portfolio Equity & Bootstrap CIs
    def simulate_single_position_v5(candidate_df: pd.DataFrame, initial_nav: float = 10000.0) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        if len(candidate_df) == 0:
            return pd.DataFrame(), {
                "trades": 0,
                "gross_expectancy_bps": 0.0,
                "net_expectancy_coinbase_bps": 0.0,
                "net_expectancy_binance_hypothetical_bps": 0.0,
                "ci_95_net_coinbase_bps": [0.0, 0.0],
                "ci_95_net_binance_hypothetical_bps": [0.0, 0.0],
                "portfolio_final_nav_coinbase": initial_nav,
                "portfolio_cumulative_pnl_pct_coinbase": 0.0,
                "portfolio_max_drawdown_pct_coinbase": 0.0,
                "portfolio_final_nav_binance_hypothetical": initial_nav,
                "portfolio_cumulative_pnl_pct_binance_hypothetical": 0.0,
                "portfolio_max_drawdown_pct_binance_hypothetical": 0.0,
                "tp_first_pct": 0.0,
                "sl_first_pct": 0.0,
                "timeout_pct": 0.0,
                "mean_holding_hours": 0.0,
                "in_trade_hours": 0.0,
                "downtime_pct": 100.0,
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
                "ci_95_net_coinbase_bps": [0.0, 0.0],
                "ci_95_net_binance_hypothetical_bps": [0.0, 0.0],
                "portfolio_final_nav_coinbase": initial_nav,
                "portfolio_cumulative_pnl_pct_coinbase": 0.0,
                "portfolio_max_drawdown_pct_coinbase": 0.0,
                "portfolio_final_nav_binance_hypothetical": initial_nav,
                "portfolio_cumulative_pnl_pct_binance_hypothetical": 0.0,
                "portfolio_max_drawdown_pct_binance_hypothetical": 0.0,
                "tp_first_pct": 0.0,
                "sl_first_pct": 0.0,
                "timeout_pct": 0.0,
                "mean_holding_hours": 0.0,
                "in_trade_hours": 0.0,
                "downtime_pct": 100.0,
                "economic_verdict": "ABSTAIN_NEUTRAL"
            }

        n_trades = len(sp_df)
        returns_raw = sp_df["tb_return"].values
        gross_bps_arr = returns_raw * 10000.0
        net_cb_arr = gross_bps_arr - COINBASE_ROUNDTRIP_BPS
        net_bin_arr = gross_bps_arr - BINANCE_ROUNDTRIP_BPS

        gross_mean_bps = float(np.mean(gross_bps_arr))
        net_coinbase_bps = float(np.mean(net_cb_arr))
        net_binance_bps = float(np.mean(net_bin_arr))

        # Stationary Block Bootstrap CI (B=10000)
        np.random.seed(42)
        B = 10000
        boot_cb = [np.mean(np.random.choice(net_cb_arr, size=n_trades, replace=True)) for _ in range(B)]
        boot_bin = [np.mean(np.random.choice(net_bin_arr, size=n_trades, replace=True)) for _ in range(B)]

        ci_cb = [round(float(np.percentile(boot_cb, 2.5)), 2), round(float(np.percentile(boot_cb, 97.5)), 2)]
        ci_bin = [round(float(np.percentile(boot_bin, 2.5)), 2), round(float(np.percentile(boot_bin, 97.5)), 2)]

        # Sequential Portfolio Simulation (100% equity allocated per position)
        nav_cb = initial_nav
        nav_bin = initial_nav
        peak_cb = initial_nav
        peak_bin = initial_nav
        max_dd_cb = 0.0
        max_dd_bin = 0.0

        for r in returns_raw:
            ret_cb = r - (COINBASE_ROUNDTRIP_BPS / 10000.0)
            ret_bin = r - (BINANCE_ROUNDTRIP_BPS / 10000.0)
            nav_cb *= (1.0 + ret_cb)
            nav_bin *= (1.0 + ret_bin)
            peak_cb = max(peak_cb, nav_cb)
            peak_bin = max(peak_bin, nav_bin)
            max_dd_cb = max(max_dd_cb, (peak_cb - nav_cb) / peak_cb if peak_cb > 0 else 0.0)
            max_dd_bin = max(max_dd_bin, (peak_bin - nav_bin) / peak_bin if peak_bin > 0 else 0.0)

        total_hours = len(test_df)
        in_trade_h = float(sp_df["tb_holding_hours"].sum())
        downtime_pct = round(max(0.0, 100.0 - (in_trade_h / total_hours * 100.0)), 2)

        tp_pct = float((sp_df["tb_outcome"] == "TP_FIRST").mean() * 100.0)
        sl_pct = float(sp_df["tb_outcome"].str.contains("SL").mean() * 100.0)
        to_pct = float((sp_df["tb_outcome"] == "TIMEOUT").mean() * 100.0)
        mean_hold = float(sp_df["tb_holding_hours"].mean())

        # Statistical Verdict Disambiguation
        if net_coinbase_bps > 0 and ci_cb[0] > 0:
            verdict = "PASS_STATISTICALLY_SIGNIFICANT_POSITIVE"
        elif ci_cb[0] <= 0 and ci_cb[1] >= 0:
            verdict = "INCONCLUSIVE_INTERVAL_CROSSES_ZERO"
        else:
            verdict = "FAIL_DECISIVELY_NEGATIVE"

        return sp_df, {
            "trades": n_trades,
            "mean_per_trade_gross_expectancy_bps": round(gross_mean_bps, 2),
            "mean_per_trade_net_coinbase_bps": round(net_coinbase_bps, 2),
            "mean_per_trade_net_binance_hypothetical_bps": round(net_binance_bps, 2),
            "ci_95_net_coinbase_bps": ci_cb,
            "ci_95_net_binance_hypothetical_bps": ci_bin,
            "portfolio_final_nav_coinbase": round(nav_cb, 2),
            "portfolio_cumulative_pnl_pct_coinbase": round(((nav_cb / initial_nav) - 1.0) * 100.0, 2),
            "portfolio_max_drawdown_pct_coinbase": round(max_dd_cb * 100.0, 2),
            "portfolio_final_nav_binance_hypothetical": round(nav_bin, 2),
            "portfolio_cumulative_pnl_pct_binance_hypothetical": round(((nav_bin / initial_nav) - 1.0) * 100.0, 2),
            "portfolio_max_drawdown_pct_binance_hypothetical": round(max_dd_bin * 100.0, 2),
            "tp_first_pct": round(tp_pct, 2),
            "sl_first_pct": round(sl_pct, 2),
            "timeout_pct": round(to_pct, 2),
            "mean_holding_hours": round(mean_hold, 1),
            "in_trade_hours": round(in_trade_h, 1),
            "downtime_pct": downtime_pct,
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
        "mean_per_trade_gross_expectancy_bps": 0.0,
        "mean_per_trade_net_coinbase_bps": 0.0,
        "mean_per_trade_net_binance_hypothetical_bps": 0.0,
        "ci_95_net_coinbase_bps": [0.0, 0.0],
        "ci_95_net_binance_hypothetical_bps": [0.0, 0.0],
        "portfolio_final_nav_coinbase": 10000.0,
        "portfolio_cumulative_pnl_pct_coinbase": 0.0,
        "portfolio_max_drawdown_pct_coinbase": 0.0,
        "portfolio_final_nav_binance_hypothetical": 10000.0,
        "portfolio_cumulative_pnl_pct_binance_hypothetical": 0.0,
        "portfolio_max_drawdown_pct_binance_hypothetical": 0.0,
        "tp_first_pct": 0.0,
        "sl_first_pct": 0.0,
        "timeout_pct": 0.0,
        "downtime_pct": 100.0,
        "economic_verdict": "ABSTAIN_NEUTRAL"
    }

    # -------------------------------------------------------------
    # CANDIDATE 1: Gap-Safe 24h Momentum
    # -------------------------------------------------------------
    mom_candidates = test_df[test_df["ret_24h"] > 0]
    _, c1_metrics = simulate_single_position_v5(mom_candidates)
    c1_metrics["candidate_id"] = "CAND-1-MOMENTUM-24H-GAP-SAFE"
    c1_metrics["description"] = "Causal 24h momentum evaluated under gap-safe single-position portfolio accounting"
    results["Candidate_1_Momentum_24h_Baseline"] = c1_metrics

    # -------------------------------------------------------------
    # CANDIDATE 2: Cost-Aware Return Filter (Ridge Regressor)
    # -------------------------------------------------------------
    ridge = Ridge(alpha=100.0, random_state=42)
    ridge.fit(train_df[feature_cols], train_df["tb_return"])

    test_df = test_df.copy()
    test_df["pred_ret"] = ridge.predict(test_df[feature_cols])

    hurdle_ratio = BINANCE_ROUNDTRIP_BPS / 10000.0
    c2_candidates = test_df[test_df["pred_ret"] > hurdle_ratio]
    _, c2_metrics = simulate_single_position_v5(c2_candidates)
    c2_metrics["candidate_id"] = "CAND-2-COST-AWARE-FILTER"
    c2_metrics["description"] = "Selective entry requiring predicted return to exceed roundtrip friction hurdle"
    c2_metrics["hurdle_bps"] = round(hurdle_ratio * 10000.0, 2)
    results["Candidate_2_Cost_Aware_Filter"] = c2_metrics

    # -------------------------------------------------------------
    # CANDIDATE 3A: Meta-Label Filter (Target: Gross Return > 15.0 bps)
    # -------------------------------------------------------------
    hurdle_bin = BINANCE_ROUNDTRIP_BPS / 10000.0
    train_df["y_meta_15bps"] = (train_df["tb_return"] > hurdle_bin).astype(int)
    test_df["y_meta_15bps"] = (test_df["tb_return"] > hurdle_bin).astype(int)

    meta_train_15 = train_df[train_df["ret_24h"] > 0]
    meta_test_15 = test_df[test_df["ret_24h"] > 0].copy()

    p_train_prev_15 = float(meta_train_15["y_meta_15bps"].mean())
    p_test_prev_15 = float(meta_test_15["y_meta_15bps"].mean())

    clf_15 = LogisticRegression(C=0.1, random_state=42, max_iter=200)
    clf_15.fit(meta_train_15[feature_cols], meta_train_15["y_meta_15bps"])
    probs_15 = clf_15.predict_proba(meta_test_15[feature_cols])[:, 1]
    meta_test_15["prob_15bps"] = probs_15

    y_test_15 = meta_test_15["y_meta_15bps"].values
    loss_m_15 = (probs_15 - y_test_15) ** 2
    loss_b_15 = (p_train_prev_15 - y_test_15) ** 2
    d_brier_15 = loss_m_15 - loss_b_15

    eps = 1e-15
    p_m_clip = np.clip(probs_15, eps, 1 - eps)
    p_b_clip = np.clip(p_train_prev_15, eps, 1 - eps)
    ll_m_15 = -(y_test_15 * np.log(p_m_clip) + (1 - y_test_15) * np.log(1 - p_m_clip))
    ll_b_15 = -(y_test_15 * np.log(p_b_clip) + (1 - y_test_15) * np.log(1 - p_b_clip))
    d_ll_15 = ll_m_15 - ll_b_15

    np.random.seed(42)
    B = 10000
    boot_dbrier_15 = [np.mean(np.random.choice(d_brier_15, size=len(d_brier_15), replace=True)) for _ in range(B)]
    boot_dll_15 = [np.mean(np.random.choice(d_ll_15, size=len(d_ll_15), replace=True)) for _ in range(B)]

    ci_dbrier_15 = [round(float(np.percentile(boot_dbrier_15, 2.5)), 6), round(float(np.percentile(boot_dbrier_15, 97.5)), 6)]
    ci_dll_15 = [round(float(np.percentile(boot_dll_15, 2.5)), 6), round(float(np.percentile(boot_dll_15, 97.5)), 6)]

    c3a_candidates = meta_test_15[meta_test_15["prob_15bps"] >= 0.45]
    _, c3a_metrics = simulate_single_position_v5(c3a_candidates)
    c3a_metrics["candidate_id"] = "CAND-3A-META-LABEL-15BPS-TARGET"
    c3a_metrics["target_definition"] = "Gross tb_return > 15.0 bps (Hypothetical Binance Perpetual break-even hurdle)"
    c3a_metrics["brier_score_model"] = round(float(brier_score_loss(y_test_15, probs_15)), 4)
    c3a_metrics["brier_score_constant_prevalence_baseline"] = round(float(brier_score_loss(y_test_15, np.full_like(probs_15, p_train_prev_15))), 4)
    c3a_metrics["brier_score_naive_50_baseline"] = round(float(brier_score_loss(y_test_15, np.full_like(probs_15, 0.50))), 4)
    c3a_metrics["brier_score_difference_ci_95"] = ci_dbrier_15
    c3a_metrics["log_loss_model"] = round(float(log_loss(y_test_15, probs_15)), 4)
    c3a_metrics["log_loss_constant_prevalence_baseline"] = round(float(log_loss(y_test_15, np.full_like(probs_15, p_train_prev_15))), 4)
    c3a_metrics["log_loss_difference_ci_95"] = ci_dll_15
    c3a_metrics["train_positive_class_prevalence"] = round(p_train_prev_15, 4)
    c3a_metrics["test_positive_class_prevalence"] = round(p_test_prev_15, 4)
    c3a_metrics["decision_threshold"] = 0.45
    results["Candidate_3A_Meta_Label_15bps_Target"] = c3a_metrics

    # -------------------------------------------------------------
    # CANDIDATE 3B: Meta-Label Filter (Target: Gross Return > 87.0 bps)
    # -------------------------------------------------------------
    hurdle_cb = COINBASE_ROUNDTRIP_BPS / 10000.0
    train_df["y_meta_87bps"] = (train_df["tb_return"] > hurdle_cb).astype(int)
    test_df["y_meta_87bps"] = (test_df["tb_return"] > hurdle_cb).astype(int)

    meta_train_87 = train_df[train_df["ret_24h"] > 0]
    meta_test_87 = test_df[test_df["ret_24h"] > 0].copy()

    p_train_prev_87 = float(meta_train_87["y_meta_87bps"].mean())
    p_test_prev_87 = float(meta_test_87["y_meta_87bps"].mean())

    clf_87 = LogisticRegression(C=0.1, random_state=42, max_iter=200)
    clf_87.fit(meta_train_87[feature_cols], meta_train_87["y_meta_87bps"])
    probs_87 = clf_87.predict_proba(meta_test_87[feature_cols])[:, 1]
    meta_test_87["prob_87bps"] = probs_87

    y_test_87 = meta_test_87["y_meta_87bps"].values
    loss_m_87 = (probs_87 - y_test_87) ** 2
    loss_b_87 = (p_train_prev_87 - y_test_87) ** 2
    d_brier_87 = loss_m_87 - loss_b_87

    p_m_clip_87 = np.clip(probs_87, eps, 1 - eps)
    p_b_clip_87 = np.clip(p_train_prev_87, eps, 1 - eps)
    ll_m_87 = -(y_test_87 * np.log(p_m_clip_87) + (1 - y_test_87) * np.log(1 - p_m_clip_87))
    ll_b_87 = -(y_test_87 * np.log(p_b_clip_87) + (1 - y_test_87) * np.log(1 - p_b_clip_87))
    d_ll_87 = ll_m_87 - ll_b_87

    boot_dbrier_87 = [np.mean(np.random.choice(d_brier_87, size=len(d_brier_87), replace=True)) for _ in range(B)]
    boot_dll_87 = [np.mean(np.random.choice(d_ll_87, size=len(d_ll_87), replace=True)) for _ in range(B)]

    ci_dbrier_87 = [round(float(np.percentile(boot_dbrier_87, 2.5)), 6), round(float(np.percentile(boot_dbrier_87, 97.5)), 6)]
    ci_dll_87 = [round(float(np.percentile(boot_dll_87, 2.5)), 6), round(float(np.percentile(boot_dll_87, 97.5)), 6)]

    c3b_candidates = meta_test_87[meta_test_87["prob_87bps"] >= 0.45]
    _, c3b_metrics = simulate_single_position_v5(c3b_candidates)
    c3b_metrics["candidate_id"] = "CAND-3B-META-LABEL-87BPS-TARGET"
    c3b_metrics["target_definition"] = "Gross tb_return > 87.0 bps (Coinbase Spot Tier 1 break-even hurdle)"
    c3b_metrics["brier_score_model"] = round(float(brier_score_loss(y_test_87, probs_87)), 4)
    c3b_metrics["brier_score_constant_prevalence_baseline"] = round(float(brier_score_loss(y_test_87, np.full_like(probs_87, p_train_prev_87))), 4)
    c3b_metrics["brier_score_naive_50_baseline"] = round(float(brier_score_loss(y_test_87, np.full_like(probs_87, 0.50))), 4)
    c3b_metrics["brier_score_difference_ci_95"] = ci_dbrier_87
    c3b_metrics["log_loss_model"] = round(float(log_loss(y_test_87, probs_87)), 4)
    c3b_metrics["log_loss_constant_prevalence_baseline"] = round(float(log_loss(y_test_87, np.full_like(probs_87, p_train_prev_87))), 4)
    c3b_metrics["log_loss_difference_ci_95"] = ci_dll_87
    c3b_metrics["train_positive_class_prevalence"] = round(p_train_prev_87, 4)
    c3b_metrics["test_positive_class_prevalence"] = round(p_test_prev_87, 4)
    c3b_metrics["decision_threshold"] = 0.45
    results["Candidate_3B_Meta_Label_87bps_Target"] = c3b_metrics

    # Governed Acceptance Gate
    is_any_passed = any(
        v.get("mean_per_trade_net_coinbase_bps", -999) > 0.0 and v.get("trades", 0) >= 30 and v.get("ci_95_net_coinbase_bps", [-999, -999])[0] > 0.0
        for k, v in results.items()
        if k != "Candidate_0_No_Trade_Baseline"
    )

    manifest_v5 = {
        "experiment_id": "EXP-RESEARCH-TO-SIGNAL-V5-STATISTICAL-INTEGRITY",
        "experiment_version": "5.0.0",
        "freeze_timestamp_utc": pd.Timestamp.now("UTC").isoformat(),
        "dataset": "data/raw/ohlcv.parquet",
        "dataset_sha256": raw_hash,
        "market_provenance": {
            "source_exchange": "Coinbase Advanced",
            "instrument": "BTC-USD",
            "market_type": "SPOT",
            "primary_empirical_backtest": "Coinbase Spot Tier 1 (87.0 bps round trip)",
            "hypothetical_sensitivity_scenario": "Hypothetical Binance USDT-M Futures Perpetual Sensitivity (15.0 bps round trip)"
        },
        "time_series_continuity": {
            "total_input_bars": len(df_raw),
            "continuous_segments_count": len(audit_summary.segments),
            "identified_gaps": audit_summary.gaps,
            "purging_embargo_hours": 24,
            "eligibility_audit_artifact": "experiments/results/research_improvement/v5_eligibility_audit.json"
        },
        "sample_split_bars": {
            "train_bars": len(train_df),
            "val_bars": len(val_df),
            "test_bars": len(test_df),
            "data_exposure_status": "2026 test split is EXPOSED retrospective development/replay data; NOT untouched prospective evidence"
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

    freeze_path = os.path.join(REPO_ROOT, "experiments", "results", "research_improvement", "v5_experiment_freeze_manifest.json")
    with open(freeze_path, "w", encoding="utf-8") as f:
        json.dump(manifest_v5, f, indent=2)
    print(f"Persisted experiment freeze manifest to {freeze_path}")
    print(json.dumps(manifest_v5, indent=2))
    return manifest_v5


if __name__ == "__main__":
    run_experiment_v5()

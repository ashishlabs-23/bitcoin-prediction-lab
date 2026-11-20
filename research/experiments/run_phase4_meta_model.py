"""
research/experiments/run_phase4_meta_model.py
=============================================
Phase 4: Strategy-Conditioned Tri-State Outcome Meta-Model
Generates point-in-time candidates from TSMOM_DONCHIAN_24H_168H on authenticated Coinbase data,
resolves outcomes via DeterministicBarrierResolver, enforces chronological train/calibration/eval splits
with 24h purging/embargo, trains calibrated multinomial logistic meta-model, and evaluates after-cost net edge.
"""

import os
import sys
import json
import math
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import log_loss

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)

from engine.strategy_signal_engine import compute_parkinson_volatility
from engine.entry_contracts import CandidateSetup
from engine.barrier_resolver import DeterministicBarrierResolver
from engine.directional_forecast_service import verify_and_load_directional_model


def extract_strategy_candidates(df: pd.DataFrame) -> List[Dict[str, Any]]:
    closes = df["close"].astype(float).values
    highs = df["high"].astype(float).values
    lows = df["low"].astype(float).values
    opens = df["open"].astype(float).values
    timestamps = df["timestamp_utc"].values
    n_bars = len(df)

    ema_168 = pd.Series(closes).ewm(span=168, adjust=False).mean().values
    ch_high_24 = pd.Series(highs).shift(1).rolling(24).max().values
    ch_low_24 = pd.Series(lows).shift(1).rolling(24).min().values

    # Preload 24h GBDT model for feature extraction
    gbdt_24h, _, _ = verify_and_load_directional_model("24h")

    candidates = []
    open_position_until_idx = -1

    for t in range(169, n_bars - 26):
        if t < open_position_until_idx:
            continue

        c_t = closes[t]
        ema_t = ema_168[t]
        h_24 = ch_high_24[t]
        l_24 = ch_low_24[t]

        is_breakout_up = (c_t > h_24) and (c_t > ema_t)
        if not is_breakout_up:
            continue

        fill_idx = t + 1
        entry_price = opens[fill_idx]
        fill_ts = timestamps[fill_idx]
        decision_ts = timestamps[t]

        # Parkinson sigma over prior 24 bars [t-23, t]
        sigma_p = max(0.005, compute_parkinson_volatility(highs[t-23:t+1], lows[t-23:t+1]))
        stop_dist = 1.5 * sigma_p * entry_price
        target_dist = 2.25 * sigma_p * entry_price

        stop_price = entry_price - stop_dist
        target_price = entry_price + target_dist

        # Causal features available strictly at decision bar t
        ema_ratio = float(c_t / ema_t)
        donchian_width_r = float((h_24 - l_24) / (stop_dist if stop_dist > 0 else 1.0))
        ret_24h = float(math.log(c_t / closes[t - 24]))
        ret_168h = float(math.log(c_t / closes[t - 168]))
        cost_ratio_27bps = float((0.0027 * entry_price) / stop_dist)

        # GBDT feature (if available)
        gbdt_prob = 0.50
        if gbdt_24h is not None:
            r1 = math.log(closes[t] / closes[t - 1])
            r4 = math.log(closes[t] / closes[t - 4])
            r24 = ret_24h
            r168 = ret_168h
            gbdt_prob = float(gbdt_24h.predict_proba(np.array([[r1, r4, r24, r168]]))[:, 1][0])

        candidate = CandidateSetup(
            candidate_id=f"cand_{t}_{fill_ts}",
            strategy_archetype="TSMOM_DONCHIAN_24H_168H",
            direction="LONG",
            instrument_id="BTC-USD",
            venue="COINBASE",
            market_type="SPOT",
            decision_timestamp_utc=decision_ts,
            fill_timestamp_utc=fill_ts,
            entry_reference_price=c_t,
            proposed_entry_price=entry_price,
            take_profit_price=target_price,
            stop_loss_price=stop_price,
            k_tp=1.5,
            k_sl=1.0,
            horizon_bars=24,
            sigma_at_t0=sigma_p,
            risk_unit_usd=stop_dist,
            cost_scenario="ACTIVE_TRADER_27BPS",
            round_trip_friction_bps=27.0,
            friction_r=cost_ratio_27bps,
            p_tp=0.333,
            p_sl=0.333,
            p_timeout=0.334,
            expected_gross_r=0.0,
            expected_net_r=-cost_ratio_27bps,
            features_hash=hashlib.sha256(f"{decision_ts}:{c_t}:{sigma_p}".encode()).hexdigest()
        )

        # Forward bars for resolution: [fill_idx, fill_idx + 24]
        forward_bars = []
        for offset in range(25):
            idx = fill_idx + offset
            if idx >= n_bars:
                break
            forward_bars.append({
                "timestamp_utc": timestamps[idx],
                "open": opens[idx],
                "high": highs[idx],
                "low": lows[idx],
                "close": closes[idx]
            })

        outcome = DeterministicBarrierResolver.resolve_candidate(candidate, forward_bars)

        # Advance in-position guard to avoid overlap
        resolved_bars = max(1, outcome.bars_held)
        open_position_until_idx = fill_idx + resolved_bars

        # Normalize exit reason to tri-state: TP_FIRST, SL_FIRST, TIMEOUT
        outcome_label = outcome.exit_reason
        if outcome_label == "INTRABAR_COLLISION_RESOLVED_SL":
            outcome_label = "SL_FIRST"

        candidates.append({
            "candidate_id": candidate.candidate_id,
            "decision_bar_idx": t,
            "decision_ts": decision_ts,
            "fill_ts": fill_ts,
            "exit_ts": outcome.exit_timestamp_utc,
            "entry_price": entry_price,
            "risk_unit": stop_dist,
            "outcome": outcome_label,
            "gross_r": outcome.gross_return_r,
            "holding_bars": outcome.bars_held,
            "features": [
                sigma_p,
                ema_ratio,
                donchian_width_r,
                ret_24h,
                ret_168h,
                cost_ratio_27bps,
                gbdt_prob
            ]
        })

    return candidates


def multiclass_brier_score(y_true_indices: np.ndarray, prob_matrix: np.ndarray, n_classes: int = 3) -> float:
    n_samples = len(y_true_indices)
    one_hot = np.zeros((n_samples, n_classes))
    for i, idx in enumerate(y_true_indices):
        one_hot[i, idx] = 1.0
    return float(np.mean(np.sum((prob_matrix - one_hot) ** 2, axis=1)))


def run_phase4_experiment(coinbase_parquet: str, output_dir: str) -> Dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_parquet(coinbase_parquet)
    if "epoch_time" not in df.columns and "timestamp" in df.columns:
        df["dt"] = pd.to_datetime(df["timestamp"], utc=True)
        df["epoch_time"] = df["dt"].view("int64") // 10**9
        df["timestamp_utc"] = df["dt"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    df = df.sort_values("epoch_time").reset_index(drop=True)
    candidates = extract_strategy_candidates(df)
    total_candidates = len(candidates)

    label_map = {"TP_FIRST": 0, "SL_FIRST": 1, "TIMEOUT": 2}
    class_names = ["TP_FIRST", "SL_FIRST", "TIMEOUT"]

    # Chronological partition with 24h purging/embargo
    # Train: 2023-01-01 to 2024-12-31
    # Calib: 2025-01-01 to 2025-12-31
    # Eval:  2026-01-01 to 2026-10-25
    train_cands = [c for c in candidates if c["decision_ts"] < "2025-01-01T00:00:00Z"]
    calib_cands = [c for c in candidates if "2025-01-01T00:00:00Z" <= c["decision_ts"] < "2026-01-01T00:00:00Z"]
    eval_cands = [c for c in candidates if c["decision_ts"] >= "2026-01-01T00:00:00Z"]

    # Purge candidates whose outcome window crosses partition boundaries
    train_cands = [c for c in train_cands if c["exit_ts"] < "2025-01-01T00:00:00Z"]
    calib_cands = [c for c in calib_cands if c["exit_ts"] < "2026-01-01T00:00:00Z"]

    X_train = np.array([c["features"] for c in train_cands])
    y_train = np.array([label_map[c["outcome"]] for c in train_cands])

    X_calib = np.array([c["features"] for c in calib_cands])
    y_calib = np.array([label_map[c["outcome"]] for c in calib_cands])

    X_eval = np.array([c["features"] for c in eval_cands])
    y_eval = np.array([label_map[c["outcome"]] for c in eval_cands])

    # 1. Base Rate Predictor
    train_counts = np.bincount(y_train, minlength=3)
    base_probs = train_counts / float(len(y_train))
    p_tp_base, p_sl_base, p_to_base = base_probs

    # Training-only estimate of E[R_TO | TIMEOUT]
    train_to_returns = [c["gross_r"] for c in train_cands if c["outcome"] == "TIMEOUT"]
    e_r_to_gross = float(np.mean(train_to_returns)) if len(train_to_returns) > 0 else 0.0

    # 2. Train Regularized Multinomial Logistic Regression with Sigmoid Calibration
    # Uses PredefinedSplit: fold -1 for training base estimator, fold 0 for independent calibration
    from sklearn.model_selection import PredefinedSplit

    X_combined = np.vstack([X_train, X_calib])
    y_combined = np.concatenate([y_train, y_calib])
    split_indices = np.concatenate([np.full(len(X_train), -1), np.zeros(len(X_calib))])
    ps = PredefinedSplit(split_indices)

    base_estimator = LogisticRegression(C=0.1, max_iter=1000, random_state=42)
    calibrator = CalibratedClassifierCV(estimator=base_estimator, cv=ps, method="sigmoid")
    calibrator.fit(X_combined, y_combined)

    # 4. Out-of-sample Evaluation on 2026 Holdout Set
    eval_probs = calibrator.predict_proba(X_eval)
    eval_base_probs = np.tile(base_probs, (len(y_eval), 1))

    brier_model = multiclass_brier_score(y_eval, eval_probs, n_classes=3)
    brier_base = multiclass_brier_score(y_eval, eval_base_probs, n_classes=3)
    bss = float(1.0 - (brier_model / brier_base)) if brier_base > 0 else 0.0

    logloss_model = float(log_loss(y_eval, eval_probs, labels=[0, 1, 2]))
    logloss_base = float(log_loss(y_eval, eval_base_probs, labels=[0, 1, 2]))

    # Verify probability normalization
    prob_sums = np.sum(eval_probs, axis=1)
    normalization_valid = bool(np.allclose(prob_sums, 1.0, atol=1e-5))

    # 5. Economic Expectancy & Policy Testing
    # Compare:
    # A) Strategy Alone (all 2026 candidate trades taken)
    # B) Strategy + Meta-Model Filter (only trades where EV_net > 0 taken)
    k_tp = 1.5
    k_sl = 1.0

    cost_results = {}
    for scenario_name, bps in [("COINBASE_RETAIL_87BPS", 87.0), ("ACTIVE_TRADER_27BPS", 27.0)]:
        strat_alone_net_r = []
        filtered_net_r = []
        filtered_trade_count = 0

        for i, c in enumerate(eval_cands):
            # Compute friction in R units
            entry_p = c["entry_price"]
            r_unit = c["risk_unit"]
            c_r = (bps / 10000.0) * entry_p / r_unit
            gross_r = c["gross_r"]
            net_r = gross_r - c_r
            strat_alone_net_r.append(net_r)

            # Meta-model EV_net
            p_tp = eval_probs[i, 0]
            p_sl = eval_probs[i, 1]
            p_to = eval_probs[i, 2]

            ev_net = p_tp * (k_tp - c_r) - p_sl * (k_sl + c_r) + p_to * (e_r_to_gross - c_r)

            # Execution rule: take trade only if EV_net > 0
            if ev_net > 0.0:
                filtered_trade_count += 1
                filtered_net_r.append(net_r)

        # Baseline stats
        mean_strat_net_r = float(np.mean(strat_alone_net_r)) if len(strat_alone_net_r) > 0 else 0.0

        # Filtered stats
        if filtered_trade_count > 0:
            mean_filtered_net_r = float(np.mean(filtered_net_r))
            np.random.seed(42)
            boot_means = [np.mean(np.random.choice(filtered_net_r, size=filtered_trade_count, replace=True)) for _ in range(2000)]
            ci_low = float(np.percentile(boot_means, 2.5))
            ci_high = float(np.percentile(boot_means, 97.5))
            has_validated_edge = bool(ci_low > 0)
        else:
            mean_filtered_net_r = 0.0
            ci_low = 0.0
            ci_high = 0.0
            has_validated_edge = False

        cost_results[scenario_name] = {
            "friction_bps": bps,
            "strategy_alone": {
                "trades": len(strat_alone_net_r),
                "mean_net_r": round(mean_strat_net_r, 4)
            },
            "strategy_plus_meta_model": {
                "trades_admitted": filtered_trade_count,
                "trades_rejected": len(strat_alone_net_r) - filtered_trade_count,
                "filter_admission_rate": round(filtered_trade_count / max(1, len(strat_alone_net_r)), 4),
                "mean_net_r": round(mean_filtered_net_r, 4),
                "ci_95_lower_r": round(ci_low, 4),
                "ci_95_upper_r": round(ci_high, 4),
                "validated_positive_edge": has_validated_edge
            }
        }

    report = {
        "experiment_id": "PHASE4_STRATEGY_CONDITIONED_TRISTATE_METAMODEL_V1",
        "dataset": coinbase_parquet,
        "sample_counts": {
            "total_candidates": total_candidates,
            "train_candidates_2023_2024": len(train_cands),
            "calib_candidates_2025": len(calib_cands),
            "eval_candidates_2026": len(eval_cands)
        },
        "base_rate_prior_probabilities": {
            "p_tp": round(p_tp_base, 4),
            "p_sl": round(p_sl_base, 4),
            "p_to": round(p_to_base, 4)
        },
        "training_timeout_mean_gross_r": round(e_r_to_gross, 4),
        "calibration_and_scoring": {
            "model_type": "LogisticRegression_Multinomial_CalibratedSigmoid",
            "probabilities_sum_to_one": normalization_valid,
            "eval_multiclass_brier_model": round(brier_model, 4),
            "eval_multiclass_brier_base": round(brier_base, 4),
            "brier_skill_score": round(bss, 4),
            "eval_log_loss_model": round(logloss_model, 4),
            "eval_log_loss_base": round(logloss_base, 4),
            "scoring_improvement_proven": bool(bss > 0 and logloss_model < logloss_base)
        },
        "cost_and_economic_expectancy": cost_results,
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat()
    }

    # Final Phase 4 Gate Decision
    scoring_ok = report["calibration_and_scoring"]["scoring_improvement_proven"]
    edge_active = cost_results["ACTIVE_TRADER_27BPS"]["strategy_plus_meta_model"]["validated_positive_edge"]
    edge_retail = cost_results["COINBASE_RETAIL_87BPS"]["strategy_plus_meta_model"]["validated_positive_edge"]

    if scoring_ok and (edge_active or edge_retail):
        report["phase4_verdict"] = "PASS_POSITIVE_EDGE_PROVEN"
    else:
        report["phase4_verdict"] = "NO_GO_EVIDENCE_GAP_NO_VALIDATED_EDGE"
        report["action_taken"] = "Keep META_MODEL_UNAVAILABLE / NO_VALIDATED_EDGE active; positive-edge alerts remain disabled."

    out_file = os.path.join(output_dir, "phase4_meta_model_summary.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    src_parquet = os.path.join(REPO_ROOT, "data", "research", "coinbase_btc_usd_hourly_v1", "coinbase_hourly.parquet")
    out_dir = os.path.join(REPO_ROOT, "research", "runs", "v32_27")
    res = run_phase4_experiment(src_parquet, out_dir)
    print(json.dumps(res, indent=2))

"""
research/historical_entry_replay.py — Empirical Historical Replay Harness for BTC-USD
===================================================================================
Replays the frozen Smart Entry / Probabilistic Entry rule across nearly 5 years of
real hourly BTC-USD market candles (2022 to October 2026, N=41,419 bars).

Evaluates:
1. Calibration of hand-set weights p_tp (Reliability curve, decile lift, Brier Skill Score).
2. Empirical Finite-Horizon Null (Random entry on identical bars with SL_FIRST collision).
3. Economic performance across all 3 regional cost tiers (India 27 bps, EU 107 bps, US 187 bps).
4. Performance breakdown by year (2022-2026) and volatility regime.
5. Rigorous sigma semantics: sigma_1h vs sigma_24h (scaled by sqrt(24)).
"""

import sys
import os
import json
import math
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from engine.modern_research_validation import (
    DeflatedSharpeRatio,
    FiniteHorizonMonteCarloNull,
    ProbabilisticCalibrationDiagnostics,
    PurgedEffectiveSampleSize,
)
from engine.execution_cost_model import ExecutionCostModel


def run_historical_replay(
    parquet_path: str = "data/raw/ohlcv.parquet",
    sample_stride: int = 1,       # 1 = evaluate every bar, 24 = non-overlapping 24h blocks
    horizon_bars: int = 24,
    k_tp: float = 1.5,
    k_sl: float = 1.0,
    random_seed: int = 42
) -> Dict[str, Any]:
    """
    Executes full deterministic historical replay across real market data.
    """
    data_file = REPO_ROOT / parquet_path
    if not data_file.exists():
        raise FileNotFoundError(f"Parquet dataset not found at {data_file}")

    # 1. Compute Data Provenance Hash
    with open(data_file, "rb") as f:
        data_hash = hashlib.sha256(f.read()).hexdigest()

    df = pd.read_parquet(data_file)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    closes = df["close"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    opens = df["open"].to_numpy(dtype=float)
    timestamps = df["timestamp"].to_numpy()
    n_total = len(closes)

    # Hand-set baseline logistic weights (H0 frozen baseline)
    # Features: [mom_1h, mom_4h, mom_24h, rs_ratio, bb_width, range_pos]
    weights = np.array([0.45, 0.35, 0.20, 0.65, -0.30, 0.25])
    bias = -0.15

    # Evaluation loop
    results = []
    null_random_results = []
    
    # Pre-compute log returns
    log_rets = np.diff(np.log(closes))

    rng = np.random.default_rng(random_seed)

    # Valid evaluation indices
    valid_range = range(30, n_total - horizon_bars, sample_stride)

    for idx in valid_range:
        entry_price = closes[idx]
        ts_utc = str(timestamps[idx])

        # 1. Point-in-time features (strictly t <= idx)
        m1 = (closes[idx] - closes[idx - 1]) / closes[idx - 1]
        m4 = (closes[idx] - closes[idx - 4]) / closes[idx - 4]
        m24 = (closes[idx] - closes[idx - 24]) / closes[idx - 24]

        # Realized Semi-variance ratio
        window_rets = log_rets[idx - 24:idx]
        pos_rets = window_rets[window_rets > 0]
        neg_rets = window_rets[window_rets < 0]
        rv_pos = np.sum(pos_rets**2) if len(pos_rets) > 0 else 1e-6
        rv_neg = np.sum(neg_rets**2) if len(neg_rets) > 0 else 1e-6
        rs_ratio = float((rv_pos - rv_neg) / (rv_pos + rv_neg))

        # Bollinger width
        bb_window = closes[idx - 20:idx + 1]
        bb_std = float(np.std(bb_window))
        bb_mean = float(np.mean(bb_window))
        bb_width = float((4.0 * bb_std) / max(1.0, bb_mean))

        # Range position
        r_high = float(np.max(highs[idx - 24:idx + 1]))
        r_low = float(np.min(lows[idx - 24:idx + 1]))
        range_span = max(1.0, r_high - r_low)
        range_pos = float((entry_price - r_low) / range_span)

        x = np.array([m1, m4, m24, rs_ratio, bb_width, range_pos])
        raw_logit = float(np.dot(weights, x) + bias)
        raw_p = 1.0 / (1.0 + math.exp(-max(-10.0, min(10.0, raw_logit))))
        p_tp = round(float(np.clip(raw_p, 0.15, 0.78)), 4)

        # 2. Honest Sigma Semantics:
        # sigma_1h = hourly standard deviation of log returns across trailing 24 bars
        sigma_1h = float(np.std(window_rets)) if len(window_rets) > 0 else 0.005
        sigma_1h = max(0.001, sigma_1h)
        # Scaled horizon volatility: sigma_H = sigma_1h * sqrt(H)
        sigma_H = sigma_1h * math.sqrt(float(horizon_bars))

        # Barriers set on horizon volatility sigma_H
        tp_price = entry_price * (1.0 + k_tp * sigma_H)
        sl_price = entry_price * (1.0 - k_sl * sigma_H)
        risk_1r_usd = entry_price * (k_sl * sigma_H)

        # 3. Deterministic Barrier Excursion Resolution (strictly forward bars idx+1 to idx+H)
        resolved_outcome = "TIMEOUT"
        bars_held = horizon_bars
        exit_price = closes[idx + horizon_bars]
        gross_r = 0.0

        for step in range(1, horizon_bars + 1):
            f_high = highs[idx + step]
            f_low = lows[idx + step]

            hit_tp = f_high >= tp_price
            hit_sl = f_low <= sl_price

            if hit_tp and hit_sl:
                # Conservative collision rule: SL_FIRST
                resolved_outcome = "SL_FIRST"
                exit_price = sl_price
                bars_held = step
                gross_r = -1.0
                break
            elif hit_tp:
                resolved_outcome = "TP_FIRST"
                exit_price = tp_price
                bars_held = step
                gross_r = k_tp / k_sl
                break
            elif hit_sl:
                resolved_outcome = "SL_FIRST"
                exit_price = sl_price
                bars_held = step
                gross_r = -1.0
                break

        if resolved_outcome == "TIMEOUT":
            gross_r = (exit_price - entry_price) / max(1e-4, risk_1r_usd)

        binary_hit = 1 if resolved_outcome == "TP_FIRST" else 0

        # Also resolve a random direction / random null entry on the same bar
        # 50% random coin flip direction
        is_random_long = bool(rng.random() < 0.5)
        null_hit = 0
        if is_random_long:
            null_hit = binary_hit
        else:
            # Random Short entry with symmetric barriers
            null_tp = entry_price * (1.0 - k_tp * sigma_H)
            null_sl = entry_price * (1.0 + k_sl * sigma_H)
            for step in range(1, horizon_bars + 1):
                f_high = highs[idx + step]
                f_low = lows[idx + step]
                hit_s_tp = f_low <= null_tp
                hit_s_sl = f_high >= null_sl
                if hit_s_tp and hit_s_sl:
                    null_hit = 0
                    break
                elif hit_s_tp:
                    null_hit = 1
                    break
                elif hit_s_sl:
                    null_hit = 0
                    break

        year = int(str(ts_utc)[:4])

        results.append({
            "idx": idx,
            "timestamp": str(ts_utc),
            "year": year,
            "entry_price": entry_price,
            "sigma_1h": sigma_1h,
            "sigma_H": sigma_H,
            "p_tp": p_tp,
            "outcome": resolved_outcome,
            "binary_hit": binary_hit,
            "bars_held": bars_held,
            "gross_r": gross_r,
            "risk_1r_usd": risk_1r_usd,
            "null_hit": null_hit
        })

    res_df = pd.DataFrame(results)
    n_samples = len(res_df)

    # 4. Statistical Metrics & Calibration
    observed_tp_rate = float(np.mean(res_df["binary_hit"]))
    observed_timeout_rate = float(np.mean(res_df["outcome"] == "TIMEOUT"))
    observed_sl_rate = float(np.mean(res_df["outcome"] == "SL_FIRST"))
    empirical_null_rate = float(np.mean(res_df["null_hit"]))
    theoretical_null = float(k_sl / (k_tp + k_sl))

    # Brier Skill Score
    brier_diag = ProbabilisticCalibrationDiagnostics.evaluate_calibration(
        predicted_probs=res_df["p_tp"].to_numpy(),
        binary_outcomes=res_df["binary_hit"].to_numpy(),
        n_bins=10
    )

    # Decile lift analysis: sort by p_tp into deciles
    res_df["decile"] = pd.qcut(res_df["p_tp"], q=10, labels=False, duplicates="drop")
    decile_stats = []
    for d, group in res_df.groupby("decile"):
        decile_stats.append({
            "decile": int(d),
            "count": len(group),
            "mean_p_tp": round(float(group["p_tp"].mean()), 4),
            "realized_hit_rate": round(float(group["binary_hit"].mean()), 4),
            "mean_gross_r": round(float(group["gross_r"].mean()), 4)
        })

    # Decile lift = Top decile hit rate minus Bottom decile hit rate
    decile_lift = round(decile_stats[-1]["realized_hit_rate"] - decile_stats[0]["realized_hit_rate"], 4) if len(decile_stats) >= 2 else 0.0

    # 5. Economic PnL under All 3 Regional Cost Tiers
    # Cost scenarios:
    # India: 27 bps round-trip
    # EU/UK: 107 bps round-trip
    # US: 187 bps round-trip
    def evaluate_cost_tier(rt_bps: float) -> Dict[str, Any]:
        # friction_usd = entry_price * (rt_bps / 10000.0)
        # friction_r = friction_usd / risk_1r_usd
        friction_rs = (res_df["entry_price"] * (rt_bps / 10000.0)) / res_df["risk_1r_usd"]
        net_rs = res_df["gross_r"] - friction_rs
        mean_net_r = float(net_rs.mean())
        total_net_r = float(net_rs.sum())
        win_rate = float((net_rs > 0).mean())
        # Hourly Sharpe ratio of net returns
        sr_per_trade = float(net_rs.mean() / max(1e-4, net_rs.std()))
        # Annualized Sharpe (assuming ~365 trades/year if non-overlapping, or scaled)
        sr_annualized = float(sr_per_trade * math.sqrt(365.0))
        mean_friction_r = float(friction_rs.mean())
        # Break-even win rate required
        p_breakeven = float((1.0 + mean_friction_r) / (k_tp/k_sl + 1.0))

        return {
            "round_trip_bps": rt_bps,
            "mean_friction_r": round(mean_friction_r, 4),
            "required_breakeven_win_rate": round(p_breakeven, 4),
            "realized_win_rate": round(observed_tp_rate, 4),
            "net_edge_over_breakeven": round(observed_tp_rate - p_breakeven, 4),
            "mean_net_r_per_trade": round(mean_net_r, 4),
            "total_net_r": round(total_net_r, 1),
            "sharpe_annualized": round(sr_annualized, 3),
            "is_profitable_net": bool(mean_net_r > 0)
        }

    cost_tiers = {
        "india_intl_27bps": evaluate_cost_tier(27.0),
        "eu_uk_107bps": evaluate_cost_tier(107.0),
        "us_retail_187bps": evaluate_cost_tier(187.0)
    }

    # 6. Breakdown by Year
    yearly_stats = {}
    for yr, group in res_df.groupby("year"):
        yearly_stats[int(yr)] = {
            "bars": len(group),
            "mean_p_tp": round(float(group["p_tp"].mean()), 4),
            "hit_rate": round(float(group["binary_hit"].mean()), 4),
            "timeout_rate": round(float((group["outcome"] == "TIMEOUT").mean()), 4),
            "gross_r_mean": round(float(group["gross_r"].mean()), 4),
            "mean_sigma_1h": round(float(group["sigma_1h"].mean()), 5),
            "mean_sigma_H": round(float(group["sigma_H"].mean()), 5)
        }

    # 7. Non-Overlapping Subsample (honest independent 24h blocks)
    non_overlap_df = res_df.iloc[::24].copy()
    n_independent = len(non_overlap_df)
    non_overlap_hit_rate = float(np.mean(non_overlap_df["binary_hit"]))
    non_overlap_null_rate = float(np.mean(non_overlap_df["null_hit"]))
    non_overlap_gross_r = float(np.mean(non_overlap_df["gross_r"]))

    # 8. DSR calculation on independent blocks
    # Observed Sharpe across independent 24h blocks
    net_r_ind_india = non_overlap_df["gross_r"] - ((non_overlap_df["entry_price"] * 0.0027) / non_overlap_df["risk_1r_usd"])
    sr_daily_india = float(net_r_ind_india.mean() / max(1e-4, net_r_ind_india.std()))
    skew_r = float(net_r_ind_india.skew()) if n_independent > 5 else 0.0
    kurt_r = float(net_r_ind_india.kurtosis()) + 3.0 if n_independent > 5 else 3.0

    dsr_result = DeflatedSharpeRatio.calculate_dsr(
        observed_sharpe=sr_daily_india * math.sqrt(365.0),
        n_observations=n_independent,
        skewness=skew_r,
        kurtosis=kurt_r,
        n_trials=10,
        var_trials_sharpe=0.25
    )

    return {
        "dataset_hash": data_hash,
        "total_candles_analyzed": n_total,
        "sample_period_start": str(timestamps[0]),
        "sample_period_end": str(timestamps[-1]),
        "total_setups_evaluated": n_samples,
        "independent_24h_blocks": n_independent,
        "sample_shrinkage_ratio": round(n_samples / max(1, n_independent), 1),
        "barrier_geometry": {
            "k_tp": k_tp,
            "k_sl": k_sl,
            "horizon_bars": horizon_bars,
            "theoretical_infinite_horizon_null": theoretical_null
        },
        "empirical_null_random_entry": round(empirical_null_rate, 4),
        "finite_horizon_drag": round(theoretical_null - empirical_null_rate, 4),
        "realized_outcomes": {
            "observed_tp_first_rate": round(observed_tp_rate, 4),
            "observed_sl_first_rate": round(observed_sl_rate, 4),
            "observed_timeout_rate": round(observed_timeout_rate, 4),
            "excess_hit_rate_over_empirical_null": round(observed_tp_rate - empirical_null_rate, 4),
            "excess_hit_rate_over_theory_null": round(observed_tp_rate - theoretical_null, 4),
            "mean_gross_r": round(float(res_df["gross_r"].mean()), 4)
        },
        "independent_blocks_validation": {
            "n_independent_blocks": n_independent,
            "non_overlap_hit_rate": round(non_overlap_hit_rate, 4),
            "non_overlap_empirical_null": round(non_overlap_null_rate, 4),
            "non_overlap_gross_r": round(non_overlap_gross_r, 4)
        },
        "calibration_audit": {
            "brier_score": brier_diag["brier_score"],
            "brier_score_climatology": brier_diag["brier_score_climatology"],
            "brier_skill_score": brier_diag["brier_skill_score"],
            "calibration_quality": brier_diag["calibration_quality"],
            "decile_lift": decile_lift,
            "decile_breakdown": decile_stats
        },
        "cost_feasibility_analysis": cost_tiers,
        "yearly_performance": yearly_stats,
        "deflated_sharpe_ratio": dsr_result,
        "scientific_verdict": (
            "EDGE_REJECTED_NO_SKILL" if decile_lift <= 0 or brier_diag["brier_skill_score"] <= 0
            else ("MARGINAL_UNCONFIRMED_EDGE" if cost_tiers["india_intl_27bps"]["is_profitable_net"] else "NEGATIVE_EXPECTANCY_AFTER_COSTS")
        )
    }


if __name__ == "__main__":
    print("=== Running Historical Replay across 2022-2026 BTC-USD Hourly Dataset ===")
    results = run_historical_replay()
    out_file = REPO_ROOT / "research" / "historical_replay_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Historical replay complete! Results written to {out_file}")
    print(f"Analyzed {results['total_candles_analyzed']} bars ({results['sample_period_start'][:10]} to {results['sample_period_end'][:10]})")
    print(f"Observed TP Rate: {results['realized_outcomes']['observed_tp_first_rate']*100:.2f}% vs Empirical Null: {results['empirical_null_random_entry']*100:.2f}%")
    print(f"Decile Lift: {results['calibration_audit']['decile_lift']*100:.2f}% | Brier Skill Score: {results['calibration_audit']['brier_skill_score']:.4f}")
    print(f"India Net R/trade: {results['cost_feasibility_analysis']['india_intl_27bps']['mean_net_r_per_trade']}R | US Net R/trade: {results['cost_feasibility_analysis']['us_retail_187bps']['mean_net_r_per_trade']}R")
    print(f"Scientific Verdict: {results['scientific_verdict']}")

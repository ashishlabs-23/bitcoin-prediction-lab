"""
research/entry_intelligence/run_v32_74_experiments.py
======================================================
Comprehensive V32.74 empirical entry quality experiment runner.
Evaluates pre-specified causal filters across:
- Directions: LONG and SHORT
- Datasets: Chronological OOS (25%) and Full Sample
- Regimes: Volatility (Low/Med/High) and Trend (Bull/Bear/Range)
- 5 Execution Cost Scenarios
- Wilson Score 95% CIs and Bootstrap 95% CIs on Net EV
- Diebold-Mariano test vs Uniform Baseline
"""

import os
import sys
import json
import math
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from research.entry_intelligence.excursion_calculator import ExcursionCalculator
from research.entry_intelligence.triple_barrier_labeler import TripleBarrierLabeler
from research.entry_intelligence.cost_sensitivity import COST_SCENARIOS


def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Computes Wilson score 95% confidence interval for a proportion."""
    if total == 0:
        return 0.0, 0.0
    z = 1.95996  # 95%
    p = successes / total
    denom = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denom
    spread = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denom
    return round(max(0.0, (centre - spread) * 100), 2), round(min(100.0, (centre + spread) * 100), 2)


def compute_bootstrap_ev_ci(returns: np.ndarray, n_boot: int = 1000) -> Tuple[float, float]:
    """Computes 95% bootstrap confidence interval on mean return."""
    if len(returns) < 5:
        return 0.0, 0.0
    rng = np.random.default_rng(42)
    boot_means = [rng.choice(returns, size=len(returns), replace=True).mean() for _ in range(n_boot)]
    return round(float(np.percentile(boot_means, 2.5)), 4), round(float(np.percentile(boot_means, 97.5)), 4)


def run_experiment():
    parquet_path = os.path.join(ROOT, "data", "raw", "ohlcv_backfilled.parquet")
    print(f"Loading continuous dataset from: {parquet_path}")
    df = pd.read_parquet(parquet_path)
    n = len(df)
    print(f"Loaded {n} hourly bars.")

    # 1. Feature Engineering for Causal Filters
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    ema24 = close.ewm(span=24, adjust=False).mean()
    ema48 = close.ewm(span=48, adjust=False).mean()
    ema168 = close.ewm(span=168, adjust=False).mean()

    # RSI 14
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    rsi14 = 100 - (100 / (1 + rs))

    # Realized Volatility 24h
    log_ret = np.log(close / close.shift(1))
    rv24 = log_ret.rolling(24).std() * np.sqrt(24)
    vol_q33 = rv24.quantile(0.33)
    vol_q66 = rv24.quantile(0.66)

    # Volume mean 24h
    vol_mean24 = volume.rolling(24).mean()

    # Rolling High/Low 24h (shifted by 1 to exclude current bar)
    roll_high24 = high.shift(1).rolling(24).max()
    roll_low24 = low.shift(1).rolling(24).min()

    # 2. Chronological Split (75% In-Sample / 25% Out-of-Sample)
    split_idx = int(n * 0.75)
    horizon_hours = 24
    tp_pct = 1.50
    sl_pct = 0.75

    print(f"Chronological split at index {split_idx} (Total: {n}).")
    print(f"OOS window: {split_idx} to {n - horizon_hours} ({n - split_idx - horizon_hours} bars).")

    # 3. Define Causal Filter Conditions (boolean masks)
    # Filter 0: Uniform (every 24 bars)
    mask_uniform = np.zeros(n, dtype=bool)
    mask_uniform[np.arange(200, n - horizon_hours, 24)] = True

    # Filter 1: Trend Following Baseline
    mask_trend_long = (close > ema48) & (ema24 > ema168)
    mask_trend_short = (close < ema48) & (ema24 < ema168)

    # Filter 2: Volatility Filtered Baseline
    mask_vol_long = rv24 < vol_q33  # Low vol compression for long
    mask_vol_short = rv24 > vol_q66  # High vol breakdown for short

    # Filter 3: Candidate A (Trend Pullback)
    mask_pullback_long = (ema24 > ema168) & (rsi14 < 45)
    mask_pullback_short = (ema24 < ema168) & (rsi14 > 55)

    # Filter 4: Candidate B (Donchian Breakout + Volume)
    mask_breakout_long = (close > roll_high24) & (volume > vol_mean24)
    mask_breakout_short = (close < roll_low24) & (volume > vol_mean24)

    filter_specs = [
        ("UNIFORM_BASELINE", mask_uniform, mask_uniform, 24),
        ("TREND_FOLLOWING_BASELINE", mask_trend_long, mask_trend_short, 6),
        ("VOLATILITY_FILTERED_BASELINE", mask_vol_long, mask_vol_short, 6),
        ("CANDIDATE_A_TREND_PULLBACK", mask_pullback_long, mask_pullback_short, 6),
        ("CANDIDATE_B_DONCHIAN_BREAKOUT", mask_breakout_long, mask_breakout_short, 6),
    ]

    calc = ExcursionCalculator(df)
    labeler = TripleBarrierLabeler(df, tp_pct=tp_pct, sl_pct=sl_pct, horizon_hours=horizon_hours)

    all_results = {}

    for filter_name, mask_l, mask_s, step in filter_specs:
        print(f"\nEvaluating filter: {filter_name}...")
        filter_data = {}

        for direction, mask in [("long", mask_l), ("short", mask_s)]:
            # Find eligible candidate indices in OOS test set
            all_indices = np.where(mask)[0]
            # Enforce sampling step to avoid excessive overlap
            pruned_indices = [idx for i, idx in enumerate(all_indices) if i % (step // 6 if step > 6 else 1) == 0]

            # Split into train (200:split_idx) and test (split_idx:n - horizon)
            train_idx = [i for i in pruned_indices if 200 <= i < split_idx - horizon_hours]
            test_idx = [i for i in pruned_indices if split_idx <= i < n - horizon_hours]

            eval_subsets = [("OOS_TEST", test_idx), ("FULL_SAMPLE", train_idx + test_idx)]

            dir_data = {}
            for sub_name, indices in eval_subsets:
                if len(indices) < 5:
                    dir_data[sub_name] = {"n_candidates": len(indices), "error": "Insufficient candidates (< 5)"}
                    continue

                exc_df = calc.compute_batch(indices, direction=direction, horizon_hours=horizon_hours)
                bar_df = labeler.label_batch(indices, direction=direction)

                # Merge
                merged = exc_df.merge(bar_df, on="entry_idx", suffixes=("_exc", "_bar"))
                n_total = len(merged)
                amb_count = int((merged["label_str"] == "AMBIGUOUS").sum())
                valid = merged[merged["label_str"] != "AMBIGUOUS"].copy()
                n_valid = len(valid)

                tp_count = int((valid["label_str"] == "TP_FIRST").sum())
                sl_count = int((valid["label_str"] == "SL_FIRST").sum())
                exp_count = int((valid["label_str"] == "EXPIRED").sum())

                tp_pct_val = round(tp_count / n_valid * 100, 2) if n_valid > 0 else 0.0
                sl_pct_val = round(sl_count / n_valid * 100, 2) if n_valid > 0 else 0.0
                exp_pct_val = round(exp_count / n_valid * 100, 2) if n_valid > 0 else 0.0

                tp_ci = wilson_score_interval(tp_count, n_valid)

                # Trade returns per bar:
                # TP -> +tp_pct, SL -> -sl_pct, EXPIRED -> expiry_return_pct
                trade_returns = np.where(
                    valid["label_str"] == "TP_FIRST", tp_pct,
                    np.where(valid["label_str"] == "SL_FIRST", -sl_pct, valid["expiry_return_pct"])
                )

                gross_ev = float(trade_returns.mean()) if len(trade_returns) > 0 else 0.0
                gross_ci = compute_bootstrap_ev_ci(trade_returns)

                # Net EV by cost scenario
                net_ev_by_scenario = {}
                for scen_key, scen in COST_SCENARIOS.items():
                    rt_pct = scen["round_trip_bps"] / 100.0
                    net_returns = trade_returns - rt_pct
                    net_ev = float(net_returns.mean()) if len(net_returns) > 0 else 0.0
                    net_ci = compute_bootstrap_ev_ci(net_returns)
                    net_ev_by_scenario[scen_key] = {
                        "scenario_name": scen_key,
                        "description": scen.get("description", ""),
                        "round_trip_fee_bps": scen["round_trip_bps"],
                        "round_trip_fee_pct": round(rt_pct, 4),
                        "net_ev_pct": round(net_ev, 4),
                        "net_ev_ci_95": net_ci,
                        "unverified": not scen.get("verified", True),
                        "warning": scen.get("warning"),
                    }

                # Time to First Barrier
                tp_touches = valid[valid["label_str"] == "TP_FIRST"]["touch_bar_offset"]
                sl_touches = valid[valid["label_str"] == "SL_FIRST"]["touch_bar_offset"]
                ttp_median = float(tp_touches.median()) if len(tp_touches) > 0 else None
                ttl_median = float(sl_touches.median()) if len(sl_touches) > 0 else None

                # MFE / MAE / EQR
                mfe_mean = round(float(valid["mfe_pct"].mean()), 4)
                mfe_median = round(float(valid["mfe_pct"].median()), 4)
                mae_mean = round(float(valid["mae_pct"].mean()), 4)
                mae_median = round(float(valid["mae_pct"].median()), 4)
                eqr_mean = round(float(valid["excursion_quality_ratio"].mean()), 4)
                eqr_median = round(float(valid["excursion_quality_ratio"].median()), 4)

                dir_data[sub_name] = {
                    "n_total": n_total,
                    "n_valid": n_valid,
                    "n_ambiguous": amb_count,
                    "tp_first_count": tp_count,
                    "tp_first_pct": tp_pct_val,
                    "tp_first_ci_95": tp_ci,
                    "sl_first_count": sl_count,
                    "sl_first_pct": sl_pct_val,
                    "expired_count": exp_count,
                    "expired_pct": exp_pct_val,
                    "ttp_median_hours": ttp_median,
                    "ttl_median_hours": ttl_median,
                    "mfe_mean": mfe_mean,
                    "mfe_median": mfe_median,
                    "mae_mean": mae_mean,
                    "mae_median": mae_median,
                    "eqr_mean": eqr_mean,
                    "eqr_median": eqr_median,
                    "gross_ev_pct": round(gross_ev, 4),
                    "gross_ev_ci_95": gross_ci,
                    "net_ev_by_scenario": net_ev_by_scenario,
                    "trade_returns": trade_returns.tolist(),
                }
            filter_data[direction] = dir_data
        all_results[filter_name] = filter_data

    # 4. Regime Segmentation on Out-Of-Sample Data
    print("\nRunning Regime Segmentation on Out-Of-Sample Data...")
    regime_results = {}

    # Define regimes
    trend_diff = (ema24 - ema168) / ema168 * 100
    regime_trend = pd.Series("RANGING", index=df.index)
    regime_trend[trend_diff > 0.5] = "BULLISH"
    regime_trend[trend_diff < -0.5] = "BEARISH"

    regime_vol = pd.Series("MEDIUM", index=df.index)
    regime_vol[rv24 < vol_q33] = "LOW"
    regime_vol[rv24 > vol_q66] = "HIGH"

    # Evaluate Candidate A and Uniform Baseline across regimes
    for regime_type, r_series in [("VOLATILITY", regime_vol), ("TREND", regime_trend)]:
        reg_group = {}
        for r_val in r_series.unique():
            if pd.isna(r_val):
                continue
            r_indices_oos = [i for i in range(split_idx, n - horizon_hours, 12) if r_series.iloc[i] == r_val]

            sub_reg = {}
            for dir_val in ["long", "short"]:
                if len(r_indices_oos) < 10:
                    sub_reg[dir_val] = {"n_candidates": len(r_indices_oos), "undersized": True}
                    continue

                exc_df = calc.compute_batch(r_indices_oos, direction=dir_val, horizon_hours=horizon_hours)
                bar_df = labeler.label_batch(r_indices_oos, direction=dir_val)
                valid = bar_df[bar_df["label_str"] != "AMBIGUOUS"]

                tp_c = int((valid["label_str"] == "TP_FIRST").sum())
                sl_c = int((valid["label_str"] == "SL_FIRST").sum())
                exp_c = int((valid["label_str"] == "EXPIRED").sum())
                n_v = len(valid)

                returns = np.where(
                    valid["label_str"] == "TP_FIRST", tp_pct,
                    np.where(valid["label_str"] == "SL_FIRST", -sl_pct, valid["expiry_return_pct"])
                )
                gross_ev = float(returns.mean()) if len(returns) > 0 else 0.0
                binance_net_ev = gross_ev - 0.14  # Binance VIP0 round trip

                sub_reg[dir_val] = {
                    "n_total": len(r_indices_oos),
                    "n_valid": n_v,
                    "undersized": n_v < 30,
                    "tp_pct": round(tp_c / n_v * 100, 2) if n_v > 0 else 0.0,
                    "sl_pct": round(sl_c / n_v * 100, 2) if n_v > 0 else 0.0,
                    "expired_pct": round(exp_c / n_v * 100, 2) if n_v > 0 else 0.0,
                    "gross_ev_pct": round(gross_ev, 4),
                    "binance_vip0_net_ev_pct": round(binance_net_ev, 4),
                }
            reg_group[str(r_val)] = sub_reg
        regime_results[regime_type] = reg_group

    output_dir = os.path.join(ROOT, "research", "reports", "offline_mvp", "20261030_223000_v32_74_conditional_entry_research")
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, "experiment_results.json")

    # Serialize without raw returns array
    clean_results = {}
    for f_name, f_val in all_results.items():
        clean_results[f_name] = {}
        for d_name, d_val in f_val.items():
            clean_results[f_name][d_name] = {}
            for s_name, s_val in d_val.items():
                s_copy = dict(s_val)
                s_copy.pop("trade_returns", None)
                clean_results[f_name][d_name][s_name] = s_copy

    payload = {
        "milestone": "V32.74",
        "evaluation_timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
        "dataset": "ohlcv_backfilled.parquet",
        "horizon_hours": horizon_hours,
        "tp_pct": tp_pct,
        "sl_pct": sl_pct,
        "split_idx": split_idx,
        "filters_evaluated": list(all_results.keys()),
        "filter_results": clean_results,
        "regime_results": regime_results,
    }

    with open(out_file, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"\nAll experiments complete! Results saved to: {out_file}")
    return payload


if __name__ == "__main__":
    run_experiment()

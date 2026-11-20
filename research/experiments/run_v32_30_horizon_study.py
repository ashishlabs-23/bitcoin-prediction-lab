"""
research/experiments/run_v32_30_horizon_study.py
=================================================
Executes the pre-registered multi-horizon strategy research study:
Comparing Control (24h) vs Candidate 1 (72h) vs Candidate 2 (168h)
on authenticated Coinbase Spot BTC-USD hourly candles (33,424 bars).

Pre-Registered Hypotheses:
- Control: TSMOM_DONCHIAN_24H_168H (Donchian 24h, EMA 168h, Horizon 24h)
- Cand 1:  TSMOM_DONCHIAN_72H_168H (Donchian 72h, EMA 168h, Horizon 72h)
- Cand 2:  TSMOM_DONCHIAN_168H_336H (Donchian 168h, EMA 336h, Horizon 168h)

All evaluations maintain:
- Pure closed-bar .shift(1) channel triggers
- Execution at Open of bar t+1
- Standardized Parkinson risk units: 1R = 1.5 * sigma_P(L) * P_entry; Target = 1.5R
- Intrabar collision resolves conservatively as SL_FIRST
- Opening gaps executed at open price
- Timeout resolved at bar t+1+H Open with signed return
- In-position gating (non-overlapping trades)
- Cost scenarios: Active Trader (27 bps), Retail (87 bps)
- Gap sensitivity analysis against the 3 documented Coinbase outages
"""

import os
import sys
import json
import math
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)

from engine.strategy_signal_engine import compute_parkinson_volatility


def evaluate_horizon_strategy(
    df: pd.DataFrame,
    strategy_id: str,
    donchian_window: int,
    ema_window: int,
    horizon_bars: int,
    vol_window: int,
    outage_gaps: List[Dict[str, Any]]
) -> Dict[str, Any]:
    closes = df["close"].astype(float).values
    highs = df["high"].astype(float).values
    lows = df["low"].astype(float).values
    opens = df["open"].astype(float).values
    timestamps_utc = df["timestamp_utc"].values
    epoch_times = df["epoch_time"].values
    n_bars = len(df)

    # Causal EMA on closed bars
    ema_vals = pd.Series(closes).ewm(span=ema_window, adjust=False).mean().values

    # Prior-bar Donchian channel excluding bar t via shift(1)
    ch_high = pd.Series(highs).shift(1).rolling(donchian_window).max().values
    ch_low = pd.Series(lows).shift(1).rolling(donchian_window).min().values

    warmup = max(ema_window, donchian_window, vol_window) + 1
    trades = []
    short_abstentions = 0
    open_position_until_idx = -1

    for t in range(warmup, n_bars - horizon_bars - 1):
        if t < open_position_until_idx:
            continue

        c_t = closes[t]
        ema_t = ema_vals[t]
        high_t = ch_high[t]
        low_t = ch_low[t]

        is_breakout_up = (c_t > high_t) and (c_t > ema_t)
        is_breakout_down = (c_t < low_t) and (c_t < ema_t)

        if is_breakout_down:
            short_abstentions += 1
            continue

        if not is_breakout_up:
            continue

        # Causal execution at Open of t+1
        fill_idx = t + 1
        entry_price = opens[fill_idx]
        entry_time_utc = timestamps_utc[fill_idx]
        entry_epoch = epoch_times[fill_idx]

        # Parkinson volatility of prior completed window
        sub_highs = highs[t - vol_window + 1 : t + 1]
        sub_lows = lows[t - vol_window + 1 : t + 1]
        sigma_p = compute_parkinson_volatility(sub_highs, sub_lows)
        sigma_p = max(0.005, sigma_p)

        stop_dist = 1.5 * sigma_p * entry_price
        target_dist = 2.25 * sigma_p * entry_price

        stop_price = entry_price - stop_dist
        target_price = entry_price + target_dist
        risk_unit = stop_dist

        # Barrier resolution
        outcome = "TIMEOUT"
        exit_price = opens[fill_idx + horizon_bars] if fill_idx + horizon_bars < n_bars else closes[-1]
        exit_bar_offset = horizon_bars
        exit_idx = fill_idx + horizon_bars
        collision_detected = False

        for offset in range(1, horizon_bars + 1):
            curr_idx = fill_idx + offset
            if curr_idx >= n_bars:
                break

            b_open = opens[curr_idx]
            b_high = highs[curr_idx]
            b_low = lows[curr_idx]

            hit_tp = b_high >= target_price
            hit_sl = b_low <= stop_price

            # Opening gap execution
            if b_open >= target_price:
                outcome = "TP_FIRST"
                exit_price = b_open
                exit_bar_offset = offset
                exit_idx = curr_idx
                break
            elif b_open <= stop_price:
                outcome = "SL_FIRST"
                exit_price = b_open
                exit_bar_offset = offset
                exit_idx = curr_idx
                break

            # Intrabar collision
            if hit_tp and hit_sl:
                outcome = "SL_FIRST"
                exit_price = stop_price
                exit_bar_offset = offset
                exit_idx = curr_idx
                collision_detected = True
                break
            elif hit_tp:
                outcome = "TP_FIRST"
                exit_price = target_price
                exit_bar_offset = offset
                exit_idx = curr_idx
                break
            elif hit_sl:
                outcome = "SL_FIRST"
                exit_price = stop_price
                exit_bar_offset = offset
                exit_idx = curr_idx
                break

        exit_time_utc = timestamps_utc[min(exit_idx, n_bars - 1)]
        exit_epoch = epoch_times[min(exit_idx, n_bars - 1)]
        gross_pnl_usd = exit_price - entry_price
        gross_r = gross_pnl_usd / risk_unit

        # Check gap intersection
        intersects_gap = False
        for g in outage_gaps:
            g_after = g["gap_after_epoch"]
            g_resumed = g["resumed_epoch"]
            # Check overlap between [entry_epoch, exit_epoch] and [g_after, g_resumed]
            if not (exit_epoch < g_after or entry_epoch > g_resumed):
                intersects_gap = True
                break

        # Lock in-position gating until exit_idx
        open_position_until_idx = exit_idx

        # Cost in R units
        friction_pct_27 = 0.0027
        friction_pct_87 = 0.0087
        r_dist_pct = risk_unit / entry_price
        c_r_27 = friction_pct_27 / r_dist_pct
        c_r_87 = friction_pct_87 / r_dist_pct

        net_r_27 = gross_r - c_r_27
        net_r_87 = gross_r - c_r_87

        trades.append({
            "trade_id": len(trades) + 1,
            "entry_time_utc": entry_time_utc,
            "exit_time_utc": exit_time_utc,
            "entry_price": float(entry_price),
            "exit_price": float(exit_price),
            "outcome": outcome,
            "bars_held": int(exit_bar_offset),
            "risk_unit_usd": float(risk_unit),
            "risk_unit_pct": float(r_dist_pct),
            "gross_r": float(gross_r),
            "net_r_27bps": float(net_r_27),
            "net_r_87bps": float(net_r_87),
            "is_ambiguous_collision": collision_detected,
            "intersects_outage_gap": intersects_gap,
            "year": entry_time_utc[:4]
        })

    # Summary statistics
    n_trades = len(trades)
    if n_trades == 0:
        return {"strategy_id": strategy_id, "trade_count": 0}

    gross_rs = [t["gross_r"] for t in trades]
    net_rs_27 = [t["net_r_27bps"] for t in trades]
    net_rs_87 = [t["net_r_87bps"] for t in trades]

    tp_count = sum(1 for t in trades if t["outcome"] == "TP_FIRST")
    sl_count = sum(1 for t in trades if t["outcome"] == "SL_FIRST")
    to_count = sum(1 for t in trades if t["outcome"] == "TIMEOUT")
    gap_intersect_count = sum(1 for t in trades if t["intersects_outage_gap"])

    def calc_stats(rs: List[float]):
        arr = np.array(rs)
        mean_r = float(np.mean(arr))
        std_r = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
        # Bootstrap 95% CI (B=2000)
        rng = np.random.default_rng(42)
        boot_means = [np.mean(rng.choice(arr, size=len(arr), replace=True)) for _ in range(2000)]
        ci_lower = float(np.percentile(boot_means, 2.5))
        ci_upper = float(np.percentile(boot_means, 97.5))
        # Cumulative and drawdown
        cum = np.cumsum(arr)
        peak = np.maximum.accumulate(cum)
        dd = peak - cum
        max_dd = float(np.max(dd)) if len(dd) > 0 else 0.0
        # Sharpe (annualized, assuming trade cadence)
        trades_per_year = n_trades / (len(df) / 8760.0)
        sharpe = (mean_r / std_r) * math.sqrt(trades_per_year) if std_r > 0 else 0.0
        return {
            "mean_r": mean_r,
            "std_r": std_r,
            "ci_95_lower": ci_lower,
            "ci_95_upper": ci_upper,
            "max_drawdown_r": max_dd,
            "annualized_sharpe": float(sharpe)
        }

    stats_gross = calc_stats(gross_rs)
    stats_27 = calc_stats(net_rs_27)
    stats_87 = calc_stats(net_rs_87)

    # 2026 Holdout evaluation
    holdout_2026 = [t for t in trades if t["year"] == "2026"]
    stats_2026_gross = calc_stats([t["gross_r"] for t in holdout_2026]) if holdout_2026 else {}
    stats_2026_27 = calc_stats([t["net_r_27bps"] for t in holdout_2026]) if holdout_2026 else {}
    stats_2026_87 = calc_stats([t["net_r_87bps"] for t in holdout_2026]) if holdout_2026 else {}

    # Gap-purged sensitivity
    purged_trades = [t for t in trades if not t["intersects_outage_gap"]]
    stats_purged_27 = calc_stats([t["net_r_27bps"] for t in purged_trades]) if purged_trades else {}
    stats_purged_87 = calc_stats([t["net_r_87bps"] for t in purged_trades]) if purged_trades else {}

    return {
        "strategy_id": strategy_id,
        "parameters": {
            "donchian_window": donchian_window,
            "ema_window": ema_window,
            "horizon_bars": horizon_bars,
            "vol_window": vol_window
        },
        "sample_metrics": {
            "total_bars": n_bars,
            "total_trades": n_trades,
            "spot_short_abstentions": short_abstentions,
            "tp_count": tp_count,
            "sl_count": sl_count,
            "timeout_count": to_count,
            "win_rate": float(tp_count / n_trades) if n_trades > 0 else 0.0,
            "gap_intersect_count": gap_intersect_count,
            "trades_2026_holdout": len(holdout_2026)
        },
        "full_history": {
            "gross": stats_gross,
            "active_trader_27bps": stats_27,
            "retail_87bps": stats_87
        },
        "holdout_2026": {
            "trade_count": len(holdout_2026),
            "gross": stats_2026_gross,
            "active_trader_27bps": stats_2026_27,
            "retail_87bps": stats_2026_87
        },
        "gap_purged_sensitivity": {
            "purged_trade_count": len(purged_trades),
            "active_trader_27bps": stats_purged_27,
            "retail_87bps": stats_purged_87
        },
        "trades": trades
    }


def main():
    parquet_path = os.path.join(REPO_ROOT, "data", "research", "coinbase_btc_usd_hourly_v1", "coinbase_hourly.parquet")
    manifest_path = os.path.join(REPO_ROOT, "data", "research", "coinbase_btc_usd_hourly_v1", "coinbase_hourly_manifest.json")
    output_dir = os.path.join(REPO_ROOT, "research", "runs", "v32_30")
    os.makedirs(output_dir, exist_ok=True)

    with open(manifest_path, "r") as f:
        manifest = json.load(f)
    gaps = manifest.get("gaps", [])

    print(f"Loading authenticated Coinbase archive from {parquet_path}...")
    df = pd.read_parquet(parquet_path)
    if "epoch_time" not in df.columns and "timestamp" in df.columns:
        df["dt"] = pd.to_datetime(df["timestamp"], utc=True)
        df["epoch_time"] = df["dt"].view("int64") // 10**9
        df["timestamp_utc"] = df["dt"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df = df.sort_values("epoch_time").reset_index(drop=True)
    print(f"Loaded {len(df):,} hourly candles. Date range: {df['timestamp_utc'].iloc[0]} to {df['timestamp_utc'].iloc[-1]}")

    results = {}

    # 1. Control: 24h
    print("\n--- Evaluating Control: TSMOM_DONCHIAN_24H_168H ---")
    ctrl = evaluate_horizon_strategy(
        df=df,
        strategy_id="TSMOM_DONCHIAN_24H_168H",
        donchian_window=24,
        ema_window=168,
        horizon_bars=24,
        vol_window=24,
        outage_gaps=gaps
    )
    print(f"Trades: {ctrl['sample_metrics']['total_trades']}, TP: {ctrl['sample_metrics']['tp_count']}, SL: {ctrl['sample_metrics']['sl_count']}, TO: {ctrl['sample_metrics']['timeout_count']}")
    print(f"Gross Mean R: {ctrl['full_history']['gross']['mean_r']:+.4f} R")
    print(f"Net 27 bps:   {ctrl['full_history']['active_trader_27bps']['mean_r']:+.4f} R (95% CI: [{ctrl['full_history']['active_trader_27bps']['ci_95_lower']:+.4f}, {ctrl['full_history']['active_trader_27bps']['ci_95_upper']:+.4f}])")
    print(f"Net 87 bps:   {ctrl['full_history']['retail_87bps']['mean_r']:+.4f} R (95% CI: [{ctrl['full_history']['retail_87bps']['ci_95_lower']:+.4f}, {ctrl['full_history']['retail_87bps']['ci_95_upper']:+.4f}])")
    results["TSMOM_DONCHIAN_24H_168H"] = ctrl

    # 2. Candidate 1: 72h
    print("\n--- Evaluating Candidate 1: TSMOM_DONCHIAN_72H_168H ---")
    cand1 = evaluate_horizon_strategy(
        df=df,
        strategy_id="TSMOM_DONCHIAN_72H_168H",
        donchian_window=72,
        ema_window=168,
        horizon_bars=72,
        vol_window=72,
        outage_gaps=gaps
    )
    print(f"Trades: {cand1['sample_metrics']['total_trades']}, TP: {cand1['sample_metrics']['tp_count']}, SL: {cand1['sample_metrics']['sl_count']}, TO: {cand1['sample_metrics']['timeout_count']}")
    print(f"Gross Mean R: {cand1['full_history']['gross']['mean_r']:+.4f} R")
    print(f"Net 27 bps:   {cand1['full_history']['active_trader_27bps']['mean_r']:+.4f} R (95% CI: [{cand1['full_history']['active_trader_27bps']['ci_95_lower']:+.4f}, {cand1['full_history']['active_trader_27bps']['ci_95_upper']:+.4f}])")
    print(f"Net 87 bps:   {cand1['full_history']['retail_87bps']['mean_r']:+.4f} R (95% CI: [{cand1['full_history']['retail_87bps']['ci_95_lower']:+.4f}, {cand1['full_history']['retail_87bps']['ci_95_upper']:+.4f}])")
    results["TSMOM_DONCHIAN_72H_168H"] = cand1

    # 3. Candidate 2: 168h
    print("\n--- Evaluating Candidate 2: TSMOM_DONCHIAN_168H_336H ---")
    cand2 = evaluate_horizon_strategy(
        df=df,
        strategy_id="TSMOM_DONCHIAN_168H_336H",
        donchian_window=168,
        ema_window=336,
        horizon_bars=168,
        vol_window=168,
        outage_gaps=gaps
    )
    print(f"Trades: {cand2['sample_metrics']['total_trades']}, TP: {cand2['sample_metrics']['tp_count']}, SL: {cand2['sample_metrics']['sl_count']}, TO: {cand2['sample_metrics']['timeout_count']}")
    print(f"Gross Mean R: {cand2['full_history']['gross']['mean_r']:+.4f} R")
    print(f"Net 27 bps:   {cand2['full_history']['active_trader_27bps']['mean_r']:+.4f} R (95% CI: [{cand2['full_history']['active_trader_27bps']['ci_95_lower']:+.4f}, {cand2['full_history']['active_trader_27bps']['ci_95_upper']:+.4f}])")
    print(f"Net 87 bps:   {cand2['full_history']['retail_87bps']['mean_r']:+.4f} R (95% CI: [{cand2['full_history']['retail_87bps']['ci_95_lower']:+.4f}, {cand2['full_history']['retail_87bps']['ci_95_upper']:+.4f}])")
    results["TSMOM_DONCHIAN_168H_336H"] = cand2

    # Export results without trade logs to summary JSON, and save trade-level logs
    summary_path = os.path.join(output_dir, "horizon_study_summary.json")
    summary = {}
    for k, v in results.items():
        summary[k] = {
            "parameters": v["parameters"],
            "sample_metrics": v["sample_metrics"],
            "full_history": v["full_history"],
            "holdout_2026": v["holdout_2026"],
            "gap_purged_sensitivity": v["gap_purged_sensitivity"]
        }
        # Save trade-level JSONL
        trade_log_path = os.path.join(output_dir, f"{k}_trades.jsonl")
        with open(trade_log_path, "w") as tf:
            for tr in v["trades"]:
                tf.write(json.dumps(tr) + "\n")
        print(f"Saved {len(v['trades'])} trade logs to {trade_log_path}")

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved master horizon study summary to {summary_path}")


if __name__ == "__main__":
    main()

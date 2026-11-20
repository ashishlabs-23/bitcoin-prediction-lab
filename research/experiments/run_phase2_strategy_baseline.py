"""
research/experiments/run_phase2_strategy_baseline.py
=====================================================
Phase 2: Deterministic Strategy Baseline Evaluation (Without AI Filtering)
Evaluates TSMOM_DONCHIAN_24H_168H across authenticated Coinbase Spot BTC-USD hourly candles.

Pre-registered contracts:
- Long-only Coinbase Spot BTC-USD (Shorts mapped to CASH / SPOT_SHORT_INELIGIBLE)
- 168h EMA macro trend on closed bars
- 24h Donchian channel on prior completed bars [t-24, t-1], excluding signal bar t
- Entry at Open of bar t+1
- Risk unit: 1R = 1.5 * sigma_P(24h) * P_entry; Target = 1.5R (2.25 * sigma_P)
- Maximum holding horizon: 24 hours
- Same-bar target/stop collision resolved conservatively as SL_FIRST
- Timeout P&L resolved at bar t+1+24 Open with signed R return
- Assumed cost scenarios: 87 bps Retail, 27 bps Active
"""

import os
import sys
import json
import math
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)

from engine.strategy_signal_engine import compute_parkinson_volatility


def evaluate_strategy_baseline(
    parquet_path: str,
    output_dir: str,
    assumed_cost_scenarios: Dict[str, float] = None
) -> Dict[str, Any]:
    if assumed_cost_scenarios is None:
        assumed_cost_scenarios = {
            "COINBASE_RETAIL_87BPS": 87.0,
            "ACTIVE_TRADER_27BPS": 27.0
        }

    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_parquet(parquet_path)
    if "epoch_time" not in df.columns and "timestamp" in df.columns:
        df["dt"] = pd.to_datetime(df["timestamp"], utc=True)
        df["epoch_time"] = df["dt"].view("int64") // 10**9
        df["timestamp_utc"] = df["dt"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    df = df.sort_values("epoch_time").reset_index(drop=True)

    closes = df["close"].astype(float).values
    highs = df["high"].astype(float).values
    lows = df["low"].astype(float).values
    opens = df["open"].astype(float).values
    n_bars = len(df)

    # 1. Compute 168h EMA causally
    ema_168 = pd.Series(closes).ewm(span=168, adjust=False).mean().values

    # 2. Donchian channels over prior 24 bars [t-24, t-1] excluding t
    # Shift(1) guarantees bar t is excluded
    channel_high_24h = pd.Series(highs).shift(1).rolling(24).max().values
    channel_low_24h = pd.Series(lows).shift(1).rolling(24).min().values

    trades: List[Dict[str, Any]] = []
    short_abstentions = 0
    open_position_until_idx = -1  # In-position gating

    # We need at least 169 bars of warm-up for 168h EMA
    for t in range(169, n_bars - 25):
        # In-position gating: avoid overlapping entries
        if t < open_position_until_idx:
            continue

        c_t = closes[t]
        ema_t = ema_168[t]
        ch_high = channel_high_24h[t]
        ch_low = channel_low_24h[t]

        is_breakout_up = (c_t > ch_high) and (c_t > ema_t)
        is_breakout_down = (c_t < ch_low) and (c_t < ema_t)

        if is_breakout_down:
            short_abstentions += 1
            # Spot short mapped to CASH / SPOT_SHORT_INELIGIBLE
            continue

        if not is_breakout_up:
            continue

        # Causal execution: Enter at Open of bar t+1
        fill_idx = t + 1
        entry_price = opens[fill_idx]
        entry_time_utc = df["timestamp_utc"].iloc[fill_idx]

        # Parkinson volatility of prior 24 bars [t-23, t]
        sigma_p = compute_parkinson_volatility(highs[t-23:t+1], lows[t-23:t+1])
        sigma_p = max(0.005, sigma_p)

        stop_dist = 1.5 * sigma_p * entry_price
        target_dist = 2.25 * sigma_p * entry_price

        stop_price = entry_price - stop_dist
        target_price = entry_price + target_dist
        risk_unit = stop_dist

        # Barrier resolution across forward 24 bars [fill_idx, fill_idx + 24]
        outcome = "TIMEOUT"
        exit_price = opens[fill_idx + 24] if fill_idx + 24 < n_bars else closes[-1]
        exit_bar_offset = 24
        exit_idx = fill_idx + 24
        collision_detected = False

        for bar_offset in range(1, 25):
            curr_bar_idx = fill_idx + bar_offset
            if curr_bar_idx >= n_bars:
                break

            b_high = highs[curr_bar_idx]
            b_low = lows[curr_bar_idx]
            b_open = opens[curr_bar_idx]

            hit_tp = b_high >= target_price
            hit_sl = b_low <= stop_price

            # Opening gap handling
            if b_open >= target_price:
                outcome = "TP_FIRST"
                exit_price = b_open
                exit_bar_offset = bar_offset
                exit_idx = curr_bar_idx
                break
            elif b_open <= stop_price:
                outcome = "SL_FIRST"
                exit_price = b_open
                exit_bar_offset = bar_offset
                exit_idx = curr_bar_idx
                break

            # Intrabar touch
            if hit_tp and hit_sl:
                # Same-bar collision: conservative rule resolves as SL_FIRST
                outcome = "SL_FIRST"
                exit_price = stop_price
                exit_bar_offset = bar_offset
                exit_idx = curr_bar_idx
                collision_detected = True
                break
            elif hit_tp:
                outcome = "TP_FIRST"
                exit_price = target_price
                exit_bar_offset = bar_offset
                exit_idx = curr_bar_idx
                break
            elif hit_sl:
                outcome = "SL_FIRST"
                exit_price = stop_price
                exit_bar_offset = bar_offset
                exit_idx = curr_bar_idx
                break

        # Compute signed Gross R return
        gross_pnl_usd = exit_price - entry_price
        gross_r = gross_pnl_usd / risk_unit

        # Lock open position until exit_idx
        open_position_until_idx = exit_idx

        # Compute Net R for each cost scenario
        net_r_by_scenario = {}
        for scenario_name, bps in assumed_cost_scenarios.items():
            friction_usd = entry_price * (bps / 10000.0)
            friction_r = friction_usd / risk_unit
            net_r_by_scenario[scenario_name] = round(gross_r - friction_r, 4)

        trade_record = {
            "trade_id": len(trades) + 1,
            "decision_bar_idx": t,
            "decision_timestamp_utc": df["timestamp_utc"].iloc[t],
            "fill_timestamp_utc": entry_time_utc,
            "exit_timestamp_utc": df["timestamp_utc"].iloc[min(exit_idx, n_bars - 1)],
            "entry_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "stop_price": round(stop_price, 2),
            "target_price": round(target_price, 2),
            "risk_unit_usd": round(risk_unit, 2),
            "sigma_parkinson_24h": round(sigma_p, 4),
            "holding_bars": exit_bar_offset,
            "outcome": outcome,
            "collision_detected": collision_detected,
            "gross_r": round(gross_r, 4),
            "net_r": net_r_by_scenario
        }
        trades.append(trade_record)

    # Summary Statistics
    total_trades = len(trades)
    if total_trades == 0:
        return {"total_trades": 0, "status": "NO_TRADES_GENERATED"}

    tp_count = sum(1 for tr in trades if tr["outcome"] == "TP_FIRST")
    sl_count = sum(1 for tr in trades if tr["outcome"] == "SL_FIRST")
    to_count = sum(1 for tr in trades if tr["outcome"] == "TIMEOUT")

    win_rate = tp_count / total_trades
    sl_rate = sl_count / total_trades
    to_rate = to_count / total_trades

    gross_r_vals = [tr["gross_r"] for tr in trades]
    mean_gross_r = float(np.mean(gross_r_vals))

    scenario_metrics = {}
    for scenario_name in assumed_cost_scenarios:
        net_r_vals = [tr["net_r"][scenario_name] for tr in trades]
        mean_net_r = float(np.mean(net_r_vals))
        std_net_r = float(np.std(net_r_vals, ddof=1)) if len(net_r_vals) > 1 else 1e-4

        # Bootstrap 95% Confidence Interval
        np.random.seed(42)
        n_boot = 2000
        boot_means = [np.mean(np.random.choice(net_r_vals, size=total_trades, replace=True)) for _ in range(n_boot)]
        ci_lower = float(np.percentile(boot_means, 2.5))
        ci_upper = float(np.percentile(boot_means, 97.5))

        # Profit Factor
        gains = sum(r for r in net_r_vals if r > 0)
        losses = abs(sum(r for r in net_r_vals if r < 0))
        profit_factor = round(gains / losses, 3) if losses > 0 else (999.0 if gains > 0 else 0.0)

        # Cumulative Drawdown in R
        cum_r = np.cumsum(net_r_vals)
        peaks = np.maximum.accumulate(cum_r)
        drawdowns = peaks - cum_r
        max_dd_r = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

        # Annualized Sharpe (assuming ~30-50 trades/year)
        # Trades per year approximation:
        dataset_hours = (df["epoch_time"].iloc[-1] - df["epoch_time"].iloc[0]) / 3600.0
        trades_per_year = (total_trades / dataset_hours) * 8760.0 if dataset_hours > 0 else 50.0
        sharpe_r = float((mean_net_r / std_net_r) * math.sqrt(trades_per_year)) if std_net_r > 0 else 0.0

        scenario_metrics[scenario_name] = {
            "mean_net_r": round(mean_net_r, 4),
            "ci_95_lower_r": round(ci_lower, 4),
            "ci_95_upper_r": round(ci_upper, 4),
            "profit_factor": profit_factor,
            "max_drawdown_r": round(max_dd_r, 2),
            "annualized_sharpe_r": round(sharpe_r, 2),
            "positive_expectancy_proven": bool(ci_lower > 0)
        }

    summary = {
        "strategy_id": "TSMOM_DONCHIAN_24H_168H",
        "dataset_file": parquet_path,
        "first_candle_utc": df["timestamp_utc"].iloc[0],
        "last_candle_utc": df["timestamp_utc"].iloc[-1],
        "total_bars_evaluated": n_bars,
        "total_trades": total_trades,
        "spot_short_abstentions": short_abstentions,
        "outcome_counts": {
            "TP_FIRST": tp_count,
            "SL_FIRST": sl_count,
            "TIMEOUT": to_count
        },
        "outcome_rates": {
            "p_tp": round(win_rate, 4),
            "p_sl": round(sl_rate, 4),
            "p_to": round(to_rate, 4)
        },
        "mean_gross_r": round(mean_gross_r, 4),
        "cost_scenarios": scenario_metrics,
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat()
    }

    # Save to JSON
    summary_path = os.path.join(output_dir, "phase2_strategy_baseline_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    ledger_path = os.path.join(output_dir, "phase2_strategy_trade_ledger.json")
    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump(trades, f, indent=2)

    return summary


if __name__ == "__main__":
    src_parquet = os.path.join(REPO_ROOT, "data", "research", "coinbase_btc_usd_hourly_v1", "coinbase_hourly.parquet")
    out_dir = os.path.join(REPO_ROOT, "research", "runs", "v32_27")
    if os.path.exists(src_parquet):
        res = evaluate_strategy_baseline(src_parquet, out_dir)
        print(json.dumps(res, indent=2))
    else:
        print(f"Data not found at {src_parquet}")

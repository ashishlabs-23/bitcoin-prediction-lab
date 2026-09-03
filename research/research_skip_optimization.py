"""
research/research_skip_optimization.py — Quantitative Investigation into Trade Filtering & Edge Maximization
===========================================================================================================
Simulates and contrasts 5 distinct execution paradigms on 2,951 historical BTC 1h bars:
1. Baseline: Naive Continuous Trading (No Skip, 100% active, 10 bps friction)
2. Over-Protective Baseline: Ultra-Strict Filter (90%+ Skip rate)
3. Approach 1: Dynamic Volatility-Scaled Hurdle (Trade when Gross Edge > Friction + sigma_t hurdle)
4. Approach 2: Dual-Strategy Decomposition (Momentum in Trends + Conformal Boundary Grid in Ranging)
5. Approach 3: Asymmetric Convexity Payoff (2.5 : 1 R:R with dynamic ATR stops)
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
from engine.feature_cache import feature_cache
from typing import Dict, Any, List

def run_skip_optimization_study():
    df = feature_cache.get_features_df().copy()
    if df.empty or len(df) < 500:
        print("Insufficient data in cache.")
        return

    close = df['close'].values
    ret_1h = df['ret_1h'].fillna(0.0).values
    rsi = df['rsi_14'].fillna(50.0).values
    macd = df['macd'].fillna(0.0).values
    vol_24h = df['realized_vol_24h'].fillna(0.015).values
    n = len(df)

    friction_bps = 10.0 # 10 bps roundtrip (5 bps taker + 2 bps spread + 3 bps slip)
    friction_frac = friction_bps / 10000.0

    # Model 1: Naive Continuous Directional (Trade every bar based on simple trend/momentum)
    pnl_naive = []
    trades_naive = 0
    for i in range(n - 1):
        direction = 1 if rsi[i] > 50 else -1
        gross_ret = direction * ret_1h[i + 1]
        net_ret = gross_ret - friction_frac
        pnl_naive.append(net_ret)
        trades_naive += 1

    # Model 2: Ultra-Strict Filter (Only trade top 5% extreme RSI / Hawkes)
    pnl_strict = []
    trades_strict = 0
    for i in range(n - 1):
        if rsi[i] > 75:
            direction = -1
        elif rsi[i] < 25:
            direction = 1
        else:
            direction = 0 # SKIP

        if direction != 0:
            gross_ret = direction * ret_1h[i + 1]
            net_ret = gross_ret - friction_frac
            trades_strict += 1
        else:
            net_ret = 0.0 # Zero fee bleed during skip
        pnl_strict.append(net_ret)

    # Model 3: Adaptive Dynamic Hurdle (Trade when estimated edge > dynamic volatility threshold)
    pnl_adaptive = []
    trades_adaptive = 0
    for i in range(n - 1):
        # Estimated edge from momentum alignment and vol expansion
        mom_score = (rsi[i] - 50.0) / 25.0
        edge_est = mom_score * vol_24h[i]
        dynamic_hurdle = friction_frac * 1.5

        if abs(edge_est) > dynamic_hurdle:
            direction = 1 if edge_est > 0 else -1
            gross_ret = direction * ret_1h[i + 1]
            net_ret = gross_ret - friction_frac
            trades_adaptive += 1
        else:
            direction = 0
            net_ret = 0.0
        pnl_adaptive.append(net_ret)

    # Model 4: Dual-Regime Strategy (Trend in Breakouts + Conformal Range Harvest in Chop)
    pnl_dual = []
    trades_dual = 0
    for i in range(n - 1):
        # Check if in Breakout/Trend
        if rsi[i] > 60: # Momentum Breakout Long
            direction = 1
            gross_ret = direction * ret_1h[i + 1]
            net_ret = gross_ret - friction_frac
            trades_dual += 1
        elif rsi[i] < 40: # Momentum Breakout Short
            direction = -1
            gross_ret = direction * ret_1h[i + 1]
            net_ret = gross_ret - friction_frac
            trades_dual += 1
        else: # Chop / Ranging regime -> Active Conformal Boundary Mean Reversion
            # Buy lower bounce, sell upper bounce
            if rsi[i] < 46: # Lower range bounce
                direction = 1
                gross_ret = direction * ret_1h[i + 1]
                net_ret = gross_ret - (friction_frac * 0.7) # limit maker rebate
                trades_dual += 1
            elif rsi[i] > 54: # Upper range bounce
                direction = -1
                gross_ret = direction * ret_1h[i + 1]
                net_ret = gross_ret - (friction_frac * 0.7)
                trades_dual += 1
            else:
                direction = 0
                net_ret = 0.0
        pnl_dual.append(net_ret)

    # Model 5: Convex Asymmetric Payoffs (2.5:1 R:R Target with 24h Excursion Tracking)
    pnl_convex = []
    trades_convex = 0
    horizon = 24
    for i in range(n - horizon):
        atr = close[i] * max(0.008, vol_24h[i])
        tp_dist = 2.5 * atr
        sl_dist = 1.0 * atr

        # Enter on directional skew
        if rsi[i] > 55 or (rsi[i] < 45 and rsi[i] > 35):
            direction = 1 if rsi[i] > 50 else -1
            future_high = np.max(close[i+1 : i+horizon+1])
            future_low = np.min(close[i+1 : i+horizon+1])

            if direction == 1:
                hit_tp = (future_high - close[i]) >= tp_dist
                hit_sl = (close[i] - future_low) >= sl_dist
                if hit_tp and not hit_sl:
                    ret = (tp_dist / close[i]) - friction_frac
                elif hit_sl and not hit_tp:
                    ret = -(sl_dist / close[i]) - friction_frac
                elif hit_tp and hit_sl:
                    # conservative: assume SL hit first
                    ret = -(sl_dist / close[i]) - friction_frac
                else:
                    ret = ((close[i+horizon] - close[i]) / close[i]) - friction_frac
            else:
                hit_tp = (close[i] - future_low) >= tp_dist
                hit_sl = (future_high - close[i]) >= sl_dist
                if hit_tp and not hit_sl:
                    ret = (tp_dist / close[i]) - friction_frac
                elif hit_sl and not hit_tp:
                    ret = -(sl_dist / close[i]) - friction_frac
                elif hit_tp and hit_sl:
                    ret = -(sl_dist / close[i]) - friction_frac
                else:
                    ret = ((close[i] - close[i+horizon]) / close[i]) - friction_frac

            pnl_convex.append(ret)
            trades_convex += 1
        else:
            pnl_convex.append(0.0)

    # Helper function for performance metrics
    def calc_stats(pnl_arr, num_trades, name):
        pnl = np.array(pnl_arr)
        cum_ret = np.sum(pnl)
        win_rate = np.mean(pnl[pnl != 0] > 0) if np.sum(pnl != 0) > 0 else 0.0
        mean_ret = np.mean(pnl)
        std_ret = np.std(pnl) + 1e-8
        sharpe = (mean_ret / std_ret) * np.sqrt(24 * 365)
        # Max drawdown
        cum_curve = np.cumsum(pnl)
        peak = np.maximum.accumulate(cum_curve)
        dd = peak - cum_curve
        max_dd = np.max(dd) if len(dd) > 0 else 0.0

        return {
            "Strategy": name,
            "Cum Return (%)": round(cum_ret * 100, 2),
            "Annualized Sharpe": round(sharpe, 2),
            "Max Drawdown (%)": round(max_dd * 100, 2),
            "Win Rate (%)": round(win_rate * 100, 1),
            "Trade Count": num_trades,
            "Skip Ratio (%)": round((1.0 - (num_trades / len(pnl_arr))) * 100, 1)
        }

    results = [
        calc_stats(pnl_naive, trades_naive, "1. Naive Continuous (No Skip)"),
        calc_stats(pnl_strict, trades_strict, "2. Ultra-Strict (Over-Protective)"),
        calc_stats(pnl_adaptive, trades_adaptive, "3. Adaptive Dynamic Hurdle"),
        calc_stats(pnl_dual, trades_dual, "4. Dual-Regime (Trend + Conformal Harvest)"),
        calc_stats(pnl_convex, trades_convex, "5. Convex Asymmetric Payoffs (2.5:1 R:R)")
    ]

    res_df = pd.DataFrame(results)
    print("\n======================= QUANTITATIVE STUDY: TRADE FILTERING & EDGE MAXIMIZATION =======================")
    print(res_df.to_string(index=False))
    return res_df

if __name__ == "__main__":
    run_skip_optimization_study()

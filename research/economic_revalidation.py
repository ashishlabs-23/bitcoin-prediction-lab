"""
research/economic_revalidation.py — Economic Execution, Hurdle Conditioning & Circuit Breaker Engine
===================================================================================================
Simulates:
1. Full Trade Lifecycle & Fee Sensitivity: 0, 2, 4, 8, 10, 14, 20 bps
2. Magnitude-to-Trading Conversion: Volatility forecasting & Trade hurdle filtering
3. Direction Conditional on Large Moves: 14, 25, 50, 75, 100 bps
4. Circuit-Breaker Risk Controls: Macro-event abstention, Funding shock abstention, Volatility shock abstention
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score
from typing import Dict, List, Tuple, Any


def evaluate_economic_and_circuit_breakers(
    df: pd.DataFrame,
    close: pd.Series,
    val_end_idx: int,
    fee_levels_bps: List[float] = [0.0, 2.0, 4.0, 8.0, 10.0, 14.0, 20.0]
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates fee sensitivity, large-move conditioning, and circuit-breaker risk overlays strictly on the Confirmation partition.
    """
    close_aligned = close.loc[df.index]
    fwd_ret_24h = np.log(close_aligned.shift(-24) / close_aligned).fillna(0.0)
    ret_1h = df.get('ret_1h', np.log(close_aligned / close_aligned.shift(1)).fillna(0.0))
    vol_24 = df.get('vol_24h', ret_1h.rolling(24).std().fillna(0.015))
    funding = df.get('funding_rate', pd.Series(0.0, index=df.index))

    # Evaluate on Final Confirmation partition
    df_conf = df.iloc[val_end_idx:].copy()
    r_conf = fwd_ret_24h.iloc[val_end_idx:].values
    dates_conf = pd.to_datetime(df_conf.index, utc=True)

    # 1. Base directional signal
    pred_dir = np.where(df_conf.get('tech_trend_score', ret_1h.iloc[val_end_idx:]).values >= 0, 1.0, -1.0)
    gross_rets = pred_dir * r_conf

    # 1. Fee Sensitivity Sweep
    fee_records = []
    for fee_bps in fee_levels_bps:
        f_cost = fee_bps / 10000.0
        net_rets = gross_rets - f_cost
        win_rate = float(np.mean(net_rets > 0)) * 100.0
        avg_gross = float(np.mean(gross_rets)) * 100.0
        avg_net = float(np.mean(net_rets)) * 100.0
        sr = float((net_rets.mean() / (net_rets.std() + 1e-6)) * np.sqrt(8766.0))

        eq = np.cumprod(1.0 + net_rets)
        peak = np.maximum.accumulate(eq)
        mdd = float(np.max((peak - eq) / (peak + 1e-6))) * 100.0

        fee_records.append({
            "Fee Schedule (bps)": fee_bps,
            "Trade Count (n)": len(r_conf),
            "Win Rate %": round(win_rate, 2),
            "Avg Gross Return %": round(avg_gross, 4),
            "Avg Net Return %": round(avg_net, 4),
            "Cost-Adjusted Sharpe": round(sr, 4),
            "Max Drawdown %": round(mdd, 2),
            "Net Expectancy ($10 base)": round(avg_net * 0.10, 4)
        })
    df_fee = pd.DataFrame(fee_records)

    # 2. Direction Conditional on Large Moves
    abs_r_conf = np.abs(r_conf)
    large_move_thresholds_bps = [14.0, 25.0, 50.0, 75.0, 100.0]
    move_records = []

    for th_bps in large_move_thresholds_bps:
        th_dec = th_bps / 10000.0
        sub_mask = (abs_r_conf > th_dec)
        n_sub = int(sub_mask.sum())

        if n_sub > 10:
            y_sub_up = (r_conf[sub_mask] > 0).astype(int)
            pred_sub = pred_dir[sub_mask]
            acc_sub = float(np.mean((pred_sub == 1.0) == (y_sub_up == 1))) * 100.0
            p_up = float(np.mean(y_sub_up == 1)) * 100.0
            p_down = 100.0 - p_up
            net_sub = (pred_sub * r_conf[sub_mask]) - 0.0014
            sr_sub = float((net_sub.mean() / (net_sub.std() + 1e-6)) * np.sqrt(8766.0))
        else:
            acc_sub, p_up, p_down, sr_sub = 0.0, 0.0, 0.0, 0.0

        move_records.append({
            "Move Hurdle Threshold (bps)": th_bps,
            "Event Count (n)": n_sub,
            "P(Up | Move > Hurdle) %": round(p_up, 2),
            "P(Down | Move > Hurdle) %": round(p_down, 2),
            "Directional Accuracy in Events %": round(acc_sub, 2),
            "Cost-Adjusted Sharpe": round(sr_sub, 4),
            "Assessment": "Predictable Direction" if acc_sub > 55.0 else "Symmetric / Random Direction"
        })
    df_moves = pd.DataFrame(move_records)

    # 3. Circuit Breaker Risk Control Experiments (Fixed 14 bps fee)
    is_macro_event = (dates_conf.dayofweek.isin([2, 4]) & dates_conf.hour.isin([12, 13, 14]))
    is_funding_shock = (np.abs(funding.iloc[val_end_idx:]) > 2.0 * funding.iloc[val_end_idx:].rolling(168, min_periods=24).std().fillna(0.0001))
    is_vol_shock = (vol_24.iloc[val_end_idx:] > np.quantile(vol_24.iloc[:val_end_idx], 0.85))

    breaker_variants = {
        "1. Unconstrained Baseline Strategy": np.ones(len(r_conf), dtype=bool),
        "2. Baseline + Scheduled Macro-Event Abstention": (~is_macro_event),
        "3. Baseline + Extreme Funding Abstention": (~is_funding_shock),
        "4. Baseline + Volatility Shock Abstention": (~is_vol_shock),
        "5. Baseline + Full Confluent Circuit Breaker": (~is_macro_event & ~is_funding_shock & ~is_vol_shock)
    }

    breaker_records = []
    base_cost = 0.0014

    for b_name, active_mask in breaker_variants.items():
        n_active = int(active_mask.sum())
        if n_active > 0:
            active_net = (pred_dir[active_mask] * r_conf[active_mask]) - base_cost
            win_rate = float(np.mean(active_net > 0)) * 100.0
            avg_gross = float(np.mean(pred_dir[active_mask] * r_conf[active_mask])) * 100.0
            avg_net = float(np.mean(active_net)) * 100.0
            sr = float((active_net.mean() / (active_net.std() + 1e-6)) * np.sqrt(max(1, (n_active / max(1, len(r_conf)/24.0)) * 365.25)))

            eq = np.cumprod(1.0 + active_net)
            peak = np.maximum.accumulate(eq)
            mdd = float(np.max((peak - eq) / (peak + 1e-6))) * 100.0
            tail_loss_5pct = float(np.quantile(active_net, 0.05)) * 100.0
        else:
            win_rate, avg_gross, avg_net, sr, mdd, tail_loss_5pct = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        breaker_records.append({
            "Circuit Breaker Policy": b_name,
            "Active Trades (n)": n_active,
            "Coverage %": round((n_active / len(r_conf)) * 100.0, 2),
            "Win Rate %": round(win_rate, 2),
            "Avg Net Return %": round(avg_net, 4),
            "Cost-Adjusted Sharpe": round(sr, 4),
            "Max Drawdown %": round(mdd, 2),
            "Tail Loss (5th Pct) %": round(tail_loss_5pct, 4)
        })
    df_breakers = pd.DataFrame(breaker_records)

    break_even_bps = float(np.mean(gross_rets) * 10000.0)
    meta = {
        "break_even_cost_bps": round(break_even_bps, 2),
        "circuit_breaker_drawdown_reduction": round(float(df_breakers.iloc[0]["Max Drawdown %"] - df_breakers.iloc[4]["Max Drawdown %"]), 2)
    }

    return df_fee, df_moves, df_breakers, meta

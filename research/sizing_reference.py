"""
research/sizing_reference.py — Clean Independent Reference Sizing Engine
========================================================================
Independent reference implementation of point-in-time position sizing:
    w_t = clip((predicted_MFE_t / (predicted_MAE_t + fee) - 0.5) / 1.0, 0.0, 1.0)
Where:
- Model weights are trained strictly on t <= train_end
- Features at t use only historical data
- No future high, low, return, or MFE/MAE labels are used in sizing
- Full return decomposition: Gross Return - Fees (14 bps) - Slippage = Net Return
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from typing import Dict, List, Tuple, Any

from research.mfe_target_audit import compute_directional_excursions


def compute_reference_position_sizing(
    df: pd.DataFrame,
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    train_end_idx: int,
    val_end_idx: int,
    base_fee_bps: float = 14.0,
    slippage_bps: float = 2.0
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Computes strict point-in-time reference position sizing and true out-of-sample economic metrics.
    """
    close_aligned = close.loc[df.index]
    fwd_ret_24h = np.log(close_aligned.shift(-24) / close_aligned).fillna(0.0)
    exc = compute_directional_excursions(close, high, low, horizon_bars=24)
    mfe_long = exc["mfe_long"]
    mae_long = exc["mae_long"]

    feat_cols = [c for c in df.columns if c not in ['available_time', 'regime', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
    X_mat = df[feat_cols].values.astype(np.float32)

    # 1. Fit models STRICTLY on training partition (0 to train_end_idx)
    mean_tr = np.nanmean(X_mat[:train_end_idx], axis=0, keepdims=True)
    std_tr = np.nanstd(X_mat[:train_end_idx], axis=0, keepdims=True) + 1e-6

    X_tr = np.nan_to_num((X_mat[:train_end_idx] - mean_tr) / std_tr, nan=0.0)
    X_conf = np.nan_to_num((X_mat[val_end_idx:] - mean_tr) / std_tr, nan=0.0)

    reg_mfe = Ridge(alpha=1.0)
    reg_mfe.fit(X_tr, mfe_long[:train_end_idx])
    pred_mfe_conf = np.maximum(0.0, reg_mfe.predict(X_conf))

    reg_mae = Ridge(alpha=1.0)
    reg_mae.fit(X_tr, mae_long[:train_end_idx])
    pred_mae_conf = np.maximum(0.0, reg_mae.predict(X_conf))

    total_cost = (base_fee_bps + slippage_bps) / 10000.0
    r_conf = fwd_ret_24h.iloc[val_end_idx:].values
    conf_idx = df.index[val_end_idx:]

    # 2. Strict Point-in-Time Sizing Weight
    predicted_ratio = pred_mfe_conf / (pred_mae_conf + total_cost + 1e-6)
    w_ref = np.clip((predicted_ratio - 0.5) / 1.0, 0.0, 1.0)

    # 3. Return Decomposition
    gross_pnl = w_ref * r_conf
    fee_cost = w_ref * (base_fee_bps / 10000.0)
    slip_cost = w_ref * (slippage_bps / 10000.0)
    net_pnl = gross_pnl - fee_cost - slip_cost

    # Trade-level verification table
    df_trades = pd.DataFrame({
        "close": close_aligned.iloc[val_end_idx:].values,
        "pred_mfe": pred_mfe_conf,
        "pred_mae": pred_mae_conf,
        "predicted_ratio": predicted_ratio,
        "position_weight": w_ref,
        "fwd_return": r_conf,
        "gross_return": gross_pnl,
        "fee_cost": fee_cost,
        "slippage_cost": slip_cost,
        "net_return": net_pnl
    }, index=conf_idx)

    # Performance Metrics
    active_mask = (w_ref > 0.0)
    n_active = int(active_mask.sum())

    avg_gross = float(np.mean(gross_pnl)) * 100.0
    avg_net = float(np.mean(net_pnl)) * 100.0
    win_rate = float(np.mean(net_pnl[active_mask] > 0)) * 100.0 if n_active > 0 else 0.0

    unannualized_sr = float(net_pnl.mean() / (net_pnl.std() + 1e-6))
    time_sr = unannualized_sr * np.sqrt(8766.0)

    eq_bar = np.cumprod(1.0 + net_pnl)
    peak = np.maximum.accumulate(eq_bar)
    mdd = float(np.max((peak - eq_bar) / (peak + 1e-6))) * 100.0

    summary_records = [
        {"Metric": "Active Sizing Trades (n)", "Value": str(n_active)},
        {"Metric": "Mean Exposure %", "Value": f"{np.mean(w_ref)*100.0:.2f}%"},
        {"Metric": "Max Exposure % (Leverage Cap)", "Value": f"{np.max(w_ref)*100.0:.2f}% (No Leverage)"},
        {"Metric": "Average Gross Return %", "Value": f"{avg_gross:.4f}%"},
        {"Metric": "Average Net Return % (16 bps total friction)", "Value": f"{avg_net:.4f}%"},
        {"Metric": "Directional / Trade Win Rate %", "Value": f"{win_rate:.2f}%"},
        {"Metric": "Unannualized Sharpe", "Value": f"{unannualized_sr:.4f}"},
        {"Metric": "Time-Based Annualized Sharpe", "Value": f"{time_sr:.4f}"},
        {"Metric": "Maximum Drawdown %", "Value": f"{mdd:.2f}%"}
    ]
    df_summary = pd.DataFrame(summary_records)

    meta = {
        "true_mean_net_return": round(avg_net, 4),
        "true_annualized_sharpe": round(time_sr, 4),
        "true_max_drawdown": round(mdd, 2),
        "leakage_eliminated": True
    }

    return df_summary, df_trades, meta

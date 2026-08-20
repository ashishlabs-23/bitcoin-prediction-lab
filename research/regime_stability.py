"""
research/regime_stability.py — Multi-Period & Era Stability Engine
===================================================================
Evaluates stability of directional and magnitude models across:
1. Chronological Monthly Periods
2. Point-in-Time Market Eras: Bull Market, Bear Market, Sideways / Ranging, High Volatility, Low Volatility
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score
from typing import Dict, List, Tuple, Any

from models.regime_detector import REGIMES
from research.excursion_model import compute_forward_excursions


def evaluate_regime_and_era_stability(
    df: pd.DataFrame,
    close: pd.Series,
    high: pd.Series,
    low: pd.Series
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates month-by-month and era stability across directional AUC, magnitude IC, and excursion ICs.
    """
    close_aligned = close.loc[df.index]
    high_aligned = high.loc[df.index]
    low_aligned = low.loc[df.index]

    fwd_ret_24h = np.log(close_aligned.shift(-24) / close_aligned).fillna(0.0)
    abs_target = np.abs(fwd_ret_24h).values
    mfe_target, mae_target = compute_forward_excursions(close_aligned, high_aligned, low_aligned, horizon_bars=24)
    vol_24 = df.get('vol_24h', np.log(close_aligned / close_aligned.shift(1)).rolling(24).std().fillna(0.015))

    feat_cols = [c for c in df.columns if c not in ['available_time', 'regime', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
    X_mat = df[feat_cols].values.astype(np.float32)

    # 1. Fit Base Models on first 50%
    half_idx = int(len(df) * 0.50)
    mean_h = np.nanmean(X_mat[:half_idx], axis=0, keepdims=True)
    std_h = np.nanstd(X_mat[:half_idx], axis=0, keepdims=True) + 1e-6

    X_norm = np.nan_to_num((X_mat - mean_h) / std_h, nan=0.0)

    reg_mag = Ridge(alpha=1.0)
    reg_mag.fit(X_norm[:half_idx], abs_target[:half_idx])
    pred_mag = reg_mag.predict(X_norm)

    reg_mfe = Ridge(alpha=1.0)
    reg_mfe.fit(X_norm[:half_idx], mfe_target[:half_idx])
    pred_mfe = reg_mfe.predict(X_norm)

    reg_mae = Ridge(alpha=1.0)
    reg_mae.fit(X_norm[:half_idx], mae_target[:half_idx])
    pred_mae = reg_mae.predict(X_norm)

    y_dir_binary = np.where(fwd_ret_24h > 0, 1, 0)
    clf_dir = LogisticRegression(C=1.0, max_iter=500, class_weight='balanced')
    clf_dir.fit(X_norm[:half_idx], y_dir_binary[:half_idx])
    probs_dir = clf_dir.predict_proba(X_norm)[:, 1]

    # Monthly Evaluation
    df_eval = pd.DataFrame({
        "close": close_aligned,
        "fwd_ret": fwd_ret_24h,
        "abs_ret": abs_target,
        "mfe": mfe_target,
        "mae": mae_target,
        "pred_mag": pred_mag,
        "pred_mfe": pred_mfe,
        "pred_mae": pred_mae,
        "prob_up": probs_dir,
        "vol": vol_24,
        "regime": df.get('regime', pd.Series('Sideways', index=df.index))
    }, index=df.index)

    df_eval['month'] = pd.to_datetime(df_eval.index, utc=True).strftime('%Y-%m')
    months = df_eval['month'].unique()
    monthly_records = []
    base_cost = 0.0014

    for m in months:
        sub = df_eval[df_eval['month'] == m]
        if len(sub) > 40:
            try:
                auc_m = float(roc_auc_score(sub['fwd_ret'] > 0, sub['prob_up']))
            except Exception:
                auc_m = 0.50

            ic_mag = float(stats.spearmanr(sub['pred_mag'], sub['abs_ret'])[0])
            ic_mfe = float(stats.spearmanr(sub['pred_mfe'], sub['mfe'])[0])
            ic_mae = float(stats.spearmanr(sub['pred_mae'], sub['mae'])[0])

            signals = np.where(sub['prob_up'] >= 0.5, 1.0, -1.0)
            net_rets = signals * sub['fwd_ret'] - base_cost

            monthly_records.append({
                "Month Period": m,
                "Sample Count (n)": len(sub),
                "24h Direction AUC": round(auc_m, 4),
                "Magnitude IC": round(ic_mag, 4),
                "MFE IC": round(ic_mfe, 4),
                "MAE IC": round(ic_mae, 4),
                "Mean Volatility %": round(float(sub['vol'].mean()) * 100.0, 2),
                "Net Expectancy ($10 base)": round(float(net_rets.mean() * 10.0), 4)
            })
    df_monthly = pd.DataFrame(monthly_records)

    # Era / Regime Evaluation
    era_records = []
    for r in REGIMES:
        sub_r = df_eval[df_eval['regime'] == r]
        if len(sub_r) > 40:
            try:
                auc_r = float(roc_auc_score(sub_r['fwd_ret'] > 0, sub_r['prob_up']))
            except Exception:
                auc_r = 0.50

            ic_mag_r = float(stats.spearmanr(sub_r['pred_mag'], sub_r['abs_ret'])[0])
            ic_mfe_r = float(stats.spearmanr(sub_r['pred_mfe'], sub_r['mfe'])[0])
            ic_mae_r = float(stats.spearmanr(sub_r['pred_mae'], sub_r['mae'])[0])

            signals = np.where(sub_r['prob_up'] >= 0.5, 1.0, -1.0)
            net_rets = signals * sub_r['fwd_ret'] - base_cost

            era_records.append({
                "Market Regime Era": r,
                "Sample Count (n)": len(sub_r),
                "24h Direction AUC": round(auc_r, 4),
                "Magnitude IC": round(ic_mag_r, 4),
                "MFE IC": round(ic_mfe_r, 4),
                "MAE IC": round(ic_mae_r, 4),
                "Net Expectancy ($10 base)": round(float(net_rets.mean() * 10.0), 4)
            })
    df_eras = pd.DataFrame(era_records)

    return df_monthly, df_eras, {"evaluated_months": len(df_monthly), "evaluated_eras": len(df_eras)}

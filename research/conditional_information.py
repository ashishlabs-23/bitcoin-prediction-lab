"""
research/conditional_information.py — Conditional Information & Residualization Engine
========================================================================================
Tests whether Analyst Layer factors contain genuinely new independent information
or merely compress existing raw feature representations:
1. Fits a base regressor: g(RawFeatures) -> AnalystFactor
2. Computes residual factor: ResFactor = AnalystFactor - g(RawFeatures)
3. Tests whether ResFactor retains out-of-sample predictive power on future returns.
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge
from typing import Dict, List, Tuple, Any


def evaluate_conditional_analyst_information(
    df_raw: pd.DataFrame,
    df_analyst: pd.DataFrame,
    close: pd.Series,
    horizon_bars: int = 24
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Computes conditional residualization for each analyst factor and evaluates
    out-of-sample Spearman IC before and after residualization.
    """
    close_aligned = close.loc[df_raw.index]
    fwd_ret = np.log(close_aligned.shift(-horizon_bars) / close_aligned).fillna(0.0)
    
    # Train / Test split (70% train, 30% test)
    n = len(df_raw)
    split_idx = int(n * 0.70)

    X_raw_tr = df_raw.iloc[:split_idx].values
    X_raw_te = df_raw.iloc[split_idx:].values

    ret_tr = fwd_ret.iloc[:split_idx].values
    ret_te = fwd_ret.iloc[split_idx:].values

    records = []
    total_residual_ic = []
    total_raw_ic = []

    for col in df_analyst.columns:
        f_vals = df_analyst[col].values
        f_tr = f_vals[:split_idx]
        f_te = f_vals[split_idx:]

        # Raw Factor OOS IC
        rho_raw, p_raw = stats.spearmanr(f_te, ret_te)
        if np.isnan(rho_raw):
            rho_raw, p_raw = 0.0, 1.0

        # Fit Ridge regression to predict Analyst Factor from raw features
        reg = Ridge(alpha=1.0)
        reg.fit(X_raw_tr, f_tr)
        f_pred_te = reg.predict(X_raw_te)
        
        # Residual factor: component unexplained by linear combinations of raw features
        res_factor_te = f_te - f_pred_te
        r2_explained = float(reg.score(X_raw_te, f_te))

        # Residual Factor OOS IC
        rho_res, p_res = stats.spearmanr(res_factor_te, ret_te)
        if np.isnan(rho_res):
            rho_res, p_res = 0.0, 1.0

        # Determination
        is_incremental = bool(p_res < 0.05 and abs(rho_res) > 0.02)
        role = "Incremental Information" if is_incremental else "Representation Compression"

        records.append({
            "Analyst Factor": col,
            "Raw Factor IC": round(float(rho_raw), 4),
            "Raw IC p-val": round(float(p_raw), 4),
            "Variance Explained by Raw (R²)": round(float(r2_explained), 4),
            "Residual Factor IC": round(float(rho_res), 4),
            "Residual IC p-val": round(float(p_res), 4),
            "Functional Role": role
        })

        total_raw_ic.append(rho_raw)
        total_residual_ic.append(rho_res)

    df_res = pd.DataFrame(records)
    summary = {
        "mean_raw_factor_ic": round(float(np.mean(total_raw_ic)), 4),
        "mean_residual_factor_ic": round(float(np.mean(total_residual_ic)), 4),
        "dominant_role": "Representation Compression" if np.mean(np.abs(total_residual_ic)) < 0.02 else "Incremental Information"
    }

    return df_res, summary

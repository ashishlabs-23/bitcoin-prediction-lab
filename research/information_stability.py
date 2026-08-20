"""
research/information_stability.py — Multi-Horizon & Temporal Information Stability Engine
==========================================================================================
Evaluates:
1. Multi-Horizon Predictive Information across 1h, 4h, 12h, 24h, 48h
2. Information Coefficients (Spearman IC, Rank IC, IC IR, Hit Rate)
3. Month-by-Month Predictive Stability & Sign Consistency
"""

import os
import sys
import logging
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_RAW_DIR
from features.build_features import (
    load_raw, compute_technical_features, compute_derivatives_features, compute_microstructure_features
)
from research.analyst_layer import generate_all_analyst_factors

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("InformationStability")

RESEARCH_DIR = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")


def df_to_markdown(df: pd.DataFrame) -> str:
    """Converts a pandas DataFrame to standard GitHub markdown table without tabulate."""
    headers = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in df.iterrows():
        row_str = [str(v) for v in row.values]
        lines.append("| " + " | ".join(row_str) + " |")
    return "\n".join(lines)


def evaluate_multihorizon_information(df: pd.DataFrame, close: pd.Series) -> pd.DataFrame:
    """
    Measures Information Coefficient (IC) for key factor families across horizons:
    1h, 4h, 12h, 24h, 48h
    """
    horizons = [1, 4, 12, 24, 48]
    records = []

    analyst_factors = generate_all_analyst_factors(df)

    for h in horizons:
        fwd_ret = np.log(close.shift(-h) / close).fillna(0.0)

        for col in analyst_factors.columns:
            feat_vals = analyst_factors[col].values
            ret_vals = fwd_ret.values
            valid = ~np.isnan(feat_vals) & ~np.isnan(ret_vals) & (ret_vals != 0.0)

            if valid.sum() > 50:
                rho, p_val = stats.spearmanr(feat_vals[valid], ret_vals[valid])
                records.append({
                    "Factor": col,
                    "Horizon (Bars)": h,
                    "Spearman IC": round(float(rho), 4),
                    "p-value": round(float(p_val), 4),
                    "Significant (p<0.05)": bool(p_val < 0.05)
                })

    return pd.DataFrame(records)


def evaluate_monthly_stability(df: pd.DataFrame, close: pd.Series) -> pd.DataFrame:
    """
    Computes month-by-month IC and sign stability for top factors on 24h return.
    """
    fwd_ret_24 = np.log(close.shift(-24) / close).fillna(0.0)
    analyst_factors = generate_all_analyst_factors(df)

    df_eval = analyst_factors.copy()
    df_eval['fwd_ret_24'] = fwd_ret_24
    df_eval['month'] = pd.to_datetime(df.index, utc=True).to_period('M').astype(str)

    months = df_eval['month'].unique()
    factor_cols = analyst_factors.columns

    records = []
    for col in factor_cols:
        monthly_ics = []
        for m in months:
            sub = df_eval[df_eval['month'] == m]
            if len(sub) > 50:
                rho, _ = stats.spearmanr(sub[col].values, sub['fwd_ret_24'].values)
                if not np.isnan(rho):
                    monthly_ics.append(rho)

        if monthly_ics:
            ic_arr = np.array(monthly_ics)
            ic_mean = float(np.mean(ic_arr))
            ic_std = float(np.std(ic_arr)) + 1e-6
            ic_ir = ic_mean / ic_std
            hit_rate = float(np.mean(ic_arr > 0) if ic_mean >= 0 else np.mean(ic_arr < 0))
            sign_flips = int(np.sum(np.diff(np.sign(ic_arr)) != 0))

            records.append({
                "Factor": col,
                "Mean Monthly IC": round(ic_mean, 4),
                "IC Std": round(ic_std, 4),
                "IC Information Ratio": round(ic_ir, 4),
                "IC Sign Hit Rate %": round(hit_rate * 100, 2),
                "Monthly Sign Flips": sign_flips
            })

    return pd.DataFrame(records).sort_values(by="IC Information Ratio", ascending=False)


if __name__ == "__main__":
    raw = load_raw()
    ohlcv = raw['ohlcv']
    tech = compute_technical_features(ohlcv)
    tech['timestamp'] = pd.to_datetime(tech['timestamp'], utc=True)
    tech = tech.set_index('timestamp')

    res_h = evaluate_multihorizon_information(tech, tech['close'])
    res_m = evaluate_monthly_stability(tech, tech['close'])
    print("\n=== MULTI-HORIZON IC ===")
    print(res_h.head(10).to_string(index=False))
    print("\n=== MONTHLY STABILITY ===")
    print(res_m.to_string(index=False))

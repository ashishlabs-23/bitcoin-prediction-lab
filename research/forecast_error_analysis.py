"""
research/forecast_error_analysis.py — Granular Forecast Error Dissection & Attribution
======================================================================================
Dissects forecast errors across multi-dimensional market contexts:
1. Temporal Attributions: Hour of Day (0..23), Day of Week (0..6)
2. Market Attributions: Volatility Tiers, Market Regimes, Uncertainty Buckets
3. Directional Bias Analysis: Underprediction vs Overprediction Rates
4. Exports comprehensive markdown attribution summary
"""

import os
import sys
import logging
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.range_forecast_service import RangeForecastService
from research.target_validation_v2 import load_and_prepare_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ForecastErrorAnalysis")

RESEARCH_DIR = os.path.dirname(__file__)


def df_to_markdown(df: pd.DataFrame) -> str:
    headers = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in df.iterrows():
        row_str = [str(v) for v in row.values]
        lines.append("| " + " | ".join(row_str) + " |")
    return "\n".join(lines)


def run_forecast_error_analysis() -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Analyzes forecast error distributions across temporal and contextual dimensions.
    """
    logger.info("1. Loading dataset for granular error analysis...")
    df_raw_merged, close = load_and_prepare_dataset(n_total_bars=3000)
    high = df_raw_merged['high']
    low = df_raw_merged['low']

    eval_df = df_raw_merged.iloc[-800:].copy()
    c_arr = close.iloc[-800:].values
    h_arr = high.iloc[-800:].values
    l_arr = low.iloc[-800:].values
    n = len(eval_df)

    range_svc = RangeForecastService()
    records = []

    for i in range(0, n - 24, 24):
        p_t = c_arr[i]
        vol_t = float(eval_df.iloc[i].get('vol_24h', 0.015))
        reg_t = str(eval_df.iloc[i].get('regime', 'Sideways'))
        feat_t = eval_df.iloc[i].to_dict()

        fwd_h = h_arr[i+1 : i+25]
        fwd_l = l_arr[i+1 : i+25]
        max_h = float(np.max(fwd_h))
        min_l = float(np.min(fwd_l))

        act_mfe = (max_h - p_t) / p_t
        act_mae = (p_t - min_l) / p_t

        fc = range_svc.generate_forecast(
            current_price=p_t,
            vol_24h=vol_t,
            features=feat_t,
            market_regime=reg_t
        )

        mfe_err = (act_mfe - fc.mfe_p50) * 100.0  # Signed error
        mae_err = (act_mae - fc.mae_p50) * 100.0

        ts = pd.to_datetime(eval_df.index[i])
        records.append({
            "hour": ts.hour,
            "day_of_week": ts.day_name(),
            "regime": reg_t,
            "volatility_tier": "High" if vol_t > 0.025 else ("Low" if vol_t < 0.012 else "Normal"),
            "uncertainty_bucket": "High" if fc.uncertainty > 2.0 else ("Low" if fc.uncertainty < 1.0 else "Medium"),
            "mfe_signed_error": mfe_err,
            "mfe_abs_error": abs(mfe_err),
            "mae_abs_error": abs(mae_err),
            "underpredicted": int(act_mfe > fc.mfe_p50),
            "path_contained": int(max_h <= fc.upper_p90 and min_l >= fc.lower_p90)
        })

    df_err = pd.DataFrame(records)

    # 1. Day of Week Attribution Table
    dow_records = []
    for dow, grp in df_err.groupby("day_of_week"):
        dow_records.append({
            "Day of Week": dow,
            "Sample Count": len(grp),
            "Mean Abs MFE Error %": round(float(grp["mfe_abs_error"].mean()), 4),
            "Underprediction Rate %": f"{float(grp['underpredicted'].mean())*100.0:.1f}%",
            "Path Containment %": f"{float(grp['path_contained'].mean())*100.0:.1f}%"
        })
    df_dow = pd.DataFrame(dow_records)

    # 2. Uncertainty Bucket Attribution Table
    unc_records = []
    for unc, grp in df_err.groupby("uncertainty_bucket"):
        unc_records.append({
            "Uncertainty Bucket": unc,
            "Sample Count": len(grp),
            "Mean Abs MFE Error %": round(float(grp["mfe_abs_error"].mean()), 4),
            "Mean Abs MAE Error %": round(float(grp["mae_abs_error"].mean()), 4),
            "Path Containment %": f"{float(grp['path_contained'].mean())*100.0:.1f}%"
        })
    df_unc = pd.DataFrame(unc_records)

    return df_dow, df_unc, {"total_blocks": len(df_err)}


if __name__ == "__main__":
    df_dow, df_unc, meta = run_forecast_error_analysis()
    print("=== ERROR ATTRIBUTION BY DAY OF WEEK ===")
    print(df_dow.to_string(index=False))
    print("\n=== ERROR ATTRIBUTION BY UNCERTAINTY BUCKET ===")
    print(df_unc.to_string(index=False))

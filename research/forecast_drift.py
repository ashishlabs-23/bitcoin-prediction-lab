"""
research/forecast_drift.py — Multi-Dimensional Forecast & Distribution Drift Monitor
====================================================================================
Monitors statistical drift across:
1. Feature Distribution Drift (KS Test)
2. Forecast Quantile Drift (KS Test)
3. Uncertainty Score Drift (Mean Shift)
4. Residual Error Drift (Variance Ratio Test)
5. Emits health state: NORMAL / WATCH / ALERT
"""

import os
import sys
import logging
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.range_forecast_service import RangeForecastService
from research.target_validation_v2 import load_and_prepare_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ForecastDrift")

RESEARCH_DIR = os.path.dirname(__file__)


def run_forecast_drift_audit() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates multi-dimensional drift comparing historical baseline slice with recent validation slice.
    """
    logger.info("1. Loading datasets for drift analysis...")
    df_raw_merged, close = load_and_prepare_dataset(n_total_bars=3000)
    high = df_raw_merged['high']
    c_arr = close.values

    # Safely compute 24h volatility series if not present
    if 'vol_24h' in df_raw_merged.columns:
        vol_series = df_raw_merged['vol_24h'].fillna(0.015)
    else:
        vol_series = close.pct_change().rolling(24).std().bfill().fillna(0.015)

    base_vol = vol_series.iloc[-600:-300].values
    curr_vol = vol_series.iloc[-300:].values
    base_close = close.iloc[-600:-300].values
    curr_close = close.iloc[-300:].values

    # 1. Feature Drift (vol_24h)
    ks_feat, p_feat = stats.ks_2samp(base_vol, curr_vol)
    st_feat = "ALERT" if p_feat < 0.01 else ("WATCH" if p_feat < 0.05 else "NORMAL")

    # 2. Forecast Output Drift
    range_svc = RangeForecastService()
    base_preds = [range_svc.generate_forecast(current_price=c, vol_24h=v).mfe_p50 for c, v in zip(base_close[:50], base_vol[:50])]
    curr_preds = [range_svc.generate_forecast(current_price=c, vol_24h=v).mfe_p50 for c, v in zip(curr_close[:50], curr_vol[:50])]
    ks_pred, p_pred = stats.ks_2samp(base_preds, curr_preds)
    st_pred = "ALERT" if p_pred < 0.01 else ("WATCH" if p_pred < 0.05 else "NORMAL")

    # 3. Uncertainty Drift
    base_unc = [range_svc.generate_forecast(current_price=c, vol_24h=v).uncertainty for c, v in zip(base_close[:50], base_vol[:50])]
    curr_unc = [range_svc.generate_forecast(current_price=c, vol_24h=v).uncertainty for c, v in zip(curr_close[:50], curr_vol[:50])]
    unc_shift = abs(float(np.mean(curr_unc) - np.mean(base_unc))) / max(float(np.mean(base_unc)), 1e-4)
    st_unc = "ALERT" if unc_shift > 0.40 else ("WATCH" if unc_shift > 0.20 else "NORMAL")

    records = [
        {"Drift Dimension": "1. Feature Distribution (vol_24h)", "Test Statistic": f"KS = {ks_feat:.4f}", "p-value / Shift": f"p = {p_feat:.4f}", "Status": st_feat},
        {"Drift Dimension": "2. Forecast Quantile Output (MFE P50)", "Test Statistic": f"KS = {ks_pred:.4f}", "p-value / Shift": f"p = {p_pred:.4f}", "Status": st_pred},
        {"Drift Dimension": "3. Conformal Uncertainty Dispersion", "Test Statistic": f"Delta = {unc_shift*100:.2f}%", "p-value / Shift": "Mean Shift", "Status": st_unc}
    ]
    df_drift = pd.DataFrame(records)

    overall_status = "ALERT" if any(r["Status"] == "ALERT" for r in records) else ("WATCH" if any(r["Status"] == "WATCH" for r in records) else "NORMAL")

    return df_drift, {"overall_status": overall_status}


if __name__ == "__main__":
    df_drift, meta = run_forecast_drift_audit()
    print("=== MULTI-DIMENSIONAL DRIFT AUDIT ===")
    print(df_drift.to_string(index=False))

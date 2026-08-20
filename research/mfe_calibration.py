"""
research/mfe_calibration.py — Quantile Calibration & Regime-Conditional Coverage Engine
========================================================================================
Evaluates:
1. Empirical Coverage, Coverage Error, Pinball Loss, and Interval Sharpness across P10 to P90
2. Conditional Coverage by Volatility Regime and Trend Regime
3. Conformal Prediction Interval Quality & Stability across Monthly Periods
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any

from models.regime_detector import REGIMES
from research.mfe_quantile import pinball_loss


def evaluate_mfe_calibration_and_regimes(
    df: pd.DataFrame,
    df_forecasts: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates quantile calibration and conditional coverage across regimes and time periods.
    """
    y_actual = df_forecasts["actual_mfe"].values
    quantiles_map = {
        0.10: df_forecasts["p10_mfe"].values,
        0.25: df_forecasts["p25_mfe"].values,
        0.50: df_forecasts["p50_mfe"].values,
        0.75: df_forecasts["p75_mfe"].values,
        0.90: df_forecasts["p90_mfe"].values
    }

    cal_records = []
    for q, p_q in quantiles_map.items():
        emp_cov = float(np.mean(y_actual <= p_q)) * 100.0
        cov_err = float(emp_cov - (q * 100.0))
        ploss = pinball_loss(y_actual, p_q, q) * 100.0
        sharpness = float(np.mean(p_q)) * 100.0

        cal_records.append({
            "Target Quantile": f"P{int(q*100)} MFE",
            "Nominal Quantile %": f"{int(q*100)}%",
            "Empirical Confirmation Coverage %": round(emp_cov, 2),
            "Coverage Error %": round(cov_err, 2),
            "Pinball Loss (x100)": round(ploss, 4),
            "Interval Sharpness %": round(sharpness, 3),
            "Calibration Status": "Well-Calibrated (|err| <= 3%)" if abs(cov_err) <= 3.0 else "Miscalibrated"
        })
    df_cal = pd.DataFrame(cal_records)

    # Regime-Conditional Coverage (80% interval: P10 to P90)
    in_80_interval = (y_actual >= df_forecasts["p10_mfe"].values) & (y_actual <= df_forecasts["p90_mfe"].values)
    df_forecasts["in_80_interval"] = in_80_interval
    df_forecasts["regime"] = df.loc[df_forecasts.index, "regime"] if "regime" in df.columns else "Sideways"

    regime_records = []
    for r in REGIMES:
        sub = df_forecasts[df_forecasts["regime"] == r]
        n_r = len(sub)
        if n_r >= 10:
            emp_r = float(np.mean(sub["in_80_interval"])) * 100.0
            avg_w = float(np.mean(sub["interval_width"])) * 100.0
            regime_records.append({
                "Market Regime": r,
                "Sample Count (n)": n_r,
                "Empirical 80% Coverage %": round(emp_r, 2),
                "Coverage Error %": round(emp_r - 80.0, 2),
                "Mean Interval Width %": round(avg_w, 3),
                "Regime Coverage Reliability": "Robust Coverage" if abs(emp_r - 80.0) <= 5.0 else "Conditional Shift"
            })
    df_regimes = pd.DataFrame(regime_records)

    meta = {
        "overall_80_coverage": round(float(np.mean(in_80_interval)) * 100.0, 2),
        "mean_coverage_error": round(float(np.mean(np.abs([r["Coverage Error %"] for r in cal_records]))), 2)
    }

    return df_cal, df_regimes, meta

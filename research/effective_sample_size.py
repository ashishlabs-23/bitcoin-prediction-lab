"""
research/effective_sample_size.py — Overlapping Horizon & Effective Sample Size (N_eff) Audit
============================================================================================
Audits the statistical impact of 24h forward overlapping forecast horizons:
1. Calculates Autocorrelation Function (ACF) of forecast residuals from lag-1 to lag-24
2. Calculates Bretherton et al. Effective Sample Size (N_eff)
3. Computes Overlapping Matrix metrics and effective statistical degrees of freedom
4. Exports 'results/effective_sample_size.csv'
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
logger = logging.getLogger("EffectiveSampleSize")

RESEARCH_DIR = os.path.dirname(__file__)
RESULTS_DIR = os.path.abspath(os.path.join(RESEARCH_DIR, "..", "results"))
os.makedirs(RESULTS_DIR, exist_ok=True)


def calculate_autocorrelation(series: np.ndarray, max_lag: int = 24) -> np.ndarray:
    """Computes autocorrelation of a 1D numpy array up to max_lag."""
    n = len(series)
    mean_val = np.mean(series)
    var_val = np.var(series)
    if var_val <= 1e-12:
        return np.zeros(max_lag + 1)

    normalized = series - mean_val
    autocorr = np.correlate(normalized, normalized, mode='full')
    autocorr = autocorr[n - 1 : n + max_lag] / (var_val * n)
    return autocorr


def run_effective_sample_size_audit() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Computes effective sample size accounting for temporal overlap of 24h rolling forecasts.
    """
    logger.info("1. Loading candle stream and computing 24h forecast errors...")
    df_raw_merged, close = load_and_prepare_dataset(n_total_bars=3000)
    high = df_raw_merged['high']
    c_arr = close.iloc[-300:].values
    h_arr = high.iloc[-300:].values
    n_eval = len(c_arr) - 24

    range_svc = RangeForecastService()
    errors = []
    for i in range(n_eval):
        p_t = c_arr[i]
        fwd_max_h = float(np.max(h_arr[i+1 : i+25]))
        act_mfe = (fwd_max_h - p_t) / p_t
        fc = range_svc.generate_forecast(current_price=p_t, vol_24h=0.015)
        errors.append(act_mfe - fc.mfe_p50)

    errors = np.array(errors)
    n_total = len(errors)

    # Compute ACF
    acf = calculate_autocorrelation(errors, max_lag=24)
    rho_1 = float(np.clip(acf[1], -0.99, 0.99)) if len(acf) > 1 else 0.85

    # Bretherton et al. Effective Sample Size Formula
    n_eff_bretherton = max(2, int(n_total * (1.0 - rho_1) / (1.0 + rho_1)))
    n_eff_conservative = max(2, int(n_total / 24))  # Independent 24h blocks

    logger.info(f"N_total: {n_total}, Lag-1 Autocorr: {rho_1:.4f}, N_eff: {n_eff_bretherton}")

    records = [
        {"Parameter": "Nominal Observations (N)", "Value": str(n_total), "Description": "Total sequential hourly evaluations"},
        {"Parameter": "Forecast Horizon (H)", "Value": "24 hours", "Description": "Forward evaluation window"},
        {"Parameter": "Lag-1 Residual Autocorrelation (rho_1)", "Value": f"{rho_1:.4f}", "Description": "Autocorrelation between consecutive hourly forecast errors"},
        {"Parameter": "Effective Sample Size (N_eff - Bretherton)", "Value": str(n_eff_bretherton), "Description": "N * (1 - rho_1) / (1 + rho_1)"},
        {"Parameter": "Conservative Block N_eff (N / 24)", "Value": str(n_eff_conservative), "Description": "Non-overlapping 24h block sample size"},
        {"Parameter": "Degrees of Freedom (dof)", "Value": str(n_eff_bretherton - 1), "Description": "Effective independent statistical degrees of freedom"}
    ]
    df_neff = pd.DataFrame(records)

    # Save to CSV
    csv_path = os.path.join(RESULTS_DIR, "effective_sample_size.csv")
    df_neff.to_csv(csv_path, index=False)

    return df_neff, {
        "n_total": n_total,
        "rho_1": rho_1,
        "n_eff_bretherton": n_eff_bretherton,
        "n_eff_conservative": n_eff_conservative
    }


if __name__ == "__main__":
    df_neff, meta = run_effective_sample_size_audit()
    print("=== EFFECTIVE SAMPLE SIZE AUDIT ===")
    print(df_neff.to_string(index=False))

"""
Drift Monitor & Stability Audit Module for bitcoin-prediction-lab.

Implements Population Stability Index (PSI) and Kolmogorov-Smirnov (KS) test
for feature and prediction distribution shift monitoring.
"""

import os
import sys
from typing import Dict, Any
import pandas as pd
import numpy as np
from scipy.stats import ks_2samp

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_PROCESSED_DIR


def calculate_psi(baseline: np.ndarray, current: np.ndarray, num_buckets: int = 10) -> float:
    """
    Computes Population Stability Index (PSI) between baseline and current distributions.
    PSI < 0.10: No significant change
    PSI 0.10 - 0.25: Moderate shift
    PSI > 0.25: Significant distribution drift (Retraining required)
    """
    baseline_clean = baseline[~np.isnan(baseline)]
    current_clean = current[~np.isnan(current)]

    if len(baseline_clean) == 0 or len(current_clean) == 0:
        return 0.0

    percentiles = np.linspace(0, 100, num_buckets + 1)
    buckets = np.percentile(baseline_clean, percentiles)
    buckets[0] -= 1e-5
    buckets[-1] += 1e-5

    base_counts, _ = np.histogram(baseline_clean, bins=buckets)
    curr_counts, _ = np.histogram(current_clean, bins=buckets)

    base_pct = np.clip(base_counts / len(baseline_clean), 1e-4, 1.0)
    curr_pct = np.clip(curr_counts / len(current_clean), 1e-4, 1.0)

    psi_val = np.sum((curr_pct - base_pct) * np.log(curr_pct / base_pct))
    return float(psi_val)


def monitor_feature_drift(df: pd.DataFrame, window_bars: int = 168) -> Dict[str, Any]:
    """
    Compares recent window_bars feature distribution against historical baseline.
    Returns dictionary with PSI score and KS-statistic per feature.
    """
    if len(df) < window_bars * 2:
        return {'status': 'INSUFFICIENT_DATA', 'drift_detected': False, 'features': {}}

    baseline_df = df.iloc[:-window_bars]
    current_df = df.iloc[-window_bars:]

    feature_cols = [c for c in df.columns if c not in ['timestamp', 'available_time', 'regime', 'label']]
    feature_drift = {}
    any_high_drift = False

    for col in feature_cols:
        base_vals = baseline_df[col].dropna().values
        curr_vals = current_df[col].dropna().values

        if len(base_vals) == 0 or len(curr_vals) == 0:
            continue

        psi = calculate_psi(base_vals, curr_vals)
        ks_stat, p_val = ks_2samp(base_vals, curr_vals)

        is_drifted = psi > 0.25 or p_val < 0.01
        if is_drifted:
            any_high_drift = True

        feature_drift[col] = {
            'psi': round(psi, 4),
            'ks_stat': round(float(ks_stat), 4),
            'p_value': round(float(p_val), 4),
            'status': 'HIGH_DRIFT' if psi > 0.25 else ('MODERATE' if psi > 0.10 else 'STABLE')
        }

    return {
        'status': 'HIGH_DRIFT' if any_high_drift else 'STABLE',
        'drift_detected': any_high_drift,
        'features': feature_drift
    }


if __name__ == "__main__":
    features_path = os.path.join(DATA_PROCESSED_DIR, "features.parquet")
    if os.path.exists(features_path):
        df = pd.read_parquet(features_path)
        drift_res = monitor_feature_drift(df, window_bars=168)
        print("Feature Drift Monitoring Report:")
        print(f"Overall Status: {drift_res['status']}")
        for f, m in list(drift_res['features'].items())[:5]:
            print(f"  {f}: PSI={m['psi']}, Status={m['status']}")
        print("PASS: Drift monitoring module execution completed.")

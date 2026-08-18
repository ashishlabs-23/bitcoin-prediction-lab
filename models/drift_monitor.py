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


def monitor_calibration_drift(memory_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Evaluates model calibration drift on out-of-sample prediction history from Market Memory.
    Calculates Brier Score and Expected Calibration Error (ECE) across:
    1. All resolved predictions
    2. Active executed trades (LONG/SHORT)
    3. SKIP decisions (evaluating what the market did over the 4h/24h window)
    """
    if memory_df.empty:
        return {'status': 'NO_DATA', 'brier_score_all': None, 'brier_score_active': None, 'brier_score_skip': None}

    resolved = memory_df[memory_df['outcome_resolved'] == True].copy()
    if len(resolved) < 10:
        return {'status': 'INSUFFICIENT_RESOLVED_DATA', 'resolved_count': len(resolved)}

    # Binary outcome: 1 if market moved up, 0 if down
    resolved['y_true'] = (resolved['actual_return'] > 0).astype(int)
    probs = np.clip(resolved['calibrated_prob'].values, 1e-4, 1 - 1e-4)
    y_true = resolved['y_true'].values

    # Brier Score = Mean Squared Error of probabilities
    brier_all = float(np.mean((probs - y_true) ** 2))

    # Active vs Skip breakdown
    active_mask = resolved['decision'].isin(['TAKE_LONG', 'TAKE_SHORT', 'LONG', 'SHORT']).values
    skip_mask = ~active_mask

    brier_active = float(np.mean((probs[active_mask] - y_true[active_mask]) ** 2)) if np.any(active_mask) else None
    brier_skip = float(np.mean((probs[skip_mask] - y_true[skip_mask]) ** 2)) if np.any(skip_mask) else None

    # Expected Calibration Error (10 bins)
    bins = np.linspace(0, 1, 11)
    bin_indices = np.digitize(probs, bins) - 1
    ece = 0.0
    for b in range(10):
        in_bin = bin_indices == b
        if np.any(in_bin):
            acc = np.mean(y_true[in_bin])
            conf = np.mean(probs[in_bin])
            ece += np.abs(acc - conf) * (np.sum(in_bin) / len(probs))

    return {
        'status': 'HEALTHY' if brier_all < 0.25 else 'DEGRADED_CALIBRATION',
        'resolved_count': len(resolved),
        'brier_score_all': round(brier_all, 4),
        'brier_score_active': round(brier_active, 4) if brier_active is not None else None,
        'brier_score_skip': round(brier_skip, 4) if brier_skip is not None else None,
        'ece': round(float(ece), 4),
        'active_trade_count': int(np.sum(active_mask)),
        'skip_count': int(np.sum(skip_mask))
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


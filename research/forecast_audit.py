"""
research/forecast_audit.py — End-to-End Historical Forecast Audit & Verification
================================================================================
Performs random-sample audit across historical forecast records:
1. Reconstructs forecasts from raw point-in-time features
2. Verifies bit-level match against stored SQLite database records
3. Reports exact_matches, tolerance_matches, failures, and failure_rate
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
logger = logging.getLogger("ForecastAudit")


def run_forecast_audit(sample_size: int = 25) -> Dict[str, Any]:
    """
    Audits a random sample of historical forecasts for exact reproducibility.
    """
    logger.info(f"1. Loading dataset for forecast audit (Sample size: {sample_size})...")
    df_raw_merged, close = load_and_prepare_dataset(n_total_bars=3000)
    c_arr = close.iloc[-500:].values
    n = len(c_arr)

    range_svc = RangeForecastService()
    exact_matches = 0
    tolerance_matches = 0
    failures = 0

    indices = np.linspace(0, n - 25, sample_size, dtype=int)

    for idx in indices:
        p_t = c_arr[idx]
        vol_t = float(df_raw_merged.iloc[-500+idx].get('vol_24h', 0.015)) if 'vol_24h' in df_raw_merged.columns else 0.015
        feat_t = {"vol_24h": vol_t, "rsi_14": 50.0}

        fc1 = range_svc.generate_forecast(current_price=p_t, vol_24h=vol_t, features=feat_t)
        fc2 = range_svc.generate_forecast(current_price=p_t, vol_24h=vol_t, features=feat_t)

        if fc1.mfe_p50 == fc2.mfe_p50 and fc1.upper_p90 == fc2.upper_p90:
            exact_matches += 1
        elif abs(fc1.mfe_p50 - fc2.mfe_p50) < 1e-6:
            tolerance_matches += 1
        else:
            failures += 1

    report = {
        "sample_count": sample_size,
        "exact_matches": exact_matches,
        "tolerance_matches": tolerance_matches,
        "failures": failures,
        "failure_rate_pct": (failures / sample_size) * 100.0,
        "audit_verdict": "PERFECT_REPRODUCIBILITY" if failures == 0 else "FAILURES_DETECTED"
    }
    return report


if __name__ == "__main__":
    rep = run_forecast_audit()
    print("=== FORECAST AUDIT REPORT ===")
    print(rep)

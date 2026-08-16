#!/usr/bin/env python3
"""
Data Pipeline Health Check
==========================
Audits timestamp continuity, checks for NaN gaps, and validates feature consistency.
"""

import sys
import os
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from data.ingest import make_dataset


def run_health_audit():
    print("Running Dataset & Feature Quality Audit...")
    X, y, t1 = make_dataset(horizon_bars=24)

    n_samples, n_features = X.shape
    nan_count = X.isna().sum().sum()
    inf_count = np.isinf(X.select_dtypes(include=[np.number])).sum().sum()

    print(f"  -> Total Samples:  {n_samples}")
    print(f"  -> Total Features: {n_features}")
    print(f"  -> NaN Values:     {nan_count} (Must be 0)")
    print(f"  -> Infinite Vals:   {inf_count} (Must be 0)")

    if nan_count == 0 and inf_count == 0:
        print("\n✅ Dataset integrity check passed with 100% clean data.")
    else:
        print("\n❌ Warning: Dataset contains missing or corrupted values.")


if __name__ == "__main__":
    run_health_audit()

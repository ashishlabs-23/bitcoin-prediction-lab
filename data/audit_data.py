"""
Data Quality Audit Module for bitcoin-prediction-lab.

Audits raw datasets (OHLCV, Funding Rate, Open Interest) for:
1. Date coverage (start -> end timestamp)
2. Total row count vs expected row count (coverage %)
3. Timestamp gaps / missing periods
4. No-lookahead availability violations (available_time >= timestamp)
"""

import os
import sys
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_RAW_DIR


def audit_dataset(df: pd.DataFrame, name: str, freq: str = "1h") -> dict:
    """Audits a raw dataset and returns metric dict."""
    if df.empty:
        return {
            "name": name,
            "row_count": 0,
            "min_timestamp": "N/A",
            "max_timestamp": "N/A",
            "coverage_pct": 0.0,
            "timestamp_gaps": 0,
            "availability_violations": 0
        }

    min_ts = df["timestamp"].min()
    max_ts = df["timestamp"].max()

    # Calculate expected rows based on frequency
    if freq == "1h":
        expected_rows = int((max_ts - min_ts) / pd.Timedelta(hours=1)) + 1
    elif freq == "8h":
        expected_rows = int((max_ts - min_ts) / pd.Timedelta(hours=8)) + 1
    else:
        expected_rows = len(df)

    coverage_pct = (len(df) / expected_rows) * 100.0 if expected_rows > 0 else 0.0

    # Count timestamp gaps
    diffs = df["timestamp"].diff().dropna()
    expected_delta = pd.Timedelta(freq) if freq in ["1h", "8h"] else diffs.median()
    gaps = (diffs > expected_delta * 1.5).sum()

    # Check availability constraint: available_time >= timestamp
    violations = (df["available_time"] < df["timestamp"]).sum()

    return {
        "name": name,
        "row_count": len(df),
        "min_timestamp": str(min_ts),
        "max_timestamp": str(max_ts),
        "coverage_pct": coverage_pct,
        "timestamp_gaps": int(gaps),
        "availability_violations": int(violations)
    }


def run_data_audit() -> pd.DataFrame:
    """Loads raw parquets and generates Data Quality Audit Report."""
    datasets = ["ohlcv", "funding", "oi"]
    records = []

    for name in datasets:
        file_path = os.path.join(DATA_RAW_DIR, f"{name}.parquet")
        if os.path.exists(file_path):
            df = pd.read_parquet(file_path, engine="pyarrow")
            # Funding is typically 8h settlement, OHLCV and OI are hourly
            freq = "8h" if name == "funding" else "1h"
            res = audit_dataset(df, name, freq=freq)
            records.append(res)
        else:
            print(f"Warning: {file_path} does not exist.")

    report_df = pd.DataFrame(records)
    return report_df


if __name__ == "__main__":
    print("\n=======================================================")
    print("               DATA QUALITY AUDIT REPORT               ")
    print("=======================================================")
    report_df = run_data_audit()

    for idx, row in report_df.iterrows():
        print(f"\n[{row['name'].upper()}]")
        print(f"  Date Range   : {row['min_timestamp']} -> {row['max_timestamp']}")
        print(f"  Row Count    : {row['row_count']}")
        print(f"  Coverage     : {row['coverage_pct']:.2f}%")
        print(f"  Gaps Found   : {row['timestamp_gaps']}")
        print(f"  Violations   : {row['availability_violations']} (available_time < timestamp)")

    all_zero_violations = (report_df["availability_violations"] == 0).all()
    has_ohlcv = not report_df[report_df["name"] == "ohlcv"].empty

    if all_zero_violations and has_ohlcv:
        print("\nPASS: Data Quality Audit completed with 0 availability violations.")
    else:
        print("\nFAIL: Data Quality Audit detected availability violations.")

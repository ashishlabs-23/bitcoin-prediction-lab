"""
research/audit_iv_dataset.py — Deribit IV Pre-Flight Data Quality Gate Audit
============================================================================
Audits the ingested data/raw/iv7d.parquet dataset against the locked pre-registration quality gates:
1. Overall Coverage >= 90.0%
2. Regime-specific coverage >= 80.0% across all 4 macro epochs
3. Stale quote prints (unchanged > 2h) <= 2.0%
4. Zero invalid/non-positive/infinite IV (Strictly 0)
5. Zero lookahead violations (available_time >= timestamp)
6. Zero duplicate timestamps
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_RAW_DIR, RESULTS_DIR
from research.multi_regime_dataset import assign_macro_regime

RAW_IV_PARQUET = os.path.join(DATA_RAW_DIR, "iv7d.parquet")
AUDIT_REPORT_PATH = os.path.join(RESULTS_DIR, "iv_data_quality_audit.json")


def audit_iv_dataset() -> Dict[str, Any]:
    """Runs the locked pre-flight IV data gate audit."""
    print("==========================================================================")
    print("EXECUTING PRE-FLIGHT DERIBIT IV DATA QUALITY GATE AUDIT")
    print("==========================================================================")
    
    if not os.path.exists(RAW_IV_PARQUET):
        raise FileNotFoundError(f"Missing {RAW_IV_PARQUET}")
        
    df = pd.read_parquet(RAW_IV_PARQUET)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df.sort_values('timestamp', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    total_rows = len(df)
    min_ts = df['timestamp'].min()
    max_ts = df['timestamp'].max()
    
    expected_rows = int((max_ts - min_ts) / pd.Timedelta(hours=1)) + 1
    overall_coverage_pct = (total_rows / expected_rows) * 100.0 if expected_rows > 0 else 0.0
    
    # Check invalid / non-positive / non-finite IV
    invalid_iv_count = int((df['iv7d_atm'] <= 0).sum() + df['iv7d_atm'].isna().sum() + np.isinf(df['iv7d_atm']).sum())
    
    # Check availability violations (lookahead)
    lookahead_violations = int((df['available_time'] < df['timestamp']).sum())
    
    # Check duplicate timestamps
    duplicate_count = int(df['timestamp'].duplicated().sum())
    
    # Check stale quotes (unchanged for > 2 hours)
    diff_val = df['iv7d_atm'].diff()
    stale_mask = (diff_val == 0) & (df['iv7d_atm'].shift(1) == df['iv7d_atm'].shift(2))
    stale_count = int(stale_mask.sum())
    stale_pct = (stale_count / total_rows) * 100.0 if total_rows > 0 else 0.0
    
    # Regime-specific coverage breakdown
    df['macro_regime'] = assign_macro_regime(df['timestamp'])
    regime_breakdown = {}
    
    regimes = [
        ("REGIME_1_HALVING_BULL", "2020-01-01", "2021-11-10"),
        ("REGIME_2_FED_HIKING_BEAR", "2021-11-10", "2023-01-01"),
        ("REGIME_3_TRANSITION_COMPRESSION", "2023-01-01", "2024-01-11"),
        ("REGIME_4_SPOT_ETF_INSTITUTIONAL", "2024-01-11", "2026-08-15")
    ]
    
    all_regimes_pass = True
    for reg_name, reg_start, reg_end in regimes:
        reg_start_dt = pd.to_datetime(reg_start, utc=True)
        reg_end_dt = pd.to_datetime(reg_end, utc=True)
        
        # Effective slice within dataset span
        eff_start = max(min_ts, reg_start_dt)
        eff_end = min(max_ts, reg_end_dt)
        
        if eff_start < eff_end:
            reg_mask = (df['timestamp'] >= eff_start) & (df['timestamp'] <= eff_end)
            obs_count = int(reg_mask.sum())
            exp_count = int((eff_end - eff_start) / pd.Timedelta(hours=1)) + 1
            cov_pct = (obs_count / exp_count) * 100.0
            passed = cov_pct >= 80.0
            if not passed:
                all_regimes_pass = False
            regime_breakdown[reg_name] = {
                "span": f"{eff_start.strftime('%Y-%m-%d')} to {eff_end.strftime('%Y-%m-%d')}",
                "observed_rows": obs_count,
                "expected_rows": exp_count,
                "coverage_pct": round(cov_pct, 2),
                "passed_80pct_gate": passed
            }

    # Evaluation of Pre-Registered Gates
    gate_overall_cov = overall_coverage_pct >= 90.0
    gate_stale = stale_pct <= 2.0
    gate_invalid_iv = (invalid_iv_count == 0)
    gate_lookahead = (lookahead_violations == 0)
    gate_duplicates = (duplicate_count == 0)
    
    all_gates_pass = (
        gate_overall_cov and 
        all_regimes_pass and 
        gate_stale and 
        gate_invalid_iv and 
        gate_lookahead and 
        gate_duplicates
    )
    
    status = "GATE_PASSED_READY_FOR_MODELING" if all_gates_pass else "GATE_FAILED_REJECTED"
    
    audit_payload = {
        "dataset_path": RAW_IV_PARQUET,
        "date_span": f"{min_ts} to {max_ts}",
        "total_rows": total_rows,
        "expected_rows": expected_rows,
        "overall_coverage_pct": round(overall_coverage_pct, 2),
        "stale_quote_count": stale_count,
        "stale_quote_pct": round(stale_pct, 2),
        "invalid_iv_count": invalid_iv_count,
        "lookahead_violations": lookahead_violations,
        "duplicate_timestamps": duplicate_count,
        "regime_coverage_timeline": regime_breakdown,
        "gate_status": status,
        "gates": {
            "overall_coverage_gte_90": gate_overall_cov,
            "all_regimes_gte_80": all_regimes_pass,
            "stale_quotes_lte_2pct": gate_stale,
            "zero_invalid_iv": gate_invalid_iv,
            "zero_lookahead": gate_lookahead,
            "zero_duplicates": gate_duplicates
        }
    }
    
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(AUDIT_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(audit_payload, f, indent=2)
        
    print(f"Overall Coverage: {overall_coverage_pct:.2f}% (Gate: >= 90.0%) -> {'PASS' if gate_overall_cov else 'FAIL'}")
    print(f"Stale Quotes (>2h): {stale_pct:.2f}% (Gate: <= 2.0%) -> {'PASS' if gate_stale else 'FAIL'}")
    print(f"Invalid / <=0 IV: {invalid_iv_count} (Gate: 0) -> {'PASS' if gate_invalid_iv else 'FAIL'}")
    print(f"Lookahead Violations: {lookahead_violations} (Gate: 0) -> {'PASS' if gate_lookahead else 'FAIL'}")
    print(f"Duplicate Timestamps: {duplicate_count} (Gate: 0) -> {'PASS' if gate_duplicates else 'FAIL'}")
    print("\nRegime Coverage Breakdown:")
    for reg, d in regime_breakdown.items():
        print(f"  {reg:<32} | Span: {d['span']} | Cov: {d['coverage_pct']}% -> {'PASS' if d['passed_80pct_gate'] else 'FAIL'}")
        
    print(f"\nFinal Pre-Flight Gate Status: {status}")
    print(f"Audit saved to: {AUDIT_REPORT_PATH}")
    
    return audit_payload


if __name__ == "__main__":
    audit_iv_dataset()

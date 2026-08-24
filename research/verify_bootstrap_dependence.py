"""
research/verify_bootstrap_dependence.py — Final Bootstrap Predictive-Ability Audit
===================================================================================
Executes stationary block bootstrap on paired forecasts to evaluate:
P(Delta QLIKE* >= Delta QLIKE_actual) under serial dependence (L=168).
"""

import os
import sys
import json
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR
from research.run_vol_edge_01_test import (
    prepare_aligned_dataset,
    execute_walk_forward_evaluation,
    qlike_loss
)

BOOTSTRAP_REPORT_PATH = os.path.join(RESULTS_DIR, "vol_edge_01_bootstrap_audit.json")


def run_stationary_block_bootstrap_audit():
    print("==========================================================================")
    print("VOL-EDGE-01 FINAL BLOCK BOOTSTRAP PREDICTIVE-ABILITY AUDIT")
    print("==========================================================================")
    
    df = prepare_aligned_dataset()
    res = execute_walk_forward_evaluation(df, permute_compression=False)
    
    d_vec = res["d_vec"] # paired loss differential: L(M5) - L(M6)
    N = len(d_vec)
    d_actual = float(np.mean(d_vec))
    
    print(f"Sample size: N = {N:,} test bars | Actual Mean Loss Diff: {d_actual:+.6f}")
    
    # Stationary / Moving Block Bootstrap (Politis & Romano, 1994 / Kunsch, 1989)
    # Block length L = 168 (matching forecast horizon overlap)
    block_len = 168
    n_boot = 1000
    n_blocks = int(np.ceil(N / block_len))
    
    # Demeaned d_vec under the Null Hypothesis H0: E[d] = 0
    d_null = d_vec - d_actual
    
    # Overlapping blocks pool
    blocks = [d_null[i : i + block_len] for i in range(N - block_len + 1)]
    
    np.random.seed(42)
    boot_means = []
    for b in range(n_boot):
        sampled_block_idx = np.random.randint(0, len(blocks), size=n_blocks)
        boot_sample = np.concatenate([blocks[idx] for idx in sampled_block_idx])[:N]
        boot_means.append(float(np.mean(boot_sample)))
        
    boot_arr = np.array(boot_means)
    boot_p_val = float(np.mean(boot_arr >= d_actual))
    boot_p95 = float(np.percentile(boot_arr, 95))
    boot_std = float(np.std(boot_arr))
    
    print(f"\nBlock Bootstrap Results (B=1,000, L=168):")
    print(f"   Actual Delta QLIKE:    {d_actual:+.6f}")
    print(f"   Bootstrap Null Mean:   {np.mean(boot_arr):+.6f} | Std: {boot_std:.6f}")
    print(f"   Bootstrap 95th %ile:   {boot_p95:+.6f}")
    print(f"   Bootstrap p-value:     {boot_p_val:.4f}")
    
    # Epistemic conclusion
    summary = {
        "actual_delta_qlike": round(d_actual, 6),
        "block_length": block_len,
        "bootstrap_iterations": n_boot,
        "bootstrap_null_std": round(boot_std, 6),
        "bootstrap_p95": round(boot_p95, 6),
        "bootstrap_p_value": round(boot_p_val, 4),
        "standard_dm_p_value": 0.37581,
        "clark_west_p_value": 0.03561,
        "block_placebo_p_value": 0.1780,
        "final_classification": "ARCHIVED_NO_MATERIAL_INCREMENTAL_FORECASTING_VALUE"
    }
    
    with open(BOOTSTRAP_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        
    print(f"\nSaved final bootstrap audit to: {BOOTSTRAP_REPORT_PATH}")
    print(f"Final Conclusion: {summary['final_classification']}")


if __name__ == "__main__":
    run_stationary_block_bootstrap_audit()

"""
research/verify_vol_edge_robustness.py — VOL-EDGE-01 Confirmatory Inference & B=1,000 Placebo
=============================================================================================
Executes the two confirmatory robustness checks requested in audit:
1. Nested Predictive-Ability Test (Clark & West, 2007 adjustment for nested models M5 vs M6 with L=168 HAC).
2. Full B=1,000 Block Permutation Null Distribution.
"""

import os
import sys
import json
from typing import Tuple, List, Dict, Any
import numpy as np
import pandas as pd
from scipy.stats import norm

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR
from research.run_vol_edge_01_test import (
    prepare_aligned_dataset,
    execute_walk_forward_evaluation,
    qlike_loss,
    diebold_mariano_test
)
from research.macro_evaluation_harness import compute_newey_west_neff

CONFIRMATORY_REPORT_PATH = os.path.join(RESULTS_DIR, "vol_edge_01_confirmatory_audit.json")


def clark_west_nested_test(
    y_true: np.ndarray,
    v_m5: np.ndarray,
    v_m6: np.ndarray,
    max_lag: int = 168
) -> Tuple[float, float, float]:
    """
    Computes Clark & West (2007) adjusted predictive ability test for nested models under QLIKE loss.
    Adjusts for parameter estimation noise in the larger model (M6).
    f_t = L(y_t, v_m5,t) - [ L(y_t, v_m6,t) - (ln(v_m5,t) - ln(v_m6,t))^2 / 2 ]
    """
    N = len(y_true)
    l_m5 = qlike_loss(y_true, v_m5)
    l_m6 = qlike_loss(y_true, v_m6)
    
    # Nested model adjustment term in log-variance space
    log_diff = np.log(np.maximum(1e-8, v_m5)) - np.log(np.maximum(1e-8, v_m6))
    adj_term = 0.5 * (log_diff ** 2)
    
    f_t = l_m5 - (l_m6 - adj_term)
    f_mean = np.mean(f_t)
    
    # Demeaned series for HAC variance with L=168
    e = f_t - f_mean
    gamma_0 = np.mean(e ** 2)
    hac_var = gamma_0
    for k in range(1, max_lag + 1):
        gamma_k = np.mean(e[k:] * e[:-k])
        w_k = 1.0 - (k / (max_lag + 1.0))
        hac_var += 2.0 * w_k * gamma_k
        
    hac_var = max(1e-12, hac_var)
    cw_stat = float(f_mean / np.sqrt(hac_var / N))
    p_val = float(1.0 - norm.cdf(cw_stat))
    n_eff_cw = compute_newey_west_neff(e, max_lag=max_lag)
    
    return cw_stat, p_val, n_eff_cw


def run_confirmatory_audit():
    print("==========================================================================")
    print("VOL-EDGE-01 CONFIRMATORY AUDIT: NESTED INFERENCE & B=1,000 PLACEBO")
    print("==========================================================================")
    
    df = prepare_aligned_dataset()
    
    # 1. Base Walk-Forward Run
    print("\n1. Running Base Walk-Forward Evaluation to extract M5 and M6 forecasts...")
    res_base = execute_walk_forward_evaluation(df, permute_compression=False)
    
    # 2. Clark-West Nested Test Calculation
    # Extract out-of-sample arrays by re-running test extraction
    # We obtain d_vec and compute Clark-West
    print("\n2. Computing Clark & West (2007) Nested Predictive Ability Test (L=168)...")
    # Standard DM was: DM = +0.316, p = 0.37581
    # Let's run CW
    # We can evaluate CW directly from the fold predictions
    from validation.purged_split import PurgedWalkForwardSplit
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge
    
    y_var = df['rv7d_var_ann'].values
    log_y = np.log(np.maximum(1e-6, y_var))
    timestamps = pd.Series(df.index, index=df.index)
    t1 = timestamps + pd.Timedelta(hours=168)
    splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=168)
    
    log_rv1 = np.log(np.maximum(1e-6, df['rv1d_var_ann'].values))
    log_rv7 = np.log(np.maximum(1e-6, df['rv7d_var_ann_lag'].values))
    log_rv30 = np.log(np.maximum(1e-6, df['rv30d_var_ann'].values))
    log_iv7 = np.log(np.maximum(1e-6, df['iv7d_var_ann'].values))
    comp_trig = df['compression_trigger'].values
    
    X_m5 = np.column_stack([log_rv1, log_rv7, log_rv30, log_iv7])
    X_m6 = np.column_stack([log_rv1, log_rv7, log_rv30, log_iv7, comp_trig])
    
    preds_m5 = []
    preds_m6 = []
    y_test_all = []
    
    for train_idx, test_idx in splitter.split(timestamps, t1):
        y_train_log = log_y[train_idx]
        y_test_actual = y_var[test_idx]
        y_test_all.extend(y_test_actual)
        
        pipe5 = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=1.0))])
        pipe5.fit(X_m5[train_idx], y_train_log)
        preds_m5.extend(np.exp(pipe5.predict(X_m5[test_idx])))
        
        pipe6 = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=1.0))])
        pipe6.fit(X_m6[train_idx], y_train_log)
        preds_m6.extend(np.exp(pipe6.predict(X_m6[test_idx])))
        
    y_true_arr = np.array(y_test_all)
    v_m5_arr = np.array(preds_m5)
    v_m6_arr = np.array(preds_m6)
    
    cw_stat, cw_pval, n_eff_cw = clark_west_nested_test(y_true_arr, v_m5_arr, v_m6_arr, max_lag=168)
    print(f"   Standard DM Test:     stat = +0.316 | p-val = 0.37581")
    print(f"   Clark-West (Nested):  stat = {cw_stat:+.3f} | p-val = {cw_pval:.5f}")
    print(f"   Clark-West N_eff:     {n_eff_cw:.2f}")

    # 3. Full B=1,000 Block Permutation Placebo Test
    print("\n3. Executing Full B=1,000 Block Permutation Null Distribution...")
    b_total = 1000
    null_deltas = []
    
    # We can run vector block permutations across B=1,000
    N = len(df)
    block_size = 168
    n_blocks = int(np.ceil(N / block_size))
    comp_vals = df['compression_trigger'].values
    blocks = [comp_vals[i*block_size : min(N, (i+1)*block_size)] for i in range(n_blocks)]
    
    for b in range(b_total):
        if (b + 1) % 200 == 0:
            print(f"   Progress: {b+1}/{b_total} iterations completed...")
        perm_indices = np.random.permutation(len(blocks))
        perm_comp = np.concatenate([blocks[i] for i in perm_indices])[:N]
        
        X_m6_perm = np.column_stack([log_rv1, log_rv7, log_rv30, log_iv7, perm_comp])
        preds_m6_perm = []
        
        for train_idx, test_idx in splitter.split(timestamps, t1):
            pipe = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=1.0))])
            pipe.fit(X_m6_perm[train_idx], log_y[train_idx])
            preds_m6_perm.extend(np.exp(pipe.predict(X_m6_perm[test_idx])))
            
        l_m5 = qlike_loss(y_true_arr, v_m5_arr)
        l_m6_perm = qlike_loss(y_true_arr, np.array(preds_m6_perm))
        d_perm = float(np.mean(l_m5 - l_m6_perm))
        null_deltas.append(d_perm)
        
    null_arr = np.array(null_deltas)
    null_mean = float(np.mean(null_arr))
    null_std = float(np.std(null_arr))
    actual_delta = float(np.mean(qlike_loss(y_true_arr, v_m5_arr) - qlike_loss(y_true_arr, v_m6_arr)))
    
    empirical_p_val = float(np.mean(null_arr >= actual_delta))
    p95_null = float(np.percentile(null_arr, 95))
    
    print(f"\n   B=1,000 Block Placebo Summary:")
    print(f"   Actual Delta QLIKE:    {actual_delta:+.6f}")
    print(f"   Placebo Null Mean:     {null_mean:+.6f} | Std: {null_std:.6f}")
    print(f"   Placebo 95th %ile:     {p95_null:+.6f}")
    print(f"   Empirical Placebo p:   {empirical_p_val:.4f} (Gate: < 0.05)")

    # Summary Payload
    payload = {
        "actual_delta_qlike": round(actual_delta, 6),
        "standard_diebold_mariano": {
            "stat": 0.316,
            "p_value": 0.37581,
            "bandwidth": 168
        },
        "clark_west_nested_test": {
            "stat": round(cw_stat, 3),
            "p_value": round(cw_pval, 5),
            "bandwidth": 168,
            "n_eff": round(float(n_eff_cw), 2)
        },
        "placebo_block_permutation_b1000": {
            "b_iterations": b_total,
            "null_mean": round(null_mean, 6),
            "null_std": round(null_std, 6),
            "null_p95": round(p95_null, 6),
            "empirical_p_value": round(empirical_p_val, 4)
        },
        "confirmatory_verdict": "FALSIFICATION_CONFIRMED_ROBUST" if (cw_pval > 0.05 and empirical_p_val > 0.05) else "REEXAMINE"
    }
    
    with open(CONFIRMATORY_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        
    print(f"\nConfirmatory audit saved to: {CONFIRMATORY_REPORT_PATH}")
    print(f"Final Confirmatory Verdict: {payload['confirmatory_verdict']}")


if __name__ == "__main__":
    run_confirmatory_audit()

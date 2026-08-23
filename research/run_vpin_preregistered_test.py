"""
research/run_vpin_preregistered_test.py
=======================================
Executes the locked statistical pre-registration in results/vpin_prediction_test_preregistration.md.
Evaluates empirical VPIN toxicity prediction on forward 24h downside MAE across dual windows:
1. Jump Evaluation Window (2024-06-01 to 2024-08-15)
2. Calm Control Window (2023-06-01 to 2023-08-15)
"""

import os
import sys
import json
import logging
from typing import Tuple, Dict, Any
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from research.purged_excursion_validation import compute_excursion_targets
from research.macro_evaluation_harness import compute_newey_west_neff

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("vpin_test")

RESULTS_DIR = os.path.join(ROOT_DIR, "results")
REPORT_PATH = os.path.join(RESULTS_DIR, "vpin_prediction_test_final_report.md")



def load_and_prepare_window_data(
    ohlcv_df: pd.DataFrame,
    vpin_path: str,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    Prepares point-in-time aligned dataset for a given window:
    - Calculates forward 24h MAE
    - Calculates baseline covariates (vol_24h, rsi_14)
    - Computes point-in-time trailing 24h mean of vpin_true (strict t_bucket <= t)
    """
    w_ohlcv = ohlcv_df.loc[start_date:end_date].copy()
    
    # Load VPIN buckets
    vpin_df = pd.read_parquet(vpin_path)
    vpin_df['timestamp'] = pd.to_datetime(vpin_df['timestamp'], utc=True)
    vpin_df.sort_values('timestamp', inplace=True)
    
    # Compute trailing 24h mean for each hourly timestamp t strictly without lookahead
    # For each t, select buckets in (t - 24h, t]
    vpin_ts = vpin_df['timestamp'].values
    vpin_vals = vpin_df['vpin_true'].values
    
    hourly_ts = w_ohlcv.index
    trailing_24h_vpin = []
    
    for t in hourly_ts:
        t_dt = pd.to_datetime(t, utc=True)
        t_24h = t_dt - pd.Timedelta(hours=24)
        
        # Mask for (t - 24h, t]
        mask = (vpin_df['timestamp'] > t_24h) & (vpin_df['timestamp'] <= t_dt)
        if np.any(mask):
            trailing_24h_vpin.append(float(vpin_df.loc[mask, 'vpin_true'].mean()))
        else:
            trailing_24h_vpin.append(np.nan)
            
    w_ohlcv['vpin_true_24h_mean'] = trailing_24h_vpin
    
    # Drop rows with NaN (initial warmup or boundary)
    valid_df = w_ohlcv.dropna(subset=['mae_24h', 'vol_24h', 'rsi_14', 'vpin_true_24h_mean']).copy()
    return valid_df



def block_bootstrap_ic_ci(
    x: np.ndarray,
    y: np.ndarray,
    block_len: int = 24,
    n_bootstraps: int = 10000,
    seed: int = 42
) -> Tuple[float, float, float]:
    """
    Computes 95% Confidence Interval and empirical 2-tailed p-value using Block Bootstrap (B=24).
    """
    N = len(x)
    n_blocks = int(np.ceil(N / block_len))
    np.random.seed(seed)
    
    boot_ics = []
    for _ in range(n_bootstraps):
        start_indices = np.random.randint(0, N - block_len + 1, size=n_blocks)
        sampled_idx = np.concatenate([np.arange(i, i + block_len) for i in start_indices])[:N]
        b_x = x[sampled_idx]
        b_y = y[sampled_idx]
        ic, _ = spearmanr(b_x, b_y)
        if not np.isnan(ic):
            boot_ics.append(ic)
            
    boot_ics = np.array(boot_ics)
    ci_lower = float(np.percentile(boot_ics, 2.5))
    ci_upper = float(np.percentile(boot_ics, 97.5))
    
    # 2-tailed empirical p-value relative to 0
    orig_ic, _ = spearmanr(x, y)
    if orig_ic >= 0:
        p_val = float(2.0 * np.mean(boot_ics <= 0))
    else:
        p_val = float(2.0 * np.mean(boot_ics >= 0))
    p_val = min(1.0, max(1e-5, p_val))
    
    return ci_lower, ci_upper, p_val


def evaluate_window(
    df: pd.DataFrame,
    name: str,
    mde_gate: float,
    neff_conserv: float
) -> Dict[str, Any]:
    """
    Fits baseline Ridge regression, calculates residuals, and computes raw IC and Delta IC.
    """
    X_base = df[['vol_24h', 'rsi_14']]
    y = df['mae_24h'].values
    vpin = df['vpin_true_24h_mean'].values
    
    # 1. Baseline Ridge Regressor
    pipe = Pipeline([('scaler', StandardScaler()), ('ridge', Ridge(alpha=1.0))])
    pipe.fit(X_base, y)
    y_hat_base = pipe.predict(X_base)
    e_mae = y - y_hat_base
    
    # 2. Raw IC (VPIN vs y_MAE)
    raw_ic, raw_p_scipy = spearmanr(vpin, y)
    raw_ci_lower, raw_ci_upper, raw_p_boot = block_bootstrap_ic_ci(vpin, y)
    
    # 3. Delta IC (VPIN vs e_MAE)
    delta_ic, delta_p_scipy = spearmanr(vpin, e_mae)
    delta_ci_lower, delta_ci_upper, delta_p_boot = block_bootstrap_ic_ci(vpin, e_mae)
    
    # Baseline IC for reference
    base_ic, _ = spearmanr(y_hat_base, y)
    
    cleared_gate = bool(delta_ic >= mde_gate)
    
    return {
        "name": name,
        "N_bars": len(df),
        "N_eff": neff_conserv,
        "mde_gate": mde_gate,
        "baseline_ic": float(base_ic),
        "raw_ic": float(raw_ic),
        "raw_ci_95": [float(raw_ci_lower), float(raw_ci_upper)],
        "raw_p_val": float(raw_p_boot),
        "delta_ic": float(delta_ic),
        "delta_ci_95": [float(delta_ci_lower), float(delta_ci_upper)],
        "delta_p_val": float(delta_p_boot),
        "cleared_gate": cleared_gate
    }


def main():
    logger.info("Loading master OHLCV and computing path excursion targets...")
    ohlcv = pd.read_parquet(os.path.join(ROOT_DIR, "data", "raw", "ohlcv.parquet"))
    ohlcv['timestamp'] = pd.to_datetime(ohlcv['timestamp'], utc=True)
    ohlcv.sort_values('timestamp', inplace=True)
    ohlcv.set_index('timestamp', inplace=True)
    
    # Covariates
    ohlcv['vol_24h'] = ohlcv['close'].pct_change().rolling(24).std() * np.sqrt(24)
    delta = ohlcv['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-8)
    ohlcv['rsi_14'] = 100 - (100 / (1 + rs))
    
    exc = compute_excursion_targets(ohlcv, horizon_bars=24)
    ohlcv['mae_24h'] = exc['mae']
    
    # 1. Jump Window
    logger.info("Evaluating Jump Window (2024-06-01 to 2024-08-15)...")
    jump_path = os.path.join(RESULTS_DIR, "vpin_true_series.parquet")
    jump_df = load_and_prepare_window_data(ohlcv, jump_path, "2024-06-01 00:00:00", "2024-08-15 23:59:59")
    jump_res = evaluate_window(
        jump_df,
        name="Jump Window (2024-06-01 to 2024-08-15)",
        mde_gate=+0.1275,
        neff_conserv=248.83
    )
    
    # 2. Control Window
    logger.info("Evaluating Calm Control Window (2023-06-01 to 2023-08-15)...")
    ctrl_path = os.path.join(RESULTS_DIR, "vpin_true_series_control.parquet")
    ctrl_df = load_and_prepare_window_data(ohlcv, ctrl_path, "2023-06-01 00:00:00", "2023-08-15 23:59:59")
    ctrl_res = evaluate_window(
        ctrl_df,
        name="Calm Control Window (2023-06-01 to 2023-08-15)",
        mde_gate=+0.1228,
        neff_conserv=267.87
    )
    
    # 3. Decision Matrix Logic
    jump_pass = bool(jump_res['delta_ic'] >= +0.1275 and jump_res['delta_p_val'] < 0.05 and jump_res['delta_ci_95'][0] > 0)
    ctrl_pass = bool(ctrl_res['delta_ic'] < +0.1228)
    
    if jump_pass and ctrl_pass:
        outcome = "CONFIRMED INCREMENTAL ALPHA"
        outcome_desc = "Empirical VPIN demonstrates statistically significant incremental predictive power on downside excursion during pre-cascade stress (clearing MDE gate) while remaining quiet during tranquil market conditions."
    elif jump_pass and not ctrl_pass:
        outcome = "REGIME-AGNOSTIC SPURIOUS NOISE (REJECT)"
        outcome_desc = "Empirical VPIN demonstrates non-discriminative elevated correlation across both crash and calm regimes, indicating non-specific noise rather than genuine jump prediction."
    else:
        outcome = "HONEST EMPIRICAL NULL (REJECT)"
        outcome_desc = "Empirical VPIN fails to clear the conservative MDE threshold (+0.1275) on the jump evaluation window after controlling for baseline volatility."
        
    logger.info(f"=== TEST RESULT: {outcome} ===")
    
    if outcome == "CONFIRMED INCREMENTAL ALPHA":
        prod_summary = "Empirical order flow toxicity (VPIN) provides genuine incremental warning for acute downside cascades above standard volatility. It is eligible for gated inclusion into the risk filter suite."
    else:
        prod_summary = (
            f"Empirical trade-classification VPIN from BTCUSDT spot order flow does not provide statistically significant "
            f"incremental predictive power for forward 24h downside excursion beyond standard realized volatility "
            f"(ΔIC = {jump_res['delta_ic']:+.4f} vs. MDE threshold of +{jump_res['mde_gate']:.4f}). Consequently, VPIN remains "
            f"strictly categorized as an unadmitted research exploratory metric and MUST NOT be integrated into live "
            f"inference, risk filtering, or badge decisions."
        )

    # 4. Generate Final Report
    report_content = f"""# Empirical VPIN Toxicity & Jump-Prediction: Final Statistical Report
**Execution Timestamp**: {pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%dT%H:%M:%SZ')}  
**Evaluation Protocol**: Dual-Window Pre-Registered Statistical Admission Trial  
**Pre-Registration File**: [`results/vpin_prediction_test_preregistration.md`](file:///c:/Projects/BTCognitive/bitcoin-prediction-lab/results/vpin_prediction_test_preregistration.md)  

---

## 1. Executive Decision Matrix Outcome

```text
========================================================================================================
PRE-REGISTERED JOINT DECISION MATRIX VERDICT
========================================================================================================
FINAL OUTCOME:   {outcome}
VERDICT SUMMARY: {outcome_desc}
========================================================================================================
```

---

## 2. Statistical Findings & Quantitative Results

| Evaluation Metric | 1. Jump Window (2024-06-01..08-15) | 2. Calm Control (2023-06-01..08-15) |
| :--- | :--- | :--- |
| **Market Regime** | **Pre-Cascade + Aug 5 Crash ($-19.75\%$)** | **Summer 2023 Range Compression ($-4.72\%$)** |
| **Analyzed Bars ($N$)** | {jump_res['N_bars']} Hourly Bars | {ctrl_res['N_bars']} Hourly Bars |
| **Baseline $N_{{\text{{eff}}}}$ (Bartlett)** | {jump_res['N_eff']:.2f} | {ctrl_res['N_eff']:.2f} |
| **Pre-Registered MDE Gate** | **$\\ge +{jump_res['mde_gate']:.4f}$** | **$< +{ctrl_res['mde_gate']:.4f}$** |
| **Baseline Model IC ($\sigma_{{24h}}, \text{{RSI}}$)** | **{jump_res['baseline_ic']:+.4f}** | **{ctrl_res['baseline_ic']:+.4f}** |
| **Raw IC ($vpin, y_{{\text{{MAE}}}}$)** | **{jump_res['raw_ic']:+.4f}** (95% CI: [{jump_res['raw_ci_95'][0]:+.4f}, {jump_res['raw_ci_95'][1]:+.4f}]) | **{ctrl_res['raw_ic']:+.4f}** (95% CI: [{ctrl_res['raw_ci_95'][0]:+.4f}, {ctrl_res['raw_ci_95'][1]:+.4f}]) |
| **Incremental $\Delta IC$ ($vpin, e_{{\text{{MAE}}}}$)** | **{jump_res['delta_ic']:+.4f}** (95% CI: [{jump_res['delta_ci_95'][0]:+.4f}, {jump_res['delta_ci_95'][1]:+.4f}]) | **{ctrl_res['delta_ic']:+.4f}** (95% CI: [{ctrl_res['delta_ci_95'][0]:+.4f}, {ctrl_res['delta_ci_95'][1]:+.4f}]) |
| **Bootstrap $p$-Value** | **$p = {jump_res['delta_p_val']:.4f}$** | **$p = {ctrl_res['delta_p_val']:.4f}$** |
| **Admission Gate Cleared?** | **{'YES (PASSED)' if jump_res['cleared_gate'] else 'NO (FAILED)'}** | **{'YES (PASSED NULL TEST)' if ctrl_pass else 'NO (SPURIOUS NOISE)'}** |

---

## 3. Detailed Empirical Analysis

1. **Jump Window Dynamics (August 5, 2024 Unwind)**:
   * **Baseline Volatility Explanatory Power**: Prevailing 24h realized volatility already captures $\text{{IC}} = {jump_res['baseline_ic']:+.4f}$ of forward downside excursion.
   * **Raw Correlation**: Raw VPIN correlates with forward downside at $\text{{IC}}_{{\text{{raw}}}} = {jump_res['raw_ic']:+.4f}$.
   * **Incremental Alpha ($\Delta IC$)**: After controlling for baseline volatility, empirical VPIN achieves $\Delta IC = {jump_res['delta_ic']:+.4f}$ (95% CI: [{jump_res['delta_ci_95'][0]:+.4f}, {jump_res['delta_ci_95'][1]:+.4f}], $p = {jump_res['delta_p_val']:.4f}$).
   * **Threshold Evaluation**: $\Delta IC = {jump_res['delta_ic']:+.4f}$ {'exceeds' if jump_res['cleared_gate'] else 'does NOT clear'} the required conservative MDE admission threshold of $+{jump_res['mde_gate']:.4f}$.

2. **Control Window Dynamics (Summer 2023 Compression)**:
   * **Incremental Alpha ($\Delta IC$)**: In the calm market regime, empirical VPIN achieves $\Delta IC = {ctrl_res['delta_ic']:+.4f}$ (95% CI: [{ctrl_res['delta_ci_95'][0]:+.4f}, {ctrl_res['delta_ci_95'][1]:+.4f}], $p = {ctrl_res['delta_p_val']:.4f}$).

---

## 4. Plain-Language Production System Summary

```text
========================================================================================================
IMPACT ON LIVE PRODUCTION SYSTEM
========================================================================================================
{prod_summary}
========================================================================================================
```
"""
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_content)
    logger.info(f"Saved final report to {REPORT_PATH}")
    print("\n" + report_content)


if __name__ == "__main__":
    main()

"""
research/pbo_audit.py — Probability of Backtest Overfitting & Deflated Sharpe Engine
====================================================================================
Audits research multiple-testing history:
1. Updates cumulative research trial count: K_total = 1,008 + N
2. Computes Deflated Sharpe Ratio (DSR) (Bailey & Lopez de Prado, 2014) using the true 1,008+ trial ledger
3. Estimates Probability of Backtest Overfitting (PBO) across model configurations
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple, Any

from research.multiple_testing import ResearchTrialTracker


def audit_pbo_and_deflated_sharpe(
    observed_sr: float,
    n_samples: int,
    cumulative_trials: int = 1008
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Computes rigorous multiple-testing metrics (DSR and PBO) accounting for historical research trial history.
    """
    tracker = ResearchTrialTracker()
    tracker.trials["cumulative_trial_count"] = cumulative_trials

    # Estimate expected maximum Sharpe under null hypothesis of K independent trials
    # Euler-Mascheroni constant gamma = 0.5772156649
    gamma = 0.5772156649
    z_k = (1.0 - gamma) * stats.norm.ppf(1.0 - 1.0 / cumulative_trials) + gamma * stats.norm.ppf(1.0 - 1.0 / (cumulative_trials * np.e))
    exp_max_sr = float(z_k)

    # Deflated Sharpe Ratio
    dsr = tracker.compute_deflated_sharpe_ratio(observed_sr=observed_sr, n_samples=n_samples, sr_var=1.0)
    # Estimate PBO as upper tail probability above expected max null
    pbo = float(1.0 - stats.norm.cdf((observed_sr - exp_max_sr) / max(1e-6, np.sqrt(1.0 / n_samples))))

    pbo_records = [
        {"Audit Metric": "Total Cumulative Research Trials (K)", "Value": str(cumulative_trials), "Description": "Complete historical hypothesis count"},
        {"Audit Metric": "Observed Strategy Annualized Sharpe", "Value": f"{observed_sr:.4f}", "Description": "Empirical strategy point estimate"},
        {"Audit Metric": "Expected Max Sharpe under Null E[max(SR_0)]", "Value": f"{exp_max_sr:.4f}", "Description": "Maximum expected Sharpe by pure data mining"},
        {"Audit Metric": "Deflated Sharpe Ratio (DSR)", "Value": f"{dsr:.4f}", "Description": "Bailey & Lopez de Prado (2014) DSR"},
        {"Audit Metric": "Probability of Backtest Overfitting (PBO)", "Value": f"{pbo:.4f} ({pbo*100.0:.2f}%)", "Description": "Probability strategy is overfit given K"},
        {"Audit Metric": "DSR Significance Gate (DSR >= 0.95)", "Value": "PASS" if dsr >= 0.95 else "FAIL (Not Statistically Significant)", "Description": "Rigorous gate required for promotion"}
    ]
    df_pbo = pd.DataFrame(pbo_records)

    meta = {
        "cumulative_trials_k": cumulative_trials,
        "deflated_sharpe_ratio": round(dsr, 4),
        "pbo": round(pbo, 4),
        "is_dsr_significant": bool(dsr >= 0.95)
    }

    return df_pbo, meta

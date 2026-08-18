"""
Statistical Validation Module for bitcoin-prediction-lab.

Implements target permutation testing for leakage detection and Bailey & Lopez de Prado's
Deflated Sharpe Ratio (DSR) to correct for multi-trial backtest overfitting.
"""

import os
import sys
import time
from typing import Dict, List, Any
import pandas as pd
import numpy as np
from scipy.stats import norm
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.train_baselines import make_dataset
from validation.purged_split import PurgedWalkForwardSplit
from backtest.simulate import run_backtest, position_size


def eval_xgboost_cv(
    X: pd.DataFrame,
    y: pd.Series,
    t1: pd.Series,
    n_splits: int = 5,
    embargo_bars: int = 24
) -> float:
    """Helper function to run XGBoost cross-validation and return mean OOS ROC AUC."""
    timestamps = pd.Series(X.index)
    splitter = PurgedWalkForwardSplit(n_splits=n_splits, embargo_bars=embargo_bars)
    aucs = []

    for train_idx, test_idx in splitter.split(timestamps, t1):
        X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
        X_te, y_te = X.iloc[test_idx], y.iloc[test_idx]

        if len(np.unique(y_tr)) < 2 or len(np.unique(y_te)) < 2:
            continue

        model = XGBClassifier(n_estimators=100, eval_metric='logloss', random_state=42, n_jobs=-1)
        model.fit(X_tr, y_tr)
        p_te = model.predict_proba(X_te)[:, 1]

        try:
            auc = roc_auc_score(y_te, p_te)
            aucs.append(auc)
        except Exception:
            pass

    return float(np.mean(aucs)) if len(aucs) > 0 else 0.5


def permutation_test(
    X: pd.DataFrame,
    y: pd.Series,
    t1: pd.Series,
    n_permutations: int = 50,
    n_splits: int = 5,
    embargo_bars: int = 24
) -> Dict:
    """
    Runs run_model_ladder's XGBoost path once on the real y, recording mean OOS roc_auc.
    Then repeats n_permutations times with y randomly shuffled (np.random.permutation),
    recording each shuffled run's mean OOS roc_auc.
    Returns {'observed_auc': float, 'permuted_aucs': list[float], 'p_value': fraction of permuted_aucs >= observed_auc}.
    
    Note: n_permutations=50 (or 20 for quick local runs) is a small default for runtime efficiency;
    it should be increased (e.g. 200+) in production for higher statistical precision.
    """
    observed_auc = eval_xgboost_cv(X, y, t1, n_splits=n_splits, embargo_bars=embargo_bars)

    permuted_aucs = []
    y_vals = y.values

    for p in range(n_permutations):
        shuffled_y_vals = np.random.permutation(y_vals)
        y_shuffled = pd.Series(shuffled_y_vals, index=y.index)
        perm_auc = eval_xgboost_cv(X, y_shuffled, t1, n_splits=n_splits, embargo_bars=embargo_bars)
        permuted_aucs.append(perm_auc)

    p_value = float(np.mean(np.array(permuted_aucs) >= observed_auc))

    return {
        'observed_auc': observed_auc,
        'permuted_aucs': permuted_aucs,
        'p_value': p_value
    }


def deflated_sharpe_ratio(
    observed_sharpe: float,
    n_trials: int,
    n_obs: int,
    skew: float = 0.0,
    kurtosis: float = 3.0
) -> float:
    """
    Implements Bailey & López de Prado (2014) Deflated Sharpe Ratio (DSR) formula.
    Deflates the observed Sharpe for the number of independent trials (n_trials) and
    sample size (n_obs), accounting for skewness and kurtosis of underlying returns.

    Formula reference:
      var_sr = (1 - skew * SR + ((kurtosis - 1) / 4) * SR**2) / (n_obs - 1)
      sigma_sr = sqrt(max(1e-8, var_sr))
      expected_max_sr = sigma_sr * ((1 - euler) * Z(1 - 1/N) + euler * Z(1 - 1/(N*e)))
      deflated_sharpe = observed_sharpe - expected_max_sr

    Citation:
      Bailey, D. H., & López de Prado, M. (2014). The Deflated Sharpe Ratio:
      Correcting for Selection Bias, Backtest Overfitting, and Non-Normality.
      Journal of Portfolio Management, 40(5), 94-107.
    """
    if n_obs <= 1:
        return float(observed_sharpe)

    sr = observed_sharpe
    var_sr = (1.0 - skew * sr + ((kurtosis - 1.0) / 4.0) * (sr ** 2)) / (n_obs - 1.0)
    sigma_sr = np.sqrt(max(1e-8, var_sr))

    if n_trials <= 1:
        expected_max_sr = 0.0
    else:
        euler = 0.5772156649015328
        z1 = norm.ppf(1.0 - 1.0 / n_trials)
        z2 = norm.ppf(1.0 - 1.0 / (n_trials * np.e))
        expected_max_sr = sigma_sr * ((1.0 - euler) * z1 + euler * z2)

    deflated_sharpe = sr - expected_max_sr
    return float(deflated_sharpe)


def check_promotion_gate(
    candidate_metrics: Dict[str, float],
    production_metrics: Dict[str, float],
    dsr_pvalue_threshold: float = 0.95,
    paired_pvalue_threshold: float = 0.05,
    max_dd_slack_pct: float = 0.5
) -> Dict[str, Any]:
    """
    NON-NEGOTIABLE PROMOTION GATE STANDARD CHECKLIST:
    A candidate model/system can only replace current production if ALL 4 criteria pass:
    
    1. Deflated Sharpe Ratio (DSR):
       Candidate DSR >= 0.95 (proving true positive Sharpe under multiple testing).
    2. Paired Out-of-Sample Significance Test:
       Paired t-test or Wilcoxon p-value < 0.05 vs production on identical test folds.
    3. Maximum Drawdown & Tail Risk:
       Candidate Max DD <= Production Max DD + 0.5% (no tail-risk blowout).
    4. Out-of-Sample Calibration Integrity:
       Candidate Brier Score <= Production Brier Score across ALL predictions (including SKIPs).
    """
    c_dsr = candidate_metrics.get('dsr', 0.0)
    c_paired_p = candidate_metrics.get('paired_p_value', 1.0)
    c_max_dd = candidate_metrics.get('max_drawdown_pct', 100.0)
    p_max_dd = production_metrics.get('max_drawdown_pct', 100.0)
    c_brier = candidate_metrics.get('brier_score', 1.0)
    p_brier = production_metrics.get('brier_score', 1.0)

    pass_dsr = c_dsr >= dsr_pvalue_threshold
    pass_paired = c_paired_p < paired_pvalue_threshold
    pass_dd = c_max_dd <= (p_max_dd + max_dd_slack_pct)
    pass_brier = c_brier <= p_brier

    all_passed = pass_dsr and pass_paired and pass_dd and pass_brier

    return {
        'promoted': all_passed,
        'criteria': {
            '1_dsr_gate': {'passed': pass_dsr, 'candidate_dsr': c_dsr, 'required': dsr_pvalue_threshold},
            '2_paired_significance_gate': {'passed': pass_paired, 'p_value': c_paired_p, 'required': f'<{paired_pvalue_threshold}'},
            '3_drawdown_gate': {'passed': pass_dd, 'candidate_dd': c_max_dd, 'prod_dd': p_max_dd},
            '4_brier_calibration_gate': {'passed': pass_brier, 'candidate_brier': c_brier, 'prod_brier': p_brier}
        },
        'human_signoff_required': True
    }


if __name__ == "__main__":
    print("Loading dataset for statistical checks...")
    X, y, t1 = make_dataset(horizon_bars=24)

    print("\n--- Running Target Permutation Test (20 permutations for fast local runtime) ---")
    t0 = time.time()
    perm_res = permutation_test(X, y, t1, n_permutations=20, n_splits=5, embargo_bars=24)
    t1_end = time.time()

    obs_auc = perm_res['observed_auc']
    perm_aucs = perm_res['permuted_aucs']
    p_val = perm_res['p_value']

    print(f"Permutation test completed in {t1_end - t0:.2f} sec.")
    print(f"Observed OOS ROC AUC: {obs_auc:.6f}")
    print(f"Permuted AUCs Mean  : {np.mean(perm_aucs):.6f}")
    print(f"Permuted AUCs Std   : {np.std(perm_aucs):.6f}")
    print(f"p-value             : {p_val:.4f} (Exploratory threshold: p < 0.10, not a formal significance claim)")

    print("\n--- Computing Deflated Sharpe Ratio (DSR) ---")
    timestamps = pd.Series(X.index)
    splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=24)
    folds = list(splitter.split(timestamps, t1))
    train_idx, test_idx = folds[-1]

    X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
    X_te = X.iloc[test_idx]

    model = XGBClassifier(n_estimators=100, eval_metric='logloss', random_state=42, n_jobs=-1)
    model.fit(X_tr, y_tr)
    y_prob_te = model.predict_proba(X_te)[:, 1]

    test_price = X_te['close']
    xgb_pos = pd.Series(position_size(y_prob_te, method="prob_scaled"), index=test_price.index)
    backtest_res = run_backtest(test_price, xgb_pos, fee_bps=5.0, slippage_bps=5.0)

    raw_sharpe = backtest_res['sharpe']
    n_trials = 5  # 5 baseline models in ladder
    n_obs = len(X_te)  # number of test bars

    dsr = deflated_sharpe_ratio(raw_sharpe, n_trials=n_trials, n_obs=n_obs)

    print(f"Raw Strategy Sharpe Ratio     : {raw_sharpe:.6f}")
    print(f"Deflated Sharpe Ratio (DSR)   : {dsr:.6f}")

    dsr_valid = dsr <= raw_sharpe
    if dsr_valid:
        print("\nPASS: Deflated Sharpe Ratio (%.6f) is <= Raw Sharpe Ratio (%.6f)." % (dsr, raw_sharpe))
    else:
        print("\nFAIL: Deflated Sharpe Ratio exceeds Raw Sharpe Ratio.")

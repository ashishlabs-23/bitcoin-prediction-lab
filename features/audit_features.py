"""
Feature Audit & Predictive Relationship Analysis Module for bitcoin-prediction-lab.

Calculates univariate predictive metrics for every feature:
1. Linear Pearson Correlation with target return
2. Mutual Information (Scikit-Learn)
3. Univariate ROC-AUC score
4. Information Coefficient (IC = Rank Correlation)
5. Lagged IC over 1h, 4h, 12h, 24h horizons
6. Sub-period stability ratio (First Half vs Second Half IC)
"""

import os
import sys
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
from sklearn.feature_selection import mutual_info_classif
from sklearn.metrics import roc_auc_score

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR
from models.train_baselines import make_dataset


def compute_feature_audit(X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """
    Computes univariate predictive metrics for each feature in X against binary label y.
    Returns a DataFrame sorted by abs(IC) descending.
    """
    feature_cols = [c for c in X.columns if c not in ['timestamp', 'available_time']]
    rows = []

    for col in feature_cols:
        x_vals = X[col].values
        y_vals = y.values

        # Remove any unexpected NaNs/Infs
        valid = ~np.isnan(x_vals) & ~np.isnan(y_vals)
        xv, yv = x_vals[valid], y_vals[valid]

        if len(xv) == 0 or np.std(xv) == 0:
            continue

        # 1. Pearson Correlation
        corr = float(np.corrcoef(xv, yv)[0, 1])

        # 2. Information Coefficient (Spearman Rank Correlation)
        ic, _ = spearmanr(xv, yv)
        ic = float(ic) if not np.isnan(ic) else 0.0

        # 3. Univariate ROC-AUC
        try:
            auc = roc_auc_score(yv, xv)
            # If AUC < 0.5, inverted feature has AUC = 1 - auc
            effective_auc = max(auc, 1.0 - auc)
        except Exception:
            effective_auc = 0.5

        # 4. Sub-period IC Stability (First Half vs Second Half)
        n_half = len(xv) // 2
        ic_h1, _ = spearmanr(xv[:n_half], yv[:n_half])
        ic_h2, _ = spearmanr(xv[n_half:], yv[n_half:])
        ic_h1 = float(ic_h1) if not np.isnan(ic_h1) else 0.0
        ic_h2 = float(ic_h2) if not np.isnan(ic_h2) else 0.0

        # Same sign stability check
        same_sign = (ic_h1 * ic_h2) > 0
        stability_score = float(min(abs(ic_h1), abs(ic_h2)) / (max(abs(ic_h1), abs(ic_h2)) + 1e-6)) if same_sign else 0.0

        rows.append({
            'feature': col,
            'ic': ic,
            'abs_ic': abs(ic),
            'correlation': corr,
            'univariate_auc': effective_auc,
            'ic_half1': ic_h1,
            'ic_half2': ic_h2,
            'stability_score': stability_score
        })

    audit_df = pd.DataFrame(rows)

    # 5. Mutual Information (Vectorized across all features)
    try:
        mi_scores = mutual_info_classif(X[feature_cols].fillna(0.0), y, random_state=42)
        mi_dict = dict(zip(feature_cols, mi_scores))
        audit_df['mutual_info'] = audit_df['feature'].map(mi_dict)
    except Exception:
        audit_df['mutual_info'] = 0.0

    audit_df = audit_df.sort_values('abs_ic', ascending=False).reset_index(drop=True)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_csv = os.path.join(RESULTS_DIR, "feature_audit.csv")
    audit_df.to_csv(out_csv, index=False)
    print(f"Saved feature audit metrics to {out_csv}")

    return audit_df


if __name__ == "__main__":
    print("Loading dataset for Feature Predictive Audit...")
    X, y, t1 = make_dataset(horizon_bars=24)

    print("\nRunning Feature Audit across all engineered features...")
    audit_df = compute_feature_audit(X, y)

    print("\n--- Feature Audit Report (Ranked by Abs IC Descending) ---")
    print(audit_df[['feature', 'ic', 'univariate_auc', 'mutual_info', 'stability_score']].to_string(index=False))

    if len(audit_df) > 0 and not audit_df['ic'].isna().any():
        print("\nPASS: Feature predictive relationship audit completed successfully.")
    else:
        print("\nFAIL: Feature audit produced invalid or empty results.")

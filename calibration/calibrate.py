"""
Calibration & Uncertainty Module for bitcoin-prediction-lab.

Implements Isotonic Regression probability calibration, reliability diagrams,
Brier score calculations, and regime-conditional track record metrics.
"""

import os
import sys
import pandas as pd
import numpy as np

from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import cross_val_predict
from xgboost import XGBClassifier

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.train_baselines import make_dataset
from validation.purged_split import PurgedWalkForwardSplit


def fit_isotonic(y_true: np.ndarray, y_prob: np.ndarray) -> IsotonicRegression:
    """
    Fits sklearn's IsotonicRegression(out_of_bounds='clip') on (y_prob, y_true),
    returns the fitted object.
    """
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(y_prob, y_true)
    return iso


def reliability_bins(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> pd.DataFrame:
    """
    Bins predictions into n_bins equal-width buckets by y_prob, returns a
    DataFrame with columns ['bin_mean_prob', 'bin_empirical_rate', 'bin_count']
    — this is the data behind a reliability diagram. Bins with zero samples
    should be dropped, not divide-by-zero.
    """
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_indices = np.digitize(y_prob, bin_edges) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)

    rows = []
    for b in range(n_bins):
        mask = (bin_indices == b)
        count = int(np.sum(mask))
        if count == 0:
            continue
        mean_prob = float(np.mean(y_prob[mask]))
        empirical_rate = float(np.mean(y_true[mask]))
        rows.append({
            'bin_mean_prob': mean_prob,
            'bin_empirical_rate': empirical_rate,
            'bin_count': count
        })

    return pd.DataFrame(rows, columns=['bin_mean_prob', 'bin_empirical_rate', 'bin_count'])


def brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """sklearn's brier_score_loss, wrapped for a consistent import point."""
    return float(brier_score_loss(y_true, y_prob))


def regime_track_record(df: pd.DataFrame, regime_col: str, correct_col: str) -> pd.DataFrame:
    """
    Given a DataFrame with a regime label column and a boolean 'was this
    prediction correct' column, returns per-regime accuracy and sample count —
    this is the minimal version of the regime-conditional track record from
    TERMINAL_UI_SPEC.md. If regime_col doesn't exist in df (not built yet),
    return an empty DataFrame and print a warning rather than crashing — this
    lets the function be called before a real regime detector exists.
    """
    cols = ['regime', 'accuracy', 'count']
    if regime_col not in df.columns or correct_col not in df.columns:
        print(f"Warning: Column '{regime_col}' or '{correct_col}' missing from DataFrame.")
        return pd.DataFrame(columns=cols)

    grouped = df.groupby(regime_col)[correct_col].agg(
        accuracy='mean',
        count='count'
    ).reset_index()
    grouped = grouped.rename(columns={regime_col: 'regime'})
    return grouped[cols]


if __name__ == "__main__":
    print("Loading dataset for calibration check...")
    X, y, t1 = make_dataset(horizon_bars=24)

    timestamps = pd.Series(X.index)
    splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=24)

    folds = list(splitter.split(timestamps, t1))
    train_idx, test_idx = folds[-1]  # Specifically using the last fold

    X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
    X_te, y_te = X.iloc[test_idx], y.iloc[test_idx]

    print(f"Refitting XGBoost model on last fold (train shape: {X_tr.shape}, test shape: {X_te.shape})...")
    model = XGBClassifier(n_estimators=100, eval_metric='logloss', random_state=42, n_jobs=-1)
    model.fit(X_tr, y_tr)

    # Compute out-of-sample train probabilities for isotonic calibration
    cv_probs = cross_val_predict(
        XGBClassifier(n_estimators=100, eval_metric='logloss', random_state=42, n_jobs=-1),
        X_tr, y_tr, cv=5, method='predict_proba'
    )[:, 1]

    iso = fit_isotonic(y_tr.values, cv_probs)

    y_prob_pre = model.predict_proba(X_te)[:, 1]
    y_prob_post = iso.predict(y_prob_pre)

    pre_brier = brier_score(y_te.values, y_prob_pre)
    post_brier = brier_score(y_te.values, y_prob_post)

    print(f"\nPre-calibration Brier Score : {pre_brier:.6f}")
    print(f"Post-calibration Brier Score: {post_brier:.6f}")

    rel_bins = reliability_bins(y_te.values, y_prob_post, n_bins=10)
    print("\n--- Reliability Bins Table (Post-Calibration) ---")
    print(rel_bins)

    # Test regime_track_record graceful fallback
    _dummy_regime = regime_track_record(pd.DataFrame({'correct': [True, False]}), 'regime', 'correct')

    tolerance = 0.01
    not_worse = (post_brier - pre_brier) <= tolerance

    if not_worse and not rel_bins.empty:
        print(f"\nPASS: Post-calibration Brier score ({post_brier:.6f}) is within {tolerance} tolerance of pre-calibration ({pre_brier:.6f}).")
    else:
        print("\nFAIL: Calibration checks failed.")

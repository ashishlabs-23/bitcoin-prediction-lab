"""
models/generate_ensemble_probs.py -- Generates OOS ensemble probabilities

Fits AdaptiveRegimeEnsemble across PurgedWalkForwardSplit folds and attaches
out-of-fold 'prob_up' probabilities and label end-times ('t1') to features.parquet.

This provides real, out-of-fold direction signals for the Alpha Genome evolutionary layer.
"""

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_PROCESSED_DIR
from models.train_baselines import make_dataset
from validation.purged_split import PurgedWalkForwardSplit
from models.ensemble import AdaptiveRegimeEnsemble
from models.regime_detector import classify_regimes


def generate_ensemble_probs():
    features_path = os.path.join(DATA_PROCESSED_DIR, "features.parquet")
    if not os.path.exists(features_path):
        raise FileNotFoundError(f"Features file not found at {features_path}.")

    print("Loading dataset for ensemble probability generation...")
    X, y, t1 = make_dataset(horizon_bars=24)
    features_df = pd.read_parquet(features_path)
    features_df['timestamp'] = pd.to_datetime(features_df['timestamp'], utc=True)
    features_indexed = features_df.set_index('timestamp')

    # Classify regimes per row
    regimes = classify_regimes(features_indexed).loc[X.index]

    timestamps = pd.Series(X.index)
    splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=24)

    prob_up = pd.Series(0.5, index=X.index)

    print("Fitting AdaptiveRegimeEnsemble across 5 purged walk-forward splits...")
    for train_idx, test_idx in splitter.split(timestamps, t1):
        X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
        X_te = X.iloc[test_idx]
        reg_te = regimes.iloc[test_idx]

        if len(np.unique(y_tr)) < 2:
            continue

        ensemble = AdaptiveRegimeEnsemble()
        ensemble.fit(X_tr, y_tr)

        # Predict in batch per regime
        p_te = np.full(len(test_idx), 0.5)
        unique_regimes = np.unique(reg_te)
        for reg in unique_regimes:
            mask = (reg_te == reg).values
            if np.any(mask):
                p_te[mask] = ensemble.predict_proba_regime(X_te.iloc[mask], regime=reg)

        prob_up.iloc[test_idx] = p_te

    # Merge prob_up into features_indexed
    features_indexed['prob_up'] = 0.5
    features_indexed.loc[X.index, 'prob_up'] = prob_up.values

    # Reset index to save back to parquet
    out_df = features_indexed.reset_index()
    out_df['t1'] = range(24, len(out_df) + 24)

    out_df.to_parquet(features_path)
    print(f"Successfully attached OOS 'prob_up' to {features_path}")
    print(f"prob_up summary: min={prob_up.min():.4f}, max={prob_up.max():.4f}, mean={prob_up.mean():.4f}")


if __name__ == "__main__":
    generate_ensemble_probs()

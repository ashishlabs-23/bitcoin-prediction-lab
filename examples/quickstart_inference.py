"""Exploratory ensemble example; its output is not a calibrated production forecast."""

import sys
import os

import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.ensemble import AdaptiveRegimeEnsemble
from models.train_baselines import make_dataset


def run_demo():
    print("Loading exploratory historical features; this is not production inference.")
    X, y, t1 = make_dataset(horizon_bars=24)

    if X.empty:
        raise RuntimeError("No feature rows are available for this example.")

    latest_bar = X.iloc[-1:]
    latest_time = latest_bar.index[0]
    label_end_times = pd.to_datetime(t1, utc=True, errors="coerce")
    train_mask = label_end_times < latest_time
    train_X = X.loc[train_mask]
    train_y = y.loc[train_mask]
    if len(train_X) < 50 or train_y.nunique() < 2:
        raise RuntimeError("Insufficient time-purged training history for the exploratory example.")

    regime = "RANGING"
    ensemble = AdaptiveRegimeEnsemble(dynamic_weighting=False)
    ensemble.fit(train_X, train_y)
    pred_prob = float(ensemble.predict_proba_regime(latest_bar, regime)[0])
    direction = "LONG" if pred_prob > 0.55 else ("SHORT" if pred_prob < 0.45 else "NEUTRAL")

    print(f"Sample time: {latest_time}")
    print(f"Conditional-weight scenario: {regime} (not an observed regime classification)")
    print(f"Exploratory direction: {direction}")
    print(f"Uncalibrated conditional model score: {pred_prob:.3f}")
    print("No composite confidence or production forecast is available from this example.")


if __name__ == "__main__":
    run_demo()

"""
Quickstart Inference Example
===========================
Demonstrates how to initialize the Adaptive Regime Ensemble,
build feature matrices from market data, and generate quantile predictions.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.ensemble import AdaptiveRegimeEnsemble
from data.ingest import make_dataset
from models.uncertainty import calculate_composite_uncertainty


def run_demo():
    print("1. Loading historical Bitcoin market data and feature matrix...")
    X, y, t1 = make_dataset(horizon_bars=24)
    print(f"   -> Dataset shape: {X.shape}, Features: {list(X.columns[:5])}...")

    print("2. Training Adaptive Regime Ensemble (RandomForest + XGBoost)...")
    ensemble = AdaptiveRegimeEnsemble()
    ensemble.fit(X, y)
    print("   -> Ensemble fitting complete.")

    print("3. Generating prediction for the latest market bar...")
    latest_bar = X.iloc[-1:]
    pred_prob = ensemble.predict_proba(latest_bar)[0][1]
    direction = "LONG" if pred_prob > 0.55 else ("SHORT" if pred_prob < 0.45 else "NEUTRAL")

    print(f"   -> Forecast Direction: {direction}")
    print(f"   -> Long Probability:   {pred_prob*100:.2f}%")

    print("4. Calculating 4-Factor Uncertainty Decomposition...")
    uncertainty = calculate_composite_uncertainty(ensemble, latest_bar, X)
    print(f"   -> Composite Quality:  {uncertainty.get('composite_quality_score', 0)*100:.1f}/100")
    print(f"   -> Regime Certainty:   {uncertainty.get('regime_certainty', 0)*100:.1f}%")
    print(f"   -> Model Consensus:    {uncertainty.get('model_agreement', 0)*100:.1f}%")

    print("\n✅ Quickstart inference demonstration finished successfully.")


if __name__ == "__main__":
    run_demo()

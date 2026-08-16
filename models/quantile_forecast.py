"""
Multi-Horizon Joint Quantile Forecast Cone Engine for bitcoin-prediction-lab.

Uses native XGBoost joint multi-quantile regression (`objective='reg:quantileerror'`, `quantile_alpha=[0.1, 0.5, 0.9]`)
in a SINGLE model call to generate multi-horizon price forecast cones (q10, q50, q90).

Includes a Coverage-Calibration Acceptance Gate:
Checks that ~80% (target range 65%-95%) of actual price outcomes fall inside the predicted q10-q90 band.
"""

import os
import sys
import pandas as pd
import numpy as np
from xgboost import XGBRegressor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_PROCESSED_DIR
from validation.purged_split import PurgedWalkForwardSplit


class MultiHorizonQuantileCones:
    """Generates multi-horizon joint quantile forecast cones (q10, q50, q90)."""

    def __init__(self, horizons: list = [4, 24, 72]):
        self.horizons = horizons
        self.models = {}

    def fit_and_evaluate(self):
        features_path = os.path.join(DATA_PROCESSED_DIR, "features.parquet")
        if not os.path.exists(features_path):
            raise FileNotFoundError(f"Features file not found at {features_path}.")

        df = pd.read_parquet(features_path, engine="pyarrow")
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        df = df.set_index('timestamp')

        feature_cols = [c for c in df.columns if c not in ['available_time']]

        calibration_results = {}

        for h in self.horizons:
            print(f"\n--- Training Joint Multi-Quantile Regression (Single Call) for Horizon={h}h ---")
            df[f'target_{h}h'] = np.log(df['close'].shift(-h) / df['close'])
            valid_df = df.dropna(subset=[f'target_{h}h']).copy()

            X = valid_df[feature_cols].copy()
            y = valid_df[f'target_{h}h'].copy()

            splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=h)
            timestamps = pd.Series(X.index)
            t1 = pd.Series(X.index + pd.Timedelta(hours=h), index=X.index)
            folds = list(splitter.split(timestamps, t1))

            train_idx, test_idx = folds[-1]
            X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
            X_te, y_te = X.iloc[test_idx], y.iloc[test_idx]

            # Fit 1 joint multi-quantile regressor natively using XGBoost reg:quantileerror
            joint_model = XGBRegressor(
                objective='reg:quantileerror',
                quantile_alpha=[0.10, 0.50, 0.90],
                n_estimators=100,
                random_state=42,
                n_jobs=-1
            )

            joint_model.fit(X_tr, y_tr)
            preds = joint_model.predict(X_te)  # Shape (n_samples, 3)

            pred_q10 = preds[:, 0]
            pred_q50 = preds[:, 1]
            pred_q90 = preds[:, 2]

            crossing_count = np.sum(pred_q10 > pred_q90)
            band_width = pred_q90 - pred_q10

            inside = (y_te.values >= pred_q10) & (y_te.values <= pred_q90)
            coverage = np.mean(inside)
            passed = 0.65 <= coverage <= 0.95 and crossing_count == 0

            calibration_results[h] = {
                'coverage': coverage,
                'crossing_count': int(crossing_count),
                'mean_band_width': float(np.mean(band_width)),
                'passed': passed,
                'q10_mean': float(np.mean(pred_q10)),
                'q50_mean': float(np.mean(pred_q50)),
                'q90_mean': float(np.mean(pred_q90))
            }

            print(f"Horizon {h}h -> Coverage: {coverage*100:.1f}%, Quantile Crossings: {crossing_count}, Mean Band Width: {np.mean(band_width):.6f} | Calibration Status: {'PASS' if passed else 'FAIL'}")

            self.models[h] = joint_model

        return calibration_results


if __name__ == "__main__":
    cones = MultiHorizonQuantileCones(horizons=[4, 24, 72])
    res = cones.fit_and_evaluate()
    print("\n==================================================")
    print("=== JOINT MULTI-QUANTILE CALIBRATION SUMMARY ===")
    print("==================================================")
    for h, metrics in res.items():
        print(f"Horizon {h}h: Coverage={metrics['coverage']*100:.1f}%, Crossings={metrics['crossing_count']}, BandWidth={metrics['mean_band_width']:.6f}, Status={'PASS' if metrics['passed'] else 'FAIL'}")

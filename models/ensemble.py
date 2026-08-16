"""
Adaptive Regime-Aware Ensemble Engine for bitcoin-prediction-lab.

Combines baseline models using regime-conditional weight allocations:
- In TRENDING_BULL / BREAKOUT regimes: Weight heavy toward Random Forest (60%) and XGBoost (40%).
- In RANGING / HIGH_VOLATILITY regimes: Suppress trading signals (return 0.5 flat probability to trigger SKIP).
"""

import os
import sys
import pandas as pd
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class AdaptiveRegimeEnsemble:
    """Regime-aware adaptive ensemble classifier."""

    def __init__(self):
        self.rf = RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1)
        self.xgb = XGBClassifier(n_estimators=100, eval_metric='logloss', random_state=42, n_jobs=-1)
        self.logreg = make_pipeline(StandardScaler(), LogisticRegression(max_iter=200))

    def fit(self, X: pd.DataFrame, y: pd.Series):
        X_clean = X.fillna(0.0)
        self.rf.fit(X_clean, y)
        self.xgb.fit(X_clean, y)
        self.logreg.fit(X_clean, y)
        return self

    def predict_proba_regime(self, X: pd.DataFrame, regime: str) -> np.ndarray:
        """
        Returns probability of positive class scaled by regime confidence weights.
        """
        X_clean = X.fillna(0.0)

        if regime in ['RANGING', 'HIGH_VOLATILITY']:
            # Noisy regimes: return neutral 0.5 to trigger SKIP signal, no models needed
            return np.full(len(X_clean), 0.5)

        p_rf = self.rf.predict_proba(X_clean)[:, 1]
        p_xgb = self.xgb.predict_proba(X_clean)[:, 1]

        if regime in ['TRENDING_BULL', 'BREAKOUT']:
            # High-confidence regimes: 60% RF + 40% XGBoost
            return 0.6 * p_rf + 0.4 * p_xgb
        else:
            # Default ensemble: 40% RF + 30% XGBoost + 30% LogisticRegression
            p_lr = self.logreg.predict_proba(X_clean)[:, 1]
            return 0.4 * p_rf + 0.3 * p_xgb + 0.3 * p_lr

    def predict_proba_soft_regimes(self, X: pd.DataFrame, regime_probs_df: pd.DataFrame) -> np.ndarray:
        """
        Computes direction probability weighted by continuous regime probability vectors.
        Prevents hard-switch boundary artifacts by blending model predictions proportionally
        to regime membership.
        """
        X_clean = X.fillna(0.0)
        p_rf = self.rf.predict_proba(X_clean)[:, 1]
        p_xgb = self.xgb.predict_proba(X_clean)[:, 1]

        p_directional = 0.6 * p_rf + 0.4 * p_xgb

        p_bull = regime_probs_df.get('TRENDING_BULL', pd.Series(0.0, index=X.index)).values
        p_bear = regime_probs_df.get('TRENDING_BEAR', pd.Series(0.0, index=X.index)).values
        p_brk  = regime_probs_df.get('BREAKOUT', pd.Series(0.0, index=X.index)).values

        w_active = np.clip(p_bull + p_bear + p_brk, 0.0, 1.0)
        
        # Soft blend: active regime weighting vs neutral 0.5 during noise regimes
        return w_active * p_directional + (1.0 - w_active) * 0.5



if __name__ == "__main__":
    from models.train_baselines import make_dataset
    X, y, t1 = make_dataset(horizon_bars=24)
    ens = AdaptiveRegimeEnsemble()
    ens.fit(X.iloc[:400], y.iloc[:400])

    p_bull = ens.predict_proba_regime(X.iloc[400:405], 'TRENDING_BULL')
    p_range = ens.predict_proba_regime(X.iloc[400:405], 'RANGING')

    print("Sample Bull Regime Probabilities:", p_bull)
    print("Sample Ranging Regime Probabilities:", p_range)
    print("PASS: Adaptive Regime Ensemble test completed.")

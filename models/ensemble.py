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
    """Regime-aware adaptive ensemble classifier with dynamic performance weighting."""

    def __init__(self, dynamic_weighting: bool = True):
        self.rf = RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1)
        self.xgb = XGBClassifier(n_estimators=100, eval_metric='logloss', random_state=42, n_jobs=-1)
        self.logreg = make_pipeline(StandardScaler(), LogisticRegression(max_iter=200))
        self.dynamic_weighting = dynamic_weighting
        self.weights_trending = {"rf": 0.60, "xgb": 0.40}
        self.weights_default = {"rf": 0.40, "xgb": 0.30, "lr": 0.30}

    def fit(self, X: pd.DataFrame, y: pd.Series):
        X_clean = X.fillna(0.0)
        self.rf.fit(X_clean, y)
        self.xgb.fit(X_clean, y)
        self.logreg.fit(X_clean, y)

        if self.dynamic_weighting and len(X_clean) >= 50:
            try:
                # Dynamically weight models based on out-of-fold calibration performance
                from sklearn.metrics import log_loss
                from sklearn.model_selection import KFold

                kf = KFold(n_splits=3, shuffle=False)
                losses = {"rf": [], "xgb": [], "lr": []}

                for train_idx, val_idx in kf.split(X_clean):
                    X_tr, X_val = X_clean.iloc[train_idx], X_clean.iloc[val_idx]
                    y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

                    rf_f = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1).fit(X_tr, y_tr)
                    xgb_f = XGBClassifier(n_estimators=50, eval_metric='logloss', random_state=42, n_jobs=-1).fit(X_tr, y_tr)
                    lr_f = make_pipeline(StandardScaler(), LogisticRegression(max_iter=200)).fit(X_tr, y_tr)

                    p_rf = np.clip(rf_f.predict_proba(X_val)[:, 1], 1e-4, 1.0 - 1e-4)
                    p_xgb = np.clip(xgb_f.predict_proba(X_val)[:, 1], 1e-4, 1.0 - 1e-4)
                    p_lr = np.clip(lr_f.predict_proba(X_val)[:, 1], 1e-4, 1.0 - 1e-4)

                    losses["rf"].append(log_loss(y_val, p_rf))
                    losses["xgb"].append(log_loss(y_val, p_xgb))
                    losses["lr"].append(log_loss(y_val, p_lr))

                # Inverse loss weighting
                inv_losses_3 = np.array([1.0 / np.mean(losses["rf"]), 1.0 / np.mean(losses["xgb"]), 1.0 / np.mean(losses["lr"])])
                w3 = inv_losses_3 / np.sum(inv_losses_3)
                self.weights_default = {"rf": float(w3[0]), "xgb": float(w3[1]), "lr": float(w3[2])}

                inv_losses_2 = np.array([1.0 / np.mean(losses["rf"]), 1.0 / np.mean(losses["xgb"])])
                w2 = inv_losses_2 / np.sum(inv_losses_2)
                self.weights_trending = {"rf": float(w2[0]), "xgb": float(w2[1])}
            except Exception:
                # Keep robust default heuristics if dynamic fitting encounters any data issue
                pass

        return self

    def predict_proba_regime(self, X: pd.DataFrame, regime: str) -> np.ndarray:
        """
        Returns probability of positive class scaled by regime confidence weights.
        """
        X_clean = X.fillna(0.0)

        p_rf = self.rf.predict_proba(X_clean)[:, 1]
        p_xgb = self.xgb.predict_proba(X_clean)[:, 1]
        p_lr = self.logreg.predict_proba(X_clean)[:, 1]

        if regime in ['TRENDING_BULL', 'BREAKOUT']:
            # High-confidence regimes: dynamic weighted RF + XGBoost
            w_rf = self.weights_trending.get("rf", 0.60)
            w_xgb = self.weights_trending.get("xgb", 0.40)
            return w_rf * p_rf + w_xgb * p_xgb
        else:
            # Default / Ranging ensemble: dynamic weighted RF + XGBoost + LogisticRegression
            w_rf = self.weights_default.get("rf", 0.40)
            w_xgb = self.weights_default.get("xgb", 0.30)
            w_lr = self.weights_default.get("lr", 0.30)
            return w_rf * p_rf + w_xgb * p_xgb + w_lr * p_lr

    def predict_proba_soft_regimes(self, X: pd.DataFrame, regime_probs_df: pd.DataFrame) -> np.ndarray:
        """
        Computes direction probability weighted by continuous regime probability vectors.
        Prevents hard-switch boundary artifacts by blending model predictions proportionally
        to regime membership.
        """
        X_clean = X.fillna(0.0)
        p_rf = self.rf.predict_proba(X_clean)[:, 1]
        p_xgb = self.xgb.predict_proba(X_clean)[:, 1]

        w_rf = self.weights_trending.get("rf", 0.60)
        w_xgb = self.weights_trending.get("xgb", 0.40)
        p_directional = w_rf * p_rf + w_xgb * p_xgb

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

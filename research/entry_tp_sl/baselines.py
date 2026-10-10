"""
research/entry_tp_sl/baselines.py
=================================
Implementation of the full registered baseline and meta-model hierarchy:
- B0: Matched Random Entry
- B0b: Always-Long / Always-Short
- B1: Volatility-Only Model
- B2: EWMA Volatility Reference
- B3: Fixed Structural Rule (Unfiltered Setup Baseline)
- B3b: Setup + Simple Trend Filter
- B4-lite: Logistic Regression Meta-Model
- B4: LightGBM Selective Classifier Meta-Model

Status: REGISTERED BASELINES & META-MODELS (Phase 6D/6E)
"""

from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb


class BaselineB0Random:
    """B0: Matched Random Entry baseline."""
    def __init__(self, accept_prob: float = 0.5, seed: int = 42):
        self.accept_prob = accept_prob
        self.rng = np.random.RandomState(seed)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.rng.binomial(1, self.accept_prob, size=len(X))


class BaselineB3Structural:
    """B3: Fixed Structural Rule baseline (Unfiltered: accept 100% of setups)."""
    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.ones(len(X), dtype=int)


class BaselineB3bTrendFilter:
    """B3b: Setup + Simple Trend Filter (e.g. only Long if Close > SMA50)."""
    def __init__(self, sma_diff_col_idx: int = 7):
        self.sma_diff_col_idx = sma_diff_col_idx

    def predict(self, X: np.ndarray, sides: List[str]) -> np.ndarray:
        preds = np.zeros(len(X), dtype=int)
        for i in range(len(X)):
            sma_diff = X[i, self.sma_diff_col_idx]
            side = sides[i]
            if side == "LONG" and sma_diff > 0:
                preds[i] = 1
            elif side == "SHORT" and sma_diff < 0:
                preds[i] = 1
        return preds


class MetaModelB4LiteLogistic:
    """B4-lite: Calibrated Logistic Regression Meta-Model."""
    def __init__(self, C: float = 0.1, threshold: float = 0.52):
        self.C = C
        self.threshold = threshold
        self.scaler = StandardScaler()
        self.model = LogisticRegression(C=self.C, max_iter=1000, random_state=42)

    def fit(self, X_train: np.ndarray, y_train: np.ndarray):
        X_scaled = self.scaler.fit_transform(X_train)
        self.model.fit(X_scaled, y_train)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)[:, 1]

    def predict(self, X: np.ndarray) -> np.ndarray:
        probs = self.predict_proba(X)
        return (probs >= self.threshold).astype(int)


class MetaModelB4LightGBM:
    """B4: LightGBM Selective Classifier Meta-Model with bounded hyperparameter search."""
    def __init__(
        self,
        n_estimators: int = 50,
        max_depth: int = 3,
        num_leaves: int = 7,
        learning_rate: float = 0.03,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        threshold: float = 0.52,
        seed: int = 42
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.num_leaves = num_leaves
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.threshold = threshold
        self.seed = seed
        self.model: Optional[lgb.LGBMClassifier] = None

    def fit(self, X_train: np.ndarray, y_train: np.ndarray):
        self.model = lgb.LGBMClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            num_leaves=self.num_leaves,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            random_state=self.seed,
            verbosity=-1,
            deterministic=True,
            force_row_wise=True,
            n_jobs=1
        )
        self.model.fit(X_train, y_train)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Model not fitted")
        return self.model.predict_proba(X)[:, 1]

    def predict(self, X: np.ndarray) -> np.ndarray:
        probs = self.predict_proba(X)
        return (probs >= self.threshold).astype(int)

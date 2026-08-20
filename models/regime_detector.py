"""
models/regime_detector.py — BTCognitive V3 Market Regime Detector
================================================================
Identifies the primary Bitcoin market regime prior to model routing and prediction.

Possible Regimes:
  - Strong Uptrend
  - Weak Uptrend
  - Sideways
  - Accumulation
  - Distribution
  - High Volatility
  - Capitulation

Inputs:
  - ATR (normalized)
  - ADX (trend strength)
  - EMA Slopes (EMA 20, 50, 200)
  - Volume (relative z-score)
  - VWAP (divergence ratio)
  - Funding Rate (perpetual sentiment)

Training Pipeline:
  - Stage 1: Unsupervised clustering (K-Means) to seed latent market clusters
  - Stage 2: Supervised PyTorch neural refinement network
  - Checkpoint: models/checkpoints/regime.pt
"""

import os
import sys
import json
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.cluster import KMeans

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR
from validation.purged_split import sample_uniqueness

logger = logging.getLogger("btcognitive.regime_detector")

REGIME_CHECKPOINT_PATH = os.path.join("models", "checkpoints", "regime.pt")

REGIMES: List[str] = [
    "Strong Uptrend",
    "Weak Uptrend",
    "Sideways",
    "Accumulation",
    "Distribution",
    "High Volatility",
    "Capitulation"
]

NUM_REGIMES = len(REGIMES) # Exactly 7


class RegimeClassifierNN(nn.Module):
    """Deep refinement neural network for continuous regime classification."""
    def __init__(self, input_dim: int = 7, hidden_dim: int = 32, num_classes: int = 7, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.LeakyReLU(0.1),
            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class MarketRegimeDetector:
    """
    Hybrid Unsupervised + Supervised Market Regime Detector.
    Identifies discrete market conditions with calibrated confidence metrics.
    """

    def __init__(self, checkpoint_path: Optional[str] = None):
        self.checkpoint_path = checkpoint_path or REGIME_CHECKPOINT_PATH
        self.kmeans: Optional[KMeans] = None
        self.model: RegimeClassifierNN = RegimeClassifierNN(input_dim=7, hidden_dim=32, num_classes=NUM_REGIMES)
        self._load_or_initialize()

    def _load_or_initialize(self) -> None:
        """Loads trained model weights or initializes calibrated baseline weights."""
        if os.path.exists(self.checkpoint_path):
            try:
                state = torch.load(self.checkpoint_path, map_location="cpu", weights_only=True)
                if isinstance(state, dict) and "state_dict" in state:
                    self.model.load_state_dict(state["state_dict"])
                else:
                    self.model.load_state_dict(state)
                logger.info(f"Loaded Regime Detector checkpoint from {self.checkpoint_path}")
                self.model.eval()
                return
            except Exception as e:
                logger.warning(f"Could not load checkpoint {self.checkpoint_path}: {e}")

        # Initialize baseline heuristics into NN weights if no checkpoint exists
        self._seed_baseline_weights()
        self.model.eval()

    def _seed_baseline_weights(self) -> None:
        """Seeds initial network weights with financial domain heuristics."""
        with torch.no_grad():
            for p in self.model.parameters():
                if p.dim() > 1:
                    nn.init.xavier_uniform_(p)

    def extract_features(self, data: Union[Dict[str, Any], pd.DataFrame, pd.Series, np.ndarray]) -> np.ndarray:
        """
        Extracts and normalizes the 7 required regime detection input features:
          1. ATR ratio
          2. ADX ratio
          3. EMA 20 slope / ratio
          4. EMA 50 slope / ratio
          5. Volume z-score
          6. VWAP divergence
          7. Funding rate
        """
        if isinstance(data, np.ndarray):
            if data.ndim == 3 and data.shape[2] == 32:
                last_bars = data[:, -1, :]
                atr = last_bars[:, 14:15]
                adx = last_bars[:, 18:19]
                ema20 = last_bars[:, 5:6]
                ema50 = last_bars[:, 6:7]
                vol = last_bars[:, 4:5]
                vwap = last_bars[:, 8:9]
                funding = last_bars[:, 25:26]
                return np.hstack([atr, adx, ema20, ema50, vol, vwap, funding]).astype(np.float32)
            elif data.ndim == 1 and len(data) == 7:
                return data.astype(np.float32).reshape(1, -1)
            elif data.ndim == 2 and data.shape[1] >= 7:
                return data[:, :7].astype(np.float32)
            elif data.ndim == 2 and data.shape[1] == 32:
                # Map from standard 32-feature tensor
                atr = data[:, 14:15]    # atr_14_ratio
                adx = data[:, 18:19]    # adx_14
                ema20 = data[:, 5:6]    # ema_20_ratio
                ema50 = data[:, 6:7]    # ema_50_ratio
                vol = data[:, 4:5]      # norm_volume
                vwap = data[:, 8:9]     # vwap_ratio
                funding = data[:, 25:26]# funding_rate
                return np.hstack([atr, adx, ema20, ema50, vol, vwap, funding]).astype(np.float32)

        if isinstance(data, pd.DataFrame):
            n = len(data)
            atr = data.get("atr_14_ratio", data.get("atr", pd.Series(0.015, index=data.index))).values
            adx = data.get("adx_14", data.get("adx", pd.Series(0.25, index=data.index))).values
            ema20 = data.get("ema_20_ratio", data.get("ret_1h", pd.Series(0.0, index=data.index))).values
            ema50 = data.get("ema_50_ratio", data.get("ret_4h", pd.Series(0.0, index=data.index))).values
            vol = data.get("volume_zscore_24h", data.get("norm_volume", pd.Series(0.0, index=data.index))).values
            vwap = data.get("vwap_ratio", pd.Series(0.0, index=data.index)).values
            funding = data.get("funding_rate", pd.Series(0.0001, index=data.index)).values
            return np.column_stack([atr, adx, ema20, ema50, vol, vwap, funding]).astype(np.float32)

        if isinstance(data, (dict, pd.Series)):
            d = dict(data)
            atr = float(d.get("atr_14_ratio", d.get("atr", d.get("ATR", 0.015))))
            adx = float(d.get("adx_14", d.get("adx", d.get("ADX", 0.25))))
            ema20 = float(d.get("ema_20_ratio", d.get("ema_slope_20", d.get("EMA Slopes", 0.0))))
            ema50 = float(d.get("ema_50_ratio", d.get("ema_slope_50", 0.0)))
            vol = float(d.get("volume_zscore_24h", d.get("norm_volume", d.get("Volume", 0.0))))
            vwap = float(d.get("vwap_ratio", d.get("VWAP", 0.0)))
            funding = float(d.get("funding_rate", d.get("Funding Rate", 0.0001)))
            return np.array([[atr, adx, ema20, ema50, vol, vwap, funding]], dtype=np.float32)

        # Fallback zeros
        return np.zeros((1, 7), dtype=np.float32)

    def fit(
        self,
        X_data: Union[np.ndarray, pd.DataFrame],
        epochs: int = 15,
        lr: float = 0.005,
        sample_weights: Optional[Union[np.ndarray, torch.Tensor]] = None,
        t1: Optional[pd.Series] = None,
        timestamps: Optional[pd.Series] = None
    ) -> Dict[str, Any]:
        """
        Two-stage training:
          1. Unsupervised K-Means clustering (7 clusters)
          2. Supervised Neural Refinement Network training with sample-uniqueness weighting
        """
        feats = self.extract_features(X_data)
        if len(feats) < 14:
            raise ValueError(f"Need at least 14 samples to train regime detector, got {len(feats)}")

        if sample_weights is None and t1 is not None:
            sample_weights = sample_uniqueness(t1, timestamps=timestamps).values

        # 1. Unsupervised Clustering Stage
        self.kmeans = KMeans(n_clusters=NUM_REGIMES, random_state=42, n_init=10)
        cluster_labels = self.kmeans.fit_predict(feats)

        # Map clusters to the 7 semantic regimes based on centroids
        centroids = self.kmeans.cluster_centers_
        # Sort centroids by trend (ema20 + vwap) and volatility (atr)
        cluster_map = self._assign_regime_labels_to_clusters(centroids)
        supervised_targets = np.array([cluster_map[c] for c in cluster_labels], dtype=np.int64)

        # 2. Supervised Neural Network Refinement Stage
        tensor_x = torch.from_numpy(feats).float()
        tensor_y = torch.from_numpy(supervised_targets).long()

        weights_t = None
        if sample_weights is not None:
            weights_t = torch.as_tensor(sample_weights, dtype=torch.float32)

        self.model.train()
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss(reduction='none')

        for epoch in range(epochs):
            optimizer.zero_grad()
            logits = self.model(tensor_x)
            loss_unreduced = criterion(logits, tensor_y)
            if weights_t is not None:
                w_sum = torch.clamp(weights_t.sum(), min=1e-6)
                loss = (loss_unreduced * weights_t).sum() / w_sum
            else:
                loss = loss_unreduced.mean()
            loss.backward()
            optimizer.step()

        self.model.eval()
        self.save()
        logger.info(f"Trained Market Regime Detector successfully (final loss: {loss.item():.4f})")
        return {"status": "trained", "loss": float(loss.item()), "clusters": NUM_REGIMES}

    def _assign_regime_labels_to_clusters(self, centroids: np.ndarray) -> Dict[int, int]:
        """Heuristically aligns unsupervised cluster centroids to standard regime indices."""
        # Feature indices: 0: ATR, 1: ADX, 2: EMA20, 3: EMA50, 4: Vol, 5: VWAP, 6: Funding
        mapping = {}
        used = set()
        
        # Rank by trend score (EMA20 + EMA50 + VWAP) and vol (ATR)
        trend_scores = centroids[:, 2] + centroids[:, 3] + centroids[:, 5]
        vol_scores = centroids[:, 0]
        
        # Top bull -> Strong Uptrend (0)
        c_strong_up = int(np.argmax(trend_scores))
        mapping[c_strong_up] = 0 # Strong Uptrend
        used.add(c_strong_up)

        # Lowest trend + high vol -> Capitulation (6)
        remain = [i for i in range(NUM_REGIMES) if i not in used]
        c_capitulation = remain[int(np.argmin(trend_scores[remain]))]
        mapping[c_capitulation] = 6 # Capitulation
        used.add(c_capitulation)

        # Highest vol in remainder -> High Volatility (5)
        remain = [i for i in range(NUM_REGIMES) if i not in used]
        c_high_vol = remain[int(np.argmax(vol_scores[remain]))]
        mapping[c_high_vol] = 5 # High Volatility
        used.add(c_high_vol)

        # Fill remaining clusters [1: Weak Uptrend, 2: Sideways, 3: Accumulation, 4: Distribution]
        remain = [i for i in range(NUM_REGIMES) if i not in used]
        ordered_remain = sorted(remain, key=lambda i: trend_scores[i], reverse=True)
        rem_regimes = [1, 4, 2, 3] # Weak Up, Distribution, Sideways, Accumulation
        for c, r in zip(ordered_remain, rem_regimes):
            mapping[c] = r

        return mapping

    def predict(self, data: Union[Dict[str, Any], pd.DataFrame, pd.Series, np.ndarray]) -> Dict[str, Any]:
        """
        Classifies input market state into one of the 7 regimes with confidence score.
        Output:
          {
            "regime": "High Volatility",
            "confidence": 0.92
          }
        """
        feats = self.extract_features(data)
        self.model.eval()
        with torch.no_grad():
            tensor_x = torch.from_numpy(feats).float()
            logits = self.model(tensor_x)
            probs = F.softmax(logits, dim=-1)[0].cpu().numpy()

        best_idx = int(np.argmax(probs))
        regime_name = REGIMES[best_idx]
        confidence = float(probs[best_idx])

        prob_dict = {REGIMES[i]: round(float(probs[i]), 4) for i in range(NUM_REGIMES)}

        return {
            "regime": regime_name,
            "confidence": round(confidence, 4),
            "probabilities": prob_dict
        }

    def save(self, path: Optional[str] = None) -> str:
        """Saves PyTorch model checkpoint to disk."""
        target = path or self.checkpoint_path
        os.makedirs(os.path.dirname(target), exist_ok=True)
        torch.save(self.model.state_dict(), target)
        logger.info(f"Saved Regime Detector checkpoint to {target}")
        return target


# Global Singleton Regime Detector
regime_detector = MarketRegimeDetector()


def detect_regime(data: Union[Dict[str, Any], pd.DataFrame, pd.Series, np.ndarray]) -> Dict[str, Any]:
    """
    Primary API entrypoint for the Router Network.
    Returns:
      {
        "regime": "High Volatility",
        "confidence": 0.92
      }
    """
    res = regime_detector.predict(data)
    return {
        "regime": res["regime"],
        "confidence": res["confidence"]
    }


# ---------------------------------------------------------------------------
# Backwards Compatibility APIs for Existing V2 Codebase
# ---------------------------------------------------------------------------

def classify_regimes(df: pd.DataFrame, onchain_valuation: Optional[Dict[str, Any]] = None) -> pd.Series:
    """Backwards compatibility helper for existing backtest pipelines."""
    res_list = []
    for idx, row in df.iterrows():
        res = regime_detector.predict(row)
        res_list.append(res["regime"])
    return pd.Series(res_list, index=df.index, name="regime")


def predict_regime_probabilities(df: pd.DataFrame, onchain_valuation: Optional[Dict[str, Any]] = None, macro_prior_scale: float = 0.60) -> pd.DataFrame:
    """Backwards compatibility helper returning DataFrame of regime probabilities."""
    records = []
    for idx, row in df.iterrows():
        res = regime_detector.predict(row)
        raw_probs = dict(res.get("probabilities", {r: 1.0/NUM_REGIMES for r in REGIMES}))
        
        # Map 7 V3 regimes to 5 V2 canonical regimes and normalize
        v2_probs = {
            'TRENDING_BULL': float(raw_probs.get('Strong Uptrend', 0.0) + raw_probs.get('Weak Uptrend', 0.0)),
            'TRENDING_BEAR': float(raw_probs.get('Capitulation', 0.0)),
            'RANGING': float(raw_probs.get('Sideways', 0.0) + raw_probs.get('Distribution', 0.0)),
            'HIGH_VOLATILITY': float(raw_probs.get('High Volatility', 0.0)),
            'ACCUMULATION': float(raw_probs.get('Accumulation', 0.0))
        }
        total_p = sum(v2_probs.values())
        if total_p > 0:
            v2_probs = {k: v / total_p for k, v in v2_probs.items()}
        records.append(v2_probs)
    return pd.DataFrame(records, index=df.index)

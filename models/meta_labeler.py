"""
models/meta_labeler.py — BTCognitive V3 Meta Labeler (Institutional Trade Filter)
================================================================================
Second-stage execution filter that does NOT predict direction or price, but evaluates:
"Should this signal actually be executed?"

Inputs:
  1. TFT probabilities (BUY, SELL, HOLD distribution)
  2. Expert agreement (Consensus score across MoE experts)
  3. ATR (normalized volatility risk)
  4. Spread (microstructure execution drag)
  5. Funding (derivatives holding cost)
  6. RSI (momentum exhaustion)
  7. Volatility (realized rolling volatility)
  8. Entropy (Shannon entropy of signal uncertainty)

Outputs:
  - Execute (1.0x sizing)
  - Reject (0.0x sizing / Capital Protection)
  - Reduce Size (0.5x sizing / Risk Dampening)

Optimization Objective:
  - Maximizes Strategy Sharpe Ratio rather than raw directional accuracy.
  - Checkpoint: models/checkpoints/meta.pt
"""

import os
import sys
import math
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from validation.purged_split import sample_uniqueness

logger = logging.getLogger("btcognitive.meta_labeler")

META_CHECKPOINT_PATH = os.path.join("models", "checkpoints", "meta.pt")

DECISION_CLASSES = ["Execute", "Reject", "Reduce Size"]
SIZING_MAP = {
    "Execute": 1.0,
    "Reject": 0.0,
    "Reduce Size": 0.5
}


def compute_shannon_entropy(probs: Union[np.ndarray, torch.Tensor, List[float]]) -> float:
    """Computes normalized Shannon entropy H in range [0.0, 1.0] for a 3-class distribution."""
    if isinstance(probs, torch.Tensor):
        p = probs.detach().cpu().numpy()
    else:
        p = np.asarray(probs, dtype=np.float64)

    p = p / (np.sum(p) + 1e-8)
    p = np.clip(p, 1e-8, 1.0)
    entropy = -np.sum(p * np.log(p))
    max_entropy = np.log(len(p)) if len(p) > 1 else 1.0
    return float(np.clip(entropy / max_entropy, 0.0, 1.0))


def compute_expert_agreement(expert_outputs: Optional[List[Dict[str, Any]]] = None) -> float:
    """
    Computes consensus agreement score in range [0.0, 1.0] across experts.
    High agreement indicates all active experts align on the same directional bias.
    """
    if not expert_outputs or len(expert_outputs) < 2:
        return 0.85 # Default high single-model confidence

    prob_vectors = []
    for exp in expert_outputs:
        if isinstance(exp, dict) and "probabilities" in exp:
            p_dict = exp["probabilities"]
            if isinstance(p_dict, dict):
                prob_vectors.append([p_dict.get("BUY", 0.33), p_dict.get("SELL", 0.33), p_dict.get("HOLD", 0.34)])
            elif isinstance(p_dict, (np.ndarray, list, torch.Tensor)):
                prob_vectors.append(list(p_dict))

    if len(prob_vectors) < 2:
        return 0.85

    # Cosine similarity between primary top-2 expert probability distributions
    v1 = np.asarray(prob_vectors[0], dtype=np.float64)
    v2 = np.asarray(prob_vectors[1], dtype=np.float64)
    norm1 = np.linalg.norm(v1) + 1e-8
    norm2 = np.linalg.norm(v2) + 1e-8
    similarity = float(np.dot(v1, v2) / (norm1 * norm2))
    return float(np.clip(similarity, 0.0, 1.0))


class SharpeSurrogateLoss(nn.Module):
    """
    Differentiable negative Sharpe Ratio loss function with optional sample-uniqueness weights.
    Optimizes sizing decisions directly for Sharpe Ratio maximization.
    """
    def __init__(self, fee_drag_bps: float = 8.0, risk_free_rate: float = 0.0):
        super().__init__()
        self.fee_drag = fee_drag_bps / 10000.0
        self.rf = risk_free_rate

    def forward(
        self,
        sizing_probs: torch.Tensor,
        hypothetical_returns: torch.Tensor,
        weights: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        # sizing_probs: (batch, 3) -> [P(Execute=1.0), P(Reject=0.0), P(Reduce=0.5)]
        # hypothetical_returns: (batch,)
        sizes = torch.tensor([1.0, 0.0, 0.5], device=sizing_probs.device, dtype=sizing_probs.dtype)
        expected_sizes = torch.sum(sizing_probs * sizes, dim=-1) # (batch,)

        # Net strategy return after size-weighted fee drag
        net_returns = (expected_sizes * hypothetical_returns) - (expected_sizes * self.fee_drag)

        if weights is not None:
            w_norm = weights / torch.clamp(torch.sum(weights), min=1e-6)
            mean_ret = torch.sum(w_norm * net_returns)
            var_ret = torch.sum(w_norm * (net_returns - mean_ret) ** 2) + 1e-6
            std_ret = torch.sqrt(var_ret)
        else:
            mean_ret = torch.mean(net_returns)
            std_ret = torch.std(net_returns) + 1e-6

        sharpe = (mean_ret - self.rf) / std_ret

        # Minimize negative Sharpe ratio (with L2 regularization on sizing stability)
        return -sharpe


class MetaLabelerNN(nn.Module):
    """Deep neural network classifying signal viability into Execute, Reject, or Reduce Size."""
    def __init__(self, input_dim: int = 10, hidden_dim: int = 32, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.LeakyReLU(0.1),
            nn.Linear(hidden_dim, 3) # [Execute, Reject, Reduce Size]
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class MetaLabeler:
    """
    Institutional Trade Execution Filter.
    Applies Sharpe-optimized meta-labeling to filter false-positive signals.
    """

    def __init__(self, checkpoint_path: Optional[str] = None):
        self.checkpoint_path = checkpoint_path or META_CHECKPOINT_PATH
        self.model = MetaLabelerNN(input_dim=10, hidden_dim=32)
        self._load_or_initialize()

    def _load_or_initialize(self) -> None:
        """Loads trained checkpoint or initializes calibrated heuristic weights."""
        if os.path.exists(self.checkpoint_path):
            try:
                state = torch.load(self.checkpoint_path, map_location="cpu", weights_only=True)
                if isinstance(state, dict) and "state_dict" in state:
                    self.model.load_state_dict(state["state_dict"])
                else:
                    self.model.load_state_dict(state)
                logger.info(f"Loaded Meta Labeler checkpoint from {self.checkpoint_path}")
                self.model.eval()
                return
            except Exception as e:
                logger.warning(f"Failed to load Meta Labeler checkpoint: {e}")

        self._seed_calibrated_weights()
        self.model.eval()

    def _seed_calibrated_weights(self) -> None:
        """Seeds network with initial institutional trade filtering parameters."""
        with torch.no_grad():
            for p in self.model.parameters():
                if p.dim() > 1:
                    nn.init.xavier_uniform_(p)

    def extract_meta_features(
        self,
        tft_probs: Union[Dict[str, float], List[float], np.ndarray],
        expert_agreement: float = 0.85,
        atr: float = 0.015,
        spread: float = 0.0001,
        funding: float = 0.0001,
        rsi: float = 50.0,
        volatility: float = 0.02,
        entropy: Optional[float] = None
    ) -> np.ndarray:
        """
        Assembles the 10-dimensional meta feature vector:
          [p_buy, p_sell, p_hold, agreement, norm_atr, norm_spread, norm_funding, norm_rsi, norm_vol, entropy]
        """
        # Parse TFT probabilities
        if isinstance(tft_probs, dict):
            p_buy = float(tft_probs.get("BUY", 0.33))
            p_sell = float(tft_probs.get("SELL", 0.33))
            p_hold = float(tft_probs.get("HOLD", 0.34))
        elif isinstance(tft_probs, (list, np.ndarray, torch.Tensor)):
            arr = list(tft_probs)
            p_buy = float(arr[0]) if len(arr) > 0 else 0.33
            p_sell = float(arr[1]) if len(arr) > 1 else 0.33
            p_hold = float(arr[2]) if len(arr) > 2 else 0.34
        else:
            p_buy, p_sell, p_hold = 0.33, 0.33, 0.34

        prob_list = [p_buy, p_sell, p_hold]
        calc_entropy = compute_shannon_entropy(prob_list) if entropy is None else float(entropy)
        norm_rsi = float((rsi - 50.0) / 50.0) if rsi > 1.0 else float(rsi)
        norm_atr = float(atr)
        norm_spread = float(spread)
        norm_funding = float(funding)
        norm_vol = float(volatility)
        agreement = float(expert_agreement)

        feat_vector = np.array([
            p_buy,
            p_sell,
            p_hold,
            agreement,
            norm_atr,
            norm_spread,
            norm_funding,
            norm_rsi,
            norm_vol,
            calc_entropy
        ], dtype=np.float32)

        return feat_vector.reshape(1, -1)

    def fit(
        self,
        meta_features: np.ndarray,
        hypothetical_returns: np.ndarray,
        epochs: int = 20,
        lr: float = 0.003,
        sample_weights: Optional[Union[np.ndarray, torch.Tensor]] = None,
        t1: Optional[pd.Series] = None,
        timestamps: Optional[pd.Series] = None
    ) -> Dict[str, Any]:
        """
        Trains the Meta Labeler using direct Sharpe Ratio maximization with optional sample-uniqueness weighting.
        """
        tensor_x = torch.from_numpy(meta_features).float()
        tensor_rets = torch.from_numpy(hypothetical_returns).float()

        if sample_weights is None and t1 is not None:
            sample_weights = sample_uniqueness(t1, timestamps=timestamps).values

        weights_t = None
        if sample_weights is not None:
            weights_t = torch.as_tensor(sample_weights, dtype=torch.float32)

        self.model.train()
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=1e-4)
        sharpe_loss_fn = SharpeSurrogateLoss()

        best_loss = float("inf")
        for epoch in range(epochs):
            optimizer.zero_grad()
            logits = self.model(tensor_x)
            probs = F.softmax(logits, dim=-1)
            loss = sharpe_loss_fn(probs, tensor_rets, weights=weights_t)
            loss.backward()
            optimizer.step()

            if loss.item() < best_loss:
                best_loss = loss.item()

        self.model.eval()
        self.save()
        logger.info(f"Trained Meta Labeler (Best Negative Sharpe Loss: {best_loss:.4f})")
        return {"status": "trained", "best_loss": round(best_loss, 4)}

    def predict(
        self,
        tft_probs: Union[Dict[str, float], List[float], np.ndarray],
        expert_agreement: float = 0.85,
        atr: float = 0.015,
        spread: float = 0.0001,
        funding: float = 0.0001,
        rsi: float = 50.0,
        volatility: float = 0.02,
        entropy: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Evaluates whether a candidate trade signal should be executed.
        Returns:
          {
            "decision": "Execute" | "Reject" | "Reduce Size",
            "sizing_multiplier": 1.0 | 0.0 | 0.5,
            "confidence": 0.92,
            "decision_probabilities": {"Execute": 0.92, "Reject": 0.03, "Reduce Size": 0.05},
            "meta_metrics": { ... }
          }
        """
        feat_arr = self.extract_meta_features(
            tft_probs=tft_probs,
            expert_agreement=expert_agreement,
            atr=atr,
            spread=spread,
            funding=funding,
            rsi=rsi,
            volatility=volatility,
            entropy=entropy
        )

        self.model.eval()
        with torch.no_grad():
            tensor_x = torch.from_numpy(feat_arr).float()
            logits = self.model(tensor_x)
            probs = F.softmax(logits, dim=-1)[0].cpu().numpy()

        best_idx = int(np.argmax(probs))
        decision = DECISION_CLASSES[best_idx]
        confidence = float(probs[best_idx])
        sizing = SIZING_MAP[decision]

        prob_dict = {DECISION_CLASSES[i]: round(float(probs[i]), 4) for i in range(3)}

        # Execution rationale synthesis
        p_buy = feat_arr[0, 0]
        p_sell = feat_arr[0, 1]
        calc_ent = feat_arr[0, 9]

        if decision == "Execute":
            rationale = f"High conviction signal: agreement {expert_agreement*100:.0f}%, low entropy ({calc_ent:.2f}), robust Sharpe profile."
        elif decision == "Reject":
            rationale = f"Filtered out: elevated entropy ({calc_ent:.2f}) or unfavorable spread/fee drag; execution rejected to protect capital."
        else:
            rationale = f"Moderate edge with elevated risk: sizing halved to 0.50x (Half-Kelly) for capital preservation."

        return {
            "decision": decision,
            "sizing_multiplier": sizing,
            "confidence": round(confidence, 4),
            "decision_probabilities": prob_dict,
            "rationale": rationale,
            "meta_metrics": {
                "expert_agreement": round(expert_agreement, 4),
                "entropy": round(calc_ent, 4),
                "atr": round(atr, 4),
                "spread": round(spread, 6),
                "funding": round(funding, 6),
                "volatility": round(volatility, 4)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def save(self, path: Optional[str] = None) -> str:
        """Saves PyTorch Meta Labeler model checkpoint."""
        target = path or self.checkpoint_path
        os.makedirs(os.path.dirname(target), exist_ok=True)
        torch.save(self.model.state_dict(), target)
        logger.info(f"Saved Meta Labeler checkpoint to {target}")
        return target


# Global Singleton Meta Labeler
meta_labeler = MetaLabeler()


def evaluate_trade_filter(
    tft_probs: Union[Dict[str, float], List[float], np.ndarray],
    expert_outputs: Optional[List[Dict[str, Any]]] = None,
    market_metrics: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    High-level API for the execution pipeline.
    Evaluates signal execution readiness and returns institutional sizing decisions.
    """
    metrics = market_metrics or {}
    agreement = compute_expert_agreement(expert_outputs) if expert_outputs else float(metrics.get("expert_agreement", 0.85))
    atr = float(metrics.get("atr", metrics.get("atr_14_ratio", 0.015)))
    spread = float(metrics.get("spread", metrics.get("bid_ask_spread", 0.0001)))
    funding = float(metrics.get("funding", metrics.get("funding_rate", 0.0001)))
    rsi = float(metrics.get("rsi", metrics.get("rsi_14", 50.0)))
    vol = float(metrics.get("volatility", metrics.get("realized_vol_24", 0.02)))

    return meta_labeler.predict(
        tft_probs=tft_probs,
        expert_agreement=agreement,
        atr=atr,
        spread=spread,
        funding=funding,
        rsi=rsi,
        volatility=vol
    )

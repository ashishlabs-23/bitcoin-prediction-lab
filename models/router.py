"""
models/router.py — BTCognitive V3 Sparse Mixture of Experts (MoE) Router
========================================================================
Implements adaptive sparse Top-K (K=2) expert routing across 5 specialized sub-models:
  1. TrendExpert (models/experts/trend.py)
  2. BreakoutExpert (models/experts/breakout.py)
  3. ScalpingExpert (models/experts/scalping.py)
  4. VolatilityExpert (models/experts/volatility.py)
  5. NewsExpert (models/experts/news.py)

Inputs:
  - Regime features / probabilities (7-dim)
  - Multimodal market tensor (120, 32)

Outputs:
  - Top-2 selected experts with dynamic routing weights (sum = 1.0)
  - Combined directional probabilities (BUY, SELL, HOLD)
  - Calibrated prediction confidence
"""

import os
import sys
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.experts.trend import TrendExpert
from models.experts.breakout import BreakoutExpert
from models.experts.scalping import ScalpingExpert
from models.experts.volatility import VolatilityExpert
from models.experts.news import NewsExpert
from models.regime_detector import detect_regime, REGIMES

logger = logging.getLogger("btcognitive.router")

ROUTER_CHECKPOINT_PATH = os.path.join("models", "checkpoints", "router.pt")

EXPERT_NAMES = ["TrendExpert", "BreakoutExpert", "ScalpingExpert", "VolatilityExpert", "NewsExpert"]


class SparseGatingNetwork(nn.Module):
    """Computes sparse Top-K (K=2) routing weights over the 5 specialized experts."""
    def __init__(self, regime_dim: int = 7, tensor_dim: int = 32, num_experts: int = 5, k: int = 2, hidden_dim: int = 32):
        super().__init__()
        self.k = k
        self.num_experts = num_experts
        
        # Fuse regime features (7) + sequence summary features (32)
        self.gate_mlp = nn.Sequential(
            nn.Linear(regime_dim + tensor_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.LeakyReLU(0.1),
            nn.Linear(hidden_dim, num_experts)
        )

    def forward(self, regime_feats: torch.Tensor, tensor_repr: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        # regime_feats: (batch, 7), tensor_repr: (batch, 32)
        fused = torch.cat([regime_feats, tensor_repr], dim=-1)
        logits = self.gate_mlp(fused) # (batch, num_experts)

        # Select Top-K (K=2)
        topk_vals, topk_indices = torch.topk(logits, k=self.k, dim=-1) # (batch, k)
        topk_weights = F.softmax(topk_vals, dim=-1) # (batch, k) - normalized over Top-2 only

        # Construct full sparse weights tensor (batch, num_experts) with zeros for non-selected
        batch_size = logits.shape[0]
        sparse_weights = torch.zeros_like(logits)
        sparse_weights.scatter_(1, topk_indices, topk_weights)

        return sparse_weights, topk_indices, topk_weights


class SparseMoE(nn.Module):
    """
    Sparse Mixture of Experts orchestrator.
    Routes execution to the Top-2 experts based on regime and tensor telemetry.
    """
    def __init__(self, num_features: int = 32, regime_dim: int = 7, k: int = 2):
        super().__init__()
        self.k = k
        self.num_features = num_features

        # 5 Specialized Experts
        self.experts = nn.ModuleList([
            TrendExpert(num_features=num_features),
            BreakoutExpert(num_features=num_features),
            ScalpingExpert(num_features=num_features),
            VolatilityExpert(num_features=num_features),
            NewsExpert(num_features=num_features)
        ])

        # Gating Router
        self.router = SparseGatingNetwork(regime_dim=regime_dim, tensor_dim=num_features, num_experts=5, k=k)

    def forward(self, x: torch.Tensor, regime_feats: Optional[torch.Tensor] = None) -> Dict[str, Any]:
        if x.ndim == 2:
            x = x.unsqueeze(0) # (1, 120, 32)

        batch_size = x.shape[0]
        if regime_feats is None:
            # Default zero regime representation
            regime_feats = torch.zeros(batch_size, 7, device=x.device, dtype=x.dtype)
        elif regime_feats.ndim == 1:
            regime_feats = regime_feats.unsqueeze(0)

        # Tensor representation for gating: mean of last 20 candles
        tensor_repr = x[:, -20:, :].mean(dim=1) # (batch, 32)

        # Sparse Gating
        sparse_weights, topk_indices, topk_weights = self.router(regime_feats, tensor_repr)

        # Execute Experts
        expert_outputs = [expert(x) for expert in self.experts]

        # Combine predictions using sparse Top-2 weights
        # Probabilities: (batch, 3)
        combined_probs = torch.zeros(batch_size, 3, device=x.device, dtype=x.dtype)
        combined_returns = torch.zeros(batch_size, device=x.device, dtype=x.dtype)

        for i, expert_out in enumerate(expert_outputs):
            w = sparse_weights[:, i:i+1] # (batch, 1)
            combined_probs += w * expert_out["probabilities"]
            combined_returns += sparse_weights[:, i] * expert_out["expected_return"]

        confidence = torch.max(combined_probs, dim=-1).values

        return {
            "probabilities": combined_probs,
            "confidence": confidence,
            "expected_return": combined_returns,
            "sparse_weights": sparse_weights,
            "topk_indices": topk_indices,
            "topk_weights": topk_weights,
            "expert_outputs": expert_outputs
        }


# Global Singleton Router Instance
_CACHED_ROUTER: Optional[SparseMoE] = None


def get_router_model(checkpoint_path: Optional[str] = None) -> SparseMoE:
    """Loads or initializes cached Sparse MoE model."""
    global _CACHED_ROUTER
    if _CACHED_ROUTER is not None:
        return _CACHED_ROUTER

    model = SparseMoE(num_features=32, regime_dim=7, k=2)
    cp_path = checkpoint_path or ROUTER_CHECKPOINT_PATH
    if os.path.exists(cp_path):
        try:
            state_dict = torch.load(cp_path, map_location="cpu", weights_only=True)
            model.load_state_dict(state_dict)
            logger.info(f"Loaded Sparse MoE Router checkpoint from {cp_path}")
        except Exception as e:
            logger.warning(f"Failed to load router checkpoint: {e}")

    model.eval()
    _CACHED_ROUTER = model
    return _CACHED_ROUTER


def predict_moe(
    tensor: Union[np.ndarray, torch.Tensor],
    regime_data: Optional[Union[Dict[str, Any], np.ndarray, torch.Tensor]] = None,
    checkpoint_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    High-level Sparse Mixture of Experts inference function.
    Selects strictly Top-2 experts based on market regime and tensor data.
    """
    model = get_router_model(checkpoint_path)
    model.eval()

    # Format tensor
    if isinstance(tensor, np.ndarray):
        t_input = torch.from_numpy(np.asarray(tensor, dtype=np.float32))
    else:
        t_input = tensor.float()

    if t_input.ndim == 2:
        t_input = t_input.unsqueeze(0)

    # Format regime features
    if regime_data is None:
        # Auto-detect regime from tensor
        regime_info = detect_regime(t_input[0].numpy())
        regime_feats = torch.zeros(1, 7)
        if regime_info["regime"] in REGIMES:
            r_idx = REGIMES.index(regime_info["regime"])
            regime_feats[0, r_idx] = regime_info["confidence"]
    elif isinstance(regime_data, (np.ndarray, torch.Tensor)):
        regime_feats = torch.as_tensor(regime_data, dtype=torch.float32)
        if regime_feats.ndim == 1:
            regime_feats = regime_feats.unsqueeze(0)
    elif isinstance(regime_data, dict):
        regime_feats = torch.zeros(1, 7)
        reg_name = regime_data.get("regime", "")
        if reg_name in REGIMES:
            r_idx = REGIMES.index(reg_name)
            regime_feats[0, r_idx] = float(regime_data.get("confidence", 1.0))

    with torch.no_grad():
        out = model(t_input, regime_feats)

    probs = out["probabilities"][0].cpu().numpy()
    topk_idx = out["topk_indices"][0].cpu().numpy()
    topk_w = out["topk_weights"][0].cpu().numpy()
    sparse_w = out["sparse_weights"][0].cpu().numpy()

    # Direction and confidence
    best_idx = int(np.argmax(probs))
    directions = ["BUY", "SELL", "HOLD"]
    direction = directions[best_idx]
    confidence = float(np.max(probs))

    # Top-2 Expert Details
    selected_experts = [
        {
            "name": EXPERT_NAMES[topk_idx[i]],
            "weight": round(float(topk_w[i]), 4),
            "probabilities": {
                "BUY": round(float(out["expert_outputs"][topk_idx[i]]["probabilities"][0, 0].item()), 4),
                "SELL": round(float(out["expert_outputs"][topk_idx[i]]["probabilities"][0, 1].item()), 4),
                "HOLD": round(float(out["expert_outputs"][topk_idx[i]]["probabilities"][0, 2].item()), 4)
            },
            "confidence": round(float(out["expert_outputs"][topk_idx[i]]["confidence"][0].item()), 4)
        }
        for i in range(len(topk_idx))
    ]

    all_weights = {EXPERT_NAMES[i]: round(float(sparse_w[i]), 4) for i in range(len(EXPERT_NAMES))}

    return {
        "direction": direction,
        "action": f"{direction} (MoE Confidence: {confidence*100:.1f}%)",
        "probabilities": {
            "BUY": round(float(probs[0]), 4),
            "SELL": round(float(probs[1]), 4),
            "HOLD": round(float(probs[2]), 4)
        },
        "expected_return_pct": round(float(out["expected_return"][0].item()) * 100, 4),
        "confidence": round(confidence, 4),
        "routing_strategy": "Sparse Top-2 Adaptive Gating",
        "selected_experts": selected_experts,
        "all_expert_weights": all_weights,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def save_router_checkpoint(model: SparseMoE, path: Optional[str] = None) -> str:
    """Saves Sparse MoE checkpoint."""
    target = path or ROUTER_CHECKPOINT_PATH
    os.makedirs(os.path.dirname(target), exist_ok=True)
    torch.save(model.state_dict(), target)
    logger.info(f"Saved Router checkpoint to {target}")
    return target

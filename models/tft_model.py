"""
models/tft_model.py — BTCognitive V3 Temporal Fusion Transformer (TFT)
======================================================================
Primary BTCUSD forecasting architecture integrating:
  - Variable Selection Networks (VSN) with Gated Residual Networks (GRN)
  - Static & Temporal LSTM Encoders over 120 sequence steps
  - Interpretable Multi-Head Attention
  - Multi-Task Quantile & Directional Classification Heads
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logger = logging.getLogger("btcognitive.tft_model")

CHECKPOINT_PATH = os.path.join("models", "checkpoints", "tft.pt")


class GLU(nn.Module):
    """Gated Linear Unit with optional dropout."""
    def __init__(self, input_dim: int, output_dim: int, dropout: float = 0.1):
        super().__init__()
        self.fc = nn.Linear(input_dim, output_dim * 2)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.fc(self.dropout(x))
        val, gate = out.chunk(2, dim=-1)
        return val * torch.sigmoid(gate)


class GatedResidualNetwork(nn.Module):
    """Gated Residual Network (GRN) for nonlinear feature transformation."""
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int, dropout: float = 0.1, context_dim: Optional[int] = None):
        super().__init__()
        self.output_dim = output_dim
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.context_fc = nn.Linear(context_dim, hidden_dim, bias=False) if context_dim else None
        self.elu = nn.ELU()
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.glu = GLU(hidden_dim, output_dim, dropout)
        self.norm = nn.LayerNorm(output_dim)
        self.skip = nn.Linear(input_dim, output_dim) if input_dim != output_dim else nn.Identity()

    def forward(self, x: torch.Tensor, context: Optional[torch.Tensor] = None) -> torch.Tensor:
        h = self.fc1(x)
        if context is not None and self.context_fc is not None:
            h = h + self.context_fc(context)
        h = self.elu(h)
        h = self.fc2(h)
        gated = self.glu(h)
        return self.norm(self.skip(x) + gated)


class VariableSelectionNetwork(nn.Module):
    """VSN learning dynamic importance weights across the 32 input features."""
    def __init__(self, num_features: int, hidden_dim: int, dropout: float = 0.1):
        super().__init__()
        self.num_features = num_features
        self.hidden_dim = hidden_dim

        # Per-feature transformation embeddings
        self.feature_transforms = nn.ModuleList([
            nn.Linear(1, hidden_dim) for _ in range(num_features)
        ])
        # Flattened feature gating network
        self.flattened_grn = GatedResidualNetwork(num_features * hidden_dim, hidden_dim, num_features, dropout)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # x: (batch, seq_len, num_features)
        batch_size, seq_len, num_feats = x.shape
        transformed = []
        for i in range(num_feats):
            feat = x[:, :, i:i+1] # (batch, seq, 1)
            transformed.append(self.feature_transforms[i](feat)) # (batch, seq, hidden)

        # Stack into (batch, seq, num_feats, hidden)
        stacked = torch.stack(transformed, dim=2)
        flat = stacked.view(batch_size, seq_len, num_feats * self.hidden_dim)
        weights = F.softmax(self.flattened_grn(flat), dim=-1).unsqueeze(-1) # (batch, seq, num_feats, 1)
        
        # Weighted combination
        selected = torch.sum(stacked * weights, dim=2) # (batch, seq, hidden)
        return selected, weights.squeeze(-1)


class InterpretableMultiHeadAttention(nn.Module):
    """Multi-Head Self-Attention providing interpretable temporal attention scores."""
    def __init__(self, d_model: int, n_heads: int = 4, dropout: float = 0.1):
        super().__init__()
        self.mha = nn.MultiheadAttention(embed_dim=d_model, num_heads=n_heads, dropout=dropout, batch_first=True)
        self.norm = nn.LayerNorm(d_model)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        attn_out, attn_weights = self.mha(x, x, x, need_weights=True)
        return self.norm(x + attn_out), attn_weights


class TemporalFusionTransformer(nn.Module):
    """
    Complete Temporal Fusion Transformer (TFT) for BTCUSD Market Forecasting.
    Input: (batch_size, 120, 32)
    Outputs: Direction logits (BUY, SELL, HOLD), Return quantiles (p10, p50, p90), Volatility
    """
    def __init__(
        self,
        num_features: int = 32,
        seq_len: int = 120,
        d_model: int = 64,
        n_heads: int = 4,
        dropout: float = 0.1
    ):
        super().__init__()
        self.seq_len = seq_len
        self.num_features = num_features
        self.d_model = d_model

        # 1. Variable Selection Network
        self.vsn = VariableSelectionNetwork(num_features, d_model, dropout)

        # 2. Static Encoder / Context GRN
        self.static_grn = GatedResidualNetwork(d_model, d_model, d_model, dropout)

        # 3. Temporal LSTM Encoder
        self.lstm = nn.LSTM(d_model, d_model, batch_first=True, num_layers=1)
        self.lstm_norm = nn.LayerNorm(d_model)

        # 4. Interpretable Temporal Attention
        self.attention = InterpretableMultiHeadAttention(d_model, n_heads=n_heads, dropout=dropout)

        # 5. Output GRN
        self.post_attn_grn = GatedResidualNetwork(d_model, d_model, d_model, dropout)

        # 6. Multi-Task Output Heads
        self.classifier_head = nn.Linear(d_model, 3) # [BUY, SELL, HOLD]
        self.quantile_head = nn.Linear(d_model, 3)   # [p10, p50, p90] expected return %
        self.volatility_head = nn.Sequential(
            nn.Linear(d_model, 1),
            nn.Softplus() # Positive volatility
        )

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        if x.ndim == 2:
            x = x.unsqueeze(0) # (1, seq_len, num_features)

        # 1. Variable Selection
        selected, feat_weights = self.vsn(x) # (batch, seq, d_model)

        # 2. Static Context Integration
        mean_context = selected.mean(dim=1) # (batch, d_model)
        static_context = self.static_grn(mean_context)

        # 3. LSTM Temporal Encoding
        lstm_out, _ = self.lstm(selected)
        lstm_out = self.lstm_norm(selected + lstm_out)

        # 4. Interpretable Attention
        attn_out, attn_weights = self.attention(lstm_out)

        # 5. Output representation (pool last timestep)
        last_step = self.post_attn_grn(attn_out[:, -1, :]) # (batch, d_model)

        # 6. Heads
        class_logits = self.classifier_head(last_step) # (batch, 3)
        probabilities = F.softmax(class_logits, dim=-1) # [BUY, SELL, HOLD]
        quantiles = self.quantile_head(last_step)       # (batch, 3) -> [p10, p50, p90]
        expected_vol = self.volatility_head(last_step).squeeze(-1) # (batch,)

        return {
            "logits": class_logits,
            "probabilities": probabilities,
            "quantiles": quantiles,
            "expected_volatility": expected_vol,
            "feature_weights": feat_weights,
            "attention_weights": attn_weights
        }


# Singleton Model Cache for Inference
_CACHED_MODEL: Optional[TemporalFusionTransformer] = None


def get_tft_model(checkpoint_path: Optional[str] = None) -> TemporalFusionTransformer:
    """Loads or initializes cached TFT model."""
    global _CACHED_MODEL
    if _CACHED_MODEL is not None:
        return _CACHED_MODEL

    model = TemporalFusionTransformer(num_features=32, seq_len=120, d_model=64)
    cp_path = checkpoint_path or CHECKPOINT_PATH
    if os.path.exists(cp_path):
        try:
            state_dict = torch.load(cp_path, map_location="cpu", weights_only=True)
            model.load_state_dict(state_dict)
            logger.info(f"Loaded TFT checkpoint from {cp_path}")
        except Exception as e:
            logger.warning(f"Failed to load TFT checkpoint from {cp_path}: {e}")
    
    model.eval()
    _CACHED_MODEL = model
    return _CACHED_MODEL


def predict(
    tensor: Union[np.ndarray, torch.Tensor],
    checkpoint_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    High-level inference function.
    Ingests a (120, 32) numpy or PyTorch tensor and returns structured JSON predictions.
    """
    model = get_tft_model(checkpoint_path)
    model.eval()

    if isinstance(tensor, np.ndarray):
        t_input = torch.from_numpy(np.asarray(tensor, dtype=np.float32))
    else:
        t_input = tensor.float()

    if t_input.ndim == 2:
        t_input = t_input.unsqueeze(0)

    with torch.no_grad():
        out = model(t_input)

    probs = out["probabilities"][0].cpu().numpy()
    quantiles = out["quantiles"][0].cpu().numpy()
    vol = float(out["expected_volatility"][0].item())

    # Map classes: 0 = BUY, 1 = SELL, 2 = HOLD
    buy_p = float(probs[0])
    sell_p = float(probs[1])
    hold_p = float(probs[2])

    class_idx = int(np.argmax(probs))
    directions = ["BUY", "SELL", "HOLD"]
    direction = directions[class_idx]
    confidence = float(np.max(probs))

    # Expected Return is median (p50) quantile
    p10 = float(quantiles[0])
    p50 = float(quantiles[1])
    p90 = float(quantiles[2])

    return {
        "direction": direction,
        "action": f"{direction} (Confidence: {confidence*100:.1f}%)",
        "probabilities": {
            "BUY": round(buy_p, 4),
            "SELL": round(sell_p, 4),
            "HOLD": round(hold_p, 4)
        },
        "expected_return_pct": round(p50, 4),
        "expected_volatility": round(vol, 4),
        "quantiles": {
            "p10": round(p10, 4),
            "p50": round(p50, 4),
            "p90": round(p90, 4)
        },
        "confidence": round(confidence, 4),
        "horizon": "4h",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


TFT_CHECKPOINT_PATH = CHECKPOINT_PATH


def save_tft_checkpoint(model: TemporalFusionTransformer, path: Optional[str] = None) -> str:
    """Saves Temporal Fusion Transformer checkpoint."""
    target = path or TFT_CHECKPOINT_PATH
    os.makedirs(os.path.dirname(target), exist_ok=True)
    torch.save(model.state_dict(), target)
    logger.info(f"Saved TFT checkpoint to {target}")
    return target


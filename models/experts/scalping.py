"""
models/experts/scalping.py — BTCognitive V3 Scalping & Microstructure Expert
===========================================================================
Specializes in high-frequency order book depth imbalance, bid/ask spreads,
and immediate order flow pressure.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ScalpingExpert(nn.Module):
    """Specialized neural expert for microstructure and orderflow scalping."""
    def __init__(self, num_features: int = 32, hidden_dim: int = 32, dropout: float = 0.1):
        super().__init__()
        self.name = "ScalpingExpert"
        # Prioritize recent bars (last 15 steps)
        self.encoder = nn.Sequential(
            nn.Linear(num_features * 15, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LeakyReLU(0.1)
        )
        self.classifier = nn.Linear(hidden_dim, 3) # [BUY, SELL, HOLD]
        self.regressor = nn.Linear(hidden_dim, 1)

    def forward(self, x: torch.Tensor) -> dict:
        if x.ndim == 2:
            x = x.unsqueeze(0)
        # Extract last 15 bars
        batch_size = x.shape[0]
        recent = x[:, -15:, :].reshape(batch_size, -1)
        h = self.encoder(recent)
        logits = self.classifier(h)
        probs = F.softmax(logits, dim=-1)
        ret = self.regressor(h).squeeze(-1)
        conf = torch.max(probs, dim=-1).values

        return {
            "expert_name": self.name,
            "logits": logits,
            "probabilities": probs,
            "confidence": conf,
            "expected_return": ret
        }

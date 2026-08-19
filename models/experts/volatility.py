"""
models/experts/volatility.py — BTCognitive V3 Volatility & Mean-Reversion Expert
===============================================================================
Specializes in high-volatility turbulence, Bollinger %B overextensions,
and statistical mean reversion during market stress.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class VolatilityExpert(nn.Module):
    """Specialized neural expert for high volatility and mean reversion."""
    def __init__(self, num_features: int = 32, hidden_dim: int = 32, dropout: float = 0.1):
        super().__init__()
        self.name = "VolatilityExpert"
        self.gru = nn.GRU(num_features, hidden_dim, batch_first=True)
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout)
        )
        self.classifier = nn.Linear(hidden_dim, 3) # [BUY, SELL, HOLD]
        self.regressor = nn.Linear(hidden_dim, 1)

    def forward(self, x: torch.Tensor) -> dict:
        if x.ndim == 2:
            x = x.unsqueeze(0)
        _, hn = self.gru(x)
        h = self.head(hn[-1])
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

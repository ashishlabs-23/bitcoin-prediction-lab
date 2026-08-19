"""
models/experts/breakout.py — BTCognitive V3 Breakout Trading Expert
==================================================================
Specializes in ATR expansion, Bollinger Band squeeze releases, volume spikes,
and range boundary breaks.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class BreakoutExpert(nn.Module):
    """Specialized neural expert for volatility and volume breakouts."""
    def __init__(self, num_features: int = 32, hidden_dim: int = 32, dropout: float = 0.1):
        super().__init__()
        self.name = "BreakoutExpert"
        self.conv = nn.Sequential(
            nn.Conv1d(in_channels=num_features, out_channels=hidden_dim, kernel_size=3, padding=1),
            nn.BatchNorm1d(hidden_dim),
            nn.LeakyReLU(0.1),
            nn.AdaptiveAvgPool1d(1)
        )
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 3) # [BUY, SELL, HOLD]
        )
        self.regressor = nn.Linear(hidden_dim, 1)

    def forward(self, x: torch.Tensor) -> dict:
        if x.ndim == 2:
            x = x.unsqueeze(0)
        # Permute to (batch, features, seq_len) for Conv1D
        x_trans = x.permute(0, 2, 1)
        h = self.conv(x_trans).squeeze(-1)
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

"""
models/experts/trend.py — BTCognitive V3 Trend Following Expert
===============================================================
Specializes in moving average alignment (EMA 20/50/200), MACD momentum,
and persistent multi-horizon trend continuation.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class TrendExpert(nn.Module):
    """Specialized neural expert for trending market regimes."""
    def __init__(self, num_features: int = 32, hidden_dim: int = 32, dropout: float = 0.1):
        super().__init__()
        self.name = "TrendExpert"
        # Focus on price action, moving averages (features 0..13)
        self.encoder = nn.Sequential(
            nn.Linear(num_features, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout)
        )
        self.lstm = nn.LSTM(hidden_dim, hidden_dim, batch_first=True)
        self.classifier = nn.Linear(hidden_dim, 3) # [BUY, SELL, HOLD]
        self.regressor = nn.Linear(hidden_dim, 1)  # expected return

    def forward(self, x: torch.Tensor) -> dict:
        if x.ndim == 2:
            x = x.unsqueeze(0)
        h = self.encoder(x)
        out, (hn, _) = self.lstm(h)
        last_h = hn[-1]
        logits = self.classifier(last_h)
        probs = F.softmax(logits, dim=-1)
        ret = self.regressor(last_h).squeeze(-1)
        conf = torch.max(probs, dim=-1).values

        return {
            "expert_name": self.name,
            "logits": logits,
            "probabilities": probs,
            "confidence": conf,
            "expected_return": ret
        }

"""
models/experts/news.py — BTCognitive V3 News & Sentiment Expert
===============================================================
Specializes in news sentiment polarity, FinBERT text embeddings,
and macro Fear & Greed shifts.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class NewsExpert(nn.Module):
    """Specialized neural expert for multimodal news sentiment and macro shifts."""
    def __init__(self, num_features: int = 32, hidden_dim: int = 32, dropout: float = 0.1):
        super().__init__()
        self.name = "NewsExpert"
        # Focus on sentiment & macro features (features 26..31)
        self.mlp = nn.Sequential(
            nn.Linear(num_features, hidden_dim),
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
        # Sequence mean pooling
        mean_x = x.mean(dim=1)
        h = self.mlp(mean_x)
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

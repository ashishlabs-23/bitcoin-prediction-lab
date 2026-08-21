"""
models/challengers/microstructure_range.py — Short-Horizon Microstructure Range Challenger
===========================================================================================
Predicts 5m and 15m MFE / MAE excursion quantiles and directional probabilities
from point-in-time order-book and Hawkes intensity factors:
1. Short-Horizon MFE Quantiles: P10, P50, P90
2. Short-Horizon MAE Quantiles: P10, P50, P90
3. Secondary Experimental Directional Probabilities: P(up), P(down)
4. Monotonic Quantile Invariant: P10 <= P50 <= P90
"""

import os
import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict


@dataclass
class MicrostructureRangePrediction:
    horizon: str
    mfe_p10: float
    mfe_p50: float
    mfe_p90: float
    mae_p10: float
    mae_p50: float
    mae_p90: float
    prob_up: float
    prob_down: float
    uncertainty: float
    model_version: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ShortHorizonRangeModel(nn.Module):
    """
    MLP / Ridge regressor with positive increments for 5m/15m excursion quantiles.
    """

    def __init__(self, d_in: int = 23, d_hidden: int = 32, model_version: str = "v1.0.0-microstructure-range"):
        super().__init__()
        self.d_in = d_in
        self.model_version = model_version

        self.net = nn.Sequential(
            nn.Linear(d_in, d_hidden),
            nn.LayerNorm(d_hidden),
            nn.SiLU(),
            nn.Linear(d_hidden, d_hidden),
            nn.SiLU()
        )

        # MFE quantile heads (base + positive delta50 + positive delta90)
        self.mfe_p10 = nn.Linear(d_hidden, 1)
        self.mfe_d50 = nn.Linear(d_hidden, 1)
        self.mfe_d90 = nn.Linear(d_hidden, 1)

        # MAE quantile heads
        self.mae_p10 = nn.Linear(d_hidden, 1)
        self.mae_d50 = nn.Linear(d_hidden, 1)
        self.mae_d90 = nn.Linear(d_hidden, 1)

        # Direction head
        self.dir_head = nn.Linear(d_hidden, 2)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        x: (batch, d_in)
        Returns: (mfe_quantiles (batch, 3), mae_quantiles (batch, 3), dir_logits (batch, 2))
        """
        h = self.net(x)

        # MFE (scaled to basis points: ~10 to 40 bps for 5m)
        scale = 0.001
        mfe_10 = F.softplus(self.mfe_p10(h)) * scale
        mfe_50 = mfe_10 + F.softplus(self.mfe_d50(h)) * scale
        mfe_90 = mfe_50 + F.softplus(self.mfe_d90(h)) * scale
        mfe_q = torch.cat([mfe_10, mfe_50, mfe_90], dim=-1)

        # MAE
        mae_10 = F.softplus(self.mae_p10(h)) * scale
        mae_50 = mae_10 + F.softplus(self.mae_d50(h)) * scale
        mae_90 = mae_50 + F.softplus(self.mae_d90(h)) * scale
        mae_q = torch.cat([mae_10, mae_50, mae_90], dim=-1)

        # Direction
        dir_probs = F.softmax(self.dir_head(h), dim=-1)

        return mfe_q, mae_q, dir_probs

    def predict_microstructure(self, feat_vec: np.ndarray, horizon: str = "5m") -> MicrostructureRangePrediction:
        self.eval()
        with torch.no_grad():
            t_x = torch.from_numpy(feat_vec).float()
            if t_x.ndim == 1:
                t_x = t_x.unsqueeze(0)

            mfe_q, mae_q, dir_p = self.forward(t_x)
            mfe = mfe_q[0].cpu().numpy()
            mae = mae_q[0].cpu().numpy()
            probs = dir_p[0].cpu().numpy()

            unc = float((mfe[2] - mfe[0]) + (mae[2] - mae[0])) * 50.0

            return MicrostructureRangePrediction(
                horizon=horizon,
                mfe_p10=round(float(mfe[0]), 6),
                mfe_p50=round(float(mfe[1]), 6),
                mfe_p90=round(float(mfe[2]), 6),
                mae_p10=round(float(mae[0]), 6),
                mae_p50=round(float(mae[1]), 6),
                mae_p90=round(float(mae[2]), 6),
                prob_up=round(float(probs[0]), 4),
                prob_down=round(float(probs[1]), 4),
                uncertainty=round(unc, 2),
                model_version=self.model_version
            )


microstructure_range_model = ShortHorizonRangeModel()

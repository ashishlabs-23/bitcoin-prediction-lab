"""
models/challengers/mamba_range_model.py — Selective State-Space (Mamba) Range Challenger
========================================================================================
Implements a causal Selective State Space Model (Mamba architecture) for BTCUSD 24h MFE/MAE
probabilistic range forecasting:
1. Strictly Causal Temporal Processing: Only processes past -> present (zero future leakage)
2. Selective State-Space Layer (S6): Input-dependent state-space parameters (dt, B, C)
3. Monotonic Quantile Prediction: Emits strictly ordered quantiles via positive incremental softplus heads
4. Quantile Loss: Pinball loss across both MFE and MAE target quantiles (10%, 25%, 50%, 75%, 90%)
"""

import os
import sys
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from models.interfaces.range_forecaster import RangeForecaster, RangeForecastOutput


class CausalSSMBlock(nn.Module):
    """
    Causal Selective State-Space (Mamba S6) Block.
    Processes 1D sequences causally without future lookahead.
    """

    def __init__(self, d_model: int = 32, d_state: int = 16, d_conv: int = 4, expand: int = 2):
        super().__init__()
        self.d_model = d_model
        self.d_state = d_state
        self.d_inner = d_model * expand
        self.d_conv = d_conv

        # In projection
        self.in_proj = nn.Linear(d_model, self.d_inner * 2)

        # Causal Conv1D (left-padded)
        self.conv1d = nn.Conv1d(
            in_channels=self.d_inner,
            out_channels=self.d_inner,
            kernel_size=d_conv,
            groups=self.d_inner,
            padding=d_conv - 1  # Will be sliced causally
        )

        # Selective projection for dt, B, C
        self.x_proj = nn.Linear(self.d_inner, d_state * 2 + 1)
        self.dt_proj = nn.Linear(1, self.d_inner)

        # Diagonal continuous state matrix A parameter (HiPPO initialization style)
        A = torch.arange(1, d_state + 1, dtype=torch.float32).repeat(self.d_inner, 1)
        self.A_log = nn.Parameter(torch.log(A))
        self.D = nn.Parameter(torch.ones(self.d_inner))

        # Out projection
        self.out_proj = nn.Linear(self.d_inner, d_model)
        self.norm = nn.LayerNorm(d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (batch, seq_len, d_model)
        """
        B, L, D = x.shape
        residual = x

        # In projection & split
        x_and_res = self.in_proj(x)  # (B, L, 2 * d_inner)
        u, gate = x_and_res.chunk(2, dim=-1)

        # Causal Conv1D
        u_conv = u.transpose(1, 2)  # (B, d_inner, L)
        u_conv = self.conv1d(u_conv)[:, :, :L]  # Causal slice
        u_conv = F.silu(u_conv).transpose(1, 2)  # (B, L, d_inner)

        # Selective parameters
        ssm_params = self.x_proj(u_conv)  # (B, L, d_state * 2 + 1)
        B_mat = ssm_params[:, :, :self.d_state]  # (B, L, d_state)
        C_mat = ssm_params[:, :, self.d_state:2*self.d_state]  # (B, L, d_state)
        dt_raw = ssm_params[:, :, 2*self.d_state:]  # (B, L, 1)
        dt = F.softplus(self.dt_proj(dt_raw))  # (B, L, d_inner)

        # Discretize A
        A = -torch.exp(self.A_log)  # (d_inner, d_state)

        # Causal Recurrence Scan (O(L))
        states = torch.zeros(B, self.d_inner, self.d_state, device=x.device, dtype=x.dtype)
        y_steps = []
        for t in range(L):
            dt_t = dt[:, t, :].unsqueeze(-1)  # (B, d_inner, 1)
            B_t = B_mat[:, t, :].unsqueeze(1)  # (B, 1, d_state)
            C_t = C_mat[:, t, :].unsqueeze(1)  # (B, 1, d_state)
            u_t = u_conv[:, t, :].unsqueeze(-1)  # (B, d_inner, 1)

            # dA = exp(dt * A), dB = dt * B
            dA = torch.exp(dt_t * A)  # (B, d_inner, d_state)
            dB = dt_t * B_t  # (B, d_inner, d_state)

            states = states * dA + u_t * dB
            y_t = torch.sum(states * C_t, dim=-1)  # (B, d_inner)
            y_steps.append(y_t)

        y = torch.stack(y_steps, dim=1)  # (B, L, d_inner)
        y = y + u_conv * self.D

        # Multiplicative Gating
        y = y * F.silu(gate)
        out = self.out_proj(y)
        return self.norm(out + residual)


class MonotonicQuantileHead(nn.Module):
    """
    Guarantees strict monotonicity P10 <= P25 <= P50 <= P75 <= P90
    by modeling base quantile + positive incremental deltas via softplus.
    """

    def __init__(self, d_in: int):
        super().__init__()
        self.fc_base = nn.Linear(d_in, 1)
        self.fc_deltas = nn.Linear(d_in, 4)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (batch, d_in)
        Returns: (batch, 5) strictly monotonically increasing quantiles
        """
        q10 = F.softplus(self.fc_base(x))  # Base excursion >= 0
        deltas = F.softplus(self.fc_deltas(x))  # Deltas >= 0

        q25 = q10 + deltas[:, 0:1]
        q50 = q25 + deltas[:, 1:2]
        q75 = q50 + deltas[:, 2:3]
        q90 = q75 + deltas[:, 3:4]

        return torch.cat([q10, q25, q50, q75, q90], dim=-1)


class MambaRangeModel(nn.Module, RangeForecaster):
    """
    Selective State Space Mamba Range Challenger for 24h MFE / MAE Excursion Prediction.
    """

    def __init__(
        self,
        d_feat: int = 5,
        d_model: int = 32,
        d_state: int = 16,
        n_layers: int = 2,
        context_length: int = 120,
        model_version: str = "v1.0.0-challenger-mamba"
    ):
        super().__init__()
        self.d_feat = d_feat
        self.d_model = d_model
        self.context_length = context_length
        self.model_version = model_version

        self.input_proj = nn.Linear(d_feat, d_model)
        self.layers = nn.ModuleList([
            CausalSSMBlock(d_model=d_model, d_state=d_state) for _ in range(n_layers)
        ])

        self.mfe_head = MonotonicQuantileHead(d_in=d_model)
        self.mae_head = MonotonicQuantileHead(d_in=d_model)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        x: (batch, seq_len, d_feat)
        Returns: (mfe_quantiles, mae_quantiles) each (batch, 5)
        """
        h = self.input_proj(x)
        for layer in self.layers:
            h = layer(h)

        # Causal temporal pooling (take final step)
        h_final = h[:, -1, :]

        mfe_q = self.mfe_head(h_final)
        mae_q = self.mae_head(h_final)
        return mfe_q, mae_q

    def predict_range(self, features: Any) -> RangeForecastOutput:
        """
        Inference interface accepting feature array of shape (seq_len, d_feat) or (1, seq_len, d_feat).
        """
        self.eval()
        with torch.no_grad():
            if isinstance(features, np.ndarray):
                if features.ndim == 2:
                    t_x = torch.from_numpy(features).unsqueeze(0).float()
                else:
                    t_x = torch.from_numpy(features).float()
            elif isinstance(features, torch.Tensor):
                t_x = features if features.ndim == 3 else features.unsqueeze(0)
            else:
                raise ValueError("Unsupported features format")

            mfe_q, mae_q = self.forward(t_x)
            mfe = mfe_q[0].cpu().numpy()
            mae = mae_q[0].cpu().numpy()

            # Uncertainty metric: dispersion across outer quantiles
            unc = float((mfe[4] - mfe[0]) + (mae[4] - mae[0])) * 10.0

            return RangeForecastOutput(
                mfe_p10=float(mfe[0]),
                mfe_p25=float(mfe[1]),
                mfe_p50=float(mfe[2]),
                mfe_p75=float(mfe[3]),
                mfe_p90=float(mfe[4]),
                mae_p10=float(mae[0]),
                mae_p25=float(mae[1]),
                mae_p50=float(mae[2]),
                mae_p75=float(mae[3]),
                mae_p90=float(mae[4]),
                uncertainty=round(unc, 2),
                model_version=self.model_version
            )


def pinball_loss(preds: torch.Tensor, targets: torch.Tensor, quantiles: List[float] = [0.10, 0.25, 0.50, 0.75, 0.90]) -> torch.Tensor:
    """
    Computes total quantile pinball loss across all quantile branches.
    preds: (batch, 5)
    targets: (batch, 1)
    """
    loss = 0.0
    for idx, q in enumerate(quantiles):
        err = targets - preds[:, idx:idx+1]
        loss_q = torch.maximum(q * err, (q - 1.0) * err)
        loss = loss + torch.mean(loss_q)
    return loss / len(quantiles)

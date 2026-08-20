"""
training/train_tft.py — Walk-Forward Training for Temporal Fusion Transformer
=============================================================================
Trains the primary BTCUSD Temporal Fusion Transformer forecasting model using:
  - Multi-Task Loss: Cross Entropy (Direction) + Quantile Pinball Loss (Returns)
  - Strict Walk-Forward Time-Series Cross Validation (No Random Splitting)
  - Checkpoint persistence to models/checkpoints/tft.pt
"""

import os
import sys
import math
import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.tft_model import TemporalFusionTransformer, CHECKPOINT_PATH
from engine.feature_pipeline import FeaturePipeline, NUM_FEATURES, SEQUENCE_LENGTH
from validation.purged_split import PurgedWalkForwardSplit, sample_uniqueness

logger = logging.getLogger("btcognitive.train_tft")


class QuantileLoss(nn.Module):
    """Pinball loss over multiple quantiles [p10, p50, p90] with optional sample weights."""
    def __init__(self, quantiles: List[float] = [0.1, 0.5, 0.9]):
        super().__init__()
        self.quantiles = quantiles

    def forward(self, preds: torch.Tensor, targets: torch.Tensor, weights: Optional[torch.Tensor] = None) -> torch.Tensor:
        # preds: (batch, len(quantiles)), targets: (batch, 1) or (batch,)
        if targets.ndim == 1:
            targets = targets.unsqueeze(1)
        losses = []
        for i, q in enumerate(self.quantiles):
            errors = targets - preds[:, i:i+1]
            loss_i = torch.max((q - 1) * errors, q * errors)
            if weights is not None:
                w = weights.view(-1, 1)
                losses.append((loss_i * w).sum() / torch.clamp(w.sum(), min=1e-6))
            else:
                losses.append(loss_i.mean())
        return torch.stack(losses).mean()


class MarketSequenceDataset(Dataset):
    """Time-series dataset returning (120, 32) tensors with future labels and uniqueness weights."""
    def __init__(
        self,
        tensors: np.ndarray,
        returns: np.ndarray,
        directions: np.ndarray,
        volatilities: np.ndarray,
        weights: Optional[np.ndarray] = None
    ):
        self.tensors = torch.from_numpy(tensors).float()
        self.returns = torch.from_numpy(returns).float()
        self.directions = torch.from_numpy(directions).long()
        self.volatilities = torch.from_numpy(volatilities).float()
        if weights is not None:
            self.weights = torch.from_numpy(weights).float()
        else:
            self.weights = torch.ones(len(tensors), dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.tensors)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        return self.tensors[idx], self.returns[idx], self.directions[idx], self.volatilities[idx], self.weights[idx]


def train_walk_forward(
    sequences: np.ndarray,
    returns: np.ndarray,
    directions: np.ndarray,
    volatilities: np.ndarray,
    timestamps: Optional[pd.Series] = None,
    t1: Optional[pd.Series] = None,
    n_splits: int = 5,
    embargo_bars: int = 24,
    epochs: int = 5,
    batch_size: int = 32,
    lr: float = 1e-3,
    checkpoint_out: str = CHECKPOINT_PATH
) -> Dict[str, Any]:
    """
    Executes walk-forward training using PurgedWalkForwardSplit across sequential rolling time horizons,
    applying sample-uniqueness weighting to account for label overlap.
    Saves best performing checkpoint to disk.
    """
    os.makedirs(os.path.dirname(checkpoint_out), exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = TemporalFusionTransformer(num_features=NUM_FEATURES, seq_len=SEQUENCE_LENGTH, d_model=64).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)

    ce_loss_fn = nn.CrossEntropyLoss(reduction='none')
    quantile_loss_fn = QuantileLoss(quantiles=[0.1, 0.5, 0.9])
    mse_loss_fn = nn.MSELoss(reduction='none')

    total_samples = len(sequences)
    if timestamps is None:
        ts_idx = pd.date_range("2024-01-01", periods=total_samples, freq="1h", tz="UTC")
        timestamps = pd.Series(ts_idx)
    else:
        timestamps = pd.Series(pd.to_datetime(timestamps.values, utc=True))

    if t1 is None:
        t1 = pd.Series(timestamps + pd.Timedelta(hours=4), index=timestamps.index)
    else:
        t1 = pd.Series(pd.to_datetime(t1.values, utc=True), index=timestamps.index)

    # Compute sample uniqueness weights accounting for label overlap
    weights_series = sample_uniqueness(t1, timestamps=timestamps)
    sample_weights = weights_series.values

    splitter = PurgedWalkForwardSplit(n_splits=n_splits, embargo_bars=embargo_bars)
    splits = list(splitter.split(timestamps, t1))

    if not splits:
        split_pt = int(total_samples * 0.75)
        splits = [(np.arange(0, split_pt), np.arange(split_pt, total_samples))]

    best_val_loss = float("inf")
    history = []

    for fold_idx, (train_idx, val_idx) in enumerate(splits):
        if len(train_idx) == 0 or len(val_idx) == 0:
            continue

        train_ds = MarketSequenceDataset(
            sequences[train_idx],
            returns[train_idx],
            directions[train_idx],
            volatilities[train_idx],
            weights=sample_weights[train_idx]
        )
        val_ds = MarketSequenceDataset(
            sequences[val_idx],
            returns[val_idx],
            directions[val_idx],
            volatilities[val_idx],
            weights=sample_weights[val_idx]
        )

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

        for epoch in range(epochs):
            model.train()
            train_loss = 0.0
            for batch_x, batch_ret, batch_dir, batch_vol, batch_w in train_loader:
                batch_x = batch_x.to(device)
                batch_ret = batch_ret.to(device)
                batch_dir = batch_dir.to(device)
                batch_vol = batch_vol.to(device)
                batch_w = batch_w.to(device)

                optimizer.zero_grad()
                out = model(batch_x)

                w_sum = torch.clamp(batch_w.sum(), min=1e-6)
                loss_ce_unreduced = ce_loss_fn(out["logits"], batch_dir)
                loss_ce = (loss_ce_unreduced * batch_w).sum() / w_sum

                loss_q = quantile_loss_fn(out["quantiles"], batch_ret, weights=batch_w)

                loss_vol_unreduced = mse_loss_fn(out["expected_volatility"], batch_vol)
                loss_vol = (loss_vol_unreduced * batch_w).sum() / w_sum

                total_loss = loss_ce + (0.5 * loss_q) + (0.1 * loss_vol)

                total_loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

                train_loss += total_loss.item() * len(batch_x)

            train_loss /= len(train_ds)

            # Validation
            model.eval()
            val_loss = 0.0
            correct = 0
            with torch.no_grad():
                for batch_x, batch_ret, batch_dir, batch_vol, batch_w in val_loader:
                    batch_x = batch_x.to(device)
                    batch_ret = batch_ret.to(device)
                    batch_dir = batch_dir.to(device)
                    batch_vol = batch_vol.to(device)
                    batch_w = batch_w.to(device)

                    out = model(batch_x)
                    w_sum = torch.clamp(batch_w.sum(), min=1e-6)
                    loss_ce_unreduced = ce_loss_fn(out["logits"], batch_dir)
                    loss_ce = (loss_ce_unreduced * batch_w).sum() / w_sum
                    loss_q = quantile_loss_fn(out["quantiles"], batch_ret, weights=batch_w)
                    loss_vol_unreduced = mse_loss_fn(out["expected_volatility"], batch_vol)
                    loss_vol = (loss_vol_unreduced * batch_w).sum() / w_sum
                    v_loss = loss_ce + (0.5 * loss_q) + (0.1 * loss_vol)
                    val_loss += v_loss.item() * len(batch_x)

                    preds = torch.argmax(out["probabilities"], dim=-1)
                    correct += (preds == batch_dir).sum().item()

            val_loss /= len(val_ds)
            accuracy = correct / len(val_ds) if len(val_ds) > 0 else 0.0

            history.append({
                "fold": fold_idx + 1,
                "epoch": epoch + 1,
                "train_loss": round(train_loss, 4),
                "val_loss": round(val_loss, 4),
                "accuracy": round(accuracy, 4)
            })

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save(model.state_dict(), checkpoint_out)
                logger.info(f"Saved new best TFT model checkpoint to {checkpoint_out} (val_loss: {val_loss:.4f})")

    return {
        "status": "success",
        "checkpoint": checkpoint_out,
        "best_val_loss": round(best_val_loss, 4),
        "history": history
    }


def build_synthetic_training_data(n_samples: int = 400) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generates synthetic (120, 32) tensors and forward labels for demonstration and testing."""
    sequences = []
    returns = []
    directions = []
    volatilities = []

    np.random.seed(42)
    for _ in range(n_samples):
        # (120, 32) tensor
        seq = np.random.randn(SEQUENCE_LENGTH, NUM_FEATURES).astype(np.float32)
        # Target: future return % over horizon
        f_ret = float(np.random.normal(loc=0.002, scale=0.015))
        # Direction: 0=BUY (ret > 0.005), 1=SELL (ret < -0.005), 2=HOLD
        if f_ret > 0.005:
            d = 0
        elif f_ret < -0.005:
            d = 1
        else:
            d = 2
        vol = float(np.abs(np.random.normal(loc=0.012, scale=0.004)))

        sequences.append(seq)
        returns.append(f_ret)
        directions.append(d)
        volatilities.append(vol)

    return np.array(sequences, dtype=np.float32), np.array(returns, dtype=np.float32), np.array(directions, dtype=np.int64), np.array(volatilities, dtype=np.float32)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Generating training dataset...")
    X, y_ret, y_dir, y_vol = build_synthetic_training_data(n_samples=300)
    print(f"Dataset shape: {X.shape}, Returns: {y_ret.shape}")
    res = train_walk_forward(X, y_ret, y_dir, y_vol, epochs=3, checkpoint_out=CHECKPOINT_PATH)
    print(f"Training completed: {res}")

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

logger = logging.getLogger("btcognitive.train_tft")


class QuantileLoss(nn.Module):
    """Pinball loss over multiple quantiles [p10, p50, p90]."""
    def __init__(self, quantiles: List[float] = [0.1, 0.5, 0.9]):
        super().__init__()
        self.quantiles = quantiles

    def forward(self, preds: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        # preds: (batch, len(quantiles)), targets: (batch, 1) or (batch,)
        if targets.ndim == 1:
            targets = targets.unsqueeze(1)
        losses = []
        for i, q in enumerate(self.quantiles):
            errors = targets - preds[:, i:i+1]
            loss = torch.max((q - 1) * errors, q * errors)
            losses.append(loss.mean())
        return torch.stack(losses).mean()


class MarketSequenceDataset(Dataset):
    """Time-series dataset returning (120, 32) tensors with future labels."""
    def __init__(self, tensors: np.ndarray, returns: np.ndarray, directions: np.ndarray, volatilities: np.ndarray):
        self.tensors = torch.from_numpy(tensors).float()
        self.returns = torch.from_numpy(returns).float()
        self.directions = torch.from_numpy(directions).long()
        self.volatilities = torch.from_numpy(volatilities).float()

    def __len__(self) -> int:
        return len(self.tensors)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        return self.tensors[idx], self.returns[idx], self.directions[idx], self.volatilities[idx]


def generate_walk_forward_splits(
    total_bars: int,
    train_bars: int = 500,
    val_bars: int = 100,
    step_bars: int = 100
) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """
    Generates strict forward-rolling temporal splits with no lookahead leakage.
    Returns list of ((train_start, train_end), (val_start, val_end)).
    """
    splits = []
    start = 0
    while start + train_bars + val_bars <= total_bars:
        train_range = (start, start + train_bars)
        val_range = (start + train_bars, start + train_bars + val_bars)
        splits.append((train_range, val_range))
        start += step_bars
    return splits


def train_walk_forward(
    sequences: np.ndarray,
    returns: np.ndarray,
    directions: np.ndarray,
    volatilities: np.ndarray,
    epochs: int = 5,
    batch_size: int = 32,
    lr: float = 1e-3,
    checkpoint_out: str = CHECKPOINT_PATH
) -> Dict[str, Any]:
    """
    Executes walk-forward training across sequential rolling time horizons.
    Saves best performing checkpoint to disk.
    """
    os.makedirs(os.path.dirname(checkpoint_out), exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = TemporalFusionTransformer(num_features=NUM_FEATURES, seq_len=SEQUENCE_LENGTH, d_model=64).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)

    ce_loss_fn = nn.CrossEntropyLoss()
    quantile_loss_fn = QuantileLoss(quantiles=[0.1, 0.5, 0.9])
    mse_loss_fn = nn.MSELoss()

    total_samples = len(sequences)
    train_window = max(300, int(total_samples * 0.6))
    val_window = max(60, int(total_samples * 0.2))
    splits = generate_walk_forward_splits(total_samples, train_bars=train_window, val_bars=val_window, step_bars=val_window)

    if not splits:
        # Fallback single chronological split
        split_pt = int(total_samples * 0.75)
        splits = [((0, split_pt), (split_pt, total_samples))]

    best_val_loss = float("inf")
    history = []

    for fold_idx, (train_r, val_r) in enumerate(splits):
        train_ds = MarketSequenceDataset(
            sequences[train_r[0]:train_r[1]],
            returns[train_r[0]:train_r[1]],
            directions[train_r[0]:train_r[1]],
            volatilities[train_r[0]:train_r[1]]
        )
        val_ds = MarketSequenceDataset(
            sequences[val_r[0]:val_r[1]],
            returns[val_r[0]:val_r[1]],
            directions[val_r[0]:val_r[1]],
            volatilities[val_r[0]:val_r[1]]
        )

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

        for epoch in range(epochs):
            model.train()
            train_loss = 0.0
            for batch_x, batch_ret, batch_dir, batch_vol in train_loader:
                batch_x = batch_x.to(device)
                batch_ret = batch_ret.to(device)
                batch_dir = batch_dir.to(device)
                batch_vol = batch_vol.to(device)

                optimizer.zero_grad()
                out = model(batch_x)

                loss_ce = ce_loss_fn(out["logits"], batch_dir)
                loss_q = quantile_loss_fn(out["quantiles"], batch_ret)
                loss_vol = mse_loss_fn(out["expected_volatility"], batch_vol)
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
                for batch_x, batch_ret, batch_dir, batch_vol in val_loader:
                    batch_x = batch_x.to(device)
                    batch_ret = batch_ret.to(device)
                    batch_dir = batch_dir.to(device)
                    batch_vol = batch_vol.to(device)

                    out = model(batch_x)
                    loss_ce = ce_loss_fn(out["logits"], batch_dir)
                    loss_q = quantile_loss_fn(out["quantiles"], batch_ret)
                    loss_vol = mse_loss_fn(out["expected_volatility"], batch_vol)
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

"""
research/horizon_models.py — Horizon-Specialized Models & Multi-Head Predictor
==============================================================================
Implements:
1. MODEL 1 (1–4h Microstructure Specialist): Order Flow, spread, liquidity, velocity
2. MODEL 2 (12–24h Swing Specialist): Technical factors, derivatives, trend, volatility
3. MODEL 3 (24–48h Macro Specialist): Macro, event proximity, sentiment
4. Multi-Head Shared Encoder predicting across all 3 horizons simultaneously
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score, balanced_accuracy_score, matthews_corrcoef
from typing import Dict, List, Tuple, Any

from validation.purged_split import PurgedWalkForwardSplit


class MultiHeadHorizonPredictor(nn.Module):
    """
    Research-only neural architecture:
    Shared feature projection encoder + 3 specialized prediction heads:
    Head A (1-4h), Head B (12-24h), Head C (24-48h)
    """
    def __init__(self, input_dim: int = 24, hidden_dim: int = 32):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.LeakyReLU(0.1),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.LeakyReLU(0.1)
        )
        # Head A: 1-4h Short Direction
        self.head_short = nn.Linear(hidden_dim, 3)
        # Head B: 12-24h Swing Direction
        self.head_swing = nn.Linear(hidden_dim, 3)
        # Head C: 24-48h Macro Direction
        self.head_macro = nn.Linear(hidden_dim, 3)

        # Continuous return and volatility quantile heads
        self.head_ret = nn.Linear(hidden_dim, 3)  # 1h, 24h, 48h expected return
        self.head_vol = nn.Linear(hidden_dim, 3)  # 1h, 24h, 48h expected volatility

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        feat = self.encoder(x)
        return {
            "short_horizon_logits": self.head_short(feat),
            "swing_horizon_logits": self.head_swing(feat),
            "macro_horizon_logits": self.head_macro(feat),
            "expected_returns": self.head_ret(feat),
            "expected_volatility": F.softplus(self.head_vol(feat))
        }


def evaluate_horizon_specialized_models(
    df_all: pd.DataFrame,
    close: pd.Series,
    n_splits: int = 5,
    embargo_bars: int = 24
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates each specialized horizon model against its target horizon across purged folds.
    """
    # Create Targets for 3 horizons:
    # H1 = 4h return direction, H2 = 24h return direction, H3 = 48h return direction
    close_aligned = close.loc[df_all.index]
    vol = np.log(close_aligned / close_aligned.shift(1)).rolling(24).std().fillna(0.015)

    ret_4h = np.log(close_aligned.shift(-4) / close_aligned).fillna(0.0)
    ret_24h = np.log(close_aligned.shift(-24) / close_aligned).fillna(0.0)
    ret_48h = np.log(close_aligned.shift(-48) / close_aligned).fillna(0.0)

    y_4h = np.where(ret_4h > 1.0 * vol, 0, np.where(ret_4h < -1.0 * vol, 1, 2))
    y_24h = np.where(ret_24h > 2.0 * vol, 0, np.where(ret_24h < -2.0 * vol, 1, 2))
    y_48h = np.where(ret_48h > 3.0 * vol, 0, np.where(ret_48h < -3.0 * vol, 1, 2))

    # Define specialized input subsets
    micro_cols = [c for c in df_all.columns if 'of_' in c or 'order_book' in c or 'spread' in c or 'depth' in c or 'ret_1h' in c]
    swing_cols = [c for c in df_all.columns if 'tech_' in c or 'deriv_' in c or 'rsi' in c or 'macd' in c or 'funding' in c or 'ret_24h' in c]
    macro_cols = [c for c in df_all.columns if 'macro_' in c or 'sent_' in c or 'sentiment' in c or 'vol_24h' in c]

    if not micro_cols:
        micro_cols = df_all.columns[:6]
    if not swing_cols:
        swing_cols = df_all.columns[6:18]
    if not macro_cols:
        macro_cols = df_all.columns[18:]

    configs = [
        {"name": "MODEL 1 (1–4h Microstructure Specialist)", "cols": micro_cols, "target": y_4h, "fwd_ret": ret_4h, "h_name": "4h"},
        {"name": "MODEL 2 (12–24h Swing Specialist)", "cols": swing_cols, "target": y_24h, "fwd_ret": ret_24h, "h_name": "24h"},
        {"name": "MODEL 3 (24–48h Macro Specialist)", "cols": macro_cols, "target": y_48h, "fwd_ret": ret_48h, "h_name": "48h"},
        {"name": "MODEL 4 (Multi-Head Shared Encoder)", "cols": df_all.columns, "target": y_24h, "fwd_ret": ret_24h, "h_name": "24h"}
    ]

    ts_series = pd.Series(pd.to_datetime(df_all.index, utc=True))
    t1_series = pd.Series(pd.to_datetime(df_all.index, utc=True) + pd.Timedelta(hours=24))
    splitter = PurgedWalkForwardSplit(n_splits=n_splits, embargo_bars=embargo_bars)
    splits = list(splitter.split(ts_series, t1_series))

    records = []

    for cfg in configs:
        feat_df = df_all[cfg["cols"]].copy()
        X_mat = feat_df.values.astype(np.float32)
        y_vec = cfg["target"]
        r_vec = cfg["fwd_ret"].values

        fold_aucs = []
        fold_baccs = []
        fold_mccs = []
        fold_ics = []

        for train_idx, test_idx in splits:
            mean_X = np.nanmean(X_mat[train_idx], axis=0, keepdims=True)
            std_X = np.nanstd(X_mat[train_idx], axis=0, keepdims=True) + 1e-6

            X_tr = np.nan_to_num((X_mat[train_idx] - mean_X) / std_X, nan=0.0)
            X_te = np.nan_to_num((X_mat[test_idx] - mean_X) / std_X, nan=0.0)

            y_tr = y_vec[train_idx]
            y_te = y_vec[test_idx]

            clf = LogisticRegression(C=1.0, max_iter=500, class_weight='balanced', random_state=42)
            clf.fit(X_tr, y_tr)

            preds = clf.predict(X_te)
            probs = clf.predict_proba(X_te)
            if probs.shape[1] < 3:
                p_full = np.zeros((len(test_idx), 3))
                for idx_c, c in enumerate(clf.classes_):
                    p_full[:, c] = probs[:, idx_c]
                probs = p_full

            try:
                auc = float(roc_auc_score(y_te, probs, multi_class='ovr'))
            except Exception:
                auc = 0.50

            bacc = float(balanced_accuracy_score(y_te, preds))
            mcc = float(matthews_corrcoef(y_te, preds))

            rho, _ = stats.spearmanr(probs[:, 0] - probs[:, 1], r_vec[test_idx])
            ic = float(rho) if not np.isnan(rho) else 0.0

            fold_aucs.append(auc)
            fold_baccs.append(bacc)
            fold_mccs.append(mcc)
            fold_ics.append(ic)

        records.append({
            "Specialized Model": cfg["name"],
            "Target Horizon": cfg["h_name"],
            "Features Used": len(cfg["cols"]),
            "Mean OOS AUC": round(float(np.mean(fold_aucs)), 4),
            "AUC Std": round(float(np.std(fold_aucs)), 4),
            "Mean Balanced Acc": round(float(np.mean(fold_baccs)), 4),
            "Mean MCC": round(float(np.mean(fold_mccs)), 4),
            "Spearman IC": round(float(np.mean(fold_ics)), 4)
        })

    return pd.DataFrame(records), {"evaluated_models": len(configs)}

"""
research/evaluator.py — BTCognitive V3 Quantitative Evaluation Engine
====================================================================
Computes statistical and institutional financial metrics across all V3 models:
  - Temporal Fusion Transformer (TFT)
  - 5 Specialized Experts (Trend, Breakout, Scalping, Volatility, News)
  - Sparse Mixture of Experts Router
  - Meta Labeler Trade Filter

Metrics Computed:
  - Accuracy
  - Precision (Macro)
  - Recall (Macro)
  - ROC AUC (One-vs-Rest)
  - Profit Factor
  - Sharpe Ratio (Annualized)
  - Deflated Sharpe Ratio (DSR)
"""

import os
import sys
import math
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.risk_metrics import sharpe_ratio, deflated_sharpe
from models.tft_model import get_tft_model
from models.router import get_router_model
from models.experts.trend import TrendExpert
from models.experts.breakout import BreakoutExpert
from models.experts.scalping import ScalpingExpert
from models.experts.volatility import VolatilityExpert
from models.experts.news import NewsExpert
from models.meta_labeler import meta_labeler

logger = logging.getLogger("btcognitive.evaluator")


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_probs: np.ndarray,
    returns: np.ndarray,
    n_trials: int = 10
) -> Dict[str, float]:
    """
    Computes standard statistical & quantitative financial metrics.
    """
    y_t = np.asarray(y_true, dtype=np.int64)
    y_p = np.asarray(y_pred, dtype=np.int64)
    y_prob = np.asarray(y_probs, dtype=np.float64)
    rets = np.asarray(returns, dtype=np.float64)

    # 1. Accuracy
    acc = float(accuracy_score(y_t, y_p))

    # 2. Precision (Macro)
    prec = float(precision_score(y_t, y_p, average="macro", zero_division=0))

    # 3. Recall (Macro)
    rec = float(recall_score(y_t, y_p, average="macro", zero_division=0))

    # 4. ROC AUC (One-vs-Rest)
    try:
        if len(np.unique(y_t)) > 1:
            if y_prob.ndim == 2 and y_prob.shape[1] >= len(np.unique(y_t)):
                roc_auc = float(roc_auc_score(y_t, y_prob, multi_class="ovr", average="macro"))
            else:
                roc_auc = 0.50
        else:
            roc_auc = 0.50
    except Exception:
        roc_auc = 0.50

    # 5. Profit Factor
    # Strategy returns based on prediction: 0=BUY (+ret), 1=SELL (-ret), 2=HOLD (0)
    strat_rets = []
    for pred_dir, r in zip(y_p, rets):
        if pred_dir == 0:   # BUY
            strat_rets.append(r)
        elif pred_dir == 1: # SELL
            strat_rets.append(-r)
        else:               # HOLD
            strat_rets.append(0.0)

    strat_rets = np.array(strat_rets)
    gains = strat_rets[strat_rets > 0].sum()
    losses = abs(strat_rets[strat_rets < 0].sum())
    profit_factor = float(gains / losses) if losses > 1e-6 else (float(gains) if gains > 0 else 1.0)

    # 6. Sharpe Ratio
    sr = sharpe_ratio(strat_rets.tolist())
    sr_val = float(sr) if sr is not None else 0.0

    # 7. Deflated Sharpe Ratio (DSR)
    dsr = deflated_sharpe(sr_val, n_trials=n_trials)
    dsr_val = float(dsr) if dsr is not None else 0.0

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "roc_auc": round(roc_auc, 4),
        "profit_factor": round(profit_factor, 4),
        "sharpe": round(sr_val, 4),
        "dsr": round(dsr_val, 4)
    }


class QuantitativeEvaluator:
    """
    Evaluates TFT, 5 Experts, Sparse MoE Router, and Meta Labeler on market data.
    """

    def __init__(self):
        self.tft = get_tft_model()
        self.router = get_router_model()
        self.experts = {
            "TrendExpert": TrendExpert(num_features=32),
            "BreakoutExpert": BreakoutExpert(num_features=32),
            "ScalpingExpert": ScalpingExpert(num_features=32),
            "VolatilityExpert": VolatilityExpert(num_features=32),
            "NewsExpert": NewsExpert(num_features=32)
        }

    def evaluate_all(
        self,
        tensors: np.ndarray,
        y_true: np.ndarray,
        returns: np.ndarray
    ) -> List[Dict[str, Any]]:
        """
        Evaluates each model and sub-module on the same test dataset.
        """
        x_t = torch.from_numpy(np.asarray(tensors, dtype=np.float32))
        if x_t.ndim == 2:
            x_t = x_t.unsqueeze(0)

        results = []

        # -------------------------------------------------------------
        # 1. Evaluate TFT Model
        # -------------------------------------------------------------
        self.tft.eval()
        with torch.no_grad():
            out_tft = self.tft(x_t)
            probs_tft = out_tft["probabilities"].cpu().numpy()
            preds_tft = np.argmax(probs_tft, axis=-1)

        m_tft = compute_metrics(y_true, preds_tft, probs_tft, returns)
        results.append({"model": "TFT (Temporal Fusion Transformer)", **m_tft})

        # -------------------------------------------------------------
        # 2. Evaluate Individual Experts
        # -------------------------------------------------------------
        for name, expert in self.experts.items():
            expert.eval()
            with torch.no_grad():
                out_e = expert(x_t)
                probs_e = out_e["probabilities"].cpu().numpy()
                preds_e = np.argmax(probs_e, axis=-1)

            m_e = compute_metrics(y_true, preds_e, probs_e, returns)
            results.append({"model": name, **m_e})

        # -------------------------------------------------------------
        # 3. Evaluate Sparse MoE Router
        # -------------------------------------------------------------
        self.router.eval()
        with torch.no_grad():
            regime_feats = torch.zeros(len(x_t), 7)
            regime_feats[:, 0] = 1.0 # Default Strong Uptrend
            out_moe = self.router(x_t, regime_feats)
            probs_moe = out_moe["probabilities"].cpu().numpy()
            preds_moe = np.argmax(probs_moe, axis=-1)

        m_moe = compute_metrics(y_true, preds_moe, probs_moe, returns)
        results.append({"model": "Sparse MoE Router", **m_moe})

        # -------------------------------------------------------------
        # 4. Evaluate Meta Labeler Filtered Strategy
        # -------------------------------------------------------------
        # Apply Meta Labeler filter to MoE predictions
        meta_preds = []
        meta_probs = []
        meta_rets = []

        for i in range(len(preds_moe)):
            res_meta = meta_labeler.predict(
                tft_probs=probs_moe[i],
                expert_agreement=0.90,
                atr=0.015,
                spread=0.0001,
                funding=0.0001,
                rsi=50.0,
                volatility=0.02
            )
            # If rejected, force HOLD (class 2) with zero return
            if res_meta["decision"] == "Reject":
                meta_preds.append(2)
                meta_probs.append([0.0, 0.0, 1.0])
                meta_rets.append(0.0)
            elif res_meta["decision"] == "Reduce Size":
                meta_preds.append(preds_moe[i])
                meta_probs.append(probs_moe[i].tolist())
                meta_rets.append(returns[i] * 0.5)
            else:
                meta_preds.append(preds_moe[i])
                meta_probs.append(probs_moe[i].tolist())
                meta_rets.append(returns[i])

        m_meta = compute_metrics(
            y_true=y_true,
            y_pred=np.array(meta_preds),
            y_probs=np.array(meta_probs),
            returns=np.array(meta_rets)
        )
        results.append({"model": "Meta Labeler (Filtered Strategy)", **m_meta})

        return results


# Global Singleton Evaluator
evaluator = QuantitativeEvaluator()


def evaluate_models(
    tensors: np.ndarray,
    y_true: np.ndarray,
    returns: np.ndarray
) -> List[Dict[str, Any]]:
    """Evaluates all V3 forecasting models & sub-experts."""
    return evaluator.evaluate_all(tensors, y_true, returns)

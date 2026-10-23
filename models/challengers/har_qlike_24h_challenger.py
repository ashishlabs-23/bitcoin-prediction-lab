"""
models/challengers/har_qlike_24h_challenger.py — 24-Hour QLIKE-Coherent HAR Challenger & Baselines
==================================================================================================
Implements:
1. Conventional HAR-24H (OLS on log variance)
2. QLIKE-Coherent HAR-24H (Direct QLIKE loss minimization, Puke & Schweikert 2026)
3. Volatility Persistence Benchmark (Trailing 24h Realized Variance)
4. Rolling Mean 30-Day Benchmark (Trailing 30d Realized Variance)
5. Diebold-Mariano & Harvey-Leybourne-Newbold (1997) paired loss test with Student's t distribution.
6. Non-overlapping daily evaluation and hourly rolling evaluation.
"""

import os
import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple, Optional, List
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy import stats

logger = logging.getLogger("btcognitive.har_qlike_24h")


def compute_qlike(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    """
    Computes element-wise canonical QLIKE loss: y / y_hat - ln(y / y_hat) - 1.
    Strictly proper scoring rule for variance (Patton, 2011).
    """
    y_pred_safe = np.maximum(1e-6, y_pred)
    y_true_safe = np.maximum(1e-6, y_true)
    ratio = y_true_safe / y_pred_safe
    return ratio - np.log(ratio) - 1.0


@dataclass(frozen=True)
class DieboldMarianoResult:
    mean_loss_diff: float
    standard_error: float
    dm_statistic: float
    hln_corrected_statistic: float
    degrees_of_freedom: int
    p_value_one_sided: float
    statistically_significant: bool


def compute_diebold_mariano_test(
    loss_baseline: np.ndarray,
    loss_challenger: np.ndarray,
    horizon_h: int = 1
) -> DieboldMarianoResult:
    """
    Computes Diebold-Mariano (1995) paired loss test with Harvey-Leybourne-Newbold (1997)
    finite sample correction and Student's t reference distribution.

    d_t = loss_baseline - loss_challenger (positive d_t => challenger has smaller loss).
    One-sided H1: Challenger has strictly smaller expected loss than baseline (d_bar > 0).
    """
    d = loss_baseline - loss_challenger
    T = len(d)
    if T < 5:
        raise ValueError("Insufficient observations for Diebold-Mariano test.")

    d_bar = float(np.mean(d))

    if horizon_h > 1:
        # Newey-West Bartlett kernel for overlapping horizon h
        gamma_0 = float(np.var(d, ddof=1))
        gamma_sum = 0.0
        for k in range(1, horizon_h):
            cov_k = float(np.cov(d[:-k], d[k:])[0, 1])
            weight = 1.0 - (k / float(horizon_h))
            gamma_sum += weight * cov_k
        nw_var = max(1e-9, gamma_0 + 2.0 * gamma_sum)
    else:
        # Non-overlapping daily observations: standard variance
        nw_var = max(1e-9, float(np.var(d, ddof=1)))

    se_dm = np.sqrt(nw_var / float(T))
    dm_stat = float(d_bar / se_dm) if se_dm > 1e-12 else 0.0

    # Harvey-Leybourne-Newbold finite-sample correction factor
    if horizon_h > 1:
        hln_factor = np.sqrt(max(1e-9, (T + 1 - 2 * horizon_h + horizon_h * (horizon_h - 1) / T) / T))
    else:
        hln_factor = np.sqrt(max(1e-9, (T - 1) / T))

    hln_stat = float(dm_stat * hln_factor)
    df = max(1, T - 1)

    # In accordance with Harvey, Leybourne & Newbold (1997), reference distribution is Student's t with (T - 1) d.f.
    p_value = float(stats.t.sf(hln_stat, df=df))
    is_sig = bool(p_value < 0.05 and d_bar > 0.0)

    return DieboldMarianoResult(
        mean_loss_diff=round(d_bar, 6),
        standard_error=round(float(se_dm), 6),
        dm_statistic=round(dm_stat, 4),
        hln_corrected_statistic=round(hln_stat, 4),
        degrees_of_freedom=df,
        p_value_one_sided=round(p_value, 5),
        statistically_significant=is_sig
    )


class ConventionalHAR24H:
    """
    Conventional Heterogeneous Autoregressive model for 24-hour variance.
    Estimated via OLS on log(rv24h_var_ann):
        ln(y) = beta_0 + X * beta + epsilon
        y_hat = exp(beta_0 + X * beta)
    """

    def __init__(self):
        self.beta: Optional[np.ndarray] = None
        self.intercept: Optional[float] = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "ConventionalHAR24H":
        n = X.shape[0]
        X_design = np.column_stack([np.ones(n), X])
        log_y = np.log(np.maximum(1e-6, y))
        b = np.linalg.lstsq(X_design, log_y, rcond=None)[0]
        self.beta = b
        self.intercept = float(b[0])
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.beta is None:
            raise ValueError("Model is not fitted.")
        n = X.shape[0]
        X_design = np.column_stack([np.ones(n), X])
        log_pred = np.clip(X_design @ self.beta, -10.0, 10.0)
        return np.exp(log_pred)


class HARQLIKE24HChallenger:
    """
    Loss-coherent HAR challenger for 24-hour realized variance.
    Directly minimizes sample QLIKE loss with L2 regularization:
        min_beta sum_t QLIKE(y_t, exp(X_t beta)) + lambda * ||beta_{1:p}||_2^2
    """

    def __init__(self, l2_reg: float = 0.05):
        self.l2_reg = l2_reg
        self.beta: Optional[np.ndarray] = None
        self.intercept: Optional[float] = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "HARQLIKE24HChallenger":
        n, p = X.shape
        X_design = np.column_stack([np.ones(n), X])

        # Initialize from OLS coefficients
        init_beta = np.linalg.lstsq(X_design, np.log(np.maximum(1e-6, y)), rcond=None)[0]

        def objective(b: np.ndarray) -> float:
            pred = np.exp(np.clip(X_design @ b, -10.0, 10.0))
            loss = np.mean(compute_qlike(y, pred))
            reg = self.l2_reg * np.sum(b[1:] ** 2)
            return float(loss + reg)

        res = minimize(objective, init_beta, method="L-BFGS-B")
        self.beta = res.x
        self.intercept = float(self.beta[0])
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.beta is None:
            raise ValueError("Model is not fitted.")
        n = X.shape[0]
        X_design = np.column_stack([np.ones(n), X])
        log_pred = np.clip(X_design @ self.beta, -10.0, 10.0)
        return np.exp(log_pred)


def evaluate_24h_volatility_suite(
    y_true: np.ndarray,
    preds_dict: Dict[str, np.ndarray],
    benchmark_key: str = "conventional_har_24h",
    horizon_h: int = 1
) -> Dict[str, Any]:
    """
    Evaluates multiple 24h volatility models on identical observations:
    Computes QLIKE, RMSE, MAE, and Diebold-Mariano tests against the benchmark.
    """
    summary = {}
    base_preds = preds_dict[benchmark_key]
    loss_base = compute_qlike(y_true, base_preds)

    for name, p in preds_dict.items():
        loss = compute_qlike(y_true, p)
        mean_q = float(np.mean(loss))
        rmse = float(np.sqrt(np.mean((y_true - p) ** 2)))
        mae = float(np.mean(np.abs(y_true - p)))

        if name == benchmark_key:
            dm_res = None
        else:
            dm_res = compute_diebold_mariano_test(loss_base, loss, horizon_h=horizon_h)

        summary[name] = {
            "mean_qlike": round(mean_q, 5),
            "rmse": round(rmse, 5),
            "mae": round(mae, 5),
            "diebold_mariano": asdict(dm_res) if dm_res else "BENCHMARK_REFERENCE"
        }

    return summary

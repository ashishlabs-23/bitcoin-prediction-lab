"""
models/challengers/har_qlike_challenger.py — QLIKE-Coherent HAR-RS-DOW Volatility Challenger
=============================================================================================
Implements Research Candidate A based on:
Puke, M., & Schweikert, K. (2026). "Coherent Forecasting of Realized Volatility."
Journal of Forecasting, 45(4), 1714–1729. https://doi.org/10.1002/for.70114

Theoretical Justification:
Standard HAR models minimize Mean Squared Error (MSE) on log-variance:
    min_beta sum_t (ln(y_t) - X_t beta)^2
However, if the ultimate evaluation loss function is QLIKE:
    QLIKE(y, y_hat) = y / y_hat - ln(y / y_hat) - 1
Patton (2011) and Puke & Schweikert (2026) prove that parameter estimation must be loss-coherent
to minimize expected finite-sample forecast risk. Minimizing in-sample QLIKE directly aligns
the optimization objective with the out-of-sample evaluation metric.

Model Specification:
- Baseline: HAR-RS-DOW-v1.0 (OLS on log variance)
- Challenger: HAR-QLIKE-v1.0 (Direct QLIKE minimization with L2 shrinkage)
- Target: Annualized forward 7-day realized variance (rv7d_var_ann)
- Horizon: 168 hours
- Inputs: Identical 10 point-in-time features [log_rv_down, log_rv_up, log_rv7, log_rv30, dow_1..dow_6]
- Epistemic Status: RESEARCH_CHALLENGER (no automatic production promotion)
"""

import os
import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy import stats

logger = logging.getLogger("btcognitive.har_qlike_challenger")


@dataclass(frozen=True)
class QLIKEEvaluationSummary:
    model_id: str
    sample_size: int
    train_sample_size: int
    in_sample_qlike: float
    out_of_sample_qlike: float
    out_of_sample_rmse: float
    out_of_sample_mae: float
    causal_conformal_coverage_pct: float
    mean_interval_width: float
    mean_winkler_score: float
    baseline_out_of_sample_qlike: float
    qlike_raw_reduction: float
    qlike_relative_reduction_pct: float
    diebold_mariano_stat: float
    hln_corrected_stat: float
    p_value_one_sided: float
    statistically_significant: bool
    verdict: str


def compute_qlike(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    """
    Computes element-wise QLIKE loss: y / y_hat - ln(y / y_hat) - 1.
    """
    y_pred_safe = np.maximum(1e-6, y_pred)
    y_true_safe = np.maximum(1e-6, y_true)
    ratio = y_true_safe / y_pred_safe
    return ratio - np.log(ratio) - 1.0


class HARQLIKEChallenger:
    """
    HAR-RS-DOW challenger estimated via loss-coherent QLIKE minimization.
    """

    def __init__(self, l2_reg: float = 0.10):
        self.l2_reg = l2_reg
        self.beta: Optional[np.ndarray] = None
        self.intercept: Optional[float] = None
        self.feature_names = [
            "log_rv_down_1d", "log_rv_up_1d", "log_rv7d_lag", "log_rv30d",
            "dow_1", "dow_2", "dow_3", "dow_4", "dow_5", "dow_6"
        ]

    def fit(self, X: np.ndarray, y: np.ndarray) -> "HARQLIKEChallenger":
        """
        Fits coefficients beta by minimizing sample QLIKE loss + L2 regularization.
        """
        n, p = X.shape
        X_design = np.column_stack([np.ones(n), X])

        # Initialize from OLS on log(y)
        init_beta = np.linalg.lstsq(X_design, np.log(np.maximum(1e-6, y)), rcond=None)[0]

        def objective(b: np.ndarray) -> float:
            pred = np.exp(np.clip(X_design @ b, -10.0, 10.0))
            loss = np.mean(compute_qlike(y, pred))
            # L2 regularization on slopes only (exclude intercept)
            reg = self.l2_reg * np.sum(b[1:] ** 2)
            return float(loss + reg)

        res = minimize(objective, init_beta, method="L-BFGS-B")
        self.beta = res.x
        self.intercept = float(self.beta[0])
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Generates point forecasts of realized variance in natural scale (annualized variance).
        """
        if self.beta is None:
            raise ValueError("Model is not fitted.")
        n = X.shape[0]
        X_design = np.column_stack([np.ones(n), X])
        log_pred = np.clip(X_design @ self.beta, -10.0, 10.0)
        return np.exp(log_pred)

    def evaluate_against_baseline(
        self,
        X_holdout: np.ndarray,
        y_holdout: np.ndarray,
        baseline_preds: np.ndarray,
        X_train: Optional[np.ndarray] = None,
        y_train: Optional[np.ndarray] = None,
        horizon_h: int = 168
    ) -> QLIKEEvaluationSummary:
        """
        Conducts rigorous paired Diebold-Mariano test with Newey-West long-run variance.
        """
        challenger_preds = self.predict(X_holdout)

        loss_base = compute_qlike(y_holdout, baseline_preds)
        loss_chal = compute_qlike(y_holdout, challenger_preds)

        d = loss_base - loss_chal  # Positive indicates challenger has smaller loss
        T = len(d)
        d_bar = float(np.mean(d))

        # Newey-West long-run variance estimate for overlapping horizon h
        gamma_0 = float(np.var(d, ddof=1))
        gamma_sum = 0.0
        for k in range(1, horizon_h):
            cov_k = float(np.cov(d[:-k], d[k:])[0, 1])
            weight = 1.0 - (k / float(horizon_h))
            gamma_sum += weight * cov_k

        nw_var = max(1e-9, gamma_0 + 2.0 * gamma_sum)
        se_dm = np.sqrt(nw_var / float(T))
        dm_stat = float(d_bar / se_dm)

        # Harvey-Leybourne-Newbold (1997) finite-sample correction
        hln_correction = np.sqrt(max(1e-9, (T + 1 - 2 * horizon_h + horizon_h * (horizon_h - 1) / T) / T))
        hln_stat = float(dm_stat * hln_correction)

        # In accordance with Harvey, Leybourne & Newbold (1997), reference distribution is Student's t with (T - 1) d.f.
        p_value = float(stats.t.sf(hln_stat, df=max(1, T - 1)))
        is_sig = bool(p_value < 0.05 and d_bar > 0.0)

        # Causal conformal evaluation for challenger
        if y_train is not None and X_train is not None:
            v_train_chal = self.predict(X_train)
            cov_pct, mean_w, mean_wink = self._compute_strictly_causal_conformal(
                y_train, v_train_chal, y_holdout, challenger_preds, horizon_h=horizon_h
            )
        else:
            cov_pct, mean_w, mean_wink = 0.0, 0.0, 0.0

        base_qlike = float(np.mean(loss_base))
        chal_qlike = float(np.mean(loss_chal))
        rel_reduc = float(((base_qlike - chal_qlike) / base_qlike) * 100.0)

        verdict = "CHALLENGER_CONFIRMED_SIGNIFICANT" if is_sig else "CHALLENGER_STATISTICALLY_EQUAL_TO_BASELINE"

        return QLIKEEvaluationSummary(
            model_id="HAR-QLIKE-v1.0",
            sample_size=T,
            train_sample_size=len(y_train) if y_train is not None else 0,
            in_sample_qlike=float(np.mean(compute_qlike(y_train, self.predict(X_train)))) if y_train is not None else 0.0,
            out_of_sample_qlike=round(chal_qlike, 5),
            out_of_sample_rmse=round(float(np.sqrt(np.mean((y_holdout - challenger_preds) ** 2))), 5),
            out_of_sample_mae=round(float(np.mean(np.abs(y_holdout - challenger_preds))), 5),
            causal_conformal_coverage_pct=round(cov_pct, 2),
            mean_interval_width=round(mean_w, 4),
            mean_winkler_score=round(mean_wink, 4),
            baseline_out_of_sample_qlike=round(base_qlike, 5),
            qlike_raw_reduction=round(d_bar, 6),
            qlike_relative_reduction_pct=round(rel_reduc, 2),
            diebold_mariano_stat=round(dm_stat, 4),
            hln_corrected_stat=round(hln_stat, 4),
            p_value_one_sided=round(p_value, 5),
            statistically_significant=is_sig,
            verdict=verdict
        )

    def _compute_strictly_causal_conformal(
        self,
        y_train: np.ndarray,
        v_train: np.ndarray,
        y_holdout: np.ndarray,
        v_holdout: np.ndarray,
        alpha: float = 0.10,
        horizon_h: int = 168
    ) -> Tuple[float, float, float]:
        res_tr = y_train - v_train
        res_ho = y_holdout - v_holdout
        N_tr = len(res_tr)
        N_ho = len(res_ho)

        res_all = np.concatenate([res_tr, res_ho])
        full_ewm_std = pd.Series(res_all).ewm(span=720, min_periods=72).std().values
        s_u_resolved = np.maximum(0.0, res_all / np.maximum(1e-4, full_ewm_std))
        s_l_resolved = np.maximum(0.0, -res_all / np.maximum(1e-4, full_ewm_std))

        k_res_indices = [N_tr + (i - horizon_h) if i >= horizon_h else N_tr - 1 for i in range(N_ho)]
        lower = np.zeros(N_ho)
        upper = np.zeros(N_ho)

        for i in range(N_ho):
            k_res = k_res_indices[i]
            std_i = full_ewm_std[k_res]
            pool_u = s_u_resolved[max(0, k_res - 1000 + 1): k_res + 1: 24]
            pool_l = s_l_resolved[max(0, k_res - 1000 + 1): k_res + 1: 24]

            k_c2 = int(np.ceil((len(pool_u) + 1) * (1.0 - alpha / 2.0)))
            q_u = float(np.sort(pool_u)[min(len(pool_u) - 1, k_c2)])
            q_l = float(np.sort(pool_l)[min(len(pool_l) - 1, k_c2)])

            v_i = v_holdout[i]
            lower[i] = max(1e-6, v_i - q_l * std_i)
            upper[i] = v_i + q_u * std_i

        covered = (y_holdout >= lower) & (y_holdout <= upper)
        cov_pct = float(np.mean(covered) * 100.0)

        widths = upper - lower
        winkler = widths.copy()
        under = y_holdout < lower
        over = y_holdout > upper
        winkler[under] += (2.0 / alpha) * (lower[under] - y_holdout[under])
        winkler[over] += (2.0 / alpha) * (y_holdout[over] - upper[over])

        return cov_pct, float(np.mean(widths)), float(np.mean(winkler))

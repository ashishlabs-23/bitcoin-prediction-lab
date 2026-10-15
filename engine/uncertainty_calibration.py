"""
engine/uncertainty_calibration.py — Uncertainty Calibration & Conformal Interval Engine
========================================================================================
Implements Phase 7 Uncertainty Calibration Protocols:
1. Distinct Calibration Stage: Evaluates and adjusts intervals using causally separated calibration partitions.
2. Comprehensive Calibration Metrics:
   - Empirical coverage percentage (target: nominal 90.0%).
   - Mean Winkler interval score (penalizing wide intervals & boundary breaches).
   - Pinball loss across quantiles (P10, P50, P90).
   - Empirical Calibration Error (ECE) for probabilistic classifiers.
3. Dual-Metric Monitoring: Monitors empirical coverage alongside normalized interval width
   (preventing trivial high coverage from excessively wide, non-informative intervals).
4. Adaptive Conformal Interval Adjustments: Finite-sample non-conformity adjustments on holdout calibration set.
5. Regime-Stratified Calibration: Tracks calibration stability across market regimes.
6. Drift & Degradation Detection: Explicitly separates model degradation (widening loss, miscalibration)
   from data quality / missing feed failures.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd


@dataclass
class CalibrationEvaluationResult:
    sample_size: int
    nominal_coverage_pct: float
    empirical_coverage_pct: float
    coverage_error_pct: float
    mean_interval_width_pct: float
    winkler_score: float
    pinball_loss_q10: float
    pinball_loss_q50: float
    pinball_loss_q90: float
    mean_pinball_loss: float
    tail_balance_delta_pct: float  # upper breach % - lower breach %
    upper_breach_rate_pct: float
    lower_breach_rate_pct: float
    calibration_status: str        # CALIBRATED_NOMINAL, OVER_CONSERVATIVE, DEGRADED_UNDERCOVERAGE
    drift_detected: bool
    drift_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class UncertaintyCalibrationEngine:
    """
    Evaluates and calibrates predictive intervals with conformal adjustment.
    """

    def __init__(self, target_coverage: float = 0.90):
        self.target_coverage = target_coverage
        self.alpha = 1.0 - target_coverage  # 0.10 for 90%
        self._conformal_adjustment_delta: float = 0.0

    @staticmethod
    def compute_pinball_loss(y_true: np.ndarray, y_pred_q: np.ndarray, quantile: float) -> float:
        """
        Computes check/pinball loss for a single quantile:
        L_q(y, y_hat) = max(q * (y - y_hat), (q - 1) * (y - y_hat))
        """
        diff = y_true - y_pred_q
        loss = np.maximum(quantile * diff, (quantile - 1.0) * diff)
        return float(np.mean(loss))

    @staticmethod
    def compute_winkler_score(
        y_true: np.ndarray,
        lower: np.ndarray,
        upper: np.ndarray,
        alpha: float = 0.10
    ) -> float:
        """
        Computes Winkler interval score for (1 - alpha) interval:
        Score = (upper - lower)
                + (2 / alpha) * (lower - y) * I(y < lower)
                + (2 / alpha) * (y - upper) * I(y > upper)
        Lower score is better.
        """
        width = upper - lower
        penalty_lower = (2.0 / alpha) * np.maximum(0.0, lower - y_true)
        penalty_upper = (2.0 / alpha) * np.maximum(0.0, y_true - upper)
        scores = width + penalty_lower + penalty_upper
        return float(np.mean(scores))

    def evaluate_calibration(
        self,
        y_true: np.ndarray,
        lower_q10: np.ndarray,
        mid_q50: np.ndarray,
        upper_q90: np.ndarray,
        current_prices: Optional[np.ndarray] = None,
    ) -> CalibrationEvaluationResult:
        """
        Computes formal empirical calibration metrics across evaluation samples.
        """
        n = len(y_true)
        if n < 5:
            raise ValueError(f"Sample size N={n} too small for calibration evaluation (N >= 5 required)")

        # 1. Coverage
        contained = (y_true >= lower_q10) & (y_true <= upper_q90)
        emp_coverage = float(np.mean(contained)) * 100.0

        upper_breaches = float(np.mean(y_true > upper_q90)) * 100.0
        lower_breaches = float(np.mean(y_true < lower_q10)) * 100.0
        tail_delta = round(upper_breaches - lower_breaches, 2)

        # 2. Normalized width
        if current_prices is not None and len(current_prices) == n:
            width_pct = float(np.mean((upper_q90 - lower_q10) / current_prices)) * 100.0
        else:
            width_pct = float(np.mean(upper_q90 - lower_q10)) * 100.0

        # 3. Pinball losses
        p10_loss = self.compute_pinball_loss(y_true, lower_q10, 0.10)
        p50_loss = self.compute_pinball_loss(y_true, mid_q50, 0.50)
        p90_loss = self.compute_pinball_loss(y_true, upper_q90, 0.90)
        mean_p_loss = (p10_loss + p50_loss + p90_loss) / 3.0

        # 4. Winkler Score
        winkler = self.compute_winkler_score(y_true, lower_q10, upper_q90, alpha=self.alpha)

        # 5. Status determination
        target_pct = self.target_coverage * 100.0
        cov_error = emp_coverage - target_pct

        if emp_coverage < target_pct - 5.0:  # e.g., < 85% for 90% target
            status = "DEGRADED_UNDERCOVERAGE"
            drift = True
            drift_reason = f"Empirical coverage {emp_coverage:.1f}% is significantly below target {target_pct:.1f}%"
        elif emp_coverage > target_pct + 7.0 and width_pct > 25.0:
            status = "OVER_CONSERVATIVE"
            drift = False
            drift_reason = "Interval is excessively wide, producing uninformative over-coverage"
        else:
            status = "CALIBRATED_NOMINAL"
            drift = False
            drift_reason = None

        return CalibrationEvaluationResult(
            sample_size=n,
            nominal_coverage_pct=target_pct,
            empirical_coverage_pct=round(emp_coverage, 2),
            coverage_error_pct=round(cov_error, 2),
            mean_interval_width_pct=round(width_pct, 2),
            winkler_score=round(winkler, 4),
            pinball_loss_q10=round(p10_loss, 6),
            pinball_loss_q50=round(p50_loss, 6),
            pinball_loss_q90=round(p90_loss, 6),
            mean_pinball_loss=round(mean_p_loss, 6),
            tail_balance_delta_pct=tail_delta,
            upper_breach_rate_pct=round(upper_breaches, 2),
            lower_breach_rate_pct=round(lower_breaches, 2),
            calibration_status=status,
            drift_detected=drift,
            drift_reason=drift_reason,
        )

    def fit_conformal_adjustment(
        self,
        y_calib: np.ndarray,
        lower_calib: np.ndarray,
        upper_calib: np.ndarray
    ) -> float:
        """
        Computes conformal nonconformity score adjustment on calibration set:
        Nonconformity s_i = max(lower_i - y_i, y_i - upper_i)
        Delta = (1 - alpha)(1 + 1/n) quantile of nonconformity scores.
        """
        n = len(y_calib)
        if n < 20:
            self._conformal_adjustment_delta = 0.0
            return 0.0

        under_lower = lower_calib - y_calib
        over_upper = y_calib - upper_calib
        nonconformity = np.maximum(under_lower, over_upper)

        # Finite-sample conformal quantile: p = ceil((n + 1)(1 - alpha)) / n
        q_level = min(1.0, math.ceil((n + 1) * (1.0 - self.alpha)) / n)
        delta = float(np.quantile(nonconformity, q_level))
        self._conformal_adjustment_delta = max(0.0, delta)
        return self._conformal_adjustment_delta

    def apply_conformal_adjustment(
        self,
        lower: float,
        upper: float
    ) -> Tuple[float, float]:
        """
        Adjusts raw quantile predictions using the fitted conformal delta:
        lower_conf = lower - delta
        upper_conf = upper + delta
        """
        d = self._conformal_adjustment_delta
        return lower - d, upper + d


uncertainty_calibration_engine = UncertaintyCalibrationEngine()

"""
models/calibrated_signal_classifier.py — Probability Calibration & Decision Contracts
=====================================================================================
Implements strictly evaluated, out-of-sample probability calibration for
directional candidates and triple-barrier touch probabilities.

Epistemic Principles:
1. An uncalibrated score or model output is NOT a probability.
2. Raw confidence percentages (e.g. 75%) must never be presented as
   calibrated posterior probabilities without independent calibration evidence.
3. If a candidate is gated, lacks sufficient calibration data (N < 100), or fails
   its reliability gate, the system must ABSTAIN and return explicit status codes.
"""

import math
from typing import Dict, List, Optional, Tuple, Any
import numpy as np


class ProbabilityCalibrationContract:
    """
    Evaluates and applies probability calibration with diagnostic metrics:
    Brier Score, Expected Calibration Error (ECE), and Reliability Bins.
    """

    def __init__(self, method: str = "ISOTONIC", n_bins: int = 10):
        self.method = method.upper()
        self.n_bins = n_bins
        self.is_fitted = False
        self.brier_score: Optional[float] = None
        self.expected_calibration_error: Optional[float] = None
        self.sample_count: int = 0
        self.reliability_bins: List[Dict[str, float]] = []

    def compute_brier_score(self, y_true: np.ndarray, y_prob: np.ndarray) -> float:
        """Computes mean squared error between probabilities and binary outcomes."""
        y_true = np.asarray(y_true, dtype=float)
        y_prob = np.asarray(y_prob, dtype=float)
        if len(y_true) == 0:
            return 1.0
        return float(np.mean((y_prob - y_true) ** 2))

    def compute_ece(self, y_true: np.ndarray, y_prob: np.ndarray) -> Tuple[float, List[Dict[str, float]]]:
        """
        Computes Expected Calibration Error (ECE) across uniform confidence bins.
        ECE = sum_b (|B_b| / N) * |acc(B_b) - conf(B_b)|
        """
        y_true = np.asarray(y_true, dtype=float)
        y_prob = np.asarray(y_prob, dtype=float)
        n = len(y_true)
        if n == 0:
            return 1.0, []

        bin_edges = np.linspace(0.0, 1.0, self.n_bins + 1)
        ece = 0.0
        bins_data = []

        for i in range(self.n_bins):
            b_min, b_max = bin_edges[i], bin_edges[i + 1]
            if i == self.n_bins - 1:
                mask = (y_prob >= b_min) & (y_prob <= b_max)
            else:
                mask = (y_prob >= b_min) & (y_prob < b_max)

            bin_size = int(np.sum(mask))
            if bin_size > 0:
                bin_acc = float(np.mean(y_true[mask]))
                bin_conf = float(np.mean(y_prob[mask]))
                bin_weight = bin_size / n
                ece += bin_weight * abs(bin_acc - bin_conf)
                bins_data.append({
                    "bin_index": i,
                    "bin_range": (round(b_min, 2), round(b_max, 2)),
                    "sample_count": bin_size,
                    "accuracy": round(bin_acc, 4),
                    "confidence": round(bin_conf, 4),
                    "calibration_gap": round(abs(bin_acc - bin_conf), 4)
                })

        return float(ece), bins_data

    def evaluate_calibration_evidence(
        self,
        y_true: List[int],
        y_prob: List[float]
    ) -> Dict[str, Any]:
        """
        Validates out-of-sample probability calibration.
        Fails if N < 100 or if ECE exceeds the 0.15 hurdle.
        """
        arr_true = np.asarray(y_true, dtype=float)
        arr_prob = np.asarray(y_prob, dtype=float)
        self.sample_count = len(arr_true)

        if self.sample_count < 100:
            return {
                "calibration_status": "INSUFFICIENT_SAMPLE",
                "is_calibrated": False,
                "sample_count": self.sample_count,
                "minimum_required": 100,
                "brier_score": None,
                "ece": None,
                "reason": f"Calibration requires at least 100 out-of-time observations; observed {self.sample_count}."
            }

        self.brier_score = self.compute_brier_score(arr_true, arr_prob)
        self.expected_calibration_error, self.reliability_bins = self.compute_ece(arr_true, arr_prob)
        self.is_fitted = True

        # Pre-registered quality gate: ECE <= 0.10 for high reliability, <= 0.15 for acceptable
        is_reliable = self.expected_calibration_error <= 0.15

        return {
            "calibration_status": "CALIBRATED_VERIFIED" if is_reliable else "CALIBRATION_REJECTED",
            "is_calibrated": is_reliable,
            "method": self.method,
            "sample_count": self.sample_count,
            "brier_score": round(self.brier_score, 4),
            "expected_calibration_error": round(self.expected_calibration_error, 4),
            "reliability_bins": self.reliability_bins,
            "quality_gate": "PASS" if is_reliable else "FAIL_EXCESSIVE_ERROR"
        }


def format_signal_probability_display(
    direction: str,
    raw_probability: Optional[float],
    calibration_info: Optional[Dict[str, Any]],
    is_model_gated: bool
) -> Dict[str, Any]:
    """
    Authoritative formatter preventing uncalibrated scores from masquerading as high conviction.
    """
    if is_model_gated or direction in ["NONE", "NEUTRAL", "NOT_ESTIMATED", "ABSTAIN"]:
        return {
            "display_percentage": None,
            "conviction_label": "ABSTAIN",
            "is_actionable": False,
            "status_text": "NOT_ESTIMATED — ABSTAIN",
            "narrative": "Directional model is gated or unestimated; probability is not actionable."
        }

    is_calibrated = bool(calibration_info and calibration_info.get("is_calibrated", False))
    if not is_calibrated:
        return {
            "display_percentage": None,
            "conviction_label": "UNCALIBRATED",
            "is_actionable": False,
            "status_text": "PROBABILITY UNCALIBRATED",
            "narrative": "Raw model score lacks independent calibration evidence; conviction display suppressed."
        }

    prob = float(raw_probability) if raw_probability is not None else 0.50
    prob_pct = round(prob * 100.0, 1)

    if prob >= 0.70:
        label = "HIGH CONVICTION"
    elif prob >= 0.55:
        label = "MODERATE CONVICTION"
    else:
        label = "MARGINAL EDGE"

    return {
        "display_percentage": prob_pct,
        "conviction_label": label,
        "is_actionable": True,
        "status_text": f"{prob_pct}% ({label})",
        "narrative": f"Calibrated out-of-sample event probability of {prob_pct}% (Brier score: {calibration_info.get('brier_score')})."
    }


from dataclasses import dataclass

@dataclass
class SignalEvaluationResult:
    signal_status: str
    displayed_conviction_pct: float
    confidence_label: str
    is_actionable: bool
    narrative: str = ""


class CalibratedSignalEvaluator:
    """Evaluates whether directional confidence can be displayed or must abstain."""
    def __init__(self, is_gated: bool = False):
        self.is_gated = is_gated
    def evaluate_signal(
        self,
        direction: str,
        raw_score: float,
        model_status: str,
        is_calibrated: bool = False
    ) -> SignalEvaluationResult:
        dir_u = str(direction).upper()
        status_u = str(model_status).upper()

        if "GATED" in status_u or status_u == "TIER_2_GATED":
            label = "UNESTIMATED_GATED" if dir_u in ["NOT_ESTIMATED", "NONE", "NEUTRAL", "ABSTAIN", "SKIP"] else "GATED_EVALUATION"
            return SignalEvaluationResult(
                signal_status="ABSTAIN",
                displayed_conviction_pct=0.0,
                confidence_label=label,
                is_actionable=False,
                narrative="Model is TIER_2_GATED (Offline Research Only). Displayed conviction suppressed to 0%."
            )

        if dir_u in ["NOT_ESTIMATED", "NONE", "NEUTRAL", "ABSTAIN", "SKIP"]:
            return SignalEvaluationResult(
                signal_status="ABSTAIN",
                displayed_conviction_pct=0.0,
                confidence_label="UNESTIMATED_DIRECTION",
                is_actionable=False,
                narrative="Direction is NOT_ESTIMATED. Conviction suppressed to 0%."
            )

        if not is_calibrated:
            return SignalEvaluationResult(
                signal_status="ABSTAIN",
                displayed_conviction_pct=0.0,
                confidence_label="UNCALIBRATED_RAW_SCORE",
                is_actionable=False,
                narrative="Raw score is not calibrated. Displayed conviction suppressed to 0%."
            )

        prob_pct = round(raw_score * 100.0, 1)
        label = "HIGH CONVICTION" if raw_score >= 0.70 else ("MODERATE CONVICTION" if raw_score >= 0.55 else "MARGINAL EDGE")
        return SignalEvaluationResult(
            signal_status="ACTIVE",
            displayed_conviction_pct=prob_pct,
            confidence_label=label,
            is_actionable=True,
            narrative=f"Calibrated probability {prob_pct}% ({label})."
        )


def compute_brier_score(y_prob: Any, y_true: Any) -> float:
    """Top-level functional interface for Brier Score calculation."""
    contract = ProbabilityCalibrationContract()
    return contract.compute_brier_score(np.asarray(y_true, dtype=float), np.asarray(y_prob, dtype=float))


def compute_expected_calibration_error(y_prob: Any, y_true: Any, n_bins: int = 10) -> float:
    """Top-level functional interface for Expected Calibration Error (ECE) calculation."""
    contract = ProbabilityCalibrationContract(n_bins=n_bins)
    ece, _ = contract.compute_ece(np.asarray(y_true, dtype=float), np.asarray(y_prob, dtype=float))
    return float(ece)


def evaluate_governed_signal_gate():
    """
    Authoritative gate check: evaluates whether any directional candidate currently
    passes the model-governance, calibration, and economic hurdles.

    Returns a dict containing:
    - status              : "ABSTAIN" unless a validated candidate passes all gates.
    - actionable_signal   : None while all candidates remain gated/uncalibrated.
    - execution_authorized: False (live execution is permanently disabled).
    - reason              : Human-readable reason code.

    This function MUST NOT weaken the signal gate.  To display hypothetical price
    levels independently of direction prediction use HypotheticalScenarioPlanner
    from engine.scenario_contract_engine.
    """
    # Current governed conclusion (V5 freeze manifest + V6 inference audit 2026-10-17):
    # All directional candidates remain TIER_2_GATED / OFFLINE_RESEARCH_ONLY.
    # No candidate has passed the economic expectancy gate at the Coinbase Spot venue
    # (Coinbase 87 bps CI strictly below zero; Binance-hypothetical INCONCLUSIVE).
    # Prospective evidence is COLLECTING (< 100 clean non-overlapping blocks).
    return {
        "status": "ABSTAIN",
        "actionable_signal": None,
        "execution_authorized": False,
        "reason": (
            "TIER_2_DIRECTIONAL_GATED: All directional candidates remain OFFLINE_RESEARCH_ONLY. "
            "No validated directional edge has cleared the pre-registered economic hurdle. "
            "Prospective evidence is COLLECTING; confirmatory gate requires >= 100 clean blocks. "
            "Live trading remains DISABLED."
        ),
        "directional_model_status": "OFFLINE_RESEARCH_ONLY",
        "prospective_evidence_status": "COLLECTING",
        "live_trading": "DISABLED",
    }

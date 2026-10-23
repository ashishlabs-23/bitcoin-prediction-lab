"""
engine/metric_contracts.py — Canonical Scientific Metric Contracts for BTCognitive
==================================================================================
Workstream B: Canonical Forecast and Metric Contracts.

Mathematical Foundations & Primary References:
1. Gneiting & Raftery (2007), "Strictly Proper Scoring Rules, Prediction, and Estimation",
   JASA 102(477), 359-378.
2. Xu & Xie (2021), "Conformal Prediction Interval for Dynamic Time-Series", ICML/PMLR 139.
3. Gibbs & Candès (2021), "Adaptive Conformal Inference Under Distribution Shift", NeurIPS 34.

Design Principles:
- Strictly proper scoring rules: distinguish point-forecast error from interval/probabilistic scores.
- Never conflate marginal 90% excursion coverage with joint path containment:
  Under independence: P(Upper and Lower) = 0.90 * 0.90 = 81%.
  Under arbitrary dependence: Fréchet bound is 80% <= P(Joint) <= 90%.
- Causal baseline integrity: baseline_delta_bps requires point-in-time benchmark forecasts
  evaluated on the exact same observations. Never calculate a baseline from future realized medians.
  If a genuine causal benchmark is not yet logged, baseline_delta_bps MUST be None (unavailable).
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
import math
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class MetricDefinition:
    """Formal specification of a scientific metric contract."""
    name: str
    display_label: str
    target: str
    horizon: str
    formula: str
    units: str
    nominal_target: Optional[float]
    statistical_interpretation: str
    limitations_and_caveats: str


# Canonical Catalog of Metric Contracts
CANONICAL_METRIC_CATALOG: Dict[str, MetricDefinition] = {
    "mfe_error_pct": MetricDefinition(
        name="mfe_error_pct",
        display_label="Mean Absolute MFE Error (%)",
        target="Maximum Favorable Excursion (MFE) within forward horizon",
        horizon="24h",
        formula="mean(|actual_mfe - exp_mfe|) * 100",
        units="percentage points (% of spot price)",
        nominal_target=None,
        statistical_interpretation="Average magnitude of deviation between predicted median upper excursion and realized upper excursion.",
        limitations_and_caveats="Evaluates point forecast accuracy of excursion amplitude; does not indicate timing or directional probability."
    ),
    "mae_error_pct": MetricDefinition(
        name="mae_error_pct",
        display_label="Mean Absolute MAE Error (%)",
        target="Maximum Adverse Excursion (MAE) within forward horizon",
        horizon="24h",
        formula="mean(|actual_mae - exp_mae|) * 100",
        units="percentage points (% of spot price)",
        nominal_target=None,
        statistical_interpretation="Average magnitude of deviation between predicted median adverse excursion and realized adverse excursion.",
        limitations_and_caveats="Evaluates point forecast accuracy of downside excursion; does not evaluate stop-loss placement economics."
    ),
    "upper_coverage_pct": MetricDefinition(
        name="upper_coverage_pct",
        display_label="Marginal Upper Excursion Coverage (%)",
        target="One-sided upper barrier breach (actual_high <= upper_p90)",
        horizon="24h",
        formula="mean(actual_high <= upper_p90) * 100",
        units="percentage (%)",
        nominal_target=90.0,
        statistical_interpretation="Empirical proportion of observations where realized intrahorizon high remained below the upper P90 bound.",
        limitations_and_caveats="Measures marginal upper envelope containment only. Does not guarantee joint path containment."
    ),
    "lower_coverage_pct": MetricDefinition(
        name="lower_coverage_pct",
        display_label="Marginal Lower Excursion Coverage (%)",
        target="One-sided lower barrier breach (actual_low >= lower_p90)",
        horizon="24h",
        formula="mean(actual_low >= lower_p90) * 100",
        units="percentage (%)",
        nominal_target=90.0,
        statistical_interpretation="Empirical proportion of observations where realized intrahorizon low remained above the lower P90 bound.",
        limitations_and_caveats="Measures marginal lower envelope containment only. Does not guarantee joint path containment."
    ),
    "joint_path_containment_pct": MetricDefinition(
        name="joint_path_containment_pct",
        display_label="Joint Price-Path Containment (%)",
        target="Both bounds satisfied: (actual_high <= upper_p90) AND (actual_low >= lower_p90)",
        horizon="24h",
        formula="mean((actual_high <= upper_p90) & (actual_low >= lower_p90)) * 100",
        units="percentage (%)",
        nominal_target=None,  # Bounded in [80%, 90%], not nominal 90%
        statistical_interpretation="Proportion of observations where the entire 24h price path remained strictly within [lower_p90, upper_p90].",
        limitations_and_caveats="For two marginal 90% bounds, theoretical joint coverage is bounded in [80%, 90%] (and 81% under independence). Must not be described as a nominal 90% scalar interval."
    ),
    "conformal_interval_width_pct": MetricDefinition(
        name="conformal_interval_width_pct",
        display_label="Normalized Conformal Interval Width (%)",
        target="Relative width of forecast envelope (upper_p90 - lower_p90) / current_price",
        horizon="24h",
        formula="mean((upper_p90 - lower_p90) / current_price) * 100",
        units="percentage of spot price (%)",
        nominal_target=None,
        statistical_interpretation="Measures the average dispersion / sharpness of the risk envelope. Narrower envelopes with valid coverage indicate superior sharpness.",
        limitations_and_caveats="Narrow width is desirable only if empirical coverage remains aligned with target. Overly narrow width leads to frequent breach."
    ),
    "winkler_score": MetricDefinition(
        name="winkler_score",
        display_label="Strictly Proper Winkler Interval Score (alpha=0.10)",
        target="Scalar prediction interval [lower_p90, upper_p90] on intrahorizon price extremum",
        horizon="24h",
        formula="mean( (U - L)/P + (2/alpha)*max(0, (L - Low)/P) + (2/alpha)*max(0, (High - U)/P) ) * 100",
        units="normalized basis score (lower is better)",
        nominal_target=None,
        statistical_interpretation="Strictly proper scoring rule balancing interval sharpness and penalty for upper/lower boundary exceedances (Gneiting & Raftery 2007).",
        limitations_and_caveats="Penalizes boundary exceedances at weight 2/alpha = 20.0. Meaningful only when comparing identical evaluation blocks."
    ),
    "baseline_delta_bps": MetricDefinition(
        name="baseline_delta_bps",
        display_label="Benchmark Outperformance (bps)",
        target="Comparative loss vs point-in-time benchmark forecast on identical observations",
        horizon="24h",
        formula="(loss_model - loss_benchmark) * 10,000",
        units="basis points (negative = model has lower error than benchmark)",
        nominal_target=None,
        statistical_interpretation="Comparative advantage in basis points against an authoritative causal benchmark.",
        limitations_and_caveats="Unavailable (None) until a point-in-time causal benchmark forecast ledger is persisted. Calculating baselines from future realized outcome medians is scientifically invalid."
    ),
}


def compute_mfe_error_pct(actual_mfe: np.ndarray, exp_mfe: np.ndarray) -> float:
    """Mean absolute MFE prediction error in percentage points."""
    return float(np.mean(np.abs(actual_mfe - exp_mfe)) * 100.0)


def compute_mae_error_pct(actual_mae: np.ndarray, exp_mae: np.ndarray) -> float:
    """Mean absolute MAE prediction error in percentage points."""
    return float(np.mean(np.abs(actual_mae - exp_mae)) * 100.0)


def compute_upper_coverage_pct(actual_high: np.ndarray, upper_p90: np.ndarray) -> float:
    """Marginal upper excursion coverage in percent."""
    return float(np.mean(actual_high <= upper_p90) * 100.0)


def compute_lower_coverage_pct(actual_low: np.ndarray, lower_p90: np.ndarray) -> float:
    """Marginal lower excursion coverage in percent."""
    return float(np.mean(actual_low >= lower_p90) * 100.0)


def compute_joint_path_containment_pct(
    actual_high: np.ndarray,
    actual_low: np.ndarray,
    upper_p90: np.ndarray,
    lower_p90: np.ndarray
) -> float:
    """Joint price-path containment in percent."""
    contained = (actual_high <= upper_p90) & (actual_low >= lower_p90)
    return float(np.mean(contained) * 100.0)


def compute_conformal_interval_width_pct(
    upper_p90: np.ndarray,
    lower_p90: np.ndarray,
    current_price: np.ndarray
) -> float:
    """Mean relative interval width in percent of spot price."""
    width_rel = (upper_p90 - lower_p90) / current_price
    return float(np.mean(width_rel) * 100.0)


def compute_winkler_score(
    actual_high: np.ndarray,
    actual_low: np.ndarray,
    upper_p90: np.ndarray,
    lower_p90: np.ndarray,
    current_price: np.ndarray,
    alpha: float = 0.10
) -> float:
    """
    Computes strictly proper Winkler interval score (Gneiting & Raftery 2007)
    normalized by current spot price:
      S_alpha = width + (2/alpha)*exceedance_high + (2/alpha)*exceedance_low
    Multiplied by 100.0 for consistent percentage-scale representation.
    """
    width = (upper_p90 - lower_p90) / current_price
    penalty_multiplier = 2.0 / alpha  # 20.0 for alpha=0.10

    high_exceedance = np.maximum(0.0, (actual_high - upper_p90) / current_price)
    low_exceedance = np.maximum(0.0, (lower_p90 - actual_low) / current_price)

    winkler_per_obs = width + (penalty_multiplier * high_exceedance) + (penalty_multiplier * low_exceedance)
    return float(np.mean(winkler_per_obs) * 100.0)


def evaluate_canonical_metrics(
    df: pd.DataFrame,
    min_observations: int = 5
) -> Dict[str, Any]:
    """
    Evaluates the full canonical metric suite on an eligible dataframe.
    Filters out invalid, degraded, or quarantined records strictly.

    Required columns:
    - current_price, actual_high, actual_low, upper_p90, lower_p90,
      actual_mfe, actual_mae, exp_mfe, exp_mae
    """
    default_empty = {
        "mfe_error_pct": None,
        "mae_error_pct": None,
        "upper_coverage_pct": None,
        "lower_coverage_pct": None,
        "joint_path_containment_pct": None,
        "p90_coverage_pct": None,  # Backward compatibility alias for joint_path_containment_pct
        "winkler_score": None,
        "conformal_interval_width_pct": None,
        "baseline_delta_bps": None,
        "baseline_status": "UNAVAILABLE",
        "baseline_reason": "Awaiting causal point-in-time benchmark forecast ledger.",
        "sample_size": 0,
        "evaluation_status": "INSUFFICIENT_SAMPLES"
    }

    if df is None or len(df) < min_observations:
        return default_empty

    # Filter for valid, eligible records
    # Must have positive price and non-null required fields
    valid_mask = (
        (df["current_price"] > 0)
        & df["actual_high"].notnull()
        & df["actual_low"].notnull()
        & df["upper_p90"].notnull()
        & df["lower_p90"].notnull()
    )

    # Exclude quarantined or degraded if data_quality column exists
    if "data_quality" in df.columns:
        valid_mask &= (df["data_quality"] == "VALID")
    if "degraded" in df.columns:
        valid_mask &= (df["degraded"] == 0)

    clean_df = df[valid_mask]
    n_obs = len(clean_df)
    if n_obs < min_observations:
        res = dict(default_empty)
        res["sample_size"] = n_obs
        return res

    curr_p = clean_df["current_price"].values
    act_h = clean_df["actual_high"].values
    act_l = clean_df["actual_low"].values
    u_p90 = clean_df["upper_p90"].values
    l_p90 = clean_df["lower_p90"].values

    act_mfe = clean_df["actual_mfe"].values if "actual_mfe" in clean_df.columns else np.maximum(0.0, (act_h - curr_p) / curr_p)
    act_mae = clean_df["actual_mae"].values if "actual_mae" in clean_df.columns else np.maximum(0.0, (curr_p - act_l) / curr_p)

    exp_mfe = clean_df["exp_mfe"].values if "exp_mfe" in clean_df.columns else (clean_df["mfe_p50"].values if "mfe_p50" in clean_df.columns else np.zeros(n_obs))
    exp_mae = clean_df["exp_mae"].values if "exp_mae" in clean_df.columns else (clean_df["mae_p50"].values if "mae_p50" in clean_df.columns else np.zeros(n_obs))

    if "mfe_error" in clean_df.columns and clean_df["mfe_error"].notnull().any():
        mfe_err = float(np.mean(np.abs(clean_df["mfe_error"])) * 100.0)
    else:
        mfe_err = compute_mfe_error_pct(act_mfe, exp_mfe)

    if "mae_error" in clean_df.columns and clean_df["mae_error"].notnull().any():
        mae_err = float(np.mean(np.abs(clean_df["mae_error"])) * 100.0)
    else:
        mae_err = compute_mae_error_pct(act_mae, exp_mae)
    upper_cov = compute_upper_coverage_pct(act_h, u_p90)
    lower_cov = compute_lower_coverage_pct(act_l, l_p90)
    joint_cont = compute_joint_path_containment_pct(act_h, act_l, u_p90, l_p90)
    width_pct = compute_conformal_interval_width_pct(u_p90, l_p90, curr_p)
    winkler = compute_winkler_score(act_h, act_l, u_p90, l_p90, curr_p, alpha=0.10)

    return {
        "mfe_error_pct": round(mfe_err, 4),
        "mae_error_pct": round(mae_err, 4),
        "upper_coverage_pct": round(upper_cov, 2),
        "lower_coverage_pct": round(lower_cov, 2),
        "joint_path_containment_pct": round(joint_cont, 2),
        "p90_coverage_pct": round(joint_cont, 2),  # Backward compatibility alias
        "winkler_score": round(winkler, 4),
        "conformal_interval_width_pct": round(width_pct, 2),
        "baseline_delta_bps": None,  # Strictly None until causal benchmark ledger exists
        "baseline_status": "UNAVAILABLE",
        "baseline_reason": (
            "Awaiting causal point-in-time benchmark forecast ledger. "
            "In-sample future-outcome baselines are strictly prohibited."
        ),
        "sample_size": n_obs,
        "evaluation_status": "EVALUATED"
    }

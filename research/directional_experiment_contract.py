"""
research/directional_experiment_contract.py — Fixed Evaluation Contract for BTC Directional Experiments
=======================================================================================================
Establishes an immutable, pre-registered evaluation contract for all prospective
directional forecasting experiments in BTCognitive.

Architectural Guarantees:
1. Target & Horizon Invariant:
   - Target: Binary sign of forward 1-hour log return: y_t = 1 if ln(P_{t+1}/P_t) > 0 else 0.
   - Horizon: 1 hour (strictly 1 bar).
2. Data & Split Protocol:
   - Asset: BTC/USD (Coinbase hourly close prices from data/raw/ohlcv.parquet).
   - Validation Scheme: Purged expanding window (5 folds, 33,919 evaluation bars).
   - Purge / Embargo: 1-hour embargo between train and test windows to eliminate boundary leakage.
3. Statistical Testing:
   - Baseline: 4-lag return model (directional-gbm-4lag-v1) achieving 53.28% accuracy.
   - Inference: Paired moving-block bootstrap (block size = 24 hours, 10,000 resamples).
   - Test of Independence: McNemar contingency test on paired prediction outcomes.
4. Causal Thresholding Protocol:
   - Confidence hurdles MUST be computed exclusively using training fold distributions.
   - Retrospective ranking on test-set probabilities is PROHIBITED.
5. Trading Friction Protocol:
   - Round-trip execution drag: 14 bps (7 bps entry taker + 7 bps exit taker).
   - Model is NOT considered viable for trading unless net expected return after friction is positive.
6. Target Feasibility Threshold:
   - 70% directional accuracy target is mathematically unproven and empirically unsupported.
   - Any claim of superior performance requires replication across multiple market regimes without post-hoc parameter tuning.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Any


@dataclass(frozen=True)
class DirectionalEvaluationContract:
    contract_version: str = "DIRECTIONAL-EVAL-v1.0"
    asset: str = "BTC/USD"
    data_source: str = "data/raw/ohlcv.parquet (Coinbase Hourly)"
    target_definition: str = "y_t = 1 if ln(Close_{t+1} / Close_t) > 0 else 0"
    prediction_horizon: str = "1 hour (1 bar)"
    baseline_model_id: str = "directional-gbm-4lag-v1"
    baseline_feature_schema: List[str] = ("ret_lag1", "ret_lag2", "ret_lag3", "ret_lag4")
    baseline_unconditional_accuracy: float = 0.5328
    validation_protocol: str = "Purged expanding window cross-validation (5 folds)"
    minimum_test_samples: int = 30000
    purge_embargo_bars: int = 1
    statistical_significance_level: float = 0.01
    bootstrap_method: str = "Paired moving-block bootstrap (block_size=24h, 10,000 iterations)"
    contingency_test: str = "McNemar test on discordant paired classifications"
    threshold_calibration_method: str = "Strictly causal in-train quantile selection"
    assumed_friction_per_leg_bps: float = 7.0
    assumed_round_trip_friction_bps: float = 14.0
    economic_hurdle: str = "Net expected return after friction > 0.0 bps/bar"
    prohibited_practices: List[str] = (
        "Post-hoc test label threshold optimization (retrospective lookahead)",
        "Selective test period exclusion (cherry-picking regimes)",
        "Conflating volatility quantile containment with directional accuracy",
        "Claiming 70% directional accuracy without audited out-of-sample proof",
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


DIRECTIONAL_EVAL_CONTRACT = DirectionalEvaluationContract()


def get_directional_evaluation_contract() -> Dict[str, Any]:
    """Returns the immutable evaluation contract for directional forecasting."""
    return DIRECTIONAL_EVAL_CONTRACT.to_dict()

"""
models/authoritative_model_registry.py — Authoritative Model Identity Single Source of Truth
=============================================================================================
Provides the single traceable source of truth for model identity, governance status,
target semantics, required features, and operational authorization across BTCognitive.

Architectural Principles:
1. Strict Role Segregation:
   - PRODUCTION_VOLATILITY: Actively authorized for production volatility forecasting and C2 risk envelopes.
   - DIRECTIONAL_RESEARCH_BENCHMARK: Strictly offline research; NOT authorized for live capital or production inference.
   - ARCHIVED_RESEARCH_CANDIDATE: Historical candidate whose provenance was superseded; fails closed.
   - FOUNDATION_RESEARCH: Research exploration foundation time-series models.
2. No Semantic Conflation:
   - A volatility risk-envelope (HAR-RS-DOW / C2) is NEVER labeled as a directional predictor.
   - Quantile containment (92.84%) is NEVER reported as directional accuracy.
   - Offline directional accuracy (53.28%) is NEVER represented as an approved production trade signal.
"""

import os
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Root directory of the repository
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class ModelClassification(str, Enum):
    PRODUCTION_VOLATILITY = "PRODUCTION_VOLATILITY"
    DIRECTIONAL_RESEARCH_BENCHMARK = "DIRECTIONAL_RESEARCH_BENCHMARK"
    ARCHIVED_RESEARCH_CANDIDATE = "ARCHIVED_RESEARCH_CANDIDATE"
    FOUNDATION_RESEARCH = "FOUNDATION_RESEARCH"
    EXPERIMENTAL_CHALLENGER = "EXPERIMENTAL_CHALLENGER"
    PRICE_FORECAST_RESEARCH = "PRICE_FORECAST_RESEARCH"


class AuthorizationStatus(str, Enum):
    AUTHORIZED_FOR_PRODUCTION = "AUTHORIZED_FOR_PRODUCTION"
    OFFLINE_RESEARCH_ONLY = "OFFLINE_RESEARCH_ONLY"
    BLOCKED_PROVENANCE_UNVERIFIED = "BLOCKED_PROVENANCE_UNVERIFIED"
    BLOCKED_AUDIT_FAILURE = "BLOCKED_AUDIT_FAILURE"


@dataclass(frozen=True)
class ModelIdentityRecord:
    canonical_id: str
    version: str
    display_name: str
    classification: ModelClassification
    authorization_status: AuthorizationStatus
    model_architecture: str
    artifact_rel_path: str
    artifact_sha256: str
    scientific_contract_hash: Optional[str]
    forecast_target: str
    forecast_horizon: str
    output_units: str
    output_interpretation: str
    directional_prediction_capability: bool
    feature_schema: List[str]
    data_source_dependencies: List[str]
    uncertainty_engine: str
    empirical_validation_summary: str
    applicable_limitations: str
    production_endpoints: List[str]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["classification"] = self.classification.value
        d["authorization_status"] = self.authorization_status.value
        return d


# ── Authoritative Model Catalog ──────────────────────────────────────────

ACTIVE_PRODUCTION_MODEL = ModelIdentityRecord(
    canonical_id="HAR-RS-DOW-v1.0",
    version="1.0.0",
    display_name="HAR Realized Semivariance with Day-of-Week Seasonality (HAR-RS-DOW)",
    classification=ModelClassification.PRODUCTION_VOLATILITY,
    authorization_status=AuthorizationStatus.AUTHORIZED_FOR_PRODUCTION,
    model_architecture="Heterogeneous Autoregressive OLS with Semivariances and Day-of-Week Seasonality",
    artifact_rel_path="experiments/results/freeze/har_rs_dow_v1.joblib",
    artifact_sha256="750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b",
    scientific_contract_hash="841deba5fb30118bea849f93ebc9fb7d1984d74fd2d709013544c6d5db94cf07",
    forecast_target="Annualized 7-Day Realized Variance (rv7d_var_ann)",
    forecast_horizon="168h (7 calendar days)",
    output_units="Annualized Variance (decimal, e.g. 0.1930) and equivalent Annualized Volatility (%)",
    output_interpretation=(
        "Parametric point forecast of 7-day integrated volatility. "
        "Does NOT predict price direction (+/- return sign). "
        "Used exclusively for volatility regime assessment and risk envelopes."
    ),
    directional_prediction_capability=False,
    feature_schema=[
        "log_rv_down_1d",
        "log_rv_up_1d",
        "log_rv7d_var_ann_lag",
        "log_rv30d_var_ann",
        "dow_1",
        "dow_2",
        "dow_3",
        "dow_4",
        "dow_5",
        "dow_6",
    ],
    data_source_dependencies=["data/raw/ohlcv.parquet"],
    uncertainty_engine="C2 Dependence-Aware Conformal Prediction (alpha=0.10, 90% nominal envelope, strictly causal delayed resolution)",
    empirical_validation_summary="84.89% causal holdout containment (95% CI: [73.14%, 93.14%]) | 92.84% pre-2026 calibration (QLIKE: 0.19300). Validated in VOL-EDGE-01 & Stage 12 audit.",
    applicable_limitations="Not a directional alpha model; does not recommend buy/sell positions; requires hourly OHLCV. Serves 168h realized variance volatility intelligence only. Live trading is strictly disabled.",
    production_endpoints=["/api/terminal/live", "/api/terminal/model-identity"]
)

DIRECTIONAL_RESEARCH_BASELINE = ModelIdentityRecord(
    canonical_id="directional-gbm-4lag-v1",
    version="1.0.0",
    display_name="LightGBM 4-Lag Directional Return Classifier",
    classification=ModelClassification.DIRECTIONAL_RESEARCH_BENCHMARK,
    authorization_status=AuthorizationStatus.OFFLINE_RESEARCH_ONLY,
    model_architecture="Gradient Boosted Decision Trees (LightGBM, max_depth=3, n_estimators=100)",
    artifact_rel_path="experiments/results/stage3_validation/stage3_directional_pipeline_results.json",
    artifact_sha256="stage3-validation-provenance",
    scientific_contract_hash=None,
    forecast_target="Sign of 1-Hour Forward Log Return (ret_1h_fwd > 0)",
    forecast_horizon="1h (1 hour)",
    output_units="Upward Return Probability [0.0, 1.0] and Binary Direction (+1 / -1)",
    output_interpretation=(
        "Offline directional research baseline. "
        "Achieves 53.28% out-of-sample directional accuracy (33,919 evaluations across 5 purged folds). "
        "Statistically indistinguishable from 15-feature complex pipeline (53.14%, p=0.4101). "
        "After 7 bps transaction friction, net simulated return is -13.07 bps/active bar. "
        "NOT AUTHORIZED FOR LIVE PRODUCTION INFERENCE OR CAPITAL DEPLOYMENT."
    ),
    directional_prediction_capability=True,
    feature_schema=["ret_lag1", "ret_lag2", "ret_lag3", "ret_lag4"],
    data_source_dependencies=["data/raw/ohlcv.parquet"],
    uncertainty_engine="Moving-block paired bootstrap confidence intervals (block_size=24h, 10,000 resamples)",
    empirical_validation_summary="53.28% accuracy (95% CI: [52.74%, 53.82%]). Causal in-train selective accuracy: 55.26% at 4.15% coverage.",
    applicable_limitations="High turnover leads to negative net expectancy after transaction friction. Unconditional 70% accuracy is unsupported.",
    production_endpoints=["/api/research/directional-audit"]
)

ARCHIVED_EXCURSION_CANDIDATE = ModelIdentityRecord(
    canonical_id="ridge_excursion_core",
    version="v3.0.0-excursion-ridge-conformal",
    display_name="Ridge MFE/MAE 24h Excursion Conformal Regressor (Legacy Candidate)",
    classification=ModelClassification.ARCHIVED_RESEARCH_CANDIDATE,
    authorization_status=AuthorizationStatus.BLOCKED_PROVENANCE_UNVERIFIED,
    model_architecture="Ridge Regression (L2) with Conformal Quantile Residual Mapping",
    artifact_rel_path="models/range_forecaster.py",
    artifact_sha256="legacy-unverified-excursion-hash",
    scientific_contract_hash=None,
    forecast_target="24h Maximum Favorable & Adverse Price Excursions (MFE/MAE)",
    forecast_horizon="24h (24 hours)",
    output_units="Fractional price excursion bounds (P10, P50, P90)",
    output_interpretation=(
        "Historical candidate from August 21, 2026. "
        "Superseded by the August 25, 2026 repaired scientific freeze contract (HAR-RS-DOW-v1.0). "
        "Preserved for audit lineage; production routes fail closed."
    ),
    directional_prediction_capability=False,
    feature_schema=["vol_24h", "rsi_14", "atr_14", "funding_rate", "mvrv_zscore"],
    data_source_dependencies=["data/raw/ohlcv.parquet", "data/raw/funding.parquet", "data/raw/onchain.parquet"],
    uncertainty_engine="Conformal Quantile Mapping (P10..P90)",
    empirical_validation_summary="90.32% joint path containment across 31 historical blocks (August 2026).",
    applicable_limitations="Superseded by HAR-RS-DOW freeze. Not authorized for live inference.",
    production_endpoints=["/prediction/range (BLOCKED)"]
)

CHALLENGER_HAR_QLIKE = ModelIdentityRecord(
    canonical_id="HAR-QLIKE-v1.0",
    version="1.0.0",
    display_name="HAR-RS-DOW Loss-Coherent QLIKE Challenger (Puke & Schweikert 2026)",
    classification=ModelClassification.EXPERIMENTAL_CHALLENGER,
    authorization_status=AuthorizationStatus.OFFLINE_RESEARCH_ONLY,
    model_architecture="Heterogeneous Autoregressive Loss-Coherent QLIKE Minimizer with L2 Regularization",
    artifact_rel_path="experiments/results/research_improvement/har_qlike_v1.joblib",
    artifact_sha256="experiments/results/research_improvement/har_qlike_v1.joblib",
    scientific_contract_hash="experiments/results/research_improvement/preregistered_evaluation_manifest.json",
    forecast_target="Annualized 7-Day Realized Variance (rv7d_var_ann)",
    forecast_horizon="168h (7 calendar days)",
    output_units="Annualized Realized Variance (decimal)",
    output_interpretation=(
        "Loss-coherent point forecast of 7-day realized variance estimated by direct sample QLIKE minimization. "
        "Evaluated against HAR-RS-DOW-v1.0. Achieves 8.77% raw QLIKE reduction, but Diebold-Mariano test "
        "indicates difference is statistically equal (DM = +0.5132, p = 0.3039). Preserved in research register."
    ),
    directional_prediction_capability=False,
    feature_schema=[
        "log_rv_down_1d",
        "log_rv_up_1d",
        "log_rv7d_var_ann_lag",
        "log_rv30d_var_ann",
        "dow_1",
        "dow_2",
        "dow_3",
        "dow_4",
        "dow_5",
        "dow_6",
    ],
    data_source_dependencies=["data/raw/ohlcv.parquet"],
    uncertainty_engine="C2 Dependence-Aware Conformal Prediction (alpha=0.10, strictly causal delayed resolution)",
    empirical_validation_summary="84.22% causal holdout containment | Out-of-sample QLIKE: 0.19598 vs Baseline 0.21483 (p=0.304).",
    applicable_limitations="Research challenger; failed DM statistical significance gate (p >= 0.05); offline research only; not authorized for production.",
    production_endpoints=["/api/research/experiments (OFFLINE_RESEARCH)"]
)

BASELINE_HAR_24H = ModelIdentityRecord(
    canonical_id="HAR-RS-DOW-24H",
    version="1.0.0",
    display_name="HAR-24H Conventional Log-Variance OLS Benchmark",
    classification=ModelClassification.EXPERIMENTAL_CHALLENGER,
    authorization_status=AuthorizationStatus.OFFLINE_RESEARCH_ONLY,
    model_architecture="Conventional Heterogeneous Autoregressive OLS on ln(rv24h_var_ann)",
    artifact_rel_path="experiments/results/research_improvement/har_ols_24h_v1.joblib",
    artifact_sha256="7a247cf1c0a9639ada911111d57bd58db1794f09a8ca749112b33fa848f10ac1",
    scientific_contract_hash="7ea814579b7297430a87e0bf142ed4ae5c30ff5554da907de2cb71fda295d6f4",
    forecast_target="Annualized 24-Hour Realized Variance (rv24h_var_ann)",
    forecast_horizon="24h (1 calendar day)",
    output_units="Annualized Realized Variance (decimal, hourly-sampled proxy)",
    output_interpretation=(
        "Standard OLS HAR benchmark on 24-hour annualized realized variance proxy. "
        "Evaluated on daily non-overlapping origins (QLIKE = 0.37259, RMSE = 0.20327). "
        "Strictly offline research model."
    ),
    directional_prediction_capability=False,
    feature_schema=["log_rv_1d", "log_rv_7d", "log_rv_30d"],
    data_source_dependencies=["data/raw/ohlcv.parquet"],
    uncertainty_engine="Standard OLS residuals",
    empirical_validation_summary="Daily non-overlapping QLIKE: 0.37259, RMSE: 0.20327 (N=243, 00:00 UTC).",
    applicable_limitations="Hourly-sampled proxy; does not predict directional price sign; offline research only.",
    production_endpoints=["/api/research/experiments (OFFLINE_RESEARCH)"]
)

CHALLENGER_HAR_QLIKE_24H = ModelIdentityRecord(
    canonical_id="HAR-QLIKE-24H",
    version="1.0.0",
    display_name="HAR-QLIKE-24H Coherent Volatility Challenger (Puke & Schweikert 2026)",
    classification=ModelClassification.EXPERIMENTAL_CHALLENGER,
    authorization_status=AuthorizationStatus.OFFLINE_RESEARCH_ONLY,
    model_architecture="Heterogeneous Autoregressive QLIKE Loss-Coherent Minimizer with L2 Regularization",
    artifact_rel_path="experiments/results/research_improvement/har_qlike_24h_v1.joblib",
    artifact_sha256="fbc8818da9cfc378ce3ab32e3ce6781b9e59815c38515302fe4128b0eeefc5f2",
    scientific_contract_hash="7ea814579b7297430a87e0bf142ed4ae5c30ff5554da907de2cb71fda295d6f4",
    forecast_target="Annualized 24-Hour Realized Variance (rv24h_var_ann)",
    forecast_horizon="24h (1 calendar day)",
    output_units="Annualized Realized Variance (decimal, hourly-sampled proxy)",
    output_interpretation=(
        "Loss-coherent point forecast of next 24-hour realized variance directly minimizing sample QLIKE. "
        "Evaluated on daily non-overlapping origins (QLIKE = 0.31729 vs OLS 0.37259, +14.84% gain). "
        "Diebold-Mariano test with HLN correction yields DM = +0.9874, p = 0.1622 (p >= 0.05). "
        "Retained in research register; NOT authorized for production."
    ),
    directional_prediction_capability=False,
    feature_schema=["log_rv_1d", "log_rv_7d", "log_rv_30d"],
    data_source_dependencies=["data/raw/ohlcv.parquet"],
    uncertainty_engine="Empirical residual dispersion",
    empirical_validation_summary="Daily non-overlapping QLIKE: 0.31729 (+14.84% gain vs OLS, HLN p=0.1622); Hourly rolling QLIKE: 0.32419 (p=0.0735).",
    applicable_limitations="Research challenger; failed DM statistical significance hurdle (p >= 0.05); offline research only; not authorized for live production.",
    production_endpoints=["/api/research/experiments (OFFLINE_RESEARCH)"]
)

PRICE_FORECAST_PERSISTENCE = ModelIdentityRecord(
    canonical_id="price-forecast-persistence-rw",
    version="1.0.0",
    display_name="BTCUSD Future-Price Persistence / Random-Walk Benchmark",
    classification=ModelClassification.PRICE_FORECAST_RESEARCH,
    authorization_status=AuthorizationStatus.OFFLINE_RESEARCH_ONLY,
    model_architecture="Zero-drift Persistence Random Walk (P_{t+h} = P_t)",
    artifact_rel_path="engine/price_forecast_engine.py",
    artifact_sha256="engine/price_forecast_engine.py",
    scientific_contract_hash=None,
    forecast_target="Future BTCUSD Closing Price at 1h, 4h, and 24h horizons",
    forecast_horizon="1h, 4h, 24h",
    output_units="USD (Future Spot Closing Price)",
    output_interpretation=(
        "Standard statistical random-walk persistence benchmark. "
        "Assumes expected forward log return is 0.0. "
        "Serves as the primary null hypothesis benchmark for all price prediction models."
    ),
    directional_prediction_capability=False,
    feature_schema=["spot_price"],
    data_source_dependencies=["data/raw/ohlcv.parquet"],
    uncertainty_engine="Rolling historical return quantiles (30d empirical)",
    empirical_validation_summary="Out-of-sample benchmark across 41,273 hourly candles. Primary hurdle model in walk-forward tournament.",
    applicable_limitations="Non-directional persistence benchmark; does not guarantee zero future variance; offline research only.",
    production_endpoints=["/api/prediction/price/forecast"]
)

PRICE_FORECAST_RIDGE = ModelIdentityRecord(
    canonical_id="price-forecast-ridge-lagged",
    version="1.0.0",
    display_name="BTCUSD Future-Price Regularized Ridge Regressor",
    classification=ModelClassification.PRICE_FORECAST_RESEARCH,
    authorization_status=AuthorizationStatus.OFFLINE_RESEARCH_ONLY,
    model_architecture="L2-Regularized Ridge Regression on Causal Lagged Returns and Volatility",
    artifact_rel_path="engine/price_forecast_engine.py",
    artifact_sha256="engine/price_forecast_engine.py",
    scientific_contract_hash=None,
    forecast_target="Future BTCUSD Closing Price at 1h, 4h, and 24h horizons",
    forecast_horizon="1h, 4h, 24h",
    output_units="USD (Future Spot Closing Price)",
    output_interpretation=(
        "Regularized linear regression using strictly point-in-time lagged returns (1h, 4h, 24h, 168h) "
        "and realized volatility proxies. Evaluated against persistence baseline via HLN test."
    ),
    directional_prediction_capability=True,
    feature_schema=["ret_1h", "ret_4h", "ret_24h", "ret_168h", "vol_24h", "vol_168h"],
    data_source_dependencies=["data/raw/ohlcv.parquet"],
    uncertainty_engine="Rolling empirical return distribution quantiles (P10, P50, P90)",
    empirical_validation_summary="Walk-forward OOS evaluation: Does not demonstrate statistically significant edge over random walk after HLN correction (p >= 0.05).",
    applicable_limitations="Experimental research candidate; does not beat random walk with statistical significance; offline research only; live trading disabled.",
    production_endpoints=["/api/prediction/price/forecast"]
)

PRICE_FORECAST_DRIFT = ModelIdentityRecord(
    canonical_id="price-forecast-rolling-drift",
    version="1.0.0",
    display_name="BTCUSD Future-Price Rolling Historical Drift Benchmark",
    classification=ModelClassification.PRICE_FORECAST_RESEARCH,
    authorization_status=AuthorizationStatus.OFFLINE_RESEARCH_ONLY,
    model_architecture="Rolling Historical Average Drift (168h window)",
    artifact_rel_path="engine/price_forecast_engine.py",
    artifact_sha256="engine/price_forecast_engine.py",
    scientific_contract_hash=None,
    forecast_target="Future BTCUSD Closing Price at 1h, 4h, and 24h horizons",
    forecast_horizon="1h, 4h, 24h",
    output_units="USD (Future Spot Closing Price)",
    output_interpretation=(
        "Extrapolates recent 7-day average hourly price drift. "
        "Evaluated against zero-drift random-walk persistence baseline."
    ),
    directional_prediction_capability=True,
    feature_schema=["rolling_drift_168h"],
    data_source_dependencies=["data/raw/ohlcv.parquet"],
    uncertainty_engine="Rolling empirical return distribution quantiles (P10, P50, P90)",
    empirical_validation_summary="Walk-forward OOS evaluation: Does not demonstrate statistically significant edge over random walk after HLN correction (p >= 0.05).",
    applicable_limitations="Experimental research baseline; offline research only; live trading disabled.",
    production_endpoints=["/api/prediction/price/forecast"]
)

# Registry dictionary
_REGISTRY: Dict[str, ModelIdentityRecord] = {
    ACTIVE_PRODUCTION_MODEL.canonical_id: ACTIVE_PRODUCTION_MODEL,
    ACTIVE_PRODUCTION_MODEL.version: ACTIVE_PRODUCTION_MODEL,
    DIRECTIONAL_RESEARCH_BASELINE.canonical_id: DIRECTIONAL_RESEARCH_BASELINE,
    DIRECTIONAL_RESEARCH_BASELINE.version: DIRECTIONAL_RESEARCH_BASELINE,
    ARCHIVED_EXCURSION_CANDIDATE.canonical_id: ARCHIVED_EXCURSION_CANDIDATE,
    ARCHIVED_EXCURSION_CANDIDATE.version: ARCHIVED_EXCURSION_CANDIDATE,
    CHALLENGER_HAR_QLIKE.canonical_id: CHALLENGER_HAR_QLIKE,
    CHALLENGER_HAR_QLIKE.version: CHALLENGER_HAR_QLIKE,
    BASELINE_HAR_24H.canonical_id: BASELINE_HAR_24H,
    BASELINE_HAR_24H.version: BASELINE_HAR_24H,
    CHALLENGER_HAR_QLIKE_24H.canonical_id: CHALLENGER_HAR_QLIKE_24H,
    CHALLENGER_HAR_QLIKE_24H.version: CHALLENGER_HAR_QLIKE_24H,
    PRICE_FORECAST_PERSISTENCE.canonical_id: PRICE_FORECAST_PERSISTENCE,
    PRICE_FORECAST_PERSISTENCE.version: PRICE_FORECAST_PERSISTENCE,
    PRICE_FORECAST_DRIFT.canonical_id: PRICE_FORECAST_DRIFT,
    PRICE_FORECAST_DRIFT.version: PRICE_FORECAST_DRIFT,
    PRICE_FORECAST_RIDGE.canonical_id: PRICE_FORECAST_RIDGE,
    PRICE_FORECAST_RIDGE.version: PRICE_FORECAST_RIDGE,
}


def get_active_production_model(runtime_readiness: Optional[Dict[str, Any]] = None) -> ModelIdentityRecord:
    """
    Returns the single authoritative production model identity.
    Enforces the invariant that the static registry CANNOT independently override
    a failed runtime gate. If runtime_readiness indicates unverified or blocked status,
    the model status fails closed.
    """
    if runtime_readiness is not None and not runtime_readiness.get("authorized", False):
        from dataclasses import replace
        reason = runtime_readiness.get("reason", "Runtime gate verification failed.")
        code = runtime_readiness.get("reason_code", "BLOCKED_AUDIT_FAILURE")
        status = AuthorizationStatus.BLOCKED_AUDIT_FAILURE
        if "PROVENANCE" in code:
            status = AuthorizationStatus.BLOCKED_PROVENANCE_UNVERIFIED
        return replace(
            ACTIVE_PRODUCTION_MODEL,
            authorization_status=status,
            applicable_limitations=f"Production inference gated ({code}): {reason}"
        )
    return ACTIVE_PRODUCTION_MODEL


def get_directional_research_baseline() -> ModelIdentityRecord:
    """Returns the authoritative directional research baseline model identity."""
    return DIRECTIONAL_RESEARCH_BASELINE


def get_model_identity(identifier: str) -> Optional[ModelIdentityRecord]:
    """Retrieves model identity by canonical ID or version string."""
    return _REGISTRY.get(identifier)


def list_authoritative_models() -> List[Dict[str, Any]]:
    """Returns all distinct authoritative model records as dictionaries."""
    seen = set()
    records = []
    for m in [
        ACTIVE_PRODUCTION_MODEL,
        DIRECTIONAL_RESEARCH_BASELINE,
        ARCHIVED_EXCURSION_CANDIDATE,
        CHALLENGER_HAR_QLIKE,
        BASELINE_HAR_24H,
        CHALLENGER_HAR_QLIKE_24H,
    ]:
        if m.canonical_id not in seen:
            seen.add(m.canonical_id)
            records.append(m.to_dict())
    return records


def verify_production_model_alignment(endpoint: str, requested_model_id: str) -> bool:
    """
    Regression gate: verifies whether a requested model is permitted to serve production output.
    Returns True only if the requested model matches the authorized production model.
    """
    prod = get_active_production_model()
    if requested_model_id in [prod.canonical_id, prod.version]:
        return True
    return False


def get_active_model_registry() -> Dict[str, Dict[str, Any]]:
    """Returns authoritative registry dictionary keyed by canonical ID with standardized attributes."""
    reg = {}
    for m in [
        ACTIVE_PRODUCTION_MODEL,
        DIRECTIONAL_RESEARCH_BASELINE,
        ARCHIVED_EXCURSION_CANDIDATE,
        CHALLENGER_HAR_QLIKE,
        BASELINE_HAR_24H,
        CHALLENGER_HAR_QLIKE_24H,
    ]:
        d = m.to_dict()
        d["forecast_horizon"] = "168h" if m.canonical_id == ACTIVE_PRODUCTION_MODEL.canonical_id else ("24h" if "24H" in m.canonical_id else ("1h" if "gbm" in m.canonical_id else m.forecast_horizon))
        d["target_variable"] = "rv7d_var_ann" if m.canonical_id == ACTIVE_PRODUCTION_MODEL.canonical_id else ("rv24h_var_ann" if "24H" in m.canonical_id else m.forecast_target)
        d["directional_trading_authorized"] = False
        reg[m.canonical_id] = d
    return reg


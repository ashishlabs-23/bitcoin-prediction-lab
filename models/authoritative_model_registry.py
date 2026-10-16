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
    applicable_limitations="Not a directional alpha model; does not recommend buy/sell positions; requires hourly OHLCV.",
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

# Registry dictionary
_REGISTRY: Dict[str, ModelIdentityRecord] = {
    ACTIVE_PRODUCTION_MODEL.canonical_id: ACTIVE_PRODUCTION_MODEL,
    ACTIVE_PRODUCTION_MODEL.version: ACTIVE_PRODUCTION_MODEL,
    DIRECTIONAL_RESEARCH_BASELINE.canonical_id: DIRECTIONAL_RESEARCH_BASELINE,
    DIRECTIONAL_RESEARCH_BASELINE.version: DIRECTIONAL_RESEARCH_BASELINE,
    ARCHIVED_EXCURSION_CANDIDATE.canonical_id: ARCHIVED_EXCURSION_CANDIDATE,
    ARCHIVED_EXCURSION_CANDIDATE.version: ARCHIVED_EXCURSION_CANDIDATE,
}


def get_active_production_model() -> ModelIdentityRecord:
    """Returns the single authoritative production model identity."""
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
    for m in [ACTIVE_PRODUCTION_MODEL, DIRECTIONAL_RESEARCH_BASELINE, ARCHIVED_EXCURSION_CANDIDATE]:
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

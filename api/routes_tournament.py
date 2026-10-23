"""
api/routes_tournament.py — BTCUSD Strategy Tournament & Risk-First Selection API
================================================================================
FastAPI router serving the V12-V17 Strategy Tournament Intelligence:
- Current market regime & hysteresis tracking (Wilder ADX 14, EMA200/50/20, BBW).
- Predeclared strategy tournament evaluations across 3 cost scenarios.
- Risk-First Top-5 candidate leaderboard.
- Cost-aware economic trade eligibility & snapshot freshness validation.
- Real-time setup levels or diagnostic rejection reasons for current BTCUSD market.
- Strict non-execution invariants (live trading permanently DISABLED, Tier 2 GATED).
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.v12_strategy_tournament_engine import V12StrategyTournamentEngine

logger = logging.getLogger("btcognitive.routes_tournament")
router = APIRouter(prefix="/api/tournament", tags=["Strategy Tournament"])


# -----------------------------------------------------------------------------
# Explicit Pydantic Boundary Schemas (OWASP ASVS 5.0 Strict Structural Allowlist)
# -----------------------------------------------------------------------------

class EconomicEligibilityModel(BaseModel):
    status: str = Field(..., description="Trade eligibility status: TRADE_COST_ELIGIBLE, COST_INELIGIBLE, STALE_MARKET_DATA, etc.")
    is_eligible: bool = Field(..., description="Whether setup passes all structural, freshness, and economic friction gates")
    rejection_reason: Optional[str] = Field(None, description="Detailed diagnostic reason for economic rejection")
    structural_rules_valid: bool = Field(default=False, description="Whether strategy entry and geometry constraints are satisfied")
    market_inputs_valid: bool = Field(default=True, description="Whether required technical indicators are present, finite, and valid")
    market_data_fresh: bool = Field(default=True, description="Whether underlying closed candle snapshot is within freshness policy")
    regime_confirmed: bool = Field(default=True, description="Whether candidate market regime has achieved 3-candle persistence")
    gross_reward_usd: Optional[float] = Field(None, description="Gross profit distance to take-profit in USD")
    gross_reward_pct: Optional[float] = Field(None, description="Gross profit distance in decimal percentage")
    gross_reward_bps: Optional[float] = Field(None, description="Gross profit distance in basis points")
    gross_risk_usd: Optional[float] = Field(None, description="Gross loss distance to stop-loss in USD")
    gross_risk_pct: Optional[float] = Field(None, description="Gross loss distance in decimal percentage")
    gross_risk_bps: Optional[float] = Field(None, description="Gross loss distance in basis points")
    gross_reward_risk: Optional[float] = Field(None, description="Gross reward/risk ratio")
    cost_scenario: str = Field(default="COINBASE_RETAIL_87BPS", description="Active cost scenario key")
    cost_round_trip_bps: float = Field(default=87.0, description="Total modeled round-trip friction in basis points")
    cost_round_trip_usd: Optional[float] = Field(None, description="Modeled round-trip friction in USD")
    itemized_costs: Dict[str, Any] = Field(default_factory=dict, description="Itemized commission, spread, slippage, and funding")
    net_reward_usd: Optional[float] = Field(None, description="Net reward after round-trip friction in USD")
    net_reward_pct: Optional[float] = Field(None, description="Net reward in decimal percentage")
    net_reward_bps: Optional[float] = Field(None, description="Net reward in basis points")
    net_risk_usd: Optional[float] = Field(None, description="Net risk after round-trip friction in USD")
    net_risk_pct: Optional[float] = Field(None, description="Net risk in decimal percentage")
    net_risk_bps: Optional[float] = Field(None, description="Net risk in basis points")
    net_reward_risk: Optional[float] = Field(None, description="Net reward/risk ratio (can be negative)")
    target_covers_cost: bool = Field(default=False, description="True only if gross target exceeds round-trip cost friction")
    breakeven_hit_rate_pct: Optional[float] = Field(None, description="Implied breakeven win rate percentage")
    preview_only: bool = Field(default=True, description="Whether setup is restricted to preview-only research visualization")


class MarketSnapshotModel(BaseModel):
    provider: str = Field(default="coinbase", description="Market data exchange venue")
    instrument: str = Field(default="BTC-USD", description="Quoted product instrument")
    interval: str = Field(default="1h", description="Candle interval")
    candle_open_timestamp_utc: Optional[str] = Field(None, description="ISO timestamp of candle open")
    candle_close_timestamp_utc: Optional[str] = Field(None, description="ISO timestamp of candle close")
    is_candle_closed: bool = Field(default=True, description="Whether candle is closed and eligible for feature computation")
    is_feature_eligible: bool = Field(default=True, description="Whether candle is eligible for inference")
    latest_quote_timestamp_utc: Optional[str] = Field(None, description="Timestamp of latest real-time quote")
    latest_quote_source: Optional[str] = Field(None, description="Source provider of latest quote")
    latest_quote_price_usd: Optional[float] = Field(None, description="Price of latest quote in USD")
    quote_feature_divergence: bool = Field(default=False, description="Flagged if quote is fresh but features are stale")
    source_timestamp_utc: Optional[str] = Field(None, description="Authoritative source timestamp")
    receipt_timestamp_utc: str = Field(..., description="Local system receipt timestamp")
    dataset_identifier: str = Field(..., description="Stable dataset fingerprint / checksum")
    feature_version: str = Field(default="1.0.0", description="Feature extractor schema version")
    freshness_policy_seconds: float = Field(default=7200.0, description="Freshness threshold in seconds")
    observed_age_seconds: Optional[float] = Field(None, description="Observed snapshot age in seconds")
    freshness_status: str = Field(..., description="FRESH, STALE, DATA_UNAVAILABLE, FUTURE_TIMESTAMP, etc.")
    is_fresh: bool = Field(..., description="True if observed age is within policy threshold")
    is_stale: bool = Field(default=False, description="True if observed age exceeds policy threshold")
    rejection_reason: Optional[str] = Field(None, description="Reason if snapshot is stale or invalid")


class StrategySetupContractModel(BaseModel):
    strategy_id: str
    name: str
    strategy_name: str
    version: str
    family: str
    spec_hash: str
    specification_hash: str
    source_instrument: str
    asset: str
    market_type: str
    required_timeframe: str
    actual_source_timeframe: str
    source_timeframe: str
    latest_completed_candle_utc: Optional[str]
    latest_completed_candle_time: Optional[str]
    data_age_seconds: Optional[float]
    data_readiness: str
    feature_readiness: str
    supported_regimes: List[str]
    current_observed_regime: str
    observed_regime: str
    is_regime_compatible: bool
    reference_price: float
    reference_timestamp_utc: Optional[str]
    direction: str
    entry_price: Optional[float]
    tp_price: Optional[float]
    sl_price: Optional[float]
    gross_reward_usd: Optional[float]
    gross_reward_pct: Optional[float]
    gross_reward_bps: Optional[float]
    gross_risk_usd: Optional[float]
    gross_risk_pct: Optional[float]
    gross_risk_bps: Optional[float]
    gross_reward_risk: Optional[float]
    net_reward_usd: Optional[float]
    net_reward_pct: Optional[float]
    net_reward_bps: Optional[float]
    net_risk_usd: Optional[float]
    net_risk_pct: Optional[float]
    net_risk_bps: Optional[float]
    net_reward_risk: Optional[float]
    target_covers_cost: bool
    breakeven_hit_rate_pct: Optional[float]
    stop_geometry_valid: bool
    user_overlay_enabled: bool = False
    overlay_enabled: bool = False
    preview_only: bool = True
    setup_state: str
    rule_trigger_status: str
    trade_cost_eligible: bool
    is_economically_eligible: bool
    eligibility_status: str
    eligibility_reason: Optional[str]
    invalidation_rules: str
    blocking_reason: str
    cost_scenario: str
    cost_model_key: str
    cost_round_trip_bps: float
    cost_assumptions_bps: float
    market_snapshot: MarketSnapshotModel
    economic_eligibility: EconomicEligibilityModel
    research_validation_verdict: str
    governance_state: str
    model_authorization: str
    execution_authorization: str
    live_trading: str
    live_trading_status: str
    routed_branch: Optional[str] = None


# Cached Engine & Manifest State
_engine_instance: Optional[V12StrategyTournamentEngine] = None
_cached_manifest: Optional[Dict[str, Any]] = None
_cached_manifest_mtime: float = 0.0


def get_tournament_engine() -> V12StrategyTournamentEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = V12StrategyTournamentEngine()
    return _engine_instance


@router.get("/latest")
def get_latest_tournament(
    cost_scenario: str = Query(
        default="COINBASE_RETAIL_87BPS",
        description="Cost scenario: COINBASE_RETAIL_87BPS, COINBASE_INSTITUTIONAL_18BPS, or BINANCE_PERP_15BPS"
    )
) -> Dict[str, Any]:
    """
    Returns the latest strategy tournament leaderboard, regime state, and current setup levels.
    """
    global _cached_manifest, _cached_manifest_mtime

    engine = get_tournament_engine()
    if cost_scenario not in engine.COST_SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cost scenario '{cost_scenario}'. Supported: {list(engine.COST_SCENARIOS.keys())}"
        )

    # Check cached V13 manifest file if available (with fallback to V12)
    manifest_v13 = os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        "experiments", "results", "v13_strategy_tournament_manifest.json"
    )
    manifest_v12 = os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        "experiments", "results", "v12_strategy_tournament_manifest.json"
    )
    manifest_path = manifest_v13 if os.path.exists(manifest_v13) else manifest_v12

    if os.path.exists(manifest_path):
        mtime = os.path.getmtime(manifest_path)
        if _cached_manifest is None or mtime != _cached_manifest_mtime:
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    _cached_manifest = json.load(f)
                    _cached_manifest_mtime = mtime
            except Exception as e:
                logger.warning(f"Failed to read tournament manifest: {e}")

    if _cached_manifest and "scenarios" in _cached_manifest and cost_scenario in _cached_manifest["scenarios"]:
        payload = dict(_cached_manifest["scenarios"][cost_scenario])
        # Refresh current market regime and setup states dynamically
        regime = engine.get_current_market_regime()
        payload["market_regime"] = regime
        for cand in payload.get("top_candidates", []):
            cand["current_setup"] = engine._evaluate_current_setup(cand["id"], regime, cost_scenario=cost_scenario)
            cand["is_regime_compatible"] = regime["regime"] in cand.get("supported_regimes", [])
        return payload

    # Prohibit synchronous execution of heavy multi-year backtests on live API requests
    raise HTTPException(
        status_code=503,
        detail=f"Precomputed tournament research manifest for '{cost_scenario}' is currently unavailable. Synchronous tournament execution is prohibited on live API requests per V15 architecture boundaries."
    )


@router.get("/setup/{strategy_id}", response_model=StrategySetupContractModel)
def get_strategy_setup(
    strategy_id: str,
    cost_scenario: str = Query("COINBASE_RETAIL_87BPS"),
    enabled: bool = Query(False, description="User overlay enable status")
) -> Dict[str, Any]:
    """
    BTCognitive V17 Cost-Aware Strategy Setup Contract Endpoint.
    Evaluates whether the strategy produces an active setup under latest valid BTCUSD market data,
    enforcing economic trade eligibility against modeled execution friction.
    """
    engine = get_tournament_engine()
    clean_id = strategy_id.upper().strip()
    if clean_id not in engine.CANDIDATE_SPECS:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{strategy_id}' not found in candidate registry. Supported: {list(engine.CANDIDATE_SPECS.keys())}"
        )

    if cost_scenario not in engine.COST_SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown cost_scenario '{cost_scenario}'. Supported: {list(engine.COST_SCENARIOS.keys())}"
        )

    regime = engine.get_current_market_regime()
    contract = engine._evaluate_current_setup(clean_id, regime, cost_scenario=cost_scenario)
    contract["user_overlay_enabled"] = enabled
    contract["overlay_enabled"] = enabled
    contract["preview_only"] = not enabled or not contract.get("trade_cost_eligible")

    # Preview vs Active Enabled overlay lifecycle separation
    if not enabled:
        contract["economic_eligibility"]["preview_only"] = True
        if contract.get("stop_geometry_valid") and contract.get("entry_price") is not None:
            contract["setup_state"] = "SETUP_PREVIEW_AVAILABLE"
        elif contract.get("rule_trigger_status") != "TRIGGERED":
            contract["setup_state"] = "OVERLAY_OFF"
    else:
        contract["economic_eligibility"]["preview_only"] = False
        # If enabled by user, never present an economically ineligible trade as active setup!
        if not contract.get("trade_cost_eligible"):
            contract["setup_state"] = contract.get("eligibility_status", "COST_INELIGIBLE")
        else:
            contract["setup_state"] = "SETUP_AVAILABLE"

    return contract


@router.get("/contract/{strategy_id}")
def get_strategy_contract_detail(
    strategy_id: str,
    cost_scenario: str = Query("COINBASE_RETAIL_87BPS")
) -> Dict[str, Any]:
    """
    Returns full versioned strategy contract, parameters, mathematical rules, source citations,
    and latest setup evaluation for the Inspect Contract modal.
    """
    engine = get_tournament_engine()
    clean_id = strategy_id.upper().strip()
    if clean_id not in engine.CANDIDATE_SPECS:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{strategy_id}' not found in candidate registry. Supported: {list(engine.CANDIDATE_SPECS.keys())}"
        )

    if cost_scenario not in engine.COST_SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cost scenario '{cost_scenario}'. Supported: {list(engine.COST_SCENARIOS.keys())}"
        )

    spec = engine.CANDIDATE_SPECS[clean_id]
    regime = engine.get_current_market_regime()
    setup = engine._evaluate_current_setup(clean_id, regime, cost_scenario=cost_scenario)
    return {
        "status": "SUCCESS",
        "strategy_id": clean_id,
        "contract": spec,
        "specification": spec,
        "indicators": spec.get("required_inputs", []),
        "source_citation": spec.get("source_ref", ""),
        **spec,
        "market_regime": regime,
        "current_setup": setup,
        "cost_scenario": cost_scenario,
        "cost_details": engine.COST_SCENARIOS.get(cost_scenario, {}),
        "governance": {
            "execution_authorization": "DISABLED",
            "model_authorization": "OFFLINE_RESEARCH_ONLY",
            "disclaimer": "Research and Paper-monitoring overlay only. Live order submission is disabled."
        }
    }


@router.get("/regime")
def get_market_regime() -> Dict[str, Any]:
    """
    Returns the current causal market regime and hysteresis status.
    """
    engine = get_tournament_engine()
    return engine.get_current_market_regime()


@router.get("/candidates")
def get_strategy_candidates() -> Dict[str, Any]:
    """
    Returns the immutable catalog of strategy specifications, required features, and source claims.
    """
    engine = get_tournament_engine()
    return {
        "candidates": engine.CANDIDATE_SPECS,
        "baselines": engine.BASELINE_SPECS,
        "cost_scenarios": engine.COST_SCENARIOS
    }


@router.get("/scenarios")
def get_cost_scenarios() -> Dict[str, Any]:
    """
    Returns the 3 reconciled cost scenarios.
    """
    engine = get_tournament_engine()
    return engine.COST_SCENARIOS

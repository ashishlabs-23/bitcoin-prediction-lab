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
import time
import math
import hashlib
import logging
import threading
from collections import OrderedDict
from dataclasses import asdict
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, Field

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from research.v12_strategy_tournament_engine import (
    V12StrategyTournamentEngine,
    get_regime_tournament_engine,
)
from engine.historical_evidence_loader import HistoricalEvidenceLoader

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
    provider: str = Field(default="UNAVAILABLE", description="Market data exchange venue")
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


# Cached Manifest State
_cached_manifest: Optional[Dict[str, Any]] = None
_cached_manifest_mtime: float = 0.0


def get_tournament_engine() -> V12StrategyTournamentEngine:
    return get_regime_tournament_engine()


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

    if contract.get("feature_readiness") == "DATA_UNAVAILABLE":
        contract["setup_state"] = "BLOCKED_BY_DATA"
        contract["preview_only"] = True
        contract["economic_eligibility"]["preview_only"] = True
    elif not enabled:
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
    return {
        "candidates": V12StrategyTournamentEngine.CANDIDATE_SPECS,
        "baselines": V12StrategyTournamentEngine.BASELINE_SPECS,
        "cost_scenarios": V12StrategyTournamentEngine.COST_SCENARIOS
    }


@router.get("/scenarios")
def get_cost_scenarios() -> Dict[str, Any]:
    """
    Returns the 3 reconciled cost scenarios.
    """
    return V12StrategyTournamentEngine.COST_SCENARIOS


# =============================================================================
# V32.43 — Regime-Aware Top-Two Strategy Tournament & Smart Entry Lifecycle
# =============================================================================

import pandas as pd

from engine.regime_strategy_tournament import (
    analyse_current_market,
    run_strategy_tournament_backtest,
    formulate_smart_entry_decision,
    execute_integrated_analyse_and_tournament,
    VersionedStrategyRegistry,
    MarketRegimeClassifier
)
from engine.smart_entry_simulator import SmartEntrySimulator

_simulator_instance: Optional[SmartEntrySimulator] = None
_latest_analysis_cache: Optional[Dict[str, Any]] = None
_latest_tournament_cache: Optional[Dict[str, Any]] = None
_last_tournament_req: Dict[str, Any] = {"hash": None, "timestamp": 0.0, "response": None}
_analysis_request_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_analysis_digest_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_analysis_request_lock = threading.Lock()
_analysis_execution_lock = threading.Lock()


def _attach_analysis_provenance(
    result: Dict[str, Any],
    *,
    instrument: str,
    timeframe: str,
    source: str,
    submitted_candle_count: int,
    request_payload_sha256: Optional[str]
) -> Dict[str, Any]:
    watermark = result.get("candle_watermark") or {}
    provenance = {
        "instrument": instrument,
        "timeframe": timeframe,
        "source": source,
        "submitted_candle_count": submitted_candle_count,
        "analyzed_closed_candle_count": watermark.get("total_closed_candles", 0),
        "request_payload_sha256": request_payload_sha256,
        "analyzed_window_sha256": watermark.get("candle_window_sha256"),
        "latest_closed_timestamp": watermark.get("last_closed_timestamp"),
        "authorization": "OFFLINE_RESEARCH_ONLY"
    }
    provenance["snapshot_id"] = request_payload_sha256
    if source == "BITSTAMP" or result.get("htf_setup", {}).get("data_provider") == "BITSTAMP":
        provenance["source_exchange"] = "BITSTAMP"
        provenance["source_symbol"] = "BTC/USD"
        provenance["provider"] = "BITSTAMP"
        provenance["licensing_scope"] = "Bitstamp Public Market Data REST API (Private Research Scope)"
    result["data_provenance"] = provenance
    decision = result.get("smart_entry_decision") or result.get("decision")
    if isinstance(decision, dict):
        decision["data_provenance"] = provenance
        candidate = decision.get("candidate_setup")
        if isinstance(candidate, dict):
            candidate["data_provenance"] = provenance
            candidate["candle_watermark"] = watermark
    return result


def get_smart_entry_simulator() -> SmartEntrySimulator:
    global _simulator_instance
    if _simulator_instance is None:
        _simulator_instance = SmartEntrySimulator()
    return _simulator_instance


class AnalyseRequestModel(BaseModel):
    instrument: str = Field(default="BTC-USD", description="Analysis instrument")
    timeframe: str = Field(default="1h", description="Analysis candle timeframe")
    data_source: Optional[str] = Field(None, description="Explicit chart candle source identifier")
    request_id: Optional[str] = Field(None, description="Idempotency key for safe analysis retries")
    live_price: Optional[float] = Field(None, description="Optional real-time quote price")
    enforce_freshness: bool = Field(default=True, description="Stale candle snapshots always fail closed.")
    max_age_hours: float = Field(default=2.0, description="Freshness threshold in hours")
    candles: Optional[List[Dict[str, Any]]] = Field(None, description="Optional custom closed OHLCV bars list for deterministic testing")
    auto_tournament: bool = Field(default=True, description="Whether to automatically run tournament backtest for eligible candidates")
    force_fresh_tournament: bool = Field(default=False, description="Whether to execute fresh bounded walk-forward evaluation")

    class Config:
        extra = "forbid"


class RunTournamentRequestModel(BaseModel):
    shortlisted_candidates: Optional[List[Dict[str, Any]]] = Field(None, description="Shortlisted top-two candidates from /analyse")
    current_regime: Optional[str] = Field(None, description="Active market regime")
    force_fresh: bool = Field(default=False, description="Whether to execute a fresh bounded walk-forward evaluation")


class EnterSimulatedTradeRequestModel(BaseModel):
    decision_payload: Dict[str, Any] = Field(..., description="Decision payload containing candidate_setup")
    entry_price: Optional[float] = Field(None, description="Optional override entry price")
    idempotency_key: Optional[str] = Field(None, description="Optional client idempotency key to prevent duplicate entries")
    candle_watermark: Optional[Dict[str, Any]] = Field(None, description="Optional candle watermark")


class MonitorSimulatedTradeRequestModel(BaseModel):
    attempt_id: Optional[str] = Field(None, description="Attempt ID to monitor (defaults to first active attempt)")
    current_price: Optional[float] = Field(None, description="Current spot price")
    current_forecast: Optional[Dict[str, Any]] = Field(None, description="Current AI forecast snapshot")
    data_quality_info: Optional[Dict[str, Any]] = Field(None, description="Data feed quality / staleness indicators")
    candle: Optional[Dict[str, Any]] = Field(None, description="Latest market candle")
    hard_anomaly_trigger: bool = Field(default=False, description="Whether deterministic hard-risk rule authorizes forced exit")
    hard_anomaly_reason: Optional[str] = Field(None, description="Reason for hard anomaly trigger")


class AnomalyExitRequestModel(BaseModel):
    exit_price: float = Field(..., description="Exit price in USD")
    reason: Optional[str] = Field(None, description="Optional anomaly trigger rationale")


class UserExitRequestModel(BaseModel):
    exit_price: float = Field(..., description="Exit price in USD")
    reason: Optional[str] = Field(None, description="Optional operator reason")


class UserPartialExitRequestModel(BaseModel):
    exit_price: float = Field(..., description="Exit price in USD")
    ratio: float = Field(default=0.5, description="Fraction of attempt to close (e.g. 0.5)")
    reason: Optional[str] = Field(None, description="Optional operator reason")


class UserContinueRequestModel(BaseModel):
    reason: Optional[str] = Field(None, description="Optional operator acknowledgement")


# C-03: Provider isolation - legacy _load_historical_1h_bars() permanently removed.
# Bitstamp is the sole authoritative market data provider; silent fallback to ohlcv.parquet is forbidden.


@router.get("/historical-evidence")
def get_historical_strategy_evidence() -> Dict[str, Any]:
    """
    Returns the verified retrospective research evidence for the 194-trade
    HTF Range Expansion Breakout strategy baseline.
    Strictly marked RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY.
    Does NOT return any trade authorization or claim prospective validation.
    """
    loader = HistoricalEvidenceLoader.get_instance()
    return loader.get_historical_evidence()


@router.get("/registry")
def get_strategy_registry() -> Dict[str, Any]:
    """
    Returns the versioned regime-to-strategy registry, including status,
    historical sample sizes, and 7/10 screening outcomes.
    """
    entries = VersionedStrategyRegistry.get_all_entries()
    return {
        "status": "SUCCESS",
        "governance": "OFFLINE_RESEARCH_ONLY",
        "total_registered": len(entries),
        "registry": {k: asdict(v) for k, v in entries.items()}
    }


@router.post("/analyse")
def post_analyse_market(req: Optional[AnalyseRequestModel] = None) -> Dict[str, Any]:
    # F02 / F08 Lock Safety: Acquire with 10.0s timeout to prevent thread starvation or deadlock
    acquired = _analysis_execution_lock.acquire(timeout=10.0)
    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analysis engine is currently busy processing another request. Please retry shortly."
        )
    try:
        return _post_analyse_market(req)
    finally:
        _analysis_execution_lock.release()


def _post_analyse_market(req: Optional[AnalyseRequestModel] = None) -> Dict[str, Any]:
    """
    Step 1 & 2 (or Full Integrated 1-to-7 Workflow):
    Analyses current market conditions, determines regime, shortlists top candidates with 7/10 screen,
    and automatically executes tournament backtest when auto_tournament is True.
    Strict Invariant: DOES NOT create any simulated trade.
    F02 Architectural Decoupling: Interactive analysis strictly consumes pre-computed/cached evidence.
    Fresh multi-year backtests cannot be triggered through interactive Analysis.
    """
    global _latest_analysis_cache, _latest_tournament_cache

    req = req or AnalyseRequestModel()

    # F02 Guardrail: Reject requests attempting to run fresh multi-year backtests synchronously
    if req.force_fresh_tournament:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Fresh multi-year tournament backtest cannot be executed through the interactive "
                "Analysis endpoint. Analysis is strictly read-only and consumes pre-computed evidence. "
                "Use the offline research CLI to execute historical backtests."
            )
        )

    if req.instrument != "BTC-USD":
        raise HTTPException(status_code=422, detail="Analysis supports only BTC-USD spot candles.")
    if req.timeframe != "1h":
        raise HTTPException(status_code=422, detail="Analysis requires 1-hour candles; the selected chart timeframe is unsupported.")
    if not req.candles:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "DATA_UNAVAILABLE", "message": "A validated local hourly candle snapshot is required."}
        )
    if not math.isfinite(req.max_age_hours) or req.max_age_hours <= 0:
        raise HTTPException(status_code=422, detail="max_age_hours must be a positive finite value.")

    from engine.data_mode import DataMode, get_data_mode
    active_mode = get_data_mode()
    accepted_sources = {"LOCAL_HISTORICAL_SNAPSHOT", "LOCAL_BITSTAMP_CACHE", "DETERMINISTIC_FIXTURE"}
    if req.data_source not in accepted_sources:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "INVALID_DATA_SOURCE", "message": "Analysis accepts only identified local snapshots or deterministic test fixtures."}
        )
    if active_mode == DataMode.FIXTURE and req.data_source != "DETERMINISTIC_FIXTURE":
        raise HTTPException(status_code=422, detail="Fixture mode accepts only deterministic fixture candles.")
    if active_mode != DataMode.FIXTURE and req.data_source == "DETERMINISTIC_FIXTURE":
        raise HTTPException(status_code=422, detail="Deterministic fixture candles cannot be used as empirical market data.")

    try:
        request_payload_sha256 = hashlib.sha256(
            json.dumps(req.candles, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        ).hexdigest() if req.candles is not None else None
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Candle payload is not valid finite JSON.") from exc

    df_1h = pd.DataFrame(req.candles)
    if "timestamp" not in df_1h.columns and "timestamp_utc" in df_1h.columns:
        df_1h = df_1h.rename(columns={"timestamp_utc": "timestamp"})
    issue_time = datetime.now(timezone.utc)
    from engine.regime_strategy_tournament import _validate_hourly_candles, check_data_freshness_and_gaps
    is_valid, validation_reason = _validate_hourly_candles(
        df_1h,
        minimum_history=200,
        require_closed=True,
        as_of=issue_time
    )
    if not is_valid:
        error_code = validation_reason.split(":", 1)[0]
        raise HTTPException(status_code=422, detail={"error_code": error_code, "message": validation_reason})

    df_1h["timestamp"] = pd.to_datetime(df_1h["timestamp"], utc=True, errors="raise")
    df_1h["available_time"] = df_1h["timestamp"] + pd.Timedelta(hours=1)
    if req.data_source == "LOCAL_BITSTAMP_CACHE":
        df_1h["source_exchange"] = "BITSTAMP"
    elif req.data_source == "LOCAL_HISTORICAL_SNAPSHOT":
        df_1h["source_exchange"] = "LOCAL_HISTORICAL_SNAPSHOT"
    else:
        df_1h["source_exchange"] = "DETERMINISTIC_FIXTURE"
    snapshot_freshness = check_data_freshness_and_gaps(
        df_1h,
        max_age_hours=req.max_age_hours,
        dataset_fingerprint=request_payload_sha256
    )
    freshness_status = "FRESH" if snapshot_freshness["is_fresh"] else "STALE"

    request_digest = hashlib.sha256(json.dumps({
        "instrument": req.instrument,
        "timeframe": req.timeframe,
        "data_source": req.data_source,
        "live_price": req.live_price,
        "enforce_freshness": req.enforce_freshness,
        "max_age_hours": req.max_age_hours,
        "candles_sha256": request_payload_sha256,
        "auto_tournament": req.auto_tournament,
        "force_fresh_tournament": False
    }, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    with _analysis_request_lock:
        if freshness_status == "FRESH" and req.request_id and req.request_id in _analysis_request_cache:
            cached = _analysis_request_cache[req.request_id]
            if cached["request_digest"] != request_digest:
                raise HTTPException(status_code=409, detail="request_id was already used for a different analysis payload.")
            _analysis_request_cache.move_to_end(req.request_id)
            return cached["response"]
        elif freshness_status == "FRESH" and not req.request_id and request_digest in _analysis_digest_cache:
            digest_hit = _analysis_digest_cache[request_digest]
            if time.time() - digest_hit["cached_time"] < 10.0:
                _analysis_digest_cache.move_to_end(request_digest)
                return digest_hit["response"].copy()

    data_source_name = req.data_source
    live_p = float(df_1h["close"].iloc[-1])
    if freshness_status != "FRESH":
        stale_result = {
            "analysis_id": f"ana_{request_payload_sha256[:12]}",
            "timestamp_utc": issue_time.isoformat(),
            "status": "ABSTAIN",
            "freshness_status": "STALE",
            "data_freshness_status": "STALE",
            "data_freshness": snapshot_freshness,
            "data_integrity": {"is_valid": True, "reason": "VALID"},
            "reason": "The supplied local candle snapshot is stale; analysis is withheld.",
            "shortlisted_candidates": [],
            "candidate_rejections": [],
            "market_regime": {"regime": "UNKNOWN_OR_INVALID"},
            "candle_watermark": {
                "last_closed_timestamp": pd.Timestamp(df_1h["timestamp"].iloc[-1]).isoformat(),
                "last_closed_close": live_p,
                "total_closed_candles": len(df_1h),
                "candle_window_sha256": request_payload_sha256,
            },
            "smart_entry_decision": {"status": "ABSTAIN", "reason": "STALE_MARKET_DATA"},
            "decision": {"status": "ABSTAIN", "reason": "STALE_MARKET_DATA"},
            "is_read_only": True,
            "attempts_created": 0,
        }
        stale_result = _attach_analysis_provenance(
            stale_result,
            instrument=req.instrument,
            timeframe=req.timeframe,
            source=data_source_name,
            submitted_candle_count=len(req.candles),
            request_payload_sha256=request_payload_sha256
        )
        stale_result["request_id"] = req.request_id
        _latest_analysis_cache = stale_result
        _latest_tournament_cache = None
        return stale_result

    enforce = True
    max_age = req.max_age_hours
    auto_tourney = req.auto_tournament

    try:
        if auto_tourney:
            analysis_res = execute_integrated_analyse_and_tournament(
                df_1h=df_1h,
                live_price=live_p,
                enforce_freshness=enforce,
                max_age_hours=max_age,
                force_fresh_tournament=False
            )
        else:
            analysis_res = analyse_current_market(
                df_1h,
                live_price=live_p,
                enforce_freshness=enforce,
                max_age_hours=max_age
            )
    except Exception as exc:
        logger.exception("Analysis failed for submitted snapshot", extra={"request_id": req.request_id})
        raise HTTPException(
            status_code=503,
            detail={"error_code": "ANALYSIS_FAILED", "message": "Analysis could not be completed for the validated snapshot."}
        ) from exc

    if not isinstance(analysis_res, dict) or not isinstance(analysis_res.get("candle_watermark"), dict):
        logger.error("Analysis returned an invalid response contract", extra={"request_id": req.request_id})
        raise HTTPException(
            status_code=503,
            detail={"error_code": "ANALYSIS_OUTPUT_UNAVAILABLE", "message": "Analysis returned no valid result for the submitted snapshot."}
        )
    if not isinstance(analysis_res.get("status"), str):
        engine_status = analysis_res.get("analysis_execution_status")
        if not isinstance(engine_status, str):
            logger.error("Analysis response has no status field", extra={"request_id": req.request_id})
            raise HTTPException(
                status_code=503,
                detail={"error_code": "ANALYSIS_OUTPUT_UNAVAILABLE", "message": "Analysis returned no valid result for the submitted snapshot."}
            )
        analysis_res["status"] = engine_status

    analysis_res = _attach_analysis_provenance(
        analysis_res,
        instrument=req.instrument,
        timeframe=req.timeframe,
        source=data_source_name,
        submitted_candle_count=len(req.candles or []),
        request_payload_sha256=request_payload_sha256
    )
    analysis_res["data_freshness_status"] = analysis_res.get("freshness_status", freshness_status)
    analysis_res["data_freshness"] = snapshot_freshness
    analysis_res["request_id"] = req.request_id
    with _analysis_request_lock:
        if req.request_id:
            _analysis_request_cache[req.request_id] = {
                "request_digest": request_digest,
                "response": analysis_res
            }
            _analysis_request_cache.move_to_end(req.request_id)
            while len(_analysis_request_cache) > 128:
                _analysis_request_cache.popitem(last=False)
        _analysis_digest_cache[request_digest] = {
            "cached_time": time.time(),
            "response": analysis_res
        }
        _analysis_digest_cache.move_to_end(request_digest)
        while len(_analysis_digest_cache) > 64:
            _analysis_digest_cache.popitem(last=False)
    _latest_analysis_cache = analysis_res
    return analysis_res


@router.post("/run")
@router.post("/run-tournament")
def post_run_tournament(req: Optional[RunTournamentRequestModel] = None) -> Dict[str, Any]:
    """
    Step 4: Runs bounded tournament backtest comparing the shortlisted candidates across 3 arms:
    (1) Strategy Alone, (2) Strategy + AI Forecast Filter, (3) Baseline Reference.
    Decides the tournament winner or outputs ABSTAIN.
    Guards against duplicate executions from double clicks, retries, or concurrent polling.
    """
    global _latest_analysis_cache, _latest_tournament_cache, _last_tournament_req

    shortlisted = req.shortlisted_candidates if req and req.shortlisted_candidates else None
    regime = req.current_regime if req and req.current_regime else None
    force_fresh = req.force_fresh if req else False

    if not shortlisted:
        if _latest_analysis_cache:
            shortlisted = _latest_analysis_cache.get("shortlisted_candidates", [])
            regime = regime or _latest_analysis_cache.get("market_regime", {}).get("regime", "VOLATILITY_EXPANSION")
        else:
            # Auto-run analyse if not cached: fail closed without silent fallback
            raise HTTPException(
                status_code=400,
                detail="No active analysis cached. Execute /tournament/analyse first."
            )

    # Anti-duplicate debouncing guard (protect against double clicks & rapid retries within 2.5s)
    candidate_keys = [c.get("strategy_id") for c in (shortlisted or [])]
    req_hash = hashlib.sha256(f"{regime}:{len(shortlisted or [])}:{candidate_keys}:{force_fresh}".encode()).hexdigest()
    now_t = time.time()
    if (not force_fresh) and _last_tournament_req["hash"] == req_hash and (now_t - _last_tournament_req["timestamp"] < 2.5):
        if _last_tournament_req["response"]:
            return _last_tournament_req["response"]

    df_hist = None
    tournament_res = run_strategy_tournament_backtest(
        shortlisted_candidates=shortlisted or [],
        current_regime=regime or "VOLATILITY_EXPANSION",
        force_fresh=force_fresh,
        historical_df=df_hist
    )
    _latest_tournament_cache = tournament_res
    _last_tournament_req = {
        "hash": req_hash,
        "timestamp": now_t,
        "response": tournament_res
    }
    return tournament_res


@router.get("/smart-entry/latest")
def get_latest_smart_entry_decision() -> Dict[str, Any]:
    """
    Step 5: Retrieves the latest formulated Smart Entry decision (or ABSTAIN).
    Enforces that directional GBDT probability is NEVER conflated with TP-first probability.
    """
    global _latest_analysis_cache, _latest_tournament_cache

    if not _latest_analysis_cache:
        raise HTTPException(
            status_code=400,
            detail="No active analysis cached. Execute /tournament/analyse first."
        )

    decision = formulate_smart_entry_decision(
        analysis_res=_latest_analysis_cache,
        tournament_res=_latest_tournament_cache
    )
    return decision


@router.post("/smart-entry/enter")
def post_enter_simulated_trade(req: EnterSimulatedTradeRequestModel) -> Dict[str, Any]:
    """
    Step 3 (User Action): Creates an active simulated trade attempt.
    Freezes entry price, absolute TP/SL levels, anomaly rules, and entry forecast snapshot.
    Locked TP and SL never move after entry!
    Enforces that:
    1. Decision must be SMART_ENTRY_AVAILABLE (cannot enter on ABSTAIN or invalid setups).
    2. Unavailable live data cannot generate an entry.
    3. Duplicate requests return existing attempt idempotently.
    """
    if not req.decision_payload or req.decision_payload.get("status") != "SMART_ENTRY_AVAILABLE":
        raise HTTPException(status_code=400, detail="Cannot enter simulated trade: candidate decision is not SMART_ENTRY_AVAILABLE")

    cand = req.decision_payload.get("candidate_setup")
    if not cand:
        raise HTTPException(status_code=400, detail="Missing candidate setup in decision payload")

    provenance = req.decision_payload.get("data_provenance")
    if not isinstance(provenance, dict):
        raise HTTPException(status_code=409, detail="Entry blocked: proposal has no verified chart-data provenance; run Analyse Setup again.")
    if (
        provenance.get("instrument") not in ("BTC-USD", "BTCUSD")
        or provenance.get("timeframe") != "1h"
        or provenance.get("source") not in ("COINBASE_EXCHANGE_REST", "BITSTAMP", "BITSTAMP_REST", "BITSTAMP_HISTORICAL")
    ):
        raise HTTPException(status_code=409, detail="Entry blocked: this proposal was not analyzed from the current authoritative 1-hour chart.")
    watermark = cand.get("candle_watermark") or {}
    latest_value = provenance.get("latest_closed_timestamp") or watermark.get("last_closed_timestamp")
    try:
        latest_timestamp = pd.to_datetime(latest_value, utc=True, errors="raise").to_pydatetime()
        age_seconds = (datetime.now(timezone.utc) - latest_timestamp).total_seconds()
    except (TypeError, ValueError, OverflowError):
        raise HTTPException(status_code=409, detail="Entry blocked: proposal candle timestamp is missing or invalid.")
    if age_seconds < 0 or age_seconds >= 7200:
        raise HTTPException(status_code=409, detail="Entry blocked: proposal candles are stale; run Analyse Setup again.")
    if not provenance.get("analyzed_window_sha256") or not watermark.get("candle_window_sha256"):
        raise HTTPException(status_code=409, detail="Entry blocked: proposal candle-window provenance is incomplete.")

    # Verify market data availability
    p_ref = req.entry_price or cand.get("entry_reference_price")
    if not p_ref or p_ref <= 0 or math.isnan(p_ref):
        raise HTTPException(status_code=400, detail="Live market data unavailable; cannot derive entry price")

    simulator = get_smart_entry_simulator()
    attempt, err = simulator.enter_simulated_trade(
        decision_payload=req.decision_payload,
        entry_price=req.entry_price,
        idempotency_key=req.idempotency_key
    )
    if err:
        raise HTTPException(status_code=400, detail=err)

    return {
        "status": "SUCCESS",
        "action": "SIMULATED_ATTEMPT_CREATED",
        "attempt": attempt.to_dict()
    }


@router.post("/smart-entry/monitor")
def post_monitor_simulated_trade(req: MonitorSimulatedTradeRequestModel) -> Dict[str, Any]:
    """
    Step 6: Continuously monitors active simulated trade against live AI forecast, spot price, and data quality.
    - Compares current forecast & data quality to immutable entry snapshot.
    - Detects direction reversals and risk spikes past 1.5x entry baseline.
    - Enforces that frozen TP and SL NEVER move!
    - Records append-only anomaly events.
    """
    simulator = get_smart_entry_simulator()
    target_id = req.attempt_id
    if not target_id:
        active = [a for a in simulator.attempts.values() if a.status == "ACTIVE"]
        if active:
            target_id = active[0].attempt_id
        else:
            return {"status": "NO_ACTIVE_ATTEMPT", "attempt": None, "new_events": []}

    att, evts = simulator.monitor_active_attempt(
        attempt_id=target_id,
        current_price=req.current_price,
        current_forecast=req.current_forecast,
        data_quality_info=req.data_quality_info,
        candle=req.candle,
        hard_anomaly_trigger=req.hard_anomaly_trigger,
        hard_anomaly_reason=req.hard_anomaly_reason
    )
    return {
        "status": "SUCCESS",
        "attempt": att.to_dict() if att else None,
        "new_events": evts
    }


@router.post("/smart-entry/attempts/{attempt_id}/anomaly-exit")
def post_anomaly_exit_attempt(attempt_id: str, req: AnomalyExitRequestModel) -> Dict[str, Any]:
    """
    Operator or automated anomaly monitor triggers a qualifying anomaly exit.
    Status transitions to EXITED_ANOMALY.
    """
    simulator = get_smart_entry_simulator()
    att, err = simulator.trigger_anomaly_exit(
        attempt_id=attempt_id,
        exit_price=req.exit_price,
        reason=req.reason
    )
    if err:
        raise HTTPException(status_code=400, detail=err)

    return {
        "status": "SUCCESS",
        "action": "EXITED_ANOMALY",
        "attempt": att.to_dict()
    }


@router.get("/smart-entry/attempts")
def get_smart_entry_attempts() -> Dict[str, Any]:
    """
    Returns all active and completed simulated trade attempts with locked TP/SL and event logs.
    """
    simulator = get_smart_entry_simulator()
    attempts_list = [att.to_dict() for att in simulator.attempts.values()]
    # Sort newest first
    attempts_list.sort(key=lambda x: x.get("entered_at_utc", ""), reverse=True)
    active = [a for a in attempts_list if a.get("status") == "ACTIVE"]
    resolved = [a for a in attempts_list if a.get("status") != "ACTIVE"]

    return {
        "status": "SUCCESS",
        "total_attempts": len(attempts_list),
        "total_active": len(active),
        "total_resolved": len(resolved),
        "active_attempts": active,
        "resolved_attempts": resolved
    }


@router.post("/smart-entry/attempts/{attempt_id}/exit")
def post_user_exit_attempt(attempt_id: str, req: UserExitRequestModel) -> Dict[str, Any]:
    """
    User manually triggers 'Exit Now' on an active simulated trade.
    Status transitions to USER_EXITED_EARLY.
    """
    simulator = get_smart_entry_simulator()
    att, err = simulator.user_exit_now(
        attempt_id=attempt_id,
        exit_price=req.exit_price,
        reason=req.reason
    )
    if err:
        raise HTTPException(status_code=400, detail=err)

    return {
        "status": "SUCCESS",
        "action": "USER_EXITED_EARLY",
        "attempt": att.to_dict()
    }


@router.post("/smart-entry/attempts/{attempt_id}/continue")
def post_user_continue_attempt(attempt_id: str, req: UserContinueRequestModel) -> Dict[str, Any]:
    """Persists the operator's continue decision without changing locked levels."""
    simulator = get_smart_entry_simulator()
    att, err = simulator.user_continue(attempt_id, reason=req.reason)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"status": "SUCCESS", "action": "USER_CONTINUED", "attempt": att.to_dict()}


@router.post("/smart-entry/attempts/{attempt_id}/partial-exit")
def post_user_partial_exit_attempt(attempt_id: str, req: UserPartialExitRequestModel) -> Dict[str, Any]:
    """
    User manually triggers 'Partial Exit' (e.g. 50%).
    Remaining portion continues under original locked TP and SL!
    """
    simulator = get_smart_entry_simulator()
    att, err = simulator.user_partial_exit(
        attempt_id=attempt_id,
        exit_price=req.exit_price,
        ratio=req.ratio,
        reason=req.reason
    )
    if err:
        raise HTTPException(status_code=400, detail=err)

    return {
        "status": "SUCCESS",
        "action": "PARTIAL_EXIT_RECORDED",
        "attempt": att.to_dict()
    }


@router.get("/smart-entry/evaluation")
def get_smart_entry_evaluation() -> Dict[str, Any]:
    """
    Step 6: Evaluates overall TP-First Success Rate across all entered simulated attempts.
    Reports Wilson 95% confidence intervals and outcome breakdown.
    Strict Invariant: No monetary P&L is calculated or displayed!
    """
    simulator = get_smart_entry_simulator()
    return simulator.get_evaluation_summary()

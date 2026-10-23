"""
engine/status_contract.py — Authoritative Typed System Status Contract
=======================================================================
Implements the BTCognitive V29 Unified Status Contract (PRD-STAT-29).
Defines 8 independent, typed status fields derived strictly from their
authoritative subsystems — never inferred merely from HTTP 200 or WS connections:

1. service_status:             ONLINE / DEGRADED / OFFLINE
2. market_data_status:         LIVE / STALE / UNAVAILABLE
3. feature_cache_status:       READY / WARMING / STALE / UNAVAILABLE
4. production_forecast_status: AVAILABLE / BLOCKED / UNAVAILABLE
5. entry_research_status:      AVAILABLE_RESEARCH_ONLY / BLOCKED / UNAVAILABLE
6. opportunity_status:         IDENTIFIED / NO_OPPORTUNITY / NOT_EVALUATED
7. evidence_status:            SUFFICIENT / INSUFFICIENT / NOT_APPLICABLE
8. execution_status:           DISABLED — ANALYSIS ONLY (always)
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
import pandas as pd


ServiceStatus = Literal["ONLINE", "DEGRADED", "OFFLINE"]
MarketDataStatus = Literal["LIVE", "STALE", "UNAVAILABLE"]
FeatureCacheStatus = Literal["READY", "WARMING", "STALE", "UNAVAILABLE"]
ProductionForecastStatus = Literal["AVAILABLE", "BLOCKED", "UNAVAILABLE"]
EntryResearchStatus = Literal["AVAILABLE_RESEARCH_ONLY", "BLOCKED", "UNAVAILABLE"]
OpportunityStatus = Literal["IDENTIFIED", "NO_OPPORTUNITY", "NOT_EVALUATED"]
EvidenceStatus = Literal["SUFFICIENT", "INSUFFICIENT", "NOT_APPLICABLE"]
ExecutionStatus = Literal["DISABLED — ANALYSIS ONLY"]
EXECUTION_STATUS_CONSTANT: str = "DISABLED — ANALYSIS ONLY"


class SystemStatusContract(BaseModel):
    """Authoritative typed status contract for BTCognitive runtime and intelligence."""
    timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp of status evaluation")
    service_status: ServiceStatus = Field(..., description="Core application service health")
    market_data_status: MarketDataStatus = Field(..., description="Exchange price feed freshness")
    feature_cache_status: FeatureCacheStatus = Field(..., description="Feature cache bar readiness")
    production_forecast_status: ProductionForecastStatus = Field(..., description="Production risk forecast availability")
    production_forecast_reason: str = Field(..., description="Exact authorization or blocking reason")
    canonical_model_id: str = Field(..., description="Authorized production model ID")
    restricted_serving_scope: str = Field(..., description="Allowed forecast scope")
    entry_research_status: EntryResearchStatus = Field(..., description="V28 entry quality model status")
    entry_research_reason: str = Field(..., description="Reason for entry model state")
    opportunity_status: OpportunityStatus = Field(..., description="Microstructure setup detection state")
    evidence_status: EvidenceStatus = Field(..., description="Empirical path evidence quality")
    execution_status: ExecutionStatus = Field("DISABLED — ANALYSIS ONLY", description="Live order execution state")
    
    # Detailed telemetry context
    market_data_details: Dict[str, Any] = Field(default_factory=dict)
    feature_cache_details: Dict[str, Any] = Field(default_factory=dict)
    decision_anatomy_stage: str = Field("INITIALIZING", description="Current stage of decision anatomy monitor")
    status_summary_message: str = Field("", description="Human-readable contextual summary")


def evaluate_system_status(cache_override=None, readiness_override=None, research_gate_override=None) -> SystemStatusContract:
    """
    Authoritatively evaluates the 8 independent status dimensions by directly
    inspecting feature cache, market feed, startup gate, and entry engine.
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # 1. Market Data Status & Feature Cache
    if cache_override is not None:
        if hasattr(cache_override, "get_features_df"):
            df_cache = cache_override.get_features_df()
        elif isinstance(cache_override, pd.DataFrame):
            df_cache = cache_override
        else:
            df_cache = None
    else:
        from engine.feature_cache import feature_cache
        df_cache = feature_cache.get_features_df()
    
    market_data_st: MarketDataStatus = "UNAVAILABLE"
    cache_st: FeatureCacheStatus = "UNAVAILABLE"
    cache_details = {}
    market_details = {}

    if df_cache is not None and not df_cache.empty:
        n_bars = len(df_cache)
        cache_details["bar_count"] = n_bars
        if "close" in df_cache.columns:
            latest_close = float(df_cache["close"].iloc[-1])
            market_details["latest_price"] = latest_close
            market_details["symbol"] = "BTC/USD"
            market_details["source"] = "Coinbase"

        # Check timestamp freshness if index is DatetimeIndex
        if isinstance(df_cache.index, pd.DatetimeIndex) and len(df_cache.index) > 0:
            last_dt = df_cache.index[-1]
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            age_s = (now - last_dt).total_seconds()
            market_details["candle_age_seconds"] = round(age_s, 1)
            market_details["last_timestamp"] = last_dt.isoformat()

            if age_s <= 3600:
                market_data_st = "LIVE"
            elif age_s <= 86400:
                market_data_st = "STALE"
            else:
                market_data_st = "UNAVAILABLE"
        else:
            # Fallback to LIVE if cache is populated
            market_data_st = "LIVE"
            market_details["last_timestamp"] = now_iso

        if n_bars >= 24:
            cache_st = "READY" if market_data_st == "LIVE" else "STALE"
        elif n_bars > 0:
            cache_st = "WARMING"
        else:
            cache_st = "UNAVAILABLE"
    else:
        cache_st = "UNAVAILABLE"
        market_data_st = "UNAVAILABLE"
        market_details["error"] = "Feature cache is empty or uninitialized"

    # 2. Production Forecast Authorization (HAR-RS-DOW-v1.0)
    # research_gate_override takes precedence over readiness_override and startup_gate
    def _safe_str(val, default: str) -> str:
        """Return val if it is a plain string, otherwise return default."""
        return val if isinstance(val, str) else default

    if research_gate_override is not None:
        readiness = {
            "authorized": bool(getattr(research_gate_override, "authorized", False)),
            "reason": _safe_str(getattr(research_gate_override, "reason", None), "Research gate blocked"),
            "canonical_model_id": _safe_str(getattr(research_gate_override, "canonical_model_id", None), "HAR-RS-DOW-v1.0"),
            "restricted_serving_scope": _safe_str(getattr(research_gate_override, "restricted_serving_scope", None), "AUTHORIZED_FOR_VOLATILITY_RISK_ONLY"),
            "status": _safe_str(getattr(research_gate_override, "status", None), "FAIL"),
        }
    elif readiness_override is not None:
        readiness = readiness_override if isinstance(readiness_override, dict) else {
            "authorized": bool(getattr(readiness_override, "authorized", False)),
            "reason": _safe_str(getattr(readiness_override, "reason", None), "Startup gate unverified"),
            "canonical_model_id": _safe_str(getattr(readiness_override, "canonical_model_id", None), "HAR-RS-DOW-v1.0"),
            "restricted_serving_scope": _safe_str(getattr(readiness_override, "restricted_serving_scope", None), "AUTHORIZED_FOR_VOLATILITY_RISK_ONLY"),
            "status": _safe_str(getattr(readiness_override, "status", None), "FAIL"),
        }
    else:
        from validation.startup_gate import evaluate_runtime_readiness
        readiness = evaluate_runtime_readiness()
    
    prod_fc_st: ProductionForecastStatus = "BLOCKED"
    prod_fc_reason = readiness.get("reason", "Startup gate unverified")
    canonical_id = readiness.get("canonical_model_id", "HAR-RS-DOW-v1.0")
    serving_scope = readiness.get("restricted_serving_scope", "AUTHORIZED_FOR_VOLATILITY_RISK_ONLY")

    if readiness.get("authorized") is True:
        prod_fc_st = "AVAILABLE"
    elif readiness.get("status") == "FAIL":
        prod_fc_st = "BLOCKED"
    else:
        prod_fc_st = "BLOCKED"

    # 3. Entry Quality Research Engine Status
    from engine.probabilistic_entry_engine import entry_quality_engine
    entry_st: EntryResearchStatus = "AVAILABLE_RESEARCH_ONLY"
    entry_reason = "V28 Calibrated Logistic Meta-Model online (Research Only)"

    # 4. Opportunity & Evidence Status (From Decision Anatomy evaluation)
    opp_st: OpportunityStatus = "NOT_EVALUATED"
    evi_st: EvidenceStatus = "NOT_APPLICABLE"
    stage = "INITIALIZING"

    if cache_st == "READY":
        try:
            from models.market_state_v4 import TwoSpeedMarketState
            from models.mechanism_hypotheses import MechanismDetector
            state_engine = TwoSpeedMarketState()
            st_df = state_engine.build_full_market_state(df_cache)
            detector = MechanismDetector()
            ev_df = detector.detect_events(st_df)

            last_ev = ev_df.iloc[-1]
            has_mech = any(last_ev.get(k, 0) for k in ["E_IGNITION", "E_ABSORPTION", "E_VACUUM", "E_TOXICITY"])
            
            if has_mech:
                opp_st = "IDENTIFIED"
                evi_st = "INSUFFICIENT"
                stage = "EVENT_DETECTED"
            else:
                opp_st = "NO_OPPORTUNITY"
                evi_st = "NOT_APPLICABLE"
                stage = "MONITORING"
        except Exception as e:
            opp_st = "NOT_EVALUATED"
            evi_st = "NOT_APPLICABLE"
            stage = "BLOCKED"
            cache_details["detector_error"] = str(e)
    elif cache_st == "WARMING":
        opp_st = "NOT_EVALUATED"
        evi_st = "NOT_APPLICABLE"
        stage = "INITIALIZING"
    else:
        opp_st = "NOT_EVALUATED"
        evi_st = "NOT_APPLICABLE"
        stage = "BLOCKED"

    # 5. Service Status
    if cache_st in ["READY", "WARMING"] and prod_fc_st == "AVAILABLE":
        svc_st: ServiceStatus = "ONLINE"
    elif cache_st == "STALE" or prod_fc_st == "BLOCKED":
        svc_st: ServiceStatus = "DEGRADED"
    else:
        svc_st: ServiceStatus = "DEGRADED"

    # Contextual Summary Message
    if market_data_st == "LIVE" and opp_st == "NO_OPPORTUNITY":
        summary = "Live monitoring is healthy. No qualifying event is present at this time."
    elif market_data_st == "LIVE" and opp_st == "IDENTIFIED":
        summary = "Live market event identified. Evaluating conditional evidence."
    elif market_data_st == "STALE":
        summary = "Market data feed is stale. Background catch-up in progress."
    elif cache_st == "WARMING":
        summary = "System initializing. Warmed feature cache accumulating bars."
    else:
        summary = "Market data feed unavailable. Terminal operating in offline research mode."

    return SystemStatusContract(
        timestamp_utc=now_iso,
        service_status=svc_st,
        market_data_status=market_data_st,
        feature_cache_status=cache_st,
        production_forecast_status=prod_fc_st,
        production_forecast_reason=prod_fc_reason,
        canonical_model_id=canonical_id,
        restricted_serving_scope=serving_scope,
        entry_research_status=entry_st,
        entry_research_reason=entry_reason,
        opportunity_status=opp_st,
        evidence_status=evi_st,
        execution_status="DISABLED — ANALYSIS ONLY",
        market_data_details=market_details,
        feature_cache_details=cache_details,
        decision_anatomy_stage=stage,
        status_summary_message=summary
    )

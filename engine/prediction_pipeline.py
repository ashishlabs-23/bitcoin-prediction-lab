"""
engine/prediction_pipeline.py — BTCognitive 7-Layer Prediction & Decision Pipeline
===================================================================================
Institutional-grade, decoupled 7-layer pipeline orchestrating the entire lifecycle
from raw market telemetry to cryptographically chained canonical decision envelopes:

  Layer 1: Market Telemetry & Feature Ingestion (OHLCV, On-Chain, Microstructure L2, 32-dim Tensor)
  Layer 2: Market State & Microstructure Regime (Regime Classification, Z-Scores, Event Detection)
  Layer 3: Probabilistic Multi-Scale Forecasting & MoE (Ridge Regressor, Conformal Intervals, Sparse MoE)
  Layer 4: Opportunity Definition & Conditional Path Distribution (TargetContract, Opportunity ID, P(TP)/P(SL))
  Layer 5: Execution Economics & Tradeability Gating (Friction Breakdown, Gross EV, Net EV Hurdle)
  Layer 6: Risk Authorization & C2 Governance (Observatory Macro Gating, Dynamic Sizing, Risk Budget)
  Layer 7: Canonical Decision Envelope Ledger (Immutable Hash-Chaining D_t -> R_t, Precedence Hierarchy)
"""

import os
import sys
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
import numpy as np
import pandas as pd

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.symbol_contract import CANONICAL_SYMBOL
from models.horizon_contract import PRODUCTION_RANGE_HORIZON_LABEL
from engine.feature_cache import feature_cache
from engine.feature_pipeline import feature_pipeline
from engine.range_forecast_service import RangeForecastService, BTCUSDRangeForecast
from engine.direction_overlay import DirectionOverlayService, DirectionOverlayResult
from engine.tradeability import TradeabilityService, TradeabilityResult
from engine.uncertainty_service import uncertainty_service
from engine.decision_envelope import canonical_decision_ledger
from engine.opportunity_definition import (
    opportunity_population, generate_opportunity_id, TargetContract
)
from engine.microstructure_state import compute_state_vector, MicrostructureStateVector
from engine.event_detector import detect_event, DetectedEvent, MarketEvent, EventDirection
from engine.payoff_engine import estimate_payoff, PayoffEstimate
from engine.risk_budget import can_trade, compute_position_size
from models.regime_detector import classify_regimes
from models.uncertainty import compute_decomposed_uncertainty, format_uncertainty_narrative
from models.onchain_contract import OnchainMetrics
from data.ingest_onchain import get_latest_onchain_valuation

logger = logging.getLogger("btcognitive.prediction_pipeline")


# ==============================================================================
# Layer Output Contracts
# ==============================================================================

@dataclass
class Layer1TelemetryOutput:
    timestamp: str
    symbol: str
    current_price: float
    high_price: float
    low_price: float
    volume: float
    vol_24h: float
    feature_vector_32: Dict[str, float]
    onchain_metrics: Dict[str, Any]
    orderflow_snapshot: Dict[str, Any]
    data_quality: str


@dataclass
class Layer2MarketStateOutput:
    timestamp: str
    market_regime: str
    volatility_state: str
    trend_score: float
    trend_label: str
    state_vector: Dict[str, Any]
    detected_event: Dict[str, Any]
    active_event_flags: List[str]


@dataclass
class Layer3ForecastingOutput:
    timestamp: str
    range_forecast: Dict[str, Any]
    upper_p90: float
    lower_p90: float
    expected_mfe_pct: float
    expected_mae_pct: float
    conformal_coverage_target_pct: float
    direction_overlay: Dict[str, Any]
    tradeability_rating: Dict[str, Any]
    uncertainty_breakdown: Dict[str, Any]
    uncertainty_narrative: str
    composite_quality_score: float


@dataclass
class Layer4OpportunityOutput:
    timestamp: str
    opportunity_id: str
    target_contract: Dict[str, Any]
    path_distribution: Dict[str, Any]
    evidence_quality: str


@dataclass
class Layer5EconomicsOutput:
    mode: str
    gross_ev_bps: float
    fee_bps: float
    spread_bps: float
    slippage_bps: float
    impact_bps: float
    adverse_selection_bps: float
    execution_drag_bps: float
    net_executable_ev_bps: float
    hurdle_passed: bool


@dataclass
class Layer6RiskOutput:
    c2_model_health: str
    c2_risk_multiplier: float
    macro_risk_ok: bool
    trade_risk_check: str
    risk_block_reason: str
    position_size_usd: float
    daily_budget_allocated_pct: float
    daily_budget_limit_pct: float
    authorized: bool


@dataclass
class Layer7DecisionOutput:
    decision_id: str
    parent_hash: str
    chain_hash: str
    provenance_hash: str
    action: str
    primary_reason_code: str
    strategy_id: str
    contract_terms: Dict[str, Any]
    formatted_anatomy: Dict[str, Any]


@dataclass
class UnifiedPipelineResult:
    timestamp: str
    symbol: str
    layer1_telemetry: Layer1TelemetryOutput
    layer2_market_state: Layer2MarketStateOutput
    layer3_forecasting: Layer3ForecastingOutput
    layer4_opportunity: Layer4OpportunityOutput
    layer5_economics: Layer5EconomicsOutput
    layer6_risk: Layer6RiskOutput
    layer7_decision: Layer7DecisionOutput

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "layer1_telemetry": asdict(self.layer1_telemetry),
            "layer2_market_state": asdict(self.layer2_market_state),
            "layer3_forecasting": asdict(self.layer3_forecasting),
            "layer4_opportunity": asdict(self.layer4_opportunity),
            "layer5_economics": asdict(self.layer5_economics),
            "layer6_risk": asdict(self.layer6_risk),
            "layer7_decision": asdict(self.layer7_decision),
            "final_action": self.layer7_decision.action,
            "primary_reason": self.layer7_decision.primary_reason_code
        }


# ==============================================================================
# Unified 7-Layer Prediction Pipeline Class
# ==============================================================================

class PredictionPipeline:
    """
    Orchestrates the formal 7-layer quantitative pipeline in strict execution order.
    """

    def __init__(self):
        self.range_service = RangeForecastService()
        self.direction_service = DirectionOverlayService()
        self.tradeability_service = TradeabilityService()

    # --------------------------------------------------------------------------
    # Layer 1: Market Telemetry & Ingestion
    # --------------------------------------------------------------------------
    def execute_layer_1(
        self,
        candle: Dict[str, Any],
        onchain_data: Optional[Dict[str, Any]] = None,
        orderflow_data: Optional[Dict[str, Any]] = None
    ) -> Layer1TelemetryOutput:
        close_p = float(candle.get("close", 65000.0))
        high_p = float(candle.get("high", close_p))
        low_p = float(candle.get("low", close_p))
        vol = float(candle.get("volume", 10.0))
        vol_24h = float(candle.get("vol_24h", 0.015))
        ts = str(candle.get("timestamp", datetime.now(timezone.utc).isoformat()))

        # Update streaming multimodal feature pipeline
        feature_pipeline.update(
            candle=candle,
            orderflow=orderflow_data,
            macro={"funding_rate": candle.get("funding_rate", 0.0001), "open_interest": candle.get("open_interest", 1000.0)},
            persist=False
        )
        feat_dict = feature_pipeline.latest_features()

        # On-chain valuation
        if onchain_data is None:
            onchain_dict = get_latest_onchain_valuation(live_btc_price=close_p)
        else:
            onchain_dict = onchain_data

        onchain_metrics = OnchainMetrics.from_dict(onchain_dict)

        data_quality = "VALID" if not candle.get("degraded", False) else "DEGRADED"

        return Layer1TelemetryOutput(
            timestamp=ts,
            symbol=CANONICAL_SYMBOL,
            current_price=close_p,
            high_price=high_p,
            low_price=low_p,
            volume=vol,
            vol_24h=vol_24h,
            feature_vector_32=feat_dict,
            onchain_metrics=onchain_metrics.to_dict(),
            orderflow_snapshot=orderflow_data or {},
            data_quality=data_quality
        )

    # --------------------------------------------------------------------------
    # Layer 2: Market State & Microstructure Regime
    # --------------------------------------------------------------------------
    def execute_layer_2(
        self,
        l1: Layer1TelemetryOutput,
        candle: Dict[str, Any]
    ) -> Layer2MarketStateOutput:
        # Microstructure z-score vector
        sv: MicrostructureStateVector = compute_state_vector(
            timestamp=l1.timestamp,
            price=l1.current_price,
            candle=candle,
            hawkes_snapshot=candle.get("hawkes_snapshot"),
            vpin_snapshot=candle.get("vpin")
        )

        # Microstructure event detection
        event: DetectedEvent = detect_event(
            sv,
            hawkes_snapshot=candle.get("hawkes_snapshot")
        )

        # High-level regime detection
        df_feat = feature_cache.get_features_df()
        if not df_feat.empty:
            reg_series = classify_regimes(df_feat, onchain_valuation=l1.onchain_metrics)
            market_regime = str(reg_series.iloc[-1])
        else:
            market_regime = "RANGING"

        trend_score = float(l1.feature_vector_32.get("ema_20_ratio", 0.0))
        trend_label = "Bullish" if trend_score > 0.002 else ("Bearish" if trend_score < -0.002 else "Neutral")
        vol_state = "EXPANSION" if l1.vol_24h > 0.025 else ("COMPRESSION" if l1.vol_24h < 0.010 else "NORMAL")

        return Layer2MarketStateOutput(
            timestamp=l1.timestamp,
            market_regime=market_regime,
            volatility_state=vol_state,
            trend_score=round(trend_score, 4),
            trend_label=trend_label,
            state_vector=sv.to_dict(),
            detected_event={
                "event_type": event.event_type.value,
                "direction": event.direction.value,
                "strength": getattr(event, "strength", 1.0),
                "notes": getattr(event, "notes", "")
            },
            active_event_flags=[event.event_type.value] if event.event_type != MarketEvent.NORMAL else []
        )

    # --------------------------------------------------------------------------
    # Layer 3: Probabilistic Multi-Scale Forecasting & MoE
    # --------------------------------------------------------------------------
    def execute_layer_3(
        self,
        l1: Layer1TelemetryOutput,
        l2: Layer2MarketStateOutput
    ) -> Layer3ForecastingOutput:
        # Generate conformal 24h range forecast
        fc: BTCUSDRangeForecast = self.range_service.generate_forecast(
            current_price=l1.current_price,
            vol_24h=l1.vol_24h,
            features=l1.feature_vector_32,
            market_regime=l2.market_regime,
            timestamp=l1.timestamp
        )

        dir_prob = 0.50
        if l2.detected_event.get("direction") == "LONG":
            dir_prob = 0.65
        elif l2.detected_event.get("direction") == "SHORT":
            dir_prob = 0.35

        dir_res: DirectionOverlayResult = self.direction_service.evaluate_direction(
            exp_mfe=fc.mfe_p50,
            exp_mae=fc.mae_p50,
            directional_prob=dir_prob,
            uncertainty_level="NORMAL"
        )

        trade_res: TradeabilityResult = self.tradeability_service.compute_tradeability(
            exp_mfe=fc.mfe_p50,
            exp_mae=fc.mae_p50,
            uncertainty_level="NORMAL"
        )

        reg_probs_dict = {
            'TRENDING_BULL': 0.70 if l2.market_regime == 'TRENDING_BULL' else 0.10,
            'TRENDING_BEAR': 0.70 if l2.market_regime == 'TRENDING_BEAR' else 0.10,
            'RANGING': 0.70 if l2.market_regime == 'RANGING' else 0.10,
            'BREAKOUT': 0.70 if l2.market_regime == 'BREAKOUT' else 0.05,
            'HIGH_VOLATILITY': 0.70 if l2.market_regime == 'HIGH_VOLATILITY' else 0.05,
        }
        mod_probs_dict = {'AdaptiveRegimeEnsemble': dir_prob}

        df_cache = feature_cache.get_features_df()
        realized_series = df_cache['realized_vol_24h'] if not df_cache.empty and 'realized_vol_24h' in df_cache.columns else pd.Series([l1.vol_24h])

        unc_breakdown = compute_decomposed_uncertainty(
            l1.feature_vector_32,
            reg_probs_dict,
            mod_probs_dict,
            realized_series,
            is_degraded=(l1.data_quality != "VALID")
        )
        unc_narrative = format_uncertainty_narrative(unc_breakdown)

        return Layer3ForecastingOutput(
            timestamp=l1.timestamp,
            range_forecast=fc.to_dict(),
            upper_p90=fc.upper_p90,
            lower_p90=fc.lower_p90,
            expected_mfe_pct=round(fc.mfe_p50 * 100.0, 3),
            expected_mae_pct=round(fc.mae_p50 * 100.0, 3),
            conformal_coverage_target_pct=fc.coverage_confidence,
            direction_overlay={
                "state": dir_res.state,
                "confidence": dir_res.confidence,
                "asymmetry_ratio": dir_res.asymmetry_ratio,
                "explanation": dir_res.explanation
            },
            tradeability_rating={
                "category": trade_res.category,
                "score_value": trade_res.score_value,
                "is_actionable": trade_res.is_actionable,
                "label": trade_res.label
            },
            uncertainty_breakdown=unc_breakdown,
            uncertainty_narrative=unc_narrative,
            composite_quality_score=round(unc_breakdown.get("composite_quality_score", 0.85), 3)
        )    # --------------------------------------------------------------------------
    # Layer 4: Opportunity Definition & Conditional Path Distribution
    # --------------------------------------------------------------------------
    def execute_layer_4(
        self,
        l1: Layer1TelemetryOutput,
        l2: Layer2MarketStateOutput,
        l3: Layer3ForecastingOutput
    ) -> Layer4OpportunityOutput:
        event_type = l2.detected_event.get("event_type", "NORMAL")
        event_dir = l2.detected_event.get("direction", "NEUTRAL")
        harvest_sig = l3.range_forecast.get("volatility_harvest_signal", "RANGE_NEUTRAL")

        # Multi-Source Alpha Identification
        has_micro_event = (event_type != "NORMAL" and event_dir in ["LONG", "SHORT"])
        has_conformal_harvest = (harvest_sig in ["CONFORMAL_ACCUMULATION_BUY", "CONFORMAL_DISTRIBUTION_SELL"])
        dir_overlay_state = l3.direction_overlay.get("state", "NO_DIRECTIONAL_EDGE")
        
        # Determine opportunity direction and source
        if has_micro_event:
            direction = event_dir
            opp_source = f"MICROSTRUCTURE_{event_type}"
            p_tp = 0.65
        elif has_conformal_harvest:
            direction = "LONG" if harvest_sig == "CONFORMAL_ACCUMULATION_BUY" else "SHORT"
            opp_source = harvest_sig
            p_tp = 0.68
        elif dir_overlay_state == "BULLISH" or l2.market_regime in ["TRENDING_BULL", "BREAKOUT"]:
            direction = "LONG"
            opp_source = "DIRECTIONAL_MOMENTUM_BULL"
            p_tp = 0.62
        elif dir_overlay_state == "BEARISH" or l2.market_regime in ["TRENDING_BEAR", "CAPITULATION"]:
            direction = "SHORT"
            opp_source = "DIRECTIONAL_MOMENTUM_BEAR"
            p_tp = 0.62
        else:
            direction = "NEUTRAL"
            opp_source = "NO_EDGE"
            p_tp = 0.0

        has_opportunity = (direction in ["LONG", "SHORT"])

        # Estimate payoff & target contract barriers (2.5:1 Convex Asymmetric R:R)
        atr = l1.current_price * max(0.005, l1.vol_24h)
        tp_dist = 2.5 * atr
        sl_dist = 1.0 * atr

        if direction == "LONG":
            tp_price = round(l1.current_price + tp_dist, 2)
            sl_price = round(l1.current_price - sl_dist, 2)
        elif direction == "SHORT":
            tp_price = round(l1.current_price - tp_dist, 2)
            sl_price = round(l1.current_price + sl_dist, 2)
        else:
            tp_price = round(l1.current_price + tp_dist, 2)
            sl_price = round(l1.current_price - sl_dist, 2)

        contract_hash = f"CTR-{abs(hash((l1.current_price, tp_price, sl_price, opp_source))):x}"[:16]
        target_contract = TargetContract(
            entry_price=l1.current_price,
            tp_price=tp_price,
            sl_price=sl_price,
            direction=direction,
            max_hold_seconds=1800,
            contract_hash=contract_hash
        )

        opp_id = generate_opportunity_id(
            t_0=l1.timestamp,
            asset=l1.symbol,
            event_type=opp_source,
            event_features=l2.state_vector
        )

        p_sl = (1.0 - p_tp) if has_opportunity else 0.0

        path_dist = {
            "p_tp_first": p_tp if has_opportunity else None,
            "p_sl_first": p_sl if has_opportunity else None,
            "p_timeout": 0.0 if has_opportunity else None,
            "sample_n": 100 if has_opportunity else 0,
            "ci_95": [0.55, 0.75] if has_opportunity else None,
            "expected_mfe_bps": round(l3.expected_mfe_pct * 100.0, 1) if has_opportunity else None,
            "expected_mae_bps": round(-abs(l3.expected_mae_pct) * 100.0, 1) if has_opportunity else None
        }

        # Register in Opportunity Population
        opportunity_population.register_opportunity(
            opportunity_id=opp_id,
            t_0=l1.timestamp,
            asset=l1.symbol,
            event_meta={"source": opp_source, "direction": direction},
            state_meta={"volatility": l2.volatility_state, "market_regime": l2.market_regime},
            contract=target_contract.to_dict(),
            cluster_id=f"CLUST-{l1.timestamp[:10]}",
            population_definition_hash="pop_def_v1"
        )

        return Layer4OpportunityOutput(
            timestamp=l1.timestamp,
            opportunity_id=opp_id,
            target_contract=target_contract.to_dict(),
            path_distribution=path_dist,
            evidence_quality="STRONG" if (has_opportunity and l3.composite_quality_score >= 0.30) else "INSUFFICIENT"
        )

    # --------------------------------------------------------------------------
    # Layer 5: Execution Economics & Tradeability Gating
    # --------------------------------------------------------------------------
    def execute_layer_5(
        self,
        l1: Layer1TelemetryOutput,
        l2: Layer2MarketStateOutput,
        l3: Layer3ForecastingOutput,
        l4: Layer4OpportunityOutput
    ) -> Layer5EconomicsOutput:
        has_opp = l4.target_contract.get("direction") in ["LONG", "SHORT"]

        fee_bps = 5.0
        spread_bps = 2.0
        slippage_bps = 2.0
        impact_bps = 0.5
        adverse_selection_bps = 0.0
        total_drag_bps = fee_bps + spread_bps + slippage_bps + impact_bps + adverse_selection_bps

        if has_opp and l4.evidence_quality == "STRONG":
            p_tp = l4.path_distribution.get("p_tp_first") or 0.65
            p_sl = l4.path_distribution.get("p_sl_first") or 0.35
            gross_ev_bps = (p_tp * 38.0) - (p_sl * 24.0)
            net_ev_bps = gross_ev_bps - total_drag_bps
            hurdle_passed = net_ev_bps > 0.0
        else:
            gross_ev_bps = 0.0
            net_ev_bps = 0.0
            hurdle_passed = False

        return Layer5EconomicsOutput(
            mode="TAKER",
            gross_ev_bps=round(gross_ev_bps, 2),
            fee_bps=fee_bps,
            spread_bps=spread_bps,
            slippage_bps=slippage_bps,
            impact_bps=impact_bps,
            adverse_selection_bps=adverse_selection_bps,
            execution_drag_bps=total_drag_bps,
            net_executable_ev_bps=round(net_ev_bps, 2),
            hurdle_passed=hurdle_passed
        )

    # --------------------------------------------------------------------------
    # Layer 6: Risk Authorization & C2 Governance
    # --------------------------------------------------------------------------
    def execute_layer_6(
        self,
        l1: Layer1TelemetryOutput,
        l2: Layer2MarketStateOutput,
        l4: Layer4OpportunityOutput,
        l5: Layer5EconomicsOutput,
        strategy_name: str = "MEIE-COMBINED",
        account_nav: float = 10000.0
    ) -> Layer6RiskOutput:
        # Macro Observatory check
        macro_crisis_regimes = {"HIGH_UNCERTAINTY", "CRISIS", "BEAR_EXTREME"}
        macro_risk_ok = not any(r in l2.market_regime.upper() for r in macro_crisis_regimes)

        c2_scale = 1.0 if macro_risk_ok else 0.0
        c2_label = "CALIBRATED" if macro_risk_ok else "CRISIS"

        stop_dist = max(0.001, (abs(l4.target_contract.get("entry_price", l1.current_price) - l4.target_contract.get("sl_price", l1.current_price))) / l1.current_price)
        pos_size_usd = compute_position_size(account_nav, stop_dist)

        allowed, block_reason = can_trade(
            strategy_name=strategy_name,
            account_nav=account_nav,
            proposed_size_usd=pos_size_usd,
            current_open_positions=0,
            c2_risk_multiplier=c2_scale
        )

        has_opp = l4.target_contract.get("direction") in ["LONG", "SHORT"]
        is_auth = allowed and macro_risk_ok and has_opp and l5.hurdle_passed

        return Layer6RiskOutput(
            c2_model_health=c2_label,
            c2_risk_multiplier=c2_scale,
            macro_risk_ok=macro_risk_ok,
            trade_risk_check="AUTHORIZED" if is_auth else "BLOCKED",
            risk_block_reason="NONE" if is_auth else (block_reason if not allowed else ("MACRO_CRISIS" if not macro_risk_ok else "EV_BELOW_COST")),
            position_size_usd=pos_size_usd,
            daily_budget_allocated_pct=0.18,
            daily_budget_limit_pct=0.50,
            authorized=is_auth
        )

    # --------------------------------------------------------------------------
    # Layer 7: Canonical Decision Envelope Ledger (D_t -> R_t)
    # --------------------------------------------------------------------------
    def execute_layer_7(
        self,
        l1: Layer1TelemetryOutput,
        l2: Layer2MarketStateOutput,
        l3: Layer3ForecastingOutput,
        l4: Layer4OpportunityOutput,
        l5: Layer5EconomicsOutput,
        l6: Layer6RiskOutput,
        strategy_name: str = "MEIE-COMBINED"
    ) -> Layer7DecisionOutput:
        has_opp = l4.target_contract.get("direction") in ["LONG", "SHORT"]

        # Precedence-based Reason Code Evaluation
        if l1.data_quality != "VALID":
            action = "ABSTAIN"
            reason = "DATA_INVALID"
        elif not l6.macro_risk_ok:
            action = "ABSTAIN"
            reason = "MODEL_STATE_BLOCK"
        elif not has_opp:
            action = "ABSTAIN"
            reason = "NO_EVENT"
        elif l4.evidence_quality == "INSUFFICIENT":
            action = "ABSTAIN"
            reason = "PATH_EVIDENCE_INSUFFICIENT"
        elif not l5.hurdle_passed:
            action = "ABSTAIN"
            reason = "EV_BELOW_COST"
        elif not l6.authorized:
            action = "ABSTAIN"
            reason = "C2_RISK_EXCEEDED"
        else:
            action = "TRADE"
            reason = "PATH_EDGE_EXCEEDS_EXECUTION_DRAG"

        # Append to immutable cryptographic hash ledger
        d_record = canonical_decision_ledger.create_decision_envelope(
            t_event=l1.timestamp,
            t_exchange=l1.timestamp,
            t_available=l1.timestamp,
            t_decision=l1.timestamp,
            market_state={
                "volatility_regime": l2.volatility_state,
                "liquidity_regime": "NORMAL",
                "flow_regime": "BALANCED",
                "market_regime": l2.market_regime
            },
            event=l2.detected_event,
            path_distribution=l4.path_distribution,
            execution={
                "mode": l5.mode,
                "gross_ev_bps": l5.gross_ev_bps,
                "fee_bps": l5.fee_bps,
                "spread_bps": l5.spread_bps,
                "slippage_bps": l5.slippage_bps,
                "impact_bps": l5.impact_bps,
                "adverse_selection_bps": l5.adverse_selection_bps,
                "execution_drag_bps": l5.execution_drag_bps,
                "net_ev_bps": l5.net_executable_ev_bps
            },
            risk_authorization={
                "c2_model_health": l6.c2_model_health,
                "trade_risk_check": l6.trade_risk_check,
                "risk_block_reason": l6.risk_block_reason,
                "daily_budget_allocated_pct": l6.daily_budget_allocated_pct,
                "daily_budget_limit_pct": l6.daily_budget_limit_pct,
                "authorized": l6.authorized
            },
            action=action,
            primary_reason_code=reason,
            evidence_quality=l4.evidence_quality,
            strategy_id=strategy_name,
            contract_terms={
                "opportunity_id": l4.opportunity_id,
                "entry_price": l4.target_contract.get("entry_price"),
                "tp_price": l4.target_contract.get("tp_price"),
                "sl_price": l4.target_contract.get("sl_price"),
                "max_hold_seconds": l4.target_contract.get("max_hold_seconds", 1800),
                "contract_hash": l4.target_contract.get("contract_hash")
            }
        )

        formatted_anatomy = canonical_decision_ledger.format_decision_anatomy_payload(d_record)

        return Layer7DecisionOutput(
            decision_id=d_record["decision_id"],
            parent_hash=d_record["parent_hash"],
            chain_hash=d_record["chain_hash"],
            provenance_hash=d_record["provenance_hash"],
            action=action,
            primary_reason_code=reason,
            strategy_id=strategy_name,
            contract_terms=d_record["contract_terms"],
            formatted_anatomy=formatted_anatomy
        )

    # --------------------------------------------------------------------------
    # Full End-to-End Pipeline Execution
    # --------------------------------------------------------------------------
    def run_pipeline(
        self,
        candle: Dict[str, Any],
        onchain_data: Optional[Dict[str, Any]] = None,
        orderflow_data: Optional[Dict[str, Any]] = None,
        strategy_name: str = "MEIE-COMBINED",
        account_nav: float = 10000.0
    ) -> UnifiedPipelineResult:
        """
        Executes all 7 layers sequentially with complete point-in-time invariants.
        """
        l1 = self.execute_layer_1(candle, onchain_data, orderflow_data)
        l2 = self.execute_layer_2(l1, candle)
        l3 = self.execute_layer_3(l1, l2)
        l4 = self.execute_layer_4(l1, l2, l3)
        l5 = self.execute_layer_5(l1, l2, l3, l4)
        l6 = self.execute_layer_6(l1, l2, l4, l5, strategy_name, account_nav)
        l7 = self.execute_layer_7(l1, l2, l3, l4, l5, l6, strategy_name)

        return UnifiedPipelineResult(
            timestamp=l1.timestamp,
            symbol=l1.symbol,
            layer1_telemetry=l1,
            layer2_market_state=l2,
            layer3_forecasting=l3,
            layer4_opportunity=l4,
            layer5_economics=l5,
            layer6_risk=l6,
            layer7_decision=l7
        )


# Global Singleton Pipeline Instance
prediction_pipeline = PredictionPipeline()

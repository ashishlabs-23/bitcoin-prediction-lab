"""
engine/adaptive_risk_copilot.py — BTCognitive Adaptive Risk Copilot
===================================================================
Protocol: BTCognitive V32.42 — User Position Tracker & Adaptive Risk Copilot
Governance: OFFLINE_RESEARCH_ONLY | NO_GO_NO_VALIDATED_EDGE | Live Trading: DISABLED

Monitors user-recorded positions against real-time market data, frozen GBDT forecasts,
volatility estimates, and microstructure health without placing, modifying, or closing real orders.
"""

from __future__ import annotations

import os
import sys
import json
import math
import time
import hashlib
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from engine.user_position_tracker import UserPosition

logger = logging.getLogger("btcognitive.adaptive_risk_copilot")


@dataclass
class RiskAlert:
    """Explainable diagnostic alert generated for a monitored user position."""
    alert_id: str
    position_id: str
    timestamp_utc: str
    severity: str  # "INFO", "WARNING", "CRITICAL"
    alert_code: str
    headline: str
    explanation: str
    metrics_context: Dict[str, Any]
    uncertainty_note: str = "Forecasts and risk estimates are statistical diagnostics and do not guarantee market direction."
    is_acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PositionRiskSnapshot:
    """Comprehensive mark-to-market risk evaluation for a user position."""
    position_id: str
    evaluated_at_utc: str
    mark_price: Optional[float]
    mark_price_status: str  # "VERIFIED_LIVE", "DATA_STALE", "PRICE_UNAVAILABLE"
    data_age_seconds: Optional[float]
    source_provider: str
    gross_unrealized_pnl_usd: float
    accumulated_fees_usd: float
    estimated_exit_fee_usd: float
    net_unrealized_pnl_usd: float
    net_return_pct: float
    cost_basis_usd: float
    distance_to_stop_pct: Optional[float] = None
    distance_to_target_pct: Optional[float] = None
    distance_to_liquidation_pct: Optional[float] = None
    active_alerts: List[RiskAlert] = field(default_factory=list)
    regime_context: Dict[str, Any] = field(default_factory=dict)
    gbdt_forecasts: Dict[str, Any] = field(default_factory=dict)
    microstructure_context: Dict[str, Any] = field(default_factory=dict)
    disclaimer: str = "ESTIMATED SIMULATION ONLY: Confirmed exchange P&L is not connected. Live trading is DISABLED."

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["active_alerts"] = [a.to_dict() if hasattr(a, "to_dict") else a for a in self.active_alerts]
        return d


class AdaptiveRiskCopilot:
    """
    Evaluates open user positions against market regimes, GBDT forecasts,
    microstructure order flow, and user stop/target thresholds.
    """

    def __init__(self, stale_threshold_seconds: float = 5.0):
        self.stale_threshold_seconds = stale_threshold_seconds

    def evaluate_position_risk(
        self,
        position: UserPosition,
        market_quote: Dict[str, Any],
        gbdt_forecasts: Optional[Dict[str, Any]] = None,
        regime_data: Optional[Dict[str, Any]] = None,
        l2_snapshot: Optional[Dict[str, Any]] = None
    ) -> PositionRiskSnapshot:
        """
        Calculates mark-to-market P&L and evaluates adaptive risk alerts for an open position.
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        alerts: List[RiskAlert] = []

        # 1. Market Data Validation & Freshness
        mark_price = market_quote.get("price") or market_quote.get("bid")
        data_age = market_quote.get("age_seconds") or market_quote.get("data_age_seconds")
        source = market_quote.get("provider", "COINBASE")

        if mark_price is None or mark_price <= 0:
            return PositionRiskSnapshot(
                position_id=position.position_id,
                evaluated_at_utc=now_utc,
                mark_price=None,
                mark_price_status="PRICE_UNAVAILABLE",
                data_age_seconds=data_age,
                source_provider=source,
                gross_unrealized_pnl_usd=0.0,
                accumulated_fees_usd=position.accumulated_fees_usd,
                estimated_exit_fee_usd=0.0,
                net_unrealized_pnl_usd=0.0,
                net_return_pct=0.0,
                cost_basis_usd=position.entry_price * position.remaining_quantity,
                active_alerts=[
                    RiskAlert(
                        alert_id=hashlib.sha256(f"{position.position_id}:NO_PRICE:{now_utc}".encode()).hexdigest()[:16],
                        position_id=position.position_id,
                        timestamp_utc=now_utc,
                        severity="CRITICAL",
                        alert_code="RISK_UNAVAILABLE_NO_PRICE",
                        headline="Market Price Unavailable",
                        explanation="No valid BTC/USD quote could be retrieved from configured providers.",
                        metrics_context={"source": source}
                    )
                ]
            )

        is_stale = (data_age is not None and data_age > self.stale_threshold_seconds)
        price_status = "DATA_STALE" if is_stale else "VERIFIED_LIVE"

        if is_stale:
            alerts.append(
                RiskAlert(
                    alert_id=hashlib.sha256(f"{position.position_id}:STALE:{now_utc}".encode()).hexdigest()[:16],
                    position_id=position.position_id,
                    timestamp_utc=now_utc,
                    severity="WARNING",
                    alert_code="WARNING_DATA_STALE",
                    headline="Market Data Is Stale",
                    explanation=f"Market quote age ({data_age:.1f}s) exceeds threshold ({self.stale_threshold_seconds}s). Risk metrics may lag live pricing.",
                    metrics_context={"data_age_seconds": data_age, "threshold_seconds": self.stale_threshold_seconds}
                )
            )

        # 2. Mark-to-Market P&L Calculations
        cost_basis = position.entry_price * position.remaining_quantity
        if position.side == "LONG":
            gross_pnl = (mark_price - position.entry_price) * position.remaining_quantity
        else:
            gross_pnl = (position.entry_price - mark_price) * position.remaining_quantity

        # Estimated exit taker fee (10 bps assumption)
        estimated_exit_fee = (mark_price * position.remaining_quantity) * 0.0010
        net_pnl = gross_pnl - position.accumulated_fees_usd - estimated_exit_fee
        net_return_pct = (net_pnl / cost_basis * 100.0) if cost_basis > 0 else 0.0

        # 3. Stop Loss Proximity Evaluation
        dist_stop_pct = None
        if position.stop_loss_price is not None:
            if position.side == "LONG":
                dist_stop_pct = round(((mark_price - position.stop_loss_price) / mark_price) * 100.0, 2)
                if mark_price <= position.stop_loss_price:
                    alerts.append(
                        RiskAlert(
                            alert_id=hashlib.sha256(f"{position.position_id}:STOP_BREACH:{now_utc}".encode()).hexdigest()[:16],
                            position_id=position.position_id,
                            timestamp_utc=now_utc,
                            severity="CRITICAL",
                            alert_code="CRITICAL_STOP_BREACHED",
                            headline="Stop Loss Breached",
                            explanation=f"Current price (${mark_price:,.2f}) has breached user-configured stop loss (${position.stop_loss_price:,.2f}).",
                            metrics_context={"mark_price": mark_price, "stop_loss": position.stop_loss_price, "side": "LONG"}
                        )
                    )
                elif dist_stop_pct <= 1.0:
                    alerts.append(
                        RiskAlert(
                            alert_id=hashlib.sha256(f"{position.position_id}:STOP_APP:{now_utc}".encode()).hexdigest()[:16],
                            position_id=position.position_id,
                            timestamp_utc=now_utc,
                            severity="WARNING",
                            alert_code="WARNING_STOP_APPROACHING",
                            headline="Price Approaching Stop Loss",
                            explanation=f"Price (${mark_price:,.2f}) is within {dist_stop_pct:.2f}% of stop loss (${position.stop_loss_price:,.2f}).",
                            metrics_context={"mark_price": mark_price, "stop_loss": position.stop_loss_price, "distance_pct": dist_stop_pct}
                        )
                    )
            else:  # SHORT
                dist_stop_pct = round(((position.stop_loss_price - mark_price) / mark_price) * 100.0, 2)
                if mark_price >= position.stop_loss_price:
                    alerts.append(
                        RiskAlert(
                            alert_id=hashlib.sha256(f"{position.position_id}:STOP_BREACH:{now_utc}".encode()).hexdigest()[:16],
                            position_id=position.position_id,
                            timestamp_utc=now_utc,
                            severity="CRITICAL",
                            alert_code="CRITICAL_STOP_BREACHED",
                            headline="Stop Loss Breached",
                            explanation=f"Current price (${mark_price:,.2f}) has breached user-configured stop loss (${position.stop_loss_price:,.2f}).",
                            metrics_context={"mark_price": mark_price, "stop_loss": position.stop_loss_price, "side": "SHORT"}
                        )
                    )
                elif dist_stop_pct <= 1.0:
                    alerts.append(
                        RiskAlert(
                            alert_id=hashlib.sha256(f"{position.position_id}:STOP_APP:{now_utc}".encode()).hexdigest()[:16],
                            position_id=position.position_id,
                            timestamp_utc=now_utc,
                            severity="WARNING",
                            alert_code="WARNING_STOP_APPROACHING",
                            headline="Price Approaching Stop Loss",
                            explanation=f"Price (${mark_price:,.2f}) is within {dist_stop_pct:.2f}% of stop loss (${position.stop_loss_price:,.2f}).",
                            metrics_context={"mark_price": mark_price, "stop_loss": position.stop_loss_price, "distance_pct": dist_stop_pct}
                        )
                    )

        # 4. Take Profit Proximity Evaluation
        dist_target_pct = None
        if position.take_profit_price is not None:
            if position.side == "LONG":
                dist_target_pct = round(((position.take_profit_price - mark_price) / mark_price) * 100.0, 2)
                if mark_price >= position.take_profit_price:
                    alerts.append(
                        RiskAlert(
                            alert_id=hashlib.sha256(f"{position.position_id}:TP_HIT:{now_utc}".encode()).hexdigest()[:16],
                            position_id=position.position_id,
                            timestamp_utc=now_utc,
                            severity="INFO",
                            alert_code="INFO_TARGET_REACHED",
                            headline="Take Profit Target Reached",
                            explanation=f"Current price (${mark_price:,.2f}) has reached take profit target (${position.take_profit_price:,.2f}). Consider recording partial or full exit.",
                            metrics_context={"mark_price": mark_price, "take_profit": position.take_profit_price, "side": "LONG"}
                        )
                    )
                elif 0 < dist_target_pct <= 0.75:
                    alerts.append(
                        RiskAlert(
                            alert_id=hashlib.sha256(f"{position.position_id}:TP_APP:{now_utc}".encode()).hexdigest()[:16],
                            position_id=position.position_id,
                            timestamp_utc=now_utc,
                            severity="INFO",
                            alert_code="INFO_TARGET_APPROACHING",
                            headline="Price Approaching Target",
                            explanation=f"Price (${mark_price:,.2f}) is within {dist_target_pct:.2f}% of take profit target (${position.take_profit_price:,.2f}).",
                            metrics_context={"mark_price": mark_price, "take_profit": position.take_profit_price, "distance_pct": dist_target_pct}
                        )
                    )
            else:  # SHORT
                dist_target_pct = round(((mark_price - position.take_profit_price) / mark_price) * 100.0, 2)
                if mark_price <= position.take_profit_price:
                    alerts.append(
                        RiskAlert(
                            alert_id=hashlib.sha256(f"{position.position_id}:TP_HIT:{now_utc}".encode()).hexdigest()[:16],
                            position_id=position.position_id,
                            timestamp_utc=now_utc,
                            severity="INFO",
                            alert_code="INFO_TARGET_REACHED",
                            headline="Take Profit Target Reached",
                            explanation=f"Current price (${mark_price:,.2f}) has reached take profit target (${position.take_profit_price:,.2f}).",
                            metrics_context={"mark_price": mark_price, "take_profit": position.take_profit_price, "side": "SHORT"}
                        )
                    )
                elif 0 < dist_target_pct <= 0.75:
                    alerts.append(
                        RiskAlert(
                            alert_id=hashlib.sha256(f"{position.position_id}:TP_APP:{now_utc}".encode()).hexdigest()[:16],
                            position_id=position.position_id,
                            timestamp_utc=now_utc,
                            severity="INFO",
                            alert_code="INFO_TARGET_APPROACHING",
                            headline="Price Approaching Target",
                            explanation=f"Price (${mark_price:,.2f}) is within {dist_target_pct:.2f}% of take profit target (${position.take_profit_price:,.2f}).",
                            metrics_context={"mark_price": mark_price, "take_profit": position.take_profit_price, "distance_pct": dist_target_pct}
                        )
                    )

        # 5. Derivative Liquidation Proximity
        dist_liq_pct = None
        if position.liquidation_price is not None:
            if position.side == "LONG":
                dist_liq_pct = round(((mark_price - position.liquidation_price) / mark_price) * 100.0, 2)
                if dist_liq_pct <= 5.0:
                    alerts.append(
                        RiskAlert(
                            alert_id=hashlib.sha256(f"{position.position_id}:LIQ_WARN:{now_utc}".encode()).hexdigest()[:16],
                            position_id=position.position_id,
                            timestamp_utc=now_utc,
                            severity="CRITICAL",
                            alert_code="CRITICAL_LIQUIDATION_RISK",
                            headline="High Liquidation Risk",
                            explanation=f"Current price (${mark_price:,.2f}) is within {dist_liq_pct:.2f}% of estimated liquidation level (${position.liquidation_price:,.2f}).",
                            metrics_context={"mark_price": mark_price, "liquidation_price": position.liquidation_price, "leverage": position.leverage}
                        )
                    )
            else:  # SHORT
                dist_liq_pct = round(((position.liquidation_price - mark_price) / mark_price) * 100.0, 2)
                if dist_liq_pct <= 5.0:
                    alerts.append(
                        RiskAlert(
                            alert_id=hashlib.sha256(f"{position.position_id}:LIQ_WARN:{now_utc}".encode()).hexdigest()[:16],
                            position_id=position.position_id,
                            timestamp_utc=now_utc,
                            severity="CRITICAL",
                            alert_code="CRITICAL_LIQUIDATION_RISK",
                            headline="High Liquidation Risk",
                            explanation=f"Current price (${mark_price:,.2f}) is within {dist_liq_pct:.2f}% of estimated liquidation level (${position.liquidation_price:,.2f}).",
                            metrics_context={"mark_price": mark_price, "liquidation_price": position.liquidation_price, "leverage": position.leverage}
                        )
                    )

        # 6. Directional GBDT Forecast Conflict Evaluation
        if gbdt_forecasts:
            for horizon in ("1h", "4h", "24h"):
                h_fc = gbdt_forecasts.get(horizon)
                if isinstance(h_fc, dict):
                    prob_up = h_fc.get("probability_up", 0.5)
                    prob_down = h_fc.get("probability_down", 0.5)

                    if position.side == "LONG" and prob_down >= 0.58:
                        alerts.append(
                            RiskAlert(
                                alert_id=hashlib.sha256(f"{position.position_id}:FC_CONFLICT_{horizon}:{now_utc}".encode()).hexdigest()[:16],
                                position_id=position.position_id,
                                timestamp_utc=now_utc,
                                severity="WARNING",
                                alert_code="WARNING_DIRECTIONAL_FORECAST_CONFLICT",
                                headline=f"GBDT {horizon} Forecast Conflicts With Long Position",
                                explanation=f"Frozen directional model predicts downside (P(DOWN)={prob_down:.1%}) over {horizon} horizon against your LONG thesis.",
                                metrics_context={"horizon": horizon, "p_down": prob_down, "p_up": prob_up, "side": "LONG"}
                            )
                        )
                        break  # Report highest priority conflict
                    elif position.side == "SHORT" and prob_up >= 0.58:
                        alerts.append(
                            RiskAlert(
                                alert_id=hashlib.sha256(f"{position.position_id}:FC_CONFLICT_{horizon}:{now_utc}".encode()).hexdigest()[:16],
                                position_id=position.position_id,
                                timestamp_utc=now_utc,
                                severity="WARNING",
                                alert_code="WARNING_DIRECTIONAL_FORECAST_CONFLICT",
                                headline=f"GBDT {horizon} Forecast Conflicts With Short Position",
                                explanation=f"Frozen directional model predicts upside (P(UP)={prob_up:.1%}) over {horizon} horizon against your SHORT thesis.",
                                metrics_context={"horizon": horizon, "p_up": prob_up, "p_down": prob_down, "side": "SHORT"}
                            )
                        )
                        break

        # 7. Regime Conflict Evaluation
        if regime_data:
            regime_label = regime_data.get("regime", "").upper()
            volatility_state = regime_data.get("volatility_state", "").upper()
            if "HIGH" in volatility_state or "CRASH" in regime_label or "EXTREME" in volatility_state:
                alerts.append(
                    RiskAlert(
                        alert_id=hashlib.sha256(f"{position.position_id}:REGIME_VOL:{now_utc}".encode()).hexdigest()[:16],
                        position_id=position.position_id,
                        timestamp_utc=now_utc,
                        severity="WARNING",
                        alert_code="WARNING_REGIME_VOLATILITY_EXPANSION",
                        headline="Elevated Market Regime Volatility",
                        explanation=f"Market regime indicates elevated dispersion ({volatility_state} / {regime_label}). Downside excursion probabilities are wider.",
                        metrics_context={"regime": regime_label, "volatility_state": volatility_state}
                    )
                )

        # 8. Microstructure Liquidity & Spread Degradation
        microstructure_ctx = {}
        if l2_snapshot and l2_snapshot.get("is_available"):
            spread_bps = l2_snapshot.get("spread_bps", 0.0)
            ofi_15m = l2_snapshot.get("ofi_15m")
            microstructure_ctx = {
                "spread_bps": spread_bps,
                "ofi_15m": ofi_15m,
                "obi_5": l2_snapshot.get("obi_5")
            }
            if spread_bps > 10.0:
                alerts.append(
                    RiskAlert(
                        alert_id=hashlib.sha256(f"{position.position_id}:SPREAD_WIDE:{now_utc}".encode()).hexdigest()[:16],
                        position_id=position.position_id,
                        timestamp_utc=now_utc,
                        severity="WARNING",
                        alert_code="WARNING_MICROSTRUCTURE_LIQUIDITY_DETERIORATION",
                        headline="Wide Order-Book Spread Detected",
                        explanation=f"Top-of-book bid-ask spread widened to {spread_bps:.1f} bps (> 10.0 bps threshold). Execution exit friction is elevated.",
                        metrics_context={"spread_bps": spread_bps}
                    )
                )
            if ofi_15m is not None:
                if position.side == "LONG" and ofi_15m < -15.0:
                    alerts.append(
                        RiskAlert(
                            alert_id=hashlib.sha256(f"{position.position_id}:OFI_ADVERSE:{now_utc}".encode()).hexdigest()[:16],
                            position_id=position.position_id,
                            timestamp_utc=now_utc,
                            severity="WARNING",
                            alert_code="WARNING_ADVERSE_ORDER_FLOW",
                            headline="Adverse Order Flow Pressuring Long",
                            explanation=f"Order flow imbalance (OFI 15m = {ofi_15m:.1f}) exhibits heavy net selling pressure against LONG position.",
                            metrics_context={"ofi_15m": ofi_15m, "side": "LONG"}
                        )
                    )
                elif position.side == "SHORT" and ofi_15m > 15.0:
                    alerts.append(
                        RiskAlert(
                            alert_id=hashlib.sha256(f"{position.position_id}:OFI_ADVERSE:{now_utc}".encode()).hexdigest()[:16],
                            position_id=position.position_id,
                            timestamp_utc=now_utc,
                            severity="WARNING",
                            alert_code="WARNING_ADVERSE_ORDER_FLOW",
                            headline="Adverse Order Flow Pressuring Short",
                            explanation=f"Order flow imbalance (OFI 15m = {ofi_15m:.1f}) exhibits aggressive buying pressure against SHORT position.",
                            metrics_context={"ofi_15m": ofi_15m, "side": "SHORT"}
                        )
                    )
        else:
            microstructure_ctx = {"status": "L2_MICROSTRUCTURE_OFFLINE"}

        return PositionRiskSnapshot(
            position_id=position.position_id,
            evaluated_at_utc=now_utc,
            mark_price=mark_price,
            mark_price_status=price_status,
            data_age_seconds=data_age,
            source_provider=source,
            gross_unrealized_pnl_usd=round(gross_pnl, 2),
            accumulated_fees_usd=round(position.accumulated_fees_usd, 2),
            estimated_exit_fee_usd=round(estimated_exit_fee, 2),
            net_unrealized_pnl_usd=round(net_pnl, 2),
            net_return_pct=round(net_return_pct, 2),
            cost_basis_usd=round(cost_basis, 2),
            distance_to_stop_pct=dist_stop_pct,
            distance_to_target_pct=dist_target_pct,
            distance_to_liquidation_pct=dist_liq_pct,
            active_alerts=alerts,
            regime_context=regime_data or {},
            gbdt_forecasts=gbdt_forecasts or {},
            microstructure_context=microstructure_ctx
        )

"""Single, safe market-monitor API and shared experimental forecast endpoints."""
from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Query, Request

from api.market_drivers import build_empirical_forecast, get_market_dashboard

logger = logging.getLogger("btcognitive.market_monitor")
router = APIRouter(tags=["BTC/USD Market Monitor"])
Horizon = Literal["1h", "4h", "24h"]


def _gate(request: Request) -> dict:
    gate = getattr(request.app.state, "research_gate", None)
    if isinstance(gate, dict):
        return {
            "status": gate.get("status", "BLOCKED_PROVENANCE_UNVERIFIED"),
            "authorized": gate.get("authorized", False),
            "provenance_status": "VERIFIED" if gate.get("authorized") else "UNVERIFIED",
            "production_forecast_available": bool(gate.get("authorized")),
            "authorization_status": gate.get("authorization_status", "BLOCKED_AUDIT_FAILURE"),
            "reason_code": gate.get("reason_code", "NONE" if gate.get("authorized") else "BLOCKED_AUDIT_FAILURE"),
            "reason": gate.get("reason", "Frozen model provenance/evaluation is not authenticated."),
            "canonical_model_id": gate.get("canonical_model_id", "HAR-RS-DOW-v1.0"),
            "forecast_target": gate.get("forecast_target", "Annualized 7-Day Realized Variance (rv7d_var_ann)"),
            "forecast_horizon": gate.get("forecast_horizon", "168h (7 calendar days)"),
            "restricted_serving_scope": gate.get("restricted_serving_scope", "AUTHORIZED_FOR_VOLATILITY_RISK_ONLY"),
            "governance_breakdown": gate.get("governance_breakdown", {}),
        }
    return {
        "status": "BLOCKED_PROVENANCE_UNVERIFIED",
        "authorized": False,
        "authorization_status": "BLOCKED_PROVENANCE_UNVERIFIED",
        "reason_code": "FROZEN_INPUT_MISSING",
        "reason": "The frozen production model has not passed runtime provenance checks.",
        "canonical_model_id": "HAR-RS-DOW-v1.0",
        "forecast_target": "Annualized 7-Day Realized Variance (rv7d_var_ann)",
        "forecast_horizon": "168h (7 calendar days)",
    }


async def _dashboard(request: Request, horizon: Horizon = "24h") -> dict:
    try:
        payload = await get_market_dashboard(
            client=getattr(request.app.state, "http", None), horizon=horizon
        )
    except Exception as exc:  # Keep the market UI alive and expose no exception text/secrets.
        logger.warning("Market dashboard refresh failed: %s", type(exc).__name__)
        payload = {
            "status": "DATA_UNAVAILABLE",
            "generated_at": None,
            "market": {
                "status": "DATA_UNAVAILABLE", "symbol": "BTC/USD", "source": None,
                "price_usd": None, "bid_usd": None, "ask_usd": None,
                "source_timestamp": None, "retrieved_at": None, "age_seconds": None,
                "reason": "All configured public market providers are unavailable.",
            },
            "technical": {}, "candles": [], "candle_interval": "1h", "candle_count": 0,
            "forecast": build_empirical_forecast([], None, horizon), "drivers": [],
            "derivatives": {"status": "UNAVAILABLE", "funding_rate": None, "open_interest_contracts": None},
            "capital_flows": {"status": "NOT_CONFIGURED", "reason": "No verified provider configured."},
            "macro": {"status": "NOT_CONFIGURED", "reason": "No verified provider configured."},
            "provider_errors": {"dashboard": type(exc).__name__},
        }

    gate = _gate(request)
    is_authorized = gate["authorized"]
    payload["research"] = {
        **payload.get("research", {}),
        **gate,
        "provenance_status": "VERIFIED" if is_authorized else "UNVERIFIED",
        "production_forecast_available": is_authorized,
        "trading_enabled": False,
        "production_model": gate["canonical_model_id"] if is_authorized else "BLOCKED",
        "message": gate["reason"] if is_authorized else "Frozen model inputs/evaluation evidence are not authenticated. The displayed forecast is an independent empirical baseline only.",
    }
    return payload


@router.get("/health")
@router.get("/api/health")
def monitor_health(request: Request) -> dict:
    """The market-monitor service health reporting verified runtime readiness."""
    gate = _gate(request)
    from engine.status_contract import evaluate_system_status
    sys_status = evaluate_system_status().model_dump()
    mode = "PRODUCTION_VOLATILITY_INTELLIGENCE" if gate.get("authorized") else "MARKET_MONITOR_ONLY"
    return {
        "status": "ok",
        "application": "BTCognitive BTC/USD Market Monitor",
        "product_mode": "ANALYSIS_ONLY",
        "mode": mode,
        "live_trading_enabled": False,
        "order_submission_enabled": False,
        "directional_recommendation_status": "DISABLED",
        "price_forecast_status": "AVAILABLE",
        "execution_status": "DISABLED_ANALYSIS_ONLY",
        "research_alerts_enabled": True,
        "market_data": "FETCH_ON_REQUEST",
        "research_status": gate["authorization_status"],
        "research_authorized": gate["authorized"],
        "production_forecast_available": gate["authorized"],
        "models_loaded": gate["authorized"],
        "trading_enabled": False,
        "system_status": sys_status
    }


@router.get("/api/readiness")
@router.get("/api/terminal/readiness")
def readiness_diagnostics(request: Request) -> dict:
    """Authoritative diagnostic readiness endpoint with exact structured reason codes."""
    gate = getattr(request.app.state, "research_gate", None)
    if not isinstance(gate, dict):
        from validation.startup_gate import evaluate_runtime_readiness
        gate = evaluate_runtime_readiness()
    enriched = dict(gate)
    enriched.update({
        "product_mode": "ANALYSIS_ONLY",
        "live_trading_enabled": False,
        "order_submission_enabled": False,
        "directional_recommendation_status": "DISABLED",
        "price_forecast_status": "AVAILABLE",
        "execution_status": "DISABLED_ANALYSIS_ONLY",
        "research_alerts_enabled": True
    })
    return enriched


@router.get("/api/dashboard")
@router.get("/api/market-drivers")
async def dashboard(request: Request, horizon: Horizon = Query("24h")) -> dict:
    """One normalized source for quote, candles, factor observations and forecast bands."""
    return await _dashboard(request, horizon)


@router.get("/prediction/latest")
@router.get("/api/prediction/latest")
async def prediction_latest(
    request: Request, live: bool = False, horizon: Horizon = Query("24h")
) -> dict:
    # Serves the empirical baseline return range alongside verified production model status
    del live
    payload = await _dashboard(request, horizon)
    gate = payload["research"]
    is_authorized = gate.get("authorized", False)
    forecast = dict(payload["forecast"])
    forecast["market"] = payload["market"]
    forecast["research"] = payload["research"]
    forecast["research_gate"] = payload["research"]
    if is_authorized:
        forecast["research_authorization"] = gate.get("authorization_status", "AUTHORIZED_FOR_PRODUCTION")
    forecast["drivers"] = payload.get("drivers", [])
    forecast["system_classification"] = "EXPLORATORY STRATEGY ANALYTICS"
    forecast["validation_status"] = "NOT VALIDATED FOR PREDICTIVE OR ECONOMIC SUPERIORITY"
    return forecast


@router.get("/prediction/range")
@router.get("/api/prediction/range")
async def prediction_range(request: Request, horizon: Horizon = Query("24h")) -> dict:
    payload = await _dashboard(request, horizon)
    return payload["forecast"]


@router.get("/prediction/range/health")
@router.get("/api/prediction/range/health")
def prediction_range_health(request: Request) -> dict:
    gate = _gate(request)
    return {
        "status": "BLOCKED_PROVENANCE_UNVERIFIED",
        "production_model_status": "BLOCKED",
        "research_status": gate["authorization_status"],
        "reason_code": "LEGACY_EXCURSION_ARCHIVED",
        "reason": "Legacy excursion model (v3.0.0-excursion) is archived. Canonical production model is HAR-RS-DOW-v1.0 serving on /api/terminal/live.",
        "canonical_production_model": "HAR-RS-DOW-v1.0",
        "canonical_readiness_source": "/api/readiness",
        "empirical_baseline_available": "AVAILABLE",
        "production_forecast_available": False,
        "trading_enabled": False,
        "observed_coverage_pct": None,
        "sample_size": None,
    }


@router.get("/api/research/entry-tp-sl")
async def research_entry_tp_sl(request: Request) -> dict:
    gate = _gate(request)
    return {
        "status": "BLOCKED",
        "research_status": gate["authorization_status"],
        "claim_level": "UNVALIDATED",
        "provenance_status": "UNVERIFIED",
        "reason": "Live capital execution and directional trading signals are prohibited under BTCognitive Operating Contract.",
        "hypothetical_signal": None,
        "entry_price": None,
        "tp_price": None,
        "sl_price": None,
        "live_capital_authorized": False,
        "execution_mode": "READ_ONLY_RESEARCH",
        "trading_enabled": False,
    }


@router.get("/market/latest")
@router.get("/api/market/latest")
async def market_latest(request: Request) -> dict:
    payload = await _dashboard(request)
    return {
        **payload["market"],
        "technical": payload.get("technical", {}),
        "derivatives": payload.get("derivatives", {}),
        "data_status": payload.get("status"),
    }


@router.get("/forecast/latest")
@router.get("/api/forecast/latest")
@router.get("/prediction/forecast")
def get_forecast_latest(horizon: str = Query("15m")) -> dict:
    """
    Returns the authoritative research-only forecast contract with future points and uncertainty bands.
    Supports 15m (Coinbase 15m candles) and 1h/4h/24h (hourly verified bars).
    """
    from engine.forecast_engine_15m import generate_forecast_contract
    return generate_forecast_contract(horizon=horizon)


@router.get("/market/candles")
@router.get("/api/market/candles")
async def market_candles(
    request: Request,
    symbol: str = Query("BTC/USD"),
    interval: str = Query("1h"),
    limit: int = Query(168, ge=1, le=500),
) -> dict:
    clean_sym = symbol.upper().replace(" ", "").replace("-", "").replace("/", "")
    if clean_sym not in {"BTCUSD", "BTCUSDT"}:
        return {
            "status": "UNSUPPORTED_REQUEST", "symbol": symbol, "interval": interval,
            "count": 0, "candles": [], "reason": "Only validated BTC/USD spot candles are exposed.",
        }

    if interval == "15m":
        from engine.coinbase_15m_adapter import coinbase_15m_adapter
        try:
            df_15m, meta = coinbase_15m_adapter.get_or_sync_15m_candles(target_count=limit)
            candles = []
            for _, r in df_15m.tail(limit).iterrows():
                candles.append({
                    "time": int(r["epoch_time"]),
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "volume": float(r["volume"]),
                })
            return {
                "status": "LIVE", "symbol": "BTC/USD", "interval": "15m",
                "count": len(candles), "candles": candles,
                "source": "Coinbase Exchange Spot REST",
                "retrieved_at": meta.get("last_completed_candle_utc"),
                "degraded": False,
            }
        except Exception as e:
            return {
                "status": "DATA_UNAVAILABLE", "symbol": "BTC/USD", "interval": "15m",
                "count": 0, "candles": [], "reason": str(e), "degraded": True,
            }

    if interval != "1h":
        return {
            "status": "UNSUPPORTED_REQUEST", "symbol": symbol, "interval": interval,
            "count": 0, "candles": [], "reason": "Only validated BTC/USD 15m and 1h spot candles are exposed.",
        }

    payload = await _dashboard(request)
    candles = payload.get("candles", [])[-limit:]
    return {
        "status": payload.get("status"), "symbol": "BTC/USD", "interval": "1h",
        "count": len(candles), "candles": candles,
        "source": payload.get("market", {}).get("source"),
        "retrieved_at": payload.get("market", {}).get("retrieved_at"),
        "degraded": payload.get("status") != "LIVE",
    }


@router.get("/market/comparator")
@router.get("/api/market/comparator")
async def market_comparator(request: Request) -> dict:
    """
    BTCognitive Multi-Exchange Spot Comparator (PRD-CMP-14).
    Evaluates real-time spot BTC-USD quotes across Coinbase, Kraken, and Bitstamp.
    Identifies active primary provider, pairwise divergence in basis points,
    and stale/degraded feeds.
    """
    from engine.spot_exchange_comparator import fetch_and_compare_spot_quotes
    client = getattr(request.app.state, "http", None)
    return await fetch_and_compare_spot_quotes(client=client)
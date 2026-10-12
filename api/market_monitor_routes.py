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
            "authorized": False,
            "reason": gate.get("reason", "Frozen model provenance/evaluation is not authenticated."),
        }
    return {
        "status": "BLOCKED_PROVENANCE_UNVERIFIED",
        "authorized": False,
        "reason": "The frozen production model has not passed runtime provenance checks.",
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
    payload["research"] = {
        **payload.get("research", {}),
        **_gate(request),
        "production_forecast_available": False,
        "trading_enabled": False,
        "production_model": "BLOCKED",
    }
    return payload


@router.get("/health")
@router.get("/api/health")
def monitor_health(request: Request) -> dict:
    """The market-monitor service can be healthy while frozen research remains blocked."""
    gate = _gate(request)
    return {
        "status": "ok",
        "application": "BTCognitive BTC/USD Market Monitor",
        "mode": "MARKET_MONITOR_ONLY",
        "market_data": "FETCH_ON_REQUEST",
        "research_status": gate["status"],
        "research_authorized": False,
        "production_forecast_available": False,
        "trading_enabled": False,
    }


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
    # Compatibility endpoint, intentionally routes to the same non-authorizing baseline.
    del live
    payload = await _dashboard(request, horizon)
    forecast = dict(payload["forecast"])
    forecast["market"] = payload["market"]
    forecast["research"] = payload["research"]
    forecast["drivers"] = payload.get("drivers", [])
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
        "research_status": gate["status"],
        "reason": gate["reason"],
        "empirical_baseline_available": "DEPENDS_ON_LIVE_DATA_AND_HISTORY",
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
        "research_status": gate["status"],
        "claim_level": "UNVALIDATED",
        "provenance_status": "UNVERIFIED",
        "reason": gate["reason"],
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


@router.get("/market/candles")
@router.get("/api/market/candles")
async def market_candles(
    request: Request,
    symbol: str = Query("BTC/USD"),
    interval: str = Query("1h"),
    limit: int = Query(168, ge=1, le=168),
) -> dict:
    if symbol.upper().replace(" ", "") not in {"BTC/USD", "BTCUSD"} or interval != "1h":
        return {
            "status": "UNSUPPORTED_REQUEST", "symbol": symbol, "interval": interval,
            "count": 0, "candles": [], "reason": "Only validated BTC/USD closed 1-hour spot candles are exposed.",
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
"""Single, safe market-monitor API and shared experimental forecast endpoints."""
from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Query, Request

from api.market_drivers import build_empirical_forecast, get_market_dashboard
from models.authoritative_model_registry import (
    AuthorizationStatus,
    get_active_production_model,
    is_production_authorized,
)

logger = logging.getLogger("btcognitive.market_monitor")
router = APIRouter(tags=["BTC/USD Market Monitor"])
Horizon = Literal["1h", "4h", "24h"]
BITSTAMP_FRESHNESS_SECONDS = 60.0


def _gate(request: Request, gate_data: object = None) -> dict:
    gate = gate_data if isinstance(gate_data, dict) else getattr(
        request.app.state, "research_gate", None
    )
    if isinstance(gate, dict):
        authorization_status = gate.get(
            "authorization_status", "BLOCKED_AUDIT_FAILURE"
        )
        registry_status = get_active_production_model().authorization_status
        serving_authorized = is_production_authorized(gate)
        if (
            registry_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY
            and authorization_status == AuthorizationStatus.AUTHORIZED_FOR_PRODUCTION.value
        ):
            authorization_status = AuthorizationStatus.OFFLINE_RESEARCH_ONLY.value
        provenance_status = (
            "VERIFIED_RESEARCH_ONLY"
            if authorization_status == "OFFLINE_RESEARCH_ONLY"
            else ("VERIFIED" if serving_authorized else "UNVERIFIED")
        )
        return {
            "status": (
                "OFFLINE_RESEARCH_ONLY"
                if authorization_status == "OFFLINE_RESEARCH_ONLY"
                else gate.get("status", "BLOCKED_PROVENANCE_UNVERIFIED")
            ),
            "authorized": serving_authorized,
            "provenance_status": provenance_status,
            "production_forecast_available": serving_authorized,
            "authorization_status": authorization_status,
            "research_edge_status": "NO_GO_NO_VALIDATED_EDGE",
            "trading_enabled": False,
            "live_capital_authorized": False,
            "reason_code": (
                "MODEL_UNAUTHORIZED"
                if authorization_status == "OFFLINE_RESEARCH_ONLY"
                else gate.get("reason_code", "NONE" if serving_authorized else "MODEL_UNAUTHORIZED")
            ),
            "reason": (
                "Runtime integrity checks do not grant authorization; governance keeps forecasts offline."
                if authorization_status == "OFFLINE_RESEARCH_ONLY"
                else gate.get("reason", "Frozen model provenance/evaluation is not authenticated.")
            ),
            "canonical_model_id": gate.get("canonical_model_id", "HAR-RS-DOW-v1.0"),
            "forecast_target": gate.get("forecast_target", "Annualized 7-Day Realized Variance (rv7d_var_ann)"),
            "forecast_horizon": gate.get("forecast_horizon", "168h (7 calendar days)"),
            "restricted_serving_scope": gate.get("restricted_serving_scope", "NONE"),
            "governance_breakdown": gate.get("governance_breakdown", {}),
        }
    return {
        "status": "BLOCKED_PROVENANCE_UNVERIFIED",
        "authorized": False,
        "authorization_status": "BLOCKED_PROVENANCE_UNVERIFIED",
        "provenance_status": "UNVERIFIED",
        "research_edge_status": "NO_GO_NO_VALIDATED_EDGE",
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
        "provenance_status": gate["provenance_status"],
        "production_forecast_available": is_authorized,
        "trading_enabled": False,
        "production_model": gate["canonical_model_id"] if is_authorized else "BLOCKED",
        "message": (
            gate["reason"]
            if is_authorized or gate["authorization_status"] == "OFFLINE_RESEARCH_ONLY"
            else "Frozen model inputs/evaluation evidence are not authenticated. "
            "The displayed forecast is an independent empirical baseline only."
        ),
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
    enriched.update(_gate(request, gate))
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
@router.get("/api/market/dashboard")
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
        forecast["research_authorization"] = gate.get("authorization_status", "BLOCKED_AUDIT_FAILURE")
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
    symbol: str = Query("BTC-USD"),
    interval: str = Query("1h"),
    limit: int = Query(500, ge=1, le=500),
) -> dict:
    from engine.data_mode import get_data_mode, DataMode, is_external_network_permitted

    mode = get_data_mode()
    clean_sym = symbol.upper().replace(" ", "").replace("-", "").replace("/", "")
    if clean_sym != "BTCUSD":
        return {
            "status": "UNSUPPORTED_REQUEST", "symbol": "BTC-USD", "interval": interval,
            "count": 0, "candles": [], "reason": "Only validated BTC-USD spot candles are exposed.",
        }

    if interval == "1m":
        feed = getattr(request.app.state, "bitstamp_trade_feed", None)
        if feed is None:
            return _unavailable_bitstamp_snapshot(
                "The Bitstamp trade feed is not configured in this application lifecycle."
            )
        try:
            snapshot = feed.snapshot(limit=limit)
        except Exception as exc:
            logger.warning("Bitstamp trade feed snapshot failed: %s", type(exc).__name__)
            return _unavailable_bitstamp_snapshot("The Bitstamp trade feed snapshot is unavailable.")
        return _normalize_bitstamp_snapshot(snapshot, limit)

    if interval == "15m":
        if not is_external_network_permitted():
            from engine.coinbase_15m_adapter import coinbase_15m_adapter
            cached = coinbase_15m_adapter.load_cached()
            if cached is not None:
                df_15m, meta = cached
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
                    "status": "HISTORICAL_SNAPSHOT", "symbol": "BTC-USD", "interval": "15m",
                    "count": len(candles), "candles": candles,
                    "source": "LOCAL_HISTORICAL_CACHE",
                    "retrieved_at": meta.get("metadata", {}).get("last_completed_candle_utc") if isinstance(meta, dict) else None,
                    "degraded": True,
                }
            return {
                "status": "DATA_UNAVAILABLE", "symbol": "BTC-USD", "interval": "15m",
                "count": 0, "candles": [], "reason": "15m candles unavailable in offline/fixture mode (external network blocked).",
                "degraded": True,
            }
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
                "status": "LIVE", "symbol": "BTC-USD", "interval": "15m",
                "count": len(candles), "candles": candles,
                "source": "Coinbase Exchange Spot REST",
                "retrieved_at": meta.get("last_completed_candle_utc"),
                "degraded": False,
            }
        except Exception as e:
            return {
                "status": "DATA_UNAVAILABLE", "symbol": "BTC-USD", "interval": "15m",
                "count": 0, "candles": [], "reason": str(e), "degraded": True,
            }

    if interval != "1h":
        return {
            "status": "UNSUPPORTED_REQUEST", "symbol": "BTC-USD", "interval": interval,
            "count": 0, "candles": [], "reason": "Only validated BTC-USD 15m and 1h spot candles are exposed.",
        }

    # Hourly market data is served only from a validated local snapshot.
    from engine.bitstamp_market_data_service import BITSTAMP_PARQUET_PATH, BITSTAMP_PROVENANCE_PATH
    import os, json, pandas as pd
    from engine.regime_strategy_tournament import _validate_hourly_candles, check_data_freshness_and_gaps

    if mode != DataMode.FIXTURE and os.path.exists(BITSTAMP_PARQUET_PATH):
        try:
            df_bs = pd.read_parquet(BITSTAMP_PARQUET_PATH)
            if df_bs.empty:
                raise ValueError("Local Bitstamp snapshot is empty.")
            if "available_time" not in df_bs:
                df_bs = df_bs.copy()
                df_bs["available_time"] = pd.to_datetime(df_bs["timestamp"], utc=True) + pd.Timedelta(hours=1)
            validation_df = df_bs.copy()
            now_utc = pd.Timestamp.now(tz="UTC")
            validation_df["is_closed"] = pd.to_datetime(validation_df["available_time"], utc=True, errors="coerce") <= now_utc
            valid, validation_reason = _validate_hourly_candles(
                validation_df,
                require_closed=True,
                as_of=now_utc.to_pydatetime()
            )
            if not valid:
                return {
                    "status": "DATA_UNAVAILABLE",
                    "freshness_status": "UNAVAILABLE",
                    "data_status": "LOCAL_HISTORICAL_SNAPSHOT",
                    "symbol": "BTC-USD",
                    "interval": "1h",
                    "count": 0,
                    "candles": [],
                    "source": "LOCAL_BITSTAMP_CACHE",
                    "retrieved_at": None,
                    "degraded": True,
                    "reason": validation_reason,
                }
            freshness = check_data_freshness_and_gaps(validation_df, max_age_hours=2.0)
            freshness_status = "FRESH" if freshness["is_fresh"] else "STALE"
            candles = []
            for _, r in df_bs.tail(limit).iterrows():
                candles.append({
                    "time": int(pd.to_datetime(r["timestamp"], utc=True).timestamp()),
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "volume": float(r["volume"]),
                })
            retrieved_at = None
            if os.path.exists(BITSTAMP_PROVENANCE_PATH):
                with open(BITSTAMP_PROVENANCE_PATH, "r", encoding="utf-8") as pf:
                    prov = json.load(pf)
                    retrieved_at = prov.get("retrieval_timestamp_utc")
            return {
                "status": freshness_status,
                "freshness_status": freshness_status,
                "data_status": "LOCAL_HISTORICAL_SNAPSHOT",
                "symbol": "BTC-USD",
                "interval": "1h",
                "count": len(candles),
                "candles": candles,
                "source": "LOCAL_BITSTAMP_CACHE",
                "retrieved_at": retrieved_at,
                "latest_completed_candle_utc": freshness.get("latest_candle_time_utc"),
                "observed_age_seconds": freshness.get("observed_age_seconds"),
                "degraded": freshness_status != "FRESH",
            }
        except Exception as e:
            logger.warning(f"Failed loading Bitstamp cache for candles endpoint: {e}")
            return {
                "status": "DATA_UNAVAILABLE",
                "freshness_status": "UNAVAILABLE",
                "data_status": "LOCAL_HISTORICAL_SNAPSHOT",
                "symbol": "BTC-USD",
                "interval": "1h",
                "count": 0,
                "candles": [],
                "source": "LOCAL_BITSTAMP_CACHE",
                "retrieved_at": None,
                "degraded": True,
                "reason": "Local Bitstamp snapshot failed validation.",
            }

    if mode == DataMode.PROVIDER and not is_external_network_permitted():
        return {
            "status": "DATA_UNAVAILABLE", "symbol": "BTC-USD", "interval": "1h",
            "count": 0, "candles": [], "source": None, "retrieved_at": None,
            "reason": "PROVIDER_NOT_CONFIGURED", "degraded": True,
        }

    payload = await _dashboard(request)
    candles = payload.get("candles", [])[-limit:]
    source = payload.get("market", {}).get("source")
    if payload.get("status") == "DATA_UNAVAILABLE" or not candles:
        return {
            "status": "DATA_UNAVAILABLE",
            "freshness_status": "UNAVAILABLE",
            "data_status": "LOCAL_HISTORICAL_SNAPSHOT",
            "symbol": "BTC-USD",
            "interval": "1h",
            "count": 0,
            "candles": [],
            "source": None,
            "retrieved_at": None,
            "degraded": True,
            "reason": "Validated local BTC-USD candles are unavailable.",
        }
    df_local = pd.DataFrame(candles)
    df_local["timestamp"] = pd.to_datetime(df_local["time"], unit="s", utc=True)
    df_local["is_closed"] = True
    valid, validation_reason = _validate_hourly_candles(
        df_local,
        require_closed=True,
        as_of=pd.Timestamp.now(tz="UTC").to_pydatetime()
    )
    if not valid:
        return {
            "status": "DATA_UNAVAILABLE",
            "freshness_status": "UNAVAILABLE",
            "data_status": "LOCAL_HISTORICAL_SNAPSHOT",
            "symbol": "BTC-USD",
            "interval": "1h",
            "count": 0,
            "candles": [],
            "source": source,
            "retrieved_at": payload.get("market", {}).get("retrieved_at"),
            "degraded": True,
            "reason": validation_reason,
        }
    freshness = check_data_freshness_and_gaps(df_local, max_age_hours=2.0)
    freshness_status = "FRESH" if freshness["is_fresh"] else "STALE"
    return {
        "status": freshness_status,
        "freshness_status": freshness_status,
        "data_status": "LOCAL_HISTORICAL_SNAPSHOT",
        "symbol": "BTC-USD",
        "interval": "1h",
        "count": len(candles),
        "candles": candles,
        "source": "LOCAL_HISTORICAL_SNAPSHOT" if source == "LOCAL_HISTORICAL_SNAPSHOT" else source,
        "retrieved_at": payload.get("market", {}).get("retrieved_at"),
        "latest_completed_candle_utc": freshness.get("latest_candle_time_utc"),
        "observed_age_seconds": freshness.get("observed_age_seconds"),
        "degraded": freshness_status != "FRESH",
    }


def _timestamp_epoch_seconds(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        numeric = None
    if numeric is not None:
        if not math.isfinite(numeric):
            return None
        return numeric / 1000.0 if abs(numeric) >= 1e12 else numeric
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except (TypeError, ValueError, OverflowError):
        return None


def _unavailable_bitstamp_snapshot(reason: str) -> dict:
    return {
        "status": "DATA_UNAVAILABLE",
        "freshness_status": "UNAVAILABLE",
        "test_only": False,
        "data_origin": "UNAVAILABLE",
        "symbol": "BTC/USD",
        "exchange": "Bitstamp",
        "market_type": "SPOT",
        "interval": "1m",
        "source": "bitstamp",
        "count": 0,
        "candles": [],
        "last_event_timestamp": None,
        "last_receive_timestamp": None,
        "latest_completed_candle_timestamp": None,
        "latest_provisional_candle_timestamp": None,
        "event_to_receive_delay_seconds": None,
        "gap_count": 0,
        "duplicate_count": 0,
        "invalid_count": 0,
        "reason": reason,
        "analysis": {
            "status": "UNAVAILABLE",
            "reason_code": "FEED_NOT_CONFIGURED",
            "reason": "No 1-minute inference engine is registered for this candle contract.",
            "engine_invoked": False,
        },
    }


def _normalize_bitstamp_snapshot(snapshot: object, limit: int) -> dict:
    if not isinstance(snapshot, dict):
        return _unavailable_bitstamp_snapshot("The Bitstamp feed returned a malformed snapshot.")

    identity_ok = (
        str(snapshot.get("symbol", "")).upper().replace("-", "").replace("/", "") == "BTCUSD"
        and str(snapshot.get("exchange", "")).lower() == "bitstamp"
        and str(snapshot.get("market_type", "")).upper() == "SPOT"
        and str(snapshot.get("interval", "")).lower() == "1m"
        and str(snapshot.get("source", "")).lower() == "bitstamp"
    )
    if not identity_ok:
        return _unavailable_bitstamp_snapshot("The feed snapshot identity does not match Bitstamp BTC/USD spot 1m.")

    raw_candles = snapshot.get("candles")
    if not isinstance(raw_candles, list):
        return _unavailable_bitstamp_snapshot("The Bitstamp feed returned no candle list.")

    candles = []
    for raw in raw_candles[-limit:]:
        if not isinstance(raw, dict):
            return _unavailable_bitstamp_snapshot("The Bitstamp feed returned a malformed candle.")
        try:
            candle_time = _timestamp_epoch_seconds(raw.get("time"))
            values = {
                name: float(raw[name])
                for name in ("open", "high", "low", "close", "volume")
            }
        except (KeyError, TypeError, ValueError, OverflowError):
            return _unavailable_bitstamp_snapshot("The Bitstamp feed returned an incomplete candle.")
        if (
            candle_time is None
            or not all(math.isfinite(value) for value in values.values())
            or min(values["open"], values["high"], values["low"], values["close"]) <= 0
            or values["volume"] < 0
            or values["high"] < max(values["open"], values["close"])
            or values["low"] > min(values["open"], values["close"])
            or values["high"] < values["low"]
        ):
            return _unavailable_bitstamp_snapshot("A Bitstamp candle failed OHLCV validation.")
        candles.append({
            "time": int(candle_time),
            **values,
            "is_closed": bool(raw.get("is_closed", False)),
            "quality_status": raw.get("quality_status", "VALID"),
            "source": "bitstamp",
            "event_timestamp": raw.get("event_timestamp"),
            "received_timestamp": raw.get("received_timestamp"),
        })

    if any(candles[index]["time"] >= candles[index + 1]["time"] for index in range(len(candles) - 1)):
        return _unavailable_bitstamp_snapshot("Bitstamp candle timestamps are duplicated or out of order.")

    last_event = snapshot.get("last_event_timestamp")
    last_receive = snapshot.get(
        "last_receive_timestamp", snapshot.get("last_receipt_timestamp")
    )
    event_epoch = _timestamp_epoch_seconds(last_event)
    receive_epoch = _timestamp_epoch_seconds(last_receive)
    try:
        delay = float(snapshot.get("event_to_receive_delay_seconds"))
        if not math.isfinite(delay):
            delay = None
    except (TypeError, ValueError, OverflowError):
        delay = None
    if delay is None and event_epoch is not None and receive_epoch is not None:
        delay = receive_epoch - event_epoch

    status_value = str(snapshot.get("status", "DATA_UNAVAILABLE")).upper()
    if status_value not in {"ACTIVE", "STALE", "DISCONNECTED", "DATA_UNAVAILABLE"}:
        status_value = "DATA_UNAVAILABLE"
    now_epoch = time.time()
    event_age = None if event_epoch is None else now_epoch - event_epoch
    receive_age = None if receive_epoch is None else now_epoch - receive_epoch
    if status_value == "ACTIVE" and (
        not candles
        or event_epoch is None
        or receive_epoch is None
        or event_age > BITSTAMP_FRESHNESS_SECONDS
        or event_age < -5.0
        or receive_age > BITSTAMP_FRESHNESS_SECONDS
        or receive_age < -5.0
        or (delay is not None and delay < -5.0)
        or (delay is not None and delay > BITSTAMP_FRESHNESS_SECONDS)
    ):
        status_value = "STALE" if candles else "DATA_UNAVAILABLE"

    completed = [candle for candle in candles if candle["is_closed"]]
    provisional = [candle for candle in candles if not candle["is_closed"]]
    latest_completed = snapshot.get("latest_completed_candle_timestamp")
    latest_provisional = snapshot.get("latest_provisional_candle_timestamp")
    if latest_completed is None and completed:
        latest_completed = completed[-1]["time"]
    if latest_provisional is None and provisional:
        latest_provisional = provisional[-1]["time"]

    freshness = (
        "FRESH" if status_value == "ACTIVE"
        else "STALE" if status_value in {"STALE", "DISCONNECTED"}
        else "UNAVAILABLE"
    )
    reason = snapshot.get("reason")
    if status_value == "STALE":
        reason = reason or "The latest Bitstamp trade observation is stale."
    elif status_value == "DISCONNECTED":
        reason = reason or "The Bitstamp trade feed is disconnected."
    elif status_value == "DATA_UNAVAILABLE":
        reason = reason or "No validated Bitstamp trade candles are available."
    test_only = snapshot.get("test_only") is True
    data_origin = "TEST_FIXTURE_ONLY" if test_only else "PROVIDER_OBSERVATION"
    analysis = {
        "status": "DATA_UNAVAILABLE",
        "engine_invoked": False,
        "reason_code": (
            "STALE_DATA"
            if freshness != "FRESH" or status_value != "ACTIVE"
            else "INSUFFICIENT_CLOSED_1M_HISTORY"
        ),
        "reason": (
            "Fresh, active observations are required before descriptive market intelligence can run."
            if freshness != "FRESH" or status_value != "ACTIVE"
            else "Market intelligence requires at least 20 consecutive closed Bitstamp 1-minute candles."
        ),
    }
    closed_tail = completed[-20:]
    if freshness == "FRESH" and status_value == "ACTIVE" and len(closed_tail) == 20:
        times = [candle["time"] for candle in closed_tail]
        contiguous = all(
            right - left == 60
            for left, right in zip(times, times[1:])
        )
        quality_valid = all(
            str(candle.get("quality_status", "")).upper() == "VALID"
            for candle in closed_tail
        )
        if contiguous and quality_valid:
            try:
                import pandas as pd
                from models.market_intelligence import MarketIntelligenceEngine

                frame = pd.DataFrame(closed_tail)
                engine = MarketIntelligenceEngine()
                analysis = {
                    "status": "UNVALIDATED" if freshness == "FRESH" else "STALE",
                    "engine_invoked": True,
                    "engine": "MarketIntelligenceEngine",
                    "input_source": "bitstamp",
                    "input_symbol": "BTC/USD",
                    "input_interval": "1m",
                    "input_candle_count": len(closed_tail),
                    "input_freshness": freshness,
                    "test_only": test_only,
                    "data_origin": data_origin,
                    "components": {
                        "structure": engine.compute_structure(frame),
                        "momentum": engine.compute_momentum(frame),
                    },
                    "reason": (
                        (
                            "Deterministic local test fixture only; not market data. Descriptive structure "
                            "and momentum are unvalidated and are not a directional forecast or trading signal."
                        )
                        if test_only
                        else "Descriptive structure and momentum only; this output is unvalidated and is not a "
                        "directional forecast or trading signal."
                    ),
                }
            except Exception as exc:
                logger.warning("Bitstamp market-intelligence calculation failed: %s", type(exc).__name__)
                analysis = {
                    "status": "DATA_UNAVAILABLE",
                    "engine_invoked": False,
                    "reason_code": "ENGINE_ERROR",
                    "reason": "Existing market-intelligence components could not process the validated candle input.",
                }
        else:
            analysis.update({
                "reason_code": "INVALID_OR_NONCONSECUTIVE_CANDLES",
                "reason": (
                    "Market intelligence requires 20 valid, consecutive, closed 1-minute candles; "
                    "the available candle tail does not meet that contract."
                ),
            })

    return {
        **snapshot,
        "status": status_value,
        "freshness_status": freshness,
        "test_only": test_only,
        "data_origin": data_origin,
        "symbol": "BTC/USD",
        "exchange": "Bitstamp",
        "market_type": "SPOT",
        "interval": "1m",
        "source": "bitstamp",
        "count": len(candles),
        "candles": candles,
        "last_event_timestamp": last_event,
        "last_receive_timestamp": last_receive,
        "latest_completed_candle_timestamp": latest_completed,
        "latest_provisional_candle_timestamp": latest_provisional,
        "event_to_receive_delay_seconds": delay,
        "gap_count": int(snapshot.get("gap_count") or 0),
        "duplicate_count": int(snapshot.get("duplicate_count") or 0),
        "invalid_count": int(snapshot.get("invalid_count") or 0),
        "reason": reason,
        "analysis": analysis,
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

"""
api/server.py — BTCognitive Production FastAPI Application Server (Hardened)
=============================================================================
Configures FastAPI with:
1. OWASP ASVS 5.0 Security Headers Middleware.
2. Rate Limiting Middleware with tier-based bucket limits.
3. Strict CORS with explicit origin allowlists.
4. Trusted Host Middleware against host-header poisoning.
5. Global Sanitized Exception Handling (zero stack-trace leakage).
6. Hardened WebSocket streaming manager with connection limits and message size caps.
7. Modular APIRouters.
"""

import os
import sys
import json
import time
import asyncio
import logging
import inspect
from contextlib import asynccontextmanager
from typing import List, Dict
from collections import defaultdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status, HTTPException, Query
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.security import (
    ALLOWED_ORIGINS,
    ALLOWED_HOSTS,
    MAX_WEBSOCKET_CONNECTIONS_PER_IP,
    MAX_WEBSOCKET_MESSAGE_BYTES
)
from api.http_client import get_shared_client, close_shared_client
from engine.feature_cache import feature_cache
from engine.inference_service import live_engine
from engine.security_audit import security_audit
from api.security_middleware import (
    SecurityHeadersMiddleware,
    RateLimitingMiddleware,
    sanitized_exception_handler
)

# Import modular route handlers
from api.routes_market import router as market_router
from api.routes_prediction import router as prediction_router
from api.routes_arena import router as arena_router
from api.routes_notifications import router as notifications_router
from api.genome_routes import router as genome_router
from api.routes_analogs import router as analogs_router
from api.routes_terminal import router as terminal_router
from api.market_monitor_routes import router as market_monitor_router
from api.routes_research import router as research_router
from api.routes_tournament import router as tournament_router
from api.routes_user_positions import router as user_positions_router
from api.routes_manual_journal import router as manual_journal_router


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("btcognitive.server")


# ---------------------------------------------------------------------------
# Hardened WebSocket Connection Manager
# ---------------------------------------------------------------------------

class HardenedConnectionManager:
    """Manages active WebSocket connections with per-IP limits and safety bounds."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connections_per_ip: Dict[str, int] = defaultdict(int)

    async def connect(self, websocket: WebSocket, client_ip: str) -> bool:
        if self.connections_per_ip[client_ip] >= MAX_WEBSOCKET_CONNECTIONS_PER_IP:
            security_audit.log_event(
                event_type="WEB_SOCKET_REJECT",
                severity="WARNING",
                client_ip=client_ip,
                path="/ws",
                details={"reason": "Connection limit per IP exceeded", "limit": MAX_WEBSOCKET_CONNECTIONS_PER_IP}
            )
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False

        await websocket.accept()
        self.active_connections.append(websocket)
        self.connections_per_ip[client_ip] += 1
        
        security_audit.log_event(
            event_type="WEB_SOCKET_CONNECT",
            severity="INFO",
            client_ip=client_ip,
            path="/ws"
        )
        return True

    def disconnect(self, websocket: WebSocket, client_ip: str):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if self.connections_per_ip[client_ip] > 0:
            self.connections_per_ip[client_ip] -= 1

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                pass


ws_manager = HardenedConnectionManager()


LOCAL_FIXTURE_CANDLE_START = 1_704_067_200
LOCAL_FIXTURE_CANDLE_BARS = tuple(
    (100.0 + index, 100.75 + index, 99.5 + index, 100.25 + index, 1.0 + index / 10)
    for index in range(20)
)


class LocalFixtureCandleFeed:
    """Deterministic in-memory chart bars; this object has no provider lifecycle."""

    def snapshot(self, limit: int = 500) -> dict:
        from engine.data_mode import LOCAL_FIXTURE_LABEL

        count = max(0, int(limit))
        candles = [
            {
                "time": LOCAL_FIXTURE_CANDLE_START + index * 60,
                "open": values[0],
                "high": values[1],
                "low": values[2],
                "close": values[3],
                "volume": values[4],
                "is_closed": True,
                "source": "fixture",
                "test_only": True,
            }
            for index, values in enumerate(LOCAL_FIXTURE_CANDLE_BARS)
        ][-count:] if count else []
        return {
            "status": "FIXTURE_ONLY",
            "freshness_status": "NOT_APPLICABLE",
            "symbol": "BTC-USD",
            "interval": "1m",
            "source": "fixture",
            "test_only": True,
            "data_origin": "TEST_FIXTURE_ONLY",
            "label": LOCAL_FIXTURE_LABEL,
            "count": len(candles),
            "candles": candles,
            "analysis": {
                "status": "UNVALIDATED",
                "engine_invoked": False,
                "reason_code": "FIXTURE_NOT_MARKET_DATA",
                "reason": "Analysis is not run for deterministic local fixture bars.",
                "test_only": True,
                "data_origin": "TEST_FIXTURE_ONLY",
            },
        }


from validation.startup_gate import evaluate_runtime_readiness, verify_scientific_contract
from models.authoritative_model_registry import is_production_authorized

# ---------------------------------------------------------------------------
# Application Lifespan Context Manager
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Authoritative lifecycle initializing market monitoring and verified production models."""
    from engine.data_mode import get_data_mode, is_local_fixture_feed_enabled

    data_mode = get_data_mode()
    fixture_mode = data_mode == "fixture"
    app.state.data_mode = data_mode
    app.state.local_fixture_feed_enabled = is_local_fixture_feed_enabled(data_mode)
    app.state.local_fixture_feed = (
        LocalFixtureCandleFeed() if app.state.local_fixture_feed_enabled else None
    )
    if fixture_mode:
        logger.info("Fixture mode startup: protected market data and model readiness are unavailable.")
    else:
        logger.info("Verifying scientific freeze contract before startup...")
        # Priority 1 Scientific Startup Gate: refuses startup on tampered artifact or invalid contract
        verify_scientific_contract()
    readiness = evaluate_runtime_readiness(force_refresh=True)
    app.state.research_gate = readiness

    if is_production_authorized(readiness):
        logger.info(
            "Authoritative research gate AUTHORIZED [model=%s, target=%s]. Pre-warming canonical terminal...",
            readiness.get("canonical_model_id"),
            readiness.get("forecast_target")
        )
        try:
            from api.routes_terminal import _init_live_terminal
            _init_live_terminal()
        except Exception as exc:
            logger.warning("Terminal pre-initialization notice: %s", exc)
    else:
        logger.warning(
            "Authoritative research gate BLOCKED [%s]: %s",
            readiness.get("reason_code"),
            readiness.get("reason")
        )

    logger.info("Initializing BTCognitive market data client and feature cache...")
    app.state.http = get_shared_client()
    app.state.ws_manager = ws_manager
    if not fixture_mode:
        feature_cache.initialize()
    # Live execution and background auto-retraining remain strictly disabled for security.
    live_engine.is_running = False

    # Bitstamp trade ingestion is observational only; the feed's ingestion path
    # does not invoke inference or emit exchange-mixed ticks.
    trade_feed = None if fixture_mode else getattr(app.state, "bitstamp_trade_feed", None)
    from engine.data_mode import is_external_network_permitted
    from engine.market_data_feed import BitstampTradeFeed
    if trade_feed is None and not fixture_mode:
        try:
            trade_feed = BitstampTradeFeed()
        except Exception as exc:
            logger.warning(
                "Bitstamp trade feed unavailable at startup: %s",
                type(exc).__name__,
            )
    app.state.bitstamp_trade_feed = trade_feed
    try:
        network_permitted = is_external_network_permitted()
    except Exception as exc:
        network_permitted = False
        network_block_reason = (
            f"External Bitstamp market-data access is blocked by policy error: {type(exc).__name__}."
        )
    else:
        network_block_reason = (
            "External Bitstamp market-data access is denied by the authoritative data-mode policy."
        )

    if not network_permitted:
        logger.info("%s", network_block_reason)
        if isinstance(trade_feed, BitstampTradeFeed):
            trade_feed.mark_network_blocked(network_block_reason)
        elif trade_feed is not None:
            # Do not expose an injected feed that might contain stale or
            # externally sourced data when network permission is denied.
            try:
                trade_feed = BitstampTradeFeed()
                trade_feed.mark_network_blocked(network_block_reason)
                app.state.bitstamp_trade_feed = trade_feed
            except Exception as exc:
                logger.warning(
                    "Bitstamp blocked-status feed unavailable at startup: %s",
                    type(exc).__name__,
                )
                trade_feed = None
                app.state.bitstamp_trade_feed = None
    elif trade_feed is not None:
        try:
            start_result = trade_feed.start()
            if inspect.isawaitable(start_result):
                start_result = await start_result
            if start_result is False:
                snapshot = trade_feed.snapshot() if hasattr(trade_feed, "snapshot") else {}
                feed_state = snapshot.get("feed_state", "UNKNOWN") if isinstance(snapshot, dict) else "UNKNOWN"
                logger.warning("Bitstamp trade feed did not start: %s", feed_state)
        except Exception as exc:
            logger.warning("Bitstamp trade feed startup failed: %s", type(exc).__name__)

    # Fixture mode has no protected market snapshot to evaluate for research alerts.
    alert_worker_task = None
    if not fixture_mode:
        from api.notifications import notification_manager

        async def _research_alert_worker():
            logger.info("Started background research-condition alert evaluator (interval=60s).")
            while True:
                try:
                    await asyncio.sleep(60.0)
                    await notification_manager.evaluate_research_conditions(ws_manager=ws_manager)
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.debug("Background research alert evaluator notice: %s", type(exc).__name__)

        alert_worker_task = asyncio.create_task(_research_alert_worker())

    try:
        yield
    finally:
        logger.info("Shutting down BTCognitive market monitor and alert worker...")
        if alert_worker_task is not None:
            alert_worker_task.cancel()
            try:
                await alert_worker_task
            except asyncio.CancelledError:
                pass
        live_engine.is_running = False
        if trade_feed is not None:
            try:
                stop_result = trade_feed.stop()
                if inspect.isawaitable(stop_result):
                    stop_result = await stop_result
                if stop_result is False:
                    snapshot = trade_feed.snapshot() if hasattr(trade_feed, "snapshot") else {}
                    feed_state = snapshot.get("feed_state", "UNKNOWN") if isinstance(snapshot, dict) else "UNKNOWN"
                    logger.warning(
                        "Bitstamp trade feed worker did not terminate before its shutdown timeout; state=%s.",
                        feed_state,
                    )
                elif stop_result is True:
                    logger.info("Bitstamp trade feed worker terminated.")
                else:
                    logger.warning("Bitstamp trade feed stop did not report worker termination status.")
            except Exception as exc:
                logger.warning("Bitstamp trade feed shutdown failed: %s", type(exc).__name__)
        await close_shared_client()
        logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# FastAPI App Initialization & Security Hardening
# ---------------------------------------------------------------------------

# Disable interactive docs in production environment
# BTC_ENVIRONMENT is canonical; ENVIRONMENT supported as legacy fallback
env_mode = (os.getenv("BTC_ENVIRONMENT") or os.getenv("ENVIRONMENT") or "development").strip().lower()
docs_url = "/docs" if env_mode != "production" else None
redoc_url = "/redoc" if env_mode != "production" else None
openapi_url = "/openapi.json" if env_mode != "production" else None

app = FastAPI(
    title="BTCognitive Engine API",
    description="Production-grade AI Bitcoin market intelligence REST & WebSocket server (OWASP ASVS 5.0 Hardened)",
    version="3.0.0",
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url
)

# 1. Global Exception Handler (Zero Information Leakage)
app.add_exception_handler(Exception, sanitized_exception_handler)
app.add_exception_handler(HTTPException, sanitized_exception_handler)
app.add_exception_handler(StarletteHTTPException, sanitized_exception_handler)

# 2. Security Headers Middleware (OWASP ASVS)
app.add_middleware(SecurityHeadersMiddleware)

# 3. Tier-based Rate Limiting & Body Size Middleware
app.add_middleware(RateLimitingMiddleware)

# 4. Trusted Host Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS
)

# 5. Strict CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Mount Modular APIRouters
# Unified market monitor is registered first so legacy fake fallbacks cannot shadow it.
app.include_router(market_monitor_router)
app.include_router(market_router)
app.include_router(prediction_router)
app.include_router(arena_router)
app.include_router(notifications_router)
app.include_router(genome_router)
app.include_router(analogs_router)
app.include_router(terminal_router)
app.include_router(research_router)
app.include_router(tournament_router)
app.include_router(user_positions_router)
app.include_router(manual_journal_router)


@app.get("/api/local-fixture/candles")
def local_fixture_candles(
    request: Request,
    symbol: str = Query("BTC-USD"),
    interval: str = Query("1m"),
    limit: int = Query(500, ge=1, le=500),
) -> dict:
    """Expose deterministic chart bars only after explicit fixture-mode opt-in."""
    from engine.data_mode import DataMode, get_data_mode, is_local_fixture_feed_enabled

    if symbol.upper().replace("-", "").replace("/", "") != "BTCUSD" or interval != "1m":
        return {
            "status": "UNSUPPORTED_REQUEST",
            "symbol": "BTC-USD",
            "interval": interval,
            "source": None,
            "count": 0,
            "candles": [],
            "reason": "The local fixture feed exposes only BTC-USD 1-minute test bars.",
        }
    feed = getattr(request.app.state, "local_fixture_feed", None)
    enabled = (
        getattr(request.app.state, "data_mode", None) == DataMode.FIXTURE.value
        and getattr(request.app.state, "local_fixture_feed_enabled", False) is True
        and get_data_mode() == DataMode.FIXTURE.value
        and is_local_fixture_feed_enabled(DataMode.FIXTURE)
    )
    if not enabled or not isinstance(feed, LocalFixtureCandleFeed):
        return {
            "status": "DATA_UNAVAILABLE",
            "freshness_status": "UNAVAILABLE",
            "symbol": "BTC-USD",
            "interval": "1m",
            "source": None,
            "test_only": False,
            "data_origin": "UNAVAILABLE",
            "count": 0,
            "candles": [],
            "analysis": {
                "status": "UNVALIDATED",
                "engine_invoked": False,
                "reason": "The opt-in local fixture feed is disabled.",
            },
            "reason": "Set BTC_LOCAL_FIXTURE_FEED=1 in fixture mode to expose local test bars.",
        }
    return feed.snapshot(limit=limit)



# ---------------------------------------------------------------------------
# Hardened WebSocket Endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_ip = websocket.client.host if websocket.client else "UNKNOWN"
    connected = await ws_manager.connect(websocket, client_ip)
    if not connected:
        return

    try:
        await websocket.send_text(json.dumps({
            "type": "CONNECTION_ESTABLISHED",
            "message": "Connected to BTCognitive Real-Time Intelligence Stream"
        }))
        while True:
            data = await websocket.receive_text()
            if len(data.encode("utf-8")) > MAX_WEBSOCKET_MESSAGE_BYTES:
                security_audit.alert_critical(
                    "WEB_SOCKET_MESSAGE_OVERSIZED",
                    client_ip,
                    "/ws",
                    {"size_bytes": len(data.encode("utf-8"))}
                )
                await websocket.close(code=status.WS_1009_MESSAGE_TOO_BIG)
                break

            is_ping = False
            trimmed = data.strip()
            if trimmed.lower() == "ping":
                is_ping = True
            else:
                try:
                    parsed_msg = json.loads(trimmed)
                    if isinstance(parsed_msg, dict) and str(parsed_msg.get("type", "")).lower() == "ping":
                        is_ping = True
                except Exception:
                    pass

            if is_ping:
                await websocket.send_text(json.dumps({
                    "type": "PONG",
                    "timestamp": int(time.time() * 1000)
                }))

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, client_ip)
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
        ws_manager.disconnect(websocket, client_ip)


# ---------------------------------------------------------------------------
# Static Files / Frontend Mount
# ---------------------------------------------------------------------------
web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
if os.path.isdir(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host=os.getenv("BTCOGNITIVE_HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")), reload=os.getenv("BTC_ENVIRONMENT", "development").lower() != "production")

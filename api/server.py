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
import logging
from contextlib import asynccontextmanager
from typing import List, Dict
from collections import defaultdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
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
from backtest.market_memory import sanitize_market_memory
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


# ---------------------------------------------------------------------------
# Application Lifespan Context Manager
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages initialization and graceful teardown of shared async resources."""
    logger.info("Initializing BTCognitive Server...")
    app.state.http = get_shared_client()
    feature_cache.initialize()

    try:
        sanitize_market_memory()
    except Exception as e:
        logger.warning(f"Error sanitizing market memory: {e}")

    live_engine.start()
    logger.info("BTCognitive Server is online and hardened.")
    yield

    logger.info("Shutting down BTCognitive Server...")
    live_engine.is_running = False
    await close_shared_client()
    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# FastAPI App Initialization & Security Hardening
# ---------------------------------------------------------------------------

# Disable docs in production environment if set
env_mode = os.getenv("BTC_ENVIRONMENT", "development").lower()
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
app.include_router(market_router)
app.include_router(prediction_router)
app.include_router(arena_router)
app.include_router(notifications_router)
app.include_router(genome_router)


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

            if data == "ping":
                await websocket.send_text(json.dumps({"type": "PONG"}))
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
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)

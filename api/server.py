"""
api/server.py — BTCognitive Production FastAPI Application Server
=================================================================
Central application server configuring FastAPI lifespan, async HTTP client,
WebSocket streaming manager, and modular APIRouters.
"""

import os
import sys
import json
import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.http_client import get_shared_client, close_shared_client
from engine.feature_cache import feature_cache
from engine.inference_service import live_engine
from engine.arena_runner import arena_runner
from backtest.market_memory import sanitize_market_memory

# Import modular route handlers
from api.routes_market import router as market_router
from api.routes_prediction import router as prediction_router
from api.routes_arena import router as arena_router
from api.routes_notifications import router as notifications_router
from api.genome_routes import router as genome_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("btcognitive.server")


# ---------------------------------------------------------------------------
# WebSocket Connection Manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)


ws_manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Application Lifespan Context Manager
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages initialization and graceful teardown of shared async resources.
    """
    logger.info("Initializing BTCognitive Server...")
    # 1. Initialize shared httpx AsyncClient
    app.state.http = get_shared_client()

    # 2. Initialize in-memory Feature Cache
    feature_cache.initialize()

    # 3. Sanitize SQLite Market Memory
    try:
        sanitize_market_memory()
    except Exception as e:
        logger.warning(f"Error sanitizing market memory: {e}")

    # 4. Start background AI inference engine
    live_engine.start()

    logger.info("BTCognitive Server is online and ready.")
    yield

    # Shutdown sequence
    logger.info("Shutting down BTCognitive Server...")
    live_engine.is_running = False
    await close_shared_client()
    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# FastAPI App Initialization
# ---------------------------------------------------------------------------

app = FastAPI(
    title="BTCognitive Engine API",
    description="Production-grade AI Bitcoin market intelligence REST & WebSocket server",
    version="2.1.0",
    lifespan=lifespan
)

# Enable CORS for frontend terminal
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Modular APIRouters
app.include_router(market_router)
app.include_router(prediction_router)
app.include_router(arena_router)
app.include_router(notifications_router)
app.include_router(genome_router)


# ---------------------------------------------------------------------------
# WebSocket Endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Initial greeting and connection confirmation
        await websocket.send_text(json.dumps({
            "type": "CONNECTION_ESTABLISHED",
            "message": "Connected to BTCognitive Real-Time Intelligence Stream"
        }))
        while True:
            data = await websocket.receive_text()
            # Echo heartbeat or client commands
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "PONG"}))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
        ws_manager.disconnect(websocket)


from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# Static Files / Frontend Terminal Mount
# ---------------------------------------------------------------------------
web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
if os.path.isdir(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)

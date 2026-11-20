"""
engine/coinbase_l2_collector.py — Opt-In Resilient Coinbase Exchange L2 Collector
=================================================================================
Implements an auditable, opt-in WebSocket collector ingesting real-time Coinbase
Exchange Level-2 (level2_batch) and matches trade feeds for BTC-USD.

Safety & Governance Invariants:
1. Disabled by Default: Requires deliberate operator action (COINBASE_L2_COLLECTOR_ENABLED=True).
   Never starts automatically during server startup or ordinary test runs.
2. BTC-USD Spot Only: Strictly rejects unauthorized instruments or derivatives.
3. Resilient Fault Detection: Detects sequence gaps, heartbeat stalls (>5.0s), and socket drops.
   Instantly marks book desynchronized and triggers a clean re-subscription snapshot.
4. Clean Graceful Shutdown: Thread-safe stop() method terminating background tasks cleanly.
5. Zero Fabrication: Data gaps or disconnections result in explicit FEATURE_UNAVAILABLE states;
   zero synthetic observations are produced.
"""

from __future__ import annotations

import os
import sys
import json
import time
import asyncio
import logging
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone

from engine.l2_microstructure_features import OrderBookTracker, L2MicrostructureSnapshot

logger = logging.getLogger("btcognitive.coinbase_l2")

DEFAULT_WS_URL = "wss://ws-feed.exchange.coinbase.com"
AUTHORIZED_PRODUCT = "BTC-USD"
MAX_HEARTBEAT_INTERVAL_SEC = 5.0


class CoinbaseL2Collector:
    """
    Opt-in, resilient Coinbase Exchange WebSocket client for Level-2 and trade match data.
    """

    def __init__(
        self,
        product_id: str = AUTHORIZED_PRODUCT,
        ws_url: str = DEFAULT_WS_URL,
        enabled: bool = False,
        tracker: Optional[OrderBookTracker] = None,
        max_reconnect_attempts: int = 5,
        event_recorder: Optional[Any] = None
    ):
        if product_id != AUTHORIZED_PRODUCT:
            raise ValueError(f"Unauthorized product '{product_id}'. Only '{AUTHORIZED_PRODUCT}' is permitted.")

        self.product_id = product_id
        self.ws_url = ws_url
        self.enabled = enabled
        self.tracker = tracker or OrderBookTracker()
        self.max_reconnect_attempts = max_reconnect_attempts
        self.event_recorder = event_recorder

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event: Optional[asyncio.Event] = None

        self.messages_processed_count = 0
        self.reconnect_count = 0
        self.last_error: Optional[str] = None

    def start(self) -> bool:
        """
        Starts the collector in a dedicated background daemon thread.
        Fails closed if enabled=False.
        """
        if not self.enabled:
            logger.warning("CoinbaseL2Collector is DISABLED by default. Explicit opt-in (enabled=True) required.")
            return False

        if self._running:
            logger.info("CoinbaseL2Collector is already running.")
            return True

        self._running = True
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True, name="CoinbaseL2CollectorThread")
        self._thread.start()
        logger.info(f"Started opt-in Coinbase L2 Collector for {self.product_id} at {self.ws_url}")
        return True

    def stop(self, timeout: float = 5.0):
        """Gracefully stops the collector and joins the background thread."""
        if not self._running:
            return

        logger.info("Stopping CoinbaseL2Collector...")
        self._running = False
        if self._loop and self._stop_event:
            self._loop.call_soon_threadsafe(self._stop_event.set)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self.tracker.reset(reason="COLLECTOR_STOPPED")
        logger.info("CoinbaseL2Collector stopped cleanly.")

    def is_healthy(self, now_epoch: Optional[float] = None) -> bool:
        """Verifies if the feed is synchronized and not stale."""
        epoch = now_epoch if now_epoch is not None else time.time()
        if not self._running or not self.tracker.is_synchronized:
            return False
        age = epoch - self.tracker.last_update_epoch
        return age <= MAX_HEARTBEAT_INTERVAL_SEC

    def get_microstructure_snapshot(
        self,
        decision_epoch: Optional[float] = None,
        window_seconds: float = 900.0
    ) -> L2MicrostructureSnapshot:
        """Returns the point-in-time microstructure snapshot from the tracker."""
        epoch = decision_epoch if decision_epoch is not None else time.time()
        return self.tracker.extract_microstructure_snapshot(
            decision_epoch=epoch,
            window_seconds=window_seconds,
            max_staleness_seconds=MAX_HEARTBEAT_INTERVAL_SEC
        )

    def _run_event_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._stop_event = asyncio.Event()
        try:
            self._loop.run_until_complete(self._connection_loop())
        finally:
            self._loop.close()

    async def _connection_loop(self):
        attempt = 0
        while self._running:
            try:
                import websockets
                logger.info(f"Connecting to Coinbase WS feed: {self.ws_url} (attempt {attempt + 1})...")
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    max_size=20 * 1024 * 1024
                ) as ws:
                    attempt = 0
                    subscribe_msg = {
                        "type": "subscribe",
                        "product_ids": [self.product_id],
                        "channels": ["level2_batch", "heartbeat", "matches"]
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    logger.info(f"Subscribed to level2_batch, heartbeat, matches for {self.product_id}.")

                    while self._running and not self._stop_event.is_set():
                        try:
                            msg_text = await asyncio.wait_for(ws.recv(), timeout=5.0)
                            received_epoch = time.time()
                            self._handle_raw_message(msg_text, received_epoch)
                        except asyncio.TimeoutError:
                            # Verify heartbeat liveness
                            if time.time() - self.tracker.last_heartbeat_epoch > MAX_HEARTBEAT_INTERVAL_SEC:
                                logger.warning("Coinbase heartbeat timeout (>5.0s); reconnecting...")
                                self.tracker.is_synchronized = False
                                self.tracker.desync_reason = "HEARTBEAT_TIMEOUT"
                                break

            except Exception as exc:
                self.last_error = str(exc)
                self.reconnect_count += 1
                self.tracker.is_synchronized = False
                self.tracker.desync_reason = f"SOCKET_ERROR: {exc}"
                attempt += 1
                logger.warning(f"Coinbase WS connection error ({exc}). Reconnecting in {min(10, 2**attempt)}s...")
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=min(10, 2**attempt))
                except asyncio.TimeoutError:
                    pass

    def _handle_raw_message(self, raw_text: str, received_epoch: float):
        """Parses and dispatches inbound Coinbase messages."""
        try:
            msg = json.loads(raw_text)
            self.messages_processed_count += 1
            msg_type = msg.get("type")

            if msg_type == "snapshot":
                if self.event_recorder is not None:
                    try:
                        self.event_recorder.record_event("snapshot", msg, epoch=received_epoch, sequence=msg.get("sequence"))
                    except Exception as rec_err:
                        logger.debug(f"Event recorder error on snapshot: {rec_err}")
                self.tracker.process_snapshot(msg, received_epoch)
            elif msg_type == "l2update":
                if self.event_recorder is not None:
                    try:
                        self.event_recorder.record_event("l2update", msg, epoch=received_epoch, sequence=msg.get("sequence"))
                    except Exception as rec_err:
                        logger.debug(f"Event recorder error on l2update: {rec_err}")
                self.tracker.process_l2update(msg, received_epoch)
            elif msg_type == "match":
                if self.event_recorder is not None:
                    try:
                        self.event_recorder.record_event("match", msg, epoch=received_epoch, sequence=msg.get("sequence"))
                    except Exception as rec_err:
                        logger.debug(f"Event recorder error on match: {rec_err}")
                self.tracker.process_match(msg, received_epoch)
            elif msg_type == "heartbeat":
                if self.event_recorder is not None:
                    try:
                        self.event_recorder.record_event("heartbeat", msg, epoch=received_epoch, sequence=msg.get("sequence"))
                    except Exception as rec_err:
                        logger.debug(f"Event recorder error on heartbeat: {rec_err}")
                self.tracker.process_heartbeat(msg, received_epoch)
            elif msg_type == "error":
                logger.error(f"Coinbase WS returned error message: {msg.get('message')}")
                self.tracker.is_synchronized = False
                self.tracker.desync_reason = f"EXCHANGE_ERROR: {msg.get('message')}"

        except Exception as exc:
            logger.debug(f"Error handling message: {exc}")

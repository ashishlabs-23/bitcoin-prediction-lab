"""
engine/market_data_feed.py — Reliable Market Data Ingestion & L2 Book Engine
=============================================================================
Implements Phase 4 Data-Quality Contracts:
1. Spot Market: Coinbase Exchange BTC-USD Trades and Level 2 Order Book with sequence tracking.
2. Continuity Verification: Detects sequence gaps, invalidates corrupted state, and triggers resynchronization.
3. Microstructure Metrics: Microprice, depth imbalance (levels 1, 5, 10), and Order Flow Imbalance (OFI).
4. Derivatives Isolation: Binance Futures Funding Rate and Open Interest isolated from spot pricing.
5. Strict Data-Quality Contract: Explicit provenance, event/receipt timestamps, freshness, and error states.
   Never fabricates substitute numbers on feed interruption.
"""

import asyncio
import json
import threading
import time
import math
import logging
import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger("btcognitive.market_data_feed")


class FreshnessStatus(str, Enum):
    FRESH = "FRESH"
    STALE = "STALE"
    DISCONTINUOUS = "DISCONTINUOUS"
    INVALID = "INVALID"
    UNINITIALIZED = "UNINITIALIZED"


class InstrumentFamily(str, Enum):
    SPOT = "SPOT"
    DERIVATIVE = "DERIVATIVE"


@dataclass
class MarketDataObservation:
    """
    Standardized observation satisfying the Phase 4 Data-Quality Contract.
    """
    source: str                          # e.g., "coinbase", "binance_futures", "kraken"
    instrument: str                      # e.g., "BTC-USD", "BTCUSDT"
    instrument_family: InstrumentFamily  # SPOT vs DERIVATIVE (never mixed)
    data_type: str                       # "L2_BOOK", "TRADE", "FUNDING_RATE", "OPEN_INTEREST"
    event_timestamp: str                 # Producer event timestamp ISO8601
    receipt_timestamp: str               # Local ingestion timestamp ISO8601
    payload: Dict[str, Any]              # Typed payload (prices, sizes, metrics)
    freshness_status: FreshnessStatus    # FRESH, STALE, DISCONTINUOUS, INVALID
    sequence_id: Optional[int] = None    # L2 update sequence tracking
    latency_ms: Optional[float] = None   # receipt_ts - event_ts
    error_state: Optional[str] = None    # Error detail if degraded


@dataclass
class L2BookMetrics:
    """Microstructure metrics derived from valid, gap-free L2 book state."""
    best_bid: float
    best_ask: float
    mid_price: float
    spread: float
    relative_spread_bps: float
    microprice: float
    depth_imbalance_top5: float
    depth_imbalance_top10: float
    total_bid_depth: float
    total_ask_depth: float
    sequence_id: int
    is_valid: bool


class CoinbaseL2OrderBook:
    """
    Level 2 Order Book maintainer for Coinbase Exchange BTC-USD.
    Tracks bids/asks sorted by price with sequence continuity checking.
    """

    def __init__(self, stale_timeout_sec: float = 15.0):
        self.stale_timeout_sec = stale_timeout_sec
        self.bids: Dict[float, float] = {}  # price -> size
        self.asks: Dict[float, float] = {}  # price -> size
        self.last_sequence: Optional[int] = None
        self.last_update_time: float = 0.0
        self.is_initialized: bool = False
        self.previous_best_bid: Optional[Tuple[float, float]] = None  # (price, size)
        self.previous_best_ask: Optional[Tuple[float, float]] = None

    def initialize_snapshot(
        self,
        bids: List[List[Any]],
        asks: List[List[Any]],
        sequence_id: int,
        event_time_iso: Optional[str] = None
    ) -> MarketDataObservation:
        """Initializes the book from a full REST/WS snapshot."""
        receipt_time = datetime.now(timezone.utc)
        self.bids.clear()
        self.asks.clear()

        for b in bids:
            price, size = float(b[0]), float(b[1])
            if size > 0:
                self.bids[price] = size

        for a in asks:
            price, size = float(a[0]), float(a[1])
            if size > 0:
                self.asks[price] = size

        self.last_sequence = sequence_id
        self.last_update_time = time.time()
        self.is_initialized = True
        self.previous_best_bid = self.get_best_bid()
        self.previous_best_ask = self.get_best_ask()

        metrics = self.compute_metrics()
        return MarketDataObservation(
            source="coinbase",
            instrument="BTC-USD",
            instrument_family=InstrumentFamily.SPOT,
            data_type="L2_BOOK_SNAPSHOT",
            event_timestamp=event_time_iso or receipt_time.isoformat(),
            receipt_timestamp=receipt_time.isoformat(),
            payload=metrics.__dict__ if metrics else {},
            freshness_status=FreshnessStatus.FRESH if metrics else FreshnessStatus.INVALID,
            sequence_id=sequence_id,
            error_state=None
        )

    def apply_delta(
        self,
        side: str,
        price: float,
        size: float,
        sequence_id: int,
        event_time_iso: Optional[str] = None
    ) -> MarketDataObservation:
        """
        Applies an incremental L2 update with strict sequence continuity checking.
        If a gap is detected, invalidates book and flags DISCONTINUOUS.
        """
        receipt_time = datetime.now(timezone.utc)

        if not self.is_initialized:
            return MarketDataObservation(
                source="coinbase",
                instrument="BTC-USD",
                instrument_family=InstrumentFamily.SPOT,
                data_type="L2_DELTA",
                event_timestamp=event_time_iso or receipt_time.isoformat(),
                receipt_timestamp=receipt_time.isoformat(),
                payload={},
                freshness_status=FreshnessStatus.UNINITIALIZED,
                sequence_id=sequence_id,
                error_state="Cannot apply delta to uninitialized book. Snapshot required."
            )

        # Sequence continuity check
        if self.last_sequence is not None and sequence_id > (self.last_sequence + 1):
            gap = sequence_id - self.last_sequence
            logger.warning(f"L2 sequence gap detected! Expected {self.last_sequence + 1}, got {sequence_id} (gap={gap}). Invalidating book.")
            self.invalidate()
            return MarketDataObservation(
                source="coinbase",
                instrument="BTC-USD",
                instrument_family=InstrumentFamily.SPOT,
                data_type="L2_DELTA",
                event_timestamp=event_time_iso or receipt_time.isoformat(),
                receipt_timestamp=receipt_time.isoformat(),
                payload={},
                freshness_status=FreshnessStatus.DISCONTINUOUS,
                sequence_id=sequence_id,
                error_state=f"Sequence continuity gap ({gap} updates lost). Book invalidated."
            )

        # Apply update
        target_side = self.bids if side.lower() == "buy" else self.asks
        if size == 0:
            target_side.pop(price, None)
        else:
            target_side[price] = size

        self.last_sequence = sequence_id
        self.last_update_time = time.time()

        metrics = self.compute_metrics()
        return MarketDataObservation(
            source="coinbase",
            instrument="BTC-USD",
            instrument_family=InstrumentFamily.SPOT,
            data_type="L2_DELTA",
            event_timestamp=event_time_iso or receipt_time.isoformat(),
            receipt_timestamp=receipt_time.isoformat(),
            payload=metrics.__dict__ if metrics else {},
            freshness_status=FreshnessStatus.FRESH if metrics else FreshnessStatus.INVALID,
            sequence_id=sequence_id,
            error_state=None
        )

    def get_best_bid(self) -> Optional[Tuple[float, float]]:
        if not self.bids:
            return None
        best_p = max(self.bids.keys())
        return (best_p, self.bids[best_p])

    def get_best_ask(self) -> Optional[Tuple[float, float]]:
        if not self.asks:
            return None
        best_p = min(self.asks.keys())
        return (best_p, self.asks[best_p])

    def compute_metrics(self) -> Optional[L2BookMetrics]:
        """Computes spread, microprice, and depth imbalances."""
        if not self.is_initialized or not self.bids or not self.asks:
            return None

        best_b = self.get_best_bid()
        best_a = self.get_best_ask()
        if not best_b or not best_a:
            return None

        bid_p, bid_s = best_b
        ask_p, ask_s = best_a

        if bid_p >= ask_p:
            # Crossed or locked book anomaly
            return None

        spread = ask_p - bid_p
        mid = (bid_p + ask_p) / 2.0
        rel_spread_bps = (spread / mid) * 10000.0

        # Microprice: volume-weighted mid price
        total_top_vol = bid_s + ask_s
        microprice = ((bid_s * ask_p) + (ask_s * bid_p)) / total_top_vol if total_top_vol > 0 else mid

        # Top 5 and Top 10 depth imbalance: (sum_bids - sum_asks) / (sum_bids + sum_asks)
        sorted_bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)
        sorted_asks = sorted(self.asks.items(), key=lambda x: x[0])

        top5_bids = sum(x[1] for x in sorted_bids[:5])
        top5_asks = sum(x[1] for x in sorted_asks[:5])
        top5_denom = top5_bids + top5_asks
        imb5 = (top5_bids - top5_asks) / top5_denom if top5_denom > 0 else 0.0

        top10_bids = sum(x[1] for x in sorted_bids[:10])
        top10_asks = sum(x[1] for x in sorted_asks[:10])
        top10_denom = top10_bids + top10_asks
        imb10 = (top10_bids - top10_asks) / top10_denom if top10_denom > 0 else 0.0

        return L2BookMetrics(
            best_bid=bid_p,
            best_ask=ask_p,
            mid_price=round(mid, 2),
            spread=round(spread, 2),
            relative_spread_bps=round(rel_spread_bps, 4),
            microprice=round(microprice, 2),
            depth_imbalance_top5=round(imb5, 4),
            depth_imbalance_top10=round(imb10, 4),
            total_bid_depth=round(sum(self.bids.values()), 4),
            total_ask_depth=round(sum(self.asks.values()), 4),
            sequence_id=self.last_sequence or 0,
            is_valid=True
        )

    def compute_ofi(self) -> float:
        """
        Computes Order Flow Imbalance (OFI) at the touch:
        OFI = I_{bid >= prev_bid} * s_bid - I_{bid <= prev_bid} * prev_s_bid
            - I_{ask <= prev_ask} * s_ask + I_{ask >= prev_ask} * prev_s_ask
        """
        curr_bid = self.get_best_bid()
        curr_ask = self.get_best_ask()
        if not curr_bid or not curr_ask or not self.previous_best_bid or not self.previous_best_ask:
            return 0.0

        b_p, b_s = curr_bid
        pb_p, pb_s = self.previous_best_bid
        a_p, a_s = curr_ask
        pa_p, pa_s = self.previous_best_ask

        # Bid component
        if b_p > pb_p:
            delta_bid = b_s
        elif b_p == pb_p:
            delta_bid = b_s - pb_s
        else:
            delta_bid = -pb_s

        # Ask component
        if a_p < pa_p:
            delta_ask = a_s
        elif a_p == pa_p:
            delta_ask = a_s - pa_s
        else:
            delta_ask = -pa_s

        ofi = delta_bid - delta_ask

        # Update previous
        self.previous_best_bid = curr_bid
        self.previous_best_ask = curr_ask
        return ofi

    def invalidate(self):
        """Invalidates book state on disconnect or sequence gap."""
        self.bids.clear()
        self.asks.clear()
        self.is_initialized = False
        self.last_sequence = None
        self.previous_best_bid = None
        self.previous_best_ask = None

    def check_freshness(self) -> FreshnessStatus:
        """Evaluates whether book data is fresh or stale."""
        if not self.is_initialized:
            return FreshnessStatus.UNINITIALIZED
        age = time.time() - self.last_update_time
        if age > self.stale_timeout_sec:
            return FreshnessStatus.STALE
        return FreshnessStatus.FRESH


class BinanceDerivativesCollector:
    """
    Ingests public funding rate and open interest from Binance Futures.
    Strictly isolated from spot market pricing under InstrumentFamily.DERIVATIVE.
    """

    @staticmethod
    def process_funding_rate(raw_payload: Dict[str, Any]) -> MarketDataObservation:
        """
        Processes Binance funding rate observation.
        Never fabricates fallback if payload is malformed.
        """
        receipt_time = datetime.now(timezone.utc)
        try:
            rate = float(raw_payload["lastFundingRate"])
            event_ts_ms = int(raw_payload.get("time", int(time.time() * 1000)))
            event_dt = datetime.fromtimestamp(event_ts_ms / 1000.0, timezone.utc)

            # Annualized basis = funding_rate * 3 * 365
            annualized_basis_pct = rate * 3.0 * 365.0 * 100.0

            return MarketDataObservation(
                source="binance_futures",
                instrument="BTCUSDT",
                instrument_family=InstrumentFamily.DERIVATIVE,
                data_type="FUNDING_RATE",
                event_timestamp=event_dt.isoformat(),
                receipt_timestamp=receipt_time.isoformat(),
                payload={
                    "funding_rate": rate,
                    "funding_rate_bps": round(rate * 10000.0, 4),
                    "annualized_basis_pct": round(annualized_basis_pct, 4),
                    "mark_price": float(raw_payload.get("markPrice", 0.0)),
                    "index_price": float(raw_payload.get("indexPrice", 0.0))
                },
                freshness_status=FreshnessStatus.FRESH,
                error_state=None
            )
        except Exception as e:
            return MarketDataObservation(
                source="binance_futures",
                instrument="BTCUSDT",
                instrument_family=InstrumentFamily.DERIVATIVE,
                data_type="FUNDING_RATE",
                event_timestamp=receipt_time.isoformat(),
                receipt_timestamp=receipt_time.isoformat(),
                payload={},
                freshness_status=FreshnessStatus.INVALID,
                error_state=f"Malformed funding rate payload: {e}"
            )

    @staticmethod
    def process_open_interest(raw_payload: Dict[str, Any], previous_oi: Optional[float] = None) -> MarketDataObservation:
        """
        Processes Binance open interest observation.
        Tracks open interest and open interest delta (contracts & USD).
        """
        receipt_time = datetime.now(timezone.utc)
        try:
            oi_contracts = float(raw_payload["openInterest"])
            event_ts_ms = int(raw_payload.get("time", int(time.time() * 1000)))
            event_dt = datetime.fromtimestamp(event_ts_ms / 1000.0, timezone.utc)

            delta_contracts = (oi_contracts - previous_oi) if previous_oi is not None else 0.0

            return MarketDataObservation(
                source="binance_futures",
                instrument="BTCUSDT",
                instrument_family=InstrumentFamily.DERIVATIVE,
                data_type="OPEN_INTEREST",
                event_timestamp=event_dt.isoformat(),
                receipt_timestamp=receipt_time.isoformat(),
                payload={
                    "open_interest_contracts": oi_contracts,
                    "open_interest_delta": round(delta_contracts, 2),
                    "has_delta": previous_oi is not None
                },
                freshness_status=FreshnessStatus.FRESH,
                error_state=None
            )
        except Exception as e:
            return MarketDataObservation(
                source="binance_futures",
                instrument="BTCUSDT",
                instrument_family=InstrumentFamily.DERIVATIVE,
                data_type="OPEN_INTEREST",
                event_timestamp=receipt_time.isoformat(),
                receipt_timestamp=receipt_time.isoformat(),
                payload={},
                freshness_status=FreshnessStatus.INVALID,
                error_state=f"Malformed open interest payload: {e}"
            )


class BitstampTradeFeed:
    """Opt-in, in-memory Bitstamp BTC/USD trade collector.

    ``start`` runs the WebSocket lifecycle in a background thread; ``stop``
    signals the asyncio loop and joins that thread. Reconnect delays use a
    capped exponential backoff. Trade event times are taken from Bitstamp's
    ``microtimestamp`` without adjustment. Accepted trades are converted to
    event-time 1-minute candles through CandleStateManager's ingestion-only
    path, which never invokes inference or emits BTCUSDT ticks.
    """

    DEFAULT_WS_URL = "wss://ws.bitstamp.net"
    CHANNEL = "live_trades_btcusd"
    STALE_AFTER_SECONDS = 60.0
    MAX_RECONNECT_DELAY_SECONDS = 30.0
    _worker_guard = threading.Lock()
    _active_worker_owner: Optional["BitstampTradeFeed"] = None

    def __init__(
        self,
        ws_url: str = DEFAULT_WS_URL,
        candle_manager: Optional[Any] = None,
        stale_after_seconds: float = STALE_AFTER_SECONDS,
        max_reconnect_delay_seconds: float = MAX_RECONNECT_DELAY_SECONDS,
        connect_timeout_seconds: float = 10.0,
    ):
        if stale_after_seconds <= 0 or max_reconnect_delay_seconds <= 0 or connect_timeout_seconds <= 0:
            raise ValueError("Feed timeouts and reconnect delay must be positive")

        if candle_manager is None:
            from api.candle_manager import CandleStateManager
            candle_manager = CandleStateManager(interval_seconds=60)

        self.ws_url = ws_url
        self.candle_manager = candle_manager
        self.stale_after_seconds = float(stale_after_seconds)
        self.max_reconnect_delay_seconds = float(max_reconnect_delay_seconds)
        self.connect_timeout_seconds = float(connect_timeout_seconds)

        self._lock = threading.RLock()
        self._started = False
        self._stop_requested = False
        self._connected = False
        self._ever_connected = False
        self._connection_attempted = False
        self._feed_state = "DATA_UNAVAILABLE"
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event: Optional[asyncio.Event] = None

        self._observations = deque(maxlen=1_000)
        self._seen_trade_ids = set()
        self._trade_id_order = deque()
        self._observed_minutes = set()
        self._last_observation: Optional[MarketDataObservation] = None
        self._gap_count = 0
        self._duplicate_count = 0
        self._invalid_count = 0
        self._reconnect_count = 0
        self._last_error: Optional[str] = None

    def start(self) -> bool:
        """Start the collector only when the authoritative network policy allows it."""
        try:
            from engine.data_mode import is_external_network_permitted

            if not is_external_network_permitted():
                self.mark_network_blocked(
                    "External Bitstamp market-data access is denied by the authoritative data-mode policy."
                )
                return False
        except Exception as exc:
            self.mark_network_blocked(
                f"External Bitstamp market-data access is blocked by policy error: {type(exc).__name__}."
            )
            return False

        with BitstampTradeFeed._worker_guard:
            active_owner = BitstampTradeFeed._active_worker_owner
            if (
                active_owner is not None
                and active_owner is not self
                and active_owner._thread is not None
                and active_owner._thread.is_alive()
            ):
                with self._lock:
                    self._feed_state = "DUPLICATE_WORKER_BLOCKED"
                    self._last_error = (
                        "Another Bitstamp trade-feed worker is already running in this application."
                    )
                return False

            if active_owner is not None and active_owner is not self:
                BitstampTradeFeed._active_worker_owner = None

            with self._lock:
                if self._thread is not None and self._thread.is_alive():
                    return True
                self._stop_requested = False
                self._started = True
                self._feed_state = "CONNECTING"
                self._last_error = None
                self._thread = threading.Thread(
                    target=self._run_event_loop,
                    daemon=True,
                    name="BitstampTradeFeed",
                )
                BitstampTradeFeed._active_worker_owner = self
                try:
                    self._thread.start()
                except Exception as exc:
                    BitstampTradeFeed._active_worker_owner = None
                    self._thread = None
                    self._started = False
                    self._feed_state = "DATA_UNAVAILABLE"
                    self._last_error = f"Bitstamp worker failed to start: {type(exc).__name__}."
                    return False
                return True

    def mark_network_blocked(self, reason: str) -> None:
        """Record a policy block and signal any existing worker to stop."""
        with self._lock:
            self._stop_requested = True
            self._started = False
            if self._loop is not None and self._stop_event is not None and not self._loop.is_closed():
                self._loop.call_soon_threadsafe(self._stop_event.set)
            self._feed_state = "NETWORK_BLOCKED"
            self._last_error = reason

    def stop(self, timeout: float = 5.0) -> bool:
        """Stop the worker and return whether its thread terminated before timeout."""
        with self._lock:
            self._stop_requested = True
            self._started = False
            loop = self._loop
            stop_event = self._stop_event
            thread = self._thread
            if loop is not None and stop_event is not None and not loop.is_closed():
                loop.call_soon_threadsafe(stop_event.set)

        if thread is not None and thread.is_alive():
            thread.join(timeout=max(0.0, timeout))

        with self._lock:
            terminated = thread is None or not thread.is_alive()
            if terminated:
                self._connected = False
                if self._feed_state not in ("NETWORK_BLOCKED", "DUPLICATE_WORKER_BLOCKED"):
                    if self._ever_connected or self._connection_attempted:
                        self._feed_state = "DISCONNECTED"
                    else:
                        self._feed_state = "DATA_UNAVAILABLE"
            else:
                previous_error = self._last_error
                self._feed_state = "SHUTDOWN_TIMEOUT"
                timeout_error = (
                    f"Bitstamp trade-feed worker did not terminate within {max(0.0, timeout):.3f} seconds."
                )
                self._last_error = (
                    f"{timeout_error} Previous status: {previous_error}"
                    if previous_error
                    else timeout_error
                )
            return terminated

    def snapshot(self, limit: int = 500) -> Dict[str, Any]:
        """Return point-in-time feed health and recent in-memory candles."""
        count = max(0, int(limit))
        now = datetime.now(timezone.utc)
        with self._lock:
            observation = self._last_observation
            age_seconds = None
            status = "DATA_UNAVAILABLE"
            if self._feed_state in ("NETWORK_BLOCKED", "DUPLICATE_WORKER_BLOCKED", "SHUTDOWN_TIMEOUT"):
                status = "DATA_UNAVAILABLE"
            elif observation is not None:
                event_dt = datetime.fromisoformat(observation.event_timestamp.replace("Z", "+00:00"))
                age_seconds = (now - event_dt).total_seconds()
                if self._connected:
                    status = (
                        "STALE"
                        if age_seconds > self.stale_after_seconds or age_seconds < -5.0
                        else "ACTIVE"
                    )
                elif self._ever_connected or self._feed_state in ("RECONNECTING", "DISCONNECTED"):
                    status = "DISCONNECTED"
            elif self._ever_connected or self._feed_state in ("RECONNECTING", "DISCONNECTED"):
                status = "DISCONNECTED"

            candles = self.candle_manager.get_ingestion_candles(count)
            completed = [candle for candle in candles if candle["is_closed"]]
            provisional = [candle for candle in candles if not candle["is_closed"]]
            delay_seconds = (
                observation.latency_ms / 1000.0
                if observation is not None and observation.latency_ms is not None
                else None
            )
            return {
                "status": status,
                "feed_state": self._feed_state,
                "symbol": "BTC/USD",
                "exchange": "Bitstamp",
                "market_type": "SPOT",
                "interval": "1m",
                "source": "bitstamp",
                "last_event_timestamp": observation.event_timestamp if observation else None,
                "last_receive_timestamp": observation.receipt_timestamp if observation else None,
                "last_receipt_timestamp": observation.receipt_timestamp if observation else None,
                "latest_completed_candle_timestamp": completed[-1]["time"] if completed else None,
                "latest_provisional_candle_timestamp": provisional[-1]["time"] if provisional else None,
                "event_to_receive_delay_seconds": delay_seconds,
                "gap_count": self._gap_count,
                "duplicate_count": self._duplicate_count,
                "invalid_count": self._invalid_count,
                "reconnect_count": self._reconnect_count,
                "last_error": self._last_error,
                "reason": self._last_error,
                "candles": candles,
            }

    @staticmethod
    def _utc_isoformat(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")

    def _handle_raw_message(
        self,
        raw_message: Any,
        received_at: Optional[datetime] = None,
    ) -> Optional[MarketDataObservation]:
        """Validate one Bitstamp message and ingest a trade, if applicable."""
        try:
            message = json.loads(raw_message)
            if not isinstance(message, dict) or message.get("event") != "trade":
                return None
            data = message.get("data")
            if not isinstance(data, dict) or message.get("channel") != self.CHANNEL:
                raise ValueError("Unexpected Bitstamp trade channel or payload")

            raw_trade_id = data["id"]
            if isinstance(raw_trade_id, bool) or not (
                isinstance(raw_trade_id, int)
                or isinstance(raw_trade_id, str)
                and re.fullmatch(r"\d+", raw_trade_id)
            ):
                raise ValueError("Trade ID must be an unsigned integer")
            trade_id = int(raw_trade_id)
            if trade_id < 0:
                raise ValueError("Trade ID must be non-negative")
            with self._lock:
                if trade_id in self._seen_trade_ids:
                    self._duplicate_count += 1
                    return None

            microtimestamp = int(data["microtimestamp"])
            timestamp_seconds = int(data["timestamp"])
            if microtimestamp < 0 or timestamp_seconds != microtimestamp // 1_000_000:
                raise ValueError("Bitstamp timestamp and microtimestamp are inconsistent")
            event_dt = datetime.fromtimestamp(microtimestamp // 1_000_000, timezone.utc)
            event_dt += timedelta(microseconds=microtimestamp % 1_000_000)
            price = float(data["price"])
            quantity = float(data["amount"])
            if not math.isfinite(price) or price <= 0:
                raise ValueError("Trade price must be finite and positive")
            if not math.isfinite(quantity) or quantity <= 0:
                raise ValueError("Trade amount must be finite and positive")

            receipt_dt = received_at or datetime.now(timezone.utc)
            if receipt_dt.tzinfo is None:
                receipt_dt = receipt_dt.replace(tzinfo=timezone.utc)
            receipt_dt = receipt_dt.astimezone(timezone.utc)
            latency_ms = (receipt_dt - event_dt).total_seconds() * 1000.0
            freshness = (
                FreshnessStatus.STALE
                if (
                    (receipt_dt - event_dt).total_seconds() > self.stale_after_seconds
                    or (receipt_dt - event_dt).total_seconds() < -5.0
                )
                else FreshnessStatus.FRESH
            )
            observation = MarketDataObservation(
                source="bitstamp",
                instrument="BTC/USD",
                instrument_family=InstrumentFamily.SPOT,
                data_type="TRADE",
                event_timestamp=self._utc_isoformat(event_dt),
                receipt_timestamp=self._utc_isoformat(receipt_dt),
                payload={
                    "trade_id": trade_id,
                    "price": price,
                    "quantity": quantity,
                    "side_code": data["type"],
                    "source_message_id": f"{self.CHANNEL}:{trade_id}",
                    "schema_version": "bitstamp.trade.v1",
                    "timestamp": data["timestamp"],
                    "microtimestamp": data["microtimestamp"],
                },
                freshness_status=freshness,
                sequence_id=trade_id,
                latency_ms=latency_ms,
            )
        except (KeyError, TypeError, ValueError, OverflowError, OSError, json.JSONDecodeError) as exc:
            with self._lock:
                self._invalid_count += 1
                self._last_error = f"Invalid Bitstamp trade message: {exc}"
            return None

        event_ms = int(event_dt.timestamp() * 1000)
        with self._lock:
            if trade_id in self._seen_trade_ids:
                self._duplicate_count += 1
                return None
            self._seen_trade_ids.add(trade_id)
            self._trade_id_order.append(trade_id)
            if len(self._trade_id_order) > 100_000:
                expired_id = self._trade_id_order.popleft()
                self._seen_trade_ids.discard(expired_id)
            self._observations.append(observation)
            self._last_observation = observation
            minute_ms = (event_ms // 60_000) * 60_000
            self._observed_minutes.add(minute_ms)
            if len(self._observed_minutes) > 2_000:
                self._observed_minutes = set(sorted(self._observed_minutes)[-2_000:])
            ordered_minutes = sorted(self._observed_minutes)
            self._gap_count = sum(
                max(0, (right - left) // 60_000 - 1)
                for left, right in zip(ordered_minutes, ordered_minutes[1:])
            )
            try:
                self.candle_manager.process_trade_ingestion_only(
                    price=price,
                    quantity=quantity,
                    timestamp_ms=event_ms,
                    trade_id=trade_id,
                    event_timestamp=observation.event_timestamp,
                    received_timestamp=observation.receipt_timestamp,
                )
            except Exception as exc:
                self._last_error = f"Candle ingestion failed: {exc}"
                logger.exception("Bitstamp trade candle ingestion failed")
            return observation

    def _run_event_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        stop_event = asyncio.Event()
        with self._lock:
            self._loop = loop
            self._stop_event = stop_event
            if self._stop_requested:
                stop_event.set()
        try:
            loop.run_until_complete(self._connection_loop())
        finally:
            with self._lock:
                self._connected = False
                self._loop = None
                self._stop_event = None
                if self._feed_state != "NETWORK_BLOCKED":
                    if self._ever_connected or self._connection_attempted:
                        self._feed_state = "DISCONNECTED"
                    else:
                        self._feed_state = "DATA_UNAVAILABLE"
            loop.close()
            with BitstampTradeFeed._worker_guard:
                if BitstampTradeFeed._active_worker_owner is self:
                    BitstampTradeFeed._active_worker_owner = None

    async def _connection_loop(self) -> None:
        attempt = 0
        while not self._stop_requested:
            with self._lock:
                self._connection_attempted = True
                self._feed_state = "CONNECTING"
            try:
                import websockets

                async with websockets.connect(
                    self.ws_url,
                    open_timeout=self.connect_timeout_seconds,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=1_000_000,
                ) as websocket:
                    with self._lock:
                        self._connected = True
                        self._ever_connected = True
                        self._feed_state = "CONNECTED"
                        self._last_error = None
                    await websocket.send(json.dumps({
                        "event": "bts:subscribe",
                        "data": {"channel": self.CHANNEL},
                    }))
                    while not self._stop_requested:
                        try:
                            raw_message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        except asyncio.TimeoutError:
                            continue
                        self._handle_raw_message(raw_message, datetime.now(timezone.utc))
                    break
            except Exception as exc:
                if self._stop_requested:
                    break
                with self._lock:
                    self._connected = False
                    self._feed_state = "RECONNECTING"
                    self._reconnect_count += 1
                    self._last_error = f"{type(exc).__name__}: {exc}"
                delay = min(
                    self.max_reconnect_delay_seconds,
                    float(2 ** min(attempt, 30)),
                )
                attempt += 1
                stop_event = self._stop_event
                if stop_event is None:
                    break
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    pass
            finally:
                with self._lock:
                    self._connected = False

        with self._lock:
            if self._ever_connected or self._connection_attempted:
                self._feed_state = "DISCONNECTED"
            else:
                self._feed_state = "DATA_UNAVAILABLE"

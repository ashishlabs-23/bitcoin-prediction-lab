"""
Candle State Manager for BTCognitive API Server.

Tracks forming vs closed candle states from streaming market ticks.
Guarantees that AI predictions are ONLY generated on closed candles.
"""

import os
import sys
import time
import math
import pandas as pd
import numpy as np
from collections import deque
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backtest.market_memory import record_prediction
from models.explainability import compute_shap_explanations


class CandleStateManager:
    """
    Stateful Candle Manager that processes real-time price ticks and triggers
    feature extraction and AI predictions ONLY on closed candles.
    """

    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self.current_candle: Optional[Dict[str, Any]] = None
        self.closed_candles: List[Dict[str, Any]] = []
        self.ingestion_candles: Dict[int, Dict[str, Any]] = {}
        self._ingestion_candle_first_order: Dict[int, Tuple[int, int]] = {}
        self._ingestion_candle_last_order: Dict[int, Tuple[int, int]] = {}
        self._ingestion_candle_quantities: Dict[int, Dict[int, float]] = {}
        self._ingestion_trade_ids: Dict[int, int] = {}
        self._ingestion_trade_id_order = deque()
        self.last_prediction: Optional[Dict[str, Any]] = None
        self.last_tick_time: Optional[float] = None
        self.model_ensemble = None

    def set_ensemble_model(self, ensemble):
        """Sets the active AI model ensemble for inference on candle close."""
        self.model_ensemble = ensemble

    def process_trade_ingestion_only(
        self,
        price: float,
        quantity: float,
        timestamp_ms: int,
        trade_id: int,
        event_timestamp: Optional[str] = None,
        received_timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add one trade to its event-time candle without closing or inferring.

        Candles are keyed by the event-time interval. Late trades update their
        original candle, and open/close are selected by (event time, trade ID)
        so arrival order cannot change the result. This path is intentionally
        separate from ``process_tick``, which may trigger model inference.
        """
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if not np.isfinite(price) or price <= 0:
            raise ValueError("price must be finite and positive")
        if not np.isfinite(quantity) or quantity <= 0:
            raise ValueError("quantity must be finite and positive")

        event_ms = int(timestamp_ms)
        trade_key = int(trade_id)
        if trade_key in self._ingestion_trade_ids:
            candle_start = self._ingestion_trade_ids[trade_key]
            return dict(self.ingestion_candles.get(candle_start, {}))

        interval_ms = self.interval_seconds * 1000
        candle_start = (event_ms // interval_ms) * interval_ms
        self._ingestion_trade_ids[trade_key] = candle_start
        order_key = (event_ms, trade_key)
        candle = self.ingestion_candles.get(candle_start)
        if candle is None:
            candle = {
                "time": candle_start,
                "open": float(price),
                "high": float(price),
                "low": float(price),
                "close": float(price),
                "volume": float(quantity),
                "is_closed": False,
                "quality_status": "VALID",
                "source": "bitstamp",
                "symbol": "BTC/USD",
                "event_timestamp": event_timestamp,
                "received_timestamp": received_timestamp,
            }
            self.ingestion_candles[candle_start] = candle
            self._ingestion_candle_first_order[candle_start] = order_key
            self._ingestion_candle_last_order[candle_start] = order_key
        else:
            candle["high"] = max(candle["high"], float(price))
            candle["low"] = min(candle["low"], float(price))
            if order_key < self._ingestion_candle_first_order[candle_start]:
                candle["open"] = float(price)
                self._ingestion_candle_first_order[candle_start] = order_key
                candle["event_timestamp"] = event_timestamp
                candle["received_timestamp"] = received_timestamp
            if order_key > self._ingestion_candle_last_order[candle_start]:
                candle["close"] = float(price)
                self._ingestion_candle_last_order[candle_start] = order_key
                candle["event_timestamp"] = event_timestamp
                candle["received_timestamp"] = received_timestamp

        quantities = self._ingestion_candle_quantities.setdefault(candle_start, {})
        quantities[trade_key] = float(quantity)
        candle["volume"] = math.fsum(quantities[key] for key in sorted(quantities))
        self._ingestion_trade_id_order.append(trade_key)
        if len(self._ingestion_trade_id_order) > 100_000:
            expired_id = self._ingestion_trade_id_order.popleft()
            self._ingestion_trade_ids.pop(expired_id, None)
        candle["is_closed"] = (
            candle_start + interval_ms <= int(time.time() * 1000)
        )
        self._prune_ingestion_candles()
        return dict(candle)

    def _prune_ingestion_candles(self) -> None:
        """Bound in-memory stream state while retaining recent candle history."""
        expired = sorted(self.ingestion_candles)[:-1_000]
        if not expired:
            return
        expired_set = set(expired)
        for key in expired:
            self.ingestion_candles.pop(key, None)
            self._ingestion_candle_first_order.pop(key, None)
            self._ingestion_candle_last_order.pop(key, None)
            self._ingestion_candle_quantities.pop(key, None)
        for trade_id, candle_start in list(self._ingestion_trade_ids.items()):
            if candle_start in expired_set:
                self._ingestion_trade_ids.pop(trade_id, None)
        self._ingestion_trade_id_order = deque(
            trade_id for trade_id in self._ingestion_trade_id_order
            if trade_id in self._ingestion_trade_ids
        )

    def get_ingestion_candles(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Return the most recent ingestion-only candles in event-time order."""
        count = max(0, int(limit))
        ordered = sorted(self.ingestion_candles)
        if not count:
            return []
        now_ms = int(time.time() * 1000)
        return [
            {
                **self.ingestion_candles[key],
                "time": key // 1000,
                "is_closed": key + self.interval_seconds * 1000 <= now_ms,
                "quality_status": self.ingestion_candles[key].get("quality_status", "VALID"),
            }
            for key in ordered[-count:]
        ]

    def seed_historical_candles(self, klines: List[Dict[str, Any]]):
        """Seeds state with recent historical OHLCV klines without duplicating seed candles."""
        if not klines:
            return

        seen_times = set()
        deduped = []
        for k in klines[-500:]:
            candle_time = k.get("time") or k.get("timestamp")
            if candle_time is not None:
                if candle_time in seen_times:
                    continue
                seen_times.add(candle_time)
            deduped.append(dict(k, is_closed=True))

        self.closed_candles = deduped
        if deduped:
            last_k = klines[-1]
            if not last_k.get("is_closed", True):
                self.closed_candles.pop()
                self.current_candle = {
                    "time": last_k["time"],
                    "open": last_k["open"],
                    "high": last_k["high"],
                    "low": last_k["low"],
                    "close": last_k["close"],
                    "volume": last_k.get("volume", 0.0),
                    "is_closed": False
                }
            else:
                self.current_candle = None

    def process_tick(self, price: float, volume: float = 0.0, timestamp_ms: Optional[int] = None) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """
        Processes an incoming price tick.
        Returns tuple: (tick_update_event, prediction_event_if_candle_closed)
        """
        interval_ms = self.interval_seconds * 1000
        now_ms = timestamp_ms if timestamp_ms else int(time.time() * 1000)

        # Handle out-of-order ticks: do not alter current candle if tick timestamp precedes current interval
        if self.current_candle is not None and now_ms < self.current_candle["time"]:
            return {
                "type": "tick_ignored",
                "reason": "OUT_OF_ORDER_TICK",
                "price": price,
                "timestamp_ms": now_ms
            }, None

        self.last_tick_time = now_ms / 1000.0

        if self.current_candle is None:
            candle_start_ms = (now_ms // interval_ms) * interval_ms
            self.current_candle = {
                "time": candle_start_ms,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
                "is_closed": False
            }

        candle_start = self.current_candle["time"]
        candle_end = candle_start + interval_ms
        candle_closed_event = None

        if now_ms >= candle_end:
            # Candle has CLOSED!
            # The closed candle's OHLCV is strictly derived from ticks within its interval.
            closed_candle = {
                "time": self.current_candle["time"],
                "open": self.current_candle["open"],
                "high": self.current_candle["high"],
                "low": self.current_candle["low"],
                "close": self.current_candle["close"],
                "volume": self.current_candle["volume"],
                "is_closed": True
            }
            self.closed_candles.append(closed_candle)
            if len(self.closed_candles) > 1000:
                self.closed_candles.pop(0)

            # Trigger feature calculation & prediction on closed candle
            prediction_payload = self._generate_prediction_on_closed_candle(closed_candle)
            candle_closed_event = prediction_payload

            # Initialize new forming candle for new interval starting with the current tick
            next_start = (now_ms // interval_ms) * interval_ms
            self.current_candle = {
                "time": next_start,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
                "is_closed": False
            }
        else:
            # Update forming candle within active interval
            self.current_candle["high"] = max(self.current_candle["high"], price)
            self.current_candle["low"] = min(self.current_candle["low"], price)
            self.current_candle["close"] = price
            self.current_candle["volume"] += volume


        # Construct tick update message payload for /ws/price
        tick_event = {
            "type": "tick",
            "symbol": "BTC-USD",
            "price": price,
            "high": self.current_candle["high"],
            "low": self.current_candle["low"],
            "volume": self.current_candle["volume"],
            "timestamp": now_ms,
            "candle_time": self.current_candle["time"],
            "is_closed": False
        }

        return tick_event, candle_closed_event

    def _generate_prediction_on_closed_candle(self, closed_candle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs feature engineering & model inference ONLY on completed, closed candles.
        Fails closed with explicit UNAVAILABLE/BLOCKED status when production models are not authorized.
        Never fabricates mock probabilities (0.68), regimes, or signals.
        """
        candle_dt = datetime.fromtimestamp(closed_candle["time"] / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        price = closed_candle["close"]
        dt_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        pred_id = f"pred_{dt_str}_{int(closed_candle['time']/1000) % 10000}"

        # Enforce model authorization: check authoritative model registry
        try:
            from models.authoritative_model_registry import get_active_production_model, AuthorizationStatus
            active_model = get_active_production_model()
            is_authorized = (
                active_model is not None
                and active_model.authorization_status
                == AuthorizationStatus.AUTHORIZED_FOR_PRODUCTION
            )
        except Exception:
            is_authorized = False

        if not is_authorized:
            # Strictly fail closed: never emit mock 0.68 probabilities or synthetic signals
            prediction_payload = {
                "type": "prediction",
                "prediction_id": pred_id,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "candle_time": candle_dt,
                "price": price,
                "direction": "UNAVAILABLE",
                "probability": None,
                "raw_prob": None,
                "tp": None,
                "sl": None,
                "regime": "UNKNOWN",
                "decision": "BLOCKED",
                "status": "BLOCKED_MODEL_UNAUTHORIZED",
                "reason": "Production model inference is disabled; research authorization required.",
                "model_version": "BLOCKED_UNAUTHORIZED",
                "feature_version": "features_v3",
                "regime_version": "regime_v1"
            }
            self.last_prediction = prediction_payload
            return prediction_payload

        # If authorized in the future, causal model prediction logic would execute here.
        # Otherwise, default to fail-closed.
        prediction_payload = {
            "type": "prediction",
            "prediction_id": pred_id,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "candle_time": candle_dt,
            "price": price,
            "direction": "UNAVAILABLE",
            "probability": None,
            "raw_prob": None,
            "tp": None,
            "sl": None,
            "regime": "UNKNOWN",
            "decision": "BLOCKED",
            "status": "BLOCKED_MODEL_UNAUTHORIZED",
            "reason": "Production model inference is disabled; research authorization required.",
            "model_version": "BLOCKED_UNAUTHORIZED",
            "feature_version": "features_v3",
            "regime_version": "regime_v1"
        }
        self.last_prediction = prediction_payload
        return prediction_payload


# Aliases for backward compatibility
CandleManager = CandleStateManager
candle_manager = CandleStateManager()

"""
Candle State Manager for BTCognitive API Server.

Tracks forming vs closed candle states from streaming market ticks.
Guarantees that AI predictions are ONLY generated on closed candles.
"""

import os
import sys
import time
import pandas as pd
import numpy as np
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
        self.last_prediction: Optional[Dict[str, Any]] = None
        self.last_tick_time: Optional[float] = None
        self.model_ensemble = None

    def set_ensemble_model(self, ensemble):
        """Sets the active AI model ensemble for inference on candle close."""
        self.model_ensemble = ensemble

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
            "symbol": "BTCUSDT",
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
            is_authorized = (active_model is not None and active_model.authorization_status == AuthorizationStatus.PRODUCTION_AUTHORIZED)
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


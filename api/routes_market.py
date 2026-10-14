"""
api/routes_market.py — Market Data, Candlestick Streams & Live Ticker
====================================================================
FastAPI APIRouter handling real-time and historical market data feeds,
leveraging the shared async HTTP client and event-driven in-memory feature cache.
"""

import math
import pandas as pd
from fastapi import APIRouter, Query

from engine.feature_cache import feature_cache

router = APIRouter(tags=["Market Feeds"])


@router.get("/candles")
def get_candles(
    interval: str = Query("1h"),
    limit: int = Query(150, ge=1, le=500),
):
    """
    Returns validated historical OHLCV rows from the feature cache.

    The dedicated market-monitor router owns refreshed market endpoints; this
    legacy endpoint is explicitly cache-only and never fills missing values.
    """
    if interval != "1h":
        return {
            "status": "UNSUPPORTED_REQUEST",
            "interval": interval,
            "candles": [],
            "count": 0,
            "degraded": True,
            "source": "feature_cache",
        }

    df = feature_cache.get_features_df()
    if not df.empty:
        candles = []
        for _, row in df.tail(limit).iterrows():
            if "timestamp" not in row or any(name not in row for name in ("open", "high", "low", "close", "volume")):
                continue
            timestamp = pd.to_datetime(row["timestamp"], utc=True, errors="coerce")
            values = [row[name] for name in ("open", "high", "low", "close", "volume")]
            try:
                open_, high, low, close, volume = (float(value) for value in values)
            except (TypeError, ValueError, OverflowError):
                continue
            if (
                pd.isna(timestamp)
                or not all(math.isfinite(value) for value in (open_, high, low, close, volume))
                or min(open_, high, low, close) <= 0
                or volume < 0
                or high < max(open_, close, low)
                or low > min(open_, close, high)
            ):
                continue
            candles.append({
                "time": int(timestamp.timestamp()),
                "open": round(open_, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": round(volume, 4),
            })
        candles.sort(key=lambda candle: candle["time"])
    else:
        candles = []

    return {
        "candles": candles,
        "count": len(candles),
        "degraded": True,
        "source": "feature_cache",
    }

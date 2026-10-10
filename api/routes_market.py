"""
api/routes_market.py — Market Data, Candlestick Streams & Live Ticker
====================================================================
FastAPI APIRouter handling real-time and historical market data feeds,
leveraging the shared async HTTP client and event-driven in-memory feature cache.
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from fastapi import APIRouter, Request, Query

from config import SYMBOL, EXCHANGE
from api.http_client import (
    fetch_binance_klines_async,
    fetch_binance_ticker_24h_async,
    fetch_live_binance_btc_price_async
)
from engine.feature_cache import feature_cache

logger = logging.getLogger("btcognitive.routes_market")

router = APIRouter(tags=["Market Feeds"])


@router.get("/market/candles")
async def get_market_candles(
    request: Request,
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    interval: str = Query("1h", description="Candle timeframe interval"),
    limit: int = Query(500, le=1000, description="Max candles to retrieve")
):
    """
    Returns live OHLCV candles directly from Binance klines API (with Coinbase fallback).
    If upstream fails, falls back gracefully to in-memory cached historical candles with degraded status.
    """
    http_client = getattr(request.app.state, "http", None)
    candles = await fetch_binance_klines_async(symbol=symbol, interval=interval, limit=limit, client=http_client)

    if not candles:
        # Graceful degradation using cached in-memory features without random number hallucination
        df = feature_cache.get_features_df()
        if not df.empty and "time" in df.columns:
            tail_df = df.tail(limit)
            candles = [
                {
                    "time": int(row["time"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row.get("volume", 0.0))
                }
                for _, row in tail_df.iterrows()
            ]
            return {
                "symbol": symbol.upper(),
                "interval": interval,
                "count": len(candles),
                "candles": candles,
                "degraded": True,
                "source": "feature_cache"
            }

    return {
        "symbol": symbol.upper(),
        "interval": interval,
        "count": len(candles),
        "candles": candles,
        "degraded": False,
        "source": "live_exchange"
    }


@router.get("/market/latest")
async def get_market_latest(request: Request, days: int = Query(90, ge=1, le=365)):
    """
    Returns latest live market price, 24h stats, and technical indicators from feature cache.
    """
    http_client = getattr(request.app.state, "http", None)
    ticker = await fetch_binance_ticker_24h_async("BTCUSDT", client=http_client)
    live_p = await fetch_live_binance_btc_price_async(client=http_client)

    latest_row = feature_cache.get_latest_row()

    price = live_p if live_p is not None else (
        float(latest_row["close"]) if latest_row is not None and latest_row.get("close") is not None else None
    )
    if price is None:
        return {
            "status": "DATA_UNAVAILABLE",
            "symbol": SYMBOL,
            "exchange": EXCHANGE,
            "market_data": None,
        }

    change_pct = (
        float(ticker["priceChangePercent"])
        if ticker is not None and ticker.get("priceChangePercent") is not None
        else None
    )
    change_24h = (
        float(ticker["priceChange"])
        if ticker is not None and ticker.get("priceChange") is not None
        else None
    )
    high_24h = (
        float(ticker["highPrice"])
        if ticker is not None and ticker.get("highPrice") is not None
        else None
    )
    low_24h = (
        float(ticker["lowPrice"])
        if ticker is not None and ticker.get("lowPrice") is not None
        else None
    )
    volume_24h = (
        float(ticker["volume"])
        if ticker is not None and ticker.get("volume") is not None
        else None
    )

    def cached_value(column: str) -> Optional[float]:
        if latest_row is None or latest_row.get(column) is None:
            return None
        return float(latest_row[column])

    ret_24h = cached_value("ret_24h")
    realized_vol = cached_value("realized_vol_24h")
    rsi_14 = cached_value("rsi_14")
    oi_change = cached_value("oi_pct_change_24h")

    return {
        "status": "OK",
        "symbol": SYMBOL,
        "exchange": EXCHANGE,
        "price": price,
        "change_24h": round(change_24h, 2) if change_24h is not None else None,
        "change_pct_24h": round(change_pct, 2) if change_pct is not None else None,
        "high_24h": round(high_24h, 2) if high_24h is not None else None,
        "low_24h": round(low_24h, 2) if low_24h is not None else None,
        "volume_24h": round(volume_24h, 2) if volume_24h is not None else None,
        "ret_24h": round(ret_24h, 4) if ret_24h is not None else None,
        "realized_vol_24h": round(realized_vol, 4) if realized_vol is not None else None,
        "rsi_14": round(rsi_14, 2) if rsi_14 is not None else None,
        "oi_change_24h": round(oi_change, 4) if oi_change is not None else None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/candles")
def get_candles(interval: str = Query("1h"), limit: int = Query(150, le=500)):
    """
    Returns historical OHLCV candles formatted for TradingView Lightweight Charts directly from memory.
    """
    df = feature_cache.get_features_df()
    if not df.empty:
        tail_df = df.tail(limit)
        candles = []
        for _, row in tail_df.iterrows():
            if "timestamp" not in row or not all(
                key in row and pd.notna(row[key])
                for key in ("open", "high", "low", "close", "volume")
            ):
                continue
            ts = int(pd.to_datetime(row["timestamp"]).timestamp())
            candles.append({
                "time": ts,
                "open": round(float(row["open"]), 2),
                "high": round(float(row["high"]), 2),
                "low": round(float(row["low"]), 2),
                "close": round(float(row["close"]), 2),
                "volume": round(float(row["volume"]), 4)
            })
        return {
            "status": "OK" if candles else "DATA_UNAVAILABLE",
            "candles": candles,
            "count": len(candles),
            "degraded": not bool(candles),
        }

    return {"candles": [], "count": 0, "degraded": True}

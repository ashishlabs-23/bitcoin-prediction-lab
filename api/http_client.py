"""
api/http_client.py — Shared Async HTTP Client & Exchange Connectors
===================================================================
Provides a high-performance singleton httpx.AsyncClient with connection pooling,
DNS caching, and non-blocking asynchronous market data fetchers for Binance & Coinbase.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
import httpx

logger = logging.getLogger("btcognitive.http_client")

# Shared connection limits & timeout configuration
HTTP_TIMEOUT = 5.0
HTTP_LIMITS = httpx.Limits(max_connections=30, max_keepalive_connections=15, keepalive_expiry=30.0)

_global_client: Optional[httpx.AsyncClient] = None


def get_shared_client() -> httpx.AsyncClient:
    """Returns or initializes the shared AsyncClient singleton."""
    global _global_client
    if _global_client is None or _global_client.is_closed:
        _global_client = httpx.AsyncClient(
            timeout=HTTP_TIMEOUT,
            limits=HTTP_LIMITS,
            headers={"User-Agent": "BTCognitive/2.0 Institutional Terminal"}
        )
    return _global_client


async def close_shared_client():
    """Closes the shared AsyncClient gracefully upon server shutdown."""
    global _global_client
    if _global_client is not None and not _global_client.is_closed:
        await _global_client.aclose()
        _global_client = None


# ---------------------------------------------------------------------------
# Asynchronous Exchange Data Fetchers (Multi-Exchange Failover: Binance -> Coinbase -> Kraken -> Bybit)
# ---------------------------------------------------------------------------

async def fetch_live_binance_btc_price_async(client: Optional[httpx.AsyncClient] = None) -> Optional[float]:
    """
    Fetch real-time BTCUSD price with multi-exchange fallback chain:
    1. Binance Coin-M / Spot
    2. Coinbase Spot
    3. Kraken Spot
    4. Bybit Spot
    """
    http = client or get_shared_client()
    
    # 1. Binance Coin-M
    try:
        url = "https://dapi.binance.com/dapi/v1/ticker/price?symbol=BTCUSD_PERP"
        res = await http.get(url, timeout=2.5)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                return float(data[0]["price"])
            return float(data["price"])
    except Exception as e:
        logger.debug(f"Binance Coin-M price fetch failed ({e}). Trying Coinbase...")

    # 2. Coinbase Spot
    try:
        url = "https://api.coinbase.com/v2/prices/BTC-USD/spot"
        res = await http.get(url, timeout=2.5)
        if res.status_code == 200:
            data = res.json()
            return float(data["data"]["amount"])
    except Exception as ce:
        logger.debug(f"Coinbase price fallback failed ({ce}). Trying Kraken...")

    # 3. Kraken Spot
    try:
        url = "https://api.kraken.com/0/public/Ticker?pair=XBTUSD"
        res = await http.get(url, timeout=2.5)
        if res.status_code == 200:
            data = res.json()
            if not data.get("error"):
                pair_data = list(data.get("result", {}).values())[0]
                return float(pair_data["c"][0])
    except Exception as ke:
        logger.debug(f"Kraken price fallback failed ({ke}). Trying Bybit...")

    # 4. Bybit Spot
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT"
        res = await http.get(url, timeout=2.5)
        if res.status_code == 200:
            data = res.json()
            tickers = data.get("result", {}).get("list", [])
            if tickers:
                return float(tickers[0]["lastPrice"])
    except Exception as be:
        logger.error(f"All exchange price fallbacks exhausted (Bybit error: {be})")

    return None


async def fetch_binance_klines_async(
    symbol: str = "BTCUSD_PERP",
    interval: str = "1h",
    limit: int = 500,
    client: Optional[httpx.AsyncClient] = None
) -> List[Dict[str, Any]]:
    """
    Fetch OHLCV klines asynchronously with multi-exchange fallback chain:
    1. Binance REST (Coin-M / Spot)
    2. Coinbase Exchange Candles
    3. Kraken OHLC
    4. Bybit Spot Klines
    Returns list of {time, open, high, low, close, volume} dicts in chronological order.
    """
    http = client or get_shared_client()
    sym_upper = symbol.upper()

    # 1. Binance
    try:
        if sym_upper in ["BTCUSD", "BTCUSD_PERP", "BTC/USD"]:
            url = f"https://dapi.binance.com/dapi/v1/klines?symbol=BTCUSD_PERP&interval={interval}&limit={min(limit, 1000)}"
        else:
            url = f"https://api.binance.com/api/v3/klines?symbol={sym_upper}&interval={interval}&limit={min(limit, 1000)}"

        res = await http.get(url, timeout=3.5)
        if res.status_code == 200:
            raw = res.json()
            candles = []
            for k in raw:
                candles.append({
                    "time": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5])
                })
            return candles
    except Exception as e:
        logger.debug(f"Binance klines fetch failed ({e}). Trying Coinbase...")

    # 2. Coinbase
    granularity_map = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "1d": 86400}
    granularity = granularity_map.get(interval, 3600)
    adjusted_limit = limit * 4 if interval == "4h" else limit

    try:
        url = f"https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity={granularity}&limit={min(adjusted_limit, 300)}"
        res = await http.get(url, timeout=3.5)
        if res.status_code == 200:
            raw = res.json()[::-1]  # Oldest first
            candles = []
            for k in raw:
                candles.append({
                    "time": int(k[0] * 1000),
                    "open": float(k[3]),
                    "high": float(k[2]),
                    "low": float(k[1]),
                    "close": float(k[4]),
                    "volume": float(k[5])
                })
            if interval == "4h":
                agg_candles = []
                for i in range(0, len(candles), 4):
                    group = candles[i:i+4]
                    if not group:
                        continue
                    agg_candles.append({
                        "time": group[0]["time"],
                        "open": group[0]["open"],
                        "high": max(c["high"] for c in group),
                        "low": min(c["low"] for c in group),
                        "close": group[-1]["close"],
                        "volume": sum(c["volume"] for c in group)
                    })
                return agg_candles[-limit:]
            return candles
    except Exception as ce:
        logger.debug(f"Coinbase klines fallback failed ({ce}). Trying Kraken...")

    # 3. Kraken
    kraken_interval_map = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}
    k_interval = kraken_interval_map.get(interval, 60)
    try:
        url = f"https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval={k_interval}"
        res = await http.get(url, timeout=3.5)
        if res.status_code == 200:
            data = res.json()
            if not data.get("error"):
                raw_candles = list(data.get("result", {}).values())[0]
                candles = []
                for k in raw_candles:
                    candles.append({
                        "time": int(float(k[0]) * 1000),
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[6])
                    })
                return candles[-limit:]
    except Exception as ke:
        logger.debug(f"Kraken klines fallback failed ({ke}). Trying Bybit...")

    # 4. Bybit
    bybit_interval_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "D"}
    b_interval = bybit_interval_map.get(interval, "60")
    try:
        url = f"https://api.bybit.com/v5/market/kline?category=spot&symbol=BTCUSDT&interval={b_interval}&limit={min(limit, 200)}"
        res = await http.get(url, timeout=3.5)
        if res.status_code == 200:
            data = res.json()
            raw_candles = data.get("result", {}).get("list", [])
            candles = []
            for k in reversed(raw_candles):  # Bybit is newest-first -> reverse
                candles.append({
                    "time": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5])
                })
            return candles
    except Exception as be:
        logger.error(f"All exchange klines fallbacks exhausted (Bybit error: {be})")

    return []


async def fetch_binance_ticker_24h_async(
    symbol: str = "BTCUSDT",
    client: Optional[httpx.AsyncClient] = None
) -> Dict[str, Any]:
    """Fetch 24h ticker statistics asynchronously from Binance with Bybit fallback."""
    http = client or get_shared_client()
    sym_upper = symbol.upper()
    try:
        if sym_upper in ["BTCUSD", "BTCUSD_PERP", "BTC/USD"]:
            url = "https://dapi.binance.com/dapi/v1/ticker/24hr?symbol=BTCUSD_PERP"
        else:
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={sym_upper}"
        res = await http.get(url, timeout=3.0)
        if res.status_code == 200:
            data = res.json()
            return data[0] if isinstance(data, list) else data
    except Exception as e:
        logger.debug(f"Binance ticker fetch failed ({e}). Trying Bybit fallback...")

    # Fallback to Bybit
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT"
        res = await http.get(url, timeout=3.0)
        if res.status_code == 200:
            data = res.json()
            tickers = data.get("result", {}).get("list", [])
            if tickers:
                t = tickers[0]
                return {
                    "lastPrice": t.get("lastPrice"),
                    "highPrice": t.get("highPrice24h"),
                    "lowPrice": t.get("lowPrice24h"),
                    "volume": t.get("volume24h"),
                    "priceChangePercent": str(float(t.get("price24hPcnt", 0)) * 100)
                }
    except Exception as be:
        logger.warning(f"Ticker fallback failed: {be}")

    return {}


async def fetch_live_binance_funding_rate_async(client: Optional[httpx.AsyncClient] = None) -> Optional[float]:
    """Fetch live funding rate from Binance Futures with Bybit fallback."""
    http = client or get_shared_client()
    try:
        url = "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT"
        res = await http.get(url, timeout=3.0)
        if res.status_code == 200:
            return float(res.json()["lastFundingRate"])
    except Exception as e:
        logger.debug(f"Binance funding rate fetch failed ({e}). Trying Bybit linear fallback...")

    # Fallback: Bybit Linear Perpetuals
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"
        res = await http.get(url, timeout=3.0)
        if res.status_code == 200:
            data = res.json()
            tickers = data.get("result", {}).get("list", [])
            if tickers and "fundingRate" in tickers[0]:
                return float(tickers[0]["fundingRate"])
    except Exception as be:
        logger.warning(f"Bybit funding rate fallback failed: {be}")

    return None


async def fetch_live_binance_funding_rate_history_async(client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, Any]]:
    """Fetch settled funding rate history from Binance Futures."""
    http = client or get_shared_client()
    try:
        url = "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=8"
        res = await http.get(url, timeout=3.0)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        logger.warning(f"Funding rate history fetch failed: {e}")
    return []


async def fetch_live_binance_open_interest_async(client: Optional[httpx.AsyncClient] = None) -> Optional[float]:
    """Fetch live open interest from Binance Futures with Bybit fallback."""
    http = client or get_shared_client()
    try:
        url = "https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT"
        res = await http.get(url, timeout=3.0)
        if res.status_code == 200:
            return float(res.json()["openInterest"])
    except Exception as e:
        logger.debug(f"Binance open interest fetch failed ({e}). Trying Bybit...")

    # Bybit open interest
    try:
        url = "https://api.bybit.com/v5/market/open-interest?category=linear&symbol=BTCUSDT&intervalTime=5min&limit=1"
        res = await http.get(url, timeout=3.0)
        if res.status_code == 200:
            data = res.json()
            items = data.get("result", {}).get("list", [])
            if items:
                return float(items[0]["openInterest"])
    except Exception as be:
        logger.warning(f"Bybit open interest fallback failed: {be}")

    return None


async def fetch_live_binance_oi_history_async(client: Optional[httpx.AsyncClient] = None) -> List[Dict[str, Any]]:
    """Fetch 24h open interest history from Binance Futures."""
    http = client or get_shared_client()
    try:
        url = "https://fapi.binance.com/futures/data/openInterestHist?symbol=BTCUSDT&period=1h&limit=25"
        res = await http.get(url, timeout=3.0)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        logger.warning(f"Open interest history fetch failed: {e}")
    return []


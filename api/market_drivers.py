"""Truthful BTC/USD market monitoring and empirical baseline forecasting.

This module is deliberately independent of the frozen production-model artifacts.
It uses public spot candles to estimate non-overlapping historical return quantiles.
Those ranges are exploratory baselines, not validated trading signals.
"""
from __future__ import annotations

import asyncio
import math
import statistics
import threading
import time
from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

HISTORY_DAYS = 90
HISTORY_TTL_SECONDS = 900
QUOTE_TTL_SECONDS = 10
DERIVATIVES_TTL_SECONDS = 60
MIN_BLOCKS = 20
BACKTEST_MIN_BLOCKS = 20
MAX_FORECAST_BLOCKS = 90
HOUR = 3600

# The three adapters all describe spot BTC quoted in USD. USDT perpetuals below
# are context only and are never substituted for the spot price or its candles.
PROVIDERS = ("coinbase", "bitstamp", "kraken")
_CACHE_LOCK = threading.Lock()
_HISTORY_CACHE: dict[str, tuple[float, list[dict[str, float]]]] = {}
_QUOTE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_DERIVATIVE_CACHE: tuple[float, dict[str, Any]] | None = None


def _utc_iso(epoch: float | int) -> str:
    return datetime.fromtimestamp(float(epoch), tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _positive(value: Any) -> float | None:
    number = _finite(value)
    return number if number is not None and number > 0 else None


def _iso_param(epoch: int) -> str:
    return _utc_iso(epoch)


async def _get_json(client: Any, url: str, params: dict[str, Any] | None = None) -> Any:
    """Fetch public market data using the app's shared client when available."""
    if client is not None:
        response = await client.get(url, params=params, timeout=httpx.Timeout(5.0, connect=2.0))
        response.raise_for_status()
        return response.json()
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(5.0, connect=2.0),
        headers={"User-Agent": "BTCognitive-MarketMonitor/1.0", "Accept": "application/json"},
    ) as own_client:
        response = await own_client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def _normalise_candles(rows: Iterable[dict[str, Any]], now: float | None = None) -> list[dict[str, float]]:
    """Validate, de-duplicate, sort and discard the current incomplete 1h candle."""
    now_epoch = time.time() if now is None else now
    closed_before = int(now_epoch // HOUR) * HOUR
    by_time: dict[int, dict[str, float]] = {}
    for row in rows:
        ts = _finite(row.get("time"))
        op = _positive(row.get("open"))
        high = _positive(row.get("high"))
        low = _positive(row.get("low"))
        close = _positive(row.get("close"))
        volume = _finite(row.get("volume", 0.0))
        if None in (ts, op, high, low, close, volume):
            continue
        ts_i = int(ts)
        if ts_i < 0 or ts_i % HOUR != 0 or ts_i + HOUR > closed_before or volume < 0:
            continue
        if low > min(op, close) or high < max(op, close) or high < low:
            continue
        by_time[ts_i] = {
            "time": float(ts_i),
            "open": float(op),
            "high": float(high),
            "low": float(low),
            "close": float(close),
            "volume": float(volume),
        }
    return [by_time[key] for key in sorted(by_time)]


async def _fetch_coinbase_history(client: Any) -> list[dict[str, float]]:
    """Fetch 90 days of Coinbase BTC-USD 1h bars in <=300-candle windows."""
    end = int(time.time() // HOUR) * HOUR
    start = end - HISTORY_DAYS * 24 * HOUR
    step = 299 * HOUR
    windows: list[tuple[int, int]] = []
    cursor = start
    while cursor < end:
        stop = min(cursor + step, end)
        windows.append((cursor, stop))
        cursor = stop
    semaphore = asyncio.Semaphore(3)

    async def load_window(lo: int, hi: int) -> list[dict[str, float]]:
        async with semaphore:
            raw = await _get_json(
                client,
                "https://api.exchange.coinbase.com/products/BTC-USD/candles",
                {"granularity": 3600, "start": _iso_param(lo), "end": _iso_param(hi)},
            )
        converted = []
        if not isinstance(raw, list):
            return converted
        for item in raw:
            # Coinbase candle: [time, low, high, open, close, volume].
            if not isinstance(item, (list, tuple)) or len(item) < 6:
                continue
            converted.append({
                "time": item[0], "low": item[1], "high": item[2],
                "open": item[3], "close": item[4], "volume": item[5],
            })
        return converted

    chunks = await asyncio.gather(
        *(load_window(lo, hi) for lo, hi in windows),
        return_exceptions=True,
    )
    rows: list[dict[str, Any]] = []
    for chunk in chunks:
        if isinstance(chunk, list):
            rows.extend(chunk)
    return _normalise_candles(rows)


async def _fetch_bitstamp_history(client: Any) -> list[dict[str, float]]:
    raw = await _get_json(
        client,
        "https://www.bitstamp.net/api/v2/ohlc/btcusd/",
        {"step": 3600, "limit": 1000},
    )
    values = ((raw or {}).get("data") or {}).get("ohlc") or []
    rows = []
    for row in values:
        rows.append({
            "time": row.get("timestamp"), "open": row.get("open"),
            "high": row.get("high"), "low": row.get("low"),
            "close": row.get("close"), "volume": row.get("volume", 0),
        })
    return _normalise_candles(rows)


async def _fetch_kraken_history(client: Any) -> list[dict[str, float]]:
    since = int(time.time()) - HISTORY_DAYS * 24 * HOUR
    raw = await _get_json(
        client, "https://api.kraken.com/0/public/OHLC",
        {"pair": "XBTUSD", "interval": 60, "since": since},
    )
    if not isinstance(raw, dict) or raw.get("error"):
        raise RuntimeError("Kraken OHLC unavailable")
    results = raw.get("result") or {}
    key = next((name for name in results if name != "last"), None)
    values = results.get(key, []) if key else []
    rows = []
    for row in values:
        if not isinstance(row, (list, tuple)) or len(row) < 7:
            continue
        rows.append({
            "time": row[0], "open": row[1], "high": row[2], "low": row[3],
            "close": row[4], "volume": row[6],
        })
    return _normalise_candles(rows)


async def _fetch_history(provider: str, client: Any) -> list[dict[str, float]]:
    with _CACHE_LOCK:
        cached = _HISTORY_CACHE.get(provider)
        if cached and time.time() - cached[0] < HISTORY_TTL_SECONDS:
            return list(cached[1])

    if provider == "coinbase":
        candles = await _fetch_coinbase_history(client)
    elif provider == "bitstamp":
        candles = await _fetch_bitstamp_history(client)
    else:
        candles = await _fetch_kraken_history(client)

    if candles:
        with _CACHE_LOCK:
            _HISTORY_CACHE[provider] = (time.time(), candles)
    return candles


async def _fetch_quote(provider: str, client: Any) -> dict[str, Any]:
    with _CACHE_LOCK:
        cached = _QUOTE_CACHE.get(provider)
        if cached and time.time() - cached[0] < QUOTE_TTL_SECONDS:
            result = dict(cached[1])
            result["cache_age_seconds"] = round(time.time() - cached[0], 2)
            return result

    if provider == "coinbase":
        raw = await _get_json(client, "https://api.exchange.coinbase.com/products/BTC-USD/ticker")
        price, bid, ask = _positive(raw.get("price")), _positive(raw.get("bid")), _positive(raw.get("ask"))
        volume = _finite(raw.get("volume", 0))
        source_time = raw.get("time")
    elif provider == "bitstamp":
        raw = await _get_json(client, "https://www.bitstamp.net/api/v2/ticker/btcusd/")
        price, bid, ask = _positive(raw.get("last")), _positive(raw.get("bid")), _positive(raw.get("ask"))
        volume = _finite(raw.get("volume", 0))
        ts = _finite(raw.get("timestamp"))
        source_time = _utc_iso(ts) if ts is not None else None
    else:
        raw = await _get_json(client, "https://api.kraken.com/0/public/Ticker", {"pair": "XBTUSD"})
        if not isinstance(raw, dict) or raw.get("error"):
            raise RuntimeError("Kraken ticker unavailable")
        results = raw.get("result") or {}
        key = next(iter(results), None)
        ticker = results.get(key) or {}
        close = ticker.get("c") or [None]
        bid_row = ticker.get("b") or [None]
        ask_row = ticker.get("a") or [None]
        volume_row = ticker.get("v") or [0, 0]
        price, bid, ask = _positive(close[0]), _positive(bid_row[0]), _positive(ask_row[0])
        volume = _finite(volume_row[-1] if volume_row else 0)
        source_time = None

    if price is None:
        raise RuntimeError(f"{provider} returned no valid BTC/USD price")
    retrieved = time.time()
    quote = {
        "provider": provider,
        "instrument": "BTC/USD",
        "price": price,
        "bid": bid,
        "ask": ask,
        "volume_24h_btc": volume,
        "source_timestamp": source_time,
        "retrieved_at": _utc_iso(retrieved),
        "retrieved_epoch": retrieved,
        "cache_age_seconds": 0.0,
    }
    with _CACHE_LOCK:
        _QUOTE_CACHE[provider] = (retrieved, quote)
    return dict(quote)


async def _fetch_derivatives(client: Any) -> dict[str, Any]:
    """Optional BTCUSDT perpetual context; never mixed into the BTC/USD spot series."""
    global _DERIVATIVE_CACHE
    with _CACHE_LOCK:
        cached = _DERIVATIVE_CACHE
        if cached and time.time() - cached[0] < DERIVATIVES_TTL_SECONDS:
            return dict(cached[1])

    try:
        funding, oi = await asyncio.gather(
            _get_json(client, "https://fapi.binance.com/fapi/v1/premiumIndex", {"symbol": "BTCUSDT"}),
            _get_json(client, "https://fapi.binance.com/fapi/v1/openInterest", {"symbol": "BTCUSDT"}),
        )
        result = {
            "status": "AVAILABLE",
            "source": "Binance USDⓈ-M BTCUSDT perpetual",
            "instrument": "BTCUSDT perpetual (USDT-quoted context, not BTC/USD spot)",
            "observed_at": _utc_iso(time.time()),
            "funding_rate": _finite((funding or {}).get("lastFundingRate")),
            "next_funding_time": _finite((funding or {}).get("nextFundingTime")),
            "open_interest_contracts": _finite((oi or {}).get("openInterest")),
            "mark_price_usdt": _positive((funding or {}).get("markPrice")),
        }
        if result["funding_rate"] is None or result["open_interest_contracts"] is None:
            raise RuntimeError("derivatives response missing required values")
    except Exception as exc:
        result = {
            "status": "UNAVAILABLE",
            "source": "Binance USDⓈ-M BTCUSDT perpetual",
            "instrument": "BTCUSDT perpetual (USDT-quoted context, not BTC/USD spot)",
            "reason": type(exc).__name__,
            "funding_rate": None,
            "open_interest_contracts": None,
            "mark_price_usdt": None,
        }
    with _CACHE_LOCK:
        _DERIVATIVE_CACHE = (time.time(), result)
    return dict(result)


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _non_overlapping_log_returns(candles: list[dict[str, float]], horizon_hours: int) -> list[float]:
    """Complete horizon returns using exact timestamps; gaps never become fake intervals."""
    if not candles or horizon_hours < 1:
        return []
    step = horizon_hours * HOUR
    by_time = {int(row["time"]): float(row["close"]) for row in candles}
    last_time = max(by_time)
    first_time = min(by_time)
    end_time = last_time - (last_time % step)
    result: list[float] = []
    while end_time - step >= first_time:
        earlier = by_time.get(end_time - step)
        later = by_time.get(end_time)
        if earlier is not None and later is not None and earlier > 0 and later > 0:
            value = math.log(later / earlier)
            if math.isfinite(value):
                result.append(value)
        end_time -= step
    result.reverse()
    return result[-MAX_FORECAST_BLOCKS:]


def _walk_forward_metrics(returns: list[float]) -> dict[str, Any]:
    n = len(returns)
    initial = min(30, max(10, n // 2))
    tests = returns[initial:]
    if len(tests) < BACKTEST_MIN_BLOCKS:
        return {
            "status": "INSUFFICIENT_HOLDOUT",
            "train_blocks_before_first_test": initial,
            "test_blocks": len(tests),
            "interval_coverage_pct": None,
            "median_absolute_error_pct": None,
            "zero_return_baseline_mae_pct": None,
            "median_vs_zero_mae_skill_pct": None,
            "note": "Not enough independent, non-overlapping test blocks for a meaningful comparison.",
        }

    hits = 0
    forecast_errors = []
    baseline_errors = []
    for index in range(initial, n):
        history = returns[max(0, index - MAX_FORECAST_BLOCKS):index]
        p10 = _percentile(history, 0.10)
        p50 = _percentile(history, 0.50)
        p90 = _percentile(history, 0.90)
        actual = returns[index]
        hits += int(p10 <= actual <= p90)
        forecast_errors.append(abs(actual - p50))
        baseline_errors.append(abs(actual))  # zero-return/random-walk baseline

    forecast_mae = statistics.fmean(forecast_errors)
    baseline_mae = statistics.fmean(baseline_errors)
    skill = ((baseline_mae - forecast_mae) / baseline_mae * 100.0) if baseline_mae > 0 else None
    return {
        "status": "WALK_FORWARD_MEASURED_NOT_PROMOTED",
        "train_blocks_before_first_test": initial,
        "test_blocks": len(tests),
        "interval_coverage_pct": round(hits / len(tests) * 100.0, 2),
        "median_absolute_error_pct": round(forecast_mae * 100.0, 5),
        "zero_return_baseline_mae_pct": round(baseline_mae * 100.0, 5),
        "median_vs_zero_mae_skill_pct": round(skill, 2) if skill is not None else None,
        "note": "Historical rolling-origin baseline only; not evidence of live profitability or validation of the frozen production model.",
    }


def build_empirical_forecast(
    candles: list[dict[str, float]],
    spot_price: float,
    horizon: str = "24h",
) -> dict[str, Any]:
    """Return empirical P10/P50/P90 price ranges without fabricating missing data."""
    valid_price = _positive(spot_price)
    horizon_hours = {"1h": 1, "4h": 4, "24h": 24}.get(horizon)
    result_base = {
        "symbol": "BTC/USD",
        "model": "rolling_non_overlapping_empirical_return_quantiles_v1",
        "forecast_mode": "EXPERIMENTAL_BASELINE",
        "validation_status": "NOT_VALIDATED_FOR_TRADING",
        "live_capital_authorized": False,
        "execution_mode": "READ_ONLY_RESEARCH",
        "research_authorization": "BLOCKED_PROVENANCE_UNVERIFIED",
        "horizon": horizon,
        "horizon_hours": horizon_hours,
        "direction": "NOT_ESTIMATED",
        "probability": None,
        "probability_pct": None,
        "tp": None,
        "sl": None,
        "price_quantiles_usd": None,
        "governance_disclaimer": (
            "This is a transparent historical-distribution baseline, not the authenticated production model "
            "and not a trading signal. Historical quantiles may fail during regime changes."
        ),
        "generated_at": _utc_iso(time.time()),
    }
    if valid_price is None:
        return {**result_base, "status": "DATA_UNAVAILABLE", "availability": "UNAVAILABLE", "reason": "NO_VALID_SPOT_PRICE"}
    if horizon_hours is None:
        return {**result_base, "status": "DATA_UNAVAILABLE", "availability": "UNAVAILABLE", "reason": "UNSUPPORTED_HORIZON"}

    closed = _normalise_candles(candles)
    closes = [row["close"] for row in closed]
    returns = _non_overlapping_log_returns(closed, horizon_hours)
    if len(returns) < MIN_BLOCKS:
        return {
            **result_base,
            "status": "DATA_UNAVAILABLE",
            "availability": "UNAVAILABLE",
            "reason": "INSUFFICIENT_NON_OVERLAPPING_HISTORY",
            "horizon": horizon,
            "horizon_hours": horizon_hours,
            "sample_blocks": len(returns),
            "minimum_required_blocks": MIN_BLOCKS,
            "spot_price_usd": valid_price,
            "price_quantiles_usd": None,
            "backtest": {
                "status": "INSUFFICIENT_HISTORY",
                "test_blocks": 0,
                "interval_coverage_pct": None,
                "median_absolute_error_pct": None,
                "zero_return_baseline_mae_pct": None,
                "median_vs_zero_mae_skill_pct": None,
            },
        }

    p10, p50, p90 = (_percentile(returns[-MAX_FORECAST_BLOCKS:], q) for q in (0.10, 0.50, 0.90))
    prices = {
        "p10": round(valid_price * math.exp(p10), 2),
        "p50": round(valid_price * math.exp(p50), 2),
        "p90": round(valid_price * math.exp(p90), 2),
    }
    return {
        **result_base,
        "status": "EXPERIMENTAL_BASELINE",
        "availability": "AVAILABLE",
        "horizon": horizon,
        "horizon_hours": horizon_hours,
        "spot_price_usd": round(valid_price, 2),
        "median_return_pct": round(p50 * 100.0, 4),
        "return_quantiles_pct": {
            "p10": round(p10 * 100.0, 4),
            "p50": round(p50 * 100.0, 4),
            "p90": round(p90 * 100.0, 4),
        },
        "price_quantiles_usd": prices,
        "historical_positive_return_frequency_pct": round(sum(value > 0 for value in returns) / len(returns) * 100.0, 2),
        "sample_blocks": len(returns),
        "sample_quality": "LIMITED" if len(returns) < 60 else "MODERATE",
        "central_interval_nominal_coverage_pct": 80.0,
        "backtest": _walk_forward_metrics(returns),
        # Safe compatibility fields: these are not TP/SL orders or targets.
        "entry_price": round(valid_price, 2),
        "btc_price": round(valid_price, 2),
        "tp": None,
        "sl": None,
        "probability": None,
        "probability_pct": None,
        "direction": "NOT_ESTIMATED",
        "action": "READ_ONLY_EXPERIMENTAL_FORECAST",
        "research_classification": "EXPERIMENTAL_BASELINE",
        "claim_level": "UNVALIDATED",
    }


def _derive_technical(candles: list[dict[str, float]]) -> dict[str, Any]:
    closes = [row["close"] for row in candles]
    highs = [row["high"] for row in candles]
    lows = [row["low"] for row in candles]
    volumes = [row["volume"] for row in candles]
    result: dict[str, Any] = {}
    for hours, label in ((1, "momentum_1h_pct"), (4, "momentum_4h_pct"), (24, "momentum_24h_pct"), (168, "momentum_7d_pct")):
        if len(closes) > hours and closes[-hours - 1] > 0:
            result[label] = round((closes[-1] / closes[-hours - 1] - 1.0) * 100.0, 4)
        else:
            result[label] = None
    log_returns = [math.log(closes[i] / closes[i-1]) for i in range(1, len(closes)) if closes[i] > 0 and closes[i-1] > 0]
    result["realized_volatility_24h_pct"] = round(statistics.stdev(log_returns[-24:]) * math.sqrt(24) * 100.0, 4) if len(log_returns) >= 2 else None
    result["realized_volatility_7d_pct"] = round(statistics.stdev(log_returns[-168:]) * math.sqrt(24 * 7) * 100.0, 4) if len(log_returns) >= 2 else None
    if len(closes) >= 15:
        deltas = [closes[i] - closes[i-1] for i in range(len(closes)-14, len(closes))]
        gains = sum(max(value, 0.0) for value in deltas)
        losses = sum(max(-value, 0.0) for value in deltas)
        result["rsi_14"] = round(100.0 if losses == 0 else 100.0 - (100.0 / (1.0 + gains / losses)), 2)
    else:
        result["rsi_14"] = None
    if len(volumes) >= 48:
        prior = statistics.fmean(volumes[-48:-24])
        latest = statistics.fmean(volumes[-24:])
        result["volume_ratio_24h"] = round(latest / prior, 3) if prior > 0 else None
    else:
        result["volume_ratio_24h"] = None
    if len(highs) >= 24 and len(lows) >= 24:
        result["high_24h_usd"] = round(max(highs[-24:]), 2)
        result["low_24h_usd"] = round(min(lows[-24:]), 2)
    else:
        result["high_24h_usd"] = None
        result["low_24h_usd"] = None
    return result


async def _load_provider_bundle(provider: str, client: Any) -> tuple[dict[str, Any], list[dict[str, float]]]:
    quote = await _fetch_quote(provider, client)
    candles = await _fetch_history(provider, client)
    if not candles:
        raise RuntimeError(f"{provider} returned no usable closed hourly candles")
    return quote, candles


async def get_market_dashboard(client: Any = None, horizon: str = "24h") -> dict[str, Any]:
    """Single source of truth for the dashboard, live market routes and baseline forecast."""
    own_client = None
    if client is None:
        own_client = httpx.AsyncClient(
            timeout=httpx.Timeout(5.0, connect=2.0),
            headers={"User-Agent": "BTCognitive-MarketMonitor/1.0", "Accept": "application/json"},
        )
        client = own_client
    try:
        selected: tuple[dict[str, Any], list[dict[str, float]]] | None = None
        errors: dict[str, str] = {}
        first_quote: dict[str, Any] | None = None
        for provider in PROVIDERS:
            try:
                quote = await _fetch_quote(provider, client)
                if first_quote is None:
                    first_quote = quote
                candles = await _fetch_history(provider, client)
                if candles:
                    selected = (quote, candles)
                    break
                errors[provider] = "NO_USABLE_CANDLES"
            except Exception as exc:
                errors[provider] = type(exc).__name__

        if selected is None:
            quote = first_quote
            market = {
                "status": "DATA_UNAVAILABLE" if quote is None else "PARTIAL",
                "symbol": "BTC/USD",
                "source": quote["provider"] if quote else None,
                "price_usd": round(quote["price"], 2) if quote else None,
                "bid_usd": quote.get("bid") if quote else None,
                "ask_usd": quote.get("ask") if quote else None,
                "source_timestamp": quote.get("source_timestamp") if quote else None,
                "retrieved_at": quote.get("retrieved_at") if quote else None,
                "age_seconds": round(time.time() - quote["retrieved_epoch"], 2) if quote else None,
                "reason": "NO_PROVIDER_RETURNED_USABLE_CLOSED_CANDLES",
            }
            forecast = build_empirical_forecast([], quote["price"] if quote else None, horizon)
            return {
                "status": "PARTIAL" if quote is not None else "DATA_UNAVAILABLE",
                "generated_at": _utc_iso(time.time()),
                "market": market,
                "technical": {},
                "candles": [],
                "forecast": forecast,
                "drivers": [],
                "derivatives": {"status": "UNAVAILABLE", "funding_rate": None, "open_interest_contracts": None},
                "capital_flows": {"status": "NOT_CONFIGURED", "reason": "No verified ETF-flow provider configured."},
                "macro": {"status": "NOT_CONFIGURED", "reason": "No FRED API key/provider configured."},
                "research": {"status": "BLOCKED_PROVENANCE_UNVERIFIED", "production_forecast_available": False, "trading_enabled": False},
                "provider_errors": errors,
            }

        quote, candles = selected
        current_epoch = quote["retrieved_epoch"]
        technical = _derive_technical(candles)
        bid, ask = quote.get("bid"), quote.get("ask")
        # Compare separately observed USD spot quotes; never average venues into a synthetic price.
        other_providers = [provider for provider in PROVIDERS if provider != quote["provider"]]
        quote_results = await asyncio.gather(
            *(_fetch_quote(provider, client) for provider in other_providers),
            return_exceptions=True,
        )
        venue_quotes = [{
            "provider": quote["provider"], "instrument": "BTC/USD",
            "price_usd": round(quote["price"], 2), "retrieved_at": quote["retrieved_at"],
        }]
        for provider, item in zip(other_providers, quote_results):
            if isinstance(item, dict):
                venue_quotes.append({
                    "provider": provider, "instrument": "BTC/USD",
                    "price_usd": round(item["price"], 2), "retrieved_at": item["retrieved_at"],
                })
            else:
                errors[f"{provider}_quote"] = type(item).__name__
        venue_prices = [item["price_usd"] for item in venue_quotes]
        venue_divergence_pct = (
            (max(venue_prices) - min(venue_prices)) / quote["price"] * 100.0
            if len(venue_prices) >= 2 and quote["price"] > 0 else None
        )
        last_candle_epoch = int(candles[-1]["time"]) if candles else None
        candle_age_seconds = max(0.0, time.time() - (last_candle_epoch + HOUR)) if last_candle_epoch else None
        spread_bps = ((ask - bid) / ((ask + bid) / 2.0) * 10000.0) if bid and ask and ask >= bid else None
        forecast = build_empirical_forecast(candles, quote["price"], horizon)
        horizons = {
            value: build_empirical_forecast(candles, quote["price"], value)
            for value in ("1h", "4h", "24h")
        }
        forecast["all_horizons"] = horizons
        derivatives = await _fetch_derivatives(client)
        drivers = [
            {"id": key, "label": label, "value": technical.get(key), "unit": "%" if key.endswith("_pct") else "", "status": "AVAILABLE" if technical.get(key) is not None else "INSUFFICIENT_HISTORY"}
            for key, label in (
                ("momentum_1h_pct", "1-hour momentum"),
                ("momentum_4h_pct", "4-hour momentum"),
                ("momentum_24h_pct", "24-hour momentum"),
                ("realized_volatility_24h_pct", "24-hour realized volatility"),
                ("realized_volatility_7d_pct", "7-day realized volatility"),
                ("rsi_14", "RSI (14)"),
                ("volume_ratio_24h", "Volume ratio (latest 24h vs prior 24h)"),
            )
        ]
        drivers.extend([
            {"id": "spread_bps", "label": "Bid–ask spread", "value": round(spread_bps, 3) if spread_bps is not None else None, "unit": "bps", "status": "AVAILABLE" if spread_bps is not None else "UNAVAILABLE"},
            {"id": "venue_divergence_pct", "label": "Cross-venue spot divergence", "value": round(venue_divergence_pct, 4) if venue_divergence_pct is not None else None, "unit": "%", "status": "AVAILABLE" if venue_divergence_pct is not None else "INSUFFICIENT_VENUES"},
            {"id": "funding_rate", "label": "BTCUSDT perpetual funding", "value": derivatives.get("funding_rate"), "unit": "rate", "status": derivatives.get("status", "UNAVAILABLE"), "source_instrument": derivatives.get("instrument")},
            {"id": "open_interest_contracts", "label": "BTCUSDT perpetual open interest", "value": derivatives.get("open_interest_contracts"), "unit": "contracts", "status": derivatives.get("status", "UNAVAILABLE"), "source_instrument": derivatives.get("instrument")},
        ])
        return {
            "status": "LIVE",
            "generated_at": _utc_iso(time.time()),
            "market": {
                "status": "LIVE",
                "symbol": "BTC/USD",
                "source": quote["provider"],
                "price_usd": round(quote["price"], 2),
                "bid_usd": round(bid, 2) if bid else None,
                "ask_usd": round(ask, 2) if ask else None,
                "spread_bps": round(spread_bps, 3) if spread_bps is not None else None,
                "volume_24h_btc": round(quote["volume_24h_btc"], 6) if quote.get("volume_24h_btc") is not None else None,
                "source_timestamp": quote.get("source_timestamp"),
                "retrieved_at": quote["retrieved_at"],
                "age_seconds": round(time.time() - current_epoch, 2),
                "latest_closed_candle_at": _utc_iso(last_candle_epoch) if last_candle_epoch else None,
                "candle_age_seconds": round(candle_age_seconds, 2) if candle_age_seconds is not None else None,
                "cross_exchange_quotes": venue_quotes,
                "cross_exchange_divergence_pct": round(venue_divergence_pct, 4) if venue_divergence_pct is not None else None,
            },
            "technical": technical,
            "candles": candles[-168:],
            "candle_interval": "1h",
            "candle_count": len(candles),
            "forecast": forecast,
            "drivers": drivers,
            "derivatives": derivatives,
            "capital_flows": {"status": "NOT_CONFIGURED", "reason": "ETF and exchange-flow observations are not integrated; no values are inferred."},
            "macro": {"status": "NOT_CONFIGURED", "reason": "FRED credentials/provider are not configured; no values are inferred."},
            "research": {
                "status": "BLOCKED_PROVENANCE_UNVERIFIED",
                "production_forecast_available": False,
                "trading_enabled": False,
                "message": "Frozen model inputs/evaluation evidence are not authenticated. The displayed forecast is an independent empirical baseline only.",
            },
            "provider_errors": errors,
        }
    finally:
        if own_client is not None:
            await own_client.aclose()


def reset_market_cache_for_tests() -> None:
    """Clear module caches to keep tests deterministic."""
    global _DERIVATIVE_CACHE
    with _CACHE_LOCK:
        _HISTORY_CACHE.clear()
        _QUOTE_CACHE.clear()
        _DERIVATIVE_CACHE = None
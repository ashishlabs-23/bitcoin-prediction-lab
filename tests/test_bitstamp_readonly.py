"""Focused contract tests for the isolated Bitstamp public read adapter."""

import asyncio
from datetime import datetime, timezone

import httpx
import pytest

from api.bitstamp_readonly import (
    BITSTAMP_OHLC_URL,
    REQUEST_TIMEOUT_SECONDS,
    BitstampReadResult,
    ReadStatus,
    fetch_bitstamp_btcusd_ohlcv,
)


NOW = 1_800_000_000
NOW_DATETIME = datetime.fromtimestamp(NOW, tz=timezone.utc)


def _payload(*candles, pair="BTC/USD"):
    return {"data": {"pair": pair, "ohlc": list(candles)}}


def _candle(timestamp, *, open_="100", high="105", low="95", close="102", volume="1.5"):
    return {
        "timestamp": str(timestamp),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }


def _mock_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_valid_response_converts_open_timestamp_and_excludes_incomplete_bar():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["timeout"] = request.extensions.get("timeout")
        return httpx.Response(
            200,
            json=_payload(
                _candle(NOW - 180),
                _candle(NOW - 60),
                _candle(NOW),
            ),
        )

    async with _mock_client(handler) as client:
        result = await fetch_bitstamp_btcusd_ohlcv(client, now=NOW_DATETIME)

    assert isinstance(result, BitstampReadResult)
    assert result.status is ReadStatus.OK
    assert seen["url"].startswith(BITSTAMP_OHLC_URL)
    assert "step=60" in seen["url"]
    assert seen["timeout"]["read"] == REQUEST_TIMEOUT_SECONDS
    assert len(result.bars) == 2
    assert result.bars[-1].source_timestamp == NOW - 60
    assert result.bars[-1].timestamp == NOW
    assert result.bars[-1].timestamp_semantics == "INTERVAL_CLOSE"
    assert result.source == "bitstamp_public_ohlc"
    assert result.venue == "BITSTAMP"
    assert result.symbol == "BTC/USD"
    assert result.source_timestamp == NOW - 60
    assert result.retrieved_at == NOW
    assert result.freshness_limit_seconds == 180


@pytest.mark.asyncio
async def test_stale_completed_bar_returns_stale_status_and_keeps_provenance():
    def handler(_request):
        return httpx.Response(200, json=_payload(_candle(NOW - 600)))

    async with _mock_client(handler) as client:
        result = await fetch_bitstamp_btcusd_ohlcv(
            client, now=NOW, freshness_limit_seconds=120
        )

    assert result.status is ReadStatus.STALE_DATA
    assert len(result.bars) == 1
    assert result.bars[0].timestamp == NOW - 540
    assert result.freshness_limit_seconds == 120


@pytest.mark.asyncio
async def test_timeout_is_data_unavailable():
    def handler(_request):
        raise httpx.ReadTimeout("mock timeout")

    async with _mock_client(handler) as client:
        result = await fetch_bitstamp_btcusd_ohlcv(client, now=NOW)

    assert result.status is ReadStatus.DATA_UNAVAILABLE
    assert result.bars == ()
    assert "timed out" in result.message


@pytest.mark.asyncio
async def test_malformed_response_is_provenance_failure():
    def handler(_request):
        return httpx.Response(200, json={"data": {"ohlc": []}})

    async with _mock_client(handler) as client:
        result = await fetch_bitstamp_btcusd_ohlcv(client, now=NOW)

    assert result.status is ReadStatus.PROVENANCE_FAILURE
    assert result.bars == ()
    assert "pair" in result.message


@pytest.mark.asyncio
async def test_inconsistent_ohlc_is_provenance_failure():
    def handler(_request):
        return httpx.Response(
            200,
            json=_payload(_candle(NOW - 60, open_="100", high="101", low="99", close="102")),
        )

    async with _mock_client(handler) as client:
        result = await fetch_bitstamp_btcusd_ohlcv(client, now=NOW)

    assert result.status is ReadStatus.PROVENANCE_FAILURE
    assert "inconsistent" in result.message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        _payload(_candle(NOW - 120), _candle(NOW - 120)),
        _payload(_candle(NOW - 60), _candle(NOW - 120)),
        _payload(_candle(NOW + 1)),
        _payload(_candle(NOW - 60, volume="NaN")),
        _payload(_candle(NOW - 60), pair="ETH/USD"),
    ],
)
async def test_invalid_timestamp_values_and_wrong_pair_fail_provenance(payload):
    def handler(_request):
        return httpx.Response(200, json=payload)

    async with _mock_client(handler) as client:
        result = await fetch_bitstamp_btcusd_ohlcv(client, now=NOW)

    assert result.status is ReadStatus.PROVENANCE_FAILURE


@pytest.mark.asyncio
async def test_non_success_http_response_is_data_unavailable():
    def handler(_request):
        return httpx.Response(503)

    async with _mock_client(handler) as client:
        result = await fetch_bitstamp_btcusd_ohlcv(client, now=NOW)

    assert result.status is ReadStatus.DATA_UNAVAILABLE


def test_invalid_freshness_limit_is_rejected_before_request():
    class NeverUsedClient:
        async def get(self, *_args, **_kwargs):
            raise AssertionError("client must not be called")

    with pytest.raises(ValueError, match="positive integer"):
        asyncio.run(fetch_bitstamp_btcusd_ohlcv(NeverUsedClient(), now=NOW, freshness_limit_seconds=0))

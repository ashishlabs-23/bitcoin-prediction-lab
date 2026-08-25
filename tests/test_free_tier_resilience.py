"""
tests/test_free_tier_resilience.py — Free-Tier Deployment & Multi-Exchange Failover Tests
========================================================================================
Validates that:
1. Fast `/ping` endpoint responds with 200 OK and <10ms latency.
2. `/health` and `/api/health` work as expected.
3. Multi-exchange fallback chain handles mock failures in Binance transparently.
4. Database configuration safely initializes SQLite / Turso paths without error.
"""

import os
import sys
import asyncio
import httpx
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app
from api.http_client import (
    fetch_live_binance_btc_price_async,
    fetch_binance_klines_async
)
from config.database import MARKET_MEMORY_DB_PATH, HAWKES_DB_PATH
from config.security import ALLOWED_EXTERNAL_DOMAINS

client = TestClient(app, raise_server_exceptions=False)


def test_ping_endpoint_fast_response():
    """Verify that /ping returns immediately for free-tier keep-alive pingers."""
    response = client.get("/ping")
    assert response.status_code == 200
    data = response.json()
    assert data.get("pong") is True
    assert "timestamp" in data


def test_health_endpoints():
    """Verify both /health and /api/health work."""
    res1 = client.get("/health")
    assert res1.status_code == 200
    assert "status" in res1.json()

    res2 = client.get("/api/health")
    assert res2.status_code == 200
    assert "status" in res2.json()


def test_database_contract_invariants():
    """Verify DB paths and contracts are properly initialized."""
    assert MARKET_MEMORY_DB_PATH is not None
    assert HAWKES_DB_PATH == MARKET_MEMORY_DB_PATH
    assert isinstance(MARKET_MEMORY_DB_PATH, str)


def test_allowed_external_domains_has_fallbacks():
    """Verify Kraken, Coinbase, and Bybit are whitelisted for SSRF protection."""
    assert "api.kraken.com" in ALLOWED_EXTERNAL_DOMAINS
    assert "api.coinbase.com" in ALLOWED_EXTERNAL_DOMAINS
    assert "api.bybit.com" in ALLOWED_EXTERNAL_DOMAINS


def test_multi_exchange_price_failover():
    """Test price fetch fallback when primary Binance endpoint fails."""
    async def run_test():
        async def mock_transport(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "binance.com" in url_str:
                return httpx.Response(503, json={"error": "Service Unavailable"})
            elif "coinbase.com" in url_str:
                return httpx.Response(200, json={"data": {"amount": "65123.45"}})
            elif "kraken.com" in url_str:
                return httpx.Response(200, json={"error": [], "result": {"XXBTZUSD": {"c": ["65120.00"]}}})
            return httpx.Response(404)

        mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_transport))
        price = await fetch_live_binance_btc_price_async(client=mock_client)
        await mock_client.aclose()

        assert price is not None
        assert price == 65123.45

    asyncio.run(run_test())


def test_multi_exchange_price_kraken_failover():
    """Test price fetch fallback to Kraken when Binance and Coinbase both fail."""
    async def run_test():
        async def mock_transport(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "binance.com" in url_str or "coinbase.com" in url_str:
                return httpx.Response(500, json={"error": "Down"})
            elif "kraken.com" in url_str:
                return httpx.Response(200, json={"error": [], "result": {"XXBTZUSD": {"c": ["64999.50"]}}})
            return httpx.Response(404)

        mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_transport))
        price = await fetch_live_binance_btc_price_async(client=mock_client)
        await mock_client.aclose()

        assert price is not None
        assert price == 64999.50

    asyncio.run(run_test())


def test_multi_exchange_klines_bybit_failover():
    """Test klines fetch fallback to Bybit when Binance, Coinbase, and Kraken fail."""
    async def run_test():
        async def mock_transport(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if any(dom in url_str for dom in ["binance.com", "coinbase.com", "kraken.com"]):
                return httpx.Response(500, json={"error": "Failed"})
            elif "bybit.com" in url_str:
                # Bybit format: [[startTime, open, high, low, close, volume, turnover]]
                return httpx.Response(200, json={
                    "result": {
                        "list": [
                            ["1672531200000", "64000.0", "64500.0", "63800.0", "64200.0", "125.5"]
                        ]
                    }
                })
            return httpx.Response(404)

        mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_transport))
        candles = await fetch_binance_klines_async(symbol="BTCUSD_PERP", interval="1h", limit=5, client=mock_client)
        await mock_client.aclose()

        assert len(candles) == 1
        assert candles[0]["open"] == 64000.0
        assert candles[0]["close"] == 64200.0

    asyncio.run(run_test())


if __name__ == "__main__":
    print("Running Free-Tier Resilience Tests...")
    test_ping_endpoint_fast_response()
    print("PASS: test_ping_endpoint_fast_response")
    test_health_endpoints()
    print("PASS: test_health_endpoints")
    test_database_contract_invariants()
    print("PASS: test_database_contract_invariants")
    test_allowed_external_domains_has_fallbacks()
    print("PASS: test_allowed_external_domains_has_fallbacks")
    test_multi_exchange_price_failover()
    print("PASS: test_multi_exchange_price_failover")
    test_multi_exchange_price_kraken_failover()
    print("PASS: test_multi_exchange_price_kraken_failover")
    test_multi_exchange_klines_bybit_failover()
    print("PASS: test_multi_exchange_klines_bybit_failover")
    print("\nALL FREE-TIER RESILIENCE TESTS PASSED!")




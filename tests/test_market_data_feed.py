"""
tests/test_market_data_feed.py — Phase 4 Market Data Feed & Data Quality Contract Tests
========================================================================================
Validates:
1. Coinbase L2 order book snapshot initialization and metric calculation.
2. Microprice and depth imbalance correctness.
3. Order Flow Imbalance (OFI) computation.
4. Sequence gap detection: out-of-order updates invalidate book with DISCONTINUOUS status.
5. Stale-feed detection when timeout threshold is exceeded.
6. Derivatives isolation: Binance funding and open interest marked DERIVATIVE, not mixed with spot.
7. Fail-closed contract: malformed payload returns INVALID without substitute numbers.
"""

import time
import pytest
from datetime import datetime, timezone

from engine.market_data_feed import (
    CoinbaseL2OrderBook,
    BinanceDerivativesCollector,
    MarketDataObservation,
    FreshnessStatus,
    InstrumentFamily
)


def test_coinbase_l2_snapshot_initialization():
    """Validates book initialization and metric calculation from L2 snapshot."""
    book = CoinbaseL2OrderBook(stale_timeout_sec=5.0)

    bids = [["68000.0", "1.5"], ["67990.0", "3.0"], ["67980.0", "2.0"]]
    asks = [["68010.0", "2.5"], ["68020.0", "1.0"], ["68030.0", "4.0"]]

    obs = book.initialize_snapshot(bids=bids, asks=asks, sequence_id=100)

    assert obs.source == "coinbase"
    assert obs.instrument == "BTC-USD"
    assert obs.instrument_family == InstrumentFamily.SPOT
    assert obs.freshness_status == FreshnessStatus.FRESH
    assert obs.sequence_id == 100

    payload = obs.payload
    assert payload["best_bid"] == 68000.0
    assert payload["best_ask"] == 68010.0
    assert payload["mid_price"] == 68005.0
    assert payload["spread"] == 10.0

    # Microprice: (1.5 * 68010 + 2.5 * 68000) / (1.5 + 2.5) = (102015 + 170000) / 4 = 272015 / 4 = 68003.75
    assert payload["microprice"] == 68003.75


def test_coinbase_l2_sequence_continuity_and_gap_invalidation():
    """Validates sequential delta application and gap detection invalidation."""
    book = CoinbaseL2OrderBook(stale_timeout_sec=5.0)

    # Initialize
    bids = [["68000.0", "1.0"]]
    asks = [["68010.0", "1.0"]]
    book.initialize_snapshot(bids=bids, asks=asks, sequence_id=100)
    assert book.is_initialized is True

    # 1. Sequential update: sequence 101 -> PASS
    obs101 = book.apply_delta(side="buy", price=68005.0, size=2.0, sequence_id=101)
    assert obs101.freshness_status == FreshnessStatus.FRESH
    assert obs101.payload["best_bid"] == 68005.0
    assert book.last_sequence == 101

    # 2. Sequence gap: expected 102, got 105 -> INVALIDATE & DISCONTINUOUS
    obs_gap = book.apply_delta(side="sell", price=68015.0, size=1.0, sequence_id=105)
    assert obs_gap.freshness_status == FreshnessStatus.DISCONTINUOUS
    assert "Sequence continuity gap" in obs_gap.error_state
    assert book.is_initialized is False
    assert len(book.bids) == 0
    assert len(book.asks) == 0


def test_coinbase_l2_stale_detection():
    """Validates that a book with no recent updates is marked STALE."""
    book = CoinbaseL2OrderBook(stale_timeout_sec=0.1)

    bids = [["68000.0", "1.0"]]
    asks = [["68010.0", "1.0"]]
    book.initialize_snapshot(bids=bids, asks=asks, sequence_id=50)

    assert book.check_freshness() == FreshnessStatus.FRESH
    time.sleep(0.15)
    assert book.check_freshness() == FreshnessStatus.STALE


def test_coinbase_l2_order_flow_imbalance():
    """Validates Order Flow Imbalance (OFI) calculation at the touch."""
    book = CoinbaseL2OrderBook()

    # Initial state: Bid 68000 (1.0), Ask 68010 (1.0)
    book.initialize_snapshot(bids=[["68000.0", "1.0"]], asks=[["68010.0", "1.0"]], sequence_id=1)

    # Bid increases in size at same price: delta_bid = +1.5 -> OFI = +1.5
    book.apply_delta(side="buy", price=68000.0, size=2.5, sequence_id=2)
    ofi = book.compute_ofi()
    assert ofi == 1.5


def test_binance_derivatives_isolation_and_contracts():
    """Validates that derivatives are isolated from spot and contract fields are typed."""
    collector = BinanceDerivativesCollector()

    # 1. Funding rate
    funding_raw = {
        "symbol": "BTCUSDT",
        "lastFundingRate": "0.0001",
        "markPrice": "68050.50",
        "indexPrice": "68045.20",
        "time": 1724000000000
    }
    obs_funding = collector.process_funding_rate(funding_raw)
    assert obs_funding.instrument_family == InstrumentFamily.DERIVATIVE
    assert obs_funding.instrument == "BTCUSDT"
    assert obs_funding.payload["funding_rate"] == 0.0001
    assert obs_funding.payload["funding_rate_bps"] == 1.0
    assert obs_funding.payload["annualized_basis_pct"] == 10.95
    assert obs_funding.freshness_status == FreshnessStatus.FRESH

    # 2. Open interest
    oi_raw = {
        "symbol": "BTCUSDT",
        "openInterest": "45250.75",
        "time": 1724000000000
    }
    obs_oi = collector.process_open_interest(oi_raw, previous_oi=45000.0)
    assert obs_oi.instrument_family == InstrumentFamily.DERIVATIVE
    assert obs_oi.payload["open_interest_contracts"] == 45250.75
    assert obs_oi.payload["open_interest_delta"] == 250.75
    assert obs_oi.payload["has_delta"] is True


def test_data_quality_fail_closed_on_malformed_payload():
    """Validates fail-closed contract: malformed payloads yield INVALID without synthetic fallback."""
    collector = BinanceDerivativesCollector()

    # Missing critical fields
    bad_funding = {"invalid_field": 123}
    obs = collector.process_funding_rate(bad_funding)
    assert obs.freshness_status == FreshnessStatus.INVALID
    assert "Malformed" in obs.error_state
    assert obs.payload == {}

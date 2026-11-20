"""
tests/test_v32_66_provider_contract.py — Provider-Neutral Contract Test Suite
=============================================================================
Validates that engine/market_data_adapters/provider_contract.py strictly enforces:
1. Valid candle normalization, type casting, and rounding.
2. Mathematical invariants: finite positive prices, high >= max(open, close),
   low <= min(open, close), volume >= 0.
3. Timestamp deduplication and chronological ordering.
4. Detection of missing intervals (gaps) without synthetic fill or interpolation.
5. Staleness detection (> 7,200s threshold).
6. Exclusion of forming/incomplete candles at UTC boundary.
7. Support for both Aggregated Global Benchmark and Venue-Specific Spot price basis.
8. Fail-closed pre-transport network guard (ExternalNetworkBlockedError).
"""

import pytest
import time
from typing import List, Dict, Any, Optional

from engine.market_data_adapters.provider_contract import (
    BaseMarketDataProvider,
    PriceBasisType,
    CandleSemantics,
    SupportedInterval,
    ProviderAttribution,
    CandleBar,
    ProviderContinuityReport,
)
from engine.data_mode import (
    DataMode,
    get_data_mode,
    ExternalNetworkBlockedError,
)


class MockFixtureProvider(BaseMarketDataProvider):
    """Deterministic in-memory mock provider conforming to BaseMarketDataProvider."""

    def __init__(
        self,
        provider_id: str = "mock_coingecko",
        price_basis: PriceBasisType = PriceBasisType.AGGREGATED_GLOBAL_BENCHMARK,
        stale_threshold_seconds: float = 7200.0,
    ):
        attribution = ProviderAttribution(
            provider_id=provider_id,
            display_name="Mock Benchmark",
            attribution_text="Data from Mock Benchmark",
            attribution_url="https://mock.example.com",
            requires_visual_badge=True,
            raw_redistribution_permitted=False,
        )
        super().__init__(
            provider_id=provider_id,
            price_basis=price_basis,
            attribution=attribution,
            max_requests_per_minute=60,
            stale_threshold_seconds=stale_threshold_seconds,
        )
        self.mock_raw_data: List[Dict[str, Any]] = []

    async def fetch_historical_candles_raw(
        self,
        symbol: str,
        interval: SupportedInterval,
        limit: int = 168,
        end_epoch_utc: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        return self.mock_raw_data[:limit]


def test_01_valid_candle_normalization_and_formatting():
    """Validates proper parsing, dataclass creation, and to_dict formatting."""
    provider = MockFixtureProvider()
    now_epoch = int(time.time())
    aligned_t = ((now_epoch - 7200) // 3600) * 3600

    raw = [
        {"time": aligned_t, "open": 65000.1234, "high": 65500.5678, "low": 64800.0, "close": 65200.999, "volume": 12.3456789}
    ]
    bars = provider._normalize_and_validate(raw, SupportedInterval.H1)
    assert len(bars) == 1
    bar = bars[0]
    assert isinstance(bar, CandleBar)
    assert bar.time == aligned_t
    assert bar.open == 65000.1234
    assert bar.high == 65500.5678
    assert bar.low == 64800.0
    assert bar.close == 65200.999
    assert bar.volume == 12.3456789

    d = bar.to_dict()
    assert d["time"] == aligned_t
    assert d["open"] == 65000.12
    assert d["high"] == 65500.57
    assert d["low"] == 64800.00
    assert d["close"] == 65201.00
    assert d["volume"] == 12.345679


def test_02_mathematical_invariants_enforced():
    """Validates that non-physical candles (high < low, high < open, negative price) are rejected."""
    provider = MockFixtureProvider()
    now_epoch = int(time.time())
    base_t = ((now_epoch - 36000) // 3600) * 3600

    invalid_rows = [
        # high < max(open, close)
        {"time": base_t, "open": 65000.0, "high": 64900.0, "low": 64000.0, "close": 64500.0, "volume": 1.0},
        # low > min(open, close)
        {"time": base_t + 3600, "open": 65000.0, "high": 66000.0, "low": 65500.0, "close": 64500.0, "volume": 1.0},
        # negative price
        {"time": base_t + 7200, "open": -100.0, "high": 66000.0, "low": 64000.0, "close": 65000.0, "volume": 1.0},
        # negative volume
        {"time": base_t + 10800, "open": 65000.0, "high": 66000.0, "low": 64000.0, "close": 65000.0, "volume": -5.0},
        # unaligned timestamp
        {"time": base_t + 14400 + 45, "open": 65000.0, "high": 66000.0, "low": 64000.0, "close": 65000.0, "volume": 1.0},
    ]

    bars = provider._normalize_and_validate(invalid_rows, SupportedInterval.H1)
    assert len(bars) == 0, f"Expected 0 valid bars, got {len(bars)}"


def test_03_deduplication_and_sorting():
    """Validates that out-of-order candles are sorted chronologically and duplicates resolved."""
    provider = MockFixtureProvider()
    now_epoch = int(time.time())
    t0 = ((now_epoch - 20000) // 3600) * 3600
    t1 = t0 + 3600
    t2 = t0 + 7200

    raw = [
        {"time": t2, "open": 66000.0, "high": 67000.0, "low": 65000.0, "close": 66500.0, "volume": 1.0},
        {"time": t0, "open": 64000.0, "high": 65000.0, "low": 63000.0, "close": 64500.0, "volume": 1.0},
        {"time": t1, "open": 65000.0, "high": 66000.0, "low": 64000.0, "close": 65500.0, "volume": 1.0},
        # Duplicate t1 with updated close
        {"time": t1, "open": 65000.0, "high": 66100.0, "low": 64000.0, "close": 65800.0, "volume": 2.0},
    ]

    bars = provider._normalize_and_validate(raw, SupportedInterval.H1)
    assert len(bars) == 3
    assert [b.time for b in bars] == [t0, t1, t2]
    # Invariant: duplicate t1 was overwritten with latest row
    assert bars[1].close == 65800.0


def test_04_continuity_detection_without_synthetic_fill():
    """Validates that missing intervals are recorded honestly without fabricating data."""
    provider = MockFixtureProvider()
    now_epoch = int(time.time())
    t0 = ((now_epoch - 30000) // 3600) * 3600
    t1 = t0 + 3600
    t3 = t0 + 3 * 3600  # Missing t0 + 2*3600
    t6 = t0 + 6 * 3600  # Missing t0 + 4*3600, t0 + 5*3600

    bars = [
        CandleBar(time=t0, open=60000, high=61000, low=59000, close=60500, volume=10),
        CandleBar(time=t1, open=60500, high=61500, low=60000, close=61000, volume=10),
        CandleBar(time=t3, open=61000, high=62000, low=60500, close=61500, volume=10),
        CandleBar(time=t6, open=61500, high=62500, low=61000, close=62000, volume=10),
    ]

    report = provider._audit_continuity(bars, SupportedInterval.H1)
    assert not report.is_continuous
    assert report.missing_intervals_count == 3
    expected_missing = [t0 + 2 * 3600, t0 + 4 * 3600, t0 + 5 * 3600]
    assert report.missing_intervals == expected_missing
    # Invariant: original bars count unchanged (no fake interpolation)
    assert len(bars) == 4


def test_05_staleness_detection():
    """Validates that feeds exceeding the stale threshold (7,200s) are flagged STALE."""
    provider = MockFixtureProvider(stale_threshold_seconds=7200.0)
    now_epoch = int(time.time())
    stale_t = now_epoch - 15000  # More than 4 hours old

    bars = [
        CandleBar(time=stale_t, open=60000, high=61000, low=59000, close=60500, volume=10),
    ]

    report = provider._audit_continuity(bars, SupportedInterval.H1)
    assert report.is_stale
    assert report.stale_seconds > 7200.0


def test_06_incomplete_forming_candle_exclusion():
    """Validates that a candle whose end time extends past current UTC time is excluded."""
    provider = MockFixtureProvider()
    now_epoch = int(time.time())
    current_hour_start = (now_epoch // 3600) * 3600
    past_hour_start = current_hour_start - 3600

    raw = [
        {"time": past_hour_start, "open": 64000.0, "high": 65000.0, "low": 63000.0, "close": 64500.0, "volume": 1.0},
        # Forming candle (current incomplete hour)
        {"time": current_hour_start, "open": 64500.0, "high": 65500.0, "low": 64000.0, "close": 65000.0, "volume": 0.5},
    ]

    bars = provider._normalize_and_validate(raw, SupportedInterval.H1)
    # The forming candle must be excluded because current_hour_start + 3600 > closed_cutoff
    assert len(bars) == 1
    assert bars[0].time == past_hour_start


def test_07_price_basis_classification():
    """Validates proper enumeration of price basis across benchmark vs venue spot."""
    benchmark_prov = MockFixtureProvider(price_basis=PriceBasisType.AGGREGATED_GLOBAL_BENCHMARK)
    assert benchmark_prov.price_basis == PriceBasisType.AGGREGATED_GLOBAL_BENCHMARK
    assert benchmark_prov.price_basis.value == "AGGREGATED_GLOBAL_BENCHMARK"

    spot_prov = MockFixtureProvider(price_basis=PriceBasisType.VENUE_SPECIFIC_SPOT_ORDERBOOK)
    assert spot_prov.price_basis == PriceBasisType.VENUE_SPECIFIC_SPOT_ORDERBOOK
    assert spot_prov.price_basis.value == "VENUE_SPECIFIC_SPOT_ORDERBOOK"


@pytest.mark.asyncio
async def test_08_fail_closed_pre_transport_guard(monkeypatch):
    """Validates that get_candles() raises ExternalNetworkBlockedError when network transport is disabled."""
    monkeypatch.setenv("DATA_MODE", "fixture")
    provider = MockFixtureProvider()
    with pytest.raises(ExternalNetworkBlockedError) as exc_info:
        await provider.get_candles("BTC-USD", SupportedInterval.H1)
    assert "blocked" in str(exc_info.value).lower()
    assert "mock_coingecko.get_candles" in str(exc_info.value)

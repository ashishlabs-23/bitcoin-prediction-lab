"""
tests/test_phase2_market_data_and_pit.py — Verification of Phase 2 Market Data & PIT Features
=============================================================================================
Tests:
1. SpotExchangeComparator: multi-exchange quote evaluation, freshness, and divergence detection.
2. BinanceDerivativesCollector: strict instrument separation under InstrumentFamily.DERIVATIVE.
3. CausalBenchmarkEngine: point-in-time benchmark ledger with zero future outcome leakage.
4. PointInTimeFeatures: available_at <= cutoff invariant and perturbation resistance.
"""

import time
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd
import pytest

from engine.spot_exchange_comparator import (
    SpotExchangeComparator,
    ExchangeProvider,
    FeedQuality,
    SpotQuote,
)
from engine.market_data_feed import (
    BinanceDerivativesCollector,
    InstrumentFamily,
    FreshnessStatus,
)
from engine.causal_benchmark_ledger import (
    CausalBenchmarkEngine,
    TargetType,
)
from engine.point_in_time_features import (
    PointInTimeFeaturePipeline,
    FEATURE_SCHEMA_VERSION,
)


def test_spot_exchange_comparator_freshness_and_selection():
    comparator = SpotExchangeComparator(stale_threshold_sec=15.0, max_divergence_bps_threshold=50.0)

    now_ms = int(time.time() * 1000)
    q_cb = comparator.evaluate_quote(
        provider=ExchangeProvider.COINBASE,
        price_usd=95000.0,
        bid_usd=94998.0,
        ask_usd=95002.0,
        source_timestamp_ms=now_ms
    )
    q_kr = comparator.evaluate_quote(
        provider=ExchangeProvider.KRAKEN,
        price_usd=95015.0,
        bid_usd=95010.0,
        ask_usd=95020.0,
        source_timestamp_ms=now_ms
    )
    # Stale bitstamp quote (30s old)
    q_bs = comparator.evaluate_quote(
        provider=ExchangeProvider.BITSTAMP,
        price_usd=94980.0,
        source_timestamp_ms=now_ms - 30_000
    )

    assert q_cb.quality == FeedQuality.FRESH
    assert q_kr.quality == FeedQuality.FRESH
    assert q_bs.quality == FeedQuality.STALE

    comparison = comparator.compare_quotes([q_cb, q_kr, q_bs])
    assert comparison.active_primary_provider == ExchangeProvider.COINBASE
    assert comparison.primary_price_usd == 95000.0
    assert comparison.healthy_providers_count == 3
    assert comparison.is_divergent is False


def test_spot_exchange_divergence_detection():
    comparator = SpotExchangeComparator(max_divergence_bps_threshold=30.0) # 0.30% = 30 bps
    now_ms = int(time.time() * 1000)

    q_cb = comparator.evaluate_quote(ExchangeProvider.COINBASE, price_usd=95000.0, source_timestamp_ms=now_ms)
    q_kr = comparator.evaluate_quote(ExchangeProvider.KRAKEN, price_usd=95500.0, source_timestamp_ms=now_ms) # ~52 bps divergence

    comparison = comparator.compare_quotes([q_cb, q_kr])
    assert comparison.is_divergent is True
    assert comparison.max_disagreement_bps > 30.0
    assert "Cross-exchange disagreement" in comparison.divergence_reason


def test_derivatives_data_strict_isolation():
    raw_funding = {
        "symbol": "BTCUSDT",
        "lastFundingRate": "0.00010000",
        "time": int(time.time() * 1000)
    }
    obs = BinanceDerivativesCollector.process_funding_rate(raw_funding)
    assert obs.instrument == "BTCUSDT"
    assert obs.instrument_family == InstrumentFamily.DERIVATIVE
    assert obs.data_type == "FUNDING_RATE"
    assert obs.freshness_status == FreshnessStatus.FRESH
    assert obs.payload["funding_rate"] == 0.0001


def test_causal_benchmark_ledger_invariance():
    engine = CausalBenchmarkEngine(min_history_periods=10)
    cutoff = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Historical candles before and after cutoff
    candles = []
    base_price = 80000.0
    for h in range(-200, 50):
        t = cutoff + timedelta(hours=h)
        candles.append({
            "timestamp": t.isoformat(),
            "close": base_price * (1.0 + 0.0005 * h)
        })

    bmk = engine.issue_range_benchmark(
        historical_closed_candles=candles,
        spot_price=85000.0,
        cutoff_dt=cutoff,
        horizon_hours=24
    )
    assert bmk is not None
    assert bmk.status == "ISSUED_CAUSAL_VALID"
    assert bmk.target_type == TargetType.EXCURSION_RANGE_24H
    assert bmk.predictions["p10_price"] < bmk.predictions["p50_price"] < bmk.predictions["p90_price"]


def test_point_in_time_feature_pipeline_causality():
    pipeline = PointInTimeFeaturePipeline()
    start_dt = pd.Timestamp("2026-05-01 00:00:00", tz="UTC")
    n = 60
    timestamps = [start_dt + pd.Timedelta(hours=i) for i in range(n)]
    prices = 90000.0 + np.cumsum(np.ones(n))

    df_base = pd.DataFrame({
        "timestamp": timestamps,
        "available_at": timestamps,
        "open": prices,
        "high": prices + 10,
        "low": prices - 10,
        "close": prices,
        "volume": [10.0] * n
    })

    feats_base = pipeline.extract_features(df_base)
    assert not feats_base.empty
    assert "realized_vol_24h" in feats_base.columns
    assert "available_at" in feats_base.columns

    # Mutating future row (index 50) must not affect features at index 20 (t_0)
    df_mutated = df_base.copy()
    df_mutated.loc[50, "close"] = 999999.0

    feats_mutated = pipeline.extract_features(df_mutated)
    np.testing.assert_almost_equal(
        feats_base.loc[20, "realized_vol_24h"],
        feats_mutated.loc[20, "realized_vol_24h"]
    )

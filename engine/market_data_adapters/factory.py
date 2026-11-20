"""
engine/market_data_adapters/factory.py — Provider Adapter Factory & Feature Gate
================================================================================
Controls initialization, feature flag enforcement, and routing to concrete
market data provider adapters.
"""

import os
from typing import Optional

from engine.market_data_adapters.base import (
    IMarketDataProviderAdapter,
    NormalizedCandle,
    NormalizedCandleResponse,
    FeedFreshnessStatus,
    FeedDiagnostics,
    VenueType,
)
from engine.market_data_adapters.bitstamp import BitstampAdapter
from engine.market_data_adapters.coingecko import CoinGeckoAdapter


def is_provider_adapter_enabled() -> bool:
    """
    Returns True only if the feature flag BTC_ENABLE_PROVIDER_ADAPTER is explicitly set to true.
    Defaults to False to prevent accidental unverified live calls.
    """
    return os.environ.get("BTC_ENABLE_PROVIDER_ADAPTER", "false").lower() == "true"


def get_market_data_adapter(provider_id: str = "bitstamp") -> IMarketDataProviderAdapter:
    """
    Instantiates the requested provider adapter.
    """
    pid = provider_id.lower().strip()
    if pid in ("bitstamp", "bitstamp_dla"):
        return BitstampAdapter()
    elif pid in ("coingecko", "coingecko_api"):
        return CoinGeckoAdapter()
    else:
        raise ValueError(f"Unknown or unsupported market data provider: '{provider_id}'. Supported: 'bitstamp', 'coingecko'.")


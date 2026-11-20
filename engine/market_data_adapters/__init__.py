"""
engine/market_data_adapters — Normalized Market Data Adapter Subsystem
"""

from engine.market_data_adapters.base import (
    IMarketDataProviderAdapter,
    NormalizedCandle,
    NormalizedCandleResponse,
    FeedFreshnessStatus,
    FeedDiagnostics,
    VenueType,
)
from engine.market_data_adapters.bitstamp import BitstampAdapter, BITSTAMP_INTERVAL_MAP
from engine.market_data_adapters.coingecko import CoinGeckoAdapter, COINGECKO_INTERVAL_MAP
from engine.market_data_adapters.factory import (
    get_market_data_adapter,
    is_provider_adapter_enabled,
)

__all__ = [
    "IMarketDataProviderAdapter",
    "NormalizedCandle",
    "NormalizedCandleResponse",
    "FeedFreshnessStatus",
    "FeedDiagnostics",
    "VenueType",
    "BitstampAdapter",
    "BITSTAMP_INTERVAL_MAP",
    "CoinGeckoAdapter",
    "COINGECKO_INTERVAL_MAP",
    "get_market_data_adapter",
    "is_provider_adapter_enabled",
]


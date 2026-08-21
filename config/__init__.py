# config/__init__.py — Makes config/ a Python package
# Re-exports canonical contracts for convenient import.

from config.paths import (
    PROJECT_ROOT,
    DATA_DIR,
    DATA_RAW_DIR,
    DATA_PROCESSED_DIR,
    RESULTS_DIR,
    RESEARCH_RESULTS_DIR,
    MODEL_REGISTRY_DIR,
    GENOME_DIR,
)

from config.database import (
    MARKET_MEMORY_DB_PATH,
    HAWKES_DB_PATH,
    LEGACY_HAWKES_DB_PATH,
)

SYMBOL: str = "BTCUSD"
EXCHANGE: str = "binance"

__all__ = [
    "PROJECT_ROOT",
    "DATA_DIR",
    "DATA_RAW_DIR",
    "DATA_PROCESSED_DIR",
    "RESULTS_DIR",
    "RESEARCH_RESULTS_DIR",
    "MODEL_REGISTRY_DIR",
    "GENOME_DIR",
    "MARKET_MEMORY_DB_PATH",
    "HAWKES_DB_PATH",
    "LEGACY_HAWKES_DB_PATH",
    "SYMBOL",
    "EXCHANGE",
]

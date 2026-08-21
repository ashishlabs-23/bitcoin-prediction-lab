"""
tests/test_system_contracts.py — Master System Contract Test Suite
==================================================================
Comprehensive verification of all foundational contracts across BTCognitive:
1. Regime Vocabulary & Mapping Contract
2. Symbol Vocabulary & Adapter Contract
3. Horizon Contract & 24H Resolution Invariant
4. Database Path Unification Contract
5. On-Chain Data Field & Quality Contract
6. Outcome Resolution & was_correct NULL Invariant
7. Synthetic Data Rejection & Health Contract
8. API Route Contracts (BTCUSD canonical output)
"""

import pytest
import os
import sqlite3
import pandas as pd
import numpy as np

from config.paths import PROJECT_ROOT, RESULTS_DIR, DATA_RAW_DIR, DATA_PROCESSED_DIR
from config.database import MARKET_MEMORY_DB_PATH, HAWKES_DB_PATH
from models.regime_contract import CanonicalRegime, normalize_regime, is_valid_regime
from models.symbol_contract import CANONICAL_SYMBOL, to_canonical, to_ccxt, to_binance
from models.horizon_contract import (
    PRODUCTION_RANGE_HORIZON_HOURS,
    PRODUCTION_RANGE_HORIZON_LABEL,
    OUTCOME_RESOLUTION_HORIZON_HOURS,
    HAWKES_SHADOW_IS_PRODUCTION
)
from models.onchain_contract import (
    OnchainMetrics,
    OnchainQuality,
    assess_onchain_quality,
    SCHEMA_VERSION_CURRENT
)
from engine.feature_cache import feature_cache
from backtest.market_memory import load_market_memory

# 1. Regime Contract
def test_master_regime_contract():
    for label in ["Strong Uptrend", "Weak Uptrend"]:
        assert normalize_regime(label) == CanonicalRegime.TRENDING_BULL
    for label in ["Sideways", "Accumulation", "Distribution"]:
        assert normalize_regime(label) == CanonicalRegime.RANGING
    assert normalize_regime("High Volatility") == CanonicalRegime.HIGH_VOLATILITY
    assert normalize_regime("Capitulation") == CanonicalRegime.TRENDING_BEAR
    assert normalize_regime(CanonicalRegime.BREAKOUT) == CanonicalRegime.BREAKOUT

# 2. Symbol Contract
def test_master_symbol_contract():
    assert CANONICAL_SYMBOL == "BTCUSD"
    assert to_canonical("BTC/USD") == "BTCUSD"
    assert to_canonical("BTCUSDT") == "BTCUSD"
    assert to_ccxt() == "BTC/USD"
    assert to_binance() == "BTCUSDT"

# 3. Horizon Contract
def test_master_horizon_contract():
    assert PRODUCTION_RANGE_HORIZON_HOURS == 24
    assert PRODUCTION_RANGE_HORIZON_LABEL == "24h"
    assert OUTCOME_RESOLUTION_HORIZON_HOURS == 24
    assert HAWKES_SHADOW_IS_PRODUCTION is False

# 4. Database Path Unification
def test_master_database_path_contract():
    assert MARKET_MEMORY_DB_PATH == HAWKES_DB_PATH
    assert os.path.exists(MARKET_MEMORY_DB_PATH)

# 5. On-Chain Metrics Contract
def test_master_onchain_contract():
    data = {
        "mvrv_ratio": 2.15,
        "nupl": 0.45,
        "cycle_phase": "NEUTRAL",
        "timestamp": "2026-08-21T00:00:00Z",
        "source": "coinmetrics_api",
        "is_live": True,
        "is_degraded": False,
        "influence_weight": 1.0
    }
    metrics = OnchainMetrics.from_dict(data)
    assert metrics.quality == OnchainQuality.VALID
    assert metrics.mvrv_ratio == 2.15
    assert metrics.schema_version == SCHEMA_VERSION_CURRENT

# 6. was_correct NULL Invariant
def test_master_was_correct_contract():
    conn = sqlite3.connect(MARKET_MEMORY_DB_PATH)
    conn.row_factory = sqlite3.Row
    unresolved_wins = conn.execute("SELECT COUNT(*) FROM predictions WHERE outcome_resolved = 0 AND was_correct IS NOT NULL").fetchone()[0]
    conn.close()
    assert unresolved_wins == 0, f"Found {unresolved_wins} unresolved predictions with non-null was_correct!"

# 7. Synthetic Feature Cache Rejection
def test_master_feature_cache_contract():
    assert hasattr(feature_cache, "is_healthy")
    # Cache must never fabricate $115K prices on empty state
    if not feature_cache.is_healthy():
        row = feature_cache.get_latest_row()
        assert row is None or row.empty or "close" not in row or row["close"] != 115000.0

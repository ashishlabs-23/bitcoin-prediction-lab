"""
tests/test_market_memory_path.py — Tests for Unified Database Path Resolution
=============================================================================
Verifies that:
- backtest.market_memory.DB_PATH resolves to config.database.MARKET_MEMORY_DB_PATH.
- engine.hawkes_shadow_session.DB_PATH resolves to config.database.MARKET_MEMORY_DB_PATH.
- Both production and shadow modules target the exact same SQLite database file.
"""

import os
from config.database import MARKET_MEMORY_DB_PATH, HAWKES_DB_PATH
from backtest.market_memory import DB_PATH as MEMORY_DB_PATH
from engine.hawkes_shadow_session import DB_PATH as SHADOW_DB_PATH

def test_database_paths_unified():
    assert MARKET_MEMORY_DB_PATH == HAWKES_DB_PATH
    assert os.path.abspath(MEMORY_DB_PATH) == os.path.abspath(MARKET_MEMORY_DB_PATH)
    assert os.path.abspath(SHADOW_DB_PATH) == os.path.abspath(MARKET_MEMORY_DB_PATH)
    assert os.path.exists(os.path.dirname(MARKET_MEMORY_DB_PATH))

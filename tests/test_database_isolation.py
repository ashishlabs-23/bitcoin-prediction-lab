"""
tests/test_database_isolation.py — Unit Tests for Database Isolation & Regression Safeguards
===========================================================================================
Workstream A: Clean Test and Database Isolation.

Verifies:
1. Session isolation: Tests write to an isolated temporary SQLite database.
2. Persistent DB protection: Mutating operations on `experiments/results/market_memory.db`
   are intercepted and blocked with RuntimeError during test runs.
3. Fail-closed access: Connections to the persistent DB are rejected.
4. Fresh DB isolation: The `fresh_test_db` fixture provides an independent, clean environment.
"""

import os
import sqlite3
import socket
import pytest
from config.database import DEFAULT_SQLITE_PATH, MARKET_MEMORY_DB_PATH
from backtest.market_memory import _get_db, DB_PATH
from engine.range_forecast_service import RangeForecastService
from engine.forecast_outcome_monitor import ForecastOutcomeMonitor


def test_session_isolation_active(test_db_path):
    """Verifies that the session test DB is isolated from the persistent production DB."""
    assert test_db_path is not None
    assert os.path.exists(test_db_path)
    assert os.path.abspath(test_db_path) != os.path.abspath(DEFAULT_SQLITE_PATH)
    assert os.path.abspath(MARKET_MEMORY_DB_PATH) == os.path.abspath(test_db_path)
    assert os.path.abspath(DB_PATH) == os.path.abspath(test_db_path)


def test_operational_stores_use_disposable_paths(test_db_path):
    from engine.arena_accounts import MEIE_DB_PATH
    from engine.feature_store import feature_store

    temp_root = os.path.realpath(os.path.dirname(test_db_path))
    assert os.path.commonpath((os.path.realpath(MEIE_DB_PATH), temp_root)) == temp_root
    assert os.path.commonpath((os.path.realpath(feature_store.db_path), temp_root)) == temp_root


def test_service_persistence_writes_to_isolated_db(test_db_path):
    """Verifies that RangeForecastService writes to the isolated test database."""
    svc = RangeForecastService()
    fc = svc.generate_forecast(current_price=95000.0, vol_24h=0.012)

    # Check that record exists in isolated test DB
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("SELECT current_price FROM range_forecasts WHERE forecast_id = ?", (fc.forecast_id,))
    row = cur.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == 95000.0

    assert row[0] == 95000.0


def test_canonical_database_connection_is_blocked():
    """
    Verifies that any attempted write operation against `experiments/results/market_memory.db`
    during test execution raises a RuntimeError safeguard.
    """
    with pytest.raises(RuntimeError, match="CANONICAL_DATABASE_ACCESS_BLOCKED"):
        sqlite3.connect(DEFAULT_SQLITE_PATH)


def test_external_network_and_protected_file_writes_are_blocked():
    protected_ledger = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data",
        "prospective_forecast_ledger.jsonl",
    )
    with pytest.raises(PermissionError, match="PROTECTED_FILE_WRITE_BLOCKED"):
        with open(protected_ledger, "a", encoding="utf-8"):
            pass

    with socket.socket() as sock, pytest.raises(RuntimeError, match="OFFLINE_NETWORK_BLOCKED"):
        sock.connect(("example.invalid", 443))


def test_fresh_test_db_fixture(fresh_test_db):
    """Verifies that `fresh_test_db` creates an independent, clean database."""
    conn = sqlite3.connect(fresh_test_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM range_forecasts;")
    count = cur.fetchone()[0]
    conn.close()

    assert count == 0

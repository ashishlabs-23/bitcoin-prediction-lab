"""
tests/test_database_isolation.py — Unit Tests for Database Isolation & Regression Safeguards
===========================================================================================
Workstream A: Clean Test and Database Isolation.

Verifies:
1. Session isolation: Tests write to an isolated temporary SQLite database.
2. Persistent DB protection: Mutating operations on `experiments/results/market_memory.db`
   are intercepted and blocked with RuntimeError during test runs.
3. Read safety: Reading from the persistent DB remains permitted for audit/verification.
4. Fresh DB isolation: The `fresh_test_db` fixture provides an independent, clean environment.
"""

import os
import sqlite3
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

    # Verify that the persistent production DB was NOT written to
    # Using read-only query to inspect persistent DB
    prod_conn = sqlite3.connect(DEFAULT_SQLITE_PATH)
    prod_cur = prod_conn.cursor()
    prod_cur.execute("SELECT current_price FROM range_forecasts WHERE forecast_id = ?", (fc.forecast_id,))
    prod_row = prod_cur.fetchone()
    prod_conn.close()

    assert prod_row is None, "Contamination failure! Record was written to persistent production database!"


def test_persistent_db_write_safeguard_triggers():
    """
    Verifies that any attempted write operation against `experiments/results/market_memory.db`
    during test execution raises a RuntimeError safeguard.
    """
    conn = sqlite3.connect(DEFAULT_SQLITE_PATH)
    try:
        with pytest.raises(RuntimeError, match="SAFETY VIOLATION.*attempted to mutate protected"):
            conn.execute("INSERT INTO predictions (prediction_id, timestamp, price, regime, raw_prob, calibrated_prob, decision, direction) VALUES ('leak_id', '2026-10-16', 100.0, 'sideways', 0.5, 0.5, 'HOLD', 'NEUTRAL');")
    finally:
        conn.close()


def test_fresh_test_db_fixture(fresh_test_db):
    """Verifies that `fresh_test_db` creates an independent, clean database."""
    conn = sqlite3.connect(fresh_test_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM range_forecasts;")
    count = cur.fetchone()[0]
    conn.close()

    assert count == 0

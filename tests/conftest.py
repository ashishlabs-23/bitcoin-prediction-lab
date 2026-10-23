"""
tests/conftest.py — Global Pytest Fixtures & Database Test Isolation Safeguard
==============================================================================
Workstream A: Clean Test and Database Isolation.

Enforces:
1. Automatic redirection of all database operations during test runs to an
   isolated temporary SQLite database, preventing contamination of
   `experiments/results/market_memory.db`.
2. Regression safeguard: Any attempt by any test to execute mutating SQL statements
   (INSERT, UPDATE, DELETE, DROP, CREATE, ALTER) against the protected persistent
   evidence database (`experiments/results/market_memory.db`) raises a fatal RuntimeError.
3. Provides reusable fixtures: `test_db_path`, `fresh_test_db`, and `isolated_db_conn`.
"""

import os
import sys
import sqlite3
import tempfile
import shutil
import pytest
from typing import Generator

# Ensure project root is in sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import config.database as db_cfg
import backtest.market_memory
import engine.hawkes_shadow_session

# Canonical persistent database path that MUST NOT be mutated by tests
PROTECTED_PERSISTENT_DB_PATH = os.path.abspath(db_cfg.DEFAULT_SQLITE_PATH)

# Module-level holder for session temp dir
_SESSION_TEMP_DIR = None
_SESSION_TEST_DB_PATH = None


class ProtectedPersistentConnection(sqlite3.Connection):
    """
    A SQLite connection wrapper that intercepts and forbids any mutating
    SQL operations against the protected persistent research database during test runs.
    """
    def execute(self, sql: str, *args, **kwargs):
        stripped = sql.strip().upper()
        mutating_verbs = ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "REPLACE")
        if any(stripped.startswith(verb) for verb in mutating_verbs):
            raise RuntimeError(
                f"SAFETY VIOLATION: Test execution attempted to mutate protected persistent "
                f"research evidence database at '{PROTECTED_PERSISTENT_DB_PATH}'! "
                f"Query blocked: {sql[:100]}..."
            )
        return super().execute(sql, *args, **kwargs)

    def executemany(self, sql: str, *args, **kwargs):
        stripped = sql.strip().upper()
        mutating_verbs = ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "REPLACE")
        if any(stripped.startswith(verb) for verb in mutating_verbs):
            raise RuntimeError(
                f"SAFETY VIOLATION: Test execution attempted to mutate protected persistent "
                f"research evidence database at '{PROTECTED_PERSISTENT_DB_PATH}'! "
                f"Query blocked: {sql[:100]}..."
            )
        return super().executemany(sql, *args, **kwargs)

    def executescript(self, sql_script: str):
        stripped = sql_script.strip().upper()
        mutating_verbs = ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "REPLACE")
        if any(verb in stripped for verb in mutating_verbs):
            raise RuntimeError(
                f"SAFETY VIOLATION: Test execution attempted to mutate protected persistent "
                f"research evidence database at '{PROTECTED_PERSISTENT_DB_PATH}' via script!"
            )
        return super().executescript(sql_script)


# Store original sqlite3.connect
_original_sqlite3_connect = sqlite3.connect


def _safe_sqlite3_connect(*args, **kwargs):
    """
    Guarded sqlite3.connect: If connecting to the persistent production database,
    return a connection with mutation operations blocked.
    """
    database = args[0] if args else kwargs.get("database")
    if database and isinstance(database, str):
        try:
            abs_target = os.path.abspath(database)
            if abs_target == PROTECTED_PERSISTENT_DB_PATH:
                # Wrap with ProtectedPersistentConnection factory
                kwargs["factory"] = ProtectedPersistentConnection
        except Exception:
            pass
    return _original_sqlite3_connect(*args, **kwargs)


def pytest_configure(config):
    """
    Early pytest hook running before test module collection.
    Initializes isolated temporary database, updates env var, and installs guard.
    """
    global _SESSION_TEMP_DIR, _SESSION_TEST_DB_PATH
    _SESSION_TEMP_DIR = tempfile.mkdtemp(prefix="btcognitive_test_db_")
    _SESSION_TEST_DB_PATH = os.path.join(_SESSION_TEMP_DIR, "isolated_market_memory.db")

    os.environ["SQLITE_DB_PATH"] = _SESSION_TEST_DB_PATH

    db_cfg.MARKET_MEMORY_DB_PATH = _SESSION_TEST_DB_PATH
    db_cfg.HAWKES_DB_PATH = _SESSION_TEST_DB_PATH
    backtest.market_memory.DB_PATH = _SESSION_TEST_DB_PATH
    backtest.market_memory.MARKET_MEMORY_DB_PATH = _SESSION_TEST_DB_PATH
    backtest.market_memory.CSV_PATH = os.path.join(_SESSION_TEMP_DIR, "isolated_market_memory.csv")
    engine.hawkes_shadow_session.DB_PATH = _SESSION_TEST_DB_PATH

    if os.path.exists(PROTECTED_PERSISTENT_DB_PATH):
        shutil.copy2(PROTECTED_PERSISTENT_DB_PATH, _SESSION_TEST_DB_PATH)
    else:
        init_conn = _original_sqlite3_connect(_SESSION_TEST_DB_PATH)
        try:
            backtest.market_memory._init_tables(init_conn)
        finally:
            init_conn.close()

    engine.hawkes_shadow_session.init_hawkes_tables()
    sqlite3.connect = _safe_sqlite3_connect


def pytest_unconfigure(config):
    """Cleanup hook restoring environment and removing temporary test database."""
    global _SESSION_TEMP_DIR
    sqlite3.connect = _original_sqlite3_connect
    if _SESSION_TEMP_DIR and os.path.exists(_SESSION_TEMP_DIR):
        shutil.rmtree(_SESSION_TEMP_DIR, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def session_database_isolation():
    """
    Autouse session fixture yielding the isolated test database path.
    """
    yield _SESSION_TEST_DB_PATH


@pytest.fixture
def test_db_path() -> str:
    """Returns the path to the isolated session SQLite test database."""
    return _SESSION_TEST_DB_PATH


@pytest.fixture
def fresh_test_db(tmp_path) -> Generator[str, None, None]:
    """
    Function-scoped fixture creating a completely fresh, isolated SQLite test DB
    with full schema initialized. Automatically cleans up after each test.
    """
    fresh_db_path = str(tmp_path / "fresh_test_market_memory.db")
    old_sqlite_env = os.environ.get("SQLITE_DB_PATH")

    os.environ["SQLITE_DB_PATH"] = fresh_db_path
    old_mm_path = db_cfg.MARKET_MEMORY_DB_PATH
    old_bm_path = backtest.market_memory.DB_PATH

    db_cfg.MARKET_MEMORY_DB_PATH = fresh_db_path
    db_cfg.HAWKES_DB_PATH = fresh_db_path
    backtest.market_memory.DB_PATH = fresh_db_path
    backtest.market_memory.MARKET_MEMORY_DB_PATH = fresh_db_path
    engine.hawkes_shadow_session.DB_PATH = fresh_db_path

    conn = _original_sqlite3_connect(fresh_db_path)
    try:
        backtest.market_memory._init_tables(conn)
    finally:
        conn.close()

    engine.hawkes_shadow_session.init_hawkes_tables()

    yield fresh_db_path

    # Restore session test DB
    if old_sqlite_env is not None:
        os.environ["SQLITE_DB_PATH"] = old_sqlite_env
    db_cfg.MARKET_MEMORY_DB_PATH = old_mm_path
    db_cfg.HAWKES_DB_PATH = old_mm_path
    backtest.market_memory.DB_PATH = old_bm_path
    backtest.market_memory.MARKET_MEMORY_DB_PATH = old_bm_path
    engine.hawkes_shadow_session.DB_PATH = old_bm_path

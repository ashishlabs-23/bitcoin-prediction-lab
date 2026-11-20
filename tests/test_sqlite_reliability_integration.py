"""
tests/test_sqlite_reliability_integration.py
=============================================
Genuine file-backed SQLite reliability and concurrency integration tests for V32.74.

Strictly satisfies Product Manager Directives:
1. File-backed only (no in-memory SQLite).
2. Tests concurrent readers under multi-threaded execution.
3. Tests concurrent status requests via FastAPI TestClient.
4. Tests missing database handling (clean HTTP 503, no unhandled 500).
5. Tests corrupt database detection (clean HTTP 503, no unhandled 500).
6. Tests lock timeout and recovery (verifies HTTP 503 on timeout, then clean recovery to 200).
"""

import os
import sys
import time
import sqlite3
import threading
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app
from backtest.market_memory import _get_db, _init_tables


def _create_populated_test_db(db_path: str, n_records: int = 25) -> str:
    """Creates a real file-backed SQLite database with canonical schema and test records."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = _get_db(db_path)
    _init_tables(conn)

    with conn:
        for i in range(n_records):
            pid = f"pred_int_{i:04d}"
            conn.execute(
                """
                INSERT OR REPLACE INTO predictions (
                    prediction_id, timestamp, candle_time, price, regime,
                    raw_prob, calibrated_prob, decision, direction,
                    outcome_resolved, was_correct, data_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pid,
                    f"2026-09-01T{i%24:02d}:00:00Z",
                    f"2026-09-01T{i%24:02d}:00:00Z",
                    60000.0 + i * 10,
                    "TRENDING_UP",
                    0.65,
                    0.62,
                    "LONG",
                    "LONG",
                    1,
                    1 if i % 2 == 0 else 0,
                    "live_terminal"
                )
            )

        # Also add Hawkes shadow tables
        conn.execute("CREATE TABLE IF NOT EXISTS hawkes_forecasts (forecast_id TEXT PRIMARY KEY, timestamp TEXT);")
        conn.execute("CREATE TABLE IF NOT EXISTS hawkes_outcomes (outcome_id TEXT PRIMARY KEY, forecast_id TEXT);")
        for i in range(5):
            conn.execute("INSERT OR REPLACE INTO hawkes_forecasts VALUES (?, ?)", (f"h_fc_{i}", "2026-09-01T00:00:00Z"))
            conn.execute("INSERT OR REPLACE INTO hawkes_outcomes VALUES (?, ?)", (f"h_oc_{i}", f"h_fc_{i}"))

    conn.close()
    return db_path


def test_concurrent_file_backed_readers(tmp_path):
    """
    Verifies that 20 concurrent reader threads querying a real file-backed SQLite
    database with WAL mode enabled all succeed without 'database is locked'.
    """
    db_file = str(tmp_path / "concurrent_readers.db")
    _create_populated_test_db(db_file, n_records=50)

    results = []
    errors = []

    def reader_task(thread_id: int):
        try:
            conn = _get_db(db_file)
            rows = conn.execute("SELECT COUNT(*) FROM predictions WHERE outcome_resolved = 1;").fetchone()[0]
            fc_rows = conn.execute("SELECT COUNT(*) FROM hawkes_forecasts;").fetchone()[0]
            conn.close()
            results.append((thread_id, rows, fc_rows))
        except Exception as e:
            errors.append((thread_id, str(e)))

    threads = []
    for t_id in range(20):
        t = threading.Thread(target=reader_task, args=(t_id,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=10.0)

    assert len(errors) == 0, f"Encountered concurrency lock errors: {errors}"
    assert len(results) == 20
    for r in results:
        assert r[1] == 50
        assert r[2] == 5


def test_concurrent_status_requests_file_backed(tmp_path, monkeypatch):
    """
    Verifies that 15 concurrent HTTP requests to /prediction/longitudinal
    hitting a real file-backed SQLite database in WAL mode return 200 OK with zero 500s.
    """
    db_file = str(tmp_path / "status_concurrent.db")
    _create_populated_test_db(db_file, n_records=20)

    monkeypatch.setenv("SQLITE_DB_PATH", db_file)
    import config.database as db_cfg
    monkeypatch.setattr(db_cfg, "MARKET_MEMORY_DB_PATH", db_file)
    import engine.longitudinal_status as ls_mod
    monkeypatch.setattr(ls_mod, "MARKET_MEMORY_DB_PATH", db_file)
    import research.post_repair_block_builder as bb_mod
    monkeypatch.setattr(bb_mod, "MARKET_MEMORY_DB_PATH", db_file)

    client = TestClient(app)
    statuses = []
    exceptions = []

    def make_request(req_id: int):
        try:
            r = client.get("/prediction/longitudinal")
            statuses.append((req_id, r.status_code))
        except Exception as exc:
            exceptions.append((req_id, str(exc)))

    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(make_request, i) for i in range(15)]
        for f in as_completed(futures):
            f.result()

    assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"
    assert len(statuses) == 15
    for _, code in statuses:
        assert code == 200, f"Expected 200, got {code}"


def test_missing_database_handling(tmp_path, monkeypatch):
    """
    Verifies that when SQLITE_DB_PATH points to a non-existent file,
    the endpoint cleanly returns HTTP 503 Service Unavailable rather than crashing with unhandled 500.
    """
    missing_file = str(tmp_path / "non_existent_dir" / "missing.db")
    monkeypatch.setenv("SQLITE_DB_PATH", missing_file)
    import config.database as db_cfg
    monkeypatch.setattr(db_cfg, "MARKET_MEMORY_DB_PATH", missing_file)
    import engine.longitudinal_status as ls_mod
    monkeypatch.setattr(ls_mod, "MARKET_MEMORY_DB_PATH", missing_file)
    import research.post_repair_block_builder as bb_mod
    monkeypatch.setattr(bb_mod, "MARKET_MEMORY_DB_PATH", missing_file)

    client = TestClient(app)
    res = client.get("/prediction/longitudinal")
    assert res.status_code == 503
    data = res.json()
    assert "missing or corrupted" in data.get("detail", "").lower() or "not found" in data.get("detail", "").lower()


def test_corrupt_database_handling(tmp_path, monkeypatch):
    """
    Verifies that when SQLITE_DB_PATH points to a corrupt file (invalid SQLite header),
    the endpoint detects corruption and returns HTTP 503 instead of crashing with unhandled 500.
    """
    corrupt_file = str(tmp_path / "corrupt_market_memory.db")
    with open(corrupt_file, "wb") as f:
        f.write(b"CORRUPT_BYTES_NOT_A_VALID_SQLITE_DATABASE_HEADER" * 10)

    monkeypatch.setenv("SQLITE_DB_PATH", corrupt_file)
    import config.database as db_cfg
    monkeypatch.setattr(db_cfg, "MARKET_MEMORY_DB_PATH", corrupt_file)
    import engine.longitudinal_status as ls_mod
    monkeypatch.setattr(ls_mod, "MARKET_MEMORY_DB_PATH", corrupt_file)
    import research.post_repair_block_builder as bb_mod
    monkeypatch.setattr(bb_mod, "MARKET_MEMORY_DB_PATH", corrupt_file)

    client = TestClient(app)
    res = client.get("/prediction/longitudinal")
    assert res.status_code == 503
    data = res.json()
    assert "corrupted" in data.get("detail", "").lower() or "database" in data.get("detail", "").lower()


def test_lock_timeout_and_recovery(tmp_path, monkeypatch):
    """
    Verifies that when a writer holds an exclusive lock longer than timeout,
    the endpoint fails closed with HTTP 503 (not 500), and once the lock
    is released, subsequent requests immediately recover to HTTP 200 OK.
    """
    db_file = str(tmp_path / "lock_recovery.db")
    _create_populated_test_db(db_file, n_records=10)

    monkeypatch.setenv("SQLITE_DB_PATH", db_file)
    import config.database as db_cfg
    monkeypatch.setattr(db_cfg, "MARKET_MEMORY_DB_PATH", db_file)
    import engine.longitudinal_status as ls_mod
    monkeypatch.setattr(ls_mod, "MARKET_MEMORY_DB_PATH", db_file)
    import research.post_repair_block_builder as bb_mod
    monkeypatch.setattr(bb_mod, "MARKET_MEMORY_DB_PATH", db_file)

    client = TestClient(app)

    # First verify normal baseline returns 200
    res_baseline = client.get("/prediction/longitudinal")
    assert res_baseline.status_code == 200

    # Hold exclusive locking mode on the database
    lock_conn = sqlite3.connect(db_file, timeout=0.1)
    lock_conn.execute("PRAGMA locking_mode = EXCLUSIVE;")
    lock_conn.execute("BEGIN EXCLUSIVE;")
    lock_conn.execute("SELECT COUNT(*) FROM predictions;").fetchone()

    # Configure reader connection to timeout quickly (0.05s) to trigger lock timeout
    from backtest import market_memory as mm_mod
    orig_get_db = mm_mod._get_db
    def short_timeout_get_db(target=None):
        conn = sqlite3.connect(target or db_file, timeout=0.05)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA busy_timeout=50;")
        except Exception:
            pass
        return conn

    monkeypatch.setattr(mm_mod, "_get_db", short_timeout_get_db)

    try:
        # Request while exclusive lock is held -> expect HTTP 503 (locked / unavailable)
        res_locked = client.get("/prediction/longitudinal")
        assert res_locked.status_code == 503
        assert "locked" in res_locked.json().get("detail", "").lower()
    finally:
        # Release exclusive lock
        lock_conn.execute("COMMIT;")
        lock_conn.execute("PRAGMA locking_mode = NORMAL;")
        lock_conn.close()

    # Restore normal _get_db
    monkeypatch.setattr(mm_mod, "_get_db", orig_get_db)

    # Request after unlock -> verify clean recovery to 200 OK
    res_recovered = client.get("/prediction/longitudinal")
    assert res_recovered.status_code == 200
    data = res_recovered.json()
    assert data["governance_mode"] == "LONGITUDINAL_MONITORING_ACTIVE"

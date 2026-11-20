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
import socket
import tempfile
import hashlib
import pathlib
import pytest
import pandas as pd
from typing import Generator
import config as app_config

# Ensure project root is in sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Select a fresh, disposable database before importing application modules.
_SESSION_TEMP_DIR = tempfile.mkdtemp(prefix="btcognitive_test_db_")
_SESSION_TEST_DB_PATH = os.path.join(_SESSION_TEMP_DIR, "isolated_market_memory.db")
_SESSION_TEST_RESULTS_DIR = os.path.join(_SESSION_TEMP_DIR, "results")
_SESSION_TEST_PROCESSED_DIR = os.path.join(_SESSION_TEMP_DIR, "processed")
_ORIGINAL_SQLITE_DB_PATH = os.environ.get("SQLITE_DB_PATH")
_ORIGINAL_MEIE_DB_PATH = os.environ.get("MEIE_DB_PATH")
_ORIGINAL_RESULTS_DIR = app_config.RESULTS_DIR
_ORIGINAL_DATA_PROCESSED_DIR = app_config.DATA_PROCESSED_DIR
os.environ["SQLITE_DB_PATH"] = _SESSION_TEST_DB_PATH
os.environ["MEIE_DB_PATH"] = os.path.join(_SESSION_TEMP_DIR, "meie_memory.db")
app_config.RESULTS_DIR = _SESSION_TEST_RESULTS_DIR
app_config.DATA_PROCESSED_DIR = _SESSION_TEST_PROCESSED_DIR

import config.database as db_cfg
import backtest.market_memory
import engine.hawkes_shadow_session

# Canonical persistent database path that MUST NOT be mutated by tests
PROTECTED_PERSISTENT_DB_PATH = os.path.normcase(os.path.realpath(db_cfg.DEFAULT_SQLITE_PATH))

# Hash and guard all persisted research/data outputs, not just selected fixtures.
PROTECTED_HASH_ROOTS = tuple(
    os.path.join(PROJECT_ROOT, relative)
    for relative in ("data", "results", os.path.join("experiments", "results"), os.path.join("research", "reports"), "models")
)
_PROTECTED_FILE_HASHES = {}

_original_sqlite3_connect = sqlite3.connect
_original_socket_connect = socket.socket.connect
_original_socket_connect_ex = socket.socket.connect_ex
_original_to_parquet = pd.DataFrame.to_parquet

_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0", "::"}
_PROTECTED_FS_EVENTS = {
    "os.mkdir", "os.remove", "os.rmdir", "os.rename", "os.replace",
    "os.chmod", "os.chown", "os.truncate", "os.link", "os.symlink",
}


def _safe_to_parquet(self, path, *args, **kwargs):
    if path and isinstance(path, (str, os.PathLike)) and _is_protected_path(path):
        raise RuntimeError(
            f"PROTECTED_DATASET_MUTATION_BLOCKED: Test attempted to write to protected "
            f"dataset at '{path}'. Tests must use isolated temporary directories (tmp_path)."
        )
    return _original_to_parquet(self, path, *args, **kwargs)


def _is_protected_path(path):
    try:
        target = os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(path))))
        if "__pycache__" in pathlib.Path(target).parts or target.endswith(".pyc"):
            return False
        return any(
            os.path.commonpath((target, os.path.normcase(os.path.realpath(root)))) ==
            os.path.normcase(os.path.realpath(root))
            for root in PROTECTED_HASH_ROOTS
        )
    except (OSError, TypeError, ValueError):
        return False


def _hash_protected_files():
    manifest = {}
    for root in PROTECTED_HASH_ROOTS:
        if not os.path.isdir(root):
            continue
        for directory, dirnames, filenames in os.walk(root):
            dirnames[:] = [name for name in dirnames if name != "__pycache__"]
            for filename in filenames:
                if filename.endswith(".pyc"):
                    continue
                path = os.path.join(directory, filename)
                relative = os.path.relpath(path, PROJECT_ROOT)
                try:
                    digest = hashlib.sha256()
                    with open(path, "rb") as source:
                        for chunk in iter(lambda: source.read(1024 * 1024), b""):
                            digest.update(chunk)
                    stat = os.stat(path)
                    manifest[relative] = (digest.hexdigest(), stat.st_size, stat.st_mtime_ns)
                except OSError as exc:
                    manifest[relative] = (f"READ_ERROR:{exc.__class__.__name__}", None, None)
    return manifest


def _protected_manifest_sha256(manifest):
    rows = (
        f"{path}\0{digest}\0{size}\0{mtime_ns}"
        for path, (digest, size, mtime_ns) in sorted(manifest.items())
    )
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def _sqlite_target_path(database):
    if not isinstance(database, (str, os.PathLike)):
        return None
    value = os.fspath(database)
    if value.startswith("file:"):
        value = value[5:].split("?", 1)[0]
    return os.path.normcase(os.path.realpath(os.path.abspath(value)))


def _audit_protected_writes(event, args):
    if event == "open" and args:
        path = args[0]
        mode = args[1] if len(args) > 1 else "r"
        flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
        is_write = (
            isinstance(mode, str) and any(flag in mode for flag in "wax+")
        ) or bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if is_write and _is_protected_path(path):
            raise PermissionError(f"PROTECTED_FILE_WRITE_BLOCKED: {path}")
    elif event in _PROTECTED_FS_EVENTS:
        for path in args[:2]:
            if isinstance(path, (str, bytes, os.PathLike)) and _is_protected_path(path):
                raise PermissionError(f"PROTECTED_FILESYSTEM_OPERATION_BLOCKED: {event}: {path}")


def _offline_guarded_connect(self, address):
    if isinstance(address, (list, tuple)) and len(address) >= 2:
        host = str(address[0]).lower()
        if host not in _ALLOWED_HOSTS and not host.startswith("127."):
            raise RuntimeError(
                f"OFFLINE_NETWORK_BLOCKED: Test execution attempted external network connection to "
                f"'{host}:{address[1]}'. BTCognitive test suites are strictly offline-first."
            )
    return _original_socket_connect(self, address)


def _offline_guarded_connect_ex(self, address):
    if isinstance(address, (list, tuple)) and len(address) >= 2:
        host = str(address[0]).lower()
        if host not in _ALLOWED_HOSTS and not host.startswith("127."):
            raise RuntimeError(
                f"OFFLINE_NETWORK_BLOCKED: Test execution attempted external network connection to "
                f"'{host}:{address[1]}'. BTCognitive test suites are strictly offline-first."
            )
    return _original_socket_connect_ex(self, address)


def _safe_sqlite3_connect(*args, **kwargs):
    database = args[0] if args else kwargs.get("database")
    if database:
        target = _sqlite_target_path(database)
        if target == PROTECTED_PERSISTENT_DB_PATH:
            raise RuntimeError(
                "CANONICAL_DATABASE_ACCESS_BLOCKED: Tests must use the disposable SQLite database "
                f"'{_SESSION_TEST_DB_PATH}', not '{db_cfg.DEFAULT_SQLITE_PATH}'."
            )
        if _is_protected_path(target):
            raise RuntimeError(f"PROTECTED_SQLITE_ACCESS_BLOCKED: {target}")
    return _original_sqlite3_connect(*args, **kwargs)


def pytest_configure(config):
    """Create an empty disposable database and install global test guards."""
    global _PROTECTED_FILE_HASHES
    _PROTECTED_FILE_HASHES = _hash_protected_files()
    db_cfg.MARKET_MEMORY_DB_PATH = _SESSION_TEST_DB_PATH
    db_cfg.HAWKES_DB_PATH = _SESSION_TEST_DB_PATH
    backtest.market_memory.DB_PATH = _SESSION_TEST_DB_PATH
    backtest.market_memory.MARKET_MEMORY_DB_PATH = _SESSION_TEST_DB_PATH
    backtest.market_memory.CSV_PATH = os.path.join(_SESSION_TEMP_DIR, "isolated_market_memory.csv")
    engine.hawkes_shadow_session.DB_PATH = _SESSION_TEST_DB_PATH

    os.makedirs(_SESSION_TEST_RESULTS_DIR, exist_ok=True)
    os.makedirs(_SESSION_TEST_PROCESSED_DIR, exist_ok=True)
    from engine import observatory as _observatory

    sys.addaudithook(_audit_protected_writes)
    init_conn = _original_sqlite3_connect(_SESSION_TEST_DB_PATH)
    try:
        backtest.market_memory._init_tables(init_conn)
    finally:
        init_conn.close()

    engine.hawkes_shadow_session.init_hawkes_tables()
    sqlite3.connect = _safe_sqlite3_connect
    socket.socket.connect = _offline_guarded_connect
    socket.socket.connect_ex = _offline_guarded_connect_ex
    pd.DataFrame.to_parquet = _safe_to_parquet


def pytest_sessionfinish(session, exitstatus):
    """Fail the session if a protected file changed, appeared, or disappeared."""
    after = _hash_protected_files()
    before_digest = _protected_manifest_sha256(_PROTECTED_FILE_HASHES)
    after_digest = _protected_manifest_sha256(after)
    changed = sorted(
        path for path in set(_PROTECTED_FILE_HASHES) | set(after)
        if _PROTECTED_FILE_HASHES.get(path) != after.get(path)
    )
    if changed:
        session.exitstatus = 1
        print(
            "\nPROTECTED_FILE_HASH_GUARD: FAIL\n" +
            "\n".join(f"  {path}" for path in changed[:50]) +
            f"\nBEFORE_MANIFEST_SHA256={before_digest}\nAFTER_MANIFEST_SHA256={after_digest}"
        )
    else:
        print(
            f"\nPROTECTED_FILE_HASH_GUARD: PASS "
            f"({len(_PROTECTED_FILE_HASHES)} files; data, results, experiment results, research, models) "
            f"BEFORE_MANIFEST_SHA256={before_digest} AFTER_MANIFEST_SHA256={after_digest}"
        )


def pytest_unconfigure(config):
    """Restore process-level guards and the caller's database environment."""
    sqlite3.connect = _original_sqlite3_connect
    socket.socket.connect = _original_socket_connect
    socket.socket.connect_ex = _original_socket_connect_ex
    pd.DataFrame.to_parquet = _original_to_parquet
    if _ORIGINAL_SQLITE_DB_PATH is None:
        os.environ.pop("SQLITE_DB_PATH", None)
    else:
        os.environ["SQLITE_DB_PATH"] = _ORIGINAL_SQLITE_DB_PATH
    if _ORIGINAL_MEIE_DB_PATH is None:
        os.environ.pop("MEIE_DB_PATH", None)
    else:
        os.environ["MEIE_DB_PATH"] = _ORIGINAL_MEIE_DB_PATH
    app_config.RESULTS_DIR = _ORIGINAL_RESULTS_DIR
    app_config.DATA_PROCESSED_DIR = _ORIGINAL_DATA_PROCESSED_DIR


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
    os.environ["SQLITE_DB_PATH"] = _SESSION_TEST_DB_PATH
    db_cfg.MARKET_MEMORY_DB_PATH = old_mm_path
    db_cfg.HAWKES_DB_PATH = old_mm_path
    backtest.market_memory.DB_PATH = old_bm_path
    backtest.market_memory.MARKET_MEMORY_DB_PATH = old_bm_path
    engine.hawkes_shadow_session.DB_PATH = old_bm_path

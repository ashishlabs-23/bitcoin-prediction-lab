import os
import socket
import sqlite3
import subprocess
import sys
import textwrap
import urllib.request

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def test_server_import_does_not_read_market_data_or_attempt_network():
    script = textwrap.dedent(
        """
        import socket
        import urllib.request
        import sqlite3
        import os
        import tempfile
        import pandas as pd
        import faulthandler
        import sys

        faulthandler.dump_traceback_later(20, file=sys.stderr)
        attempts = []
        disposable_root = os.path.normcase(os.path.realpath(tempfile.gettempdir()))

        def guarded_sqlite_connect(database, *args, **kwargs):
            db_name = os.fsdecode(os.fspath(database))
            if db_name == ":memory:" or db_name.startswith("file::memory:") or "mode=memory" in db_name:
                return original_sqlite_connect(database, *args, **kwargs)

            path = db_name[5:] if db_name.startswith("file:") else db_name
            normalized = os.path.normcase(os.path.realpath(path))
            try:
                is_disposable = os.path.commonpath([disposable_root, normalized]) == disposable_root
            except ValueError:
                is_disposable = False
            if is_disposable:
                return original_sqlite_connect(database, *args, **kwargs)

            attempts.append(("persistent sqlite connect", normalized))
            raise AssertionError(f"unexpected persistent SQLite connection: {normalized}")

        def block(kind):
            def blocked(*args, **kwargs):
                attempts.append(kind)
                raise AssertionError(f"unexpected {kind}")
            return blocked

        original_sqlite_connect = sqlite3.connect
        pd.read_parquet = block("parquet read")
        sqlite3.connect = guarded_sqlite_connect
        socket.socket.connect = block("socket connect")
        socket.socket.connect_ex = block("socket connect_ex")
        socket.create_connection = block("socket create_connection")
        socket.getaddrinfo = block("DNS lookup")
        urllib.request.urlopen = block("urllib request")

        print("importing api.server", flush=True)
        try:
            import api.server
        finally:
            assert attempts == [], f"unexpected import side effects: {attempts!r}"
        print("imported api.server", flush=True)
        import api.routes_tournament
        import api.routes_terminal as terminal_routes
        import engine.observatory as observatory_module
        import importlib
        arena_module = importlib.import_module("engine.arena_runner")
        import research.v12_strategy_tournament_engine as tournament_engine

        assert api.server.app.router.lifespan_context is not None
        assert arena_module.arena_runner._instance is None
        assert observatory_module.observatory._instance is None
        assert terminal_routes.observatory._instance is None
        assert terminal_routes.observatory._factory_kwargs == {"nominal_target": 0.90}
        assert tournament_engine._regime_tournament_engine is None
        assert attempts == []
        """
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr
        raise AssertionError(
            f"server import subprocess timed out; stdout={stdout!r}; stderr={stderr!r}"
        ) from exc

    assert result.returncode == 0, result.stdout + result.stderr


def test_fixture_lifespan_skips_protected_data_model_cache_and_network():
    script = textwrap.dedent(
        """
        import os
        import socket
        import sqlite3
        import urllib.request
        import pandas as pd
        from fastapi.testclient import TestClient

        os.environ["DATA_MODE"] = "fixture"
        os.environ["BTC_DATA_MODE"] = "fixture"
        attempts = []
        original_connect = sqlite3.connect

        def guarded_connect(database, *args, **kwargs):
            name = os.fsdecode(os.fspath(database))
            if name == ":memory:" or name.startswith("file::memory:") or "mode=memory" in name:
                return original_connect(database, *args, **kwargs)
            attempts.append(("persistent sqlite connect", name))
            raise AssertionError(f"unexpected persistent SQLite connection: {name}")

        def blocked(kind):
            def reject(*args, **kwargs):
                attempts.append(kind)
                raise AssertionError(f"unexpected {kind}")
            return reject

        def is_loopback(address):
            return isinstance(address, tuple) and address and str(address[0]).lower() in {
                "localhost", "127.0.0.1", "::1"
            }

        original_connect_socket = socket.socket.connect
        original_connect_ex = socket.socket.connect_ex
        original_create_connection = socket.create_connection
        original_getaddrinfo = socket.getaddrinfo

        def guarded_connect(sock, address):
            if is_loopback(address):
                return original_connect_socket(sock, address)
            attempts.append(("external socket connect", address))
            raise AssertionError(f"unexpected external socket: {address!r}")

        def guarded_connect_ex(sock, address):
            if is_loopback(address):
                return original_connect_ex(sock, address)
            attempts.append(("external socket connect_ex", address))
            raise AssertionError(f"unexpected external socket: {address!r}")

        def guarded_create_connection(address, *args, **kwargs):
            if is_loopback(address):
                return original_create_connection(address, *args, **kwargs)
            attempts.append(("external create_connection", address))
            raise AssertionError(f"unexpected external connection: {address!r}")

        def guarded_getaddrinfo(host, *args, **kwargs):
            if str(host).lower() in {"localhost", "127.0.0.1", "::1"}:
                return original_getaddrinfo(host, *args, **kwargs)
            attempts.append(("external DNS lookup", host))
            raise AssertionError(f"unexpected external DNS lookup: {host!r}")

        sqlite3.connect = guarded_connect
        pd.read_parquet = blocked("parquet read")
        socket.socket.connect = guarded_connect
        socket.socket.connect_ex = guarded_connect_ex
        socket.create_connection = guarded_create_connection
        socket.getaddrinfo = guarded_getaddrinfo
        urllib.request.urlopen = blocked("urllib request")

        from api.server import app, feature_cache, live_engine
        import importlib
        arena_module = importlib.import_module("engine.arena_runner")
        observatory_module = importlib.import_module("engine.observatory")
        terminal_routes = importlib.import_module("api.routes_terminal")
        assert attempts == []
        assert arena_module.arena_runner._instance is None
        assert observatory_module.observatory._instance is None
        assert terminal_routes.observatory._instance is None

        with TestClient(app) as client:
            readiness = client.get("/api/readiness")
            assert readiness.status_code == 200
            body = readiness.json()
            assert body["status"] == "BLOCKED"
            assert body["reason_code"] == "FIXTURE_MODE_DATA_UNAVAILABLE"
            assert body["authorization_status"] == "BLOCKED_AUDIT_FAILURE"
            assert body["authorized"] is False
            assert body["canonical_model_id"] is None
            assert body["model_version"] is None
            assert body["system_classification"] == "FIXTURE_ONLY"
            assert body["checks"]["point_in_time_data"]["status"] == "UNAVAILABLE"
            assert body["checks"]["model_readiness"]["status"] == "NOT_CHECKED"

            health = client.get("/health")
            assert health.status_code == 200, health.text
            health_body = health.json()
            assert health_body["research_authorized"] is False
            assert health_body["production_forecast_available"] is False
            assert health_body["system_status"]["production_forecast_status"] == "BLOCKED"
            assert health_body["system_status"]["canonical_model_id"] is None

        assert attempts == []
        assert not feature_cache._is_initialized
        assert live_engine.model is None
        assert arena_module.arena_runner._instance is None
        assert observatory_module.observatory._instance is None
        assert terminal_routes.observatory._instance is None
        """
    )
    env = os.environ.copy()
    env["DATA_MODE"] = "fixture"
    env["BTC_DATA_MODE"] = "fixture"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_fixture_server_import_and_lifespan_never_connect_persistent_sqlite():
    script = textwrap.dedent(
        """
        import os
        import builtins
        import socket
        import sqlite3
        import sys
        import urllib.request

        import pandas as pd

        os.environ["DATA_MODE"] = "fixture"
        os.environ["BTC_DATA_MODE"] = "fixture"
        os.environ.pop("BTC_LOCAL_FIXTURE_FEED", None)
        attempts = []
        original_connect = sqlite3.connect
        original_open = builtins.open
        original_socket_connect = socket.socket.connect
        original_socket_connect_ex = socket.socket.connect_ex
        original_create_connection = socket.create_connection
        original_getaddrinfo = socket.getaddrinfo

        def guarded_connect(database, *args, **kwargs):
            name = os.fsdecode(os.fspath(database))
            if name == ":memory:" or name.startswith("file::memory:") or "mode=memory" in name:
                return original_connect(database, *args, **kwargs)
            attempts.append(name)
            raise AssertionError(f"persistent SQLite is forbidden in fixture mode: {name}")

        def guarded_open(file, *args, **kwargs):
            path = os.path.normcase(os.path.abspath(os.fsdecode(os.fspath(file))))
            protected_roots = (
                os.path.normcase(os.path.abspath(os.path.join("data", "raw"))),
                os.path.normcase(os.path.abspath(os.path.join("experiments", "results"))),
                os.path.normcase(os.path.abspath("checkpoints")),
            )
            protected_names = {
                "ohlcv.parquet",
                "ohlcv_pre_backfill_backup.parquet",
                "ohlcv_backfilled.parquet",
                "prospective_entry_ledger.jsonl",
                "prospective_shadow_v1.jsonl",
                "prospective_entry_ledger_v2.jsonl",
            }
            if (
                os.path.basename(path) in protected_names
                or any(
                    os.path.commonpath([root, path]) == root
                    for root in protected_roots
                )
            ):
                attempts.append(("protected file access", path))
                raise AssertionError(f"protected fixture file access is forbidden: {path}")
            return original_open(file, *args, **kwargs)

        def blocked(kind):
            def reject(*args, **kwargs):
                attempts.append(kind)
                raise AssertionError(f"unexpected {kind}")
            return reject

        def is_loopback(address):
            return isinstance(address, tuple) and address and str(address[0]).lower() in {
                "localhost", "127.0.0.1", "::1"
            }

        def guarded_socket_connect(sock, address):
            if is_loopback(address):
                return original_socket_connect(sock, address)
            attempts.append(("external socket connect", address))
            raise AssertionError(f"unexpected external socket: {address!r}")

        def guarded_socket_connect_ex(sock, address):
            if is_loopback(address):
                return original_socket_connect_ex(sock, address)
            attempts.append(("external socket connect_ex", address))
            raise AssertionError(f"unexpected external socket: {address!r}")

        def guarded_create_connection(address, *args, **kwargs):
            if is_loopback(address):
                return original_create_connection(address, *args, **kwargs)
            attempts.append(("external create_connection", address))
            raise AssertionError(f"unexpected external connection: {address!r}")

        def guarded_getaddrinfo(host, *args, **kwargs):
            if str(host).lower() in {"localhost", "127.0.0.1", "::1"}:
                return original_getaddrinfo(host, *args, **kwargs)
            attempts.append(("external DNS lookup", host))
            raise AssertionError(f"unexpected external DNS lookup: {host!r}")

        sqlite3.connect = guarded_connect
        builtins.open = guarded_open
        pd.read_parquet = blocked("Parquet read")
        socket.socket.connect = guarded_socket_connect
        socket.socket.connect_ex = guarded_socket_connect_ex
        socket.create_connection = guarded_create_connection
        socket.getaddrinfo = guarded_getaddrinfo
        urllib.request.urlopen = blocked("urllib request")

        from api.server import app
        assert attempts == [], f"persistent SQLite attempted during server import: {attempts!r}"

        from fastapi.testclient import TestClient
        from backtest.market_memory import _get_db

        with TestClient(app) as client:
            health = client.get("/api/health")
            readiness = client.get("/api/readiness")
            history = client.get("/api/prediction/range/history")
            assert health.status_code == 200
            assert readiness.status_code == 200
            assert history.status_code == 200
            assert history.json()["status"] == "NO_DATA"
            assert readiness.json()["status"] == "BLOCKED"
            assert readiness.json()["canonical_model_id"] is None
            assert health.json()["system_status"]["data_mode"] == "fixture"
            assert health.json()["system_status"]["local_fixture_feed_enabled"] is False
            conn = _get_db()
            assert conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0] == 0
            assert conn.execute("PRAGMA database_list").fetchone()[2] == ""
            conn.close()

        assert attempts == [], f"persistent SQLite attempted during fixture lifespan: {attempts!r}"
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_observatory_proxy_initializes_only_on_explicit_access_with_temporary_databases(tmp_path):
    from engine.observatory import LazyForecastAccuracyObservatory

    connect_paths = []
    original_connect = sqlite3.connect

    def tracked_connect(database, *args, **kwargs):
        connect_paths.append(os.path.abspath(os.fspath(database)))
        return original_connect(database, *args, **kwargs)

    first_path = os.path.abspath(tmp_path / "arena_observatory_proxy.db")
    terminal_path = os.path.abspath(tmp_path / "terminal_observatory_proxy.db")
    first_proxy = LazyForecastAccuracyObservatory(db_path=first_path)
    terminal_proxy = LazyForecastAccuracyObservatory(
        nominal_target=0.90,
        db_path=terminal_path,
    )
    assert first_proxy._instance is None
    assert terminal_proxy._instance is None
    assert connect_paths == []

    sqlite3.connect = tracked_connect
    try:
        first_snapshot = first_proxy.get_canonical_snapshot()
        terminal_snapshot = terminal_proxy.get_canonical_snapshot()
    finally:
        sqlite3.connect = original_connect

    assert first_snapshot.to_dict()["status"] == "UNAVAILABLE"
    assert terminal_snapshot.to_dict()["status"] == "UNAVAILABLE"
    assert first_proxy._instance is not None
    assert terminal_proxy._instance is not None
    assert terminal_proxy.nominal_target == 0.90
    terminal_proxy.abstained_count = 2
    assert terminal_proxy._instance.abstained_count == 2
    assert terminal_proxy.records is terminal_proxy._instance.records
    assert set(connect_paths) == {first_path, terminal_path}


def test_fixture_tournament_endpoint_is_lazy_and_reads_only_explicit_fixture(monkeypatch):
    monkeypatch.setenv("DATA_MODE", "fixture")
    monkeypatch.setenv("BTC_DATA_MODE", "fixture")
    import research.v12_strategy_tournament_engine as tournament_engine
    import api.routes_tournament as tournament_routes
    from api.server import app

    fixture_path = "controlled-fixture-hourly.parquet"
    original_exists = os.path.exists
    reads = []
    close = np.linspace(100.0, 120.0, 220)
    fixture = pd.DataFrame(
        {
            "timestamp": pd.date_range("2020-01-01", periods=len(close), freq="h", tz="UTC"),
            "open": close - 0.1,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.full(len(close), 100.0),
        }
    )

    def fixture_exists(path):
        if os.fspath(path) == fixture_path:
            return True
        return original_exists(path)

    def read_fixture(path, *args, **kwargs):
        assert os.fspath(path) == fixture_path
        reads.append(path)
        return fixture.copy()

    monkeypatch.setattr(tournament_engine, "_regime_tournament_engine", None)
    monkeypatch.setattr(tournament_engine.os.path, "exists", fixture_exists)
    monkeypatch.setattr(tournament_engine.pd, "read_parquet", read_fixture)

    assert tournament_engine._regime_tournament_engine is None
    with TestClient(app) as client:
        unavailable = client.get("/api/tournament/regime")
        assert unavailable.status_code == 200
        assert unavailable.json()["status"] == "DATA_UNAVAILABLE"
    assert reads == []

    monkeypatch.setattr(tournament_engine, "_regime_tournament_engine", None)
    monkeypatch.setattr(
        tournament_routes,
        "get_regime_tournament_engine",
        lambda: tournament_engine.get_regime_tournament_engine(data_path=fixture_path),
    )
    with TestClient(app) as client:
        available = client.get("/api/tournament/regime")
        assert available.status_code == 200
        assert available.json()["regime"] != "TRANSITION_UNSUPPORTED"

    engine = tournament_engine._regime_tournament_engine
    assert engine is not None and engine.data_status == "AVAILABLE"
    assert engine.df_1h is not None and len(engine.df_1h) == len(fixture)
    assert engine.df_4h is not None
    assert len(reads) == 1
    assert os.fspath(reads[0]) == fixture_path


def test_missing_tournament_data_remains_explicitly_unavailable(monkeypatch):
    monkeypatch.setenv("DATA_MODE", "fixture")
    monkeypatch.setenv("BTC_DATA_MODE", "fixture")
    import api.routes_tournament as tournament_routes
    import research.v12_strategy_tournament_engine as tournament_engine
    from api.server import app

    missing_path = "controlled-missing-hourly.parquet"
    original_exists = os.path.exists

    def missing_exists(path):
        if os.fspath(path) == missing_path:
            return False
        return original_exists(path)

    monkeypatch.setattr(tournament_engine, "_regime_tournament_engine", None)
    monkeypatch.setattr(tournament_engine.os.path, "exists", missing_exists)
    monkeypatch.setattr(
        tournament_routes,
        "get_regime_tournament_engine",
        lambda: tournament_engine.get_regime_tournament_engine(data_path=missing_path),
    )

    with TestClient(app) as client:
        regime = client.get("/api/tournament/regime")
        assert regime.status_code == 200
        regime_data = regime.json()
        assert regime_data["status"] == "DATA_UNAVAILABLE"
        assert regime_data["instrument"] == "BTC-USD"
        assert regime_data["venue"] == "UNAVAILABLE"
        assert regime_data["granularity"] == "1h"
        assert regime_data["regime"] == "TRANSITION_UNSUPPORTED"
        assert regime_data["raw_regime"] == "TRANSITION_UNSUPPORTED"
        assert regime_data["hysteresis_status"] == "UNAVAILABLE"
        assert regime_data["execution_authorization"] == "DISABLED"
        assert regime_data["directional_authorization"] == "OFFLINE_RESEARCH_ONLY"
        for field in (
            "latest_completed_time",
            "latest_completed_price",
            "adx_14",
            "plus_di",
            "minus_di",
            "ema_20",
            "ema_50",
            "ema_200",
            "atr_14",
            "bb_width",
            "bbw_percentile",
        ):
            assert regime_data[field] is None

        setup = client.get("/api/tournament/setup/MTF_MOMENTUM_TREND")
        assert setup.status_code == 200
        validated_setup = tournament_routes.StrategySetupContractModel.model_validate(setup.json())
        assert validated_setup.feature_readiness == "DATA_UNAVAILABLE"
        assert validated_setup.data_readiness == "BLOCKED_BY_DATA"
        assert validated_setup.setup_state == "BLOCKED_BY_DATA"
        assert validated_setup.entry_price is None
        assert validated_setup.market_snapshot.freshness_status == "DATA_UNAVAILABLE"

    engine = tournament_engine._regime_tournament_engine
    assert engine is not None and engine.data_status == "DATA_UNAVAILABLE"
    assert engine.df_1h is None
    assert engine.run_tournament()["status"] == "DATA_UNAVAILABLE"


def test_missing_tournament_data_remains_unavailable_in_routes(monkeypatch):
    import api.routes_tournament as tournament_routes
    import research.v12_strategy_tournament_engine as tournament_engine

    missing_path = "controlled:missing-hourly-dataset"
    original_exists = os.path.exists

    def missing_exists(path):
        if os.fspath(path) == missing_path:
            return False
        return original_exists(path)

    monkeypatch.setattr(tournament_engine, "_regime_tournament_engine", None)
    monkeypatch.setattr(tournament_engine.os.path, "exists", missing_exists)
    engine = tournament_engine.get_regime_tournament_engine(data_path=missing_path)
    monkeypatch.setattr(tournament_routes, "get_tournament_engine", lambda: engine)

    assert engine.data_status == "DATA_UNAVAILABLE"
    assert engine.df_1h is None
    assert tournament_routes.get_market_regime()["status"] == "DATA_UNAVAILABLE"
    assert engine.run_tournament()["status"] == "DATA_UNAVAILABLE"

    setup = tournament_routes.get_strategy_setup(
        "MTF_MOMENTUM_TREND",
        cost_scenario="COINBASE_RETAIL_87BPS",
        enabled=True,
    )
    validated_setup = tournament_routes.StrategySetupContractModel.model_validate(setup)
    assert validated_setup.feature_readiness == "DATA_UNAVAILABLE"
    assert validated_setup.data_readiness == "BLOCKED_BY_DATA"
    assert validated_setup.setup_state == "BLOCKED_BY_DATA"
    assert validated_setup.entry_price is None
    assert validated_setup.market_snapshot.freshness_status == "DATA_UNAVAILABLE"

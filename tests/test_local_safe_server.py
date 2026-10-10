from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient

from api import local_safe_server


def test_safe_entry_point_import_isolated_from_legacy_runtime():
    project_root = Path(__file__).resolve().parents[1]
    check = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; from api import local_safe_server; "
                "blocked = ('api.server', 'engine.inference_service', "
                "'engine.feature_cache', 'backtest.market_memory', "
                "'research.entry_tp_sl.run_full_research_pipeline'); "
                "loaded = [name for name in sys.modules if any("
                "name == prefix or name.startswith(prefix + '.') "
                "for prefix in blocked)]; "
                "assert not loaded, loaded"
            ),
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert check.returncode == 0, check.stderr


def test_local_safe_routes_report_unavailable_without_signal_values():
    with TestClient(local_safe_server.app) as client:
        research = client.get("/api/research/entry-tp-sl")
        latest = client.get("/prediction/latest")
        status = client.get("/api/research/status")

    assert research.status_code == 200
    assert research.json()["status"] == "BLOCKED_AUDIT_FAILURE"
    assert research.json()["hypothetical_signal"] is None
    assert latest.status_code == 200
    assert latest.json()["status"] == "MODEL_UNAVAILABLE"
    assert not {
        "entry",
        "entry_price",
        "tp",
        "tp_price",
        "sl",
        "sl_price",
        "probability",
        "confidence",
    }.intersection(latest.json())
    assert status.status_code == 200
    assert status.json()["authorization"]["authorized"] is False


def test_local_safe_serves_existing_frontend_assets():
    with TestClient(local_safe_server.app) as client:
        root = client.get("/")
        script = client.get("/app.js")
        stylesheet = client.get("/styles.css")

    assert root.status_code == 200
    assert "BTCOGNITIVE_LOCAL_SAFE_MODE" in root.text
    assert "https://" not in root.text
    assert "styles.css?local-safe=1" in root.text
    assert "app.js?v=10.5" in root.text
    assert root.headers["content-security-policy"].endswith("connect-src 'self'")
    assert script.status_code == 200
    assert (local_safe_server.WEB_ROOT / "app.js").is_file()
    assert stylesheet.status_code == 200
    assert "fonts.googleapis.com" not in stylesheet.text
    assert "text/css" in stylesheet.headers["content-type"]


def test_local_safe_frontend_fails_closed_if_local_app_script_is_missing(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text(
        '<html><body><div id="root"></div></body></html>',
        encoding="utf-8",
    )
    monkeypatch.setattr(local_safe_server, "WEB_ROOT", tmp_path)

    with TestClient(local_safe_server.app) as client:
        response = client.get("/")

    assert response.status_code == 503
    assert "initialization failed" in response.text


def test_scenario_calculation_is_available_while_experiment_gate_is_blocked():
    payload = {
        "side": "LONG",
        "reference_price": 100.0,
        "volatility_atr": 2.0,
        "barrier_pair_id": "barrier_pair_01",
        "horizon_minutes": 240,
    }
    with TestClient(local_safe_server.app) as client:
        blocked_status = client.get("/api/research/status").json()
        options = client.get("/api/scenario/options")
        calculated = client.post("/api/scenario/calculate", json=payload)

    assert blocked_status["authorization"]["authorized"] is False
    assert calculated.status_code == 200
    result = calculated.json()
    assert result["status"] == "SCENARIO_CALCULATION"
    assert result["label"] == "SCENARIO_CALCULATION — NOT A MODEL PREDICTION"
    assert result["entry_price"] == 100.0
    assert result["tp_price"] == 102.0
    assert result["sl_price"] == 98.0
    assert result["input_source"] == "USER_PROVIDED"
    assert result["execution_mode"] == "PAPER_RESEARCH_ONLY"
    assert options.status_code == 200
    assert len(options.json()["barrier_pairs"]) == 5


def test_scenario_calculation_rejects_missing_invalid_and_mismatched_inputs():
    valid = {
        "side": "LONG",
        "reference_price": 100.0,
        "volatility_atr": 2.0,
        "barrier_pair_id": "barrier_pair_01",
        "horizon_minutes": 240,
    }
    cases = [
        ({**valid, "reference_price": None}, 422),
        ({**valid, "volatility_atr": 0.0}, 422),
        ({**valid, "barrier_pair_id": "unknown"}, 422),
        ({**valid, "horizon_minutes": 120}, 422),
        ({**valid, "side": "BUY"}, 422),
    ]
    with TestClient(local_safe_server.app) as client:
        for payload, expected_status in cases:
            response = client.post("/api/scenario/calculate", json=payload)
            assert response.status_code == expected_status


def test_scenario_calculation_side_and_frozen_pair_control_only_barrier_geometry():
    base = {
        "side": "LONG",
        "reference_price": 100.0,
        "volatility_atr": 2.0,
        "barrier_pair_id": "barrier_pair_01",
        "horizon_minutes": 240,
    }
    with TestClient(local_safe_server.app) as client:
        long_result = client.post("/api/scenario/calculate", json=base).json()
        short_result = client.post(
            "/api/scenario/calculate",
            json={**base, "side": "SHORT"},
        ).json()
        wider_pair_result = client.post(
            "/api/scenario/calculate",
            json={**base, "barrier_pair_id": "barrier_pair_02"},
        ).json()

    assert (long_result["entry_price"], long_result["tp_price"], long_result["sl_price"]) == (
        100.0,
        102.0,
        98.0,
    )
    assert (short_result["entry_price"], short_result["tp_price"], short_result["sl_price"]) == (
        100.0,
        98.0,
        102.0,
    )
    assert wider_pair_result["entry_price"] == long_result["entry_price"]
    assert wider_pair_result["tp_price"] == 103.0
    assert wider_pair_result["sl_price"] == long_result["sl_price"]
    assert wider_pair_result["vertical_horizon_minutes"] == long_result["vertical_horizon_minutes"]


def test_safe_application_has_no_order_mutation_routes():
    route_paths = {route.path for route in local_safe_server.app.routes}

    assert not any(
        path in route_paths
        for path in {
            "/api/arena/trade",
            "/api/arena/experiment",
            "/api/order/buy",
            "/api/order/sell",
        }
    )

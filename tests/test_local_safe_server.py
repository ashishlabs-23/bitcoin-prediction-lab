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
    assert latest.json()["status"] == "DATA_UNAVAILABLE"
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

    assert root.status_code == 200
    assert "BTCOGNITIVE_LOCAL_SAFE_MODE" in root.text
    assert script.status_code == 200
    assert (local_safe_server.WEB_ROOT / "app.js").is_file()

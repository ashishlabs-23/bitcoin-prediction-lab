import os
from pathlib import Path
import subprocess
import sys
import tempfile


def test_shared_prediction_endpoints_do_not_publish_cached_legacy_values():
    project_root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="btcognitive-route-test-") as temp_dir:
        env = os.environ.copy()
        env["SQLITE_DB_PATH"] = str(Path(temp_dir) / "isolated.sqlite3")
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import asyncio; from api.routes_prediction import "
                    "get_prediction_latest, get_prediction_range, "
                    "get_research_entry_tp_sl; from engine.inference_service "
                    "import live_engine; "
                    "live_engine.latest_prediction = {'tp': 12, 'sl': 10, "
                    "'entry_price': 11, 'probability': 0.9}; "
                    "live_engine.latest_range_forecast = {'upper': 13, "
                    "'lower': 9}; "
                    "latest = asyncio.run(get_prediction_latest()); "
                    "forecast = asyncio.run(get_prediction_range()); "
                    "research = asyncio.run(get_research_entry_tp_sl()); "
                    "assert latest['status'] == 'DATA_UNAVAILABLE'; "
                    "assert not {'tp', 'sl', 'entry_price', 'probability'} "
                    "& latest.keys(); "
                    "assert forecast['status'] == 'HISTORICAL_UNVERIFIED'; "
                    "assert forecast['forecast'] is None; "
                    "assert research['status'] == 'BLOCKED_AUDIT_FAILURE'; "
                    "assert research['hypothetical_signal'] is None; "
                    "assert research['metrics'] is None; "
                    "assert not live_engine.is_running and not live_engine.warmed_up"
                ),
            ],
            cwd=project_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode == 0, result.stderr

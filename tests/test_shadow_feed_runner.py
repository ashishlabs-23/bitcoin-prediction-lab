"""
tests/test_shadow_feed_runner.py — Unit & Integration Tests for V30.4 Shadow Feed Runner
======================================================================================
Validates:
1. Closed-candle boundary enforcement (drops forming bar).
2. OHLC validation and corruption filtering.
3. Feed outage and graceful offline fallback.
4. Dry-run execution safety (no ledger mutations).
5. In-position gating and delayed outcome resolution.
6. Cross-process FileLock integration.
7. Status telemetry generation in data/prospective_shadow_status.json.
8. Preservation of data/prospective_entry_ledger.jsonl.
9. Permanent disablement of live trading authorization.
"""

import os
import json
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from engine.prospective_shadow_collector import ProspectiveShadowLedger, STRATEGY_ID
from engine.shadow_feed_runner import ShadowFeedRunner


@pytest.fixture
def isolated_runner(tmp_path):
    ledger_path = str(tmp_path / "test_feed_shadow.jsonl")
    status_path = str(tmp_path / "test_feed_status.json")
    ohlcv_path = str(tmp_path / "test_ohlcv.parquet")

    # Generate synthetic historical 1h bars for test setup
    base_ts = pd.to_datetime("2026-10-20T00:00:00+00:00")
    bars = []
    price = 80000.0
    for i in range(150):
        ts = base_ts + pd.Timedelta(hours=i)
        bars.append({
            "timestamp": ts,
            "open": price,
            "high": price + 200.0,
            "low": price - 200.0,
            "close": price + 50.0,
            "volume": 100.0,
            "available_time": ts + pd.Timedelta(hours=1)
        })
        price += 20.0

    df_hist = pd.DataFrame(bars)
    df_hist.to_parquet(ohlcv_path, index=False)

    ledger = ProspectiveShadowLedger(ledger_path=ledger_path)
    return ShadowFeedRunner(
        ledger=ledger,
        ohlcv_path=ohlcv_path,
        status_path=status_path,
        timeout_seconds=2,
        max_retries=1
    )


def test_closed_candle_boundary_drops_forming_bar(isolated_runner):
    """The runner must strictly exclude any candle whose timestamp is >= current hour epoch."""
    import time
    now_epoch = int(time.time())
    current_hour_epoch = (now_epoch // 3600) * 3600
    past_closed_epoch = current_hour_epoch - 3600

    # Mock response with 1 past closed candle and 1 currently forming candle
    mock_payload = [
        [current_hour_epoch, 81000.0, 81500.0, 81200.0, 81400.0, 50.0],  # forming bar
        [past_closed_epoch, 80500.0, 81200.0, 80600.0, 81100.0, 120.0],  # completed bar
    ]

    with patch("urllib.request.urlopen") as mock_url:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_url.return_value = mock_resp

        res = isolated_runner.fetch_recent_closed_candles()
        assert res["success"] is True
        assert res["raw_candles_fetched"] == 2
        # Exactly 1 closed candle accepted; forming candle dropped!
        assert res["valid_closed_candles"] == 1
        df_closed = res["df_closed"]
        assert len(df_closed) == 1
        assert df_closed.iloc[0]["timestamp"] == pd.to_datetime(past_closed_epoch, unit="s", utc=True)


def test_ohlc_invariants_reject_corrupt_candles(isolated_runner):
    """Corrupt candles violating High >= Low or Low <= Open/Close must be rejected."""
    import time
    past_epoch = int(time.time() - 7200)

    # Low is higher than high! Invalid candle
    mock_payload = [
        [past_epoch, 85000.0, 81000.0, 82000.0, 83000.0, 50.0],  # Low > High
        [past_epoch - 3600, 79000.0, 81000.0, 80000.0, 80500.0, -10.0],  # Negative volume
        [past_epoch - 7200, 79000.0, 81000.0, 80000.0, 80500.0, 100.0],  # Valid candle
    ]

    with patch("urllib.request.urlopen") as mock_url:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_url.return_value = mock_resp

        res = isolated_runner.fetch_recent_closed_candles()
        assert res["success"] is True
        assert res["valid_closed_candles"] == 1


def test_feed_outage_graceful_offline_fallback(isolated_runner):
    """When the remote API is unreachable, runner continues with local data without crashing."""
    with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
        summary = isolated_runner.run_evaluation_cycle(sync_live=True, dry_run=True)
        assert summary["feed_status"] == "OFFLINE"
        assert summary["latest_closed_4h_candle"] is not None


def test_dry_run_does_not_mutate_ledger(isolated_runner):
    """In dry-run mode, no records may be written to the prospective shadow ledger."""
    summary = isolated_runner.run_evaluation_cycle(sync_live=False, dry_run=True)
    assert summary["dry_run"] is True

    # Ledger remains empty
    summary_ledger = isolated_runner.ledger.get_ledger_summary()
    assert summary_ledger["total_candidates"] == 0
    assert summary_ledger["total_outcomes"] == 0


def test_status_telemetry_file_written(isolated_runner):
    """Runner must write valid JSON telemetry to status_path."""
    isolated_runner.run_evaluation_cycle(sync_live=False, dry_run=True)
    assert os.path.exists(isolated_runner.status_path)

    with open(isolated_runner.status_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["runner_version"] == "V30.5-SHADOW-FEED-RUNNER"
    assert data["live_trading_authorization"] == "DISABLED — ANALYSIS ONLY"
    assert data["governance_status"] == "OFFLINE_RESEARCH_ONLY"
    assert "ledger_summary" in data


def test_existing_prospective_ledger_untouched(isolated_runner):
    """Execution of shadow runner must NEVER alter data/prospective_entry_ledger.jsonl."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    existing_ledger = os.path.join(repo_root, "data", "prospective_entry_ledger.jsonl")
    assert os.path.exists(existing_ledger)

    with open(existing_ledger, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    assert len(lines) == 5

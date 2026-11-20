import asyncio
import hashlib
import json
import os
import socket
import subprocess
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from api import market_monitor_routes, routes_tournament
from api.routes_research import SmartEntrySnapshotRequest
from engine.arena_evolution import _get_c2_risk_multiplier
from engine.bitstamp_market_data_service import BitstampMarketDataService
from engine.coinbase_15m_adapter import Coinbase15mAdapter
from engine.decoupled_analysis_engine import DecoupledAnalysisEngine
from engine.range_forecast_service import RangeForecastService
from engine.uncertainty_service import UncertaintyService


def _closed_candles(count=220, *, end_age_hours=0):
    now = pd.Timestamp.now(tz="UTC")
    latest_open = now.floor("h") - pd.Timedelta(hours=end_age_hours + 1)
    start = latest_open - pd.Timedelta(hours=count - 1)
    rows = []
    for index in range(count):
        timestamp = start + pd.Timedelta(hours=index)
        close = 80_000.0 + index * 2.0
        rows.append({
            "timestamp_utc": timestamp.isoformat(),
            "open": close - 1.0,
            "high": close + 2.0,
            "low": close - 2.0,
            "close": close,
            "volume": 10.0,
            "is_closed": True,
        })
    return rows


def _dataframe_snapshot(rows):
    frame = pd.DataFrame(rows).rename(columns={"timestamp_utc": "timestamp"})
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["available_time"] = frame["timestamp"] + pd.Timedelta(hours=1)
    return frame


@pytest.fixture(autouse=True)
def clear_analysis_caches():
    routes_tournament._analysis_request_cache.clear()
    routes_tournament._analysis_digest_cache.clear()


def test_blocked_external_providers_do_not_reach_subprocess_or_socket(monkeypatch):
    monkeypatch.setenv("BTC_DATA_MODE", "fixture")
    subprocess_run = Mock(side_effect=AssertionError("subprocess must not run"))
    socket_create = Mock(side_effect=AssertionError("socket must not be created"))
    monkeypatch.setattr(subprocess, "run", subprocess_run)
    monkeypatch.setattr(socket, "socket", socket_create)

    with pytest.raises(RuntimeError, match="strictly prohibits external network calls"):
        BitstampMarketDataService().fetch_raw_bitstamp_ohlcv()
    with pytest.raises(RuntimeError, match="strictly prohibits external network calls"):
        Coinbase15mAdapter().fetch_single_chunk()

    subprocess_run.assert_not_called()
    socket_create.assert_not_called()


def test_stale_local_candle_cache_is_never_reported_fresh_or_live(monkeypatch):
    monkeypatch.setenv("BTC_DATA_MODE", "offline_research")
    from engine import bitstamp_market_data_service

    parquet_path = bitstamp_market_data_service.BITSTAMP_PARQUET_PATH
    monkeypatch.setattr(
        os.path,
        "exists",
        lambda path: path == parquet_path
    )
    stale_frame = _dataframe_snapshot(_closed_candles(240, end_age_hours=5))
    monkeypatch.setattr(pd, "read_parquet", lambda _: stale_frame.copy())
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    response = asyncio.run(market_monitor_routes.market_candles(
        request, symbol="BTC-USD", interval="1h", limit=500
    ))
    assert response["status"] == "STALE"
    assert response["freshness_status"] == "STALE"
    assert response["source"] == "LOCAL_BITSTAMP_CACHE"
    assert response["status"] != "LIVE"
    assert response["count"] == 240


def test_analysis_consumes_exact_validated_frontend_snapshot(monkeypatch):
    monkeypatch.setenv("BTC_DATA_MODE", "fixture")
    routes_tournament._analysis_digest_cache.clear()
    rows = _closed_candles()
    captured = {}

    def analyse(frame, **kwargs):
        captured["frame"] = frame.copy()
        return {
            "status": "SUCCESS",
            "candle_watermark": {
                "total_closed_candles": len(frame),
                "candle_window_sha256": "engine-window-hash",
                "last_closed_timestamp": frame["timestamp"].iloc[-1].isoformat(),
            },
        }

    monkeypatch.setattr(routes_tournament, "analyse_current_market", analyse)
    response = routes_tournament.post_analyse_market(routes_tournament.AnalyseRequestModel(
        data_source="DETERMINISTIC_FIXTURE",
        candles=rows,
        auto_tournament=False,
    ))

    assert captured["frame"]["close"].tolist() == [row["close"] for row in rows]
    assert response["data_provenance"]["submitted_candle_count"] == len(rows)
    assert response["data_provenance"]["analyzed_closed_candle_count"] == len(rows)
    assert response["data_provenance"]["snapshot_id"] == response["data_provenance"]["request_payload_sha256"]
    assert response["data_provenance"]["source"] == "DETERMINISTIC_FIXTURE"
    assert response["data_provenance"]["authorization"] == "OFFLINE_RESEARCH_ONLY"


def test_analysis_http_api_uses_fixed_local_snapshot_and_reports_unavailable_calibration(monkeypatch):
    monkeypatch.setenv("BTC_DATA_MODE", "fixture")

    fixed_now = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz is not None else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(routes_tournament, "datetime", FixedDateTime)
    from engine import regime_strategy_tournament
    monkeypatch.setattr(regime_strategy_tournament, "datetime", FixedDateTime)

    latest_open = pd.Timestamp("2026-11-03T11:00:00Z")
    start = latest_open - pd.Timedelta(hours=219)
    rows = []
    for index in range(220):
        timestamp = (start + pd.Timedelta(hours=index)).strftime("%Y-%m-%dT%H:%M:%SZ")
        close = 80_000 + index * 2
        rows.append({
            "timestamp_utc": timestamp,
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": 10,
            "is_closed": True,
        })

    fixture_sha256 = hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    assert fixture_sha256 == "81e3d4e215fe1c7ef34a8929934bc634bb9c4daf233b6f2046ca3c1215a63964"
    captured = {}

    def analyse(frame, **kwargs):
        captured["frame"] = frame.copy()
        return {
            "status": "ABSTAIN",
            "candle_watermark": {
                "total_closed_candles": len(frame),
                "candle_window_sha256": fixture_sha256,
                "last_closed_timestamp": frame["timestamp"].iloc[-1].isoformat(),
            },
            "calibration_status": "UNAVAILABLE",
            "conformal_calibrated": False,
            "coverage_pct": None,
            "confidence_pct": None,
        }

    monkeypatch.setattr(routes_tournament, "analyse_current_market", analyse)
    from fastapi.testclient import TestClient
    from api.server import app

    client = TestClient(app)
    response = client.post("/api/tournament/analyse", json={
        "data_source": "DETERMINISTIC_FIXTURE",
        "candles": rows,
        "auto_tournament": False,
        "max_age_hours": 2,
    })

    assert response.status_code == 200, response.text
    payload = response.json()
    assert captured["frame"]["close"].tolist() == [row["close"] for row in rows]
    assert payload["data_provenance"]["snapshot_id"] == fixture_sha256
    assert payload["data_provenance"]["request_payload_sha256"] == fixture_sha256
    assert payload["data_provenance"]["submitted_candle_count"] == 220
    assert payload["data_provenance"]["analyzed_closed_candle_count"] == 220
    assert payload["data_provenance"]["source"] == "DETERMINISTIC_FIXTURE"
    assert payload["data_provenance"]["authorization"] == "OFFLINE_RESEARCH_ONLY"
    assert payload["data_freshness_status"] == "FRESH"
    assert payload["calibration_status"] == "UNAVAILABLE"
    assert payload["conformal_calibrated"] is False
    assert payload["coverage_pct"] is None
    assert payload["confidence_pct"] is None


@pytest.mark.parametrize(
    ("mutation", "error_code"),
    [
        ("duplicate", "DUPLICATE_CANDLE_TIMESTAMP"),
        ("gap", "CANDLE_GAP"),
        ("incomplete", "INCOMPLETE_CANDLE"),
        ("malformed", "INVALID_OHLC_GEOMETRY"),
        ("missing_volume", "MALFORMED_CANDLES"),
    ],
)
def test_invalid_analysis_snapshots_fail_closed(monkeypatch, mutation, error_code):
    monkeypatch.setenv("BTC_DATA_MODE", "fixture")
    rows = _closed_candles()
    if mutation == "duplicate":
        rows[10]["timestamp_utc"] = rows[9]["timestamp_utc"]
    elif mutation == "gap":
        rows.pop(10)
    elif mutation == "incomplete":
        rows[-1]["is_closed"] = False
    elif mutation == "malformed":
        rows[-1]["high"] = rows[-1]["low"] - 1
    else:
        rows[-1].pop("volume")

    with pytest.raises(HTTPException) as error:
        routes_tournament.post_analyse_market(routes_tournament.AnalyseRequestModel(
            data_source="DETERMINISTIC_FIXTURE",
            candles=rows,
            auto_tournament=False,
        ))
    assert error.value.status_code == 422
    assert error_code in str(error.value.detail)


def test_analysis_source_defaults_and_calibration_request_parameters_cannot_enable_c2():
    with pytest.raises(ValidationError):
        routes_tournament.AnalyseRequestModel(conformal_calibrated=True)
    with pytest.raises(ValidationError):
        routes_tournament.AnalyseRequestModel(c2_enabled=True)

    result = UncertaintyService().evaluate_uncertainty(
        mfe_p10=0.005, mfe_p90=0.015, exp_mfe=0.01
    )
    assert result.confidence_level == "UNAVAILABLE"
    assert result.coverage_confidence_pct is None


def test_c2_and_missing_or_unknown_calibration_provenance_are_unavailable(monkeypatch):
    engine = DecoupledAnalysisEngine()
    engine.range_service.generate_forecast = lambda **_: SimpleNamespace(
        upper_p10=100.1, upper_p50=100.2, upper_p90=100.3,
        lower_p10=99.9, lower_p50=99.8, lower_p90=99.7,
    )
    frame = _dataframe_snapshot(_closed_candles(240))
    report = engine.compute_market_intelligence_report(
        frame,
        live_price=float(frame["close"].iloc[-1]),
        dataset_fingerprint=None,
    )

    c2 = report["conformal_risk_envelope_7d"]
    assert c2["status"] == "UNAVAILABLE"
    assert c2["calibration_status"] == "DISABLED_BY_GOVERNANCE"
    assert c2["nominal_target_coverage_pct"] is None
    assert report["calibration_health_state"] == "UNAVAILABLE"
    assert report["excursion_estimates_24h"]["calibration_status"] == "UNAVAILABLE"
    assert "not calibrated empirical quantiles" in report["excursion_estimates_24h"]["anti_conflation_notice"]


def test_c2_api_and_source_defaults_cannot_claim_calibration():
    request = SmartEntrySnapshotRequest(
        instrument="BTC-USD",
        timestamp_utc=pd.Timestamp.now(tz="UTC").isoformat(),
    )
    assert request.c2_health == "UNAVAILABLE"
    with pytest.raises(ValidationError):
        SmartEntrySnapshotRequest(
            instrument="BTC-USD",
            timestamp_utc=pd.Timestamp.now(tz="UTC").isoformat(),
            c2_health="CALIBRATED",
        )
    assert _get_c2_risk_multiplier("NORMAL") == 0.0
    assert _get_c2_risk_multiplier("COMPRESSION") == 0.0


def test_scenario_api_rejects_c2_controls():
    from fastapi.testclient import TestClient
    from api.server import app

    client = TestClient(app)
    what_if = client.post("/api/arena/what-if-scenario", json={"c2_enabled": True})
    preview = client.post("/api/arena/scenario-preview", json={"conformal_calibrated": True})
    assert what_if.status_code == 422
    assert preview.status_code == 422


def test_scenario_api_requires_user_boundaries_instead_of_c2_defaults(monkeypatch):
    from fastapi.testclient import TestClient
    from api.server import app
    from api import routes_arena

    monkeypatch.setattr(
        routes_arena.observatory,
        "get_canonical_snapshot",
        lambda: SimpleNamespace(to_dict=lambda: {"rv_5m": 0.0024}),
    )
    client = TestClient(app)
    response = client.post(
        "/api/arena/what-if-scenario",
        json={"spot_price": 64_500.0},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "INPUT_REQUIRED"
    assert response.json()["empirical_conformal_reference"]["status"] == "UNAVAILABLE"


def test_arena_context_suppresses_calibration_and_risk_envelope_claims(monkeypatch):
    from api import routes_arena

    snapshot = routes_arena.observatory.get_canonical_snapshot()
    monkeypatch.setattr(routes_arena.observatory, "get_canonical_snapshot", lambda: snapshot)
    monkeypatch.setattr(routes_arena, "arena_runner", SimpleNamespace(get_status=lambda: {}))

    response = routes_arena.get_arena_context()
    risk = response["context"]["risk"]
    assert risk["nominal_target_coverage"] is None
    assert risk["lower_bound"] is None
    assert risk["upper_bound"] is None
    assert risk["calibration_status"] == "UNAVAILABLE"
    assert response["context"]["model"]["health"] == "UNAVAILABLE"


def test_cross_horizon_api_keeps_calibration_outputs_unavailable():
    from api.server import app
    from fastapi.testclient import TestClient

    response = TestClient(app).get("/api/arena/cross-horizon-profile")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "UNAVAILABLE"
    assert payload["c2_status"] == "DISABLED"
    assert payload["calibration_status"] == "UNAVAILABLE"
    assert payload["question_a_fixed_contract_sensitivity"] == []
    assert payload["question_b_horizon_specific_calibrations"] == []


def test_missing_forecast_health_database_does_not_report_zero_counts(monkeypatch):
    import sqlite3
    from api import routes_prediction
    from backtest import market_memory

    def unavailable_db():
        raise sqlite3.OperationalError("isolated test database unavailable")

    monkeypatch.setattr(market_memory, "_get_db", unavailable_db)
    payload = asyncio.run(routes_prediction.get_prediction_range_health())

    assert payload["status"] == "UNAVAILABLE"
    assert payload["total_forecasts_count"] is None
    assert payload["resolved_valid_count"] is None
    assert payload["quarantined_test_fixtures_count"] is None
    assert payload["unresolved_backlog_count"] is None
    assert payload["resolver_queue_status"] == "UNAVAILABLE"


def test_unverified_accuracy_and_calibration_are_unavailable():
    from api.routes_prediction import get_prediction_accuracy

    payload = get_prediction_accuracy()

    assert payload["status"] == "UNAVAILABLE_UNVERIFIED"
    assert payload["range_accuracy"]["calibration_status"] == "UNAVAILABLE"
    assert payload["range_accuracy"]["p90_mfe_coverage_pct"] is None
    assert payload["range_accuracy"]["p90_mae_coverage_pct"] is None


def test_range_forecast_requires_observed_volatility_and_reports_no_calibration(monkeypatch):
    service = RangeForecastService()
    monkeypatch.setattr(service, "_persist_forecast", lambda *_: None)
    with pytest.raises(ValueError, match="observed 24h volatility"):
        service.generate_forecast(current_price=80_000)

    forecast = service.generate_forecast(
        current_price=80_000,
        vol_24h=0.02,
        features={"vol_24h": 0.02, "rsi_14": 50.0},
    )
    assert forecast.calibration_status == "UNAVAILABLE"
    assert forecast.coverage_confidence is None
    assert forecast.volatility_harvest_signal == "UNAVAILABLE_UNCALIBRATED"
    assert forecast.conformal_trade_setup is None
    assert "not a calibrated quantile forecast" in forecast.natural_language_explanation


@pytest.mark.parametrize("bad_output", [None, {"status": "SUCCESS"}])
def test_analysis_engine_exceptions_or_missing_outputs_fail_safely(monkeypatch, bad_output):
    monkeypatch.setenv("BTC_DATA_MODE", "fixture")
    rows = _closed_candles()

    def broken(*_, **__):
        if bad_output is None:
            raise RuntimeError("internal detail must not be exposed")
        return bad_output

    monkeypatch.setattr(routes_tournament, "analyse_current_market", broken)
    with pytest.raises(HTTPException) as error:
        routes_tournament.post_analyse_market(routes_tournament.AnalyseRequestModel(
            data_source="DETERMINISTIC_FIXTURE",
            candles=rows,
            auto_tournament=False,
        ))
    assert error.value.status_code == 503
    assert "internal detail" not in str(error.value.detail)
    assert "ANALYSIS_FAILED" in str(error.value.detail) or "ANALYSIS_OUTPUT_UNAVAILABLE" in str(error.value.detail)


def test_missing_feature_row_and_unpersisted_regime_history_are_unavailable(monkeypatch):
    from fastapi import HTTPException
    from api import routes_prediction
    from engine.feature_cache import feature_cache

    monkeypatch.setattr(feature_cache, "get_latest_row", lambda: None)
    with pytest.raises(HTTPException) as error:
        routes_prediction.get_prediction_pipeline_layers()
    assert error.value.status_code == 503
    assert error.value.detail["status"] == "DATA_UNAVAILABLE"

    history = routes_prediction.get_prediction_market_state_history(limit=3)
    assert history["status"] == "UNAVAILABLE"
    assert history["count"] is None
    assert history["history"] == []


def test_empty_strategy_accounts_do_not_report_zero_win_rate(monkeypatch):
    from api import routes_arena
    from engine import arena_accounts

    monkeypatch.setattr(arena_accounts, "get_all_accounts", lambda: [
        {"strategy_name": name} for name in arena_accounts.STRATEGY_NAMES
    ])
    response = routes_arena.get_strategy_summary()
    assert response["strategies"]
    assert all(item["win_rate_pct"] is None for item in response["strategies"])
    assert all(item["nav"] is None for item in response["strategies"])

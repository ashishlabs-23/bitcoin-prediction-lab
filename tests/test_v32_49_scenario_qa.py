"""V32.49 regressions for chart provenance, candle integrity and simulated lifecycle."""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import api.routes_tournament as tournament_routes
import engine.regime_strategy_tournament as tournament_engine
from api.server import app
from engine.regime_strategy_tournament import (
    analyse_current_market,
    check_data_freshness_and_gaps,
    formulate_smart_entry_decision,
    run_strategy_tournament_backtest,
)
from engine.smart_entry_simulator import SmartEntrySimulator


client = TestClient(app)


def _bars(count: int = 168, *, end_age_seconds: int = 3600) -> pd.DataFrame:
    """Build deterministic synthetic bars for code-path tests only."""
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(seconds=end_age_seconds)
    start = end - timedelta(hours=count - 1)
    rows = []
    for index in range(count):
        close = 80_000.0 + index
        rows.append({
            "timestamp_utc": (start + timedelta(hours=index)).isoformat(),
            "open": close - 1.0,
            "high": close + 100.0,
            "low": close - 100.0,
            "close": close,
            "volume": 10.0,
            "is_closed": True,
        })
    return pd.DataFrame(rows)


def _decision(direction: str = "LONG", *, forecast_direction: str | None = None, forecast_risk: float = 0.02) -> dict:
    entry = 100.0
    target, stop = (110.0, 90.0) if direction == "LONG" else (90.0, 110.0)
    return {
        "decision_id": f"dec-{direction.lower()}",
        "status": "SMART_ENTRY_AVAILABLE",
        "candidate_setup": {
            "strategy_id": "TEST_STRATEGY",
            "strategy_name": "Test strategy",
            "version": "1.0.0",
            "tournament_id": f"tournament-{direction.lower()}",
            "direction": direction,
            "entry_reference_price": entry,
            "proposed_tp_price": target,
            "proposed_sl_price": stop,
            "max_duration_hours": 24,
            "latest_ai_forecast": {
                "forecast_direction": forecast_direction or ("UP" if direction == "LONG" else "DOWN"),
                "forecast_risk": forecast_risk,
            },
        },
    }


@pytest.mark.parametrize("count,expected", [(167, "Insufficient warm-up"), (168, None)])
def test_warmup_boundary(count: int, expected: str | None) -> None:
    result = analyse_current_market(_bars(count), enforce_freshness=False)
    if expected:
        assert result["status"] == "ABSTAIN"
        assert expected.lower() in result["reason"].lower()
    else:
        assert result["data_integrity"]["is_valid"] is True
        assert result["candle_watermark"]["total_closed_candles"] == 168


@pytest.mark.parametrize(
    "mutation,expected_code",
    [
        ("duplicate", "DUPLICATE_CANDLE_TIMESTAMP"),
        ("out_of_order", "OUT_OF_ORDER_CANDLES"),
        ("gap", "CANDLE_GAP"),
        ("nan", "MALFORMED_CANDLES"),
        ("infinity", "MALFORMED_CANDLES"),
        ("null", "MALFORMED_CANDLES"),
        ("text", "MALFORMED_CANDLES"),
        ("impossible", "INVALID_OHLC_GEOMETRY"),
        ("nonpositive", "INVALID_PRICE"),
        ("missing_volume", "MALFORMED_CANDLES"),
    ],
)
def test_invalid_candle_windows_fail_closed(mutation: str, expected_code: str) -> None:
    frame = _bars()
    if mutation == "duplicate":
        frame.loc[10, "timestamp_utc"] = frame.loc[9, "timestamp_utc"]
    elif mutation == "out_of_order":
        frame.loc[[10, 11], "timestamp_utc"] = frame.loc[[11, 10], "timestamp_utc"].to_numpy()
    elif mutation == "gap":
        shifted = pd.to_datetime(frame.loc[10:, "timestamp_utc"], utc=True) + pd.Timedelta(hours=2)
        frame.loc[10:, "timestamp_utc"] = [value.isoformat() for value in shifted]
    elif mutation == "nan":
        frame.loc[3, "close"] = float("nan")
    elif mutation == "infinity":
        frame.loc[3, "high"] = float("inf")
    elif mutation == "null":
        frame.loc[3, "volume"] = None
    elif mutation == "text":
        frame["open"] = frame["open"].astype(object)
        frame.loc[3, "open"] = "not-a-price"
    elif mutation == "impossible":
        frame.loc[3, "high"] = frame.loc[3, "low"] - 1
    elif mutation == "nonpositive":
        frame.loc[3, "close"] = 0
    elif mutation == "missing_volume":
        frame = frame.drop(columns=["volume"])

    result = analyse_current_market(frame, enforce_freshness=False)
    assert result["status"] == "ABSTAIN"
    assert expected_code in result["reason"]
    assert result["shortlisted_candidates"] == []
    assert result["attempts_created"] == 0


@pytest.mark.parametrize(
    "age_seconds,expected",
    [(7199, True), (7200, False), (7201, False)],
)
def test_freshness_cutoff_is_strict(age_seconds: int, expected: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    fixed_now = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(tournament_engine, "datetime", FixedDateTime)
    frame = _bars(end_age_seconds=age_seconds)
    last_time = pd.to_datetime(frame.iloc[-1]["timestamp_utc"], utc=True)
    frame.loc[len(frame) - 1, "timestamp_utc"] = (fixed_now - timedelta(seconds=age_seconds)).isoformat()
    frame.loc[: len(frame) - 2, "timestamp_utc"] = [
        (fixed_now - timedelta(seconds=age_seconds + 3600 * (len(frame) - 1 - index))).isoformat()
        for index in range(len(frame) - 1)
    ]
    freshness = check_data_freshness_and_gaps(frame, max_age_hours=2.0)
    assert freshness["is_fresh"] is expected
    assert freshness["freshness_status"] == ("FRESH" if expected else "MARKET_DATA_STALE")
    assert last_time is not None


def test_open_bar_is_excluded_before_validation_and_hashing() -> None:
    frame = _bars()
    baseline = analyse_current_market(frame, enforce_freshness=False)
    open_bar = frame.iloc[-1].copy()
    open_bar["timestamp_utc"] = frame.iloc[-1]["timestamp_utc"]
    open_bar["high"] = float("inf")
    open_bar["is_closed"] = False
    with_open = pd.concat([frame, open_bar.to_frame().T], ignore_index=True)
    result = analyse_current_market(with_open, enforce_freshness=False)
    assert result.get("status") == baseline.get("status")
    assert result["attempts_created"] == 0
    assert result["candle_watermark"]["candle_window_sha256"] == baseline["candle_watermark"]["candle_window_sha256"]


def test_analyse_api_uses_exact_submitted_window_and_retries_idempotently(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _bars()
    submitted = frame.to_dict(orient="records")
    captured: list[pd.DataFrame] = []
    calls = 0

    def fake_execute(**kwargs):
        nonlocal calls
        calls += 1
        captured.append(kwargs["df_1h"].copy())
        closed = kwargs["df_1h"]
        return {
            "analysis_id": "analysis-window-test",
            "is_read_only": True,
            "attempts_created": 0,
            "candle_watermark": {
                "last_closed_timestamp": closed.iloc[-1]["timestamp_utc"],
                "candle_window_sha256": tournament_engine._closed_candle_window_hash(closed),
                "total_closed_candles": len(closed),
            },
            "shortlisted_candidates": [],
            "candidate_rejections": [],
            "tournament": {"execution_source": "CACHED_WALK_FORWARD_EVALUATION"},
            "smart_entry_decision": {"status": "NO_SMART_ENTRY", "action": "ABSTAIN", "candidate_setup": None},
        }

    monkeypatch.setattr(tournament_routes, "execute_integrated_analyse_and_tournament", fake_execute)
    request = {
        "instrument": "BTC-USD",
        "timeframe": "1h",
        "data_source": "COINBASE_EXCHANGE_REST",
        "request_id": "v32-49-idempotent-analysis",
        "candles": submitted,
        "auto_tournament": True,
    }
    first = client.post("/api/tournament/analyse", json=request)
    retry = client.post("/api/tournament/analyse", json=request)
    assert first.status_code == retry.status_code == 200
    assert first.json()["analysis_id"] == retry.json()["analysis_id"] == "analysis-window-test"
    assert len(captured) == calls == 1
    pd.testing.assert_frame_equal(captured[0].reset_index(drop=True), pd.DataFrame(submitted).reset_index(drop=True), check_dtype=False)
    provenance = first.json()["data_provenance"]
    assert provenance["source"] == "COINBASE_EXCHANGE_REST"
    assert provenance["analyzed_closed_candle_count"] == len(submitted)
    assert provenance["request_payload_sha256"] == hashlib.sha256(
        json.dumps(submitted, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    assert provenance["analyzed_window_sha256"] == first.json()["candle_watermark"]["candle_window_sha256"]


def test_analyse_api_rejects_request_id_reuse_with_different_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tournament_routes, "execute_integrated_analyse_and_tournament", lambda **kwargs: {
        "analysis_id": "cached",
        "candle_watermark": {"total_closed_candles": len(kwargs["df_1h"]), "candle_window_sha256": "hash"},
        "shortlisted_candidates": [],
        "tournament": None,
        "smart_entry_decision": {"status": "NO_SMART_ENTRY", "action": "ABSTAIN", "candidate_setup": None},
    })
    frame = _bars()
    payload = {
        "request_id": "v32-49-payload-conflict",
        "data_source": "COINBASE_EXCHANGE_REST",
        "candles": frame.to_dict(orient="records"),
    }
    assert client.post("/api/tournament/analyse", json=payload).status_code == 200
    payload["candles"][0]["close"] += 1
    conflict = client.post("/api/tournament/analyse", json=payload)
    assert conflict.status_code == 409
    assert "different analysis payload" in conflict.json()["detail"]


@pytest.mark.parametrize(
    "force_fresh,expected_source",
    [
        (False, "CACHED_WALK_FORWARD_UNAVAILABLE"),
        (True, "FRESH_EVALUATION_BLOCKED"),
    ],
)
def test_tournament_does_not_present_unverified_metrics(force_fresh: bool, expected_source: str) -> None:
    candidate = {
        "strategy_id": "TSMOM_DONCHIAN_24H_168H",
        "strategy_name": "Test-only candidate",
        "version": "1.0.0",
        "screen_7_of_10": {"passed": True, "tp_hits": 7, "total_attempts": 10},
    }
    result = run_strategy_tournament_backtest(
        [candidate],
        current_regime="TRENDING_BULLISH",
        force_fresh=force_fresh,
        historical_df=_bars() if force_fresh else None,
    )
    assert result["execution_source"] == expected_source
    assert result["cache_validation"]["hashes_matched"] is False
    assert result["cache_validation"]["newly_executed"] is False
    assert result["candidate_results"] == []
    assert result["baseline_comparator"] is None
    assert result["tournament_winner"] is None
    assert result["final_verdict"] == "ABSTAIN"
    assert "No arm metrics were computed or reused" in result["verdict_explanation"]
    assert result["attempts_created"] == 0


def test_tournament_is_explicitly_skipped_when_no_candidates_qualify() -> None:
    result = run_strategy_tournament_backtest([], current_regime="UNKNOWN_OR_INVALID")
    assert result["execution_source"] == "NOT_RUN_NO_ELIGIBLE_CANDIDATES"
    assert result["candidate_results"] == []
    assert result["final_verdict"] == "ABSTAIN"
    assert result["attempts_created"] == 0


def test_no_candidate_abstention_explains_screen_rejections_and_safe_next_step() -> None:
    decision = formulate_smart_entry_decision(
        analysis_res={
            "status": "ABSTAIN",
            "reason": "No shortlisted candidates provided for tournament evaluation.",
            "shortlisted_candidates": [],
            "candidate_rejections": [{"strategy_id": f"REJECTED_{index}"} for index in range(5)],
        },
        tournament_res={
            "final_verdict": "ABSTAIN",
            "execution_source": "NOT_RUN_NO_ELIGIBLE_CANDIDATES",
            "tournament_winner": None,
        },
    )
    assert decision["status"] == "NO_SMART_ENTRY"
    assert "No strategy passed the current eligibility screen." in decision["reason"]
    assert "rejected 5 strategies" in decision["reason"]
    assert "tournament was skipped" in decision["reason"]
    assert "no simulated attempt was created" in decision["reason"]


@pytest.mark.parametrize(
    "direction,entry,target,stop,valid",
    [
        ("LONG", 100, 110, 90, True),
        ("SHORT", 100, 90, 110, True),
        ("LONG", 100, 90, 110, False),
        ("SHORT", 100, 110, 90, False),
        ("LONG", 100, 100, 90, False),
        ("LONG", 100, float("nan"), 90, False),
    ],
)
def test_entry_geometry_is_direction_aware_and_finite(
    tmp_path, direction: str, entry: float, target: float, stop: float, valid: bool
) -> None:
    sim = SmartEntrySimulator(str(tmp_path / "attempts.jsonl"))
    decision = _decision(direction)
    candidate = decision["candidate_setup"]
    candidate.update({
        "entry_reference_price": entry,
        "proposed_tp_price": target,
        "proposed_sl_price": stop,
    })
    attempt, error = sim.enter_simulated_trade(decision, entry_price=entry)
    assert (attempt is not None) is valid
    assert (error is None) is valid
    if attempt:
        assert attempt.direction == direction
        assert attempt.reward_risk_ratio == 1.0


def test_entry_idempotency_is_atomic_and_survives_restart(tmp_path) -> None:
    ledger = str(tmp_path / "attempts.jsonl")
    sim = SmartEntrySimulator(ledger)
    decision = _decision()

    def enter(_):
        return sim.enter_simulated_trade(decision, entry_price=100.0, idempotency_key="same-click")[0]

    with ThreadPoolExecutor(max_workers=8) as pool:
        attempts = list(pool.map(enter, range(16)))
    assert len({attempt.attempt_id for attempt in attempts if attempt}) == 1
    with open(ledger, encoding="utf-8") as stream:
        records = [json.loads(line) for line in stream if line.strip()]
    assert sum(record["event_type"] == "ATTEMPT_ENTERED" for record in records) == 1

    restored = SmartEntrySimulator(ledger)
    retried, error = restored.enter_simulated_trade(decision, entry_price=101.0, idempotency_key="same-click")
    assert error is None
    assert retried.attempt_id == attempts[0].attempt_id
    assert retried.reference_entry_price == 100.0


@pytest.mark.parametrize(
    "entry_direction,forecast_direction,expected_alert",
    [
        ("LONG", "UP", False),
        ("LONG", "DOWN", True),
        ("SHORT", "DOWN", False),
        ("SHORT", "UP", True),
    ],
)
def test_monitor_direction_flip_is_position_aware(
    tmp_path, entry_direction: str, forecast_direction: str, expected_alert: bool
) -> None:
    sim = SmartEntrySimulator(str(tmp_path / f"{entry_direction}-{forecast_direction}.jsonl"))
    attempt, error = sim.enter_simulated_trade(_decision(entry_direction), entry_price=100)
    assert error is None
    updated, events = sim.monitor_active_attempt(
        attempt.attempt_id,
        current_price=100,
        current_forecast={"forecast_direction": forecast_direction, "forecast_risk": 0.02},
    )
    assert updated.direction_change_alert is expected_alert
    assert any(event.get("event_type", event.get("event")) == "FORECAST_DIRECTION_FLIP" for event in events) is expected_alert
    assert updated.frozen_tp_price == attempt.frozen_tp_price
    assert updated.frozen_sl_price == attempt.frozen_sl_price


@pytest.mark.parametrize(
    "risk,expected_alert",
    [(0.0298, False), (0.03, True), (0.0302, True)],
)
def test_monitor_risk_spike_uses_inclusive_150_percent_boundary(tmp_path, risk: float, expected_alert: bool) -> None:
    sim = SmartEntrySimulator(str(tmp_path / f"risk-{risk}.jsonl"))
    attempt, error = sim.enter_simulated_trade(_decision(forecast_risk=0.02), entry_price=100)
    assert error is None
    updated, events = sim.monitor_active_attempt(
        attempt.attempt_id,
        current_price=100,
        current_forecast={"forecast_direction": "UP", "forecast_risk": risk},
    )
    assert updated.risk_spike_alert is expected_alert
    assert any(event["event_type"] == "FORECAST_RISK_SPIKE" for event in events) is expected_alert


def test_malformed_forecast_degrades_without_fabricating_alerts(tmp_path) -> None:
    sim = SmartEntrySimulator(str(tmp_path / "malformed.jsonl"))
    attempt, error = sim.enter_simulated_trade(_decision(), entry_price=100)
    assert error is None
    updated, events = sim.monitor_active_attempt(
        attempt.attempt_id,
        current_price=100,
        current_forecast={"forecast_direction": "DOWN", "probability_up": float("nan")},
    )
    assert updated.data_quality_state == "DEGRADED_MALFORMED_FORECAST"
    assert not updated.direction_change_alert
    assert not updated.risk_spike_alert
    assert [event.get("event_type") for event in events] == ["DATA_FEED_DEGRADED"]


def test_missing_forecast_degrades_and_monitor_state_recovers_after_restart(tmp_path) -> None:
    ledger = str(tmp_path / "monitor-recovery.jsonl")
    sim = SmartEntrySimulator(ledger)
    attempt, error = sim.enter_simulated_trade(_decision(), entry_price=100)
    assert error is None

    degraded, events = sim.monitor_active_attempt(attempt.attempt_id, current_price=100, current_forecast=None)
    assert degraded.data_quality_state == "DEGRADED_FORECAST_UNAVAILABLE"
    assert degraded.last_monitored_at_utc is not None
    assert any(event["event_type"] == "DATA_FEED_DEGRADED" for event in events)

    restored = SmartEntrySimulator(ledger)
    recovered, events = restored.monitor_active_attempt(
        attempt.attempt_id,
        current_price=100,
        current_forecast={"forecast_direction": "UP", "forecast_risk": 0.02},
    )
    assert recovered.data_quality_state == "NORMAL"
    assert recovered.last_monitored_at_utc is not None
    assert any(event["event_type"] == "DATA_FEED_RECOVERED" for event in events)


def test_out_of_order_forecasts_do_not_replace_latest_snapshot_or_raise_false_alerts(tmp_path) -> None:
    ledger = str(tmp_path / "forecast-order.jsonl")
    sim = SmartEntrySimulator(ledger)
    attempt, error = sim.enter_simulated_trade(_decision(), entry_price=100)
    assert error is None
    latest_timestamp = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    older_timestamp = (datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat()

    updated, _ = sim.monitor_active_attempt(
        attempt.attempt_id,
        current_price=100,
        current_forecast={
            "timestamp_utc": latest_timestamp,
            "forecast_direction": "UP",
            "forecast_risk": 0.02,
        },
    )
    assert updated.last_forecast_timestamp_utc == latest_timestamp
    count_before_old_update = sum(
        event.get("event_type") == "FORECAST_SNAPSHOT" for event in updated.events
    )

    duplicate, duplicate_events = sim.monitor_active_attempt(
        attempt.attempt_id,
        current_price=100,
        current_forecast={
            "timestamp_utc": latest_timestamp,
            "forecast_direction": "DOWN",
            "forecast_risk": 0.04,
        },
    )
    assert duplicate.last_forecast_timestamp_utc == latest_timestamp
    assert not duplicate.direction_change_alert
    assert not duplicate.risk_spike_alert
    assert sum(event.get("event_type") == "FORECAST_SNAPSHOT" for event in duplicate.events) == count_before_old_update
    assert not any(event.get("event_type") == "FORECAST_DIRECTION_FLIP" for event in duplicate_events)

    updated, events = sim.monitor_active_attempt(
        attempt.attempt_id,
        current_price=100,
        current_forecast={
            "timestamp_utc": older_timestamp,
            "forecast_direction": "DOWN",
            "forecast_risk": 0.04,
        },
    )
    assert updated.last_forecast_timestamp_utc == latest_timestamp
    assert updated.current_forecast_snapshot["forecast_direction"] == "UP"
    assert not updated.direction_change_alert
    assert not updated.risk_spike_alert
    assert sum(event.get("event_type") == "FORECAST_SNAPSHOT" for event in updated.events) == count_before_old_update
    assert not any(event.get("event_type") == "FORECAST_DIRECTION_FLIP" for event in events)

    restored = SmartEntrySimulator(ledger).attempts[attempt.attempt_id]
    assert restored.last_forecast_timestamp_utc == latest_timestamp
    assert restored.current_forecast_snapshot["forecast_direction"] == "UP"


def test_continue_choice_persists_and_dual_touch_remains_unresolved(tmp_path) -> None:
    ledger = str(tmp_path / "lifecycle.jsonl")
    sim = SmartEntrySimulator(ledger)
    attempt, error = sim.enter_simulated_trade(_decision(), entry_price=100)
    assert error is None
    continued, continue_error = sim.user_continue(attempt.attempt_id, "acknowledged")
    assert continue_error is None
    assert continued.status == "ACTIVE"
    assert continued.frozen_tp_price == 110
    restored = SmartEntrySimulator(ledger)
    assert any(event.get("event_type") == "USER_CONTINUED" for event in restored.attempts[attempt.attempt_id].events)
    unresolved, events = restored.monitor_active_attempt(
        attempt.attempt_id,
        candle={"open": 100, "high": 111, "low": 89, "close": 101},
    )
    assert unresolved.status == "UNRESOLVED_INTRABAR_ORDER"
    assert any(event.get("status") == "UNRESOLVED_INTRABAR_ORDER" for event in events)


def test_partial_exit_then_continue_persists_active_remainder(tmp_path) -> None:
    ledger = str(tmp_path / "partial-continue.jsonl")
    sim = SmartEntrySimulator(ledger)
    attempt, error = sim.enter_simulated_trade(_decision(), entry_price=100)
    assert error is None
    partial, partial_error = sim.user_partial_exit(attempt.attempt_id, exit_price=105, ratio=0.5)
    assert partial_error is None
    assert partial.status == "ACTIVE"
    assert partial.remaining_ratio == 0.5

    continued, continue_error = sim.user_continue(attempt.attempt_id, "keep monitoring remainder")
    assert continue_error is None
    assert continued.status == "ACTIVE"
    assert continued.remaining_ratio == 0.5
    assert continued.frozen_tp_price == 110
    assert continued.frozen_sl_price == 90

    restored = SmartEntrySimulator(ledger).attempts[attempt.attempt_id]
    assert restored.status == "ACTIVE"
    assert restored.remaining_ratio == 0.5
    assert len(restored.partial_exits) == 1
    assert any(event.get("event_type") == "USER_CONTINUED" for event in restored.events)


def test_api_entry_rejects_stale_or_non_chart_provenance(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    sim = SmartEntrySimulator(str(tmp_path / "api-entry.jsonl"))
    monkeypatch.setattr(tournament_routes, "get_smart_entry_simulator", lambda: sim)
    decision = _decision()
    missing = client.post("/api/tournament/smart-entry/enter", json={"decision_payload": decision})
    assert missing.status_code == 409
    assert "no verified chart-data provenance" in missing.json()["detail"]
    decision["data_provenance"] = {
        "instrument": "BTC-USD",
        "timeframe": "1h",
        "source": "SERVER_HISTORICAL_DATA",
        "latest_closed_timestamp": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        "analyzed_window_sha256": "window-hash",
    }
    rejected = client.post("/api/tournament/smart-entry/enter", json={"decision_payload": decision})
    assert rejected.status_code == 409
    assert client.get("/api/tournament/smart-entry/attempts").json()["total_attempts"] == 0


def test_api_entry_rejects_expired_proposal_and_accepts_fresh_chart_provenance(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    sim = SmartEntrySimulator(str(tmp_path / "fresh-api-entry.jsonl"))
    monkeypatch.setattr(tournament_routes, "get_smart_entry_simulator", lambda: sim)
    decision = _decision()
    watermark = {
        "last_closed_timestamp": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
        "candle_window_sha256": "window-hash",
    }
    decision["candidate_setup"]["candle_watermark"] = watermark
    decision["data_provenance"] = {
        "instrument": "BTC-USD",
        "timeframe": "1h",
        "source": "COINBASE_EXCHANGE_REST",
        "latest_closed_timestamp": watermark["last_closed_timestamp"],
        "analyzed_window_sha256": "window-hash",
    }
    stale = client.post("/api/tournament/smart-entry/enter", json={"decision_payload": decision})
    assert stale.status_code == 409
    assert sim.attempts == {}

    fresh_timestamp = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    decision["candidate_setup"]["candle_watermark"]["last_closed_timestamp"] = fresh_timestamp
    decision["data_provenance"]["latest_closed_timestamp"] = fresh_timestamp
    created = client.post("/api/tournament/smart-entry/enter", json={
        "decision_payload": decision,
        "entry_price": 100,
        "idempotency_key": "api-entry-once",
    })
    retried = client.post("/api/tournament/smart-entry/enter", json={
        "decision_payload": decision,
        "entry_price": 101,
        "idempotency_key": "api-entry-once",
    })
    assert created.status_code == retried.status_code == 200
    assert created.json()["attempt"]["attempt_id"] == retried.json()["attempt"]["attempt_id"]
    assert len(sim.attempts) == 1


def test_analysis_schema_blocks_wrong_instrument_and_timeframe() -> None:
    assert client.post("/api/tournament/analyse", json={"instrument": "BTC-USDT"}).status_code == 422
    assert client.post("/api/tournament/analyse", json={"timeframe": "4h"}).status_code == 422

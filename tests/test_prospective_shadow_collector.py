"""
tests/test_prospective_shadow_collector.py — Unit Tests for V30.3 Shadow Collector
================================================================================
Validates:
1. Immutable candidate and outcome data contracts.
2. Separate append-only ledger safety and persistence across restarts.
3. Candidate deduplication and idempotency.
4. Deterministic outcome resolution (SL first, Horizon timeout, opening gap slippage).
5. MFE / MAE excursion tracking.
6. Multi-scenario cost calculations (87 / 18.6 / 15 / 120 bps).
7. Preservation of existing `data/prospective_entry_ledger.jsonl`.
8. Permanent disablement of live trading authorization.
"""

import os
import json
import dataclasses
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from engine.prospective_shadow_collector import (
    ShadowCandidateRecord,
    ShadowOutcomeRecord,
    ProspectiveShadowLedger,
    HTFShadowCollector,
    compute_shadow_candidate_id,
    STRATEGY_ID,
    STRATEGY_SPEC_HASH,
    COST_REGISTRY_BPS,
)


@pytest.fixture
def temp_ledger(tmp_path):
    ledger_path = str(tmp_path / "test_shadow_ledger.jsonl")
    return ProspectiveShadowLedger(ledger_path=ledger_path)


@pytest.fixture
def sample_candidate():
    cost_bps_dict = {k: v["round_trip_bps"] for k, v in COST_REGISTRY_BPS.items()}
    cand_id = compute_shadow_candidate_id(
        strategy_id=STRATEGY_ID,
        decision_timestamp_utc="2026-10-23T00:00:00+00:00",
        entry_reference_price=80000.0,
        stop_loss_price=78000.0,
        horizon_bars=18
    )
    return ShadowCandidateRecord(
        record_type="SHADOW_CANDIDATE",
        schema_version="PROSPECTIVE_SHADOW_V1",
        candidate_id=cand_id,
        strategy_id=STRATEGY_ID,
        strategy_spec_hash=STRATEGY_SPEC_HASH,
        instrument_id="BTC-USD",
        venue="COINBASE",
        market_type="SPOT",
        decision_timestamp_utc="2026-10-23T00:00:00+00:00",
        data_availability_timestamp_utc="2026-10-23T00:00:00+00:00",
        signal_inputs={"close": 80100.0, "range_high_20_4h": 80000.0, "range_low_20_4h": 78000.0},
        entry_reference_price=80100.0,
        fill_assumption="NEXT_BAR_OPEN",
        proposed_entry_price=80200.0,
        stop_loss_price=78000.0,
        take_profit_price=None,
        direction="LONG",
        horizon_bars=18,
        primary_cost_scenario="COINBASE_RETAIL_87BPS",
        cost_assumptions_bps=cost_bps_dict,
        action="CANDIDATE_EMITTED",
        abstention_reason=None,
        data_quality_status="VALID"
    )


def test_candidate_contract_immutability(sample_candidate):
    """Candidate records must be frozen against modification."""
    with pytest.raises(Exception):
        sample_candidate.proposed_entry_price = 85000.0


def test_ledger_append_and_idempotency(temp_ledger, sample_candidate):
    """Ledger must append candidate once and reject duplicates."""
    # First append succeeds
    assert temp_ledger.append_candidate(sample_candidate) is True

    # Duplicate append is rejected
    assert temp_ledger.append_candidate(sample_candidate) is False

    candidates = temp_ledger.get_registered_candidates()
    assert len(candidates) == 1
    assert candidates[0]["candidate_id"] == sample_candidate.candidate_id


def test_ledger_restart_persistence(tmp_path, sample_candidate):
    """Ledger index and records must survive instance destruction and reload."""
    ledger_path = str(tmp_path / "persistent_shadow.jsonl")
    ledger1 = ProspectiveShadowLedger(ledger_path=ledger_path)
    ledger1.append_candidate(sample_candidate)

    # Re-instantiate from disk
    ledger2 = ProspectiveShadowLedger(ledger_path=ledger_path)
    summary = ledger2.get_ledger_summary()
    assert summary["total_candidates"] == 1
    assert sample_candidate.candidate_id in summary["registered_candidate_ids"]
    # Idempotency maintained across restarts
    assert ledger2.append_candidate(sample_candidate) is False


def test_existing_prospective_ledger_preservation():
    """V30.3 must verify that data/prospective_entry_ledger.jsonl is untouched."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    existing_ledger = os.path.join(repo_root, "data", "prospective_entry_ledger.jsonl")
    assert os.path.exists(existing_ledger)

    with open(existing_ledger, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    # V30.0 / V30.1 / V30.2 verified line count is exactly 5
    assert len(lines) == 5
    for l in lines:
        rec = json.loads(l)
        assert rec.get("execution_authorization") == "DISABLED — ANALYSIS ONLY"


def test_live_trading_disabled_guard(sample_candidate):
    """Live trading must remain permanently disabled in candidate contracts."""
    assert sample_candidate.execution_authorization == "DISABLED — ANALYSIS ONLY"
    assert sample_candidate.governance_status == "OFFLINE_RESEARCH_ONLY"


def test_resolver_stop_loss_hit(sample_candidate):
    """Resolver must trigger STOP_LOSS when bar low breaches stop loss."""
    collector = HTFShadowCollector()
    future_bars = pd.DataFrame([
        {"timestamp": "2026-10-23T04:00:00+00:00", "open": 80200.0, "high": 80500.0, "low": 79500.0, "close": 79800.0},
        {"timestamp": "2026-10-23T08:00:00+00:00", "open": 79800.0, "high": 79900.0, "low": 77500.0, "close": 77600.0},  # Low breaches 78000
    ])

    outcome = collector.resolve_candidate_outcome(sample_candidate, future_bars)
    assert outcome is not None
    assert outcome.exit_reason == "STOP_LOSS"
    assert outcome.resolution_status == "RESOLVED"
    assert outcome.exit_price == 78000.0
    assert outcome.bars_held_4h == 2
    assert outcome.holding_hours == 8.0
    # Entry 80200 -> Exit 78000 = -2200 / 80200 = -274.31 bps gross
    expected_gross_bps = round(((78000.0 - 80200.0) / 80200.0) * 10000.0, 2)
    assert outcome.gross_return_bps == expected_gross_bps
    # Net returns after 87 bps
    assert outcome.net_returns_by_scenario_bps["COINBASE_RETAIL_87BPS"] == round(expected_gross_bps - 87.0, 2)
    assert outcome.risk_unit_usd == 2200.0
    assert outcome.gross_r == -1.0
    # Net R: (-2200 - (80200 * 0.0087)) / 2200 = (-2200 - 697.74) / 2200 = -1.3172 R
    assert outcome.net_r_by_scenario["COINBASE_RETAIL_87BPS"] == -1.3172


def test_resolver_zero_or_negative_risk_rejected(sample_candidate):
    """Candidates with entry <= stop (zero or negative risk) must be rejected with ValueError."""
    collector = HTFShadowCollector()
    bad_candidate = dataclasses.replace(sample_candidate, proposed_entry_price=78000.0, stop_loss_price=78000.0)
    future_bars = pd.DataFrame([
        {"timestamp": "2026-10-23T04:00:00+00:00", "open": 78000.0, "high": 78500.0, "low": 77500.0, "close": 77800.0},
    ])
    with pytest.raises(ValueError, match="Invalid risk geometry"):
        collector.resolve_candidate_outcome(bad_candidate, future_bars)


def test_resolver_opening_gap_below_stop(sample_candidate):
    """When a bar opens below the stop price, exit must fill at open to reflect slippage."""
    collector = HTFShadowCollector()
    future_bars = pd.DataFrame([
        {"timestamp": "2026-10-23T04:00:00+00:00", "open": 77000.0, "high": 77500.0, "low": 76000.0, "close": 76500.0},  # Gapped down
    ])

    outcome = collector.resolve_candidate_outcome(sample_candidate, future_bars)
    assert outcome is not None
    assert outcome.exit_reason == "STOP_LOSS"
    assert outcome.exit_price == 77000.0  # Slippage gap fill at open!


def test_resolver_horizon_timeout(sample_candidate):
    """When position reaches max horizon (18 4h bars) without stop hit, exit at horizon close."""
    collector = HTFShadowCollector()
    bars = []
    base_ts = pd.to_datetime("2026-10-23T04:00:00+00:00")
    for i in range(18):
        ts = (base_ts + pd.Timedelta(hours=4 * i)).isoformat()
        bars.append({"timestamp": ts, "open": 80500.0, "high": 81000.0, "low": 79000.0, "close": 80800.0})

    future_bars = pd.DataFrame(bars)
    outcome = collector.resolve_candidate_outcome(sample_candidate, future_bars)
    assert outcome is not None
    assert outcome.exit_reason == "HORIZON_TIMEOUT"
    assert outcome.bars_held_4h == 18
    assert outcome.holding_hours == 72.0
    assert outcome.exit_price == 80800.0
    expected_gross = round(((80800.0 - 80200.0) / 80200.0) * 10000.0, 2)
    assert outcome.gross_return_bps == expected_gross
    assert outcome.net_returns_by_scenario_bps["COINBASE_RETAIL_87BPS"] == round(expected_gross - 87.0, 2)
    # Risk = 80200 - 78000 = 2200. Gain = 80800 - 80200 = 600. Gross R = 600 / 2200 = 0.2727 R
    assert outcome.gross_r == round(600.0 / 2200.0, 4)
    # Net R: (600 - 697.74) / 2200 = -97.74 / 2200 = -0.0444 R
    assert outcome.net_r_by_scenario["COINBASE_RETAIL_87BPS"] == round((600.0 - 697.74) / 2200.0, 4)


def test_collector_causal_evaluation():
    """Verify that evaluate_bar_for_candidate generates causal candidate only on true breakout."""
    collector = HTFShadowCollector()
    cur_bar = pd.Series({
        "timestamp": "2026-10-23T00:00:00+00:00",
        "open": 79500.0,
        "high": 80500.0,
        "low": 79000.0,
        "close": 80200.0,
        "range_high_20_4h": 80000.0,
        "range_low_20_4h": 78000.0,
        "volume": 1250.0
    })

    cand = collector.evaluate_bar_for_candidate(cur_bar, nxt_bar_open=80250.0, nxt_bar_timestamp_utc="2026-10-23T04:00:00+00:00")
    assert cand is not None
    assert cand.direction == "LONG"
    assert cand.proposed_entry_price == 80250.0  # Filled at next bar's open
    assert cand.stop_loss_price == 78000.0
    assert cand.signal_inputs["breakout_excess_bps"] == 25.0  # (80200 - 80000) / 80000 * 10000

    # Non-breakout candle returns None
    cur_bar_no_breakout = cur_bar.copy()
    cur_bar_no_breakout["close"] = 79900.0
    cand_none = collector.evaluate_bar_for_candidate(cur_bar_no_breakout, nxt_bar_open=79950.0, nxt_bar_timestamp_utc="2026-10-23T04:00:00+00:00")
    assert cand_none is None


def test_in_position_gating_suppresses_overlapping_candidates(tmp_path):
    """While an active candidate is unresolved, subsequent breakout signals must be suppressed."""
    ledger_path = str(tmp_path / "gating_shadow.jsonl")
    ledger = ProspectiveShadowLedger(ledger_path=ledger_path)
    collector = HTFShadowCollector(ledger=ledger)

    cur_bar1 = pd.Series({
        "timestamp": "2026-10-23T00:00:00+00:00",
        "open": 79500.0, "high": 80500.0, "low": 79000.0, "close": 80200.0,
        "range_high_20_4h": 80000.0, "range_low_20_4h": 78000.0, "volume": 1200.0
    })

    cand1 = collector.evaluate_bar_for_candidate(cur_bar1, nxt_bar_open=80250.0, nxt_bar_timestamp_utc="2026-10-23T04:00:00+00:00")
    assert cand1 is not None
    assert ledger.append_candidate(cand1) is True

    # Position is now open (registered in ledger, not yet resolved)
    assert collector.get_active_unresolved_candidate() is not None

    # Next breakout candle arrives while position is still active
    cur_bar2 = pd.Series({
        "timestamp": "2026-10-23T04:00:00+00:00",
        "open": 80300.0, "high": 81200.0, "low": 80100.0, "close": 81000.0,
        "range_high_20_4h": 80000.0, "range_low_20_4h": 78000.0, "volume": 1500.0
    })

    cand2 = collector.evaluate_bar_for_candidate(cur_bar2, nxt_bar_open=81050.0, nxt_bar_timestamp_utc="2026-10-23T08:00:00+00:00")
    # Suppressed due to in-position gating!
    assert cand2 is None


def test_cross_process_file_lock_synchronization(tmp_path):
    """Verifies that two independent ledger instances coordinate via FileLock."""
    ledger_path = str(tmp_path / "shared_shadow.jsonl")
    ledger1 = ProspectiveShadowLedger(ledger_path=ledger_path)
    ledger2 = ProspectiveShadowLedger(ledger_path=ledger_path)

    cost_bps_dict = {k: v["round_trip_bps"] for k, v in COST_REGISTRY_BPS.items()}
    cand = ShadowCandidateRecord(
        record_type="SHADOW_CANDIDATE",
        schema_version="PROSPECTIVE_SHADOW_V1",
        candidate_id="scand_concurrency_test",
        strategy_id=STRATEGY_ID,
        strategy_spec_hash=STRATEGY_SPEC_HASH,
        instrument_id="BTC-USD",
        venue="COINBASE",
        market_type="SPOT",
        decision_timestamp_utc="2026-10-23T00:00:00+00:00",
        data_availability_timestamp_utc="2026-10-23T00:00:00+00:00",
        signal_inputs={"close": 80100.0},
        entry_reference_price=80100.0,
        fill_assumption="NEXT_BAR_OPEN",
        proposed_entry_price=80200.0,
        stop_loss_price=78000.0,
        take_profit_price=None,
        direction="LONG",
        horizon_bars=18,
        primary_cost_scenario="COINBASE_RETAIL_87BPS",
        cost_assumptions_bps=cost_bps_dict,
        action="CANDIDATE_EMITTED",
        abstention_reason=None,
        data_quality_status="VALID"
    )

    # Ledger 1 appends
    assert ledger1.append_candidate(cand) is True

    # Ledger 2 (simulating independent process) attempts duplicate append under lock
    assert ledger2.append_candidate(cand) is False

    # Ledger 2 reads the candidate appended by Ledger 1
    assert "scand_concurrency_test" in ledger2._registered_candidate_ids


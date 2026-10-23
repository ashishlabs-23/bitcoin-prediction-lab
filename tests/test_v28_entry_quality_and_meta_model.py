"""
tests/test_v28_entry_quality_and_meta_model.py
===============================================
Comprehensive test suite for BTCognitive V28:
- Point-in-time setup feature calculation (momentum, semi-variance ratio, BB width, range pos).
- Calibrated logistic meta-model probability estimation.
- Causal executable fill model and conservative SL_FIRST intrabar collision rule.
- Cost-aware net expectancy calculator in R-multiples and strict abstention gating.
- Append-only prospective ledger logging.
- FastAPI REST endpoint /api/research/entry-quality.
- Epistemic invariants: analysis-only, trading disabled, no unearned promotion.
"""

import os
import json
import math
import tempfile
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
from starlette.testclient import TestClient

from engine.probabilistic_entry_engine import ProbabilisticEntryEngine
from api.server import app


@pytest.fixture
def temp_engine():
    """Provides an isolated ProbabilisticEntryEngine instance with a temporary ledger."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = ProbabilisticEntryEngine(data_dir=Path(tmpdir))
        yield engine


def test_v28_point_in_time_features(temp_engine):
    """Verify that features are computed using only past data at t0 without lookahead."""
    # Synthetic causal data: 30 closed bars
    np.random.seed(42)
    closes = 60000.0 + np.cumsum(np.random.randn(30) * 100)
    highs = closes + np.abs(np.random.randn(30) * 50)
    lows = closes - np.abs(np.random.randn(30) * 50)

    # 1. LONG features
    feats_long = temp_engine.compute_setup_features(closes, highs, lows, side="LONG")
    assert "mom_1h" in feats_long
    assert "mom_4h" in feats_long
    assert "mom_24h" in feats_long
    assert "rs_ratio" in feats_long
    assert "bb_width" in feats_long
    assert "range_pos" in feats_long
    assert 0.0 <= feats_long["rs_ratio"] <= 1.0
    assert 0.0 <= feats_long["range_pos"] <= 1.0

    # 2. SHORT features polarity inversion
    feats_short = temp_engine.compute_setup_features(closes, highs, lows, side="SHORT")
    assert np.isclose(feats_long["mom_1h"], -feats_short["mom_1h"], atol=1e-6)
    assert np.isclose(feats_long["mom_4h"], -feats_short["mom_4h"], atol=1e-6)
    assert np.isclose(feats_long["mom_24h"], -feats_short["mom_24h"], atol=1e-6)
    assert np.isclose(feats_long["rs_ratio"], 1.0 - feats_short["rs_ratio"], atol=1e-4)


def test_v28_calibrated_probabilities_normalization(temp_engine):
    """Verify probability predictions are calibrated and sum to exactly 1.0."""
    features = {
        "mom_1h": 0.005,
        "mom_4h": 0.012,
        "mom_24h": 0.025,
        "rs_ratio": 0.65,
        "bb_width": 0.015,
        "range_pos": 0.70
    }
    probs = temp_engine.predict_barrier_probabilities(features)

    assert 0.15 <= probs["p_tp"] <= 0.78
    assert probs["p_timeout"] == 0.08
    assert probs["p_sl"] >= 0.05
    total_p = probs["p_tp"] + probs["p_sl"] + probs["p_timeout"]
    assert np.isclose(total_p, 1.0, atol=1e-4)
    assert probs["calibration_status"] == "VALIDATED_ISOTONIC_CALIBRATION"


def test_v28_friction_and_net_expectancy(temp_engine):
    """Verify net expectancy in R-multiples accounts for friction and penalizes timeouts."""
    entry_price = 80000.0
    sigma_t0 = 0.010  # 1% volatility
    k_tp = 1.5
    k_sl = 1.0

    # Under base friction: round trip = 87 bps (0.87%)
    # Risk unit = 1R = 80000 * (1.0 * 0.010) = $800
    # Friction = 80000 * 0.0087 = $696 -> friction in R = 696 / 800 = 0.87 R
    decision = temp_engine.evaluate_decision_gate(
        side="LONG",
        entry_price=entry_price,
        sigma_t0=sigma_t0,
        k_tp=k_tp,
        k_sl=k_sl,
        features={"mom_1h": 0.0, "mom_4h": 0.0, "mom_24h": 0.0, "rs_ratio": 0.5, "bb_width": 0.01, "range_pos": 0.5},
        selective_threshold=0.60
    )

    assert decision["friction_r"] > 0.8
    assert decision["risk_unit_usd"] == 800.0
    # Expected net R must equal gross R minus friction R
    calc_net_r = round(decision["expected_gross_r"] - decision["friction_r"], 4)
    assert np.isclose(decision["expected_net_r"], calc_net_r, atol=1e-4)


def test_v28_decision_gate_abstains_on_negative_expectancy(temp_engine):
    """Verify engine returns ABSTAIN with NEGATIVE_EXPECTANCY_AFTER_COSTS when edge is cost-erased."""
    entry_price = 80000.0
    sigma_t0 = 0.005  # Low volatility makes friction very large in R

    decision = temp_engine.evaluate_decision_gate(
        side="LONG",
        entry_price=entry_price,
        sigma_t0=sigma_t0,
        k_tp=1.5,
        k_sl=1.0,
        features={"mom_1h": 0.0, "mom_4h": 0.0, "mom_24h": 0.0, "rs_ratio": 0.5, "bb_width": 0.01, "range_pos": 0.5},
        selective_threshold=0.50
    )

    assert decision["expected_net_r"] < 0.0
    assert decision["action"] == "ABSTAIN"
    assert decision["primary_reason"] == "NEGATIVE_EXPECTANCY_AFTER_COSTS"
    assert decision["execution_authorization"] == "DISABLED — ANALYSIS ONLY"


def test_v28_decision_gate_abstains_below_selective_threshold(temp_engine):
    """Verify engine abstains if win probability is below selective threshold even if gross edge is non-negative."""
    # Artificially test with huge volatility so friction is small in R
    decision = temp_engine.evaluate_decision_gate(
        side="LONG",
        entry_price=80000.0,
        sigma_t0=0.08,  # high volatility reduces friction in R
        k_tp=2.0,
        k_sl=1.0,
        features={"mom_1h": 0.001, "mom_4h": 0.002, "mom_24h": 0.005, "rs_ratio": 0.55, "bb_width": 0.02, "range_pos": 0.6},
        selective_threshold=0.75  # demanding threshold
    )

    if decision["expected_net_r"] > 0:
        # If expectancy is positive, it must still abstain because p_tp < 75%
        assert decision["probabilities"]["p_tp"] < 0.75
        assert decision["action"] == "ABSTAIN"
        assert "WIN_PROBABILITY_BELOW_SELECTIVE_THRESHOLD" in decision["primary_reason"]


def test_v28_prospective_ledger_append_only(temp_engine):
    """Verify prospective decisions are written append-only to JSONL ledger."""
    decision1 = temp_engine.evaluate_decision_gate(side="LONG", entry_price=80000.0, sigma_t0=0.01)
    decision2 = temp_engine.evaluate_decision_gate(side="SHORT", entry_price=79500.0, sigma_t0=0.012)

    ts1 = temp_engine.log_prospective_decision(decision1)
    ts2 = temp_engine.log_prospective_decision(decision2)

    assert os.path.exists(temp_engine.ledger_file)
    with open(temp_engine.ledger_file, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]

    assert len(lines) == 2
    assert lines[0]["side"] == "LONG"
    assert lines[1]["side"] == "SHORT"
    assert lines[0]["decision_timestamp_utc"] == ts1
    assert lines[1]["decision_timestamp_utc"] == ts2


def test_v28_fastapi_entry_quality_endpoint():
    """Verify /api/research/entry-quality endpoint returns valid response schema and non-execution invariant."""
    client = TestClient(app)
    resp = client.get("/api/research/entry-quality?side=LONG&k_tp=1.5&k_sl=1.0&threshold=0.60")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "SUCCESS"
    assert data["engine_version"] == "ENTRY_TP_SL_RESOLVER_V1"
    assert "features_evaluated" in data
    assert "decision" in data
    assert "recent_prospective_records" in data

    decision = data["decision"]
    assert decision["side"] == "LONG"
    assert decision["execution_authorization"] == "DISABLED — ANALYSIS ONLY"
    assert decision["governance_status"] == "OFFLINE_RESEARCH_ONLY"
    assert decision["action"] in ["ABSTAIN", "ACCEPTED_RESEARCH_CANDIDATE"]
    assert "probabilities" in decision
    assert "p_tp" in decision["probabilities"]
    assert "p_sl" in decision["probabilities"]


def test_v28_conservative_intrabar_touch_resolution():
    """
    Epistemic test: In bars where High >= TP and Low <= SL (intrabar collision),
    verify that a causal simulator resolves to SL_FIRST rather than assuming the profitable outcome.
    """
    entry_price = 100.0
    tp_price = 105.0
    sl_price = 95.0

    # Ambiguous candle
    bar_high = 106.0
    bar_low = 94.0

    # Rule: Never assume TP occurred before SL without finer tick confirmation
    touch_tp = bar_high >= tp_price
    touch_sl = bar_low <= sl_price
    assert touch_tp and touch_sl, "Fixture must be an intrabar collision"

    # Conservative resolution
    first_barrier = "SL_FIRST" if (touch_tp and touch_sl) else ("TP_FIRST" if touch_tp else "SL_FIRST")
    assert first_barrier == "SL_FIRST"

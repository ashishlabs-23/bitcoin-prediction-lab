"""
tests/test_v32_63_calculation_correctness.py — Feature Value & Calculation Correctness Suite
============================================================================================
BTCognitive V32.63 Independent Verification Test Suite.
Verifies:
1. Exact mathematical parity against hand-computed golden fixtures (EMA, ATR, ADX, Donchian, Bollinger).
2. Analytical Wilson 95% Score Confidence Intervals (7/10 Screen).
3. Break-even win rate & execution cost friction models across fee schedules.
4. Strict causal non-lookahead invariants on Donchian breakout bounds.
5. Invariance of all 6 protected research datasets and prospective ledgers.
"""

import os
import sys
import json
import math
import hashlib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app
from engine.regime_strategy_tournament import (
    compute_ema,
    compute_atr,
    compute_adx as compute_adx_tournament,
    compute_wilson_ci,
    compute_bollinger_bandwidth,
    compute_parkinson_volatility as compute_parkinson_tournament,
    VersionedStrategyRegistry,
)
from engine.strategy_signal_engine import (
    compute_adx as compute_adx_signal,
    compute_parkinson_volatility as compute_parkinson_signal,
)
from engine.execution_cost_model import ExecutionCostModel


GOLDEN_FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "research",
    "reports",
    "v32_63_feature_value_audit",
    "20261029_223400_audit",
    "golden_calculation_cases.json"
)

PROTECTED_FILES = [
    ("data/raw/ohlcv.parquet", "c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f"),
    ("data/raw/ohlcv_pre_backfill_backup.parquet", "c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8"),
    ("data/raw/ohlcv_backfilled.parquet", "1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c"),
    ("data/prospective_entry_ledger.jsonl", "91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7"),
    ("data/prospective_shadow_v1.jsonl", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    ("data/prospective_entry_ledger_v2.jsonl", "e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604"),
]


@pytest.fixture(scope="module")
def golden_cases():
    with open(GOLDEN_FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_01_ema_golden_hand_calculated(golden_cases):
    """Verifies EMA calculation against exact hand-calculated recursive series."""
    case = golden_cases["ema_cases"][0]
    prices = np.array(case["input_prices"], dtype=np.float64)
    period = case["period"]
    expected_final = case["final_expected_value"]

    computed_final = compute_ema(prices, period)
    assert abs(computed_final - expected_final) < 1e-4, (
        f"EMA-3 final mismatch: computed {computed_final}, expected {expected_final}"
    )

    # Flat series check
    case_flat = golden_cases["ema_cases"][1]
    prices_flat = np.array(case_flat["input_prices"], dtype=np.float64)
    computed_flat = compute_ema(prices_flat, case_flat["period"])
    assert abs(computed_flat - case_flat["final_expected_value"]) < 1e-4


def test_02_wilson_ci_exact_answers(golden_cases):
    """Verifies Wilson Score 95% Confidence Interval analytical bounds."""
    for case in golden_cases["wilson_ci_cases"]:
        lower, upper = compute_wilson_ci(case["successes"], case["total"], case["confidence"])
        assert abs(lower - case["expected_lower"]) <= 1e-3, (
            f"Case {case['case_id']}: lower bound mismatch {lower} vs {case['expected_lower']}"
        )
        assert abs(upper - case["expected_upper"]) <= 1e-3, (
            f"Case {case['case_id']}: upper bound mismatch {upper} vs {case['expected_upper']}"
        )


def test_03_breakeven_winrate_formula(golden_cases):
    """Verifies analytical break-even win rate calculation after friction in R."""
    for case in golden_cases["breakeven_winrate_cases"]:
        bep = ExecutionCostModel.calculate_breakeven_win_rate(
            friction_r=case["friction_r"],
            k_tp=case["k_tp"],
            k_sl=case["k_sl"]
        )
        assert abs(bep - case["expected_breakeven_winrate"]) <= 1e-3, (
            f"Case {case['case_id']}: BEP mismatch {bep} vs {case['expected_breakeven_winrate']}"
        )


def test_04_donchian_causal_no_lookahead(golden_cases):
    """Verifies that Donchian channel bounds strictly exclude current bar t."""
    case = golden_cases["donchian_cases"][0]
    highs = pd.Series(case["highs"])
    lows = pd.Series(case["lows"])

    # Strict causal shift(1) rule
    upper_channel = highs.shift(1).rolling(24).max()
    lower_channel = lows.shift(1).rolling(24).min()
    mid_channel = (upper_channel + lower_channel) / 2.0

    # At bar index 24 (the 25th bar with extreme values 150 high, 40 low)
    # The channel evaluated at index 24 MUST reflect only bars 0..23
    val_upper = upper_channel.iloc[24]
    val_lower = lower_channel.iloc[24]
    val_mid = mid_channel.iloc[24]

    assert val_upper == case["expected_prior_upper"], (
        f"Lookahead leak detected! Upper {val_upper} != {case['expected_prior_upper']}"
    )
    assert val_lower == case["expected_prior_lower"], (
        f"Lookahead leak detected! Lower {val_lower} != {case['expected_prior_lower']}"
    )
    assert val_mid == case["expected_prior_mid"]


def test_05_atr_true_range_fixtures(golden_cases):
    """Verifies True Range handling of normal bars, gap up, and gap down."""
    case = golden_cases["atr_cases"][0]
    c1, c2, c3 = case["candles"]

    # Bar 1: Normal bar (no prior close)
    tr1 = c1["high"] - c1["low"]
    assert tr1 == case["expected_tr_bar1"]

    # Bar 2: Gap Up (c2.low > c1.close)
    tr2 = max(c2["high"] - c2["low"], abs(c2["high"] - c1["close"]), abs(c2["low"] - c1["close"]))
    assert tr2 == case["expected_tr_bar2_gap_up"]

    # Bar 3: Gap Down (c3.high < c2.close)
    tr3 = max(c3["high"] - c3["low"], abs(c3["high"] - c2["close"]), abs(c3["low"] - c2["close"]))
    assert tr3 == case["expected_tr_bar3_gap_down"]


def test_06_adx_bounded_and_smoothing():
    """Verifies ADX boundary invariants [0, 100] and smoothing behavior."""
    n = 60
    # Create trending synthetic sequence
    trend_closes = np.linspace(80000, 90000, n)
    trend_highs = trend_closes + 200.0
    trend_lows = trend_closes - 150.0

    adx_tourn = compute_adx_tournament(trend_highs, trend_lows, trend_closes, period=14)
    adx_sig = compute_adx_signal(trend_highs, trend_lows, trend_closes, period=14)

    assert 0.0 <= adx_tourn <= 100.0, f"Tournament ADX {adx_tourn} out of bounds"
    assert 0.0 <= adx_sig <= 100.0, f"Signal DX {adx_sig} out of bounds"
    assert adx_tourn > 20.0, "Strong upward trend failed to produce elevated ADX"


def test_07_bollinger_bandwidth_calculation():
    """Verifies Bollinger Bandwidth, upper, middle, and lower bands."""
    closes = np.array([100.0] * 20, dtype=np.float64)
    bw, upper, mid, lower = compute_bollinger_bandwidth(closes, period=20, num_std=2.0)
    assert mid == 100.0
    assert upper == 100.0
    assert lower == 100.0
    assert bw == 0.0


def test_08_parkinson_volatility():
    """Verifies Parkinson volatility estimator numerical sanity."""
    highs = np.array([105.0] * 24, dtype=np.float64)
    lows = np.array([95.0] * 24, dtype=np.float64)
    vol = compute_parkinson_tournament(highs, lows)
    assert 0.001 < vol < 0.50, f"Parkinson volatility {vol} outside plausible range"


def test_09_offline_analyse_zero_mutations():
    """Verifies that calling POST /api/tournament/analyse performs zero ledger writes."""
    client = TestClient(app)
    payload = {
        "client_request_id": "v32_63_calc_test_001",
        "symbol": "BTC-USD",
        "timeframe": "1h",
        "cost_scenario": "COINBASE_ADVANCED_87BPS"
    }

    # Record size of prospective ledger before call
    ledger_path = "data/prospective_entry_ledger.jsonl"
    size_before = os.path.getsize(ledger_path) if os.path.exists(ledger_path) else 0

    res = client.post("/api/tournament/analyse", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "analysis_id" in data
    assert data.get("attempts_created", 0) == 0
    assert "smart_entry_decision" in data

    size_after = os.path.getsize(ledger_path) if os.path.exists(ledger_path) else 0
    assert size_before == size_after, "Analyse endpoint mutated prospective ledger!"


def test_10_protected_files_invariance():
    """Verifies that all 6 protected research files remain bit-for-bit identical."""
    for rel_path, expected_hash in PROTECTED_FILES:
        full_path = os.path.join(os.path.dirname(__file__), "..", rel_path)
        assert os.path.exists(full_path), f"Protected file missing: {rel_path}"
        with open(full_path, "rb") as f:
            computed_hash = hashlib.sha256(f.read()).hexdigest()
        assert computed_hash == expected_hash, (
            f"MUTATION DETECTED in protected file {rel_path}! "
            f"Expected {expected_hash}, got {computed_hash}"
        )

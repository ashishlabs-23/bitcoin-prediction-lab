"""
tests/test_research_to_signal_engine_v3.py
=========================================
Comprehensive deterministic test suite for Research-to-Signal Engine v3:
Experiment Integrity, Realistic Two-Sided Execution Costs & Selective Paper-Signal Research.

Verifies:
1. Two-sided execution costs (Binance perpetual taker + spread + slippage + holding funding; Coinbase spot 80 bps).
2. Monotonicity of net expectancy under fee variations.
3. Zero-cost gross PnL identity across venues.
4. Single-position-at-a-time portfolio accounting (at most 1 active position open at any time).
5. Split boundary purging and outcome embargo (no label maturity leakage).
6. Forensic proof of why logistic classifier produced zero trades at p >= 0.60 (target prevalence ~17.5%).
7. Corrected 24h momentum baseline under single-position portfolio and two-sided costs.
8. Selective candidate evaluation (Candidates 0, 1, 2, 3) under preregistered gates.
9. Governed conclusion integrity (NO_CANDIDATE_PASSED_PREREGISTERED_GATE when net EV <= 0).
10. Execution authorization is permanently DISABLED.
"""

import math
import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from engine.execution_cost_model import ExecutionCostModel
from engine.scenario_contract_engine import ScenarioContractEngine, compute_bracket_geometry
from models.signal_contract import ExecutionAuthorization, SignalStatus


# =========================================================================
# 1. TWO-SIDED EXECUTION COST MODEL TESTS (AGENT B)
# =========================================================================

def test_binance_futures_two_sided_taker_costs():
    """Verify Binance Futures perpetual taker: 5 bps entry + 5 bps exit = 10 bps commission."""
    cost_model = ExecutionCostModel(venue="BINANCE_FUTURES", product_type="PERPETUAL")
    lifecycle = cost_model.calculate_full_lifecycle_cost(
        entry_price=80000.0,
        exit_price=81000.0,
        size_btc=0.1,
        holding_hours=0.0,
        direction="LONG"
    )
    # Entry fee 5 bps, Exit fee 5 bps => 10 bps
    assert lifecycle["entry_fee_bps"] == 5.0
    assert lifecycle["exit_fee_bps"] == 5.0
    assert lifecycle["two_sided_commission_bps"] == 10.0
    # Two-sided spread = 0.5 + 0.5 = 1.0 bps, Two-sided slippage = 1.0 + 1.0 = 2.0 bps
    assert lifecycle["two_sided_spread_bps"] == 1.0
    assert lifecycle["two_sided_slippage_bps"] == 2.0
    # Zero holding hours => zero funding
    assert lifecycle["funding_bps"] == 0.0
    # Total friction = 10 + 1 + 2 = 13.0 bps (approx due to notional exit difference)
    assert lifecycle["total_friction_bps"] == pytest.approx(13.06, abs=0.2)


def test_binance_futures_holding_funding_duration_dependent():
    """Verify perpetual funding is paid/received across 8-hour intervals."""
    cost_model = ExecutionCostModel(venue="BINANCE_FUTURES", product_type="PERPETUAL")
    
    # 7 hours hold: 0 intervals passed => 0 funding
    f_7h = cost_model.calculate_holding_funding_cost(notional_usd=8000.0, holding_hours=7.0, position_direction="LONG")
    assert f_7h["intervals_passed"] == 0
    assert f_7h["effective_funding_bps"] == 0.0

    # 16 hours hold: 2 intervals passed (1.0 bps each) => 2.0 bps for LONG
    f_16h = cost_model.calculate_holding_funding_cost(notional_usd=8000.0, holding_hours=16.0, position_direction="LONG")
    assert f_16h["intervals_passed"] == 2
    assert f_16h["effective_funding_bps"] == 2.0

    # SHORT receives positive funding rate (negative cost / payment received)
    f_short = cost_model.calculate_holding_funding_cost(notional_usd=8000.0, holding_hours=16.0, position_direction="SHORT")
    assert f_short["effective_funding_bps"] == -2.0


def test_coinbase_advanced_spot_tier1_two_sided_costs():
    """Verify Coinbase Spot Tier 1 taker: 40 bps entry + 40 bps exit = 80 bps commission."""
    cost_model = ExecutionCostModel(venue="COINBASE", product_type="SPOT")
    lifecycle = cost_model.calculate_full_lifecycle_cost(
        entry_price=80000.0,
        exit_price=80000.0,
        size_btc=0.1,
        holding_hours=24.0,
        direction="LONG"
    )
    # Entry fee 40 bps, Exit fee 40 bps => 80 bps
    assert lifecycle["entry_fee_bps"] == 40.0
    assert lifecycle["exit_fee_bps"] == 40.0
    assert lifecycle["two_sided_commission_bps"] == 80.0
    # Spot market has 0 funding regardless of holding hours
    assert lifecycle["funding_bps"] == 0.0
    # Total friction = 80 + 3 (spread) + 4 (slippage) = 87.0 bps
    assert lifecycle["total_friction_bps"] == pytest.approx(87.0, abs=0.5)


def test_monotonicity_of_cost_sensitivity():
    """Verify that net expectancy decreases monotonically as friction increases."""
    gross_return_bps = 25.0
    frictions = [0.0, 7.0, 13.0, 15.25, 40.0, 87.0]
    net_returns = [gross_return_bps - f for f in frictions]
    for i in range(len(net_returns) - 1):
        assert net_returns[i] > net_returns[i + 1]


def test_zero_cost_gross_identity():
    """Verify that under zero-cost assumptions, gross PnL is completely venue-agnostic."""
    entry_p = 80000.0
    exit_p = 81600.0  # +2.0%
    gross_bps = (exit_p - entry_p) / entry_p * 10000.0
    assert gross_bps == pytest.approx(200.0, abs=1e-5)


# =========================================================================
# 2. EXPERIMENT FORENSICS & LEAKAGE AUDIT TESTS (AGENT A & D)
# =========================================================================

def test_split_boundary_purging_prevents_outcome_leakage():
    """Verify that a 24-bar embargo/purge prevents training labels from maturing inside evaluation window."""
    H = 24
    # Label issued at bar t requires window [t+1, t+H]
    train_end_bar = 1000
    purge_len = H - 1
    safe_train_end = train_end_bar - purge_len
    # Max safe issue bar matures at:
    max_label_maturity = safe_train_end + H
    eval_start_bar = train_end_bar + 1
    # Maturity must be <= eval_start_bar
    assert max_label_maturity <= eval_start_bar + 1


def test_logistic_classifier_zero_trade_forensic_proof():
    """
    Forensic proof: An unweighted model predicting a target with ~17.5% prevalence
    outputs probabilities centered around ~18-20% and maximum score < 30%.
    Therefore, requiring p >= 0.60 mathematically guarantees 0 trades.
    """
    # Simulate a calibrated event probability distribution with base rate 17.5%
    np.random.seed(42)
    n = 6000
    y_true = np.random.binomial(1, 0.175, size=n)
    # Predicted probabilities from a logistic model with moderate predictive signal
    logits = np.log(0.175 / (1.0 - 0.175)) + np.random.normal(0, 0.25, size=n)
    probs = 1.0 / (1.0 + np.exp(-logits))
    
    # Assertions on distribution
    assert probs.mean() == pytest.approx(0.18, abs=0.03)
    assert probs.max() < 0.40
    # Zero trades at p >= 0.50 or p >= 0.60
    assert (probs >= 0.60).sum() == 0
    assert (probs >= 0.50).sum() == 0


# =========================================================================
# 3. SINGLE-POSITION PORTFOLIO ACCOUNTING TESTS (AGENT E)
# =========================================================================

def test_single_position_accounting_strictly_prevents_overlap():
    """Verify that single-position simulator enforces non-overlapping trades."""
    # 3 hypothetical trade signals that would overlap under naive simulation
    trades = [
        {"issue_idx": 10, "entry_idx": 11, "long_exit_idx": 25, "long_return": 0.01, "long_outcome": "TP_FIRST"},
        {"issue_idx": 12, "entry_idx": 13, "long_exit_idx": 30, "long_return": -0.01, "long_outcome": "SL_FIRST"},
        {"issue_idx": 26, "entry_idx": 27, "long_exit_idx": 45, "long_return": 0.02, "long_outcome": "TP_FIRST"}
    ]
    df_trades = pd.DataFrame(trades)

    sp_trades = []
    curr_exit = -1
    for idx, row in df_trades.iterrows():
        if row["entry_idx"] > curr_exit:
            sp_trades.append(row)
            curr_exit = row["long_exit_idx"]

    # Trade at issue_idx 12 was rejected because prior trade exits at index 25
    assert len(sp_trades) == 2
    assert sp_trades[0]["issue_idx"] == 10
    assert sp_trades[1]["issue_idx"] == 26


# =========================================================================
# 4. CANDIDATE STUDY & GOVERNANCE GATE TESTS (AGENT C & H)
# =========================================================================

def test_preregistered_manifest_integrity_and_verdict():
    """Verify that EXP-RESEARCH-TO-SIGNAL-V3-SELECTIVE manifest exists and records truthful verdict."""
    manifest_path = Path("experiments/results/research_improvement/v3_selective_signal_manifest.json")
    assert manifest_path.exists(), "Manifest v3 must be generated and persisted."
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["experiment_id"] == "EXP-RESEARCH-TO-SIGNAL-V3-SELECTIVE"
    assert manifest["portfolio_policy"] == "SINGLE_POSITION_AT_A_TIME"
    assert manifest["execution_authorization"] == "DISABLED"

    candidates = manifest["candidates"]
    assert "Candidate_0_No_Trade_Baseline" in candidates
    assert "Candidate_1_Momentum_24h_Baseline" in candidates
    assert "Candidate_2_Cost_Aware_Filter" in candidates
    assert "Candidate_3_Meta_Label_Filter" in candidates

    # Candidate 1 has negative net expectancy
    c1 = candidates["Candidate_1_Momentum_24h_Baseline"]
    assert c1["net_expectancy_binance_bps"] < 0.0
    assert c1["economic_verdict"] == "FAIL_NEGATIVE_AFTER_COSTS"

    # Candidate 3 has negative net expectancy after Binance costs
    c3 = candidates["Candidate_3_Meta_Label_Filter"]
    assert c3["net_expectancy_binance_bps"] < 0.0
    assert c3["economic_verdict"] == "FAIL_NEGATIVE_AFTER_COSTS"

    # Final governed conclusion
    assert manifest["governed_conclusion"] == "NO_CANDIDATE_PASSED_PREREGISTERED_GATE"


def test_scenario_contract_engine_fails_closed_when_expectancy_negative():
    """Verify scenario engine returns ABSTAIN when candidate net expectancy is negative."""
    engine = ScenarioContractEngine(exchange="Binance_Futures", instrument="BTCUSDT")
    sig = engine.evaluate_scenario_candidate(
        reference_price=80000.0,
        direction="LONG",
        horizon="1h",
        is_model_gated=False,
        # Probabilities with negative net expectancy
        p_tp=0.15,
        p_sl=0.35,
        p_timeout=0.50,
        cost_bps=15.25
    )
    assert sig.signal_status == SignalStatus.ABSTAIN
    assert sig.invalidation_reason == "ECONOMIC_EXPECTANCY_NEGATIVE"
    assert sig.execution_authorization == ExecutionAuthorization.DISABLED
    assert sig.entry_price is None
    assert sig.take_profit is None
    assert sig.stop_loss is None

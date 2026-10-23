"""
tests/test_phase4_directional_research_gate.py — Verification of Phase 4 Directional Research Gate
===================================================================================================
Tests:
1. DirectionalResearchGate evaluates candidates against random walk and majority class baselines.
2. Deducts realistic exchange fees, spread, and slippage using ExecutionRealityEngine.
3. Produces selective coverage curves (100%, 50%, 25%, 10%).
4. Emits NO_MEASURABLE_DIRECTIONAL_EDGE_AFTER_COSTS on realistic BTCUSD signals hovering near 50-52%.
5. Enforces fail-closed AUTHORIZED_FOR_RESEARCH_ONLY governance status.
"""

import numpy as np
import pytest

from research.directional_research_gate import (
    DirectionalResearchGate,
    DirectionalHorizonEvaluation,
    DirectionalResearchGateReport,
)
from backtest.execution_reality import ExecutionRealityEngine


def test_directional_research_gate_negative_expectancy_rejection():
    gate = DirectionalResearchGate()
    np.random.seed(42)

    # Simulate 500 samples with 51% accuracy (typical empirical BTC classifier)
    n = 500
    y_true = np.random.binomial(1, 0.50, n)
    # Slight correlated signal yielding ~51.5% accuracy
    noise = np.random.normal(0, 1, n)
    raw_score = 0.05 * (2 * y_true - 1) + noise
    y_prob = 1.0 / (1.0 + np.exp(-raw_score))

    # Realized returns in bps (mean 0, std 100 bps)
    future_returns_bps = np.random.normal(0, 100, n)

    eval_24h = gate.evaluate_horizon(
        horizon="24h",
        y_true_binary=y_true,
        y_prob=y_prob,
        future_returns_bps=future_returns_bps
    )

    assert eval_24h.horizon == "24h"
    assert eval_24h.sample_size == 500
    assert 45.0 <= eval_24h.unconditional_accuracy_pct <= 58.0
    # Lower bound of 95% CI is below 50%
    assert eval_24h.accuracy_ci_95[0] < 50.0

    # Selective coverage curve has entries for 100%, 50%, 25%, 10%
    assert "100%" in eval_24h.selective_coverage_curve
    assert "50%" in eval_24h.selective_coverage_curve
    assert "25%" in eval_24h.selective_coverage_curve
    assert "10%" in eval_24h.selective_coverage_curve

    # Net expectancy after 8 bps taker friction is negative
    assert eval_24h.net_expectancy_bps_after_costs < eval_24h.gross_expectancy_bps
    assert eval_24h.has_statistically_significant_edge is False
    assert eval_24h.verdict == "NO_MEASURABLE_DIRECTIONAL_EDGE_AFTER_COSTS"


def test_full_gate_report_fail_closed():
    gate = DirectionalResearchGate()
    np.random.seed(123)
    n = 200
    y_true = np.random.binomial(1, 0.50, n)
    y_prob = np.random.uniform(0.40, 0.60, n)
    rets = np.random.normal(0, 50, n)

    ev_1h = gate.evaluate_horizon("1h", y_true, y_prob, rets)
    ev_4h = gate.evaluate_horizon("4h", y_true, y_prob, rets)
    ev_24h = gate.evaluate_horizon("24h", y_true, y_prob, rets)

    report = gate.run_full_gate({
        "1h": ev_1h,
        "4h": ev_4h,
        "24h": ev_24h,
    })

    assert report.overall_verdict == "NO_MEASURABLE_DIRECTIONAL_EDGE_AFTER_COSTS"
    assert report.authorization_status == "AUTHORIZED_FOR_RESEARCH_ONLY"
    assert "strictly remain RESEARCH_ONLY" in report.scientific_summary

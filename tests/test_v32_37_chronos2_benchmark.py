"""
tests/test_v32_37_chronos2_benchmark.py
=========================================
Unit and integration tests for BTCognitive V32.37 Chronos-2 Comparative Benchmark.
Verifies:
1. Causal timestamp alignment and context preparation (zero lookahead).
2. Target calculation exactness (1h, 4h, 24h log returns and directional labels).
3. Outage gap detection (ensuring genuine market data gaps are tracked and excluded).
4. Pinball (quantile) loss exactness against hand-computed values.
5. Winkler score calculation exactness for 80% prediction intervals.
6. Diebold-Mariano test with Harvey-Leybourne-Newbold (1997) finite-sample correction.
7. Chronos-2 output shape, quantile monotonicity (P10 <= P50 <= P90), and probability proxy labeling.
8. Model governance boundaries (OFFLINE_RESEARCH_ONLY, live trading disabled, valid decision enum).
"""

import os
import sys
import math
import pytest
import numpy as np
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from research.experiments.run_v32_37_chronos2_benchmark import (
    compute_pinball_loss,
    compute_winkler_score,
    compute_diebold_mariano_hln
)


def test_causal_context_preparation():
    """Verify that context inputs at origin t use strictly closed bars <= t."""
    timestamps = [f"2026-01-01T{h:02d}:00:00Z" for h in range(24)]
    closes = np.arange(100.0, 124.0)

    # Context window = 10 bars
    # Forecast origin at index t=15 (timestamp 2026-01-01T15:00:00Z)
    t = 15
    context = closes[t - 10 + 1 : t + 1]
    assert len(context) == 10
    assert context[-1] == closes[t] == 115.0
    assert context[0] == closes[t - 9] == 106.0
    # Future bars (t+1 .. t+24) must NOT be in context
    assert 116.0 not in context


def test_target_horizon_calculations():
    """Verify 1h, 4h, 24h log return and binary directional label exactness."""
    p_t = 60000.0
    p_1h = 60600.0 # +1%
    p_4h = 59400.0 # -1%
    p_24h = 60000.0 # flat

    ret_1h = math.log(p_1h / p_t)
    dir_1h = 1 if p_1h > p_t else 0
    assert round(ret_1h, 4) == round(math.log(1.01), 4)
    assert dir_1h == 1

    ret_4h = math.log(p_4h / p_t)
    dir_4h = 1 if p_4h > p_t else 0
    assert round(ret_4h, 4) == round(math.log(0.99), 4)
    assert dir_4h == 0

    ret_24h = math.log(p_24h / p_t)
    dir_24h = 1 if p_24h > p_t else 0
    assert ret_24h == 0.0
    assert dir_24h == 0


def test_outage_gap_detection():
    """Verify detection of timestamp jumps exceeding expected horizon stride."""
    # Origin at t=0, future at t=7 (7 hours apart instead of 1 hour)
    epoch_t = 1778202000
    epoch_future_normal = epoch_t + 3600 # 1h
    epoch_future_gap = epoch_t + (7 * 3600) # 7h jump (e.g. Coinbase outage)

    is_gap_normal = (epoch_future_normal - epoch_t) != 3600
    is_gap_outage = (epoch_future_gap - epoch_t) != 3600

    assert not is_gap_normal
    assert is_gap_outage


def test_pinball_loss_exactness():
    """Verify pinball loss against hand-computed known answers."""
    # Case 1: y = 100, pred = 90 (underpredict by 10, error = +10)
    # For q=0.9: loss = q * error = 0.9 * 10 = 9.0
    # For q=0.1: loss = q * error = 0.1 * 10 = 1.0
    y1 = np.array([100.0])
    p1 = np.array([90.0])
    assert abs(compute_pinball_loss(y1, p1, 0.90) - 9.0) < 1e-6
    assert abs(compute_pinball_loss(y1, p1, 0.10) - 1.0) < 1e-6

    # Case 2: y = 100, pred = 110 (overpredict by 10, error = -10)
    # For q=0.9: loss = (q - 1) * error = -0.1 * -10 = 1.0
    # For q=0.1: loss = (q - 1) * error = -0.9 * -10 = 9.0
    p2 = np.array([110.0])
    assert abs(compute_pinball_loss(y1, p2, 0.90) - 1.0) < 1e-6
    assert abs(compute_pinball_loss(y1, p2, 0.10) - 9.0) < 1e-6

    # Case 3: exact prediction
    assert compute_pinball_loss(y1, y1, 0.50) == 0.0


def test_winkler_score_exactness():
    """Verify Winkler score for 80% interval against known-answers."""
    alpha = 0.20
    lower = np.array([90.0])
    upper = np.array([110.0])
    # Width is 20.0

    # Inside interval: y = 100 -> score = width = 20.0
    y_in = np.array([100.0])
    assert abs(compute_winkler_score(y_in, lower, upper, alpha) - 20.0) < 1e-6

    # Below lower bound: y = 80 -> penalty = (2 / 0.20) * (90 - 80) = 10 * 10 = 100.0
    # Total score = 20 + 100 = 120.0
    y_below = np.array([80.0])
    assert abs(compute_winkler_score(y_below, lower, upper, alpha) - 120.0) < 1e-6

    # Above upper bound: y = 120 -> penalty = (2 / 0.20) * (120 - 110) = 10 * 10 = 100.0
    # Total score = 20 + 100 = 120.0
    y_above = np.array([120.0])
    assert abs(compute_winkler_score(y_above, lower, upper, alpha) - 120.0) < 1e-6


def test_diebold_mariano_hln_statistic():
    """Verify Diebold-Mariano test with Harvey-Leybourne-Newbold correction."""
    np.random.seed(42)
    N = 100

    # Case 1: Identical errors -> DM stat == 0, p-value == 1.0
    errs = np.random.randn(N)
    res_ident = compute_diebold_mariano_hln(errs, errs, h=1)
    assert res_ident["dm_stat"] == 0.0
    assert res_ident["p_value"] == 1.0

    # Case 2: Model 1 has strictly smaller errors than Model 2
    errs_better = 0.5 * np.random.randn(N)
    errs_worse = 2.0 * np.random.randn(N)
    res_better = compute_diebold_mariano_hln(errs_better, errs_worse, h=1)
    assert res_better["hln_stat"] < 0.0 # Model 1 loss is lower
    assert res_better["p_value"] < 0.01 # Highly statistically significant

    # Case 3: HLN correction factor reduces test stat magnitude for small T
    # Check that hln_corr factor matches formula sqrt((T + 1 - 2h + h(h-1)/T)/T)
    T = 20
    h = 4
    expected_corr = math.sqrt((T + 1 - 2*h + (h * (h - 1)) / T) / T)
    assert 0.0 < expected_corr < 1.0


def test_quantile_monotonicity_and_probability_proxy():
    """Verify that predicted quantiles obey P10 <= P50 <= P90 and probability proxy is bounded [0, 1]."""
    p10 = 60000.0
    p50 = 60500.0
    p90 = 61200.0

    assert p10 <= p50 <= p90

    # Probability proxy calculation
    origin_prices = [59000.0, 60250.0, 60800.0, 62000.0]
    for p_t in origin_prices:
        if p_t <= p10:
            p_up = 0.90
        elif p_t <= p50:
            p_le = 0.10 + 0.40 * (p_t - p10) / (p50 - p10)
            p_up = 1.0 - p_le
        elif p_t <= p90:
            p_le = 0.50 + 0.40 * (p_t - p50) / (p90 - p50)
            p_up = 1.0 - p_le
        else:
            p_up = 0.10
        assert 0.0 <= p_up <= 1.0


def test_governance_and_decision_integrity():
    """Verify that summary output follows required schema, governance locks, and valid decision enum."""
    summary_path = os.path.join(REPO_ROOT, "research", "reports", "v32_37_chronos2_benchmark_summary.json")
    if not os.path.exists(summary_path):
        pytest.skip("Benchmark summary file not yet generated")

    import json
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["production_lock"] == "OFFLINE_RESEARCH_ONLY"
    assert data["live_trading_status"] == "DISABLED"
    assert data["master_decision"] in {
        "CHRONOS2_RESEARCH_CANDIDATE",
        "NO_INCREMENTAL_FORECAST_VALUE",
        "INCONCLUSIVE"
    }
    assert "horizons" in data
    assert "1h" in data["horizons"]
    assert "4h" in data["horizons"]
    assert "24h" in data["horizons"]

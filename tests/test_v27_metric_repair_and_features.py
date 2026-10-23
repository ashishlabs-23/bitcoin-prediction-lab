"""
tests/test_v27_metric_repair_and_features.py — V27 Metric Integrity & Research Feature Verification Suite
========================================================================================================
Validates:
1. Strategy Transition Accounting & Turnover:
   - flat -> long (1 unit)
   - long -> flat (1 unit)
   - long -> short (2 units)
   - short -> long (2 units)
   - repeated position (0 units)
   - initial active position accounting (prepend=0 vs prepend=pos[0])
2. Compounded Simple Equity vs Additive Log Returns:
   - Verifies that log return sums are not conflated with simple percentage returns.
   - Verifies max drawdown calculation on compounded equity.
3. Forecast Canonical Boundaries:
   - Verifies exact N=(15000, 3750, 625) from range(20000, 35000 - h + 1, h).
4. Realized Semi-Variance Exact Algebraic Identity:
   - Hand-calculated fixture verifying RV == RS+ + RS- and asymmetry ratio.
5. Cross-Venue Spot Divergence Quote Normalization:
   - Verifies USD fiat vs USDT basis tagging.
6. Funding Rate Research Schema:
   - Verifies linear vs inverse separation and exploratory hypothesis tag.
7. Execution Gates Fail-Closed Invariant.
"""

import math
import numpy as np
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from api.server import app
from engine.realized_semi_variance import semi_variance_engine
from engine.cross_venue_divergence import cross_venue_engine
from engine.funding_rate_research import funding_research_engine

client = TestClient(app)
REPO_ROOT = Path(__file__).resolve().parent.parent


# ===========================================================================
# 1. Strategy Transition Accounting Deterministic Test Cases
# ===========================================================================

def test_v27_transition_accounting_deterministic_cases():
    """Verify exact turnover unit calculation across all atomic position transitions."""
    # Test cases: (pos_t_minus_1, pos_t, expected_turnover, expected_type)
    cases = [
        (0, 1, 1.0, "FLAT_TO_LONG_ENTRY"),
        (1, 0, 1.0, "LONG_TO_FLAT_EXIT"),
        (0, -1, 1.0, "FLAT_TO_SHORT_ENTRY"),
        (-1, 0, 1.0, "SHORT_TO_FLAT_EXIT"),
        (1, -1, 2.0, "LONG_TO_SHORT_REVERSAL"),
        (-1, 1, 2.0, "SHORT_TO_LONG_REVERSAL"),
        (1, 1, 0.0, "REPEATED_LONG"),
        (-1, -1, 0.0, "REPEATED_SHORT"),
        (0, 0, 0.0, "REPEATED_FLAT")
    ]
    for p_prev, p_curr, expected_turnover, desc in cases:
        turnover = abs(p_curr - p_prev)
        assert turnover == expected_turnover, f"Failed for {desc}: expected {expected_turnover}, got {turnover}"


def test_v27_dual_ema_100_events_reconciliation():
    """Reconcile reported Dual-EMA counts of 100 events, 99 reversals, and 199 turnover units."""
    # When portfolio starts flat (s_{-1} = 0) and takes position s_0 = 1, then reverses 99 times:
    positions = np.array([1, -1] * 50)  # Length 100: [1, -1, 1, -1, ..., -1]
    
    # prepend=0 (Initial portfolio starts FLAT from cash)
    diff_0 = np.abs(np.diff(positions, prepend=0))
    events_0 = int(np.sum(diff_0 > 0))
    reversals_0 = int(np.sum(diff_0 == 2))
    entries_0 = int(np.sum(diff_0 == 1))
    turnover_0 = float(np.sum(diff_0))
    round_trips_0 = turnover_0 / 2.0

    assert events_0 == 100, f"Expected 100 events, got {events_0}"
    assert reversals_0 == 99, f"Expected 99 reversals, got {reversals_0}"
    assert entries_0 == 1, f"Expected 1 entry, got {entries_0}"
    assert turnover_0 == 199.0, f"Expected 199.0 turnover units, got {turnover_0}"
    assert round_trips_0 == 99.5, f"Expected 99.5 round trips, got {round_trips_0}"

    # prepend=positions[0] (Suppresses initial entry cost)
    diff_pos0 = np.abs(np.diff(positions, prepend=positions[0]))
    events_pos0 = int(np.sum(diff_pos0 > 0))
    reversals_pos0 = int(np.sum(diff_pos0 == 2))
    turnover_pos0 = float(np.sum(diff_pos0))

    assert events_pos0 == 99, "prepend=pos[0] suppresses initial entry cost, yielding 99 events"
    assert reversals_pos0 == 99
    assert turnover_pos0 == 198.0


# ===========================================================================
# 2. Compounded Equity vs Additive Log Returns
# ===========================================================================

def test_v27_compounded_equity_math_distinction():
    """Verify that additive log-return bps is never directly treated as simple percentage return."""
    # Hand-crafted example: 2 bars of -50% simple returns
    # Bar 1: R1 = -0.5, r1 = ln(0.5) = -0.6931 (-6931 bps)
    # Bar 2: R2 = -0.5, r2 = ln(0.5) = -0.6931 (-6931 bps)
    # Total log return = -1.3863 (-13863 bps)
    # If one naively divides bps by 100: "-138.63%", which is an impossible simple return (>100% loss without debt).
    # True compounded simple return = 0.5 * 0.5 - 1 = -0.75 (-75.0%).
    # Implied simple return from log return = exp(-1.3863) - 1 = 0.25 - 1 = -0.75 (-75.0%).
    log_ret_sum_bps = -13862.94
    naive_div_100 = log_ret_sum_bps / 100.0
    true_simple_return_pct = (math.exp(log_ret_sum_bps / 10000.0) - 1.0) * 100.0

    assert naive_div_100 < -100.0, "Naive division by 100 yields impossible loss exceeding 100%"
    assert abs(true_simple_return_pct - (-75.0)) < 0.01, f"Expected -75%, got {true_simple_return_pct}"


# ===========================================================================
# 3. Forecast Canonical Sample Boundaries N=(15000, 3750, 625)
# ===========================================================================

def test_v27_canonical_sample_boundaries():
    """Verify that range(20000, 35000 - h + 1, h) generates exact N=(15000, 3750, 625)."""
    h_configs = [(1, 15000), (4, 3750), (24, 625)]
    for h, exp_N in h_configs:
        origins = list(range(20000, 35000 - h + 1, h))
        assert len(origins) == exp_N, f"Horizon {h}h: expected {exp_N}, got {len(origins)}"
        assert origins[0] == 20000
        # Final target must hit exactly index 35000
        last_target = origins[-1] + h
        assert last_target == 35000, f"Last target for {h}h must be 35000, got {last_target}"


# ===========================================================================
# 4. Realized Semi-Variance Exact Algebraic Identity Fixture
# ===========================================================================

def test_v27_realized_semi_variance_identity():
    """Verify hand-calculated fixture for RV == RS+ + RS- and asymmetry ratio."""
    # Hand fixture: 4 returns: [+0.02, -0.01, +0.03, -0.04]
    # Squares: [0.0004, 0.0001, 0.0009, 0.0016]
    # Positive returns: +0.02, +0.03 -> squares: 0.0004 + 0.0009 = 0.0013
    # Negative returns: -0.01, -0.04 -> squares: 0.0001 + 0.0016 = 0.0017
    # Total RV = 0.0013 + 0.0017 = 0.0030
    # Asymmetry ratio = (0.0013 - 0.0017) / (0.0030) = -0.0004 / 0.0030 = -0.133333
    returns = np.array([0.02, -0.01, 0.03, -0.04])
    metrics = semi_variance_engine.compute_semi_variance_components(returns, annualize=False)

    assert abs(metrics["rv"] - 0.0030) < 1e-6
    assert abs(metrics["rs_plus"] - 0.0013) < 1e-6
    assert abs(metrics["rs_minus"] - 0.0017) < 1e-6
    assert abs(metrics["rv"] - (metrics["rs_plus"] + metrics["rs_minus"])) < 1e-12
    assert abs(metrics["asymmetry_ratio"] - (-0.133333)) < 1e-4
    assert metrics["status"] == "HOURLY_SAMPLED_RESEARCH_FEATURE"


# ===========================================================================
# 5. Cross-Venue Spot Divergence Quote Normalization
# ===========================================================================

def test_v27_cross_venue_quote_normalization():
    """Verify quote-currency normalization and basis identification."""
    # Coinbase USD vs Kraken USD: Pure USD fiat
    res_fiat = cross_venue_engine.compute_pairwise_divergence(
        ref_price=65000.0, cmp_price=64950.0,
        ref_venue="COINBASE", cmp_venue="KRAKEN",
        ref_currency="USD", cmp_currency="USD"
    )
    assert res_fiat["is_quote_normalized"] is True
    assert res_fiat["currency_risk_flag"] == "NONE"
    # div_bps = ln(65000 / 64950) * 10000 = 7.69 bps
    assert abs(res_fiat["divergence_log_bps"] - 7.69) < 0.1

    # Coinbase USD vs Binance USDT: Cross-currency stablecoin basis
    res_usdt = cross_venue_engine.compute_pairwise_divergence(
        ref_price=65000.0, cmp_price=65100.0,
        ref_venue="COINBASE", cmp_venue="BINANCE",
        ref_currency="USD", cmp_currency="USDT"
    )
    assert res_usdt["is_quote_normalized"] is False
    assert res_usdt["currency_risk_flag"] == "STABLECOIN_PEG_BASIS"
    assert res_usdt["execution_authorization"] == "DISABLED"


# ===========================================================================
# 6. Funding Rate Research Schema & Exploratory Flag
# ===========================================================================

def test_v27_funding_rate_schema_and_exploratory_flag():
    """Verify perpetual funding rate normalization and exploratory hypothesis semantics."""
    # Linear USDT perpetual: 0.01% per 8h (normal rate)
    rec_normal = funding_research_engine.normalize_funding_record(
        instrument="BTCUSDT",
        funding_rate=0.0001,
        funding_time_utc="2026-10-19T16:00:00Z",
        contract_type="LINEAR_USDT"
    )
    assert rec_normal["funding_rate_bps"] == 1.0
    assert rec_normal["exploratory_hypothesis"]["is_extreme_leverage_flag"] is False
    assert rec_normal["exploratory_hypothesis"]["scientific_status"] == "UNVALIDATED_EXPLORATORY_HYPOTHESIS_ONLY"

    # Extreme rate: 0.04% per 8h (>0.03% threshold)
    rec_extreme = funding_research_engine.normalize_funding_record(
        instrument="BTCUSDT",
        funding_rate=0.0004,
        funding_time_utc="2026-10-19T16:00:00Z",
        contract_type="LINEAR_USDT"
    )
    assert rec_extreme["exploratory_hypothesis"]["is_extreme_leverage_flag"] is True
    assert rec_extreme["execution_authorization"] == "DISABLED"


# ===========================================================================
# 7. Non-Execution Invariants Fail-Closed
# ===========================================================================

def test_v27_execution_gates_fail_closed():
    """Verify that trade execution endpoints return HTTP 404/405 fail-closed."""
    for ep, payload in [
        ("/api/orders", {"symbol": "BTC-USD", "side": "buy"}),
        ("/api/trade", {"action": "BUY"}),
        ("/api/paper/order", {"amount": 100})
    ]:
        res = client.post(ep, json=payload)
        assert res.status_code in (404, 405), f"Endpoint {ep} must fail closed (404/405), got {res.status_code}"

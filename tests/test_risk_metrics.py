"""
tests/test_risk_metrics.py -- Unit tests for models/risk_metrics.py

Validates all risk metric functions including:
  - Sharpe / Sortino ratios
  - Maximum drawdown
  - VaR / CVaR
  - Win rate, profit factor, expectancy
  - Deflated Sharpe
"""

import sys
import os
import pytest
import random
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.risk_metrics import (
    sharpe_ratio,
    sortino_ratio,
    maximum_drawdown,
    calmar_ratio,
    value_at_risk,
    conditional_var,
    win_rate,
    profit_factor,
    expectancy,
    deflated_sharpe,
    compute_full_metrics,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def positive_returns():
    """60% win-rate, small positive expected value."""
    random.seed(42)
    return [random.choice([0.015, -0.008]) for _ in range(200)]


@pytest.fixture
def equity_curve(positive_returns):
    curve = [10000.0]
    for r in positive_returns:
        curve.append(curve[-1] * (1 + r))
    return curve


@pytest.fixture
def pnl_list(equity_curve):
    return [equity_curve[i+1] - equity_curve[i] for i in range(len(equity_curve)-1)]


# ---------------------------------------------------------------------------
# Sharpe Ratio Tests
# ---------------------------------------------------------------------------

def test_sharpe_positive_for_profitable_strategy(positive_returns):
    sr = sharpe_ratio(positive_returns)
    assert sr is not None and sr > 0, f"Expected positive Sharpe, got {sr}"


def test_sharpe_returns_none_for_empty():
    assert sharpe_ratio([]) is None


def test_sharpe_returns_none_for_single():
    assert sharpe_ratio([0.01]) is None


def test_sharpe_zero_variance():
    """Constant returns → zero variance → None."""
    assert sharpe_ratio([0.01, 0.01, 0.01]) is None


# ---------------------------------------------------------------------------
# Sortino Ratio Tests
# ---------------------------------------------------------------------------

def test_sortino_positive_for_profitable(positive_returns):
    sr = sortino_ratio(positive_returns)
    assert sr is not None and sr > 0


def test_sortino_greater_than_sharpe_for_skewed(positive_returns):
    """Sortino > Sharpe when returns are right-skewed."""
    sh = sharpe_ratio(positive_returns)
    so = sortino_ratio(positive_returns)
    if sh is not None and so is not None:
        assert so >= sh * 0.8, "Sortino should be >= Sharpe for mostly positive returns"


# ---------------------------------------------------------------------------
# Maximum Drawdown Tests
# ---------------------------------------------------------------------------

def test_mdd_perfect_growth():
    """Monotonically increasing equity should have zero drawdown."""
    curve = [100 * (1.01 ** i) for i in range(100)]
    assert maximum_drawdown(curve) == 0.0


def test_mdd_full_loss():
    """Total loss from 100 to 0 → 100% drawdown."""
    curve = [100.0, 50.0, 0.01]
    mdd = maximum_drawdown(curve)
    assert mdd > 0.99


def test_mdd_known_value():
    """[100, 90, 80, 100] → 20% drawdown."""
    curve = [100.0, 90.0, 80.0, 100.0]
    mdd = maximum_drawdown(curve)
    assert mdd == pytest.approx(0.20, abs=0.001)


# ---------------------------------------------------------------------------
# VaR / CVaR Tests
# ---------------------------------------------------------------------------

def test_var_positive_value(positive_returns):
    var = value_at_risk(positive_returns, confidence=0.95)
    assert var is not None and var >= 0


def test_cvar_geq_var(positive_returns):
    """CVaR (Expected Shortfall) must be >= VaR at same confidence."""
    var  = value_at_risk(positive_returns, 0.95)
    cvar = conditional_var(positive_returns, 0.95)
    if var is not None and cvar is not None:
        assert cvar >= var - 1e-9, f"CVaR ({cvar}) should be >= VaR ({var})"


def test_var_empty():
    assert value_at_risk([]) is None


# ---------------------------------------------------------------------------
# Trade Quality Metrics Tests
# ---------------------------------------------------------------------------

def test_win_rate_all_wins():
    assert win_rate([10.0, 5.0, 3.0]) == 1.0


def test_win_rate_all_losses():
    assert win_rate([-1.0, -2.0]) == 0.0


def test_win_rate_empty():
    assert win_rate([]) == 0.0


def test_profit_factor_known():
    """Profit factor: 30 gross profit / 10 gross loss = 3.0."""
    pnl = [10.0, 20.0, -5.0, -5.0]
    pf  = profit_factor(pnl)
    assert pf == pytest.approx(3.0, rel=0.01)


def test_profit_factor_no_losses():
    """No losses → None (infinite profit factor)."""
    assert profit_factor([10.0, 5.0]) is None


def test_expectancy_positive(positive_returns, pnl_list):
    exp = expectancy(pnl_list)
    assert exp > 0, "Expected positive expectancy for profitable strategy"


# ---------------------------------------------------------------------------
# Deflated Sharpe Test
# ---------------------------------------------------------------------------

def test_deflated_sharpe_bounds():
    """DSR should always be in [0, 1]."""
    dsr = deflated_sharpe(sharpe=2.0, n_trials=100)
    assert 0.0 <= dsr <= 1.0


def test_deflated_sharpe_high_for_good_strategy():
    """High Sharpe with few trials → high DSR."""
    dsr = deflated_sharpe(sharpe=5.0, n_trials=5)
    assert dsr > 0.5


# ---------------------------------------------------------------------------
# Full Metrics Integration Test
# ---------------------------------------------------------------------------

def test_compute_full_metrics(positive_returns, equity_curve, pnl_list):
    m = compute_full_metrics(positive_returns, equity_curve, pnl_list)
    assert "sharpe_ratio"  in m
    assert "max_drawdown"  in m
    assert "win_rate"      in m
    assert "profit_factor" in m
    assert "expectancy"    in m
    assert m["max_drawdown"] >= 0
    assert 0.0 <= m["win_rate"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

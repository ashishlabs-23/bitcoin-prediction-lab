"""
tests/test_position_manager.py -- Unit tests for models/position_manager.py

Covers:
  - Kelly fraction computation
  - Correct position sizing for LONG/SHORT/SKIP
  - Regime cap enforcement
  - Risk overlay blocking
  - Edge cases (zero SL, extreme probabilities)
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.position_manager import (
    kelly_fraction,
    compute_position,
    RiskOverlay,
    MAX_POSITION_PCT,
    MIN_POSITION_PCT,
)

# ---------------------------------------------------------------------------
# Kelly Fraction Tests
# ---------------------------------------------------------------------------

def test_kelly_positive_edge():
    """Kelly should be positive for a profitable setup."""
    kf = kelly_fraction(prob_win=0.60, win_return=0.02, loss_return=0.01)
    assert kf > 0, "Expected positive Kelly fraction for profitable setup"


def test_kelly_negative_edge():
    """Kelly should be near-zero or negative for a losing setup."""
    kf = kelly_fraction(prob_win=0.40, win_return=0.01, loss_return=0.02)
    assert kf <= 0.05, f"Expected low/negative Kelly, got {kf}"


def test_kelly_zero_win_return():
    """Zero win_return should return Kelly=0."""
    kf = kelly_fraction(prob_win=0.70, win_return=0.0, loss_return=0.01)
    assert kf == 0.0


def test_kelly_zero_loss_return():
    """Zero loss_return should return Kelly=0 (undefined odds)."""
    kf = kelly_fraction(prob_win=0.70, win_return=0.02, loss_return=0.0)
    assert kf == 0.0


# ---------------------------------------------------------------------------
# Position Sizing Tests
# ---------------------------------------------------------------------------

def test_long_position_basic():
    """LONG signal should produce a positive position with valid TP/SL."""
    spec = compute_position(
        direction="LONG",
        prob=0.72,
        entry_price=63000.0,
        tp_price=64600.0,
        sl_price=62200.0,
        portfolio_value=10_000.0,
        regime="TRENDING_BULL",
    )
    assert spec.direction == "LONG"
    assert MIN_POSITION_PCT <= spec.position_pct <= MAX_POSITION_PCT
    assert spec.position_btc > 0
    assert spec.risk_reward_ratio == pytest.approx(2.0, rel=0.01)


def test_short_position_basic():
    """SHORT signal should produce a valid short position."""
    spec = compute_position(
        direction="SHORT",
        prob=0.68,
        entry_price=63000.0,
        tp_price=61500.0,
        sl_price=63700.0,
        portfolio_value=10_000.0,
        regime="TRENDING_BEAR",
    )
    assert spec.direction == "SHORT"
    assert spec.position_pct > 0


def test_skip_signal():
    """SKIP direction should always return zero position."""
    spec = compute_position(
        direction="SKIP",
        prob=0.50,
        entry_price=63000.0,
        tp_price=63500.0,
        sl_price=62500.0,
        portfolio_value=10_000.0,
        regime="RANGING",
    )
    assert spec.direction == "SKIP"
    assert spec.position_pct == 0.0
    assert spec.position_btc == 0.0


def test_regime_cap_high_volatility():
    """HIGH_VOLATILITY regime should cap position at 5%."""
    spec = compute_position(
        direction="LONG",
        prob=0.85,
        entry_price=63000.0,
        tp_price=66000.0,
        sl_price=60000.0,
        portfolio_value=10_000.0,
        regime="HIGH_VOLATILITY",
    )
    assert spec.position_pct <= 0.05, f"Expected <=5% in HIGH_VOLATILITY, got {spec.position_pct:.2%}"


def test_regime_cap_ranging():
    """RANGING regime should cap position at 8%."""
    spec = compute_position(
        direction="LONG",
        prob=0.85,
        entry_price=63000.0,
        tp_price=66000.0,
        sl_price=60000.0,
        portfolio_value=10_000.0,
        regime="RANGING",
    )
    assert spec.position_pct <= 0.08, f"Expected <=8% in RANGING, got {spec.position_pct:.2%}"


def test_risk_overlay_drawdown_block():
    """RiskOverlay should block new positions when drawdown limit is breached."""
    overlay = RiskOverlay(current_drawdown=0.16, max_drawdown_limit=0.15)
    spec = compute_position(
        direction="LONG",
        prob=0.72,
        entry_price=63000.0,
        tp_price=64600.0,
        sl_price=62200.0,
        portfolio_value=10_000.0,
        regime="TRENDING_BULL",
        risk_overlay=overlay,
    )
    assert spec.direction == "SKIP", "Expected SKIP when drawdown limit breached"
    assert "drawdown" in spec.rationale.lower()


def test_risk_overlay_open_positions_block():
    """RiskOverlay should block when max open positions reached."""
    overlay = RiskOverlay(open_positions=3, max_open_positions=3)
    spec = compute_position(
        direction="LONG",
        prob=0.72,
        entry_price=63000.0,
        tp_price=64600.0,
        sl_price=62200.0,
        portfolio_value=10_000.0,
        regime="TRENDING_BULL",
        risk_overlay=overlay,
    )
    assert spec.direction == "SKIP", "Expected SKIP when max open positions reached"


def test_position_pct_bounds():
    """Position size should always be within [MIN, MAX] for active signals."""
    spec = compute_position(
        direction="LONG",
        prob=0.99,
        entry_price=63000.0,
        tp_price=70000.0,
        sl_price=60000.0,
        portfolio_value=1_000_000.0,
        regime="TRENDING_BULL",
    )
    assert spec.position_pct <= MAX_POSITION_PCT, "Should never exceed max position cap"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

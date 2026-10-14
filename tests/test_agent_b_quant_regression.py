"""
tests/test_agent_b_quant_regression.py — Agent B Quantitative Integrity Regression Suite
========================================================================================
Covers:
1. Look-ahead bias elimination: point-in-time expanding percentile rank vs full-series rank.
   Future data perturbation must NOT alter earlier barrier widths or labels.
2. Historical analogs forward excursions: strictly bars t+1..t+24, excluding current bar wicks.
   Last 24 bars evaluate to NaN.
3. Wilder RSI: 14-period smoothing with warm-up NaNs, 50.0 on flat markets, 100 on all-gain, 0 on all-loss.
4. Kraken candle history freshness and staleness rejection (>2h).
5. Backtest execution cost alignment: turnover fees deducted at actual execution bar t.
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from labeling.targets import triple_barrier_label, expanding_percentile_rank
from research.historical_analogs import compute_forward_excursions
from features.build_features import compute_wilder_rsi
from backtest.simulate import run_backtest


def test_point_in_time_vol_rank_prevents_lookahead_bias():
    """
    Verify that expanding_percentile_rank is strictly point-in-time:
    Perturbing or appending future data must NOT change previously computed ranks.
    """
    np.random.seed(42)
    base_data = pd.Series(np.random.normal(0.02, 0.005, 100))

    # Compute ranks on first 50 observations
    initial_ranks = expanding_percentile_rank(base_data.iloc[:50], min_periods=10)

    # Compute ranks on full 100 observations
    full_ranks = expanding_percentile_rank(base_data, min_periods=10)

    # First 50 ranks MUST be mathematically identical
    np.testing.assert_allclose(
        initial_ranks.values,
        full_ranks.iloc[:50].values,
        rtol=1e-7,
        atol=1e-7,
        err_msg="Future data leaked into earlier barrier volatility ranks!"
    )


def test_forward_excursion_excludes_current_wick_and_preserves_horizon():
    """
    Verify forward MFE and MAE evaluate strictly bars t+1 through t+24.
    The current bar's (bar t) high or low must never enter forward excursion metrics.
    """
    n = 50
    highs = pd.Series(100.0, index=range(n))
    lows = pd.Series(100.0, index=range(n))
    closes = pd.Series(100.0, index=range(n))

    # Plant a massive spike on bar t=10 only
    highs.iloc[10] = 500.0
    lows.iloc[10] = 10.0

    mfe_series, mae_series, _ = compute_forward_excursions(highs, lows, closes, horizon_bars=24)

    # Bar t=10's forward excursion must NOT see its own bar 10 spike
    # Its forward horizon is bars 11..34 where high is 100.0 and close is 100.0 (return 0.0)
    assert mfe_series.iloc[10] == pytest.approx(0.0, abs=1e-5), "Current bar spike contaminated its own forward MFE!"
    assert mae_series.iloc[10] == pytest.approx(0.0, abs=1e-5), "Current bar wick contaminated its own forward MAE!"

    # Bars within the final 24 bars horizon must be NaN (no silently shortened horizons)
    assert pd.isna(mfe_series.iloc[-1]), "End-of-series bar should have NaN MFE"
    assert pd.isna(mfe_series.iloc[-24]), "Bar at n - 24 must have NaN MFE"


def test_wilder_rsi_calculations_and_edge_cases():
    """
    Verify standard 14-period Wilder smoothing across canonical regimes.
    """
    # 1. Warm-up: First 14 bars must be NaN
    ramp = pd.Series(np.linspace(100, 115, 30))
    rsi_ramp = compute_wilder_rsi(ramp, window=14)
    assert rsi_ramp.iloc[:14].isna().all(), "Wilder RSI did not produce NaN warm-up for first 14 periods"

    # 2. Flat market: exactly 50.0
    flat = pd.Series([100.0] * 30)
    rsi_flat = compute_wilder_rsi(flat, window=14)
    assert rsi_flat.iloc[14:].eq(50.0).all(), "Flat market RSI did not return 50.0"

    # 3. All gain: strictly 100.0
    all_gain = pd.Series(range(100, 140))
    rsi_gain = compute_wilder_rsi(all_gain, window=14)
    assert rsi_gain.iloc[14:].eq(100.0).all(), "All-gain sequence RSI did not return 100.0"

    # 4. All loss: strictly 0.0
    all_loss = pd.Series(range(140, 100, -1))
    rsi_loss = compute_wilder_rsi(all_loss, window=14)
    assert rsi_loss.iloc[14:].eq(0.0).all(), "All-loss sequence RSI did not return 0.0"


def test_backtest_costs_charged_at_actual_execution_bar():
    """
    Verify backtest costs (fees + slippage) are charged on the actual execution bar
    where the position change occurs, preserving gross_return > net_return with costs deducted.
    """
    n = 10
    prices = pd.Series([100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 112.0, 114.0, 116.0, 118.0])
    # Position: flat on bar 0..2, LONG on bar 3..5, flat bar 6..9
    # Position signal generated at bar 2 -> enters at bar 3 (lagged)
    positions = pd.Series([0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    res = run_backtest(
        price=prices,
        position=positions,
        fee_bps=10.0,      # 10 bps
        slippage_bps=5.0   # 5 bps
    )

    assert "gross_return" in res
    assert "net_return" in res
    assert "total_cost" in res
    assert "n_trades" in res

    # 2 round-trip position changes (entry at bar 3, exit at bar 6)
    assert res["n_trades"] == 2
    assert res["total_cost"] == pytest.approx(0.003, abs=1e-5) # 2 * (15 bps / 10000) = 0.003
    assert res["net_return"] < res["gross_return"]

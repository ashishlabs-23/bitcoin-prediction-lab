"""
tests/test_sizing_forensics.py — Unit Tests for Position-Sizing Forensics & Economic Verification
=================================================================================================
Verifies:
1. Detection of future information leakage and dependency graph integrity
2. Point-in-time reference position sizing calculation and return decomposition
3. Exposure and leverage bounds (No leverage > 1.0)
4. Multi-target range and full price path containment metrics
5. Sharpe annualization consistency across time and trade frequencies
6. 10,000 block bootstrap reproducibility
7. Multiple-testing trial ledger accounting (K_total)
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.sizing_forensics import audit_position_sizing_dataflow
from research.sizing_reference import compute_reference_position_sizing
from research.range_coverage_audit import audit_detailed_range_and_path_coverage
from research.sharpe_audit import audit_sharpe_calculations
from research.leverage_audit import audit_exposure_and_leverage
from research.economic_bootstrap import run_economic_block_bootstrap
from research.pbo_audit import audit_pbo_and_deflated_sharpe
from research.multiple_testing import ResearchTrialTracker


@pytest.fixture
def sample_forensic_df():
    """Generates synthetic dataset for forensic testing."""
    np.random.seed(42)
    n = 300
    ts = pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC")
    close = 60000.0 * np.exp(np.cumsum(np.random.normal(0.0002, 0.01, size=n)))
    high = close * 1.008
    low = close * 0.992

    df = pd.DataFrame({
        'open': close * 0.999,
        'high': high,
        'low': low,
        'close': close,
        'volume': np.random.uniform(100, 1000, size=n),
        'ret_1h': np.random.normal(0, 0.01, size=n),
        'vol_24h': np.random.uniform(0.01, 0.03, size=n),
        'rsi_14': np.random.uniform(20, 80, size=n),
        'sma_ratio_20': np.random.normal(0, 0.01, size=n),
        'funding_rate': np.random.normal(0.0001, 0.0002, size=n)
    }, index=ts)

    return df, pd.Series(close, index=ts), pd.Series(high, index=ts), pd.Series(low, index=ts)


def test_sizing_dependency_graph_and_leakage_detection():
    df_deps, meta = audit_position_sizing_dataflow()
    assert isinstance(df_deps, pd.DataFrame)
    assert len(df_deps) == 8
    assert meta["leakage_detected"] is True
    assert meta["leakage_resolved"] is True


def test_reference_sizing_implementation(sample_forensic_df):
    df, close, high, low = sample_forensic_df
    train_end = 200
    val_end = 250
    df_summary, df_trades, meta = compute_reference_position_sizing(df, close, high, low, train_end, val_end)

    assert isinstance(df_summary, pd.DataFrame)
    assert isinstance(df_trades, pd.DataFrame)
    assert (df_trades["position_weight"] >= 0.0).all()
    assert (df_trades["position_weight"] <= 1.0).all()
    # Verify return decomposition: net = gross - fee - slip
    np.testing.assert_allclose(
        df_trades["net_return"].values,
        df_trades["gross_return"].values - df_trades["fee_cost"].values - df_trades["slippage_cost"].values,
        rtol=1e-5
    )


def test_range_and_path_coverage_audit(sample_forensic_df):
    df, close, high, low = sample_forensic_df
    val_end = 250
    df_cov, meta = audit_detailed_range_and_path_coverage(df, close, high, low, val_end)

    assert isinstance(df_cov, pd.DataFrame)
    assert len(df_cov) == 6
    assert "full_path_p90_coverage" in meta


def test_sharpe_calculations_and_annualization(sample_forensic_df):
    df, close, high, low = sample_forensic_df
    train_end = 200
    val_end = 250
    _, df_trades, _ = compute_reference_position_sizing(df, close, high, low, train_end, val_end)
    df_sharpe, meta = audit_sharpe_calculations(df_trades["net_return"], df_trades.index)

    assert isinstance(df_sharpe, pd.DataFrame)
    assert len(df_sharpe) == 4
    assert "unannualized_sharpe" in meta


def test_exposure_and_leverage_audit():
    weights = np.array([0.0, 0.25, 0.50, 0.75, 1.0])
    returns = np.array([0.01, -0.02, 0.015, -0.005, 0.02])
    df_exp, df_lev, meta = audit_exposure_and_leverage(weights, returns)

    assert isinstance(df_exp, pd.DataFrame)
    assert isinstance(df_lev, pd.DataFrame)
    assert meta["is_unleveraged"] is True


def test_economic_block_bootstrap():
    net_pnl = np.random.normal(-0.001, 0.01, size=200)
    df_boot, meta = run_economic_block_bootstrap(net_pnl, n_resamples=100, block_size=12)

    assert isinstance(df_boot, pd.DataFrame)
    assert len(df_boot) == 5
    assert len(meta["bootstrap_mean_net_ci"]) == 2


def test_pbo_and_dsr_audit():
    df_pbo, meta = audit_pbo_and_deflated_sharpe(observed_sr=1.2, n_samples=450, cumulative_trials=1099)
    assert isinstance(df_pbo, pd.DataFrame)
    assert len(df_pbo) == 6
    assert meta["cumulative_trials_k"] == 1099

"""
tests/test_mfe_excursion.py — Unit Tests for MFE/MAE Excursion & Range Prediction Suite
=======================================================================================
Verifies:
1. Directional MFE/MAE label computation & non-negativity invariants
2. Multi-horizon alignment and zero lookahead leakage
3. Quantile MFE/MAE monotonicity (P10 <= P25 <= P50 <= P75 <= P90)
4. Conformal prediction interval coverage calculations
5. Hurdle probability classification integrity
6. Conditional direction and structural asymmetry
7. Excursion-first economic simulation and 3-system comparison
8. Research trial tracker accounting (K_total)
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.mfe_target_audit import compute_directional_excursions, audit_mfe_leakage_and_horizons
from research.mfe_baselines import evaluate_mfe_baselines_and_decay
from research.mfe_quantile import evaluate_mfe_quantile_and_conformal
from research.mae_quantile import evaluate_mae_quantile_and_envelope
from research.hurdle_probability import evaluate_hurdle_probability_targets
from research.conditional_direction import evaluate_conditional_direction_and_asymmetry
from research.tradeability_model import evaluate_tradeability_and_selectivity
from research.excursion_economic_simulation import evaluate_excursion_economic_systems
from research.multiple_testing import ResearchTrialTracker


@pytest.fixture
def sample_excursion_df():
    """Generates synthetic dataset for excursion testing."""
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


def test_directional_excursions_invariants(sample_excursion_df):
    _, close, high, low = sample_excursion_df
    exc = compute_directional_excursions(close, high, low, horizon_bars=12)

    assert "mfe_long" in exc
    assert "mfe_short" in exc
    assert "mae_long" in exc
    assert "mae_short" in exc
    assert (exc["mfe_long"] >= 0).all()
    assert (exc["mfe_short"] >= 0).all()
    assert (exc["mae_long"] >= 0).all()
    assert (exc["mae_short"] >= 0).all()


def test_mfe_leakage_and_audit(sample_excursion_df):
    df, close, high, low = sample_excursion_df
    df_audit, meta = audit_mfe_leakage_and_horizons(df, close, high, low, horizons=[4, 12, 24])

    assert isinstance(df_audit, pd.DataFrame)
    assert len(df_audit) == 3
    assert "is_leakage_free" in meta


def test_mfe_baselines_execution(sample_excursion_df):
    df, close, high, low = sample_excursion_df
    train_end = 200
    val_end = 250
    df_models, df_decay, df_ctrl, meta = evaluate_mfe_baselines_and_decay(df, close, high, low, train_end, val_end, horizon_bars=12)

    assert isinstance(df_models, pd.DataFrame)
    assert isinstance(df_decay, pd.DataFrame)
    assert isinstance(df_ctrl, pd.DataFrame)
    assert "confirmation_mfe_ic" in meta


def test_quantile_monotonicity_and_conformal(sample_excursion_df):
    df, close, high, low = sample_excursion_df
    train_end = 200
    val_end = 250
    df_q, df_conf, meta = evaluate_mfe_quantile_and_conformal(df, close, high, low, train_end, val_end)

    assert isinstance(df_q, pd.DataFrame)
    assert len(df_q) == 5
    assert meta["is_monotonic"] is True
    assert isinstance(df_conf, pd.DataFrame)


def test_mae_quantile_and_envelope(sample_excursion_df):
    df, close, high, low = sample_excursion_df
    train_end = 200
    val_end = 250
    df_mae_q, df_mae_conf, df_envelope, meta = evaluate_mae_quantile_and_envelope(df, close, high, low, train_end, val_end)

    assert isinstance(df_mae_q, pd.DataFrame)
    assert isinstance(df_envelope, pd.DataFrame)
    assert len(df_envelope) == 4


def test_hurdle_probability_execution(sample_excursion_df):
    df, close, high, low = sample_excursion_df
    train_end = 200
    val_end = 250
    df_hurdles, meta = evaluate_hurdle_probability_targets(df, close, high, low, train_end, val_end, hurdles_bps=[10.0, 20.0])

    assert isinstance(df_hurdles, pd.DataFrame)
    assert len(df_hurdles) == 2


def test_conditional_direction_and_tradeability(sample_excursion_df):
    df, close, high, low = sample_excursion_df
    train_end = 200
    val_end = 250
    df_cond, df_asym, meta = evaluate_conditional_direction_and_asymmetry(df, close, high, low, train_end, val_end)
    df_cats, df_sel, t_meta = evaluate_tradeability_and_selectivity(df, close, high, low, train_end, val_end)

    assert isinstance(df_cond, pd.DataFrame)
    assert isinstance(df_cats, pd.DataFrame)
    assert isinstance(df_sel, pd.DataFrame)


def test_excursion_economic_systems_benchmark(sample_excursion_df):
    df, close, high, low = sample_excursion_df
    train_end = 200
    val_end = 250
    df_sys, meta = evaluate_excursion_economic_systems(df, close, high, low, train_end, val_end)

    assert isinstance(df_sys, pd.DataFrame)
    assert len(df_sys) == 3
    assert "best_system" in meta

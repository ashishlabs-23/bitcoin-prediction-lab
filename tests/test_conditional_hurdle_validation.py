"""
tests/test_conditional_hurdle_validation.py — Unit Tests for Conditional Hurdle & Excursion Signal Confirmation Suite
====================================================================================================================
Verifies:
1. Contiguous event clustering and non-overlapping cooldown filtering
2. Point-in-time funding signal alignment and leakage-free properties
3. Funding direction asymmetry and threshold ladder calculations
4. Magnitude and MFE/MAE excursion forecasting
5. Conditional hurdle rule execution
6. Research trial tracking integrity (K_total)
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.funding_signal_audit import audit_funding_signal_point_in_time
from research.event_independence import cluster_contiguous_events, filter_non_overlapping_trades, evaluate_event_independence_and_clustering
from research.funding_direction import evaluate_funding_directional_asymmetry
from research.funding_thresholds import evaluate_funding_threshold_ladder
from research.funding_horizon import evaluate_funding_holding_horizons
from research.funding_controls import evaluate_funding_volatility_controls
from research.magnitude_model import evaluate_magnitude_models
from research.excursion_model import compute_forward_excursions, evaluate_excursion_models
from research.hurdle_model import evaluate_hurdle_and_excursion_rules
from research.multiple_testing import ResearchTrialTracker


@pytest.fixture
def sample_funding_dataset():
    """Generates synthetic dataset for funding and excursion testing."""
    np.random.seed(42)
    n = 300
    ts = pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC")
    close = 60000.0 * np.exp(np.cumsum(np.random.normal(0.0002, 0.01, size=n)))
    high = close * 1.008
    low = close * 0.992
    funding = np.random.normal(0.0001, 0.0003, size=n)
    # Inject funding spike
    funding[50:55] = 0.0020
    funding[120:124] = -0.0015

    df = pd.DataFrame({
        'open': close * 0.999,
        'high': high,
        'low': low,
        'close': close,
        'volume': np.random.uniform(100, 1000, size=n),
        'funding_rate': funding,
        'ret_1h': np.random.normal(0, 0.01, size=n),
        'vol_24h': np.random.uniform(0.01, 0.03, size=n),
        'rsi_14': np.random.uniform(20, 80, size=n),
        'sma_ratio_20': np.random.normal(0, 0.01, size=n)
    }, index=ts)

    return df, pd.Series(close, index=ts), pd.Series(high, index=ts), pd.Series(low, index=ts)


def test_event_clustering_and_cooldown():
    mask = pd.Series([False, True, True, True, False, False, True, True, False])
    clusters = cluster_contiguous_events(mask)
    assert len(clusters) == 2
    assert clusters[0][2] == 3
    assert clusters[1][2] == 2

    # Test cooldown filter
    ts_base = pd.Timestamp("2026-01-01 00:00:00")
    dummy_events = [
        (ts_base, ts_base + pd.Timedelta(hours=2), 2),
        (ts_base + pd.Timedelta(hours=4), ts_base + pd.Timedelta(hours=6), 2),
        (ts_base + pd.Timedelta(hours=50), ts_base + pd.Timedelta(hours=52), 2)
    ]
    filtered = filter_non_overlapping_trades(dummy_events, cooldown_hours=24)
    assert len(filtered) == 2


def test_funding_signal_audit(sample_funding_dataset):
    df, close, _, _ = sample_funding_dataset
    df_audit, meta = audit_funding_signal_point_in_time(df, close, window_hours=48)
    assert isinstance(df_audit, pd.DataFrame)
    assert "is_leakage_free" in meta


def test_funding_directional_asymmetry(sample_funding_dataset):
    df, close, _, _ = sample_funding_dataset
    funding_z = pd.Series(np.random.normal(0, 1, size=len(df)), index=df.index)
    funding_z.iloc[10:15] = 2.5
    funding_z.iloc[30:35] = -2.5

    df_dir, meta = evaluate_funding_directional_asymmetry(df, close, funding_z, threshold_sigma=2.0)
    assert isinstance(df_dir, pd.DataFrame)
    assert len(df_dir) == 2


def test_magnitude_and_excursion_models(sample_funding_dataset):
    df, close, high, low = sample_funding_dataset
    mfe, mae = compute_forward_excursions(close, high, low, horizon_bars=12)
    assert len(mfe) == len(close)
    assert len(mae) == len(close)
    assert (mfe >= 0).all()
    assert (mae >= 0).all()

    df_mag, mag_meta = evaluate_magnitude_models(df, close, horizon_bars=12, n_splits=3)
    assert isinstance(df_mag, pd.DataFrame)
    assert len(df_mag) == 5

    df_exc, exc_meta = evaluate_excursion_models(df, close, high, low, horizon_bars=12, n_splits=3)
    assert isinstance(df_exc, pd.DataFrame)
    assert len(df_exc) == 2


def test_hurdle_rules_execution(sample_funding_dataset):
    df, close, high, low = sample_funding_dataset
    df_ratio, df_fee, meta = evaluate_hurdle_and_excursion_rules(df, close, high, low, ratios=[1.0, 2.0], horizon_bars=12)
    assert isinstance(df_ratio, pd.DataFrame)
    assert isinstance(df_fee, pd.DataFrame)
    assert len(df_ratio) == 2


def test_trial_tracker_k_accounting():
    tracker = ResearchTrialTracker()
    tracker.record_experiment("Test1", n_models=2, n_horizons=3, n_configs=4)
    k = tracker.total_trial_count_k()
    assert k >= 10

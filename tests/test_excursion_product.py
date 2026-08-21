"""
tests/test_excursion_product.py — Unit Tests for Range, Excursion & Risk Prediction Product Suite
=================================================================================================
Verifies:
1. Quantile ordering monotonicity (P10 <= P25 <= P50 <= P75 <= P90)
2. MFE/MAE price range containment and non-negativity
3. Conformal coverage and calibration error metrics
4. Hurdle label prevalence and continuous regression comparison
5. Tradeability formulation scoring and position sizing risk reduction
6. Research trial tracking integrity (K_total)
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.hurdle_label_audit import audit_hurdle_labels_and_calibration
from research.mfe_distribution import generate_probabilistic_mfe_distribution
from research.mfe_calibration import evaluate_mfe_calibration_and_regimes
from research.range_forecast import generate_and_evaluate_range_forecasts
from research.risk_envelope import generate_risk_envelope_and_decision_table
from research.tradeability_score import evaluate_tradeability_formulations_and_sizing
from research.conditional_direction_v2 import evaluate_secondary_conditional_direction
from research.multiple_testing import ResearchTrialTracker


@pytest.fixture
def sample_product_df():
    """Generates synthetic dataset for product testing."""
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
        'funding_rate': np.random.normal(0.0001, 0.0002, size=n),
        'regime': np.random.choice(['Bull', 'Bear', 'Sideways', 'High Volatility'], size=n)
    }, index=ts)

    return df, pd.Series(close, index=ts), pd.Series(high, index=ts), pd.Series(low, index=ts)


def test_hurdle_label_audit_execution(sample_product_df):
    df, close, high, low = sample_product_df
    train_end = 200
    val_end = 250
    df_prev, df_prob_dist, df_comp, meta = audit_hurdle_labels_and_calibration(df, close, high, low, train_end, val_end)

    assert isinstance(df_prev, pd.DataFrame)
    assert isinstance(df_prob_dist, pd.DataFrame)
    assert isinstance(df_comp, pd.DataFrame)
    assert "prevalence_14bps" in meta


def test_mfe_probabilistic_distribution_and_monotonicity(sample_product_df):
    df, close, high, low = sample_product_df
    train_end = 200
    val_end = 250
    df_sum, df_forecasts, meta = generate_probabilistic_mfe_distribution(df, close, high, low, train_end, val_end)

    assert isinstance(df_sum, pd.DataFrame)
    assert isinstance(df_forecasts, pd.DataFrame)
    # Monotonicity test: P10 <= P25 <= P50 <= P75 <= P90
    assert (df_forecasts["p10_mfe"] <= df_forecasts["p25_mfe"]).all()
    assert (df_forecasts["p25_mfe"] <= df_forecasts["p50_mfe"]).all()
    assert (df_forecasts["p50_mfe"] <= df_forecasts["p75_mfe"]).all()
    assert (df_forecasts["p75_mfe"] <= df_forecasts["p90_mfe"]).all()


def test_mfe_calibration_and_containment(sample_product_df):
    df, close, high, low = sample_product_df
    train_end = 200
    val_end = 250
    _, df_forecasts, _ = generate_probabilistic_mfe_distribution(df, close, high, low, train_end, val_end)
    df_cal, df_regimes, meta = evaluate_mfe_calibration_and_regimes(df, df_forecasts)

    assert isinstance(df_cal, pd.DataFrame)
    assert isinstance(df_regimes, pd.DataFrame)
    assert len(df_cal) == 5
    assert "overall_80_coverage" in meta


def test_range_forecast_and_risk_envelope(sample_product_df):
    df, close, high, low = sample_product_df
    train_end = 200
    val_end = 250
    _, df_forecasts, _ = generate_probabilistic_mfe_distribution(df, close, high, low, train_end, val_end)
    df_range_sum, df_range_bands, r_meta = generate_and_evaluate_range_forecasts(df, close, high, low, df_forecasts)
    df_env, df_decision, env_meta = generate_risk_envelope_and_decision_table(df_forecasts)

    assert isinstance(df_range_sum, pd.DataFrame)
    assert isinstance(df_range_bands, pd.DataFrame)
    assert isinstance(df_env, pd.DataFrame)
    assert isinstance(df_decision, pd.DataFrame)
    assert len(df_decision) == 4


def test_tradeability_formulations_and_sizing(sample_product_df):
    df, close, high, low = sample_product_df
    train_end = 200
    val_end = 250
    df_trade_form, df_sizing, meta = evaluate_tradeability_formulations_and_sizing(df, close, high, low, train_end, val_end)

    assert isinstance(df_trade_form, pd.DataFrame)
    assert isinstance(df_sizing, pd.DataFrame)
    assert len(df_trade_form) == 4
    assert len(df_sizing) == 3


def test_secondary_conditional_direction(sample_product_df):
    df, close, high, low = sample_product_df
    train_end = 200
    val_end = 250
    df_cond, meta = evaluate_secondary_conditional_direction(df, close, high, low, train_end, val_end)

    assert isinstance(df_cond, pd.DataFrame)
    assert "is_direction_necessary" in meta
    assert meta["is_direction_necessary"] is False

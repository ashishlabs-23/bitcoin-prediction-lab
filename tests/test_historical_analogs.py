"""
tests/test_historical_analogs.py — Unit Tests for Historical Analog Retrieval
"""

import os
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from research.historical_analogs import HistoricalAnalogEngine, get_analog_engine


def test_analog_engine_initialization():
    engine = get_analog_engine()
    assert engine.df is not None
    assert len(engine.df) > 1000
    assert engine.features_norm is not None
    assert engine.features_norm.shape[1] == 6
    assert engine.feature_names == [
        'vol_1h',
        'vol_4h',
        'vol_24h',
        'term_structure_ratio',
        'funding_rate',
        'open_interest_delta_24h'
    ]


def test_expanding_window_no_lookahead():
    """
    Verify that expanding window standardization at index t depends only on rows 0..t.
    """
    engine = get_analog_engine()
    raw_feats = engine.df[engine.feature_names].values.astype(np.float64)
    norm_feats = engine.features_norm

    # Check for row t=2000
    t = 2000
    sub_raw = raw_feats[:t+1]
    expected_mean = np.mean(sub_raw, axis=0)
    expected_var = np.maximum(1e-8, np.mean(sub_raw**2, axis=0) - expected_mean**2)
    expected_std = np.sqrt(expected_var)
    expected_norm = (raw_feats[t] - expected_mean) / (expected_std + 1e-6)

    np.testing.assert_allclose(norm_feats[t], expected_norm, rtol=1e-5, atol=1e-5)


def test_embargo_exclusion():
    """
    Verify that find_analogs strictly excludes points within +/- embargo_hours.
    """
    engine = get_analog_engine()
    res = engine.find_analogs(max_k=20, embargo_hours=48, min_similarity=0.50)
    q_dt = pd.to_datetime(res['query_timestamp'], utc=True)

    for analog in res['analogs']:
        a_dt = pd.to_datetime(analog['timestamp'], utc=True)
        diff_hours = abs((a_dt - q_dt).total_seconds()) / 3600.0
        assert diff_hours >= 48.0, f"Analog {analog['timestamp']} violated 48h embargo from query {q_dt}"


def test_greedy_temporal_separation():
    """
    Verify that all selected analogs maintain at least min_separation_days between each other.
    """
    engine = get_analog_engine()
    min_sep_days = 7.0
    res = engine.find_analogs(max_k=20, min_similarity=0.80, min_separation_days=min_sep_days)
    analogs = res['analogs']
    assert len(analogs) > 0

    timestamps = [pd.to_datetime(a['timestamp'], utc=True) for a in analogs]
    for i in range(len(timestamps)):
        for j in range(i + 1, len(timestamps)):
            diff_days = abs((timestamps[i] - timestamps[j]).total_seconds()) / 86400.0
            assert diff_days >= (min_sep_days - 1e-4), (
                f"Analogs {analogs[i]['timestamp']} and {analogs[j]['timestamp']} "
                f"violated {min_sep_days}d separation (actual diff: {diff_days:.2f}d)"
            )


def test_dynamic_k_and_similarity_threshold():
    """
    Verify that dynamic k returns only analogs that clear the similarity threshold.
    """
    engine = get_analog_engine()
    # High threshold (e.g. 0.92)
    res_high = engine.find_analogs(max_k=20, min_similarity=0.92, min_separation_days=7.0)
    for a in res_high['analogs']:
        assert a['similarity_score'] >= 0.92
    assert res_high['aggregate_stats']['k_analogs_used'] == len(res_high['analogs'])

    # Standard threshold (e.g. 0.80)
    res_std = engine.find_analogs(max_k=20, min_similarity=0.80, min_separation_days=7.0)
    for a in res_std['analogs']:
        assert a['similarity_score'] >= 0.80
    assert len(res_std['analogs']) >= len(res_high['analogs'])


def test_similarity_distribution_stats():
    """
    Verify that dataset-wide similarity percentiles are correctly calculated.
    """
    engine = get_analog_engine()
    res = engine.find_analogs(max_k=20, min_similarity=0.80)

    assert "similarity_distribution" in res
    sd = res['similarity_distribution']
    assert "p10_similarity" in sd
    assert "p50_median_similarity" in sd
    assert "p90_similarity" in sd
    assert "p99_similarity" in sd
    assert "max_similarity" in sd
    assert sd['min_similarity'] <= sd['p50_median_similarity'] <= sd['p99_similarity'] <= sd['max_similarity']


def test_analog_output_structure():
    """
    Verify structure and types of returned analogs and aggregate stats.
    """
    engine = get_analog_engine()
    res = engine.find_analogs(max_k=20, min_similarity=0.80, current_p10_p90_band=(-0.05, 0.05))

    assert "query_timestamp" in res
    assert "query_price" in res
    assert "analogs" in res
    assert "aggregate_stats" in res
    assert "disclaimer" in res

    stats = res['aggregate_stats']
    assert stats['k_analogs_used'] == len(res['analogs'])
    assert "mean_realized_mfe_pct" in stats
    assert "median_realized_mfe_pct" in stats
    assert "mean_realized_mae_pct" in stats
    assert "median_realized_mae_pct" in stats
    assert "containment_rate_pct" in stats
    assert 0.0 <= stats['containment_rate_pct'] <= 100.0

    if res['analogs']:
        first = res['analogs'][0]
        assert first['rank'] == 1
        assert 0.0 <= first['similarity_score'] <= 1.0
        assert "realized_mfe_24h_pct" in first
        assert "realized_mae_24h_pct" in first
        assert "contained_in_band" in first
        assert isinstance(first['contained_in_band'], bool)

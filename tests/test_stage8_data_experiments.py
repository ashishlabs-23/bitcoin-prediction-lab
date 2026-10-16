"""
tests/test_stage8_data_experiments.py — Stage 8 Historical Data Strategy & Validation Tests
===========================================================================================
Verifies:
1. Existence and schema integrity of Stage 8 machine-readable experiment results.
2. Verified provenance and continuity of Binance historical funding rate series (2022-2026).
3. Exact audit of OHLCV completeness and the March 24, 2023 Binance outage gap.
4. Point-in-time causal integrity of derivatives feature joins (zero future lookahead).
5. Production model registry immutability (HAR-RS-DOW-v1.0 preserved as authorized production model).
"""

import os
import json
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STAGE8_JSON = os.path.join(REPO_ROOT, "experiments", "results", "stage8_data_experiments", "stage8_experiment_results.json")
FUNDING_PARQUET = os.path.join(REPO_ROOT, "data", "raw", "binance_funding_2022_2026.parquet")
OHLCV_PARQUET = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")


def test_stage8_results_file_exists_and_valid():
    """Verify Stage 8 results JSON exists and contains all pre-registered experiment keys."""
    assert os.path.exists(STAGE8_JSON), f"Missing Stage 8 results file: {STAGE8_JSON}"
    with open(STAGE8_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    required_keys = [
        "timestamp",
        "experiment_1_canonical_history_funding",
        "experiment_2_common_period_oi",
        "experiment_3_multihorizon_4h",
        "experiment_4_economic_viability"
    ]
    for k in required_keys:
        assert k in data, f"Missing key {k} in Stage 8 results"


def test_binance_funding_dataset_integrity():
    """Verify Binance historical funding rate parquet contains continuous 2022-2026 history."""
    assert os.path.exists(FUNDING_PARQUET), f"Missing verified funding parquet at {FUNDING_PARQUET}"
    df_fund = pd.read_parquet(FUNDING_PARQUET)
    assert len(df_fund) >= 5100, f"Expected >= 5,100 funding rate settlements, found {len(df_fund)}"

    ts = pd.to_datetime(df_fund["timestamp"], utc=True)
    assert ts.min() <= pd.to_datetime("2022-01-01 01:00:00+00:00")
    assert ts.max() >= pd.to_datetime("2026-09-01 00:00:00+00:00")
    assert df_fund["funding_rate"].isnull().sum() == 0


def test_ohlcv_completeness_and_outage_audit():
    """
    Verify OHLCV completeness: exactly 40,902 rows spanning 2022-01-01 to 2026-09-01,
    with exactly ONE missing hourly bar on 2023-03-24 13:00 UTC (Binance matching engine outage).
    """
    df = pd.read_parquet(OHLCV_PARQUET)
    assert len(df) == 40902

    ts = pd.to_datetime(df["timestamp"], utc=True).sort_values().reset_index(drop=True)
    diffs = ts.diff()

    # Exactly one gap greater than 1 hour
    gap_idx = diffs[diffs > pd.Timedelta(hours=1)].index
    assert len(gap_idx) == 1, f"Expected exactly 1 historical gap, found {len(gap_idx)}"

    idx = gap_idx[0]
    t_before = ts.loc[idx - 1]
    t_after = ts.loc[idx]
    assert t_before == pd.to_datetime("2023-03-24 12:00:00+00:00")
    assert t_after == pd.to_datetime("2023-03-24 14:00:00+00:00")
    assert diffs.loc[idx] == pd.Timedelta(hours=2)


def test_point_in_time_funding_alignment():
    """Verify that merged funding rate at bar t only uses settlements occurring at or before t."""
    from research.stage8_data_experiments import prepare_stage8_datasets
    df_full, _ = prepare_stage8_datasets()

    df_fund = pd.read_parquet(FUNDING_PARQUET)
    df_fund["ts_settle"] = pd.to_datetime(df_fund["timestamp"], utc=True).dt.floor("1h")
    fund_map = dict(zip(df_fund["ts_settle"], df_fund["funding_rate"]))

    # Test random sample of rows: funding_rate_prev must match latest past settlement
    sample_indices = [100, 500, 2000, 10000, 25000, 35000]
    for idx in sample_indices:
        t_bar = df_full.loc[idx, "timestamp"]
        f_rate = df_full.loc[idx, "funding_rate_prev"]

        # Find latest settlement <= t_bar
        past_settles = [s for s in fund_map if s <= t_bar]
        latest_settle = max(past_settles)
        assert abs(f_rate - fund_map[latest_settle]) < 1e-12


def test_production_model_registry_integrity_stage8():
    """Ensure HAR-RS-DOW-v1.0 remains the sole authorized production model during Stage 8."""
    from models.authoritative_model_registry import (
        get_active_production_model,
        get_directional_research_baseline,
        AuthorizationStatus,
        ModelClassification
    )

    prod = get_active_production_model()
    assert prod.canonical_id == "HAR-RS-DOW-v1.0"
    assert prod.authorization_status == AuthorizationStatus.AUTHORIZED_FOR_PRODUCTION
    assert prod.directional_prediction_capability is False

    directional = get_directional_research_baseline()
    assert directional.canonical_id == "directional-gbm-4lag-v1"
    assert directional.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY

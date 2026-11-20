import numpy as np
import pandas as pd
import pytest

from research.entry_tp_sl import run_full_research_pipeline as pipeline
from research.entry_tp_sl.pit_features import (
    PITTimingContract,
    PITTimingProvenanceError,
    compute_pit_features_table,
    validate_pit_timing_data,
)


def _verified_test_contract():
    return PITTimingContract(
        source_id="synthetic-unit-test-fixture-only",
        timestamp_column="Timestamp",
        timestamp_role="bar_close",
        timestamp_unit="unix_seconds",
        timezone="UTC",
        availability_column="available_timestamp",
        availability_rule="available_timestamp <= Timestamp",
        verified=True,
    )


def _fixture_frame(rows=130):
    timestamps = 1_700_000_000 + np.arange(rows) * 900
    close = 100.0 + np.arange(rows, dtype=float) * 0.1
    return pd.DataFrame(
        {
            "Timestamp": timestamps,
            "available_timestamp": timestamps,
            "Open": close - 0.02,
            "High": close + 0.1,
            "Low": close - 0.1,
            "Close": close,
            "Volume": 10.0 + np.arange(rows, dtype=float),
        }
    )


def test_pipeline_refuses_before_reading_csv_without_repository_authorization(monkeypatch):
    read_calls = []

    def record_read(*args, **kwargs):
        read_calls.append((args, kwargs))
        raise AssertionError("CSV must not be read without repository authorization.")

    monkeypatch.setattr(pipeline.pd, "read_csv", record_read)

    with pytest.raises(PITTimingProvenanceError, match="no repository-controlled"):
        pipeline.run()

    assert read_calls == []


def test_caller_supplied_verified_contract_cannot_authorize_csv_read(monkeypatch):
    read_calls = []

    def record_read(*args, **kwargs):
        read_calls.append((args, kwargs))
        raise AssertionError("Caller-supplied contracts cannot authorize CSV access.")

    monkeypatch.setattr(pipeline.pd, "read_csv", record_read)

    with pytest.raises(TypeError, match="unexpected keyword argument 'timing_contract'"):
        pipeline.run(timing_contract=_verified_test_contract())

    assert read_calls == []


def test_features_require_verified_timing_contract():
    frame = _fixture_frame()

    with pytest.raises(PITTimingProvenanceError, match="timing provenance is unresolved"):
        compute_pit_features_table(frame)

    features = compute_pit_features_table(frame, timing_contract=_verified_test_contract())
    assert features.loc[100, "vol_atr14_pct"] > 0


def test_future_availability_is_rejected_before_feature_computation():
    frame = _fixture_frame()
    frame.loc[75, "available_timestamp"] = frame.loc[75, "Timestamp"] + 1

    with pytest.raises(PITTimingProvenanceError, match="availability violation"):
        compute_pit_features_table(frame, timing_contract=_verified_test_contract())


def test_future_rows_cannot_change_prior_features_under_verified_contract():
    contract = _verified_test_contract()
    original = _fixture_frame()
    changed_future = original.copy()
    changed_future.loc[115:, ["Open", "High", "Low", "Close", "Volume"]] *= 3.0

    original_features = compute_pit_features_table(original, timing_contract=contract)
    changed_features = compute_pit_features_table(changed_future, timing_contract=contract)
    feature_columns = [
        "vol_atr14_pct",
        "vol_realized_24h",
        "vol_parkinson_24h",
        "mom_roc_4",
        "mom_roc_16",
        "mom_rsi_14",
        "vol_volume_ratio_20",
        "trend_sma50_diff",
        "time_hour_sin",
        "time_hour_cos",
    ]

    np.testing.assert_allclose(
        original_features.loc[100, feature_columns].to_numpy(dtype=float),
        changed_features.loc[100, feature_columns].to_numpy(dtype=float),
        equal_nan=True,
    )


def test_declared_availability_column_must_exist():
    frame = _fixture_frame().drop(columns="available_timestamp")

    with pytest.raises(PITTimingProvenanceError, match="timing columns are absent"):
        validate_pit_timing_data(frame, _verified_test_contract())

"""
tests/test_data_validation_2026_11_28.py — Red-team tests for the 2026-11-28
P1 data-engineering batch (Agent 03/04).

Covers:
* data/validate.py hard invariants (duplicate timestamps, high<low, negative
  volume, NaN prices) and the soft gap report (must NOT raise).
* data/ingest.save_raw: atomic write + merge semantics (existing rows survive a
  subset re-ingestion; last observation wins on duplicate timestamps) and
  fail-closed validation.
* data/ingest._call_with_retries: bounded retries, success on a later attempt,
  RuntimeError (not a silent partial result) on exhaustion.
* features/build_features.compute_technical_features: rejects an invalid raw
  frame before any feature arithmetic.
"""

import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from data import ingest  # noqa: E402
from data.validate import (  # noqa: E402
    DataValidationError,
    ValidationReport,
    validate_ohlcv,
)


def make_ohlcv(n=24, start="2024-01-01T00:00:00Z", freq="1h", seed=7) -> pd.DataFrame:
    """Deterministic, structurally valid OHLCV frame (no synthetic claim implied)."""
    rng = np.random.default_rng(seed)
    ts = pd.date_range(start=start, periods=n, freq=freq, tz="UTC")
    close = 30_000.0 * np.exp(np.cumsum(rng.normal(0.0, 0.002, size=n)))
    open_ = np.concatenate([[close[0]], close[:-1]])
    high = np.maximum(open_, close) * 1.001
    low = np.minimum(open_, close) * 0.999
    return pd.DataFrame(
        {
            "timestamp": ts,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.uniform(10.0, 100.0, size=n),
            "available_time": ts + pd.Timedelta(hours=1),
        }
    )


# ---------------------------------------------------------------------------
# validate_ohlcv — hard invariants
# ---------------------------------------------------------------------------

def test_valid_frame_passes_and_report_is_json_serialisable():
    report = validate_ohlcv(make_ohlcv(48), name="unit_ohlcv")
    assert isinstance(report, ValidationReport)
    assert report.ok is True
    assert report.errors == []
    assert report.rows == 48
    assert report.duplicate_timestamps == 0
    assert report.largest_gap_bars == 0
    assert report.gaps_over_2_bars == 0
    payload = json.dumps(report.to_dict())
    assert "unit_ohlcv" in payload


def test_duplicate_timestamps_raise_and_report_counts_them():
    df = make_ohlcv(10)
    df = pd.concat([df, df.iloc[[4]]], ignore_index=True)
    with pytest.raises(DataValidationError) as excinfo:
        validate_ohlcv(df, name="dup")
    report = excinfo.value.report
    assert isinstance(excinfo.value, ValueError)
    assert report.duplicate_timestamps == 1
    assert any("duplicate timestamp" in e for e in report.errors)
    assert excinfo.value.report.to_dict()["duplicate_timestamps"] == 1


def test_high_below_low_raises():
    df = make_ohlcv(5)
    df.loc[2, "high"] = df.loc[2, "low"] - 1.0
    with pytest.raises(DataValidationError) as excinfo:
        validate_ohlcv(df)
    assert any("high < low" in e for e in excinfo.value.report.errors)


def test_high_below_body_raises():
    df = make_ohlcv(5)
    df.loc[1, "high"] = max(df.loc[1, "open"], df.loc[1, "close"]) - 0.5
    with pytest.raises(DataValidationError) as excinfo:
        validate_ohlcv(df)
    assert any("high < max(open, close)" in e for e in excinfo.value.report.errors)


def test_negative_volume_raises():
    df = make_ohlcv(5)
    df.loc[3, "volume"] = -1.0
    with pytest.raises(DataValidationError) as excinfo:
        validate_ohlcv(df)
    assert any("negative volume" in e for e in excinfo.value.report.errors)


def test_nan_close_raises():
    df = make_ohlcv(5)
    df.loc[2, "close"] = np.nan
    with pytest.raises(DataValidationError) as excinfo:
        validate_ohlcv(df)
    assert any("NaN" in e and "close" in e for e in excinfo.value.report.errors)


def test_missing_required_column_raises():
    df = make_ohlcv(5).drop(columns=["volume"])
    with pytest.raises(DataValidationError) as excinfo:
        validate_ohlcv(df)
    assert any("missing required columns" in e for e in excinfo.value.report.errors)


# ---------------------------------------------------------------------------
# validate_ohlcv — gap detection is REPORT ONLY
# ---------------------------------------------------------------------------

def test_gap_over_two_bars_is_reported_but_does_not_raise():
    df = make_ohlcv(10)
    # Remove rows 4,5,6 -> 3 missing bars between 03:00 and 07:00.
    gapped = pd.concat([df.iloc[:4], df.iloc[7:]], ignore_index=True)
    report = validate_ohlcv(gapped, name="gapped")
    assert report.ok is True
    assert report.errors == []
    assert report.largest_gap_bars == 3
    assert report.gaps_over_2_bars == 1
    assert report.largest_gap_start == pd.Timestamp("2024-01-01T03:00:00Z").isoformat()
    assert report.largest_gap_end == pd.Timestamp("2024-01-01T07:00:00Z").isoformat()
    assert any("gap" in w for w in report.warnings)


def test_two_bar_gap_is_not_counted_as_alert():
    df = make_ohlcv(10)
    gapped = pd.concat([df.iloc[:4], df.iloc[6:]], ignore_index=True)  # 2 missing bars
    report = validate_ohlcv(gapped)
    assert report.largest_gap_bars == 2
    assert report.gaps_over_2_bars == 0


# ---------------------------------------------------------------------------
# save_raw — validate, merge, atomic replace
# ---------------------------------------------------------------------------

def test_save_raw_merge_preserves_existing_rows_when_new_frame_is_subset(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "DATA_RAW_DIR", str(tmp_path))
    full = make_ohlcv(12)
    path = ingest.save_raw(full, "ohlcv")
    assert os.path.exists(path)

    # A partially-failed pagination run delivers only the first 3 rows.
    ingest.save_raw(full.iloc[:3].copy(), "ohlcv")

    merged = pd.read_parquet(path, engine="pyarrow")
    assert len(merged) == 12, "existing history must not be truncated by a subset write"
    assert merged["timestamp"].is_monotonic_increasing
    assert merged["timestamp"].duplicated().sum() == 0


def test_save_raw_deduplicates_keeping_last_observation(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "DATA_RAW_DIR", str(tmp_path))
    df = make_ohlcv(6)
    path = ingest.save_raw(df, "ohlcv")

    revision = df.iloc[[2]].copy()
    revision.loc[:, "close"] = revision["close"] * 2.0
    revision.loc[:, "high"] = revision["high"] * 2.0
    ingest.save_raw(revision, "ohlcv")

    merged = pd.read_parquet(path, engine="pyarrow")
    assert len(merged) == 6
    ts = df.loc[2, "timestamp"]
    row = merged.loc[merged["timestamp"] == ts]
    assert len(row) == 1
    assert row["close"].iloc[0] == pytest.approx(revision["close"].iloc[0])


def test_save_raw_rejects_invalid_frame_without_writing(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "DATA_RAW_DIR", str(tmp_path))
    df = make_ohlcv(6)
    ingest.save_raw(df, "ohlcv")
    before = (tmp_path / "ohlcv.parquet").read_bytes()

    bad = make_ohlcv(6)
    bad.loc[1, "high"] = bad.loc[1, "low"] - 5.0
    with pytest.raises(DataValidationError):
        ingest.save_raw(bad, "ohlcv")

    assert (tmp_path / "ohlcv.parquet").read_bytes() == before
    leftovers = [p for p in os.listdir(tmp_path) if p.endswith(".tmp")]
    assert leftovers == [], "temporary files must be cleaned up on failure"


# ---------------------------------------------------------------------------
# _call_with_retries — bounded, exponential backoff, loud failure
# ---------------------------------------------------------------------------

def test_retries_recover_on_a_later_attempt(monkeypatch):
    sleeps = []
    monkeypatch.setattr(ingest.time, "sleep", lambda s: sleeps.append(s))
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("rate limited")
        return "ok"

    assert ingest._call_with_retries(flaky, description="flaky", base_delay=0.5) == "ok"
    assert calls["n"] == 3
    assert sleeps == [0.5, 1.0]


def test_retries_are_bounded_and_raise_instead_of_returning_partial(monkeypatch):
    monkeypatch.setattr(ingest.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def always_fails():
        calls["n"] += 1
        raise TimeoutError("down")

    with pytest.raises(RuntimeError) as excinfo:
        ingest._call_with_retries(always_fails, description="down feed", max_attempts=4)
    assert calls["n"] == 4
    assert "4 attempts" in str(excinfo.value)


# ---------------------------------------------------------------------------
# build_features — fail closed on invalid raw data
# ---------------------------------------------------------------------------

def test_build_features_rejects_invalid_frame():
    from features.build_features import compute_technical_features

    bad = make_ohlcv(60)
    bad.loc[10, "high"] = bad.loc[10, "low"] - 1.0
    with pytest.raises(DataValidationError):
        compute_technical_features(bad)


def test_build_features_accepts_valid_frame_and_flags_atr_as_observed():
    from features.build_features import compute_technical_features

    feats = compute_technical_features(make_ohlcv(60))
    assert "atr_14_imputed" in feats.columns
    assert feats["atr_14_imputed"].eq(0).all()


def test_build_features_marks_atr_imputed_when_high_low_absent():
    from features.build_features import compute_technical_features

    df = make_ohlcv(60).drop(columns=["high", "low"])
    # validate_ohlcv requires OHLC -> validation rejects before the fallback,
    # which is the intended fail-closed behaviour.
    with pytest.raises(DataValidationError):
        compute_technical_features(df)


def test_derivatives_flags_mark_missing_sources():
    from features.build_features import compute_derivatives_features

    funding = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=6, freq="8h", tz="UTC"),
            "funding_rate": [0.0001] * 6,
            "available_time": pd.date_range("2024-01-01", periods=6, freq="8h", tz="UTC"),
        }
    )
    deriv = compute_derivatives_features(funding, pd.DataFrame())
    assert deriv["funding_rate_imputed"].eq(0).all()
    assert deriv["open_interest_imputed"].eq(1).all()

    deriv2 = compute_derivatives_features(pd.DataFrame(), pd.DataFrame())
    assert deriv2.empty
    assert "funding_rate_imputed" in deriv2.columns

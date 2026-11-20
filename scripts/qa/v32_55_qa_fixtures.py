"""Deterministic QA-only fixtures. Writes only below the supplied disposable root."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

FIXTURE_ID = "deterministic_hourly_v1"
SCHEMA = ("timestamp", "open", "high", "low", "close", "volume", "available_time")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normal_frame() -> pd.DataFrame:
    timestamps = pd.date_range("2024-01-01T00:00:00Z", periods=240, freq="h")
    opens = [42000.0 + index * 2.0 for index in range(len(timestamps))]
    closes = [value + (1.0 if index % 2 else -1.0) for index, value in enumerate(opens)]
    return pd.DataFrame({"timestamp": timestamps, "open": opens,
        "high": [max(left, right) + 3.0 for left, right in zip(opens, closes)],
        "low": [min(left, right) - 3.0 for left, right in zip(opens, closes)],
        "close": closes, "volume": [100.0 + index for index in range(len(timestamps))],
        "available_time": timestamps + pd.Timedelta(hours=1)})


def _write_parquet(frame: pd.DataFrame, target: Path) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(target, index=False)
    return {"path": str(target), "sha256": _sha256(target), "rows": len(frame)}


def build_fixture_bundle(disposable_root: Path) -> dict[str, Any]:
    """Create QA data/response cases inside the sandbox, never the repository."""
    root = disposable_root.resolve()
    qa_root = root / "data" / "qa_fixtures" / FIXTURE_ID
    normal = _normal_frame()
    fixtures = {
        "normal_hourly": _write_parquet(normal, qa_root / "normal_hourly.parquet"),
        "missing_interval": _write_parquet(normal.drop(index=[80, 81]).reset_index(drop=True), qa_root / "missing_interval.parquet"),
        "duplicate_timestamp": _write_parquet(pd.concat([normal, normal.iloc[[100]]], ignore_index=True), qa_root / "duplicate_timestamp.parquet"),
    }
    invalid = normal.copy()
    invalid.loc[20, "high"] = invalid.loc[20, "close"] - 1.0
    invalid.loc[21, "low"] = invalid.loc[21, "open"] + 1.0
    invalid.loc[22, "volume"] = -1.0
    fixtures["invalid_ohlcv"] = _write_parquet(invalid, qa_root / "invalid_ohlcv.parquet")
    stale = normal.copy()
    stale["timestamp"] = stale["timestamp"] - pd.Timedelta(days=3650)
    stale["available_time"] = stale["timestamp"] + pd.Timedelta(hours=1)
    fixtures["stale_hourly"] = _write_parquet(stale, qa_root / "stale_hourly.parquet")
    responses = {"unavailable_forecast": {"status": "unavailable", "forecast": None, "reason": "QA_ONLY"},
        "malformed_forecast": {"forecast": {"horizon_hours": "not-a-number", "variance": None}},
        "api_timeout": {"status": 504, "error": "QA_TIMEOUT", "retryable": True},
        "unavailable_response": {"status": 503, "error": "QA_UNAVAILABLE", "retryable": True}}
    response_path = qa_root / "response_cases.json"
    response_path.write_text(json.dumps(responses, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    fixtures["response_cases"] = {"path": str(response_path), "sha256": _sha256(response_path)}
    manifest = {"fixture_id": FIXTURE_ID, "qa_only": True, "not_market_evidence": True,
        "not_forecast_source": True, "schema": list(SCHEMA),
        "timestamp_semantics": "UTC hourly candle-open; available_time is candle-open plus one hour",
        "deterministic_seed": "literal_v1_no_rng", "fixtures": fixtures}
    manifest_path = qa_root / "qa_fixture_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def assert_fixture_bundle(bundle: dict[str, Any], disposable_root: Path) -> None:
    root = disposable_root.resolve()
    if not all(bundle[key] for key in ("qa_only", "not_market_evidence", "not_forecast_source")):
        raise RuntimeError("QA fixture provenance flags are incomplete")
    for fixture in bundle["fixtures"].values():
        path = Path(fixture["path"]).resolve()
        if path != root and root not in path.parents:
            raise RuntimeError(f"Fixture escaped disposable directory: {path}")
    normal = pd.read_parquet(bundle["fixtures"]["normal_hourly"]["path"])
    if tuple(normal.columns) != SCHEMA or len(normal) != 240 or normal["timestamp"].duplicated().any():
        raise RuntimeError("Normal fixture violates the candle schema contract")
    if not (normal["available_time"] == normal["timestamp"] + pd.Timedelta(hours=1)).all():
        raise RuntimeError("Normal fixture availability semantics are invalid")
    gap = pd.read_parquet(bundle["fixtures"]["missing_interval"]["path"])
    duplicate = pd.read_parquet(bundle["fixtures"]["duplicate_timestamp"]["path"])
    invalid = pd.read_parquet(bundle["fixtures"]["invalid_ohlcv"]["path"])
    if not (gap["timestamp"].diff() > pd.Timedelta(hours=1)).any() or not duplicate["timestamp"].duplicated().any():
        raise RuntimeError("Declared gap/duplicate defects absent")
    if not ((invalid["high"] < invalid[["open", "close"]].max(axis=1)).any() or (invalid["volume"] < 0).any()):
        raise RuntimeError("Declared OHLCV defect absent")

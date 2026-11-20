"""Acquire and validate a versioned BTC-USD hourly dataset from Coinbase."""

from __future__ import annotations

import argparse
import gzip
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = (
    REPOSITORY_ROOT
    / "data"
    / "research"
    / "coinbase_btc_usd_hourly_verified_v2"
)
COINBASE_CANDLES_URL = (
    "https://api.exchange.coinbase.com/products/BTC-USD/candles"
)
GRANULARITY_SECONDS = 3600
MAX_CANDLES_PER_REQUEST = 250
REQUEST_PACING_SECONDS = 0.35
MAX_RETRIES = 5
OHLCV_FIELDS = ("open", "high", "low", "close", "volume")
OUTPUT_COLUMNS = ("timestamp", *OHLCV_FIELDS, "available_time")


def _utc_iso(epoch_seconds: int) -> str:
    return (
        datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write(path: Path, content: bytes) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as target:
        target.write(content)
        target.flush()
        os.fsync(target.fileno())
    os.replace(temporary, path)


def _fetch_response(start_epoch: int, end_epoch: int) -> tuple[bytes, str, int]:
    query = urlencode(
        {
            "granularity": GRANULARITY_SECONDS,
            "start": _utc_iso(start_epoch),
            "end": _utc_iso(end_epoch),
        }
    )
    request_url = f"{COINBASE_CANDLES_URL}?{query}"
    request = Request(
        request_url,
        headers={
            "User-Agent": "BTCognitive-Verified-Dataset-V2/1.0",
            "Accept": "application/json",
        },
    )
    for attempt in range(MAX_RETRIES):
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read()
                if response.status != 200:
                    raise RuntimeError(
                        f"Coinbase returned HTTP {response.status}: {request_url}"
                    )
                return body, request_url, response.status
        except HTTPError as error:
            retryable = error.code == 429 or 500 <= error.code < 600
            if not retryable or attempt == MAX_RETRIES - 1:
                raise
        except (URLError, TimeoutError, OSError):
            if attempt == MAX_RETRIES - 1:
                raise
        time.sleep(min(2**attempt, 16))
    raise RuntimeError("Coinbase request exhausted retries without a response")


def _parse_candles(
    payload: bytes, start_epoch: int, end_epoch: int
) -> list[dict[str, Any]]:
    try:
        data = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Coinbase response is not valid JSON") from error
    if not isinstance(data, list):
        raise ValueError("Coinbase response must be a JSON array")
    if len(data) > 300:
        raise ValueError(f"Coinbase returned {len(data)} candles; maximum is 300")

    candles = []
    for index, row in enumerate(data):
        if not isinstance(row, list) or len(row) != 6:
            raise ValueError(f"Malformed Coinbase candle at response index {index}")
        epoch, low, high, open_price, close, volume = row
        if isinstance(epoch, bool) or not isinstance(epoch, (int, float)):
            raise ValueError(f"Invalid candle timestamp at response index {index}")
        epoch = int(epoch)
        if epoch % GRANULARITY_SECONDS or not start_epoch <= epoch <= end_epoch:
            raise ValueError(
                f"Candle timestamp {_utc_iso(epoch)} is outside the requested "
                "hourly interval"
            )
        try:
            values = {
                "open": float(open_price),
                "high": float(high),
                "low": float(low),
                "close": float(close),
                "volume": float(volume),
            }
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Invalid OHLCV value at response index {index}"
            ) from error
        candles.append(
            {
                "epoch": epoch,
                "timestamp": pd.Timestamp(epoch, unit="s", tz="UTC"),
                **values,
                "available_time": pd.Timestamp(
                    epoch + GRANULARITY_SECONDS, unit="s", tz="UTC"
                ),
            }
        )
    return candles


def _validate_candle_values(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "finite_ohlcv": True,
            "valid_ohlc_bounds": True,
            "nonnegative_volume": True,
        }
    numeric = frame[list(OHLCV_FIELDS)].to_numpy(dtype=float)
    finite = bool(numeric.size == 0 or all(math.isfinite(x) for x in numeric.flat))
    valid_bounds = bool(
        (
            (frame["high"] >= frame[["open", "close", "low"]].max(axis=1))
            & (frame["low"] <= frame[["open", "close", "high"]].min(axis=1))
        ).all()
    )
    nonnegative_volume = bool((frame["volume"] >= 0).all())
    return {
        "finite_ohlcv": finite,
        "valid_ohlc_bounds": valid_bounds,
        "nonnegative_volume": nonnegative_volume,
    }


def _inspect_dataset(frame: pd.DataFrame) -> dict[str, Any]:
    timestamps = pd.to_datetime(frame["timestamp"], utc=True)
    if timestamps.empty:
        raise ValueError("Acquired dataset is empty")
    diffs = timestamps.diff().dropna()
    gap_rows = []
    for index, difference in enumerate(diffs, start=1):
        if difference != pd.Timedelta(seconds=GRANULARITY_SECONDS):
            previous = timestamps.iloc[index - 1]
            current = timestamps.iloc[index]
            gap_rows.append(
                {
                    "after_utc": previous.isoformat(),
                    "resumes_utc": current.isoformat(),
                    "missing_intervals": int(
                        difference.total_seconds() / GRANULARITY_SECONDS
                    )
                    - 1,
                }
            )
    values = _validate_candle_values(frame)
    return {
        "rows": int(len(frame)),
        "expected_hourly_timestamps": int(
            (timestamps.iloc[-1].timestamp() - timestamps.iloc[0].timestamp())
            / GRANULARITY_SECONDS
        )
        + 1,
        "first_timestamp_utc": timestamps.iloc[0].isoformat(),
        "last_timestamp_utc": timestamps.iloc[-1].isoformat(),
        "timestamps_monotonic_increasing": bool(timestamps.is_monotonic_increasing),
        "duplicate_timestamps": int(timestamps.duplicated().sum()),
        "missing_interval_count": len(gap_rows),
        "gaps": gap_rows,
        "timestamp_timezone": str(timestamps.dt.tz),
        **values,
    }


def _compare_to_existing(
    acquired: pd.DataFrame, existing_path: Path
) -> dict[str, Any]:
    existing = pd.read_parquet(existing_path)
    required = {"timestamp", *OHLCV_FIELDS}
    if not required.issubset(existing.columns):
        raise ValueError(
            f"Comparison dataset is missing columns: {sorted(required - set(existing))}"
        )
    existing["timestamp"] = pd.to_datetime(existing["timestamp"], utc=True)
    left = existing[["timestamp", *OHLCV_FIELDS]].copy()
    right = acquired[["timestamp", *OHLCV_FIELDS]].copy()
    if left["timestamp"].duplicated().any() or right["timestamp"].duplicated().any():
        raise ValueError("Cannot compare datasets with duplicate timestamps")
    left = left.set_index("timestamp")
    right = right.set_index("timestamp")
    shared = left.index.intersection(right.index)
    missing_from_new = left.index.difference(right.index)
    new_only = right.index.difference(left.index)
    old_values = left.loc[shared, list(OHLCV_FIELDS)].to_numpy(dtype=float)
    new_values = right.loc[shared, list(OHLCV_FIELDS)].to_numpy(dtype=float)
    mismatch_rows, mismatch_columns = (old_values != new_values).nonzero()
    mismatch_counts_by_field = {
        field: int((mismatch_columns == index).sum())
        for index, field in enumerate(OHLCV_FIELDS)
    }
    mismatches = [
        {
            "timestamp_utc": shared[row].isoformat(),
            "field": OHLCV_FIELDS[column],
            "existing": float(old_values[row, column]),
            "acquired": float(new_values[row, column]),
        }
        for row, column in zip(mismatch_rows, mismatch_columns)
    ]
    return {
        "existing_path": str(existing_path),
        "existing_rows": int(len(left)),
        "acquired_rows": int(len(right)),
        "shared_timestamps": int(len(shared)),
        "missing_from_acquired": [
            timestamp.isoformat() for timestamp in missing_from_new
        ],
        "only_in_acquired": [timestamp.isoformat() for timestamp in new_only],
        "shared_value_mismatch_count": len(mismatches),
        "shared_value_mismatch_count_by_field": mismatch_counts_by_field,
        "shared_value_mismatch_sample": mismatches[:100],
        "_detailed_mismatches": mismatches,
    }


def compare_coinbase_captures(
    earlier_path: Path, later_path: Path
) -> dict[str, Any]:
    earlier = pd.read_parquet(earlier_path)
    later = pd.read_parquet(later_path)
    timestamp_column = "timestamp_utc" if "timestamp_utc" in earlier else "timestamp"
    fields = {"timestamp_utc", "timestamp", *OHLCV_FIELDS}
    if not set(OHLCV_FIELDS).issubset(earlier) or not set(OHLCV_FIELDS).issubset(later):
        raise ValueError("A Coinbase capture is missing required OHLCV columns")
    earlier["timestamp"] = pd.to_datetime(
        earlier[timestamp_column], utc=True
    )
    later_timestamp_column = (
        "timestamp_utc" if "timestamp_utc" in later else "timestamp"
    )
    later["timestamp"] = pd.to_datetime(later[later_timestamp_column], utc=True)
    left = earlier[["timestamp", *OHLCV_FIELDS]].set_index("timestamp")
    right = later[["timestamp", *OHLCV_FIELDS]].set_index("timestamp")
    if left.index.has_duplicates or right.index.has_duplicates:
        raise ValueError("A Coinbase capture contains duplicate timestamps")
    shared = left.index.intersection(right.index)
    old_values = left.loc[shared, list(OHLCV_FIELDS)].to_numpy(dtype=float)
    new_values = right.loc[shared, list(OHLCV_FIELDS)].to_numpy(dtype=float)
    mismatch_rows, mismatch_columns = (old_values != new_values).nonzero()
    mismatch_counts = {
        field: int((mismatch_columns == index).sum())
        for index, field in enumerate(OHLCV_FIELDS)
    }
    samples = [
        {
            "timestamp_utc": shared[row].isoformat(),
            "field": OHLCV_FIELDS[column],
            "earlier": float(old_values[row, column]),
            "later": float(new_values[row, column]),
        }
        for row, column in zip(mismatch_rows[:100], mismatch_columns[:100])
    ]
    return {
        "earlier_dataset": str(earlier_path),
        "earlier_sha256": _sha256(earlier_path.read_bytes()),
        "earlier_rows": int(len(left)),
        "later_dataset": str(later_path),
        "later_sha256": _sha256(later_path.read_bytes()),
        "later_rows": int(len(right)),
        "shared_timestamps": int(len(shared)),
        "earlier_only_timestamps": int(len(left.index.difference(right.index))),
        "later_only_timestamps": int(len(right.index.difference(left.index))),
        "exact_numeric_mismatches_by_field": mismatch_counts,
        "exact_numeric_mismatch_count": int(len(mismatch_rows)),
        "mismatch_sample": samples,
    }


def verify_dataset(output_dir: Path) -> dict[str, Any]:
    """Rebuild the tabular data from archived response bodies and verify all hashes."""
    manifest_path = output_dir / "acquisition_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    candles_by_epoch: dict[int, dict[str, Any]] = {}
    raw_hashes_valid = True
    page_checks = []
    for page in manifest["pages"]:
        raw_path = output_dir / page["raw_response_file"]
        body = raw_path.read_bytes()
        observed_hash = _sha256(body)
        hash_matches = observed_hash == page["raw_response_sha256"]
        raw_hashes_valid = raw_hashes_valid and hash_matches
        start_epoch = _epoch_from_iso(page["request_start_utc"])
        end_epoch = _epoch_from_iso(page["request_end_utc"])
        candles = _parse_candles(body, start_epoch, end_epoch)
        if len(candles) != page["response_candle_count"]:
            raise ValueError(f"Archived candle count changed for page {page['page_index']}")
        for candle in candles:
            previous = candles_by_epoch.get(candle["epoch"])
            if previous is not None and any(
                previous[field] != candle[field] for field in OHLCV_FIELDS
            ):
                raise ValueError(
                    f"Archived pages conflict at {_utc_iso(candle['epoch'])}"
                )
            candles_by_epoch.setdefault(candle["epoch"], candle)
        page_checks.append(
            {
                "page_index": page["page_index"],
                "raw_sha256_matches": hash_matches,
                "response_candle_count_matches": (
                    len(candles) == page["response_candle_count"]
                ),
            }
        )

    rebuilt = pd.DataFrame(
        [candles_by_epoch[epoch] for epoch in sorted(candles_by_epoch)]
    )[list(OUTPUT_COLUMNS)]
    dataset_path = output_dir / manifest["dataset_file"]
    stored_bytes = dataset_path.read_bytes()
    stored = pd.read_parquet(dataset_path)
    if len(stored) != len(rebuilt):
        raise ValueError("Rebuilt dataset row count differs from stored dataset")
    for column in OUTPUT_COLUMNS:
        if column in {"timestamp", "available_time"}:
            equal = (
                pd.DatetimeIndex(
                    pd.to_datetime(stored[column], utc=True)
                ).as_unit("ns").asi8
                == pd.DatetimeIndex(
                    pd.to_datetime(rebuilt[column], utc=True)
                ).as_unit("ns").asi8
            ).all()
        else:
            equal = (
                stored[column].astype(float).to_numpy()
                == rebuilt[column].astype(float).to_numpy()
            ).all()
        if not equal:
            raise ValueError(f"Rebuilt dataset differs in column {column}")
    dataset_hash_matches = _sha256(stored_bytes) == manifest["dataset_sha256"]
    result = {
        "manifest_exists": True,
        "page_count": len(page_checks),
        "page_checks": page_checks,
        "all_raw_response_hashes_match": raw_hashes_valid,
        "dataset_sha256_matches_manifest": dataset_hash_matches,
        "rebuilt_rows": int(len(rebuilt)),
        "stored_rows": int(len(stored)),
        "rebuilt_values_match_stored_dataset": True,
    }
    if not raw_hashes_valid:
        raise ValueError("One or more archived response hashes do not match")
    if not dataset_hash_matches:
        raise ValueError("Stored dataset hash does not match the manifest")
    return result


def build_dataset(
    *,
    start_epoch: int,
    last_candle_epoch: int,
    output_dir: Path,
    comparison_path: Path,
    request_pacing_seconds: float = REQUEST_PACING_SECONDS,
    dataset_id: str = "coinbase_btc_usd_hourly_verified_v2",
) -> dict[str, Any]:
    if start_epoch % GRANULARITY_SECONDS or last_candle_epoch % GRANULARITY_SECONDS:
        raise ValueError("Start and end timestamps must be UTC hourly boundaries")
    if last_candle_epoch < start_epoch:
        raise ValueError("Dataset end must not precede its start")
    if output_dir.exists():
        raise FileExistsError(
            f"Refusing to overwrite an existing dataset version: {output_dir}"
        )

    output_dir.mkdir(parents=True)
    raw_dir = output_dir / "raw_responses"
    raw_dir.mkdir()
    candles_by_epoch: dict[int, dict[str, Any]] = {}
    pages: list[dict[str, Any]] = []
    page_start = start_epoch
    page_index = 0

    while page_start <= last_candle_epoch:
        page_end = min(
            page_start + (MAX_CANDLES_PER_REQUEST - 1) * GRANULARITY_SECONDS,
            last_candle_epoch,
        )
        page_index += 1
        body, request_url, status = _fetch_response(page_start, page_end)
        raw_name = f"page_{page_index:04d}.json"
        _atomic_write(raw_dir / raw_name, body)
        page_candles = _parse_candles(body, page_start, page_end)
        if len(page_candles) > MAX_CANDLES_PER_REQUEST:
            raise ValueError(
                f"Request page {page_index} exceeded the requested "
                f"{MAX_CANDLES_PER_REQUEST}-candle limit"
            )

        duplicates = 0
        for candle in page_candles:
            epoch = candle["epoch"]
            previous = candles_by_epoch.get(epoch)
            if previous is not None:
                if any(previous[field] != candle[field] for field in OHLCV_FIELDS):
                    raise ValueError(
                        f"Conflicting duplicate candle at {_utc_iso(epoch)}"
                    )
                duplicates += 1
            else:
                candles_by_epoch[epoch] = candle

        pages.append(
            {
                "page_index": page_index,
                "request_url": request_url,
                "request_start_utc": _utc_iso(page_start),
                "request_end_utc": _utc_iso(page_end),
                "http_status": status,
                "raw_response_file": f"raw_responses/{raw_name}",
                "raw_response_bytes": len(body),
                "raw_response_sha256": _sha256(body),
                "response_candle_count": len(page_candles),
                "identical_duplicate_rows": duplicates,
                "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
        page_start = page_end + GRANULARITY_SECONDS
        if page_start <= last_candle_epoch:
            time.sleep(request_pacing_seconds)

    records = [candles_by_epoch[epoch] for epoch in sorted(candles_by_epoch)]
    frame = pd.DataFrame(records)
    frame = frame[list(OUTPUT_COLUMNS)]
    validation = _inspect_dataset(frame)
    parquet_path = output_dir / "coinbase_btc_usd_hourly.parquet"
    temporary_parquet = output_dir / "coinbase_btc_usd_hourly.parquet.tmp"
    frame.to_parquet(temporary_parquet, index=False)
    os.replace(temporary_parquet, parquet_path)
    parquet_hash = _sha256(parquet_path.read_bytes())

    expected_count = (
        (last_candle_epoch - start_epoch) // GRANULARITY_SECONDS
    ) + 1
    expected_epochs = set(
        range(start_epoch, last_candle_epoch + 1, GRANULARITY_SECONDS)
    )
    actual_epochs = set(candles_by_epoch)
    validation["expected_hourly_timestamps"] = expected_count
    validation["missing_expected_timestamps"] = [
        _utc_iso(epoch) for epoch in sorted(expected_epochs - actual_epochs)
    ]
    validation["timestamps_outside_requested_range"] = [
        _utc_iso(epoch) for epoch in sorted(actual_epochs - expected_epochs)
    ]
    comparison_result = _compare_to_existing(frame, comparison_path)
    detailed_mismatches = comparison_result.pop("_detailed_mismatches")
    mismatch_file = "shared_value_mismatches.jsonl.gz"
    mismatch_content = b"".join(
        (
            json.dumps(mismatch, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        for mismatch in detailed_mismatches
    )
    mismatch_bytes = gzip.compress(mismatch_content, mtime=0)
    _atomic_write(output_dir / mismatch_file, mismatch_bytes)
    comparison = {
        **comparison_result,
        "shared_value_mismatches_file": mismatch_file,
        "shared_value_mismatches_sha256": _sha256(mismatch_bytes),
        "shared_value_mismatches_compressed_bytes": len(mismatch_bytes),
    }

    complete_coverage = (
        validation["rows"] == expected_count
        and validation["duplicate_timestamps"] == 0
        and validation["missing_interval_count"] == 0
        and comparison["shared_value_mismatch_count"] == 0
        and validation["finite_ohlcv"]
        and validation["valid_ohlc_bounds"]
        and validation["nonnegative_volume"]
    )
    manifest = {
        "dataset_id": dataset_id,
        "venue": "COINBASE",
        "market_type": "SPOT",
        "product_id": "BTC-USD",
        "timeframe": "1h",
        "granularity_seconds": GRANULARITY_SECONDS,
        "candle_timestamp_semantics": "UTC candle-open time, Unix epoch seconds in source",
        "available_time_semantics": "Derived as candle-open UTC plus one hour (bar close)",
        "acquisition_started_at_utc": pages[0]["captured_at_utc"],
        "acquisition_completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_start_utc": _utc_iso(start_epoch),
        "requested_last_candle_utc": _utc_iso(last_candle_epoch),
        "expected_hourly_timestamps": expected_count,
        "page_limit": MAX_CANDLES_PER_REQUEST,
        "request_pacing_seconds": request_pacing_seconds,
        "retry_policy": {
            "max_retries": MAX_RETRIES,
            "exponential_backoff_seconds": [1, 2, 4, 8, 16],
            "retryable_http_status": "429 and 5xx",
        },
        "pages": pages,
        "dataset_file": parquet_path.name,
        "dataset_sha256": parquet_hash,
        "validation": validation,
        "comparison": comparison,
        "status": "ACQUIRED_VALIDATION_PASSED"
        if complete_coverage
        else "ACQUIRED_WITH_REVIEW_REQUIRED",
        "no_gap_filling_or_value_substitution": True,
    }
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    _atomic_write(output_dir / "acquisition_manifest.json", manifest_bytes)
    _atomic_write(
        output_dir / "comparison.json",
        (json.dumps(comparison, indent=2) + "\n").encode("utf-8"),
    )
    _atomic_write(
        output_dir / "validation.json",
        (json.dumps(validation, indent=2) + "\n").encode("utf-8"),
    )
    _atomic_write(
        output_dir / "rebuild_verification.json",
        (json.dumps(verify_dataset(output_dir), indent=2) + "\n").encode("utf-8"),
    )
    return manifest


def _epoch_from_iso(value: str) -> int:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    return int(timestamp.timestamp())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--start",
        help="Inclusive UTC start timestamp (defaults to primary dataset minimum).",
    )
    parser.add_argument(
        "--last-candle",
        help=(
            "Inclusive UTC candle-open timestamp. Defaults to the latest fully "
            "closed hourly candle."
        ),
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--dataset-id",
        default="coinbase_btc_usd_hourly_verified_v2",
        help="Immutable dataset-version identity recorded in the acquisition manifest.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Rebuild and verify from archived responses without network access.",
    )
    parser.add_argument(
        "--refresh-audit",
        action="store_true",
        help="Regenerate comparison and validation reports from an existing dataset.",
    )
    parser.add_argument(
        "--compare-to",
        type=Path,
        default=REPOSITORY_ROOT / "data" / "raw" / "ohlcv.parquet",
    )
    parser.add_argument(
        "--pacing-seconds", type=float, default=REQUEST_PACING_SECONDS
    )
    args = parser.parse_args()

    if args.verify_only:
        print(json.dumps(verify_dataset(args.output_dir.resolve()), indent=2))
        return

    if args.refresh_audit:
        manifest_path = args.output_dir.resolve() / "acquisition_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        dataset_path = args.output_dir.resolve() / manifest["dataset_file"]
        frame = pd.read_parquet(dataset_path)
        validation = _inspect_dataset(frame)
        start_epoch = _epoch_from_iso(manifest["requested_start_utc"])
        last_epoch = _epoch_from_iso(manifest["requested_last_candle_utc"])
        expected = set(range(start_epoch, last_epoch + 1, GRANULARITY_SECONDS))
        observed = {
            int(pd.Timestamp(timestamp).timestamp())
            for timestamp in pd.to_datetime(frame["timestamp"], utc=True)
        }
        validation["expected_hourly_timestamps"] = len(expected)
        validation["missing_expected_timestamps"] = [
            _utc_iso(epoch) for epoch in sorted(expected - observed)
        ]
        validation["timestamps_outside_requested_range"] = [
            _utc_iso(epoch) for epoch in sorted(observed - expected)
        ]
        comparison_result = _compare_to_existing(frame, args.compare_to.resolve())
        detailed_mismatches = comparison_result.pop("_detailed_mismatches")
        mismatch_file = "shared_value_mismatches.jsonl.gz"
        mismatch_content = b"".join(
            (
                json.dumps(mismatch, sort_keys=True, separators=(",", ":")) + "\n"
            ).encode("utf-8")
            for mismatch in detailed_mismatches
        )
        mismatch_bytes = gzip.compress(mismatch_content, mtime=0)
        _atomic_write(
            args.output_dir.resolve() / mismatch_file,
            mismatch_bytes,
        )
        comparison = {
            **comparison_result,
            "shared_value_mismatches_file": mismatch_file,
            "shared_value_mismatches_sha256": _sha256(mismatch_bytes),
            "shared_value_mismatches_compressed_bytes": len(mismatch_bytes),
        }
        previous_capture = (
            REPOSITORY_ROOT
            / "data"
            / "research"
            / "coinbase_btc_usd_hourly_v1"
            / "coinbase_hourly.parquet"
        )
        if previous_capture.is_file():
            cross_capture = compare_coinbase_captures(
                previous_capture,
                args.output_dir.resolve() / manifest["dataset_file"],
            )
            manifest["cross_capture_comparison"] = cross_capture
            _atomic_write(
                args.output_dir.resolve() / "cross_capture_comparison.json",
                (json.dumps(cross_capture, indent=2) + "\n").encode("utf-8"),
            )
        manifest["validation"] = validation
        manifest["comparison"] = comparison
        manifest["status"] = (
            "ACQUIRED_WITH_REVIEW_REQUIRED"
            if (
                validation["rows"] != len(expected)
                or validation["missing_interval_count"] > 0
                or validation["duplicate_timestamps"] > 0
                or comparison["shared_value_mismatch_count"] > 0
                or not validation["finite_ohlcv"]
                or not validation["valid_ohlc_bounds"]
                or not validation["nonnegative_volume"]
            )
            else "ACQUIRED_VALIDATION_PASSED"
        )
        _atomic_write(
            manifest_path,
            (json.dumps(manifest, indent=2) + "\n").encode("utf-8"),
        )
        _atomic_write(
            args.output_dir.resolve() / "comparison.json",
            (json.dumps(comparison, indent=2) + "\n").encode("utf-8"),
        )
        _atomic_write(
            args.output_dir.resolve() / "validation.json",
            (json.dumps(validation, indent=2) + "\n").encode("utf-8"),
        )
        _atomic_write(
            args.output_dir.resolve() / "rebuild_verification.json",
            (json.dumps(verify_dataset(args.output_dir.resolve()), indent=2) + "\n").encode("utf-8"),
        )
        print(
            json.dumps(
                {
                    "status": manifest["status"],
                    "shared_value_mismatches": comparison[
                        "shared_value_mismatch_count"
                    ],
                    "mismatch_archive": mismatch_file,
                    "mismatch_archive_sha256": comparison[
                        "shared_value_mismatches_sha256"
                    ],
                },
                indent=2,
            )
        )
        return

    existing = pd.read_parquet(args.compare_to, columns=["timestamp"])
    existing_start = pd.to_datetime(existing["timestamp"], utc=True).min()
    start_epoch = (
        _epoch_from_iso(args.start)
        if args.start
        else int(existing_start.timestamp())
    )
    if args.last_candle:
        last_candle_epoch = _epoch_from_iso(args.last_candle)
    else:
        current_hour_epoch = (
            int(datetime.now(timezone.utc).timestamp()) // GRANULARITY_SECONDS
        ) * GRANULARITY_SECONDS
        last_candle_epoch = current_hour_epoch - GRANULARITY_SECONDS

    manifest = build_dataset(
        start_epoch=start_epoch,
        last_candle_epoch=last_candle_epoch,
        output_dir=args.output_dir.resolve(),
        comparison_path=args.compare_to.resolve(),
        request_pacing_seconds=args.pacing_seconds,
        dataset_id=args.dataset_id,
    )
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "dataset_file": str(args.output_dir / manifest["dataset_file"]),
                "dataset_sha256": manifest["dataset_sha256"],
                "candles": manifest["validation"]["rows"],
                "pages": len(manifest["pages"]),
                "missing_intervals": manifest["validation"][
                    "missing_interval_count"
                ],
                "shared_value_mismatches": manifest["comparison"][
                    "shared_value_mismatch_count"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from research.data_acquisition import build_coinbase_hourly_verified_v2 as builder


class CoinbaseHourlyVerifiedV2Tests(unittest.TestCase):
    def test_build_paginates_archives_and_reproduces_comparison(self):
        start = 1_700_000_000 // 3600 * 3600
        last = start + 250 * 3600
        timestamps = list(range(start, last + 1, 3600))
        existing = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(timestamps, unit="s", utc=True),
                "open": [100.0] * len(timestamps),
                "high": [102.0] * len(timestamps),
                "low": [99.0] * len(timestamps),
                "close": [101.0] * len(timestamps),
                "volume": [1.0] * len(timestamps),
            }
        )

        def fake_fetch(page_start, page_end):
            rows = [
                [epoch, 99.0, 102.0, 100.0, 101.0, 1.0]
                for epoch in range(page_start, page_end + 1, 3600)
            ]
            return (
                json.dumps(rows[::-1]).encode("utf-8"),
                f"https://example.test?start={page_start}&end={page_end}",
                200,
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            comparison_path = root / "existing.parquet"
            existing.to_parquet(comparison_path, index=False)
            output_dir = root / "verified_v2"
            with (
                patch.object(builder, "_fetch_response", side_effect=fake_fetch),
                patch.object(builder.time, "sleep"),
            ):
                manifest = builder.build_dataset(
                    start_epoch=start,
                    last_candle_epoch=last,
                    output_dir=output_dir,
                    comparison_path=comparison_path,
                    request_pacing_seconds=0,
                )

            self.assertEqual(len(manifest["pages"]), 2)
            self.assertTrue(
                all(
                    page["response_candle_count"] <= builder.MAX_CANDLES_PER_REQUEST
                    for page in manifest["pages"]
                )
            )
            self.assertEqual(manifest["validation"]["rows"], 251)
            self.assertEqual(manifest["validation"]["missing_interval_count"], 0)
            self.assertEqual(
                manifest["comparison"]["shared_value_mismatch_count"], 0
            )
            self.assertEqual(
                manifest["comparison"]["missing_from_acquired"], []
            )
            for page in manifest["pages"]:
                raw = output_dir / page["raw_response_file"]
                self.assertEqual(
                    hashlib.sha256(raw.read_bytes()).hexdigest(),
                    page["raw_response_sha256"],
                )
            replay = builder.verify_dataset(output_dir)
            self.assertTrue(replay["all_raw_response_hashes_match"])
            self.assertTrue(replay["dataset_sha256_matches_manifest"])
            self.assertTrue(replay["rebuilt_values_match_stored_dataset"])
            stored = pd.read_parquet(output_dir / manifest["dataset_file"])
            self.assertEqual(len(stored), 251)
            self.assertEqual(str(stored["timestamp"].dt.tz), "UTC")
            with self.assertRaises(FileExistsError):
                builder.build_dataset(
                    start_epoch=start,
                    last_candle_epoch=last,
                    output_dir=output_dir,
                    comparison_path=comparison_path,
                    request_pacing_seconds=0,
                )

    def test_parse_rejects_out_of_range_candles_instead_of_dropping_them(self):
        start = 1_700_000_000 // 3600 * 3600
        payload = json.dumps([[start - 3600, 99, 102, 100, 101, 1]]).encode()
        with self.assertRaisesRegex(ValueError, "outside the requested"):
            builder._parse_candles(payload, start, start)

    def test_inspection_reports_gaps_and_invalid_values(self):
        start = 1_700_000_000 // 3600 * 3600
        frame = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    [start, start + 7200], unit="s", utc=True
                ),
                "open": [100.0, float("nan")],
                "high": [102.0, 99.0],
                "low": [99.0, 100.0],
                "close": [101.0, 98.0],
                "volume": [1.0, -1.0],
            }
        )
        report = builder._inspect_dataset(frame)
        self.assertEqual(report["missing_interval_count"], 1)
        self.assertFalse(report["finite_ohlcv"])
        self.assertFalse(report["valid_ohlc_bounds"])
        self.assertFalse(report["nonnegative_volume"])

    def test_compare_coinbase_captures_reports_exact_shared_values(self):
        start = 1_700_000_000 // 3600 * 3600
        rows = {
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
            "volume": [1.0, 2.0],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            earlier = root / "earlier.parquet"
            later = root / "later.parquet"
            pd.DataFrame(
                {
                    "timestamp_utc": pd.to_datetime(
                        [start, start + 3600], unit="s", utc=True
                    ),
                    **rows,
                }
            ).to_parquet(earlier, index=False)
            later_rows = {**rows, "volume": [1.0, 2.5]}
            pd.DataFrame(
                {
                    "timestamp": pd.to_datetime(
                        [start, start + 3600], unit="s", utc=True
                    ),
                    **later_rows,
                }
            ).to_parquet(later, index=False)

            comparison = builder.compare_coinbase_captures(earlier, later)

        self.assertEqual(comparison["shared_timestamps"], 2)
        self.assertEqual(comparison["exact_numeric_mismatch_count"], 1)
        self.assertEqual(comparison["exact_numeric_mismatches_by_field"]["volume"], 1)


if __name__ == "__main__":
    unittest.main()

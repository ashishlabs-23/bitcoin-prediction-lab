"""
engine/bitstamp_market_data_service.py — Bitstamp BTC/USD Spot Market Data Integration
=====================================================================================
Official Bitstamp REST API market-data service for BTCognitive Analysis.
Provides on-demand retrieval, rigorous multi-stage validation, short in-memory caching,
request deduplication, fail-closed freshness semantics, and source-separated persistence.

Prime Epistemic & Operating Directives:
1. Strict Source Separation: Never appends Bitstamp candles to Coinbase historical OHLCV
   (data/raw/ohlcv.parquet), protected historical datasets, or trade ledgers.
2. Endpoint: Official public market-data REST endpoint
   GET https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=3600&limit=1000&exclude_current_candle=true
3. Zero Synthetic Fabrication: No interpolation, no stitching, no fabricated quotes.
4. Fail-Closed Safety: Stale or unvalidated data returns explicit MARKET_DATA_UNAVAILABLE.
5. Non-Execution: Live trading disabled; zero broker orders; strictly OFFLINE_RESEARCH_ONLY.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
from engine.data_mode import assert_no_external_network

logger = logging.getLogger("btcognitive.bitstamp_service")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BITSTAMP_STORAGE_DIR = os.path.join(REPO_ROOT, "data", "providers", "bitstamp")
BITSTAMP_PARQUET_PATH = os.path.join(BITSTAMP_STORAGE_DIR, "BTCUSD_1h.parquet")
BITSTAMP_PROVENANCE_PATH = os.path.join(BITSTAMP_STORAGE_DIR, "provenance.json")

BITSTAMP_STEP_SECONDS = 3600  # 1 hour
DEFAULT_LIMIT = 1000
BITSTAMP_CACHE_TTL_SECONDS = 120.0  # 2-minute in-memory cache TTL for deduplication
FRESHNESS_THRESHOLD_HOURS = 2.0


class BitstampDataValidationError(ValueError):
    """Raised when Bitstamp candle data violates integrity invariants."""
    pass


class BitstampMarketDataService:
    """
    On-demand market-data service for Bitstamp BTC/USD Spot hourly candles.
    Thread-safe with request deduplication and local source-separated caching.
    """

    _instance: Optional["BitstampMarketDataService"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self):
        self._refresh_lock = threading.Lock()
        self._cached_df: Optional[pd.DataFrame] = None
        self._cached_metadata: Optional[Dict[str, Any]] = None
        self._last_retrieval_epoch: float = 0.0

    @classmethod
    def get_instance(cls) -> "BitstampMarketDataService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @staticmethod
    def _utc_iso(epoch_seconds: float) -> str:
        return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def validate_bitstamp_ohlc(
        self,
        raw_data: Dict[str, Any],
        retrieval_epoch: Optional[int] = None
    ) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
        """
        Validates raw Bitstamp OHLC response against all data integrity invariants:
        1. Pair matches BTC/USD or btcusd.
        2. Non-empty ohlc array.
        3. All numeric fields present and valid.
        4. Extrema invariants: high >= max(open, close), low <= min(open, close), high >= low.
        5. Non-negative volume.
        6. Completed candle invariant: (timestamp + step) <= retrieval_epoch.
        7. Strict monotonic ascending timestamps.
        8. Hourly alignment: exactly 3600s interval between consecutive candles (no gaps).
        9. No duplicate timestamps.
        """
        retrieval_epoch = retrieval_epoch or int(time.time())

        # 1. Structure check
        ohlc_list = raw_data.get("data", {}).get("ohlc")
        if ohlc_list is None and isinstance(raw_data.get("ohlc"), list):
            ohlc_list = raw_data["ohlc"]

        pair = raw_data.get("data", {}).get("pair") or raw_data.get("pair")
        if pair is not None:
            clean_pair = str(pair).upper().replace("/", "").replace("-", "")
            if clean_pair != "BTCUSD":
                return False, [], f"INVALID_PAIR: Expected BTC/USD, received '{pair}'"

        if not ohlc_list or not isinstance(ohlc_list, list):
            return False, [], "EMPTY_OR_MISSING_OHLC: Bitstamp returned zero candles"

        validated_candles: List[Dict[str, Any]] = []
        prev_ts = None
        eps = 1e-4

        for idx, bar in enumerate(ohlc_list):
            if not isinstance(bar, dict):
                return False, [], f"MALFORMED_ROW_{idx}: Expected dict, got {type(bar).__name__}"

            try:
                t_sec = int(bar.get("timestamp") or 0)
                o = float(bar.get("open") or 0.0)
                h = float(bar.get("high") or 0.0)
                l = float(bar.get("low") or 0.0)
                c = float(bar.get("close") or 0.0)
                v = float(bar.get("volume") or 0.0)
            except (ValueError, TypeError) as e:
                return False, [], f"INVALID_NUMERIC_FIELD_ROW_{idx}: {e}"

            # Basic positivity
            if o <= 0 or h <= 0 or l <= 0 or c <= 0:
                return False, [], f"NON_POSITIVE_PRICE_ROW_{idx}: o={o}, h={h}, l={l}, c={c}"
            if v < 0:
                return False, [], f"NEGATIVE_VOLUME_ROW_{idx}: v={v}"

            # Extrema bounds
            if h < max(o, c) - eps:
                return False, [], f"HIGH_BELOW_OPEN_CLOSE_ROW_{idx}: h={h}, o={o}, c={c}"
            if l > min(o, c) + eps:
                return False, [], f"LOW_ABOVE_OPEN_CLOSE_ROW_{idx}: l={l}, o={o}, c={c}"
            if h < l:
                return False, [], f"HIGH_LESS_THAN_LOW_ROW_{idx}: h={h}, l={l}"

            # Completed candle check: candle end must not be in the future
            candle_end = t_sec + BITSTAMP_STEP_SECONDS
            if candle_end > (retrieval_epoch + 120):  # 120s buffer for clock drift
                return False, [], f"INCOMPLETE_CANDLE_ROW_{idx}: Candle end {candle_end} exceeds retrieval {retrieval_epoch}"

            # Monotonicity & gaps
            if prev_ts is not None:
                if t_sec == prev_ts:
                    return False, [], f"DUPLICATE_TIMESTAMP_ROW_{idx}: Duplicate timestamp {t_sec}"
                if t_sec < prev_ts:
                    return False, [], f"NON_MONOTONIC_TIMESTAMPS_ROW_{idx}: {t_sec} < {prev_ts}"
                delta = t_sec - prev_ts
                if delta != BITSTAMP_STEP_SECONDS:
                    return False, [], f"INTERVAL_GAP_DETECTED_ROW_{idx}: Gap of {delta}s (expected {BITSTAMP_STEP_SECONDS}s)"

            prev_ts = t_sec
            validated_candles.append({
                "timestamp": t_sec,
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": v
            })

        return True, validated_candles, None

    def fetch_raw_bitstamp_ohlcv(
        self,
        limit: int = DEFAULT_LIMIT,
        timeout_sec: float = 30.0
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str], float, str]:
        """
        Executes HTTP GET to the official Bitstamp OHLC public endpoint.
        Uses Windows PowerShell (powershell.exe) with native SChannel TLS 1.2 on Windows
        to negotiate Imperva Incapsula WAF cleanly, or httpx on non-Windows.
        Returns: (success, raw_data_dict, error_msg, latency_ms, raw_sha256)
        """
        assert_no_external_network("Bitstamp OHLCV fetch")
        url = f"https://www.bitstamp.net/api/v2/ohlc/btcusd/?step={BITSTAMP_STEP_SECONDS}&limit={limit}&exclude_current_candle=true"
        start_time = time.perf_counter()

        # On Windows, native Windows PowerShell (powershell.exe) using SChannel TLS 1.2
        # is uniquely trusted by Imperva Incapsula WAF.
        if sys.platform == "win32":
            ps_script = (
                "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; "
                "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
                f"(Invoke-RestMethod -Uri '{url}' -UserAgent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)') | ConvertTo-Json -Depth 6 -Compress"
            )

            for attempt in range(2):
                try:
                    cmd = [
                        "powershell",
                        "-NoProfile",
                        "-NonInteractive",
                        "-Command",
                        ps_script
                    ]
                    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
                    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                    if proc.returncode != 0:
                        err_text = proc.stderr.strip()
                        if attempt == 0:
                            time.sleep(1.0)
                            continue
                        logger.warning(f"PowerShell Bitstamp request failed (code {proc.returncode}): {err_text}")
                        return False, None, f"UPSTREAM_FETCH_FAILED: {err_text}", latency_ms, ""

                    raw_text = proc.stdout.strip()
                    if not raw_text:
                        return False, None, "EMPTY_RESPONSE: Upstream returned no data", latency_ms, ""

                    raw_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
                    data = json.loads(raw_text)
                    return True, data, None, latency_ms, raw_sha256
                except subprocess.TimeoutExpired:
                    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    return False, None, f"UPSTREAM_TIMEOUT: Bitstamp request exceeded {timeout_sec}s", latency_ms, ""
                except Exception as e:
                    if attempt == 0:
                        time.sleep(1.0)
                        continue
                    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    return False, None, f"UPSTREAM_ERROR: {str(e)}", latency_ms, ""

        # Non-Windows fallback using httpx
        try:
            import httpx
            with httpx.Client(timeout=timeout_sec, headers={"User-Agent": "BTCognitive/1.0"}) as client:
                resp = client.get(url)
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                if resp.status_code == 200:
                    raw_text = resp.text
                    raw_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
                    return True, resp.json(), None, latency_ms, raw_sha256
                elif resp.status_code == 429:
                    return False, None, "RATE_LIMIT_EXCEEDED: Bitstamp HTTP 429", latency_ms, ""
                else:
                    return False, None, f"UPSTREAM_HTTP_{resp.status_code}", latency_ms, ""
        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return False, None, f"HTTPX_ERROR: {str(e)}", latency_ms, ""

    def create_dataframe_from_candles(self, validated_candles: List[Dict[str, Any]]) -> pd.DataFrame:
        """Constructs canonical DataFrame from validated candle dicts."""
        rows = []
        for c in validated_candles:
            t_open = c["timestamp"]
            t_close = t_open + BITSTAMP_STEP_SECONDS
            rows.append({
                "timestamp": pd.to_datetime(t_open, unit="s", utc=True),
                "available_time": pd.to_datetime(t_close, unit="s", utc=True),
                "open": float(c["open"]),
                "high": float(c["high"]),
                "low": float(c["low"]),
                "close": float(c["close"]),
                "volume": float(c["volume"]),
                "source_exchange": "BITSTAMP",
                "source_symbol": "BTC/USD",
                "instrument_type": "SPOT",
                "interval": "1h",
            })

        df = pd.DataFrame(rows)
        return df.sort_values("timestamp").reset_index(drop=True)

    def persist_bitstamp_dataset(
        self,
        validated_candles: List[Dict[str, Any]],
        retrieval_iso: str,
        raw_payload_sha256: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Persists validated Bitstamp candles into a source-separated versioned Parquet dataset.
        Never touches or mutates data/raw/ohlcv.parquet.
        """
        os.makedirs(BITSTAMP_STORAGE_DIR, exist_ok=True)
        df = self.create_dataframe_from_candles(validated_candles)

        # Atomic Parquet write
        tmp_parquet = BITSTAMP_PARQUET_PATH + ".tmp"
        df.to_parquet(tmp_parquet, index=False)
        os.replace(tmp_parquet, BITSTAMP_PARQUET_PATH)

        # Compute Parquet SHA-256
        with open(BITSTAMP_PARQUET_PATH, "rb") as f:
            parquet_sha256 = hashlib.sha256(f.read()).hexdigest()

        first_ts = df["timestamp"].iloc[0].isoformat()
        last_open_ts = df["timestamp"].iloc[-1].isoformat()
        last_close_ts = df["available_time"].iloc[-1].isoformat()

        provenance = {
            "provider": "BITSTAMP",
            "source_exchange": "BITSTAMP",
            "source_symbol": "BTC/USD",
            "pair": "btcusd",
            "instrument_type": "SPOT",
            "interval": "1h",
            "step_seconds": BITSTAMP_STEP_SECONDS,
            "row_count": len(df),
            "earliest_candle_open_utc": first_ts,
            "latest_candle_open_utc": last_open_ts,
            "latest_candle_close_utc": last_close_ts,
            "retrieval_timestamp_utc": retrieval_iso,
            "raw_payload_sha256": raw_payload_sha256,
            "parquet_sha256": parquet_sha256,
            "parquet_path": "data/providers/bitstamp/BTCUSD_1h.parquet",
            "licensing_scope": "Bitstamp Public Market Data REST API (Private Research Scope)",
            "execution_status": "OFFLINE_RESEARCH_ONLY",
            "live_trading_enabled": False
        }

        tmp_prov = BITSTAMP_PROVENANCE_PATH + ".tmp"
        with open(tmp_prov, "w", encoding="utf-8") as f:
            json.dump(provenance, f, indent=2)
        os.replace(tmp_prov, BITSTAMP_PROVENANCE_PATH)

        return df, provenance

    def get_or_refresh_bitstamp_data(
        self,
        force_refresh: bool = False,
        max_cache_age_sec: float = BITSTAMP_CACHE_TTL_SECONDS,
        mock_raw_response: Optional[Dict[str, Any]] = None,
        limit: int = DEFAULT_LIMIT,
        persist: Optional[bool] = None
    ) -> Tuple[bool, Optional[pd.DataFrame], Dict[str, Any]]:
        """
        Main entry point for on-demand Bitstamp data retrieval and validation.
        Enforces caching, request deduplication, validation, and source-separated persistence.
        """
        now_epoch = time.time()
        retrieval_iso = self._utc_iso(now_epoch)

        # Default: persist live fetches, do NOT overwrite disk on mock responses unless explicit
        should_persist = persist if persist is not None else (mock_raw_response is None)

        with self._refresh_lock:
            # 1. In-memory cache hit check
            if not force_refresh and self._cached_df is not None:
                cache_age = now_epoch - self._last_retrieval_epoch
                if cache_age < max_cache_age_sec:
                    meta = dict(self._cached_metadata or {})
                    meta["cache_status"] = "IN_MEMORY_CACHE_HIT"
                    meta["cache_age_seconds"] = round(cache_age, 2)
                    return True, self._cached_df.copy(), meta

            # 2. Acquire raw data (mocked or live)
            if mock_raw_response is not None:
                raw_data = mock_raw_response
                raw_bytes = json.dumps(raw_data, sort_keys=True).encode("utf-8")
                raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
                latency_ms = 0.0
                success = True
                err_msg = None
            else:
                success, raw_data, err_msg, latency_ms, raw_sha256 = self.fetch_raw_bitstamp_ohlcv(limit=limit)

            if not success or raw_data is None:
                # Return failure without overwriting existing files
                error_meta = {
                    "provider": "BITSTAMP",
                    "error_code": "MARKET_DATA_UNAVAILABLE",
                    "error_message": err_msg or "Failed acquiring Bitstamp market data",
                    "latency_ms": latency_ms,
                    "retrieval_timestamp_utc": retrieval_iso,
                    "cached_snapshot_available": os.path.exists(BITSTAMP_PARQUET_PATH)
                }
                return False, None, error_meta

            # 3. Validate
            is_valid, validated_bars, val_err = self.validate_bitstamp_ohlc(raw_data, int(now_epoch))
            if not is_valid:
                error_meta = {
                    "provider": "BITSTAMP",
                    "error_code": "DATA_INTEGRITY_VIOLATION",
                    "error_message": val_err or "Bitstamp data validation failed",
                    "latency_ms": latency_ms,
                    "raw_payload_sha256": raw_sha256,
                    "retrieval_timestamp_utc": retrieval_iso
                }
                return False, None, error_meta

            # 4. Construct / Persist to source-separated Parquet
            if should_persist:
                df, provenance = self.persist_bitstamp_dataset(validated_bars, retrieval_iso, raw_sha256)
            else:
                df = self.create_dataframe_from_candles(validated_bars)
                provenance = {
                    "provider": "BITSTAMP",
                    "source_exchange": "BITSTAMP",
                    "source_symbol": "BTC/USD",
                    "pair": "btcusd",
                    "instrument_type": "SPOT",
                    "interval": "1h",
                    "step_seconds": BITSTAMP_STEP_SECONDS,
                    "row_count": len(df),
                    "earliest_candle_open_utc": df["timestamp"].iloc[0].isoformat(),
                    "latest_candle_open_utc": df["timestamp"].iloc[-1].isoformat(),
                    "latest_candle_close_utc": df["available_time"].iloc[-1].isoformat(),
                    "retrieval_timestamp_utc": retrieval_iso,
                    "raw_payload_sha256": raw_sha256,
                    "parquet_sha256": "MOCK_IN_MEMORY_ONLY",
                    "parquet_path": "in_memory",
                    "licensing_scope": "Bitstamp Public Market Data REST API (Private Research Scope)",
                    "execution_status": "OFFLINE_RESEARCH_ONLY",
                    "live_trading_enabled": False
                }

            provenance["latency_ms"] = latency_ms
            provenance["cache_status"] = "FRESH_NETWORK_ACQUISITION"

            # 5. Update in-memory cache
            self._cached_df = df
            self._cached_metadata = provenance
            self._last_retrieval_epoch = now_epoch

            return True, df.copy(), provenance

    @staticmethod
    def compute_bitstamp_freshness(df: pd.DataFrame, max_age_hours: float = FRESHNESS_THRESHOLD_HOURS) -> Dict[str, Any]:
        """
        Computes strict fail-closed data freshness from the latest completed candle's end time.
        data_age_seconds = now_utc - latest_completed_candle_end_utc
        """
        now_epoch = time.time()
        if df is None or df.empty:
            return {
                "is_fresh": False,
                "data_freshness_status": "MARKET_DATA_UNAVAILABLE",
                "data_age_seconds": None,
                "data_age_hours": None,
                "latest_completed_close_utc": None,
                "latest_close_price": None
            }

        last_row = df.iloc[-1]
        avail_time = pd.to_datetime(last_row["available_time"], utc=True)
        avail_epoch = avail_time.timestamp()

        age_seconds = max(0.0, now_epoch - avail_epoch)
        age_hours = round(age_seconds / 3600.0, 2)
        is_fresh = age_hours <= max_age_hours

        return {
            "is_fresh": is_fresh,
            "data_freshness_status": "FRESH" if is_fresh else "MARKET_DATA_STALE",
            "data_age_seconds": round(age_seconds, 1),
            "data_age_hours": age_hours,
            "max_age_hours": max_age_hours,
            "latest_completed_close_utc": avail_time.isoformat(),
            "latest_completed_open_utc": pd.to_datetime(last_row["timestamp"], utc=True).isoformat(),
            "latest_close_price": float(last_row["close"]),
            "source_exchange": "BITSTAMP",
            "source_symbol": "BTC/USD"
        }


# Singleton accessor
def get_bitstamp_service() -> BitstampMarketDataService:
    return BitstampMarketDataService.get_instance()

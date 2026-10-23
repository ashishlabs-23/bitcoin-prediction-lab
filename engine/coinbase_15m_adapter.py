"""
engine/coinbase_15m_adapter.py — Real 15-Minute Market Data Ingestion & Continuity
==================================================================================
Connects directly to Coinbase Exchange REST API for BTC-USD 15-minute (900-second) candles.
Features:
- Official Coinbase REST endpoint: /products/BTC-USD/candles?granularity=900
- Chunked pagination for historical backfill (up to 300 candles per API window)
- Causal point-in-time validation: strictly increasing 900s timestamps, OHLC integrity, non-negative volume
- Strict exclusion of partially-formed live candles from historical training / evaluation buffers
- Continuity segment tracking: assigns segment IDs across data gaps (>900s)
- Atomic persistence to data/raw/coinbase_15m.parquet with machine-readable manifest
- Zero synthetic data fabrication: fails closed if exchange is unreachable.
"""

import os
import time
import json
import math
import hashlib
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np

logger = logging.getLogger("btcognitive.coinbase_15m")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_PARQUET_PATH = os.path.join(REPO_ROOT, "data", "raw", "coinbase_15m.parquet")
DEFAULT_MANIFEST_PATH = os.path.join(REPO_ROOT, "data", "raw", "coinbase_15m_manifest.json")
COINBASE_CANDLES_URL = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
GRANULARITY_15M = 900  # 15 minutes in seconds


def _utc_iso(epoch_sec: float) -> str:
    return datetime.fromtimestamp(epoch_sec, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Coinbase15mAdapter:
    """
    Ingests, validates, and manages Coinbase BTC-USD 15-minute OHLCV candle streams.
    """

    def __init__(
        self,
        parquet_path: str = DEFAULT_PARQUET_PATH,
        manifest_path: str = DEFAULT_MANIFEST_PATH,
        user_agent: str = "BTCognitive-V10/1.0"
    ):
        self.parquet_path = parquet_path
        self.manifest_path = manifest_path
        self.user_agent = user_agent

    def fetch_single_chunk(
        self,
        start_iso: Optional[str] = None,
        end_iso: Optional[str] = None,
        timeout_sec: float = 6.0
    ) -> List[List[float]]:
        """
        Fetches up to 300 15m candles from Coinbase Exchange REST API.
        Response format per candle: [ time, low, high, open, close, volume ]
        """
        params = [f"granularity={GRANULARITY_15M}"]
        if start_iso:
            params.append(f"start={start_iso}")
        if end_iso:
            params.append(f"end={end_iso}")
        
        query_str = "&".join(params)
        url = f"{COINBASE_CANDLES_URL}?{query_str}"

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list):
                    return data
                raise ValueError(f"Unexpected Coinbase response format: {type(data)}")
        except Exception as e:
            logger.warning(f"Coinbase 15m fetch failed for URL {url}: {e}")
            raise

    def fetch_historical_backfill(self, total_candles: int = 1800) -> List[Dict[str, Any]]:
        """
        Paginates backwards in time to fetch total_candles genuine 15m bars from Coinbase.
        """
        candles_by_time: Dict[int, Dict[str, Any]] = {}
        now_epoch = int(time.time())
        # Align end to last completed 15m boundary
        cursor_end = (now_epoch // GRANULARITY_15M) * GRANULARITY_15M

        # Max 300 candles per call
        chunk_size = min(300, total_candles)
        
        while len(candles_by_time) < total_candles:
            cursor_start = cursor_end - (chunk_size * GRANULARITY_15M)
            start_iso = _utc_iso(cursor_start)
            end_iso = _utc_iso(cursor_end)

            try:
                raw_chunk = self.fetch_single_chunk(start_iso=start_iso, end_iso=end_iso)
            except Exception as e:
                logger.error(f"Error fetching chunk [{start_iso} -> {end_iso}]: {e}")
                break

            if not raw_chunk:
                break

            chunk_added = 0
            for item in raw_chunk:
                # Coinbase: [ time, low, high, open, close, volume ]
                if len(item) < 6:
                    continue
                t, low, high, open_, close, vol = item[0], item[1], item[2], item[3], item[4], item[5]
                t_int = int(t)
                if t_int not in candles_by_time:
                    candles_by_time[t_int] = {
                        "time": t_int,
                        "open": float(open_),
                        "high": float(high),
                        "low": float(low),
                        "close": float(close),
                        "volume": float(vol)
                    }
                    chunk_added += 1

            if chunk_added == 0:
                # No new older candles returned
                break

            # Move cursor back
            oldest_in_chunk = min(int(x[0]) for x in raw_chunk)
            cursor_end = oldest_in_chunk

            # Rate limit politeness
            time.sleep(0.2)

        sorted_candles = [candles_by_time[k] for k in sorted(candles_by_time.keys())]
        return sorted_candles

    def validate_and_segment_candles(
        self,
        candles: List[Dict[str, Any]],
        discard_forming: bool = True
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Validates OHLCV integrity, bucket alignment, and tags continuity segments.
        """
        if not candles:
            return [], {"status": "EMPTY", "count": 0}

        now_epoch = int(time.time())
        current_forming_bucket = (now_epoch // GRANULARITY_15M) * GRANULARITY_15M

        validated: List[Dict[str, Any]] = []
        seen_timestamps = set()
        segment_id = 0
        last_t = None
        gap_count = 0

        for c in candles:
            t = int(c.get("time", 0))
            if t <= 0:
                continue

            # Check 900s bucket alignment
            if t % GRANULARITY_15M != 0:
                continue

            # Discard duplicate timestamps
            if t in seen_timestamps:
                continue

            # Discard currently forming partial candle if requested
            if discard_forming and t >= current_forming_bucket:
                continue

            op = float(c.get("open", 0.0))
            hi = float(c.get("high", 0.0))
            lo = float(c.get("low", 0.0))
            cl = float(c.get("close", 0.0))
            vol = float(c.get("volume", 0.0))

            # Finite and positive price checks
            if not all(math.isfinite(x) and x > 0 for x in [op, hi, lo, cl]):
                continue
            if not math.isfinite(vol) or vol < 0:
                continue

            # OHLC geometric bounds
            if lo > min(op, cl) or hi < max(op, cl) or hi < lo:
                continue

            # Gap check: if step > 900s, increment segment_id
            if last_t is not None:
                step = t - last_t
                if step < GRANULARITY_15M:
                    # Non-increasing timestamp violation
                    continue
                elif step > GRANULARITY_15M:
                    gap_count += 1
                    segment_id += 1

            seen_timestamps.add(t)
            last_t = t

            row = {
                "timestamp": pd.to_datetime(t, unit="s", utc=True),
                "epoch_time": t,
                "open": op,
                "high": hi,
                "low": lo,
                "close": cl,
                "volume": vol,
                "segment_id": f"seg_15m_{segment_id}"
            }
            validated.append(row)

        metadata = {
            "status": "VALIDATED" if validated else "NO_VALID_CANDLES",
            "total_validated": len(validated),
            "gap_count": gap_count,
            "segment_count": segment_id + 1 if validated else 0,
            "first_candle_utc": _utc_iso(validated[0]["epoch_time"]) if validated else None,
            "last_completed_candle_utc": _utc_iso(validated[-1]["epoch_time"]) if validated else None,
            "last_completed_epoch": validated[-1]["epoch_time"] if validated else None,
            "last_completed_close": validated[-1]["close"] if validated else None,
            "granularity_seconds": GRANULARITY_15M,
            "instrument": "BTC-USD",
            "source": "Coinbase Exchange REST API"
        }
        return validated, metadata

    def persist(
        self,
        candles: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Saves validated 15m candle history to parquet and creates a provenance manifest.
        Returns the SHA-256 hash of the parquet file.
        """
        # Merge with existing history if parquet already exists on disk
        combined_dict: Dict[int, Dict[str, Any]] = {}
        if os.path.exists(self.parquet_path):
            try:
                existing_df = pd.read_parquet(self.parquet_path)
                for _, r in existing_df.iterrows():
                    e_t = int(r.get("epoch_time", r.get("time", 0)))
                    if e_t > 0:
                        combined_dict[e_t] = {
                            "time": e_t,
                            "open": float(r["open"]),
                            "high": float(r["high"]),
                            "low": float(r["low"]),
                            "close": float(r["close"]),
                            "volume": float(r["volume"])
                        }
            except Exception as e:
                logger.warning(f"Could not read existing parquet to merge: {e}")

        for c in candles:
            e_t = int(c.get("epoch_time", c.get("time", 0)))
            if e_t > 0:
                combined_dict[e_t] = {
                    "time": e_t,
                    "open": float(c["open"]),
                    "high": float(c["high"]),
                    "low": float(c["low"]),
                    "close": float(c["close"]),
                    "volume": float(c["volume"])
                }

        merged_raw = [combined_dict[k] for k in sorted(combined_dict.keys())]
        validated_all, fresh_meta = self.validate_and_segment_candles(merged_raw, discard_forming=True)
        if validated_all:
            candles = validated_all
            metadata = fresh_meta

        df = pd.DataFrame(candles)
        os.makedirs(os.path.dirname(self.parquet_path), exist_ok=True)

        # Write Parquet atomically
        temp_parquet = f"{self.parquet_path}.tmp"
        df.to_parquet(temp_parquet, engine="pyarrow", index=False)
        if os.path.exists(self.parquet_path):
            os.remove(self.parquet_path)
        os.rename(temp_parquet, self.parquet_path)

        # Compute SHA-256
        sha256 = hashlib.sha256()
        with open(self.parquet_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        file_hash = sha256.hexdigest()

        # Write manifest
        manifest = {
            "dataset_id": "coinbase_btc_usd_15m_validated",
            "source": "Coinbase Exchange REST API",
            "instrument": "BTC-USD",
            "granularity_seconds": GRANULARITY_15M,
            "timeframe": "15m",
            "sha256_hash": file_hash,
            "file_size_bytes": os.path.getsize(self.parquet_path),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata
        }
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Persisted {len(candles)} 15m candles to {self.parquet_path} (hash: {file_hash[:16]}...)")
        return file_hash

    def load_cached(self) -> Optional[Tuple[pd.DataFrame, Dict[str, Any]]]:
        """Loads cached 15m candles and manifest from disk if available."""
        if not os.path.exists(self.parquet_path) or not os.path.exists(self.manifest_path):
            return None
        try:
            df = pd.read_parquet(self.parquet_path)
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            return df, manifest
        except Exception as e:
            logger.warning(f"Failed loading 15m cache: {e}")
            return None

    def get_or_sync_15m_candles(
        self,
        target_count: int = 1800,
        max_age_seconds: int = 1800
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Returns validated 15m DataFrame. If cache is missing, stale, or has fewer than
        target_count candles, syncs with Coinbase REST API and merges without truncating history.
        """
        cached = self.load_cached()
        if cached is not None:
            df, manifest = cached
            meta = manifest.get("metadata", {})
            last_epoch = meta.get("last_completed_epoch")
            if last_epoch:
                age = time.time() - last_epoch
                if age < max_age_seconds and len(df) >= target_count:
                    meta["cache_hit"] = True
                    meta["cache_age_seconds"] = round(age, 1)
                    return df, meta

        # Otherwise perform live sync and merge with cached history
        logger.info("Syncing fresh 15-minute candles from Coinbase...")
        fetch_count = max(target_count, len(df) if cached is not None else 0)
        raw = self.fetch_historical_backfill(total_candles=fetch_count)
        
        # Merge raw candles with existing cached candles if available
        combined_dict: Dict[int, Dict[str, Any]] = {}
        if cached is not None:
            c_df, _ = cached
            for _, r in c_df.iterrows():
                e_t = int(r["epoch_time"])
                combined_dict[e_t] = {
                    "time": e_t,
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "volume": float(r["volume"])
                }

        for c in raw:
            c_t = int(c["time"])
            combined_dict[c_t] = c

        merged_raw = [combined_dict[k] for k in sorted(combined_dict.keys())]

        validated, metadata = self.validate_and_segment_candles(merged_raw, discard_forming=True)
        if not validated:
            if cached is not None:
                df, manifest = cached
                meta = manifest.get("metadata", {})
                meta["degraded_warning"] = "Live fetch failed; using existing cache"
                return df, meta
            raise RuntimeError("Failed to fetch or validate 15m candles from Coinbase")

        self.persist(validated, metadata)
        df = pd.DataFrame(validated)
        metadata["cache_hit"] = False
        return df, metadata


# Global singleton instance
coinbase_15m_adapter = Coinbase15mAdapter()

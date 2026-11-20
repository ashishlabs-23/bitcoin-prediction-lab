"""Tardis.dev Trade Archive Parser and Multi-Timeframe Candle Aggregator.

Governed under BTCognitive V35.0 Protocol:
- Strictly point-in-time causal aggregation.
- Microsecond timestamp semantics.
- Deduplication and stable chronological sorting.
- 4-hour candles derived strictly from closed 1-hour bars.
- Zero price interpolation.
"""

from __future__ import annotations

import io
import gzip
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


class TardisSampleParser:
    """Parses Tardis.dev CSV trade dumps and causally synthesizes OHLCV bars."""

    REQUIRED_COLUMNS = ["exchange", "symbol", "timestamp", "price", "amount"]

    @classmethod
    def load_and_clean_trades(
        cls,
        source: Union[str, Path, io.StringIO, bytes],
        symbol_filter: str = "BTCUSD"
    ) -> pd.DataFrame:
        """
        Loads raw Tardis.dev trade CSV (plain text or gzipped), cleans duplicates,
        and enforces microsecond chronological ordering.
        """
        if isinstance(source, bytes):
            # Decompress if gzipped
            if source[:2] == b"\x1f\x8b":
                source = gzip.decompress(source)
            df = pd.read_csv(io.BytesIO(source))
        elif isinstance(source, (str, Path)):
            path_obj = Path(source)
            if path_obj.exists():
                if path_obj.suffix == ".gz":
                    df = pd.read_csv(path_obj, compression="gzip")
                else:
                    df = pd.read_csv(path_obj)
            else:
                # Assume string content
                df = pd.read_csv(io.StringIO(str(source)))
        elif isinstance(source, io.StringIO):
            df = pd.read_csv(source)
        else:
            raise ValueError(f"Unsupported source type: {type(source)}")

        # Normalize column names
        df.columns = [c.strip().lower() for c in df.columns]

        # Verify columns
        for col in cls.REQUIRED_COLUMNS:
            if col not in df.columns:
                raise ValueError(f"Tardis trade record missing required column: '{col}'")

        # Filter symbol
        if symbol_filter:
            df = df[df["symbol"].str.upper() == symbol_filter.upper()].copy()

        if len(df) == 0:
            return pd.DataFrame(columns=["exchange", "symbol", "timestamp", "local_timestamp", "id", "side", "price", "amount", "dt_utc"])

        # Timestamp semantics: Tardis records timestamp in microseconds since Unix epoch
        # (e.g. 1561939200000000 = 2019-07-01 00:00:00 UTC)
        df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce").astype("int64")
        df["price"] = pd.to_numeric(df["price"], errors="coerce").astype("float64")
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").astype("float64")

        # Convert microseconds to datetime64[ns, UTC]
        df["dt_utc"] = pd.to_datetime(df["timestamp"], unit="us", utc=True)

        # Deduplication: remove identical executions
        dedup_cols = ["timestamp", "price", "amount"]
        if "id" in df.columns:
            dedup_cols.append("id")
        df = df.drop_duplicates(subset=dedup_cols, keep="first").copy()

        # Enforce stable chronological sort
        sort_cols = ["timestamp"]
        if "id" in df.columns:
            sort_cols.append("id")
        df = df.sort_values(sort_cols).reset_index(drop=True)

        return df

    @classmethod
    def aggregate_to_timeframe(
        cls,
        df_trades: pd.DataFrame,
        freq: str = "1h"
    ) -> pd.DataFrame:
        """
        Aggregates clean tick trades into causal OHLCV candles with VWAP and trade count.
        freq: '5min' (or '5m'), '1h', etc.
        """
        if df_trades is None or len(df_trades) == 0:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "vwap", "trade_count"])

        df = df_trades.copy()
        df = df.set_index("dt_utc")

        # Group by bucket floor
        grouped = df.groupby(pd.Grouper(freq=freq))

        candles = []
        last_close = None

        for bucket_start, group in grouped:
            if len(group) == 0:
                # Exchange downtime / zero trade interval
                # Emitted as flat bar if last_close is available (no interpolation)
                if last_close is not None:
                    candles.append({
                        "timestamp": bucket_start.isoformat(),
                        "open": last_close,
                        "high": last_close,
                        "low": last_close,
                        "close": last_close,
                        "volume": 0.0,
                        "vwap": last_close,
                        "trade_count": 0,
                        "is_zero_volume_gap": True
                    })
                continue

            open_p = float(group["price"].iloc[0])
            high_p = float(group["price"].max())
            low_p = float(group["price"].min())
            close_p = float(group["price"].iloc[-1])
            vol = float(group["amount"].sum())
            cnt = int(len(group))
            vwap_p = float((group["price"] * group["amount"]).sum() / vol) if vol > 0 else close_p

            last_close = close_p

            candles.append({
                "timestamp": bucket_start.isoformat(),
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": vol,
                "vwap": round(vwap_p, 2),
                "trade_count": cnt,
                "is_zero_volume_gap": False
            })

        return pd.DataFrame(candles)

    @classmethod
    def aggregate_4h_from_1h(cls, df_1h: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Aggregates completed 1-hour bars into 4-hour candles.
        Enforces causal rule: a 4h candle is valid if and only if all 4 1-hour constituent bars are present.
        """
        if df_1h is None or len(df_1h) == 0:
            return pd.DataFrame(), {"status": "EMPTY_INPUT", "completed_4h_candles": 0}

        df = df_1h.copy()
        df["dt"] = pd.to_datetime(df["timestamp"], utc=True)
        df["bucket_4h"] = df["dt"].dt.floor("4h")

        candles_4h = []
        incomplete_count = 0

        for bucket_start, group in df.groupby("bucket_4h"):
            # Enforce 4 constituent bars
            if len(group) < 4:
                incomplete_count += 1
                continue

            open_p = float(group["open"].iloc[0])
            high_p = float(group["high"].max())
            low_p = float(group["low"].min())
            close_p = float(group["close"].iloc[-1])
            vol = float(group["volume"].sum())
            cnt = int(group["trade_count"].sum()) if "trade_count" in group.columns else 0

            candles_4h.append({
                "timestamp": bucket_start.isoformat(),
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": vol,
                "trade_count": cnt,
                "constituent_1h_bars": len(group)
            })

        res_df = pd.DataFrame(candles_4h)
        meta = {
            "status": "SUCCESS",
            "total_1h_bars": len(df_1h),
            "completed_4h_candles": len(res_df),
            "incomplete_dropped_buckets": incomplete_count
        }
        return res_df, meta


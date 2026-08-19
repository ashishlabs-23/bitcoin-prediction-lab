"""
engine/feature_store.py — BTCognitive V3 SQLite Operational Feature Store
========================================================================
High-throughput, ACID-compliant operational storage utilizing SQLite WAL mode.
Stores aligned market streams (candles, features, orderflow, macro, sentiment)
and supports zero-copy Parquet dataset exports for ML training.
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
import numpy as np
import pandas as pd

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_PROCESSED_DIR

logger = logging.getLogger("btcognitive.feature_store")

DEFAULT_DB_PATH = os.path.join(DATA_PROCESSED_DIR, "feature_store.db")


from contextlib import contextmanager

class FeatureStore:
    """
    Operational SQLite storage for BTCognitive V3 multimodal data engine.
    Configured with Write-Ahead Logging (WAL) and NORMAL synchrony for concurrent access.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    @contextmanager
    def _connection(self):
        """Yields a thread-safe SQLite connection with WAL mode enabled and ensures clean closure."""
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initializes tables for all 5 operational market data streams."""
        with self._connection() as conn:
            # 1. Candles table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS candles (
                    timestamp TEXT PRIMARY KEY,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    degraded INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                );
            """)

            # 2. Features table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS features (
                    timestamp TEXT PRIMARY KEY,
                    feature_vector BLOB NOT NULL,
                    feature_dict TEXT NOT NULL,
                    shape_rows INTEGER NOT NULL,
                    shape_cols INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

            # 3. Orderflow table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orderflow (
                    timestamp TEXT PRIMARY KEY,
                    bid_depth REAL NOT NULL,
                    ask_depth REAL NOT NULL,
                    spread REAL NOT NULL,
                    imbalance REAL NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

            # 4. Macro table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS macro (
                    timestamp TEXT PRIMARY KEY,
                    funding_rate REAL NOT NULL,
                    open_interest REAL NOT NULL,
                    fear_greed REAL NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

            # 5. Sentiment table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sentiment (
                    timestamp TEXT PRIMARY KEY,
                    sentiment_score REAL NOT NULL,
                    embed_dim0 REAL NOT NULL,
                    embed_dim1 REAL NOT NULL,
                    embed_dim2 REAL NOT NULL,
                    headline TEXT,
                    created_at TEXT NOT NULL
                );
            """)

            # Indexes for timestamp lookup speed
            conn.execute("CREATE INDEX IF NOT EXISTS idx_candles_ts ON candles(timestamp);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_features_ts ON features(timestamp);")
            conn.commit()

    def insert_candle(self, candle: Dict[str, Any]) -> None:
        """Inserts or replaces 1-minute OHLCV candle record."""
        ts = str(candle.get("timestamp"))
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO candles (timestamp, open, high, low, close, volume, degraded, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ts,
                float(candle["open"]),
                float(candle["high"]),
                float(candle["low"]),
                float(candle["close"]),
                float(candle["volume"]),
                1 if candle.get("degraded", False) else 0,
                created_at
            ))
            conn.commit()

    def insert_features(self, timestamp: str, vector: np.ndarray, feature_dict: Dict[str, float]) -> None:
        """Inserts engineered feature vector (stored as float32 binary buffer) and JSON metadata."""
        created_at = datetime.now(timezone.utc).isoformat()
        vec_bytes = np.asarray(vector, dtype=np.float32).tobytes()
        dict_json = json.dumps(feature_dict)
        shape = vector.shape
        rows = shape[0] if vector.ndim > 1 else 1
        cols = shape[1] if vector.ndim > 1 else shape[0]

        with self._connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO features (timestamp, feature_vector, feature_dict, shape_rows, shape_cols, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(timestamp), vec_bytes, dict_json, rows, cols, created_at))
            conn.commit()

    def insert_orderflow(self, data: Dict[str, Any]) -> None:
        """Inserts order book depth and flow metrics."""
        ts = str(data["timestamp"])
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO orderflow (timestamp, bid_depth, ask_depth, spread, imbalance, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ts,
                float(data.get("bid_depth", 0.0)),
                float(data.get("ask_depth", 0.0)),
                float(data.get("spread", 0.0)),
                float(data.get("imbalance", 0.0)),
                created_at
            ))
            conn.commit()

    def insert_macro(self, data: Dict[str, Any]) -> None:
        """Inserts funding rate, open interest, and fear & greed index."""
        ts = str(data["timestamp"])
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO macro (timestamp, funding_rate, open_interest, fear_greed, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                ts,
                float(data.get("funding_rate", 0.0)),
                float(data.get("open_interest", 0.0)),
                float(data.get("fear_greed", 50.0)),
                created_at
            ))
            conn.commit()

    def insert_sentiment(self, data: Dict[str, Any]) -> None:
        """Inserts news sentiment score and embedding projections."""
        ts = str(data["timestamp"])
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sentiment (timestamp, sentiment_score, embed_dim0, embed_dim1, embed_dim2, headline, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ts,
                float(data.get("sentiment_score", 0.0)),
                float(data.get("embed_dim0", 0.0)),
                float(data.get("embed_dim1", 0.0)),
                float(data.get("embed_dim2", 0.0)),
                str(data.get("headline", "")),
                created_at
            ))
            conn.commit()

    def get_recent_candles(self, limit: int = 120) -> pd.DataFrame:
        """Retrieves the N most recent candles ordered by timestamp ascending."""
        with self._connection() as conn:
            query = """
                SELECT timestamp, open, high, low, close, volume, degraded
                FROM candles
                ORDER BY timestamp DESC
                LIMIT ?
            """
            df = pd.read_sql_query(query, conn, params=(limit,))
        if df.empty:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "degraded"])
        return df.iloc[::-1].reset_index(drop=True)

    def export_to_parquet(
        self,
        table_name: str,
        output_path: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> str:
        """
        Exports data from any SQLite table to an optimized Parquet file for ML training.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        valid_tables = {"candles", "features", "orderflow", "macro", "sentiment"}
        if table_name not in valid_tables:
            raise ValueError(f"Invalid table name '{table_name}'. Must be one of {valid_tables}")

        query = f"SELECT * FROM {table_name}"
        conditions = []
        params = []
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp ASC"

        with self._connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        df.to_parquet(output_path, engine="pyarrow", index=False)
        logger.info(f"Exported {len(df)} rows from table '{table_name}' to {output_path}")
        return output_path


# Global Singleton Instance
feature_store = FeatureStore()

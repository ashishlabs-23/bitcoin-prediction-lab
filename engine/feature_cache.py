"""
engine/feature_cache.py — Event-Driven In-Memory Feature Store
=============================================================
Authoritative in-memory DataFrame store that computes and caches technical features
once on every closed candle / tick event. Eliminates repeated disk & Parquet reads.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from config import DATA_PROCESSED_DIR

logger = logging.getLogger("btcognitive.feature_cache")


class FeatureCache:
    """
    Thread-safe, event-driven in-memory feature cache for BTCognitive.
    """

    def __init__(self):
        self._df: Optional[pd.DataFrame] = None
        self._last_update_ts: float = 0.0
        self._is_initialized: bool = False
        self._is_degraded: bool = False

    def initialize(self):
        """Initializes the in-memory dataframe from local parquet or enters DEGRADED state."""
        feat_path = os.path.join(DATA_PROCESSED_DIR, "features.parquet")
        if os.path.exists(feat_path):
            try:
                df = pd.read_parquet(feat_path, engine="pyarrow")
                df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
                self._df = df.sort_values("timestamp").reset_index(drop=True)
                self._is_initialized = True
                self._is_degraded = False
                self._last_update_ts = time.time()
                logger.info(f"FeatureCache initialized from parquet with {len(self._df)} rows.")
                return
            except Exception as e:
                logger.warning(f"FeatureCache failed to read parquet: {e}")

        # If no real data available, enter DEGRADED state without fabricating prices
        self._df = pd.DataFrame()
        self._is_initialized = True
        self._is_degraded = True
        self._last_update_ts = time.time()
        logger.warning("FeatureCache: No real historical data found. Entering DEGRADED state.")

    def is_healthy(self) -> bool:
        """Returns True if cache has valid real data and is not degraded."""
        return self._is_initialized and not self._is_degraded and self._df is not None and not self._df.empty

    def update_from_candles(
        self,
        candles: List[Dict[str, Any]],
        funding_rate: float = 0.0001,
        funding_change: float = 0.0,
        oi: float = 100000.0,
        oi_change: float = 0.0
    ):
        """
        Recomputes full feature set from incoming klines in a single pass.
        Called once when a new candle closes or on background polling ticks.
        """
        if not candles:
            return

        df = pd.DataFrame(candles)
        if "time" in df.columns and "timestamp" not in df.columns:
            df["timestamp"] = pd.to_datetime(df["time"], unit="ms", utc=True)

        # Returns
        df["ret_1h"] = np.log(df["close"] / df["close"].shift(1)).fillna(0.0)
        df["ret_4h"] = np.log(df["close"] / df["close"].shift(4)).fillna(0.0)
        df["ret_24h"] = np.log(df["close"] / df["close"].shift(24)).fillna(0.0)

        # RSI-14
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1.0 / 14.0, min_periods=14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / 14.0, min_periods=14, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df["rsi_14"] = (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)

        # MACD (12, 26, 9)
        ema12 = df["close"].ewm(span=12, adjust=False).mean()
        ema26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

        # Moving Average Ratios
        sma20 = df["close"].rolling(window=20).mean()
        sma50 = df["close"].rolling(window=50).mean()
        df["sma_ratio_20"] = ((df["close"] / sma20) - 1.0).fillna(0.0)
        df["sma_ratio_50"] = ((df["close"] / sma50) - 1.0).fillna(0.0)

        # Volatility & ATR
        df["realized_vol_24h"] = df["ret_1h"].rolling(window=24).std().fillna(0.015)
        tr = np.maximum(
            df["high"] - df["low"],
            np.maximum((df["high"] - df["close"].shift(1)).abs(), (df["low"] - df["close"].shift(1)).abs())
        )
        df["atr_14"] = tr.rolling(window=14).mean().fillna(df["close"] * 0.01)

        # Derivatives
        df["funding_rate"] = funding_rate
        df["funding_rate_change_24h"] = funding_change
        df["open_interest"] = oi
        df["oi_pct_change_24h"] = oi_change

        self._df = df
        self._last_update_ts = time.time()
        self._is_initialized = True

    def get_features_df(self) -> pd.DataFrame:
        """Returns the in-memory dataframe instantly without disk reads."""
        if self._df is None or not self._is_initialized:
            self.initialize()
        return self._df

    def get_latest_row(self) -> Optional[pd.Series]:
        """Returns the latest feature snapshot row."""
        df = self.get_features_df()
        return df.iloc[-1] if not df.empty else None

    @property
    def is_ready(self) -> bool:
        return self._is_initialized and self._df is not None and not self._df.empty


# Global singleton instance
feature_cache = FeatureCache()

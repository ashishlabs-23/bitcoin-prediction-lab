"""
engine/feature_pipeline.py — BTCognitive V3 Multimodal Feature Pipeline
======================================================================
Transforms synchronized multi-stream market data into a standardized (120, 32)
float32 immutable numpy tensor.

Features include:
  - Technical Indicators (EMA 20/50/200, RSI 14, MACD/Signal, ATR 14, Bollinger Width/%B, VWAP, ROC, ADX, OBV)
  - Normalized OHLCV price action & rolling volatility
  - Order book depth & flow imbalance
  - Macro derivatives flow (funding rate, open interest delta, Fear & Greed)
  - Sentiment polarity & multimodal text embeddings
"""

import os
import sys
import collections
from typing import Dict, List, Optional, Any, Union
import numpy as np
import pandas as pd

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.feature_store import feature_store, FeatureStore

FEATURE_NAMES = [
    # Price action & Normalized OHLCV (1 - 5)
    "norm_open",
    "norm_high",
    "norm_low",
    "norm_close_ret",
    "norm_volume",
    # Moving Averages & Trend Ratios (6 - 10)
    "ema_20_ratio",
    "ema_50_ratio",
    "ema_200_ratio",
    "vwap_ratio",
    "roc_10",
    # Momentum Oscillators (11 - 14)
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    # Volatility & Bands (15 - 18)
    "atr_14_ratio",
    "bollinger_width",
    "bollinger_pct_b",
    "realized_vol_24",
    # Directional Movement & Volume Flow (19 - 21)
    "adx_14",
    "obv_norm",
    "plus_minus_di_spread",
    # Microstructure & Orderbook Depth (22 - 25)
    "bid_ask_spread",
    "order_book_imbalance",
    "depth_liquidity_score",
    "microstructure_pressure",
    # Macro Derivatives & Market Sentiment (26 - 28)
    "funding_rate",
    "open_interest_delta",
    "fear_greed_index",
    # News Sentiment & Embeddings (29 - 32)
    "sentiment_score",
    "sentiment_embed_dim0",
    "sentiment_embed_dim1",
    "sentiment_embed_dim2",
]

NUM_FEATURES = len(FEATURE_NAMES)  # Exactly 32
SEQUENCE_LENGTH = 120              # Exactly 120 candles


class FeaturePipeline:
    """
    Real-time streaming feature pipeline converting sequential market events
    into immutable (120, 32) float32 numpy tensors.
    """

    def __init__(self, store: Optional[FeatureStore] = None, max_history: int = 500):
        self.store = store or feature_store
        self.max_history = max_history
        self._history: List[Dict[str, Any]] = []
        self._feature_history: collections.deque = collections.deque(maxlen=self.max_history)
        self._latest_features_dict: Dict[str, float] = {name: 0.0 for name in FEATURE_NAMES}

        # Initialize state from store if available
        self._warmup_from_store()

    def _warmup_from_store(self) -> None:
        """Loads historical candles from operational SQLite store on initialization."""
        try:
            recent_df = self.store.get_recent_candles(limit=self.max_history)
            if not recent_df.empty:
                for _, row in recent_df.iterrows():
                    self.update(row.to_dict(), persist=False)
        except Exception as e:
            # Cold start fallback
            pass

    def update(
        self,
        candle: Union[Dict[str, Any], pd.Series],
        orderflow: Optional[Dict[str, Any]] = None,
        macro: Optional[Dict[str, Any]] = None,
        sentiment: Optional[Dict[str, Any]] = None,
        persist: bool = True
    ) -> None:
        """
        Ingests a completed 1-minute candle and associated multimodal context.
        Computes all 32 technical and multimodal features, storing the result.
        """
        c_dict = candle.to_dict() if isinstance(candle, pd.Series) else dict(candle)
        
        # Ensure mandatory OHLCV fields
        open_p = float(c_dict.get("open", 0.0))
        high_p = float(c_dict.get("high", open_p))
        low_p = float(c_dict.get("low", open_p))
        close_p = float(c_dict.get("close", open_p))
        vol = float(c_dict.get("volume", 0.0))
        ts = str(c_dict.get("timestamp", ""))
        degraded = bool(c_dict.get("degraded", False))

        item = {
            "timestamp": ts,
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "volume": vol,
            "degraded": degraded,
            "orderflow": orderflow or {},
            "macro": macro or {},
            "sentiment": sentiment or {}
        }
        self._history.append(item)
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

        # Compute full features for the sequence
        computed_dict, feat_vector = self._compute_latest_row()
        self._latest_features_dict = computed_dict
        self._feature_history.append(feat_vector)

        if persist:
            try:
                self.store.insert_candle(item)
                self.store.insert_features(ts, feat_vector, computed_dict)
                if orderflow:
                    self.store.insert_orderflow({"timestamp": ts, **orderflow})
                if macro:
                    self.store.insert_macro({"timestamp": ts, **macro})
                if sentiment:
                    self.store.insert_sentiment({"timestamp": ts, **sentiment})
            except Exception:
                pass

    def _compute_latest_row(self) -> tuple[Dict[str, float], np.ndarray]:
        """Calculates the 32 engineered features for the most recent candle."""
        n = len(self._history)
        if n == 0:
            zeros = np.zeros(NUM_FEATURES, dtype=np.float32)
            return {name: 0.0 for name in FEATURE_NAMES}, zeros

        closes = np.array([x["close"] for x in self._history], dtype=np.float64)
        opens = np.array([x["open"] for x in self._history], dtype=np.float64)
        highs = np.array([x["high"] for x in self._history], dtype=np.float64)
        lows = np.array([x["low"] for x in self._history], dtype=np.float64)
        volumes = np.array([x["volume"] for x in self._history], dtype=np.float64)
        current_close = closes[-1] if closes[-1] > 0 else 1.0

        # 1-5: Normalized OHLCV
        norm_open = float((opens[-1] - current_close) / current_close)
        norm_high = float((highs[-1] - current_close) / current_close)
        norm_low = float((lows[-1] - current_close) / current_close)
        prev_close = closes[-2] if n > 1 and closes[-2] > 0 else current_close
        norm_close_ret = float(np.log(max(current_close, 1e-8) / max(prev_close, 1e-8)))
        
        # Volume rolling z-score (20-bar)
        v_win = volumes[-20:] if n >= 20 else volumes
        v_mean = float(np.mean(v_win))
        v_std = float(np.std(v_win)) + 1e-8
        norm_volume = float((volumes[-1] - v_mean) / v_std)

        # 6-8: EMA 20, 50, 200 ratios
        def calc_ema(arr: np.ndarray, span: int) -> float:
            if len(arr) == 0:
                return current_close
            s = pd.Series(arr)
            return float(s.ewm(span=span, adjust=False).mean().iloc[-1])

        ema20 = calc_ema(closes, 20)
        ema50 = calc_ema(closes, 50)
        ema200 = calc_ema(closes, 200)
        ema_20_ratio = float((current_close / ema20) - 1.0) if ema20 > 0 else 0.0
        ema_50_ratio = float((current_close / ema50) - 1.0) if ema50 > 0 else 0.0
        ema_200_ratio = float((current_close / ema200) - 1.0) if ema200 > 0 else 0.0

        # 9: VWAP (Cumulative typical price * volume / cumulative volume over available window)
        typ_price = (highs + lows + closes) / 3.0
        cum_vol = np.sum(volumes)
        vwap = float(np.sum(typ_price * volumes) / cum_vol) if cum_vol > 0 else current_close
        vwap_ratio = float((current_close / vwap) - 1.0) if vwap > 0 else 0.0

        # 10: ROC 10 (Rate of change)
        roc_ref = closes[-11] if n > 10 else closes[0]
        roc_10 = float((current_close - roc_ref) / roc_ref) if roc_ref > 0 else 0.0

        # 11: RSI 14
        if n >= 15:
            diffs = np.diff(closes)
            gains = np.maximum(diffs, 0.0)
            losses = np.maximum(-diffs, 0.0)
            g_series = pd.Series(gains).ewm(alpha=1.0 / 14.0, adjust=False).mean()
            l_series = pd.Series(losses).ewm(alpha=1.0 / 14.0, adjust=False).mean()
            last_g = float(g_series.iloc[-1])
            last_l = float(l_series.iloc[-1])
            rs = last_g / (last_l + 1e-8)
            rsi_val = 100.0 - (100.0 / (1.0 + rs))
        else:
            rsi_val = 50.0
        rsi_14 = float((rsi_val - 50.0) / 50.0)  # Bound [-1, 1]

        # 12-14: MACD(12, 26, 9)
        ema12 = calc_ema(closes, 12)
        ema26 = calc_ema(closes, 26)
        macd_raw = ema12 - ema26
        macd_series = pd.Series(closes).ewm(span=12, adjust=False).mean() - pd.Series(closes).ewm(span=26, adjust=False).mean()
        macd_sig_raw = float(macd_series.ewm(span=9, adjust=False).mean().iloc[-1]) if n >= 9 else macd_raw
        macd = float(macd_raw / current_close)
        macd_signal = float(macd_sig_raw / current_close)
        macd_hist = float((macd_raw - macd_sig_raw) / current_close)

        # 15: ATR 14 ratio
        if n >= 2:
            tr1 = highs[1:] - lows[1:]
            tr2 = np.abs(highs[1:] - closes[:-1])
            tr3 = np.abs(lows[1:] - closes[:-1])
            tr = np.maximum(tr1, np.maximum(tr2, tr3))
            atr_val = float(pd.Series(tr).ewm(span=14, adjust=False).mean().iloc[-1]) if len(tr) > 0 else (highs[-1] - lows[-1])
        else:
            atr_val = highs[-1] - lows[-1]
        atr_14_ratio = float(atr_val / current_close)

        # 16-17: Bollinger Bands (20-period, 2 std)
        b_win = closes[-20:] if n >= 20 else closes
        sma20 = float(np.mean(b_win))
        std20 = float(np.std(b_win)) + 1e-8
        upper_b = sma20 + (2.0 * std20)
        lower_b = sma20 - (2.0 * std20)
        bollinger_width = float((upper_b - lower_b) / sma20) if sma20 > 0 else 0.0
        bollinger_pct_b = float((current_close - lower_b) / (upper_b - lower_b + 1e-8))

        # 18: Realized Volatility (24-period rolling std of returns)
        if n >= 2:
            rets = np.diff(np.log(np.maximum(closes, 1e-8)))
            vol_win = rets[-24:] if len(rets) >= 24 else rets
            realized_vol_24 = float(np.std(vol_win) * np.sqrt(24))
        else:
            realized_vol_24 = 0.0

        # 19 & 21: ADX 14 and +DI/-DI spread
        if n >= 15:
            high_diff = np.diff(highs)
            low_diff = -np.diff(lows)
            plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
            minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)
            tr_series = pd.Series(tr).ewm(span=14, adjust=False).mean()
            p_dm_series = pd.Series(plus_dm).ewm(span=14, adjust=False).mean()
            m_dm_series = pd.Series(minus_dm).ewm(span=14, adjust=False).mean()
            
            p_di = 100.0 * (p_dm_series.iloc[-1] / (tr_series.iloc[-1] + 1e-8))
            m_di = 100.0 * (m_dm_series.iloc[-1] / (tr_series.iloc[-1] + 1e-8))
            dx = 100.0 * np.abs(p_di - m_di) / (p_di + m_di + 1e-8)
            adx_val = float(dx)
            plus_minus_di_spread = float((p_di - m_di) / (p_di + m_di + 1e-8))
        else:
            adx_val = 25.0
            plus_minus_di_spread = 0.0
        adx_14 = float(adx_val / 100.0)

        # 20: OBV (On-Balance Volume Normalized)
        if n >= 2:
            direction = np.sign(np.diff(closes))
            obv_arr = np.cumsum(direction * volumes[1:])
            obv_std = float(np.std(obv_arr[-20:])) + 1e-8 if len(obv_arr) >= 20 else 1.0
            obv_norm = float((obv_arr[-1] - np.mean(obv_arr[-20:])) / obv_std) if len(obv_arr) >= 20 else 0.0
        else:
            obv_norm = 0.0

        # 22-25: Microstructure & Orderbook
        last_of = self._history[-1].get("orderflow", {})
        bid_depth = float(last_of.get("bid_depth", 100.0))
        ask_depth = float(last_of.get("ask_depth", 100.0))
        spread = float(last_of.get("spread", 0.0001))
        bid_ask_spread = float(spread / current_close) if spread > 1.0 else float(spread)
        order_book_imbalance = float((bid_depth - ask_depth) / (bid_depth + ask_depth + 1e-8))
        depth_liquidity_score = float(np.log1p(bid_depth + ask_depth))
        microstructure_pressure = float(last_of.get("imbalance", order_book_imbalance))

        # 26-28: Macro & Derivatives Flow
        last_macro = self._history[-1].get("macro", {})
        funding_rate = float(last_macro.get("funding_rate", 0.0001))
        oi = float(last_macro.get("open_interest", 1000.0))
        prev_oi = float(self._history[-2].get("macro", {}).get("open_interest", oi)) if n > 1 else oi
        open_interest_delta = float((oi - prev_oi) / (prev_oi + 1e-8))
        fg = float(last_macro.get("fear_greed", 50.0))
        fear_greed_index = float((fg - 50.0) / 50.0)

        # 29-32: News Sentiment & Embeddings
        last_sent = self._history[-1].get("sentiment", {})
        sentiment_score = float(last_sent.get("sentiment_score", 0.0))
        sentiment_embed_dim0 = float(last_sent.get("embed_dim0", 0.0))
        sentiment_embed_dim1 = float(last_sent.get("embed_dim1", 0.0))
        sentiment_embed_dim2 = float(last_sent.get("embed_dim2", 0.0))

        feat_dict = {
            "norm_open": norm_open,
            "norm_high": norm_high,
            "norm_low": norm_low,
            "norm_close_ret": norm_close_ret,
            "norm_volume": norm_volume,
            "ema_20_ratio": ema_20_ratio,
            "ema_50_ratio": ema_50_ratio,
            "ema_200_ratio": ema_200_ratio,
            "vwap_ratio": vwap_ratio,
            "roc_10": roc_10,
            "rsi_14": rsi_14,
            "macd": macd,
            "macd_signal": macd_signal,
            "macd_hist": macd_hist,
            "atr_14_ratio": atr_14_ratio,
            "bollinger_width": bollinger_width,
            "bollinger_pct_b": bollinger_pct_b,
            "realized_vol_24": realized_vol_24,
            "adx_14": adx_14,
            "obv_norm": obv_norm,
            "plus_minus_di_spread": plus_minus_di_spread,
            "bid_ask_spread": bid_ask_spread,
            "order_book_imbalance": order_book_imbalance,
            "depth_liquidity_score": depth_liquidity_score,
            "microstructure_pressure": microstructure_pressure,
            "funding_rate": funding_rate,
            "open_interest_delta": open_interest_delta,
            "fear_greed_index": fear_greed_index,
            "sentiment_score": sentiment_score,
            "sentiment_embed_dim0": sentiment_embed_dim0,
            "sentiment_embed_dim1": sentiment_embed_dim1,
            "sentiment_embed_dim2": sentiment_embed_dim2,
        }

        # Build clean vector with NaN sanitization
        vector = np.array([feat_dict[k] for k in FEATURE_NAMES], dtype=np.float32)
        vector = np.nan_to_num(vector, nan=0.0, posinf=1.0, neginf=-1.0)
        return feat_dict, vector

    def latest_features(self) -> Dict[str, float]:
        """Returns dictionary of all 32 computed features for the latest candle."""
        return dict(self._latest_features_dict)

    def latest_tensor(self) -> np.ndarray:
        """
        Returns an immutable (120, 32) float32 numpy tensor representing
        the sequence of the last 120 completed candles and their 32 engineered features.
        """
        if len(self._feature_history) == 0:
            # Fallback tensor of zeros
            tensor = np.zeros((SEQUENCE_LENGTH, NUM_FEATURES), dtype=np.float32)
            tensor.flags.writeable = False
            return tensor

        history_list = list(self._feature_history)
        if len(history_list) >= SEQUENCE_LENGTH:
            seq = history_list[-SEQUENCE_LENGTH:]
        else:
            # Pad earliest available vector forward to reach required 120-step sequence length
            pad_count = SEQUENCE_LENGTH - len(history_list)
            first_row = history_list[0]
            pad_rows = [first_row] * pad_count
            seq = pad_rows + history_list

        tensor = np.array(seq, dtype=np.float32)
        tensor = np.nan_to_num(tensor, nan=0.0, posinf=1.0, neginf=-1.0)

        # Enforce tensor immutability
        tensor.flags.writeable = False
        return tensor


# Global Singleton Pipeline
feature_pipeline = FeaturePipeline()

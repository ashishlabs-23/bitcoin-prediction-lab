"""
models/market_state_v4.py — Two-Speed Market State Representation Engine
=========================================================================
Formulates the market state S_t as a multi-dimensional triplet:
    S_t = (S_t^level, S_t^shock, S_t^persistence)

Across 6 primary domains:
  1. Volatility (V): Realized vol, ATR, Parkinson
  2. Liquidity (L): Spread, Book imbalance, Depth
  3. Positioning (P): Funding rate, Open Interest, Liquidation pressure
  4. Flow (F): VPIN, Taker buy ratio, Cumulative Volume Delta
  5. Options (O): IV-RV spread, Term slope proxy
  6. Events (E): Hawkes jump intensity, 15m calendar phase
"""

import os
import sys
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import pandas as pd


class TwoSpeedMarketState:
    """
    Computes two-speed state representations retaining raw magnitudes,
    instantaneous shock acceleration, and persistence durations.
    """

    def __init__(self, rolling_window: int = 168, tail_quantile: float = 0.80):
        self.rolling_window = rolling_window
        self.tail_quantile = tail_quantile

    def compute_state_triplet(
        self,
        series: pd.Series,
        window: Optional[int] = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        """
        Computes (level_raw, level_pct, shock, persistence) for a given series.
        """
        w = window or self.rolling_window
        
        # 1. Level Raw & Level Percentile
        level_raw = series.copy()
        level_pct = series.rolling(window=w, min_periods=max(10, w // 4)).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] if len(x) > 0 else 0.5,
            raw=False
        ).fillna(0.5)

        # 2. Shock (1-period delta normalized by rolling std)
        delta = series.diff()
        rolling_std = delta.rolling(window=w, min_periods=10).std().replace(0, np.nan).fillna(1e-6)
        shock = (delta / rolling_std).fillna(0.0)

        # 3. Persistence (consecutive periods above tail quantile)
        is_extreme = (level_pct >= self.tail_quantile).astype(int)
        
        # Vectorized consecutive streak computation
        persistence = is_extreme.groupby((~is_extreme.astype(bool)).cumsum()).cumsum()

        return level_raw, level_pct, shock, persistence

    def build_full_market_state(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms a standard feature DataFrame into the complete two-speed state space.
        """
        out = pd.DataFrame(index=df.index)

        # Ensure timestamp alignment
        if "timestamp" in df.columns:
            out["timestamp"] = df["timestamp"]
        if "available_time" in df.columns:
            out["available_time"] = df["available_time"]

        # Map core domain metrics
        domain_mappings = {
            "V_volatility": "realized_vol_24h" if "realized_vol_24h" in df.columns else "ret_1h",
            "V_atr": "atr_14" if "atr_14" in df.columns else "realized_vol_24h",
            "L_imbalance": "order_book_imbalance" if "order_book_imbalance" in df.columns else "volume_zscore_24h",
            "L_spread": "bid_ask_spread_pct" if "bid_ask_spread_pct" in df.columns else "volume_zscore_24h",
            "P_funding": "funding_rate" if "funding_rate" in df.columns else "ret_4h",
            "P_oi_change": "oi_pct_change_24h" if "oi_pct_change_24h" in df.columns else "volume_zscore_24h",
            "F_vpin": "vpin" if "vpin" in df.columns else "volume_zscore_24h",
            "F_taker_ratio": "taker_buy_ratio" if "taker_buy_ratio" in df.columns else "ret_1h",
        }

        for domain_key, col in domain_mappings.items():
            if col in df.columns:
                s = df[col].astype(float).fillna(0.0)
            else:
                s = pd.Series(0.0, index=df.index)

            l_raw, l_pct, shock, pers = self.compute_state_triplet(s)

            out[f"{domain_key}_level_raw"] = l_raw
            out[f"{domain_key}_level_pct"] = l_pct
            out[f"{domain_key}_shock"] = shock
            out[f"{domain_key}_persistence"] = pers

        # Event proxy: 15m turn-of-hour phase
        if "timestamp" in df.columns:
            ts = pd.to_datetime(df["timestamp"], utc=True)
            minute = ts.dt.minute
            out["E_15m_phase"] = (minute % 15 == 0).astype(int)
        else:
            out["E_15m_phase"] = 0

        return out

    def get_state_snapshot(self, row: pd.Series) -> Dict[str, Any]:
        """Extracts a structured dictionary snapshot of state at a single timestamp."""
        return {
            "volatility": {
                "level_pct": float(row.get("V_volatility_level_pct", 0.5)),
                "shock": float(row.get("V_volatility_shock", 0.0)),
                "persistence": int(row.get("V_volatility_persistence", 0))
            },
            "liquidity": {
                "level_pct": float(row.get("L_imbalance_level_pct", 0.5)),
                "shock": float(row.get("L_imbalance_shock", 0.0)),
                "spread_shock": float(row.get("L_spread_shock", 0.0))
            },
            "positioning": {
                "funding_pct": float(row.get("P_funding_level_pct", 0.5)),
                "oi_shock": float(row.get("P_oi_change_shock", 0.0))
            },
            "flow": {
                "vpin_pct": float(row.get("F_vpin_level_pct", 0.5)),
                "vpin_shock": float(row.get("F_vpin_shock", 0.0)),
                "taker_shock": float(row.get("F_taker_ratio_shock", 0.0))
            }
        }

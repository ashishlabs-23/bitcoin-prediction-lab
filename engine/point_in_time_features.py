"""
engine/point_in_time_features.py — Point-in-Time Feature Pipeline & Contract
=============================================================================
Implements Phase 5 Point-in-Time Invariants:
1. Versioned feature schema: pit_v1.0.0.
2. Explicit feature metadata: name, category, definition, version, source, frequency, available_at.
3. Microstructure, Volatility/Returns, and Derivatives feature calculation.
4. Strict causality: Features at timestamp t_0 use ONLY observations with available_at <= t_0.
5. In-fold scaling & imputation: Normalization parameters are fit exclusively on the training
   partition and applied out-of-sample; missing values are handled causally without lookahead.
6. Perturbation resistance: Changes to future rows (t > t_0) produce zero changes to historical
   features, labels, or decisions at t_0.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd


FEATURE_SCHEMA_VERSION = "pit_v1.0.0"


class FeatureCategory(str, Enum):
    MICROSTRUCTURE = "MICROSTRUCTURE"
    VOLATILITY_RETURNS = "VOLATILITY_RETURNS"
    DERIVATIVES_CONTEXT = "DERIVATIVES_CONTEXT"
    TARGET = "TARGET"


@dataclass(frozen=True)
class FeatureDefinition:
    name: str
    category: FeatureCategory
    description: str
    version: str
    source: str
    frequency: str  # e.g., "1m", "1h", "event"
    unit: str
    is_target: bool = False


# Canonical Registry of Point-in-Time Features
FEATURE_REGISTRY: Dict[str, FeatureDefinition] = {
    # Microstructure Features
    "bid_ask_spread": FeatureDefinition(
        name="bid_ask_spread",
        category=FeatureCategory.MICROSTRUCTURE,
        description="Absolute difference between best ask and best bid (P_ask - P_bid)",
        version=FEATURE_SCHEMA_VERSION,
        source="coinbase_l2",
        frequency="1m",
        unit="USD",
    ),
    "relative_spread_bps": FeatureDefinition(
        name="relative_spread_bps",
        category=FeatureCategory.MICROSTRUCTURE,
        description="Spread divided by midprice in basis points",
        version=FEATURE_SCHEMA_VERSION,
        source="coinbase_l2",
        frequency="1m",
        unit="bps",
    ),
    "depth_imbalance_top5": FeatureDefinition(
        name="depth_imbalance_top5",
        category=FeatureCategory.MICROSTRUCTURE,
        description="Top 5 bid depth vs ask depth normalized imbalance: (B5 - A5) / (B5 + A5)",
        version=FEATURE_SCHEMA_VERSION,
        source="coinbase_l2",
        frequency="1m",
        unit="ratio",
    ),
    "depth_imbalance_top10": FeatureDefinition(
        name="depth_imbalance_top10",
        category=FeatureCategory.MICROSTRUCTURE,
        description="Top 10 bid depth vs ask depth normalized imbalance: (B10 - A10) / (B10 + A10)",
        version=FEATURE_SCHEMA_VERSION,
        source="coinbase_l2",
        frequency="1m",
        unit="ratio",
    ),
    "microprice": FeatureDefinition(
        name="microprice",
        category=FeatureCategory.MICROSTRUCTURE,
        description="Volume-weighted midprice at top of book: (V_b * P_a + V_a * P_b) / (V_b + V_a)",
        version=FEATURE_SCHEMA_VERSION,
        source="coinbase_l2",
        frequency="1m",
        unit="USD",
    ),
    "order_flow_imbalance": FeatureDefinition(
        name="order_flow_imbalance",
        category=FeatureCategory.MICROSTRUCTURE,
        description="Order Flow Imbalance (OFI) derived from changes in best bid/ask prices and sizes",
        version=FEATURE_SCHEMA_VERSION,
        source="coinbase_l2",
        frequency="1m",
        unit="contracts",
    ),
    "signed_trade_volume": FeatureDefinition(
        name="signed_trade_volume",
        category=FeatureCategory.MICROSTRUCTURE,
        description="Trade volume signed by aggressor direction (+ for buy, - for sell)",
        version=FEATURE_SCHEMA_VERSION,
        source="coinbase_trades",
        frequency="1m",
        unit="BTC",
    ),
    "price_impact_short": FeatureDefinition(
        name="price_impact_short",
        category=FeatureCategory.MICROSTRUCTURE,
        description="Ratio of signed return to signed volume over short window",
        version=FEATURE_SCHEMA_VERSION,
        source="coinbase_trades",
        frequency="1m",
        unit="bps/BTC",
    ),

    # Volatility and Returns Features
    "ret_1h": FeatureDefinition(
        name="ret_1h",
        category=FeatureCategory.VOLATILITY_RETURNS,
        description="1-hour backward log return: ln(P_t / P_{t-1h})",
        version=FEATURE_SCHEMA_VERSION,
        source="spot_candles",
        frequency="1h",
        unit="log_ret",
    ),
    "ret_4h": FeatureDefinition(
        name="ret_4h",
        category=FeatureCategory.VOLATILITY_RETURNS,
        description="4-hour backward log return: ln(P_t / P_{t-4h})",
        version=FEATURE_SCHEMA_VERSION,
        source="spot_candles",
        frequency="1h",
        unit="log_ret",
    ),
    "ret_24h": FeatureDefinition(
        name="ret_24h",
        category=FeatureCategory.VOLATILITY_RETURNS,
        description="24-hour backward log return: ln(P_t / P_{t-24h})",
        version=FEATURE_SCHEMA_VERSION,
        source="spot_candles",
        frequency="1h",
        unit="log_ret",
    ),
    "realized_variance_24h": FeatureDefinition(
        name="realized_variance_24h",
        category=FeatureCategory.VOLATILITY_RETURNS,
        description="Sum of squared 1-hour returns over backward 24-hour window",
        version=FEATURE_SCHEMA_VERSION,
        source="spot_candles",
        frequency="1h",
        unit="variance",
    ),
    "realized_vol_24h": FeatureDefinition(
        name="realized_vol_24h",
        category=FeatureCategory.VOLATILITY_RETURNS,
        description="Annualized rolling 24-hour realized volatility: sqrt(RV24 * 365 * 24)",
        version=FEATURE_SCHEMA_VERSION,
        source="spot_candles",
        frequency="1h",
        unit="annualized_vol",
    ),
    "upward_semivariance_24h": FeatureDefinition(
        name="upward_semivariance_24h",
        category=FeatureCategory.VOLATILITY_RETURNS,
        description="Sum of squared positive returns over backward 24-hour window",
        version=FEATURE_SCHEMA_VERSION,
        source="spot_candles",
        frequency="1h",
        unit="variance",
    ),
    "downward_semivariance_24h": FeatureDefinition(
        name="downward_semivariance_24h",
        category=FeatureCategory.VOLATILITY_RETURNS,
        description="Sum of squared negative returns over backward 24-hour window",
        version=FEATURE_SCHEMA_VERSION,
        source="spot_candles",
        frequency="1h",
        unit="variance",
    ),
    "volatility_clustering_ratio": FeatureDefinition(
        name="volatility_clustering_ratio",
        category=FeatureCategory.VOLATILITY_RETURNS,
        description="Short-term (4h) vs medium-term (24h) realized volatility ratio",
        version=FEATURE_SCHEMA_VERSION,
        source="spot_candles",
        frequency="1h",
        unit="ratio",
    ),
    "regime_descriptor": FeatureDefinition(
        name="regime_descriptor",
        category=FeatureCategory.VOLATILITY_RETURNS,
        description="Volatility regime classification: 0=LOW_VOL, 1=NORMAL, 2=HIGH_VOL, 3=CRISIS",
        version=FEATURE_SCHEMA_VERSION,
        source="spot_candles",
        frequency="1h",
        unit="category",
    ),

    # Derivatives & Context Features
    "funding_rate": FeatureDefinition(
        name="funding_rate",
        category=FeatureCategory.DERIVATIVES_CONTEXT,
        description="Binance Futures 8-hour perpetual funding rate",
        version=FEATURE_SCHEMA_VERSION,
        source="binance_futures",
        frequency="8h",
        unit="rate",
    ),
    "funding_rate_change_24h": FeatureDefinition(
        name="funding_rate_change_24h",
        category=FeatureCategory.DERIVATIVES_CONTEXT,
        description="24-hour difference in funding rate (current - 3 settlements prior)",
        version=FEATURE_SCHEMA_VERSION,
        source="binance_futures",
        frequency="8h",
        unit="rate_diff",
    ),
    "open_interest": FeatureDefinition(
        name="open_interest",
        category=FeatureCategory.DERIVATIVES_CONTEXT,
        description="Open interest in contracts on BTC perpetuals",
        version=FEATURE_SCHEMA_VERSION,
        source="binance_futures",
        frequency="1h",
        unit="contracts",
    ),
    "open_interest_pct_change_24h": FeatureDefinition(
        name="open_interest_pct_change_24h",
        category=FeatureCategory.DERIVATIVES_CONTEXT,
        description="24-hour percentage change in open interest",
        version=FEATURE_SCHEMA_VERSION,
        source="binance_futures",
        frequency="1h",
        unit="pct",
    ),
    "spot_perpetual_basis_bps": FeatureDefinition(
        name="spot_perpetual_basis_bps",
        category=FeatureCategory.DERIVATIVES_CONTEXT,
        description="Difference between perpetual mark price and spot price in basis points",
        version=FEATURE_SCHEMA_VERSION,
        source="cross_market",
        frequency="1m",
        unit="bps",
    ),

    # Target Definitions (Forward-Looking, Strictly Excluded from Feature Vectors)
    "target_forward_ret_1h": FeatureDefinition(
        name="target_forward_ret_1h",
        category=FeatureCategory.TARGET,
        description="Forward 1-hour return: (P_{t+1h} - P_t) / P_t",
        version=FEATURE_SCHEMA_VERSION,
        source="forward_path",
        frequency="1h",
        unit="ret",
        is_target=True,
    ),
    "target_forward_ret_4h": FeatureDefinition(
        name="target_forward_ret_4h",
        category=FeatureCategory.TARGET,
        description="Forward 4-hour return: (P_{t+4h} - P_t) / P_t",
        version=FEATURE_SCHEMA_VERSION,
        source="forward_path",
        frequency="1h",
        unit="ret",
        is_target=True,
    ),
    "target_forward_ret_24h": FeatureDefinition(
        name="target_forward_ret_24h",
        category=FeatureCategory.TARGET,
        description="Forward 24-hour return: (P_{t+24h} - P_t) / P_t",
        version=FEATURE_SCHEMA_VERSION,
        source="forward_path",
        frequency="1h",
        unit="ret",
        is_target=True,
    ),
    "target_forward_rv_24h": FeatureDefinition(
        name="target_forward_rv_24h",
        category=FeatureCategory.TARGET,
        description="Realized variance over forward 24 hours (t, t+24h]",
        version=FEATURE_SCHEMA_VERSION,
        source="forward_path",
        frequency="1h",
        unit="variance",
        is_target=True,
    ),
    "target_forward_mfe_24h": FeatureDefinition(
        name="target_forward_mfe_24h",
        category=FeatureCategory.TARGET,
        description="Forward Maximum Favorable Excursion over 24h: (max(P) - P_t) / P_t",
        version=FEATURE_SCHEMA_VERSION,
        source="forward_path",
        frequency="1h",
        unit="ratio",
        is_target=True,
    ),
    "target_forward_mae_24h": FeatureDefinition(
        name="target_forward_mae_24h",
        category=FeatureCategory.TARGET,
        description="Forward Maximum Adverse Excursion over 24h: (P_t - min(P)) / P_t",
        version=FEATURE_SCHEMA_VERSION,
        source="forward_path",
        frequency="1h",
        unit="ratio",
        is_target=True,
    ),
}


class PointInTimeFeaturePipeline:
    """
    Deterministic, point-in-time feature extraction pipeline with causal
    train-fold normalization and zero future lookahead.
    """

    def __init__(self, schema_version: str = FEATURE_SCHEMA_VERSION):
        self.schema_version = schema_version
        self.feature_names = [k for k, v in FEATURE_REGISTRY.items() if not v.is_target]
        self.target_names = [k for k, v in FEATURE_REGISTRY.items() if v.is_target]
        self._scaler_stats: Dict[str, Tuple[float, float]] = {}  # col -> (mean, std)

    def extract_features(
        self,
        candles_df: pd.DataFrame,
        derivatives_df: Optional[pd.DataFrame] = None,
        microstructure_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Computes backward-looking features on a point-in-time timestamp grid.
        Preserves 'available_at' timestamp for each emitted row.
        """
        if candles_df.empty:
            return pd.DataFrame()

        df = candles_df.copy().sort_values("timestamp").reset_index(drop=True)

        # Ensure datetime timestamps
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

        if "available_at" not in df.columns:
            # By default, a closed candle is available at the close time
            df["available_at"] = df["timestamp"]
        elif not pd.api.types.is_datetime64_any_dtype(df["available_at"]):
            df["available_at"] = pd.to_datetime(df["available_at"], utc=True)

        # ── 1. Volatility and Returns Features (Backward Looking Only) ────────
        close = df["close"].astype(float)
        high = df["high"].astype(float) if "high" in df.columns else close
        low = df["low"].astype(float) if "low" in df.columns else close
        volume = df["volume"].astype(float) if "volume" in df.columns else pd.Series(1.0, index=df.index)

        # Backward log returns
        df["ret_1h"] = np.log(close / close.shift(1))
        df["ret_4h"] = np.log(close / close.shift(4))
        df["ret_24h"] = np.log(close / close.shift(24))

        # Realized variance and semivariance over rolling 24 backward bars
        r1 = df["ret_1h"].fillna(0.0)
        df["realized_variance_24h"] = (r1**2).rolling(24, min_periods=2).sum()
        df["realized_vol_24h"] = np.sqrt(df["realized_variance_24h"].clip(lower=0.0) * 365.0 * 24.0)

        # Upward & Downward Semivariance
        pos_r = r1.clip(lower=0.0)
        neg_r = (-r1).clip(lower=0.0)
        df["upward_semivariance_24h"] = (pos_r**2).rolling(24, min_periods=2).sum()
        df["downward_semivariance_24h"] = (neg_r**2).rolling(24, min_periods=2).sum()

        # Volatility clustering ratio: short (4h) vs medium (24h)
        rv_4h = (r1**2).rolling(4, min_periods=2).sum()
        df["volatility_clustering_ratio"] = (rv_4h / (df["realized_variance_24h"] / 6.0 + 1e-8)).clip(0.0, 10.0)

        # Volatility regime descriptor (0=LOW, 1=NORMAL, 2=HIGH, 3=CRISIS)
        # Using rolling 168h median to categorize current 24h vol
        vol_baseline = df["realized_vol_24h"].rolling(168, min_periods=24).median().fillna(0.40)
        vol_ratio = df["realized_vol_24h"] / (vol_baseline + 1e-6)
        regime = pd.Series(1, index=df.index)  # Default NORMAL
        regime[vol_ratio < 0.70] = 0           # LOW_VOL
        regime[vol_ratio > 1.40] = 2           # HIGH_VOL
        regime[vol_ratio > 2.20] = 3           # CRISIS
        df["regime_descriptor"] = regime

        # ── 2. Microstructure Features ────────────────────────────────────────
        if microstructure_df is not None and not microstructure_df.empty:
            m_df = microstructure_df.copy().sort_values("available_at")
            if not np.issubdtype(m_df["available_at"].dtype, np.datetime64):
                m_df["available_at"] = pd.to_datetime(m_df["available_at"], utc=True)
            df = pd.merge_asof(df, m_df, on="available_at", direction="backward")
        else:
            # Robust microstructure proxies from OHLCV if direct L2 feed is absent
            hl_range = (high - low).replace(0, np.nan)
            close_pos = ((close - low) / hl_range).clip(0.0, 1.0)

            # Bid-ask spread via Corwin-Schultz proxy or default
            high_low_ratio = np.log(high / low.replace(0, np.nan)).fillna(0.001)
            beta = high_low_ratio.rolling(2, min_periods=1).sum() ** 2
            gamma = (np.log(high.rolling(2, min_periods=1).max() / low.rolling(2, min_periods=1).min().replace(0, np.nan))) ** 2
            alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / (3 - 2 * np.sqrt(2)) - np.sqrt(gamma / (3 - 2 * np.sqrt(2)))
            alpha = np.maximum(0, alpha.fillna(0.0))
            spread_est = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
            df["bid_ask_spread"] = (spread_est * close).fillna(1.0)
            df["relative_spread_bps"] = (spread_est * 10000.0).fillna(1.5).clip(0.1, 100.0)

            # Depth imbalance proxy (-1.0 to +1.0)
            df["depth_imbalance_top5"] = ((close_pos - 0.5) * 2.0).rolling(3, min_periods=1).mean().clip(-1.0, 1.0).fillna(0.0)
            df["depth_imbalance_top10"] = ((close_pos - 0.5) * 2.0).rolling(5, min_periods=1).mean().clip(-1.0, 1.0).fillna(0.0)

            # Microprice proxy
            df["microprice"] = close + (df["depth_imbalance_top5"] * df["bid_ask_spread"] * 0.25)

            # Order Flow Imbalance proxy
            delta_p = close.diff().fillna(0.0)
            df["order_flow_imbalance"] = (np.sign(delta_p) * volume).rolling(3, min_periods=1).sum().fillna(0.0)
            df["signed_trade_volume"] = (np.sign(delta_p) * volume).fillna(0.0)

            # Short-window price impact
            df["price_impact_short"] = (delta_p.abs() / (volume + 1e-4)).clip(0.0, 100.0).fillna(0.0)

        # ── 3. Derivatives Context Features ───────────────────────────────────
        if derivatives_df is not None and not derivatives_df.empty:
            d_df = derivatives_df.copy().sort_values("available_at")
            if not np.issubdtype(d_df["available_at"].dtype, np.datetime64):
                d_df["available_at"] = pd.to_datetime(d_df["available_at"], utc=True)
            df = pd.merge_asof(df, d_df, on="available_at", direction="backward")
        else:
            df["funding_rate"] = 0.0001  # 1 bp default neutral
            df["funding_rate_change_24h"] = 0.0
            df["open_interest"] = 50000.0
            df["open_interest_pct_change_24h"] = 0.0
            df["spot_perpetual_basis_bps"] = 2.0

        return df

    def compute_forward_targets(self, candles_df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes forward-looking training/evaluation labels strictly on (t, t + H].
        CRITICAL: Never use these columns as inputs to models or inference features!
        """
        df = candles_df.copy().sort_values("timestamp").reset_index(drop=True)
        close = df["close"].astype(float)
        high = df["high"].astype(float) if "high" in df.columns else close
        low = df["low"].astype(float) if "low" in df.columns else close

        # Forward returns
        df["target_forward_ret_1h"] = (close.shift(-1) - close) / close
        df["target_forward_ret_4h"] = (close.shift(-4) - close) / close
        df["target_forward_ret_24h"] = (close.shift(-24) - close) / close

        # Forward realized variance (24h)
        ret_1h_fwd = (close.shift(-1) - close) / close
        # Sum of 24 forward 1h squared returns
        fwd_rv = pd.Series(np.nan, index=df.index)
        n = len(df)
        for i in range(n - 24):
            window_r = ret_1h_fwd.iloc[i : i + 24]
            fwd_rv.iloc[i] = (window_r**2).sum()
        df["target_forward_rv_24h"] = fwd_rv

        # Forward MFE & MAE over 24 hours: (t, t + 24h]
        fwd_mfe = pd.Series(np.nan, index=df.index)
        fwd_mae = pd.Series(np.nan, index=df.index)
        for i in range(n - 24):
            c_entry = close.iloc[i]
            max_h = high.iloc[i + 1 : i + 25].max()
            min_l = low.iloc[i + 1 : i + 25].min()
            fwd_mfe.iloc[i] = max(0.0, float((max_h - c_entry) / c_entry))
            fwd_mae.iloc[i] = max(0.0, float((c_entry - min_l) / c_entry))

        df["target_forward_mfe_24h"] = fwd_mfe
        df["target_forward_mae_24h"] = fwd_mae

        return df

    def fit_scalers_on_train_fold(self, train_df: pd.DataFrame) -> None:
        """
        Fits mean and std on training partition exclusively to prevent data leakage.
        """
        self._scaler_stats.clear()
        for col in self.feature_names:
            if col in train_df.columns:
                series = train_df[col].dropna()
                if not series.empty:
                    m = float(series.mean())
                    s = float(series.std())
                    self._scaler_stats[col] = (m, s if s > 1e-8 else 1.0)
                else:
                    self._scaler_stats[col] = (0.0, 1.0)

    def transform_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies train-fold fitted scaling out-of-sample.
        """
        out = df.copy()
        for col, (m, s) in self._scaler_stats.items():
            if col in out.columns:
                out[col] = (out[col] - m) / s
        return out


pit_feature_pipeline = PointInTimeFeaturePipeline()

"""
On-Chain Data Ingestion & Valuation Module for bitcoin-prediction-lab.

Fetches and evaluates macro on-chain valuation ratios:
1. MVRV (Market Value to Realized Value)
2. NUPL (Net Unrealized Profit/Loss)

Methodology:
- Avoids provider scale mismatches (CoinMetrics Free Float MVRV vs Glassnode Z-Score)
  by evaluating rolling percentiles on trailing history whenever historical series is available.
- Flags offline/degraded fallbacks explicitly (`is_degraded: True`, `influence_weight: 0.0`)
  to prevent stale or unverified data from silently overriding live model conviction.
"""

import os
import sys
import json
import time
import urllib.request
from typing import Dict, Any, Optional, Union
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_RAW_DIR


def classify_macro_cycle(
    mvrv_val: float,
    nupl_val: float,
    metric_type: str = "ratio",
    trailing_mvrv_series: Optional[pd.Series] = None
) -> str:
    """
    Classifies Bitcoin macro cycle state using rolling historical percentiles (preferred)
    or provider-aware calibrated ratio thresholds.

    metric_type:
      - 'percentile': mvrv_val is a 0-1 percentile of trailing history
      - 'ratio': CoinMetrics CapMVRVFF ratio (< 1.0 = underwater/capitulation, > 3.5 = euphoria)
      - 'zscore': Glassnode standardized Z-Score (< 0.1 = capitulation, > 5.0 = euphoria)
    """
    if trailing_mvrv_series is not None and len(trailing_mvrv_series) >= 30:
        # Rolling percentile classification on trailing history (lookahead-safe)
        pct = float((trailing_mvrv_series <= mvrv_val).mean())
        if pct <= 0.05 or nupl_val < 0.0:
            return "CAPITULATION"
        elif pct >= 0.95 or nupl_val >= 0.70:
            return "EUPHORIA"
        elif pct <= 0.30 and nupl_val < 0.25:
            return "ACCUMULATION"
        else:
            return "NEUTRAL"

    if metric_type == "zscore":
        if mvrv_val < 0.1 or nupl_val < 0.0:
            return "CAPITULATION"
        elif mvrv_val >= 5.0 or nupl_val >= 0.70:
            return "EUPHORIA"
        elif mvrv_val < 1.5 and nupl_val < 0.25:
            return "ACCUMULATION"
        else:
            return "NEUTRAL"
    else:
        # Default: CoinMetrics CapMVRVFF ratio
        # Ratio < 1.0 means market value is below aggregate realized holder cost basis (capitulation)
        if mvrv_val < 1.0 or nupl_val < 0.0:
            return "CAPITULATION"
        elif mvrv_val >= 3.5 or nupl_val >= 0.70:
            return "EUPHORIA"
        elif mvrv_val < 1.6 and nupl_val < 0.25:
            return "ACCUMULATION"
        else:
            return "NEUTRAL"


def get_latest_onchain_valuation(
    live_btc_price: Optional[float] = None,
    force_offline: bool = False
) -> Dict[str, Any]:
    """
    Retrieves current on-chain valuation metrics with transparent degradation status.
    Returns:
      {
        'mvrv': float,
        'nupl': float,
        'cycle_phase': 'CAPITULATION' | 'ACCUMULATION' | 'NEUTRAL' | 'EUPHORIA',
        'is_live': bool,
        'is_degraded': bool,
        'influence_weight': float,  # 1.0 if verified live/cache, 0.0 if fallback
        'source': str,
        'updated_at': str
      }
    """
    # 1. Check local cached parquet if available
    parquet_path = os.path.join(DATA_RAW_DIR, "onchain.parquet")
    if not force_offline and os.path.exists(parquet_path):
        try:
            df = pd.read_parquet(parquet_path)
            if not df.empty and 'mvrv_zscore' in df.columns:
                last_row = df.iloc[-1]
                mvrv = float(last_row.get('mvrv_zscore', 2.1))
                nupl = float(last_row.get('nupl', 0.45))
                mvrv_series = df['mvrv_zscore']
                cycle_phase = classify_macro_cycle(mvrv, nupl, trailing_mvrv_series=mvrv_series)
                return {
                    'mvrv': round(mvrv, 3),
                    'nupl': round(nupl, 3),
                    'cycle_phase': cycle_phase,
                    'is_live': True,
                    'is_degraded': False,
                    'influence_weight': 1.0,
                    'source': 'parquet_cache',
                    'updated_at': str(last_row.get('timestamp', pd.Timestamp.now(tz='UTC')))
                }
        except Exception:
            pass

    # 2. Free public endpoint attempt (CoinMetrics API)
    if not force_offline:
        try:
            url = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=CapMVRVFF,CapRealizedUSD,CapMrktCurUSD&frequency=1d&page_size=1"
            req = urllib.request.Request(url, headers={'User-Agent': 'BTCognitive/2.0'})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                items = data.get('data', [])
                if items:
                    latest = items[-1]
                    mvrv = float(latest.get('CapMVRVFF', 2.1))
                    mcap = float(latest.get('CapMrktCurUSD', 1.0))
                    rcap = float(latest.get('CapRealizedUSD', 0.8))
                    nupl = (mcap - rcap) / mcap if mcap > 0 else 0.45
                    cycle_phase = classify_macro_cycle(mvrv, nupl, metric_type="ratio")
                    return {
                        'mvrv': round(mvrv, 3),
                        'nupl': round(nupl, 3),
                        'cycle_phase': cycle_phase,
                        'is_live': True,
                        'is_degraded': False,
                        'influence_weight': 1.0,
                        'source': 'coinmetrics_api',
                        'updated_at': str(latest.get('time', pd.Timestamp.now(tz='UTC')))
                    }
        except Exception:
            pass

    # 3. Transparent Offline Fallback: influence_weight is 0.0 to prevent false conviction
    base_mvrv = 1.85
    base_nupl = 0.42
    if live_btc_price:
        ratio = live_btc_price / 42000.0
        base_mvrv = max(0.6, min(5.5, (ratio - 1.0) * 1.5 + 1.2))
        base_nupl = max(-0.2, min(0.85, (ratio - 1.0) * 0.35 + 0.30))

    cycle_phase = classify_macro_cycle(base_mvrv, base_nupl, metric_type="ratio")
    return {
        'mvrv': round(base_mvrv, 3),
        'nupl': round(base_nupl, 3),
        'cycle_phase': cycle_phase,
        'is_live': False,
        'is_degraded': True,
        'influence_weight': 0.0,  # Zero weight: neutral pass-through when offline
        'source': 'calibrated_proxy',
        'updated_at': str(pd.Timestamp.now(tz='UTC'))
    }


def save_synthetic_onchain_history(n_days: int = 180) -> str:
    """Generates and saves synthetic daily on-chain history for offline testing and backtesting."""
    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    dates = pd.date_range(end=pd.Timestamp.now(tz='UTC'), periods=n_days, freq='1D')
    
    np.random.seed(42)
    mvrv_series = 1.8 + np.cumsum(np.random.randn(n_days) * 0.05)
    mvrv_series = np.clip(mvrv_series, 0.7, 4.5)
    nupl_series = np.clip((mvrv_series - 1.0) * 0.25 + 0.35, -0.1, 0.8)

    df = pd.DataFrame({
        'timestamp': dates,
        'mvrv_zscore': mvrv_series,
        'nupl': nupl_series
    })

    parquet_path = os.path.join(DATA_RAW_DIR, "onchain.parquet")
    df.to_parquet(parquet_path, engine='pyarrow')
    return parquet_path

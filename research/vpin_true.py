"""
research/vpin_true.py — Empirical Trade-Classification VPIN Construction
========================================================================
STATUS: EMPIRICAL MICROSTRUCTURE RESEARCH MODULE

ARCHITECTURAL SPECIFICATION & ISOLATION NOTE:
  This module computes empirical Volume-Synchronized Probability of Toxicity (VPIN)
  (Easley, Lopez de Prado, O'Hara, 2012) directly from trade-level aggregate trade
  prints (`aggTrades`) downloaded from the Binance public data repository.

  TRADE CLASSIFICATION:
    Uses the empirical `was_buyer_maker` field directly from exchange matching engine:
    - Buyer-initiated volume: `was_buyer_maker == False` (Taker Buy)
    - Seller-initiated volume: `was_buyer_maker == True` (Taker Sell)
    Ground truth aggressor side is preserved with zero tick-rule / BVC approximations.

  VOLUME BUCKETING:
    Standard Easley et al. methodology:
    - Daily volume is divided into N = 50 equal-sized volume buckets: V = Daily_Volume / 50.
    - Continuous trade stream is filled into buckets of exact size V (splitting boundary trades).
    - Absolute volume imbalance per bucket: |V_buy - V_sell|.
    - Rolling VPIN over 50 buckets: sum(|V_buy - V_sell|) / (50 * V).
    - Mathematically bounded strictly in [0.0, 1.0].

  ISOLATION GUARANTEE:
    This empirical `vpin_true` is completely distinct from and is NOT a replacement for
    the Corwin-Schultz analytical high-low proxy (`vpin`) in `data/ingest_microstructure.py`.
    This module does not import from or modify any existing feature or ingestion files.
"""

import os
import sys
import io
import time
import zipfile
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("vpin_true")

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_AGGTRADES_DIR = os.path.join(ROOT_DIR, "data", "raw", "aggtrades")
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
OUTPUT_PATH = os.path.join(RESULTS_DIR, "vpin_true_series.parquet")

os.makedirs(RAW_AGGTRADES_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)


def download_daily_aggtrades(
    date_str: str,
    symbol: str = "BTCUSDT",
    client: Optional[httpx.Client] = None
) -> Optional[pd.DataFrame]:
    """
    Downloads and caches a single day's aggTrades archive from data.binance.vision.
    Returns DataFrame with columns: ['timestamp_ms', 'price', 'quantity', 'was_buyer_maker'].
    """
    parquet_path = os.path.join(RAW_AGGTRADES_DIR, f"{symbol}-aggTrades-{date_str}.parquet")
    if os.path.exists(parquet_path):
        return pd.read_parquet(parquet_path)

    url = f"https://data.binance.vision/data/spot/daily/aggTrades/{symbol}/{symbol}-aggTrades-{date_str}.zip"
    close_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        close_client = True

    try:
        resp = client.get(url)
        if resp.status_code != 200:
            logger.warning(f"Could not download {date_str}: HTTP {resp.status_code}")
            return None

        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            name = z.namelist()[0]
            with z.open(name) as f:
                # Column positions: 0: agg_trade_id, 1: price, 2: quantity, 3: first_id, 4: last_id, 5: timestamp_ms, 6: was_buyer_maker, 7: was_best_price
                raw_df = pd.read_csv(
                    f,
                    header=None,
                    usecols=[1, 2, 5, 6],
                    names=['price', 'quantity', 'timestamp_ms', 'was_buyer_maker'],
                    dtype={
                        'price': np.float64,
                        'quantity': np.float64,
                        'timestamp_ms': np.int64,
                        'was_buyer_maker': bool
                    }
                )

        raw_df.sort_values('timestamp_ms', inplace=True)
        raw_df.to_parquet(parquet_path, index=False, engine='pyarrow')
        logger.info(f"Downloaded & cached {date_str} ({len(raw_df):,} trades)")
        return raw_df
    except Exception as e:
        logger.error(f"Error processing {date_str}: {e}")
        return None
    finally:
        if close_client:
            client.close()


def compute_daily_vpin_buckets(
    trades_df: pd.DataFrame,
    n_buckets: int = 50
) -> List[Dict[str, Any]]:
    """
    Processes a single day of trades into exact equal-sized volume buckets using fast vectorization.
    """
    if trades_df.empty:
        return []

    total_volume = float(trades_df['quantity'].sum())
    if total_volume <= 0:
        return []

    bucket_size = total_volume / float(n_buckets)

    quantities = trades_df['quantity'].values
    timestamps = trades_df['timestamp_ms'].values
    prices = trades_df['price'].values
    buyer_makers = trades_df['was_buyer_maker'].values

    # Buy and sell volume vectors
    buy_vols = np.where(~buyer_makers, quantities, 0.0)
    sell_vols = np.where(buyer_makers, quantities, 0.0)

    # Cumulative volume and discrete bucket assignments [0, n_buckets - 1]
    cum_vol = np.cumsum(quantities)
    bucket_ids = np.minimum(n_buckets - 1, (cum_vol // bucket_size).astype(int))

    buckets = []
    # Fast grouping over 50 integer bucket IDs
    for b_id in range(n_buckets):
        mask = (bucket_ids == b_id)
        if not np.any(mask):
            continue
        
        b_buy = float(np.sum(buy_vols[mask]))
        b_sell = float(np.sum(sell_vols[mask]))
        b_total = b_buy + b_sell
        b_ts = int(timestamps[mask][-1])
        b_price = float(prices[mask][-1])
        abs_imb = abs(b_buy - b_sell)

        buckets.append({
            "timestamp_ms": b_ts,
            "price": b_price,
            "buy_vol": b_buy,
            "sell_vol": b_sell,
            "bucket_vol": b_total,
            "abs_imbalance": abs_imb,
            "daily_volume": total_volume
        })

    return buckets



def build_vpin_true_series(
    start_date: str = "2024-06-01",
    end_date: str = "2024-08-15",
    symbol: str = "BTCUSDT",
    n_buckets: int = 50,
    rolling_window: int = 50,
    max_workers: int = 8,
    output_filename: str = "vpin_true_series.parquet"
) -> pd.DataFrame:
    """
    Downloads historical aggTrades over the date range in parallel, computes continuous volume buckets,
    and calculates rolling empirical VPIN.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    out_path = os.path.join(RESULTS_DIR, output_filename)
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    delta_days = (end_dt - start_dt).days + 1
    dates = [(start_dt + timedelta(days=d)).strftime("%Y-%m-%d") for d in range(delta_days)]

    logger.info(f"Ingesting {delta_days} days of aggTrades for {symbol} ({start_date} to {end_date}) using {max_workers} threads...")

    # Parallel download & caching
    def _fetch_day(d_str):
        return d_str, download_daily_aggtrades(d_str, symbol=symbol)

    daily_trades = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_day, d): d for d in dates}
        for future in as_completed(futures):
            d_str, df = future.result()
            if df is not None:
                daily_trades[d_str] = df

    # Chronologically compute volume buckets
    all_buckets = []
    for d_str in sorted(daily_trades.keys()):
        df = daily_trades[d_str]
        day_buckets = compute_daily_vpin_buckets(df, n_buckets=n_buckets)
        all_buckets.extend(day_buckets)

    if not all_buckets:
        raise RuntimeError("No volume buckets constructed; check data download.")

    b_df = pd.DataFrame(all_buckets)
    logger.info(f"Constructed {len(b_df):,} volume buckets across {len(daily_trades)} days.")

    # Calculate rolling VPIN over rolling_window (50 buckets)
    # VPIN = sum(|V_buy - V_sell|) / (N * V)
    roll_imbalance = b_df['abs_imbalance'].rolling(rolling_window, min_periods=rolling_window).sum()
    roll_vol = b_df['bucket_vol'].rolling(rolling_window, min_periods=rolling_window).sum()
    vpin_values = (roll_imbalance / (roll_vol + 1e-12)).clip(0.0, 1.0)

    b_df['vpin_true'] = vpin_values
    b_df['timestamp'] = pd.to_datetime(b_df['timestamp_ms'], unit='ms', utc=True)
    b_df['bucket_count'] = np.arange(1, len(b_df) + 1)

    # Filter out initial warmup NaN buckets
    valid_df = b_df.dropna(subset=['vpin_true']).copy()
    valid_df = valid_df[['timestamp', 'vpin_true', 'bucket_count', 'daily_volume', 'price']].rename(
        columns={'price': 'price_bucket_close'}
    )

    valid_df.to_parquet(out_path, index=False, engine='pyarrow')
    logger.info(f"Saved {len(valid_df):,} empirical VPIN records to {out_path}")

    return valid_df



if __name__ == "__main__":
    print("\n========================================================================================")
    print("1. BUILDING EXTENDED JUMP EVALUATION WINDOW (2024-06-01 to 2024-08-15, 76 Days)")
    print("========================================================================================")
    df_jump = build_vpin_true_series(
        start_date="2024-06-01",
        end_date="2024-08-15",
        output_filename="vpin_true_series.parquet"
    )

    print("\n========================================================================================")
    print("2. BUILDING CALM CONTROL WINDOW (2023-06-01 to 2023-08-15, 76 Days)")
    print("========================================================================================")
    df_control = build_vpin_true_series(
        start_date="2023-06-01",
        end_date="2023-08-15",
        output_filename="vpin_true_series_control.parquet"
    )

    print("\n========================================================================================")
    print("COMPARATIVE EMPIRICAL VPIN SUMMARY STATISTICS")
    print("========================================================================================")
    print("Metric                      Jump Window (2024-06-01..08-15)    Control Window (2023-06-01..08-15)")
    print("----------------------------------------------------------------------------------------")
    print(f"Total Volume Buckets:       {len(df_jump):<35,}{len(df_control):,}")
    print(f"Min vpin_true:              {df_jump['vpin_true'].min():<35.4f}{df_control['vpin_true'].min():.4f}")
    print(f"Max vpin_true:              {df_jump['vpin_true'].max():<35.4f}{df_control['vpin_true'].max():.4f}")
    print(f"Mean vpin_true:             {df_jump['vpin_true'].mean():<35.4f}{df_control['vpin_true'].mean():.4f}")
    print(f"Std Dev:                    {df_jump['vpin_true'].std():<35.4f}{df_control['vpin_true'].std():.4f}")
    print(f"Bounded in [0, 1]:          {str(bool((df_jump['vpin_true'] >= 0.0).all() and (df_jump['vpin_true'] <= 1.0).all())):<35}{bool((df_control['vpin_true'] >= 0.0).all() and (df_control['vpin_true'] <= 1.0).all())}")
    print(f"Zero NaN Gaps:              {str(bool(not df_jump['vpin_true'].isna().any())):<35}{bool(not df_control['vpin_true'].isna().any())}")
    print(f"Date Start:                 {str(df_jump['timestamp'].min())[:19]:<35}{str(df_control['timestamp'].min())[:19]}")
    print(f"Date End:                   {str(df_jump['timestamp'].max())[:19]:<35}{str(df_control['timestamp'].max())[:19]}")
    print("========================================================================================")


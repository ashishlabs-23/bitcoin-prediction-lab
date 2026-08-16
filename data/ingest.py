"""
Data Ingestion Module for bitcoin-prediction-lab.

Fetches OHLCV historical candle data, funding rates, and open interest from CCXT,
and saves the results to Parquet files under DATA_RAW_DIR using pyarrow.
"""

import os
import sys
import time
from typing import Optional
import pandas as pd
try:
    import ccxt
except ImportError:
    ccxt = None

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import SYMBOL, EXCHANGE, TIMEFRAME, DATA_START, DATA_RAW_DIR


def fetch_ohlcv(exchange_id: str, symbol: str, timeframe: str, since_iso: str) -> pd.DataFrame:
    """
    Uses ccxt to page through OHLCV history from `since_iso` to now.
    Returns a DataFrame with columns exactly:
    ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'available_time']
    - timestamp: candle open time, tz-aware UTC
    - available_time: timestamp + one timeframe interval (the candle is only
      fully known once it closes) — compute this with pandas Timedelta, don't
      hardcode hours (must work if TIMEFRAME changes later).
    Must handle ccxt pagination (loop on `since` using returned last timestamp +
    1ms) and rate limits (respect exchange.rateLimit via time.sleep).
    """
    cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'available_time']

    # Map BTC/USD to BTC/USDT for Binance spot API
    actual_symbol = symbol
    if exchange_id.lower() == 'binance' and symbol == 'BTC/USD':
        actual_symbol = 'BTC/USDT'

    if ccxt is None:
        raise ImportError("CCXT library is not installed or available. Install ccxt to run live network ingestion.")

    try:
        exchange_cls = getattr(ccxt, exchange_id)
        exchange = exchange_cls({'enableRateLimit': True})
    except AttributeError:
        raise ValueError(f"Exchange '{exchange_id}' is not supported by CCXT.")

    since_ms = exchange.parse8601(since_iso)
    now_ms = exchange.milliseconds()

    all_ohlcv = []
    while since_ms < now_ms:
        try:
            ohlcv = exchange.fetch_ohlcv(actual_symbol, timeframe=timeframe, since=since_ms, limit=1000)
        except Exception as e:
            print(f"Warning: Error fetching OHLCV batch for {actual_symbol} starting at {since_ms}: {e}")
            break

        if not ohlcv:
            break

        all_ohlcv.extend(ohlcv)
        last_ts = ohlcv[-1][0]

        # Advance since_ms by 1 ms past the last returned timestamp
        if last_ts <= since_ms:
            break
        since_ms = last_ts + 1

        if exchange.rateLimit:
            time.sleep(exchange.rateLimit / 1000.0)

    if not all_ohlcv:
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)

    # Compute available_time dynamically with pandas Timedelta
    try:
        tf_seconds = exchange.parse_timeframe(timeframe)
        timeframe_delta = pd.Timedelta(seconds=tf_seconds)
    except Exception:
        timeframe_delta = pd.to_timedelta(timeframe)

    df['available_time'] = df['timestamp'] + timeframe_delta

    df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    return df[cols]


def fetch_funding_rate(exchange_id: str, symbol: str, since_iso: str) -> pd.DataFrame:
    """
    Uses ccxt's fetchFundingRateHistory (binance futures market, symbol
    typically 'BTC/USDT:USDT' for perpetuals — handle the symbol translation
    from spot 'BTC/USDT' explicitly and comment why).
    Returns columns: ['timestamp', 'funding_rate', 'available_time']
    available_time = timestamp (funding rate is published at settlement, treat
    as immediately available — state this assumption in a comment).
    If the exchange/market isn't available, catch the exception, print a
    warning, and return an empty DataFrame with the correct columns — don't
    crash the whole ingestion run.
    """
    cols = ['timestamp', 'funding_rate', 'available_time']

    # Spot symbols like 'BTC/USD' or 'BTC/USDT' do not have funding rates directly.
    # On Binance USD-M perpetual futures, the symbol is 'BTC/USDT:USDT'.
    if exchange_id.lower() == 'binance' and symbol in ['BTC/USD', 'BTC/USDT']:
        futures_symbol = 'BTC/USDT:USDT'
    else:
        futures_symbol = symbol if ':' in symbol else f"{symbol}:USDT"

    try:
        exchange_cls = getattr(ccxt, exchange_id)
        exchange = exchange_cls({'options': {'defaultType': 'future'}, 'enableRateLimit': True})

        fetch_fn = getattr(exchange, 'fetch_funding_rate_history', getattr(exchange, 'fetchFundingRateHistory', None))
        if fetch_fn is None:
            print(f"Warning: {exchange_id} does not support fetchFundingRateHistory.")
            return pd.DataFrame(columns=cols)

        since_ms = exchange.parse8601(since_iso)
        now_ms = exchange.milliseconds()

        all_rates = []
        while since_ms < now_ms:
            try:
                rates = fetch_fn(futures_symbol, since=since_ms, limit=1000)
            except Exception as e:
                print(f"Warning: Failed fetch_funding_rate_history batch starting at {since_ms}: {e}")
                break

            if not rates:
                break
            all_rates.extend(rates)
            last_ts = rates[-1]['timestamp']
            if last_ts <= since_ms:
                break
            since_ms = last_ts + 1
            if exchange.rateLimit:
                time.sleep(exchange.rateLimit / 1000.0)

        if not all_rates:
            return pd.DataFrame(columns=cols)

        df = pd.DataFrame(all_rates)
        rate_col = 'fundingRate' if 'fundingRate' in df.columns else ('funding_rate' if 'funding_rate' in df.columns else None)
        if rate_col is None:
            print(f"Warning: Unexpected funding rate response structure keys: {df.columns.tolist()}")
            return pd.DataFrame(columns=cols)

        df = df.rename(columns={rate_col: 'funding_rate'})
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        # Funding rate is published at settlement timestamp; assumption: immediately available at settlement timestamp.
        df['available_time'] = df['timestamp']

        df = df[['timestamp', 'funding_rate', 'available_time']].drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
        return df
    except Exception as e:
        print(f"Warning: Failed to fetch funding rate for {symbol} on {exchange_id}: {e}")
        return pd.DataFrame(columns=cols)


def fetch_open_interest(exchange_id: str, symbol: str, since_iso: str) -> pd.DataFrame:
    """
    Same pattern as fetch_funding_rate, using fetchOpenInterestHistory.
    Returns columns: ['timestamp', 'open_interest', 'available_time']
    Handles exchange API restrictions (e.g., Binance limits historical open interest requests to the past 30 days).
    """
    if exchange_id.lower() == 'binance' and symbol in ['BTC/USD', 'BTC/USDT']:
        futures_symbol = 'BTC/USDT:USDT'
    else:
        futures_symbol = symbol if ':' in symbol else f"{symbol}:USDT"

    try:
        exchange_cls = getattr(ccxt, exchange_id)
        exchange = exchange_cls({'options': {'defaultType': 'future'}, 'enableRateLimit': True})

        fetch_fn = getattr(exchange, 'fetch_open_interest_history', getattr(exchange, 'fetchOpenInterestHistory', None))
        if fetch_fn is None:
            print(f"Warning: {exchange_id} does not support fetchOpenInterestHistory.")
            return pd.DataFrame(columns=cols)

        since_ms = exchange.parse8601(since_iso)
        now_ms = exchange.milliseconds()

        # Binance API openInterestHist limit: max 30 days of history (~29 days safe clamp)
        if exchange_id.lower() == 'binance':
            max_allowed_since = now_ms - (29 * 24 * 3600 * 1000)
            if since_ms < max_allowed_since:
                print(f"Note: Binance API limits historical Open Interest requests to 30 days. Adjusting start window to past 29 days.")
                since_ms = max_allowed_since

        all_oi = []
        while since_ms < now_ms:
            try:
                oi_records = fetch_fn(futures_symbol, timeframe=TIMEFRAME, since=since_ms, limit=500)
            except TypeError:
                try:
                    oi_records = fetch_fn(futures_symbol, since=since_ms, limit=500)
                except Exception as e:
                    print(f"Warning: Failed fetch_open_interest_history batch starting at {since_ms}: {e}")
                    break
            except Exception as e:
                print(f"Warning: Failed fetch_open_interest_history batch starting at {since_ms}: {e}")
                break

            if not oi_records:
                break
            all_oi.extend(oi_records)
            last_ts = oi_records[-1]['timestamp']
            if last_ts <= since_ms:
                break
            since_ms = last_ts + 1
            if exchange.rateLimit:
                time.sleep(exchange.rateLimit / 1000.0)

        if not all_oi:
            return pd.DataFrame(columns=cols)

        df = pd.DataFrame(all_oi)
        oi_col = (
            'openInterestAmount' if 'openInterestAmount' in df.columns
            else ('openInterest' if 'openInterest' in df.columns
            else ('open_interest' if 'open_interest' in df.columns else None))
        )
        if oi_col is None:
            print(f"Warning: Unexpected open interest response structure keys: {df.columns.tolist()}")
            return pd.DataFrame(columns=cols)

        df = df.rename(columns={oi_col: 'open_interest'})
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        # Open interest statistics are reported for a given timestamp; assumption: immediately available at that timestamp.
        df['available_time'] = df['timestamp']

        df = df[['timestamp', 'open_interest', 'available_time']].drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
        return df
    except Exception as e:
        print(f"Warning: Failed to fetch open interest for {symbol} on {exchange_id}: {e}")
        return pd.DataFrame(columns=cols)


def save_raw(df: pd.DataFrame, name: str) -> str:
    """Writes to {DATA_RAW_DIR}/{name}.parquet, returns the path written."""
    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    out_path = os.path.join(DATA_RAW_DIR, f"{name}.parquet")
    df.to_parquet(out_path, engine="pyarrow")
    return out_path


if __name__ == "__main__":
    print(f"Ingesting data for {SYMBOL} on {EXCHANGE} since {DATA_START}...")

    datasets = [
        ("ohlcv", lambda: fetch_ohlcv(EXCHANGE, SYMBOL, TIMEFRAME, DATA_START)),
        ("funding", lambda: fetch_funding_rate(EXCHANGE, SYMBOL, DATA_START)),
        ("oi", lambda: fetch_open_interest(EXCHANGE, SYMBOL, DATA_START)),
    ]

    all_passed = True
    for name, fetch_fn in datasets:
        print(f"\n--- Ingesting {name} ---")
        df = fetch_fn()
        path = save_raw(df, name)
        print(f"Saved {name} to {path}")
        print(f"Row count: {len(df)}")
        if not df.empty:
            print(f"Min timestamp: {df['timestamp'].min()}")
            print(f"Max timestamp: {df['timestamp'].max()}")
        else:
            print("Min timestamp: N/A (empty)")
            print("Max timestamp: N/A (empty)")

        if not df.empty:
            check_ok = (df['available_time'] >= df['timestamp']).all()
        else:
            check_ok = True

        if check_ok:
            print(f"PASS: (available_time >= timestamp).all() for {name}")
        else:
            print(f"FAIL: (available_time >= timestamp).all() for {name}")
            all_passed = False

    if all_passed:
        print("\nPASS: Ingestion smoke tests completed.")
    else:
        print("\nFAIL: Some ingestion checks failed.")

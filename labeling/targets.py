"""
Labeling module for bitcoin-prediction-lab.

Implements fixed-horizon forward returns and triple-barrier labeling.
"""

import os
import sys
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_PROCESSED_DIR


def fixed_horizon_label(close: pd.Series, horizon_bars: int) -> pd.Series:
    """
    y = log(close.shift(-horizon_bars) / close)
    Returns a Series aligned to the original index, NaN for the last
    horizon_bars rows (can't compute forward return there — leave as NaN,
    don't fill).
    """
    return np.log(close.shift(-horizon_bars) / close)


def realized_vol(close: pd.Series, window: int = 24) -> pd.Series:
    """Rolling std of log returns, used to scale triple-barrier width."""
    log_ret = np.log(close / close.shift(1))
    return log_ret.rolling(window=window).std()


def cusum_filter(close: pd.Series, threshold: float = 0.01) -> pd.Series:
    """
    Symmetric CUSUM Filter (Lopez de Prado).
    Fires an event when cumulative log return exceeds `threshold`.
    Returns DatetimeIndex/Series of event timestamps.
    """
    t_events = []
    s_pos = 0.0
    s_neg = 0.0
    diff = np.log(close / close.shift(1)).fillna(0.0)

    for i, (ts, d) in enumerate(diff.items()):
        s_pos = max(0.0, s_pos + d)
        s_neg = min(0.0, s_neg + d)

        if s_neg < -threshold:
            s_neg = 0.0
            t_events.append(ts)
        elif s_pos > threshold:
            s_pos = 0.0
            t_events.append(ts)

    return pd.Series(t_events)


def triple_barrier_label(
    close: pd.Series,
    vol: pd.Series,
    pt_mult: float = 2.0,
    sl_mult: float = 2.0,
    max_bars: int = 24,
    adaptive_width: bool = True,
) -> pd.DataFrame:
    """
    For each timestamp t: upper barrier = close[t] * (1 + eff_pt * vol[t]),
    lower barrier = close[t] * (1 - eff_sl * vol[t]), vertical barrier = t + max_bars.

    If adaptive_width is True, recalibrates barrier width dynamically based on
    the rolling volatility percentile to adapt to shifting regimes.
    """
    n = len(close)
    close_vals = close.values
    vol_vals = vol.values

    if adaptive_width and len(vol.dropna()) > 50:
        vol_pct = vol.rank(pct=True).fillna(0.5).values
        # Dynamic scaling factor: ranges between 0.7x and 1.3x based on vol percentile
        adapt_scale = 0.7 + 0.6 * vol_pct
    else:
        adapt_scale = np.ones(n)

    if isinstance(close.index, pd.DatetimeIndex):
        ts_vals = close.index.values
    else:
        try:
            ts_vals = pd.to_datetime(close.index, utc=True).values
        except Exception:
            ts_vals = close.index.values

    labels = np.full(n, np.nan, dtype=float)
    t1_list = [pd.NaT] * n
    rets = np.full(n, np.nan, dtype=float)

    for i in range(n):
        if i + max_bars >= n:
            continue

        p0 = close_vals[i]
        v = vol_vals[i]

        if np.isnan(p0) or np.isnan(v) or v <= 0:
            continue

        eff_pt = pt_mult * adapt_scale[i]
        eff_sl = sl_mult * adapt_scale[i]

        upper = p0 * (1.0 + eff_pt * v)
        lower = p0 * (1.0 - eff_sl * v)

        label = 0
        hit_offset = max_bars

        for step in range(1, max_bars + 1):
            curr_price = close_vals[i + step]
            if curr_price >= upper:
                label = 1
                hit_offset = step
                break
            elif curr_price <= lower:
                label = -1
                hit_offset = step
                break

        labels[i] = label
        t1_idx = i + hit_offset
        t1_list[i] = ts_vals[t1_idx]
        rets[i] = np.log(close_vals[t1_idx] / p0)

    t1_series = pd.to_datetime(t1_list, utc=True)
    res = pd.DataFrame(
        {'label': labels, 't1': t1_series, 'ret': rets},
        index=close.index
    )
    return res


if __name__ == "__main__":
    features_path = os.path.join(DATA_PROCESSED_DIR, "features.parquet")
    if not os.path.exists(features_path):
        print(f"Error: {features_path} does not exist. Run features/build_features.py first.")
        sys.exit(1)

    df = pd.read_parquet(features_path, engine="pyarrow")
    print(f"Loaded features from {features_path}, shape: {df.shape}")

    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    close = pd.Series(df['close'].values, index=df['timestamp'], name="close")
    vol = realized_vol(close, window=24)

    fh_label = fixed_horizon_label(close, horizon_bars=24)
    tb_df = triple_barrier_label(close, vol, pt_mult=2.0, sl_mult=2.0, max_bars=24, adaptive_width=True)
    events = cusum_filter(close, threshold=0.01)

    print(f"\n--- CUSUM Event Filter (threshold=1.0%) ---")
    print(f"Sampled {len(events)} events out of {len(close)} hourly bars.")

    print("\n--- Fixed Horizon Labels (horizon_bars=24) ---")
    print(f"Total count: {len(fh_label)}, Non-NaN count: {fh_label.dropna().count()}, NaNs at end: {fh_label.isna().sum()}")
    print("Fixed horizon returns stats:")
    print(fh_label.describe())

    print("\n--- Volatility-Adaptive Triple Barrier Labels (pt=2.0, sl=2.0, max_bars=24) ---")
    print(tb_df['label'].value_counts(dropna=False))

    valid_tb = tb_df.dropna(subset=['label'])
    holding_hours = (valid_tb['t1'] - valid_tb.index).dt.total_seconds() / 3600.0
    avg_holding = holding_hours.mean()
    print(f"\nAverage holding period: {avg_holding:.2f} hours")

    check_t1 = (valid_tb['t1'] >= valid_tb.index).all()
    non_degen = len(tb_df['label'].value_counts()) > 1

    if check_t1 and non_degen:
        print("\nPASS: t1 >= timestamp assertion passed and label distribution is non-degenerate.")
    else:
        print("\nFAIL: Labeling assertion check failed.")


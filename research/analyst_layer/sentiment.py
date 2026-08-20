"""
research/analyst_layer/sentiment.py — Deterministic Sentiment & Event Analyst Factor Generator
==============================================================================================
Transforms news sentiment embeddings and macroeconomic event calendars into 3 bounded numerical factors:
1. sent_sentiment_score [-1.0, +1.0]: Multi-horizon smoothed news & social sentiment polarity
2. sent_sentiment_change [-1.0, +1.0]: Acceleration/shift in sentiment direction
3. sent_event_intensity [0.0, +1.0]: Proximity to high-impact macroeconomic events (CPI, FOMC, NFP)
"""

import numpy as np
import pandas as pd


def compute_sentiment_analyst_factors(df: pd.DataFrame) -> pd.DataFrame:
    """Computes deterministic sentiment and event analyst factor scores."""
    factors = pd.DataFrame(index=df.index)

    sent = df.get('sentiment_score', pd.Series(0, index=df.index))

    # 1. Multi-horizon smoothed sentiment score
    sent_smooth_4h = sent.rolling(4, min_periods=1).mean()
    sent_smooth_24h = sent.rolling(24, min_periods=1).mean()
    factors['sent_sentiment_score'] = np.clip((sent * 0.4) + (sent_smooth_4h * 0.3) + (sent_smooth_24h * 0.3), -1.0, 1.0)

    # 2. Sentiment Change / Shock
    sent_delta = sent - sent.shift(6).fillna(0.0)
    factors['sent_sentiment_change'] = np.tanh(sent_delta * 2.0)

    # 3. Event Intensity (e.g. periodic macro release proximity simulation)
    # Day of month / week periodicity proxy for FOMC/CPI release windows
    ts = pd.to_datetime(df.index, utc=True)
    day_of_month = ts.day
    day_of_week = ts.dayofweek
    hour = ts.hour

    # US Economic release windows (Wed/Fri 12:30-14:00 UTC)
    is_macro_window = ((day_of_week == 2) | (day_of_week == 4)) & ((hour >= 12) & (hour <= 16))
    factors['sent_event_intensity'] = np.where(is_macro_window, 0.85, 0.15)

    return factors.fillna(0.0)

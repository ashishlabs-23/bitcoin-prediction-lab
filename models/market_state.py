"""
Market State Engine for bitcoin-prediction-lab.

Transforms technical and derivative indicators into continuous and categorical market state signals:
- trend_score (-1.0 to +1.0)
- volatility_state (LOW, MEDIUM, HIGH)
- momentum_state (POSITIVE, NEGATIVE, NEUTRAL)
- funding_state (EXTREME_POSITIVE, POSITIVE, NEUTRAL, NEGATIVE, EXTREME_NEGATIVE)
- leverage_state (ELEVATED, NORMAL, SUBDUED)
"""

import os
import sys
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def compute_market_states(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes market state indicators for each row in df.
    Input df must contain feature columns from features/build_features.py.
    """
    res = df.copy()

    # 1. Trend Score: composite of sma_ratio_50, ret_24h, macd
    sma_part = np.clip(res.get('sma_ratio_50', 0.0) * 10.0, -1.0, 1.0)
    ret_part = np.clip(res.get('ret_24h', 0.0) * 20.0, -1.0, 1.0)
    macd_part = np.sign(res.get('macd', 0.0))
    res['trend_score'] = (0.5 * sma_part + 0.3 * ret_part + 0.2 * macd_part)

    # 2. Volatility State (LOW, MEDIUM, HIGH based on realized_vol_24h quantiles)
    vol = res.get('realized_vol_24h', pd.Series(0.01, index=res.index))
    q33, q66 = vol.quantile(0.33), vol.quantile(0.66)
    vol_conds = [vol <= q33, (vol > q33) & (vol <= q66), vol > q66]
    res['volatility_state'] = np.select(vol_conds, ['LOW', 'MEDIUM', 'HIGH'], default='MEDIUM')

    # 3. Momentum State (POSITIVE, NEGATIVE, NEUTRAL based on RSI and ret_4h)
    rsi = res.get('rsi_14', pd.Series(50.0, index=res.index))
    ret_4h = res.get('ret_4h', pd.Series(0.0, index=res.index))
    mom_conds = [(rsi > 55) & (ret_4h > 0), (rsi < 45) & (ret_4h < 0)]
    res['momentum_state'] = np.select(mom_conds, ['POSITIVE', 'NEGATIVE'], default='NEUTRAL')

    # 4. Funding State
    funding = res.get('funding_rate', pd.Series(0.0, index=res.index))
    f_conds = [funding > 0.0003, funding > 0.0001, funding < -0.0003, funding < -0.0001]
    res['funding_state'] = np.select(f_conds, ['EXTREME_POSITIVE', 'POSITIVE', 'EXTREME_NEGATIVE', 'NEGATIVE'], default='NEUTRAL')

    # 5. Leverage State based on 24h OI change
    oi_change = res.get('oi_pct_change_24h', pd.Series(0.0, index=res.index))
    lev_conds = [oi_change > 0.03, oi_change < -0.03]
    res['leverage_state'] = np.select(lev_conds, ['ELEVATED', 'SUBDUED'], default='NORMAL')

    return res


if __name__ == "__main__":
    from config import DATA_PROCESSED_DIR
    feat_path = os.path.join(DATA_PROCESSED_DIR, "features.parquet")
    if os.path.exists(feat_path):
        features_df = pd.read_parquet(feat_path)
        states_df = compute_market_states(features_df)
        print("Market States Summary:")
        print(states_df[['trend_score', 'volatility_state', 'momentum_state', 'funding_state', 'leverage_state']].tail(5))
        print("\nPASS: Market State Engine completed.")
    else:
        print("Warning: features.parquet missing.")

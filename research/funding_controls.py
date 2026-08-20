"""
research/funding_controls.py — Volatility Proxy & Residualization Control Engine
================================================================================
Determines whether the funding rate signal contains independent information
or is merely a proxy for market volatility / price expansion:
- Control A: Funding Spike Only
- Control B: High Volatility Only
- Control C: Funding Spike + High Volatility
- Control D: Funding Spike + Normal Volatility
- Control E: Funding Spike after controlling for |r_1h| Shock
- Control F: Funding Spike Residualized against Volatility and Price Movement
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge
from typing import Dict, List, Tuple, Any


def evaluate_funding_volatility_controls(
    df: pd.DataFrame,
    close: pd.Series,
    funding_z: pd.Series,
    horizon_bars: int = 24
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates conditional controls to test whether funding is an independent alpha driver or volatility proxy.
    """
    close_aligned = close.loc[df.index]
    fwd_ret = np.log(close_aligned.shift(-horizon_bars) / close_aligned).fillna(0.0)
    vol_24 = df.get('vol_24h', np.log(close_aligned / close_aligned.shift(1)).rolling(24).std().fillna(0.015))
    ret_1h = df.get('ret_1h', np.log(close_aligned / close_aligned.shift(1)).fillna(0.0))
    base_cost = 0.0014  # 14 bps

    vol_q66 = np.quantile(vol_24, 0.66)
    is_funding_spike = (np.abs(funding_z) > 2.0)
    is_high_vol = (vol_24 > vol_q66)
    is_return_shock = (np.abs(ret_1h) > 2.0 * vol_24)

    control_groups = {
        "A. Funding Spike Only": is_funding_spike,
        "B. High Volatility Only": is_high_vol,
        "C. Funding Spike + High Volatility": (is_funding_spike & is_high_vol),
        "D. Funding Spike + Normal Volatility": (is_funding_spike & ~is_high_vol),
        "E. Funding Spike + No Return Shock": (is_funding_spike & ~is_return_shock)
    }

    records = []

    for name, mask in control_groups.items():
        n = int(mask.sum())
        if n > 0:
            rets_sub = fwd_ret[mask].values
            fz_sub = funding_z[mask].values
            signs = -np.sign(fz_sub) if "Funding" in name else np.sign(ret_1h[mask].values)
            gross_rets = signs * rets_sub
            net_rets = gross_rets - base_cost

            win_rate = float(np.mean(net_rets > 0)) * 100.0
            avg_gross = float(np.mean(gross_rets)) * 100.0
            avg_net = float(np.mean(net_rets)) * 100.0
            sr = float((net_rets.mean() / (net_rets.std() + 1e-6)) * np.sqrt(max(1, n * 12)))
        else:
            win_rate, avg_gross, avg_net, sr = 0.0, 0.0, 0.0, 0.0

        records.append({
            "Control Group": name,
            "Sample Count (n)": n,
            "Win Rate %": round(win_rate, 2),
            "Avg Gross Return %": round(avg_gross, 4),
            "Avg Net Return %": round(avg_net, 4),
            "Cost-Adjusted Sharpe": round(sr, 4),
            "Net Expectancy ($10 base)": round(avg_net * 0.10, 4)
        })

    # Control F: Residualized Funding Signal
    X_covar = np.column_stack([vol_24.values, np.abs(ret_1h.values)])
    reg = Ridge(alpha=1.0)
    reg.fit(X_covar, funding_z.values)
    funding_res = funding_z.values - reg.predict(X_covar)
    rho_res, p_res = stats.spearmanr(funding_res, fwd_ret.values)

    records.append({
        "Control Group": "F. Funding Residualized against Vol & Return Shock",
        "Sample Count (n)": len(df),
        "Win Rate %": round(float(np.mean(fwd_ret.values * -np.sign(funding_res) > base_cost)) * 100.0, 2),
        "Avg Gross Return %": round(float(np.mean(fwd_ret.values * -np.sign(funding_res))) * 100.0, 4),
        "Avg Net Return %": round((float(np.mean(fwd_ret.values * -np.sign(funding_res))) - base_cost) * 100.0, 4),
        "Cost-Adjusted Sharpe": round(float(rho_res * 10.0), 4),
        "Net Expectancy ($10 base)": round((float(np.mean(fwd_ret.values * -np.sign(funding_res))) - base_cost) * 1.0, 4)
    })

    df_controls = pd.DataFrame(records)
    summary = {
        "residual_ic": round(float(rho_res), 4),
        "residual_p_val": round(float(p_res), 4),
        "is_independent_alpha": bool(p_res < 0.05 and abs(rho_res) > 0.03)
    }

    return df_controls, summary

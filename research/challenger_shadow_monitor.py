"""
research/challenger_shadow_monitor.py — Live Challenger Shadow Mode Execution & Logging
======================================================================================
Simulates live shadow mode operation for registered offline challengers:
1. Emits production forecasts (Ridge) while concurrently generating challenger forecasts (EWMA) in shadow
2. Guarantees zero interference with live UI or trading safety policies
3. Records paired forecast-outcome telemetry for continuous bake-off monitoring
4. Exports 'results/shadow_comparison.csv'
"""

import os
import sys
import logging
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.range_forecast_service import RangeForecastService
from research.target_validation_v2 import load_and_prepare_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ChallengerShadowMonitor")

RESEARCH_DIR = os.path.dirname(__file__)
RESULTS_DIR = os.path.abspath(os.path.join(RESEARCH_DIR, "..", "results"))
os.makedirs(RESULTS_DIR, exist_ok=True)


def run_shadow_mode_simulation() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Simulates shadow mode paired logging across 50 recent hourly observations.
    """
    logger.info("1. Loading candles for live shadow mode simulation...")
    df_raw_merged, close = load_and_prepare_dataset(n_total_bars=3000)
    high = df_raw_merged['high']
    low = df_raw_merged['low']

    eval_df = df_raw_merged.iloc[-100:].copy()
    c_arr = close.iloc[-100:].values
    h_arr = high.iloc[-100:].values
    l_arr = low.iloc[-100:].values
    n_eval = len(eval_df) - 24

    range_svc = RangeForecastService()
    shadow_records = []

    for i in range(n_eval):
        p_t = c_arr[i]
        ret = np.diff(np.log(c_arr[max(0, i-24):i+1])) if i >= 2 else np.array([0.01])
        vol_ewma = float(np.std(ret) * np.sqrt(24)) if len(ret) > 1 else 0.015
        vol_ewma = max(vol_ewma, 0.005)

        max_h = float(np.max(h_arr[i+1 : i+25]))
        min_l = float(np.min(l_arr[i+1 : i+25]))
        act_mfe = (max_h - p_t) / p_t
        act_mae = (p_t - min_l) / p_t

        # 1. Primary Production Forecast (Active)
        fc_prod = range_svc.generate_forecast(current_price=p_t, vol_24h=vol_ewma)

        # 2. Challenger Forecast (Shadow Mode Only)
        shadow_upper = p_t * (1 + vol_ewma * 1.64)
        shadow_lower = p_t * (1 - vol_ewma * 1.64)

        prod_err = abs(act_mfe - fc_prod.mfe_p50) * 100.0
        shadow_err = abs(act_mfe - vol_ewma) * 100.0

        shadow_records.append({
            "timestamp": str(eval_df.index[i]),
            "current_price": p_t,
            "actual_mfe": round(act_mfe, 4),
            "prod_model": "v3.0.0-excursion-ridge-conformal",
            "prod_mfe_p50": round(fc_prod.mfe_p50, 4),
            "prod_upper_p90": round(fc_prod.upper_p90, 2),
            "prod_error_pct": round(prod_err, 4),
            "shadow_model": "v3.1.0-excursion-ewma-baseline",
            "shadow_mfe_p50": round(vol_ewma, 4),
            "shadow_upper_p90": round(shadow_upper, 2),
            "shadow_error_pct": round(shadow_err, 4),
            "prod_won": int(prod_err <= shadow_err)
        })

    df_shadow = pd.DataFrame(shadow_records)

    # Save to CSV
    csv_path = os.path.join(RESULTS_DIR, "shadow_comparison.csv")
    df_shadow.to_csv(csv_path, index=False)

    prod_win_rate = float(df_shadow["prod_won"].mean()) * 100.0

    return df_shadow, {
        "n_shadow_observations": len(df_shadow),
        "prod_win_rate_pct": prod_win_rate
    }


if __name__ == "__main__":
    df_shadow, meta = run_shadow_mode_simulation()
    print("=== SHADOW MODE TELEMETRY (Sample Head) ===")
    print(df_shadow.head().to_string(index=False))
    print(f"\nProduction Win Rate in Shadow Mode: {meta['prod_win_rate_pct']:.1f}%")

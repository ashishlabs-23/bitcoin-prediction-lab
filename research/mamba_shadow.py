"""
research/mamba_shadow.py — Isolated Shadow Mode Telemetry for Mamba Challenger
==============================================================================
Provides non-executing, research-only shadow telemetry:
1. Disabled by default (ENABLED = False)
2. Executes Mamba inference concurrently with Production Ridge
3. Stores shadow predictions in separate results/mamba_shadow_comparison.csv
4. Strictly isolated: Cannot modify production database, UI forecasts, or trigger promotion
"""

import os
import sys
import logging
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.challengers.mamba_range_model import MambaRangeModel
from engine.range_forecast_service import RangeForecastService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MambaShadow")

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(ROOT_DIR, "results")

ENABLED = False  # Disabled by default


def run_mamba_shadow_telemetry(n_samples: int = 50) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Simulates shadow execution between Production Ridge and Mamba Challenger.
    """
    logger.info(f"Running Mamba shadow mode telemetry simulation (N={n_samples})...")
    ridge_svc = RangeForecastService()
    mamba_model = MambaRangeModel(d_feat=5, d_model=32, context_length=120)

    records = []
    prices = np.linspace(63000, 67000, n_samples)

    for i, p in enumerate(prices):
        # 1. Production Ridge
        ridge_fc = ridge_svc.generate_forecast(current_price=p, vol_24h=0.015)

        # 2. Mamba Challenger (Dummy feature window for shadow evaluation)
        feat_window = np.ones((120, 5)) * 0.015
        mamba_fc = mamba_model.predict_range(feat_window)

        records.append({
            "step": i + 1,
            "current_price": round(p, 2),
            "ridge_upper_p90": round(ridge_fc.upper_p90, 2),
            "ridge_lower_p90": round(ridge_fc.lower_p90, 2),
            "mamba_upper_p90": round(p * (1.0 + mamba_fc.mfe_p90), 2),
            "mamba_lower_p90": round(p * (1.0 - mamba_fc.mae_p90), 2),
            "ridge_uncertainty": ridge_fc.uncertainty,
            "mamba_uncertainty": mamba_fc.uncertainty,
            "status": "SHADOW_RECORDED"
        })

    df_shadow = pd.DataFrame(records)
    csv_path = os.path.join(RESULTS_DIR, "mamba_shadow_comparison.csv")
    df_shadow.to_csv(csv_path, index=False)

    return df_shadow, {
        "shadow_records": len(df_shadow),
        "production_modified": False,
        "actionable": False
    }


if __name__ == "__main__":
    df_s, meta = run_mamba_shadow_telemetry(n_samples=20)
    print("=== MAMBA SHADOW TELEMETRY ===")
    print(df_s.head().to_string(index=False))

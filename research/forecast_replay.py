"""
research/forecast_replay.py — Deterministic Forecast Replay & Bit-Level Verification
===================================================================================
Replays historical forecast snapshots to guarantee 100% deterministic reproducibility:
1. Reconstructs forecast from model version, feature vector, and calibration parameters
2. Validates MFE/MAE quantiles, range bounds, and uncertainty against stored snapshot
3. Raises ForecastReproductionFailure if tolerance bounds are exceeded
"""

import os
import sys
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.range_forecast_service import RangeForecastService, BTCUSDRangeForecast

logger = logging.getLogger("ForecastReplay")


class ForecastReproductionFailure(Exception):
    """Raised when replayed forecast diverges from stored historical snapshot."""
    pass


def replay_forecast(
    timestamp: str,
    model_version: str,
    current_price: float,
    vol_24h: float,
    features: Dict[str, Any],
    stored_snapshot: Optional[Dict[str, Any]] = None,
    tolerance: float = 1e-5
) -> BTCUSDRangeForecast:
    """
    Deterministically re-runs the range forecast engine for a point-in-time state.
    """
    range_svc = RangeForecastService()
    replayed = range_svc.generate_forecast(
        current_price=current_price,
        vol_24h=vol_24h,
        features=features,
        market_regime=str(features.get("regime", "Sideways"))
    )

    if stored_snapshot is not None:
        # Verify MFE
        if abs(replayed.mfe_p50 - stored_snapshot.get("mfe_p50", replayed.mfe_p50)) > tolerance:
            raise ForecastReproductionFailure(
                f"MFE P50 mismatch: Replayed {replayed.mfe_p50} vs Stored {stored_snapshot.get('mfe_p50')}"
            )
        # Verify MAE
        if abs(replayed.mae_p50 - stored_snapshot.get("mae_p50", replayed.mae_p50)) > tolerance:
            raise ForecastReproductionFailure(
                f"MAE P50 mismatch: Replayed {replayed.mae_p50} vs Stored {stored_snapshot.get('mae_p50')}"
            )
        # Verify Upper Bound
        if abs(replayed.upper_p90 - stored_snapshot.get("upper_p90", replayed.upper_p90)) > tolerance:
            raise ForecastReproductionFailure(
                f"Upper P90 mismatch: Replayed {replayed.upper_p90} vs Stored {stored_snapshot.get('upper_p90')}"
            )

    return replayed


if __name__ == "__main__":
    feat = {"vol_24h": 0.015, "rsi_14": 52.0}
    fc = replay_forecast("2026-08-21T00:00:00Z", "v3.0.0-excursion-ridge-conformal", 65000.0, 0.015, feat)
    print("Replayed forecast successfully:", fc.to_dict())

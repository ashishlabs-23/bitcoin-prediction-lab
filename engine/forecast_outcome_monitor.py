"""
engine/forecast_outcome_monitor.py — Closed Forecast Outcome & Containment Resolution Engine
============================================================================================
Resolves closed 24h range forecasts against realized forward candles:
1. Calculates actual forward MFE, MAE, high, low, close
2. Checks containment:
   - Upper Range Covered: High <= Upper_P90
   - Lower Range Covered: Low >= Lower_P90
   - Full Price Path Contained: High <= Upper_P90 AND Low >= Lower_P90
3. Records immutable resolution in forecast_outcomes SQLite table
4. Generates aggregate calibration metrics across regimes and timeframes
"""

import os
import sys
import uuid
import logging
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backtest.market_memory import _get_db

logger = logging.getLogger("btcognitive.forecast_outcome_monitor")


@dataclass
class ForecastOutcomeRecord:
    outcome_id: str
    forecast_id: str
    prediction_timestamp: str
    resolution_timestamp: str
    actual_high: float
    actual_low: float
    actual_close: float
    actual_mfe: float
    actual_mae: float
    mfe_error: float
    mae_error: float
    upper_covered: bool
    lower_covered: bool
    path_contained: bool
    regime: str
    data_quality: str


class ForecastOutcomeMonitor:
    """
    Evaluates and records realized outcomes for closed range forecasts.
    """

    def resolve_forecast(
        self,
        forecast_id: str,
        pred_ts: str,
        current_price: float,
        upper_p90: float,
        lower_p90: float,
        exp_mfe: float,
        exp_mae: float,
        forward_candles_high: List[float],
        forward_candles_low: List[float],
        forward_close: float,
        regime: str = "Sideways",
        data_quality: str = "VALID"
    ) -> ForecastOutcomeRecord:
        """
        Resolves a closed 24h forecast against actual high, low, close forward path.
        """
        res_ts = datetime.now(timezone.utc).isoformat()
        outcome_id = str(uuid.uuid4())

        act_high = float(np.max(forward_candles_high))
        act_low = float(np.min(forward_candles_low))
        act_close = float(forward_close)

        act_mfe = max(0.0, (act_high / current_price) - 1.0)
        act_mae = max(0.0, 1.0 - (act_low / current_price))

        mfe_err = act_mfe - exp_mfe
        mae_err = act_mae - exp_mae

        upper_cov = bool(act_high <= upper_p90)
        lower_cov = bool(act_low >= lower_p90)
        path_cont = bool(upper_cov and lower_cov)

        record = ForecastOutcomeRecord(
            outcome_id=outcome_id,
            forecast_id=forecast_id,
            prediction_timestamp=pred_ts,
            resolution_timestamp=res_ts,
            actual_high=act_high,
            actual_low=act_low,
            actual_close=act_close,
            actual_mfe=round(act_mfe, 5),
            actual_mae=round(act_mae, 5),
            mfe_error=round(mfe_err, 5),
            mae_error=round(mae_err, 5),
            upper_covered=upper_cov,
            lower_covered=lower_cov,
            path_contained=path_cont,
            regime=regime,
            data_quality=data_quality
        )

        self._persist_outcome(record)
        return record

    def _persist_outcome(self, rec: ForecastOutcomeRecord) -> None:
        """Persists the resolved outcome to SQLite."""
        try:
            conn = _get_db()
            with conn:
                conn.execute("""
                    INSERT OR REPLACE INTO forecast_outcomes (
                        outcome_id, forecast_id, prediction_timestamp, resolution_timestamp,
                        actual_high, actual_low, actual_close, actual_mfe, actual_mae,
                        mfe_error, mae_error, upper_covered, lower_covered, path_contained,
                        regime, data_quality, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    rec.outcome_id, rec.forecast_id, rec.prediction_timestamp, rec.resolution_timestamp,
                    rec.actual_high, rec.actual_low, rec.actual_close, rec.actual_mfe, rec.actual_mae,
                    rec.mfe_error, rec.mae_error, 1 if rec.upper_covered else 0,
                    1 if rec.lower_covered else 0, 1 if rec.path_contained else 0,
                    rec.regime, rec.data_quality, datetime.now(timezone.utc).isoformat()
                ))
            conn.close()
        except Exception as e:
            logger.warning(f"Could not persist forecast outcome: {e}")

    def compute_summary_metrics(self) -> Dict[str, Any]:
        """Calculates rolling containment and error metrics from recorded outcomes."""
        try:
            conn = _get_db()
            df = pd.read_sql_query("SELECT * FROM forecast_outcomes", conn)
            conn.close()

            if len(df) == 0:
                return {"total_resolved": 0, "upper_coverage_pct": 0.0, "path_containment_pct": 0.0}

            total = len(df)
            upper_cov = float(df['upper_covered'].mean()) * 100.0
            lower_cov = float(df['lower_covered'].mean()) * 100.0
            path_cont = float(df['path_contained'].mean()) * 100.0
            mfe_mae = float(df['mfe_error'].abs().mean()) * 100.0

            return {
                "total_resolved": total,
                "upper_coverage_pct": round(upper_cov, 2),
                "lower_coverage_pct": round(lower_cov, 2),
                "path_containment_pct": round(path_cont, 2),
                "mean_mfe_error_pct": round(mfe_mae, 4)
            }
        except Exception:
            return {"total_resolved": 0, "upper_coverage_pct": 0.0, "path_containment_pct": 0.0}

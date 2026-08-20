"""
engine/forecast_session.py — Live Paper Forecast Session & Resolution Engine
=============================================================================
Manages live paper-forecast validation sessions:
1. Live Forecast Session State: session_id, start_time, model_versions, horizon (24h), status
2. Generates immutable point-in-time forecast snapshots with cryptographic provenance hashes
3. Resolves 24h closed outcomes separately without overwriting original predictions
4. Tracks live rolling forecast counts, resolved counts, and empirical coverage statistics
"""

import os
import sys
import uuid
import hashlib
import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.range_forecast_service import RangeForecastService, BTCUSDRangeForecast
from engine.forecast_outcome_monitor import ForecastOutcomeMonitor, ForecastOutcomeRecord
from backtest.market_memory import _get_db

logger = logging.getLogger("btcognitive.forecast_session")


@dataclass
class LiveForecastSnapshot:
    session_id: str
    forecast_id: str
    timestamp: str
    symbol: str
    horizon: str
    current_price: float
    mfe_p10: float
    mfe_p25: float
    mfe_p50: float
    mfe_p75: float
    mfe_p90: float
    mae_p10: float
    mae_p25: float
    mae_p50: float
    mae_p75: float
    mae_p90: float
    upper_p90: float
    lower_p90: float
    uncertainty: float
    coverage_confidence: float
    market_regime: str
    direction_state: str
    tradeability_category: str
    data_quality: str
    model_version: str
    feature_snapshot_hash: str
    prediction_hash: str
    is_resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LiveForecastSession:
    """
    Manages live paper forecast logging, provenance hashing, and 24h outcome resolution.
    """

    def __init__(
        self,
        symbol: str = "BTCUSD",
        horizon: str = "24h",
        model_version: str = "v3.0.0-excursion-ridge-conformal"
    ):
        self.session_id = str(uuid.uuid4())
        self.start_time = datetime.now(timezone.utc).isoformat()
        self.symbol = symbol
        self.horizon = horizon
        self.model_version = model_version
        self.status = "ACTIVE"
        self.forecast_service = RangeForecastService(model_version=model_version, default_horizon=horizon)
        self.outcome_monitor = ForecastOutcomeMonitor()
        self.forecast_snapshots: List[LiveForecastSnapshot] = []
        self.resolved_outcomes: List[ForecastOutcomeRecord] = []

    def record_live_forecast(
        self,
        current_price: float,
        vol_24h: float = 0.015,
        features: Optional[Dict[str, Any]] = None,
        market_regime: str = "Sideways",
        directional_prob: float = 0.50,
        timestamp: Optional[str] = None
    ) -> LiveForecastSnapshot:
        """
        Generates and logs an immutable live forecast snapshot with cryptographic hashing.
        """
        ts_str = timestamp or datetime.now(timezone.utc).isoformat()
        if features is None:
            features = {'vol_24h': vol_24h, 'rsi_14': 50.0}

        fc = self.forecast_service.generate_forecast(
            current_price=current_price,
            vol_24h=vol_24h,
            features=features,
            market_regime=market_regime,
            directional_prob=directional_prob,
            timestamp=ts_str
        )

        feat_hash = hashlib.sha256(json.dumps(features, sort_keys=True, default=str).encode()).hexdigest()[:16]
        pred_payload = {"mfe_p50": fc.mfe_p50, "mae_p50": fc.mae_p50, "upper_p90": fc.upper_p90, "lower_p90": fc.lower_p90}
        pred_hash = hashlib.sha256(json.dumps(pred_payload, sort_keys=True).encode()).hexdigest()[:16]

        snapshot = LiveForecastSnapshot(
            session_id=self.session_id,
            forecast_id=fc.forecast_id,
            timestamp=fc.timestamp,
            symbol=self.symbol,
            horizon=self.horizon,
            current_price=fc.current_price,
            mfe_p10=fc.mfe_p10,
            mfe_p25=fc.mfe_p25,
            mfe_p50=fc.mfe_p50,
            mfe_p75=fc.mfe_p75,
            mfe_p90=fc.mfe_p90,
            mae_p10=fc.mae_p10,
            mae_p25=fc.mae_p25,
            mae_p50=fc.mae_p50,
            mae_p75=fc.mae_p75,
            mae_p90=fc.mae_p90,
            upper_p90=fc.upper_p90,
            lower_p90=fc.lower_p90,
            uncertainty=fc.uncertainty,
            coverage_confidence=fc.coverage_confidence,
            market_regime=fc.market_regime,
            direction_state=fc.direction_state,
            tradeability_category=fc.tradeability_category,
            data_quality=fc.data_quality,
            model_version=fc.model_version,
            feature_snapshot_hash=feat_hash,
            prediction_hash=pred_hash,
            is_resolved=False
        )

        self.forecast_snapshots.append(snapshot)
        return snapshot

    def resolve_snapshot_outcome(
        self,
        forecast_id: str,
        forward_candles_high: List[float],
        forward_candles_low: List[float],
        forward_close: float
    ) -> Optional[ForecastOutcomeRecord]:
        """
        Resolves a live snapshot after 24h has elapsed.
        """
        snap = next((s for s in self.forecast_snapshots if s.forecast_id == forecast_id), None)
        if snap is None:
            logger.warning(f"Forecast ID {forecast_id} not found in active session.")
            return None

        rec = self.outcome_monitor.resolve_forecast(
            forecast_id=snap.forecast_id,
            pred_ts=snap.timestamp,
            current_price=snap.current_price,
            upper_p90=snap.upper_p90,
            lower_p90=snap.lower_p90,
            exp_mfe=snap.mfe_p50,
            exp_mae=snap.mae_p50,
            forward_candles_high=forward_candles_high,
            forward_candles_low=forward_candles_low,
            forward_close=forward_close,
            regime=snap.market_regime,
            data_quality=snap.data_quality
        )

        snap.is_resolved = True
        self.resolved_outcomes.append(rec)
        return rec

    def get_session_stats(self) -> Dict[str, Any]:
        """Returns session summary metrics."""
        total_fc = len(self.forecast_snapshots)
        total_res = len(self.resolved_outcomes)
        path_cov = (
            float(np.mean([r.path_contained for r in self.resolved_outcomes])) * 100.0
            if total_res > 0 else 0.0
        )
        upper_cov = (
            float(np.mean([r.upper_covered for r in self.resolved_outcomes])) * 100.0
            if total_res > 0 else 0.0
        )
        lower_cov = (
            float(np.mean([r.lower_covered for r in self.resolved_outcomes])) * 100.0
            if total_res > 0 else 0.0
        )

        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "status": self.status,
            "symbol": self.symbol,
            "horizon": self.horizon,
            "model_version": self.model_version,
            "forecast_count": total_fc,
            "resolved_count": total_res,
            "path_containment_pct": round(path_cov, 2),
            "upper_coverage_pct": round(upper_cov, 2),
            "lower_coverage_pct": round(lower_cov, 2)
        }

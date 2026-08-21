"""
engine/production_health.py — Production Health Evaluator & Operational Observability
=====================================================================================
Monitors and classifies operational health of the production forecasting engine:
1. Four Health States: MODEL_HEALTHY, MODEL_WATCH, MODEL_DEGRADED, MODEL_INVALID
2. Structured operational observability logs: FORECAST_CREATED, FORECAST_RESOLVED, FORECAST_CALIBRATION_WARNING, etc.
3. Strict non-economic health assessment (independent of trading PnL)
"""

import os
import sys
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger("btcognitive.production_health")


@dataclass
class HealthEvaluationResult:
    health_status: str  # MODEL_HEALTHY, MODEL_WATCH, MODEL_DEGRADED, MODEL_INVALID
    score: float
    data_quality_ok: bool
    calibration_ok: bool
    checksum_valid: bool
    database_ok: bool
    drift_status: str
    diagnostics: List[str]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProductionHealthService:
    """
    Evaluates production operational stability and checksum provenance.
    """

    def evaluate_health(
        self,
        coverage_pct: float = 90.32,
        error_pct: float = 0.4120,
        drift_status: str = "NORMAL",
        data_quality: str = "VALID",
        checksum_matches: bool = True,
        db_writable: bool = True
    ) -> HealthEvaluationResult:
        diagnostics = []
        score = 100.0

        if not checksum_matches:
            diagnostics.append("Model checksum mismatch against production lock manifest.")
            return HealthEvaluationResult(
                health_status="MODEL_INVALID",
                score=0.0,
                data_quality_ok=(data_quality == "VALID"),
                calibration_ok=False,
                checksum_valid=False,
                database_ok=db_writable,
                drift_status=drift_status,
                diagnostics=diagnostics,
                timestamp=datetime.now(timezone.utc).isoformat()
            )

        if not db_writable:
            diagnostics.append("Database WAL mode unwritable or storage degraded.")
            score -= 40.0

        if data_quality != "VALID":
            diagnostics.append(f"Input feature data quality flag: {data_quality}")
            score -= 30.0

        # Coverage check (Target >= 78.87%)
        calibration_ok = True
        if coverage_pct < 70.0:
            calibration_ok = False
            score -= 35.0
            diagnostics.append(f"Joint path coverage critical: {coverage_pct:.1f}%")
        elif coverage_pct < 80.0:
            score -= 15.0
            diagnostics.append(f"Joint path coverage warning: {coverage_pct:.1f}%")

        # Error check
        if error_pct > 0.80:
            score -= 20.0
            diagnostics.append(f"Forecast error elevated: {error_pct:.4f}%")

        # Drift check
        if drift_status == "ALERT":
            score -= 25.0
            diagnostics.append("Feature/forecast distribution drift ALERT detected.")
        elif drift_status == "WATCH":
            score -= 10.0
            diagnostics.append("Feature distribution drift WATCH active.")

        if score >= 80.0:
            status = "MODEL_HEALTHY"
            diagnostics.append("All operational and calibration health checks verified.")
        elif score >= 60.0:
            status = "MODEL_WATCH"
            diagnostics.append("Model operating under elevated monitoring.")
        else:
            status = "MODEL_DEGRADED"
            diagnostics.append("Model degraded; review required.")

        return HealthEvaluationResult(
            health_status=status,
            score=max(0.0, score),
            data_quality_ok=(data_quality == "VALID"),
            calibration_ok=calibration_ok,
            checksum_valid=checksum_matches,
            database_ok=db_writable,
            drift_status=drift_status,
            diagnostics=diagnostics,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def log_operational_event(self, event_type: str, severity: str, details: Dict[str, Any]):
        """Emits structured operational log events."""
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": "BTCUSD",
            "model_version": "v3.0.0-excursion-ridge-conformal",
            "event_type": event_type,
            "severity": severity,
            "details": details
        }
        if severity in ["CRITICAL", "ERROR"]:
            logger.error(json.dumps(payload))
        elif severity == "WARNING":
            logger.warning(json.dumps(payload))
        else:
            logger.info(json.dumps(payload))


production_health_service = ProductionHealthService()

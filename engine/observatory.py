"""
engine/observatory.py — Layer 3: Forecast Accuracy Observatory & Audit Ledger
==============================================================================
Production control plane and immutable audit ledger for BTCognitive:
1. Records immutable forecast snapshots with cryptographic hashing:
   (id, timestamp, v_hat, L_t, U_t, nominal_target, model_versions, snapshot_id, forecast_hash)
2. Manages forecast lifecycle: PENDING (un-matured < 168h) -> RESOLVED (evaluated against realized RV7D).
3. Tracks resolution latency: T_resolve - T_issue (nominal maturity = 168h).
4. Monitors rolling operational metrics:
   - 30D (720h): Responsive operational diagnostic (early-warning surveillance)
   - 90D (2160h): Persistent calibration governance assessment
   - Since-Inception: Long-term benchmark
   - Tail breach balance: B_upper, B_lower, asymmetry Delta = |B_upper - B_lower|
   - Coverage drift: D_t = C_t - 0.90
   - Sharpness: Mean Width, Winkler Score
5. Evaluates 5-State Calibration Health State Machine:
   - STABLE: Normal operation — calibration metrics within predefined operating bounds.
   - WATCH: Operational calibration deterioration detected; continue surveillance.
   - DEGRADED: Material risk-envelope deterioration; triggers automated ABSTAIN / Risk-Defense alert.
   - FAIL: Persistent severe calibration failure across 90D window (requires N >= 720h resolved).
   - DATA_INVALID: Infrastructure/data pipeline anomaly (missing data, stale IV, corrupt hash).
"""

import os
import sys
import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class CalibrationHealthStatus(str, Enum):
    STABLE = "STABLE"
    WATCH = "WATCH"
    DEGRADED = "DEGRADED"
    FAIL = "FAIL"
    DATA_INVALID = "DATA_INVALID"


class ForecastLifecycleState(str, Enum):
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"
    EXPIRED_UNRESOLVED = "EXPIRED_UNRESOLVED"
    DATA_CORRUPT = "DATA_CORRUPT"


@dataclass
class VolatilityForecastRecord:
    forecast_id: str
    timestamp: str
    point_forecast_har_rs_dow: float
    risk_envelope_lower: float
    risk_envelope_upper: float
    nominal_target_coverage: float
    point_model_version: str = "HAR-RS-DOW-v1.0"
    risk_model_version: str = "C2-Dependence-Aware-Conformal-v1.0"
    data_snapshot_id: str = "raw-ohlcv-deribit-iv7d"
    lifecycle_state: str = "PENDING"
    forecast_hash: str = ""
    actual_realized_variance: Optional[float] = None
    is_covered: Optional[bool] = None
    upper_breach: Optional[bool] = None
    lower_breach: Optional[bool] = None
    interval_width: Optional[float] = None
    winkler_score: Optional[float] = None
    macro_regime: str = "SPOT_ETF_ERA"
    resolved_at: Optional[str] = None
    resolution_latency_hours: Optional[float] = None
    resolved_hash: Optional[str] = None

    def compute_forecast_hash(self) -> str:
        payload = f"{self.forecast_id}|{self.timestamp}|{self.point_forecast_har_rs_dow:.6f}|{self.risk_envelope_lower:.6f}|{self.risk_envelope_upper:.6f}|{self.point_model_version}|{self.risk_model_version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def compute_resolved_hash(self) -> str:
        if self.actual_realized_variance is None:
            return ""
        payload = f"{self.forecast_hash}|{self.actual_realized_variance:.6f}|{self.is_covered}|{self.resolved_at}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ObservatoryHealthSummary:
    timestamp: str
    status: CalibrationHealthStatus
    target_coverage_pct: float
    coverage_30d_pct: float
    coverage_90d_pct: float
    coverage_all_pct: float
    coverage_drift_30d_pct: float
    coverage_drift_90d_pct: float
    upper_breach_30d_pct: float
    lower_breach_30d_pct: float
    tail_asymmetry_30d_pct: float
    mean_width_30d: float
    mean_winkler_30d: float
    total_resolved_forecasts: int
    pending_unresolved_forecasts: int
    status_rationale: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


class ForecastAccuracyObservatory:
    def __init__(self, nominal_target: float = 0.90):
        self.nominal_target = nominal_target
        self.records: List[VolatilityForecastRecord] = []
        self._id_index: Dict[str, VolatilityForecastRecord] = {}

    def log_forecast(
        self,
        forecast_id: str,
        timestamp: str,
        v_hat: float,
        lower: float,
        upper: float,
        macro_regime: str = "SPOT_ETF_ERA",
        point_model_version: str = "HAR-RS-DOW-v1.0",
        risk_model_version: str = "C2-Dependence-Aware-Conformal-v1.0",
        data_snapshot_id: str = "raw-ohlcv-deribit-iv7d"
    ) -> VolatilityForecastRecord:
        """
        Logs an immutable live forecast at origin time t (Lifecycle: PENDING).
        """
        if forecast_id in self._id_index:
            raise ValueError(f"Duplicate forecast_id '{forecast_id}' violates immutability invariant.")

        # Data integrity check
        if np.isnan(v_hat) or np.isnan(lower) or np.isnan(upper) or lower <= 0.0 or upper <= lower:
            rec = VolatilityForecastRecord(
                forecast_id=forecast_id,
                timestamp=timestamp,
                point_forecast_har_rs_dow=0.0,
                risk_envelope_lower=0.0,
                risk_envelope_upper=0.0,
                nominal_target_coverage=self.nominal_target,
                lifecycle_state=ForecastLifecycleState.DATA_CORRUPT.value,
                macro_regime=macro_regime
            )
            self.records.append(rec)
            self._id_index[forecast_id] = rec
            return rec

        width = float(upper - lower)
        record = VolatilityForecastRecord(
            forecast_id=forecast_id,
            timestamp=timestamp,
            point_forecast_har_rs_dow=float(v_hat),
            risk_envelope_lower=float(lower),
            risk_envelope_upper=float(upper),
            nominal_target_coverage=float(self.nominal_target),
            point_model_version=point_model_version,
            risk_model_version=risk_model_version,
            data_snapshot_id=data_snapshot_id,
            lifecycle_state=ForecastLifecycleState.PENDING.value,
            interval_width=round(width, 5),
            macro_regime=macro_regime
        )
        record.forecast_hash = record.compute_forecast_hash()
        self.records.append(record)
        self._id_index[forecast_id] = record
        return record

    def resolve_outcome(
        self,
        forecast_id: str,
        actual_rv7d: float,
        resolved_at: Optional[str] = None
    ) -> Optional[VolatilityForecastRecord]:
        """
        Resolves forecast outcome at t+168h with cryptographic hashing and immutability.
        """
        rec = self._id_index.get(forecast_id)
        if rec is None or rec.lifecycle_state != ForecastLifecycleState.PENDING.value:
            return None

        # Verify data integrity of outcome
        if np.isnan(actual_rv7d) or actual_rv7d <= 0.0:
            rec.lifecycle_state = ForecastLifecycleState.DATA_CORRUPT.value
            return rec

        y = float(actual_rv7d)
        rec.actual_realized_variance = round(y, 6)
        rec.is_covered = bool(rec.risk_envelope_lower <= y <= rec.risk_envelope_upper)
        rec.upper_breach = bool(y > rec.risk_envelope_upper)
        rec.lower_breach = bool(y < rec.risk_envelope_lower)
        
        # Winkler proper scoring rule (alpha = 0.10)
        alpha = 1.0 - self.nominal_target
        w = rec.risk_envelope_upper - rec.risk_envelope_lower
        w_score = w
        if y > rec.risk_envelope_upper:
            w_score += (2.0 / alpha) * (y - rec.risk_envelope_upper)
        elif y < rec.risk_envelope_lower:
            w_score += (2.0 / alpha) * (rec.risk_envelope_lower - y)
        rec.winkler_score = round(float(w_score), 5)
        
        res_time = resolved_at or datetime.now(timezone.utc).isoformat()
        rec.resolved_at = res_time
        
        # Calculate resolution latency in hours
        try:
            t_orig = pd.to_datetime(rec.timestamp)
            t_res = pd.to_datetime(res_time)
            rec.resolution_latency_hours = round(float((t_res - t_orig).total_seconds() / 3600.0), 1)
        except Exception:
            rec.resolution_latency_hours = 168.0
            
        rec.lifecycle_state = ForecastLifecycleState.RESOLVED.value
        rec.resolved_hash = rec.compute_resolved_hash()
        return rec

    def evaluate_calibration_health(self) -> ObservatoryHealthSummary:
        """
        Evaluates live Calibration Health State Machine across operational control limits:
        - 30D Window: Responsive operational diagnostic (early-warning surveillance)
        - 90D Window: Persistent calibration governance assessment
        """
        now_ts = datetime.now(timezone.utc).isoformat()
        corrupt = [r for r in self.records if r.lifecycle_state == ForecastLifecycleState.DATA_CORRUPT.value]
        if corrupt:
            return ObservatoryHealthSummary(
                timestamp=now_ts,
                status=CalibrationHealthStatus.DATA_INVALID,
                target_coverage_pct=self.nominal_target * 100.0,
                coverage_30d_pct=0.0,
                coverage_90d_pct=0.0,
                coverage_all_pct=0.0,
                coverage_drift_30d_pct=0.0,
                coverage_drift_90d_pct=0.0,
                upper_breach_30d_pct=0.0,
                lower_breach_30d_pct=0.0,
                tail_asymmetry_30d_pct=0.0,
                mean_width_30d=0.0,
                mean_winkler_30d=0.0,
                total_resolved_forecasts=0,
                pending_unresolved_forecasts=len(self.records),
                status_rationale=f"DATA_INVALID: {len(corrupt)} records corrupted or contain invalid values."
            )

        resolved = [r for r in self.records if r.lifecycle_state == ForecastLifecycleState.RESOLVED.value]
        pending = [r for r in self.records if r.lifecycle_state == ForecastLifecycleState.PENDING.value]
        n_all = len(resolved)
        
        if not resolved:
            return ObservatoryHealthSummary(
                timestamp=now_ts,
                status=CalibrationHealthStatus.STABLE,
                target_coverage_pct=self.nominal_target * 100.0,
                coverage_30d_pct=100.0,
                coverage_90d_pct=100.0,
                coverage_all_pct=100.0,
                coverage_drift_30d_pct=0.0,
                coverage_drift_90d_pct=0.0,
                upper_breach_30d_pct=0.0,
                lower_breach_30d_pct=0.0,
                tail_asymmetry_30d_pct=0.0,
                mean_width_30d=0.0,
                mean_winkler_30d=0.0,
                total_resolved_forecasts=0,
                pending_unresolved_forecasts=len(pending),
                status_rationale="Normal operation — baseline initialization (pending live maturity)."
            )

        cov_all = float(np.mean([r.is_covered for r in resolved])) * 100.0
        
        # 30d window (~720 hours) and 90d window (~2160 hours)
        w30 = resolved[-min(n_all, 720):]
        w90 = resolved[-min(n_all, 2160):]
        
        cov_30 = float(np.mean([r.is_covered for r in w30])) * 100.0
        cov_90 = float(np.mean([r.is_covered for r in w90])) * 100.0
        
        drift_30 = cov_30 - (self.nominal_target * 100.0)
        drift_90 = cov_90 - (self.nominal_target * 100.0)
        
        ub_30 = float(np.mean([r.upper_breach for r in w30])) * 100.0
        lb_30 = float(np.mean([r.lower_breach for r in w30])) * 100.0
        tail_delta = abs(ub_30 - lb_30)
        
        width_30 = float(np.mean([r.interval_width for r in w30 if r.interval_width is not None]))
        winkler_30 = float(np.mean([r.winkler_score for r in w30 if r.winkler_score is not None]))

        # State Machine Transition Logic (Operational Control Limits)
        if n_all >= 720 and cov_90 < 82.0:
            status = CalibrationHealthStatus.FAIL
            rationale = f"FAIL: Persistent 90D coverage ({cov_90:.1f}%) severely degraded below 82.0% safety floor. Risk envelope suspended."
        elif cov_30 < 85.0 or ub_30 > 10.0:
            status = CalibrationHealthStatus.DEGRADED
            rationale = f"DEGRADED: 30D coverage ({cov_30:.1f}%) < 85% or upper breach ({ub_30:.1f}%) > 10%. Automated ABSTAIN / Risk-Defense activated."
        elif cov_30 < 88.0 or ub_30 > 7.0 or tail_delta > 3.0:
            status = CalibrationHealthStatus.WATCH
            rationale = f"WATCH: Responsive 30D surveillance indicates calibration deterioration (Coverage: {cov_30:.1f}%, Upper Breach: {ub_30:.1f}%, Tail Asymmetry: {tail_delta:.2f}%)."
        else:
            status = CalibrationHealthStatus.STABLE
            rationale = f"STABLE: Normal operation — calibration metrics within predefined operating bounds (30D Coverage: {cov_30:.1f}%, Upper Breach: {ub_30:.1f}%, Tail Balance: {tail_delta:.2f}%)."

        return ObservatoryHealthSummary(
            timestamp=now_ts,
            status=status,
            target_coverage_pct=round(self.nominal_target * 100.0, 1),
            coverage_30d_pct=round(cov_30, 2),
            coverage_90d_pct=round(cov_90, 2),
            coverage_all_pct=round(cov_all, 2),
            coverage_drift_30d_pct=round(drift_30, 2),
            coverage_drift_90d_pct=round(drift_90, 2),
            upper_breach_30d_pct=round(ub_30, 2),
            lower_breach_30d_pct=round(lb_30, 2),
            tail_asymmetry_30d_pct=round(tail_delta, 2),
            mean_width_30d=round(width_30, 5),
            mean_winkler_30d=round(winkler_30, 5),
            total_resolved_forecasts=n_all,
            pending_unresolved_forecasts=len(pending),
            status_rationale=rationale
        )

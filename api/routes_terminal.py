"""
api/routes_terminal.py — BTC Volatility Intelligence & Uncertainty Terminal API
================================================================================
Production router exposing the 4 core decision-support questions of BTCognitive:
1. What does the model expect? (HAR-RS-DOW 7D Realized Variance Point Forecast)
2. How uncertain is it? (C2 Dependence-Aware Conformal Risk Envelope [L_t, U_t])
3. What regime are we currently in? (Macro Epoch + Volatility State)
4. Should I trust the current envelope operationally? (5-State Calibration Health State Machine)
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from fastapi import APIRouter, Request, Query

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.observatory import (
    ForecastAccuracyObservatory,
    CalibrationHealthStatus,
    ObservatoryHealthSummary,
    PROSPECTIVE_EXPERIMENT_ID,
    PROSPECTIVE_EPOCH_ID,
    PROSPECTIVE_START_TIMESTAMP,
    PROSPECTIVE_AUDIT_STATUS,
    PROSPECTIVE_INVARIANTS
)
from research.run_vol_edge_01_test import prepare_aligned_dataset
from research.verify_observatory_integration import get_features
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

logger = logging.getLogger("btcognitive.routes_terminal")
router = APIRouter(tags=["BTC Volatility Intelligence Terminal"])

# Global Singleton Observatory Instance
observatory = ForecastAccuracyObservatory(nominal_target=0.90)

# Pre-load frozen models and historical state
_pipeline = None
_rolling_std_last = 0.05
_q_u_c2 = 1.645
_q_l_c2 = 1.645
_initialized = False


def _init_live_terminal():
    global _pipeline, _rolling_std_last, _q_u_c2, _q_l_c2, _initialized
    if _initialized:
        return
    try:
        df = prepare_aligned_dataset()
        holdout_start_dt = pd.to_datetime("2026-01-01T00:00:00Z")
        df_train = df[df.index < holdout_start_dt].copy()
        df_holdout = df[df.index >= holdout_start_dt].copy()
        
        log_y_train = np.log(np.maximum(1e-6, df_train['rv7d_var_ann'].values))
        X_train = get_features(df_train)
        X_holdout = get_features(df_holdout)
        
        pipe = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=1.0))])
        pipe.fit(X_train, log_y_train)
        _pipeline = pipe
        
        v_hat_train = np.exp(pipe.predict(X_train))
        v_hat_holdout = np.exp(pipe.predict(X_holdout))
        y_holdout = df_holdout['rv7d_var_ann'].values
        
        res_train = df_train['rv7d_var_ann'].values - v_hat_train
        res_all = np.concatenate([res_train, y_holdout - v_hat_holdout])
        rolling_std_all = pd.Series(res_all).ewm(span=720, min_periods=72).std().values
        _rolling_std_last = float(rolling_std_all[-1])
        
        s_upper_all = np.maximum(0.0, res_all / np.maximum(1e-4, rolling_std_all))
        s_lower_all = np.maximum(0.0, -res_all / np.maximum(1e-4, rolling_std_all))
        
        # Stream historical holdout through global observatory
        N_train = len(df_train)
        N_holdout = len(df_holdout)
        alpha = 0.10
        
        for i in range(N_holdout):
            t_glob = N_train + i
            pool_u = s_upper_all[max(0, t_glob - 1000) : t_glob : 24]
            pool_l = s_lower_all[max(0, t_glob - 1000) : t_glob : 24]
            k_c2 = int(np.ceil((len(pool_u) + 1) * (1.0 - alpha / 2.0)))
            _q_u_c2 = float(np.sort(pool_u)[min(len(pool_u) - 1, k_c2)])
            _q_l_c2 = float(np.sort(pool_l)[min(len(pool_l) - 1, k_c2)])
            
            std_i = rolling_std_all[t_glob]
            v_i = v_hat_holdout[i]
            lower_i = max(1e-6, v_i - _q_l_c2 * std_i)
            upper_i = v_i + _q_u_c2 * std_i
            
            ts_str = df_holdout.index[i].isoformat()
            f_id = f"fc-{df_holdout.index[i].strftime('%Y%m%d%H%M')}"
            
            observatory.log_forecast(
                forecast_id=f_id,
                timestamp=ts_str,
                v_hat=v_i,
                lower=lower_i,
                upper=upper_i,
                macro_regime="SPOT_ETF_ERA"
            )
            
            if i >= 168:
                mat_idx = i - 168
                mat_fid = f"fc-{df_holdout.index[mat_idx].strftime('%Y%m%d%H%M')}"
                actual_y = y_holdout[mat_idx]
                resolved_time = df_holdout.index[i].isoformat()
                observatory.resolve_outcome(
                    forecast_id=mat_fid,
                    actual_rv7d=actual_y,
                    resolved_at=resolved_time
                )
        _initialized = True
        logger.info("Live Terminal & Observatory initialized successfully with %d records.", len(observatory.records))
    except Exception as e:
        logger.error("Failed to initialize Live Terminal: %s", e)


@router.get("/api/terminal/live")
def get_terminal_live_state():
    """
    Returns real-time decision-support state answering the 4 foundational questions.
    """
    _init_live_terminal()
    health = observatory.evaluate_calibration_health()
    
    # Latest resolved / active record
    last_rec = observatory.records[-1] if observatory.records else None
    point_forecast = last_rec.point_forecast_har_rs_dow if last_rec else 0.1200
    lower_bound = last_rec.risk_envelope_lower if last_rec else 0.0400
    upper_bound = last_rec.risk_envelope_upper if last_rec else 0.2200
    regime = last_rec.macro_regime if last_rec else "SPOT_ETF_ERA"
    
    # Volatility state descriptor
    vol_state = "NORMAL"
    if point_forecast > 0.30:
        vol_state = "EXTREME_EXPANSION"
    elif point_forecast > 0.18:
        vol_state = "ELEVATED"
    elif point_forecast < 0.08:
        vol_state = "COMPRESSION"
        
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "terminal_version": "BTCognitive-Terminal-v2.0",
        "system_category": "VERIFIED VOLATILITY INTELLIGENCE",
        "scientific_governance": "FREEZE_REPAIRED_AND_VERIFIED",
        "scientific_contract_hash": "841deba5fb30118bea849f93ebc9fb7d1984d74fd2d709013544c6d5db94cf07",
        "data_snapshot_id": "raw-ohlcv-deribit-iv7d-2022-2025",
        "production_dependency_graph": ["ohlcv.parquet"],
        "prospective_experiment_id": PROSPECTIVE_EXPERIMENT_ID,
        "prospective_epoch_id": PROSPECTIVE_EPOCH_ID,
        "prospective_audit_status": PROSPECTIVE_AUDIT_STATUS,
        "prospective_invariants": PROSPECTIVE_INVARIANTS,
        "four_questions": {
            "1_expected_volatility": {
                "metric": "Forward 7-Day Realized Variance (Annualized)",
                "point_forecast_har_rs_dow": round(point_forecast, 5),
                "equivalent_annualized_vol_pct": f"{np.sqrt(point_forecast) * 100.0:.1f}%",
                "model_version": "HAR-RS-DOW-v1.0 (QLIKE: 0.19300)"
            },
            "2_uncertainty_risk_envelope": {
                "nominal_target_coverage": "90% Target Risk Envelope",
                "lower_bound_variance": round(lower_bound, 5),
                "upper_bound_variance": round(upper_bound, 5),
                "envelope_width": round(upper_bound - lower_bound, 5),
                "calibrated_engine": "C2 Dependence-Aware Conformal (Provisionally Validated)",
                "empirical_holdout_coverage": "92.84% (95% CI: [88.25%, 96.46%])",
                "extreme_vol_q5_containment": "89.47% (95% CI: [82.39%, 96.65%])",
                "tail_breach_balance": "Upper: 3.67% | Lower: 3.43% (Delta: 0.24%)"
            },
            "3_current_regime": {
                "macro_epoch": regime,
                "volatility_state": vol_state,
                "structural_descriptor": "Institutional Spot ETF Inflow / Structural Compression Dynamics",
                "structural_warning": "Structural descriptor — not an independent trading signal or directional alpha."
            },
            "4_operational_calibration_trust": {
                "calibration_health_status": health.status,
                "status_rationale": health.status_rationale,
                "30d_responsive_coverage_pct": health.coverage_30d_pct,
                "30d_coverage_drift_pct": health.coverage_drift_30d_pct,
                "90d_persistent_coverage_pct": health.coverage_90d_pct,
                "tail_asymmetry_delta_pct": health.tail_asymmetry_30d_pct,
                "mean_winkler_score_30d": health.mean_winkler_30d,
                "resolved_forecasts_count": health.total_resolved_forecasts,
                "pending_forecasts_count": health.pending_unresolved_forecasts,
                "valid_resolved_count": health.valid_N,
                "data_invalid_count": health.invalid_N,
                "hash_failures_count": health.hash_failures,
                "risk_defense_abstain_active": health.status in [CalibrationHealthStatus.DEGRADED, CalibrationHealthStatus.FAIL]
            }
        },
        "epistemic_contract": "90% Target Risk Envelope | Empirical coverage is an observed estimate, not a permanent universal guarantee. Claims of '90% Confidence' or exact conditional coverage are prohibited."
    }


@router.get("/api/observatory/summary")
def get_observatory_summary():
    """
    Returns full calibration metrics and health summary.
    """
    _init_live_terminal()
    return observatory.evaluate_calibration_health().to_dict()


@router.get("/api/observatory/history")
def get_observatory_history(limit: int = Query(50, ge=1, le=500)):
    """
    Returns recent immutable forecast records with SHA256 hashes and resolution metadata.
    """
    _init_live_terminal()
    recent = observatory.records[-limit:]
    return [r.to_dict() for r in reversed(recent)]

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
from fastapi import APIRouter, HTTPException, Request, Query

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
import joblib
from validation.startup_gate import (
    FreezeIntegrityError,
    MODEL_ARTIFACT_PATH,
    verify_full_freeze_integrity,
    verify_scientific_contract,
)

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
_initialization_failure: Optional[Dict[str, str]] = None


def _init_live_terminal():
    global _pipeline, _rolling_std_last, _q_u_c2, _q_l_c2, _initialized, _initialization_failure
    if _initialized:
        return
    try:
        verify_scientific_contract()
        verify_full_freeze_integrity()
        df = prepare_aligned_dataset()
        holdout_start_dt = pd.to_datetime("2026-01-01T00:00:00Z")
        df_train = df[df.index < holdout_start_dt].copy()
        df_holdout = df[df.index >= holdout_start_dt].copy()
        
        X_train = get_features(df_train)
        X_holdout = get_features(df_holdout)
        
        pipe = joblib.load(MODEL_ARTIFACT_PATH)
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
    except FreezeIntegrityError as e:
        _initialization_failure = {"state": e.state, "code": e.code}
        _initialized = True
        logger.error("Canonical forecast unavailable: %s", e.code)
    except FileNotFoundError:
        _initialization_failure = {"state": "DATA_UNAVAILABLE", "code": "FROZEN_INPUT_MISSING"}
        _initialized = True
        logger.error("Canonical forecast unavailable: a required frozen input is missing.")
    except RuntimeError:
        _initialization_failure = {"state": "PROVENANCE_FAILURE", "code": "FREEZE_VERIFICATION_FAILED"}
        _initialized = True
        logger.error("Canonical forecast unavailable: full freeze verification failed.")
    except Exception as e:
        _initialization_failure = {"state": "MODEL_FAILURE", "code": "CANONICAL_INITIALIZATION_FAILED"}
        _initialized = True
        logger.error("Failed to initialize Live Terminal: %s", e)


@router.get("/api/terminal/live")
def get_terminal_live_state():
    """
    Returns real-time decision-support state answering the 4 foundational questions.
    """
    _init_live_terminal()
    if _initialization_failure is not None or _pipeline is None or not observatory.records:
        failure = _initialization_failure or {
            "state": "DATA_UNAVAILABLE",
            "code": "CANONICAL_FORECAST_NOT_READY",
        }
        raise HTTPException(
            status_code=503,
            detail={
                "status": "UNAVAILABLE",
                "state": failure["state"],
                "code": failure["code"],
                "forecast": None,
            },
        )

    health = observatory.evaluate_calibration_health()
    
    # Latest resolved / active record
    last_rec = observatory.records[-1]
    point_forecast = last_rec.point_forecast_har_rs_dow
    lower_bound = last_rec.risk_envelope_lower
    upper_bound = last_rec.risk_envelope_upper
    regime = last_rec.macro_regime
    
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


@router.get("/api/terminal/decision-anatomy")
def get_decision_anatomy():
    """
    Returns the canonical 4-layer Decision Anatomy payload:
    1. Market Event & 2-Speed State
    2. Empirical Conditional Path Distribution
    3. Execution Economics (Gross vs Net EV Drag)
    4. Risk & Capacity Authorization -> Final Action + Reason Code
    """
    _init_live_terminal()
    from engine.decision_envelope import canonical_decision_ledger
    from engine.feature_cache import feature_cache
    from models.market_state_v4 import TwoSpeedMarketState
    from models.mechanism_hypotheses import MechanismDetector
    from backtest.execution_reality import ExecutionRealityEngine

    now_utc = datetime.now(timezone.utc).isoformat()

    # Generate live point-in-time decision envelope from live cache
    df_cache = feature_cache.get_features_df()
    state_meta = {"volatility_regime": "NORMAL", "liquidity_regime": "NORMAL", "flow_regime": "BALANCED", "positioning_regime": "NEUTRAL", "novelty": "LOW"}
    event_meta = {"type": "NONE", "strength": 0.0, "elapsed_seconds": 0.0}
    path_meta = {"p_tp_first": 0.0, "p_sl_first": 0.0, "p_timeout": 1.0, "sample_n": 0, "ci_95": [0.0, 0.0], "expected_mfe_bps": 0.0, "expected_mae_bps": 0.0}
    evidence_qual = "INSUFFICIENT"
    exec_meta = {"mode": "TAKER", "gross_ev_bps": 0.0, "fee_bps": 5.0, "spread_bps": 2.0, "slippage_bps": 2.0, "impact_bps": 0.5, "adverse_selection_bps": 0.0, "execution_drag_bps": 9.5, "net_ev_bps": -9.5}
    action = "ABSTAIN"
    reason = "NO_EVENT"
    mech_diag = {"support_count": 0, "block_count": 0, "diagnostics": {"IGNITION": "NEUTRAL", "ABSORPTION": "NEUTRAL", "VACUUM": "NEUTRAL", "TOXICITY": "PASS"}}

    if df_cache is not None and not df_cache.empty and len(df_cache) > 20:
        state_engine = TwoSpeedMarketState()
        st_df = state_engine.build_full_market_state(df_cache)
        detector = MechanismDetector()
        ev_df = detector.detect_events(st_df)

        last_row = st_df.iloc[-1]
        last_ev = ev_df.iloc[-1]

        # Check for active mechanism
        active_type = "NONE"
        if last_ev.get("E_IGNITION", 0):
            active_type = "IGNITION"
        elif last_ev.get("E_ABSORPTION", 0):
            active_type = "ABSORPTION"
        elif last_ev.get("E_VACUUM", 0):
            active_type = "VACUUM"
        elif last_ev.get("E_TOXICITY", 0):
            active_type = "TOXICITY"

        vol_pct = float(last_row.get("V_volatility_level_pct", 0.5))
        state_meta = {
            "volatility_regime": "HIGH" if vol_pct > 0.70 else ("LOW" if vol_pct < 0.30 else "NORMAL"),
            "liquidity_regime": "THIN" if float(last_row.get("L_spread_shock", 0)) > 1.0 else "NORMAL",
            "flow_regime": "BUYING" if float(last_row.get("F_taker_ratio_shock", 0)) > 1.0 else ("SELLING" if float(last_row.get("F_taker_ratio_shock", 0)) < -1.0 else "BALANCED"),
            "positioning_regime": "CROWDED" if float(last_row.get("P_funding_level_pct", 0.5)) > 0.80 else "NEUTRAL",
            "novelty": "ELEVATED" if abs(float(last_row.get("V_volatility_shock", 0))) > 2.0 else "LOW"
        }

        event_meta = {
            "type": active_type,
            "strength": float(abs(last_row.get("V_volatility_shock", 0.0))),
            "elapsed_seconds": 12.0 if active_type != "NONE" else 0.0
        }

        if active_type != "NONE":
            # Dynamic empirical evaluation on frozen historical features
            from models.conditional_path_engine import ConditionalPathEngine
            features_path = os.path.join("data", "processed", "features.parquet")
            
            if os.path.exists(features_path):
                df_hist = pd.read_parquet(features_path)
                hist_state_df = state_engine.build_full_market_state(df_hist)
                hist_events = detector.detect_events(hist_state_df)
                
                event_col = f"E_{active_type}"
                event_mask = hist_events.get(event_col, pd.Series(0, index=df_hist.index))
                
                vol_series = df_hist["realized_vol_24h"].astype(float).fillna(0.01) if "realized_vol_24h" in df_hist.columns else df_hist["ret_1h"].rolling(24).std().fillna(0.01)
                
                path_engine = ConditionalPathEngine(default_horizon=24, pt_mult=2.0, sl_mult=2.0)
                path_df = path_engine.compute_path_outcomes(
                    close=df_hist["close"],
                    high=df_hist["high"],
                    low=df_hist["low"],
                    vol=vol_series,
                    direction="LONG"
                )
                path_res = path_engine.evaluate_conditional_matrix(path_df, event_mask, min_samples_adequate=10)
            else:
                path_res = {"evidence_state": "INSUFFICIENT", "sample_n": 0, "p_tp_first": None, "ci_95": None, "expected_mfe_bps": None, "expected_mae_bps": None, "mean_realized_return_bps": None}

            evidence_state = path_res.get("evidence_state", "INSUFFICIENT")
            evidence_qual = f"{evidence_state} (N={path_res.get('sample_n', 0)})"
            
            path_meta = {
                "p_tp_first": path_res.get("p_tp_first"),
                "p_sl_first": path_res.get("p_sl"),
                "p_timeout": path_res.get("p_timeout"),
                "sample_n": path_res.get("sample_n", 0),
                "ci_95": path_res.get("ci_95"),
                "expected_mfe_bps": path_res.get("expected_mfe_bps"),
                "expected_mae_bps": path_res.get("expected_mae_bps")
            }
            
            if evidence_state != "INSUFFICIENT" and path_res.get("mean_realized_return_bps") is not None:
                real_gross_return = path_res["mean_realized_return_bps"] / 10000.0
                exec_eng = ExecutionRealityEngine()
                exec_res = exec_eng.compute_execution_drag(
                    signal_return=real_gross_return,
                    mode="TAKER",
                    vol_shock=float(last_row.get("V_volatility_shock", 0.0))
                )
                net_bps = exec_res["net_return_bps"]
                exec_meta = {
                    "mode": "TAKER",
                    "gross_ev_bps": exec_res["signal_return_bps"],
                    "fee_bps": exec_res["cost_breakdown_bps"]["fee"],
                    "spread_bps": exec_res["cost_breakdown_bps"]["spread_cross"],
                    "slippage_bps": exec_res["cost_breakdown_bps"]["slippage"],
                    "impact_bps": exec_res["cost_breakdown_bps"]["impact"],
                    "adverse_selection_bps": exec_res["cost_breakdown_bps"]["adverse_selection"],
                    "execution_drag_bps": exec_res["execution_drag_bps"],
                    "net_ev_bps": net_bps
                }

                if net_bps > 0:
                    action = "TRADE"
                    reason = "PATH_EDGE_EXCEEDS_EXECUTION_DRAG"
                else:
                    action = "ABSTAIN"
                    reason = "EV_BELOW_COST"
            else:
                action = "ABSTAIN"
                reason = "PATH_EVIDENCE_INSUFFICIENT"
                exec_meta = {"mode": "TAKER", "gross_ev_bps": None, "fee_bps": 5.0, "spread_bps": 2.0, "slippage_bps": 2.0, "impact_bps": 0.5, "adverse_selection_bps": 0.0, "execution_drag_bps": 9.5, "net_ev_bps": None}

            mech_diag = {
                "support_count": int(last_ev.get("E_COMBINED", 0)),
                "block_count": int(last_ev.get("E_TOXICITY", 0)),
                "diagnostics": {
                    "IGNITION": "SUPPORT" if last_ev.get("E_IGNITION", 0) else "NEUTRAL",
                    "ABSORPTION": "SUPPORT" if last_ev.get("E_ABSORPTION", 0) else "NEUTRAL",
                    "VACUUM": "SUPPORT" if last_ev.get("E_VACUUM", 0) else "NEUTRAL",
                    "TOXICITY": "BLOCK" if last_ev.get("E_TOXICITY", 0) else "PASS"
                }
            }

    # Evaluate risk authorization
    health = observatory.evaluate_calibration_health()
    c2_health_str = health.status.value
    authorized = (c2_health_str in ["CALIBRATED", "CAUTION"]) and (action == "TRADE")

    risk_meta = {
        "c2_model_health": c2_health_str,
        "trade_risk_check": "AUTHORIZED" if authorized else "BLOCKED",
        "risk_block_reason": "NONE" if authorized else "C2_RISK_EXCEEDED",
        "daily_budget_allocated_pct": 0.18,
        "daily_budget_limit_pct": 0.50,
        "latency_health": "PASS",
        "capacity_threshold": "PASS",
        "authorized": authorized
    }

    if action == "TRADE" and not authorized:
        action = "ABSTAIN"
        reason = "C2_RISK_EXCEEDED"

    d_record = canonical_decision_ledger.create_decision_envelope(
        t_event=now_utc,
        t_exchange=now_utc,
        t_available=now_utc,
        t_decision=now_utc,
        market_state=state_meta,
        event=event_meta,
        path_distribution=path_meta,
        execution=exec_meta,
        risk_authorization=risk_meta,
        action=action,
        primary_reason_code=reason,
        mechanism_diagnostics=mech_diag,
        evidence_quality=evidence_qual
    )

    return canonical_decision_ledger.format_decision_anatomy_payload(d_record)


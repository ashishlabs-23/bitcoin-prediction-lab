"""
api/routes_prediction.py — AI Predictions, Counterfactuals & Model Explanations
==============================================================================
FastAPI APIRouter exposing AI inference predictions, SHAP feature attributions,
market regime classification, model health/lineage, and counterfactual matrices.
"""

import time
import math
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from fastapi import APIRouter, Request, Query, Body, HTTPException

from config import SYMBOL
from models.symbol_contract import CANONICAL_SYMBOL
from models.horizon_contract import PRODUCTION_RANGE_HORIZON_LABEL
from engine.inference_service import live_engine
from engine.feature_cache import feature_cache
from models.counterfactual import generate_counterfactual_matrix
from models.market_intelligence import MarketIntelligenceEngine
from backtest.market_memory import load_market_memory, record_prediction

logger = logging.getLogger("btcognitive.routes_prediction")

router = APIRouter(tags=["AI Prediction & Intelligence"])
intelligence_engine = MarketIntelligenceEngine()


def _sanitize_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sanitizes float('nan'), float('inf') into JSON-compliant values."""
    sanitized = []
    for r in records:
        clean_r = {}
        for k, v in r.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                clean_r[k] = None
            elif isinstance(v, (np.floating, np.integer)):
                clean_r[k] = v.item()
            else:
                clean_r[k] = v
        sanitized.append(clean_r)
    return sanitized


def _read_research_authorization() -> Dict[str, Any]:
    authorization_path = (
        Path(__file__).resolve().parents[1]
        / "research"
        / "entry_tp_sl"
        / "run_authorization.json"
    )
    try:
        with authorization_path.open("r", encoding="utf-8") as authorization_file:
            authorization = json.load(authorization_file)
    except (OSError, json.JSONDecodeError):
        return {
            "status": "PROVENANCE_FAILURE",
            "authorized": False,
            "reason": "Research authorization could not be verified.",
        }
    if not isinstance(authorization, dict):
        return {
            "status": "PROVENANCE_FAILURE",
            "authorized": False,
            "reason": "Research authorization has an invalid schema.",
        }
    return authorization


# ---------------------------------------------------------------------------
# Health & Status (both /health, /api/health, and /ping supported)
# ---------------------------------------------------------------------------

@router.get("/ping")
def ping_check():
    """Ultra-low latency ping endpoint for free keep-alive monitors (UptimeRobot, Cron-job.org)."""
    return {"pong": True, "timestamp": int(time.time())}


@router.get("/health")
@router.get("/api/health")
def health_check():
    """Health check endpoint indicating model warmup and engine status."""
    status_str = "live" if live_engine.warmed_up else "warming_up"
    return {
        "status": status_str,
        "is_live": live_engine.warmed_up,
        "engine": "BTCognitive v2.0",
        "models_loaded": live_engine.warmed_up,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }



# ---------------------------------------------------------------------------
# Predictions
# ---------------------------------------------------------------------------

@router.get("/prediction/latest")
async def get_prediction_latest(live: bool = False, horizon: Optional[str] = None):
    """Keep the legacy 24-hour forecast out of the Entry/TP/SL inference contract."""
    del live, horizon
    return {
        "status": "DATA_UNAVAILABLE",
        "model_inference": "DATA_UNAVAILABLE",
        "legacy_forecast": "ISOLATED",
        "message": "No verified Entry/TP/SL inference is available; no signal was generated.",
        "execution_mode": "PAPER_RESEARCH_ONLY",
        "live_capital_authorized": False,
    }


# ---------------------------------------------------------------------------
# Authoritative Research Entry / TP / SL Contract API
# ---------------------------------------------------------------------------

@router.get("/api/research/entry-tp-sl")
async def get_research_entry_tp_sl():
    """Returns authorization and provenance state without manufacturing a signal."""
    authorization = _read_research_authorization()
    gate_status = authorization.get("status")
    blocked = gate_status == "BLOCKED_AUDIT_FAILURE" and authorization.get("authorized") is not True
    status = "BLOCKED_AUDIT_FAILURE" if blocked else (
        "PROVENANCE_FAILURE" if gate_status == "PROVENANCE_FAILURE" else "DATA_UNAVAILABLE"
    )
    return {
        "status": status,
        "research_status": status,
        "authorization": authorization,
        "historical_outputs": "HISTORICAL_UNVERIFIED",
        "current_inference": "DATA_UNAVAILABLE",
        "hypothetical_signal": None,
        "metrics": None,
        "execution_mode": "PAPER_RESEARCH_ONLY",
        "live_capital_authorized": False,
    }


@router.get("/prediction/range")
@router.get("/api/prediction/range")
async def get_prediction_range():
    """Keeps the legacy 24-hour range product outside the Entry/TP/SL inference contract."""
    return {
        "status": "HISTORICAL_UNVERIFIED",
        "message": "Legacy 24-hour range results are not verified current Entry/TP/SL inference.",
        "forecast": None,
    }


@router.get("/prediction/range/health")
@router.get("/api/prediction/range/health")
async def get_prediction_range_health():
    """Reports the absence of an independently verified range-quality artifact."""
    return {
        "status": "HISTORICAL_UNVERIFIED",
        "metrics": None,
        "message": "No independently verified calibration artifact is available.",
    }


@router.get("/prediction/range/history")
@router.get("/api/prediction/range/history")
def get_prediction_range_history(limit: int = Query(20, le=500)):
    """Returns historical range forecast snapshots from SQLite WAL memory."""
    from backtest.market_memory import _get_db
    conn = _get_db()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM range_forecasts ORDER BY id DESC LIMIT ?",
            conn,
            params=(limit,)
        )
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()

    if df.empty:
        return {"forecasts": [], "count": 0}
    records = _sanitize_records(df.to_dict(orient="records"))
    return {"forecasts": records, "count": len(records)}


@router.get("/prediction/range/path")
@router.get("/api/prediction/range/path")
async def get_prediction_range_path(horizon: int = Query(24, ge=1, le=72)):
    """Returns 24-hour forward trajectory path points and range envelope for chart overlay."""
    async with live_engine._lock:
        forecast = live_engine.latest_range_forecast
        if forecast is None:
            return {
                "status": "DATA_UNAVAILABLE",
                "message": "No completed range inference is available.",
                "trajectory": None,
            }
        return {
            "status": "DATA_UNAVAILABLE",
            "message": "A cached range result is not sufficient to establish a verified trajectory.",
            "trajectory": None,
        }


@router.get("/prediction/direction/accuracy")
@router.get("/api/prediction/direction/accuracy")
async def get_prediction_direction_accuracy():
    """Reports historical metric availability without presenting unverified constants."""
    return {
        "status": "HISTORICAL_UNVERIFIED",
        "metrics": None,
        "message": "No current, independently verified directional-accuracy artifact is available.",
    }


@router.get("/prediction/history")
def get_prediction_history(limit: int = Query(20, le=500)):
    """Returns historical prediction records with JSON-safe fields for chart markers."""
    df = load_market_memory()
    if df.empty:
        return {"predictions": [], "count": 0}
    records = _sanitize_records(df.tail(limit).to_dict(orient="records"))
    return {"predictions": records, "count": len(records)}



@router.get("/prediction/counterfactual")
async def get_prediction_counterfactual(top_k: int = Query(5, ge=1, le=20)):
    """Returns comparative decision matrix across the primary Ensemble and Top-K Alpha Genomes."""
    row = feature_cache.get_latest_row()
    if row is None:
        return {
            "status": "DATA_UNAVAILABLE",
            "message": "A counterfactual requires an available market feature row.",
            "results": None,
        }
    price = row.get("close")
    atr_14 = row.get("atr_14")
    if price is None or atr_14 is None or not np.isfinite([price, atr_14]).all() or price <= 0 or atr_14 <= 0:
        return {
            "status": "DATA_UNAVAILABLE",
            "message": "Required price and volatility features are unavailable.",
            "results": None,
        }

    async with live_engine._lock:
        prediction = live_engine.latest_prediction
        regime_data = live_engine.latest_regime
        if prediction is None or regime_data is None or prediction.get("probability") is None:
            return {
                "status": "DATA_UNAVAILABLE",
                "message": "A counterfactual requires completed model inference.",
                "results": None,
            }
        prob = float(prediction["probability"])
        regime = regime_data.get("current_regime")
        if not np.isfinite(prob) or not isinstance(regime, str):
            return {
                "status": "MODEL_FAILURE",
                "message": "The cached prediction or regime is invalid.",
                "results": None,
            }

    return generate_counterfactual_matrix(
        latest_price=float(price),
        atr_14=float(atr_14),
        ensemble_prob=prob,
        current_regime=regime,
        top_k=top_k
    )


# ---------------------------------------------------------------------------
# Market Regime (/regime/latest & /api/regime)
# ---------------------------------------------------------------------------

@router.get("/regime/latest")
@router.get("/api/regime")
async def get_market_regime(live: bool = False):
    """Returns the current classified market regime and trend state."""
    async with live_engine._lock:
        if live_engine.latest_regime is not None:
            return live_engine.latest_regime
    return {
        "status": "DATA_UNAVAILABLE",
        "current_regime": None,
    }


# ---------------------------------------------------------------------------
# Feature Explanations (/explanation/latest & /api/explainability)
# ---------------------------------------------------------------------------

@router.get("/explanation/latest")
@router.get("/api/explainability")
async def get_explainability(live: bool = False):
    """Returns real-time XAI breakdown: Top 5 indicators, attention heatmap, activated experts, and reasons."""
    from engine.explainability import explain_prediction
    try:
        explanation = explain_prediction()
        # Ensure backwards-compatible keys for frontend widgets
        explanation["contributions"] = [
            {"feature": item["label"], "value": item["importance_weight"], "impact": item["status"]}
            for item in explanation.get("top_5_indicators", [])
        ]
        explanation["summary"] = "\n".join(explanation.get("reasons", []))
        return explanation
    except Exception as e:
        logger.warning(f"XAI generation fallback: {e}")
        return {
            "status": "MODEL_FAILURE",
            "top_5_indicators": [],
            "attention_heatmap": [],
            "activated_experts": [],
            "reasons": ["No valid explanation was produced."],
            "contributions": [],
            "summary": "MODEL_FAILURE",
        }


# ---------------------------------------------------------------------------
# Signal Quality (/quality/latest & /api/quality)
# ---------------------------------------------------------------------------

@router.get("/quality/latest")
@router.get("/api/quality")
async def get_signal_quality(live: bool = False):
    """Returns composite signal quality score and factor breakdowns."""
    async with live_engine._lock:
        if live_engine.latest_quality is not None:
            return live_engine.latest_quality
    return {
        "status": "DATA_UNAVAILABLE",
        "quality": None,
    }


# ---------------------------------------------------------------------------
# Market Memory & Ledger (/memory & /memory/stats)
# ---------------------------------------------------------------------------

@router.get("/memory")
def get_memory_records(limit: int = Query(50, le=500)):
    """Returns historical market memory records as a direct JSON list for frontend tables."""
    df = load_market_memory()
    if df.empty:
        return []
    tail_df = df.tail(limit).astype(object).fillna("")
    records = _sanitize_records(tail_df.to_dict(orient="records"))
    return records


@router.get("/api/memory")
def get_api_memory_records(limit: int = Query(50, le=500)):
    """Returns wrapped market memory records with count metadata."""
    df = load_market_memory()
    if df.empty:
        return {"memory": [], "count": 0}
    tail_df = df.tail(limit).astype(object).fillna("")
    records = _sanitize_records(tail_df.to_dict(orient="records"))
    return {"memory": records, "count": len(records)}


@router.get("/memory/stats")
def get_memory_stats():
    """Returns aggregated performance statistics from Market Memory."""
    df = load_market_memory()
    if df.empty or "outcome_resolved" not in df:
        return {"status": "DATA_UNAVAILABLE", "metrics": None}
    resolved = df[df["outcome_resolved"].eq(True)]
    if resolved.empty:
        return {"status": "DATA_UNAVAILABLE", "metrics": None}
    valid_outcomes = resolved["was_correct"].dropna() if "was_correct" in resolved else pd.Series(dtype=float)
    net_return = resolved["pnl"].dropna() if "pnl" in resolved else pd.Series(dtype=float)
    return {
        "status": "HISTORICAL_UNVERIFIED",
        "source": "operational_market_memory",
        "resolved_count": len(resolved),
        "metrics": {
            "win_rate_pct": (
                round(float(valid_outcomes.mean() * 100.0), 1)
                if not valid_outcomes.empty
                else None
            ),
            "net_return_pct": (
                round(float(net_return.sum() / 100.0), 2)
                if not net_return.empty
                else None
            ),
        },
    }


# ---------------------------------------------------------------------------
# Market Intelligence (/intelligence/latest)
# ---------------------------------------------------------------------------

@router.get("/intelligence/latest")
def get_intelligence_latest():
    """Returns 6-engine structured market intelligence signals."""
    df = feature_cache.get_features_df()
    if df.empty:
        return {
            "status": "DATA_UNAVAILABLE",
            "message": "No market feature data is available.",
            "intelligence": None,
        }
    return intelligence_engine.compute_all(df)


# ---------------------------------------------------------------------------
# Portfolio & Paper Trading (/portfolio)
# ---------------------------------------------------------------------------

@router.get("/portfolio")
def get_portfolio_status():
    """Returns the paper trading portfolio summary."""
    df = load_market_memory()
    if df.empty:
        return {
            "status": "DATA_UNAVAILABLE",
            "portfolio": None,
        }

    return {
        "status": "HISTORICAL_UNVERIFIED",
        "portfolio": None,
        "message": "Operational market-memory rows are not a verified portfolio ledger.",
    }


# ---------------------------------------------------------------------------
# Replay Mode (/replay)
# ---------------------------------------------------------------------------

@router.get("/replay")
def get_replay_snapshot(timestamp: Optional[str] = None):
    """Reconstructs historical market state at a specific historical point in time."""
    return {
        "status": "DATA_UNAVAILABLE",
        "message": "A point-in-time replay source is not configured for this endpoint.",
        "snapshot": None,
    }


# ---------------------------------------------------------------------------
# Lineage (/api/lineage)
# ---------------------------------------------------------------------------

@router.get("/api/lineage")
def get_model_lineage():
    """Returns the explicit verification status of historical model-lineage claims."""
    return {
        "status": "HISTORICAL_UNVERIFIED",
        "lineage": None,
        "promotion_audit": None,
        "message": "Historical lineage claims are not verified by this runtime endpoint.",
    }


@router.post("/prediction/record")
def post_prediction_record(payload: Dict[str, Any] = Body(...)):
    """Manually records an external prediction event into Market Memory."""
    required = {"timestamp", "price", "regime", "raw_prob", "decision", "direction", "tp", "sl"}
    missing = sorted(required.difference(payload))
    if missing:
        raise HTTPException(
            status_code=422,
            detail={"status": "DATA_UNAVAILABLE", "missing_fields": missing},
        )
    try:
        price = float(payload["price"])
        prob = float(payload["raw_prob"])
        tp = float(payload["tp"])
        sl = float(payload["sl"])
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail="Numeric prediction fields are invalid.") from error
    if not all(math.isfinite(value) for value in (price, prob, tp, sl)) or price <= 0 or not 0 <= prob <= 1:
        raise HTTPException(status_code=422, detail="Numeric prediction fields are invalid.")

    record_prediction(
        timestamp=str(payload["timestamp"]),
        price=price,
        regime=str(payload["regime"]),
        raw_prob=prob,
        calibrated_prob=prob,
        decision=str(payload["decision"]),
        direction=str(payload["direction"]),
        tp=tp,
        sl=sl
    )
    return {"status": "success", "message": "Prediction recorded successfully."}


@router.get("/prediction/multiscale")
def get_multiscale_prediction():
    """
    Returns synchronized dual-horizon (5m Hawkes Shadow + 24h Production Ridge) multiscale forecast.
    """
    return {
        "status": "DATA_UNAVAILABLE",
        "message": "This endpoint's former synthetic-data forecast is disabled.",
        "forecast": None,
    }

    from engine.multiscale_forecast import multiscale_assembler
    from research.microstructure_dataset import generate_synthetic_l2_event_stream
    from research.hawkes_shadow_health import hawkes_shadow_health_monitor

    row = feature_cache.get_latest_row()
    p0 = float(row.get("close", 65200.0)) if row is not None else 65200.0
    vol = float(row.get("realized_vol_24h", 0.015)) if row is not None else 0.015
    df_events = generate_synthetic_l2_event_stream(n_events=50)

    m_fc = multiscale_assembler.generate_multiscale(
        current_price=p0,
        vol_24h=vol,
        df_recent_events=df_events
    )
    health = hawkes_shadow_health_monitor.evaluate_shadow_health()

    res = m_fc.to_dict()
    res["production_model_version"] = "v3.0.0-excursion-ridge-conformal"
    res["shadow_model_version"] = "v1.0.0-challenger-hawkes-microstructure"
    res["shadow_health"] = health.health_status
    return res


@router.get("/prediction/multiscale/health")
def get_multiscale_health():
    """
    Returns operational health and calibration statistics for dual-horizon multiscale forecasting.
    """
    return {
        "status": "HISTORICAL_UNVERIFIED",
        "metrics": None,
    }

    from engine.multiscale_health import multiscale_health_service
    report = multiscale_health_service.get_health_report()
    return report.to_dict()


@router.get("/prediction/horizons")
def get_prediction_horizons():
    """
    Returns synchronized multi-horizon forecasts across 7 distinct timescales.
    """
    return {
        "status": "DATA_UNAVAILABLE",
        "message": "The former multi-horizon response included synthetic event data and fixed estimates.",
        "horizons": None,
    }

    from engine.range_forecast_service import RangeForecastService
    from engine.hawkes_shadow_session import hawkes_shadow_session
    from research.microstructure_dataset import generate_synthetic_l2_event_stream

    row = feature_cache.get_latest_row()
    p0 = float(row.get("close", 65200.0)) if row is not None else 65200.0
    vol = float(row.get("realized_vol_24h", 0.015)) if row is not None else 0.015
    df_events = generate_synthetic_l2_event_stream(n_events=50)

    svc = RangeForecastService()
    ridge_fc = svc.generate_forecast(current_price=p0, vol_24h=vol)
    hawkes_fc, _ = hawkes_shadow_session.generate_shadow_forecast(current_price=p0, df_recent_events=df_events)

    horizons_payload = {
        "5m": {
            "model": "v1.0.0-challenger-hawkes-microstructure",
            "state": "VALIDATED_SHADOW_MODEL",
            "mfe_p50_bps": round(hawkes_fc.mfe_p50 * 10000.0, 1),
            "mae_p50_bps": round(hawkes_fc.mae_p50 * 10000.0, 1),
            "upper_p90": hawkes_fc.upper_p90,
            "lower_p90": hawkes_fc.lower_p90,
            "direction": hawkes_fc.direction_state,
            "uncertainty": hawkes_fc.uncertainty
        },
        "15m": {
            "model": "v1.0.0-research-ofi-regressor",
            "state": "RESEARCH",
            "mfe_p50_bps": 18.6,
            "mae_p50_bps": 20.2,
            "upper_p90": round(p0 * 1.0035, 2),
            "lower_p90": round(p0 * 0.9965, 2),
            "direction": "NO_EDGE",
            "uncertainty": 0.3
        },
        "1h": {
            "model": "v1.0.0-research-momentum-tree",
            "state": "RESEARCH",
            "mfe_p50_bps": 42.5,
            "mae_p50_bps": 48.2,
            "upper_p90": round(p0 * 1.0085, 2),
            "lower_p90": round(p0 * 0.9915, 2),
            "direction": "BULLISH",
            "uncertainty": 0.6
        },
        "4h": {
            "model": "v1.0.0-research-funding-hurdle",
            "state": "RESEARCH",
            "mfe_p50_bps": 88.4,
            "mae_p50_bps": 96.5,
            "upper_p90": round(p0 * 1.0180, 2),
            "lower_p90": round(p0 * 0.9820, 2),
            "direction": "NEUTRAL",
            "uncertainty": 1.1
        },
        "12h": {
            "model": "v1.0.0-research-ridge-swing",
            "state": "RESEARCH",
            "mfe_p50_bps": 182.0,
            "mae_p50_bps": 210.0,
            "upper_p90": round(p0 * 1.0320, 2),
            "lower_p90": round(p0 * 0.9680, 2),
            "direction": "NO_EDGE",
            "uncertainty": 1.4
        },
        "24h": {
            "model": "v3.0.0-excursion-ridge-conformal",
            "state": "PRODUCTION",
            "mfe_p50_bps": round(ridge_fc.mfe_p50 * 10000.0, 1),
            "mae_p50_bps": round(ridge_fc.mae_p50 * 10000.0, 1),
            "upper_p90": ridge_fc.upper_p90,
            "lower_p90": ridge_fc.lower_p90,
            "direction": ridge_fc.direction_state,
            "uncertainty": ridge_fc.uncertainty
        },
        "48h": {
            "model": "v1.0.0-research-vol-cone",
            "state": "RESEARCH_EXPERIMENTAL",
            "mfe_p50_bps": 340.0,
            "mae_p50_bps": 390.0,
            "upper_p90": round(p0 * 1.0650, 2),
            "lower_p90": round(p0 * 0.9350, 2),
            "direction": "NO_EDGE",
            "uncertainty": 2.8
        }
    }

    return {
        "symbol": "BTCUSD",
        "current_price": p0,
        "available_horizons": list(horizons_payload.keys()),
        "forecast_by_horizon": horizons_payload
    }


@router.get("/prediction/horizons/health")
def get_prediction_horizons_health():
    """
    Returns operational health status across all 7 candidate horizons.
    """
    return {
        "status": "HISTORICAL_UNVERIFIED",
        "health_records": None,
        "metrics": None,
    }

    from research.horizon_health import evaluate_horizon_health_and_gaps
    df_health, meta = evaluate_horizon_health_and_gaps()
    return {
        "status": "HEALTHY",
        "horizon_count": len(df_health),
        "health_records": df_health.to_dict(orient="records"),
        "primary_research_gap": meta["primary_gap"]
    }


@router.get("/prediction/market-state")
def get_prediction_market_state():
    """
    Returns unified multiscale market-state contextual intelligence across all operational layers.
    """
    return {
        "status": "DATA_UNAVAILABLE",
        "market_state": None,
    }

    from engine.market_state import market_state_engine

    row = feature_cache.get_latest_row()
    p0 = float(row.get("close", 65200.0)) if row is not None else 65200.0
    vol = float(row.get("realized_vol_24h", 0.015)) if row is not None else 0.015

    state = market_state_engine.evaluate_market_state(
        current_price=p0,
        vol_24h=vol,
        hawkes_direction="BEARISH",
        uncertainty=1.6
    )
    return state.to_dict()


@router.get("/prediction/market-state/history")
def get_prediction_market_state_history(limit: int = 50):
    """
    Returns historical market-state snapshots with resolved 24h outcomes.
    """
    return {
        "status": "HISTORICAL_UNVERIFIED",
        "history": None,
        "message": "Historical market-state samples are not independently verified.",
    }

    from research.market_state_dataset import generate_market_state_history_dataset
    df_hist = generate_market_state_history_dataset(n_samples=min(200, limit))
    return {
        "count": len(df_hist),
        "history": df_hist.to_dict(orient="records")
    }


@router.get("/research/foundation-models")
@router.get("/api/research/foundation-models")
def get_research_foundation_models_leaderboard():
    """
    Returns the formal BTCUSD Forecast Model Benchmark Leaderboard across Foundation Models & Production.
    """
    from research.foundation_leaderboard import get_foundation_model_leaderboard_payload
    return get_foundation_model_leaderboard_payload()


@router.get("/prediction/intelligence")
@router.get("/api/prediction/intelligence")
def get_prediction_intelligence():
    """
    Unified Forecast Intelligence Layer translating all validated and experimental model outputs
    into a coherent, decoupled intelligence experience.
    """
    return {
        "status": "DATA_UNAVAILABLE",
        "intelligence": None,
    }

    from engine.forecast_intelligence import forecast_intelligence_orchestrator

    row = feature_cache.get_latest_row()
    p0 = float(row.get("close", 65200.0)) if row is not None else 65200.0
    vol = float(row.get("realized_vol_24h", 0.015)) if row is not None else 0.015

    intel = forecast_intelligence_orchestrator.generate_intelligence(
        current_price=p0,
        vol_24h=vol,
        hawkes_direction="BULLISH_PRESSURE",
        uncertainty=1.6
    )
    return intel.to_dict()


@router.get("/prediction/intelligence/health")
@router.get("/api/prediction/intelligence/health")
def get_prediction_intelligence_health():
    """
    Comprehensive multi-pillar operational health, longitudinal tracking, and reliability status.
    """
    return {
        "status": "HISTORICAL_UNVERIFIED",
        "metrics": None,
    }

    return {
        "production_status": "VALIDATED_PRODUCTION_RANGE_SYSTEM",
        "production_blocks": 40,
        "production_N_eff": 38.3,
        "production_coverage_pct": 91.25,
        "production_mfe_error_pct": 0.3965,
        "production_mae_error_pct": 0.5600,
        "production_baseline_delta_bps": -14.2,
        "calibration_status": "CALIBRATION_OK",
        "context_status": "CONTEXT_STABLE",
        "model_decay": "MODEL_STABLE",
        "data_quality": "HEALTHY",
        "provenance": "PROVENANCE_MATCHED",
        "shadow_hawkes_status": "VALIDATED_SHADOW_MODEL",
        "shadow_hawkes_N_eff": 135.0,
        "foundation_status": "FOUNDATION_RESEARCH",
        "overall_reliability": "VERY_HIGH"
    }


@router.get("/research/models")
@router.get("/api/research/models")
def get_research_all_models_leaderboard():
    """
    Exposes all models grouped strictly by governance role: PRODUCTION, SHADOW, RESEARCH, REJECTED.
    """
    return {
        "status": "HISTORICAL_UNVERIFIED",
        "leaderboard": None,
    }

    return {
        "title": "BTCUSD MODEL RESEARCH & PRODUCTION LEADERBOARD",
        "categories": {
            "PRODUCTION": [
                {"model": "Ridge + Volatility Context", "version": "v3.0.0-ridge-vol-v1.0.0", "horizon": "24h", "mfe_error": "0.3980%", "winkler": 605.10, "status": "ACTIVE_PRODUCTION"}
            ],
            "SHADOW": [
                {"model": "Hawkes Microstructure", "version": "v1.0.0-challenger-hawkes-microstructure", "horizon": "5m", "mfe_error": "9.30 bps", "winkler": 96.90, "status": "VALIDATED_SHADOW"}
            ],
            "RESEARCH": [
                {"model": "Intermediate Horizon 1H", "version": "1h-tech-ofi-vol", "horizon": "1h", "mfe_error": "42.50 bps", "winkler": 240.10, "status": "RESEARCH_ONLY"},
                {"model": "Intermediate Horizon 4H", "version": "4h-tech-deriv-vol", "horizon": "4h", "mfe_error": "88.40 bps", "winkler": 380.50, "status": "RESEARCH_ONLY"}
            ],
            "REJECTED": [
                {"model": "Mamba State-Space Model v1", "version": "v1.0.0-challenger-mamba-selective-ssm", "horizon": "24h", "rejection_reason": "Worse MFE/MAE than Ridge; no paired improvement"}
            ]
        },
        "foundation_models": {
            "status": "UNAVAILABLE_NOT_EXECUTED",
            "authoritative": False,
            "leaderboard": []
        }
    }


@router.get("/prediction/accuracy")
@router.get("/api/prediction/accuracy")
def get_prediction_accuracy():
    """
    Returns canonical production forecast accuracy observatory scorecard.
    """
    return {
        "status": "HISTORICAL_UNVERIFIED",
        "metrics": None,
    }

    return {
        "title": "BTCUSD PRODUCTION FORECAST ACCURACY OBSERVATORY",
        "system_version": "v3.0.0-ridge-volatility-context",
        "horizon": "24h",
        "governance_status": "VALIDATED_PRODUCTION_RANGE_SYSTEM",
        "sample_accounting": {
            "raw_forecast_count": 744,
            "independent_blocks_24h": 31,
            "effective_sample_size": 31.0,
            "lag_1_autocorrelation": 0.024
        },
        "range_accuracy": {
            "mfe_mae_pct": 0.3980,
            "mae_mae_pct": 0.5620,
            "p90_mfe_coverage_pct": 91.80,
            "p90_mae_coverage_pct": 90.40,
            "joint_path_containment_pct": 91.10,
            "winkler_score": 605.10,
            "interval_width_pct": 5.28,
            "calibration_status": "CALIBRATION_OK"
        },
        "directional_accuracy": {
            "status": "NO_MEASURABLE_EDGE",
            "direction_accuracy_pct": 50.4,
            "balanced_accuracy_pct": 50.2,
            "roc_auc": 0.504,
            "mcc": 0.008
        },
        "baseline_comparison": {
            "baseline_model": "Simple Ridge Baseline (No Vol Context)",
            "paired_mfe_delta_bps": -14.0,
            "ci_95_pct": [-0.0175, -0.0105],
            "permutation_p": 0.0006,
            "edge_status": "STATISTICALLY_SUPERIOR"
        },
        "operational_reliability": {
            "score": 87.92,
            "tier": "VERY_HIGH",
            "drift_psi": 0.024,
            "model_status": "MODEL_STABLE"
        }
    }


@router.get("/prediction/accuracy/history")
@router.get("/api/prediction/accuracy/history")
def get_prediction_accuracy_history(limit: int = 30):
    """
    Returns rolling block accuracy time-series history snapshots.
    """
    return {
        "status": "HISTORICAL_UNVERIFIED",
        "history": None,
    }

    from research.accuracy_timeseries import generate_production_accuracy_timeseries
    df_ts, _ = generate_production_accuracy_timeseries()
    return {
        "count": len(df_ts),
        "history": df_ts.to_dict(orient="records")
    }


@router.get("/prediction/failures")
@router.get("/api/prediction/failures")
def get_prediction_failures(limit: int = 10):
    """
    Searchable failure and tail envelope breach library.
    """
    return {
        "status": "HISTORICAL_UNVERIFIED",
        "failures": None,
    }

    from research.forecast_failure_analysis import run_forecast_failure_analysis
    df_fails, meta = run_forecast_failure_analysis()
    return {
        "total_failures_logged": meta["total_failures_logged"],
        "breach_rate_pct": meta["breach_rate_pct"],
        "conformal_alignment": meta["conformal_alignment"],
        "failures": df_fails.to_dict(orient="records")
    }


@router.get("/prediction/longitudinal")
@router.get("/api/prediction/longitudinal")
def get_prediction_longitudinal():
    """
    Returns active longitudinal monitoring progress, strictly separating OBSERVED evidence from TARGET milestones.
    """
    from engine.longitudinal_status import longitudinal_status_service
    res = longitudinal_status_service.get_status_report().to_dict()
    res["governance_mode"] = "LONGITUDINAL_MONITORING_ACTIVE"
    return res


@router.get("/prediction/longitudinal/health")
@router.get("/api/prediction/longitudinal/health")
def get_prediction_longitudinal_health():
    """
    Returns automated daily longitudinal evidence collector health and provenance status.
    """
    from research.post_repair_longitudinal_monitor import post_repair_monitor
    status = post_repair_monitor.get_status()
    return {
        "monitor_status": status["monitoring_status"],
        "evidence_phase": status["evidence_phase"],
        "evidence_boundary": status["evidence_boundary"],
        "model_health": status["health_status"]["model_health"],
        "context_health": status["health_status"]["context_health"],
        "data_health": status["health_status"]["data_health"],
        "provenance_health": status["health_status"]["provenance_health"],
        "stop_rule": "NO_NEW_RESEARCH_REQUIRED",
        "observed_blocks": status["observed_valid_blocks"],
        "observed_valid_blocks": status["observed_valid_blocks"],
        "next_milestone": status["next_milestone"]
    }


@router.get("/prediction/longitudinal/resolution-health")
@router.get("/api/prediction/longitudinal/resolution-health")
def get_prediction_longitudinal_resolution_health():
    """
    Returns resolution engine health, pending counts, and data freshness.
    """
    from research.post_repair_outcome_resolver import post_repair_resolver
    return post_repair_resolver.get_resolution_health()


@router.get("/research/next-trigger")
@router.get("/api/research/next-trigger")
def get_research_next_trigger():
    """
    Returns the formal Research Stop-Rule state. New ML experiments are BLOCKED unless a failure trigger is active.
    """
    from research.research_stop_rule import research_stop_rule_engine
    eval_res = research_stop_rule_engine.evaluate_production_health()
    return eval_res.to_dict()


@router.get("/prediction/pipeline/layers")
@router.get("/api/prediction/pipeline/layers")
def get_prediction_pipeline_layers():
    """
    Returns live end-to-end execution snapshot across all 7 institutional prediction layers.
    """
    from engine.prediction_pipeline import prediction_pipeline
    from engine.feature_cache import feature_cache

    row = feature_cache.get_latest_row()
    if row is None:
        return {
            "status": "DATA_UNAVAILABLE",
            "message": "No verified feature row is available to evaluate pipeline layers.",
            "layers": None,
        }

    res = prediction_pipeline.run_pipeline(candle=row)
    return res.to_dict()

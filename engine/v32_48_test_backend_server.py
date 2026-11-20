"""
engine/v32_48_test_backend_server.py — Isolated FastAPI Backend for V32.48 Browser QA
====================================================================================
Governance & Testing Invariants:
1. Real execution of execute_integrated_analyse_and_tournament() during Analyse.
2. Complete 1-to-7 workflow without a mandatory second click for tournament backtesting.
3. Isolated temporary directory for Smart Entry ledger to ensure zero writes to protected files.
4. Test-control endpoints for controlled candle fixtures, stale feed injection, and AI anomaly monitoring.
5. Server-side event counters to verify request traces and ensure zero trade attempts during Analyse.
6. Serves static frontend assets from web/ mounted at root.
"""

import os
import sys
import json
import uuid
import math
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import pandas as pd
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from engine.regime_strategy_tournament import (
    analyse_current_market,
    run_strategy_tournament_backtest,
    formulate_smart_entry_decision,
    execute_integrated_analyse_and_tournament,
    VersionedStrategyRegistry
)
from engine.smart_entry_simulator import SmartEntrySimulator

# Create temp isolation directories for test execution
TEST_DIR = tempfile.mkdtemp(prefix="btcog_v32_48_qa_")
SMART_ENTRY_LEDGER = os.path.join(TEST_DIR, "test_smart_entry_attempts.jsonl")
PAPER_LEDGER_PATH = os.path.join(TEST_DIR, "test_paper_execution_ledger.jsonl")

# Initialize test simulator instance with dedicated test ledger
test_simulator = SmartEntrySimulator(ledger_file=SMART_ENTRY_LEDGER)

app = FastAPI(title="BTCognitive V32.48 QA Test Backend", version="32.48.0")

# Server-side counters and state
counters = {
    "analyse_calls": 0,
    "tournament_executions": 0,
    "attempts_created": 0,
    "duplicate_blocked": 0
}

state = {
    "is_stale_mode": False,
    "degraded_data_mode": False,
    "custom_candles": None,
    "last_analysis": None,
    "last_tournament": None,
    "last_decision": None,
    "last_tournament_req_hash": None,
    "last_tournament_req_time": 0.0,
    "paper_positions": [
        {
            "id": "paper_pos_1",
            "strategy_id": "MEIE-VOL-EXPANSION",
            "entry_price": 80500.0,
            "current_price": 81200.0,
            "unrealized_pnl_usd": 700.0,
            "status": "OPEN",
            "research_sleeve": "GATED_TIER_2"
        }
    ],
    "manual_journal": []
}


import numpy as np

def _build_bullish_fixture(n_bars: int = 250, target_close: float = 80300.0) -> pd.DataFrame:
    np.random.seed(4248)
    base_price = 75000.0
    dates = pd.date_range("2026-09-01", periods=n_bars, freq="1h", tz="UTC")
    returns = np.full(n_bars, 0.0015)
    vol = 0.015
    noise = np.random.normal(0, vol, n_bars)
    prices = base_price * np.exp(np.cumsum(returns + noise))
    scale = target_close / prices[-1]
    prices = prices * scale
    highs = prices * (1.0 + np.abs(np.random.normal(0, vol * 0.5, n_bars)))
    lows = prices * (1.0 - np.abs(np.random.normal(0, vol * 0.5, n_bars)))
    opens = prices * (1.0 + np.random.normal(0, vol * 0.2, n_bars))
    closes = prices
    volumes = np.full(n_bars, 1200.0)
    return pd.DataFrame({
        "timestamp_utc": [d.isoformat() for d in dates],
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "is_closed": [True] * n_bars
    })

def _get_active_df_1h(live_price: float = 80300.0):
    if state["custom_candles"]:
        return pd.DataFrame(state["custom_candles"])
    return _build_bullish_fixture(250, target_close=live_price)


# ---------------------------------------------------------------------------
# Health & Status Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
@app.get("/api/health")
def get_health():
    return {
        "status": "ok",
        "application": "BTCognitive BTC/USD Market Monitor (V32.48 QA Test Instance)",
        "product_mode": "ANALYSIS_ONLY",
        "mode": "PRODUCTION_VOLATILITY_INTELLIGENCE",
        "live_trading_enabled": False,
        "order_submission_enabled": False,
        "price_forecast_status": "AVAILABLE",
        "research_status": "AUTHORIZED_FOR_PRODUCTION",
        "research_authorized": True,
        "trading_enabled": False,
        "system_status": {
            "service_status": "ONLINE",
            "market_data_status": "STALE" if state["is_stale_mode"] else ("DEGRADED" if state["degraded_data_mode"] else "LIVE"),
            "decision_anatomy_stage": "MONITORING"
        }
    }


@app.get("/market/latest")
@app.get("/api/terminal/live")
def get_market_latest():
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "timestamp_utc": now_iso,
        "price": 80603.99,
        "bid": 80602.50,
        "ask": 80604.50,
        "volume_24h": 12500.4,
        "source": "Coinbase Spot (Test Fixture)",
        "feed_status": "STALE" if state["is_stale_mode"] else ("DEGRADED" if state["degraded_data_mode"] else "FRESH"),
        "is_fresh": not state["is_stale_mode"]
    }


@app.get("/prediction/latest")
def get_prediction_latest():
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "status": "STALE" if state["is_stale_mode"] else "AVAILABLE",
        "timestamp_utc": now_iso,
        "model_id": "HAR-RS-DOW-v1.0",
        "target": "rv7d_var_ann",
        "horizon": "168h",
        "point_forecast": 0.5234,
        "risk_envelope_lower": 0.4120,
        "risk_envelope_upper": 0.6780,
        "nominal_coverage": 0.90,
        "empirical_validation_status": "VALIDATED",
        "market_regime": "VOL_EXPANDING"
    }


@app.get("/prediction/history")
def get_prediction_history(limit: int = 20):
    return {"predictions": [], "limit": limit}


@app.get("/regime/latest")
def get_regime_latest():
    return {
        "regime": "VOL_EXPANDING",
        "confidence": 0.88,
        "volatility_ratio_1h_24h": 1.25,
        "adx_14": 28.5,
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }


@app.get("/intelligence/latest")
def get_intelligence_latest():
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "regime": "VOL_EXPANDING",
        "risk_outlook": "BALANCED_RISK",
        "feed_quality": "STALE" if state["is_stale_mode"] else ("DEGRADED" if state["degraded_data_mode"] else "FRESH")
    }


@app.get("/api/terminal/status")
def get_terminal_status():
    active_count = len([a for a in test_simulator.attempts.values() if a.status == "ACTIVE"])
    return {
        "status": "ONLINE",
        "market_data_status": "MARKET_DATA_STALE" if state["is_stale_mode"] else ("DEGRADED" if state["degraded_data_mode"] else "LIVE"),
        "active_attempt_count": active_count,
        "paper_positions_count": len(state["paper_positions"]),
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/terminal/decision-anatomy")
def get_decision_anatomy():
    return {
        "stage": "MONITORING",
        "feed_status": "STALE" if state["is_stale_mode"] else ("DEGRADED" if state["degraded_data_mode"] else "FRESH"),
        "active_regime": "VOL_EXPANDING",
        "shortlisted_count": 2
    }


# ---------------------------------------------------------------------------
# Integrated Analyse & Tournament Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/tournament/candidates")
@app.get("/api/tournament/latest")
def get_tournament_candidates():
    if state["last_analysis"]:
        return state["last_analysis"]
    df = _get_active_df_1h()
    return analyse_current_market(df, live_price=80603.99)


@app.post("/api/tournament/analyse")
def post_tournament_analyse(req: Optional[Dict[str, Any]] = None):
    """
    Step 1 & 2 (or Full Integrated 1-to-7 Workflow):
    Analyses market and automatically runs tournament backtest when auto_tournament is True.
    Strict Invariant: DOES NOT create any simulated trade attempt.
    """
    counters["analyse_calls"] += 1
    
    live_p = (req or {}).get("live_price", 80603.99)
    df_1h = _get_active_df_1h(live_p)
    if req and req.get("candles"):
        df_1h = pd.DataFrame(req["candles"])
    enforce = (req or {}).get("enforce_freshness", False) or state["is_stale_mode"]
    max_age = (req or {}).get("max_age_hours", 2.0)
    auto_tourney = (req or {}).get("auto_tournament", True)
    fresh_tourney = (req or {}).get("force_fresh_tournament", False)

    if auto_tourney:
        counters["tournament_executions"] += 1
        integrated_res = execute_integrated_analyse_and_tournament(
            df_1h=df_1h,
            live_price=live_p,
            enforce_freshness=enforce,
            max_age_hours=max_age,
            force_fresh_tournament=fresh_tourney
        )
        state["last_analysis"] = integrated_res
        state["last_tournament"] = integrated_res.get("tournament")
        state["last_decision"] = integrated_res.get("decision")
        return integrated_res

    analysis_res = analyse_current_market(
        df_1h,
        live_price=live_p,
        enforce_freshness=enforce,
        max_age_hours=max_age
    )
    state["last_analysis"] = analysis_res
    return analysis_res


@app.post("/api/tournament/run")
@app.post("/api/tournament/run-tournament")
def post_tournament_run(req: Optional[Dict[str, Any]] = None):
    """
    Step 4: Manual/Re-run bounded tournament backtest.
    Includes anti-duplicate debouncing guard.
    """
    now = datetime.now(timezone.utc).timestamp()
    req_hash = str(req)
    if state["last_tournament_req_hash"] == req_hash and (now - state["last_tournament_req_time"]) < 2.5:
        counters["duplicate_blocked"] += 1
        return state["last_tournament"]

    counters["tournament_executions"] += 1
    state["last_tournament_req_hash"] = req_hash
    state["last_tournament_req_time"] = now

    analysis = state.get("last_analysis") or get_tournament_candidates()
    candidates = (req or {}).get("shortlisted_candidates") or analysis.get("shortlisted_candidates")
    regime = (req or {}).get("current_regime") or (analysis.get("market_regime", {}).get("regime") if isinstance(analysis.get("market_regime"), dict) else analysis.get("market_regime")) or "VOL_EXPANDING"
    force_fresh = (req or {}).get("force_fresh", False)

    res = run_strategy_tournament_backtest(candidates, current_regime=regime, force_fresh=force_fresh)
    state["last_tournament"] = res

    decision = formulate_smart_entry_decision(
        analysis_res=analysis,
        tournament_res=res
    )
    state["last_decision"] = decision
    return res


@app.get("/api/tournament/smart-entry/latest")
def get_smart_entry_latest():
    if state["is_stale_mode"]:
        return {
            "status": "NO_SMART_ENTRY",
            "action": "ABSTAIN",
            "reason": "Market data is stale (>2.0 hours). All entries blocked.",
            "candidate_setup": None
        }
    if state["last_decision"]:
        return state["last_decision"]
    
    # Run analysis + decision if not yet available
    df = _get_active_df_1h()
    analysis = analyse_current_market(df)
    decision = formulate_smart_entry_decision(analysis_res=analysis, tournament_res=state.get("last_tournament"))
    return decision


@app.post("/api/tournament/smart-entry/enter")
def post_smart_entry_enter(body: Dict[str, Any] = None):
    """Explicit Enter (Simulated) with locked levels and duplicate protection."""
    if state["is_stale_mode"]:
        raise HTTPException(status_code=400, detail="Cannot enter trade: Market data feed is stale.")

    dec = (body or {}).get("decision_payload") or state.get("last_decision")
    if not dec or dec.get("status") not in ("SMART_ENTRY_AVAILABLE", "SUCCESS"):
        raise HTTPException(status_code=400, detail="Cannot enter simulated trade: candidate decision is not SMART_ENTRY_AVAILABLE")

    p_ref = (body or {}).get("entry_price") or dec.get("candidate_setup", {}).get("entry_reference_price") or 80600.0
    idempotency_key = (body or {}).get("idempotency_key", str(uuid.uuid4()))

    att, err = test_simulator.enter_simulated_trade(
        decision_payload=dec,
        entry_price=p_ref,
        idempotency_key=idempotency_key
    )
    if err:
        raise HTTPException(status_code=400, detail=err)

    counters["attempts_created"] += 1
    return {"status": "SUCCESS", "action": "SIMULATED_ATTEMPT_CREATED", "attempt": att.to_dict()}


@app.post("/api/tournament/smart-entry/monitor")
def post_smart_entry_monitor(body: Optional[Dict[str, Any]] = None):
    req = body or {}
    target_id = req.get("attempt_id")
    if not target_id:
        active = [a for a in test_simulator.attempts.values() if a.status == "ACTIVE"]
        if active:
            target_id = active[0].attempt_id
        else:
            return {"status": "NO_ACTIVE_ATTEMPT", "attempt": None, "new_events": []}

    att, evts = test_simulator.monitor_active_attempt(
        attempt_id=target_id,
        current_price=req.get("current_price"),
        current_forecast=req.get("current_forecast"),
        data_quality_info=req.get("data_quality_info"),
        candle=req.get("candle"),
        hard_anomaly_trigger=req.get("hard_anomaly_trigger", False),
        hard_anomaly_reason=req.get("hard_anomaly_reason")
    )
    return {
        "status": "SUCCESS",
        "attempt": att.to_dict() if att else None,
        "new_events": evts
    }


@app.get("/api/tournament/smart-entry/attempts")
def get_smart_entry_attempts():
    attempts_list = [att.to_dict() for att in test_simulator.attempts.values()]
    attempts_list.sort(key=lambda x: x.get("entered_at_utc", ""), reverse=True)
    active = [a for a in attempts_list if a.get("status") == "ACTIVE"]
    resolved = [a for a in attempts_list if a.get("status") != "ACTIVE"]

    return {
        "status": "SUCCESS",
        "total_attempts": len(attempts_list),
        "total_active": len(active),
        "total_resolved": len(resolved),
        "active_attempts": active,
        "resolved_attempts": resolved,
        # Legacy frontend compatibility
        "history": attempts_list,
        "total_history": len(attempts_list)
    }


@app.post("/api/tournament/smart-entry/attempts/{attempt_id}/exit")
def post_smart_entry_exit(attempt_id: str, body: Optional[Dict[str, Any]] = None):
    exit_p = (body or {}).get("exit_price", 80900.0)
    reason = (body or {}).get("reason", "USER_REQUESTED_EXIT")
    att, err = test_simulator.user_exit_now(attempt_id, exit_price=exit_p, reason=reason)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"status": "SUCCESS", "action": "USER_EXITED_EARLY", "result": att.to_dict(), "attempt": att.to_dict()}


@app.post("/api/tournament/smart-entry/attempts/{attempt_id}/partial-exit")
def post_smart_entry_partial_exit(attempt_id: str, body: Optional[Dict[str, Any]] = None):
    exit_p = (body or {}).get("exit_price", 81500.0)
    ratio = (body or {}).get("ratio", 0.5)
    att, err = test_simulator.user_partial_exit(attempt_id, exit_price=exit_p, ratio=ratio)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"status": "SUCCESS", "action": "PARTIAL_EXIT_RECORDED", "result": att.to_dict(), "attempt": att.to_dict()}


@app.post("/api/tournament/smart-entry/attempts/{attempt_id}/anomaly-exit")
def post_smart_entry_anomaly_exit(attempt_id: str, body: Optional[Dict[str, Any]] = None):
    exit_p = (body or {}).get("exit_price", 80200.0)
    reason = (body or {}).get("reason", "QUALIFYING_ANOMALY_TRIGGERED")
    att, err = test_simulator.trigger_anomaly_exit(attempt_id, exit_price=exit_p, reason=reason)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"status": "SUCCESS", "action": "EXITED_ANOMALY", "attempt": att.to_dict()}


@app.get("/api/tournament/smart-entry/evaluation")
def get_smart_entry_evaluation():
    return test_simulator.get_evaluation_summary()


@app.get("/api/tournament/registry")
def get_tournament_registry():
    entries = VersionedStrategyRegistry.get_all_entries()
    return {
        "status": "SUCCESS",
        "governance": "OFFLINE_RESEARCH_ONLY",
        "total_registered": len(entries),
        "registered_strategies": [
            {"strategy_id": k, "name": v.strategy_name, "version": v.strategy_version}
            for k, v in entries.items()
        ]
    }


# ---------------------------------------------------------------------------
# Paper Trading Endpoints (Isolated Simulated Execution Sleeve)
# ---------------------------------------------------------------------------
@app.get("/api/research/paper-trading/status")
def get_paper_trading_status():
    return {
        "status": "ACTIVE_RESEARCH_SLEEVE",
        "engine_label": "RESEARCH ONLY · SIMULATED EXECUTION",
        "isolated_ledger": PAPER_LEDGER_PATH,
        "active_positions_count": len(state["paper_positions"]),
        "modeled_frictions": {
            "slippage_bps": 5.0,
            "commission_bps": 15.0,
            "latency_ms": 120.0
        }
    }


@app.get("/api/research/paper-trading/portfolio")
def get_paper_trading_portfolio():
    return {
        "portfolio_equity_usd": 100000.0,
        "unrealized_pnl_usd": 700.0,
        "realized_pnl_usd": 1420.0,
        "active_positions": state["paper_positions"]
    }


@app.get("/api/research/paper-trading/ledger")
def get_paper_trading_ledger(limit: int = 50):
    records = []
    if os.path.exists(PAPER_LEDGER_PATH):
        with open(PAPER_LEDGER_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line.strip()))
    return {"records": records[-limit:], "total_records": len(records)}


@app.get("/api/research/paper-trading/gbdt-evaluation")
def get_paper_trading_gbdt_evaluation(limit: int = 20):
    return {
        "evaluations": [],
        "sample_size": 45,
        "brier_score": 0.182,
        "research_only": True
    }


# ---------------------------------------------------------------------------
# User Position & Manual Journal Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/user/positions")
def get_user_positions():
    return {"positions": []}


@app.get("/api/manual-journal/trades")
def get_manual_journal_trades():
    return {"trades": state["manual_journal"]}


@app.post("/api/manual-journal/trades")
def post_manual_journal_trade(trade: Dict[str, Any]):
    trade_id = str(uuid.uuid4())[:8]
    record = {
        "trade_id": trade_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "is_manual_entry": True,
        **trade
    }
    state["manual_journal"].append(record)
    return {"status": "RECORDED", "trade": record}


# ---------------------------------------------------------------------------
# Test Control & Adversarial Injection Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/test-control/counters")
def get_counters():
    return {
        **counters,
        "active_attempts_count": len([a for a in test_simulator.attempts.values() if a.status == "ACTIVE"]),
        "total_simulator_attempts": len(test_simulator.attempts)
    }


@app.post("/api/test-control/toggle-stale")
def toggle_stale_data(req: Optional[Dict[str, Any]] = None, is_stale: Optional[bool] = None):
    if req is not None and "is_stale" in req:
        state["is_stale_mode"] = bool(req["is_stale"])
    elif is_stale is not None:
        state["is_stale_mode"] = bool(is_stale)
    else:
        state["is_stale_mode"] = True
    return {"is_stale_mode": state["is_stale_mode"]}


@app.post("/api/test-control/toggle-degraded")
def toggle_degraded_data(req: Optional[Dict[str, Any]] = None, is_degraded: Optional[bool] = None):
    if req is not None and "is_degraded" in req:
        state["degraded_data_mode"] = bool(req["is_degraded"])
    elif is_degraded is not None:
        state["degraded_data_mode"] = bool(is_degraded)
    else:
        state["degraded_data_mode"] = True
    return {"degraded_data_mode": state["degraded_data_mode"]}


@app.post("/api/test-control/inject-anomaly")
async def inject_anomaly_into_active(request: Request, body: Optional[Dict[str, Any]] = None, anomaly_type: Optional[str] = None):
    """Injects an AI anomaly into the active attempt without moving TP/SL."""
    try:
        data = await request.json()
    except Exception:
        data = body or {}
    anom = (data or {}).get("anomaly_type") or (body or {}).get("anomaly_type") or anomaly_type or "DIRECTION_REVERSAL"
    active = [a for a in test_simulator.attempts.values() if a.status == "ACTIVE"]
    if not active:
        raise HTTPException(status_code=400, detail="No active attempt to inject anomaly into")
    att = active[0]

    if anom == "DIRECTION_REVERSAL":
        att, evts = test_simulator.monitor_active_attempt(
            attempt_id=att.attempt_id,
            current_forecast={"direction": "DOWN", "probability_down": 0.85, "volatility": 35.0}
        )
    elif anom == "RISK_SPIKE":
        att, evts = test_simulator.monitor_active_attempt(
            attempt_id=att.attempt_id,
            current_forecast={"volatility": 85.0, "forecast_risk": 85.0, "direction": "UP"}
        )
    return {"status": "ANOMALY_INJECTED", "attempt": att.to_dict(), "events": evts}


@app.post("/api/test-control/reset")
def reset_test_state():
    state["is_stale_mode"] = False
    state["degraded_data_mode"] = False
    state["last_analysis"] = None
    state["last_tournament"] = None
    state["last_decision"] = None
    state["custom_candles"] = None
    for k in counters:
        counters[k] = 0
    test_simulator.attempts.clear()
    test_simulator.active_attempt = None
    if os.path.exists(SMART_ENTRY_LEDGER):
        try:
            os.remove(SMART_ENTRY_LEDGER)
        except Exception:
            pass
    return {"status": "RESET_COMPLETE"}


# ---------------------------------------------------------------------------
# WebSocket Support (/ws)
# ---------------------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_text(json.dumps({
                "type": "HEARTBEAT",
                "service": "ONLINE",
                "timestamp_utc": datetime.now(timezone.utc).isoformat()
            }))
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Mount Static Frontend
# ---------------------------------------------------------------------------
web_dir = os.path.join(REPO_ROOT, "web")
if os.path.isdir(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")


def run_test_server(port: int = 8094):
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8094
    print(f"Starting V32.48 QA Test Backend on port {port}...")
    run_test_server(port)

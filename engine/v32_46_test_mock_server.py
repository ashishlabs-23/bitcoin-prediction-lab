"""
engine/v32_46_test_mock_server.py — Deterministic Test Server for V32.46 Browser QA & Real Integration
======================================================================================================
Governance & Safety Invariants:
1. Zero live exchange network calls (no Coinbase, Binance, Kraken, or external HTTP requests).
2. Serves static frontend assets from web/ mounted at root.
3. Provides deterministic fixtures for AI forecasts, market regime, terminal status, and paper trading.
4. Uses temporary, isolated ledgers for Smart Entry and Paper Trading to verify storage isolation.
5. Implements full Smart Entry and Paper Trading lifecycle endpoints matching api/routes_tournament.py
   and api/routes_research.py.
6. Runs on configurable localhost port (default 8090) with WebSocket support.
"""

import os
import sys
import json
import uuid
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from engine.regime_strategy_tournament import (
    analyse_current_market,
    run_strategy_tournament_backtest,
    formulate_smart_entry_decision
)
from engine.smart_entry_simulator import SmartEntrySimulator

# Create temp isolation directories for test execution
TEST_DIR = tempfile.mkdtemp(prefix="btcog_v32_46_qa_")
SMART_ENTRY_LEDGER = os.path.join(TEST_DIR, "test_smart_entry_attempts.jsonl")
PAPER_LEDGER_PATH = os.path.join(TEST_DIR, "test_paper_execution_ledger.jsonl")

# Initialize test simulator instance with dedicated test ledger
test_simulator = SmartEntrySimulator(ledger_file=SMART_ENTRY_LEDGER)

app = FastAPI(title="BTCognitive V32.46 QA Mock Server", version="32.46.0")

# State holders
state = {
    "is_stale_mode": False,
    "last_analysis": None,
    "last_tournament": None,
    "last_decision": None,
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

# ---------------------------------------------------------------------------
# Health & Status Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
@app.get("/api/health")
def get_health():
    return {
        "status": "ok",
        "application": "BTCognitive BTC/USD Market Monitor (QA Test Instance)",
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
            "market_data_status": "STALE" if state["is_stale_mode"] else "LIVE",
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
        "source": "Coinbase Spot (Mocked Fixture)",
        "feed_status": "STALE" if state["is_stale_mode"] else "FRESH",
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
        "feed_quality": "STALE" if state["is_stale_mode"] else "FRESH"
    }

@app.get("/api/terminal/status")
def get_terminal_status():
    active_count = len([a for a in test_simulator.attempts.values() if a.status == "ACTIVE"])
    return {
        "status": "ONLINE",
        "market_data_status": "MARKET_DATA_STALE" if state["is_stale_mode"] else "LIVE",
        "active_attempt_count": active_count,
        "paper_positions_count": len(state["paper_positions"]),
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/terminal/decision-anatomy")
def get_decision_anatomy():
    return {
        "stage": "MONITORING",
        "feed_status": "STALE" if state["is_stale_mode"] else "FRESH",
        "active_regime": "VOL_EXPANDING",
        "shortlisted_count": 2
    }

# ---------------------------------------------------------------------------
# Tournament & Smart Entry Endpoints (Real engine logic + Temp SQLite)
# ---------------------------------------------------------------------------
@app.get("/api/tournament/candidates")
@app.get("/api/tournament/latest")
def get_tournament_candidates():
    candidates = [
        {
            "strategy_id": "MEIE-VOL-EXPANSION",
            "strategy_name": "MEIE Volatility Expansion Breakout",
            "version": "3.2.0",
            "direction": "LONG",
            "holding_horizon_hours": 24,
            "compatible_regimes": ["VOL_EXPANDING"],
            "sample_provenance": "HISTORICAL_WALKFORWARD_SCREENING",
            "screen_7_of_10_passed": True,
            "screen_7_of_10": {
                "passed": True,
                "tp_hits": 8,
                "total": 10,
                "total_attempts": 10,
                "tp_rate": 0.80,
                "wilson_ci_95": (0.49, 0.94),
                "evidence_source": "HISTORICAL_WALKFORWARD_SCREENING",
                "explanation": "8 of last 10 historical walk-forward opportunities hit Take-Profit before Stop-Loss."
            },
            "proposed_geometry": {
                "reference_entry_price": 80600.0,
                "take_profit_price": 82500.0,
                "stop_loss_price": 79500.0,
                "proposed_tp_price": 82500.0,
                "proposed_sl_price": 79500.0,
                "reward_usd": 1900.0,
                "risk_usd": 1100.0,
                "reward_risk_ratio": 1.73,
                "max_holding_hours": 24,
                "anomaly_policy": "FAIL_CLOSED_ABSTAIN"
            }
        },
        {
            "strategy_id": "VR-MEAN-REVERSION",
            "strategy_name": "Volatility Risk Mean Reversion",
            "version": "2.1.0",
            "direction": "SHORT",
            "holding_horizon_hours": 12,
            "compatible_regimes": ["VOL_EXPANDING", "COMPRESSED_RANGE"],
            "sample_provenance": "HISTORICAL_WALKFORWARD_SCREENING",
            "screen_7_of_10_passed": True,
            "screen_7_of_10": {
                "passed": True,
                "tp_hits": 7,
                "total": 10,
                "total_attempts": 10,
                "tp_rate": 0.70,
                "wilson_ci_95": (0.40, 0.89),
                "evidence_source": "HISTORICAL_WALKFORWARD_SCREENING",
                "explanation": "7 of last 10 historical walk-forward opportunities hit Take-Profit before Stop-Loss."
            },
            "proposed_geometry": {
                "reference_entry_price": 80600.0,
                "take_profit_price": 81800.0,
                "stop_loss_price": 79800.0,
                "proposed_tp_price": 81800.0,
                "proposed_sl_price": 79800.0,
                "reward_usd": 1200.0,
                "risk_usd": 800.0,
                "reward_risk_ratio": 1.50,
                "max_holding_hours": 12,
                "anomaly_policy": "FAIL_CLOSED_ABSTAIN"
            }
        }
    ]
    return {
        "market_regime": {"regime": "VOL_EXPANDING"},
        "shortlisted_candidates": candidates,
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/tournament/analyse")
def post_tournament_analyse():
    """Analyse current market. Strictly read-only; zero trade attempts created."""
    res = get_tournament_candidates()
    state["last_analysis"] = res
    return {
        "analysis_status": "ANALYSIS_COMPLETE",
        "is_read_only": True,
        "market_regime": {"regime": "VOL_EXPANDING"},
        "shortlisted_candidates": res["shortlisted_candidates"],
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/tournament/run")
def post_tournament_run():
    """Runs 3-arm tournament backtest with transparent cache disclosure."""
    candidates = get_tournament_candidates()["shortlisted_candidates"]
    res = run_strategy_tournament_backtest(candidates, current_regime="VOL_EXPANDING")
    state["last_tournament"] = res
    
    # Formulate decision automatically after tournament
    analysis = state.get("last_analysis") or get_tournament_candidates()
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
    # Default initial state
    return {
        "status": "NO_SMART_ENTRY",
        "action": "ABSTAIN",
        "reason": "Tournament backtest not yet run. Run Analyse & Backtest to evaluate setup.",
        "candidate_setup": None
    }

@app.post("/api/tournament/smart-entry/enter")
def post_smart_entry_enter(body: Dict[str, Any] = None):
    """Explicit Enter (Simulated) with locked levels and duplicate protection."""
    if state["is_stale_mode"]:
        raise HTTPException(status_code=400, detail="Cannot enter trade: Market data feed is stale.")
    
    # Check if existing decision is valid or create qualifying candidate
    dec = state.get("last_decision")
    if not dec or dec.get("status") in ("NO_SMART_ENTRY", "ABSTAIN", "REJECTED"):
        dec = {
            "decision_id": "dec_mock_qualifying",
            "tournament_id": "tourn_mock_1",
            "market_regime": "VOL_EXPANDING",
            "status": "SMART_ENTRY_AVAILABLE",
            "action": "ENTER_SIMULATED",
            "candidate_setup": {
                "strategy_id": "MEIE-VOL-EXPANSION",
                "strategy_name": "MEIE Volatility Expansion Breakout",
                "strategy_version": "3.2.0",
                "entry_reference_price": 80600.0,
                "proposed_tp_price": 82500.0,
                "proposed_sl_price": 79500.0,
                "max_duration_hours": 24.0,
                "anomaly_policy": "ADX_COLLAPSE_BELOW_15",
                "forecast_snapshot": {"point_forecast": 0.5234, "timestamp": datetime.now(timezone.utc).isoformat()}
            }
        }
    
    idempotency_key = (body or {}).get("idempotency_key", str(uuid.uuid4()))
    att, err = test_simulator.enter_simulated_trade(
        decision_payload=dec,
        entry_price=80600.0,
        idempotency_key=idempotency_key
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"status": "SUCCESS", "attempt": att.to_dict()}

@app.get("/api/tournament/smart-entry/attempts")
def get_smart_entry_attempts():
    active = [a.to_dict() for a in test_simulator.attempts.values() if a.status == "ACTIVE"]
    history = [a.to_dict() for a in test_simulator.attempts.values()]
    return {
        "active_attempts": active,
        "history": history,
        "total_active": len(active),
        "total_history": len(history)
    }

@app.post("/api/tournament/smart-entry/attempts/{attempt_id}/exit")
def post_smart_entry_exit(attempt_id: str):
    att, err = test_simulator.user_exit_now(attempt_id, exit_price=80900.0, reason="USER_REQUESTED_EXIT")
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"status": "SUCCESS", "result": att.to_dict()}

@app.post("/api/tournament/smart-entry/attempts/{attempt_id}/partial-exit")
def post_smart_entry_partial_exit(attempt_id: str):
    att, err = test_simulator.user_partial_exit(attempt_id, exit_price=81500.0, ratio=0.5)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"status": "SUCCESS", "result": att.to_dict()}

@app.get("/api/tournament/smart-entry/evaluation")
def get_smart_entry_evaluation():
    return test_simulator.get_evaluation_summary()

@app.get("/api/tournament/registry")
def get_tournament_registry():
    return {
        "registered_strategies": [
            {"strategy_id": "MEIE-VOL-EXPANSION", "name": "MEIE Volatility Expansion", "version": "3.2.0"},
            {"strategy_id": "VR-MEAN-REVERSION", "name": "Volatility Risk Mean Reversion", "version": "2.1.0"}
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
# Adversarial & Testing Control Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/test-control/toggle-stale")
def toggle_stale_data(is_stale: bool = True):
    state["is_stale_mode"] = is_stale
    return {"is_stale_mode": state["is_stale_mode"]}

# ---------------------------------------------------------------------------
# WebSocket Support (/ws)
# ---------------------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Send periodic heartbeats
            await websocket.send_text(json.dumps({
                "type": "HEARTBEAT",
                "service": "ONLINE",
                "timestamp_utc": datetime.now(timezone.utc).isoformat()
            }))
            # Receive or wait
            msg = await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Mount Static Files from web/ at root
# ---------------------------------------------------------------------------
web_dir = os.path.join(REPO_ROOT, "web")
if os.path.isdir(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")


def run_test_server(port: int = 8090):
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    print(f"Starting V32.46 QA Mock Server on port {port}...")
    run_test_server(port)

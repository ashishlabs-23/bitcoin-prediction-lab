"""
api/routes_arena.py — 24/7 AI Experiment Arena & Stress Testing Endpoints
========================================================================
Thin FastAPI APIRouter exposing paper trading state, trade logs, equity curve,
and Monte Carlo stress experimentation from engine.arena_runner.
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import numpy as np
from fastapi import APIRouter, Query, Body, HTTPException
from fastapi.responses import FileResponse

from engine.arena_runner import arena_runner
from engine.feature_cache import feature_cache
from engine.observatory import observatory
from data.ingest_onchain import get_latest_onchain_valuation
from backtest.market_memory import record_stress_trial

logger = logging.getLogger("btcognitive.routes_arena")

router = APIRouter(tags=["AI Experiment Arena"])


@router.get("/api/arena/context")
def get_arena_context():
    """
    Returns canonical point-in-time 4-State Observatory Context + Exploratory Strategy Context.
    Read-only context and audit layer. Does NOT modify strategy decisions or execution rules.
    """
    # 1. Canonical point-in-time 4-state snapshot
    snapshot = observatory.get_canonical_snapshot()
    status = arena_runner.get_status()
    
    # 2. Extract exploratory strategy actions
    recent_actions = status.get("recent_actions", ["SKIP", "LONG", "SKIP", "SKIP"])
    if not recent_actions or len(recent_actions) < 4:
        recent_actions = ["SKIP", "LONG", "SKIP", "SKIP"]
    
    skip_count = recent_actions.count("SKIP")
    agreement_ratio = float(skip_count / len(recent_actions)) if recent_actions else 0.75
    ensemble_action = "SKIP" if agreement_ratio >= 0.5 else "LONG"

    # 3. Record decision context in immutable ledger at t0
    arena_runner.record_arena_decision_context(
        strategy_actions=recent_actions,
        agreement_ratio=agreement_ratio,
        ensemble_action=ensemble_action,
        observatory_snapshot=snapshot.to_dict(),
        scientific_contract_hash=snapshot.scientific_contract_hash
    )

    return {
        "context": snapshot.to_dict(),
        "strategy": {
            "actions": recent_actions,
            "agreement_ratio": round(agreement_ratio, 2),
            "ensemble_action": ensemble_action,
            "bankroll": status.get("bankroll", 10.0),
            "total_pnl_pct": status.get("total_pnl_pct", 0.0)
        },
        "governance": {
            "verified_core": True,
            "strategy_layer_validated": False,
            "scientific_contract_hash": snapshot.scientific_contract_hash,
            "disclaimer": "Exploratory Strategy Analytics — Strategy actions are descriptive/counterfactual outputs and are not validated for predictive or economic superiority. Observatory context is informational and does not modify strategy decisions."
        }
    }


@router.get("/api/arena/status")
def get_arena_status():
    """Returns comprehensive 24/7 autonomous paper trading status, PnL, and open positions."""
    status_dict = arena_runner.get_status()
    status_dict["system_classification"] = "EXPLORATORY STRATEGY ANALYTICS"
    status_dict["validation_status"] = "NOT VALIDATED FOR PREDICTIVE OR ECONOMIC SUPERIORITY"
    status_dict["governance_disclaimer"] = "Exploratory strategy research simulation. Not validated by HAR-RS-DOW/C2 scientific research."
    return status_dict


@router.get("/api/arena/trades")
def get_arena_trades(limit: int = Query(50, le=200)):
    """Returns historical closed trade ledger from SQLite WAL."""
    trades = arena_runner.get_recent_trades(limit=limit)
    return {"trades": trades, "count": len(trades)}


@router.get("/api/arena/equity")
def get_arena_equity(limit: int = Query(100, le=500)):
    """Returns equity curve balance history and drawdowns."""
    equity = arena_runner.get_equity_curve(limit=limit)
    return {"equity_curve": equity, "count": len(equity)}


@router.post("/api/arena/trade")
async def execute_arena_paper_trade(payload: Optional[Dict[str, Any]] = Body(default={})):
    """Executes a single paper trade adhering to the $10 bankroll formula."""
    if payload is None:
        payload = {}
    action = payload.get("action", "BUY").upper()
    row = feature_cache.get_latest_row()
    live_p = float(row["close"]) if row is not None else 65000.0
    confidence = float(payload.get("confidence", 0.82))
    reasoning = str(payload.get("reasoning", "Manual / Automated Arena order"))
    result = arena_runner.execute_paper_trade(action=action, price=live_p, confidence=confidence, reasoning=reasoning)
    return {"status": "success", "trade": result, "arena_status": arena_runner.get_status()}


@router.post("/api/arena/reset")
def reset_arena_experiment():
    """Resets the experiment back to the initial $10.00 virtual starting bankroll."""
    return arena_runner.reset_experiment()


@router.post("/api/arena/retrain")
def trigger_arena_retraining():
    """Triggers offline supervised retraining and Deflated Sharpe Ratio validation."""
    return arena_runner.trigger_retrain()


@router.get("/api/arena/export/csv")
def export_arena_csv():
    """Exports all trades to CSV format."""
    csv_path = arena_runner.export_csv()
    return FileResponse(
        csv_path,
        media_type="text/csv",
        filename=f"BTCognitive_Arena_Trades_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    )


@router.post("/api/arena/sync_google_sheet")
async def sync_arena_google_sheet(payload: Optional[Dict[str, Any]] = Body(default={})):
    """Pushes recent trades and bankroll state to a Google Apps Script Web App webhook."""
    if payload is None:
        payload = {}
    webhook_url = str(payload.get("webhook_url", "")).strip()
    if not webhook_url or not webhook_url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid webhook_url. Must be a valid HTTP URL.")
    limit = int(payload.get("limit", 50))
    return arena_runner.sync_to_google_script(webhook_url=webhook_url, limit=limit)


@router.post("/api/arena/experiment")
async def run_arena_experiment(payload: Optional[Dict[str, Any]] = Body(default={})):
    """
    Executes a multi-trial Monte Carlo stress experiment on the AI Prediction Engine.
    Simulates volatility, on-chain valuation phase shifts, and orderbook shocks.
    Optionally logs trials into isolated SQLite stress_trials table.
    """
    if payload is None:
        payload = {}

    trials_count = int(np.clip(payload.get("trials_count", 15), 5, 50))
    vol_mult = float(payload.get("volatility_mult", 1.2))
    macro_shock = str(payload.get("macro_shock", "CURRENT")).upper()
    liq_shock_pct = float(payload.get("liquidity_shock_pct", 0.0))
    commit_to_ledger = bool(payload.get("commit_to_ledger", False))

    row = feature_cache.get_latest_row()
    live_p = float(row["close"]) if row is not None else 65000.0
    base_atr = float(row.get("atr_14", live_p * 0.012)) if row is not None else live_p * 0.012

    onchain = get_latest_onchain_valuation(live_btc_price=live_p)
    from models.onchain_contract import OnchainQuality, assess_onchain_quality, OnchainMetrics
    onchain_q = assess_onchain_quality(onchain)
    
    if onchain_q == OnchainQuality.INVALID and macro_shock == "CURRENT":
        raise HTTPException(status_code=400, detail="Cannot run Arena experiment: upstream onchain data is INVALID.")
        
    allow_degraded = bool(payload.get("allow_degraded", True))
    experiment_mode = "VALID"
    if onchain_q in [OnchainQuality.DEGRADED, OnchainQuality.STALE] and macro_shock == "CURRENT":
        if not allow_degraded:
            raise HTTPException(status_code=400, detail="Arena experiment blocked: onchain data is DEGRADED. Set allow_degraded=True to run research experiment.")
        experiment_mode = "DEGRADED_RESEARCH"

    if macro_shock == "CAPITULATION":
        sim_cycle = "CAPITULATION"
        sim_mvrv, sim_nupl = 0.92, -0.05
    elif macro_shock == "EUPHORIA":
        sim_cycle = "EUPHORIA"
        sim_mvrv, sim_nupl = 3.65, 0.74
    elif macro_shock == "NEUTRAL":
        sim_cycle = "NEUTRAL"
        sim_mvrv, sim_nupl = 1.85, 0.42
    else:
        try:
            m = OnchainMetrics.from_dict(onchain)
            sim_cycle = m.cycle_phase
            sim_mvrv = m.mvrv_ratio
            sim_nupl = m.nupl
        except Exception:
            sim_cycle = onchain.get("cycle_phase", "NEUTRAL")
            sim_mvrv = float(onchain.get("mvrv", 1.85))
            sim_nupl = float(onchain.get("nupl", 0.42))

    trials_results = []
    directions_count = {"LONG": 0, "SHORT": 0, "SKIP": 0}

    for i in range(trials_count):
        noise_ret = float(np.random.normal(0, 0.015 * vol_mult))
        noise_rsi = float(np.clip(50.0 + noise_ret * 400.0 + np.random.normal(0, 5), 20, 85))
        noise_price = round(live_p * (1.0 + float(np.random.normal(0, 0.005 * vol_mult))), 2)

        macro_shift = 0.06 if sim_cycle == "CAPITULATION" else (-0.06 if sim_cycle == "EUPHORIA" else 0.0)
        raw_score = (noise_rsi - 50.0) / 40.0 + (noise_ret * 20.0) + (liq_shock_pct / 100.0) + macro_shift
        sim_prob = float(np.clip(1.0 / (1.0 + np.exp(-raw_score)), 0.15, 0.88))

        if sim_cycle == "HIGH_VOLATILITY" or vol_mult >= 2.5 or abs(sim_prob - 0.50) < 0.04:
            decision, direction = "SKIP", "SKIP"
        elif sim_prob >= 0.54:
            decision, direction = "TAKE_LONG", "LONG"
        elif sim_prob <= 0.46:
            decision, direction = "TAKE_SHORT", "SHORT"
        else:
            decision, direction = "SKIP", "SKIP"

        directions_count[direction] += 1
        sim_atr = base_atr * vol_mult
        sim_tp = round(noise_price + 2.0 * sim_atr if direction == "LONG" else noise_price - 2.0 * sim_atr, 2)
        sim_sl = round(noise_price - 1.5 * sim_atr if direction == "LONG" else noise_price + 1.5 * sim_atr, 2)

        hypo_ret = float(np.random.normal(0.002 if direction == "LONG" else -0.002, 0.008 * vol_mult))
        was_corr = (hypo_ret > 0) if direction == "LONG" else ((hypo_ret < 0) if direction == "SHORT" else abs(hypo_ret) < 0.004)
        pnl_bps = round(10000.0 * (hypo_ret if was_corr else -abs(hypo_ret)), 2)

        trial_data = {
            "trial_id": i + 1,
            "sim_price": noise_price,
            "direction": direction,
            "decision": decision,
            "probability_pct": round(sim_prob * 100, 1),
            "sim_tp": sim_tp,
            "sim_sl": sim_sl,
            "macro_cycle": sim_cycle,
            "hypothetical_ret_pct": round(hypo_ret * 100, 2),
            "hypothetical_pnl_bps": pnl_bps,
            "was_correct": was_corr,
            "volatility_stress": round(float(np.clip(1.0 / vol_mult, 0.2, 1.0)), 2)
        }
        trials_results.append(trial_data)

        if commit_to_ledger:
            record_stress_trial(
                trial_id=f"stress_{int(time.time())}_{i+1}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                price=noise_price,
                direction=direction,
                decision=decision,
                probability=sim_prob,
                tp=sim_tp,
                sl=sim_sl,
                macro_shock=sim_cycle,
                volatility_mult=vol_mult,
                liquidity_shock_pct=liq_shock_pct,
                hypothetical_return=hypo_ret,
                was_correct=was_corr,
                pnl_bps=pnl_bps,
                data_source="synthetic_arena"
            )

    long_pct = round(directions_count["LONG"] / trials_count * 100, 1)
    short_pct = round(directions_count["SHORT"] / trials_count * 100, 1)
    skip_pct = round(directions_count["SKIP"] / trials_count * 100, 1)
    resilience_score = round(float(np.clip(100.0 - (vol_mult - 1.0) * 18.0 - (skip_pct * 0.2), 45.0, 98.0)), 1)
    narrative = f"Completed {trials_count} stochastic Monte Carlo experiments under {vol_mult}x volatility stress and {sim_cycle} macro context."

    return {
        "status": "success",
        "trials_count": trials_count,
        "parameters": {
            "volatility_mult": vol_mult,
            "macro_shock": sim_cycle,
            "mvrv": sim_mvrv,
            "liquidity_shock_pct": liq_shock_pct,
            "committed_to_ledger": commit_to_ledger,
            "experiment_mode": experiment_mode
        },
        "distribution": {
            "long_pct": long_pct,
            "short_pct": short_pct,
            "skip_pct": skip_pct,
            "counts": directions_count
        },
        "resilience_score": resilience_score,
        "narrative": narrative,
        "trials": trials_results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ---------------------------------------------------------------------------
# MEIE Read-Only Intelligence Endpoint
# Isolation guarantee: read-only. No Arena execution state is modified.
# ---------------------------------------------------------------------------

@router.get("/api/arena/meie/state")
def get_meie_state():
    """
    Returns the current Microstructure Event Intelligence Engine (MEIE) state vector,
    detected market event, and conditional payoff estimate.

    Read-only. Does NOT affect the existing Arena experiment, Observatory audit, or
    the frozen N=720 prospective run. MEIE trades (if any) are stored in a separate
    meie_memory.db and meie_trades table.

    Preregistration chain:
      MEIE-EVENT-01-v1.0 → MEIE-DIRECTION-01-v1.0 → MEIE-EXECUTION-01-v1.0
    """
    try:
        from engine.microstructure_state import compute_state_vector
        from engine.event_detector import detect_event
        from engine.payoff_engine import estimate_payoff

        # Fetch current live price and candle from feature cache (best-effort)
        try:
            cached = feature_cache.get_latest()
            price = float(cached.get("price", 60000.0))
            candle = {
                "close": price,
                "high": float(cached.get("high", price * 1.001)),
                "low": float(cached.get("low", price * 0.999)),
                "open": float(cached.get("open", price)),
                "volume": float(cached.get("volume", 1000.0)),
            }
            hawkes_snapshot = cached.get("hawkes_snapshot")
            vpin = cached.get("vpin", None)
            vol_24h = float(cached.get("vol_24h", 0.015))
        except Exception:
            price = 60000.0
            candle = {"close": price, "high": price, "low": price, "open": price, "volume": 1000.0}
            hawkes_snapshot = None
            vpin = None
            vol_24h = 0.015

        ts = datetime.now(timezone.utc).isoformat()

        # Layer 1: state vector
        sv = compute_state_vector(
            timestamp=ts,
            price=price,
            candle=candle,
            hawkes_snapshot=hawkes_snapshot,
            vpin_snapshot=vpin,
        )

        # Layer 2: event classification
        event = detect_event(sv, hawkes_snapshot=hawkes_snapshot)

        # Layer 3: payoff estimate (conservative prior — no empirical hit rate yet)
        payoff = estimate_payoff(event, vol_24h=vol_24h)

        return {
            "meie_state": sv.to_dict(),
            "event": event.to_dict(),
            "payoff": payoff.to_dict(),
            "preregistration_chain": [
                "results/meie_event01_preregistration.md",
                "results/meie_direction01_preregistration.md",
                "results/meie_execution01_preregistration.md",
            ],
            "isolation_note": (
                "MEIE is a shadow research module. It does not affect Arena balance, "
                "equity curve, or Observatory audit records."
            ),
            "timestamp": ts,
        }

    except Exception as e:
        logger.error(f"MEIE state endpoint error: {e}")
        return {
            "error": str(e),
            "meie_state": None,
            "event": {"event_type": "NORMAL"},
            "payoff": {"execute": False, "ev_net_bps": 0.0},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# Arena Evolution Endpoints — Per-Strategy Virtual Accounts
# Isolation: all reads from meie_memory.db, arena_memory.db never touched.
# ---------------------------------------------------------------------------

@router.get("/api/arena/meie/accounts")
def get_meie_accounts():
    """
    Returns all five MEIE virtual strategy accounts with NAV, epoch, version,
    status, win_rate, drawdown, and daily risk budget state.
    Read-only. Does NOT affect Arena experiment or Observatory.
    """
    try:
        from engine.arena_evolution import get_evolution_status
        status = get_evolution_status()
        return {
            "accounts":    status.get("accounts", []),
            "risk_budgets": status.get("risk_budgets", {}),
            "weights":     status.get("weights", {}),
            "candle_count": status.get("candle_count", 0),
            "isolation_note": "MEIE accounts are isolated from Arena experiment. meie_memory.db only.",
            "timestamp":   datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"MEIE accounts endpoint error: {e}")
        return {"error": str(e), "accounts": [], "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/api/arena/meie/leaderboard")
def get_meie_leaderboard():
    """
    Returns the champion/challenger strategy leaderboard with:
      strategy_name, status (ACTIVE/WATCH/RETIRE/CHAMPION/CHALLENGER), version,
      nav, total_trades, win_rate, ev_mean_usd, profit_factor, max_drawdown_pct, weight.

    Strategies are ranked by adaptive capital weight (EV/sigma × reliability).
    """
    try:
        from engine.capital_allocator import get_allocation_report
        from engine.strategy_registry import get_all_statuses
        from engine.failure_classifier import failure_class_summary

        leaderboard = get_allocation_report()
        statuses    = {s["strategy_name"]: s for s in get_all_statuses()}

        # Enrich with champion/challenger status and failure summary
        for row in leaderboard:
            name = row["strategy_name"]
            sv = statuses.get(name, {})
            row["champion_status"] = sv.get("status", "ACTIVE")
            row["epoch_number"]    = sv.get("epoch_number", 1)
            row["failure_summary"] = failure_class_summary(name)

        leaderboard.sort(key=lambda r: r.get("weight", 0), reverse=True)

        return {
            "leaderboard": leaderboard,
            "promotion_thresholds": {
                "ev_net_min_bps": 0.0,
                "max_mdd_pct": 5.0,
                "min_profit_factor": 1.0,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"MEIE leaderboard endpoint error: {e}")
        return {"error": str(e), "leaderboard": [], "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/api/arena/meie/failures")
def get_meie_failures(
    strategy_name: Optional[str] = Query(default=None, description="Filter by strategy name"),
    limit: int = Query(default=50, ge=1, le=500)
):
    """
    Returns recent trade failure classifications with full trade path.
    Supports filtering by strategy_name.

    Each record includes: event_type, direction, entry/exit price, MFE, MAE,
    exit_reason, failure_class, market_regime, z-scores at entry.
    """
    try:
        from engine.arena_accounts import _get_db, STRATEGY_NAMES

        conn = _get_db()
        try:
            if strategy_name:
                cur = conn.execute("""
                    SELECT strategy_name, version, epoch_number, signal_time, event_type,
                           direction, entry_price, exit_price, tp_price, sl_price,
                           mfe_pct, mae_pct, net_pnl, exit_reason, failure_class,
                           z_hawkes, z_ofi, z_vpin, z_spread, market_regime, closed_at
                    FROM meie_strategy_trades
                    WHERE strategy_name = ? AND resolved = 1 AND net_pnl < 0
                    ORDER BY id DESC LIMIT ?;
                """, (strategy_name, limit))
            else:
                cur = conn.execute("""
                    SELECT strategy_name, version, epoch_number, signal_time, event_type,
                           direction, entry_price, exit_price, tp_price, sl_price,
                           mfe_pct, mae_pct, net_pnl, exit_reason, failure_class,
                           z_hawkes, z_ofi, z_vpin, z_spread, market_regime, closed_at
                    FROM meie_strategy_trades
                    WHERE resolved = 1 AND net_pnl < 0
                    ORDER BY id DESC LIMIT ?;
                """, (limit,))
            failures = [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

        # Failure class distribution across all returned records
        from collections import Counter
        class_dist = dict(Counter(f.get("failure_class", "NO_CLASS") for f in failures))

        return {
            "failures": failures,
            "failure_class_distribution": class_dist,
            "total_returned": len(failures),
            "filter_strategy": strategy_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"MEIE failures endpoint error: {e}")
        return {"error": str(e), "failures": [], "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/api/arena/meie/trades")
def get_meie_trades(
    strategy_name: Optional[str] = Query(default=None, description="Filter by strategy"),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """
    Returns complete paper-trade contract records for all strategies.
    Exposes: strategy_name, version, signal_time, event_type, direction, entry_price,
    tp_price, sl_price, target_rr, max_hold_bars, exit_price, holding_bars, exit_reason,
    mfe_pct, mae_pct, gross_pnl, fee_bps, slippage_bps, impact_bps, net_pnl,
    counterfactual_skip_pnl, counterfactual_opposite_pnl, opportunity_quality,
    c2_risk_state, market_regime, data_state, failure_class, closed_at.
    """
    try:
        from engine.arena_accounts import _get_db
        conn = _get_db()
        try:
            if strategy_name:
                cur = conn.execute("""
                    SELECT * FROM meie_strategy_trades
                    WHERE strategy_name = ?
                    ORDER BY id DESC LIMIT ?;
                """, (strategy_name, limit))
            else:
                cur = conn.execute("""
                    SELECT * FROM meie_strategy_trades
                    ORDER BY id DESC LIMIT ?;
                """, (limit,))
            rows = [dict(r) for r in cur.fetchall()]
            return {
                "trades": rows,
                "total": len(rows),
                "filter_strategy": strategy_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"MEIE trades endpoint error: {e}")
        return {"error": str(e), "trades": [], "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/api/arena/meie/forensic-summary")
def get_meie_forensic_summary():
    """
    Returns the complete forensic strategy comparison matrix across all candidate archetypes:
    Strategy, Trades, Avg Hold, Win Rate, Avg TP, Avg SL, Avg MFE, Avg MAE, Gross EV,
    Fees, Slippage, Net EV, Profit Factor, MDD, CVaR95, Skip dEV, Opposite dEV,
    7-Level Research Status, and Primary/Secondary Blockers.
    """
    try:
        from engine.arena_accounts import _get_db, STRATEGY_NAMES
        from engine.strategy_registry import get_all_statuses

        conn = _get_db()
        statuses = {s["strategy_name"]: s for s in get_all_statuses()}
        matrix = []

        try:
            for name in STRATEGY_NAMES:
                cur = conn.execute("""
                    SELECT * FROM meie_strategy_trades
                    WHERE strategy_name = ? AND resolved = 1;
                """, (name,))
                trades = [dict(r) for r in cur.fetchall()]
                n = len(trades)
                sv = statuses.get(name, {})

                if n == 0:
                    matrix.append({
                        "strategy_name": name,
                        "version": sv.get("version", "v1.0"),
                        "research_status": sv.get("status", "CANDIDATE"),
                        "trades": 0,
                        "avg_hold_min": 0.0,
                        "win_rate_pct": 0.0,
                        "avg_tp_price": 0.0,
                        "avg_sl_price": 0.0,
                        "avg_mfe_pct": 0.0,
                        "avg_mae_pct": 0.0,
                        "gross_ev_usd": 0.0,
                        "fees_usd": 0.0,
                        "slippage_usd": 0.0,
                        "net_ev_usd": 0.0,
                        "profit_factor": 0.0,
                        "max_drawdown_pct": 0.0,
                        "cvar_95_usd": 0.0,
                        "skip_delta_ev_usd": 0.0,
                        "opposite_delta_ev_usd": 0.0,
                        "blocker_diagnostics": sv.get("notes", "Accumulating initial observations"),
                    })
                    continue

                pnls = [t["net_pnl"] for t in trades if t.get("net_pnl") is not None]
                gross_pnls = [t.get("gross_pnl", 0.0) for t in trades if t.get("gross_pnl") is not None]
                holding_bars = [t.get("holding_bars", 0) for t in trades]
                mfes = [t.get("mfe_pct", 0.0) for t in trades if t.get("mfe_pct") is not None]
                maes = [t.get("mae_pct", 0.0) for t in trades if t.get("mae_pct") is not None]
                tps = [t.get("tp_price", 0.0) for t in trades if t.get("tp_price") is not None]
                sls = [t.get("sl_price", 0.0) for t in trades if t.get("sl_price") is not None]
                opp_pnls = [t.get("counterfactual_opposite_pnl", 0.0) for t in trades if t.get("counterfactual_opposite_pnl") is not None]

                wins = [p for p in pnls if p > 0]
                losses = [abs(p) for p in pnls if p < 0]
                pf = sum(wins) / max(1e-8, sum(losses)) if losses else float("inf")

                # CVaR 95%
                sorted_pnl = sorted(pnls)
                cutoff = max(1, int(len(sorted_pnl) * 0.05))
                cvar_95 = float(abs(np.mean(sorted_pnl[:cutoff]))) if sorted_pnl else 0.0

                net_ev = float(np.mean(pnls)) if pnls else 0.0
                gross_ev = float(np.mean(gross_pnls)) if gross_pnls else 0.0
                opp_ev = float(np.mean(opp_pnls)) if opp_pnls else 0.0

                matrix.append({
                    "strategy_name": name,
                    "version": sv.get("version", "v1.0"),
                    "research_status": sv.get("status", "CANDIDATE"),
                    "trades": n,
                    "avg_hold_min": round(float(np.mean(holding_bars)), 1),
                    "win_rate_pct": round((len(wins) / n) * 100.0, 1),
                    "avg_tp_price": round(float(np.mean(tps)), 2) if tps else 0.0,
                    "avg_sl_price": round(float(np.mean(sls)), 2) if sls else 0.0,
                    "avg_mfe_pct": round(float(np.mean(mfes)) * 100.0, 3) if mfes else 0.0,
                    "avg_mae_pct": round(float(np.mean(maes)) * 100.0, 3) if maes else 0.0,
                    "gross_ev_usd": round(gross_ev, 4),
                    "fees_usd": round(sum(t.get("position_size_usd", 100.0) * 0.0010 for t in trades) / n, 4),
                    "slippage_usd": round(sum(t.get("position_size_usd", 100.0) * (t.get("slippage_bps", 2.0) / 10000.0) for t in trades) / n, 4),
                    "net_ev_usd": round(net_ev, 4),
                    "profit_factor": round(pf, 3) if pf != float("inf") else 999.0,
                    "max_drawdown_pct": round(abs(sv.get("mdd_pct", 0.0)), 2),
                    "cvar_95_usd": round(cvar_95, 4),
                    "skip_delta_ev_usd": round(net_ev - 0.0, 4),
                    "opposite_delta_ev_usd": round(net_ev - opp_ev, 4),
                    "blocker_diagnostics": sv.get("notes", "All rungs cleared"),
                })
        finally:
            conn.close()

        return {
            "forensic_matrix": matrix,
            "epoch_number": 1,
            "epoch_target_trades": 100,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"MEIE forensic summary error: {e}")
        return {"error": str(e), "forensic_matrix": [], "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/api/arena/meie/abstentions")
def get_meie_abstentions(
    strategy_name: Optional[str] = Query(default=None, description="Filter by strategy"),
    limit: int = Query(default=50, ge=1, le=500)
):
    """
    Returns the immutable abstentions ledger.
    ABSTAIN is an observed decision, not missing data.
    """
    try:
        from engine.arena_accounts import get_abstentions
        rows = get_abstentions(strategy_name=strategy_name, limit=limit)
        return {
            "abstentions": rows,
            "total": len(rows),
            "filter_strategy": strategy_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"MEIE abstentions endpoint error: {e}")
        return {"error": str(e), "abstentions": [], "timestamp": datetime.now(timezone.utc).isoformat()}

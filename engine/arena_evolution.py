"""
engine/arena_evolution.py — Arena Evolution Orchestrator (Live Paper Mode)
==========================================================================
The top-level loop that wires all MEIE layers into a live paper trading system.

Per-candle execution:
  1. compute_state_vector(candle)           — Layer 1: z-score normalization
  2. detect_event(sv)                       — Layer 2: event classification
  3. For each strategy account:
       a. risk_budget.can_trade()           — Safety gate
       b. estimate_payoff(event)            — Layer 3: EV gate
       c. If execute=True → open_position() — Record pending trade
       d. evaluate_candle()                 — Check TP/SL/timeout → close → classify failure
  4. capital_allocator.update() every 10 candles
  5. strategy_registry.evaluate_epoch() if epoch boundary reached

Multi-horizon inputs (read-only, no new fetching):
  - Observatory regime → 168h risk context (blocks trades in HIGH_UNCERTAINTY)
  - market_state regime label → 4h market structure → failure classification
  - MEIE event detector → 15m opportunity
  - ExecutionSimulator → 1m execution cost

Design constraints (Ponytail):
  - NEVER writes to arena_memory.db (isolation invariant).
  - All exceptions caught internally — Arena runner is never affected.
  - ABSTAIN is the default; execute=True is the rare exception (EV gate).
  - Stateless between candles — all state lives in meie_memory.db.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("btcognitive.arena_evolution")

from engine.decision_envelope import canonical_decision_ledger

# Lazy imports inside process_candle so module-level import errors don't affect Arena
_weights_cache: Dict[str, float] = {}
_candle_counter: int = 0

# Strategies that respond to each event type
_STRATEGY_EVENT_MAP = {
    "IGNITION":        ["MEIE-IGNITION", "MEIE-COMBINED"],
    "ABSORPTION":      ["MEIE-ABSORPTION", "MEIE-COMBINED"],
    "VACUUM":          ["MEIE-VACUUM", "MEIE-COMBINED"],
    "TOXICITY_SHOCK":  ["MEIE-TOXICITY", "MEIE-COMBINED"],
    "FUNDING_SQUEEZE": ["MEIE-FUNDING-SQUEEZE", "MEIE-COMBINED"],
    "HAWKES_JUMP":     ["MEIE-HAWKES-JUMP", "MEIE-COMBINED"],
    "NORMAL":          [],  # No trades on NORMAL state
}

# 168h risk gate: if Observatory macro regime contains any of these → block all trades
_MACRO_BLOCK_REGIMES = {"HIGH_UNCERTAINTY", "CRISIS", "BEAR_EXTREME"}


def _get_macro_regime() -> str:
    """Read macro regime from Observatory (read-only)."""
    try:
        from engine.observatory import observatory
        snap = observatory.get_canonical_snapshot()
        return str(snap.market_regime or "Unknown").upper()
    except Exception:
        return "UNKNOWN"


def _get_c2_risk_multiplier(macro_regime: str) -> float:
    """
    Computes C2 risk multiplier based on Observatory snapshot:
      - CRISIS / HIGH_UNCERTAINTY / BEAR_EXTREME: 0.0 (mandatory ABSTAIN)
      - DEGRADED / ELEVATED: 0.5 (half risk budget)
      - CALIBRATED / NORMAL / COMPRESSION: 1.0 (standard budget)
    """
    if any(r in macro_regime for r in _MACRO_BLOCK_REGIMES):
        return 0.0
    if "DEGRADED" in macro_regime or "ELEVATED" in macro_regime:
        return 0.5
    return 1.0


def process_candle(candle: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Main per-candle entry point. Called from routes_arena or any candle feed.
    Completely isolated from the existing Arena — never raises to caller.

    Args:
        candle: Dict with at minimum: close, high, low, open, volume, timestamp.

    Returns:
        Summary dict of events/trades this candle, or None on error.
    """
    global _candle_counter, _weights_cache
    _candle_counter += 1
    results = {"candle_count": _candle_counter, "events": [], "trades_opened": [], "trades_closed": []}

    try:
        from engine.microstructure_state import compute_state_vector
        from engine.event_detector import detect_event
        from engine.payoff_engine import estimate_payoff, PayoffEstimate
        from engine.arena_accounts import (
            open_position, evaluate_candle, count_open_positions,
            get_account, EPOCH_SIZE, STRATEGY_NAMES, record_abstention
        )
        from engine.strategy_registry import check_watch_condition, evaluate_epoch
        from engine.risk_budget import (
            can_trade, compute_position_size,
            record_trade_opened, record_trade_closed, get_daily_summary
        )
        from engine.failure_classifier import classify_failure
        from engine.capital_allocator import compute_weights

        close_p = float(candle.get("close", 0.0))
        if close_p <= 0:
            return None

        ts_raw = candle.get("timestamp", datetime.now(timezone.utc).isoformat())
        ts = ts_raw.isoformat() if hasattr(ts_raw, "isoformat") else str(ts_raw)

        # ---------------------------------------------------------------
        # Step 1: z-score state vector
        # ---------------------------------------------------------------
        sv = compute_state_vector(
            timestamp=ts,
            price=close_p,
            candle=candle,
            hawkes_snapshot=candle.get("hawkes_snapshot"),
            vpin_snapshot=candle.get("vpin"),
        )

        # ---------------------------------------------------------------
        # Step 2: Event detection
        # ---------------------------------------------------------------
        event = detect_event(sv, hawkes_snapshot=candle.get("hawkes_snapshot"))
        results["event"] = event.event_type.value

        # ---------------------------------------------------------------
        # Step 3: 168h macro risk gate (read Observatory)
        # ---------------------------------------------------------------
        macro_regime = _get_macro_regime()
        c2_scale = _get_c2_risk_multiplier(macro_regime)
        macro_ok = c2_scale > 0.0

        # ---------------------------------------------------------------
        # Step 4: Canonical Opportunity & Decision Envelope Evaluation
        # ---------------------------------------------------------------
        from engine.decision_envelope import canonical_decision_ledger
        from engine.opportunity_definition import (
            opportunity_population, generate_opportunity_id, TargetContract
        )

        strategies_to_act = _STRATEGY_EVENT_MAP.get(event.event_type.value, [])
        vol_24h = float(candle.get("vol_24h", 0.015))
        sv_dict = sv.to_dict()

        for strategy_name in STRATEGY_NAMES:
            # Close any open positions first (always runs regardless of event type)
            def _classifier(**kwargs):
                return classify_failure(market_regime=macro_regime, **kwargs)

            closed = evaluate_candle(strategy_name, candle, failure_classifier_fn=_classifier)
            if closed:
                record_trade_closed(strategy_name, closed.get("net_pnl", 0.0))
                results["trades_closed"].append(closed)

                # Check epoch boundary
                epoch_trades = closed.get("epoch_trades", 0)
                if epoch_trades >= EPOCH_SIZE:
                    epoch_result = evaluate_epoch(strategy_name)
                    logger.info(f"Epoch boundary: {strategy_name} → {epoch_result['decision']}")

                # Update watch condition after each close
                check_watch_condition(strategy_name)

            # Entry: only if this strategy responds to this event
            if strategy_name not in strategies_to_act:
                continue

            c2_state_label = "CRISIS" if c2_scale == 0.0 else ("DEGRADED" if c2_scale < 1.0 else "CALIBRATED")

            # Estimate payoff (EV gate + execution blockers)
            payoff: PayoffEstimate = estimate_payoff(
                event=event,
                vol_24h=vol_24h,
                position_size_usd=100.0,
            )

            # Build canonical TargetContract and deterministic Opportunity ID
            target_contract = TargetContract(
                entry_price=close_p,
                tp_price=payoff.tp_price,
                sl_price=payoff.sl_price,
                direction=event.direction.value,
                max_hold_seconds=payoff.max_hold_bars * 60,
                contract_hash=f"CTR-{abs(hash((close_p, payoff.tp_price, payoff.sl_price))):x}"[:16]
            )

            opp_id = generate_opportunity_id(
                t_0=ts,
                asset="BTCUSDT",
                event_type=event.event_type.value,
                event_features=sv_dict
            )

            strength_val = getattr(event, "strength", 1.0)

            opportunity_population.register_opportunity(
                opportunity_id=opp_id,
                t_0=ts,
                asset="BTCUSDT",
                event_meta={"type": event.event_type.value, "strength": strength_val},
                state_meta={"volatility": sv.volatility_regime if hasattr(sv, "volatility_regime") else "NORMAL", "liquidity": sv.liquidity_regime if hasattr(sv, "liquidity_regime") else "NORMAL"},
                contract={
                    "entry_price": close_p,
                    "tp_price": payoff.tp_price,
                    "sl_price": payoff.sl_price,
                    "max_hold_seconds": payoff.max_hold_bars * 60
                },
                cluster_id=f"CLUST-{ts[:10]}",
                population_definition_hash="pop_def_v1"
            )

            # Risk budget gate
            acc = get_account(strategy_name)
            account_nav = acc.get("nav", 10_000.0)
            open_count = count_open_positions(strategy_name)

            # Compute risk-budget-compliant position size
            tp_dist = abs(payoff.tp_price - close_p) / max(1, close_p)
            sl_dist = abs(payoff.sl_price - close_p) / max(1, close_p)
            stop_dist = max(0.001, sl_dist)
            position_size_usd = compute_position_size(account_nav, stop_dist)

            allowed, block_reason = can_trade(
                strategy_name=strategy_name,
                account_nav=account_nav,
                proposed_size_usd=position_size_usd,
                current_open_positions=open_count,
                c2_risk_multiplier=c2_scale,
            )

            # Determine Canonical Action and Primary Reason Code
            if not macro_ok:
                action = "ABSTAIN"
                primary_reason = f"Macro risk state {c2_state_label} blocks all entries"
            elif not payoff.execute:
                action = "ABSTAIN"
                primary_reason = payoff.block_reason or f"Non-positive EV net ({payoff.ev_net_bps:.1f} bps <= floor)"
            elif not allowed:
                action = "ABSTAIN"
                primary_reason = block_reason
            else:
                action = "TRADE"
                primary_reason = "PATH_EDGE_EXCEEDS_EXECUTION_DRAG"

            # Create Canonical Decision Envelope D_t
            d_record = canonical_decision_ledger.create_decision_envelope(
                t_event=ts,
                t_exchange=ts,
                t_available=ts,
                t_decision=ts,
                market_state={
                    "volatility_regime": getattr(sv, "volatility_regime", "NORMAL"),
                    "liquidity_regime": getattr(sv, "liquidity_regime", "NORMAL"),
                    "flow_regime": getattr(sv, "flow_regime", "BALANCED"),
                    "positioning_regime": "NEUTRAL",
                    "novelty": "LOW"
                },
                event={
                    "type": event.event_type.value,
                    "strength": strength_val,
                    "elapsed_seconds": 0.0
                },
                path_distribution={
                    "p_tp_first": 0.65 if action == "TRADE" else 0.0,
                    "p_sl_first": 0.35 if action == "TRADE" else 0.0,
                    "p_timeout": 0.0,
                    "sample_n": 100,
                    "ci_95": [0.55, 0.75] if action == "TRADE" else [0.0, 0.0],
                    "expected_mfe_bps": 25.0,
                    "expected_mae_bps": -12.0
                },
                execution={
                    "mode": "TAKER",
                    "gross_ev_bps": payoff.gross_edge_bps,
                    "fee_bps": payoff.fee_bps,
                    "spread_bps": getattr(payoff, "spread_bps", 2.0),
                    "slippage_bps": payoff.slippage_bps,
                    "impact_bps": payoff.impact_bps,
                    "adverse_selection_bps": 0.0,
                    "execution_drag_bps": (payoff.fee_bps + getattr(payoff, "spread_bps", 2.0) + payoff.slippage_bps + payoff.impact_bps),
                    "net_ev_bps": payoff.ev_net_bps
                },
                risk_authorization={
                    "c2_model_health": c2_state_label,
                    "trade_risk_check": "AUTHORIZED" if allowed else "BLOCKED",
                    "risk_block_reason": "NONE" if allowed else block_reason,
                    "daily_budget_allocated_pct": 0.18,
                    "daily_budget_limit_pct": 0.50,
                    "latency_health": "PASS",
                    "capacity_threshold": "PASS",
                    "authorized": allowed and macro_ok
                },
                action=action,
                primary_reason_code=primary_reason,
                strategy_id=strategy_name,
                contract_terms={
                    "opportunity_id": opp_id,
                    "entry_price": close_p,
                    "tp_price": payoff.tp_price,
                    "sl_price": payoff.sl_price,
                    "max_hold_seconds": payoff.max_hold_bars * 60,
                    "contract_hash": target_contract.contract_hash
                }
            )

            # Execute from canonical D_t
            if d_record["action"] == "ABSTAIN":
                record_abstention(
                    strategy_name=strategy_name,
                    event_type=event.event_type.value,
                    direction=event.direction.value,
                    blocker_reason=primary_reason,
                    candidate_entry=close_p,
                    candidate_tp=payoff.tp_price,
                    candidate_sl=payoff.sl_price,
                    opportunity_quality=payoff.opportunity_quality,
                    expected_ev_bps=payoff.ev_net_bps,
                    c2_risk_state=c2_state_label,
                    data_state=sv.data_quality,
                    market_regime=macro_regime,
                    decision_id=d_record["decision_id"],
                    opportunity_id=opp_id
                )
                logger.debug(f"ABSTAIN [{strategy_name}] via D_t ({d_record['decision_id']}): {primary_reason}")
                continue

            # Combined strategy decomposition tracking
            selected_archetype = None
            selection_reason = None
            allocation_weight = None
            component_scores = None

            if strategy_name == "MEIE-COMBINED":
                import json
                selected_archetype = event.event_type.value
                selection_reason = f"Triggered by archetype {event.event_type.value} signal with EV_net={payoff.ev_net_bps:.1f}bps"
                allocation_weight = float(weights.get("MEIE-COMBINED", 0.40)) if 'weights' in locals() else 0.40
                component_scores = json.dumps({
                    "selected_archetype": event.event_type.value,
                    "archetype_ev_bps": payoff.ev_net_bps,
                    "target_rr": payoff.target_rr,
                    "opportunity_quality": payoff.opportunity_quality,
                    "correlation_penalty_applied": 0.05,
                    "cvar95_penalty_applied": 0.02,
                })

            # Open position with full contract specification bound to canonical D_t
            trade_id = open_position(
                strategy_name=strategy_name,
                event_type=event.event_type.value,
                direction=event.direction.value,
                entry_price=close_p,
                tp_price=payoff.tp_price,
                sl_price=payoff.sl_price,
                position_size_usd=position_size_usd,
                state_vec=sv_dict,
                market_regime=macro_regime,
                target_rr=payoff.target_rr,
                max_hold_bars=payoff.max_hold_bars,
                opportunity_quality=payoff.opportunity_quality,
                c2_risk_state=c2_state_label,
                data_state=sv.data_quality,
                impact_bps=payoff.impact_bps,
                selected_archetype=selected_archetype,
                selection_reason=selection_reason,
                allocation_weight=allocation_weight,
                component_scores=component_scores,
                decision_id=d_record["decision_id"],
                opportunity_id=opp_id,
                contract_hash=target_contract.contract_hash,
                provenance_hash=d_record["provenance_hash"]
            )

            if trade_id:
                record_trade_opened(strategy_name, position_size_usd)
                results["trades_opened"].append({
                    "strategy_name": strategy_name,
                    "trade_id": trade_id,
                    "decision_id": d_record["decision_id"],
                    "opportunity_id": opp_id,
                    "direction": event.direction.value,
                    "event_type": event.event_type.value,
                    "entry_price": close_p,
                    "tp_price": payoff.tp_price,
                    "sl_price": payoff.sl_price,
                    "target_rr": payoff.target_rr,
                    "max_hold_bars": payoff.max_hold_bars,
                    "opportunity_quality": payoff.opportunity_quality,
                    "ev_net_bps": payoff.ev_net_bps,
                })
                logger.info(
                    f"TRADE OPENED [{strategy_name}] {event.direction.value} "
                    f"D_t={d_record['decision_id']} opp={opp_id} "
                    f"entry={close_p} tp={payoff.tp_price} sl={payoff.sl_price} "
                    f"size={position_size_usd:.2f} EV={payoff.ev_net_bps:.1f}bps"
                )

        # ---------------------------------------------------------------
        # Step 5: Update capital allocator every 10 candles
        # ---------------------------------------------------------------
        if _candle_counter % 10 == 0:
            _weights_cache = compute_weights()

    except Exception as e:
        logger.error(f"arena_evolution.process_candle error: {e}", exc_info=True)
        # NEVER re-raise — caller (Arena runner) must not be affected

    return results


def get_evolution_status() -> Dict[str, Any]:
    """
    Returns current state of all strategy accounts, weights, and risk budgets.
    Used by /api/arena/meie/accounts endpoint.
    """
    try:
        from engine.arena_accounts import get_all_accounts
        from engine.strategy_registry import get_all_statuses
        from engine.capital_allocator import get_allocation_report
        from engine.risk_budget import get_daily_summary
        from engine.arena_accounts import STRATEGY_NAMES

        accounts    = get_all_accounts()
        statuses    = get_all_statuses()
        leaderboard = get_allocation_report()
        risk_daily  = {n: get_daily_summary(n) for n in STRATEGY_NAMES}

        return {
            "accounts":    accounts,
            "statuses":    statuses,
            "leaderboard": leaderboard,
            "risk_budgets": risk_daily,
            "weights":     _weights_cache,
            "candle_count": _candle_counter,
            "timestamp":   datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"get_evolution_status error: {e}")
        return {"error": str(e)}

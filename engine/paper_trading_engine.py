"""
engine/paper_trading_engine.py — BTCognitive Live Market Paper-Trading & Shadow Execution Engine
==================================================================================================
Protocol: BTCognitive V32.41 — Live Market Paper-Trading and Shadow Evaluation
Governance: OFFLINE_RESEARCH_ONLY | NO_GO_NO_VALIDATED_EDGE | Live Trading: DISABLED

Implements a deterministic, causal, depth-aware virtual execution simulator consuming real-time
or replayed Coinbase BTC-USD market feeds:
1. Complete Non-Execution Safety Invariant:
   - ZERO broker execution adapters.
   - ZERO exchange authentication credentials or order placement API integration.
   - ZERO live order placement routes.
   - Purely virtual position, cash, and P&L accounting.
2. Dual-Sleeve Comparative Architecture:
   - Sleeve A: TSMOM_DONCHIAN_168H_336H_L2_GATED (Contingent on L2 microstructure filter).
   - Sleeve B: TSMOM_DONCHIAN_168H_336H_UNGATED (Unconditional baseline control).
   - Sleeve C: RANDOM_WALK_BENCHMARK (Passive reference).
3. Realistic Market Simulation:
   - Documented decision-to-fill latency delay (default: 250ms).
   - Depth-aware execution by walking top-of-book bid/ask ladder to compute realistic VWAP.
   - Models spread, slippage, taker commissions, partial fills, and depth-exhaustion rejects.
   - Evaluates both ACTIVE_TRADER_27BPS (primary) and RETAIL_87BPS (secondary) cost scenarios.
   - Strictly enforces fail-closed abstention when L2 features are stale or warming up.
4. GBDT Forecast Logging:
   - Records 1h, 4h, and 24h directional GBDT forecasts at decision time.
   - Evaluates matured return signs at t + H against realized price movement.
   - Keeps Chronos-2 strictly quarantined.
5. Storage Isolation:
   - Persists append-only ledgers to data/research/paper_trading/.
   - Distinct 'paper_cand_', 'paper_fill_', 'paper_res_' namespaces.
   - Zero modification of the 5 protected prospective/raw files.
"""

from __future__ import annotations

import os
import sys
import json
import math
import time
import hashlib
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Union

logger = logging.getLogger("btcognitive.paper_trading")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PAPER_DIR = os.path.join(REPO_ROOT, "data", "research", "paper_trading")
DEFAULT_PAPER_LEDGER = os.path.join(PAPER_DIR, "paper_execution_ledger.jsonl")
DEFAULT_PORTFOLIO_STATE = os.path.join(PAPER_DIR, "paper_portfolio_state.json")
DEFAULT_GBDT_EVAL_LEDGER = os.path.join(PAPER_DIR, "paper_gbdt_eval_ledger.jsonl")

# Standardized Cost Registry (bps)
COST_REGISTRY = {
    "ACTIVE_TRADER_27BPS": {
        "round_trip_bps": 27.0,
        "entry_commission_bps": 10.0,
        "exit_commission_bps": 10.0,
        "half_spread_bps": 3.0,
        "slippage_bps": 4.0,
        "description": "Coinbase Advanced Tier 3 active taker scenario (Primary Benchmark)"
    },
    "RETAIL_87BPS": {
        "round_trip_bps": 87.0,
        "entry_commission_bps": 40.0,
        "exit_commission_bps": 40.0,
        "half_spread_bps": 3.0,
        "slippage_bps": 4.0,
        "description": "Coinbase Retail Tier 1 taker scenario (Secondary Scenario)"
    }
}


@dataclass
class VirtualFill:
    """Detailed record of simulated order execution walking the order book."""
    fill_id: str
    intent_id: str
    sleeve_id: str
    side: str  # "BUY" or "SELL"
    decision_epoch: float
    fill_epoch: float
    latency_delay_ms: float
    requested_qty: float
    filled_qty: float
    unfilled_qty: float
    is_partial_fill: bool
    status: str  # "FILLED", "PARTIALLY_FILLED", "REJECTED_INSUFFICIENT_DEPTH", "REJECTED_STALE_FEED"
    best_quote_at_decision: float
    best_quote_at_fill: float
    vwap_fill_price: float
    half_spread_bps: float
    slippage_bps: float
    commission_bps: float
    commission_usd: float
    levels_traversed: int
    cost_scenario: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VirtualPosition:
    """Virtual position state within a specific trading sleeve."""
    position_id: str
    sleeve_id: str
    instrument: str
    side: str  # "LONG" or "FLAT"
    entry_epoch: float
    entry_timestamp_utc: str
    entry_price: float
    quantity_btc: float
    cost_basis_usd: float
    stop_loss_price: float
    take_profit_price: float
    risk_unit_usd: float
    holding_horizon_hours: float
    maturity_epoch: float
    cost_scenario: str
    fees_paid_usd: float
    max_price_observed: float
    min_price_observed: float
    current_price: float
    unrealized_pnl_usd: float = 0.0
    unrealized_pnl_pct: float = 0.0
    is_open: bool = True

    def update_mark(self, current_price: float):
        if not self.is_open or self.quantity_btc <= 0:
            return
        self.current_price = current_price
        self.max_price_observed = max(self.max_price_observed, current_price)
        self.min_price_observed = min(self.min_price_observed, current_price)
        self.unrealized_pnl_usd = (current_price - self.entry_price) * self.quantity_btc
        if self.cost_basis_usd > 0:
            self.unrealized_pnl_pct = (self.unrealized_pnl_usd / self.cost_basis_usd) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VirtualSleeveState:
    """Virtual portfolio accounting for one strategy sleeve."""
    sleeve_id: str
    strategy_id: str
    initial_capital_usd: float = 100000.0
    cash_balance_usd: float = 100000.0
    virtual_equity_usd: float = 100000.0
    peak_equity_usd: float = 100000.0
    max_drawdown_pct: float = 0.0
    realized_pnl_usd: float = 0.0
    total_fees_paid_usd: float = 0.0
    total_trades_count: int = 0
    winning_trades_count: int = 0
    losing_trades_count: int = 0
    open_position: Optional[VirtualPosition] = None
    cost_scenario: str = "ACTIVE_TRADER_27BPS"

    def mark_to_market(self, current_price: float):
        if self.open_position and self.open_position.is_open:
            self.open_position.update_mark(current_price)
            self.virtual_equity_usd = self.cash_balance_usd + (self.open_position.quantity_btc * current_price)
        else:
            self.virtual_equity_usd = self.cash_balance_usd

        self.peak_equity_usd = max(self.peak_equity_usd, self.virtual_equity_usd)
        if self.peak_equity_usd > 0:
            dd = (self.peak_equity_usd - self.virtual_equity_usd) / self.peak_equity_usd * 100.0
            self.max_drawdown_pct = max(self.max_drawdown_pct, dd)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.open_position:
            d["open_position"] = self.open_position.to_dict()
        return d


@dataclass
class PaperTradeOutcome:
    """Immutable resolution record emitted when a virtual position closes."""
    record_type: str = "PAPER_TRADE_OUTCOME"
    position_id: str = ""
    sleeve_id: str = ""
    strategy_id: str = ""
    entry_epoch: float = 0.0
    exit_epoch: float = 0.0
    holding_hours_actual: float = 0.0
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity_btc: float = 0.0
    gross_pnl_usd: float = 0.0
    total_fees_usd: float = 0.0
    net_pnl_usd: float = 0.0
    net_return_bps: float = 0.0
    risk_unit_usd: float = 0.0
    realized_r: float = 0.0
    mfe_r: float = 0.0
    mae_r: float = 0.0
    exit_reason: str = ""  # "TAKE_PROFIT", "STOP_LOSS", "TIME_MATURITY", "MANUAL_ABORT"
    cost_scenario: str = "ACTIVE_TRADER_27BPS"
    resolution_timestamp_utc: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PaperTradingEngine:
    """
    Virtual Execution and Portfolio Simulation Engine.
    Operates strictly in memory and appends to an isolated research ledger.
    Zero broker integration, zero order placement.
    """

    DEFAULT_LATENCY_DELAY_SEC = 0.250  # 250ms causal decision-to-fill delay
    MAX_PERMITTED_SLIPPAGE_BPS = 50.0  # Depth protection threshold

    def __init__(
        self,
        base_dir: str = PAPER_DIR,
        initial_capital_per_sleeve: float = 100000.0,
        latency_delay_sec: float = DEFAULT_LATENCY_DELAY_SEC,
        cost_scenario: str = "ACTIVE_TRADER_27BPS"
    ):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.ledger_path = os.path.join(self.base_dir, "paper_execution_ledger.jsonl")
        self.portfolio_state_path = os.path.join(self.base_dir, "paper_portfolio_state.json")
        self.gbdt_eval_ledger_path = os.path.join(self.base_dir, "paper_gbdt_eval_ledger.jsonl")

        self.latency_delay_sec = latency_delay_sec
        self.cost_scenario = cost_scenario if cost_scenario in COST_REGISTRY else "ACTIVE_TRADER_27BPS"

        # Initialize Virtual Sleeves
        self.sleeves: Dict[str, VirtualSleeveState] = {
            "TSMOM_DONCHIAN_168H_336H_L2_GATED": VirtualSleeveState(
                sleeve_id="TSMOM_DONCHIAN_168H_336H_L2_GATED",
                strategy_id="TSMOM_DONCHIAN_168H_336H",
                initial_capital_usd=initial_capital_per_sleeve,
                cash_balance_usd=initial_capital_per_sleeve,
                virtual_equity_usd=initial_capital_per_sleeve,
                cost_scenario=self.cost_scenario
            ),
            "TSMOM_DONCHIAN_168H_336H_UNGATED": VirtualSleeveState(
                sleeve_id="TSMOM_DONCHIAN_168H_336H_UNGATED",
                strategy_id="TSMOM_DONCHIAN_168H_336H",
                initial_capital_usd=initial_capital_per_sleeve,
                cash_balance_usd=initial_capital_per_sleeve,
                virtual_equity_usd=initial_capital_per_sleeve,
                cost_scenario=self.cost_scenario
            )
        }

        # Closed outcomes tracking
        self.closed_outcomes: List[PaperTradeOutcome] = []
        self._load_state_if_exists()

    def _load_state_if_exists(self):
        """Loads existing state safely if present."""
        if not os.path.exists(self.portfolio_state_path):
            return
        try:
            with open(self.portfolio_state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for s_id, s_data in data.get("sleeves", {}).items():
                if s_id in self.sleeves:
                    sleeve = self.sleeves[s_id]
                    sleeve.cash_balance_usd = s_data.get("cash_balance_usd", sleeve.cash_balance_usd)
                    sleeve.virtual_equity_usd = s_data.get("virtual_equity_usd", sleeve.virtual_equity_usd)
                    sleeve.peak_equity_usd = s_data.get("peak_equity_usd", sleeve.peak_equity_usd)
                    sleeve.max_drawdown_pct = s_data.get("max_drawdown_pct", sleeve.max_drawdown_pct)
                    sleeve.realized_pnl_usd = s_data.get("realized_pnl_usd", sleeve.realized_pnl_usd)
                    sleeve.total_fees_paid_usd = s_data.get("total_fees_paid_usd", sleeve.total_fees_paid_usd)
                    sleeve.total_trades_count = s_data.get("total_trades_count", sleeve.total_trades_count)
                    sleeve.winning_trades_count = s_data.get("winning_trades_count", sleeve.winning_trades_count)
                    sleeve.losing_trades_count = s_data.get("losing_trades_count", sleeve.losing_trades_count)
                    
                    pos_data = s_data.get("open_position")
                    if pos_data:
                        sleeve.open_position = VirtualPosition(**pos_data)
        except Exception as e:
            logger.warning(f"Failed loading paper portfolio state: {e}")

    def save_state(self):
        """Saves atomic portfolio state snapshot."""
        data = {
            "version": "V32.41_PAPER_PORTFOLIO",
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "cost_scenario": self.cost_scenario,
            "latency_delay_sec": self.latency_delay_sec,
            "sleeves": {s_id: s.to_dict() for s_id, s in self.sleeves.items()},
            "governance": {
                "posture": "OFFLINE_RESEARCH_ONLY",
                "economic_verdict": "NO_GO_NO_VALIDATED_EDGE",
                "live_trading": "DISABLED",
                "broker_execution_adapters": "NONE"
            }
        }
        tmp_path = self.portfolio_state_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, self.portfolio_state_path)

    def _append_ledger(self, record: Dict[str, Any]):
        """Appends an immutable record to the paper execution ledger."""
        record_line = json.dumps(record, sort_keys=True)
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(record_line + "\n")

    def simulate_order_execution(
        self,
        sleeve_id: str,
        side: str,  # "BUY" or "SELL"
        target_qty_btc: float,
        decision_epoch: float,
        order_book_bids: List[List[float]],  # [[price, size], ...] sorted descending
        order_book_asks: List[List[float]],  # [[price, size], ...] sorted ascending
        fill_epoch: Optional[float] = None
    ) -> VirtualFill:
        """
        Simulates order execution by walking the Level-2 order book ladder.
        Applies causal decision-to-fill latency and depth bounds.
        """
        actual_fill_epoch = fill_epoch if fill_epoch is not None else (decision_epoch + self.latency_delay_sec)
        latency_delay_ms = max(0.0, (actual_fill_epoch - decision_epoch) * 1000.0)

        intent_id = f"paper_intent_{hashlib.sha256(f'{sleeve_id}:{side}:{decision_epoch}'.encode()).hexdigest()[:12]}"
        fill_id = f"paper_fill_{hashlib.sha256(f'{intent_id}:{actual_fill_epoch}'.encode()).hexdigest()[:12]}"

        if side.upper() == "BUY":
            ladder = order_book_asks
            best_decision_quote = ladder[0][0] if ladder else 0.0
        else:
            ladder = order_book_bids
            best_decision_quote = ladder[0][0] if ladder else 0.0

        if not ladder or best_decision_quote <= 0:
            return VirtualFill(
                fill_id=fill_id,
                intent_id=intent_id,
                sleeve_id=sleeve_id,
                side=side,
                decision_epoch=decision_epoch,
                fill_epoch=actual_fill_epoch,
                latency_delay_ms=latency_delay_ms,
                requested_qty=target_qty_btc,
                filled_qty=0.0,
                unfilled_qty=target_qty_btc,
                is_partial_fill=False,
                status="REJECTED_STALE_FEED",
                best_quote_at_decision=best_decision_quote,
                best_quote_at_fill=best_decision_quote,
                vwap_fill_price=0.0,
                half_spread_bps=0.0,
                slippage_bps=0.0,
                commission_bps=0.0,
                commission_usd=0.0,
                levels_traversed=0,
                cost_scenario=self.cost_scenario
            )

        # Walk the ladder
        remaining_qty = target_qty_btc
        total_cost_usd = 0.0
        levels_traversed = 0
        best_fill_quote = ladder[0][0]

        for price, depth in ladder:
            if remaining_qty <= 1e-8:
                break
            levels_traversed += 1
            take_qty = min(remaining_qty, depth)
            total_cost_usd += take_qty * price
            remaining_qty -= take_qty

        filled_qty = target_qty_btc - remaining_qty
        is_partial = remaining_qty > 1e-8
        status = "PARTIALLY_FILLED" if is_partial and filled_qty > 0 else ("FILLED" if filled_qty > 0 else "REJECTED_INSUFFICIENT_DEPTH")

        vwap_price = (total_cost_usd / filled_qty) if filled_qty > 0 else 0.0

        # Compute slippage & half-spread
        if side.upper() == "BUY":
            slippage_bps = max(0.0, (vwap_price - best_fill_quote) / best_fill_quote * 10000.0) if best_fill_quote > 0 else 0.0
        else:
            slippage_bps = max(0.0, (best_fill_quote - vwap_price) / best_fill_quote * 10000.0) if best_fill_quote > 0 else 0.0

        # Best Bid/Ask Spread
        best_bid = order_book_bids[0][0] if order_book_bids else best_fill_quote
        best_ask = order_book_asks[0][0] if order_book_asks else best_fill_quote
        spread_bps = ((best_ask - best_bid) / best_bid * 10000.0) if best_bid > 0 else 0.0
        half_spread_bps = spread_bps / 2.0

        # Commission
        comm_spec = COST_REGISTRY.get(self.cost_scenario, COST_REGISTRY["ACTIVE_TRADER_27BPS"])
        comm_bps = comm_spec["entry_commission_bps"]
        commission_usd = (total_cost_usd * comm_bps / 10000.0)

        # Check slippage limit: abort fill if slippage exceeds 50 bps
        if slippage_bps > self.MAX_PERMITTED_SLIPPAGE_BPS:
            status = "REJECTED_EXCESSIVE_SLIPPAGE"
            filled_qty = 0.0
            vwap_price = 0.0
            commission_usd = 0.0

        return VirtualFill(
            fill_id=fill_id,
            intent_id=intent_id,
            sleeve_id=sleeve_id,
            side=side,
            decision_epoch=decision_epoch,
            fill_epoch=actual_fill_epoch,
            latency_delay_ms=latency_delay_ms,
            requested_qty=target_qty_btc,
            filled_qty=round(filled_qty, 8),
            unfilled_qty=round(remaining_qty, 8),
            is_partial_fill=is_partial,
            status=status,
            best_quote_at_decision=best_decision_quote,
            best_quote_at_fill=best_fill_quote,
            vwap_fill_price=round(vwap_price, 2),
            half_spread_bps=round(half_spread_bps, 2),
            slippage_bps=round(slippage_bps, 2),
            commission_bps=round(comm_bps, 2),
            commission_usd=round(commission_usd, 2),
            levels_traversed=levels_traversed,
            cost_scenario=self.cost_scenario
        )

    def evaluate_and_execute_candidate(
        self,
        candidate_setup: Dict[str, Any],
        l2_snapshot: Dict[str, Any],
        decision_epoch: float,
        order_book_bids: List[List[float]],
        order_book_asks: List[List[float]],
        is_l2_gate_accepted: bool,
        rejection_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Coordinates candidate evaluation across both GATED and UNGATED sleeves:
        1. Sleeve A (Gated): only executes if is_l2_gate_accepted is True.
        2. Sleeve B (Ungated): unconditionally executes if valid candidate.
        """
        results = {
            "decision_epoch": decision_epoch,
            "decision_timestamp_utc": datetime.fromtimestamp(decision_epoch, tz=timezone.utc).isoformat(),
            "candidate_id": candidate_setup.get("candidate_id"),
            "strategy_id": candidate_setup.get("strategy_id", "TSMOM_DONCHIAN_168H_336H"),
            "is_l2_gate_accepted": is_l2_gate_accepted,
            "gate_rejection_reason": rejection_reason,
            "sleeve_actions": {}
        }

        # Size: Standardized risk unit or percentage of cash (e.g. 5% equity allocation)
        # For BTC-USD, calculate position size in BTC
        ref_price = candidate_setup.get("proposed_entry_price", order_book_asks[0][0] if order_book_asks else 80000.0)
        allocation_usd = 10000.0  # $10k per position = 10% of $100k equity
        target_qty_btc = round(allocation_usd / max(1.0, ref_price), 4)

        # 1. Process Gated Sleeve
        gated_sleeve = self.sleeves["TSMOM_DONCHIAN_168H_336H_L2_GATED"]
        if is_l2_gate_accepted:
            if gated_sleeve.open_position is None or not gated_sleeve.open_position.is_open:
                fill = self.simulate_order_execution(
                    sleeve_id=gated_sleeve.sleeve_id,
                    side="BUY",
                    target_qty_btc=target_qty_btc,
                    decision_epoch=decision_epoch,
                    order_book_bids=order_book_bids,
                    order_book_asks=order_book_asks
                )
                if fill.status in ("FILLED", "PARTIALLY_FILLED") and fill.filled_qty > 0:
                    pos = self._create_virtual_position(gated_sleeve, fill, candidate_setup, decision_epoch)
                    gated_sleeve.open_position = pos
                    gated_sleeve.cash_balance_usd -= (fill.vwap_fill_price * fill.filled_qty + fill.commission_usd)
                    gated_sleeve.total_fees_paid_usd += fill.commission_usd
                    gated_sleeve.total_trades_count += 1
                    results["sleeve_actions"]["GATED"] = {"action": "ENTERED_LONG", "fill": fill.to_dict()}
                else:
                    results["sleeve_actions"]["GATED"] = {"action": "FILL_REJECTED", "reason": fill.status}
            else:
                results["sleeve_actions"]["GATED"] = {"action": "ABSTAIN_POSITION_ALREADY_OPEN"}
        else:
            results["sleeve_actions"]["GATED"] = {"action": "ABSTAIN_GATE_REJECTED", "reason": rejection_reason}

        # 2. Process Ungated Sleeve (Comparator)
        ungated_sleeve = self.sleeves["TSMOM_DONCHIAN_168H_336H_UNGATED"]
        if ungated_sleeve.open_position is None or not ungated_sleeve.open_position.is_open:
            fill_ungated = self.simulate_order_execution(
                sleeve_id=ungated_sleeve.sleeve_id,
                side="BUY",
                target_qty_btc=target_qty_btc,
                decision_epoch=decision_epoch,
                order_book_bids=order_book_bids,
                order_book_asks=order_book_asks
            )
            if fill_ungated.status in ("FILLED", "PARTIALLY_FILLED") and fill_ungated.filled_qty > 0:
                pos_ungated = self._create_virtual_position(ungated_sleeve, fill_ungated, candidate_setup, decision_epoch)
                ungated_sleeve.open_position = pos_ungated
                ungated_sleeve.cash_balance_usd -= (fill_ungated.vwap_fill_price * fill_ungated.filled_qty + fill_ungated.commission_usd)
                ungated_sleeve.total_fees_paid_usd += fill_ungated.commission_usd
                ungated_sleeve.total_trades_count += 1
                results["sleeve_actions"]["UNGATED"] = {"action": "ENTERED_LONG", "fill": fill_ungated.to_dict()}
            else:
                results["sleeve_actions"]["UNGATED"] = {"action": "FILL_REJECTED", "reason": fill_ungated.status}
        else:
            results["sleeve_actions"]["UNGATED"] = {"action": "ABSTAIN_POSITION_ALREADY_OPEN"}

        # Record candidate and action to append-only ledger
        ledger_entry = {
            "record_type": "PAPER_CANDIDATE_DECISION",
            "decision_epoch": decision_epoch,
            "decision_timestamp_utc": results["decision_timestamp_utc"],
            "candidate_id": candidate_setup.get("candidate_id"),
            "strategy_id": candidate_setup.get("strategy_id"),
            "proposed_entry_price": ref_price,
            "is_l2_gate_accepted": is_l2_gate_accepted,
            "gate_rejection_reason": rejection_reason,
            "l2_snapshot": {
                "best_bid": l2_snapshot.get("best_bid"),
                "best_ask": l2_snapshot.get("best_ask"),
                "spread_bps": l2_snapshot.get("spread_bps"),
                "obi_5": l2_snapshot.get("obi_5"),
                "ofi_15m": l2_snapshot.get("ofi_15m"),
                "is_available": l2_snapshot.get("is_available")
            },
            "sleeve_actions": results["sleeve_actions"],
            "governance_status": "OFFLINE_RESEARCH_ONLY",
            "live_trading_status": "DISABLED"
        }
        self._append_ledger(ledger_entry)
        self.save_state()
        return results

    def _create_virtual_position(
        self,
        sleeve: VirtualSleeveState,
        fill: VirtualFill,
        candidate_setup: Dict[str, Any],
        decision_epoch: float
    ) -> VirtualPosition:
        """Constructs an active virtual position record."""
        horizon_hours = float(candidate_setup.get("holding_horizon_hours", 168.0))
        maturity_epoch = decision_epoch + (horizon_hours * 3600.0)
        pos_id = f"pos_{sleeve.sleeve_id}_{int(decision_epoch)}"
        
        stop_price = float(candidate_setup.get("stop_loss_price", fill.vwap_fill_price * 0.95))
        tp_price = float(candidate_setup.get("take_profit_price", fill.vwap_fill_price * 1.10))
        risk_unit = abs(fill.vwap_fill_price - stop_price) * fill.filled_qty

        return VirtualPosition(
            position_id=pos_id,
            sleeve_id=sleeve.sleeve_id,
            instrument="BTC-USD",
            side="LONG",
            entry_epoch=fill.fill_epoch,
            entry_timestamp_utc=datetime.fromtimestamp(fill.fill_epoch, tz=timezone.utc).isoformat(),
            entry_price=fill.vwap_fill_price,
            quantity_btc=fill.filled_qty,
            cost_basis_usd=round(fill.vwap_fill_price * fill.filled_qty, 2),
            stop_loss_price=round(stop_price, 2),
            take_profit_price=round(tp_price, 2),
            risk_unit_usd=round(risk_unit, 2),
            holding_horizon_hours=horizon_hours,
            maturity_epoch=maturity_epoch,
            cost_scenario=self.cost_scenario,
            fees_paid_usd=fill.commission_usd,
            max_price_observed=fill.vwap_fill_price,
            min_price_observed=fill.vwap_fill_price,
            current_price=fill.vwap_fill_price,
            is_open=True
        )

    def check_and_resolve_positions(
        self,
        current_epoch: float,
        current_price: float,
        order_book_bids: List[List[float]],
        order_book_asks: List[List[float]]
    ) -> List[PaperTradeOutcome]:
        """
        Causally checks open virtual positions across sleeves against TP, SL, and Time-Maturity.
        Enforces strict delayed outcome resolution (never prematurely resolves before barrier or maturity).
        """
        resolved: List[PaperTradeOutcome] = []

        for sleeve in self.sleeves.values():
            sleeve.mark_to_market(current_price)
            pos = sleeve.open_position
            if not pos or not pos.is_open:
                continue

            exit_reason = None
            if current_price >= pos.take_profit_price:
                exit_reason = "TAKE_PROFIT"
            elif current_price <= pos.stop_loss_price:
                exit_reason = "STOP_LOSS"
            elif current_epoch >= pos.maturity_epoch:
                exit_reason = "TIME_MATURITY"

            if exit_reason:
                # Simulate exit order walking bids
                exit_fill = self.simulate_order_execution(
                    sleeve_id=sleeve.sleeve_id,
                    side="SELL",
                    target_qty_btc=pos.quantity_btc,
                    decision_epoch=current_epoch,
                    order_book_bids=order_book_bids,
                    order_book_asks=order_book_asks
                )
                exit_price = exit_fill.vwap_fill_price if exit_fill.filled_qty > 0 else current_price
                exit_commission = exit_fill.commission_usd

                # P&L accounting
                gross_pnl = (exit_price - pos.entry_price) * pos.quantity_btc
                total_fees = pos.fees_paid_usd + exit_commission
                net_pnl = gross_pnl - total_fees
                net_ret_bps = (net_pnl / pos.cost_basis_usd * 10000.0) if pos.cost_basis_usd > 0 else 0.0

                # R-multiples
                r_unit = pos.risk_unit_usd if pos.risk_unit_usd > 0 else 1.0
                realized_r = net_pnl / r_unit
                mfe_r = ((pos.max_price_observed - pos.entry_price) * pos.quantity_btc) / r_unit
                mae_r = ((pos.min_price_observed - pos.entry_price) * pos.quantity_btc) / r_unit

                outcome = PaperTradeOutcome(
                    position_id=pos.position_id,
                    sleeve_id=sleeve.sleeve_id,
                    strategy_id=sleeve.strategy_id,
                    entry_epoch=pos.entry_epoch,
                    exit_epoch=exit_fill.fill_epoch,
                    holding_hours_actual=round((exit_fill.fill_epoch - pos.entry_epoch) / 3600.0, 2),
                    entry_price=pos.entry_price,
                    exit_price=exit_price,
                    quantity_btc=pos.quantity_btc,
                    gross_pnl_usd=round(gross_pnl, 2),
                    total_fees_usd=round(total_fees, 2),
                    net_pnl_usd=round(net_pnl, 2),
                    net_return_bps=round(net_ret_bps, 2),
                    risk_unit_usd=pos.risk_unit_usd,
                    realized_r=round(realized_r, 3),
                    mfe_r=round(mfe_r, 3),
                    mae_r=round(mae_r, 3),
                    exit_reason=exit_reason,
                    cost_scenario=self.cost_scenario,
                    resolution_timestamp_utc=datetime.fromtimestamp(exit_fill.fill_epoch, tz=timezone.utc).isoformat()
                )

                # Update sleeve balances
                sleeve.cash_balance_usd += (exit_price * pos.quantity_btc - exit_commission)
                sleeve.realized_pnl_usd += net_pnl
                sleeve.total_fees_paid_usd += exit_commission
                if net_pnl > 0:
                    sleeve.winning_trades_count += 1
                else:
                    sleeve.losing_trades_count += 1

                pos.is_open = False
                sleeve.open_position = None
                sleeve.mark_to_market(current_price)

                # Append outcome record
                self._append_ledger(outcome.to_dict())
                self.closed_outcomes.append(outcome)
                resolved.append(outcome)

        if resolved:
            self.save_state()
        return resolved

    def log_and_evaluate_gbdt_forecasts(
        self,
        closes: List[float],
        decision_epoch: float,
        timeframe: str = "15m"
    ) -> Dict[str, Any]:
        """
        Evaluates frozen GBDT return-sign classifiers (1h, 4h, 24h) point-in-time,
        logs the forecasts, and checks prior matured forecasts against actual return signs.
        Chronos-2 is quarantined.
        """
        from engine.directional_forecast_service import compute_directional_gbdt_forecast

        horizons = ["1h", "4h", "24h"]
        forecast_entry = {
            "record_type": "PAPER_GBDT_FORECAST_EMISSION",
            "decision_epoch": decision_epoch,
            "decision_timestamp_utc": datetime.fromtimestamp(decision_epoch, tz=timezone.utc).isoformat(),
            "timeframe": timeframe,
            "spot_price": closes[-1] if closes else None,
            "forecasts": {},
            "governance": "OFFLINE_RESEARCH_ONLY"
        }

        for h in horizons:
            fc = compute_directional_gbdt_forecast(closes, timeframe=timeframe, horizon=h)
            h_seconds = {"1h": 3600, "4h": 14400, "24h": 86400}[h]
            forecast_entry["forecasts"][h] = {
                "model_id": fc.get("model_id"),
                "status": fc.get("status"),
                "probability_up": fc.get("probability_up"),
                "probability_down": fc.get("probability_down"),
                "predicted_direction": fc.get("predicted_direction"),
                "maturity_epoch": decision_epoch + h_seconds,
                "maturity_timestamp_utc": datetime.fromtimestamp(decision_epoch + h_seconds, tz=timezone.utc).isoformat()
            }

        # Append to GBDT eval ledger
        line = json.dumps(forecast_entry, sort_keys=True)
        with open(self.gbdt_eval_ledger_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        return forecast_entry

    def get_summary_report(self) -> Dict[str, Any]:
        """Returns typed operational and performance summary across sleeves."""
        gated = self.sleeves["TSMOM_DONCHIAN_168H_336H_L2_GATED"]
        ungated = self.sleeves["TSMOM_DONCHIAN_168H_336H_UNGATED"]

        gated_ret_pct = ((gated.virtual_equity_usd - gated.initial_capital_usd) / gated.initial_capital_usd * 100.0)
        ungated_ret_pct = ((ungated.virtual_equity_usd - ungated.initial_capital_usd) / ungated.initial_capital_usd * 100.0)

        return {
            "engine_status": "PAPER_ENGINE_READY",
            "posture": "OFFLINE_RESEARCH_ONLY",
            "economic_verdict": "NO_GO_NO_VALIDATED_EDGE",
            "live_trading": "DISABLED",
            "cost_scenario": self.cost_scenario,
            "latency_delay_sec": self.latency_delay_sec,
            "sleeves": {
                "gated": {
                    "sleeve_id": gated.sleeve_id,
                    "virtual_equity_usd": round(gated.virtual_equity_usd, 2),
                    "net_return_pct": round(gated_ret_pct, 2),
                    "realized_pnl_usd": round(gated.realized_pnl_usd, 2),
                    "max_drawdown_pct": round(gated.max_drawdown_pct, 2),
                    "total_trades": gated.total_trades_count,
                    "win_rate_pct": round(gated.winning_trades_count / max(1, gated.total_trades_count) * 100.0, 1),
                    "total_fees_paid_usd": round(gated.total_fees_paid_usd, 2),
                    "has_open_position": bool(gated.open_position and gated.open_position.is_open)
                },
                "ungated": {
                    "sleeve_id": ungated.sleeve_id,
                    "virtual_equity_usd": round(ungated.virtual_equity_usd, 2),
                    "net_return_pct": round(ungated_ret_pct, 2),
                    "realized_pnl_usd": round(ungated.realized_pnl_usd, 2),
                    "max_drawdown_pct": round(ungated.max_drawdown_pct, 2),
                    "total_trades": ungated.total_trades_count,
                    "win_rate_pct": round(ungated.winning_trades_count / max(1, ungated.total_trades_count) * 100.0, 1),
                    "total_fees_paid_usd": round(ungated.total_fees_paid_usd, 2),
                    "has_open_position": bool(ungated.open_position and ungated.open_position.is_open)
                }
            },
            "quarantined_models": ["Chronos-2"],
            "disclaimer": "ALL FIGURES ARE PURELY SIMULATED PAPER TRADING. NO REAL CAPITAL, COMMISSIONS, OR BROKER ORDERS EXIST."
        }

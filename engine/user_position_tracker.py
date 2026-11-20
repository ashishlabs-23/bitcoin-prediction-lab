"""
engine/user_position_tracker.py — BTCognitive User Position Tracker & Lifecycle Manager
========================================================================================
Protocol: BTCognitive V32.42 — User Position Tracker & Adaptive Risk Copilot
Governance: OFFLINE_RESEARCH_ONLY | NO_GO_NO_VALIDATED_EDGE | Live Trading: DISABLED

Implements an auditable, isolated user-position registry and lifecycle event store:
1. Non-Execution Safety Invariant:
   - ZERO live broker execution adapters.
   - Users record positions they have ALREADY entered on external venues.
   - The engine provides risk monitoring, diagnostic telemetry, and paper journaling ONLY.
   - Never transmits orders to Coinbase, Binance, or any external exchange.
2. Complete Lifecycle Tracking:
   - OPEN_LONG, OPEN_SHORT, PARTIAL_EXIT, CLOSE_POSITION.
   - Spot BTC-USD strictly forbids naked short positions (SPOT_SHORT_INELIGIBLE).
   - Derivatives (perpetuals/futures) require contract metadata (leverage, margin).
3. Append-Only Persistence & Isolation:
   - Stored in data/research/user_positions/user_position_events.jsonl.
   - Completely isolated from protected prospective ledgers and raw parquet files.
   - Idempotent event deduplication and restart-survival state reconstruction.
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
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger("btcognitive.user_position_tracker")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
USER_POSITIONS_DIR = os.path.join(REPO_ROOT, "data", "research", "user_positions")
DEFAULT_EVENT_LOG = os.path.join(USER_POSITIONS_DIR, "user_position_events.jsonl")
DEFAULT_STATE_FILE = os.path.join(USER_POSITIONS_DIR, "user_positions_state.json")

VALID_INSTRUMENTS = {"BTC-USD", "BTC/USD", "BTC-USDT", "BTC-PERP", "BTC-USD-PERP"}
VALID_VENUES = {"COINBASE", "KRAKEN", "BINANCE", "BITSTAMP", "OTHER"}
VALID_MARKET_TYPES = {"SPOT", "PERPETUAL", "FUTURES"}
VALID_SIDES = {"LONG", "SHORT"}


@dataclass
class PartialExitRecord:
    """Record of an individual partial exit event."""
    exit_id: str
    exit_price: float
    quantity: float
    fee_usd: float
    exit_timestamp_utc: str
    realized_pnl_usd: float
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UserPosition:
    """Full lifecycle state of a user-recorded position."""
    position_id: str
    user_id: str
    instrument: str
    venue: str
    market_type: str  # "SPOT", "PERPETUAL", "FUTURES"
    side: str  # "LONG", "SHORT"
    entry_price: float
    initial_quantity: float
    remaining_quantity: float
    entry_timestamp_utc: str
    entry_fee_usd: float
    accumulated_fees_usd: float
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    leverage: float = 1.0
    margin_usd: Optional[float] = None
    liquidation_price: Optional[float] = None
    status: str = "OPEN"  # "OPEN", "PARTIALLY_CLOSED", "CLOSED"
    notes: Optional[str] = None
    partial_exits: List[PartialExitRecord] = field(default_factory=list)
    closed_timestamp_utc: Optional[str] = None
    final_exit_price: Optional[float] = None
    total_realized_pnl_usd: float = 0.0
    created_at_epoch: float = field(default_factory=time.time)
    updated_at_epoch: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["partial_exits"] = [pe.to_dict() if hasattr(pe, "to_dict") else pe for pe in self.partial_exits]
        return d


class UserPositionTracker:
    """
    Registry and lifecycle manager for user-recorded trading positions.
    Guarantees event idempotency, spot short validation, and persistence isolation.
    """

    def __init__(
        self,
        base_dir: str = USER_POSITIONS_DIR,
        event_log_path: Optional[str] = None,
        state_file_path: Optional[str] = None
    ):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.event_log_path = event_log_path or os.path.join(self.base_dir, "user_position_events.jsonl")
        self.state_file_path = state_file_path or os.path.join(self.base_dir, "user_positions_state.json")

        self.positions: Dict[str, UserPosition] = {}
        self.processed_event_ids: set[str] = set()

        self._recover_state_from_event_log()

    def _recover_state_from_event_log(self):
        """Reconstructs positions deterministically by replaying the append-only event log."""
        if not os.path.exists(self.event_log_path):
            return

        try:
            with open(self.event_log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    event = json.loads(line)
                    self._apply_event_in_memory(event, persist=False)
            logger.info(f"Reconstructed {len(self.positions)} user positions from event log.")
        except Exception as e:
            logger.error(f"Error recovering user positions from event log: {e}")

    def _persist_event(self, event: Dict[str, Any]):
        """Atomically appends an event to the append-only log and writes state snapshot."""
        line = json.dumps(event, sort_keys=True)
        with open(self.event_log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        # Snapshot write
        self._save_state_snapshot()

    def _save_state_snapshot(self):
        """Writes atomic JSON snapshot of active and closed positions."""
        snapshot = {
            "version": "V32.42_USER_POSITIONS",
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "positions_count": len(self.positions),
            "positions": {pid: p.to_dict() for pid, p in self.positions.items()},
            "governance": {
                "posture": "OFFLINE_RESEARCH_ONLY",
                "live_trading": "DISABLED",
                "purpose": "POSITION_RISK_MONITORING_ONLY"
            }
        }
        tmp_path = self.state_file_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)
        os.replace(tmp_path, self.state_file_path)

    def _apply_event_in_memory(self, event: Dict[str, Any], persist: bool = False) -> Tuple[bool, Optional[str]]:
        """Applies a position lifecycle event to in-memory state."""
        event_id = event.get("event_id")
        if not event_id:
            return False, "Missing event_id"

        if event_id in self.processed_event_ids:
            return False, f"Duplicate event_id '{event_id}' rejected (idempotency guard)"

        event_type = event.get("event_type")
        pos_id = event.get("position_id")

        if event_type in ("OPEN_LONG", "OPEN_SHORT"):
            if pos_id in self.positions:
                return False, f"Position '{pos_id}' already exists"

            partial_exits_raw = event.get("partial_exits", [])
            partial_exits = [
                PartialExitRecord(**pe) if isinstance(pe, dict) else pe
                for pe in partial_exits_raw
            ]

            pos = UserPosition(
                position_id=pos_id,
                user_id=event.get("user_id", "default_user"),
                instrument=event["instrument"],
                venue=event.get("venue", "COINBASE"),
                market_type=event.get("market_type", "SPOT"),
                side=event["side"],
                entry_price=float(event["entry_price"]),
                initial_quantity=float(event["quantity"]),
                remaining_quantity=float(event["quantity"]),
                entry_timestamp_utc=event["entry_timestamp_utc"],
                entry_fee_usd=float(event.get("entry_fee_usd", 0.0)),
                accumulated_fees_usd=float(event.get("entry_fee_usd", 0.0)),
                stop_loss_price=float(event["stop_loss_price"]) if event.get("stop_loss_price") is not None else None,
                take_profit_price=float(event["take_profit_price"]) if event.get("take_profit_price") is not None else None,
                leverage=float(event.get("leverage", 1.0)),
                margin_usd=float(event["margin_usd"]) if event.get("margin_usd") is not None else None,
                liquidation_price=float(event["liquidation_price"]) if event.get("liquidation_price") is not None else None,
                status="OPEN",
                notes=event.get("notes"),
                partial_exits=partial_exits,
                created_at_epoch=event.get("timestamp_epoch", time.time()),
                updated_at_epoch=event.get("timestamp_epoch", time.time())
            )
            self.positions[pos_id] = pos
            self.processed_event_ids.add(event_id)

        elif event_type == "PARTIAL_EXIT":
            if pos_id not in self.positions:
                return False, f"Position '{pos_id}' not found"
            pos = self.positions[pos_id]
            if pos.status == "CLOSED":
                return False, f"Position '{pos_id}' is already CLOSED"

            exit_qty = float(event["quantity"])
            if exit_qty <= 0:
                return False, f"Exit quantity must be positive, got {exit_qty}"
            if exit_qty > pos.remaining_quantity:
                return False, f"Exit quantity {exit_qty} exceeds remaining quantity {pos.remaining_quantity}"

            exit_price = float(event["exit_price"])
            fee_usd = float(event.get("fee_usd", 0.0))

            # P&L calculation for exited fraction
            if pos.side == "LONG":
                gross_pnl = (exit_price - pos.entry_price) * exit_qty
            else:
                gross_pnl = (pos.entry_price - exit_price) * exit_qty

            realized_pnl = gross_pnl - fee_usd

            partial_record = PartialExitRecord(
                exit_id=event.get("exit_id", f"exit_{event_id[:8]}"),
                exit_price=exit_price,
                quantity=exit_qty,
                fee_usd=fee_usd,
                exit_timestamp_utc=event["timestamp_utc"],
                realized_pnl_usd=round(realized_pnl, 2),
                reason=event.get("reason")
            )
            pos.partial_exits.append(partial_record)
            pos.remaining_quantity = round(pos.remaining_quantity - exit_qty, 8)
            pos.accumulated_fees_usd = round(pos.accumulated_fees_usd + fee_usd, 2)
            pos.total_realized_pnl_usd = round(pos.total_realized_pnl_usd + realized_pnl, 2)
            pos.updated_at_epoch = event.get("timestamp_epoch", time.time())

            if pos.remaining_quantity <= 1e-8:
                pos.status = "CLOSED"
                pos.closed_timestamp_utc = event["timestamp_utc"]
                pos.final_exit_price = exit_price
            else:
                pos.status = "PARTIALLY_CLOSED"

            self.processed_event_ids.add(event_id)

        elif event_type == "CLOSE_POSITION":
            if pos_id not in self.positions:
                return False, f"Position '{pos_id}' not found"
            pos = self.positions[pos_id]
            if pos.status == "CLOSED":
                return False, f"Position '{pos_id}' is already CLOSED"

            exit_price = float(event["exit_price"])
            fee_usd = float(event.get("fee_usd", 0.0))
            closing_qty = pos.remaining_quantity

            if pos.side == "LONG":
                gross_pnl = (exit_price - pos.entry_price) * closing_qty
            else:
                gross_pnl = (pos.entry_price - exit_price) * closing_qty

            realized_pnl = gross_pnl - fee_usd

            partial_record = PartialExitRecord(
                exit_id=event.get("exit_id", f"close_{event_id[:8]}"),
                exit_price=exit_price,
                quantity=closing_qty,
                fee_usd=fee_usd,
                exit_timestamp_utc=event["timestamp_utc"],
                realized_pnl_usd=round(realized_pnl, 2),
                reason=event.get("reason", "FULL_CLOSE")
            )
            pos.partial_exits.append(partial_record)
            pos.remaining_quantity = 0.0
            pos.accumulated_fees_usd = round(pos.accumulated_fees_usd + fee_usd, 2)
            pos.total_realized_pnl_usd = round(pos.total_realized_pnl_usd + realized_pnl, 2)
            pos.status = "CLOSED"
            pos.closed_timestamp_utc = event["timestamp_utc"]
            pos.final_exit_price = exit_price
            pos.updated_at_epoch = event.get("timestamp_epoch", time.time())
            self.processed_event_ids.add(event_id)

        else:
            return False, f"Unsupported event_type '{event_type}'"

        if persist:
            self._persist_event(event)

        return True, None

    def record_open_position(
        self,
        position_id: str,
        instrument: str,
        side: str,
        entry_price: float,
        quantity: float,
        entry_timestamp_utc: str,
        user_id: str = "default_user",
        venue: str = "COINBASE",
        market_type: str = "SPOT",
        entry_fee_usd: float = 0.0,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        leverage: float = 1.0,
        margin_usd: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Tuple[Optional[UserPosition], Optional[str]]:
        """
        Validates and records a newly opened user position.
        Enforces spot short ineligibility and derivative contract validation.
        """
        # 1. Parameter Validations
        side_clean = str(side).upper().strip()
        if side_clean not in VALID_SIDES:
            return None, f"Invalid side '{side}'. Must be 'LONG' or 'SHORT'."

        mkt_clean = str(market_type).upper().strip()
        if mkt_clean not in VALID_MARKET_TYPES:
            return None, f"Invalid market_type '{market_type}'. Must be one of {VALID_MARKET_TYPES}."

        # 2. Spot Short Constraint Enforcement
        if mkt_clean == "SPOT" and side_clean == "SHORT":
            return None, (
                "SPOT_SHORT_INELIGIBLE: Spot short positions on BTC-USD are not supported "
                "without an explicit borrow/collateral facility. Please select PERPETUAL or FUTURES."
            )

        if entry_price <= 0 or not math.isfinite(entry_price):
            return None, f"Invalid entry_price: {entry_price}"

        if quantity <= 0 or not math.isfinite(quantity):
            return None, f"Invalid quantity: {quantity}"

        # 3. Optional Stops & Targets Logic
        if stop_loss_price is not None:
            if stop_loss_price <= 0 or not math.isfinite(stop_loss_price):
                return None, f"Invalid stop_loss_price: {stop_loss_price}"
            if side_clean == "LONG" and stop_loss_price >= entry_price:
                return None, f"For LONG position, stop_loss_price ({stop_loss_price}) must be below entry_price ({entry_price})"
            if side_clean == "SHORT" and stop_loss_price <= entry_price:
                return None, f"For SHORT position, stop_loss_price ({stop_loss_price}) must be above entry_price ({entry_price})"

        if take_profit_price is not None:
            if take_profit_price <= 0 or not math.isfinite(take_profit_price):
                return None, f"Invalid take_profit_price: {take_profit_price}"
            if side_clean == "LONG" and take_profit_price <= entry_price:
                return None, f"For LONG position, take_profit_price ({take_profit_price}) must be above entry_price ({entry_price})"
            if side_clean == "SHORT" and take_profit_price >= entry_price:
                return None, f"For SHORT position, take_profit_price ({take_profit_price}) must be below entry_price ({entry_price})"

        # 4. Derivative Contract / Liquidation Modeling
        liquidation_price = None
        if mkt_clean in ("PERPETUAL", "FUTURES"):
            lev = max(1.0, float(leverage))
            mm_rate = 0.005  # Standard 0.5% maintenance margin
            if side_clean == "LONG":
                liquidation_price = round(entry_price * (1.0 - (1.0 / lev) + mm_rate), 2)
            else:
                liquidation_price = round(entry_price * (1.0 + (1.0 / lev) - mm_rate), 2)

        # 5. Construct Event
        event_id = hashlib.sha256(f"{position_id}:OPEN:{entry_timestamp_utc}".encode()).hexdigest()[:16]
        event = {
            "event_id": event_id,
            "event_type": f"OPEN_{side_clean}",
            "position_id": position_id,
            "user_id": user_id,
            "instrument": instrument,
            "venue": venue,
            "market_type": mkt_clean,
            "side": side_clean,
            "entry_price": entry_price,
            "quantity": quantity,
            "entry_timestamp_utc": entry_timestamp_utc,
            "entry_fee_usd": entry_fee_usd,
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "leverage": leverage,
            "margin_usd": margin_usd or ((entry_price * quantity) / max(1.0, leverage)),
            "liquidation_price": liquidation_price,
            "notes": notes,
            "timestamp_epoch": time.time(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        }

        success, err = self._apply_event_in_memory(event, persist=True)
        if not success:
            return None, err

        return self.positions[position_id], None

    def record_partial_exit(
        self,
        position_id: str,
        exit_price: float,
        quantity: float,
        exit_timestamp_utc: str,
        fee_usd: float = 0.0,
        reason: Optional[str] = None
    ) -> Tuple[Optional[UserPosition], Optional[str]]:
        """Records a partial exit from an open position."""
        if position_id not in self.positions:
            return None, f"Position '{position_id}' not found"

        pos = self.positions[position_id]
        if pos.status == "CLOSED":
            return None, f"Position '{position_id}' is already closed"

        if exit_price <= 0 or not math.isfinite(exit_price):
            return None, f"Invalid exit_price: {exit_price}"

        if quantity <= 0 or quantity > pos.remaining_quantity:
            return None, f"Invalid quantity: must be between 0 and remaining {pos.remaining_quantity}"

        event_id = hashlib.sha256(f"{position_id}:PARTIAL:{exit_timestamp_utc}:{quantity}".encode()).hexdigest()[:16]
        event = {
            "event_id": event_id,
            "event_type": "PARTIAL_EXIT",
            "position_id": position_id,
            "exit_id": f"pe_{event_id[:8]}",
            "exit_price": exit_price,
            "quantity": quantity,
            "fee_usd": fee_usd,
            "timestamp_utc": exit_timestamp_utc,
            "reason": reason,
            "timestamp_epoch": time.time()
        }

        success, err = self._apply_event_in_memory(event, persist=True)
        if not success:
            return None, err

        return self.positions[position_id], None

    def record_close_position(
        self,
        position_id: str,
        exit_price: float,
        exit_timestamp_utc: str,
        fee_usd: float = 0.0,
        reason: Optional[str] = "USER_REQUESTED_CLOSE"
    ) -> Tuple[Optional[UserPosition], Optional[str]]:
        """Records full closing of remaining position."""
        if position_id not in self.positions:
            return None, f"Position '{position_id}' not found"

        pos = self.positions[position_id]
        if pos.status == "CLOSED":
            return None, f"Position '{position_id}' is already closed"

        if exit_price <= 0 or not math.isfinite(exit_price):
            return None, f"Invalid exit_price: {exit_price}"

        event_id = hashlib.sha256(f"{position_id}:CLOSE:{exit_timestamp_utc}".encode()).hexdigest()[:16]
        event = {
            "event_id": event_id,
            "event_type": "CLOSE_POSITION",
            "position_id": position_id,
            "exit_id": f"close_{event_id[:8]}",
            "exit_price": exit_price,
            "fee_usd": fee_usd,
            "timestamp_utc": exit_timestamp_utc,
            "reason": reason,
            "timestamp_epoch": time.time()
        }

        success, err = self._apply_event_in_memory(event, persist=True)
        if not success:
            return None, err

        return self.positions[position_id], None

    def get_open_positions(self, user_id: Optional[str] = None) -> List[UserPosition]:
        """Returns all positions with status OPEN or PARTIALLY_CLOSED."""
        result = [
            p for p in self.positions.values()
            if p.status in ("OPEN", "PARTIALLY_CLOSED")
        ]
        if user_id:
            result = [p for p in result if p.user_id == user_id]
        return sorted(result, key=lambda x: x.created_at_epoch, reverse=True)

    def get_closed_positions(self, user_id: Optional[str] = None) -> List[UserPosition]:
        """Returns all positions with status CLOSED."""
        result = [p for p in self.positions.values() if p.status == "CLOSED"]
        if user_id:
            result = [p for p in result if p.user_id == user_id]
        return sorted(result, key=lambda x: x.updated_at_epoch, reverse=True)

    def get_position(self, position_id: str) -> Optional[UserPosition]:
        return self.positions.get(position_id)

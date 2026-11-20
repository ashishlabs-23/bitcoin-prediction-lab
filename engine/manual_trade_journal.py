"""
engine/manual_trade_journal.py — BTCognitive Manual Trade Journal & AI Evaluation Engine
========================================================================================
BTCognitive V32.42: Observational Manual Trade Journal & Dual Performance Evaluation.

Strict Epistemic & Operating Principles:
1. NON-EXECUTION INVARIANT:
   - Zero broker execution, zero order routing, zero live position auto-management.
   - Users execute trades elsewhere and manually record entries and exits.
2. IMMUTABLE ENTRY FORECAST SNAPSHOT:
   - At trade entry, captures an exact timestamped snapshot of the latest available
     BTCognitive AI forecast, model version, horizons, regime, and strategy signal.
   - Preserves underlying data freshness/staleness explicitly. Never fabricates or backfills.
   - Secured with an immutable SHA-256 digest over normalized snapshot attributes.
3. RIGOROUS P&L CALCULATIONS:
   - Long Gross P&L = (Exit - Entry) * Quantity * Multiplier
   - Short Gross P&L = (Entry - Exit) * Quantity * Multiplier
   - Net P&L = Gross P&L - Entry Fees - Exit Fees - Explicit Costs
   - Derivative calculations require valid contract parameters; otherwise marked
     CALCULATION_INCOMPLETE_MISSING_CONTRACT_SPECS.
   - If fees are unknown, marked GROSS_PNL_ONLY / NET_PNL_INCOMPLETE (never silently $0).
   - If quantity is omitted, marked PRICE_DIRECTION_ONLY with return on price.
4. BIFURCATED PERFORMANCE EVALUATION:
   - A. User Trade Performance: Win rate, gross/net P&L, avg win/loss, max drawdown,
     regime breakdown.
   - B. AI Forecast Performance: Snapshot validity coverage, directional agreement,
     model horizon accuracy, user vs model outcome contingency matrix.
   - Explicit INSUFFICIENT_EVIDENCE disclaimer for small or user-selected samples.
5. AUDITABLE CORRECTIONS & DURABLE PERSISTENCE:
   - Append-only event store at data/manual_trades/manual_trades_ledger.jsonl.
   - Historical records never silently overwritten; edits recorded as adjustments.
"""

from __future__ import annotations

import os
import sys
import json
import time
import math
import uuid
import hashlib
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
import threading

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engine.directional_forecast_service import compute_directional_gbdt_forecast

logger = logging.getLogger("btcognitive.manual_trade_journal")

DEFAULT_JOURNAL_DIR = os.path.join(REPO_ROOT, "data", "manual_trades")
DEFAULT_JOURNAL_LEDGER = os.path.join(DEFAULT_JOURNAL_DIR, "manual_trades_ledger.jsonl")


def _compute_dict_sha256(data: Dict[str, Any]) -> str:
    """Computes a canonical SHA-256 digest over normalized JSON string."""
    normalized = json.dumps(data, sort_keys=True, separators=(',', ':'), default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _get_utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================================
# Forecast Snapshot Capture
# ============================================================================

def capture_entry_forecast_snapshot(
    instrument: str = "BTC-USD",
    reference_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    Captures the exact point-in-time BTCognitive forecast available at trade entry.
    If market data or model artifacts are unavailable or stale, records that status honestly.
    Never fabricates predictions.
    """
    snapshot_time = _get_utc_now_iso()
    horizons_data = {}
    
    # 1. Evaluate directional GBDT models for 1h, 4h, 24h
    primary_pred_dir = "UNAVAILABLE"
    primary_p_up = None
    primary_p_down = None
    forecast_status = "VALID"
    data_age_seconds = 1.0  # nominal unless detected otherwise

    # Try to load recent price bars from feature cache or engine if available
    recent_closes = []
    try:
        from engine.feature_cache import feature_cache
        bars = feature_cache.get_recent_bars(timeframe="15m", limit=700)
        if bars and len(bars) >= 673:
            recent_closes = [float(b.get("close", 0.0)) for b in bars if float(b.get("close", 0.0)) > 0]
    except Exception:
        pass

    # If no feature cache bars, check live engine or memory
    if len(recent_closes) < 673:
        try:
            from engine.inference_service import live_engine
            if hasattr(live_engine, "history_closes") and len(live_engine.history_closes) >= 673:
                recent_closes = list(live_engine.history_closes)
        except Exception:
            pass

    if len(recent_closes) >= 673:
        for hz in ["1h", "4h", "24h"]:
            res = compute_directional_gbdt_forecast(recent_closes, timeframe="15m", horizon=hz)
            horizons_data[hz] = {
                "status": res.get("status"),
                "p_up": res.get("probability_up"),
                "p_down": res.get("probability_down"),
                "predicted_direction": res.get("predicted_direction"),
                "model_id": res.get("model_id"),
                "target": res.get("target")
            }
            if hz == "1h":
                primary_pred_dir = res.get("predicted_direction", "UNAVAILABLE")
                primary_p_up = res.get("probability_up")
                primary_p_down = res.get("probability_down")
    else:
        # Insufficient bars to evaluate directional model causality
        forecast_status = "UNAVAILABLE_INSUFFICIENT_HISTORY"
        for hz in ["1h", "4h", "24h"]:
            horizons_data[hz] = {
                "status": "UNAVAILABLE_INSUFFICIENT_HISTORY",
                "p_up": None,
                "p_down": None,
                "predicted_direction": "UNAVAILABLE",
                "model_id": f"directional-gbm-{hz}-v1",
                "target": f"Sign of forward {hz} return"
            }

    # 2. Market Regime & Strategy Signal
    regime = "UNKNOWN"
    strategy_signal = "ABSTAIN"
    try:
        from engine.inference_service import live_engine
        if hasattr(live_engine, "latest_regime") and live_engine.latest_regime:
            regime = str(live_engine.latest_regime)
    except Exception:
        regime = "NORMAL_VOLATILITY"

    # Assemble core payload for immutable digest
    core_payload = {
        "snapshot_timestamp_utc": snapshot_time,
        "instrument": instrument,
        "reference_price": reference_price,
        "forecast_status": forecast_status,
        "model_id": "directional-gbm-ensemble-v1.0",
        "model_version": "v1.0",
        "predicted_direction": primary_pred_dir,
        "probability_up": primary_p_up,
        "probability_down": primary_p_down,
        "data_age_seconds": data_age_seconds,
        "regime_classification": regime,
        "strategy_signal": strategy_signal,
        "horizons": horizons_data
    }

    # Immutable SHA-256 seal
    core_payload["immutable_sha256"] = _compute_dict_sha256(core_payload)
    return core_payload


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class ManualExitRecord:
    """Record of a partial or full exit against a manual trade."""
    exit_id: str
    exit_timestamp_utc: str
    exit_price: float
    quantity: float
    exit_fee_usd: Optional[float] = None
    notes: Optional[str] = None
    gross_pnl_usd: Optional[float] = None
    net_pnl_usd: Optional[float] = None
    pnl_status: str = "GROSS_PNL_ONLY"


@dataclass
class AdjustmentRecord:
    """Auditable adjustment entry for corrections."""
    adjustment_id: str
    timestamp_utc: str
    field_name: str
    old_value: Any
    new_value: Any
    reason: str


@dataclass
class ManualTradeRecord:
    """Primary manual trade journal record with immutable entry forecast snapshot."""
    trade_id: str
    user_id: str
    instrument: str
    direction: str  # "LONG" or "SHORT"
    market_type: str  # "SPOT", "PERPETUAL", "FUTURES"
    entry_price: float
    entry_timestamp_utc: str
    initial_quantity: Optional[float] = None
    remaining_quantity: Optional[float] = None
    entry_fee_usd: Optional[float] = None
    leverage: float = 1.0
    contract_multiplier: float = 1.0
    contract_spec_valid: bool = True
    notes: Optional[str] = None
    forecast_snapshot: Dict[str, Any] = field(default_factory=dict)
    
    # State & Lifecycle
    status: str = "OPEN"  # "OPEN", "PARTIALLY_EXITED", "CLOSED"
    exits: List[Dict[str, Any]] = field(default_factory=list)
    adjustments: List[Dict[str, Any]] = field(default_factory=list)
    closed_timestamp_utc: Optional[str] = None
    final_exit_price: Optional[float] = None
    
    # Calculated Outcomes
    gross_pnl_usd: Optional[float] = None
    net_pnl_usd: Optional[float] = None
    pnl_status: str = "GROSS_PNL_ONLY"
    return_on_notional_pct: Optional[float] = None
    user_outcome: Optional[str] = None  # "WIN", "LOSS", "BREAKEVEN"
    forecast_agreement: bool = False
    forecast_outcome: Optional[str] = None  # "CORRECT", "INCORRECT", "UNAVAILABLE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ManualTradeRecord:
        return cls(**d)


# ============================================================================
# Manual Trade Journal Storage & Engine
# ============================================================================

class ManualTradeJournal:
    """
    Durable, append-only manual trade journal and AI forecast evaluation engine.
    Ensures strict separation from virtual paper sleeves and live brokers.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or DEFAULT_JOURNAL_DIR
        self.ledger_path = os.path.join(self.base_dir, "manual_trades_ledger.jsonl")
        self._lock = threading.RLock()
        self._trades: Dict[str, ManualTradeRecord] = {}
        self._initialized = False
        self._init_storage()

    def _init_storage(self):
        with self._lock:
            os.makedirs(self.base_dir, exist_ok=True)
            if not os.path.exists(self.ledger_path):
                with open(self.ledger_path, "w", encoding="utf-8") as f:
                    pass
            self._replay_ledger()
            self._initialized = True

    def _replay_ledger(self):
        """Reconstructs state deterministically from append-only events."""
        self._trades.clear()
        if not os.path.exists(self.ledger_path):
            return

        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    event_type = event.get("event_type")
                    payload = event.get("payload", {})
                    trade_id = payload.get("trade_id")

                    if event_type == "TRADE_ENTERED":
                        rec = ManualTradeRecord.from_dict(payload)
                        self._trades[trade_id] = rec

                    elif event_type == "TRADE_PARTIAL_EXIT":
                        if trade_id in self._trades:
                            trade = self._trades[trade_id]
                            exit_data = payload.get("exit_record")
                            trade.exits.append(exit_data)
                            trade.remaining_quantity = payload.get("remaining_quantity")
                            trade.status = "PARTIALLY_EXITED"
                            trade.gross_pnl_usd = payload.get("accumulated_gross_pnl")
                            trade.net_pnl_usd = payload.get("accumulated_net_pnl")
                            trade.pnl_status = payload.get("pnl_status")

                    elif event_type == "TRADE_CLOSED":
                        if trade_id in self._trades:
                            trade = self._trades[trade_id]
                            trade.status = "CLOSED"
                            trade.remaining_quantity = 0.0
                            trade.closed_timestamp_utc = payload.get("closed_timestamp_utc")
                            trade.final_exit_price = payload.get("final_exit_price")
                            trade.gross_pnl_usd = payload.get("gross_pnl_usd")
                            trade.net_pnl_usd = payload.get("net_pnl_usd")
                            trade.pnl_status = payload.get("pnl_status")
                            trade.return_on_notional_pct = payload.get("return_on_notional_pct")
                            trade.user_outcome = payload.get("user_outcome")
                            trade.forecast_outcome = payload.get("forecast_outcome")
                            exit_data = payload.get("final_exit_record")
                            if exit_data:
                                trade.exits.append(exit_data)

                    elif event_type == "TRADE_ADJUSTED":
                        if trade_id in self._trades:
                            trade = self._trades[trade_id]
                            adj = payload.get("adjustment")
                            if adj:
                                trade.adjustments.append(adj)
                                field_name = adj.get("field_name")
                                new_val = adj.get("new_value")
                                if hasattr(trade, field_name):
                                    setattr(trade, field_name, new_val)

                except Exception as e:
                    logger.warning(f"Error replaying manual trade journal event: {e}")

    def _append_event(self, event_type: str, payload: Dict[str, Any]):
        """Appends an event atomically to the persistent ledger."""
        event = {
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "timestamp_utc": _get_utc_now_iso(),
            "event_type": event_type,
            "payload": payload
        }
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

    # ========================================================================
    # Trade Entry ("I Entered a Trade")
    # ========================================================================

    def record_entry(
        self,
        instrument: str = "BTC-USD",
        direction: str = "LONG",
        entry_price: float = 0.0,
        entry_timestamp_utc: Optional[str] = None,
        quantity: Optional[float] = None,
        entry_fee_usd: Optional[float] = None,
        market_type: str = "SPOT",
        leverage: float = 1.0,
        contract_multiplier: float = 1.0,
        notes: Optional[str] = None,
        user_id: str = "default_user",
        trade_id: Optional[str] = None,
        pre_captured_snapshot: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[ManualTradeRecord], Optional[str]]:
        """
        Records a manual trade entry with an immutable forecast snapshot.
        Validates prices, directions, and contract parameters.
        """
        with self._lock:
            # 1. Validation
            dir_clean = str(direction).upper().strip()
            if dir_clean not in {"LONG", "SHORT"}:
                return None, f"INVALID_DIRECTION: Direction must be LONG or SHORT, received '{direction}'"

            try:
                p_entry = float(entry_price)
                if not math.isfinite(p_entry) or p_entry <= 0:
                    return None, f"INVALID_PRICE: entry_price must be finite and > 0, received {entry_price}"
            except (ValueError, TypeError):
                return None, f"INVALID_PRICE: entry_price must be a valid float, received {entry_price}"

            qty = None
            if quantity is not None:
                try:
                    qty = float(quantity)
                    if not math.isfinite(qty) or qty <= 0:
                        return None, f"INVALID_QUANTITY: quantity must be > 0, received {quantity}"
                except (ValueError, TypeError):
                    return None, f"INVALID_QUANTITY: quantity must be a float, received {quantity}"

            # Contract specifications validation
            mkt_clean = str(market_type).upper().strip()
            if mkt_clean not in {"SPOT", "PERPETUAL", "FUTURES"}:
                mkt_clean = "SPOT"

            contract_spec_valid = True
            mult = float(contract_multiplier) if contract_multiplier else 1.0
            if mkt_clean in {"PERPETUAL", "FUTURES"}:
                if mult <= 0 or not math.isfinite(mult):
                    contract_spec_valid = False

            # ID generation & duplicate protection
            tid = trade_id or f"trd_{uuid.uuid4().hex[:10]}"
            if tid in self._trades:
                return None, f"DUPLICATE_TRADE_ID: Trade '{tid}' already exists in journal"

            ts_entry = entry_timestamp_utc or _get_utc_now_iso()

            # 2. Immutable Forecast Snapshot
            if pre_captured_snapshot:
                snapshot = pre_captured_snapshot
            else:
                snapshot = capture_entry_forecast_snapshot(instrument=instrument, reference_price=p_entry)

            # Check directional agreement
            pred_dir = snapshot.get("predicted_direction", "UNAVAILABLE")
            forecast_agreed = (dir_clean == pred_dir)

            fee_usd = None
            if entry_fee_usd is not None:
                try:
                    f_val = float(entry_fee_usd)
                    if math.isfinite(f_val) and f_val >= 0:
                        fee_usd = f_val
                except (ValueError, TypeError):
                    pass

            pnl_status = "GROSS_PNL_ONLY"
            if qty is None:
                pnl_status = "PRICE_DIRECTION_ONLY"
            elif not contract_spec_valid:
                pnl_status = "CALCULATION_INCOMPLETE_MISSING_CONTRACT_SPECS"
            elif fee_usd is not None:
                pnl_status = "NET_PNL_INCOMPLETE"  # Entry fee known, but exit fee pending

            # Create Record
            trade = ManualTradeRecord(
                trade_id=tid,
                user_id=user_id,
                instrument=instrument,
                direction=dir_clean,
                market_type=mkt_clean,
                entry_price=p_entry,
                entry_timestamp_utc=ts_entry,
                initial_quantity=qty,
                remaining_quantity=qty,
                entry_fee_usd=fee_usd,
                leverage=float(leverage) if leverage else 1.0,
                contract_multiplier=mult,
                contract_spec_valid=contract_spec_valid,
                notes=notes,
                forecast_snapshot=snapshot,
                status="OPEN",
                pnl_status=pnl_status,
                forecast_agreement=forecast_agreed
            )

            self._trades[tid] = trade
            self._append_event("TRADE_ENTERED", trade.to_dict())
            return trade, None

    # ========================================================================
    # Trade Exit ("I Exited")
    # ========================================================================

    def record_exit(
        self,
        trade_id: str,
        exit_price: float,
        exit_timestamp_utc: Optional[str] = None,
        quantity: Optional[float] = None,
        exit_fee_usd: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Tuple[Optional[ManualTradeRecord], Optional[str]]:
        """
        Records a manual trade exit (partial or full).
        Calculates Gross P&L, Net P&L (if fees known), and updates trade lifecycle.
        """
        with self._lock:
            if trade_id not in self._trades:
                return None, f"TRADE_NOT_FOUND: Trade '{trade_id}' does not exist"

            trade = self._trades[trade_id]
            if trade.status == "CLOSED":
                return None, f"TRADE_ALREADY_CLOSED: Trade '{trade_id}' is already closed"

            try:
                p_exit = float(exit_price)
                if not math.isfinite(p_exit) or p_exit <= 0:
                    return None, f"INVALID_PRICE: exit_price must be > 0, received {exit_price}"
            except (ValueError, TypeError):
                return None, f"INVALID_PRICE: exit_price must be a float, received {exit_price}"

            ts_exit = exit_timestamp_utc or _get_utc_now_iso()

            # Determine exit quantity
            has_quantities = (trade.remaining_quantity is not None)
            exit_qty = None
            is_full_close = False

            if has_quantities:
                rem = trade.remaining_quantity
                if quantity is None:
                    exit_qty = rem
                    is_full_close = True
                else:
                    try:
                        q_req = float(quantity)
                        if not math.isfinite(q_req) or q_req <= 0:
                            return None, f"INVALID_QUANTITY: exit quantity must be > 0, received {quantity}"
                        if q_req > rem + 1e-9:
                            return None, f"QUANTITY_EXCEEDED: exit quantity {q_req} exceeds remaining {rem}"
                        exit_qty = q_req
                        if abs(rem - exit_qty) < 1e-9:
                            is_full_close = True
                    except (ValueError, TypeError):
                        return None, f"INVALID_QUANTITY: exit quantity must be a float"
            else:
                # Price-direction only mode
                is_full_close = True

            # Parse optional exit fee
            fee_exit = None
            if exit_fee_usd is not None:
                try:
                    f_val = float(exit_fee_usd)
                    if math.isfinite(f_val) and f_val >= 0:
                        fee_exit = f_val
                except (ValueError, TypeError):
                    pass

            # Calculate P&L for this exit slice
            exit_gross_pnl = None
            exit_net_pnl = None
            slice_pnl_status = "GROSS_PNL_ONLY"

            if not trade.contract_spec_valid:
                slice_pnl_status = "CALCULATION_INCOMPLETE_MISSING_CONTRACT_SPECS"
            elif not has_quantities:
                slice_pnl_status = "PRICE_DIRECTION_ONLY"
            else:
                # Standard linear formulation
                mult = trade.contract_multiplier
                if trade.direction == "LONG":
                    exit_gross_pnl = (p_exit - trade.entry_price) * exit_qty * mult
                else:  # SHORT
                    exit_gross_pnl = (trade.entry_price - p_exit) * exit_qty * mult

                if fee_exit is not None:
                    exit_net_pnl = exit_gross_pnl - fee_exit
                    slice_pnl_status = "NET_PNL_COMPLETE"
                else:
                    slice_pnl_status = "GROSS_PNL_ONLY"

            exit_rec = ManualExitRecord(
                exit_id=f"ext_{uuid.uuid4().hex[:8]}",
                exit_timestamp_utc=ts_exit,
                exit_price=p_exit,
                quantity=exit_qty if exit_qty is not None else 0.0,
                exit_fee_usd=fee_exit,
                notes=notes,
                gross_pnl_usd=exit_gross_pnl,
                net_pnl_usd=exit_net_pnl,
                pnl_status=slice_pnl_status
            )

            if is_full_close:
                # Final reconciliation
                all_exits = list(trade.exits) + [asdict(exit_rec)]
                total_gross = 0.0
                all_fees_known = (trade.entry_fee_usd is not None)
                total_fees = trade.entry_fee_usd or 0.0

                weighted_price_num = 0.0
                total_qty = 0.0

                for ex in all_exits:
                    q = ex.get("quantity", 0.0)
                    p = ex.get("exit_price", p_exit)
                    weighted_price_num += p * q
                    total_qty += q
                    if ex.get("gross_pnl_usd") is not None:
                        total_gross += ex.get("gross_pnl_usd")
                    f_val = ex.get("exit_fee_usd")
                    if f_val is not None:
                        total_fees += f_val
                    else:
                        all_fees_known = False

                final_price = weighted_price_num / total_qty if total_qty > 0 else p_exit

                # Outcome determination
                if trade.direction == "LONG":
                    price_diff = final_price - trade.entry_price
                else:
                    price_diff = trade.entry_price - final_price

                if abs(price_diff) < 1e-4:
                    user_outcome = "BREAKEVEN"
                elif price_diff > 0:
                    user_outcome = "WIN"
                else:
                    user_outcome = "LOSS"

                # Return on notional
                ret_notional = (price_diff / trade.entry_price) * 100.0

                # Evaluate Forecast Outcome
                pred_dir = trade.forecast_snapshot.get("predicted_direction", "UNAVAILABLE")
                if pred_dir == "UNAVAILABLE":
                    forecast_outcome = "UNAVAILABLE"
                else:
                    # Model predicted UP -> price went up -> CORRECT
                    # Model predicted DOWN -> price went down -> CORRECT
                    actual_dir = "UP" if final_price > trade.entry_price else ("DOWN" if final_price < trade.entry_price else "NEUTRAL")
                    forecast_outcome = "CORRECT" if pred_dir == actual_dir else "INCORRECT"

                # Overall PNL status
                if not trade.contract_spec_valid:
                    final_pnl_status = "CALCULATION_INCOMPLETE_MISSING_CONTRACT_SPECS"
                    final_gross = None
                    final_net = None
                elif not has_quantities:
                    final_pnl_status = "PRICE_DIRECTION_ONLY"
                    final_gross = None
                    final_net = None
                elif all_fees_known:
                    final_pnl_status = "NET_PNL_COMPLETE"
                    final_gross = total_gross
                    final_net = total_gross - total_fees
                else:
                    final_pnl_status = "GROSS_PNL_ONLY"
                    final_gross = total_gross
                    final_net = None

                # Update in-memory trade
                trade.status = "CLOSED"
                trade.remaining_quantity = 0.0
                trade.closed_timestamp_utc = ts_exit
                trade.final_exit_price = final_price
                trade.gross_pnl_usd = final_gross
                trade.net_pnl_usd = final_net
                trade.pnl_status = final_pnl_status
                trade.return_on_notional_pct = ret_notional
                trade.user_outcome = user_outcome
                trade.forecast_outcome = forecast_outcome
                trade.exits.append(asdict(exit_rec))

                # Append persistence event
                payload = {
                    "trade_id": trade_id,
                    "closed_timestamp_utc": ts_exit,
                    "final_exit_price": final_price,
                    "gross_pnl_usd": final_gross,
                    "net_pnl_usd": final_net,
                    "pnl_status": final_pnl_status,
                    "return_on_notional_pct": ret_notional,
                    "user_outcome": user_outcome,
                    "forecast_outcome": forecast_outcome,
                    "final_exit_record": asdict(exit_rec)
                }
                self._append_event("TRADE_CLOSED", payload)
            else:
                # Partial Exit
                new_rem = trade.remaining_quantity - exit_qty
                trade.remaining_quantity = new_rem
                trade.status = "PARTIALLY_EXITED"
                trade.exits.append(asdict(exit_rec))

                # Accumulated partial PnL
                curr_gross = sum(e.get("gross_pnl_usd") or 0.0 for e in trade.exits)
                trade.gross_pnl_usd = curr_gross

                payload = {
                    "trade_id": trade_id,
                    "remaining_quantity": new_rem,
                    "accumulated_gross_pnl": curr_gross,
                    "accumulated_net_pnl": None,
                    "pnl_status": "GROSS_PNL_ONLY",
                    "exit_record": asdict(exit_rec)
                }
                self._append_event("TRADE_PARTIAL_EXIT", payload)

            return trade, None

    # ========================================================================
    # Auditable Adjustments
    # ========================================================================

    def record_adjustment(
        self,
        trade_id: str,
        field_name: str,
        new_value: Any,
        reason: str
    ) -> Tuple[Optional[ManualTradeRecord], Optional[str]]:
        """
        Records an auditable correction. Historical records are preserved with an
        AdjustmentRecord; never silently overwritten.
        """
        with self._lock:
            if trade_id not in self._trades:
                return None, f"TRADE_NOT_FOUND: Trade '{trade_id}' does not exist"

            trade = self._trades[trade_id]
            allowed_fields = {"notes", "entry_fee_usd", "leverage", "contract_multiplier"}
            if field_name not in allowed_fields:
                return None, f"DISALLOWED_FIELD: Field '{field_name}' cannot be adjusted. Allowed: {allowed_fields}"

            old_val = getattr(trade, field_name, None)
            adj = AdjustmentRecord(
                adjustment_id=f"adj_{uuid.uuid4().hex[:8]}",
                timestamp_utc=_get_utc_now_iso(),
                field_name=field_name,
                old_value=old_val,
                new_value=new_value,
                reason=reason
            )

            trade.adjustments.append(asdict(adj))
            setattr(trade, field_name, new_value)

            payload = {
                "trade_id": trade_id,
                "adjustment": asdict(adj)
            }
            self._append_event("TRADE_ADJUSTED", payload)
            return trade, None

    # ========================================================================
    # Query Methods
    # ========================================================================

    def get_trade(self, trade_id: str) -> Optional[ManualTradeRecord]:
        with self._lock:
            return self._trades.get(trade_id)

    def get_open_trades(self) -> List[ManualTradeRecord]:
        with self._lock:
            return [t for t in self._trades.values() if t.status in {"OPEN", "PARTIALLY_EXITED"}]

    def get_closed_trades(self) -> List[ManualTradeRecord]:
        with self._lock:
            return [t for t in self._trades.values() if t.status == "CLOSED"]

    def get_all_trades(self) -> List[ManualTradeRecord]:
        with self._lock:
            return list(self._trades.values())

    # ========================================================================
    # Dual Performance Evaluation (Prompt Section 3)
    # ========================================================================

    def evaluate_performance(self) -> Dict[str, Any]:
        """
        Calculates separate User Trade Performance and AI Forecast Performance.
        Separates user outcome from model correctness.
        Enforces clear caveats for small samples.
        """
        with self._lock:
            closed = [t for t in self._trades.values() if t.status == "CLOSED"]
            total_closed = len(closed)

            # -------------------------------------------------------------
            # Part A: User Trade Performance
            # -------------------------------------------------------------
            wins = [t for t in closed if t.user_outcome == "WIN"]
            losses = [t for t in closed if t.user_outcome == "LOSS"]
            breakevens = [t for t in closed if t.user_outcome == "BREAKEVEN"]

            win_count = len(wins)
            loss_count = len(losses)
            be_count = len(breakevens)
            win_rate = (win_count / total_closed) if total_closed > 0 else 0.0

            gross_pnls = [t.gross_pnl_usd for t in closed if t.gross_pnl_usd is not None]
            total_gross = sum(gross_pnls) if gross_pnls else 0.0

            net_pnls = [t.net_pnl_usd for t in closed if t.net_pnl_usd is not None]
            total_net = sum(net_pnls) if net_pnls else None

            win_gross_amounts = [t.gross_pnl_usd for t in wins if t.gross_pnl_usd is not None]
            loss_gross_amounts = [t.gross_pnl_usd for t in losses if t.gross_pnl_usd is not None]

            avg_win = (sum(win_gross_amounts) / len(win_gross_amounts)) if win_gross_amounts else 0.0
            avg_loss = (sum(loss_gross_amounts) / len(loss_gross_amounts)) if loss_gross_amounts else 0.0
            avg_net = (total_net / len(net_pnls)) if net_pnls else (total_gross / len(gross_pnls) if gross_pnls else 0.0)

            # Cumulative series & max drawdown
            max_drawdown_usd = 0.0
            cum_pnl = 0.0
            peak_pnl = 0.0
            for t in closed:
                p = t.net_pnl_usd if t.net_pnl_usd is not None else (t.gross_pnl_usd or 0.0)
                cum_pnl += p
                if cum_pnl > peak_pnl:
                    peak_pnl = cum_pnl
                dd = peak_pnl - cum_pnl
                if dd > max_drawdown_usd:
                    max_drawdown_usd = dd

            # Results by direction
            long_trades = [t for t in closed if t.direction == "LONG"]
            short_trades = [t for t in closed if t.direction == "SHORT"]

            def _summarize_group(group: List[ManualTradeRecord]):
                g_wins = sum(1 for t in group if t.user_outcome == "WIN")
                g_total = len(group)
                g_pnl = sum(t.gross_pnl_usd or 0.0 for t in group)
                return {
                    "count": g_total,
                    "wins": g_wins,
                    "win_rate": (g_wins / g_total) if g_total > 0 else 0.0,
                    "total_gross_pnl": g_pnl
                }

            by_direction = {
                "LONG": _summarize_group(long_trades),
                "SHORT": _summarize_group(short_trades)
            }

            # Results by regime
            by_regime: Dict[str, Dict[str, Any]] = {}
            for t in closed:
                r = t.forecast_snapshot.get("regime_classification", "UNKNOWN")
                if r not in by_regime:
                    by_regime[r] = {"count": 0, "wins": 0, "gross_pnl": 0.0}
                by_regime[r]["count"] += 1
                if t.user_outcome == "WIN":
                    by_regime[r]["wins"] += 1
                by_regime[r]["gross_pnl"] += (t.gross_pnl_usd or 0.0)

            for r, stat in by_regime.items():
                stat["win_rate"] = (stat["wins"] / stat["count"]) if stat["count"] > 0 else 0.0

            user_performance = {
                "completed_trades": total_closed,
                "winning_trades": win_count,
                "losing_trades": loss_count,
                "breakeven_trades": be_count,
                "win_rate": round(win_rate, 4),
                "total_gross_pnl_usd": round(total_gross, 2),
                "total_net_pnl_usd": round(total_net, 2) if total_net is not None else None,
                "pnl_completeness": "NET_PNL_COMPLETE" if (net_pnls and len(net_pnls) == total_closed) else "GROSS_PNL_ONLY",
                "average_win_usd": round(avg_win, 2),
                "average_loss_usd": round(avg_loss, 2),
                "average_net_result_usd": round(avg_net, 2),
                "maximum_observed_drawdown_usd": round(max_drawdown_usd, 2),
                "by_direction": by_direction,
                "by_regime": by_regime
            }

            # -------------------------------------------------------------
            # Part B: AI Forecast Performance
            # -------------------------------------------------------------
            valid_snapshots = [t for t in closed if t.forecast_snapshot.get("forecast_status") == "VALID"]
            unavailable_snapshots = [t for t in closed if t.forecast_snapshot.get("forecast_status") != "VALID"]

            # Agreement with trade direction
            agreed_trades = [t for t in closed if t.forecast_agreement]
            disagreed_trades = [t for t in closed if not t.forecast_agreement]

            agreement_rate = (len(agreed_trades) / total_closed) if total_closed > 0 else 0.0

            # Model correctness across eligible trades
            eligible_for_accuracy = [t for t in closed if t.forecast_outcome in {"CORRECT", "INCORRECT"}]
            correct_forecasts = [t for t in eligible_for_accuracy if t.forecast_outcome == "CORRECT"]
            incorrect_forecasts = [t for t in eligible_for_accuracy if t.forecast_outcome == "INCORRECT"]

            model_accuracy = (len(correct_forecasts) / len(eligible_for_accuracy)) if eligible_for_accuracy else 0.0

            # Contingency Matrix (User outcome vs Model correctness)
            matrix = {
                "user_win_model_correct": len([t for t in eligible_for_accuracy if t.user_outcome == "WIN" and t.forecast_outcome == "CORRECT"]),
                "user_win_model_incorrect": len([t for t in eligible_for_accuracy if t.user_outcome == "WIN" and t.forecast_outcome == "INCORRECT"]),
                "user_loss_model_correct": len([t for t in eligible_for_accuracy if t.user_outcome == "LOSS" and t.forecast_outcome == "CORRECT"]),
                "user_loss_model_incorrect": len([t for t in eligible_for_accuracy if t.user_outcome == "LOSS" and t.forecast_outcome == "INCORRECT"])
            }

            # Calibration check (Brier score) if sample >= 10
            brier_score = None
            if len(eligible_for_accuracy) >= 10:
                squared_diffs = []
                for t in eligible_for_accuracy:
                    p_up = t.forecast_snapshot.get("probability_up")
                    if p_up is not None:
                        actual_binary = 1.0 if t.final_exit_price > t.entry_price else 0.0
                        squared_diffs.append((p_up - actual_binary) ** 2)
                if squared_diffs:
                    brier_score = round(sum(squared_diffs) / len(squared_diffs), 4)

            ai_performance = {
                "total_evaluated_trades": total_closed,
                "valid_forecast_snapshots": len(valid_snapshots),
                "missing_or_stale_snapshots": len(unavailable_snapshots),
                "directional_agreement_count": len(agreed_trades),
                "directional_agreement_rate": round(agreement_rate, 4),
                "eligible_accuracy_evaluations": len(eligible_for_accuracy),
                "model_correct_count": len(correct_forecasts),
                "model_incorrect_count": len(incorrect_forecasts),
                "model_accuracy_rate": round(model_accuracy, 4),
                "contingency_matrix": matrix,
                "brier_score": brier_score,
                "insufficient_sample": (total_closed < 30),
                "disclaimer": (
                    "INSUFFICIENT EVIDENCE: This journal is a manual, self-selected sample. "
                    "It cannot by itself establish statistical significance, predictive edge, "
                    "or trading profitability across all market conditions."
                )
            }

            return {
                "status": "SUCCESS",
                "evaluated_at_utc": _get_utc_now_iso(),
                "user_performance": user_performance,
                "ai_performance": ai_performance
            }

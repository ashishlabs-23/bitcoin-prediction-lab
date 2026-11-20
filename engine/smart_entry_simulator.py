"""
engine/smart_entry_simulator.py — Smart Entry Simulator with Locked TP/SL
========================================================================
BTCognitive V32.43: Lifecycle simulator for Smart Entry attempts.

Key Invariants:
1. Entry on Explicit Action Only:
   - Simulated trades are created ONLY when the user clicks "Enter (Simulated)".
   - Analysis and tournament backtests NEVER create an active attempt.
2. Immutable TP/SL and Anomaly Policy:
   - On entry, absolute TP and SL levels, anomaly rules, max duration, and entry
     forecast snapshot are permanently locked.
   - Subsequent AI forecast updates or regime shifts NEVER move or rewrite TP/SL.
3. Live Forecast & Direction-Change Alerts:
   - AI forecasts continue updating live. If a reversal is detected, an explainable
     DIRECTION_CHANGE_ALERT is emitted without modifying the active trade rules.
   - User can choose Exit Now or Partial Exit.
4. Outcome Evaluation Without Monetary P&L:
   - Classifies attempts into:
     SUCCESS_TP_HIT, FAILURE_SL_HIT, EXITED_ANOMALY, USER_EXITED_EARLY,
     TIMEOUT_NO_TP, UNRESOLVED_INTRABAR_ORDER.
   - Partial exit is recorded as a lifecycle event, not an automatic success.
   - Primary metric: TP-First Hit Rate = Attempts reaching TP first / Eligible entered attempts.
   - Never calculates or displays dollar P&L.
5. Durable Append-Only Persistence:
   - Stored in data/smart_entry/smart_entry_attempts.jsonl.
   - Fully recoverable across restarts.
"""

from __future__ import annotations

import os
import sys
import json
import time
import hashlib
import math
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field, fields
from datetime import datetime, timezone

from engine.regime_strategy_tournament import compute_wilson_ci


LEDGER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "smart_entry"))
LEDGER_FILE = os.path.join(LEDGER_DIR, "smart_entry_attempts.jsonl")


@dataclass
class SimulatedTradeAttempt:
    attempt_id: str
    tournament_id: str
    strategy_id: str
    strategy_name: str
    strategy_version: str
    direction: str  # "LONG"
    market_regime: str
    entered_at_utc: str
    reference_entry_price: float
    frozen_tp_price: float
    frozen_sl_price: float
    reward_usd: float
    risk_usd: float
    reward_risk_ratio: float
    max_duration_hours: float
    timeout_at_utc: str
    anomaly_policy: str
    entry_forecast_snapshot: Dict[str, Any]
    immutable_sha256: str
    status: str  # "ACTIVE", "SUCCESS_TP_HIT", "FAILURE_SL_HIT", "EXITED_ANOMALY", "USER_EXITED_EARLY", "TIMEOUT_NO_TP", "UNRESOLVED_INTRABAR_ORDER"
    idempotency_key: Optional[str] = None
    remaining_ratio: float = 1.0  # 1.0 full, 0.5 after partial exit
    closed_at_utc: Optional[str] = None
    final_exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    candle_watermark: Dict[str, Any] = field(default_factory=dict)
    last_monitored_at_utc: Optional[str] = None
    last_forecast_timestamp_utc: Optional[str] = None
    current_forecast_snapshot: Dict[str, Any] = field(default_factory=dict)
    data_quality_state: str = "NORMAL"
    direction_change_alert: bool = False
    direction_change_rationale: Optional[str] = None
    risk_spike_alert: bool = False
    risk_spike_rationale: Optional[str] = None
    anomaly_events: List[Dict[str, Any]] = field(default_factory=list)
    monitoring_alerts: List[Dict[str, Any]] = field(default_factory=list)
    partial_exits: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SmartEntrySimulator:
    """Manages active simulated attempts, lifecycle transitions, and outcome evaluation."""

    def __init__(self, ledger_file: Optional[str] = None):
        self.ledger_file = ledger_file or LEDGER_FILE
        self.attempts: Dict[str, SimulatedTradeAttempt] = {}
        self._state_lock = threading.RLock()
        os.makedirs(os.path.dirname(self.ledger_file), exist_ok=True)
        self._load_ledger()

    def _load_ledger(self):
        """Reconstructs state from append-only JSONL ledger."""
        if not os.path.exists(self.ledger_file):
            return
        valid_field_names = {f.name for f in fields(SimulatedTradeAttempt)}
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                    event_type = payload.get("event_type")
                    data = payload.get("data", {})
                    att_id = data.get("attempt_id")
                    if not att_id:
                        continue

                    if event_type == "ATTEMPT_ENTERED":
                        filtered = {k: v for k, v in data.items() if k in valid_field_names}
                        self.attempts[att_id] = SimulatedTradeAttempt(**filtered)
                    elif att_id in self.attempts:
                        att = self.attempts[att_id]
                        if event_type == "PARTIAL_EXIT":
                            att.remaining_ratio = data.get("remaining_ratio", 0.5)
                            att.partial_exits.append(data)
                            att.events.append(payload)
                        elif event_type in ("TP_HIT", "SL_HIT", "ANOMALY_EXIT", "USER_EXIT", "TIMEOUT", "UNRESOLVED"):
                            att.status = data.get("status", att.status)
                            att.closed_at_utc = data.get("closed_at_utc")
                            att.final_exit_price = data.get("final_exit_price")
                            att.exit_reason = data.get("exit_reason")
                            att.events.append(payload)
                        elif event_type in ("DIRECTION_CHANGE_ALERT", "FORECAST_DIRECTION_FLIP"):
                            att.direction_change_alert = True
                            att.direction_change_rationale = data.get("rationale")
                            att.anomaly_events.append(data)
                            att.events.append(payload)
                        elif event_type in ("RISK_SPIKE_ALERT", "FORECAST_RISK_SPIKE"):
                            att.risk_spike_alert = True
                            att.risk_spike_rationale = data.get("rationale")
                            att.anomaly_events.append(data)
                            att.events.append(payload)
                        elif event_type == "DATA_FEED_DEGRADED":
                            att.data_quality_state = data.get("data_quality_state", "DEGRADED")
                            att.anomaly_events.append(data)
                            att.events.append(payload)
                        elif event_type == "DATA_FEED_RECOVERED":
                            att.data_quality_state = "NORMAL"
                            att.events.append(payload)
                        elif event_type == "MONITORING_TICK":
                            att.last_monitored_at_utc = data.get("timestamp_utc")
                            att.events.append(payload)
                        elif event_type == "FORECAST_SNAPSHOT":
                            att.last_forecast_timestamp_utc = data.get("timestamp_utc")
                            att.current_forecast_snapshot = data.get("forecast", {})
                            att.events.append(payload)
                        elif event_type == "USER_CONTINUED":
                            att.events.append(payload)
                except Exception as e:
                    print(f"[SmartEntrySimulator] Error replaying ledger line: {e}")

    def _append_event(self, event_type: str, data: Dict[str, Any]):
        """Atomically appends event to ledger."""
        record = {
            "event_type": event_type,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def enter_simulated_trade(
        self,
        decision_payload: Dict[str, Any],
        entry_price: Optional[float] = None,
        idempotency_key: Optional[str] = None
    ) -> Tuple[Optional[SimulatedTradeAttempt], Optional[str]]:
        with self._state_lock:
            return self._enter_simulated_trade(decision_payload, entry_price, idempotency_key)

    def _enter_simulated_trade(
        self,
        decision_payload: Dict[str, Any],
        entry_price: Optional[float],
        idempotency_key: Optional[str]
    ) -> Tuple[Optional[SimulatedTradeAttempt], Optional[str]]:
        """
        Step 3 of lifecycle: User clicks "Enter (Simulated)".
        Freezes entry price, absolute TP/SL levels, anomaly rules, and entry forecast snapshot.
        Enforces idempotency and duplicate prevention:
        - If an ACTIVE attempt already exists for this strategy and tournament, returns existing attempt.
        - Rejects entry if decision status is not SMART_ENTRY_AVAILABLE.
        """
        if not decision_payload:
            return None, "Empty decision payload"
        if decision_payload.get("status") in ("NO_SMART_ENTRY", "ABSTAIN", "REJECTED"):
            return None, "Cannot enter trade: decision status is not SMART_ENTRY_AVAILABLE"

        candidate = decision_payload.get("candidate_setup")
        if not candidate:
            return None, "No candidate setup present in decision payload"

        strategy_id = candidate.get("strategy_id")
        tournament_id = candidate.get("tournament_id") or decision_payload.get("tournament_id", "trn_manual")
        decision_id = decision_payload.get("decision_id", "")

        # Duplicate Prevention / Idempotency Check:
        # If an active attempt already exists with the same strategy and tournament ID (non-manual)
        # or matching explicit idempotency key or decision_id, return existing attempt idempotently.
        for existing_att in self.attempts.values():
            if existing_att.status == "ACTIVE":
                if idempotency_key and existing_att.idempotency_key == idempotency_key:
                    return existing_att, None
                if decision_id and existing_att.tournament_id == decision_id:
                    return existing_att, None
                if tournament_id != "trn_manual" and existing_att.strategy_id == strategy_id and existing_att.tournament_id == tournament_id:
                    return existing_att, None

        try:
            p_entry = float(entry_price if entry_price is not None else candidate.get("entry_reference_price"))
            tp = float(candidate.get("proposed_tp_price"))
            sl = float(candidate.get("proposed_sl_price"))
        except (TypeError, ValueError):
            return None, "Invalid TP/SL geometry: entry, target, and stop must be finite numbers"
        if not all(math.isfinite(value) and value > 0 for value in (p_entry, tp, sl)):
            return None, "Invalid TP/SL geometry: entry, target, and stop must be positive finite numbers"
        direction = str(candidate.get("direction", "LONG")).upper()
        if direction == "LONG":
            geometry_valid = sl < p_entry < tp
            reward, risk = tp - p_entry, p_entry - sl
        elif direction == "SHORT":
            geometry_valid = tp < p_entry < sl
            reward, risk = p_entry - tp, sl - p_entry
        else:
            return None, f"Unsupported simulated direction: {direction}"
        if not geometry_valid:
            return None, f"Invalid TP/SL geometry for {direction}: Entry={p_entry}, TP={tp}, SL={sl}"

        now_ts = datetime.now(timezone.utc).isoformat()
        max_hours = float(candidate.get("max_duration_hours", 24.0))
        timeout_ts = datetime.fromtimestamp(
            time.time() + max_hours * 3600, tz=timezone.utc
        ).isoformat()

        # Idempotent attempt ID calculation
        key_seed = idempotency_key or decision_id or (f"{strategy_id}:{tournament_id}" if tournament_id != "trn_manual" else f"{strategy_id}:{now_ts}")
        raw_id_str = f"{strategy_id}:{p_entry}:{tp}:{sl}:{key_seed}"
        att_id = f"att_{hashlib.sha256(raw_id_str.encode()).hexdigest()[:12]}"

        if att_id in self.attempts and self.attempts[att_id].status == "ACTIVE":
            return self.attempts[att_id], None

        # Seal entry forecast snapshot with SHA-256
        forecast = candidate.get("latest_ai_forecast")
        forecast_snap = dict(forecast) if isinstance(forecast, dict) else {}
        forecast_snap["captured_at_utc"] = now_ts
        snap_sha = hashlib.sha256(json.dumps(forecast_snap, sort_keys=True).encode()).hexdigest()

        # Capture immutable candle watermark
        candle_wm = candidate.get("candle_watermark") or decision_payload.get("candle_watermark") or {}
        if not candle_wm and "candle_watermark_hash" in candidate:
            candle_wm = {"candle_watermark_hash": candidate["candle_watermark_hash"]}

        reward = round(reward, 2)
        risk = round(risk, 2)
        rr = round(reward / risk, 2) if risk > 0 else 1.5

        attempt = SimulatedTradeAttempt(
            attempt_id=att_id,
            tournament_id=tournament_id,
            strategy_id=strategy_id,
            strategy_name=candidate.get("strategy_name", strategy_id),
            strategy_version=candidate.get("version", "1.0.0"),
            direction=direction,
            market_regime=candidate.get("market_regime", "UNKNOWN"),
            entered_at_utc=now_ts,
            reference_entry_price=round(p_entry, 2),
            frozen_tp_price=round(tp, 2),
            frozen_sl_price=round(sl, 2),
            reward_usd=reward,
            risk_usd=risk,
            reward_risk_ratio=rr,
            max_duration_hours=max_hours,
            timeout_at_utc=timeout_ts,
            anomaly_policy=candidate.get("anomaly_policy", "Standard anomaly rules"),
            entry_forecast_snapshot=forecast_snap,
            immutable_sha256=snap_sha,
            idempotency_key=idempotency_key,
            candle_watermark=candle_wm,
            last_monitored_at_utc=now_ts,
            last_forecast_timestamp_utc=forecast_snap.get("timestamp_utc"),
            current_forecast_snapshot=forecast_snap,
            data_quality_state="NORMAL",
            status="ACTIVE",
            remaining_ratio=1.0,
            events=[{"event": "ATTEMPT_ENTERED", "timestamp": now_ts}]
        )

        self.attempts[att_id] = attempt
        self._append_event("ATTEMPT_ENTERED", attempt.to_dict())
        return attempt, None

    def trigger_anomaly_exit(
        self,
        attempt_id: str,
        exit_price: float,
        reason: Optional[str] = None
    ) -> Tuple[Optional[SimulatedTradeAttempt], Optional[str]]:
        """Transitions active attempt to EXITED_ANOMALY when qualifying anomaly condition triggers."""
        if attempt_id not in self.attempts:
            return None, f"Attempt {attempt_id} not found"
        att = self.attempts[attempt_id]
        if att.status != "ACTIVE":
            return None, f"Attempt {attempt_id} is already closed ({att.status})"

        now_ts = datetime.now(timezone.utc).isoformat()
        att.status = "EXITED_ANOMALY"
        att.closed_at_utc = now_ts
        att.final_exit_price = float(exit_price)
        att.exit_reason = reason or f"Qualifying anomaly condition triggered: {att.anomaly_policy}"

        data = {
            "attempt_id": attempt_id,
            "status": att.status,
            "closed_at_utc": now_ts,
            "final_exit_price": att.final_exit_price,
            "exit_reason": att.exit_reason
        }
        self._append_event("ANOMALY_EXIT", data)
        return att, None

    def monitor_active_attempt(
        self,
        attempt_id: str,
        current_price: Optional[float] = None,
        current_forecast: Optional[Dict[str, Any]] = None,
        data_quality_info: Optional[Dict[str, Any]] = None,
        candle: Optional[Dict[str, Any]] = None,
        hard_anomaly_trigger: bool = False,
        hard_anomaly_reason: Optional[str] = None
    ) -> Tuple[Optional[SimulatedTradeAttempt], List[Dict[str, Any]]]:
        """
        Continuously monitors an active simulated attempt against live updates:
        1. Compares current forecast & data quality to immutable entry snapshot.
        2. Detects direction flip or risk spike past 1.5x entry baseline and triggers alerts.
        3. Enforces that forecast updates NEVER move or rewrite frozen TP/SL.
        4. Rejects silent failure on stale/malformed data.
        5. Conservative first-touch resolution (dual-touch = UNRESOLVED_INTRABAR_ORDER).
        """
        if attempt_id not in self.attempts:
            return None, []
        att = self.attempts[attempt_id]
        if att.status != "ACTIVE":
            return att, []

        now_ts = datetime.now(timezone.utc).isoformat()
        last_tick = next(
            (event for event in reversed(att.events) if event.get("event_type") == "MONITORING_TICK"),
            None,
        )
        last_tick_timestamp = (
            (last_tick.get("data") or {}).get("timestamp_utc")
            or last_tick.get("timestamp_utc")
            if last_tick else None
        )
        if not last_tick_timestamp or last_tick_timestamp[:16] != now_ts[:16]:
            tick_data = {"attempt_id": attempt_id, "timestamp_utc": now_ts}
            tick_event = {
                "event_type": "MONITORING_TICK",
                "timestamp_utc": now_ts,
                "data": tick_data,
            }
            self._append_event("MONITORING_TICK", tick_data)
            att.events.append(tick_event)
        att.last_monitored_at_utc = now_ts
        new_events = []

        # 0. Data Quality State Evaluation
        dq = data_quality_info or {}
        try:
            price_age_seconds = float(dq.get("price_feed_age_seconds", 0) or 0)
            forecast_age_seconds = float(dq.get("forecast_age_seconds", 0) or 0)
        except (TypeError, ValueError):
            price_age_seconds = forecast_age_seconds = float("inf")
        is_stale_data = bool(dq.get("is_stale") or dq.get("price_stale") or dq.get("stale_market_data") or price_age_seconds > 300)
        is_stale_fc = bool(dq.get("forecast_stale") or dq.get("model_unavailable") or forecast_age_seconds > 3600)
        is_malformed = bool(dq.get("malformed_forecast") or dq.get("is_malformed"))
        forecast_unavailable = current_forecast is None or bool(dq.get("model_unavailable"))
        if current_forecast is not None and not isinstance(current_forecast, dict):
            is_malformed = True
        elif isinstance(current_forecast, dict):
            # If forecast dict is non-empty but has no recognized direction or volatility fields
            if not any(k in current_forecast for k in ("direction", "forecast_direction", "probability_up", "probability_down")):
                is_malformed = True
            for probability_key in ("probability_up", "probability_down"):
                probability = current_forecast.get(probability_key)
                if probability is not None:
                    try:
                        probability = float(probability)
                    except (TypeError, ValueError):
                        is_malformed = True
                        continue
                    if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
                        is_malformed = True
            for risk_key in ("realized_volatility_annualized_pct", "volatility", "forecast_risk", "variance"):
                risk_value = current_forecast.get(risk_key)
                if risk_value is not None:
                    try:
                        risk_value = float(risk_value)
                    except (TypeError, ValueError):
                        is_malformed = True
                        continue
                    if not math.isfinite(risk_value) or risk_value < 0.0:
                        is_malformed = True
        entry_snapshot = att.entry_forecast_snapshot or {}
        for risk_key in ("realized_volatility_annualized_pct", "volatility", "forecast_risk", "variance"):
            risk_value = entry_snapshot.get(risk_key)
            if risk_value is not None:
                try:
                    risk_value = float(risk_value)
                except (TypeError, ValueError):
                    is_malformed = True
                    continue
                if not math.isfinite(risk_value) or risk_value < 0.0:
                    is_malformed = True

        if isinstance(current_forecast, dict) and current_forecast.get("timestamp_utc") is not None:
            try:
                incoming_timestamp = datetime.fromisoformat(
                    str(current_forecast["timestamp_utc"]).replace("Z", "+00:00")
                )
                if incoming_timestamp.tzinfo is None:
                    raise ValueError("Forecast timestamp must include a timezone")
                incoming_timestamp = incoming_timestamp.astimezone(timezone.utc)
                previous_timestamp = None
                if att.last_forecast_timestamp_utc:
                    previous_timestamp = datetime.fromisoformat(
                        att.last_forecast_timestamp_utc.replace("Z", "+00:00")
                    ).astimezone(timezone.utc)
                if previous_timestamp and incoming_timestamp <= previous_timestamp:
                    current_forecast = att.current_forecast_snapshot or None
                    is_stale_fc = (datetime.now(timezone.utc) - previous_timestamp).total_seconds() > 3600
                else:
                    att.last_forecast_timestamp_utc = incoming_timestamp.isoformat()
                    att.current_forecast_snapshot = dict(current_forecast)
                    snapshot_event = {
                        "attempt_id": attempt_id,
                        "timestamp_utc": incoming_timestamp.isoformat(),
                        "forecast": att.current_forecast_snapshot,
                    }
                    self._append_event("FORECAST_SNAPSHOT", snapshot_event)
                    att.events.append({
                        "event_type": "FORECAST_SNAPSHOT",
                        "timestamp_utc": now_ts,
                        "data": snapshot_event,
                    })
            except (TypeError, ValueError, OverflowError):
                is_malformed = True

        forecast_unavailable = current_forecast is None or bool(dq.get("model_unavailable"))
        has_gaps = bool(dq.get("missing_candles") or dq.get("candle_gaps"))

        if is_malformed:
            dq_state = "DEGRADED_MALFORMED_FORECAST"
        elif is_stale_fc:
            dq_state = "DEGRADED_STALE_FORECAST"
        elif current_price is None:
            dq_state = "DEGRADED_PRICE_UNAVAILABLE"
        elif is_stale_data:
            dq_state = "DEGRADED_STALE_PRICE_FEED"
        elif forecast_unavailable:
            dq_state = "DEGRADED_FORECAST_UNAVAILABLE"
        elif has_gaps:
            dq_state = "DEGRADED_CANDLE_GAPS"
        else:
            dq_state = "NORMAL"

        if dq_state != att.data_quality_state:
            att.data_quality_state = dq_state
            if dq_state != "NORMAL":
                dq_event = {
                    "attempt_id": attempt_id,
                    "event_type": "DATA_FEED_DEGRADED",
                    "timestamp_utc": now_ts,
                    "data_quality_state": dq_state,
                    "rationale": dq.get("reason") or f"Data feed entered {dq_state} state."
                }
                att.anomaly_events.append(dq_event)
                self._append_event("DATA_FEED_DEGRADED", dq_event)
                new_events.append(dq_event)
            else:
                recovery_event = {
                    "attempt_id": attempt_id,
                    "event_type": "DATA_FEED_RECOVERED",
                    "timestamp_utc": now_ts,
                    "data_quality_state": "NORMAL",
                    "rationale": "Market price and forecast data returned within the monitoring quality policy.",
                }
                self._append_event("DATA_FEED_RECOVERED", recovery_event)
                att.events.append({
                    "event_type": "DATA_FEED_RECOVERED",
                    "timestamp_utc": now_ts,
                    "data": recovery_event,
                })
                new_events.append(recovery_event)

        # 1. Forecast Direction Flip Check (Advisory Alert — TP/SL never move!)
        if current_forecast and not is_malformed and not is_stale_fc:
            new_dir = str(current_forecast.get("forecast_direction") or current_forecast.get("direction") or "").upper()
            expected_forecast_direction = "UP" if att.direction == "LONG" else "DOWN"
            if new_dir in ("UP", "DOWN") and new_dir != expected_forecast_direction:
                if not att.direction_change_alert:
                    att.direction_change_alert = True
                    prob = current_forecast.get("probability_up") if new_dir == "UP" else current_forecast.get("probability_down", 0.65)
                    prob_val = float(prob) if prob is not None else None
                    rationale = (
                        f"AI Forecast reversed from {att.direction} to {new_dir} "
                        f"({f'P({new_dir}) = {prob_val*100:.1f}%' if prob_val is not None else 'probability unavailable'}). "
                        "Original TP and SL remain locked. Operator decision required: Continue, Partial Exit, or Exit Now."
                    )
                    att.direction_change_rationale = rationale
                    flip_event = {
                        "attempt_id": attempt_id,
                        "event_type": "FORECAST_DIRECTION_FLIP",
                        "timestamp_utc": now_ts,
                        "entry_direction": att.direction,
                        "current_direction": new_dir,
                        "rationale": rationale
                    }
                    att.anomaly_events.append(flip_event)
                    self._append_event("DIRECTION_CHANGE_ALERT", flip_event)
                    att.monitoring_alerts.append({
                        "alert_id": f"alt_dir_{int(time.time()*1000)}",
                        "type": "FORECAST_DIRECTION_FLIP",
                        "severity": "WARNING",
                        "message": rationale,
                        "options": ["CONTINUE", "PARTIAL_EXIT", "EXIT_NOW"],
                        "timestamp_utc": now_ts
                    })
                    new_events.append(flip_event)

        # 2. Forecast Risk / Volatility Spike Check (1.5x entry baseline hurdle)
        if current_forecast and not is_malformed and not is_stale_fc:
            entry_snap = att.entry_forecast_snapshot or {}
            risk_fields = ("realized_volatility_annualized_pct", "volatility", "forecast_risk", "variance")
            entry_risk_val = next((entry_snap[key] for key in risk_fields if entry_snap.get(key) is not None), None)
            current_risk_val = next((current_forecast[key] for key in risk_fields if current_forecast.get(key) is not None), None)
            if entry_risk_val is not None and current_risk_val is not None:
                try:
                    entry_risk = float(entry_risk_val)
                    curr_risk = float(current_risk_val)
                except (TypeError, ValueError):
                    entry_risk = float("nan")
                    curr_risk = float("nan")
                if not math.isfinite(entry_risk) or not math.isfinite(curr_risk) or entry_risk < 0.0 or curr_risk < 0.0:
                    dq_state = "DEGRADED_MALFORMED_FORECAST"
                    att.data_quality_state = dq_state
                    continue_risk_check = False
                else:
                    continue_risk_check = True
                threshold = round(entry_risk * 1.5, 4)
                if continue_risk_check and curr_risk >= threshold:
                    if not att.risk_spike_alert:
                        att.risk_spike_alert = True
                        spike_rationale = (
                            f"Forecast risk spiked to {curr_risk:.4f} >= threshold {threshold:.4f} "
                            f"(Entry Baseline: {entry_risk:.4f}, 1.5x hurdle). "
                            "Original TP/SL remain locked. Operator decision required."
                        )
                        att.risk_spike_rationale = spike_rationale
                        spike_event = {
                            "attempt_id": attempt_id,
                            "event_type": "FORECAST_RISK_SPIKE",
                            "timestamp_utc": now_ts,
                            "entry_risk": entry_risk,
                            "current_risk": curr_risk,
                            "threshold": threshold,
                            "rationale": spike_rationale
                        }
                        att.anomaly_events.append(spike_event)
                        self._append_event("RISK_SPIKE_ALERT", spike_event)
                        att.monitoring_alerts.append({
                            "alert_id": f"alt_risk_{int(time.time()*1000)}",
                            "type": "FORECAST_RISK_SPIKE",
                            "severity": "WARNING",
                            "message": spike_rationale,
                            "options": ["CONTINUE", "PARTIAL_EXIT", "EXIT_NOW"],
                            "timestamp_utc": now_ts
                        })
                        new_events.append(spike_event)

        # 3. Deterministic Hard-Risk Forced Exit (Authorized by Pre-Frozen Policy Only)
        if hard_anomaly_trigger:
            att.status = "EXITED_ANOMALY"
            att.closed_at_utc = now_ts
            att.final_exit_price = float(current_price or att.reference_entry_price)
            att.exit_reason = hard_anomaly_reason or f"Deterministic hard-risk policy executed: {att.anomaly_policy}"
            event_data = {
                "attempt_id": attempt_id,
                "status": att.status,
                "closed_at_utc": now_ts,
                "final_exit_price": att.final_exit_price,
                "exit_reason": att.exit_reason
            }
            self._append_event("ANOMALY_EXIT", event_data)
            new_events.append(event_data)
            return att, new_events

        # 4. Conservative Price & Candle Outcome Resolution
        if candle:
            high = float(candle.get("high", 0.0))
            low = float(candle.get("low", 0.0))
            close = float(candle.get("close", 0.0))
            candle_ts = candle.get("timestamp_utc") or now_ts

            # Simultaneous TP & SL touched within single bar -> UNRESOLVED_INTRABAR_ORDER
            if high >= att.frozen_tp_price and low <= att.frozen_sl_price:
                att.status = "UNRESOLVED_INTRABAR_ORDER"
                att.closed_at_utc = candle_ts
                att.final_exit_price = close
                att.exit_reason = "Simultaneous TP and SL touch within single bar; intrabar order unresolved without tick feed."
                event_data = {
                    "attempt_id": attempt_id,
                    "status": att.status,
                    "closed_at_utc": candle_ts,
                    "final_exit_price": close,
                    "exit_reason": att.exit_reason
                }
                self._append_event("UNRESOLVED", event_data)
                new_events.append(event_data)
                return att, new_events

            # TP hit (first touch known)
            if high >= att.frozen_tp_price:
                att.status = "SUCCESS_TP_HIT"
                att.closed_at_utc = candle_ts
                att.final_exit_price = att.frozen_tp_price
                att.exit_reason = f"Profit target hit at locked level ${att.frozen_tp_price:.2f}"
                event_data = {
                    "attempt_id": attempt_id,
                    "status": att.status,
                    "closed_at_utc": candle_ts,
                    "final_exit_price": att.frozen_tp_price,
                    "exit_reason": att.exit_reason
                }
                self._append_event("TP_HIT", event_data)
                new_events.append(event_data)
                return att, new_events

            # SL hit (first touch known)
            if low <= att.frozen_sl_price:
                att.status = "FAILURE_SL_HIT"
                att.closed_at_utc = candle_ts
                att.final_exit_price = att.frozen_sl_price
                att.exit_reason = f"Stop loss hit at locked level ${att.frozen_sl_price:.2f}"
                event_data = {
                    "attempt_id": attempt_id,
                    "status": att.status,
                    "closed_at_utc": candle_ts,
                    "final_exit_price": att.frozen_sl_price,
                    "exit_reason": att.exit_reason
                }
                self._append_event("SL_HIT", event_data)
                new_events.append(event_data)
                return att, new_events

        elif current_price is not None:
            c_p = float(current_price)
            if c_p >= att.frozen_tp_price:
                att.status = "SUCCESS_TP_HIT"
                att.closed_at_utc = now_ts
                att.final_exit_price = att.frozen_tp_price
                att.exit_reason = f"Profit target hit at locked level ${att.frozen_tp_price:.2f}"
                event_data = {
                    "attempt_id": attempt_id,
                    "status": att.status,
                    "closed_at_utc": now_ts,
                    "final_exit_price": att.frozen_tp_price,
                    "exit_reason": att.exit_reason
                }
                self._append_event("TP_HIT", event_data)
                new_events.append(event_data)
                return att, new_events
            elif c_p <= att.frozen_sl_price:
                att.status = "FAILURE_SL_HIT"
                att.closed_at_utc = now_ts
                att.final_exit_price = att.frozen_sl_price
                att.exit_reason = f"Stop loss hit at locked level ${att.frozen_sl_price:.2f}"
                event_data = {
                    "attempt_id": attempt_id,
                    "status": att.status,
                    "closed_at_utc": now_ts,
                    "final_exit_price": att.frozen_sl_price,
                    "exit_reason": att.exit_reason
                }
                self._append_event("SL_HIT", event_data)
                new_events.append(event_data)
                return att, new_events

        # 5. Holding Duration Timeout Check
        try:
            enter_dt = datetime.fromisoformat(att.entered_at_utc.replace("Z", "+00:00"))
            curr_dt = datetime.fromisoformat(now_ts.replace("Z", "+00:00"))
            elapsed_hrs = (curr_dt - enter_dt).total_seconds() / 3600.0
            if elapsed_hrs >= att.max_duration_hours:
                att.status = "TIMEOUT_NO_TP"
                att.closed_at_utc = now_ts
                att.final_exit_price = float(current_price or att.reference_entry_price)
                att.exit_reason = f"Maximum holding duration ({att.max_duration_hours}h) reached without target."
                event_data = {
                    "attempt_id": attempt_id,
                    "status": att.status,
                    "closed_at_utc": now_ts,
                    "final_exit_price": att.final_exit_price,
                    "exit_reason": att.exit_reason
                }
                self._append_event("TIMEOUT", event_data)
                new_events.append(event_data)
                return att, new_events
        except Exception:
            pass

        return att, new_events

    def update_active_attempts(
        self,
        candle: Dict[str, Any],
        latest_forecast: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluates active attempts against incoming market candle or forecast.
        Delegates to monitor_active_attempt for consistent invariant enforcement.
        """
        updated_events = []
        c_price = float(candle.get("close", 0.0))
        hard_anom = bool(candle.get("anomaly_triggered") or candle.get("is_anomaly") or candle.get("trigger_anomaly"))
        anom_reason = candle.get("anomaly_reason")

        for att_id, att in list(self.attempts.items()):
            if att.status != "ACTIVE":
                continue
            _, evts = self.monitor_active_attempt(
                attempt_id=att_id,
                current_price=c_price,
                current_forecast=latest_forecast,
                candle=candle,
                hard_anomaly_trigger=hard_anom,
                hard_anomaly_reason=anom_reason
            )
            updated_events.extend(evts)

        return updated_events

    def user_exit_now(
        self,
        attempt_id: str,
        exit_price: float,
        reason: Optional[str] = None
    ) -> Tuple[Optional[SimulatedTradeAttempt], Optional[str]]:
        """Operator explicitly chooses to exit early."""
        if attempt_id not in self.attempts:
            return None, f"Attempt {attempt_id} not found"
        att = self.attempts[attempt_id]
        if att.status != "ACTIVE":
            return None, f"Attempt {attempt_id} is already closed ({att.status})"

        now_ts = datetime.now(timezone.utc).isoformat()
        att.status = "USER_EXITED_EARLY"
        att.closed_at_utc = now_ts
        att.final_exit_price = float(exit_price)
        att.exit_reason = reason or "Operator chose Exit Now"

        data = {
            "attempt_id": attempt_id,
            "status": att.status,
            "closed_at_utc": now_ts,
            "final_exit_price": att.final_exit_price,
            "exit_reason": att.exit_reason
        }
        self._append_event("USER_EXIT", data)
        return att, None

    def user_continue(self, attempt_id: str, reason: Optional[str] = None) -> Tuple[Optional[SimulatedTradeAttempt], Optional[str]]:
        """Persist the operator's explicit decision to keep monitoring locked levels."""
        if attempt_id not in self.attempts:
            return None, f"Attempt {attempt_id} not found"
        att = self.attempts[attempt_id]
        if att.status != "ACTIVE":
            return None, f"Attempt {attempt_id} is already closed ({att.status})"
        data = {
            "attempt_id": attempt_id,
            "reason": reason or "Operator chose to continue monitoring with locked TP/SL.",
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        }
        event = {
            "event_type": "USER_CONTINUED",
            "timestamp_utc": data["timestamp_utc"],
            "data": data
        }
        att.events.append(event)
        self._append_event("USER_CONTINUED", data)
        return att, None

    def user_partial_exit(
        self,
        attempt_id: str,
        exit_price: float,
        ratio: float = 0.5,
        reason: Optional[str] = None
    ) -> Tuple[Optional[SimulatedTradeAttempt], Optional[str]]:
        """Operator closes a portion (e.g. 50%); remainder continues with locked TP/SL."""
        if attempt_id not in self.attempts:
            return None, f"Attempt {attempt_id} not found"
        att = self.attempts[attempt_id]
        if att.status != "ACTIVE":
            return None, f"Attempt {attempt_id} is not active ({att.status})"
        if ratio <= 0.0 or ratio >= att.remaining_ratio:
            return None, f"Partial exit ratio ({ratio}) must be positive and less than remaining ({att.remaining_ratio})"

        now_ts = datetime.now(timezone.utc).isoformat()
        att.remaining_ratio = round(att.remaining_ratio - ratio, 4)
        pe_event = {
            "attempt_id": attempt_id,
            "timestamp_utc": now_ts,
            "exit_price": float(exit_price),
            "ratio_closed": ratio,
            "remaining_ratio": att.remaining_ratio,
            "reason": reason or "Operator took partial exit"
        }
        att.partial_exits.append(pe_event)
        self._append_event("PARTIAL_EXIT", pe_event)
        return att, None

    def get_active_attempts(self) -> List[SimulatedTradeAttempt]:
        """Returns list of currently active simulated attempts."""
        return [a for a in self.attempts.values() if a.status == "ACTIVE"]

    def get_resolved_attempts(self) -> List[SimulatedTradeAttempt]:
        """Returns list of closed/resolved simulated attempts."""
        return [a for a in self.attempts.values() if a.status != "ACTIVE"]

    def get_all_attempts(self) -> List[SimulatedTradeAttempt]:
        """Returns list of all simulated attempts."""
        return list(self.attempts.values())

    def get_evaluation_summary(self) -> Dict[str, Any]:
        """
        Step 6 of lifecycle: Evaluates overall TP-First Success Rate and outcomes.
        DOES NOT compute or display monetary P&L!
        """
        all_attempts = list(self.attempts.values())
        total_entered = len(all_attempts)

        active = [a for a in all_attempts if a.status == "ACTIVE"]
        resolved = [a for a in all_attempts if a.status != "ACTIVE"]

        tp_hits = [a for a in resolved if a.status == "SUCCESS_TP_HIT"]
        sl_hits = [a for a in resolved if a.status == "FAILURE_SL_HIT"]
        anomalies = [a for a in resolved if a.status == "EXITED_ANOMALY"]
        user_exits = [a for a in resolved if a.status == "USER_EXITED_EARLY"]
        timeouts = [a for a in resolved if a.status == "TIMEOUT_NO_TP"]
        unresolved = [a for a in resolved if a.status == "UNRESOLVED_INTRABAR_ORDER"]

        # Strict Phase B & D Outcome Accounting:
        # Only eligible completed attempts (TP hit, SL hit, Anomaly exit, Timeout) count in numerator and denominator.
        # Pending (ACTIVE), partial exits, user-exited early, and unresolved dual-touch are reported separately.
        eligible_completed = len(tp_hits) + len(sl_hits) + len(anomalies) + len(timeouts)
        tp_rate = len(tp_hits) / eligible_completed if eligible_completed > 0 else 0.0
        wilson_ci = compute_wilson_ci(len(tp_hits), eligible_completed)

        # Count total partial exit events
        total_partial_events = sum(len(a.partial_exits) for a in all_attempts)

        return {
            "summary_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "total_attempts_entered": total_entered,
            "active_attempts": len(active),
            "pending_active_attempts": len(active),
            "resolved_attempts": len(resolved),
            "primary_metric": {
                "metric_name": "TP_FIRST_SUCCESS_RATE",
                "rate": round(tp_rate, 4),
                "numerator_tp_hits": len(tp_hits),
                "denominator_eligible_entered": eligible_completed,
                "denominator_eligible_completed": eligible_completed,
                "wilson_ci_95": wilson_ci
            },
            "outcome_counts": {
                "SUCCESS_TP_HIT": len(tp_hits),
                "FAILURE_SL_HIT": len(sl_hits),
                "EXITED_ANOMALY": len(anomalies),
                "TIMEOUT_NO_TP": len(timeouts),
                "USER_EXITED_EARLY": len(user_exits),
                "UNRESOLVED_INTRABAR_ORDER": len(unresolved)
            },
            "separately_reported_outcomes": {
                "pending_active": len(active),
                "user_exited_early": len(user_exits),
                "unresolved_intrabar_order": len(unresolved),
                "partial_exit_events_total": total_partial_events
            },
            "lifecycle_events": {
                "partial_exit_events_total": total_partial_events
            },
            "sample_size_caveat": (
                "Evaluated strictly on simulated research attempts under locked TP/SL rules. "
                "Only eligible completed attempts count in denominator. "
                "No monetary P&L is displayed. A high hit rate on small samples does not prove a live trading edge."
            )
        }

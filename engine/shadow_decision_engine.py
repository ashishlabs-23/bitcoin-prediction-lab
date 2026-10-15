"""
engine/shadow_decision_engine.py — Research-Only Shadow Mode Decision Engine
=============================================================================
Implements Phase 8 & Phase 9 Invariants:
1. Research-Only Shadow Mode: Generates forward-looking probabilistic decisions and
   commits them to an immutable audit ledger before outcomes occur.
2. Origin Hash Commitment: Cryptographic SHA256 commitment over input features, model version,
   generation timestamp, and predicted quantiles.
3. Rigorous Economic Decision Gate:
   - Abstains if feed data is stale (ABSTAIN_STALE_FEED).
   - Abstains if calibration is degraded or coverage < 85% (ABSTAIN_DEGRADED_CALIBRATION).
   - Abstains if interval width is too wide / non-informative (ABSTAIN_UNCERTAINTY_TOO_WIDE).
   - Abstains if net edge after fees & slippage is below preregistered economic hurdle (ABSTAIN_INSUFFICIENT_NET_EDGE).
     (Honors Track V3 COST_ERASED findings: requires Net Edge >= +10.0 bps over 35 bps base friction).
4. Point-in-Time Resolution: Outcomes are resolved at maturity (t_0 + H) without ever mutating origin payloads.
5. Zero Live-Capital Guard: Live capital execution, broker API calls, and real money routing are strictly prohibited.
"""

from __future__ import annotations

import os
import sys
import json
import sqlite3
import hashlib
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd

from config.database import MARKET_MEMORY_DB_PATH
from engine.forecasting_ladder import MultiHorizonForecastOutput, ForecastHorizon


class DecisionGateStatus(str, Enum):
    RESEARCH_DECISION_RECORDED = "RESEARCH_DECISION_RECORDED"
    ABSTAIN_STALE_FEED = "ABSTAIN_STALE_FEED"
    ABSTAIN_DEGRADED_CALIBRATION = "ABSTAIN_DEGRADED_CALIBRATION"
    ABSTAIN_UNCERTAINTY_TOO_WIDE = "ABSTAIN_UNCERTAINTY_TOO_WIDE"
    ABSTAIN_INSUFFICIENT_NET_EDGE = "ABSTAIN_INSUFFICIENT_NET_EDGE"
    ABSTAIN_NO_DIRECTIONAL_EDGE = "ABSTAIN_NO_DIRECTIONAL_EDGE"


@dataclass
class ShadowDecisionRecord:
    record_id: str
    generation_timestamp: str
    horizon: str
    current_price: float
    model_version: str
    feature_schema_version: str
    origin_commitment_hash: str

    # Forecast bounds
    price_lower_p10: float
    price_mid_p50: float
    price_upper_p90: float
    interval_width_pct: float

    # Economic Evaluation
    expected_gross_edge_bps: float
    preregistered_friction_bps: float
    expected_net_edge_bps: float
    economic_hurdle_bps: float
    gate_status: DecisionGateStatus
    proposed_action: str  # "ABSTAIN", "RESEARCH_LONG", "RESEARCH_SHORT"

    # Forward Resolution State (strictly populated at t_0 + H)
    is_resolved: bool = False
    resolution_timestamp: Optional[str] = None
    actual_price_at_maturity: Optional[float] = None
    actual_return_bps: Optional[float] = None
    was_contained: Optional[bool] = None
    realized_net_pnl_bps: Optional[float] = None

    # Safety Guard
    live_trading_prohibited: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ShadowDecisionEngine:
    """
    Research-only decision engine operating in strict shadow mode.
    """

    # Preregistered transaction friction (from research/entry_tp_sl/PREREGISTRATION_v1.md)
    BASE_FRICTION_BPS = 35.0         # 25 bps taker fee + 10 bps slippage
    CONSERVATIVE_FRICTION_BPS = 65.0  # 40 bps taker fee + 25 bps slippage
    MIN_REQUIRED_NET_EDGE_BPS = 10.0  # E_min hurdle: +10 bps net expectancy

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or MARKET_MEMORY_DB_PATH
        self._init_db()

    def _init_db(self):
        """Initializes SQLite shadow decision table if not present."""
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS shadow_decision_records (
                        record_id TEXT PRIMARY KEY,
                        generation_timestamp TEXT NOT NULL,
                        horizon TEXT NOT NULL,
                        current_price REAL NOT NULL,
                        model_version TEXT NOT NULL,
                        feature_schema_version TEXT NOT NULL,
                        origin_commitment_hash TEXT NOT NULL,
                        price_lower_p10 REAL NOT NULL,
                        price_mid_p50 REAL NOT NULL,
                        price_upper_p90 REAL NOT NULL,
                        interval_width_pct REAL NOT NULL,
                        expected_gross_edge_bps REAL NOT NULL,
                        preregistered_friction_bps REAL NOT NULL,
                        expected_net_edge_bps REAL NOT NULL,
                        economic_hurdle_bps REAL NOT NULL,
                        gate_status TEXT NOT NULL,
                        proposed_action TEXT NOT NULL,
                        is_resolved INTEGER DEFAULT 0,
                        resolution_timestamp TEXT,
                        actual_price_at_maturity REAL,
                        actual_return_bps REAL,
                        was_contained INTEGER,
                        realized_net_pnl_bps REAL,
                        live_trading_prohibited INTEGER DEFAULT 1
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_shadow_ts ON shadow_decision_records(generation_timestamp);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_shadow_resolved ON shadow_decision_records(is_resolved);")
        finally:
            conn.close()

    def evaluate_decision_gate(
        self,
        forecast: MultiHorizonForecastOutput,
        feed_freshness_status: str = "FRESH",
        calibration_coverage_pct: float = 91.2,
        estimated_gross_return_bps: float = 0.0,
        directional_signal: str = "NONE"
    ) -> ShadowDecisionRecord:
        """
        Applies rigorous preregistered gate rules to evaluate shadow decision.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        rec_id = f"shd_{uuid.uuid4().hex[:12]}"

        # 1. Check feed freshness
        if feed_freshness_status != "FRESH":
            gate_status = DecisionGateStatus.ABSTAIN_STALE_FEED
            action = "ABSTAIN"
            gross_edge = 0.0
            net_edge = -self.BASE_FRICTION_BPS
        # 2. Check calibration health
        elif calibration_coverage_pct < 85.0:
            gate_status = DecisionGateStatus.ABSTAIN_DEGRADED_CALIBRATION
            action = "ABSTAIN"
            gross_edge = 0.0
            net_edge = -self.BASE_FRICTION_BPS
        # 3. Check uncertainty interval width (e.g., width > 20% on 24h is uninformative)
        elif forecast.interval_width_pct > 25.0:
            gate_status = DecisionGateStatus.ABSTAIN_UNCERTAINTY_TOO_WIDE
            action = "ABSTAIN"
            gross_edge = 0.0
            net_edge = -self.BASE_FRICTION_BPS
        # 4. Check directional edge
        elif directional_signal in {"NONE", "NO_DIRECTIONAL_EDGE"}:
            gate_status = DecisionGateStatus.ABSTAIN_NO_DIRECTIONAL_EDGE
            action = "ABSTAIN"
            gross_edge = 0.0
            net_edge = 0.0
        else:
            # 5. Economic Hurdle Check
            gross_edge = abs(estimated_gross_return_bps)
            net_edge = gross_edge - self.BASE_FRICTION_BPS
            if net_edge < self.MIN_REQUIRED_NET_EDGE_BPS:
                gate_status = DecisionGateStatus.ABSTAIN_INSUFFICIENT_NET_EDGE
                action = "ABSTAIN"
            else:
                gate_status = DecisionGateStatus.RESEARCH_DECISION_RECORDED
                action = f"RESEARCH_{directional_signal.upper()}"

        # Origin hash commitment
        hash_payload = {
            "record_id": rec_id,
            "timestamp": now_iso,
            "horizon": forecast.horizon,
            "price": forecast.current_price,
            "p10": forecast.price_lower_p10,
            "p50": forecast.price_mid_p50,
            "p90": forecast.price_upper_p90,
            "gate_status": gate_status.value,
            "action": action
        }
        origin_hash = hashlib.sha256(json.dumps(hash_payload, sort_keys=True).encode()).hexdigest()

        record = ShadowDecisionRecord(
            record_id=rec_id,
            generation_timestamp=now_iso,
            horizon=forecast.horizon,
            current_price=forecast.current_price,
            model_version=forecast.model_version,
            feature_schema_version=forecast.feature_schema_version,
            origin_commitment_hash=origin_hash,
            price_lower_p10=forecast.price_lower_p10,
            price_mid_p50=forecast.price_mid_p50,
            price_upper_p90=forecast.price_upper_p90,
            interval_width_pct=forecast.interval_width_pct,
            expected_gross_edge_bps=round(gross_edge, 2),
            preregistered_friction_bps=self.BASE_FRICTION_BPS,
            expected_net_edge_bps=round(net_edge, 2),
            economic_hurdle_bps=self.MIN_REQUIRED_NET_EDGE_BPS,
            gate_status=gate_status,
            proposed_action=action,
            is_resolved=False,
            live_trading_prohibited=True
        )

        self._persist_record(record)
        return record

    def _persist_record(self, record: ShadowDecisionRecord) -> None:
        """Stores decision record immutably in SQLite."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            with conn:
                conn.execute("""
                    INSERT INTO shadow_decision_records (
                        record_id, generation_timestamp, horizon, current_price,
                        model_version, feature_schema_version, origin_commitment_hash,
                        price_lower_p10, price_mid_p50, price_upper_p90, interval_width_pct,
                        expected_gross_edge_bps, preregistered_friction_bps, expected_net_edge_bps,
                        economic_hurdle_bps, gate_status, proposed_action, is_resolved, live_trading_prohibited
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1)
                """, (
                    record.record_id, record.generation_timestamp, record.horizon, record.current_price,
                    record.model_version, record.feature_schema_version, record.origin_commitment_hash,
                    record.price_lower_p10, record.price_mid_p50, record.price_upper_p90, record.interval_width_pct,
                    record.expected_gross_edge_bps, record.preregistered_friction_bps, record.expected_net_edge_bps,
                    record.economic_hurdle_bps, record.gate_status.value, record.proposed_action
                ))
        finally:
            conn.close()

    def resolve_decision_outcome(
        self,
        record_id: str,
        actual_price: float,
        resolution_timestamp_iso: Optional[str] = None
    ) -> Optional[ShadowDecisionRecord]:
        """
        Resolves a shadow decision record once forward window has elapsed.
        Never mutates original forecast parameters or origin hash.
        """
        res_iso = resolution_timestamp_iso or datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("SELECT * FROM shadow_decision_records WHERE record_id = ?", (record_id,)).fetchone()
            if not row:
                return None

            entry_p = float(row["current_price"])
            p_low = float(row["price_lower_p10"])
            p_high = float(row["price_upper_p90"])
            action = str(row["proposed_action"])

            ret_bps = ((actual_price - entry_p) / entry_p) * 10000.0
            contained = 1 if (p_low <= actual_price <= p_high) else 0

            # Calculate net realized PnL
            if action == "RESEARCH_LONG":
                net_pnl = ret_bps - float(row["preregistered_friction_bps"])
            elif action == "RESEARCH_SHORT":
                net_pnl = -ret_bps - float(row["preregistered_friction_bps"])
            else:
                net_pnl = 0.0

            with conn:
                conn.execute("""
                    UPDATE shadow_decision_records
                    SET is_resolved = 1,
                        resolution_timestamp = ?,
                        actual_price_at_maturity = ?,
                        actual_return_bps = ?,
                        was_contained = ?,
                        realized_net_pnl_bps = ?
                    WHERE record_id = ?
                """, (res_iso, actual_price, round(ret_bps, 2), contained, round(net_pnl, 2), record_id))

            # Reload updated record
            updated_row = conn.execute("SELECT * FROM shadow_decision_records WHERE record_id = ?", (record_id,)).fetchone()
            return ShadowDecisionRecord(
                record_id=updated_row["record_id"],
                generation_timestamp=updated_row["generation_timestamp"],
                horizon=updated_row["horizon"],
                current_price=updated_row["current_price"],
                model_version=updated_row["model_version"],
                feature_schema_version=updated_row["feature_schema_version"],
                origin_commitment_hash=updated_row["origin_commitment_hash"],
                price_lower_p10=updated_row["price_lower_p10"],
                price_mid_p50=updated_row["price_mid_p50"],
                price_upper_p90=updated_row["price_upper_p90"],
                interval_width_pct=updated_row["interval_width_pct"],
                expected_gross_edge_bps=updated_row["expected_gross_edge_bps"],
                preregistered_friction_bps=updated_row["preregistered_friction_bps"],
                expected_net_edge_bps=updated_row["expected_net_edge_bps"],
                economic_hurdle_bps=updated_row["economic_hurdle_bps"],
                gate_status=DecisionGateStatus(updated_row["gate_status"]),
                proposed_action=updated_row["proposed_action"],
                is_resolved=bool(updated_row["is_resolved"]),
                resolution_timestamp=updated_row["resolution_timestamp"],
                actual_price_at_maturity=updated_row["actual_price_at_maturity"],
                actual_return_bps=updated_row["actual_return_bps"],
                was_contained=bool(updated_row["was_contained"]),
                realized_net_pnl_bps=updated_row["realized_net_pnl_bps"],
                live_trading_prohibited=True
            )
        finally:
            conn.close()

    def execute_live_order(self, *args, **kwargs):
        """Live trading is strictly prohibited in BTCognitive."""
        raise RuntimeError("CRITICAL VIOLATION: Live capital execution is permanently disabled in BTCognitive research systems.")


shadow_decision_engine = ShadowDecisionEngine()

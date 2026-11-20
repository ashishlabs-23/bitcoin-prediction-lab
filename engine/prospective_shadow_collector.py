"""
engine/prospective_shadow_collector.py — BTCognitive V30.3 Prospective Shadow Collector
=====================================================================================
Establishes a reproducible, forward-only shadow evaluation engine and append-only
ledger for HTF_RANGE_EXPANSION_BREAKOUT (Strategy D), the strongest exploratory
candidate identified in V30.2.

Epistemic & Non-Execution Invariants:
1. Strict Non-Execution: Live trading, real capital, and broker APIs are PERMANENTLY
   DISABLED. All candidates and outcomes are recorded strictly for offline research.
2. Separate Versioned Ledger: Appends only to `data/prospective_shadow_v1.jsonl`.
   NEVER modifies or rewrites `data/prospective_entry_ledger.jsonl`.
3. Two-Phase Audit Trail:
   - Phase A (Decision Time t0): Immutable candidate setup record written immediately.
   - Phase B (Maturity / Touch t_exit): Outcome record appended ONLY after the horizon
     or stop condition has elapsed. Prior records are never modified or overwritten.
4. Causal Boundaries:
   - Candidate evaluated strictly on completed 4h bar close.
   - Entry fill convention: Earliest possible execution at next bar's OPEN (no lookahead).
   - Stop Loss: 20-bar 4h Range Low (prior closed bars).
   - Max Horizon: 18 4h bars (72 hours).
5. Comprehensive Cost Scenarios:
   - COINBASE_RETAIL_87BPS: 87.0 bps round-trip (Primary benchmark)
   - COINBASE_INSTITUTIONAL_18BPS: 18.6 bps round-trip (Institutional spot)
   - BINANCE_PERP_15BPS: 15.0 bps round-trip (Hypothetical linear perp with funding)
   - ADVERSE_STRESS_120BPS: 120.0 bps round-trip (High-volatility stress scenario)
6. Deduplication & Idempotency: Duplicate candidates at the same timestamp are rejected.
"""

from __future__ import annotations

import os
import json
import uuid
import math
import hashlib
import logging
import threading
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Union

import pandas as pd
import numpy as np
from filelock import FileLock

logger = logging.getLogger("btcognitive.prospective_shadow")

DEFAULT_SHADOW_LEDGER_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "prospective_shadow_v1.jsonl")
)

STRATEGY_ID = "HTF_RANGE_EXPANSION_BREAKOUT"
STRATEGY_SPEC_HASH = "e1a3436a18ff992d"
STRATEGY_TIMEFRAME = "4h"
LOOKBACK_BARS = 20
MAX_HOLD_BARS = 18  # 18 * 4h = 72 hours
PRIMARY_INSTRUMENT = "BTC-USD"
PRIMARY_VENUE = "COINBASE"
PRIMARY_COST_SCENARIO = "COINBASE_RETAIL_87BPS"

COST_REGISTRY_BPS = {
    "COINBASE_RETAIL_87BPS": {
        "round_trip_bps": 87.0,
        "entry_commission_bps_per_side": 40.0,
        "exit_commission_bps_per_side": 40.0,
        "two_sided_commission_bps": 80.0,
        "half_spread_bps_per_side": 1.5,
        "round_trip_spread_bps": 3.0,
        "slippage_bps_per_side": 2.0,
        "round_trip_slippage_bps": 4.0,
        "round_trip_funding_bps": 0.0,
        "venue": "COINBASE",
        "market_type": "SPOT",
        "provenance": "Coinbase Advanced Tier 1 (<$10k) taker round-trip (40+40 comm + 3 spread + 4 slip)"
    },
    "COINBASE_INSTITUTIONAL_18BPS": {
        "round_trip_bps": 18.6,
        "entry_commission_bps_per_side": 8.0,
        "exit_commission_bps_per_side": 8.0,
        "two_sided_commission_bps": 16.0,
        "half_spread_bps_per_side": 0.5,
        "round_trip_spread_bps": 1.0,
        "slippage_bps_per_side": 0.8,
        "round_trip_slippage_bps": 1.6,
        "round_trip_funding_bps": 0.0,
        "venue": "COINBASE",
        "market_type": "SPOT",
        "provenance": "Coinbase Advanced Institutional high-volume taker round-trip"
    },
    "BINANCE_PERP_15BPS": {
        "round_trip_bps": 15.0,
        "entry_commission_bps_per_side": 5.0,
        "exit_commission_bps_per_side": 5.0,
        "two_sided_commission_bps": 10.0,
        "half_spread_bps_per_side": 0.5,
        "round_trip_spread_bps": 1.0,
        "slippage_bps_per_side": 1.0,
        "round_trip_slippage_bps": 2.0,
        "round_trip_funding_bps": 2.0,
        "venue": "BINANCE_FUTURES",
        "market_type": "PERPETUAL",
        "provenance": "Binance USDT-M Futures VIP 0 taker with 24h funding drag estimate"
    },
    "ADVERSE_STRESS_120BPS": {
        "round_trip_bps": 120.0,
        "entry_commission_bps_per_side": 50.0,
        "exit_commission_bps_per_side": 50.0,
        "two_sided_commission_bps": 100.0,
        "half_spread_bps_per_side": 4.0,
        "round_trip_spread_bps": 8.0,
        "slippage_bps_per_side": 6.0,
        "round_trip_slippage_bps": 12.0,
        "round_trip_funding_bps": 0.0,
        "venue": "COINBASE",
        "market_type": "SPOT",
        "provenance": "Adverse volatility / illiquidity execution stress test"
    }
}


def compute_shadow_candidate_id(
    strategy_id: str,
    decision_timestamp_utc: str,
    entry_reference_price: float,
    stop_loss_price: float,
    horizon_bars: int
) -> str:
    """Computes a deterministic, tamper-evident candidate identifier."""
    payload = f"{strategy_id}:{decision_timestamp_utc}:{entry_reference_price:.2f}:{stop_loss_price:.2f}:{horizon_bars}"
    sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"scand_{sha[:16]}"


@dataclass(frozen=True)
class ShadowCandidateRecord:
    """
    Immutable candidate record emitted at decision time t0.
    Frozen dataclass to prevent in-memory mutation.
    """
    record_type: str  # "SHADOW_CANDIDATE"
    schema_version: str  # "PROSPECTIVE_SHADOW_V1"
    candidate_id: str
    strategy_id: str
    strategy_spec_hash: str
    instrument_id: str
    venue: str
    market_type: str
    decision_timestamp_utc: str
    data_availability_timestamp_utc: str
    signal_inputs: Dict[str, Any]
    entry_reference_price: float
    fill_assumption: str  # "NEXT_BAR_OPEN"
    proposed_entry_price: float
    stop_loss_price: float
    take_profit_price: Optional[float]
    direction: str  # "LONG"
    horizon_bars: int  # 18 4h bars (72h)
    primary_cost_scenario: str
    cost_assumptions_bps: Dict[str, float]
    action: str  # "CANDIDATE_EMITTED" or "ABSTAIN"
    abstention_reason: Optional[str]
    data_quality_status: str  # "VALID", "SUSPECT_GAP", "MISSING_DATA"
    execution_authorization: str = "DISABLED — ANALYSIS ONLY"
    governance_status: str = "OFFLINE_RESEARCH_ONLY"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ShadowOutcomeRecord:
    """
    Immutable outcome resolution record emitted after trade conclusion.
    Links to candidate_id without rewriting the original candidate entry.
    """
    record_type: str  # "SHADOW_OUTCOME"
    schema_version: str  # "PROSPECTIVE_SHADOW_V1"
    candidate_id: str
    strategy_id: str
    resolution_status: str  # "RESOLVED", "TIMEOUT", "AMBIGUOUS", "EXCLUDED"
    exit_reason: str  # "STOP_LOSS", "HORIZON_TIMEOUT", "MANUAL_RECOVERY"
    is_ambiguous_touch: bool
    entry_timestamp_utc: str
    exit_timestamp_utc: str
    entry_fill_price: float
    exit_price: float
    bars_held_4h: int
    holding_hours: float
    gross_return_bps: float
    net_returns_by_scenario_bps: Dict[str, float]
    risk_unit_usd: float
    gross_r: float
    net_r_by_scenario: Dict[str, float]
    mfe_r: float
    mae_r: float
    resolution_timestamp_utc: str
    data_quality_status: str
    execution_authorization: str = "DISABLED — ANALYSIS ONLY"
    governance_status: str = "OFFLINE_RESEARCH_ONLY"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProspectiveShadowLedger:
    """
    Thread-safe and cross-process safe, append-only durable storage for shadow candidates and outcomes.
    Guarantees:
    - Never overwrites or truncates existing data.
    - Prevents candidate duplicate registrations across threads and processes.
    - Cross-process locking via filelock.FileLock.
    - Atomic writes with explicit OS flush and sync.
    - Full crash recovery and audit indexing on initialization.
    """

    def __init__(self, ledger_path: Optional[str] = None, lock_path: Optional[str] = None):
        self.ledger_path = ledger_path or DEFAULT_SHADOW_LEDGER_PATH
        self.lock_path = lock_path or (self.ledger_path + ".lock")
        self._thread_lock = threading.Lock()
        self._file_lock = FileLock(self.lock_path, timeout=10.0)
        self._registered_candidate_ids: set[str] = set()
        self._resolved_candidate_ids: set[str] = set()
        self._ensure_file_and_index()

    def _ensure_file_and_index(self) -> None:
        """Ensures ledger directory exists and builds an in-memory index from disk."""
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.lock_path), exist_ok=True)
        if not os.path.exists(self.ledger_path):
            with open(self.ledger_path, "w", encoding="utf-8") as f:
                pass  # create empty file
            return

        self._reindex_from_disk()

    def _reindex_from_disk(self) -> None:
        """Reconstructs state index from existing records on disk."""
        if not os.path.exists(self.ledger_path):
            return
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                clean = line.strip()
                if not clean:
                    continue
                try:
                    rec = json.loads(clean)
                    c_id = rec.get("candidate_id")
                    rec_type = rec.get("record_type")
                    if c_id:
                        if rec_type == "SHADOW_CANDIDATE":
                            self._registered_candidate_ids.add(c_id)
                        elif rec_type == "SHADOW_OUTCOME":
                            self._resolved_candidate_ids.add(c_id)
                except json.JSONDecodeError as e:
                    logger.warning(f"Corrupt JSON at line {line_no} of shadow ledger: {e}")

    def append_candidate(self, candidate: ShadowCandidateRecord) -> bool:
        """
        Appends an immutable decision record with thread and cross-process safety.
        Returns True if appended, False if candidate_id was already registered (idempotency).
        """
        with self._thread_lock, self._file_lock:
            self._reindex_from_disk()
            if candidate.candidate_id in self._registered_candidate_ids:
                logger.info(f"Candidate {candidate.candidate_id} already registered. Skipping append.")
                return False

            payload = json.dumps(candidate.to_dict()) + "\n"
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())

            self._registered_candidate_ids.add(candidate.candidate_id)
            return True

    def append_outcome(self, outcome: ShadowOutcomeRecord) -> bool:
        """
        Appends an immutable outcome resolution record with thread and cross-process safety.
        Returns True if appended, False if already resolved.
        """
        with self._thread_lock, self._file_lock:
            self._reindex_from_disk()
            if outcome.candidate_id in self._resolved_candidate_ids:
                logger.info(f"Outcome for {outcome.candidate_id} already recorded. Skipping append.")
                return False

            payload = json.dumps(outcome.to_dict()) + "\n"
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())

            self._resolved_candidate_ids.add(outcome.candidate_id)
            return True

    def get_registered_candidates(self) -> List[Dict[str, Any]]:
        """Reads all candidate records from the ledger."""
        records = []
        if not os.path.exists(self.ledger_path):
            return records
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                clean = line.strip()
                if clean:
                    rec = json.loads(clean)
                    if rec.get("record_type") == "SHADOW_CANDIDATE":
                        records.append(rec)
        return records

    def get_resolved_outcomes(self) -> List[Dict[str, Any]]:
        """Reads all outcome records from the ledger."""
        records = []
        if not os.path.exists(self.ledger_path):
            return records
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                clean = line.strip()
                if clean:
                    rec = json.loads(clean)
                    if rec.get("record_type") == "SHADOW_OUTCOME":
                        records.append(rec)
        return records

    def get_ledger_summary(self) -> Dict[str, Any]:
        """Provides an auditable summary of ledger contents."""
        candidates = self.get_registered_candidates()
        outcomes = self.get_resolved_outcomes()
        return {
            "ledger_path": self.ledger_path,
            "total_candidates": len(candidates),
            "total_outcomes": len(outcomes),
            "pending_resolution": len(candidates) - len(outcomes),
            "registered_candidate_ids": sorted(list(self._registered_candidate_ids)),
            "resolved_candidate_ids": sorted(list(self._resolved_candidate_ids))
        }


class HTFShadowCollector:
    """
    Orchestrates prospective candidate generation and causal outcome resolution
    for HTF_RANGE_EXPANSION_BREAKOUT.
    """

    def __init__(self, ledger: Optional[ProspectiveShadowLedger] = None):
        self.ledger = ledger or ProspectiveShadowLedger()

    @staticmethod
    def resample_1h_to_4h(df_1h: pd.DataFrame) -> pd.DataFrame:
        """
        Converts 1h OHLCV into strictly point-in-time 4h candles.
        Uses left-closed, left-labeled intervals with explicit Range High/Low computation.
        """
        df = df_1h.copy()
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            df = df.set_index("timestamp")

        agg_dict = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }
        df_4h = df.resample("4h", closed="left", label="left").agg(agg_dict).dropna().reset_index()

        # Shift(1) ensures rolling lookback strictly contains CLOSED prior bars
        df_4h["range_high_20_4h"] = df_4h["high"].shift(1).rolling(LOOKBACK_BARS).max()
        df_4h["range_low_20_4h"] = df_4h["low"].shift(1).rolling(LOOKBACK_BARS).min()
        return df_4h

    def get_active_unresolved_candidate(self) -> Optional[Dict[str, Any]]:
        """Returns candidate record if there is currently an open, unresolved position."""
        unresolved_ids = self.ledger._registered_candidate_ids - self.ledger._resolved_candidate_ids
        if not unresolved_ids:
            return None
        for cand in reversed(self.ledger.get_registered_candidates()):
            if cand.get("candidate_id") in unresolved_ids:
                return cand
        return None

    def evaluate_bar_for_candidate(
        self,
        cur_4h_bar: pd.Series,
        nxt_bar_open: float,
        nxt_bar_timestamp_utc: str,
        allow_overlapping: bool = False
    ) -> Optional[ShadowCandidateRecord]:
        """
        Evaluates a closed 4h bar for a causal breakout candidate.
        Returns a ShadowCandidateRecord if breakout criteria are met, otherwise None.
        Enforces non-overlapping position gating by default.
        """
        if not allow_overlapping and self.get_active_unresolved_candidate() is not None:
            return None

        close_price = float(cur_4h_bar["close"])
        range_high = cur_4h_bar.get("range_high_20_4h")
        range_low = cur_4h_bar.get("range_low_20_4h")

        if pd.isna(range_high) or pd.isna(range_low):
            return None

        range_high = float(range_high)
        range_low = float(range_low)

        # Breakout condition on CLOSED candle
        if close_price <= range_high:
            return None

        decision_ts = pd.to_datetime(cur_4h_bar["timestamp"], utc=True).isoformat()
        availability_ts = decision_ts  # closed bar is available immediately at close

        cand_id = compute_shadow_candidate_id(
            strategy_id=STRATEGY_ID,
            decision_timestamp_utc=decision_ts,
            entry_reference_price=nxt_bar_open,
            stop_loss_price=range_low,
            horizon_bars=MAX_HOLD_BARS
        )

        cost_bps_dict = {k: v["round_trip_bps"] for k, v in COST_REGISTRY_BPS.items()}

        candidate = ShadowCandidateRecord(
            record_type="SHADOW_CANDIDATE",
            schema_version="PROSPECTIVE_SHADOW_V1",
            candidate_id=cand_id,
            strategy_id=STRATEGY_ID,
            strategy_spec_hash=STRATEGY_SPEC_HASH,
            instrument_id=PRIMARY_INSTRUMENT,
            venue=PRIMARY_VENUE,
            market_type="SPOT",
            decision_timestamp_utc=decision_ts,
            data_availability_timestamp_utc=availability_ts,
            signal_inputs={
                "close": close_price,
                "range_high_20_4h": range_high,
                "range_low_20_4h": range_low,
                "breakout_excess_bps": round(((close_price - range_high) / range_high) * 10000.0, 2),
                "volume": float(cur_4h_bar.get("volume", 0.0))
            },
            entry_reference_price=close_price,
            fill_assumption="NEXT_BAR_OPEN",
            proposed_entry_price=nxt_bar_open,
            stop_loss_price=range_low,
            take_profit_price=None,  # Strategy D uses trailing/horizon exit
            direction="LONG",
            horizon_bars=MAX_HOLD_BARS,
            primary_cost_scenario=PRIMARY_COST_SCENARIO,
            cost_assumptions_bps=cost_bps_dict,
            action="CANDIDATE_EMITTED",
            abstention_reason=None,
            data_quality_status="VALID",
            execution_authorization="DISABLED — ANALYSIS ONLY",
            governance_status="OFFLINE_RESEARCH_ONLY"
        )
        return candidate

    def resolve_candidate_outcome(
        self,
        candidate: ShadowCandidateRecord,
        future_4h_bars: pd.DataFrame
    ) -> Optional[ShadowOutcomeRecord]:
        """
        Deterministically evaluates future bars to resolve the candidate outcome.
        Returns ShadowOutcomeRecord if resolution conditions (stop or horizon) are met.
        If the trade has not concluded yet, returns None (still pending).
        """
        if future_4h_bars.empty:
            return None

        entry_price = candidate.proposed_entry_price
        stop_price = candidate.stop_loss_price
        risk_usd = entry_price - stop_price
        if risk_usd <= 0:
            raise ValueError(
                f"Invalid risk geometry for candidate {candidate.candidate_id}: "
                f"proposed_entry_price ({entry_price}) <= stop_loss_price ({stop_price}). "
                "LONG candidates require strictly positive risk (entry > stop)."
            )

        mfe_r = 0.0
        mae_r = 0.0
        entry_ts = candidate.decision_timestamp_utc

        for idx in range(len(future_4h_bars)):
            bar = future_4h_bars.iloc[idx]
            bar_high = float(bar["high"])
            bar_low = float(bar["low"])
            bar_close = float(bar["close"])
            bar_open = float(bar["open"])
            bar_ts = pd.to_datetime(bar["timestamp"], utc=True).isoformat()

            # Track excursion
            fav = (bar_high - entry_price) / risk_usd
            adv = (bar_low - entry_price) / risk_usd
            mfe_r = max(mfe_r, fav)
            mae_r = min(mae_r, adv)

            bars_held = idx + 1
            max_hold_expired = bars_held >= candidate.horizon_bars
            stop_hit = bar_low <= stop_price

            if stop_hit or max_hold_expired:
                # Determine exit price with opening gap protection
                is_ambiguous = False
                if stop_hit:
                    exit_reason = "STOP_LOSS"
                    # If open gapped below stop, fill at open (slippage)
                    exit_price = min(stop_price, bar_open) if bar_open <= stop_price else stop_price
                else:
                    exit_reason = "HORIZON_TIMEOUT"
                    exit_price = bar_close

                gross_return_bps = ((exit_price - entry_price) / entry_price) * 10000.0
                gross_r = (exit_price - entry_price) / risk_usd

                # Compute net returns (bps) and net R for all registered scenarios
                net_returns = {}
                net_r_dict = {}
                for scen, cfg in COST_REGISTRY_BPS.items():
                    rt_bps = cfg["round_trip_bps"]
                    net_returns[scen] = round(gross_return_bps - rt_bps, 2)
                    friction_usd = entry_price * (rt_bps / 10000.0)
                    net_r = ((exit_price - entry_price) - friction_usd) / risk_usd
                    net_r_dict[scen] = round(net_r, 4)

                now_ts = datetime.now(timezone.utc).isoformat()

                return ShadowOutcomeRecord(
                    record_type="SHADOW_OUTCOME",
                    schema_version="PROSPECTIVE_SHADOW_V1",
                    candidate_id=candidate.candidate_id,
                    strategy_id=candidate.strategy_id,
                    resolution_status="RESOLVED",
                    exit_reason=exit_reason,
                    is_ambiguous_touch=is_ambiguous,
                    entry_timestamp_utc=entry_ts,
                    exit_timestamp_utc=bar_ts,
                    entry_fill_price=entry_price,
                    exit_price=round(exit_price, 2),
                    bars_held_4h=bars_held,
                    holding_hours=float(bars_held * 4),
                    gross_return_bps=round(gross_return_bps, 2),
                    net_returns_by_scenario_bps=net_returns,
                    risk_unit_usd=round(risk_usd, 2),
                    gross_r=round(gross_r, 4),
                    net_r_by_scenario=net_r_dict,
                    mfe_r=round(mfe_r, 4),
                    mae_r=round(mae_r, 4),
                    resolution_timestamp_utc=now_ts,
                    data_quality_status="VALID",
                    execution_authorization="DISABLED — ANALYSIS ONLY",
                    governance_status="OFFLINE_RESEARCH_ONLY"
                )

        return None  # Still pending maturation

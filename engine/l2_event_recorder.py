"""
engine/l2_event_recorder.py — Immutable Replayable L2 Event Recorder & Audit Engine
===================================================================================
BTCognitive V32.38: Adaptive Market Intelligence & Level-2 Data Integrity

Provides immutable, replayable event storage, deterministic SHA-256 event checksums,
and deterministic replay into OrderBookTracker.
Tracks data loss metrics transparently (duplicates, sequence gaps, out-of-order, heartbeat stalls)
and storage footprint without data fabrication.
"""

from __future__ import annotations

import os
import json
import time
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Sequence, Tuple

from engine.l2_microstructure_features import OrderBookTracker


@dataclass(frozen=True)
class RawL2Event:
    """Immutable Level-2 market event record with deterministic checksum."""
    event_id: str
    timestamp_utc: str
    epoch: float
    event_type: str  # 'snapshot', 'l2update', 'match', 'heartbeat'
    sequence: Optional[int]
    payload: Dict[str, Any]
    checksum_sha256: str
    schema_version: str = "v32.38.l2_event"

    @classmethod
    def create(
        cls,
        event_type: str,
        payload: Dict[str, Any],
        epoch: Optional[float] = None,
        sequence: Optional[int] = None
    ) -> RawL2Event:
        ep = epoch if epoch is not None else time.time()
        ts_utc = datetime.fromtimestamp(ep, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        canonical_str = json.dumps(
            {"type": event_type, "epoch": ep, "sequence": sequence, "payload": payload},
            sort_keys=True
        )
        checksum = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
        event_id = f"l2ev-{checksum[:16]}"
        return cls(
            event_id=event_id,
            timestamp_utc=ts_utc,
            epoch=ep,
            event_type=event_type,
            sequence=sequence,
            payload=payload,
            checksum_sha256=checksum
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class L2ReplaySummary:
    """Summary of deterministic event replay."""
    events_replayed: int
    valid_updates: int
    dropped_duplicates: int
    dropped_out_of_order: int
    sequence_gaps: int
    heartbeat_stalls: int
    final_is_synchronized: bool
    final_best_bid: Optional[float]
    final_best_ask: Optional[float]
    final_mid_price: Optional[float]
    final_sequence: int
    desync_reason: Optional[str]
    replay_duration_ms: float


class L2EventRecorder:
    """
    Manages in-memory and append-only disk logging of raw Level-2 events
    with data loss accounting and deterministic replay capabilities.
    """

    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path
        self._events: List[RawL2Event] = []
        self.total_bytes_written: int = 0
        self.total_events_recorded: int = 0

    def record_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        epoch: Optional[float] = None,
        sequence: Optional[int] = None
    ) -> RawL2Event:
        event = RawL2Event.create(
            event_type=event_type,
            payload=payload,
            epoch=epoch,
            sequence=sequence
        )
        self._events.append(event)
        self.total_events_recorded += 1

        if self.log_path:
            line = json.dumps(event.to_dict()) + "\n"
            line_bytes = line.encode("utf-8")
            self.total_bytes_written += len(line_bytes)
            os.makedirs(os.path.dirname(os.path.abspath(self.log_path)), exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line)

        return event

    def get_events(self) -> List[RawL2Event]:
        return list(self._events)

    def clear(self):
        self._events.clear()
        self.total_events_recorded = 0
        self.total_bytes_written = 0

    @staticmethod
    def replay_events(
        events: Sequence[RawL2Event],
        tracker: Optional[OrderBookTracker] = None,
        max_staleness_seconds: float = 5.0
    ) -> Tuple[OrderBookTracker, L2ReplaySummary]:
        """
        Replays raw events sequentially into an OrderBookTracker deterministically.
        Verifies synchronization, sequence progression, and data loss events.
        """
        t0 = time.perf_counter()
        tr = tracker or OrderBookTracker()
        tr.reset(reason="REPLAY_START")

        valid_updates = 0

        for ev in events:
            ep = ev.epoch
            ev_type = ev.event_type.lower()
            p = ev.payload

            if ev_type == "snapshot":
                tr.process_snapshot(p, received_epoch=ep)
                valid_updates += 1
            elif ev_type == "l2update":
                applied = tr.process_l2update(p, received_epoch=ep)
                if applied:
                    valid_updates += 1
            elif ev_type == "match":
                tr.process_match(p, received_epoch=ep)
                valid_updates += 1
            elif ev_type == "heartbeat":
                tr.process_heartbeat(p, received_epoch=ep)
                valid_updates += 1

        b_b, _ = tr.get_best_bid()
        b_a, _ = tr.get_best_ask()
        mid = 0.5 * (b_b + b_a) if (b_b and b_a and b_a > b_b) else None

        duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        summary = L2ReplaySummary(
            events_replayed=len(events),
            valid_updates=valid_updates,
            dropped_duplicates=tr.dropped_duplicates_count,
            dropped_out_of_order=tr.dropped_out_of_order_count,
            sequence_gaps=tr.sequence_gaps_count,
            heartbeat_stalls=tr.heartbeat_timeouts_count,
            final_is_synchronized=tr.is_synchronized,
            final_best_bid=b_b,
            final_best_ask=b_a,
            final_mid_price=mid,
            final_sequence=tr.last_sequence,
            desync_reason=tr.desync_reason,
            replay_duration_ms=duration_ms
        )

        return tr, summary

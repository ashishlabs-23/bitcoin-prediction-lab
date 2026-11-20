"""
engine/l2_microstructure_features.py — Causal Level-2 Market Microstructure Features
=====================================================================================
BTCognitive V32.38: Adaptive Market Intelligence & Level-2 Causal Feature Layer

Implements point-in-time order book and trade flow analytics derived from Coinbase
Exchange Level-2 and matches data:
1. Multi-window Order Flow Imbalance (OFI) based on Cont, Kukanov & Stoikov (2014): 1m, 5m, 15m.
2. Multi-depth Order Book Imbalance (OBI_K) at depth K in {5, 10, 25, 50} and cumulative tier volume.
3. Spread in basis points and depth within price bands (10 bps, 25 bps).
4. Multi-window Cumulative Volume Delta (CVD) and aggressor buy/sell ratios.
5. High-frequency realized volatility and micro-liquidity / price-impact measures (Kyle's lambda, Amihud).
6. Sequence gap, duplicate, out-of-order, and heartbeat stall detection with explicit fail-closed boundaries.

Causal Invariants:
- Zero Lookahead: Calculations strictly consume messages with local receipt timestamps <= t_decision.
- Strict Fail-Closed: If book is desynchronized, stale (>5s heartbeat), or sequence gap detected,
  returns is_available=False with explicit reason_code. Zero synthetic zero-filling.
- Immutable point-in-time snapshot with schema version v32.38.causal_l2.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Sequence
import numpy as np


@dataclass(frozen=True)
class L2MicrostructureSnapshot:
    """Immutable point-in-time microstructure observation."""
    is_available: bool
    reason_code: Optional[str]
    observation_time_utc: str
    observation_epoch: float
    best_bid: Optional[float]
    best_ask: Optional[float]
    mid_price: Optional[float]
    spread_bps: Optional[float]
    obi_5: Optional[float]
    obi_10: Optional[float]
    obi_25: Optional[float]
    ofi_value: Optional[float]
    cvd_value: Optional[float]
    trade_count_in_window: int
    book_updates_in_window: int
    data_age_seconds: float
    is_feed_synchronized: bool

    # --- V32.38 Extended Microstructure Features ---
    obi_50: Optional[float] = None
    ofi_1m: Optional[float] = None
    ofi_5m: Optional[float] = None
    ofi_15m: Optional[float] = None
    cvd_1m: Optional[float] = None
    cvd_5m: Optional[float] = None
    cvd_15m: Optional[float] = None
    bid_depth_5: Optional[float] = None
    ask_depth_5: Optional[float] = None
    bid_depth_25: Optional[float] = None
    ask_depth_25: Optional[float] = None
    bid_depth_10bps: Optional[float] = None
    ask_depth_10bps: Optional[float] = None
    total_bid_depth: Optional[float] = None
    total_ask_depth: Optional[float] = None
    hf_realized_vol_15m: Optional[float] = None
    kyles_lambda_proxy: Optional[float] = None
    amihud_illiquidity_proxy: Optional[float] = None
    first_event_epoch: Optional[float] = None
    last_event_epoch: Optional[float] = None
    event_count_consumed: int = 0
    schema_version: str = "v32.38.causal_l2"

    # --- V32.40B Feature Warm-Up & Qualification Extensions ---
    feature_status: Dict[str, str] = field(default_factory=dict)
    valid_history_duration_seconds: float = 0.0
    is_window_warmed_up: bool = False

    def is_feature_available(self, feature_name: str) -> bool:
        """Returns True if the specific feature is verified ready and warmed up."""
        if not self.is_available or not self.is_feed_synchronized:
            return False
        return self.feature_status.get(feature_name) == "READY"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_obi(bids: Dict[float, float], asks: Dict[float, float], depth: int = 5) -> float:
    """
    Computes Order Book Imbalance at top K levels:
    OBI_K = (sum(V_bid) - sum(V_ask)) / (sum(V_bid) + sum(V_ask)) in [-1.0, +1.0].
    """
    if not bids or not asks or depth <= 0:
        return 0.0

    sorted_bids = sorted(bids.items(), key=lambda x: x[0], reverse=True)[:depth]
    sorted_asks = sorted(asks.items(), key=lambda x: x[0], reverse=False)[:depth]

    v_bid = sum(qty for _, qty in sorted_bids)
    v_ask = sum(qty for _, qty in sorted_asks)
    total_v = v_bid + v_ask

    if total_v <= 0:
        return 0.0

    return float((v_bid - v_ask) / total_v)


def compute_depth_volume(book: Dict[float, float], depth: int = 5, is_bid: bool = True) -> float:
    """Computes available cumulative volume across top K levels."""
    if not book or depth <= 0:
        return 0.0
    sorted_levels = sorted(book.items(), key=lambda x: x[0], reverse=is_bid)[:depth]
    return float(sum(qty for _, qty in sorted_levels))


def compute_depth_within_bps(
    book: Dict[float, float],
    mid_price: float,
    bps: float = 10.0,
    is_bid: bool = True
) -> float:
    """
    Computes available cumulative depth within a defined basis-point threshold from mid price.
    """
    if not book or mid_price <= 0:
        return 0.0
    threshold = (bps / 10000.0) * mid_price
    if is_bid:
        min_price = mid_price - threshold
        return float(sum(qty for p, qty in book.items() if p >= min_price))
    else:
        max_price = mid_price + threshold
        return float(sum(qty for p, qty in book.items() if p <= max_price))


def compute_spread_bps(best_bid: float, best_ask: float) -> float:
    """Computes top-of-book half-spread / relative spread in basis points."""
    if best_bid <= 0 or best_ask <= 0 or best_ask <= best_bid:
        return 0.0
    mid = 0.5 * (best_bid + best_ask)
    return float(((best_ask - best_bid) / mid) * 10000.0)


def compute_ofi_from_top_of_book_events(events: Sequence[Dict[str, Any]]) -> float:
    """
    Computes Order Flow Imbalance (OFI) based on Cont, Kukanov & Stoikov (2014):
    Delta Q_B:
      - if P_B(k) > P_B(k-1): +q_B(k)
      - if P_B(k) == P_B(k-1): q_B(k) - q_B(k-1)
      - if P_B(k) < P_B(k-1): -q_B(k-1)
    Delta Q_A:
      - if P_A(k) > P_A(k-1): -q_A(k)
      - if P_A(k) == P_A(k-1): q_A(k) - q_A(k-1)
      - if P_A(k) < P_A(k-1): +q_A(k-1)
    OFI = sum(Delta Q_B - Delta Q_A).
    """
    if len(events) < 2:
        return 0.0

    total_ofi = 0.0
    for i in range(1, len(events)):
        prev = events[i - 1]
        curr = events[i]

        p_b_prev = prev["best_bid"]
        q_b_prev = prev["best_bid_size"]
        p_b_curr = curr["best_bid"]
        q_b_curr = curr["best_bid_size"]

        p_a_prev = prev["best_ask"]
        q_a_prev = prev["best_ask_size"]
        p_a_curr = curr["best_ask"]
        q_a_curr = curr["best_ask_size"]

        # Bid delta
        if p_b_curr > p_b_prev:
            delta_b = q_b_curr
        elif p_b_curr == p_b_prev:
            delta_b = q_b_curr - q_b_prev
        else:
            delta_b = -q_b_prev

        # Ask delta
        if p_a_curr > p_a_prev:
            delta_a = -q_a_curr
        elif p_a_curr == p_a_prev:
            delta_a = q_a_curr - q_a_prev
        else:
            delta_a = q_a_prev

        total_ofi += (delta_b - delta_a)

    return float(total_ofi)


def compute_cvd_from_matches(matches: Sequence[Dict[str, Any]]) -> float:
    """
    Computes Cumulative Volume Delta (CVD):
    CVD = sum(buy_size) - sum(sell_size) where side denotes aggressor / taker side.
    """
    if not matches:
        return 0.0
    buy_vol = sum(float(m["size"]) for m in matches if str(m.get("side", "")).lower() == "buy")
    sell_vol = sum(float(m["size"]) for m in matches if str(m.get("side", "")).lower() == "sell")
    return float(buy_vol - sell_vol)


def compute_hf_realized_vol(events: Sequence[Dict[str, Any]]) -> float:
    """
    Computes annualized realized volatility from high-frequency mid-quote log returns.
    """
    if len(events) < 5:
        return 0.0

    mids = [0.5 * (e["best_bid"] + e["best_ask"]) for e in events]
    log_mids = np.log(mids)
    returns = np.diff(log_mids)
    if len(returns) == 0:
        return 0.0

    # Hourly return proxy scaled to annual (8,760 hours)
    std_ret = float(np.std(returns, ddof=1)) if len(returns) > 1 else 0.0
    return float(std_ret * math.sqrt(8760.0 * 60.0)) # scaled for 1-minute cadence proxy


def compute_kyles_lambda_proxy(events: Sequence[Dict[str, Any]], ofi: float) -> float:
    """
    Computes Kyle's Lambda price impact proxy:
    lambda = |Delta P_mid| / max(|OFI|, 0.001) in $/BTC.
    """
    if len(events) < 2 or abs(ofi) < 1e-4:
        return 0.0
    mid_start = 0.5 * (events[0]["best_bid"] + events[0]["best_ask"])
    mid_end = 0.5 * (events[-1]["best_bid"] + events[-1]["best_ask"])
    delta_p = abs(mid_end - mid_start)
    return float(delta_p / max(abs(ofi), 1e-3))


def compute_amihud_proxy(events: Sequence[Dict[str, Any]], matches: Sequence[Dict[str, Any]]) -> float:
    """
    Computes Amihud illiquidity proxy:
    illiq = (|Delta P_mid / P_mid_0|) / max(Total_Volume, 0.001) * 1e6.
    """
    if len(events) < 2 or not matches:
        return 0.0
    mid_start = 0.5 * (events[0]["best_bid"] + events[0]["best_ask"])
    mid_end = 0.5 * (events[-1]["best_bid"] + events[-1]["best_ask"])
    if mid_start <= 0:
        return 0.0
    ret_pct = abs(mid_end - mid_start) / mid_start
    total_vol = sum(float(m.get("size", 0.0)) for m in matches)
    return float((ret_pct / max(total_vol, 1e-3)) * 1e6)


class OrderBookTracker:
    """
    In-memory Level-2 order book reconstructor and microstructure feature provider.
    Maintains bids, asks, sequencing, event history, and transparent data loss metrics.
    """

    def __init__(self, max_history_events: int = 5000):
        self.bids: Dict[float, float] = {}
        self.asks: Dict[float, float] = {}
        self.last_sequence: int = -1
        self.last_heartbeat_epoch: float = 0.0
        self.last_update_epoch: float = 0.0
        self.is_synchronized: bool = False
        self.desync_reason: Optional[str] = "NOT_INITIALIZED"
        self.sync_epoch: Optional[float] = None
        self.first_event_epoch: Optional[float] = None

        # Bounded circular buffers for feature computation
        self.max_history_events = max_history_events
        self.top_of_book_history: List[Dict[str, Any]] = []
        self.match_history: List[Dict[str, Any]] = []

        # Data loss & fault metrics (V32.38)
        self.dropped_duplicates_count: int = 0
        self.dropped_out_of_order_count: int = 0
        self.sequence_gaps_count: int = 0
        self.heartbeat_timeouts_count: int = 0
        self.events_processed_count: int = 0

    def reset(self, reason: str = "MANUAL_RESET"):
        """Resets the local order book state to uninitialized."""
        self.bids.clear()
        self.asks.clear()
        self.last_sequence = -1
        self.last_heartbeat_epoch = 0.0
        self.last_update_epoch = 0.0
        self.is_synchronized = False
        self.desync_reason = reason
        self.sync_epoch = None
        self.first_event_epoch = None
        self.top_of_book_history.clear()
        self.match_history.clear()

    def process_snapshot(self, snapshot_msg: Dict[str, Any], received_epoch: float):
        """Processes an authoritative Coinbase snapshot message."""
        self.bids.clear()
        self.asks.clear()

        raw_bids = snapshot_msg.get("bids", [])
        raw_asks = snapshot_msg.get("asks", [])

        for price_str, size_str in raw_bids:
            p = float(price_str)
            s = float(size_str)
            if s > 0:
                self.bids[p] = s

        for price_str, size_str in raw_asks:
            p = float(price_str)
            s = float(size_str)
            if s > 0:
                self.asks[p] = s

        seq = snapshot_msg.get("sequence")
        self.last_sequence = int(seq) if seq is not None else 0
        self.last_heartbeat_epoch = received_epoch
        self.last_update_epoch = received_epoch
        self.is_synchronized = True
        self.desync_reason = None
        self.sync_epoch = received_epoch
        if self.first_event_epoch is None:
            self.first_event_epoch = received_epoch
        self.events_processed_count += 1

        self._record_top_of_book(received_epoch)

    def process_l2update(self, update_msg: Dict[str, Any], received_epoch: float) -> bool:
        """
        Processes a Coinbase delta update (l2update).
        Returns True if update was applied cleanly; False if sequence gap/duplicate/out-of-order occurred.
        """
        if not self.is_synchronized:
            return False

        seq = update_msg.get("sequence")
        if seq is not None:
            seq_int = int(seq)
            if self.last_sequence >= 0:
                # 1. Out-of-order check
                if seq_int < self.last_sequence:
                    self.dropped_out_of_order_count += 1
                    return False

                # 2. Duplicate check
                if seq_int == self.last_sequence:
                    self.dropped_duplicates_count += 1
                    return False

                # 3. Sequence gap check
                if seq_int > self.last_sequence + 1:
                    self.is_synchronized = False
                    self.sequence_gaps_count += 1
                    self.desync_reason = f"SEQUENCE_GAP_DETECTED (expected {self.last_sequence + 1}, got {seq_int})"
                    self.sync_epoch = None
                    self.top_of_book_history.clear()
                    self.match_history.clear()
                    return False

            self.last_sequence = seq_int

        changes = update_msg.get("changes", [])
        for side, price_str, size_str in changes:
            p = float(price_str)
            s = float(size_str)
            side_clean = str(side).lower()

            target_book = self.bids if side_clean == "buy" else self.asks
            if s <= 0:
                target_book.pop(p, None)
            else:
                target_book[p] = s

        self.last_update_epoch = received_epoch
        self.events_processed_count += 1
        self._record_top_of_book(received_epoch)
        return True

    def process_match(self, match_msg: Dict[str, Any], received_epoch: float):
        """Processes an executed trade match from the matches feed."""
        trade_record = {
            "epoch": received_epoch,
            "trade_id": match_msg.get("trade_id"),
            "price": float(match_msg.get("price", 0.0)),
            "size": float(match_msg.get("size", 0.0)),
            "side": str(match_msg.get("side", "")).lower()
        }
        self.match_history.append(trade_record)
        self.events_processed_count += 1
        if len(self.match_history) > self.max_history_events:
            self.match_history.pop(0)

    def process_heartbeat(self, heartbeat_msg: Dict[str, Any], received_epoch: float):
        """Updates heartbeat timestamp to track socket liveness."""
        self.last_heartbeat_epoch = received_epoch
        self.events_processed_count += 1

    def _record_top_of_book(self, epoch: float):
        best_b, best_b_sz = self.get_best_bid()
        best_a, best_a_sz = self.get_best_ask()
        if best_b is not None and best_a is not None:
            self.top_of_book_history.append({
                "epoch": epoch,
                "best_bid": best_b,
                "best_bid_size": best_b_sz,
                "best_ask": best_a,
                "best_ask_size": best_a_sz
            })
            if len(self.top_of_book_history) > self.max_history_events:
                self.top_of_book_history.pop(0)

    def get_best_bid(self) -> Tuple[Optional[float], float]:
        if not self.bids:
            return None, 0.0
        best_p = max(self.bids.keys())
        return best_p, self.bids[best_p]

    def get_best_ask(self) -> Tuple[Optional[float], float]:
        if not self.asks:
            return None, 0.0
        best_p = min(self.asks.keys())
        return best_p, self.asks[best_p]

    def extract_microstructure_snapshot(
        self,
        decision_epoch: float,
        window_seconds: float = 900.0,
        max_staleness_seconds: float = 5.0
    ) -> L2MicrostructureSnapshot:
        """
        Extracts causal point-in-time microstructure features strictly <= decision_epoch.
        Fails closed with is_available=False if feed is uninitialized, desynchronized, or stale.
        """
        now_utc = datetime.fromtimestamp(decision_epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        data_age = max(0.0, decision_epoch - self.last_update_epoch)

        # 1. Synchronization Check
        if not self.is_synchronized:
            reason = f"L2_FEED_DESYNCHRONIZED: {self.desync_reason or 'UNKNOWN'}"
            fail_status = {k: "UNAVAILABLE_DESYNCHRONIZED" for k in [
                "spread_bps", "obi_5", "obi_10", "obi_25", "obi_50",
                "ofi_1m", "ofi_5m", "ofi_15m", "cvd_1m", "cvd_5m", "cvd_15m", "hf_realized_vol_15m"
            ]}
            return L2MicrostructureSnapshot(
                is_available=False,
                reason_code=reason,
                observation_time_utc=now_utc,
                observation_epoch=decision_epoch,
                best_bid=None,
                best_ask=None,
                mid_price=None,
                spread_bps=None,
                obi_5=None,
                obi_10=None,
                obi_25=None,
                ofi_value=None,
                cvd_value=None,
                trade_count_in_window=0,
                book_updates_in_window=0,
                data_age_seconds=data_age,
                is_feed_synchronized=False,
                feature_status=fail_status,
                valid_history_duration_seconds=0.0,
                is_window_warmed_up=False
            )

        # 2. Staleness Check
        if data_age > max_staleness_seconds:
            self.heartbeat_timeouts_count += 1
            reason = f"L2_DATA_STALE: age={data_age:.2f}s > threshold={max_staleness_seconds:.1f}s"
            fail_status = {k: "UNAVAILABLE_STALE" for k in [
                "spread_bps", "obi_5", "obi_10", "obi_25", "obi_50",
                "ofi_1m", "ofi_5m", "ofi_15m", "cvd_1m", "cvd_5m", "cvd_15m", "hf_realized_vol_15m"
            ]}
            return L2MicrostructureSnapshot(
                is_available=False,
                reason_code=reason,
                observation_time_utc=now_utc,
                observation_epoch=decision_epoch,
                best_bid=None,
                best_ask=None,
                mid_price=None,
                spread_bps=None,
                obi_5=None,
                obi_10=None,
                obi_25=None,
                ofi_value=None,
                cvd_value=None,
                trade_count_in_window=0,
                book_updates_in_window=0,
                data_age_seconds=data_age,
                is_feed_synchronized=False,
                feature_status=fail_status,
                valid_history_duration_seconds=0.0,
                is_window_warmed_up=False
            )

        best_b, best_b_sz = self.get_best_bid()
        best_a, best_a_sz = self.get_best_ask()

        if best_b is None or best_a is None or best_a <= best_b:
            fail_status = {k: "UNAVAILABLE_CROSSED_BOOK" for k in [
                "spread_bps", "obi_5", "obi_10", "obi_25", "obi_50",
                "ofi_1m", "ofi_5m", "ofi_15m", "cvd_1m", "cvd_5m", "cvd_15m", "hf_realized_vol_15m"
            ]}
            return L2MicrostructureSnapshot(
                is_available=False,
                reason_code="L2_EMPTY_OR_CROSSED_BOOK",
                observation_time_utc=now_utc,
                observation_epoch=decision_epoch,
                best_bid=best_b,
                best_ask=best_a,
                mid_price=None,
                spread_bps=None,
                obi_5=None,
                obi_10=None,
                obi_25=None,
                ofi_value=None,
                cvd_value=None,
                trade_count_in_window=0,
                book_updates_in_window=0,
                data_age_seconds=data_age,
                is_feed_synchronized=True,
                feature_status=fail_status,
                valid_history_duration_seconds=0.0,
                is_window_warmed_up=False
            )

        mid_p = 0.5 * (best_b + best_a)
        spread_bps = compute_spread_bps(best_b, best_a)

        # Static Book Imbalances across 5, 10, 25, 50 levels (Available immediately upon snapshot)
        obi_5 = compute_obi(self.bids, self.asks, depth=5)
        obi_10 = compute_obi(self.bids, self.asks, depth=10)
        obi_25 = compute_obi(self.bids, self.asks, depth=25)
        obi_50 = compute_obi(self.bids, self.asks, depth=50)

        # Tier volumes
        bid_depth_5 = compute_depth_volume(self.bids, depth=5, is_bid=True)
        ask_depth_5 = compute_depth_volume(self.asks, depth=5, is_bid=False)
        bid_depth_25 = compute_depth_volume(self.bids, depth=25, is_bid=True)
        ask_depth_25 = compute_depth_volume(self.asks, depth=25, is_bid=False)
        total_bid_depth = float(sum(self.bids.values()))
        total_ask_depth = float(sum(self.asks.values()))

        # Depth within 10 bps
        bid_depth_10bps = compute_depth_within_bps(self.bids, mid_price=mid_p, bps=10.0, is_bid=True)
        ask_depth_10bps = compute_depth_within_bps(self.asks, mid_price=mid_p, bps=10.0, is_bid=False)

        # Continuous Valid History Duration since last synchronization / reconnect
        sync_start = self.sync_epoch if self.sync_epoch is not None else (self.top_of_book_history[0]["epoch"] if self.top_of_book_history else decision_epoch)
        valid_history_duration = max(0.0, decision_epoch - sync_start)

        # Multi-Window Causal Events strictly <= decision_epoch
        w1m_start = decision_epoch - 60.0
        w5m_start = decision_epoch - 300.0
        w15m_start = decision_epoch - window_seconds

        events_15m = [e for e in self.top_of_book_history if w15m_start <= e["epoch"] <= decision_epoch]
        events_5m = [e for e in events_15m if e["epoch"] >= w5m_start]
        events_1m = [e for e in events_5m if e["epoch"] >= w1m_start]

        matches_15m = [m for m in self.match_history if w15m_start <= m["epoch"] <= decision_epoch]
        matches_5m = [m for m in matches_15m if m["epoch"] >= w5m_start]
        matches_1m = [m for m in matches_5m if m["epoch"] >= w1m_start]

        feature_status = {
            "spread_bps": "READY",
            "obi_5": "READY",
            "obi_10": "READY",
            "obi_25": "READY",
            "obi_50": "READY",
            "bid_depth_5": "READY",
            "ask_depth_5": "READY",
            "bid_depth_25": "READY",
            "ask_depth_25": "READY",
            "bid_depth_10bps": "READY",
            "ask_depth_10bps": "READY",
            "total_bid_depth": "READY",
            "total_ask_depth": "READY",
        }

        # 1-minute OFI & CVD
        if valid_history_duration < 60.0:
            ofi_1m = None
            feature_status["ofi_1m"] = f"UNAVAILABLE_WARMING_UP (elapsed={valid_history_duration:.1f}s < 60.0s)"
            feature_status["cvd_1m"] = f"UNAVAILABLE_WARMING_UP (elapsed={valid_history_duration:.1f}s < 60.0s)"
        elif len(events_1m) < 2:
            ofi_1m = None
            feature_status["ofi_1m"] = "UNAVAILABLE_INSUFFICIENT_EVENTS (< 2 updates in window)"
            feature_status["cvd_1m"] = "READY"
        else:
            ofi_1m = compute_ofi_from_top_of_book_events(events_1m)
            feature_status["ofi_1m"] = "READY"
            feature_status["cvd_1m"] = "READY"

        cvd_1m = compute_cvd_from_matches(matches_1m)

        # 5-minute OFI & CVD
        if valid_history_duration < 300.0:
            ofi_5m = None
            feature_status["ofi_5m"] = f"UNAVAILABLE_WARMING_UP (elapsed={valid_history_duration:.1f}s < 300.0s)"
            feature_status["cvd_5m"] = f"UNAVAILABLE_WARMING_UP (elapsed={valid_history_duration:.1f}s < 300.0s)"
        elif len(events_5m) < 2:
            ofi_5m = None
            feature_status["ofi_5m"] = "UNAVAILABLE_INSUFFICIENT_EVENTS (< 2 updates in window)"
            feature_status["cvd_5m"] = "READY"
        else:
            ofi_5m = compute_ofi_from_top_of_book_events(events_5m)
            feature_status["ofi_5m"] = "READY"
            feature_status["cvd_5m"] = "READY"

        cvd_5m = compute_cvd_from_matches(matches_5m)

        # 15-minute OFI & CVD
        if valid_history_duration < 900.0:
            ofi_15m = None
            feature_status["ofi_15m"] = f"UNAVAILABLE_WARMING_UP (elapsed={valid_history_duration:.1f}s < 900.0s)"
            feature_status["cvd_15m"] = f"UNAVAILABLE_WARMING_UP (elapsed={valid_history_duration:.1f}s < 900.0s)"
            feature_status["hf_realized_vol_15m"] = f"UNAVAILABLE_WARMING_UP (elapsed={valid_history_duration:.1f}s < 900.0s)"
        elif len(events_15m) < 2:
            ofi_15m = None
            feature_status["ofi_15m"] = "UNAVAILABLE_INSUFFICIENT_EVENTS (< 2 updates in window)"
            feature_status["cvd_15m"] = "READY"
            feature_status["hf_realized_vol_15m"] = "READY"
        else:
            ofi_15m = compute_ofi_from_top_of_book_events(events_15m)
            feature_status["ofi_15m"] = "READY"
            feature_status["cvd_15m"] = "READY"
            feature_status["hf_realized_vol_15m"] = "READY"

        cvd_15m = compute_cvd_from_matches(matches_15m)

        # Primary ofi_value and cvd_value corresponding to window_seconds
        if window_seconds == 60.0:
            ofi_val = ofi_1m
            cvd_val = cvd_1m
        elif window_seconds == 300.0:
            ofi_val = ofi_5m
            cvd_val = cvd_5m
        else:
            ofi_val = ofi_15m
            cvd_val = cvd_15m

        # Volatility & Liquidity Proxies
        hf_vol_15m = compute_hf_realized_vol(events_15m) if valid_history_duration >= 900.0 else None
        kyles_lambda = compute_kyles_lambda_proxy(events_15m, ofi_15m) if ofi_15m is not None else None
        amihud_proxy = compute_amihud_proxy(events_15m, matches_15m)

        is_window_warmed_up = valid_history_duration >= window_seconds

        # Event range
        first_ep = events_15m[0]["epoch"] if events_15m else decision_epoch
        last_ep = events_15m[-1]["epoch"] if events_15m else decision_epoch
        consumed = len(events_15m) + len(matches_15m)

        return L2MicrostructureSnapshot(
            is_available=True,
            reason_code=None,
            observation_time_utc=now_utc,
            observation_epoch=decision_epoch,
            best_bid=best_b,
            best_ask=best_a,
            mid_price=mid_p,
            spread_bps=spread_bps,
            obi_5=obi_5,
            obi_10=obi_10,
            obi_25=obi_25,
            ofi_value=ofi_val,
            cvd_value=cvd_val,
            trade_count_in_window=len(matches_15m),
            book_updates_in_window=len(events_15m),
            data_age_seconds=data_age,
            is_feed_synchronized=True,
            # Extended fields
            obi_50=obi_50,
            ofi_1m=ofi_1m,
            ofi_5m=ofi_5m,
            ofi_15m=ofi_15m,
            cvd_1m=cvd_1m,
            cvd_5m=cvd_5m,
            cvd_15m=cvd_15m,
            bid_depth_5=bid_depth_5,
            ask_depth_5=ask_depth_5,
            bid_depth_25=bid_depth_25,
            ask_depth_25=ask_depth_25,
            bid_depth_10bps=bid_depth_10bps,
            ask_depth_10bps=ask_depth_10bps,
            total_bid_depth=total_bid_depth,
            total_ask_depth=total_ask_depth,
            hf_realized_vol_15m=hf_vol_15m,
            kyles_lambda_proxy=kyles_lambda,
            amihud_illiquidity_proxy=amihud_proxy,
            first_event_epoch=first_ep,
            last_event_epoch=last_ep,
            event_count_consumed=consumed,
            schema_version="v32.38.causal_l2",
            feature_status=feature_status,
            valid_history_duration_seconds=valid_history_duration,
            is_window_warmed_up=is_window_warmed_up
        )

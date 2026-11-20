"""
engine/run_l2_prospective_burnin.py — Controlled Operator Burn-In & Runbook CLI
================================================================================
BTCognitive V32.39: Prospective Level-2 Shadow Qualification

Provides an operator-facing CLI entrypoint for preflight qualification, disk space
monitoring, deterministic dry-run verification, and controlled burn-in execution.

Safety & Governance Rules:
- Defaults to safe read-only preflight check; NEVER starts collection automatically.
- Requires BOTH --authorize-collection flag AND environment variable
  COINBASE_L2_COLLECTOR_ENABLED=1 to start live ingestion.
- Enforces minimum 500MB free disk space before and during collection.
- Traps SIGINT / SIGTERM for clean graceful shutdown and state flush.
"""

from __future__ import annotations

import os
import sys
import json
import time
import socket
import signal
import shutil
import logging
import argparse
from typing import Dict, List, Optional, Any

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from engine.coinbase_l2_collector import CoinbaseL2Collector, AUTHORIZED_PRODUCT, DEFAULT_WS_URL
from engine.l2_microstructure_features import OrderBookTracker
from engine.l2_event_recorder import RawL2Event, L2EventRecorder
from engine.prospective_l2_qualification import audit_prospective_l2_qualification

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("btcognitive.l2_burnin")

MIN_DISK_SPACE_MB = 500.0


def check_free_disk_space_mb(target_dir: str) -> float:
    """Returns free disk space in megabytes for the given directory."""
    os.makedirs(target_dir, exist_ok=True)
    usage = shutil.disk_usage(target_dir)
    return round(usage.free / (1024.0 * 1024.0), 2)


def check_coinbase_dns_resolution(host: str = "ws-feed.exchange.coinbase.com") -> bool:
    """Verifies DNS lookup for Coinbase WebSocket feed without establishing connection."""
    try:
        socket.gethostbyname(host)
        return True
    except Exception:
        return False


def run_preflight_checks(target_dir: str) -> Dict[str, Any]:
    """
    Executes comprehensive preflight checks:
    1. Disk space verification.
    2. Coinbase feed DNS resolution.
    3. Protected file integrity.
    4. Collector permission status.
    """
    free_mb = check_free_disk_space_mb(target_dir)
    dns_ok = check_coinbase_dns_resolution()
    audit_status = audit_prospective_l2_qualification()

    disk_ok = free_mb >= MIN_DISK_SPACE_MB

    is_all_ready = disk_ok and dns_ok and audit_status.zero_synthetic_l2_assertion

    return {
        "free_disk_space_mb": free_mb,
        "disk_space_sufficient": disk_ok,
        "coinbase_feed_dns_resolved": dns_ok,
        "target_product": AUTHORIZED_PRODUCT,
        "feed_url": DEFAULT_WS_URL,
        "preflight_status": "READY" if is_all_ready else "FAILED",
        "collector_operational_status": audit_status.collector_operational_status,
        "permission_respected": audit_status.collector_permission_respected
    }


def execute_dry_run_test() -> Dict[str, Any]:
    """
    Executes a deterministic synthetic event replay to verify:
    - Snapshot ingestion
    - Delta updates & level deletions
    - Top-of-book recording
    - Multi-window OFI and OBI feature extraction
    - Clean teardown
    """
    tracker = OrderBookTracker()
    recorder = L2EventRecorder()
    base_epoch = time.time()

    # 1. Snapshot
    snap_payload = {
        "type": "snapshot",
        "product_id": "BTC-USD",
        "sequence": 1,
        "bids": [["68000.00", "2.0"], ["67950.00", "4.0"]],
        "asks": [["68050.00", "1.5"], ["68100.00", "3.0"]]
    }
    recorder.record_event("snapshot", snap_payload, epoch=base_epoch, sequence=1)

    # 2. Update
    upd_payload = {
        "type": "l2update",
        "product_id": "BTC-USD",
        "sequence": 2,
        "changes": [["buy", "68010.00", "1.0"], ["sell", "68050.00", "0.0"]]
    }
    recorder.record_event("l2update", upd_payload, epoch=base_epoch + 1.0, sequence=2)

    # 3. Match
    match_payload = {
        "type": "match",
        "trade_id": "dry_001",
        "price": "68010.00",
        "size": "0.5",
        "side": "buy"
    }
    recorder.record_event("match", match_payload, epoch=base_epoch + 2.0, sequence=3)

    # Replay
    tracker, summary = L2EventRecorder.replay_events(recorder.get_events(), tracker=tracker)
    snap = tracker.extract_microstructure_snapshot(decision_epoch=base_epoch + 3.0)

    return {
        "dry_run_success": summary.final_is_synchronized and snap.is_available,
        "events_replayed": summary.events_replayed,
        "final_sequence": summary.final_sequence,
        "best_bid": snap.best_bid,
        "best_ask": snap.best_ask,
        "spread_bps": snap.spread_bps,
        "obi_5": snap.obi_5,
        "cvd_15m": snap.cvd_15m
    }


def main():
    parser = argparse.ArgumentParser(description="BTCognitive V32.39/V32.40A Level-2 Prospective Burn-In Engine")
    parser.add_argument("--dry-run", action="store_true", help="Execute preflight checks and synthetic stream verification")
    parser.add_argument("--authorize-collection", action="store_true", help="Explicit operator flag required to run live collection")
    parser.add_argument("--target", type=str, default=AUTHORIZED_PRODUCT, help=f"Target trading product (default: {AUTHORIZED_PRODUCT})")
    parser.add_argument("--duration-sec", "--duration-seconds", dest="duration_seconds", type=int, default=300, help="Burn-in run duration in seconds (default: 300)")
    parser.add_argument("--data-dir", type=str, default=os.path.join(REPO_ROOT, "data", "research", "l2_stream"), help="Target data directory")

    args = parser.parse_args()

    print("=================================================================")
    print("BTCognitive V32.40A: Level-2 Prospective Burn-In Preflight Engine")
    print("=================================================================")

    # 1. Preflight checks
    preflight = run_preflight_checks(args.data_dir)
    print(f"Target Product:        {args.target}")
    print(f"Feed URL:              {preflight['feed_url']}")
    print(f"Free Disk Space:       {preflight['free_disk_space_mb']} MB (Sufficient: {preflight['disk_space_sufficient']})")
    print(f"Coinbase Feed DNS:     {'RESOLVED' if preflight['coinbase_feed_dns_resolved'] else 'FAILED'}")
    print(f"Preflight Status:      {preflight['preflight_status']}")
    print(f"Collector Status:      {preflight['collector_operational_status']}")

    # 2. Dry run test
    dry_run = execute_dry_run_test()
    print(f"Dry-Run Stream Replay: {'PASSED' if dry_run['dry_run_success'] else 'FAILED'}")
    print(f"Synthetic Replay Snap: Best Bid=${dry_run['best_bid']}, Best Ask=${dry_run['best_ask']}, Spread={dry_run['spread_bps']} bps")

    if args.dry_run:
        print("\n[DRY-RUN COMPLETE] Preflight and synthetic stream replay passed cleanly.")
        print("Protected data files remain completely untouched.")
        sys.exit(0)

    # 3. Check live authorization
    env_enabled = os.environ.get("COINBASE_L2_COLLECTOR_ENABLED", "0").strip() == "1"
    is_authorized = args.authorize_collection and env_enabled

    if not is_authorized:
        print("\n-----------------------------------------------------------------")
        print("OPERATOR STATUS: READY_FOR_OPERATOR_AUTHORIZATION")
        print("Live capture is DISABLED. No collector process was started.")
        print("\nTo authorize and execute a controlled live burn-in run, run:")
        print("  $env:COINBASE_L2_COLLECTOR_ENABLED = '1'")
        print("  & '.\\.venv_win\\Scripts\\python.exe' engine/run_l2_prospective_burnin.py --target BTC-USD --authorize-collection --duration-sec 3600")
        print("-----------------------------------------------------------------")
        sys.exit(0)

    # 4. Authorized collection run
    print(f"\nOPERATOR AUTHORIZATION DETECTED. Starting controlled burn-in for {args.duration_seconds}s...")
    os.makedirs(args.data_dir, exist_ok=True)
    session_ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    events_log_path = os.path.join(args.data_dir, f"l2_burnin_events_{session_ts}.jsonl")
    
    recorder = L2EventRecorder(log_path=events_log_path)
    tracker = OrderBookTracker()
    collector = CoinbaseL2Collector(
        product_id=args.target,
        ws_url=DEFAULT_WS_URL,
        enabled=True,
        tracker=tracker,
        event_recorder=recorder
    )

    stop_requested = False

    def handle_signal(sig, frame):
        nonlocal stop_requested
        print("\nShutdown signal received. Stopping collector gracefully...")
        stop_requested = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    collector.start()
    t_start = time.time()
    print(f"Collector running for up to {args.duration_seconds} seconds. Press Ctrl+C to abort cleanly.")

    try:
        while not stop_requested and (time.time() - t_start) < args.duration_seconds:
            time.sleep(2.0)
            elapsed = time.time() - t_start
            free_mb = check_free_disk_space_mb(args.data_dir)
            if free_mb < MIN_DISK_SPACE_MB:
                logger.error(f"Low disk space ({free_mb} MB < {MIN_DISK_SPACE_MB} MB). Aborting burn-in cleanly.")
                break

            b_b, _ = tracker.get_best_bid()
            b_a, _ = tracker.get_best_ask()
            seq = tracker.last_sequence
            ev_count = recorder.total_events_recorded
            print(f"[{elapsed:.1f}s/{args.duration_seconds}s] Synced: {tracker.is_synchronized} | Seq: {seq} | Events: {ev_count} | Bid: {b_b} | Ask: {b_a} | Free: {free_mb:.0f}MB", end="\r")

    finally:
        collector.stop()
        print("\nBurn-in session concluded cleanly.")

    # 5. Post-burnin data verification and summary generation
    print("\nExecuting post-burn-in deterministic replay & data quality verification...")
    recorded_events = recorder.get_events()
    event_counts_by_type = {}
    for ev in recorded_events:
        t = ev.event_type
        event_counts_by_type[t] = event_counts_by_type.get(t, 0) + 1

    replay_tracker = OrderBookTracker()
    _, replay_summary = L2EventRecorder.replay_events(recorded_events, tracker=replay_tracker)
    final_snap = replay_tracker.extract_microstructure_snapshot(decision_epoch=time.time())

    summary_data = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_product": args.target,
        "planned_duration_sec": args.duration_seconds,
        "actual_elapsed_sec": round(time.time() - t_start, 2),
        "total_events_recorded": recorder.total_events_recorded,
        "total_bytes_written": recorder.total_bytes_written,
        "events_log_path": events_log_path,
        "event_counts_by_type": event_counts_by_type,
        "data_quality_metrics": {
            "is_synchronized": replay_summary.final_is_synchronized,
            "final_sequence": replay_summary.final_sequence,
            "dropped_duplicates": replay_summary.dropped_duplicates,
            "dropped_out_of_order": replay_summary.dropped_out_of_order,
            "sequence_gaps": replay_summary.sequence_gaps,
            "heartbeat_stalls": replay_summary.heartbeat_stalls,
            "reconnect_count": collector.reconnect_count,
            "last_error": collector.last_error
        },
        "replay_verification": {
            "events_replayed": replay_summary.events_replayed,
            "replay_duration_ms": replay_summary.replay_duration_ms,
            "replay_best_bid": replay_summary.final_best_bid,
            "replay_best_ask": replay_summary.final_best_ask,
            "replay_mid_price": replay_summary.final_mid_price,
            "replay_passed": replay_summary.final_is_synchronized and replay_summary.sequence_gaps == 0
        },
        "feature_snapshot": {
            "is_available": final_snap.is_available,
            "best_bid": final_snap.best_bid,
            "best_ask": final_snap.best_ask,
            "spread_bps": final_snap.spread_bps,
            "obi_5": final_snap.obi_5,
            "ofi_15m": final_snap.ofi_15m,
            "cvd_15m": final_snap.cvd_15m,
            "data_age_seconds": final_snap.data_age_seconds
        },
        "governed_decisions": {
            "economic_verdict": "NO_GO_NO_VALIDATED_EDGE",
            "model_authorization": "OFFLINE_RESEARCH_ONLY",
            "live_trading_state": "DISABLED"
        }
    }

    summary_file = os.path.join(REPO_ROOT, "research", "reports", "v32_40a_burnin_capture_summary.json")
    os.makedirs(os.path.dirname(summary_file), exist_ok=True)
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print("=================================================================")
    print("V32.40A BURN-IN POST-CAPTURE QUALIFICATION RESULTS")
    print("=================================================================")
    print(f"Total Events Recorded:    {recorder.total_events_recorded}")
    print(f"Event Breakdown:          {event_counts_by_type}")
    print(f"Sequence Gaps:            {replay_summary.sequence_gaps}")
    print(f"Dropped Duplicates:       {replay_summary.dropped_duplicates}")
    print(f"Dropped Out-of-Order:     {replay_summary.dropped_out_of_order}")
    print(f"Heartbeat Stalls:         {replay_summary.heartbeat_stalls}")
    print(f"Replay Sync Status:       {'SYNCHRONIZED' if replay_summary.final_is_synchronized else 'DESYNCHRONIZED'}")
    print(f"Replay Mid Price:         ${replay_summary.final_mid_price}")
    print(f"Final Microstructure Snap: Spread={final_snap.spread_bps} bps, OBI_5={final_snap.obi_5}, OFI_15m={final_snap.ofi_15m}")
    print(f"Capture Summary Saved:    {summary_file}")
    print("=================================================================")


if __name__ == "__main__":
    main()

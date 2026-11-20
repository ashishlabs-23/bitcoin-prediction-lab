"""
engine/shadow_feed_runner.py — Controlled Read-Only Shadow Feed Ingestion & Evaluation Runner
============================================================================================
BTCognitive V30.4: Operational, read-only prospective data-collection system for
HTF_RANGE_EXPANSION_BREAKOUT.

Operational & Non-Execution Guarantees:
1. Strict Non-Execution: Zero live order routing, zero broker credentials, zero execution endpoints.
2. Read-Only Ingestion: Connects strictly to public read-only exchange feeds (Coinbase Exchange candles).
3. Closed-Candle Boundary: Drops the currently forming candle; only strictly closed bars are ingested.
4. Causal Evaluation:
   - Signals evaluated on completed 4h bar close (derived from 1h closed bars).
   - Fills simulated at next bar's open (no lookahead).
   - In-position gating: Exactly one candidate active at a time; no overlapping positions.
5. Durable, Cross-Process Persistence:
   - Writes exclusively to `data/prospective_shadow_v1.jsonl`.
   - Never touches or modifies `data/prospective_entry_ledger.jsonl`.
   - Cross-process FileLock ensures concurrency safety.
6. Observability: Emits detailed operational telemetry to `data/prospective_shadow_status.json`.
"""

from __future__ import annotations

import os
import sys
import time
import json
import logging
import argparse
import signal
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple

import pandas as pd
import numpy as np
from filelock import FileLock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engine.prospective_shadow_collector import (
    ProspectiveShadowLedger,
    HTFShadowCollector,
    ShadowCandidateRecord,
    ShadowOutcomeRecord,
    STRATEGY_ID,
    STRATEGY_SPEC_HASH,
    PRIMARY_INSTRUMENT,
    PRIMARY_VENUE,
    PRIMARY_COST_SCENARIO,
    DEFAULT_SHADOW_LEDGER_PATH,
)

logger = logging.getLogger("btcognitive.shadow_feed_runner")

DEFAULT_STATUS_PATH = os.path.join(REPO_ROOT, "data", "prospective_shadow_status.json")
DEFAULT_OHLCV_PATH = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
RUNNER_LOCK_PATH = os.path.join(REPO_ROOT, "data", ".prospective_shadow_runner.lock")
COINBASE_CANDLES_URL = "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600"
USER_AGENT = "BTCognitive-ShadowFeed/1.0"
STALE_FEED_THRESHOLD_SECONDS = 7200  # 2 hours — warn if latest candle is older


def _pid_is_running(pid: int) -> bool:
    """Portable check: returns True if *pid* names a running process."""
    if pid == os.getpid():
        return True
    try:
        import psutil
        return bool(psutil.pid_exists(pid))
    except ImportError:
        pass
    if sys.platform == "win32":
        try:
            import ctypes
            SYNCHRONIZE = 0x00100000
            handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return True
    else:
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except Exception:
            return True


class ShadowFeedRunner:
    """
    Controlled, read-only shadow runner for forward prospective candle ingestion
    and deterministic candidate/outcome lifecycle evaluation.
    """

    def __init__(
        self,
        ledger: Optional[ProspectiveShadowLedger] = None,
        ohlcv_path: Optional[str] = None,
        status_path: Optional[str] = None,
        lock_path: Optional[str] = None,
        timeout_seconds: int = 10,
        max_retries: int = 3
    ):
        self.ledger = ledger or ProspectiveShadowLedger()
        self.collector = HTFShadowCollector(ledger=self.ledger)
        self.ohlcv_path = ohlcv_path or DEFAULT_OHLCV_PATH
        self.status_path = status_path or DEFAULT_STATUS_PATH
        self.lock_path = lock_path or RUNNER_LOCK_PATH
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._shutdown_requested = False
        os.makedirs(os.path.dirname(self.status_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.lock_path), exist_ok=True)

    # ── Single-Instance Lock ─────────────────────────────────────────────
    def is_locked(self) -> bool:
        """Returns True if lock file is held by an active running process."""
        if not os.path.exists(self.lock_path):
            return False
        try:
            with open(self.lock_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            pid = data.get("pid")
            if pid:
                return _pid_is_running(int(pid))
        except Exception:
            pass
        return False

    def acquire_lock(self) -> bool:
        """Acquires single-instance lock. Returns False if already held by active process."""
        if os.path.exists(self.lock_path):
            try:
                with open(self.lock_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                pid = data.get("pid")
                if pid and _pid_is_running(int(pid)):
                    logger.warning(f"Shadow runner lock held by PID {pid}. Aborting.")
                    return False
            except Exception:
                pass
            try:
                os.remove(self.lock_path)
            except OSError:
                pass

        lock_data = {
            "pid": os.getpid(),
            "acquired_utc": datetime.now(timezone.utc).isoformat(),
            "runner": "ShadowFeedRunner-V30.5"
        }
        with open(self.lock_path, "w", encoding="utf-8") as f:
            json.dump(lock_data, f)
            f.flush()
            os.fsync(f.fileno())
        logger.info(f"Shadow runner lock acquired (PID {os.getpid()}).")
        return True

    def release_lock(self) -> None:
        """Releases the single-instance lock if held by this process."""
        if os.path.exists(self.lock_path):
            try:
                with open(self.lock_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("pid") == os.getpid():
                    os.remove(self.lock_path)
                    logger.info("Shadow runner lock released.")
            except Exception:
                pass

    # ── Feed Freshness Check ─────────────────────────────────────────────
    def check_freshness(self) -> Dict[str, Any]:
        """
        Checks staleness of the latest closed candle in local storage.
        Returns a diagnostic dict with freshness age and warning status.
        """
        result: Dict[str, Any] = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "ohlcv_path": self.ohlcv_path,
            "exists": False,
            "latest_candle_utc": None,
            "age_seconds": None,
            "is_stale": None,
            "stale_threshold_seconds": STALE_FEED_THRESHOLD_SECONDS,
        }
        if not os.path.exists(self.ohlcv_path):
            result["notice"] = "OHLCV storage file does not exist."
            return result

        try:
            df = pd.read_parquet(self.ohlcv_path)
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            latest = df["timestamp"].max()
            now = pd.Timestamp.now(tz="UTC")
            age = (now - latest).total_seconds()
            result["exists"] = True
            result["latest_candle_utc"] = latest.isoformat()
            result["age_seconds"] = round(age, 1)
            result["is_stale"] = age > STALE_FEED_THRESHOLD_SECONDS
            result["total_candles"] = len(df)
        except Exception as e:
            result["notice"] = f"Error reading OHLCV file: {e}"
        return result

    def fetch_recent_closed_candles(self) -> Dict[str, Any]:
        """
        Fetches recent hourly BTC-USD spot candles from Coinbase public REST API.
        Enforces closed-candle boundary, drops currently forming candle, validates OHLC.
        """
        result: Dict[str, Any] = {
            "success": False,
            "provider": "coinbase",
            "url": COINBASE_CANDLES_URL,
            "receipt_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "raw_candles_fetched": 0,
            "valid_closed_candles": 0,
            "latest_closed_timestamp_utc": None,
            "df_closed": None,
            "notice": None
        }

        headers = {"User-Agent": USER_AGENT}
        data = None
        last_err = None

        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(COINBASE_CANDLES_URL, headers=headers)
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    payload_bytes = resp.read()
                    data = json.loads(payload_bytes.decode("utf-8"))
                break
            except Exception as e:
                last_err = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)

        if data is None:
            result["notice"] = f"Coinbase feed unreachable after {self.max_retries} attempts: {last_err}"
            return result

        if not isinstance(data, list) or len(data) == 0:
            result["notice"] = "Coinbase returned empty or invalid response payload."
            return result

        result["raw_candles_fetched"] = len(data)

        # Candle schema: [time (epoch seconds), low, high, open, close, volume]
        now_epoch = int(time.time())
        current_hour_epoch = (now_epoch // 3600) * 3600

        valid_rows = []
        for item in data:
            if not isinstance(item, (list, tuple)) or len(item) < 6:
                continue
            bar_time, low, high, open_p, close_p, vol = item[:6]
            # Exclude current in-progress candle
            if bar_time >= current_hour_epoch:
                continue
            # Validate mathematical OHLC invariants
            if low > min(open_p, close_p) or high < max(open_p, close_p) or vol < 0 or low <= 0:
                continue

            valid_rows.append({
                "timestamp": pd.to_datetime(bar_time, unit="s", utc=True),
                "open": float(open_p),
                "high": float(high),
                "low": float(low),
                "close": float(close_p),
                "volume": float(vol),
                "available_time": pd.to_datetime(bar_time + 3600, unit="s", utc=True),
            })

        if not valid_rows:
            result["notice"] = "No valid completed closed candles found in response."
            return result

        df_closed = pd.DataFrame(valid_rows).drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
        result["valid_closed_candles"] = len(df_closed)
        result["latest_closed_timestamp_utc"] = df_closed["timestamp"].max().isoformat()
        result["df_closed"] = df_closed
        result["success"] = True
        return result

    def sync_candles_to_storage(self, df_new: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """
        Merges new closed candles into historical storage with atomic write and deduplication.
        Returns the combined DataFrame and count of new candles added.
        """
        if os.path.exists(self.ohlcv_path):
            df_existing = pd.read_parquet(self.ohlcv_path)
            if "timestamp" in df_existing.columns:
                df_existing["timestamp"] = pd.to_datetime(df_existing["timestamp"], utc=True)
            else:
                df_existing = df_existing.reset_index()
                df_existing["timestamp"] = pd.to_datetime(df_existing["timestamp"], utc=True)

            max_existing_ts = df_existing["timestamp"].max()
            new_bars = df_new[df_new["timestamp"] > max_existing_ts]
            if not new_bars.empty:
                df_combined = pd.concat([df_existing, new_bars], ignore_index=True)
                df_combined.drop_duplicates(subset=["timestamp"], inplace=True)
                df_combined.sort_values("timestamp", inplace=True)

                # Atomic write via .tmp
                temp_file = self.ohlcv_path + ".tmp"
                df_combined.to_parquet(temp_file, index=False)
                os.replace(temp_file, self.ohlcv_path)
                return df_combined, len(new_bars)
            return df_existing, 0
        else:
            os.makedirs(os.path.dirname(self.ohlcv_path), exist_ok=True)
            temp_file = self.ohlcv_path + ".tmp"
            df_new.to_parquet(temp_file, index=False)
            os.replace(temp_file, self.ohlcv_path)
            return df_new, len(df_new)

    def run_evaluation_cycle(
        self,
        sync_live: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Executes a single end-to-end evaluation cycle:
        1. Ingests fresh closed candles if sync_live is True.
        2. Derives point-in-time 4h candles.
        3. Resolves any active open candidate if horizon or stop is touched.
        4. If position is flat, checks latest closed 4h candle for breakout signal.
        5. Writes records to data/prospective_shadow_v1.jsonl (unless dry_run).
        6. Updates telemetry in data/prospective_shadow_status.json.
        """
        cycle_start_utc = datetime.now(timezone.utc).isoformat()
        cycle_summary: Dict[str, Any] = {
            "cycle_start_utc": cycle_start_utc,
            "sync_live": sync_live,
            "dry_run": dry_run,
            "feed_status": "UNKNOWN",
            "candles_fetched": 0,
            "candles_added_to_storage": 0,
            "latest_closed_1h_candle": None,
            "latest_closed_4h_candle": None,
            "active_candidate_before_cycle": None,
            "active_candidate_after_cycle": None,
            "resolved_outcome": None,
            "emitted_candidate": None,
            "execution_authorization": "DISABLED — ANALYSIS ONLY",
            "governance_status": "OFFLINE_RESEARCH_ONLY"
        }

        # 1. Sync live candles if requested
        df_1h = None
        if sync_live:
            fetch_res = self.fetch_recent_closed_candles()
            if fetch_res["success"] and fetch_res["df_closed"] is not None:
                df_1h, added = self.sync_candles_to_storage(fetch_res["df_closed"])
                cycle_summary["feed_status"] = "HEALTHY"
                cycle_summary["candles_fetched"] = fetch_res["valid_closed_candles"]
                cycle_summary["candles_added_to_storage"] = added
                cycle_summary["latest_closed_1h_candle"] = fetch_res["latest_closed_timestamp_utc"]
            else:
                cycle_summary["feed_status"] = "OFFLINE"
                cycle_summary["notice"] = fetch_res.get("notice")
                if os.path.exists(self.ohlcv_path):
                    df_1h = pd.read_parquet(self.ohlcv_path)
                    df_1h["timestamp"] = pd.to_datetime(df_1h["timestamp"], utc=True)
        else:
            cycle_summary["feed_status"] = "OFFLINE_LOCAL_ONLY"
            if os.path.exists(self.ohlcv_path):
                df_1h = pd.read_parquet(self.ohlcv_path)
                df_1h["timestamp"] = pd.to_datetime(df_1h["timestamp"], utc=True)

        if df_1h is None or df_1h.empty:
            cycle_summary["notice"] = "No market data available for evaluation."
            self._write_status(cycle_summary)
            return cycle_summary

        # 2. Resample to 4h
        df_4h = self.collector.resample_1h_to_4h(df_1h)
        if len(df_4h) < 25:
            cycle_summary["notice"] = "Insufficient 4h candles (<25) for 20-bar lookback."
            self._write_status(cycle_summary)
            return cycle_summary

        latest_4h = df_4h.iloc[-1]
        cycle_summary["latest_closed_4h_candle"] = pd.to_datetime(latest_4h["timestamp"], utc=True).isoformat()

        # 3. Check for active unresolved candidate
        active_cand = self.collector.get_active_unresolved_candidate()
        cycle_summary["active_candidate_before_cycle"] = active_cand.get("candidate_id") if active_cand else None

        if active_cand:
            # Reconstruct candidate dataclass for resolution evaluation
            cand_obj = ShadowCandidateRecord(**active_cand)
            cand_entry_ts = pd.to_datetime(cand_obj.decision_timestamp_utc, utc=True)
            future_bars = df_4h[df_4h["timestamp"] > cand_entry_ts]

            outcome = self.collector.resolve_candidate_outcome(cand_obj, future_bars)
            if outcome:
                cycle_summary["resolved_outcome"] = outcome.to_dict()
                if not dry_run:
                    self.ledger.append_outcome(outcome)
                    logger.info(f"Resolved outcome for {cand_obj.candidate_id}: {outcome.exit_reason}")
                active_cand = None  # Position is now closed
        else:
            # 4. If flat, check latest completed 4h candle for breakout signal
            # We evaluate df_4h.iloc[-2] as cur_bar and df_4h.iloc[-1]['open'] as nxt_bar_open
            # to guarantee that the signal bar is 100% closed and next bar's open exists.
            signal_bar = df_4h.iloc[-2]
            next_bar = df_4h.iloc[-1]
            nxt_open = float(next_bar["open"])
            nxt_ts = pd.to_datetime(next_bar["timestamp"], utc=True).isoformat()

            new_cand = self.collector.evaluate_bar_for_candidate(
                cur_4h_bar=signal_bar,
                nxt_bar_open=nxt_open,
                nxt_bar_timestamp_utc=nxt_ts,
                allow_overlapping=False
            )

            if new_cand:
                cycle_summary["emitted_candidate"] = new_cand.to_dict()
                if not dry_run:
                    self.ledger.append_candidate(new_cand)
                    logger.info(f"Emitted new shadow candidate: {new_cand.candidate_id}")
                active_cand = new_cand.to_dict()

        cycle_summary["active_candidate_after_cycle"] = active_cand.get("candidate_id") if active_cand else None
        self._write_status(cycle_summary)
        return cycle_summary

    def _write_status(self, cycle_summary: Dict[str, Any]) -> None:
        """Writes thread and cross-process safe operational telemetry."""
        ledger_summary = self.ledger.get_ledger_summary()
        status_payload = {
            "runner_version": "V30.5-SHADOW-FEED-RUNNER",
            "last_cycle_timestamp_utc": cycle_summary.get("cycle_start_utc"),
            "feed_status": cycle_summary.get("feed_status"),
            "latest_closed_1h_candle": cycle_summary.get("latest_closed_1h_candle"),
            "latest_closed_4h_candle": cycle_summary.get("latest_closed_4h_candle"),
            "active_unresolved_candidate_id": cycle_summary.get("active_candidate_after_cycle"),
            "ledger_summary": ledger_summary,
            "last_cycle_details": {
                "candles_fetched": cycle_summary.get("candles_fetched"),
                "candles_added_to_storage": cycle_summary.get("candles_added_to_storage"),
                "resolved_outcome": cycle_summary.get("resolved_outcome"),
                "emitted_candidate": cycle_summary.get("emitted_candidate"),
                "notice": cycle_summary.get("notice")
            },
            "live_trading_authorization": "DISABLED — ANALYSIS ONLY",
            "governance_status": "OFFLINE_RESEARCH_ONLY"
        }

        temp_status = self.status_path + ".tmp"
        with open(temp_status, "w", encoding="utf-8") as f:
            json.dump(status_payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_status, self.status_path)


def main():
    parser = argparse.ArgumentParser(
        description="BTCognitive V30.5 Shadow Feed Runner -- Prospective Shadow Collection CLI",
        epilog="""
USAGE EXAMPLES:
  Single cycle:    python -m engine.shadow_feed_runner --once
  Loop mode:       python -m engine.shadow_feed_runner --loop --interval 3600
  Status check:    python -m engine.shadow_feed_runner --status
  Freshness check: python -m engine.shadow_feed_runner --check-freshness
  Dry run:         python -m engine.shadow_feed_runner --once --dry-run
  Stop loop:       Press Ctrl+C (graceful shutdown after current cycle)
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--once", action="store_true", help="Execute single evaluation cycle and exit")
    parser.add_argument("--loop", action="store_true", help="Run continuously with single-instance lock and graceful SIGINT")
    parser.add_argument("--interval", type=int, default=3600, help="Seconds between cycles in --loop mode (default: 3600)")
    parser.add_argument("--dry-run", action="store_true", help="Execute evaluation without appending to ledger")
    parser.add_argument("--no-sync", action="store_true", help="Skip live feed sync; use local storage only")
    parser.add_argument("--status", action="store_true", help="Display current operational status and exit")
    parser.add_argument("--check-freshness", action="store_true", help="Check feed data freshness and exit")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    runner = ShadowFeedRunner()

    # ── Status command ────────────────────────────────────────────────────
    if args.status:
        print("=== Shadow Feed Runner Status ===")
        # Runner lock status
        if runner.is_locked():
            try:
                with open(runner.lock_path, "r", encoding="utf-8") as f:
                    lock_data = json.load(f)
                print(f"Runner Lock: ACTIVE (PID {lock_data.get('pid')}, since {lock_data.get('acquired_utc')})")
            except Exception:
                print("Runner Lock: ACTIVE (details unreadable)")
        else:
            print("Runner Lock: INACTIVE (no loop running)")

        # Status telemetry
        if os.path.exists(runner.status_path):
            with open(runner.status_path, "r", encoding="utf-8") as f:
                print(f.read())
        else:
            print(f"No status telemetry at {runner.status_path}")
        return

    # ── Freshness check command ───────────────────────────────────────────
    if args.check_freshness:
        freshness = runner.check_freshness()
        print("=== Feed Freshness Check ===")
        print(json.dumps(freshness, indent=2, default=str))
        if freshness.get("is_stale"):
            print(f"\n[WARNING] Feed is STALE ({freshness['age_seconds']:.0f}s > {STALE_FEED_THRESHOLD_SECONDS}s threshold)")
        elif freshness.get("exists"):
            print(f"\n[OK] Feed is FRESH ({freshness['age_seconds']:.0f}s old)")
        return

    sync_live = not args.no_sync

    # ── Single-shot mode ──────────────────────────────────────────────────
    if args.once or not args.loop:
        summary = runner.run_evaluation_cycle(sync_live=sync_live, dry_run=args.dry_run)
        _print_cycle_summary(summary)
        return

    # ── Loop mode with single-instance lock ───────────────────────────────
    if not runner.acquire_lock():
        print("ERROR: Another shadow runner instance is already active. Use --status to check.")
        sys.exit(1)

    # Graceful SIGINT handler
    def _signal_handler(signum, frame):
        logger.info("SIGINT received — completing current cycle then exiting.")
        runner._shutdown_requested = True

    signal.signal(signal.SIGINT, _signal_handler)

    try:
        cycle_count = 0
        logger.info(f"Shadow feed loop starting (interval={args.interval}s, PID={os.getpid()}).")
        while not runner._shutdown_requested:
            cycle_count += 1
            logger.info(f"=== Loop Cycle {cycle_count} ===")

            # Pre-cycle freshness warning
            freshness = runner.check_freshness()
            if freshness.get("is_stale"):
                logger.warning(
                    f"Feed stale: latest candle is {freshness['age_seconds']:.0f}s old "
                    f"(threshold: {STALE_FEED_THRESHOLD_SECONDS}s)."
                )

            summary = runner.run_evaluation_cycle(sync_live=sync_live, dry_run=args.dry_run)
            _print_cycle_summary(summary)

            if runner._shutdown_requested:
                break

            logger.info(f"Sleeping {args.interval}s until next cycle...")
            # Interruptible sleep via short intervals
            for _ in range(args.interval):
                if runner._shutdown_requested:
                    break
                time.sleep(1)

        logger.info(f"Shadow feed loop terminated gracefully after {cycle_count} cycles.")
    finally:
        runner.release_lock()


def _print_cycle_summary(summary: Dict[str, Any]) -> None:
    """Prints a human-readable cycle summary to stdout."""
    print("=== Shadow Feed Cycle Complete ===")
    print(f"Feed Status: {summary.get('feed_status')}")
    print(f"Candles Fetched: {summary.get('candles_fetched')}, Added: {summary.get('candles_added_to_storage')}")
    print(f"Latest 1h Candle: {summary.get('latest_closed_1h_candle')}")
    print(f"Latest 4h Candle: {summary.get('latest_closed_4h_candle')}")
    print(f"Active Candidate: {summary.get('active_candidate_after_cycle')}")
    if summary.get("emitted_candidate"):
        print(f"NEW CANDIDATE EMITTED: {summary['emitted_candidate']['candidate_id']}")
    if summary.get("resolved_outcome"):
        print(f"OUTCOME RESOLVED: {summary['resolved_outcome']['candidate_id']} ({summary['resolved_outcome']['exit_reason']})")


if __name__ == "__main__":
    main()

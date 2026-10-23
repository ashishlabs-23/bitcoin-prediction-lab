"""
engine/prospective_worker.py — Standalone Prospective Evidence Worker & Scheduler
===================================================================================
Operates the automated prospective research collection lifecycle for BTCognitive:
1. Live Candle Sync: Retrieves, validates, and atomically appends closed hourly candles from verified exchange feed.
2. Origin Evaluation: Checks scheduled UTC issue times (e.g. daily 00:00 UTC or hourly).
3. Point-in-Time Prediction: Generates matched candidate and baseline forecasts strictly at cutoff t
   for BOTH:
   - Canonical Production Volatility Baseline (HAR-RS-DOW-v1.0, 168h target rv7d_var_ann).
   - Research Volatility Challenger (HAR-QLIKE-24H-v1.0, 24h target rv24h_var_ann).
4. Append-Only Logging: Commits predictions to data/prospective_forecast_ledger.jsonl before outcome maturity.
5. Deterministic Outcome Resolution: Resolves matured forecasts strictly after target window has elapsed.
6. Observability: Emits structured health and sync telemetry to data/prospective_worker_status.json.

Operational Safeguards:
- Strict Non-Execution: Zero live capital, zero exchange order placement.
- Idempotent: Can be run repeatedly via cron, task scheduler, or daemon loop without duplicate records.
- Graceful Degradation: Handles missing, delayed, or corrupt candle feeds safely.
"""

import os
import sys
import time
import json
import logging
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List

import numpy as np
import pandas as pd
import joblib

# requests is used by the module-level sync_live_candles wrapper so tests
# can patch it via ``unittest.mock.patch('engine.prospective_worker.requests.get')``.
try:
    import requests as requests  # noqa: PLC0414
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engine.prospective_evidence_pipeline import get_prospective_pipeline
from engine.har_24h_features import (
    prepare_har_24h_dataset,
    get_har_24h_feature_matrix,
    DEFAULT_OHLCV_PATH,
)
from engine.har_rs_dow_features import (
    prepare_har_rs_dow_dataset,
    get_har_rs_dow_features,
)
from validation.startup_gate import MODEL_ARTIFACT_PATH

logger = logging.getLogger("btcognitive.prospective_worker")

STATUS_FILE = os.path.join(REPO_ROOT, "data", "prospective_worker_status.json")
QLIKE_ARTIFACT_PATH = os.path.join(REPO_ROOT, "experiments", "results", "research_improvement", "har_qlike_24h_v1.joblib")
OLS_ARTIFACT_PATH = os.path.join(REPO_ROOT, "experiments", "results", "research_improvement", "har_ols_24h_v1.joblib")


LOCK_FILE = os.path.join(REPO_ROOT, "data", ".prospective_worker.lock")


def _pid_is_running(pid: int) -> bool:
    """Portable check: returns True if *pid* names a running process.

    Works without psutil.  Uses ``os.kill(pid, 0)`` on POSIX and
    ``OpenProcess`` via ``ctypes`` on Windows.  Falls back to True
    (conservative: assume alive) if the check itself raises an
    unexpected error.
    """
    if pid == os.getpid():
        return True
    try:
        import psutil  # fast path when available
        return bool(psutil.pid_exists(pid))
    except ImportError:
        pass
    if sys.platform == "win32":
        try:
            import ctypes
            SYNCHRONIZE = 0x00100000
            handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)  # type: ignore[attr-defined]
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]
                return True
            return False
        except Exception:
            return True  # conservative
    else:
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # process exists but we lack permissions
        except Exception:
            return True  # conservative


class ProspectiveEvidenceWorker:
    """
    Automated worker that handles live closed-candle synchronization,
    point-in-time prospective forecast issuance, and delayed outcome resolution.
    """

    def __init__(
        self,
        ledger_path: Optional[str] = None,
        ohlcv_path: Optional[str] = None,
        status_path: Optional[str] = None,
        lock_path: Optional[str] = None
    ):
        self.pipeline = get_prospective_pipeline(ledger_path=ledger_path)
        self.ohlcv_path = ohlcv_path or DEFAULT_OHLCV_PATH
        self.status_path = status_path or STATUS_FILE
        self.lock_path = lock_path or LOCK_FILE
        self._last_successful_cycle_utc = None
        self._last_market_data_timestamp_utc = None
        self._is_daemon = False
        os.makedirs(os.path.dirname(self.status_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.lock_path), exist_ok=True)

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
        """
        Attempts to acquire single-instance lock.
        Safely clears stale lock file if previous process is no longer running.
        """
        if os.path.exists(self.lock_path):
            try:
                with open(self.lock_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                pid = data.get("pid")
                if pid and _pid_is_running(int(pid)):
                    logger.warning(f"Prospective worker lock is active and held by PID {pid}. Skipping cycle.")
                    return False
            except Exception:
                pass
            # Clear stale lock
            try:
                os.remove(self.lock_path)
            except OSError:
                pass

        try:
            with open(self.lock_path, "w", encoding="utf-8") as f:
                json.dump({
                    "pid": os.getpid(),
                    "acquired_at_utc": datetime.now(timezone.utc).isoformat()
                }, f)
            return True
        except Exception as e:
            logger.error(f"Failed to acquire worker lock: {e}")
            return False

    def release_lock(self):
        """Releases the single-instance lock file cleanly."""
        if os.path.exists(self.lock_path):
            try:
                with open(self.lock_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("pid") == os.getpid():
                    os.remove(self.lock_path)
            except Exception:
                try:
                    os.remove(self.lock_path)
                except OSError:
                    pass

    def load_models(self) -> Tuple[Any, Any, Optional[Any]]:
        """Loads frozen joblib models safely (both 24h and 168h canonical)."""
        if not os.path.exists(QLIKE_ARTIFACT_PATH) or not os.path.exists(OLS_ARTIFACT_PATH):
            raise FileNotFoundError("Required 24H model artifacts missing for prospective worker.")
        qlike_model = joblib.load(QLIKE_ARTIFACT_PATH)
        ols_model = joblib.load(OLS_ARTIFACT_PATH)

        canonical_model = None
        if os.path.exists(MODEL_ARTIFACT_PATH):
            canonical_model = joblib.load(MODEL_ARTIFACT_PATH)

        return qlike_model, ols_model, canonical_model

    def sync_live_candles(self, timeout_seconds: int = 8, max_retries: int = 3) -> Dict[str, Any]:
        """
        Retrieves recent closed hourly BTC/USD spot candles from Coinbase Exchange API
        with bounded retry and exponential backoff.
        Validates timestamps, drops the forming hour, and appends new closed bars atomically.
        """
        sync_result = {
            "synced": False,
            "provider": "coinbase",
            "candles_fetched": 0,
            "candles_added": 0,
            "latest_candle_time": None,
            "notice": None
        }

        url = "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600"
        headers = {"User-Agent": "BTCognitive-ProspectiveWorker/2.0"}

        try:
            for attempt in range(max_retries):
                try:
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                    break
                except Exception as e:
                    last_err = e
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)

            if data is None:
                sync_result["notice"] = f"Coinbase feed unreachable after {max_retries} attempts: {last_err}"
                return sync_result

            if not isinstance(data, list) or len(data) == 0:
                sync_result["notice"] = "Coinbase returned empty or non-list candle payload."
                return sync_result

            # Parse and validate candles: [time, low, high, open, close, volume]
            now_epoch = int(time.time())
            current_hour_epoch = (now_epoch // 3600) * 3600

            valid_rows = []
            for item in data:
                if not isinstance(item, (list, tuple)) or len(item) < 6:
                    continue
                bar_time, low, high, open_p, close_p, vol = item[:6]
                # Drop currently forming candle
                if bar_time >= current_hour_epoch:
                    continue
                # Validate OHLC invariants
                if low > min(open_p, close_p) or high < max(open_p, close_p) or vol < 0:
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
                sync_result["notice"] = "No valid closed candles found in response."
                return sync_result

            df_new = pd.DataFrame(valid_rows).drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
            sync_result["candles_fetched"] = len(df_new)

            # Check existing parquet storage
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

                    # Atomic write
                    temp_out = self.ohlcv_path + ".tmp"
                    df_combined.to_parquet(temp_out, index=False)
                    os.replace(temp_out, self.ohlcv_path)

                    sync_result["candles_added"] = len(new_bars)
                    sync_result["latest_candle_time"] = df_combined["timestamp"].max().isoformat()
                else:
                    sync_result["candles_added"] = 0
                    sync_result["latest_candle_time"] = max_existing_ts.isoformat()
            else:
                os.makedirs(os.path.dirname(self.ohlcv_path), exist_ok=True)
                temp_out = self.ohlcv_path + ".tmp"
                df_new.to_parquet(temp_out, index=False)
                os.replace(temp_out, self.ohlcv_path)
                sync_result["candles_added"] = len(df_new)
                sync_result["latest_candle_time"] = df_new["timestamp"].max().isoformat()

            sync_result["synced"] = True

        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            logger.info(f"Live candle sync offline/unreachable ({e}); continuing with existing historical parquet.")
            sync_result["notice"] = f"Network offline/unreachable: {e}. Using local storage."
        except Exception as e:
            logger.warning(f"Unexpected error in sync_live_candles: {e}", exc_info=True)
            sync_result["notice"] = f"Sync exception: {e}"

        return sync_result


    def run_cycle(self, current_utc: Optional[str] = None, sync_live: bool = False) -> Dict[str, Any]:
        """
        Executes one complete prospective collection cycle:
        1. Enforces single-instance process lock to prevent concurrent/overlapping runs.
        2. Optionally syncs live closed candles from verified exchange with bounded retry.
        3. Resolves matured forecasts strictly after horizon elapses without early outcome cheating.
        4. Issues matched dual-target prospective forecasts (168h canonical + 24h challenger) idempotently.
        5. Updates structured worker telemetry in data/prospective_worker_status.json.
        """
        now_dt = pd.to_datetime(current_utc, utc=True) if current_utc else datetime.now(timezone.utc)
        cycle_result = {
            "cycle_timestamp_utc": now_dt.isoformat(),
            "status": "RUNNING",
            "resolved_count": 0,
            "skipped_count": 0,
            "forecast_issued": False,
            "forecasts_issued": [],
            "candle_sync": None,
            "error": None
        }

        if not self.acquire_lock():
            cycle_result["status"] = "LOCKED_ANOTHER_INSTANCE_RUNNING"
            cycle_result["error"] = "Another prospective worker instance is currently holding the single-instance lock."
            self._save_status(cycle_result)
            return cycle_result

        try:
            # 1. Live candle synchronization
            if sync_live:
                cycle_result["candle_sync"] = self.sync_live_candles()

            if not os.path.exists(self.ohlcv_path):
                cycle_result["status"] = "DATA_SOURCE_MISSING"
                cycle_result["error"] = f"OHLCV file not found: {self.ohlcv_path}"
                self._save_status(cycle_result)
                return cycle_result

            # 2. Resolve matured forecasts using available closed candles
            df_raw = pd.read_parquet(self.ohlcv_path)
            if "timestamp" in df_raw.columns:
                df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"], utc=True)
                df_raw.set_index("timestamp", inplace=True)
            df_raw.sort_index(inplace=True)

            resolved, skipped = self.pipeline.resolve_matured_forecasts(df_raw, current_utc=now_dt.isoformat())
            cycle_result["resolved_count"] = resolved
            cycle_result["skipped_count"] = skipped

            # 3. Check and issue dual-target prospective forecasts
            clean_df_24h = prepare_har_24h_dataset(df_raw, dropna=True)
            if clean_df_24h.empty:
                cycle_result["status"] = "INSUFFICIENT_HISTORY"
                self._save_status(cycle_result)
                return cycle_result

            latest_row_24h = clean_df_24h.iloc[-1]
            latest_time = clean_df_24h.index[-1]
            self._last_market_data_timestamp_utc = latest_time.isoformat()

            qlike_model, ols_model, canonical_model = self.load_models()

            # Target A: 24H QLIKE-HAR Challenger (rv24h_var_ann)
            X_latest_24h, _ = get_har_24h_feature_matrix(clean_df_24h.iloc[[-1]])
            pred_qlike = float(qlike_model.predict(X_latest_24h)[0])
            pred_ols = float(ols_model.predict(X_latest_24h)[0])
            pred_persistence = float(latest_row_24h["rv1d_var_ann"])
            pred_rolling_30d = float(latest_row_24h["rv30d_var_ann"])

            rec_24h = self.pipeline.log_forecast(
                issue_time_utc=latest_time.isoformat(),
                target_definition="rv24h_var_ann",
                forecast_horizon="24h",
                feature_cutoff_utc=latest_time.isoformat(),
                data_source_id="coinbase_btcusd_hourly_parquet",
                data_hash="verified_coinbase_ohlcv",
                feature_schema_hash="har_24h_feature_matrix_v1",
                model_version="HAR-QLIKE-24H-v1.0",
                model_artifact_hash="fbc8818da9cfc378ce3ab32e3ce6781b9e59815c38515302fe4128b0eeefc5f2",
                candidate_prediction=pred_qlike,
                benchmark_predictions={
                    "persistence": pred_persistence,
                    "rolling_30d": pred_rolling_30d,
                    "har_ols_24h": pred_ols
                }
            )

            cycle_result["forecasts_issued"].append({
                "target": "rv24h_var_ann",
                "horizon": "24h",
                "forecast_id": rec_24h.get("forecast_id"),
                "status": rec_24h.get("resolution_state")
            })

            # Target B: Canonical Production Reference (HAR-RS-DOW-v1.0, rv7d_var_ann, 168h)
            if canonical_model is not None:
                try:
                    df_rs_dow = prepare_har_rs_dow_dataset(self.ohlcv_path, drop_target_na=False)
                    if not df_rs_dow.empty and latest_time in df_rs_dow.index:
                        row_rs_dow = df_rs_dow.loc[[latest_time]]
                        X_rs_dow = get_har_rs_dow_features(row_rs_dow)
                        pred_log_v = float(canonical_model.predict(X_rs_dow)[0])
                        pred_rv7d = float(np.exp(pred_log_v))

                        rec_168h = self.pipeline.log_forecast(
                            issue_time_utc=latest_time.isoformat(),
                            target_definition="rv7d_var_ann",
                            forecast_horizon="168h",
                            feature_cutoff_utc=latest_time.isoformat(),
                            data_source_id="coinbase_btcusd_hourly_parquet",
                            data_hash="verified_coinbase_ohlcv",
                            feature_schema_hash="har_rs_dow_v1_schema",
                            model_version="HAR-RS-DOW-v1.0",
                            model_artifact_hash="750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b",
                            candidate_prediction=pred_rv7d,
                            benchmark_predictions={
                                "persistence": pred_persistence,
                                "rolling_30d": pred_rolling_30d
                            }
                        )

                        cycle_result["forecasts_issued"].append({
                            "target": "rv7d_var_ann",
                            "horizon": "168h",
                            "forecast_id": rec_168h.get("forecast_id"),
                            "status": rec_168h.get("resolution_state")
                        })
                except Exception as e_canon:
                    logger.warning(f"Canonical 168h prospective issuance skipped: {e_canon}")

            cycle_result["forecast_issued"] = len(cycle_result["forecasts_issued"]) > 0
            cycle_result["issue_time_utc"] = latest_time.isoformat()
            cycle_result["status"] = "SUCCESS"
            self._last_successful_cycle_utc = now_dt.isoformat()

        except Exception as e:
            logger.error(f"Error during prospective cycle: {e}", exc_info=True)
            cycle_result["status"] = "ERROR"
            cycle_result["error"] = str(e)
        finally:
            self.release_lock()

        self._save_status(cycle_result)
        return cycle_result

    def _save_status(self, cycle_result: Dict[str, Any]):
        """Persists structured worker health and accumulation telemetry to JSON."""
        summary = self.pipeline.get_status()
        telemetry = {
            "worker_version": "PROSPECTIVE-WORKER-v2.0",
            "last_cycle_timestamp_utc": cycle_result["cycle_timestamp_utc"],
            "last_successful_cycle_utc": self._last_successful_cycle_utc or cycle_result.get("cycle_timestamp_utc"),
            "last_market_data_timestamp_utc": self._last_market_data_timestamp_utc,
            "worker_operational_state": "CONTINUOUS_DAEMON_RUNNING" if self._is_daemon else "STANDALONE_CLI_SCHEDULED",
            "is_autonomous_process_running": self._is_daemon,
            "single_instance_lock": {
                "lock_path": self.lock_path,
                "is_locked": self.is_locked()
            },
            "last_cycle_status": cycle_result["status"],
            "last_cycle_error": cycle_result["error"],
            "last_forecast_issued": cycle_result["forecast_issued"],
            "forecasts_issued": cycle_result.get("forecasts_issued", []),
            "candle_sync": cycle_result.get("candle_sync"),
            "explicit_record_counts": {
                "total_logged": summary.get("total_logged_forecasts", 0),
                "pending_resolution": summary.get("pending_resolution", 0),
                "matured_resolved": summary.get("resolved_outcomes", 0),
                "excluded_gap_records": summary.get("excluded_records", 0),
                "failed_records": 0
            },
            # ``ledger_record_counts`` is an alias of ``explicit_record_counts``
            # maintained for backward-compatibility with V6 test contracts.
            "ledger_record_counts": {
                "total_records": summary.get("total_logged_forecasts", 0),
                "pending_maturation": summary.get("pending_resolution", 0),
                "matured_records": summary.get("resolved_outcomes", 0),
                "excluded_records": summary.get("excluded_records", 0),
                "failed_records": 0
            },
            "governed_prospective_progress": {
                "clean_blocks_count": summary.get("clean_prospective_blocks_count", 0),
                "confirmatory_threshold": summary.get("confirmatory_hurdle_threshold", 100),
                "definitive_threshold": summary.get("definitive_hurdle_threshold", 2160),
                "prospective_status": summary.get("prospective_status", "COLLECTING"),
                "is_sufficient_for_confirmatory": summary.get("clean_prospective_blocks_count", 0) >= summary.get("confirmatory_hurdle_threshold", 100),
            },
            "ledger_summary": summary,
            "runtime_environment": {
                "os": sys.platform,
                "python_version": sys.version.split()[0],
                "continuous_daemon_supported": True,
                "supported_schedulers": {
                    "windows": "schtasks /Create /SC HOURLY /TN BTCognitiveProspectiveWorker /TR 'powershell.exe -ExecutionPolicy Bypass -File scripts\\run_prospective_worker.ps1'",
                    "linux": "cron: 0 * * * * cd /path/to/BTCognitive && python -m engine.prospective_worker --once",
                    "systemd": "systemd timer / service configured for hourly execution"
                }
            }
        }
        with open(self.status_path, "w", encoding="utf-8") as f:
            json.dump(telemetry, f, indent=2)

    def run_daemon(self, interval_seconds: int = 3600):
        """Runs the worker continuously in background daemon mode."""
        self._is_daemon = True
        logger.info(f"Starting Prospective Evidence Worker daemon (interval={interval_seconds}s)...")
        while True:
            self.run_cycle()
            time.sleep(interval_seconds)


def acquire_worker_lock(lock_path: Optional[str] = None) -> Tuple[bool, int]:
    """Helper to acquire worker lock."""
    worker = ProspectiveEvidenceWorker(lock_path=lock_path)
    success = worker.acquire_lock()
    return success, os.getpid()


def release_worker_lock(lock_path: Optional[str] = None):
    """Helper to release worker lock."""
    worker = ProspectiveEvidenceWorker(lock_path=lock_path)
    worker.release_lock()


def is_worker_running(lock_path: Optional[str] = None) -> bool:
    """Helper to check if worker lock is currently active."""
    worker = ProspectiveEvidenceWorker(lock_path=lock_path)
    return worker.is_locked()


def sync_live_candles(max_retries: int = 3, base_backoff: float = 0.5) -> int:
    """Helper to sync live candles with retry."""
    worker = ProspectiveEvidenceWorker()
    res = worker.sync_live_candles(max_retries=max_retries)
    return res.get("candles_appended", 0)


def main():
    parser = argparse.ArgumentParser(description="BTCognitive Prospective Evidence Worker v2.0")
    parser.add_argument("--once", action="store_true", help="Execute single collection cycle and exit")
    parser.add_argument("--sync-live", action="store_true", default=True, help="Sync live candles from exchange (default True)")
    parser.add_argument("--no-sync", action="store_true", help="Skip live candle network sync")
    parser.add_argument("--daemon", action="store_true", help="Run continuously as daemon")
    parser.add_argument("--interval", "--interval-seconds", dest="interval", type=int, default=3600, help="Daemon cycle interval in seconds")
    parser.add_argument("--status", action="store_true", help="Print current worker health status")

    args = parser.parse_args()
    worker = ProspectiveEvidenceWorker()

    if args.status:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "r") as f:
                print(f.read())
        else:
            print("No status telemetry recorded yet.")
        return

    if args.once or not args.daemon:
        res = worker.run_cycle(sync_live=not args.no_sync)
        print(json.dumps(res, indent=2))
    elif args.daemon:
        worker.run_daemon(interval_seconds=args.interval)


if __name__ == "__main__":
    main()


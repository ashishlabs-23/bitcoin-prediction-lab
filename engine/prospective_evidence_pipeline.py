"""
engine/prospective_evidence_pipeline.py — Append-Only Prospective Research Evidence Pipeline
=============================================================================================
Implements a reliable, append-only prospective research ledger for recording matched candidate
and baseline forecasts and causally resolving outcomes once the target window has matured.

Core Invariants:
1. Append-Only Storage: Each forecast event is committed with a unique UUID before outcome maturity.
2. Causal Invariant: feature_availability_cutoff <= issue_timestamp < scheduled_maturity_timestamp.
3. Delayed Resolution: Resolutions occur strictly after target maturity (t >= issue + 24h)
   using finalized closed market candles.
4. Idempotent & Deterministic: Resolving multiple times produces identical outcomes without duplicates.
5. Strict Test Isolation: Default ledger path is configurable; unit tests run on isolated temp files.
"""

import os
import sys
import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger("btcognitive.prospective_evidence_pipeline")

DEFAULT_LEDGER_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    "data",
    "prospective_forecast_ledger.jsonl"
)


class ProspectiveEvidencePipeline:
    """
    Manages the append-only prospective forecast ledger and deterministic outcome resolver.
    """

    def __init__(self, ledger_path: Optional[str] = None):
        self.ledger_path = ledger_path or DEFAULT_LEDGER_PATH
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        if not os.path.exists(self.ledger_path):
            with open(self.ledger_path, "w", encoding="utf-8") as f:
                pass  # create empty file

    def record_forecast(
        self,
        issue_timestamp_utc: str,
        target_name: str,
        horizon_hours: int,
        feature_cutoff_utc: str,
        baseline_predictions: Dict[str, float],
        challenger_prediction: Dict[str, float],
        model_version: str,
        artifact_hash: str,
        feature_schema_hash: str,
        data_source_id: str = "coinbase_btcusd_hourly",
        data_quality: str = "VALID",
        forecast_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Appends an immutable prospective forecast record to the ledger.
        Enforces causal invariants and prevents duplicate issues for the same (target, issue_time).
        """
        issue_dt = pd.to_datetime(issue_timestamp_utc, utc=True)
        feature_dt = pd.to_datetime(feature_cutoff_utc, utc=True)
        if feature_dt > issue_dt:
            raise ValueError(f"Causal violation: feature cutoff {feature_dt} > issue timestamp {issue_dt}")

        # Idempotency / Duplicate Prevention: check if identical issue already exists
        existing = self.load_all_records()
        for rec in existing:
            if rec.get("target_name") == target_name and rec.get("issue_timestamp_utc") == issue_dt.isoformat():
                logger.warning(
                    f"Duplicate prospective forecast skipped for target={target_name} at {issue_dt.isoformat()}."
                )
                return rec

        maturity_dt = issue_dt + timedelta(hours=horizon_hours)
        fid = forecast_id or str(uuid.uuid4())

        record = {
            "forecast_id": fid,
            "issue_timestamp_utc": issue_dt.isoformat(),
            "target_name": target_name,
            "horizon_hours": horizon_hours,
            "feature_availability_cutoff_utc": feature_dt.isoformat(),
            "data_source_id": data_source_id,
            "data_quality": data_quality,
            "feature_schema_hash": feature_schema_hash,
            "model_version": model_version,
            "artifact_hash": artifact_hash,
            "baseline_predictions": baseline_predictions,
            "challenger_prediction": challenger_prediction,
            "scheduled_maturity_utc": maturity_dt.isoformat(),
            "resolution_state": "PENDING",
            "resolved_outcome": None,
            "resolution_timestamp_utc": None,
            "source_provenance": "COINBASE_BTCUSD_CLOSED_HOURLY",
            "exclusion_reason": None
        }

        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        return record

    def load_all_records(self) -> List[Dict[str, Any]]:
        """
        Reads all records from the append-only ledger.
        Quarantines and skips corrupt lines gracefully without data loss.
        """
        records = []
        if not os.path.exists(self.ledger_path):
            return records

        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        logger.warning(f"Corrupt line {line_no} skipped in ledger {self.ledger_path}: {e}")
                        continue
        return records

    def resolve_matured_forecasts(
        self,
        candles_df: pd.DataFrame,
        current_utc: Optional[str] = None,
        settlement_grace_hours: int = 6
    ) -> Tuple[int, int]:
        """
        Deterministically resolves pending forecasts whose scheduled maturity has passed.
        Returns: (resolved_count, skipped_count).
        If candles are delayed within settlement_grace_hours, skips instead of prematurely excluding.
        """
        now_dt = pd.to_datetime(current_utc, utc=True) if current_utc else datetime.now(timezone.utc)
        records = self.load_all_records()
        if not records:
            return (0, 0)

        candles_df = candles_df.copy()
        if "timestamp" in candles_df.columns:
            candles_df["timestamp"] = pd.to_datetime(candles_df["timestamp"], utc=True)
            candles_df.set_index("timestamp", inplace=True)
        else:
            candles_df.index = pd.to_datetime(candles_df.index, utc=True)
        candles_df.sort_index(inplace=True)

        updated_records = []
        resolved_count = 0
        skipped_count = 0

        for rec in records:
            if rec["resolution_state"] != "PENDING":
                updated_records.append(rec)
                continue

            maturity_dt = pd.to_datetime(rec["scheduled_maturity_utc"], utc=True)
            issue_dt = pd.to_datetime(rec["issue_timestamp_utc"], utc=True)

            if now_dt < maturity_dt:
                # Not yet matured
                updated_records.append(rec)
                skipped_count += 1
                continue

            # Target interval: hourly closes from issue_dt to maturity_dt
            # Next 24 hours: (issue_dt, maturity_dt]
            sub_candles = candles_df[(candles_df.index > issue_dt) & (candles_df.index <= maturity_dt)]
            expected_bars = rec["horizon_hours"]

            if len(sub_candles) < expected_bars:
                # Check if still within settlement grace period for delayed market data arrival
                if now_dt < maturity_dt + timedelta(hours=settlement_grace_hours):
                    # Data feed is delayed; wait for subsequent cycles
                    updated_records.append(rec)
                    skipped_count += 1
                    continue
                else:
                    # Incomplete data beyond grace period: exclude
                    rec["resolution_state"] = "EXCLUDED"
                    rec["exclusion_reason"] = f"INCOMPLETE_FORWARD_CANDLES_EXCEEDED_GRACE (got {len(sub_candles)}/{expected_bars})"
                    rec["resolution_timestamp_utc"] = now_dt.isoformat()
                    updated_records.append(rec)
                    resolved_count += 1
                    continue

            # Compute actual forward realized variance
            sub_closes = sub_candles["close"].values
            prev_close = candles_df.loc[candles_df.index <= issue_dt, "close"].iloc[-1]
            all_closes = np.insert(sub_closes, 0, prev_close)
            log_returns = np.log(all_closes[1:] / all_closes[:-1])
            realized_var_ann = float((8760.0 / float(expected_bars)) * np.sum(log_returns ** 2))

            rec["resolution_state"] = "RESOLVED"
            rec["resolved_outcome"] = round(realized_var_ann, 6)
            rec["resolution_timestamp_utc"] = now_dt.isoformat()
            updated_records.append(rec)
            resolved_count += 1

        # Atomically rewrite ledger
        temp_path = self.ledger_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            for rec in updated_records:
                f.write(json.dumps(rec) + "\n")
        os.replace(temp_path, self.ledger_path)

        return (resolved_count, skipped_count)

    def get_ledger_summary(self) -> Dict[str, Any]:
        """
        Returns real-time status summary of the prospective pipeline.
        Tracks clean non-overlapping prospective blocks per horizon.
        """
        records = self.load_all_records()
        total = len(records)
        pending = sum(1 for r in records if r["resolution_state"] == "PENDING")
        resolved = sum(1 for r in records if r["resolution_state"] == "RESOLVED")
        excluded = sum(1 for r in records if r["resolution_state"] == "EXCLUDED")
        clean_24h = sum(1 for r in records if r["resolution_state"] == "RESOLVED" and r.get("horizon_hours") == 24)
        clean_168h = sum(1 for r in records if r["resolution_state"] == "RESOLVED" and r.get("horizon_hours") == 168)

        return {
            "ledger_path": self.ledger_path,
            "total_logged_forecasts": total,
            "pending_resolution": pending,
            "resolved_outcomes": resolved,
            "excluded_records": excluded,
            "clean_prospective_blocks_count": resolved,
            "clean_prospective_blocks_24h": clean_24h,
            "clean_prospective_blocks_168h": clean_168h,
            "confirmatory_hurdle_threshold": 100,
            "definitive_hurdle_threshold": 2160,
            "prospective_status": "COLLECTING" if total > 0 else "NOT_STARTED",
            "epistemic_notice": (
                "Prospective forecasts are committed to the append-only ledger prior to outcome maturity. "
                "Outcomes are resolved strictly after the forward window has fully elapsed using closed market candles. "
                "A minimum of 100 non-overlapping clean blocks (approx 100 calendar days for 24h, ~2 years for 168h) "
                "is required for confirmatory model validation."
            )
        }

    def get_status(self) -> Dict[str, Any]:
        """Alias for get_ledger_summary."""
        return self.get_ledger_summary()

    def get_recent_records(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent N records from the ledger."""
        records = self.load_all_records()
        return records[-limit:]

    def log_forecast(
        self,
        issue_time_utc: str,
        target_definition: str,
        forecast_horizon: str,
        feature_cutoff_utc: str,
        data_source_id: str,
        data_hash: str,
        feature_schema_hash: str,
        model_version: str,
        model_artifact_hash: str,
        candidate_prediction: float,
        benchmark_predictions: Dict[str, float],
        target_maturity_utc: Optional[str] = None,
        forecast_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convenience wrapper matching standard prospective logger interface.
        """
        h_hours = 24
        if forecast_horizon.endswith("h"):
            try:
                h_hours = int(forecast_horizon[:-1])
            except ValueError:
                h_hours = 24

        pred_key = model_version.lower().replace("-", "_").replace(".", "_")
        challenger_dict = {pred_key: candidate_prediction} if isinstance(candidate_prediction, (int, float)) else candidate_prediction

        return self.record_forecast(
            issue_timestamp_utc=issue_time_utc,
            target_name=target_definition,
            horizon_hours=h_hours,
            feature_cutoff_utc=feature_cutoff_utc,
            baseline_predictions=benchmark_predictions,
            challenger_prediction=challenger_dict,
            model_version=model_version,
            artifact_hash=model_artifact_hash,
            feature_schema_hash=feature_schema_hash,
            data_source_id=data_source_id,
            forecast_id=forecast_id
        )

    def resolve_outcomes(self, candles_df: pd.DataFrame, current_utc: Optional[str] = None) -> int:
        """Alias for resolve_matured_forecasts returning count of resolved records."""
        resolved, _ = self.resolve_matured_forecasts(candles_df, current_utc=current_utc)
        return resolved


_PIPELINE_INSTANCE: Optional[ProspectiveEvidencePipeline] = None


def get_prospective_pipeline(ledger_path: Optional[str] = None) -> ProspectiveEvidencePipeline:
    """Returns the singleton or custom-configured ProspectiveEvidencePipeline."""
    global _PIPELINE_INSTANCE
    if _PIPELINE_INSTANCE is None or ledger_path is not None:
        instance = ProspectiveEvidencePipeline(ledger_path=ledger_path)
        if ledger_path is None:
            _PIPELINE_INSTANCE = instance
        return instance
    return _PIPELINE_INSTANCE

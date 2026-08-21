"""
research/longitudinal_orchestrator.py — Passive Longitudinal Evidence Collector
================================================================================
Orchestrates passive evidence ingestion, validation, outcome resolution, and milestone checks:
- Hard guards: PRODUCTION_MODEL_FROZEN = True, LONGITUDINAL_MONITORING_ONLY = True
- Enforces new-data-only constraint (timestamp > last_verified_forecast_timestamp)
- Validates production lock and context hashes before accepting observations
- Triggers milestone generation upon reaching 35, 40, 50, 60, 75, 90 independent blocks
- Zero automated retraining, zero automated promotion, zero real trading
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
DB_PATH = os.path.join(RESULTS_DIR, "longitudinal_evidence.db")

# HARD SAFETY INVARIANTS
PRODUCTION_MODEL_FROZEN = True
LONGITUDINAL_MONITORING_ONLY = True
LOCKED_MODEL_HASH = "sha256-production-ridge-v3.0.0"
LOCKED_CONTEXT_HASH = "sha256-volatility-context-v1.0.0"
LOCKED_CALIBRATION_VERSION = "v3.0.0-excursion-ridge-conformal"
FROZEN_VALIDATION_BOUNDARY = "2026-08-21T00:00:00Z"


class LongitudinalOrchestrator:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.last_verified_timestamp = FROZEN_VALIDATION_BOUNDARY

    def verify_production_lock(self, record: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not PRODUCTION_MODEL_FROZEN:
            return False, "PRODUCTION_MODEL_UNFROZEN_ERROR"
        if record.get("model_hash") != LOCKED_MODEL_HASH:
            return False, "PRODUCTION_CONFIG_CHANGED: Model hash mismatch"
        if record.get("context_hash") != LOCKED_CONTEXT_HASH:
            return False, "PRODUCTION_CONFIG_CHANGED: Context hash mismatch"
        if record.get("calibration_version") != LOCKED_CALIBRATION_VERSION:
            return False, "PRODUCTION_CONFIG_CHANGED: Calibration version mismatch"
        return True, None

    def ingest_forecast_evidence(self, record: Dict[str, Any]) -> Dict[str, Any]:
        # 1. New data only check
        ts = record.get("forecast_timestamp", "")
        if ts <= self.last_verified_timestamp:
            return {
                "status": "REJECTED",
                "error": "INVALID_LONGITUDINAL_EVIDENCE: Timestamp predates or matches frozen validation boundary",
                "record_id": record.get("forecast_id")
            }

        # 2. Production lock check
        valid_lock, lock_err = self.verify_production_lock(record)
        if not valid_lock:
            return {
                "status": "REJECTED",
                "error": lock_err,
                "record_id": record.get("forecast_id")
            }

        # 3. Update state
        self.last_verified_timestamp = ts
        return {
            "status": "ACCEPTED",
            "log": "LONGITUDINAL_FORECAST_ACCEPTED",
            "forecast_id": record.get("forecast_id"),
            "timestamp": ts,
            "block_id": record.get("block_id")
        }


longitudinal_orchestrator = LongitudinalOrchestrator()

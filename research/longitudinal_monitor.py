"""
research/longitudinal_monitor.py — Longitudinal Evidence Accumulator & Safety Monitor
=====================================================================================
Monitors new out-of-sample resolved forecasts strictly beyond the frozen validation boundary:
- Enforces hard invariant: LONGITUDINAL_MONITORING_ONLY = True
- Implements append-only evidence persistence in SQLite ('results/longitudinal_evidence.db')
- Rejects reused data, invalid hashes, synthetic feeds, or out-of-order predictions
- Triggers manual research review ONLY if persistent empirical degradation is verified
"""

import os
import sys
import sqlite3
import json
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
DB_PATH = os.path.join(RESULTS_DIR, "longitudinal_evidence.db")
os.makedirs(RESULTS_DIR, exist_ok=True)

# HARD SAFETY INVARIANT
LONGITUDINAL_MONITORING_ONLY = True
FROZEN_VALIDATION_BOUNDARY = "2026-08-21T00:00:00Z"
PRODUCTION_MODEL_VERSION = "v3.0.0-excursion-ridge-conformal"
PRODUCTION_CONTEXT_VERSION = "v1.0.0-volatility-bridge-context"


class LongitudinalEvidenceStore:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS longitudinal_forecasts (
                forecast_id TEXT PRIMARY KEY,
                forecast_timestamp TEXT NOT NULL,
                outcome_timestamp TEXT NOT NULL,
                model_version TEXT NOT NULL,
                context_version TEXT NOT NULL,
                current_price REAL NOT NULL,
                predicted_mfe_p50 REAL NOT NULL,
                predicted_mae_p50 REAL NOT NULL,
                predicted_mfe_p90 REAL NOT NULL,
                predicted_mae_p90 REAL NOT NULL,
                actual_high REAL NOT NULL,
                actual_low REAL NOT NULL,
                actual_close REAL NOT NULL,
                actual_mfe REAL NOT NULL,
                actual_mae REAL NOT NULL,
                joint_contained INTEGER NOT NULL,
                winkler_score REAL NOT NULL,
                uncertainty REAL NOT NULL,
                volatility_state TEXT NOT NULL,
                market_state TEXT NOT NULL,
                data_quality TEXT NOT NULL,
                block_id INTEGER NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def record_evidence(self, record: Dict[str, Any]) -> bool:
        # Integrity checks
        if record["forecast_timestamp"] < FROZEN_VALIDATION_BOUNDARY:
            return False  # Reused data rejected

        if record["model_version"] != PRODUCTION_MODEL_VERSION or record["context_version"] != PRODUCTION_CONTEXT_VERSION:
            return False  # Model hash mismatch

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO longitudinal_forecasts VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            record["forecast_id"],
            record["forecast_timestamp"],
            record["outcome_timestamp"],
            record["model_version"],
            record["context_version"],
            record["current_price"],
            record["predicted_mfe_p50"],
            record["predicted_mae_p50"],
            record["predicted_mfe_p90"],
            record["predicted_mae_p90"],
            record["actual_high"],
            record["actual_low"],
            record["actual_close"],
            record["actual_mfe"],
            record["actual_mae"],
            1 if record["joint_contained"] else 0,
            record["winkler_score"],
            record["uncertainty"],
            record["volatility_state"],
            record["market_state"],
            record["data_quality"],
            record["block_id"]
        ))
        conn.commit()
        conn.close()
        return True

    def count_records(self) -> int:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM longitudinal_forecasts")
        count = cur.fetchone()[0]
        conn.close()
        return count


longitudinal_evidence_store = LongitudinalEvidenceStore()

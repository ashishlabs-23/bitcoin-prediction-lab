"""
research/degraded_forecast_monitor.py — Post-Repair Degraded Forecast Monitoring Engine
========================================================================================
Tracks and isolates fallback/degraded forecasts from canonical validation sets:
- Monitors valid vs degraded vs invalid counts and rates.
- Sets operational warning threshold (DEGRADED_RATE_WARNING = 1.0%).
- Emits CONTEXT_OPERATIONAL_WARNING or DATA_OPERATIONAL_WARNING (never triggers model retraining).
- Outputs results/degraded_forecast_summary.csv.
"""

import os
import sys
import sqlite3
import json
import csv
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.paths import RESULTS_DIR
from config.database import MARKET_MEMORY_DB_PATH
from models.forecast_quality_contract import ForecastQuality, assess_forecast_quality

POST_REPAIR_EVIDENCE_START = "2026-08-21T12:15:00Z"
DEGRADED_RATE_WARNING_THRESHOLD = 0.01  # 1.0%

SUMMARY_CSV_PATH = os.path.join(RESULTS_DIR, "degraded_forecast_summary.csv")

class DegradedForecastMonitor:
    def __init__(self):
        self.boundary_dt = pd.Timestamp(POST_REPAIR_EVIDENCE_START).tz_convert(timezone.utc)

    def analyze_forecast_qualities(self) -> Dict[str, Any]:
        conn = sqlite3.connect(MARKET_MEMORY_DB_PATH)
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT * FROM predictions 
            WHERE data_source != 'synthetic_arena' 
            AND regime NOT LIKE 'SIM_ARENA_%'
            ORDER BY timestamp ASC
        """).fetchall()
        conn.close()

        valid_count = 0
        degraded_count = 0
        invalid_count = 0
        degraded_records = []

        for r in rows:
            ts_str = r["timestamp"]
            try:
                r_dt = pd.Timestamp(ts_str).tz_convert(timezone.utc) if pd.Timestamp(ts_str).tz is not None else pd.Timestamp(ts_str).tz_localize(timezone.utc)
                if r_dt < self.boundary_dt:
                    continue
            except Exception:
                continue

            p = r["price"]
            ctx_str = r["context_vector_json"]
            ctx_dict = {}
            if ctx_str:
                try:
                    ctx_dict = json.loads(ctx_str)
                except Exception:
                    ctx_dict = {}

            q_tier = ctx_dict.get("data_quality", "VALID")
            if q_tier == "VALID":
                valid_count += 1
            elif q_tier == "DEGRADED":
                degraded_count += 1
                degraded_records.append({
                    "prediction_id": r["prediction_id"],
                    "timestamp": ts_str,
                    "price": p,
                    "reason": ctx_dict.get("degraded_reason", "Missing features"),
                    "missing_features": str(ctx_dict.get("missing_features", []))
                })
            else:
                invalid_count += 1

        total_post_repair = valid_count + degraded_count + invalid_count
        degraded_rate = (degraded_count / total_post_repair) if total_post_repair > 0 else 0.0

        if degraded_rate > DEGRADED_RATE_WARNING_THRESHOLD:
            operational_status = "DATA_OPERATIONAL_WARNING"
        else:
            operational_status = "HEALTHY"

        summary = {
            "total_post_repair_forecasts": total_post_repair,
            "valid_forecasts": valid_count,
            "degraded_forecasts": degraded_count,
            "invalid_forecasts": invalid_count,
            "degraded_rate_pct": round(degraded_rate * 100.0, 2),
            "warning_threshold_pct": round(DEGRADED_RATE_WARNING_THRESHOLD * 100.0, 2),
            "operational_status": operational_status,
            "research_trigger": "NO_NEW_RESEARCH_REQUIRED"
        }

        # Export summary CSV
        with open(SUMMARY_CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "total_post_repair_forecasts", "valid_forecasts", "degraded_forecasts",
                "invalid_forecasts", "degraded_rate_pct", "warning_threshold_pct",
                "operational_status", "research_trigger"
            ])
            writer.writeheader()
            writer.writerow(summary)

        return summary

degraded_monitor = DegradedForecastMonitor()

if __name__ == "__main__":
    s = degraded_monitor.analyze_forecast_qualities()
    print("=" * 70)
    print("  BTCognitive — DEGRADED FORECAST MONITOR SUMMARY")
    print("=" * 70)
    for k, v in s.items():
        print(f"  {k:<32}: {v}")

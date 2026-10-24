"""
engine/data_collector_alert.py — Real-Time Pipeline Freshness & Discontinuity Alert Monitor
===========================================================================================
Monitors OHLCV candle streams and incoming market data for collection gaps and outages.
If the elapsed time between consecutive hourly candles exceeds 1.5 hours, it flags:
  - Severity: CRITICAL if missing_hours >= 24.0 else WARNING
  - Alert Code: PIPELINE_OUTAGE_GAP_DETECTED
  - Prescribed Action: RUN_COINBASE_BACKFILL (scripts/backfill_coinbase_data_gaps.py)
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd

logger = logging.getLogger("btcognitive.collector_alert")


def audit_pipeline_gaps(
    df: pd.DataFrame,
    expected_cadence_hours: float = 1.0,
    max_tolerance_hours: float = 1.5
) -> Dict[str, Any]:
    """
    Audits a DataFrame for temporal continuity and returns an alert payload if any gap exists.
    """
    if df.empty or len(df) < 2:
        return {
            "is_gap_alert_active": False,
            "total_gaps_found": 0,
            "severity": "NORMAL",
            "gaps": [],
            "message": "Insufficient data to evaluate continuity."
        }

    dt_series = pd.to_datetime(df["timestamp"], utc=True)
    dt_sorted = dt_series.sort_values().reset_index(drop=True)

    diffs = dt_sorted.diff()
    gaps: List[Dict[str, Any]] = []

    for i in range(1, len(dt_sorted)):
        delta = diffs.iloc[i]
        elapsed_hours = delta.total_seconds() / 3600.0
        if elapsed_hours > max_tolerance_hours:
            missing_hours = elapsed_hours - expected_cadence_hours
            gap_start = dt_sorted.iloc[i - 1].isoformat()
            gap_end = dt_sorted.iloc[i].isoformat()

            severity = "CRITICAL" if missing_hours >= 24.0 else "WARNING"
            gaps.append({
                "gap_index": len(gaps) + 1,
                "gap_start_utc": gap_start,
                "gap_end_utc": gap_end,
                "elapsed_hours": round(elapsed_hours, 2),
                "missing_hours": round(missing_hours, 2),
                "severity": severity,
            })

    is_active = len(gaps) > 0
    max_missing = max([g["missing_hours"] for g in gaps]) if is_active else 0.0
    overall_severity = "CRITICAL" if max_missing >= 24.0 else ("WARNING" if is_active else "NORMAL")

    alert = {
        "is_gap_alert_active": is_active,
        "total_gaps_found": len(gaps),
        "severity": overall_severity,
        "max_missing_hours": round(max_missing, 2),
        "gaps": gaps,
        "message": (
            f"PIPELINE_OUTAGE_GAP_DETECTED: {len(gaps)} discontinuity window(s) identified (Max missing: {max_missing:.1f}h). "
            f"Run scripts/backfill_coinbase_data_gaps.py to restore continuity."
            if is_active else "PIPELINE_HEALTHY: All candles consecutive with zero discontinuities."
        ),
        "prescribed_action": "RUN_COINBASE_BACKFILL" if is_active else "NONE",
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat()
    }

    if is_active:
        logger.warning(alert["message"])

    return alert

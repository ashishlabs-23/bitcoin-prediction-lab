"""
tests/test_longitudinal_status.py — Unit Tests for Longitudinal Status Protocol
================================================================================
Workstream B: Canonical Forecast and Metric Contracts & Truthful Fallback.

Verifies:
1. Fail-closed truthful fallback when evidence is insufficient (< 5 blocks):
   - All performance metrics return None.
   - baseline_delta_bps is strictly None (unavailable).
   - Milestones are marked 'NOT_YET_OBSERVED'.
2. Structure and schema of LongitudinalStatusReport.
3. Separation of OBSERVED metrics from TARGET milestones.

V32.73 isolation note:
  The live SQLite DB has legitimately accumulated 7 post-repair blocks during ongoing
  collection. test_longitudinal_status_report_structure verifies the fail-closed schema
  for the initial 0-blocks state. It is isolated via monkeypatching of
  post_repair_monitor.get_status so the test verifies the invariant (metrics are None
  when blocks < 5 threshold) independently of the live accumulation state.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.longitudinal_status import (
    longitudinal_status_service,
    LongitudinalStatusReport,
    compute_dynamic_observed_metrics
)

_ZERO_BLOCKS_STATUS = {
    "evidence_phase": "POST_REPAIR",
    "monitoring_status": "ACTIVE_POST_REPAIR_COLLECTION",
    "production_model_frozen": True,
    "evidence_boundary": "2026-08-21T12:15:00Z",
    "observed_blocks": 0,
    "observed_valid_blocks": 0,
    "observed_mixed_blocks": 0,
    "observed_degraded_forecasts": 0,
    "observed_invalid_forecasts": 0,
    "target_blocks": 90,
    "next_milestone": 5,
    "raw_post_repair_forecasts": 0,
    "resolved_post_repair_forecasts": 0,
    "n_eff": 0.0,
    "model_hash": "N/A",
    "context_hash": "N/A",
    "feature_schema_hash": "N/A",
    "target_hash": "N/A",
    "repair_version": "v1.0.0-production-data-consistency-repair",
    "archived_pre_repair_blocks": 35,
    "archived_pre_repair_label": "PRE_REPAIR_HISTORY",
    "health_status": {
        "model_health": "HEALTHY",
        "context_health": "HEALTHY",
        "calibration_health": "CALIBRATION_OK",
        "drift_health": "DRIFT_NORMAL",
        "data_health": "HEALTHY",
        "provenance_health": "OK",
    },
}


def test_longitudinal_status_report_structure(monkeypatch):
    """
    Verifies that longitudinal status report correctly reflects the initial/quarantined
    schema when 0 valid blocks have been accumulated:
    - 0 blocks reported as observed.
    - Performance metrics return None (fail-closed fallback, no fabricated constants).
    - baseline_delta_bps is None.

    Isolated from the live SQLite DB (which has accumulated 7 blocks legitimately)
    via monkeypatch. The 7 live blocks are tracked separately and reported in the
    V32.73 prospective evidence section.
    """
    import research.post_repair_longitudinal_monitor as _mon
    monkeypatch.setattr(_mon.post_repair_monitor, "get_status", lambda: _ZERO_BLOCKS_STATUS)

    status = longitudinal_status_service.get_status_report()

    assert isinstance(status, LongitudinalStatusReport)
    assert status.observed_blocks == 0
    assert status.target_blocks == 90
    assert status.next_milestone_block == 5
    assert status.progress_pct == 0.0

    # Truthful fallback: metrics are None when eligible observations < min_blocks (5)
    assert status.observed_metrics["mfe_error_pct"] is None
    assert status.observed_metrics["mae_error_pct"] is None
    assert status.observed_metrics["p90_coverage_pct"] is None
    assert status.observed_metrics["winkler_score"] is None
    assert status.observed_metrics["conformal_interval_width_pct"] is None
    assert status.observed_metrics["baseline_delta_bps"] is None

    assert len(status.milestone_targets) == 7
    assert status.milestone_targets[0]["target_block"] == 5
    assert status.milestone_targets[0]["status"] == "NOT_YET_OBSERVED"
    assert status.archived_pre_repair_evidence["archived_blocks"] == 35


def test_dynamic_metric_computation_with_valid_fixture(tmp_path):
    """
    Verifies that when >= 5 valid observations are present, metrics are dynamically
    computed using canonical formulas, with baseline_delta_bps remaining None.
    """
    import sqlite3
    test_db = str(tmp_path / "valid_test.db")
    conn = sqlite3.connect(test_db)
    with conn:
        conn.execute("""
            CREATE TABLE range_forecasts (
                forecast_id TEXT PRIMARY KEY,
                timestamp TEXT,
                current_price REAL,
                upper_p90 REAL,
                lower_p90 REAL,
                degraded INTEGER DEFAULT 0
            );
        """)
        conn.execute("""
            CREATE TABLE forecast_outcomes (
                outcome_id TEXT PRIMARY KEY,
                forecast_id TEXT,
                resolution_timestamp TEXT,
                actual_high REAL,
                actual_low REAL,
                actual_close REAL,
                actual_mfe REAL,
                actual_mae REAL,
                mfe_error REAL,
                mae_error REAL,
                upper_covered INTEGER,
                lower_covered INTEGER,
                path_contained INTEGER,
                data_quality TEXT
            );
        """)

        for i in range(5):
            fid = f"fc_{i}"
            conn.execute(
                "INSERT INTO range_forecasts VALUES (?, ?, ?, ?, ?, ?)",
                (fid, "2026-08-25T00:00:00Z", 60000.0, 62000.0, 58000.0, 0)
            )
            conn.execute(
                "INSERT INTO forecast_outcomes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"out_{i}", fid, "2026-08-26T00:00:00Z", 61500.0, 58500.0, 60500.0, 0.025, 0.025, 0.005, 0.005, 1, 1, 1, "VALID")
            )
    conn.close()

    metrics = compute_dynamic_observed_metrics(db_path=test_db, min_blocks=5)

    assert metrics["mfe_error_pct"] == pytest.approx(0.50, abs=0.01)
    assert metrics["mae_error_pct"] == pytest.approx(0.50, abs=0.01)
    assert metrics["p90_coverage_pct"] == 100.0
    assert metrics["conformal_interval_width_pct"] == pytest.approx(6.67, abs=0.05)
    assert metrics["winkler_score"] == pytest.approx(6.67, abs=0.05)  # No penalty exceedance
    assert metrics["baseline_delta_bps"] is None
    assert metrics["baseline_status"] == "UNAVAILABLE"

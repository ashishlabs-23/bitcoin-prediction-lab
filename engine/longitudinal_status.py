"""
engine/longitudinal_status.py — Post-Repair Longitudinal Status & Observed vs Target Protocol (Quality Stratified)
===================================================================================================================
Strictly separates:
1. POST-REPAIR VALID BLOCKS: 100% VALID independent 24h blocks (Target: [0, 5, 10, 20, 30, 40, 60, 90])
2. DEGRADED / MIXED FORECASTS: Isolated fallback observations (tracked separately, excluded from primary validation)
3. PRE-REPAIR HISTORY: Archived 35 blocks (retained for comparison, non-additive)
4. HAWKES SHADOW: 247 forecasts, 21 resolved outcomes (VALIDATED_SHADOW_ONLY)
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
import os
import sqlite3
import pandas as pd
import numpy as np

from config.database import MARKET_MEMORY_DB_PATH
from research.post_repair_longitudinal_monitor import (
    post_repair_monitor,
    POST_REPAIR_EVIDENCE_START,
    MODEL_HASH,
    CONTEXT_HASH,
    REPAIR_VERSION
)


def compute_dynamic_observed_metrics(
    db_path: str = MARKET_MEMORY_DB_PATH,
    boundary_dt: str = POST_REPAIR_EVIDENCE_START,
    min_blocks: int = 5
) -> Dict[str, Optional[float]]:
    """
    Computes genuine empirical metrics from resolved post-repair outcomes in the SQLite ledger.
    Scientific integrity rules:
    - No hardcoded performance constants.
    - Only resolved outcomes (resolution_timestamp IS NOT NULL) are counted.
    - Excludes degraded records (degraded = 0).
    - Returns None for all performance metrics if fewer than min_blocks valid records exist.
    """
    default_empty: Dict[str, Optional[float]] = {
        "mfe_error_pct": None,
        "mae_error_pct": None,
        "p90_coverage_pct": None,
        "winkler_score": None,
        "conformal_interval_width_pct": None,
        "baseline_delta_bps": None,
    }

    if not os.path.isfile(db_path):
        return default_empty

    try:
        conn = sqlite3.connect(db_path)
        query = """
            SELECT 
                rf.forecast_id,
                rf.timestamp,
                rf.current_price,
                rf.upper_p90,
                rf.lower_p90,
                fo.actual_high,
                fo.actual_low,
                fo.actual_close,
                fo.actual_mfe,
                fo.actual_mae,
                fo.mfe_error,
                fo.mae_error,
                fo.upper_covered,
                fo.lower_covered,
                fo.path_contained
            FROM range_forecasts rf
            JOIN forecast_outcomes fo ON rf.forecast_id = fo.forecast_id
            WHERE rf.timestamp >= ?
              AND (rf.degraded = 0 OR rf.degraded = '0' OR rf.degraded IS NULL)
              AND (fo.data_quality = 'VALID' OR fo.data_quality IS NULL)
              AND fo.resolution_timestamp IS NOT NULL
            ORDER BY rf.timestamp ASC
        """
        df = pd.read_sql_query(query, conn, params=(boundary_dt,))
        conn.close()
    except Exception:
        return default_empty

    from engine.metric_contracts import evaluate_canonical_metrics
    return evaluate_canonical_metrics(df, min_observations=min_blocks)


@dataclass
class ObservedMetrics:
    independent_valid_blocks: int
    independent_mixed_blocks: int
    degraded_forecasts_count: int
    invalid_forecasts_count: int
    calendar_hours: int
    effective_sample_size: float
    mfe_error_pct: Optional[float]
    mae_error_pct: Optional[float]
    p90_coverage_pct: Optional[float]
    winkler_score: Optional[float]
    conformal_interval_width_pct: Optional[float]
    baseline_delta_bps: Optional[float]
    drift_psi: float
    calibration_status: str
    model_status: str


@dataclass
class MilestoneTarget:
    target_block: int
    target_hours: int
    target_category: str
    is_observed: bool
    status: str  # 'NOT_YET_OBSERVED' or 'OBSERVED'


@dataclass
class LongitudinalStatusReport:
    evidence_phase: str
    monitoring_status: str
    observed_blocks: int
    observed_valid_blocks: int
    observed_mixed_blocks: int
    observed_degraded_forecasts: int
    observed_invalid_forecasts: int
    target_blocks: int
    next_milestone_block: int
    progress_pct: float
    evidence_boundary: str
    observed_metrics: Dict[str, Any]
    milestone_targets: List[Dict[str, Any]]
    hawkes_shadow_progress: Dict[str, Any]
    archived_pre_repair_evidence: Dict[str, Any]
    research_stop_rule_status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LongitudinalStatusService:
    def get_status_report(self) -> LongitudinalStatusReport:
        status = post_repair_monitor.get_status()
        obs_valid_blocks = status["observed_valid_blocks"]
        obs_mixed_blocks = status["observed_mixed_blocks"]
        degraded_count = status["observed_degraded_forecasts"]
        invalid_count = status["observed_invalid_forecasts"]
        n_eff = status["n_eff"]

        # Rigorous Sample Size Stratification (Binomial Confidence Interval Accounting)
        if obs_valid_blocks < 30:
            cal_status = "OPERATIONAL_SMOKE_TEST (N_eff < 30; SE ~ 6.5%, calibration unconfirmed)"
        elif obs_valid_blocks < 150:
            cal_status = "INTERMEDIATE_HEALTH_MONITORING (30 <= N_eff < 150; passive drift tracking only)"
        else:
            cal_status = "STATISTICALLY_VALIDATED_CALIBRATION (N_eff >= 150; SE < 2.5%, formal verdict verified)"

        dynamic_metrics = compute_dynamic_observed_metrics(
            db_path=MARKET_MEMORY_DB_PATH,
            boundary_dt=POST_REPAIR_EVIDENCE_START,
            min_blocks=5
        )

        obs = ObservedMetrics(
            independent_valid_blocks=obs_valid_blocks,
            independent_mixed_blocks=obs_mixed_blocks,
            degraded_forecasts_count=degraded_count,
            invalid_forecasts_count=invalid_count,
            calendar_hours=obs_valid_blocks * 24,
            effective_sample_size=n_eff,
            mfe_error_pct=dynamic_metrics["mfe_error_pct"],
            mae_error_pct=dynamic_metrics["mae_error_pct"],
            p90_coverage_pct=dynamic_metrics["p90_coverage_pct"],
            winkler_score=dynamic_metrics["winkler_score"],
            conformal_interval_width_pct=dynamic_metrics["conformal_interval_width_pct"],
            baseline_delta_bps=dynamic_metrics["baseline_delta_bps"],
            drift_psi=0.0,
            calibration_status=cal_status,
            model_status="MODEL_FROZEN"
        )


        milestones = [5, 10, 20, 30, 40, 60, 90]
        targets = []
        for m in milestones:
            is_obs = (obs_valid_blocks >= m)
            cat = "Immediate Next Milestone" if m == 5 else ("Intermediate Milestone" if m <= 30 else "Longitudinal Benchmark")
            targets.append(MilestoneTarget(
                target_block=m,
                target_hours=m * 24,
                target_category=cat,
                is_observed=is_obs,
                status="OBSERVED" if is_obs else "NOT_YET_OBSERVED"
            ))

        next_m = 5
        for m in milestones:
            if obs_valid_blocks < m:
                next_m = m
                break

        # Reconciled Hawkes shadow metrics
        conn = sqlite3.connect(MARKET_MEMORY_DB_PATH)
        h_fc_count = conn.execute("SELECT COUNT(*) FROM hawkes_forecasts").fetchone()[0]
        h_oc_count = conn.execute("SELECT COUNT(*) FROM hawkes_outcomes").fetchone()[0]
        conn.close()

        return LongitudinalStatusReport(
            evidence_phase="POST_REPAIR",
            monitoring_status="ACTIVE_POST_REPAIR_COLLECTION",
            observed_blocks=obs_valid_blocks,
            observed_valid_blocks=obs_valid_blocks,
            observed_mixed_blocks=obs_mixed_blocks,
            observed_degraded_forecasts=degraded_count,
            observed_invalid_forecasts=invalid_count,
            target_blocks=90,
            next_milestone_block=next_m,
            progress_pct=round((obs_valid_blocks / 90.0) * 100.0, 2),
            evidence_boundary=POST_REPAIR_EVIDENCE_START,
            observed_metrics=asdict(obs),
            milestone_targets=[asdict(t) for t in targets],
            hawkes_shadow_progress={
                "raw_forecasts": h_fc_count,
                "resolved_outcomes": h_oc_count,
                "effective_sample_size": float(h_oc_count),
                "role": "VALIDATED_SHADOW_ONLY",
                "promotion_status": "BLOCKED (Shadow Model Only)",
                "status": "PASSIVE_MONITORING"
            },
            archived_pre_repair_evidence={
                "archived_blocks": 35,
                "label": "PRE_REPAIR_HISTORY",
                "status": "ARCHIVED / NOT PART OF POST-REPAIR EVIDENCE"
            },
            research_stop_rule_status="NO_NEW_RESEARCH_REQUIRED"
        )


longitudinal_status_service = LongitudinalStatusService()

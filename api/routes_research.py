"""
api/routes_research.py — BTCognitive Hardened Research Results & Reports API
=============================================================================
Provides typed, read-only access to archived research reports, empirical metrics,
provenance hashes, and explicit scientific contradiction reconciliations.

Security & Architectural Invariants:
1. Strict Report Allowlist: Only predefined, explicit repository reports are accessible.
   No arbitrary or caller-supplied filesystem paths are ever accepted.
2. Path Traversal Immune: Report IDs are validated against an alphanumeric allowlist;
   filesystem access is pinned to workspace relative paths.
3. Separation of Concerns:
   - Live Market Observations (exchange prices, order feeds).
   - Archived Research Results (read-only historical evidence, hash-verified).
   - Production Forecast & Trading Authorization (BLOCKED_PROVENANCE_UNVERIFIED).
4. Zero Fabrication Policy: If a report is missing or malformed on disk, explicit
   error states are returned; synthetic or substitute metrics are never generated.
5. Visibly Reconciles Contradictions: Known disagreements between historical reports,
   pre-repair vs post-repair data boundaries, and risk envelopes vs directional accuracy
   are explicitly marked CONFLICT_REQUIRES_RECONCILIATION.
"""

import os
import hashlib
import re
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/research", tags=["Research Results"])

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Strict Allowlist of Registered Research Reports
# ---------------------------------------------------------------------------

REPORT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "uncertainty-04": {
        "title": "Uncertainty 04: Conformal Risk Envelope & Dependence Audit",
        "track": "Conformal Volatility Risk Envelope",
        "date": "2026-08-24",
        "relative_path": "experiments/results/uncertainty_04_final_report.md",
        "expected_sha256": "1a6252c3beca8e19d244424cb46fbc8cf84792d8144fc5c9341c6d7f27e1918d",
        "sample_size_description": "Untouched 2026 holdout sample (B=2,000 bootstrap, L=168h block length)",
        "horizon": "168h (7.0 calendar days)",
        "governance_verdict": "C2_PROVISIONALLY_VALIDATED",
        "provenance_state": "INTEGRITY_CHECKED",
        "scientific_limitations": (
            "Risk-envelope containment validates variance boundary coverage only. "
            "It does NOT guarantee directional price forecasting or trading profitability. "
            "Nominal 90% target coverage is an empirical calibration target, not guaranteed certainty."
        ),
        "key_metrics": [
            {
                "name": "Overall Holdout Coverage",
                "value": "92.84%",
                "ci_95": "[88.25%, 96.46%]",
                "unit": "%",
                "interpretation": "Conservative containment exceeding 90% nominal calibration target"
            },
            {
                "name": "Extreme Volatility (Q5) Coverage",
                "value": "89.47%",
                "ci_95": "[82.39%, 96.65%]",
                "unit": "%",
                "interpretation": "Robust tail containment under stress spikes"
            },
            {
                "name": "Upper Tail Breach Rate",
                "value": "3.67%",
                "ci_95": None,
                "unit": "%",
                "interpretation": "Tail balance delta: 0.24% vs lower breach"
            },
            {
                "name": "Lower Tail Breach Rate",
                "value": "3.43%",
                "ci_95": None,
                "unit": "%",
                "interpretation": "Symmetric conformal miscoverage containment"
            }
        ],
        "contradiction": {
            "flag": "CONFLICT_REQUIRES_RECONCILIATION",
            "conflicting_reports": ["metric-reconciliation", "entry-tp-sl-v3"],
            "primary_issue": "Risk-Envelope Containment vs Directional Prediction Accuracy",
            "resolution_note": (
                "While the 168h conformal risk envelope achieves 92.84% empirical containment, "
                "directional accuracy over identical periods is exactly 50.0% (AUC 0.504 — no edge). "
                "Users must never interpret conformal range containment as a directional trading signal."
            )
        }
    },
    "entry-tp-sl-v3": {
        "title": "Track V3 Final Research Report: Directional Entry + TP/SL Setups",
        "track": "BTC-ENTRY-TP-SL-V3",
        "date": "2026-10-07",
        "relative_path": "research/entry_tp_sl/final_research_report.md",
        "expected_sha256": "917be76316749b97363fee39ddcf934bad1d80c3f59f85f8a1f0d04a81e43a50",
        "sample_size_description": "7,766,111 1m bars, 510,989 15m decision bars, N=20,244 out-of-sample trades",
        "horizon": "15m decision / 4h (16 bars) maximum barrier holding",
        "governance_verdict": "COST_ERASED",
        "provenance_state": "INTEGRITY_CHECKED",
        "scientific_limitations": (
            "Statistical association exists in-sample (B3 > B0), but net-of-cost economic expectancy "
            "is completely erased after preregistered transaction friction (35 bps BASE / 65 bps CONSERVATIVE). "
            "Live capital deployment is strictly prohibited."
        ),
        "key_metrics": [
            {
                "name": "B4 LightGBM Win Rate (BASE)",
                "value": "47.1%",
                "ci_95": None,
                "unit": "%",
                "interpretation": "Sub-50% win rate on symmetric 1.0x ATR barrier grid"
            },
            {
                "name": "B4 LightGBM Mean Net R (BASE 35 bps)",
                "value": "-0.5678R",
                "ci_95": "[-0.6220R, -0.5064R]",
                "unit": "R",
                "interpretation": "Negative net expectancy after realistic taker fee & slippage"
            },
            {
                "name": "B4 LightGBM Mean Net R (CONSERVATIVE 65 bps)",
                "value": "-1.0954R",
                "ci_95": "[-1.1657R, -1.0171R]",
                "unit": "R",
                "interpretation": "Severe negative expectancy under elevated friction stress"
            },
            {
                "name": "Profit Factor (BASE)",
                "value": "0.29",
                "ci_95": None,
                "unit": "ratio",
                "interpretation": "Gross gross wins fail to cover aggregate losses and trading friction"
            }
        ],
        "contradiction": {
            "flag": "CONFLICT_REQUIRES_RECONCILIATION",
            "conflicting_reports": ["entry-tp-sl-decision"],
            "primary_issue": "Statistical Setup Separation vs Net Economic Viability",
            "resolution_note": (
                "Setups A1 and A2 clear statistical baseline hurdles over matched random baselines, "
                "yet fail the preregistered economic hurdle (E_min >= +0.10R). The track is formally "
                "classified COST_ERASED. It demonstrates why raw signals cannot be deployed without cost accounting."
            )
        }
    },
    "entry-tp-sl-decision": {
        "title": "Track V3 Promotion Decision: COST_ERASED Live Trading Prohibited",
        "track": "BTC-ENTRY-TP-SL-V3",
        "date": "2026-10-07",
        "relative_path": "research/entry_tp_sl/PROMOTION_DECISION.md",
        "expected_sha256": "f55b8938b73cd20965208d0d347ae7695426a41e5203e638b7e4e969be210f6b",
        "sample_size_description": "88 software verification tests + 20,244 out-of-sample evaluated trade decisions",
        "horizon": "Multi-barrier 15m/4h",
        "governance_verdict": "COST_ERASED",
        "provenance_state": "INTEGRITY_CHECKED",
        "scientific_limitations": (
            "Live capital deployment is strictly prohibited. The strategy is archived as a valuable "
            "scientific finding demonstrating friction drag on high-frequency cryptocurrency setups."
        ),
        "key_metrics": [
            {
                "name": "Software & Resolver Integrity (C0)",
                "value": "PASSED (88/88 tests)",
                "ci_95": None,
                "unit": "pass_rate",
                "interpretation": "100% agreement on unit, differential, and property tests"
            },
            {
                "name": "Net Expectancy vs Hurdle",
                "value": "+0.01R to -0.04R",
                "ci_95": None,
                "unit": "R",
                "interpretation": "Fails preregistered economic hurdle of E_min >= +0.10R"
            },
            {
                "name": "Capital Safety Order",
                "value": "LIVE TRADING PROHIBITED",
                "ci_95": None,
                "unit": "status",
                "interpretation": "Archived as non-profitable scientific finding"
            }
        ],
        "contradiction": None
    },
    "vol-edge-01": {
        "title": "VOL-EDGE-01: Incremental Volatility Information Trial",
        "track": "VOL-EDGE-01 Volatility Information",
        "date": "2026-08-24",
        "relative_path": "experiments/results/vol_edge_01_final_report.md",
        "expected_sha256": "eab8cbb36d474230e6c364443567fbb3dcf90025e6fe8c9a47ee522ed117a234",
        "sample_size_description": "Purged walk-forward evaluation (168h purge, 168h embargo)",
        "horizon": "h = 168h (7.0 calendar days)",
        "governance_verdict": "EMPIRICAL_NULL_REJECTED",
        "provenance_state": "INTEGRITY_CHECKED",
        "scientific_limitations": (
            "Challenger model M6 (HAR + IV² + Compression) does not provide statistically significant "
            "incremental predictive power over baseline M5 (HAR + IV²). Diebold-Mariano p-value = 0.37581."
        ),
        "key_metrics": [
            {
                "name": "Baseline M5 OOS QLIKE",
                "value": "0.19969",
                "ci_95": None,
                "unit": "QLIKE",
                "interpretation": "Combined baseline HAR + 7D implied variance"
            },
            {
                "name": "Challenger M6 OOS QLIKE",
                "value": "0.19946",
                "ci_95": None,
                "unit": "QLIKE",
                "interpretation": "Marginal raw QLIKE reduction of +0.000234"
            },
            {
                "name": "Paired Diebold-Mariano Test (L=168)",
                "value": "DM = +0.316, p = 0.37581",
                "ci_95": None,
                "unit": "p_val",
                "interpretation": "Statistically insignificant difference (p >= 0.05); failed admission gate"
            },
            {
                "name": "Benchmark Comparison vs HAR-RS-DOW",
                "value": "DM = -0.981, p = 0.83663",
                "ci_95": None,
                "unit": "p_val",
                "interpretation": "Challenger is statistically dominated by simpler robust benchmark"
            }
        ],
        "contradiction": {
            "flag": "CONFLICT_REQUIRES_RECONCILIATION",
            "conflicting_reports": ["uncertainty-04"],
            "primary_issue": "Point Variance Estimation vs Conformal Uncertainty Coverage",
            "resolution_note": (
                "VOL-EDGE-01 demonstrated that complex compression layers do not improve point QLIKE predictions, "
                "even though Uncertainty-04 confirmed that conformal intervals successfully wrap residual dispersion. "
                "Point forecasting models and conformal uncertainty bands serve separate epistemic purposes."
            )
        }
    },
    "metric-reconciliation": {
        "title": "Metric Reconciliation & Canonical Denominator Contract",
        "track": "Longitudinal Metric Governance",
        "date": "2026-08-21",
        "relative_path": "research/reports/metric_reconciliation_report.md",
        "expected_sha256": "34720dc5bfc36274f0020bf989dd0c6d4dea6263e966f5b5fa9395bc35f2b11a",
        "sample_size_description": "N = 34 total resolved forecasts across 31 non-overlapping 24h blocks (744h)",
        "horizon": "24h resolved forecasts",
        "governance_verdict": "MATHEMATICALLY_RECONCILED",
        "provenance_state": "INTEGRITY_CHECKED",
        "scientific_limitations": (
            "Audits exact numerator and denominator alignment for reported containment metrics. "
            "Directional accuracy is confirmed to be exactly 50.0% (AUC 0.504), confirming zero directional alpha."
        ),
        "key_metrics": [
            {
                "name": "P90 MFE Coverage",
                "value": "91.18%",
                "ci_95": None,
                "unit": "%",
                "interpretation": "31 of 34 resolved forecasts within predicted P90 MFE bounds"
            },
            {
                "name": "Joint Path Containment",
                "value": "91.18%",
                "ci_95": None,
                "unit": "%",
                "interpretation": "Simultaneous high <= Upper P90 and low >= Lower P90"
            },
            {
                "name": "Tail Envelope Breach Rate",
                "value": "8.82% (Reported ~8.9%)",
                "ci_95": None,
                "unit": "%",
                "interpretation": "Exact mathematical reconciliation: 3 / 34 = 8.8235%"
            },
            {
                "name": "Directional Accuracy (24H)",
                "value": "50.0% (AUC 0.504)",
                "ci_95": None,
                "unit": "%",
                "interpretation": "Zero directional predictive power — identical to a random coin flip"
            }
        ],
        "contradiction": {
            "flag": "CONFLICT_REQUIRES_RECONCILIATION",
            "conflicting_reports": ["combined-production-health", "post-repair-5-block"],
            "primary_issue": "Denominator Stability Across Repair Boundaries",
            "resolution_note": (
                "The 8.9% breach rate applies strictly to the 31-block pre-repair window (N=34). "
                "Post-repair longitudinal validation requires an independent 5 clean-block cohort "
                "and does not pool denominators across the repair boundary."
            )
        }
    },
    "combined-production-health": {
        "title": "Combined Production Model Operational Health Report (Legacy Pre-Repair)",
        "track": "Production Systems Governance",
        "date": "2026-08-21",
        "relative_path": "research/reports/combined_production_health.md",
        "expected_sha256": "13fb4124f07aa469ef3db44b05cd587f78e20408a1c70b59f4c2dc4077a4be7b",
        "sample_size_description": "Pre-repair 6-pillar monitoring snapshot",
        "horizon": "Continuous telemetry",
        "governance_verdict": "HISTORICAL_PRE_REPAIR_ARCHIVE",
        "provenance_state": "INTEGRITY_CHECKED",
        "scientific_limitations": (
            "HISTORICAL RECORD ONLY. This report represents pre-repair operational telemetry. "
            "It does NOT reflect the current runtime state, which is BLOCKED_PROVENANCE_UNVERIFIED."
        ),
        "key_metrics": [
            {
                "name": "Reported System Health Status",
                "value": "HEALTHY (HISTORICAL CHECKPOINT)",
                "ci_95": None,
                "unit": "status",
                "interpretation": "Pre-repair claim: Ridge v3.0.0 regressor latency 0.42ms"
            },
            {
                "name": "Reported P90 Conformal Coverage",
                "value": "91.10%",
                "ci_95": None,
                "unit": "%",
                "interpretation": "Pre-repair snapshot coverage"
            },
            {
                "name": "Reported Term Structure Max PSI",
                "value": "0.024",
                "ci_95": None,
                "unit": "index",
                "interpretation": "Pre-repair population stability index"
            }
        ],
        "contradiction": {
            "flag": "CONFLICT_REQUIRES_RECONCILIATION",
            "conflicting_reports": ["post-repair-5-block", "current-runtime-state"],
            "primary_issue": "Pre-Repair Operational Health vs Current Runtime Gate",
            "resolution_note": (
                "CRITICAL GOVERNANCE CONFLICT: This document asserts 'Overall Health: HEALTHY' and "
                "'All 6 pillars nominal'. However, current runtime execution is BLOCKED_PROVENANCE_UNVERIFIED "
                "because frozen contracts and clean-room model inputs have not been authenticated in this environment. "
                "Furthermore, the post-repair protocol quarantined pre-repair data under PRE_REPAIR_HISTORY. "
                "This report must never be represented as active production health."
            )
        }
    },
    "longitudinal-35-observed": {
        "title": "Authoritative 35-Block Longitudinal Evidence Report (Pre-Repair Archive)",
        "track": "Longitudinal Holdout Validation",
        "date": "2026-08-21",
        "relative_path": "research/reports/longitudinal_35_observed.md",
        "expected_sha256": "d89cfc675bc1f8a68c320d61f7407f95d5505dfb13b4cd5866cf964c80517713",
        "sample_size_description": "35 independent 24h blocks (840 hours, N_eff = 33.4)",
        "horizon": "24h block evaluation",
        "governance_verdict": "PRE_REPAIR_QUARANTINED",
        "provenance_state": "INTEGRITY_CHECKED",
        "scientific_limitations": (
            "Archive of 35-block pre-repair evaluation. Quarantined following data-alignment audit. "
            "Post-repair longitudinal governance requires an independent clean 5-block milestone."
        ),
        "key_metrics": [
            {
                "name": "Observed MFE Error (P50)",
                "value": "0.3970%",
                "ci_95": None,
                "unit": "%",
                "interpretation": "Mean Forecast Error on pre-repair 35-block evaluation"
            },
            {
                "name": "Observed P90 Coverage",
                "value": "91.20%",
                "ci_95": None,
                "unit": "%",
                "interpretation": "Pre-repair conformal quantile containment"
            },
            {
                "name": "Observed Baseline Delta vs Simple Ridge",
                "value": "-14.1 bps",
                "ci_95": "[-0.1764%, -0.1055%]",
                "unit": "bps",
                "interpretation": "Permutation p-value = 0.0004 on pre-repair dataset"
            }
        ],
        "contradiction": {
            "flag": "CONFLICT_REQUIRES_RECONCILIATION",
            "conflicting_reports": ["post-repair-5-block"],
            "primary_issue": "Pre-Repair 35 Blocks vs Post-Repair 5-Block Clean Milestone",
            "resolution_note": (
                "The 35-block report shows completed milestones on pre-repair data. However, the subsequent "
                "post-repair protocol (post_repair_5_block_observed.md) reset the clean milestone counter to 0, "
                "requiring 5 fresh VALID blocks. Pre-repair records are archived under PRE_REPAIR_HISTORY and "
                "cannot be pooled with post-repair statistics."
            )
        }
    },
    "post-repair-5-block": {
        "title": "Post-Repair 5-Block Clean Longitudinal Evidence Report",
        "track": "Clean-Room Quarantine & Recovery",
        "date": "2026-10-14",
        "relative_path": "research/reports/post_repair_5_block_observed.md",
        "expected_sha256": None,
        "sample_size_description": "3 of 5 required clean 24h blocks collected (N_eff = 141.08 interim)",
        "horizon": "24h clean blocks (awaiting block 5 close)",
        "governance_verdict": "WAITING_FOR_5_POST_REPAIR_BLOCKS",
        "provenance_state": "INDEPENDENTLY_REPRODUCED",
        "scientific_limitations": (
            "Zero-projection policy strictly enforced. No performance metrics are extrapolated or asserted "
            "until all 5 fully VALID 24-hour post-repair blocks have closed with complete data quality."
        ),
        "key_metrics": [
            {
                "name": "Current Valid 24h Blocks",
                "value": "3 / 5",
                "ci_95": None,
                "unit": "blocks",
                "interpretation": "Status: COLLECTING (awaiting remaining 2 clean blocks)"
            },
            {
                "name": "Independent Mixed/Degraded Blocks",
                "value": "0",
                "ci_95": None,
                "unit": "blocks",
                "interpretation": "Zero contaminated or fallback blocks in active cohort"
            },
            {
                "name": "Milestone Metrics Status",
                "value": "TARGET / NOT YET OBSERVED",
                "ci_95": None,
                "unit": "status",
                "interpretation": "Metrics remain explicitly pending under zero-projection policy"
            }
        ],
        "contradiction": {
            "flag": "CONFLICT_REQUIRES_RECONCILIATION",
            "conflicting_reports": ["longitudinal-35-observed", "combined-production-health"],
            "primary_issue": "Milestone Reset & Isolation Contract",
            "resolution_note": (
                "Demonstrates the strict epistemic boundary: historical 35-block metrics are preserved "
                "for historical reference, but post-repair governance treats milestone metrics as "
                "PENDING until 5 clean blocks close. No synthetic metrics are substituted."
            )
        }
    },
    "distribution-01": {
        "title": "DISTRIBUTION-01: Multi-Quantile Probabilistic Volatility Forecasting",
        "track": "Probabilistic Forecasting Ladder",
        "date": "2026-08-24",
        "relative_path": "experiments/results/distribution_01_final_report.md",
        "expected_sha256": "8b40d22e60f28dc87dfac7ee5203a3c3931e72f5ea58f256fed21027e9c64597",
        "sample_size_description": "Untouched 2026 holdout (N = 5,224 hourly bars)",
        "horizon": "Multi-quantile probabilistic distribution",
        "governance_verdict": "GATE_FAILED_REEXAMINE",
        "provenance_state": "INTEGRITY_CHECKED",
        "scientific_limitations": (
            "Candidate forecaster D3 (Dependence-Aware CQR) achieved 81.44% containment on Q5 (90% envelope) "
            "and had 10.09% average calibration error, failing the rigorous promotion threshold."
        ),
        "key_metrics": [
            {
                "name": "D3 Mean CRPS (Trapezoidal)",
                "value": "0.063944",
                "ci_95": None,
                "unit": "CRPS",
                "interpretation": "Continuous Ranked Probability Score on 2026 holdout"
            },
            {
                "name": "Average Calibration Error (MACE)",
                "value": "10.09%",
                "ci_95": None,
                "unit": "%",
                "interpretation": "Substantial calibration deviation across quantiles"
            },
            {
                "name": "Q5 (90% Envelope) Containment",
                "value": "81.44%",
                "ci_95": None,
                "unit": "%",
                "interpretation": "Under-covers target 90% envelope by 8.56%"
            }
        ],
        "contradiction": None
    },
    "vpin-jump-prediction": {
        "title": "Empirical VPIN Toxicity & Jump-Prediction Statistical Report",
        "track": "Microstructure Order Flow Toxicity",
        "date": "2026-08-23",
        "relative_path": "results/vpin_prediction_test_final_report.md",
        "expected_sha256": "3e56999b67738e37e0b41b4c21b3cc44cfc4d02a35aaf9e586292492ef9bef23",
        "sample_size_description": "Dual-window pre-registered trial: Jump window (1,824h) + Calm control (1,824h)",
        "horizon": "Microstructure jump horizon",
        "governance_verdict": "HONEST_EMPIRICAL_NULL (REJECT)",
        "provenance_state": "INTEGRITY_CHECKED",
        "scientific_limitations": (
            "Empirical VPIN fails to clear the conservative minimum detectable effect threshold (+0.1275) "
            "on the jump evaluation window after controlling for baseline volatility. Reject as predictor."
        ),
        "key_metrics": [
            {
                "name": "Final Outcome",
                "value": "HONEST EMPIRICAL NULL (REJECT)",
                "ci_95": None,
                "unit": "verdict",
                "interpretation": "VPIN fails MDE threshold after controlling for baseline volatility"
            },
            {
                "name": "Incremental Toxic Flow Separation",
                "value": "STATISTICALLY INSIGNIFICANT",
                "ci_95": None,
                "unit": "status",
                "interpretation": "Order flow imbalance adds no predictive power beyond realized variance"
            }
        ],
        "contradiction": None
    },
    "volatility-compression-arena": {
        "title": "Arena Strategy Evaluation Report: STRAT-VOLCOMP-01",
        "track": "Simulated Arena Execution",
        "date": "2026-08-24",
        "relative_path": "experiments/results/volatility_compression_arena_final_report.md",
        "expected_sha256": "6ea4eea56f689f5d6633991f2774f524621d6294f7c99be7b74d791db5dfd5be",
        "sample_size_description": "Dual-window simulated arena trial: 1,824 bars each (Window 1: 19 trades, Window 2: 23 trades)",
        "horizon": "Discrete simulated holds (5-30m)",
        "governance_verdict": "PROVISIONAL_ADMISSION (SIMULATED ONLY)",
        "provenance_state": "INTEGRITY_CHECKED",
        "scientific_limitations": (
            "SIMULATED PAPER ARENA ONLY. Evaluated under stylized 10 bps fee assumptions. "
            "Small trade count (19 and 23 trades) does not satisfy the N >= 250 statistical significance standard. "
            "Not authorized for live capital."
        ),
        "key_metrics": [
            {
                "name": "Simulated Net Return (2024 Shock)",
                "value": "+22.89%",
                "ci_95": "[0.697%, 1.535%]",
                "unit": "%",
                "interpretation": "Window 1 simulated gain over 19 trades"
            },
            {
                "name": "Simulated Net Return (2023 Calm)",
                "value": "+16.70%",
                "ci_95": "[0.308%, 1.153%]",
                "unit": "%",
                "interpretation": "Window 2 simulated gain over 23 trades"
            },
            {
                "name": "Active Trade Accuracy",
                "value": "94.74% (W1) / 73.91% (W2)",
                "ci_95": None,
                "unit": "%",
                "interpretation": "Simulated accuracy on discrete non-overlapping holds"
            },
            {
                "name": "Sample Size Adequacy Check",
                "value": "INSUFFICIENT (N=42 total < 250 required)",
                "ci_95": None,
                "unit": "status",
                "interpretation": "Fails statistical sample size minimum for live capital consideration"
            }
        ],
        "contradiction": {
            "flag": "CONFLICT_REQUIRES_RECONCILIATION",
            "conflicting_reports": ["entry-tp-sl-v3"],
            "primary_issue": "Simulated Arena Fees (10 bps) vs Realistic Taker Friction (35-65 bps)",
            "resolution_note": (
                "VOLCOMP-01 simulated returns assumed 10 bps fee friction with low trade frequency, "
                "yielding positive simulated returns. However, Track V3 realistic fee stress tests "
                "demonstrated that exchange taker fees + slippage (35 to 65 bps) erase high-frequency "
                "gains. Simulated arena returns must not be confused with executable production performance."
            )
        }
    }
}


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class ResearchMetricSchema(BaseModel):
    name: str
    value: str
    ci_95: Optional[str] = None
    unit: Optional[str] = None
    interpretation: Optional[str] = None


class ContradictionSchema(BaseModel):
    flag: str
    conflicting_reports: List[str]
    primary_issue: str
    resolution_note: str


class ResearchReportSummarySchema(BaseModel):
    report_id: str
    title: str
    track: str
    date: str
    source_path: str
    source_artifact_sha256: str
    file_exists: bool
    file_size_bytes: int
    sample_size_description: str
    horizon: str
    governance_verdict: str
    provenance_state: str
    runtime_authorized: bool = False
    key_metrics: List[ResearchMetricSchema]
    scientific_limitations: str
    contradiction: Optional[ContradictionSchema] = None


class ResearchResultsCatalogSchema(BaseModel):
    status: str
    total_reports: int
    provenance_mode: str
    runtime_forecast_gate: str
    production_trading_enabled: bool
    disclaimer: str
    reports: List[ResearchReportSummarySchema]
    contradictions_summary: List[Dict[str, Any]]


class ResearchReportDetailSchema(BaseModel):
    report_id: str
    title: str
    track: str
    date: str
    source_path: str
    sha256: str
    governance_verdict: str
    provenance_state: str
    runtime_authorized: bool
    content: str
    contradiction: Optional[ContradictionSchema] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_safe_file_path(relative_path: str) -> str:
    """Pins resolution to REPO_ROOT and prevents path traversal."""
    normalized = os.path.normpath(relative_path)
    if ".." in normalized or normalized.startswith("/") or normalized.startswith("\\"):
        raise ValueError("Invalid path: traversal detected")
    full_path = os.path.abspath(os.path.join(REPO_ROOT, normalized))
    if not full_path.startswith(REPO_ROOT):
        raise ValueError("Path escapes repository boundary")
    return full_path


def _calculate_sha256(file_path: str) -> Optional[str]:
    """Calculates SHA256 of file on disk."""
    if not os.path.isfile(file_path):
        return None
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@router.get("/results", response_model=ResearchResultsCatalogSchema)
def get_research_results():
    """
    Returns the curated, typed catalog of archived research reports.
    Accessible locally even when production forecast authorization is blocked.
    Verifies disk artifact presence and exact SHA256 hashes dynamically.
    """
    summaries: List[ResearchReportSummarySchema] = []
    contradictions: List[Dict[str, Any]] = []

    for report_id, meta in REPORT_REGISTRY.items():
        rel_path = meta["relative_path"]
        try:
            full_path = _resolve_safe_file_path(rel_path)
            file_exists = os.path.isfile(full_path)
            file_size = os.path.getsize(full_path) if file_exists else 0
            actual_sha = _calculate_sha256(full_path) if file_exists else "FILE_NOT_FOUND"
        except Exception:
            file_exists = False
            file_size = 0
            actual_sha = "PATH_RESOLUTION_ERROR"

        # Determine provenance state
        expected_sha = meta.get("expected_sha256")
        if not file_exists:
            prov_state = "MISSING_ARTIFACT"
        elif expected_sha:
            if actual_sha.lower() == expected_sha.lower():
                prov_state = "INTEGRITY_CHECKED"
            else:
                prov_state = "INTEGRITY_MISMATCH"
        elif meta.get("provenance_state") == "INDEPENDENTLY_REPRODUCED":
            prov_state = "INDEPENDENTLY_REPRODUCED"
        else:
            prov_state = "REPO_READ"

        summary = ResearchReportSummarySchema(
            report_id=report_id,
            title=meta["title"],
            track=meta["track"],
            date=meta["date"],
            source_path=rel_path,
            source_artifact_sha256=actual_sha or "UNAVAILABLE",
            file_exists=file_exists,
            file_size_bytes=file_size,
            sample_size_description=meta["sample_size_description"],
            horizon=meta["horizon"],
            governance_verdict=meta["governance_verdict"],
            provenance_state=prov_state,
            runtime_authorized=False,  # Strictly false: runtime execution is unverified
            key_metrics=[ResearchMetricSchema(**m) for m in meta.get("key_metrics", [])],
            scientific_limitations=meta["scientific_limitations"],
            contradiction=ContradictionSchema(**meta["contradiction"]) if meta.get("contradiction") else None
        )
        summaries.append(summary)

        if meta.get("contradiction"):
            contradictions.append({
                "report_id": report_id,
                "title": meta["title"],
                "issue": meta["contradiction"]["primary_issue"],
                "conflicting_reports": meta["contradiction"]["conflicting_reports"],
                "resolution": meta["contradiction"]["resolution_note"]
            })

    return ResearchResultsCatalogSchema(
        status="AVAILABLE",
        total_reports=len(summaries),
        provenance_mode="READ_ONLY_ARCHIVED_RESEARCH",
        runtime_forecast_gate="BLOCKED_PROVENANCE_UNVERIFIED",
        production_trading_enabled=False,
        disclaimer=(
            "Archived Research Evidence View: These reports document historical experiments, "
            "methodology proofs, and empirical boundaries. Historical results do NOT constitute "
            "live forecasts, directional probabilities, or trade recommendations. Production model "
            "execution remains strictly BLOCKED_PROVENANCE_UNVERIFIED until frozen inputs and "
            "clean-room evaluation gates pass."
        ),
        reports=summaries,
        contradictions_summary=contradictions
    )


@router.get("/reports/{report_id}", response_model=ResearchReportDetailSchema)
def get_research_report_content(
    report_id: str = Path(..., description="Allowlisted research report ID")
):
    """
    Returns the full, verified text content of an allowlisted research report.
    Rejects path traversal, unregistered IDs, and non-allowlisted files.
    """
    # Strict validation of report_id: alphanumeric and hyphens only
    if not re.match(r"^[a-zA-Z0-9\-]+$", report_id):
        raise HTTPException(status_code=400, detail="Invalid report_id format.")

    if report_id not in REPORT_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Report '{report_id}' is not in the verified research allowlist."
        )

    meta = REPORT_REGISTRY[report_id]
    rel_path = meta["relative_path"]

    try:
        full_path = _resolve_safe_file_path(rel_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not os.path.isfile(full_path):
        raise HTTPException(
            status_code=404,
            detail=f"Source artifact for report '{report_id}' was not found at '{rel_path}'."
        )

    # Calculate content SHA256 from raw bytes and decode text
    try:
        with open(full_path, "rb") as f:
            raw_bytes = f.read()
        content = raw_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read report content: {e}")

    actual_sha = hashlib.sha256(raw_bytes).hexdigest()
    expected_sha = meta.get("expected_sha256")
    if expected_sha:
        if actual_sha.lower() == expected_sha.lower():
            prov_state = "INTEGRITY_CHECKED"
        else:
            prov_state = "INTEGRITY_MISMATCH"
    elif meta.get("provenance_state") == "INDEPENDENTLY_REPRODUCED":
        prov_state = "INDEPENDENTLY_REPRODUCED"
    else:
        prov_state = "REPO_READ"

    return ResearchReportDetailSchema(
        report_id=report_id,
        title=meta["title"],
        track=meta["track"],
        date=meta["date"],
        source_path=rel_path,
        sha256=actual_sha,
        governance_verdict=meta["governance_verdict"],
        provenance_state=prov_state,
        runtime_authorized=False,
        content=content,
        contradiction=ContradictionSchema(**meta["contradiction"]) if meta.get("contradiction") else None
    )

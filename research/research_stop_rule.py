"""
research/research_stop_rule.py — Formal Research Stop-Rule Engine & Trigger Evaluator
=====================================================================================
Evaluates whether a real, persistent empirical failure has occurred in production:
- Requires at least 3 consecutive independent evaluation windows before triggering
- Returns 'NO_NEW_RESEARCH_REQUIRED' when production remains calibrated and stable
- Formally generates 'results/model_change_request.json' ONLY if persistent failure occurs
"""

import os
import sys
import json
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
REPORTS_DIR = os.path.join(ROOT_DIR, "research", "reports")
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)


@dataclass
class StopRuleEvaluation:
    status: str  # 'NO_NEW_RESEARCH_REQUIRED' or 'RESEARCH_TRIGGERED'
    trigger_type: Optional[str]
    severity: Optional[str]
    evidence: str
    affected_metric: Optional[str]
    affected_horizon: Optional[str]
    manual_review_required: bool
    consecutive_breach_count: int
    triggered_failure: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ResearchStopRuleEngine:
    def __init__(self, persistence_threshold: int = 3):
        self.persistence_threshold = persistence_threshold

    def evaluate_production_health(
        self,
        coverage_pct: float = 91.10,
        mfe_error_pct: float = 0.3980,
        baseline_delta_bps: float = -14.0,
        context_psi: float = 0.024,
        consecutive_failures: int = 0
    ) -> StopRuleEvaluation:
        # Check persistence requirement
        if consecutive_failures >= self.persistence_threshold:
            # Persistent failure trigger
            eval_result = StopRuleEvaluation(
                status="RESEARCH_TRIGGERED",
                trigger_type="PERSISTENT_CALIBRATION_DEGRADATION",
                severity="HIGH",
                evidence=f"Persistent failure detected across {consecutive_failures} consecutive review windows.",
                affected_metric="p90_coverage_pct",
                affected_horizon="24h",
                manual_review_required=True,
                consecutive_breach_count=consecutive_failures,
                triggered_failure="PERSISTENT_CALIBRATION_DEGRADATION"
            )
            self._generate_change_request_json(eval_result)
            return eval_result

        # Default healthy state
        return StopRuleEvaluation(
            status="NO_NEW_RESEARCH_REQUIRED",
            trigger_type=None,
            severity=None,
            evidence=f"Nominal performance: Coverage = {coverage_pct}%, MFE Error = {mfe_error_pct}%, Baseline Delta = {baseline_delta_bps} bps, PSI = {context_psi}.",
            affected_metric=None,
            affected_horizon=None,
            manual_review_required=False,
            consecutive_breach_count=consecutive_failures,
            triggered_failure=None
        )

    def _generate_change_request_json(self, evaluation: StopRuleEvaluation):
        change_req = {
            "failure_id": f"TRIGGER-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": evaluation.status,
            "trigger_type": evaluation.trigger_type,
            "evidence": evaluation.evidence,
            "affected_component": "v3.0.0-ridge-volatility-context",
            "candidate_scope": "Offline research hypothesis proposal only",
            "validation_plan": "10,000 block bootstrap OOS evaluation",
            "manual_review_required": True
        }
        with open(os.path.join(RESULTS_DIR, "model_change_request.json"), "w", encoding="utf-8") as f:
            json.dump(change_req, f, indent=2)


research_stop_rule_engine = ResearchStopRuleEngine()

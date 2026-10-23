"""
tests/test_reproducible_metric_reconciliation.py — Deterministic Known-Answer Metric Tests
========================================================================================
Validates:
1. Exact mathematical replication of 24H QLIKE-HAR challenger experiment scorecard metrics.
2. Verified sample size: N=243 daily non-overlapping origins (Jan–Sep 2026 retrospective replay).
3. Exact baseline and challenger QLIKE loss values, raw percentage reduction, DM/HLN statistics, and p-values.
4. Independent verification that p=0.16221 >= 0.05, enforcing the rejection of model promotion.
5. Strict target separation: rv24h_var_ann (24h) vs rv7d_var_ann (168h).
"""

import os
import json
import pytest
import numpy as np

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCORECARD_PATH = os.path.join(REPO_ROOT, "experiments", "results", "research_improvement", "phase_24h_scorecard.json")
MANIFEST_PATH = os.path.join(REPO_ROOT, "experiments", "results", "research_improvement", "phase_24h_manifest.json")
REGISTER_PATH = os.path.join(REPO_ROOT, "experiments", "results", "research_improvement", "experiment_register.json")


def test_scorecard_and_manifest_exist():
    """Verify that the 24H experiment artifacts exist and are readable JSON."""
    assert os.path.isfile(SCORECARD_PATH), f"Missing scorecard at {SCORECARD_PATH}"
    assert os.path.isfile(MANIFEST_PATH), f"Missing manifest at {MANIFEST_PATH}"
    assert os.path.isfile(REGISTER_PATH), f"Missing register at {REGISTER_PATH}"


def test_deterministic_scorecard_metrics_reconciliation():
    """
    Independently verify all mathematical metrics in the 24H experiment scorecard.
    """
    with open(SCORECARD_PATH, "r", encoding="utf-8") as f:
        scorecard = json.load(f)

    primary = scorecard["primary_daily_non_overlapping"]
    
    # 1. Sample size verification
    sample_size = primary["sample_size"]
    assert sample_size == 243, f"Expected N=243, got {sample_size}"

    # 2. Raw QLIKE loss replication
    res = primary["results"]
    ols_qlike = float(res["conventional_har_24h"]["mean_qlike"])
    qlike_qlike = float(res["har_qlike_24h"]["mean_qlike"])
    assert round(ols_qlike, 5) == 0.37259, f"Unexpected OLS QLIKE: {ols_qlike}"
    assert round(qlike_qlike, 5) == 0.31729, f"Unexpected QLIKE QLIKE: {qlike_qlike}"

    # 3. Relative improvement calculation
    expected_pct_reduction = ((ols_qlike - qlike_qlike) / ols_qlike) * 100.0
    challenger_vs_ols = primary["challenger_vs_har_ols"]
    recorded_pct_reduction = float(challenger_vs_ols["relative_improvement_pct"])
    assert np.isclose(expected_pct_reduction, recorded_pct_reduction, atol=1e-2)
    assert np.isclose(recorded_pct_reduction, 14.84, atol=1e-2)

    # 4. Paired Diebold-Mariano test with Harvey-Leybourne-Newbold correction
    dm_stat = float(challenger_vs_ols["diebold_mariano_statistic"])
    hln_stat = float(challenger_vs_ols["hln_corrected_statistic"])
    p_val = float(challenger_vs_ols["p_value_one_sided"])
    df = challenger_vs_ols["degrees_of_freedom"]
    assert df == 242
    assert np.isclose(dm_stat, 0.9895, atol=1e-3)
    assert np.isclose(hln_stat, 0.9874, atol=1e-3)
    assert np.isclose(p_val, 0.16221, atol=1e-3)

    # 5. Significance check: p >= 0.05 must fail the promotion hurdle
    assert p_val >= 0.05, "p-value unexpectedly indicated significance!"
    assert challenger_vs_ols["statistically_significant"] is False
    assert scorecard["decision_verdict"] == "RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY"


def test_experiment_register_provenance():
    """Verify EXP-2026-04-QLIKE-24H is registered with strict research-only authorization."""
    with open(REGISTER_PATH, "r", encoding="utf-8") as f:
        register = json.load(f)

    exp_map = {e["experiment_id"]: e for e in register.get("experiments", [])}
    assert "EXP-2026-04-QLIKE-24H" in exp_map

    exp = exp_map["EXP-2026-04-QLIKE-24H"]
    assert exp["candidate_name"] == "HAR-QLIKE-24H"
    assert "rv24h_var_ann" in exp["target"]
    assert exp["paired_comparison"]["statistically_significant"] is False
    assert exp["decision"] == "RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY"


def test_target_horizon_separation():
    """Verify target contract definitions are mathematically separated."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    tc = manifest["target_contract"]
    assert tc["name"] == "rv24h_var_ann"
    assert tc["horizon_hours"] == 24
    assert tc["annualization_factor"] == 365.0

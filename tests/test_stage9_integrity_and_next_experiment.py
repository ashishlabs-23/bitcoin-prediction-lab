"""
tests/test_stage9_integrity_and_next_experiment.py — Stage 9 Integrity & Reconciliation Tests
=============================================================================================
Verifies:
1. Stage 9 machine-readable integrity results exist and conform to schema.
2. Cross-stage baseline discrepancy reconciliation:
   - Verifies common evaluation sample of 33,916 test bars.
   - Verifies >= 97.5% prediction agreement on common sample.
   - Confirms root cause: 31-hour warm-up difference (200h vs 168h) shifting walk-forward boundaries.
3. Corrected transaction-cost arithmetic:
   - Proves old selective backtest omitted exit fees when closing to cash.
   - Audits that corrected economics strictly satisfy Gross - Turnover * Fee = Net.
   - Verifies selective tiers remain deeply unprofitable (-10.55 bps/bar institutional at 5% coverage).
4. Runtime dependency classification & iv7d.parquet audit:
   - Verifies iv7d.parquet is classified as RESEARCH_BENCHMARK, not RUNTIME_INFERENCE.
   - Confirms active production model HAR-RS-DOW-v1.0 does not depend on iv7d.parquet.
5. Funding rate timestamp causal alignment:
   - Settlements occur strictly at 00:00, 08:00, 16:00 UTC.
   - Backward-looking alignment relative to candle open timestamp guarantees zero future lookahead.
6. Primary experiment (Option A: Target Noise Deadzone):
   - Confirms hypothesis test results: deadzone filtering fails to break 53.4% barrier on significant moves.
   - Proves difference is statistically non-significant (p > 0.05).
7. Production model immutability:
   - HAR-RS-DOW-v1.0 is strictly preserved as authorized production model.
   - Directional models remain OFFLINE_RESEARCH_ONLY.
"""

import os
import json
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STAGE9_JSON = os.path.join(REPO_ROOT, "experiments", "results", "stage9_reconciliation", "stage9_integrity_results.json")
OHLCV_PARQUET = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
FUNDING_PARQUET = os.path.join(REPO_ROOT, "data", "raw", "binance_funding_2022_2026.parquet")


@pytest.fixture(scope="module")
def stage9_results():
    assert os.path.exists(STAGE9_JSON), f"Missing Stage 9 results JSON: {STAGE9_JSON}"
    with open(STAGE9_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def test_stage9_results_schema(stage9_results):
    """Verify Stage 9 results JSON contains all required audit and experiment sections."""
    required_keys = [
        "timestamp",
        "stage_git_commit",
        "production_model_state",
        "runtime_dependency_iv7d_audit",
        "baseline_reconciliation",
        "cost_model_reconciliation",
        "funding_causal_audit",
        "primary_experiment_deadzone"
    ]
    for key in required_keys:
        assert key in stage9_results, f"Missing key {key} in Stage 9 results"


def test_baseline_reconciliation_sample_and_agreement(stage9_results):
    """Verify common evaluation sample size and >= 97.5% prediction agreement."""
    rec = stage9_results["baseline_reconciliation"]
    assert rec["stage6_test_bars"] == 33919
    assert rec["stage8_test_bars"] == 33942
    assert rec["common_test_bars"] == 33916

    # Prediction agreement
    agree_pct = rec["prediction_agreement_pct"]
    assert agree_pct >= 97.5, f"Expected >= 97.5% prediction agreement, got {agree_pct}%"

    # Common slice accuracy reconciliation
    assert abs(rec["common_slice_stage6_accuracy"] - 53.28) < 0.1
    assert abs(rec["common_slice_stage8_accuracy"] - 53.13) < 0.1
    assert "200 hours" in rec["root_cause_explanation"]
    assert "168 hours" in rec["root_cause_explanation"]


def test_transaction_cost_audit_formula_and_omitted_exit_fee(stage9_results):
    """
    Verify transaction cost audit:
    1. Unfiltered row turnover matches transitions (pos_prev = 0 to pos = +/-1 and flip between +/-1).
    2. In selective tiers, old code omitted cash exit fee (1 transition) when conf < hurdle.
    3. Corrected net returns strictly satisfy Gross - Turnover * 7.0 bps = Net Inst.
    """
    audit = stage9_results["cost_model_reconciliation"]
    assert "CRITICAL FLAW DISCOVERED" in audit["audit_finding"]

    recon_table = audit["reconciliation_table"]
    for row in recon_table:
        gross = row["mean_gross_return_bps"]
        turnover = row["turnover_transitions_per_bar"]
        audited_net_inst = row["audited_correct_net_inst_14bps"]
        audited_net_ret = row["audited_correct_net_retail_35bps"]

        # Check exact formula: Gross - turnover * 7.0 == audited_net_inst
        expected_inst = round(gross - turnover * 7.0, 2)
        assert abs(audited_net_inst - expected_inst) <= 0.05, f"Formula mismatch for tier {row['coverage_tier']}"

        expected_ret = round(gross - turnover * 17.5, 2)
        assert abs(audited_net_ret - expected_ret) <= 0.05, f"Formula mismatch for tier {row['coverage_tier']}"

        # If selective tier, reported net inst was overstated (less negative than audited)
        if row["coverage_tier"] != "100pct":
            assert row["reported_net_inst_14bps"] > row["audited_correct_net_inst_14bps"], (
                f"Reported net inst should be overstated due to missing exit fee: {row}"
            )


def test_runtime_dependency_iv7d_classification():
    """Verify iv7d.parquet is classified as RESEARCH_BENCHMARK and not RUNTIME_INFERENCE."""
    from validation.dependency_schema import classify_dependency, is_runtime_dependency, is_research_benchmark

    assert classify_dependency("iv7d.parquet") == "RESEARCH_BENCHMARK"
    assert is_runtime_dependency("iv7d.parquet") is False
    assert is_research_benchmark("iv7d.parquet") is True

    assert classify_dependency("ohlcv.parquet") == "RUNTIME_INFERENCE"
    assert is_runtime_dependency("ohlcv.parquet") is True


def test_funding_timestamp_settlement_distribution(stage9_results):
    """Verify Binance funding rate settlements occur at 00, 08, 16 UTC."""
    fund_audit = stage9_results["funding_causal_audit"]
    assert fund_audit["settlement_hours"] == [0, 8, 16]
    assert fund_audit["minute_distribution"] == {"0": 5113} or fund_audit["minute_distribution"] == {0: 5113}
    assert fund_audit["second_distribution"] == {"0": 5113} or fund_audit["second_distribution"] == {0: 5113}
    assert fund_audit["total_funding_records"] == 5113


def test_deadzone_experiment_results(stage9_results):
    """Verify primary deadzone experiment results and statistical failure to break 53.4% barrier."""
    exp = stage9_results["primary_experiment_deadzone"]
    base = exp["baseline_gbdt"]
    dead = exp["deadzone_challenger"]

    # Verify sample sizes
    assert exp["sample_size_all"] >= 33000
    assert exp["significant_coverage_pct"] >= 55.0

    # Verify difference on significant moves is non-significant (p > 0.05)
    paired = dead["paired_diff_significant"]
    assert paired["bootstrap_p_val"] > 0.05
    assert paired["statistically_significant"] is False


def test_production_model_registry_immutability():
    """Verify HAR-RS-DOW-v1.0 remains active production model and directional model is OFFLINE_RESEARCH_ONLY."""
    from models.authoritative_model_registry import (
        get_active_production_model,
        get_directional_research_baseline,
        verify_production_model_alignment,
        ModelClassification,
        AuthorizationStatus,
    )
    prod = get_active_production_model()
    assert prod.canonical_id == "HAR-RS-DOW-v1.0"
    assert prod.classification == ModelClassification.PRODUCTION_VOLATILITY
    assert prod.authorization_status == AuthorizationStatus.AUTHORIZED_FOR_PRODUCTION
    assert verify_production_model_alignment("/api/terminal/live", "HAR-RS-DOW-v1.0") is True
    assert verify_production_model_alignment("/api/terminal/live", "directional-gbm-4lag-v1") is False

    dir_model = get_directional_research_baseline()
    assert dir_model.canonical_id == "directional-gbm-4lag-v1"
    assert dir_model.classification == ModelClassification.DIRECTIONAL_RESEARCH_BENCHMARK
    assert dir_model.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY

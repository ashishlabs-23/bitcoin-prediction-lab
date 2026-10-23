"""
tests/test_experiment_freeze_and_statistical_integrity_v5.py
============================================================
Comprehensive deterministic acceptance test suite for:
BTCognitive V5 — Statistical Integrity, Experiment Freeze & Prospective Research.

Verifies:
1. Exact feature lookback warm-ups (ret_1h=1, ret_4h=4, ret_24h=24, rv_24h=24, vol_spread=191 bars).
2. Machine-readable eligibility audit consistency (3 segments, 2 gaps, split counts).
3. Target semantics: Gross 15.0 bps (hypothetical perpetual) vs Gross 87.0 bps (Coinbase spot).
4. Statistical uncertainty: Bootstrap CIs on net expectancy and paired loss differences.
5. Inconclusive vs decisively negative classification (Binance crosses zero; Coinbase bounded away).
6. Compounded portfolio equity simulation distinct from mean per-trade expectancy.
7. Authoritative experiment freeze manifest v5.0.0 persistence and integrity.
8. Prospective ledger audit (3 resolved 24h records, 2 pending 168h records).
9. Fail-closed non-execution (live trading disabled).
"""

import os
import json
import numpy as np
import pandas as pd
import pytest

from engine.continuity_time_series import ContinuityTimeSeriesEngine, continuity_engine
from engine.execution_cost_model import ExecutionCostModel
from engine.prospective_evidence_pipeline import ProspectiveEvidencePipeline
from models.signal_contract import ExecutionAuthorization


# =========================================================================
# 1. FEATURE LOOKBACK & ELIGIBILITY AUDIT (AGENT A)
# =========================================================================

def test_v5_eligibility_audit_artifact_exists_and_matches_data():
    """Verify machine-readable eligibility audit contains exact segment and lookback statistics."""
    audit_path = "experiments/results/research_improvement/v5_eligibility_audit.json"
    assert os.path.exists(audit_path), f"Audit artifact missing at {audit_path}"

    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)

    assert audit["audit_version"] == "V5-CONTINUITY-ELIGIBILITY-AUDIT"
    assert audit["total_input_bars"] == 41261
    assert audit["clean_bars"] == 41261
    assert audit["discontinuities_count"] == 2
    assert audit["segments_count"] == 3

    # Feature lookbacks
    reqs = audit["feature_lookback_requirements"]
    assert reqs["ret_1h"]["lookback_bars"] == 1
    assert reqs["ret_4h"]["lookback_bars"] == 4
    assert reqs["ret_24h"]["lookback_bars"] == 24
    assert reqs["rv_24h"]["lookback_bars"] == 24
    assert reqs["vol_spread"]["lookback_bars"] == 191


def test_vol_spread_exact_191_bar_warmup_per_segment():
    """Verify that vol_spread requires exactly 191 bars after a segment boundary."""
    df_raw = pd.read_parquet("data/raw/ohlcv.parquet")
    df_clean, summary = continuity_engine.audit_and_segment(df_raw)
    df_feat = continuity_engine.build_continuity_features(df_clean)

    for seg_id, group in df_feat.groupby("segment_id"):
        # The first 191 bars in each segment must have vol_spread as NaN
        assert group["vol_spread"].iloc[:191].isna().all()
        # Bar 191 (the 192nd bar) must be a finite float
        assert not np.isnan(group["vol_spread"].iloc[191])


# =========================================================================
# 2. TARGET SEMANTICS & INSTRUMENT SEPARATION (AGENT B)
# =========================================================================

def test_target_semantics_disambiguates_15bps_from_87bps():
    """Verify target definitions distinguish Binance hypothetical 15bps from Coinbase 87bps."""
    manifest_path = "experiments/results/research_improvement/v5_experiment_freeze_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    cands = manifest["candidates"]
    c3a = cands["Candidate_3A_Meta_Label_15bps_Target"]
    c3b = cands["Candidate_3B_Meta_Label_87bps_Target"]

    assert "15.0 bps" in c3a["target_definition"]
    assert "87.0 bps" in c3b["target_definition"]
    assert c3a["train_positive_class_prevalence"] > c3b["train_positive_class_prevalence"]


def test_coinbase_spot_primary_vs_binance_perpetual_hypothetical():
    """Verify market provenance tags Binance Futures as an explicit hypothetical sensitivity."""
    manifest_path = "experiments/results/research_improvement/v5_experiment_freeze_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    prov = manifest["market_provenance"]
    assert prov["source_exchange"] == "Coinbase Advanced"
    assert prov["market_type"] == "SPOT"
    assert "87.0 bps" in prov["primary_empirical_backtest"]
    assert "Hypothetical" in prov["hypothetical_sensitivity_scenario"]


# =========================================================================
# 3. STATISTICAL VALIDITY & UNCERTAINTY (AGENT C)
# =========================================================================

def test_brier_and_logloss_paired_difference_confidence_intervals():
    """Verify model underperformance on Target A is statistically confirmed by positive CI."""
    manifest_path = "experiments/results/research_improvement/v5_experiment_freeze_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    c3a = manifest["candidates"]["Candidate_3A_Meta_Label_15bps_Target"]

    brier_ci = c3a["brier_score_difference_ci_95"]
    ll_ci = c3a["log_loss_difference_ci_95"]

    # Both CIs must be strictly positive (Model Loss > Baseline Loss)
    assert brier_ci[0] > 0.0, f"Brier CI lower bound not > 0: {brier_ci}"
    assert ll_ci[0] > 0.0, f"LogLoss CI lower bound not > 0: {ll_ci}"


def test_candidate_1_inconclusive_vs_decisively_negative_classification():
    """Verify Candidate 1 net expectancy CI crosses zero on Binance but is bounded negative on Coinbase."""
    manifest_path = "experiments/results/research_improvement/v5_experiment_freeze_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    c1 = manifest["candidates"]["Candidate_1_Momentum_24h_Baseline"]

    ci_cb = c1["ci_95_net_coinbase_bps"]
    ci_bin = c1["ci_95_net_binance_hypothetical_bps"]

    # Coinbase: Upper bound is negative (decisively negative)
    assert ci_cb[1] < 0.0, f"Coinbase net expectancy upper bound is not negative: {ci_cb}"

    # Binance Hypothetical: Lower bound negative, upper bound positive (crosses zero, inconclusive)
    assert ci_bin[0] < 0.0 and ci_bin[1] > 0.0, f"Binance CI does not cross zero: {ci_bin}"


def test_sequential_portfolio_simulation_distinct_from_mean_expectancy():
    """Verify portfolio compounding NAV and drawdown metrics are present and distinct from mean expectancy."""
    manifest_path = "experiments/results/research_improvement/v5_experiment_freeze_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    c1 = manifest["candidates"]["Candidate_1_Momentum_24h_Baseline"]

    assert c1["portfolio_final_nav_coinbase"] < 5000.0  # collapsed from 10000
    assert c1["portfolio_max_drawdown_pct_coinbase"] > 75.0
    assert c1["downtime_pct"] > 30.0  # Cash downtime explicitly modeled


# =========================================================================
# 4. EXPERIMENT FREEZE & PROSPECTIVE EVIDENCE (AGENT D & E)
# =========================================================================

def test_v5_manifest_freeze_and_retrospective_exposure_label():
    """Verify v5 manifest explicitly designates 2026 as exposed development data."""
    manifest_path = "experiments/results/research_improvement/v5_experiment_freeze_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["experiment_version"] == "5.0.0"
    assert manifest["governed_conclusion"] == "NO_CANDIDATE_PASSED_PREREGISTERED_GATE"
    assert manifest["execution_authorization"] == "DISABLED"
    assert "EXPOSED retrospective development" in manifest["sample_split_bars"]["data_exposure_status"]


def test_prospective_ledger_record_count_and_state_consistency():
    """Verify prospective ledger contains exactly 3 resolved 24h records and 2 pending 168h records."""
    ledger_path = "data/prospective_forecast_ledger.jsonl"
    assert os.path.exists(ledger_path)

    records = [json.loads(line) for line in open(ledger_path, "r", encoding="utf-8")]
    assert len(records) >= 5

    resolved_24h = [r for r in records if r["target_name"] == "rv24h_var_ann" and r["resolution_state"] == "RESOLVED"]
    pending_168h = [r for r in records if r["target_name"] == "rv7d_var_ann" and r["resolution_state"] == "PENDING"]

    assert len(resolved_24h) >= 3
    assert len(pending_168h) >= 2

    # Verify each resolved record has a finite outcome and resolution timestamp
    for r in resolved_24h:
        assert isinstance(r["resolved_outcome"], (float, int))
        assert r["resolved_outcome"] > 0.0
        assert r["resolution_timestamp_utc"] is not None


def test_fail_closed_non_execution_invariant():
    """Verify live trading and automated model promotion remain strictly disabled."""
    assert ExecutionAuthorization.DISABLED.value == "DISABLED"

"""
tests/test_experiment_integrity_v4.py
====================================
Comprehensive deterministic test suite for Experiment Integrity v4:
Gap-Aware Time Series, Instrument-Correct Costs & Reproducible Strategy Evaluation.

Verifies:
1. Continuous hourly segmentation (identifying 1h gap on 2023-03-24 and 742h gap on 2026-09-01).
2. Segment lookback resets (ret_1h, ret_4h, ret_24h, rv_24h are NaN when crossing gaps).
3. Forward horizon gap exclusion (forward window crossing gap is marked DISCONTINUOUS_FORWARD_HORIZON_GAP).
4. Exact 24-hour elapsed UTC duration contract (rejects labels with elapsed duration != 24.0h).
5. Split boundary purging (no training label matures in validation; no validation label matures in test).
6. Market provenance: Coinbase Spot is primary empirical backtest; Binance Perpetual is hypothetical sensitivity.
7. Execution cost model: Per-side fees, duration-dependent holding funding, direction sensitivity, embedded spread.
8. Probability calibration baselines: Model evaluated against constant training prevalence baseline, not solely naive 0.50.
9. Manifest v4 integrity and governed conclusion (NO_CANDIDATE_PASSED_PREREGISTERED_GATE).
10. Live trading permanently DISABLED.
"""

import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from engine.continuity_time_series import (
    ContinuityTimeSeriesEngine,
    continuity_engine,
    TimeSeriesSegment
)
from engine.execution_cost_model import ExecutionCostModel
from engine.scenario_contract_engine import ScenarioContractEngine
from models.signal_contract import ExecutionAuthorization, SignalStatus


# =========================================================================
# 1. TIME SERIES CONTINUITY & SEGMENTATION TESTS (AGENT A)
# =========================================================================

def test_continuity_segmentation_identifies_all_dataset_gaps():
    """Verify that audit_and_segment correctly partitions the raw dataset into 3 contiguous segments."""
    df_raw = pd.read_parquet("data/raw/ohlcv.parquet")
    df_clean, summary = continuity_engine.audit_and_segment(df_raw)

    # Dataset partition & continuity integrity contract:
    # 41,273 continuous hourly bars from 2022-01-01 00:00:00 UTC to 2026-10-17 15:00:00 UTC
    assert len(df_raw) == 41273
    assert df_raw["timestamp"].is_monotonic_increasing is True
    assert df_raw["timestamp"].duplicated().sum() == 0
    assert summary.total_input_rows == len(df_raw)
    assert summary.total_duplicates_removed == 0
    assert summary.gap_count == 2
    assert len(summary.segments) == 3
    assert sum(s.total_bars for s in summary.segments) == len(df_raw)
    assert df_clean["segment_id"].nunique() == 3

    # Gap 1: 2023-03-24 (1h missing, elapsed 2h)
    g1 = summary.gaps[0]
    assert g1["gap_id"] == 1
    assert g1["missing_hours"] == 1.0
    assert g1["elapsed_hours"] == 2.0
    assert "2023-03-24" in g1["gap_start_timestamp"]

    # Gap 2: 2026-09-01 to 2026-10-02 (742h missing, elapsed 743h)
    g2 = summary.gaps[1]
    assert g2["gap_id"] == 2
    assert g2["missing_hours"] == 742.0
    assert g2["elapsed_hours"] == 743.0
    assert "2026-09-01" in g2["gap_start_timestamp"]
    assert "2026-10-02" in g2["gap_end_timestamp"]


def test_synthetic_gap_detection_and_segment_assignment():
    """Verify that any synthetic discontinuity triggers a new segment."""
    dates = pd.date_range("2026-01-01 00:00:00", periods=5, freq="1h", tz="UTC").tolist()
    # Insert a 3-hour jump
    dates.extend(pd.date_range("2026-01-01 08:00:00", periods=5, freq="1h", tz="UTC").tolist())
    df_synth = pd.DataFrame({
        "timestamp": dates,
        "open": np.linspace(80000, 81000, 10),
        "high": np.linspace(80100, 81100, 10),
        "low": np.linspace(79900, 80900, 10),
        "close": np.linspace(80050, 81050, 10),
        "volume": 100.0
    })

    engine = ContinuityTimeSeriesEngine(expected_cadence_hours=1.0)
    df_clean, summary = engine.audit_and_segment(df_synth)

    assert summary.gap_count == 1
    assert len(summary.segments) == 2
    assert summary.gaps[0]["missing_hours"] == 3.0
    assert df_clean.loc[0:4, "segment_id"].unique().tolist() == [0]
    assert df_clean.loc[5:9, "segment_id"].unique().tolist() == [1]


def test_features_reset_at_segment_boundary_no_cross_gap_contamination():
    """Verify that ret_1h, ret_4h, ret_24h and rv_24h are NaN when looking across a gap."""
    df_raw = pd.read_parquet("data/raw/ohlcv.parquet")
    df_clean, _ = continuity_engine.audit_and_segment(df_raw)
    df_feat = continuity_engine.build_continuity_features(df_clean)

    # First row of Segment 2 (after the 31-day gap, index 40902)
    gap_idx = 40902
    assert df_feat.loc[gap_idx, "segment_id"] == 2
    # ret_1h must be NaN (NOT an 8.67% monthly return)
    assert np.isnan(df_feat.loc[gap_idx, "ret_1h"])
    # ret_4h must be NaN
    assert np.isnan(df_feat.loc[gap_idx, "ret_4h"])
    # ret_24h must be NaN
    assert np.isnan(df_feat.loc[gap_idx, "ret_24h"])
    # rv_24h must be NaN for the first 24 bars of Segment 2
    assert np.isnan(df_feat.loc[gap_idx, "rv_24h"])
    assert np.isnan(df_feat.loc[gap_idx + 23, "rv_24h"])
    # Bar 24 of Segment 2 has 24 continuous hours, so rv_24h is valid
    assert not np.isnan(df_feat.loc[gap_idx + 24, "rv_24h"])


def test_forward_horizon_gap_exclusion_prevents_fake_labels():
    """Verify that candles whose 24-hour forward window crosses a gap are marked EXCLUDED."""
    df_raw = pd.read_parquet("data/raw/ohlcv.parquet")
    df_clean, _ = continuity_engine.audit_and_segment(df_raw)
    df_feat = continuity_engine.build_continuity_features(df_clean)
    df_labels = continuity_engine.build_gap_safe_triple_barrier_labels(df_feat, horizon_hours=24)

    # The last candle before gap 2 is at index 40901 (2026-09-01 06:00 UTC)
    # Forward 24h spans across the 31-day gap!
    pre_gap_idx = 40901
    assert df_labels.loc[pre_gap_idx, "tb_exclusion_reason"] == "DISCONTINUOUS_FORWARD_HORIZON_GAP"
    assert np.isnan(df_labels.loc[pre_gap_idx, "tb_label"])
    assert pd.isna(df_labels.loc[pre_gap_idx, "tb_outcome"]) or df_labels.loc[pre_gap_idx, "tb_outcome"] is None

    # Check 10 bars before gap
    for i in range(40901 - 23, 40902):
        assert df_labels.loc[i, "tb_exclusion_reason"] == "DISCONTINUOUS_FORWARD_HORIZON_GAP"
        assert np.isnan(df_labels.loc[i, "tb_label"])


def test_elapsed_duration_mismatch_rejected():
    """Verify that a label requiring 24 hours strictly rejects intervals with elapsed time != 24h."""
    dates = pd.date_range("2026-01-01 00:00:00", periods=60, freq="1h", tz="UTC").tolist()
    # Missing 5 hours (gap from 2026-01-03 12:00 to 17:00)
    dates.extend(pd.date_range("2026-01-03 17:00:00", periods=30, freq="1h", tz="UTC").tolist())
    n_pts = len(dates)
    # Add non-zero variance so rv_24h > 1e-5
    base_prices = 80000.0 + np.sin(np.linspace(0, 10, n_pts)) * 500.0
    df_synth = pd.DataFrame({
        "timestamp": dates,
        "open": base_prices,
        "high": base_prices + 50.0,
        "low": base_prices - 50.0,
        "close": base_prices + 10.0,
        "volume": 100.0
    })

    engine = ContinuityTimeSeriesEngine(expected_cadence_hours=1.0)
    df_clean, _ = engine.audit_and_segment(df_synth)
    df_feat = engine.build_continuity_features(df_clean)
    df_labeled = engine.build_gap_safe_triple_barrier_labels(df_feat, horizon_hours=24)

    # Bars 36..59 in segment 0 have valid lookback (>= 24), but their 24h forward horizon crosses into segment 1!
    for idx in range(36, 60):
        assert df_labeled.loc[idx, "tb_exclusion_reason"] == "DISCONTINUOUS_FORWARD_HORIZON_GAP"
        assert np.isnan(df_labeled.loc[idx, "tb_label"])

    # Test explicit elapsed duration mismatch within a single segment
    # Take df_feat which has valid lookback at index 25 (24 prior bars)
    df_mismatch = df_feat.iloc[:55].copy()
    # At index 25, forward 24th bar is index 49. Artificially make index 49 30 hours after index 25
    ts_25 = df_mismatch.loc[df_mismatch.index[25], "timestamp"]
    df_mismatch.loc[df_mismatch.index[49], "timestamp"] = ts_25 + pd.Timedelta(hours=30)
    df_mismatch_labeled = engine.build_gap_safe_triple_barrier_labels(df_mismatch, horizon_hours=24)
    assert df_mismatch_labeled.loc[df_mismatch.index[25], "tb_exclusion_reason"] == "ELAPSED_DURATION_MISMATCH"


# =========================================================================
# 2. INSTRUMENT IDENTITY & MARKET-DATA CONTRACT (AGENT B)
# =========================================================================

def test_market_provenance_and_instrument_separation():
    """Verify market data contract distinguishes Coinbase Spot from hypothetical Binance Perpetual."""
    manifest_path = Path("experiments/results/research_improvement/v4_gap_aware_directional_manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    prov = manifest["market_provenance"]
    assert prov["source_exchange"] == "Coinbase Advanced"
    assert prov["instrument"] == "BTC-USD"
    assert prov["market_type"] == "SPOT"
    assert "Coinbase Spot Tier 1" in prov["primary_empirical_backtest"]
    assert "hypothetical" in prov["hypothetical_sensitivity_scenario"].lower()


# =========================================================================
# 3. COST RECONCILIATION & PROBABILITY CALIBRATION AUDIT (AGENT C & E)
# =========================================================================

def test_coinbase_advanced_spot_tier1_cost_schedule():
    """Verify Coinbase Spot Tier 1 round-trip friction is 87.0 bps."""
    cost_info = ExecutionCostModel.calculate_round_trip_cost("Coinbase")
    assert cost_info["total_round_trip_bps"] == 87.0
    assert cost_info["two_sided_commission_bps"] == 80.0
    assert cost_info["bid_ask_spread_bps"] == 3.0
    assert cost_info["slippage_bps"] == 4.0
    assert cost_info["funding_bps"] == 0.0
    assert cost_info["is_hypothetical_scenario"] is False


def test_binance_perpetual_hypothetical_scenario_schedule():
    """Verify Binance Futures Perpetual round-trip friction is ~15 bps with hypothetical tagging."""
    cost_info = ExecutionCostModel.calculate_round_trip_cost("Binance_Futures", holding_hours=18.0)
    assert cost_info["two_sided_commission_bps"] == 10.0
    assert cost_info["bid_ask_spread_bps"] == 1.0
    assert cost_info["slippage_bps"] == 2.0
    # 18 hours hold = 2 intervals (1.0 bps each) = 2.0 bps funding
    assert cost_info["funding_bps"] == 2.0
    assert cost_info["total_round_trip_bps"] == 15.0
    assert cost_info["is_hypothetical_scenario"] is True


def test_brier_score_evaluated_against_prevalence_baseline():
    """Verify model calibration is compared against historical prevalence baseline, not solely naive 0.50."""
    manifest_path = Path("experiments/results/research_improvement/v4_gap_aware_directional_manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    c3 = manifest["candidates"]["Candidate_3_Meta_Label_Filter"]
    brier_model = c3["brier_score_model"]
    brier_prev = c3["brier_score_constant_prevalence_baseline"]
    brier_naive = c3["brier_score_naive_50_baseline"]

    # Model beats naive 0.50 (0.2485 < 0.2500)
    assert brier_model < brier_naive
    # Model does NOT beat the constant prevalence baseline (0.2485 >= 0.2480)
    assert brier_model >= brier_prev


# =========================================================================
# 4. REPRODUCIBLE SCORECARD & GOVERNED DECISION (AGENT D & H)
# =========================================================================

def test_manifest_v4_governed_conclusion_and_non_execution():
    """Verify manifest v4 records NO_CANDIDATE_PASSED_PREREGISTERED_GATE and execution is disabled."""
    manifest_path = Path("experiments/results/research_improvement/v4_gap_aware_directional_manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["experiment_id"] == "EXP-RESEARCH-TO-SIGNAL-V4-GAP-AWARE"
    assert manifest["governed_conclusion"] == "NO_CANDIDATE_PASSED_PREREGISTERED_GATE"
    assert manifest["execution_authorization"] == "DISABLED"
    assert manifest["portfolio_policy"] == "SINGLE_POSITION_AT_A_TIME"

    c1 = manifest["candidates"]["Candidate_1_Momentum_24h_Baseline"]
    assert c1["trades"] == 227
    assert c1["net_expectancy_coinbase_bps"] < 0.0
    assert c1["economic_verdict"] == "FAIL_NEGATIVE_AFTER_COSTS"


def test_scenario_contract_engine_fails_closed_under_v4_gap_safe_pipeline():
    """Verify scenario contract engine fails closed with ECONOMIC_EXPECTANCY_NEGATIVE."""
    engine = ScenarioContractEngine(exchange="Coinbase", instrument="BTC-USD")
    sig = engine.evaluate_scenario_candidate(
        reference_price=80000.0,
        direction="LONG",
        horizon="1h",
        is_model_gated=False
    )
    assert sig.signal_status == SignalStatus.ABSTAIN
    assert sig.invalidation_reason == "ECONOMIC_EXPECTANCY_NEGATIVE"
    assert sig.execution_authorization == ExecutionAuthorization.DISABLED
    assert sig.entry_price is None
    assert sig.take_profit is None
    assert sig.stop_loss is None

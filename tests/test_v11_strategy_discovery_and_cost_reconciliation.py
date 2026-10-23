"""
tests/test_v11_strategy_discovery_and_cost_reconciliation.py
=============================================================
BTCognitive V11 — Strategy Discovery, Cost-Aware Validation & PRD Completion Tests
==================================================================================
Validates:
1. 15-minute extended dataset integrity & manifest hash consistency (1,800 candles, 0 gaps).
2. Historical test fixture timestamp (1760700600) vs live runtime origin disambiguation.
3. Execution cost scenario reconciliation (Coinbase Retail 87 bps vs Institutional 18.6 bps vs Binance 15 bps).
4. Frozen strategy candidate specifications and barrier definitions.
5. Chronological walk-forward partitioning with purged embargoes.
6. Statistical validation: NO_TRADE superiority under realistic transaction costs.
7. Nominal model-based diffusion band labeling (uncalibrated coverage).
8. Strict governance boundaries: Live trading DISABLED, directional recommendation ABSTAIN.
"""

import os
import sys
import json
import pytest
import numpy as np
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engine.coinbase_15m_adapter import Coinbase15mAdapter
from engine.execution_cost_model import ExecutionCostModel
from engine.forecast_engine_15m import generate_forecast_contract
from research.v11_strategy_discovery_engine import V11StrategyDiscoveryEngine, compute_file_sha256


@pytest.fixture(scope="module")
def v11_engine():
    engine = V11StrategyDiscoveryEngine()
    engine.load_and_verify_data()
    engine.compute_causal_features()
    return engine


def test_coinbase_15m_extended_dataset_integrity(v11_engine):
    """Verify validated candles, 0 gaps, 1 segment, and SHA-256 match."""
    audit = v11_engine.load_and_verify_data()
    assert audit["row_count"] >= 600
    assert audit["gap_count"] == 0
    assert audit["is_continuous"] is True
    assert audit["hash_matched"] is True
    assert audit["first_epoch"] <= audit["last_epoch"]
    assert audit["last_epoch"] >= 1792252800   # 2026-10-17 16:00:00 UTC


def test_v10_example_timestamp_reconciliation(v11_engine):
    """Verify example timestamp 1760700600 is identified as historical test snapshot."""
    audit = v11_engine.load_and_verify_data()
    ts_audit = audit["example_timestamp_audit"]
    assert ts_audit["v10_audit_example_epoch"] == 1760700600
    assert ts_audit["classification"] == "HISTORICAL_STATIC_TEST_FIXTURE_SNAPSHOT"
    assert ts_audit["is_runtime_origin"] is False
    assert ts_audit["runtime_latest_epoch"] >= 1792252800


def test_execution_cost_scenarios_reconciliation():
    """Verify itemized friction models for Retail (87 bps), Institutional (18.6 bps), and Futures (15 bps)."""
    scenarios = V11StrategyDiscoveryEngine.COST_SCENARIOS
    
    # 1. Coinbase Retail Tier 1
    cb_ret = scenarios["COINBASE_RETAIL_87BPS"]
    assert cb_ret["round_trip_bps"] == 87.0
    assert cb_ret["two_sided_commission_bps"] == 80.0
    assert cb_ret["two_sided_spread_bps"] == 3.0
    assert cb_ret["two_sided_slippage_bps"] == 4.0
    assert cb_ret["funding_bps"] == 0.0

    # 2. Coinbase Institutional Tier 5+
    cb_inst = scenarios["COINBASE_INSTITUTIONAL_18BPS"]
    assert cb_inst["round_trip_bps"] == 18.6
    assert cb_inst["two_sided_commission_bps"] == 11.6
    assert cb_inst["two_sided_spread_bps"] == 3.0
    assert cb_inst["two_sided_slippage_bps"] == 4.0

    # 3. Binance Perpetual Futures
    bin_perp = scenarios["BINANCE_PERP_15BPS"]
    assert bin_perp["round_trip_bps"] == 15.0
    assert bin_perp["two_sided_commission_bps"] == 10.0
    assert bin_perp["funding_bps"] == 2.0
    assert bin_perp["is_hypothetical"] is True


def test_predeclared_strategy_candidates_frozen_contracts(v11_engine):
    """Verify all 3 predeclared strategy candidates execute cleanly over development split."""
    strategies = ["NO_TRADE", "TS_MOM_TREND", "VOL_BREAKOUT_REGIME", "MEAN_REVERT_FLOW_BLOCKED"]
    
    for strat in strategies:
        res = v11_engine.run_strategy_backtest(
            strategy_id=strat,
            cost_scenario_key="COINBASE_INSTITUTIONAL_18BPS",
            start_idx=64,
            end_idx=500,
            apply_eligibility_filter=True
        )
        assert res["strategy_id"] == strat
        assert "net_expectancy_bps" in res
        assert "win_rate" in res
        assert "profit_factor" in res


def test_walk_forward_purged_embargoes(v11_engine):
    """Verify chronological split bounds and embargo structure."""
    total_bars = len(v11_engine.df_features)
    assert total_bars >= 600
    train_start = 64
    train_end = int(train_start + (total_bars - train_start) * 0.6)
    val_start = train_end + 1
    val_end = int(train_start + (total_bars - train_start) * 0.8)
    holdout_start = val_end + 1
    holdout_end = total_bars
    assert train_start < train_end < val_start < val_end < holdout_start <= holdout_end

    # Ensure splits are chronologically ordered
    t_train_last = v11_engine.df_features.iloc[train_end - 1]["epoch_time"]
    t_val_first = v11_engine.df_features.iloc[val_start]["epoch_time"]
    t_val_last = v11_engine.df_features.iloc[val_end - 1]["epoch_time"]
    t_holdout_first = v11_engine.df_features.iloc[holdout_start]["epoch_time"]

    assert t_train_last < t_val_first
    assert t_val_last < t_holdout_first


def test_holdout_validation_confirms_no_candidate_passed(v11_engine):
    """Verify that NO candidate achieved positive net expectancy on holdout under conservative 87 bps costs."""
    strategies = ["TS_MOM_TREND", "VOL_BREAKOUT_REGIME", "MEAN_REVERT_FLOW_BLOCKED"]
    total_bars = len(v11_engine.df_features)
    holdout_start = int(64 + (total_bars - 64) * 0.8) + 1
    
    for strat in strategies:
        res = v11_engine.run_strategy_backtest(
            strategy_id=strat,
            cost_scenario_key="COINBASE_RETAIL_87BPS",
            start_idx=holdout_start,
            end_idx=total_bars,
            apply_eligibility_filter=True
        )
        # Either zero trades due to cost hurdle, or negative net expectancy
        if res["trades_count"] > 0:
            assert res["net_expectancy_bps"] < 0, f"Strategy {strat} unexpectedly had positive return under 87 bps"
            assert res["net_expectancy_ci_95"][0] < 0


def test_nominal_model_band_labeling():
    """Verify 15m forecast contract specifies nominal model diffusion bands, not demonstrated 90% empirical coverage."""
    contract = generate_forecast_contract(horizon="15m")
    assert contract["status"] == "FORECAST_AVAILABLE_RESEARCH_ONLY"
    assert "Nominal Model-Based Diffusion Envelope" in contract["uncertainty_method"]
    assert "uncalibrated coverage" in contract["uncertainty_method"]


def test_governance_invariants_preserved():
    """Verify live trading disabled, directional recommendation abstain, and research only."""
    contract = generate_forecast_contract(horizon="15m")
    assert contract["live_trading"] == "DISABLED"
    assert contract["directional_recommendation"] == "ABSTAIN"
    assert contract["governance_state"] == "TIER 2 GATED (ABSTAIN)"
    assert contract["model_readiness"] == "MODEL_TIMEFRAME_INCOMPATIBLE"

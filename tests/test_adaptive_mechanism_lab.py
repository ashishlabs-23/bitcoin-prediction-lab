"""
tests/test_adaptive_mechanism_lab.py — Complete Test Suite for Market Mechanism Lab
=====================================================================================
Validates all levels (L0 to L9) of the Adaptive Market Mechanism Laboratory:
  - L0: Provenance Contract & Three-Clock Invariants
  - State: Two-Speed (Level, Shock, Persistence) state extraction
  - L1: Mechanism Hypothesis Detection & Divergence Testing
  - L2/L3: Empirical Conditional Path & Excursion Engine
  - L4/L5: Execution Reality, Adverse Selection & Net EV Drag
  - L6: Multi-Stress Survival Matrix, Capacity & Attribution
  - L7/L8: Universal Research Census, DSR & Null Controls
  - L9: Multi-Dimensional Ultimate Holdout & One-Shot Rule
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.provenance_contract import ProvenanceContract, TemporalProvenanceError
from models.market_state_v4 import TwoSpeedMarketState
from models.mechanism_hypotheses import MechanismDetector
from models.conditional_path_engine import ConditionalPathEngine
from backtest.execution_reality import ExecutionRealityEngine
from backtest.survival_stress_matrix import SurvivalStressMatrix
from validation.research_census import ResearchCensus
from validation.ultimate_holdout_gate import UltimateHoldoutGate


@pytest.fixture
def sample_market_data():
    """Generates synthetic multi-variable market data for deterministic test execution."""
    np.random.seed(42)
    n = 300
    timestamps = pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC")
    
    # Geometric random walk
    rets = np.random.normal(0.0002, 0.01, n)
    prices = 65000.0 * np.exp(np.cumsum(rets))
    
    highs = prices * (1.0 + np.abs(np.random.normal(0, 0.004, n)))
    lows = prices * (1.0 - np.abs(np.random.normal(0, 0.004, n)))
    opens = prices * (1.0 + np.random.normal(0, 0.001, n))
    vols = np.abs(np.random.normal(100.0, 30.0, n))

    df = pd.DataFrame({
        "timestamp": timestamps,
        "available_time": timestamps, # 0 latency for baseline
        "open": opens,
        "high": highs,
        "low": lows,
        "close": prices,
        "volume": vols,
        "ret_1h": rets,
        "realized_vol_24h": pd.Series(rets).rolling(24).std().fillna(0.01).values,
        "atr_14": pd.Series(highs - lows).rolling(14).mean().fillna(200.0).values,
        "funding_rate": np.random.normal(0.0001, 0.0001, n),
        "vpin": np.clip(np.random.normal(0.5, 0.15, n), 0.1, 0.95),
        "bid_ask_spread_pct": np.clip(np.random.normal(0.0002, 0.00005, n), 0.0001, 0.001),
        "order_book_imbalance": np.random.normal(0.0, 0.3, n),
        "taker_buy_ratio": np.clip(np.random.normal(0.5, 0.1, n), 0.2, 0.8)
    })
    return df


def test_l0_provenance_contract(sample_market_data):
    """Verifies L0 three-clock temporal validation and lookahead rejection."""
    prov = ProvenanceContract()
    
    # 1. Valid baseline data
    res = prov.validate_dataframe(sample_market_data)
    assert res["valid"] is True
    assert "provenance_hash" in res

    # 2. Causality violation test (available_time before event timestamp)
    bad_df = sample_market_data.copy()
    bad_df.loc[10, "available_time"] = bad_df.loc[10, "timestamp"] - pd.Timedelta(seconds=5)
    res_bad = prov.validate_dataframe(bad_df)
    assert res_bad["valid"] is False
    assert any("Causality violation" in v for v in res_bad["violations"])

    # 3. Decision boundary filtering
    t0 = sample_market_data["timestamp"].iloc[100]
    filtered = prov.filter_admissible_data(sample_market_data, t0)
    assert len(filtered) == 101
    assert filtered["available_time"].max() <= t0


def test_two_speed_market_state(sample_market_data):
    """Verifies Level 2 Two-Speed state representation (level, shock, persistence)."""
    state_engine = TwoSpeedMarketState(rolling_window=50)
    state_df = state_engine.build_full_market_state(sample_market_data)

    assert "V_volatility_level_pct" in state_df.columns
    assert "V_volatility_shock" in state_df.columns
    assert "V_volatility_persistence" in state_df.columns
    assert "F_vpin_shock" in state_df.columns
    assert "L_spread_shock" in state_df.columns

    # Snapshot extraction
    snapshot = state_engine.get_state_snapshot(state_df.iloc[-1])
    assert "volatility" in snapshot
    assert "liquidity" in snapshot
    assert "flow" in snapshot


def test_l1_mechanism_hypotheses(sample_market_data):
    """Verifies mechanism event detection and statistical divergence testing."""
    state_engine = TwoSpeedMarketState(rolling_window=50)
    state_df = state_engine.build_full_market_state(sample_market_data)

    detector = MechanismDetector()
    events_df = detector.detect_events(state_df)

    assert "E_IGNITION" in events_df.columns
    assert "E_ABSORPTION" in events_df.columns
    assert "E_VACUUM" in events_df.columns
    assert "E_TOXICITY" in events_df.columns
    assert "E_COMBINED" in events_df.columns

    # Test event validity
    val_res = detector.test_event_validity_l1(
        events=events_df["E_COMBINED"],
        forward_returns=sample_market_data["ret_1h"].shift(-1).fillna(0.0),
        min_events=5
    )
    assert "valid_l1" in val_res
    assert "ks_statistic" in val_res


def test_l2_l3_conditional_path_engine(sample_market_data):
    """Verifies discrete empirical competing-risk evaluation and first-passage profiles."""
    path_engine = ConditionalPathEngine(default_horizon=12, pt_mult=1.5, sl_mult=1.5)
    
    vol = pd.Series(sample_market_data["ret_1h"]).rolling(24).std().fillna(0.01)
    path_df = path_engine.compute_path_outcomes(
        close=sample_market_data["close"],
        high=sample_market_data["high"],
        low=sample_market_data["low"],
        vol=vol,
        direction="LONG"
    )

    assert "outcome" in path_df.columns
    assert "t_hit" in path_df.columns
    assert "mfe" in path_df.columns
    assert "mae" in path_df.columns

    # Check outcomes belong to discrete competing set
    valid_outcomes = set(path_df["outcome"].unique())
    assert valid_outcomes.issubset({"TP_HIT", "SL_HIT", "TIMEOUT", "INVALID"})

    # Evaluate conditional matrix
    mask = pd.Series(True, index=sample_market_data.index)
    matrix_res = path_engine.evaluate_conditional_matrix(path_df, mask)
    assert "p_tp" in matrix_res
    assert "p_sl" in matrix_res
    assert "p_tp_first" in matrix_res


def test_l4_l5_execution_reality():
    """Verifies maker/taker execution drag, adverse selection, and net EV."""
    exec_engine = ExecutionRealityEngine(
        base_fee_bps_maker=1.0,
        base_fee_bps_taker=5.0,
        base_spread_bps=2.0
    )

    # 1. Taker mode (market order)
    res_taker = exec_engine.compute_execution_drag(
        signal_return=0.0020, # +20 bps raw signal
        mode="TAKER",
        order_size_usd=10000.0,
        vol_shock=1.0
    )
    assert res_taker["mode"] == "TAKER"
    assert res_taker["net_return_bps"] < res_taker["signal_return_bps"]
    assert res_taker["execution_drag_bps"] > 0.0

    # 2. Maker mode (limit order with adverse selection)
    res_maker = exec_engine.compute_execution_drag(
        signal_return=0.0020,
        mode="MAKER",
        vpin=0.80, # High toxicity
        book_imbalance=-0.5
    )
    assert res_maker["mode"] == "MAKER"
    assert "adverse_selection" in res_maker["cost_breakdown_bps"]


def test_l6_survival_stress_matrix():
    """Verifies cost curve, latency half-life, capacity curve, and mechanism attribution."""
    stress = SurvivalStressMatrix()
    
    # 1. Cost Survival
    cost_res = stress.compute_cost_survival_curve(base_signal_return=0.0025, mode="TAKER")
    assert "1.0x" in cost_res["curve_bps"]
    assert "2.0x" in cost_res["curve_bps"]
    assert cost_res["survives_1_5x"] is True

    # 2. Latency Survival
    lat_res = stress.compute_latency_survival_curve(base_signal_return=0.0025, mode="TAKER")
    assert "0ms" in lat_res["curve_bps"]
    assert "250ms" in lat_res["curve_bps"]
    assert "latency_half_life_ms" in lat_res

    # 3. Capacity Curve
    cap_res = stress.compute_capacity_curve(base_signal_return=0.0025, mode="TAKER")
    assert "$1,000" in cap_res["curve_bps"]
    assert "$100,000" in cap_res["curve_bps"]
    assert cap_res["q_max_usd"] > 0.0

    # 4. Mechanism Attribution
    attr_res = stress.compute_mechanism_attribution(
        ev_event_plus_state=0.0025,
        ev_state_only_baseline=0.0008
    )
    assert attr_res["incremental_mechanism_alpha_bps"] == 17.0
    assert attr_res["valid_mechanism_attribution"] is True


def test_l7_l8_research_census():
    """Verifies trial registration, DSR multiple-testing adjustment, and null controls."""
    census = ResearchCensus(ledger_file="experiments/results/test_census.json")
    
    # 1. Register trial
    t_rec = census.register_trial(
        strategy_name="MEIE-IGNITION",
        feature_spec={"vpin": True, "vol_shock": True},
        event_spec={"type": "IGNITION", "threshold": 1.5},
        params={"tp": 2.0, "sl": 1.5, "horizon": 24},
        execution_spec={"mode": "TAKER", "fee_bps": 5.0},
        data_range="2026-01-01_2026-06-01",
        observed_sharpe=1.85,
        observed_return_bps=22.5
    )
    assert "trial_hash" in t_rec
    assert census.total_trials_count >= 1

    # 2. Deflated Sharpe Ratio
    np.random.seed(42)
    rets = np.random.normal(0.001, 0.01, 200)
    dsr_res = census.compute_deflated_sharpe_ratio(observed_sr=1.85, returns=rets, n_trials=50)
    assert "dsr" in dsr_res
    assert 0.0 <= dsr_res["dsr"] <= 1.0

    # 3. Edge Lifecycle
    lifecycle = census.evaluate_edge_lifecycle_l7([25.0, 22.0, 18.0])
    assert lifecycle in ["ACCELERATING", "STABLE", "DECAYING", "COLLAPSED", "REVERSED"]


def test_l9_ultimate_holdout_gate(sample_market_data, tmp_path):
    """Verifies Level 9 blind promotion trial and one-shot non-iteration rule."""
    test_audit_file = str(tmp_path / "test_holdout_audit.json")
    gate = UltimateHoldoutGate(evaluated_candidates_file=test_audit_file)
    
    # 1. Evaluate candidate
    candidate_hash = "cand_test_hash_001"
    rets = pd.Series(np.random.normal(0.0015, 0.008, len(sample_market_data)), index=sample_market_data.index)
    events = pd.Series(np.random.choice([0, 1], size=len(sample_market_data), p=[0.85, 0.15]), index=sample_market_data.index)
    state_rets = pd.Series(np.random.normal(0.0003, 0.008, len(sample_market_data)), index=sample_market_data.index)

    res_promo = gate.evaluate_candidate_for_promotion(
        strategy_name="MEIE-IGNITION-V4",
        candidate_hash=candidate_hash,
        holdout_returns=rets,
        event_series=events,
        state_only_returns=state_rets,
        mode="TAKER"
    )

    assert "verdict" in res_promo
    assert "survival_scorecard" in res_promo

    # 2. One-Shot rule enforcement (re-testing same hash must be rejected)
    res_repeat = gate.evaluate_candidate_for_promotion(
        strategy_name="MEIE-IGNITION-V4",
        candidate_hash=candidate_hash,
        holdout_returns=rets,
        event_series=events,
        state_only_returns=state_rets
    )
    assert res_repeat["verdict"] == "REJECTED_ALREADY_EVALUATED"
    assert res_repeat["promoted"] is False

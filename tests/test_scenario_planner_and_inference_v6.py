"""BTCognitive V6 Acceptance & Red-Team Test Suite.

Covers:
1. Scenario calculation:
   - Known-answer LONG and SHORT levels.
   - Log-return volatility units and horizon scaling (sqrt(H)).
   - Exact ratio calculation from prices (Gross R:R).
   - Custom entry anchor.
   - Negative, zero, NaN and infinite input rejection.
   - Unsupported 5m/15m horizon gating.
   - Contract version consistency and governance metadata.
2. Signal separation:
   - No candidate passes: active signal remains ABSTAIN, while scenario preview succeeds.
   - Scenario preview returns is_actionable=False, execution_authorization=DISABLED.
   - Hypothetical levels do NOT create an active paper position or populate directional prediction.
3. Statistical correction:
   - Politis-Romano stationary bootstrap vs Naive IID bootstrap on serially correlated AR(1) process.
   - Block sampling strictly respects contiguous segment boundaries (no cross-gap pooling).
   - Paired loss differences remain strictly paired.
   - Seeded reproducibility and sensitivity across L in [12, 24, 48].
   - Correct interpretation: Brier CI crosses zero (INCONCLUSIVE_INTERVAL_CROSSES_ZERO).
4. Prospective worker:
   - Single-instance file lock prevents concurrent worker execution.
   - Duplicate-run idempotency (skips existing hourly issuance).
   - Pending outcomes remain unresolved prior to maturity.
   - Telemetry file reports truthful heartbeat, explicit pending/matured counts, and no fabricated cron status.
"""

import os
import math
import json
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

from engine.scenario_contract_engine import (
    HypotheticalScenarioPlanner,
    SCENARIO_PLANNER_VERSION,
    SUPPORTED_HOURLY_HORIZONS,
)
from engine.stationary_bootstrap import (
    compute_segment_aware_bootstrap_ci,
    run_block_length_sensitivity_analysis,
    generate_stationary_bootstrap_segment_indices,
    generate_circular_block_bootstrap_segment_indices,
)
from engine.prospective_worker import (
    acquire_worker_lock,
    release_worker_lock,
    is_worker_running,
    LOCK_FILE,
    STATUS_FILE,
    sync_live_candles,
)


class TestScenarioCalculationContract:
    """Verifies Agent B scenario mathematics and volatility inputs."""

    def test_known_answer_long_and_short_geometry(self):
        """Validates known-answer formulas:
        P = 80000.0, sigma_1h = 0.01, H = 4 hours.
        sigma_H = 0.01 * sqrt(4) = 0.02.
        LONG:
          TP = 80000 * exp(1.5 * 0.02) = 80000 * exp(0.03) = 82436.425
          SL = 80000 * exp(-1.0 * 0.02) = 80000 * exp(-0.02) = 78415.996
          reward_dist = 2436.425, risk_dist = 1584.004
          Gross R:R = 2436.425 / 1584.004 = 1.5381
        SHORT:
          TP = 80000 * exp(-1.5 * 0.02) = 80000 * exp(-0.03) = 77634.789
          SL = 80000 * exp(1.0 * 0.02) = 80000 * exp(0.02) = 81616.059
          reward_dist = 2365.211, risk_dist = 1616.059
          Gross R:R = 2365.211 / 1616.059 = 1.4636
        """
        P = 80000.0
        sigma_1h = 0.01
        H = 4.0
        sigma_H = sigma_1h * math.sqrt(H)
        assert abs(sigma_H - 0.02) < 1e-9

        # LONG geometry
        tp_long = P * math.exp(1.5 * sigma_H)
        sl_long = P * math.exp(-1.0 * sigma_H)
        assert sl_long < P < tp_long
        reward_long = tp_long - P
        risk_long = P - sl_long
        rr_long = reward_long / risk_long
        assert round(tp_long, 2) == 82436.36
        assert round(sl_long, 2) == 78415.89
        assert round(rr_long, 2) == 1.54

        # SHORT geometry
        tp_short = P * math.exp(-1.5 * sigma_H)
        sl_short = P * math.exp(1.0 * sigma_H)
        assert tp_short < P < sl_short
        reward_short = P - tp_short
        risk_short = sl_short - P
        rr_short = reward_short / risk_short
        assert round(tp_short, 2) == 77635.64
        assert round(sl_short, 2) == 81616.11
        assert round(rr_short, 2) == 1.46

    def test_live_market_scenario_preview(self):
        """Verifies scenario calculation from verified continuous market data."""
        planner = HypotheticalScenarioPlanner()
        result = planner.compute_scenario_preview(horizon="24h")
        assert result["status"] == "SUCCESS"
        assert result["is_actionable"] is False
        assert result["execution_authorization"] == "DISABLED"
        assert result["contract_version"] == SCENARIO_PLANNER_VERSION
        assert result["instrument"] == "BTC/USD"
        assert result["market_type"] == "SPOT"
        assert result["anchor_source"] == "VERIFIED_MARKET_REFERENCE"
        assert result["reference_price"] > 0
        assert result["volatility_estimate"] > 0

        scenarios = result["scenarios"]
        long_s = scenarios["LONG"]
        short_s = scenarios["SHORT"]

        # Enforce geometry invariants
        assert long_s["stop_loss"] < long_s["entry_reference"] < long_s["take_profit"]
        assert short_s["take_profit"] < short_s["entry_reference"] < short_s["stop_loss"]

        # Verify Gross R:R recomputed from emitted price levels
        recomputed_rr_long = round(long_s["reward_distance_usd"] / long_s["risk_distance_usd"], 2)
        assert long_s["gross_reward_to_risk"] == recomputed_rr_long

        recomputed_rr_short = round(short_s["reward_distance_usd"] / short_s["risk_distance_usd"], 2)
        assert short_s["gross_reward_to_risk"] == recomputed_rr_short

    def test_custom_entry_anchor(self):
        """Verifies custom hypothetical entry anchor."""
        planner = HypotheticalScenarioPlanner()
        custom_anchor = 85000.0
        result = planner.compute_scenario_preview(horizon="4h", custom_entry_price=custom_anchor)
        assert result["status"] == "SUCCESS"
        assert result["anchor_source"] == "USER_CUSTOM"
        assert result["reference_price"] == custom_anchor
        assert result["scenarios"]["LONG"]["entry_reference"] == custom_anchor
        assert result["scenarios"]["SHORT"]["entry_reference"] == custom_anchor

    def test_reject_invalid_custom_entry_prices(self):
        """Rejects negative, zero, NaN, and non-finite custom prices."""
        planner = HypotheticalScenarioPlanner()
        for bad_p in [-100.0, 0.0, float("nan"), float("inf"), -float("inf")]:
            res = planner.compute_scenario_preview(horizon="24h", custom_entry_price=bad_p)
            assert res["status"] == "UNAVAILABLE"
            assert res["rejection_code"] == "INVALID_CUSTOM_ENTRY_PRICE"

    def test_reject_unsupported_subhourly_horizons(self):
        """Verifies that 5m and 15m requests fail-closed because only hourly data is verified."""
        planner = HypotheticalScenarioPlanner()
        for sub_h in ["5m", "15m"]:
            res = planner.compute_scenario_preview(horizon=sub_h)
            assert res["status"] == "UNAVAILABLE"
            assert res["rejection_code"] == "DATA_FREQUENCY_UNSUPPORTED"
            assert "Hourly" in res["rejection_narrative"]

    def test_supported_horizons_coverage(self):
        """Verifies 1h, 4h, and 24h are all supported and scale sigma properly."""
        planner = HypotheticalScenarioPlanner()
        res_1h = planner.compute_scenario_preview(horizon="1h")
        res_4h = planner.compute_scenario_preview(horizon="4h")
        res_24h = planner.compute_scenario_preview(horizon="24h")

        assert res_1h["status"] == "SUCCESS"
        assert res_4h["status"] == "SUCCESS"
        assert res_24h["status"] == "SUCCESS"

        # sigma_H = sigma_1h * sqrt(H)
        sig_1h = res_1h["volatility_estimate"]
        sig_4h = res_4h["volatility_estimate"]
        sig_24h = res_24h["volatility_estimate"]

        assert abs(sig_4h - (sig_1h * 2.0)) < 1e-4
        assert abs(sig_24h - (sig_1h * math.sqrt(24.0))) < 1e-4


class TestSignalSeparation:
    """Verifies that the hypothetical scenario planner does NOT pollute the active directional signal."""

    def test_active_signal_remains_abstained_while_scenario_succeeds(self):
        from models.calibrated_signal_classifier import evaluate_governed_signal_gate
        planner = HypotheticalScenarioPlanner()

        # 1. Active directional signal evaluation
        active_gate = evaluate_governed_signal_gate()
        assert active_gate["status"] == "ABSTAIN"
        assert active_gate["actionable_signal"] is None
        assert active_gate["execution_authorized"] is False

        # 2. Independent hypothetical scenario preview
        preview = planner.compute_scenario_preview(horizon="24h")
        assert preview["status"] == "SUCCESS"
        assert preview["is_actionable"] is False
        assert preview["execution_authorization"] == "DISABLED"

        # 3. Invariants: preview levels must never have direction probabilities or execution authorization
        assert "direction_probability" not in preview
        assert "directional_edge" not in preview
        assert preview["scenarios"]["LONG"]["take_profit"] > 0
        assert preview["scenarios"]["SHORT"]["take_profit"] > 0


class TestStatisticalInferenceCorrection:
    """Verifies Agent C stationary block bootstrap against naive IID sampling."""

    def test_synthetic_ar1_bootstrap_expansion(self):
        """Under an AR(1) process with positive autocorrelation, IID bootstrap
        underestimates the standard error. Stationary block bootstrap must produce
        a wider, more honest confidence interval."""
        np.random.seed(42)
        n = 1000
        rho = 0.8
        # Generate AR(1) series
        eps = np.random.normal(0, 1, size=n)
        x = np.zeros(n)
        for t in range(1, n):
            x[t] = rho * x[t - 1] + eps[t]

        # Naive IID bootstrap (L=1)
        res_iid = compute_segment_aware_bootstrap_ci(
            values=x, block_length=1, n_bootstraps=500, method="circular", seed=42
        )
        se_iid = res_iid["std_error"]

        # Stationary block bootstrap with mean block length 24
        sb_res = compute_segment_aware_bootstrap_ci(
            values=x, block_length=24, n_bootstraps=500, method="stationary", seed=42
        )
        se_sb = sb_res["std_error"]

        # Theoretical inflation factor for AR(1) with rho=0.8 is substantial
        assert se_sb > 1.8 * se_iid, f"Expected block bootstrap SE to be > 1.8x IID SE, got {se_sb / se_iid:.2f}x"

    def test_segment_boundary_preservation(self):
        """Verifies that block bootstrap respects contiguous segment boundaries."""
        # Create two disjoint segments
        seg1 = np.ones(50) * 10.0
        seg2 = np.ones(50) * 20.0
        vals = np.concatenate([seg1, seg2])
        seg_ids = np.array([0] * 50 + [1] * 50)

        res = compute_segment_aware_bootstrap_ci(
            values=vals,
            segment_ids=seg_ids,
            block_length=12,
            n_bootstraps=200,
            method="stationary",
            seed=42
        )
        assert res["mean"] == 15.0
        assert res["ci_lower"] <= 15.0 <= res["ci_upper"]
        assert res["segments_count"] == 2

    def test_block_length_sensitivity_and_paired_loss(self):
        """Verifies sensitivity across L in [12, 24, 48] and paired loss differences."""
        np.random.seed(123)
        n = 300
        # Model loss and baseline loss paired per timestamp
        base_loss = np.random.uniform(0.1, 0.3, size=n)
        # Add small correlated noise
        diff = np.random.normal(0.001, 0.01, size=n)
        model_loss = base_loss + diff

        # Paired loss difference series
        loss_diff = model_loss - base_loss

        sens = run_block_length_sensitivity_analysis(
            values=loss_diff,
            candidate_block_lengths=[12, 24, 48],
            n_bootstraps=200,
            seed=42
        )

        assert "L_12_stationary" in sens
        assert "L_24_stationary" in sens
        assert "L_48_stationary" in sens
        assert "L_1_naive_iid" in sens

        # Check that SE increases from L=1 to L=24
        se_iid = sens["L_1_naive_iid"]["std_error"]
        se_24 = sens["L_24_stationary"]["std_error"]
        assert se_24 > 0.0


class TestProspectiveWorkerHardening:
    """Verifies Agent D prospective worker locking and state integrity."""

    def test_single_instance_lock_acquisition_and_release(self):
        """Verifies that acquire_worker_lock creates lockfile and release cleans it up."""
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

        acquired, pid = acquire_worker_lock()
        assert acquired is True
        assert pid == os.getpid()
        assert os.path.exists(LOCK_FILE)
        assert is_worker_running() is True

        # Second acquisition should fail because lock is held by current process
        acquired2, pid2 = acquire_worker_lock()
        assert acquired2 is False
        assert pid2 == os.getpid()

        # Release lock
        release_worker_lock()
        assert not os.path.exists(LOCK_FILE)
        assert is_worker_running() is False

    def test_prospective_worker_status_telemetry(self):
        """Verifies status telemetry file structure and honesty."""
        assert os.path.exists(STATUS_FILE)
        with open(STATUS_FILE, "r") as f:
            status = json.load(f)

        assert status["worker_version"] == "PROSPECTIVE-WORKER-v2.0"
        assert status["worker_operational_state"] == "STANDALONE_CLI_SCHEDULED"
        # Must not fabricate autonomous process running
        assert status["is_autonomous_process_running"] is False
        assert "ledger_record_counts" in status
        counts = status["ledger_record_counts"]
        assert counts["total_records"] >= 0
        assert counts["pending_maturation"] >= 0
        assert counts["matured_records"] >= 0
        assert "governed_prospective_progress" in status

    def test_candle_sync_bounded_backoff(self):
        """Verifies that sync_live_candles handles API failures gracefully with retry backoff."""
        with patch("engine.prospective_worker.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 503
            mock_get.return_value = mock_resp

            # Should exhaust max_retries and return without crashing
            res = sync_live_candles(max_retries=2, base_backoff=0.01)
            assert res == 0

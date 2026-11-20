"""
Unit and Acceptance Tests for BTCognitive V33.4 — HTF Breakout Prospective Shadow Validation Protocol
Validates:
1. Frozen Protocol Constants & Parameter Invariants.
2. Strict Ledger Separation (Shadow Ledger vs Conformal Forecast Ledger).
3. Shadow Ledger Schema Validation (Executed & Suppressed Dual Accounting).
4. Inactive Collector Operational Guardrail & Network Lock.
5. Conformal Forecast Ledger Frozen at 7/100 Blocks.
6. Protected Hash Verification (Manifest 1.7.0).
7. Governance Invariants (Disabled Live Trading, Offline Research Only).
"""

import hashlib
import json
from pathlib import Path
import pytest
from engine.htf_prospective_shadow_runner import HTFProspectiveShadowProtocol

class TestV33_4_HTF_Prospective_Protocol:

    @pytest.fixture(autouse=True)
    def setup_protocol(self):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.protocol = HTFProspectiveShadowProtocol(self.base_dir)
        self.report_dir = self.base_dir / "research" / "reports" / "offline_mvp" / "20261101_330400_v33_04_htf_prospective_protocol"
        self.schema_path = self.report_dir / "v33_4_shadow_ledger_schema.json"
        self.hash_json = self.report_dir / "v33_4_protected_hash_verification.json"

    def test_protocol_constants_and_invariants(self):
        """Verify that protocol constants match pre-registered parameters exactly."""
        status = self.protocol.get_protocol_status()
        assert status["strategy"] == "HTF_RANGE_EXPANSION_BREAKOUT"
        assert status["filter"] == "MarketRegimeClassifier"
        assert status["hysteresis_bars"] == 3
        assert status["donchian_window_4h"] == 20
        assert status["max_hold_hours"] == 72
        assert status["modeled_cost_bps"] == 26.0
        assert status["notional_allocation_fraction"] == 0.10
        assert status["min_required_blocks"] == 100
        assert status["live_trading"] == "DISABLED"
        assert status["model_authorization"] == "OFFLINE_RESEARCH_ONLY"

    def test_ledger_path_separation(self):
        """Assert strategy shadow ledger is strictly separated from conformal forecast ledger."""
        status = self.protocol.get_protocol_status()
        assert status["ledger_distinct_from_conformal"] is True
        assert self.protocol.LEDGER_RELATIVE_PATH != self.protocol.CONFORMAL_LEDGER_PATH
        assert "htf_prospective_shadow_ledger.jsonl" in self.protocol.LEDGER_RELATIVE_PATH
        assert "prospective_forecast_ledger.jsonl" in self.protocol.CONFORMAL_LEDGER_PATH

    def test_schema_validation_executed_and_suppressed(self):
        """Verify schema validation for both EXECUTED_SHADOW and SUPPRESSED_CHOP events."""
        valid_executed = {
            "signal_id": "SIG_20261101_001",
            "timestamp_issue_utc": "2026-11-01T00:00:00Z",
            "breakout_bar_close": 70100.0,
            "execution_open_price": 70120.0,
            "stop_loss_price": 68500.0,
            "regime_at_entry": "VOLATILITY_EXPANSION",
            "regime_confirmed_bars": 4,
            "filter_action": "EXECUTED_SHADOW",
            "cost_modeled_bps": 26.0,
            "exit_timestamp_utc": "2026-11-04T00:00:00Z",
            "exit_price": 71500.0,
            "holding_hours": 72.0,
            "gross_return_bps": 196.8,
            "net_return_bps": 170.8,
            "protocol_version": "V33.4_FROZEN_SHADOW"
        }
        assert self.protocol.validate_ledger_record(valid_executed) is True

        valid_suppressed = {
            "signal_id": "SIG_20261101_002",
            "timestamp_issue_utc": "2026-11-01T04:00:00Z",
            "breakout_bar_close": 70300.0,
            "execution_open_price": 70310.0,
            "stop_loss_price": 69000.0,
            "regime_at_entry": "CONSOLIDATION_RANGE",
            "regime_confirmed_bars": 5,
            "filter_action": "SUPPRESSED_CHOP",
            "cost_modeled_bps": 26.0,
            "exit_timestamp_utc": "2026-11-02T12:00:00Z",
            "exit_price": 69000.0,
            "holding_hours": 32.0,
            "gross_return_bps": -186.3,
            "net_return_bps": -212.3,
            "protocol_version": "V33.4_FROZEN_SHADOW"
        }
        assert self.protocol.validate_ledger_record(valid_suppressed) is True

        # Test failure on cost mismatch
        invalid_cost = valid_executed.copy()
        invalid_cost["cost_modeled_bps"] = 24.0
        with pytest.raises(ValueError, match="Cost mismatch"):
            self.protocol.validate_ledger_record(invalid_cost)

        # Test failure on net return mismatch
        invalid_net = valid_executed.copy()
        invalid_net["net_return_bps"] = 196.8  # Did not subtract 26.0 bps
        with pytest.raises(ValueError, match="Net return mismatch"):
            self.protocol.validate_ledger_record(invalid_net)

    def test_collector_inactive_guardrail(self):
        """Assert starting live collection raises RuntimeError when collector is inactive."""
        assert self.protocol.COLLECTOR_STATUS == "INACTIVE_AWAITING_MANAGEMENT_AUTHORIZATION"
        assert self.protocol.NETWORK_ACCESS == "BLOCKED"
        with pytest.raises(RuntimeError, match="Operational Prerequisite Violation"):
            self.protocol.start_live_collection()

    def test_conformal_forecast_ledger_frozen_7_blocks(self):
        """Assert prospective forecast ledger remains frozen with SHA-256 verified."""
        conformal_file = self.base_dir / "data" / "prospective_forecast_ledger.jsonl"
        assert conformal_file.exists()

        lines = [line.strip() for line in open(conformal_file) if line.strip()]
        assert len(lines) == 21

        # Verify SHA-256 hash
        hasher = hashlib.sha256()
        with open(conformal_file, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        expected_sha = "ee58b37c71c5c3ff322af3084d27b306eb0a445a8bd6e01a74b76d8168ccd491"
        assert hasher.hexdigest() == expected_sha

    def test_manifest_v1_7_0_and_hashes(self):
        """Verify protected hash verification JSON matches manifest 1.7.0."""
        assert self.hash_json.exists()
        with open(self.hash_json) as f:
            data = json.load(f)

        assert data["manifest_version"] == "1.7.0"
        assert data["governed_determination"] == "FROZEN_RESEARCH_PROTOCOL_PRE_REGISTERED"

        for ds in data["protected_dataset_registry"]:
            rel_path = ds["relative_path"]
            file_path = self.base_dir / rel_path
            assert file_path.exists()

            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            assert hasher.hexdigest() == ds["expected_sha256"]
            assert ds["hash_matched"] is True

    def test_governance_invariants(self):
        """Verify governance invariants: live trading DISABLED, model authorization OFFLINE_RESEARCH_ONLY."""
        with open(self.hash_json) as f:
            data = json.load(f)

        invariants = data["governance_invariants"]
        assert invariants["live_trading"] == "DISABLED - ANALYSIS ONLY"
        assert invariants["model_authorization"] == "OFFLINE_RESEARCH_ONLY"
        assert "RESTRICTED" in invariants["vpin_gate_status"]
        assert "RESTRICTED" in invariants["algorithmic_routing_status"]
        assert "Q2=INSUFFICIENT_EVIDENCE" in invariants["entry_analysis_architecture"]

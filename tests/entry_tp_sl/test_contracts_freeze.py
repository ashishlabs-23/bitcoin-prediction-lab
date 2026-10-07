import json
import hashlib
from pathlib import Path
import pytest

TRACK_ROOT = Path(__file__).resolve().parents[2] / "research" / "entry_tp_sl"
REPO_ROOT = Path(__file__).resolve().parents[2]


def test_contracts_parse_and_contain_required_fields():
    instrument_contract = json.loads((TRACK_ROOT / "instrument_contract.json").read_text(encoding="utf-8"))
    decision_contract = json.loads((TRACK_ROOT / "decision_contract.json").read_text(encoding="utf-8"))
    entry_contract = json.loads((TRACK_ROOT / "entry_execution_contract.json").read_text(encoding="utf-8"))
    outcome_contract = json.loads((TRACK_ROOT / "outcome_accounting_contract.json").read_text(encoding="utf-8"))
    manifest = json.loads((TRACK_ROOT / "contract_freeze_manifest.json").read_text(encoding="utf-8"))

    assert instrument_contract["status"] == "FROZEN"
    assert instrument_contract["instrument"]["symbol"] == "BTC/USD"
    assert instrument_contract["instrument"]["market_type"] == "SPOT"

    assert decision_contract["status"] == "FROZEN"
    assert decision_contract["decision_timing"]["cadence_seconds"] == 900
    assert decision_contract["point_in_time_invariants"]["no_forming_bar_features"] is True

    assert entry_contract["status"] == "FROZEN"
    assert entry_contract["execution_mechanism"]["liquidity_role"] == "TAKER"
    assert entry_contract["execution_cost_scenarios"]["BASE"]["total_round_trip_cost_bps"] == 35.0
    assert entry_contract["execution_cost_scenarios"]["CONSERVATIVE"]["total_round_trip_cost_bps"] == 65.0

    assert outcome_contract["status"] == "FROZEN"
    assert outcome_contract["position_lifecycle"]["max_concurrent_positions"] == 1
    assert outcome_contract["volatility_estimator"]["PRIMARY"]["name"] == "ATR_14_15M"
    assert len(outcome_contract["predetermined_barrier_grid"]) == 5
    assert outcome_contract["time_horizon"]["PRIMARY_HORIZON_MINUTES"] == 240


def test_dataset_sha256_matches_manifest():
    manifest = json.loads((TRACK_ROOT / "data_intake_manifest.json").read_text(encoding="utf-8"))
    freeze_manifest = json.loads((TRACK_ROOT / "contract_freeze_manifest.json").read_text(encoding="utf-8"))
    
    assert manifest["approved_for_research"] is True
    assert manifest["sha256"] == freeze_manifest["dataset_sha256"]
    
    csv_path = REPO_ROOT / "data" / "raw" / "btcusd_1-min_data.csv"
    assert csv_path.exists()
    
    h = hashlib.sha256()
    with open(csv_path, "rb") as f:
        while chunk := f.read(8192 * 1024):
            h.update(chunk)
    assert h.hexdigest() == manifest["sha256"]


def test_contract_manifest_integrity_and_tamper_detection():
    manifest_path = TRACK_ROOT / "contract_freeze_manifest.json"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    recorded_hash = manifest_data["manifest_sha256"]

    # Reconstruct data without the hash field
    check_data = {k: v for k, v in manifest_data.items() if k != "manifest_sha256"}
    computed_hash = hashlib.sha256(json.dumps(check_data, indent=2, sort_keys=True).encode("utf-8")).hexdigest()
    assert recorded_hash == computed_hash, "Manifest integrity hash failed"

    # Verify each individual file hash recorded in manifest
    for fname, expected_hash in manifest_data["contract_file_hashes"].items():
        fpath = TRACK_ROOT / fname
        assert fpath.exists(), f"Missing contract file: {fname}"
        actual_hash = hashlib.sha256(fpath.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {fname}: expected {expected_hash}, got {actual_hash}"


def test_intrabar_ambiguity_and_timeout_accounting_invariants():
    outcome_contract = json.loads((TRACK_ROOT / "outcome_accounting_contract.json").read_text(encoding="utf-8"))
    
    # Invariant: Unresolved dual touches default to conservative SL_FIRST
    assert outcome_contract["intrabar_ambiguity_policy"]["unresolved_dual_touch_policy"] == "CONSERVATIVE_SL_FIRST"
    assert outcome_contract["intrabar_ambiguity_policy"]["record_same_timestamp_collision"] is True
    assert outcome_contract["intrabar_ambiguity_policy"]["record_unresolved_intrabar_order"] is True
    
    # Invariant: Timeout is never hard-coded to -1R
    assert outcome_contract["r_multiple_accounting"]["timeout_is_never_hardcoded_minus_one_r"] is True
    assert "P_timeout" in outcome_contract["r_multiple_accounting"]["gross_r_timeout_exit_formula"]


def test_cost_deductions_are_strictly_positive():
    entry_contract = json.loads((TRACK_ROOT / "entry_execution_contract.json").read_text(encoding="utf-8"))
    base_costs = entry_contract["execution_cost_scenarios"]["BASE"]
    conservative_costs = entry_contract["execution_cost_scenarios"]["CONSERVATIVE"]

    for cost_dict in [base_costs, conservative_costs]:
        for k, v in cost_dict.items():
            if isinstance(v, (int, float)):
                assert v > 0, f"Cost field {k} must be strictly positive, got {v}"


def test_trial_ledger_root_entry_is_deterministic():
    ledger_path = TRACK_ROOT / "trial_ledger.jsonl"
    assert ledger_path.exists()
    
    lines = [line.strip() for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 1
    
    root_event = json.loads(lines[0])
    assert root_event["event_index"] == 0
    assert root_event["trial_id"] == "TRIAL_ROOT_REGISTRATION"
    assert root_event["status"] == "REGISTERED"
    assert root_event["parent_hash"] is None
    
    # Verify cryptographic integrity of every entry in the hash chain
    prev_hash = None
    for i, line in enumerate(lines):
        entry = json.loads(line)
        assert entry["event_index"] == i
        if i == 0:
            assert entry["parent_hash"] is None
        else:
            assert entry["parent_hash"] == prev_hash
        check_event = {k: v for k, v in entry.items() if k != "entry_hash"}
        computed_hash = hashlib.sha256(json.dumps(check_event, sort_keys=True).encode("utf-8")).hexdigest()
        assert entry["entry_hash"] == computed_hash
        prev_hash = entry["entry_hash"]


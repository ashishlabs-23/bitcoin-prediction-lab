import json
import hashlib
from pathlib import Path
import pytest

TRACK_ROOT = Path(__file__).resolve().parents[2] / "research" / "entry_tp_sl"
REPO_ROOT = Path(__file__).resolve().parents[2]


def test_pilot_label_manifest_and_samples():
    pilot_manifest_path = TRACK_ROOT / "pilot_labels" / "pilot_labels_manifest.json"
    pilot_sample_path = TRACK_ROOT / "pilot_labels" / "pilot_labels_sample.jsonl"
    
    assert pilot_manifest_path.exists()
    assert pilot_sample_path.exists()
    
    manifest = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    assert manifest["resolver_version"] == "ENTRY_TP_SL_RESOLVER_V1"
    assert manifest["row_count"] == 500
    assert manifest["outcome_counts"]["TP_FIRST"] > 0
    assert manifest["outcome_counts"]["SL_FIRST"] > 0
    assert manifest["outcome_counts"]["TIMEOUT"] > 0
    assert manifest["COLLISION_count"] >= 0

    lines = [line.strip() for line in pilot_sample_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 500
    
    for line in lines:
        record = json.loads(line)
        assert record["resolver_version"] == "ENTRY_TP_SL_RESOLVER_V1"
        assert record["pair_id"] == "barrier_pair_01"
        assert record["outcome_state"] in ["TP_FIRST", "SL_FIRST", "TIMEOUT", "DATA_GAP", "UNRESOLVED_INTRABAR"]
        if record["same_timestamp_collision"]:
            assert record["unresolved_intrabar_order"] is True
            assert record["outcome_state"] == "SL_FIRST"
        if record["timeout"]:
            assert record["outcome_state"] == "TIMEOUT"
            assert record["gross_r"] is not None


def test_feasibility_audit_report_presence():
    audit_md = TRACK_ROOT / "feasibility_audit.md"
    reachability_md = TRACK_ROOT / "resolver_reachability_after_6B.md"
    
    assert audit_md.exists()
    assert reachability_md.exists()
    
    content = audit_md.read_text(encoding="utf-8")
    assert "7,766,111" in content
    assert "510,989" in content
    assert "FEASIBILITY UPPER BOUND" in content

"""
tests/test_post_repair_monitoring.py — Tests for Post-Repair Longitudinal Monitoring Engine
============================================================================================
Verifies:
- Monitoring status is ACTIVE_POST_REPAIR_COLLECTION.
- Observed blocks initialized at 0.
- Production model is frozen.
- Archived pre-repair blocks are recorded as 35 (PRE_REPAIR_HISTORY).
- Hawkes shadow status is VALIDATED_SHADOW_ONLY.
"""

from research.post_repair_longitudinal_monitor import post_repair_monitor, POST_REPAIR_EVIDENCE_START
from engine.longitudinal_status import longitudinal_status_service

def test_post_repair_monitor_status():
    status = post_repair_monitor.get_status()
    assert status["evidence_phase"] == "POST_REPAIR"
    assert status["monitoring_status"] == "ACTIVE_POST_REPAIR_COLLECTION"
    assert status["production_model_frozen"] is True
    assert status["observed_blocks"] == 0
    assert status["target_blocks"] == 90
    assert status["next_milestone"] == 5
    assert status["archived_pre_repair_blocks"] == 35

def test_longitudinal_service_endpoint_payload():
    report = longitudinal_status_service.get_status_report().to_dict()
    assert report["evidence_phase"] == "POST_REPAIR"
    assert report["monitoring_status"] == "ACTIVE_POST_REPAIR_COLLECTION"
    assert report["observed_blocks"] == 0
    assert report["archived_pre_repair_evidence"]["archived_blocks"] == 35
    assert report["hawkes_shadow_progress"]["role"] == "VALIDATED_SHADOW_ONLY"
    assert report["research_stop_rule_status"] == "NO_NEW_RESEARCH_REQUIRED"

"""
tests/test_research_results_api.py
===================================
Automated regression tests verifying the Research Results API & UI contracts:
1. Historical research results remain fully accessible when production forecasting is blocked.
2. Production forecast remains unavailable (BLOCKED_PROVENANCE_UNVERIFIED) and trading disabled.
3. API returns real, source-linked report content with exact SHA256 provenance hashes.
4. Path traversal, secret file reading, and arbitrary filesystem access are strictly blocked.
5. Known conflicting reports are flagged CONFLICT_REQUIRES_RECONCILIATION and never silently merged.
6. Missing or corrupt artifacts fail closed without fabricating synthetic substitute metrics.
7. Frontend code visibly distinguishes live price data, archived results, and blocked production model.
"""

import os
import hashlib
import pytest
from fastapi.testclient import TestClient
from api.server import app
import api.routes_research as research_module

client = TestClient(app)


def test_research_results_catalog_available_when_forecast_blocked():
    """Historical research results are accessible even when production forecasting is blocked."""
    # 1. Fetch research results
    res = client.get("/api/research/results")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "AVAILABLE"
    assert data["provenance_mode"] == "READ_ONLY_ARCHIVED_RESEARCH"
    assert data["runtime_forecast_gate"] == "BLOCKED_PROVENANCE_UNVERIFIED"
    assert data["production_trading_enabled"] is False
    assert data["total_reports"] >= 10
    assert len(data["reports"]) == data["total_reports"]

    # 2. Verify production forecast gate remains strictly blocked
    gate_res = client.get("/api/research/entry-tp-sl")
    assert gate_res.status_code == 200
    gate_data = gate_res.json()
    assert gate_data["status"] == "BLOCKED"
    assert gate_data["research_status"] in {"BLOCKED_PROVENANCE_UNVERIFIED", "BLOCKED_AUDIT_FAILURE"}
    assert gate_data["live_capital_authorized"] is False
    assert gate_data["entry_price"] is None
    assert gate_data["tp_price"] is None
    assert gate_data["sl_price"] is None


def test_all_allowlisted_reports_present_with_exact_hashes():
    """All allowlisted research reports exist on disk and match expected SHA256 hashes."""
    res = client.get("/api/research/results")
    assert res.status_code == 200
    data = res.json()

    for report in data["reports"]:
        report_id = report["report_id"]
        rel_path = report["source_path"]
        full_path = os.path.abspath(os.path.join(research_module.REPO_ROOT, rel_path))

        assert os.path.isfile(full_path), f"Report file for '{report_id}' missing at '{rel_path}'"
        assert report["file_exists"] is True
        if report_id == "post-repair-5-block":
            assert report["provenance_state"] in ("INTEGRITY_CHECKED", "INDEPENDENTLY_REPRODUCED")
        else:
            assert report["provenance_state"] == "INTEGRITY_CHECKED"
        assert report["runtime_authorized"] is False

        # Verify disk SHA256 matches returned SHA256 exactly
        with open(full_path, "rb") as f:
            disk_sha = hashlib.sha256(f.read()).hexdigest()
        assert report["source_artifact_sha256"] == disk_sha, f"SHA mismatch for {report_id}"


def test_research_report_content_retrieval_and_source_linking():
    """Individual report content is accurately retrieved and source-linked."""
    expected_reports = [
        "uncertainty-04",
        "entry-tp-sl-v3",
        "entry-tp-sl-decision",
        "vol-edge-01",
        "metric-reconciliation",
        "combined-production-health",
        "longitudinal-35-observed",
        "post-repair-5-block"
    ]

    for rid in expected_reports:
        res = client.get(f"/api/research/reports/{rid}")
        assert res.status_code == 200, f"Failed to retrieve report content for {rid}"
        data = res.json()
        assert data["report_id"] == rid
        if rid == "post-repair-5-block":
            assert data["provenance_state"] in ("INTEGRITY_CHECKED", "INDEPENDENTLY_REPRODUCED")
        else:
            assert data["provenance_state"] == "INTEGRITY_CHECKED"
        assert data["runtime_authorized"] is False
        assert len(data["content"]) > 100

        # Verify disk content matches retrieved content exactly
        full_path = os.path.abspath(os.path.join(research_module.REPO_ROOT, data["source_path"]))
        with open(full_path, "rb") as f:
            disk_content = f.read().decode("utf-8", errors="replace")
        assert data["content"] == disk_content


def test_path_traversal_and_arbitrary_file_read_prevention():
    """Path traversal and access to non-allowlisted files are strictly rejected."""
    traversal_targets = [
        "../../.env",
        "..%2F..%2F.env",
        "../requirements.txt",
        "config/security.py",
        "api/server.py",
        "non_existent_report_id",
        "../..",
        "/etc/passwd",
        "uncertainty-04/../../../.git"
    ]

    for target in traversal_targets:
        res = client.get(f"/api/research/reports/{target}")
        assert res.status_code in {400, 404}, f"Path traversal target '{target}' was not rejected (HTTP {res.status_code})"


def test_conflicting_reports_visibly_flagged_and_never_merged():
    """Known scientific contradictions are explicitly flagged with CONFLICT_REQUIRES_RECONCILIATION."""
    res = client.get("/api/research/results")
    assert res.status_code == 200
    data = res.json()

    # Index reports by id
    reports_by_id = {r["report_id"]: r for r in data["reports"]}

    # 1. Uncertainty-04 vs Metric Reconciliation
    # Conformal risk envelope (92.84% containment) vs Directional accuracy (50.0% / AUC 0.504 — no edge)
    u04 = reports_by_id["uncertainty-04"]
    assert u04["contradiction"] is not None
    assert u04["contradiction"]["flag"] == "CONFLICT_REQUIRES_RECONCILIATION"
    assert "Directional" in u04["contradiction"]["primary_issue"]
    mr = reports_by_id["metric-reconciliation"]
    # Verify metric reconciliation contains 50.0% directional accuracy
    dir_metrics = [m for m in mr["key_metrics"] if "Directional Accuracy" in m["name"]]
    assert len(dir_metrics) == 1
    assert "50.0%" in dir_metrics[0]["value"]
    assert "coin flip" in dir_metrics[0]["interpretation"].lower()

    # 2. Entry-TP-SL V3: In-sample statistical setup separation vs Net economic viability (COST_ERASED)
    v3 = reports_by_id["entry-tp-sl-v3"]
    assert v3["governance_verdict"] == "COST_ERASED"
    assert v3["contradiction"] is not None
    assert v3["contradiction"]["flag"] == "CONFLICT_REQUIRES_RECONCILIATION"

    # 3. Legacy Combined Production Health vs Current Runtime
    cph = reports_by_id["combined-production-health"]
    assert cph["contradiction"] is not None
    assert cph["contradiction"]["flag"] == "CONFLICT_REQUIRES_RECONCILIATION"
    assert "Current Runtime" in cph["contradiction"]["primary_issue"]
    assert "BLOCKED_PROVENANCE_UNVERIFIED" in cph["contradiction"]["resolution_note"]

    # 4. Longitudinal 35-Block vs Post-Repair 5-Block Clean Milestone
    l35 = reports_by_id["longitudinal-35-observed"]
    pr5 = reports_by_id["post-repair-5-block"]
    assert l35["contradiction"] is not None
    assert pr5["contradiction"] is not None
    assert l35["contradiction"]["flag"] == "CONFLICT_REQUIRES_RECONCILIATION"
    assert pr5["contradiction"]["flag"] == "CONFLICT_REQUIRES_RECONCILIATION"


def test_missing_artifact_fails_closed_without_synthetic_metrics(monkeypatch):
    """Missing report files produce an explicit error state, never fabricated substitute results."""
    # Temporarily insert a dummy report with a missing file into the registry
    test_id = "test-missing-report"
    fake_registry = dict(research_module.REPORT_REGISTRY)
    fake_registry[test_id] = {
        "title": "Missing Synthetic Report",
        "track": "Test Track",
        "date": "2026-10-14",
        "relative_path": "research/reports/non_existent_file_xyz_123.md",
        "expected_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        "sample_size_description": "N/A",
        "horizon": "N/A",
        "governance_verdict": "UNVERIFIED",
        "provenance_state": "UNVERIFIED",
        "scientific_limitations": "Test limitations",
        "key_metrics": []
    }
    monkeypatch.setattr(research_module, "REPORT_REGISTRY", fake_registry)

    res = client.get("/api/research/results")
    assert res.status_code == 200
    data = res.json()
    missing_report = next(r for r in data["reports"] if r["report_id"] == test_id)
    assert missing_report["file_exists"] is False
    assert missing_report["provenance_state"] == "MISSING_ARTIFACT"
    assert missing_report["source_artifact_sha256"] == "FILE_NOT_FOUND"

    # Detail request for the missing file must return 404
    detail_res = client.get(f"/api/research/reports/{test_id}")
    assert detail_res.status_code == 404


def test_frontend_distinguishes_three_pillars_and_discloses_reconciliations():
    """web/app.js visibly implements 3-pillar separation, navigation, and contradiction handling."""
    app_js_path = os.path.join(research_module.REPO_ROOT, "web", "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Three distinct pillars in UI
    assert "1. Live Market Observations" in content
    assert "2. Archived Research Evidence" in content
    assert "3. Production Forecast & Execution" in content
    assert "BLOCKED · PROVENANCE UNVERIFIED" in content

    # 2. Navigation to #/research
    assert 'href: "#/research"' in content
    assert 'path === "/research"' in content
    assert "ResearchResultsView" in content

    # 3. Contradiction banner and badges
    assert "CONFLICT_REQUIRES_RECONCILIATION" in content
    assert "Visible Scientific Contradiction Reconciliations" in content
    assert "Risk Envelope ≠ Directional Alpha" in content

    # 4. Safe source inspection modal (no dangerouslySetInnerHTML)
    assert "Inspect Source Markdown" in content
    assert "dangerouslySetInnerHTML" not in content

    # 5. PredictionPanel blocked state provides research link
    assert "View Archived Research Results & Evidence" in content

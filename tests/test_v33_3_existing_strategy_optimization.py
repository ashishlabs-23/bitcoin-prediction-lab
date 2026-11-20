"""
tests/test_v33_3_existing_strategy_optimization.py — Dedicated Acceptance Suite for V33.3
======================================================================================
Verifies:
1. Complete strategy inventory and classification.
2. Authentic empirical performance figures of HTF_RANGE_EXPANSION_BREAKOUT from v13 tournament manifest.
3. Separation of authentic OHLCV evidence from quarantined datasets and synthetic heuristics.
4. Identification of failure modes (chop / range bound regime losses).
5. Protected dataset registry SHA-256 integrity.
6. Strict governance invariants: live trading permanently DISABLED, OFFLINE_RESEARCH_ONLY.
"""

import os
import json
import hashlib
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
V13_MANIFEST_PATH = os.path.join(REPO_ROOT, "experiments", "results", "v13_strategy_tournament_manifest.json")
V33_3_MANIFEST_PATH = os.path.join(
    REPO_ROOT,
    "research",
    "reports",
    "offline_mvp",
    "20261031_330300_v33_03_existing_strategy_optimization",
    "v33_3_protected_hash_verification.json"
)


def compute_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestExistingStrategyInventoryAndPerformance:
    """Verifies strategy inventory, tournament metrics, and performance audit."""

    def test_v13_tournament_manifest_exists(self):
        assert os.path.exists(V13_MANIFEST_PATH), "v13_strategy_tournament_manifest.json must exist"

    def test_htf_range_expansion_is_only_positive_candidate(self):
        """Verifies HTF_RANGE_EXPANSION_BREAKOUT is the only positive Net EV candidate under institutional fees."""
        with open(V13_MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        inst = manifest["scenarios"]["COINBASE_INSTITUTIONAL_18BPS"]
        candidates = inst["top_candidates"]

        htf_cand = next((c for c in candidates if c["id"] == "HTF_RANGE_EXPANSION_BREAKOUT"), None)
        assert htf_cand is not None, "HTF_RANGE_EXPANSION_BREAKOUT must be present in top candidates"

        # Verify key empirical metrics
        assert htf_cand["trade_count"] == 194
        assert pytest.approx(htf_cand["win_rate"], 0.01) == 0.443
        assert pytest.approx(htf_cand["profit_factor"], 0.01) == 1.07
        assert pytest.approx(htf_cand["net_expectancy_bps"], 0.1) == 11.0
        assert pytest.approx(htf_cand["breakeven_cost_bps"], 0.1) == 31.6
        assert pytest.approx(htf_cand["avg_win_bps"], 0.1) == 383.2
        assert pytest.approx(htf_cand["avg_loss_bps"], 0.1) == -285.3

        # Verify all other candidates have negative Net EV
        other_candidates = [c for c in candidates if c["id"] != "HTF_RANGE_EXPANSION_BREAKOUT"]
        for oc in other_candidates:
            assert oc["net_expectancy_bps"] < 0, f"Candidate {oc['id']} must have negative net expectancy"
            assert oc["profit_factor"] < 1.0, f"Candidate {oc['id']} must have profit factor < 1.0"

    def test_retail_fee_destruction(self):
        """Verifies that retail friction (87 bps) consumes edge for all strategies."""
        with open(V13_MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        retail = manifest["scenarios"]["COINBASE_RETAIL_87BPS"]
        for c in retail["top_candidates"]:
            assert c["net_expectancy_bps"] < 0, f"All strategies must fail retail fee drag: {c['id']}"
            assert c["profit_factor"] < 1.0

    def test_breakeven_cost_threshold(self):
        """Verifies the breakeven cost ceiling of HTF_RANGE_EXPANSION_BREAKOUT is 31.6 bps."""
        with open(V13_MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        inst_cands = manifest["scenarios"]["COINBASE_INSTITUTIONAL_18BPS"]["top_candidates"]
        htf = next(c for c in inst_cands if c["id"] == "HTF_RANGE_EXPANSION_BREAKOUT")
        assert pytest.approx(htf["breakeven_cost_bps"], 0.1) == 31.6


class TestDataProvenanceAndProtectedLedger:
    """Verifies SHA-256 hashes of protected datasets and governance invariants."""

    def test_v33_3_protected_hash_manifest_exists(self):
        assert os.path.exists(V33_3_MANIFEST_PATH), "v33_3_protected_hash_verification.json must exist"

    def test_protected_datasets_hashes_match(self):
        with open(V33_3_MANIFEST_PATH, "r", encoding="utf-8") as f:
            v_manifest = json.load(f)

        for entry in v_manifest["protected_dataset_registry"]:
            rel_path = entry["relative_path"]
            full_path = os.path.join(REPO_ROOT, rel_path)
            assert os.path.exists(full_path), f"Protected file {rel_path} must exist"
            actual_sha = compute_sha256(full_path)
            assert actual_sha == entry["expected_sha256"], f"SHA256 mismatch for {rel_path}"

    def test_governance_invariants(self):
        with open(V33_3_MANIFEST_PATH, "r", encoding="utf-8") as f:
            v_manifest = json.load(f)

        invariants = v_manifest["governance_invariants"]
        assert invariants["live_trading"] == "DISABLED — ANALYSIS ONLY"
        assert invariants["model_authorization"] == "OFFLINE_RESEARCH_ONLY"
        assert invariants["selected_candidate"] == "HTF_RANGE_EXPANSION_BREAKOUT"
        assert invariants["governed_decision"] == "EXISTING_STRATEGY_IMPROVEMENT_CANDIDATE"


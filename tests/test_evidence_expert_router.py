"""
tests/test_evidence_expert_router.py
======================================
Tests for Adaptive Evidence & Expert Router (AEER):
1. Horizon-Conditioned Dynamic Feature Selection (15m vs Cycle).
2. Marginal Value of Information (VOI) computation & Collinearity Redundancy Pruning.
3. Three Evidence Control Modes: AI_RECOMMEND, AI_PLUS_USER, USER_ONLY.
4. Mixture-of-Experts (MoE) Strategy Routing across 5 canonical MEIE specialists.
"""

import pytest
from engine.evidence_router import (
    AdaptiveEvidenceRouter,
    adaptive_evidence_router,
    compute_indicator_config_hash,
    SUPPORTED_HORIZONS,
    INFORMATION_CLUSTERS,
    HORIZON_FEATURE_AFFINITY,
    MEIE_EXPERTS
)


def test_supported_horizons_and_clusters():
    """Verify all 6 horizons and 5 information clusters are defined."""
    assert len(SUPPORTED_HORIZONS) == 6
    assert "15m" in SUPPORTED_HORIZONS
    assert "CYCLE" in SUPPORTED_HORIZONS
    assert len(INFORMATION_CLUSTERS) == 5
    assert "ORDER_FLOW_LIQUIDITY" in INFORMATION_CLUSTERS
    assert "ONCHAIN_VALUATION" in INFORMATION_CLUSTERS


def test_horizon_conditioned_feature_selection():
    """
    Verify that 15m horizon selects micro features (OFI, Hawkes, VPIN) as PRIMARY,
    while CYCLE horizon selects on-chain features (MVRV, Mayer, Puell) as PRIMARY.
    """
    router = AdaptiveEvidenceRouter()

    # 15-minute horizon
    res_15m = router.route_evidence(horizon="15m", evidence_mode="AI_RECOMMEND")
    primary_15m = [x["indicator"] for x in res_15m["categorized_evidence"]["PRIMARY"]]
    excluded_15m = [x["indicator"] for x in res_15m["categorized_evidence"]["EXCLUDED"]]

    assert "ofi" in primary_15m or "hawkes" in primary_15m
    assert "mvrv" in excluded_15m
    assert "mayer" in excluded_15m

    # Cycle horizon
    res_cycle = router.route_evidence(horizon="CYCLE", evidence_mode="AI_RECOMMEND")
    primary_cycle = [x["indicator"] for x in res_cycle["categorized_evidence"]["PRIMARY"]]
    excluded_cycle = [x["indicator"] for x in res_cycle["categorized_evidence"]["EXCLUDED"]]

    assert "mvrv" in primary_cycle or "mayer" in primary_cycle
    assert "ofi" in excluded_cycle
    assert "rv_5m" in excluded_cycle


def test_marginal_voi_computation_and_redundancy_penalty():
    """
    Verify that marginal Value of Information (VOI) decreases when redundant
    collinear indicators from the same cluster are added.
    """
    router = AdaptiveEvidenceRouter()

    # MVRV alone in ONCHAIN_VALUATION cluster
    voi_mvrv_alone = router.compute_marginal_voi(
        indicator="mvrv",
        currently_selected=[],
        horizon="CYCLE"
    )
    assert voi_mvrv_alone["voi_bps"] >= 3.0
    assert voi_mvrv_alone["collinearity_penalty"] == 0.0

    # STH-MVRV added when MVRV is already active
    voi_sth_mvrv = router.compute_marginal_voi(
        indicator="sth_mvrv",
        currently_selected=["mvrv"],
        horizon="CYCLE"
    )
    assert voi_sth_mvrv["collinearity_penalty"] > 0.0
    assert voi_sth_mvrv["is_redundant"] is True
    # Diminishing incremental value
    assert voi_sth_mvrv["voi_bps"] < voi_mvrv_alone["voi_bps"]


def test_evidence_control_modes():
    """
    Verify the 3 evidence control modes:
      1. AI_RECOMMEND: Autonomous sparse high-VOI set.
      2. AI_PLUS_USER: Merges AI set with user additions and audits marginal VOI.
      3. USER_ONLY: Respects manual user set.
    """
    router = AdaptiveEvidenceRouter()

    # 1. AI_RECOMMEND
    r1 = router.route_evidence(horizon="15m", evidence_mode="AI_RECOMMEND")
    assert len(r1["active_indicators"]) >= 3
    assert r1["total_voi_bps"] > 0.0

    # 2. AI_PLUS_USER (user adds MVRV to 15m)
    r2 = router.route_evidence(
        horizon="15m",
        evidence_mode="AI_PLUS_USER",
        user_selected_indicators=["mvrv"]
    )
    assert "mvrv" in r2["active_indicators"]
    # AI alert warning user that MVRV is low-VOI for 15m
    assert any("MVRV" in a and "low" in a.lower() for a in r2["user_audit_alerts"])

    # 3. USER_ONLY
    r3 = router.route_evidence(
        horizon="15m",
        evidence_mode="USER_ONLY",
        user_selected_indicators=["funding", "open_interest"]
    )
    assert r3["active_indicators"] == ["funding", "open_interest"]


def test_mixture_of_experts_strategy_routing():
    """
    Verify that MoE routing selects the specialist whose regime operational assumptions match:
      - VOL_EXPANDING -> MEIE-IGNITION gets top weight
      - VOL_COMPRESSION -> MEIE-ABSORPTION gets top weight
    """
    router = AdaptiveEvidenceRouter()
    mock_candidates = [
        {"strategy_id": "MEIE-IGNITION", "selection_score": 80.0},
        {"strategy_id": "MEIE-ABSORPTION", "selection_score": 80.0},
        {"strategy_id": "MEIE-VACUUM", "selection_score": 75.0},
        {"strategy_id": "MEIE-TOXICITY", "selection_score": 60.0},
        {"strategy_id": "MEIE-COMBINED", "selection_score": 78.0}
    ]

    # Expanding regime -> IGNITION wins
    moe_expand = router.route_strategy_experts(mock_candidates, market_regime="VOL_EXPANDING", horizon="15m")
    assert moe_expand["selected_expert"] == "MEIE-IGNITION"

    # Compression regime -> ABSORPTION wins
    moe_compress = router.route_strategy_experts(mock_candidates, market_regime="VOL_COMPRESSION", horizon="15m")
    assert moe_compress["selected_expert"] == "MEIE-ABSORPTION"


def test_strategy_selection_engine_integration():
    """
    Verify that StrategySelectionEngine returns full AEER evidence routing and expert routing.
    """
    from engine.strategy_selection import strategy_selection_engine

    res = strategy_selection_engine.evaluate_dual_hypothesis(
        enabled_indicators=["ofi", "hawkes", "funding"],
        live_price=64000.0,
        regime="VOL_EXPANDING",
        horizon="15m",
        evidence_mode="AI_RECOMMEND"
    )

    assert "evidence_routing" in res
    assert "expert_routing" in res
    assert res["evidence_routing"]["horizon"] == "15m"
    assert "total_voi_bps" in res["evidence_routing"]
    assert res["expert_routing"]["selected_expert"] in ["MEIE-IGNITION", "MEIE-COMBINED"]

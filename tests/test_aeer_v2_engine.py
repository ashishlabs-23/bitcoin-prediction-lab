"""
tests/test_aeer_v2_engine.py
=============================
Tests for AEER 2: Adaptive Evidence, Hypothesis & Expert Router:
  1. Sparse Evidence Portfolio (Domain Partitioning & Representation Caps).
  2. Signal Stability & Decay Penalty.
  3. Evidence Balance (Explicit Supporting vs Contradictory Evidence & Conflict Detection).
  4. Dual Counterfactual Worlds (H_long vs H_short: MFE, MAE, Gross/Net EV).
  5. Mechanism Matching Matrix M_{i,j}(t) = Strategy_i x Evidence_j x Regime_t.
  6. 3-Way Intent Resolution Options.
"""

import pytest
from engine.evidence_router import (
    AdaptiveEvidenceRouterV2,
    adaptive_evidence_router,
    compute_indicator_config_hash,
    SUPPORTED_HORIZONS,
    EVIDENCE_DOMAINS,
    BASELINE_SIGNAL_STABILITY,
    STRATEGY_MECHANISM_SPECS
)
from engine.strategy_selection import strategy_selection_engine


def test_aeer_v2_sparse_evidence_portfolio():
    """
    Verify that AEER 2 selects a sparse portfolio of diverse domains,
    preventing 4-5 redundant order flow features from dominating.
    """
    router = AdaptiveEvidenceRouterV2()
    portfolio = router.build_sparse_evidence_portfolio(horizon="15m", market_regime="VOL_EXPANDING")

    sparse_inds = portfolio["sparse_indicators"]
    domain_meta = portfolio["domain_portfolio"]

    # Must contain representatives across diverse domains
    assert len(sparse_inds) >= 3
    assert len(sparse_inds) <= 8  # Enforces sparse budget
    assert portfolio["domain_count"] >= 2

    # Flow domain should have at most 2 representatives
    flow_reps = domain_meta.get("ORDER_FLOW", {}).get("active_representatives", [])
    assert len(flow_reps) <= 2


def test_signal_stability_and_decay_penalty():
    """
    Verify that signals with lower stability scores receive decay penalties,
    suppressing uncalibrated indicators during routing.
    """
    router = AdaptiveEvidenceRouterV2()

    # Hawkes has high stability (0.85)
    r_hawkes = router.compute_routing_relevance("hawkes", [], "15m")
    assert r_hawkes["stability_score"] >= 0.80
    assert r_hawkes["stability_status"] in ["HIGH_STABILITY", "VERY_HIGH_STABILITY"]

    # Artificially inject an unstable signal
    router.stability_registry["test_unstable"] = {
        "score": 0.20,
        "status": "DECAYING",
        "note": "Out-of-sample correlation broke down"
    }
    router.affinity["15m"]["test_unstable"] = 0.90

    r_unstable = router.compute_routing_relevance("test_unstable", [], "15m")
    assert r_unstable["routing_relevance_bps"] < 1.5
    assert r_unstable["stability_score"] == 0.20


def test_evidence_balance_support_vs_contradiction():
    """
    Verify that Evidence Balance explicitly tracks support and contradiction,
    and detects conflicted signals resulting in an UNCERTAIN state.
    """
    router = AdaptiveEvidenceRouterV2()

    # Bullish scenario: OFI high, Hawkes high, funding negative
    snap_bullish = {"ofi": 0.70, "hawkes": 2.5, "funding": -0.0002, "vpin": 0.25}
    bal_bull = router.evaluate_evidence_balance(["ofi", "hawkes", "funding"], snap_bullish)

    assert len(bal_bull["long_balance"]["support"]) >= 2
    assert len(bal_bull["short_balance"]["contradiction"]) >= 2
    assert bal_bull["status"] == "RESOLVED"
    assert bal_bull["is_uncertain"] is False

    # Conflicted scenario: high VPIN spike + no directional consensus
    snap_conflicted = {"ofi": 0.05, "hawkes": 0.8, "funding": 0.0, "vpin": 0.75}
    bal_conflicted = router.evaluate_evidence_balance(["ofi", "hawkes", "vpin"], snap_conflicted)
    assert bal_conflicted["is_uncertain"] is True


def test_dual_counterfactual_path_evaluation():
    """
    Verify parallel evaluation of H_long vs H_short counterfactual worlds.
    """
    router = AdaptiveEvidenceRouterV2()
    snap_bullish = {"ofi": 0.70, "hawkes": 2.5, "funding": -0.0002, "vpin": 0.25}
    bal = router.evaluate_evidence_balance(["ofi", "hawkes", "funding"], snap_bullish)

    cf = router.evaluate_dual_counterfactual_paths("MEIE-IGNITION", 64500.0, bal, ["ofi", "hawkes", "funding"])

    assert "long_counterfactual" in cf
    assert "short_counterfactual" in cf
    assert cf["long_counterfactual"]["net_ev_bps"] > cf["short_counterfactual"]["net_ev_bps"]
    assert cf["delta_ev_long_minus_short"] > 0


def test_mechanism_matching_matrix():
    """
    Verify that Strategy x Evidence x Regime concordance correctly matches mechanisms:
      - IGNITION matches VOL_EXPANDING + ORDER_FLOW
      - ABSORPTION matches VOL_COMPRESSION + LIQUIDITY
    """
    router = AdaptiveEvidenceRouterV2()

    # Expanding regime with OFI and RV_5m
    m_ignition = router.compute_mechanism_matching("MEIE-IGNITION", "VOL_EXPANDING", ["ofi", "rv_5m"])
    assert m_ignition["regime_matched"] is True
    assert m_ignition["concordance_score"] >= 0.80

    # Compression regime matches ABSORPTION
    m_absorption = router.compute_mechanism_matching("MEIE-ABSORPTION", "VOL_COMPRESSION", ["ofi", "vpin"])
    assert m_absorption["regime_matched"] is True
    assert m_absorption["concordance_score"] >= 0.80


def test_aeer_v2_3_way_resolution_options():
    """
    Verify that when user direction preference is rejected,
    structured 3-Way Interactive Resolution Options are provided in the audit response.
    """
    res = strategy_selection_engine.evaluate_dual_hypothesis(
        enabled_indicators=["ofi", "hawkes", "funding"],
        live_price=64200.0,
        regime="VOL_EXPANDING",
        user_direction_preference="SHORT",
        horizon="15m",
        evidence_mode="AI_RECOMMEND"
    )

    audit = res["user_preference_audit"]
    assert audit["status"] == "REJECTED_BY_AI"
    assert audit["resolution_options"] is not None
    assert audit["resolution_options"]["can_follow_ai"] is True
    assert audit["resolution_options"]["can_abstain"] is True
    assert audit["resolution_options"]["can_force_user"] is True
    assert "UNCONFIRMED_USER_OVERRIDE" in audit["resolution_options"]["warning"]

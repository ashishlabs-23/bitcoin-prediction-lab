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


def test_prospective_features_provenance_and_active_consumption():
    """
    Verifies that changing each of the three prospective features:
      1. sweep_candidate
      2. derivatives_quadrant
      3. session_state
    actively changes the AEER payload and provenance hash while keeping other inputs constant,
    without automatically declaring a direction or creating new mechanisms.
    """
    router = AdaptiveEvidenceRouterV2()

    base_snapshot = {
        "spot_price": 64000.0,
        "ofi": 0.2,
        "hawkes": 1.2,
        "vpin": 0.25,
        "funding": 0.0001,
        "open_interest": 1.0,
        "rv_5m": 0.002,
        "sweep_candidate": False,
        "derivatives_quadrant": "STABLE",
        "session_state": "ASIA_RANGE"
    }

    base_dq = router.decompose_decision_questions(
        intent="AUTO",
        horizon="15m",
        market_snapshot=base_snapshot,
        active_sparse_indicators=["ofi", "sweep_candidate", "derivatives_quadrant", "session_state"]
    )
    base_hash = base_dq["provenance"]["provenance_hash"]
    assert base_dq["provenance"]["is_directional_trade_signal"] is False

    # 1. Test sweep_candidate perturbation
    sweep_snapshot = dict(base_snapshot, sweep_candidate=True)
    sweep_dq = router.decompose_decision_questions(
        intent="AUTO",
        horizon="15m",
        market_snapshot=sweep_snapshot,
        active_sparse_indicators=["ofi", "sweep_candidate", "derivatives_quadrant", "session_state"]
    )
    assert sweep_dq["provenance"]["provenance_hash"] != base_hash
    assert sweep_dq["provenance"]["is_directional_trade_signal"] is False

    rel_base_sweep = router.compute_routing_relevance("sweep_candidate", [], "15m", market_snapshot=base_snapshot)
    rel_active_sweep = router.compute_routing_relevance("sweep_candidate", [], "15m", market_snapshot=sweep_snapshot)
    assert rel_active_sweep["routing_relevance_bps"] > rel_base_sweep["routing_relevance_bps"]

    # 2. Test derivatives_quadrant perturbation
    dq_snapshot = dict(base_snapshot, derivatives_quadrant="PRICE_UP_OI_UP")
    dq_result = router.decompose_decision_questions(
        intent="AUTO",
        horizon="15m",
        market_snapshot=dq_snapshot,
        active_sparse_indicators=["ofi", "sweep_candidate", "derivatives_quadrant", "session_state"]
    )
    assert dq_result["provenance"]["provenance_hash"] != base_hash
    assert dq_result["provenance"]["is_directional_trade_signal"] is False

    rel_base_dq = router.compute_routing_relevance("derivatives_quadrant", [], "15m", market_snapshot=base_snapshot)
    rel_active_dq = router.compute_routing_relevance("derivatives_quadrant", [], "15m", market_snapshot=dq_snapshot)
    assert rel_active_dq["routing_relevance_bps"] > rel_base_dq["routing_relevance_bps"]

    # 3. Test session_state perturbation
    session_snapshot = dict(base_snapshot, session_state="NY_LONDON_OVERLAP")
    session_result = router.decompose_decision_questions(
        intent="AUTO",
        horizon="15m",
        market_snapshot=session_snapshot,
        active_sparse_indicators=["ofi", "sweep_candidate", "derivatives_quadrant", "session_state"]
    )
    assert session_result["provenance"]["provenance_hash"] != base_hash
    assert session_result["provenance"]["is_directional_trade_signal"] is False

    rel_base_sess = router.compute_routing_relevance("session_state", [], "15m", market_snapshot=base_snapshot)
    rel_active_sess = router.compute_routing_relevance("session_state", [], "15m", market_snapshot=session_snapshot)
    assert rel_active_sess["routing_relevance_bps"] > rel_base_sess["routing_relevance_bps"]

    # Verify prospective manifest contents
    manifest = session_result["provenance"]["prospective_feature_manifest"]
    assert len(manifest) == 3
    features_present = {m["feature"]: m for m in manifest}
    assert "session_state" in features_present
    assert features_present["session_state"]["value"] == "NY_LONDON_OVERLAP"
    assert features_present["session_state"]["validation_status"] == "PROSPECTIVE"


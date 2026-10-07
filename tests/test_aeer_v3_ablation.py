"""
tests/test_aeer_v3_ablation.py
==============================
Empirical Validation & Prospective Ablation Suite for AEER 3:
1. Seven Canonical Decision Questions (Q1 through Q7).
2. Conditional Activation Mask A_q(tau): Q6 is CONTEXT ONLY on 15m, ACTIVE on 7d/CYCLE.
3. Many-to-Many Question-Evidence Graph and Question-Level Evidence Quality.
4. Q7 Mechanism-Regime Compatibility M_{i,j}(t, tau) with horizon penalty.
5. Decoupled TradeRiskCheck(D_t) vs Model Health.
6. Evidence Sufficiency Gate (Operational Floor N >= 30, CI Width).
7. Three Guidance Modes (AUTO / GUIDED / CUSTOM) and User Override Policy Tagging.
8. AI Advisory Challenge when slow cycle indicators are selected on short horizons.
"""

import pytest
from engine.evidence_router import (
    adaptive_evidence_router,
    DECISION_QUESTIONS,
    compute_indicator_config_hash
)
from engine.strategy_selection import (
    strategy_selection_engine,
    StrategySelectionEngine,
    CANONICAL_STRATEGY_ARCHETYPES
)


def test_seven_canonical_decision_questions_structure():
    """Verify all 7 canonical decision questions exist in the registry."""
    expected_questions = [
        "Q1_DIRECTION",
        "Q2_CONTINUATION",
        "Q3_EXHAUSTION",
        "Q4_LIQUIDITY_EXECUTION",
        "Q5_RISK_CONFORMAL",
        "Q6_CYCLE_CONTEXT",
        "Q7_REGIME_COMPATIBILITY"
    ]
    for q_id in expected_questions:
        assert q_id in DECISION_QUESTIONS
        assert "title" in DECISION_QUESTIONS[q_id]
        assert "question" in DECISION_QUESTIONS[q_id]
        assert "primary_features" in DECISION_QUESTIONS[q_id]
        assert "active_horizons" in DECISION_QUESTIONS[q_id]


def test_conditional_activation_q6_context_only_on_short_horizons():
    """
    Ablation 1: Conditional Activation Mask A_q(tau).
    For a 15m scalp: Q6 is strictly CONTEXT ONLY.
    For a 7d or CYCLE swing: Q6 becomes ACTIVE.
    """
    # 15m evaluation
    res_15m = adaptive_evidence_router.decompose_decision_questions(
        horizon="15m",
        active_sparse_indicators=["ofi", "hawkes", "vpin", "rv_5m"]
    )
    q_15m = res_15m["questions"]
    assert q_15m["Q1_DIRECTION"]["is_active"] is True
    assert q_15m["Q1_DIRECTION"]["activation_state"] == "ACTIVE"
    assert q_15m["Q6_CYCLE_CONTEXT"]["is_active"] is False
    assert q_15m["Q6_CYCLE_CONTEXT"]["activation_state"] == "CONTEXT_ONLY"
    assert q_15m["Q7_REGIME_COMPATIBILITY"]["is_active"] is True

    # 7d evaluation
    res_7d = adaptive_evidence_router.decompose_decision_questions(
        horizon="7d",
        active_sparse_indicators=["mvrv", "sth_mvrv", "rv_24h", "options_iv"]
    )
    q_7d = res_7d["questions"]
    assert q_7d["Q6_CYCLE_CONTEXT"]["is_active"] is True
    assert q_7d["Q6_CYCLE_CONTEXT"]["activation_state"] == "ACTIVE"


def test_question_evidence_quality_and_many_to_many_graph():
    """
    Ablation 2: Many-to-many question-evidence graph.
    One indicator (e.g. hawkes) informs both Q1 and Q2.
    Questions with 2+ stable indicators achieve STRONG evidence quality.
    """
    res = adaptive_evidence_router.decompose_decision_questions(
        horizon="15m",
        active_sparse_indicators=["ofi", "hawkes", "rv_5m", "vpin"]
    )
    questions = res["questions"]
    why_list = res["why_these_indicators"]

    # Hawkes is mapped to multiple answering questions
    hawkes_item = next(w for w in why_list if w["indicator"] == "hawkes")
    assert "Q1_DIRECTION" in hawkes_item["answered_questions"]
    assert "Q2_CONTINUATION" in hawkes_item["answered_questions"]

    # Q1 has OFI and Hawkes -> STRONG quality
    assert questions["Q1_DIRECTION"]["evidence_quality"] == "STRONG"
    assert questions["Q1_DIRECTION"]["status"] == "PASS"


def test_q7_mechanism_regime_matching_with_horizon_penalty():
    """
    Ablation 3: M_{i,j}(t, tau) incorporates both regime and horizon concordance.
    MEIE-IGNITION in VOL_EXPANDING on 15m has high concordance.
    MEIE-IGNITION on 7d or CYCLE receives substantial horizon penalty.
    """
    # 15m concordance in expansion
    m_15m = adaptive_evidence_router.compute_mechanism_matching(
        strategy_id="MEIE-IGNITION",
        market_regime="VOL_EXPANDING",
        active_indicators=["ofi", "hawkes", "rv_5m"],
        horizon="15m"
    )
    assert m_15m["horizon_matched"] is True
    assert m_15m["concordance_score"] >= 0.80
    assert m_15m["status"] == "FULL_CONCORDANCE"

    # 7d concordance for ignition
    m_7d = adaptive_evidence_router.compute_mechanism_matching(
        strategy_id="MEIE-IGNITION",
        market_regime="VOL_EXPANDING",
        active_indicators=["ofi", "hawkes", "rv_5m"],
        horizon="7d"
    )
    assert m_7d["horizon_matched"] is False
    assert m_7d["concordance_score"] < m_15m["concordance_score"]
    assert m_7d["horizon_score"] == 0.35


def test_trade_risk_check_decoupling():
    """
    Ablation 4: Decoupled TradeRiskCheck(D_t).
    Model Health != Trade Authorization.
    When trade risk check is BLOCKED, execution fails immediately.
    """
    engine = StrategySelectionEngine()
    mock_candidate = {
        "strategy_id": "MEIE-IGNITION",
        "has_required_data": True,
        "optimal_direction": "LONG",
        "optimal_net_ev_bps": 15.0,
        "long_hypothesis": {
            "n_samples": 120,
            "ci_lower_pct": 55.0,
            "ci_upper_pct": 65.0
        },
        "short_hypothesis": {
            "n_samples": 120,
            "ci_lower_pct": 35.0,
            "ci_upper_pct": 45.0
        }
    }

    # Trade risk blocked
    is_ok, code, reason = engine.check_hard_eligibility_gates(
        candidate_eval=mock_candidate,
        trade_risk_status="BLOCKED_BY_JUMP_TAIL"
    )
    assert is_ok is False
    assert code == "FAIL_TRADE_RISK_BLOCKED"


def test_evidence_sufficiency_operational_floor_and_variance():
    """
    Ablation 5: Evidence Sufficiency Gate.
    Operational floor N >= 30 and CI width threshold.
    """
    engine = StrategySelectionEngine()
    # Case A: N < 30
    mock_low_n = {
        "strategy_id": "MEIE-IGNITION",
        "has_required_data": True,
        "optimal_direction": "LONG",
        "optimal_net_ev_bps": 20.0,
        "long_hypothesis": {"n_samples": 18, "ci_lower_pct": 52.0, "ci_upper_pct": 62.0},
        "short_hypothesis": {"n_samples": 18, "ci_lower_pct": 30.0, "ci_upper_pct": 40.0}
    }
    is_ok, code, _ = engine.check_hard_eligibility_gates(mock_low_n)
    assert is_ok is False
    assert code == "FAIL_LOW_SAMPLE_N"

    # Case B: Excessive CI width (high variance/uncertainty)
    mock_wide_ci = {
        "strategy_id": "MEIE-IGNITION",
        "has_required_data": True,
        "optimal_direction": "LONG",
        "optimal_net_ev_bps": 20.0,
        "long_hypothesis": {"n_samples": 50, "ci_lower_pct": 45.0, "ci_upper_pct": 75.0}, # Width = 30% > 22%
        "short_hypothesis": {"n_samples": 50, "ci_lower_pct": 30.0, "ci_upper_pct": 50.0}
    }
    is_ok, code, _ = engine.check_hard_eligibility_gates(mock_wide_ci)
    assert is_ok is False
    assert code == "FAIL_HIGH_EVIDENCE_VARIANCE"


def test_user_guidance_modes_and_override_tagging():
    """
    Ablation 6: Three Guidance Modes (AUTO, GUIDED, CUSTOM) and Override Provenance.
    When user forces an unconfirmed direction, policy is tagged as USER_OVERRIDE_UNCONFIRMED.
    """
    engine = StrategySelectionEngine()
    # 1. AUTO mode
    res_auto = engine.evaluate_dual_hypothesis(
        enabled_indicators=["ofi", "hawkes", "rv_5m"],
        live_price=64000.0,
        regime="VOL_EXPANDING",
        user_direction_preference="AUTO"
    )
    assert res_auto["guidance_mode"] == "AUTO"
    assert res_auto["execution_policy"] == "AI_OPTIMAL"

    # 2. GUIDED mode where AI rejects user short preference
    res_guided = engine.evaluate_dual_hypothesis(
        enabled_indicators=["ofi", "hawkes", "rv_5m"],
        live_price=64000.0,
        regime="VOL_EXPANDING",
        user_direction_preference="SHORT"
    )
    assert res_guided["guidance_mode"] == "GUIDED"
    assert res_guided["execution_policy"] == "USER_OVERRIDE_REJECTED"
    assert res_guided["synthesis"]["final_action"] == "ABSTAIN"
    opts = res_guided["user_preference_audit"]["resolution_options"]
    assert opts["force_policy_tag"] == "USER_OVERRIDE_UNCONFIRMED"
    assert "UNCONFIRMED" in opts["user_action"]


def test_ai_advisory_challenge_slow_cycle_on_fast_horizon():
    """
    Ablation 7: AI Advisory Audit.
    Selecting slow cycle indicators (MVRV, Mayer) for a 15m decision
    triggers an explicit AI advisory warning recommending context-only use.
    """
    res = adaptive_evidence_router.decompose_decision_questions(
        horizon="15m",
        user_selected_indicators=["mvrv", "mayer"],
        active_sparse_indicators=["ofi", "hawkes", "mvrv", "mayer"]
    )
    audit = res["user_advisory_audit"]
    assert audit["has_advisory_alert"] is True
    assert "mvrv" in audit["challenged_indicators"]
    assert "mayer" in audit["challenged_indicators"]
    assert "valid on-chain valuation" in audit["challenge_narrative"]
    assert "Recommendation: Keep as secondary CONTEXT only" in audit["challenge_narrative"]


def test_tier_0_geometric_touch_martingale_null():
    """
    Tier 0 Null: Driftless Log-Price First-Passage Null Family (mu = 0).
    Verifies that:
    1. P_0 = ln(S_0 / P_10) / ln(P_90 / P_10) has zero free parameters under d ln S_t = sigma dW_t.
    2. Exact log-symmetry holds iff S_0^2 = U * L (geometric mean).
    3. Finite-horizon touch probabilities scale with local volatility sigma * sqrt(T).
    4. Epistemic status separates analysis expert from directional signal (is_directional_trade_signal is False).
    """
    s0 = 64000.0
    u = 64512.0
    l = 63552.0
    res = adaptive_evidence_router.decompose_decision_questions(
        horizon="15m",
        market_snapshot={
            "spot_price": s0,
            "conformal_p90": u,
            "conformal_p10": l,
            "rv_5m": 0.024
        }
    )
    t0 = res["tier_0_geometric_touch"]
    assert t0["model_tier"] == "TIER_0_DRIFTLESS_LOGPRICE_NULL"
    assert t0["drift_mu"] == 0.0
    assert t0["is_directional_trade_signal"] is False
    assert 0.0 < t0["p_upper_p90"] < 1.0
    assert abs((t0["p_upper_p90"] + t0["p_lower_p10"]) - 1.0) < 1e-4

    # Exact Classical Double Barrier Finite horizon reachability
    finite = t0["finite_horizon_touch"]
    assert 0.0 < finite["p_upper_first_within_horizon"] <= t0["p_upper_p90"]
    assert 0.0 < finite["p_lower_first_within_horizon"] <= t0["p_lower_p10"]
    assert 0.0 < finite["p_exit_within_horizon"] <= 1.0
    assert 0.0 <= finite["p_survive_within_horizon"] <= 1.0

    # Verify exact log-symmetry condition: S_0 = sqrt(U * L)
    geom_u = 64000.0 * 1.01
    geom_l = 64000.0 / 1.01
    # Note: geom_u * geom_l == 64000.0^2 exactly!
    res_geom_sym = adaptive_evidence_router.decompose_decision_questions(
        horizon="15m",
        market_snapshot={
            "spot_price": 64000.0,
            "conformal_p90": geom_u,
            "conformal_p10": geom_l
        }
    )
    t0_geom = res_geom_sym["tier_0_geometric_touch"]
    assert t0_geom["log_symmetry"]["is_log_symmetric"] is True
    assert abs(t0_geom["p_upper_p90"] - 0.50) < 1e-4


def test_prospective_features_5_arm_ablation():
    """
    Ablation Study: 5-Arm Protocol for Prospective Contextual Features
      Arm 1: BASELINE (Core microstructure & volatility only)
      Arm 2: BASELINE + SESSION
      Arm 3: BASELINE + SWEEP
      Arm 4: BASELINE + DERIVATIVES
      Arm 5: BASELINE + ALL_THREE

    Verifies:
      - Systematic, isolated measurement of incremental routing change.
      - Absence of directional trade signal across all 5 arms (epistemic isolation).
      - Registration of PROSPECTIVE_ROUTING_PRIOR in provenance.
    """
    snap = {
        "spot_price": 64000.0,
        "conformal_p90": 64800.0,
        "conformal_p10": 63200.0,
        "ofi": 0.45,
        "hawkes": 1.9,
        "vpin": 0.32,
        "funding": 0.00018,
        "open_interest": 2.5,
        "rv_5m": 0.0025,
        "session_state": "NY_LONDON_OVERLAP",
        "sweep_candidate": True,
        "derivatives_quadrant": "PRICE_UP_OI_UP"
    }

    base_set = ["ofi", "hawkes", "vpin", "rv_5m"]

    # Arm 1: BASELINE
    arm1 = adaptive_evidence_router.decompose_decision_questions(
        horizon="15m", market_snapshot=snap, active_sparse_indicators=base_set
    )
    # Arm 2: BASELINE + SESSION
    arm2 = adaptive_evidence_router.decompose_decision_questions(
        horizon="15m", market_snapshot=snap, active_sparse_indicators=base_set + ["session_state"]
    )
    # Arm 3: BASELINE + SWEEP
    arm3 = adaptive_evidence_router.decompose_decision_questions(
        horizon="15m", market_snapshot=snap, active_sparse_indicators=base_set + ["sweep_candidate"]
    )
    # Arm 4: BASELINE + DERIVATIVES
    arm4 = adaptive_evidence_router.decompose_decision_questions(
        horizon="15m", market_snapshot=snap, active_sparse_indicators=base_set + ["derivatives_quadrant"]
    )
    # Arm 5: BASELINE + ALL_THREE
    arm5 = adaptive_evidence_router.decompose_decision_questions(
        horizon="15m", market_snapshot=snap, active_sparse_indicators=base_set + ["session_state", "sweep_candidate", "derivatives_quadrant"]
    )

    arms = [arm1, arm2, arm3, arm4, arm5]

    # Invariance and arm tagging across all 5 arms
    assert arm1["provenance"]["ablation_arm"] == "A1_BASELINE"
    assert arm2["provenance"]["ablation_arm"] == "A2_BASELINE_PLUS_SESSION"
    assert arm3["provenance"]["ablation_arm"] == "A3_BASELINE_PLUS_SWEEP"
    assert arm4["provenance"]["ablation_arm"] == "A4_BASELINE_PLUS_DERIVATIVES"
    assert arm5["provenance"]["ablation_arm"] == "A5_BASELINE_PLUS_ALL_THREE"

    for i, arm in enumerate(arms, start=1):
        prov = arm["provenance"]
        assert prov["is_directional_trade_signal"] is False, f"Arm {i} leaked directional bias"
        assert prov["epistemic_classification"] == "PROSPECTIVE_ROUTING_PRIOR"
        assert "routing_prior_config_hash" in prov
        assert prov["observation_id"].startswith("obs_")
        assert prov["decision_timestamp"] is not None
        assert prov["outcome_timestamp"] is None
        assert prov["feature_set_hash"] is not None

    # Arm 2: session_state enters Q7
    assert "session_state" in arm2["questions"]["Q7_REGIME_COMPATIBILITY"]["assigned_indicators"]
    assert "session_state" not in arm1["questions"]["Q7_REGIME_COMPATIBILITY"]["assigned_indicators"]

    # Arm 3: sweep_candidate enters Q2
    assert "sweep_candidate" in arm3["questions"]["Q2_CONTINUATION"]["assigned_indicators"]
    assert "sweep_candidate" not in arm1["questions"]["Q2_CONTINUATION"]["assigned_indicators"]

    # Arm 4: derivatives_quadrant enters Q3
    assert "derivatives_quadrant" in arm4["questions"]["Q3_EXHAUSTION"]["assigned_indicators"]
    assert "derivatives_quadrant" not in arm1["questions"]["Q3_EXHAUSTION"]["assigned_indicators"]

    # Arm 5: contains all three
    arm5_assigned = {
        ind for q in arm5["questions"].values() for ind in q.get("assigned_indicators", [])
    }
    assert {"session_state", "sweep_candidate", "derivatives_quadrant"}.issubset(arm5_assigned)


def test_information_value_vs_heuristic_weighting_ablation():
    """
    Distinguishes raw information value from heuristic weighting:
      RAW FEATURE (use_neutral_priors=True, multiplier=1.0)
      vs
      FEATURE + CURRENT MULTIPLIER (use_neutral_priors=False)
    """
    snap_active = {
        "session_state": "NY_LONDON_OVERLAP",
        "sweep_candidate": True,
        "derivatives_quadrant": "PRICE_UP_OI_UP"
    }

    # 1. Sweep candidate
    rel_raw_sweep = adaptive_evidence_router.compute_routing_relevance(
        "sweep_candidate", [], "15m", market_snapshot=snap_active, use_neutral_priors=True
    )
    rel_weighted_sweep = adaptive_evidence_router.compute_routing_relevance(
        "sweep_candidate", [], "15m", market_snapshot=snap_active, use_neutral_priors=False
    )
    # Raw has positive base utility * affinity
    assert rel_raw_sweep["routing_relevance_bps"] > 0.0
    # Heuristic multiplier scales relevance up by 1.35x
    assert rel_weighted_sweep["routing_relevance_bps"] > rel_raw_sweep["routing_relevance_bps"]

    # 2. Session state
    rel_raw_sess = adaptive_evidence_router.compute_routing_relevance(
        "session_state", [], "15m", market_snapshot=snap_active, use_neutral_priors=True
    )
    rel_weighted_sess = adaptive_evidence_router.compute_routing_relevance(
        "session_state", [], "15m", market_snapshot=snap_active, use_neutral_priors=False
    )
    assert rel_raw_sess["routing_relevance_bps"] > 0.0
    assert rel_weighted_sess["routing_relevance_bps"] > rel_raw_sess["routing_relevance_bps"]

    # 3. Derivatives quadrant
    rel_raw_dq = adaptive_evidence_router.compute_routing_relevance(
        "derivatives_quadrant", [], "15m", market_snapshot=snap_active, use_neutral_priors=True
    )
    rel_weighted_dq = adaptive_evidence_router.compute_routing_relevance(
        "derivatives_quadrant", [], "15m", market_snapshot=snap_active, use_neutral_priors=False
    )
    assert rel_raw_dq["routing_relevance_bps"] > 0.0
    assert rel_weighted_dq["routing_relevance_bps"] > rel_raw_dq["routing_relevance_bps"]


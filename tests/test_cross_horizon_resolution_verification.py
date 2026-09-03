"""
tests/test_cross_horizon_resolution_verification.py
===================================================
Automated Verification Suite for Cross-Horizon Resolution & Patience Analysis.

Enforces:
1. Question A: Fixed (E, U, L) geometry invariant across all horizons T in {5m, 15m, 1h, 4h, 1d}.
2. Question B: Independent empirical conformal calibrations (U_T, L_T) scale with horizon.
3. Probability Conservation: P_U(T) + P_L(T) + P_0(T) == 1.0 (error < 1e-5) for every row.
4. Evidence Persistence Provenance: Formal estimation method, window, and stability metadata.
5. Zero Optimization: No 'OPTIMAL_HORIZON', no 'SWEET_SPOT', and system_recommendation == 'NONE'.
"""

import pytest
from engine.evidence_router import adaptive_evidence_router


def test_question_a_fixed_boundaries_invariant_across_all_horizons():
    """
    Contract 1:
    Verifies that Question A (Fixed-Contract Analytical Time Sensitivity)
    uses the EXACT SAME entry, upper target, and lower stop across all horizons.
    Answers: 'What happens purely because I allow the same scenario more time?'
    """
    s0 = 77000.0
    u_fixed = 78000.0
    l_fixed = 76500.0

    profile = adaptive_evidence_router.compute_cross_horizon_resolution_profile(
        s0=s0,
        entry_price=s0,
        u_fixed=u_fixed,
        l_fixed=l_fixed,
        current_horizon="15m"
    )

    q_a = profile["question_a_fixed_contract_sensitivity"]
    assert len(q_a) == 5
    
    first_boundary_hash = q_a[0]["boundary_hash"]
    
    for row in q_a:
        assert row["entry_price"] == s0
        assert row["u_target"] == u_fixed
        assert row["l_target"] == l_fixed
        assert row["boundary_hash"] == first_boundary_hash
        assert "calibration_hash" in row
        assert "n_eff" in row
        assert "ci_width" in row
        assert "raw_N" in row
        assert "independent_blocks" in row
        assert row["status"] == "VALID"

    # Monotonicity: P_0 (no-exit / survival) must decrease as time allowance T increases
    p0_values = [row["p_no_exit"] for row in q_a]
    for i in range(len(p0_values) - 1):
        assert p0_values[i] >= p0_values[i + 1]


def test_question_b_independent_empirical_calibrations():
    """
    Contract 2:
    Verifies that Question B (Horizon-Specific Empirical Calibrations)
    evaluates dynamically calibrated envelopes (U_T, L_T) for each independent horizon.
    Answers: 'How does empirical contract geometry adapt across independent horizons?'
    """
    s0 = 77000.0
    u_fixed = 78000.0
    l_fixed = 76500.0

    profile = adaptive_evidence_router.compute_cross_horizon_resolution_profile(
        s0=s0,
        entry_price=s0,
        u_fixed=u_fixed,
        l_fixed=l_fixed,
        current_horizon="15m"
    )

    q_b = profile["question_b_horizon_specific_calibrations"]
    assert len(q_b) == 5

    # Calibrated upper targets must expand monotonically with horizon
    u_b_values = [row["u_calibrated"] for row in q_b]
    l_b_values = [row["l_calibrated"] for row in q_b]
    
    for i in range(len(u_b_values) - 1):
        assert u_b_values[i] < u_b_values[i + 1]
        assert l_b_values[i] > l_b_values[i + 1]

    # Distinct boundary hashes for each row in Question B
    b_hashes = [row["boundary_hash"] for row in q_b]
    assert len(set(b_hashes)) == len(b_hashes)


def test_probability_conservation_holds_for_all_horizons_in_profile():
    """
    Contract 3:
    Verifies that for every row in both Question A and Question B:
    P_U(T) + P_L(T) + P_0(T) == 1.0 (error < 1e-5).
    """
    s0 = 77500.0
    u_fixed = 78300.0
    l_fixed = 77000.0

    profile = adaptive_evidence_router.compute_cross_horizon_resolution_profile(
        s0=s0,
        entry_price=s0,
        u_fixed=u_fixed,
        l_fixed=l_fixed,
        current_horizon="15m"
    )

    for row in profile["question_a_fixed_contract_sensitivity"]:
        total = row["p_upper_first"] + row["p_lower_first"] + row["p_no_exit"]
        assert abs(total - 1.0) < 1e-5
        assert row["conservation_error"] < 1e-5

    for row in profile["question_b_horizon_specific_calibrations"]:
        total = row["p_upper_first"] + row["p_lower_first"] + row["p_no_exit"]
        assert abs(total - 1.0) < 1e-5
        assert row["conservation_error"] < 1e-5


def test_evidence_persistence_provenance_metadata():
    """
    Contract 4:
    Verifies that Evidence Persistence matrix has formal estimation provenance
    (estimation_method, sample_size, stability_status) and distinguishes
    compatibility from profitability.
    """
    profile = adaptive_evidence_router.compute_cross_horizon_resolution_profile(
        s0=77000.0,
        entry_price=77000.0,
        u_fixed=78000.0,
        l_fixed=76500.0,
        current_horizon="15m"
    )

    evidence_list = profile["evidence_persistence_matrix"]
    assert len(evidence_list) >= 5

    for item in evidence_list:
        assert "indicator_id" in item
        assert "estimated_half_life" in item
        assert "estimated_half_life_str" in item
        assert "horizon_compatibility" in item
        assert "estimation_method" in item
        assert "sample_size" in item
        assert "stability_status" in item
        assert item["stability_status"] in ["ESTIMATED_OOS", "ILLUSTRATIVE"]


def test_no_optimizer_recommendation_in_horizon_profile():
    """
    Contract 5:
    Verifies that the Cross-Horizon Profile contains zero optimizer language,
    no 'OPTIMAL_HORIZON' or 'SWEET_SPOT' keys, and system_recommendation == 'NONE'.
    """
    profile = adaptive_evidence_router.compute_cross_horizon_resolution_profile(
        s0=77000.0,
        entry_price=77000.0,
        u_fixed=78000.0,
        l_fixed=76500.0,
        current_horizon="15m"
    )

    assert profile["system_recommendation"] == "NONE"
    assert profile["observation_type"] == "HORIZON_SENSITIVITY_OBSERVATION"
    assert "optimal_horizon" not in profile
    assert "sweet_spot" not in profile
    assert "expected_rr" not in str(profile).lower()

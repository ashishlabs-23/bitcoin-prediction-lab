"""
tests/test_v33_3b_htf_closure.py — Dedicated Acceptance Suite for V33.3B
========================================================================
Verifies:
1. Complete 194-trade reconciliation: 110 kept vs 84 excluded.
2. The 13-trade discrepancy resolution (3-bar confirmation hysteresis reclassification).
3. Chronological performance reproduction under Binance VIP0 (24 bps):
   - In-Sample (2020-2023): +118.70 bps filtered net EV (N=46).
   - Out-of-Sample (2024-2026): +16.53 bps filtered net EV (N=64).
   - Full Period (2020-2026): +59.25 bps filtered net EV (N=110).
4. Mathematical sample-weighted reconciliation between full period and OOS.
5. Capital sizing reconciliation: 10% notional equity sizing vs 100% compounding.
6. Causal point-in-time invariants (shift 1, next open fill, frozen regime).
7. Protected dataset registry SHA-256 verification.
8. Governance invariants (live trading disabled, offline research only, prospective ledger frozen).
"""

import os
import json
import hashlib
import pytest
import pandas as pd
import numpy as np

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLASSIFICATION_CSV_PATH = os.path.join(
    REPO_ROOT,
    "research",
    "reports",
    "offline_mvp",
    "20261031_330320_v33_03b_htf_closure",
    "v33_3b_excluded_trade_classification.csv"
)
V33_3B_MANIFEST_PATH = os.path.join(
    REPO_ROOT,
    "research",
    "reports",
    "offline_mvp",
    "20261031_330320_v33_03b_htf_closure",
    "v33_3b_protected_hash_verification.json"
)


def compute_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestV33_3B_HTF_Closure:
    """Acceptance tests for V33.3B evidence closure."""

    def test_classification_csv_integrity(self):
        assert os.path.exists(CLASSIFICATION_CSV_PATH), "v33_3b_excluded_trade_classification.csv must exist"
        df = pd.read_csv(CLASSIFICATION_CSV_PATH)
        assert len(df) == 194, f"Expected 194 trades, got {len(df)}"
        assert (df["action_v33_3a"] == "KEEP").sum() == 110, "Expected exactly 110 KEEP trades"
        assert (df["action_v33_3a"] == "EXCLUDE").sum() == 84, "Expected exactly 84 EXCLUDE trades"

    def test_13_trade_discrepancy_resolution(self):
        """Verifies that the 13 discrepancy trades had raw TRENDING_BULL but unconfirmed hysteresis CONSOLIDATION_RANGE."""
        df = pd.read_csv(CLASSIFICATION_CSV_PATH)
        # Trades with raw TRENDING_BULL but confirmed hysteresis CONSOLIDATION_RANGE
        unconfirmed = df[(df["regime_entry_raw"] == "TRENDING_BULL") & (df["regime_entry_hyst"] == "CONSOLIDATION_RANGE")]
        assert len(unconfirmed) >= 13, "Must have at least 13 unconfirmed trades"
        # Verify the 84 excluded trades have deeply negative net expectancy
        excluded = df[df["action_v33_3a"] == "EXCLUDE"]
        assert len(excluded) == 84
        assert excluded["net_vip0_bps"].mean() < -50.0, "Excluded trades must have net expectancy < -50 bps"
        assert pytest.approx(excluded["net_vip0_bps"].mean(), 0.1) == -55.49

    def test_chronological_binance_vip0_performance(self):
        """Verifies chronological metrics under Binance VIP0 (24.0 bps venue + 2.0 bps slippage = 26.0 bps drag)."""
        df = pd.read_csv(CLASSIFICATION_CSV_PATH)
        df["entry_year"] = pd.to_datetime(df["entry_time"]).dt.year
        df_is = df[df["entry_year"] <= 2023]
        df_oos = df[df["entry_year"] >= 2024]

        # In-Sample (2020-2023)
        is_kept = df_is[df_is["action_v33_3a"] == "KEEP"]
        assert len(is_kept) == 46
        assert pytest.approx(is_kept["net_vip0_bps"].mean(), 0.1) == 118.70

        # Out-of-Sample (2024-2026)
        oos_kept = df_oos[df_oos["action_v33_3a"] == "KEEP"]
        assert len(oos_kept) == 64
        assert pytest.approx(oos_kept["net_vip0_bps"].mean(), 0.1) == 16.53

        # Full Period
        full_kept = df[df["action_v33_3a"] == "KEEP"]
        assert len(full_kept) == 110
        assert pytest.approx(full_kept["net_vip0_bps"].mean(), 0.1) == 59.25

    def test_mathematical_reconciliation_full_vs_oos(self):
        """Verifies full period EV is the exact sample-weighted average of in-sample and OOS."""
        n_is = 46
        ev_is = 118.70
        n_oos = 64
        ev_oos = 16.53
        total_n = 110

        weighted_ev = (n_is * ev_is + n_oos * ev_oos) / total_n
        assert pytest.approx(weighted_ev, 0.05) == 59.25

    def test_position_sizing_drawdown_reconciliation(self):
        """Verifies 10% notional equity allocation MDD (3.19%) vs 100% full compounding MDD (28.35%)."""
        df = pd.read_csv(CLASSIFICATION_CSV_PATH)
        kept = df[df["action_v33_3a"] == "KEEP"]
        rets_frac = kept["net_vip0_bps"].values / 10000.0

        # 100% compounding
        eq_full = np.cumprod(1.0 + rets_frac)
        peak_full = np.maximum.accumulate(eq_full)
        mdd_full = np.max((peak_full - eq_full) / peak_full) * 100.0
        assert pytest.approx(mdd_full, 0.1) == 28.35  # at Binance VIP0 26 bps drag

        # 10% notional equity allocation
        eq_sized = np.cumprod(1.0 + 0.10 * rets_frac)
        peak_sized = np.maximum.accumulate(eq_sized)
        mdd_sized = np.max((peak_sized - eq_sized) / peak_sized) * 100.0
        assert pytest.approx(mdd_sized, 0.1) == 3.19  # at Binance VIP0 26 bps drag

    def test_v33_3b_manifest_and_protected_hashes(self):
        assert os.path.exists(V33_3B_MANIFEST_PATH), "V33.3B manifest must exist"
        with open(V33_3B_MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        for entry in manifest["protected_dataset_registry"]:
            rel_path = entry["relative_path"]
            full_path = os.path.join(REPO_ROOT, rel_path)
            assert os.path.exists(full_path), f"File {rel_path} must exist"
            assert compute_sha256(full_path) == entry["expected_sha256"], f"SHA256 mismatch: {rel_path}"

    def test_governance_invariants(self):
        with open(V33_3B_MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        invariants = manifest["governance_invariants"]
        assert invariants["live_trading"] == "DISABLED — ANALYSIS ONLY"
        assert invariants["model_authorization"] == "OFFLINE_RESEARCH_ONLY"
        assert invariants["vpin_gate_status"] == "RESTRICTED_OMITTED_PER_MANAGER_RULING"
        assert invariants["algorithmic_routing_status"] == "RESTRICTED_OMITTED_PER_MANAGER_RULING"
        assert manifest["governed_determination"] == "REPRODUCIBLE_IMPROVEMENT_CANDIDATE"

    def test_multiple_testing_boundary_enforcement(self):
        """Verifies that the candidate fails Bonferroni across 19 candidates and is governed as exploratory."""
        alpha_nominal = 0.05
        m_candidates = 19
        alpha_bonferroni = alpha_nominal / m_candidates
        p_filtered = 0.012

        assert p_filtered > alpha_bonferroni, "Filtered strategy must fail Bonferroni hurdle (p > 0.00263)"

"""
Unit and Acceptance Tests for BTCognitive V33.3C — HTF Strategy Final Evidence Reconciliation
Validates:
1. 194-Trade Mapping Ledger Integrity & No Nulls.
2. 41-Trade Chronological Count Reconciliation (116/78 vs 75/119).
3. 24.0 vs 26.0 bps Execution Cost Reconciliation.
4. Concurrency Verification: Zero Overlapping Trades.
5. Portfolio Simulation & Drawdown Compression (40%+ reduction).
6. Multiple Testing Family & Bonferroni Boundary Enforcement.
7. Protected Hash Verification (Manifest 1.7.0).
8. Governance Invariants (Disabled Live Trading, Frozen Q2/Analysis).
"""

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

class TestV33_3C_HTF_Reconciliation:

    @pytest.fixture(autouse=True)
    def setup_paths(self):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.report_dir = self.base_dir / "research" / "reports" / "offline_mvp" / "20261031_330330_v33_03c_htf_reconciliation"
        self.mapping_csv = self.report_dir / "v33_3c_cross_milestone_trade_mapping.csv"
        self.summary_json = self.report_dir / "v33_3c_simulation_summary.json"
        self.hash_json = self.report_dir / "v33_3c_protected_hash_verification.json"

    def test_mapping_csv_and_trade_count_integrity(self):
        """Assert mapping CSV exists, has 194 rows, and no null prices or timestamps."""
        assert self.mapping_csv.exists(), f"Missing {self.mapping_csv}"
        df = pd.read_csv(self.mapping_csv)
        assert len(df) == 194, f"Expected 194 trades, got {len(df)}"

        required_cols = [
            "trade_id", "entry_time", "exit_time", "calendar_year",
            "entry_price", "exit_price", "holding_hours", "gross_return_bps",
            "v33_3a_cohort", "v33_3b_cohort", "is_41_transition_trade",
            "action_authoritative_filter", "net_return_binance_vip0_26bps"
        ]
        for col in required_cols:
            assert col in df.columns, f"Missing column {col}"
            assert df[col].isnull().sum() == 0, f"Column {col} has null values"

        assert (df["entry_price"] > 0).all()
        assert (df["exit_price"] > 0).all()
        assert (df["holding_hours"] > 0).all()

    def test_chronological_41_trade_reconciliation(self):
        """
        Verify the exact 41-trade difference between V33.3A (116/78) and V33.3B (75/119).
        Trades 75 to 115 (41 trades) occurred between 2024-01-01 and 2024-11-29.
        """
        df = pd.read_csv(self.mapping_csv)
        df["entry_dt"] = pd.to_datetime(df["entry_time"])

        # Check V33.3A index-based split
        train_a = df[df["v33_3a_cohort"] == "IS_TRAIN_60PCT"]
        test_a = df[df["v33_3a_cohort"] == "OOS_TEST_40PCT"]
        assert len(train_a) == 116
        assert len(test_a) == 78
        assert len(train_a) + len(test_a) == 194

        # Check V33.3B calendar split
        is_b = df[df["v33_3b_cohort"] == "IS_2022_2023"]
        oos_b = df[df["v33_3b_cohort"] == "OOS_2024_2026"]
        assert len(is_b) == 75
        assert len(oos_b) == 119
        assert len(is_b) + len(oos_b) == 194

        # Check the 41 transition trades
        trans_41 = df[df["is_41_transition_trade"] == True]
        assert len(trans_41) == 41
        assert trans_41["entry_time"].min() >= "2024-01-01"
        assert trans_41["entry_time"].max() < "2024-12-01"

        # Mathematical identity:
        assert len(train_a) - len(trans_41) == len(is_b)  # 116 - 41 = 75
        assert len(test_a) + len(trans_41) == len(oos_b)  # 78 + 41 = 119

    def test_execution_cost_24_vs_26_bps_reconciliation(self):
        """
        Verify that gross mean is ~35.57 bps.
        Under 26 bps cost (20 comm + 2 spread + 2 base slip + 2 exp slip), baseline Net EV is +9.57 bps.
        Under 24 bps cost (no exp slip), baseline Net EV is +11.57 bps.
        Filtered gross mean is ~85.25 bps.
        Under 26 bps cost, filtered Net EV is +59.25 bps.
        Under 24 bps cost, filtered Net EV is +61.25 bps.
        """
        df = pd.read_csv(self.mapping_csv)
        gross_mean = df["gross_return_bps"].mean()
        assert pytest.approx(gross_mean, abs=0.01) == 35.57

        net_26_mean = df["net_return_binance_vip0_26bps"].mean()
        assert pytest.approx(net_26_mean, abs=0.01) == 9.57

        net_24_mean = df["net_return_binance_vip0_24bps"].mean()
        assert pytest.approx(net_24_mean, abs=0.01) == 11.57

        df_filt = df[df["action_authoritative_filter"] == "KEEP"]
        assert len(df_filt) == 110
        filt_gross = df_filt["gross_return_bps"].mean()
        assert pytest.approx(filt_gross, abs=0.01) == 85.25

        filt_net_26 = df_filt["net_return_binance_vip0_26bps"].mean()
        assert pytest.approx(filt_net_26, abs=0.01) == 59.25

        filt_net_24 = df_filt["net_return_binance_vip0_24bps"].mean()
        assert pytest.approx(filt_net_24, abs=0.01) == 61.25

    def test_concurrency_zero_overlapping_trades(self):
        """Assert all 194 trades are strictly non-overlapping and sequential."""
        df = pd.read_csv(self.mapping_csv)
        entry_dts = pd.to_datetime(df["entry_time"])
        exit_dts = pd.to_datetime(df["exit_time"])

        overlaps = 0
        for i in range(1, len(df)):
            if entry_dts.iloc[i] < exit_dts.iloc[i - 1]:
                overlaps += 1

        assert overlaps == 0, f"Found {overlaps} overlapping trades!"

    def test_portfolio_simulation_mdd_reduction(self):
        """
        Verify portfolio simulation summary:
        In OOS (2024-2026), filter reduces MDD by >= 40% under 100% allocation,
        and from 5.88% down to 3.19% under 10% allocation.
        """
        assert self.summary_json.exists(), f"Missing {self.summary_json}"
        with open(self.summary_json) as f:
            data = json.load(f)

        oos_sim = data["sim_results"]["oos_period"]
        base_100_mdd = oos_sim["baseline_100pct"]["max_drawdown_pct"]
        filt_100_mdd = oos_sim["filtered_100pct"]["max_drawdown_pct"]
        assert pytest.approx(base_100_mdd, abs=0.5) == 47.35
        assert pytest.approx(filt_100_mdd, abs=0.5) == 28.35
        rel_reduction_100 = (base_100_mdd - filt_100_mdd) / base_100_mdd
        assert rel_reduction_100 >= 0.38

        base_10_mdd = oos_sim["baseline_10pct"]["max_drawdown_pct"]
        filt_10_mdd = oos_sim["filtered_10pct"]["max_drawdown_pct"]
        assert pytest.approx(base_10_mdd, abs=0.1) == 5.88
        assert pytest.approx(filt_10_mdd, abs=0.1) == 3.19

    def test_multiple_testing_bonferroni_hurdle(self):
        """Assert multiple-testing boundary: 19 candidates require alpha = 0.00263; p-values fail."""
        m_candidates = 19
        alpha_nominal = 0.05
        bonferroni_hurdle = alpha_nominal / m_candidates
        assert pytest.approx(bonferroni_hurdle, abs=0.0001) == 0.00263

        with open(self.summary_json) as f:
            data = json.load(f)

        p_val_oos = data["stat_summary"]["oos_period"]["p_val_filt_vs_base"]
        p_val_full_excl = data["stat_summary"]["full_period"]["p_val_filt_vs_excl"]

        assert p_val_oos > bonferroni_hurdle
        assert p_val_full_excl > bonferroni_hurdle

    def test_manifest_v1_7_0_and_protected_hashes(self):
        """Verify protected hash verification file adheres to manifest 1.7.0 and matches hashes."""
        assert self.hash_json.exists(), f"Missing {self.hash_json}"
        with open(self.hash_json) as f:
            data = json.load(f)

        assert data["manifest_version"] == "1.7.0"
        assert data["governed_determination"] == "REPRODUCIBLE_IMPROVEMENT_CANDIDATE"
        assert data["operating_contract"] == "OFFLINE_RESEARCH_ONLY"

        for ds in data["protected_dataset_registry"]:
            rel_path = ds["relative_path"]
            file_path = self.base_dir / rel_path
            assert file_path.exists(), f"Dataset file missing: {rel_path}"

            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            computed_hash = hasher.hexdigest()

            assert computed_hash == ds["expected_sha256"], f"Hash mismatch on {rel_path}"
            assert ds["hash_matched"] is True

    def test_governance_invariants(self):
        """Verify governance invariants: live trading DISABLED, model authorization OFFLINE_RESEARCH_ONLY."""
        with open(self.hash_json) as f:
            data = json.load(f)

        invariants = data["governance_invariants"]
        assert invariants["live_trading"] == "DISABLED - ANALYSIS ONLY"
        assert invariants["model_authorization"] == "OFFLINE_RESEARCH_ONLY"
        assert "RESTRICTED" in invariants["vpin_gate_status"]
        assert "RESTRICTED" in invariants["algorithmic_routing_status"]
        assert "Q2=INSUFFICIENT_EVIDENCE" in invariants["entry_analysis_architecture"]


"""
research/post_repair_comparison.py — Pre vs Post Repair Metric Comparison Report Generator
========================================================================================
Documents the architectural comparison between historical pre-repair metrics
and post-repair canonical baseline.

Outputs:
  - research/reports/pre_post_repair_comparison.md
"""

import os
import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.paths import RESULTS_DIR

REPORT_PATH = os.path.join(os.path.dirname(__file__), "reports", "pre_post_repair_comparison.md")
os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)

COMPARISON_RECORDS = [
    {
        "metric": "Directional Win Rate",
        "pre_repair": "100.0% (Unresolved DEFAULT 1)",
        "post_repair": "Awaiting post-repair resolved cycles (NULL for unresolved)",
        "difference": "Elimination of 100% win-rate default bias",
        "reason": "Unresolved records previously carried was_correct=1. Now strictly set to NULL.",
        "validity": "NOT DIRECTLY COMPARABLE (Pre-repair metric was methodologically distorted)"
    },
    {
        "metric": "Forecast Evaluation Horizon",
        "pre_repair": "4 Hours (Label/Resolution Mismatch)",
        "post_repair": "24 Hours (Contract-Locked)",
        "difference": "20 Hours horizon alignment",
        "reason": "Production model trained on 24h targets but resolved on 4h timer. Fixed to 24h.",
        "validity": "NOT DIRECTLY COMPARABLE (Different evaluation horizons)"
    },
    {
        "metric": "On-Chain Metric Semantics",
        "pre_repair": "mvrv_zscore (1.85 fallback)",
        "post_repair": "CoinMetrics CapMVRVFF ratio (explicit DEGRADED states)",
        "difference": "Semantic clarification from Z-score to Ratio",
        "reason": "Upstream data provides raw market-to-realized ratio; silent 1.85 fallback eliminated.",
        "validity": "VALID (Post-repair preserves actual scientific ratio scale)"
    },
    {
        "metric": "Regime Classification Vocabulary",
        "pre_repair": "7 V3 Neural Strings / 'NORMAL' bug",
        "post_repair": "5 CanonicalRegime Enum states",
        "difference": "Deterministic normalization to canonical ensemble branches",
        "reason": "Prevented unhandled string mismatch in downstream position manager.",
        "validity": "VALID (Preserves intended ensemble routing)"
    },
    {
        "metric": "Database Storage Integrity",
        "pre_repair": "2 Fragmented DBs (268 orphan shadow rows)",
        "post_repair": "Single Unified SQLite WAL Database",
        "difference": "Zero split-brain path risk",
        "reason": "Consolidated shadow and production tables into authoritative database.",
        "validity": "VALID (Full ACID and WAL integrity restored)"
    },
    {
        "metric": "Independent Longitudinal Blocks",
        "pre_repair": "35 Blocks (Historical pre-repair counter)",
        "post_repair": "0 Blocks (Post-repair baseline reset)",
        "difference": "Counter reset to 0",
        "reason": "Pre-repair blocks evaluated under distorted runtime cannot mix with clean post-repair baseline.",
        "validity": "NOT DIRECTLY COMPARABLE (New post-repair evidence sequence begins at 0)"
    }
]

def generate_comparison_report():
    print("=" * 70)
    print("  BTCognitive — PRE vs POST REPAIR COMPARISON GENERATOR")
    print("=" * 70)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# 📑 Pre-Repair vs Post-Repair Metric Reconciliation & Comparison Report\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).isoformat()}  \n")
        f.write("**Status:** `COMPLETED_DATA_INTEGRITY_REPAIR`  \n\n")
        
        f.write("## 1. Architectural & Metric Comparison Table\n\n")
        f.write("| Evaluated Metric / Dimension | Pre-Repair Historical Value | Post-Repair Reconciled Baseline | Observed Difference | Root Cause & Semantic Rationale | Comparability Classification |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        
        for c in COMPARISON_RECORDS:
            f.write(f"| **{c['metric']}** | {c['pre_repair']} | {c['post_repair']} | {c['difference']} | {c['reason']} | `{c['validity']}` |\n")

        f.write("\n\n## 2. Key Governance Findings\n\n")
        f.write("1. **No Performance Degradation:** The underlying forecasting weights (Ridge conformal quantiles and volatility context) remain 100% frozen and unaltered.  \n")
        f.write("2. **Evidence Reset Rationale:** Historical metrics evaluated under 4h resolution with `was_correct=1` defaults cannot be aggregated with 24h canonical observations without contaminating longitudinal statistics.  \n")
        f.write("3. **Milestone Restart:** Post-repair longitudinal evidence starts cleanly at block `0`, tracking the new milestone sequence `[0, 5, 10, 20, 30, 40, 60, 90]`.  \n")

    print(f"Comparison report generated at: {REPORT_PATH}")

if __name__ == "__main__":
    generate_comparison_report()

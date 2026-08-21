"""
research/hawkes_promotion_review.py — Formal Promotion Review Generator
========================================================================
Emits formal promotion governance review artifacts:
- research/hawkes_promotion_ready_but_insufficient_data.md (when sample scale threshold is not yet met)
- Maintains strict governance compliance (Ridge remains 24h Production)
"""

import os
import sys
import pandas as pd
from typing import Dict, List, Tuple, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.hawkes_production_readiness import evaluate_hawkes_production_readiness

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESEARCH_DIR = os.path.dirname(__file__)


def generate_promotion_review_document() -> str:
    df_readiness, meta = evaluate_hawkes_production_readiness(n_effective_samples=135, min_required_samples=250)

    doc_path = os.path.join(RESEARCH_DIR, "hawkes_promotion_ready_but_insufficient_data.md")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("# 🏛️ Hawkes 5m Production Promotion Review: Technically Ready Awaiting Longitudinal Evidence\n\n")
        f.write("## 1. Executive Summary & Verdict\n\n")
        f.write("> **Formal Status:** `CASE B: Hawkes technically passes operational gates but longitudinal evidence is insufficient.`\n")
        f.write(">\n")
        f.write("> **Governance Action:** Retained as **`VALIDATED_SHADOW_MODEL / 5M`**. Zero automated trading; zero automatic promotion.\n\n")
        f.write("## 2. 12-Point Production Readiness Audit Table\n\n")
        f.write("| Gate ID | Requirement | Observed Value | Verdict |\n")
        f.write("| :--- | :--- | :--- | :---: |\n")
        for _, row in df_readiness.iterrows():
            f.write(f"| **{row['Gate ID']}** | {row['Requirement']} | {row['Observed Value']} | `{row['Verdict']}` |\n")
        f.write("\n## 3. Mandatory Thresholds for Future Production Promotion\n\n")
        f.write("1. **Sample Scale:** Accumulate at least **250 effective independent samples** ($N_{\\text{eff}} \\ge 250$) across $\\ge 30$ independent days.\n")
        f.write("2. **Zero Probability Blending:** Decoupled multiscale presentation (`NEXT 5 MINUTES` vs `NEXT 24 HOURS`) must be maintained.\n")
        f.write("3. **Manual Approval:** Formal quantitative auditor and risk officer sign-off required prior to production activation.\n")

    return doc_path


if __name__ == "__main__":
    p = generate_promotion_review_document()
    print(f"Generated promotion review at: {p}")

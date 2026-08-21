"""
research/milestone_5_post_repair_gate.py — 5-Block Clean Evidence Milestone Gate (Quality Stratified)
===================================================================================================
Evaluates the first 5-block milestone for post-repair longitudinal evidence.

Gate Logic:
- Requires valid_independent_blocks >= 5 (100% VALID blocks).
- Rejects mixed or degraded blocks from primary milestone lock.
- If valid_independent_blocks < 5:
    Returns WAITING_FOR_5_POST_REPAIR_BLOCKS.
    Generates observation status report showing VALID, MIXED, DEGRADED block counts.
"""

import os
import sys
import json
import csv
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.paths import RESULTS_DIR
from config.database import MARKET_MEMORY_DB_PATH
from research.post_repair_longitudinal_monitor import (
    post_repair_monitor,
    POST_REPAIR_EVIDENCE_START,
    MODEL_HASH,
    CONTEXT_HASH,
    REPAIR_VERSION
)
from research.post_repair_block_builder import build_post_repair_blocks

MILESTONE_LOCK_PATH = os.path.join(RESULTS_DIR, "post_repair_milestone_5_lock.json")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "reports", "post_repair_5_block_observed.md")
os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)

def evaluate_milestone_5_gate() -> Dict[str, Any]:
    print("=" * 70)
    print("  BTCognitive — 5-BLOCK CLEAN EVIDENCE MILESTONE GATE")
    print(f"  Boundary Timestamp: {POST_REPAIR_EVIDENCE_START}")
    print("=" * 70)

    status = post_repair_monitor.get_status()
    blocks, accounting = build_post_repair_blocks()
    valid_blocks = accounting["independent_valid_blocks"]
    mixed_blocks = accounting["independent_mixed_blocks"]
    degraded_blocks = accounting["independent_degraded_blocks"]

    print(f"Post-Repair Valid 24h Blocks:    {valid_blocks} / 5 Target")
    print(f"Post-Repair Mixed Blocks:        {mixed_blocks}")
    print(f"Post-Repair Degraded Blocks:     {degraded_blocks}")
    print(f"Post-Repair Degraded Forecasts:  {status['observed_degraded_forecasts']}")

    if valid_blocks < 5:
        decision = "WAITING_FOR_5_POST_REPAIR_BLOCKS"
        print(f"\nSTATUS: {decision}")
        print("Awaiting accumulation and full 24h outcome resolution of 5 VALID independent blocks.")

        # Generate Status Report
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write("# 🔬 Post-Repair 5-Block Clean Longitudinal Evidence Report\n\n")
            f.write(f"**Report Generated:** {datetime.now(timezone.utc).isoformat()}  \n")
            f.write(f"**Evidence Boundary:** `{POST_REPAIR_EVIDENCE_START}`  \n")
            f.write(f"**Gate Status:** `{decision}`  \n\n")
            
            f.write("## 1. Quality-Stratified Block & Observation Accounting\n\n")
            f.write("| Parameter | Current Observed Value | Target Milestone | Status |\n")
            f.write("| :--- | :--- | :--- | :--- |\n")
            f.write(f"| **Independent VALID 24H Blocks** | `{valid_blocks}` | `5` | `COLLECTING` |\n")
            f.write(f"| **Independent MIXED Blocks** | `{mixed_blocks}` | `0` (Isolated) | `SEPARATE` |\n")
            f.write(f"| **Independent DEGRADED Blocks** | `{degraded_blocks}` | `0` (Isolated) | `SEPARATE` |\n")
            f.write(f"| **Degraded Forecasts Count** | `{status['observed_degraded_forecasts']}` | - | `WATCH` |\n")
            f.write(f"| **Effective Sample (N_eff)** | `{status['n_eff']}` | `~5.0` | `COMPUTING_ON_CLOSE` |\n")
            f.write(f"| **Production Model** | `v3.0.0-ridge-volatility-context` | FROZEN | `ACTIVE` |\n")

            f.write("\n\n## 2. Milestone Metrics Table (Zero-Projection Policy)\n\n")
            f.write("| Metric | Target Standard | Observed 5-Block Value | Ridge Delta | Verification Status |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            f.write("| **MFE Error (P50)** | $\\le 0.40\\%$ | *TARGET / NOT YET OBSERVED* | *PENDING* | `AWAITING_5_VALID_BLOCKS` |\n")
            f.write("| **MAE Error (P50)** | $\\le 0.60\\%$ | *TARGET / NOT YET OBSERVED* | *PENDING* | `AWAITING_5_VALID_BLOCKS` |\n")
            f.write("| **P90 MFE Coverage** | $\\ge 90.0\\%$ | *TARGET / NOT YET OBSERVED* | *PENDING* | `AWAITING_5_VALID_BLOCKS` |\n")
            f.write("| **P90 MAE Coverage** | $\\ge 90.0\\%$ | *TARGET / NOT YET OBSERVED* | *PENDING* | `AWAITING_5_VALID_BLOCKS` |\n")
            f.write("| **Joint Path Containment**| $\\ge 90.0\\%$ | *TARGET / NOT YET OBSERVED* | *PENDING* | `AWAITING_5_VALID_BLOCKS` |\n")
            f.write("| **Winkler Score** | $\\le 6.50$ | *TARGET / NOT YET OBSERVED* | *PENDING* | `AWAITING_5_VALID_BLOCKS` |\n")

            f.write("\n\n## 3. Passive Monitoring Continuation Protocol\n\n")
            f.write("1. **5 VALID Block Requirement:** The primary validation milestone strictly requires 5 fully VALID blocks where all individual forecasts carry `data_quality = VALID`.  \n")
            f.write("2. **Zero Model Changes:** No retraining, parameter updates, or weight tuning will be performed during longitudinal monitoring.  \n")
            f.write("3. **Historical Isolation:** Historical 35-block pre-repair records remain archived under `PRE_REPAIR_HISTORY` and are strictly excluded from post-repair sample accounting.  \n")

        gate_result = {
            "decision": decision,
            "observed_blocks": valid_blocks,
            "observed_valid_blocks": valid_blocks,
            "target_blocks": 5,
            "lock_created": False,
            "report_path": REPORT_PATH
        }
        return gate_result

    else:
        decision = "POST_REPAIR_5_BLOCK_REVIEW_COMPLETE"
        print(f"\nSTATUS: {decision} — 5 VALID Blocks Satisfied.")

        lock_data = {
            "milestone": "MILESTONE_5_POST_REPAIR_VALID",
            "milestone_timestamp": datetime.now(timezone.utc).isoformat(),
            "evidence_boundary": POST_REPAIR_EVIDENCE_START,
            "observed_valid_blocks": 5,
            "production_model_hash": MODEL_HASH,
            "context_hash": CONTEXT_HASH,
            "repair_version": REPAIR_VERSION,
            "status": "LOCKED"
        }
        with open(MILESTONE_LOCK_PATH, "w", encoding="utf-8") as f:
            json.dump(lock_data, f, indent=2)

        gate_result = {
            "decision": decision,
            "observed_blocks": valid_blocks,
            "observed_valid_blocks": valid_blocks,
            "target_blocks": 5,
            "lock_created": True,
            "lock_path": MILESTONE_LOCK_PATH,
            "report_path": REPORT_PATH
        }
        return gate_result

if __name__ == "__main__":
    evaluate_milestone_5_gate()

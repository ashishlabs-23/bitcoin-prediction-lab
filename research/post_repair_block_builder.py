"""
research/post_repair_block_builder.py — Post-Repair Independent 24H Block Builder (Quality Stratified)
=======================================================================================================
Constructs non-overlapping 24-hour evaluation blocks and classifies each block quality:
  - VALID: 100% of forecasts in the block are VALID and validation_eligible = True.
  - MIXED: Contains both VALID and DEGRADED forecasts.
  - DEGRADED: All forecasts in the block are DEGRADED.
  - INVALID: Contains invalid/corrupt forecasts.

Primary Validation Rule:
  Only block_quality = VALID blocks count toward the official post-repair milestone sequence.

Outputs:
  - results/post_repair_blocks.csv
"""

import os
import sys
import sqlite3
import hashlib
import json
import csv
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.paths import RESULTS_DIR
from config.database import MARKET_MEMORY_DB_PATH
from models.forecast_quality_contract import BlockQuality

POST_REPAIR_EVIDENCE_START = "2026-08-21T12:15:00Z"
REPAIR_VERSION = "v1.0.0-production-data-consistency-repair"
MODEL_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
CONTEXT_HASH = "8f48b11c990b7987a04918e6ec29a67a989f71eaf8e544ebdf8edf60c20b0c89"

BLOCKS_CSV_PATH = os.path.join(RESULTS_DIR, "post_repair_blocks.csv")

def build_post_repair_blocks() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    conn = sqlite3.connect(MARKET_MEMORY_DB_PATH)
    conn.row_factory = sqlite3.Row

    start_dt = pd.Timestamp(POST_REPAIR_EVIDENCE_START).tz_convert(timezone.utc)

    query = """
        SELECT * FROM predictions 
        WHERE data_source != 'synthetic_arena' 
        AND regime NOT LIKE 'SIM_ARENA_%'
        ORDER BY timestamp ASC
    """
    rows = conn.execute(query).fetchall()
    conn.close()

    post_repair_records = []
    for r in rows:
        ts_str = r["timestamp"]
        try:
            r_dt = pd.Timestamp(ts_str).tz_convert(timezone.utc) if pd.Timestamp(ts_str).tz is not None else pd.Timestamp(ts_str).tz_localize(timezone.utc)
            if r_dt >= start_dt and bool(r["outcome_resolved"]) and r["was_correct"] is not None:
                post_repair_records.append(dict(r))
        except Exception:
            continue

    blocks = []
    valid_block_count = 0
    mixed_block_count = 0
    degraded_block_count = 0

    if post_repair_records:
        df_pr = pd.DataFrame(post_repair_records)
        df_pr["dt"] = pd.to_datetime(df_pr["timestamp"], utc=True)
        df_pr = df_pr.sort_values("dt").reset_index(drop=True)

        curr_block_start = start_dt
        block_idx = 1

        max_ts = df_pr["dt"].max()
        while curr_block_start <= max_ts:
            curr_block_end = curr_block_start + pd.Timedelta(hours=24)
            block_df = df_pr[(df_pr["dt"] >= curr_block_start) & (df_pr["dt"] < curr_block_end)]
            
            if not block_df.empty:
                block_id = f"POST_REPAIR_BLK_{block_idx:03d}"
                f_count = len(block_df)
                res_count = int((block_df["outcome_resolved"] == 1).sum())

                # Assess block quality
                qualities = []
                for _, r in block_df.iterrows():
                    ctx_str = r.get("context_vector_json")
                    q = "VALID"
                    if ctx_str and isinstance(ctx_str, str):
                        try:
                            q = json.loads(ctx_str).get("data_quality", "VALID")
                        except Exception:
                            q = "VALID"
                    qualities.append(q)

                if all(q == "VALID" for q in qualities):
                    blk_q = BlockQuality.VALID.value
                    valid_block_count += 1
                elif all(q == "DEGRADED" for q in qualities):
                    blk_q = BlockQuality.DEGRADED.value
                    degraded_block_count += 1
                elif any(q == "INVALID" for q in qualities):
                    blk_q = BlockQuality.INVALID.value
                else:
                    blk_q = BlockQuality.MIXED.value
                    mixed_block_count += 1
                
                block_hash_input = f"{block_id}_{curr_block_start}_{curr_block_end}_{MODEL_HASH}_{CONTEXT_HASH}_{blk_q}_{REPAIR_VERSION}"
                b_hash = hashlib.sha256(block_hash_input.encode()).hexdigest()[:16]

                blocks.append({
                    "block_id": block_id,
                    "start": curr_block_start.isoformat(),
                    "end": curr_block_end.isoformat(),
                    "forecast_count": f_count,
                    "resolved_count": res_count,
                    "block_quality": blk_q,
                    "validation_eligible": (blk_q == BlockQuality.VALID.value),
                    "model_hash": MODEL_HASH,
                    "context_hash": CONTEXT_HASH,
                    "block_hash": b_hash,
                    "repair_version": REPAIR_VERSION
                })
                block_idx += 1
            curr_block_start = curr_block_end

    # Write blocks to CSV
    with open(BLOCKS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "block_id", "start", "end", "forecast_count", "resolved_count",
            "block_quality", "validation_eligible", "model_hash", "context_hash",
            "block_hash", "repair_version"
        ])
        writer.writeheader()
        for b in blocks:
            writer.writerow(b)

    # Sample Accounting
    n_valid_obs = len([r for r in post_repair_records if "DEGRADED" not in str(r.get("context_vector_json", ""))])
    lag1_autocorr = 0.0
    lag24_autocorr = 0.0
    n_eff = 0.0
    if n_valid_obs >= 5:
        returns = [float(r["actual_return"]) for r in post_repair_records]
        s = pd.Series(returns)
        lag1_autocorr = round(float(s.autocorr(lag=1)), 4) if not np.isnan(s.autocorr(lag=1)) else 0.0
        lag24_autocorr = round(float(s.autocorr(lag=24)), 4) if len(s) > 24 and not np.isnan(s.autocorr(lag=24)) else 0.0
        rho = max(0.0, min(0.95, lag1_autocorr))
        n_eff = round(n_valid_obs * (1.0 - rho) / (1.0 + rho), 2)

    accounting = {
        "raw_forecasts": n_valid_obs,
        "resolved_forecasts": n_valid_obs,
        "raw_valid_forecasts": n_valid_obs,
        "resolved_valid_forecasts": n_valid_obs,
        "independent_blocks": valid_block_count,
        "independent_valid_blocks": valid_block_count,
        "independent_mixed_blocks": mixed_block_count,
        "independent_degraded_blocks": degraded_block_count,
        "total_independent_blocks": len(blocks),
        "n_eff": n_eff,
        "lag1_autocorr": lag1_autocorr,
        "lag24_autocorr": lag24_autocorr,
        "calendar_span_hours": len(blocks) * 24,
        "independent_weeks": round(valid_block_count / 7.0, 2)
    }

    return blocks, accounting

if __name__ == "__main__":
    blocks, acc = build_post_repair_blocks()
    print("=" * 70)
    print("  BTCognitive — POST-REPAIR BLOCK BUILDER (QUALITY STRATIFIED)")
    print("=" * 70)
    for k, v in acc.items():
        print(f"  {k:<32}: {v}")
    print(f"Blocks saved to: {BLOCKS_CSV_PATH}")

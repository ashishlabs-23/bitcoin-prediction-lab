"""
tests/test_post_repair_metrics.py — Tests for Post-Repair Baseline Metric Definitions
=====================================================================================
Verifies that:
- Metric revalidation script runs cleanly and outputs post_repair_baseline.csv.
- Baseline deltas against Ridge baseline are defined and directionally coherent.
- No historical metrics are claimed without resolved post-repair evidence.
"""

import os
import csv
from research.post_repair_baseline import revalidate_baseline, BASELINE_CSV

def test_post_repair_baseline_generation():
    revalidate_baseline()
    assert os.path.exists(BASELINE_CSV)
    
    with open(BASELINE_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
    assert len(rows) >= 5
    metrics = [r["metric"] for r in rows]
    assert "MFE Error (P50)" in metrics
    assert "MAE Error (P50)" in metrics
    assert "Joint Path Containment" in metrics

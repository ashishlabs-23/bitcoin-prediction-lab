"""
research/experiments/run_v32_28_master_pipeline.py
==================================================
Master execution script for V32.28:
Runs Phase 2 Strategy Baseline, Phase 3 Forecast Evaluation,
Phase 4 Meta-Model Training & Calibration, and Phase 5 Ablation
storing reproducible artifacts in research/runs/v32_28/.
"""

import os
import sys
import json

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)

from research.experiments.run_phase2_strategy_baseline import evaluate_strategy_baseline
from research.experiments.run_phase3_forecast_evaluation import evaluate_forecast_models
from research.experiments.run_phase4_meta_model import run_phase4_experiment
from research.experiments.run_phase5_ablation import run_phase5_ablation


def run_master_pipeline():
    src_parquet = os.path.join(REPO_ROOT, "data", "research", "coinbase_btc_usd_hourly_v1", "coinbase_hourly.parquet")
    out_dir = os.path.join(REPO_ROOT, "research", "runs", "v32_28")
    os.makedirs(out_dir, exist_ok=True)

    print(f"--- 1. Running Phase 2 Strategy Baseline on {src_parquet} ---")
    p2 = evaluate_strategy_baseline(src_parquet, out_dir)
    print(f"Phase 2 Complete: {p2['total_trades']} trades, Mean Gross R: {p2['mean_gross_r']}")

    print(f"\n--- 2. Running Phase 3 Forecast Evaluation ---")
    p3 = evaluate_forecast_models(src_parquet, out_dir)
    print(f"Phase 3 Complete: GBDT 24h AUC = {p3['gbdt_directional_models']['24h']['auc_roc']}")

    print(f"\n--- 3. Running Phase 4 Meta-Model Training & Calibration ---")
    p4 = run_phase4_experiment(src_parquet, out_dir)
    print(f"Phase 4 Complete: BSS = {p4['calibration_and_scoring']['brier_skill_score']}, Verdict: {p4['phase4_verdict']}")

    print(f"\n--- 4. Running Phase 5 Policy Ablation ---")
    p5 = run_phase5_ablation(out_dir)
    print(f"Phase 5 Complete: Evaluated {len(p5['variants'])} variants.")

    master_summary = {
        "version": "V32.28",
        "output_directory": out_dir,
        "phase2_strategy": p2,
        "phase3_forecast": p3,
        "phase4_meta_model": p4,
        "phase5_ablation": p5
    }

    master_file = os.path.join(out_dir, "master_pipeline_execution_summary.json")
    with open(master_file, "w", encoding="utf-8") as f:
        json.dump(master_summary, f, indent=2)

    print(f"\nAll phases executed successfully. Summary written to {master_file}")
    return master_summary


if __name__ == "__main__":
    run_master_pipeline()

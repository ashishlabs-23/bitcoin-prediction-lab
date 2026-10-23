import os
import sys
sys.path.insert(0, os.path.abspath("."))
import hashlib
import json
import math
import numpy as np
import pandas as pd
from engine.price_forecast_engine import price_forecast_engine

def run_audit():
    ohlcv_path = "data/raw/ohlcv.parquet"
    assert os.path.exists(ohlcv_path), f"Missing {ohlcv_path}"
    
    with open(ohlcv_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    
    df = pd.read_parquet(ohlcv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    # Check continuity
    diffs = df["timestamp"].diff().dropna()
    expected_step = pd.Timedelta(hours=1)
    gaps = diffs[diffs != expected_step]
    
    print(f"Dataset path: {ohlcv_path}")
    print(f"Dataset SHA-256: {file_hash}")
    print(f"Total rows: {len(df)}")
    print(f"Date range: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
    print(f"Candle gaps (diff != 1h): {len(gaps)}")
    
    # Run tournament
    print("\nExecuting walk-forward tournament on 15,000 blocks...")
    res = price_forecast_engine.run_walk_forward_tournament(test_blocks=15000, train_window=20000)
    
    print(f"\nTournament ID: {res['tournament_id']}")
    print(f"Sample Status: {res['sample_status']}")
    print(f"Verdict: {res['tournament_verdict']}")
    
    results = {}
    for h, h_res in res["results_by_horizon"].items():
        n = h_res["sample_size_origins"]
        rw = h_res["persistence_baseline"]
        drift = h_res["rolling_drift_baseline"]
        ridge = h_res["ridge_candidate"]
        
        # Verify skill score formula: (1 - MAE_cand / MAE_rw) * 100
        calc_skill_ridge = (1.0 - ridge["mae_usd"] / rw["mae_usd"]) * 100.0
        
        print(f"\n--- HORIZON {h} (N = {n} non-overlapping blocks) ---")
        print(f"  Persistence RW: MAE = ${rw['mae_usd']:.2f}, RMSE = ${rw['rmse_usd']:.2f}, Bias = ${rw['bias_usd']:.2f}")
        print(f"  Rolling Drift:  MAE = ${drift['mae_usd']:.2f}, RMSE = ${drift['rmse_usd']:.2f}, Bias = ${drift['bias_usd']:.2f}, Skill = {drift['skill_score_pct']:.3f}%, DM = {drift['dm_hln_stat']}, p = {drift['p_value']}")
        print(f"  Ridge Lagged:   MAE = ${ridge['mae_usd']:.2f}, RMSE = ${ridge['rmse_usd']:.2f}, Bias = ${ridge['bias_usd']:.2f}, Skill = {ridge['skill_score_pct']:.3f}%, DM = {ridge['dm_hln_stat']}, p = {ridge['p_value']}")
        print(f"  Formula check: calculated skill = {calc_skill_ridge:.3f}% vs reported {ridge['skill_score_pct']:.3f}%")
        print(f"  Horizon verdict: {h_res['verdict']}")
        
        results[h] = {
            "n_observations": n,
            "persistence_mae_usd": rw["mae_usd"],
            "persistence_rmse_usd": rw["rmse_usd"],
            "persistence_bias_usd": rw["bias_usd"],
            "drift_mae_usd": drift["mae_usd"],
            "drift_rmse_usd": drift["rmse_usd"],
            "drift_skill_pct": drift["skill_score_pct"],
            "drift_p_value": drift["p_value"],
            "ridge_mae_usd": ridge["mae_usd"],
            "ridge_rmse_usd": ridge["rmse_usd"],
            "ridge_skill_pct": ridge["skill_score_pct"],
            "ridge_p_value": ridge["p_value"],
            "verdict": h_res["verdict"]
        }

    out_file = "experiments/results/v20_forecast_reproducibility_manifest.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "manifest_version": "20.0.0",
            "dataset_sha256": file_hash,
            "dataset_rows": len(df),
            "date_range_utc": [str(df['timestamp'].iloc[0]), str(df['timestamp'].iloc[-1])],
            "skill_score_formula": "Skill_pct = (1.0 - MAE_model / MAE_persistence) * 100.0",
            "statistical_test": "Diebold-Mariano with Harvey-Leybourne-Newbold (1997) correction and Student-t(N-1) distribution",
            "results_by_horizon": results,
            "overall_conclusion": res["overall_conclusion"]
        }, f, indent=2)
    print(f"\nWrote manifest to {out_file}")

if __name__ == "__main__":
    run_audit()

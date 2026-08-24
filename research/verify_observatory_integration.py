import os
import sys
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR
from engine.observatory import (
    ForecastAccuracyObservatory,
    CalibrationHealthStatus,
    ForecastLifecycleState
)
from research.run_vol_edge_01_test import prepare_aligned_dataset
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

OUTPUT_MANIFEST = os.path.join(RESULTS_DIR, "observatory_integration_audit.json")


def get_features(sub_df: pd.DataFrame) -> np.ndarray:
    log_rv_down = np.log(np.maximum(1e-6, sub_df['rv_down_1d'].values))
    log_rv_up = np.log(np.maximum(1e-6, sub_df['rv_up_1d'].values))
    log_rv7 = np.log(np.maximum(1e-6, sub_df['rv7d_var_ann_lag'].values))
    log_rv30 = np.log(np.maximum(1e-6, sub_df['rv30d_var_ann'].values))
    dow_dummies = pd.get_dummies(sub_df['dow'], prefix='dow', drop_first=True).values
    if dow_dummies.shape[1] < 6:
        pad = np.zeros((len(sub_df), 6 - dow_dummies.shape[1]))
        dow_dummies = np.column_stack([dow_dummies, pad])
    return np.column_stack([log_rv_down, log_rv_up, log_rv7, log_rv30, dow_dummies])


def run_observatory_integration_audit():
    print("==========================================================================")
    print("RUNNING FORECAST ACCURACY OBSERVATORY PRODUCTION INTEGRATION AUDIT")
    print("==========================================================================")
    
    df = prepare_aligned_dataset()
    holdout_start_dt = pd.to_datetime("2026-01-01T00:00:00Z")
    
    df_train = df[df.index < holdout_start_dt].copy()
    df_holdout = df[df.index >= holdout_start_dt].copy()
    
    # Fit frozen HAR-RS-DOW point forecasts on training data
    log_y_train = np.log(np.maximum(1e-6, df_train['rv7d_var_ann'].values))
    X_train = get_features(df_train)
    X_holdout = get_features(df_holdout)
    
    pipe = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=1.0))])
    pipe.fit(X_train, log_y_train)
    
    v_hat_train = np.exp(pipe.predict(X_train))
    v_hat_holdout = np.exp(pipe.predict(X_holdout))
    y_holdout = df_holdout['rv7d_var_ann'].values
    
    res_train = df_train['rv7d_var_ann'].values - v_hat_train
    res_all = np.concatenate([res_train, y_holdout - v_hat_holdout])
    rolling_std_all = pd.Series(res_all).ewm(span=720, min_periods=72).std().values
    
    s_upper_all = np.maximum(0.0, res_all / np.maximum(1e-4, rolling_std_all))
    s_lower_all = np.maximum(0.0, -res_all / np.maximum(1e-4, rolling_std_all))
    
    N_train = len(df_train)
    N_holdout = len(df_holdout)
    alpha = 0.10
    
    obs = ForecastAccuracyObservatory(nominal_target=0.90)
    print(f"\n1. Streaming {N_holdout:,} holdout forecasts through Observatory ledger...")
    
    for i in range(N_holdout):
        t_global = N_train + i
        pool_u = s_upper_all[max(0, t_global - 1000) : t_global : 24]
        pool_l = s_lower_all[max(0, t_global - 1000) : t_global : 24]
        k_c2 = int(np.ceil((len(pool_u) + 1) * (1.0 - alpha / 2.0)))
        q_u = float(np.sort(pool_u)[min(len(pool_u) - 1, k_c2)])
        q_l = float(np.sort(pool_l)[min(len(pool_l) - 1, k_c2)])
        
        std_i = rolling_std_all[t_global]
        v_i = v_hat_holdout[i]
        lower_i = max(1e-6, v_i - q_l * std_i)
        upper_i = v_i + q_u * std_i
        
        ts_str = df_holdout.index[i].isoformat()
        f_id = f"fc-{df_holdout.index[i].strftime('%Y%m%d%H%M')}"
        
        # Log forecast (PENDING)
        obs.log_forecast(
            forecast_id=f_id,
            timestamp=ts_str,
            v_hat=v_i,
            lower=lower_i,
            upper=upper_i,
            macro_regime="SPOT_ETF_ERA"
        )
        
        # Simulate rolling outcome resolution at maturity (i >= 168)
        if i >= 168:
            mat_idx = i - 168
            mat_fid = f"fc-{df_holdout.index[mat_idx].strftime('%Y%m%d%H%M')}"
            actual_y = y_holdout[mat_idx]
            resolved_time = df_holdout.index[i].isoformat()
            obs.resolve_outcome(
                forecast_id=mat_fid,
                actual_rv7d=actual_y,
                resolved_at=resolved_time
            )

    print("\n2. Evaluating Final Live Observatory Calibration Health Summary...")
    summary = obs.evaluate_calibration_health()
    
    print("\n=================== OBSERVATORY HEALTH CONTROL PLANE ===================")
    print(f"Operational Health Status:    {summary.status.value}")
    print(f"Status Rationale:             {summary.status_rationale}")
    print(f"Total Logged Forecasts:       {len(obs.records):,}")
    print(f"Total Resolved Forecasts:     {summary.total_resolved_forecasts:,}")
    print(f"Pending Maturing Forecasts:   {summary.pending_unresolved_forecasts:,}")
    print(f"30-Day Coverage (Responsive): {summary.coverage_30d_pct:.2f}% (Drift: {summary.coverage_drift_30d_pct:+.2f}%)")
    print(f"90-Day Coverage (Persistent): {summary.coverage_90d_pct:.2f}% (Drift: {summary.coverage_drift_90d_pct:+.2f}%)")
    print(f"All-Time Holdout Coverage:    {summary.coverage_all_pct:.2f}%")
    print(f"30-Day Upper / Lower Breach:  {summary.upper_breach_30d_pct:.2f}% / {summary.lower_breach_30d_pct:.2f}% (Tail Delta: {summary.tail_asymmetry_30d_pct:.2f}%)")
    print(f"30-Day Mean Width / Winkler:  {summary.mean_width_30d:.5f} / {summary.mean_winkler_30d:.5f}")
    print("==========================================================================")
    
    # Audit sample record
    sample_rec = obs.records[100]
    print("\nSample Resolved Ledger Entry (Index 100):")
    print(f"   Forecast ID:         {sample_rec.forecast_id}")
    print(f"   Timestamp:           {sample_rec.timestamp}")
    print(f"   Forecast Hash:       {sample_rec.forecast_hash[:16]}...")
    print(f"   Point Forecast:      {sample_rec.point_forecast_har_rs_dow:.5f}")
    print(f"   Risk Envelope:       [{sample_rec.risk_envelope_lower:.5f}, {sample_rec.risk_envelope_upper:.5f}]")
    print(f"   Actual Realized RV:  {sample_rec.actual_realized_variance:.5f}")
    print(f"   Is Covered:          {sample_rec.is_covered}")
    print(f"   Resolution Latency:  {sample_rec.resolution_latency_hours} hours")
    print(f"   Resolved Hash:       {sample_rec.resolved_hash[:16]}...")
    
    # Assertions
    assert summary.status == CalibrationHealthStatus.STABLE
    assert sample_rec.resolution_latency_hours == 168.0
    assert len(sample_rec.forecast_hash) == 64
    assert len(sample_rec.resolved_hash) == 64
    print("\nObservatory Integration Assertions: ALL PASSED (100% Verified)")
    
    # Save Manifest
    with open(OUTPUT_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(summary.to_dict(), f, indent=2)
    print(f"Observatory Audit Manifest saved to: {OUTPUT_MANIFEST}")


if __name__ == "__main__":
    run_observatory_integration_audit()

"""
research/evaluate_har_calibration_and_coverage.py — Realized Variance HAR Calibration & Coverage
================================================================================================
Empirical evaluation of HAR-24H volatility forecasting model against:
1. Benchmark 1: EWMA-24h
2. Benchmark 2: EWMA-168h
3. Benchmark 3: Lagged 24h Realized Variance

Out-of-sample test window: 2025-01-01 to 2026-10-23 (Coinbase BTC-USD).
Metrics:
- QLIKE Loss: y/v_hat - ln(y/v_hat) - 1
- Root Mean Squared Error (RMSE)
- Diebold-Mariano Test with Harvey-Leybourne-Newbold (1997) finite-sample correction (h=24)
- Forward 24-Hour High-Low Price Range Coverage across multiples k * sigma_24h
"""

import json
import math
import os
import sys
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from engine.har_24h_features import prepare_har_24h_dataset, get_har_24h_feature_matrix


def compute_qlike(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    ratio = y_true / np.maximum(1e-8, y_pred)
    return ratio - np.log(np.maximum(1e-8, ratio)) - 1.0


def diebold_mariano_hln(d: np.ndarray, h: int = 24) -> Tuple[float, float]:
    """
    Diebold-Mariano test with Harvey-Leybourne-Newbold (1997) finite-sample correction.
    d_t = loss_benchmark_t - loss_model_t.
    Positive d means model has lower loss (model is superior).
    """
    T = len(d)
    d_mean = float(np.mean(d))
    gamma_0 = float(np.var(d, ddof=1))

    # Newey-West / Bartlett autocovariance kernel
    auto_cov_sum = 0.0
    for lag in range(1, h):
        weight = 1.0 - (lag / float(h))
        cov_lag = float(np.cov(d[:-lag], d[lag:])[0, 1])
        auto_cov_sum += 2.0 * weight * cov_lag

    lr_var = gamma_0 + auto_cov_sum
    if lr_var <= 1e-12:
        return 0.0, 1.0

    dm_stat = d_mean / math.sqrt(lr_var / float(T))
    # HLN finite sample correction factor
    hln_factor = math.sqrt((T + 1 - 2 * h + (h * (h - 1)) / float(T)) / float(T))
    dm_stat_corrected = dm_stat * hln_factor

    # Two-sided p-value with Student's t_{T-1}
    p_value = 2.0 * (1.0 - stats.t.cdf(abs(dm_stat_corrected), df=max(1, T - 1)))
    return float(dm_stat_corrected), float(p_value)


def run_har_evaluation() -> Dict[str, Any]:
    df = prepare_har_24h_dataset("data/raw/ohlcv.parquet")
    df["year"] = df.index.year

    train_mask = (df["year"] <= 2024)
    test_mask = (df["year"] >= 2025)

    train_df = df[train_mask].copy()
    test_df = df[test_mask].copy()

    X_train, feat_names = get_har_24h_feature_matrix(train_df)
    y_train = train_df["rv24h_var_ann"].values

    X_test, _ = get_har_24h_feature_matrix(test_df)
    y_test = test_df["rv24h_var_ann"].values

    # Fit HAR-24H (Ridge regression in log-variance domain)
    log_y_train = np.log(np.maximum(1e-6, y_train))
    model = Ridge(alpha=1.0)
    model.fit(X_train, log_y_train)

    pred_log_y_test = model.predict(X_test)
    v_hat_har = np.exp(pred_log_y_test)

    # Baselines
    sq_ret = df["r"] ** 2 * 8760.0
    ewma_24 = sq_ret.ewm(span=24).mean().loc[test_df.index].values
    ewma_168 = sq_ret.ewm(span=168).mean().loc[test_df.index].values
    rv_lag = test_df["rv1d_var_ann"].values

    # Losses
    qlike_har = compute_qlike(y_test, v_hat_har)
    qlike_ewma24 = compute_qlike(y_test, ewma_24)
    qlike_ewma168 = compute_qlike(y_test, ewma_168)
    qlike_lag = compute_qlike(y_test, rv_lag)

    rmse_har = math.sqrt(float(np.mean((y_test - v_hat_har) ** 2)))
    rmse_ewma24 = math.sqrt(float(np.mean((y_test - ewma_24) ** 2)))
    rmse_ewma168 = math.sqrt(float(np.mean((y_test - ewma_168) ** 2)))
    rmse_lag = math.sqrt(float(np.mean((y_test - rv_lag) ** 2)))

    # Diebold-Mariano tests
    dm_vs_ewma24, p_vs_ewma24 = diebold_mariano_hln(qlike_ewma24 - qlike_har, h=24)
    dm_vs_ewma168, p_vs_ewma168 = diebold_mariano_hln(qlike_ewma168 - qlike_har, h=24)
    dm_vs_lag, p_vs_lag = diebold_mariano_hln(qlike_lag - qlike_har, h=24)

    # Forward 24h price range coverage
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    test_positions = [df.index.get_loc(idx) for idx in test_df.index]

    ranges = []
    sigmas_24h = []
    for pos_i, loc_t in enumerate(test_positions[:-24]):
        fwd_high = np.max(highs[loc_t + 1 : loc_t + 25])
        fwd_low = np.min(lows[loc_t + 1 : loc_t + 25])
        c_0 = closes[loc_t]
        norm_range = (fwd_high - fwd_low) / c_0
        ranges.append(norm_range)
        sig_24 = math.sqrt(v_hat_har[pos_i] * 24.0 / 8760.0)
        sigmas_24h.append(sig_24)

    ranges = np.array(ranges)
    sigmas_24h = np.array(sigmas_24h)

    coverage_grid = {}
    for k_val in [1.5, 2.0, 2.5, 3.0, 3.5]:
        cov = float(np.mean(ranges <= k_val * sigmas_24h))
        coverage_grid[f"{k_val:.1f}x"] = {
            "multiplier": k_val,
            "empirical_coverage_pct": round(cov * 100.0, 2),
            "breach_pct": round((1.0 - cov) * 100.0, 2),
        }

    out = {
        "evaluation_name": "HAR-24H vs EWMA Out-of-Sample Calibration Audit",
        "sample_period": "2025-01-01 to 2026-10-23",
        "n_test_bars": len(test_df),
        "mean_target_annualized_variance": round(float(np.mean(y_test)), 4),
        "mean_target_annualized_vol": round(math.sqrt(float(np.mean(y_test))) * 100, 2),
        "qlike_loss": {
            "HAR_24H": round(float(np.mean(qlike_har)), 5),
            "EWMA_24H": round(float(np.mean(qlike_ewma24)), 5),
            "EWMA_168H": round(float(np.mean(qlike_ewma168)), 5),
            "Lagged_24H_RV": round(float(np.mean(qlike_lag)), 5),
        },
        "rmse_annualized_variance": {
            "HAR_24H": round(rmse_har, 4),
            "EWMA_24H": round(rmse_ewma24, 4),
            "EWMA_168H": round(rmse_ewma168, 4),
            "Lagged_24H_RV": round(rmse_lag, 4),
        },
        "diebold_mariano_tests": {
            "HAR_vs_EWMA_24H": {
                "dm_stat": round(dm_vs_ewma24, 4),
                "p_value": float(f"{p_vs_ewma24:.4e}"),
                "superior_model": "HAR_24H" if dm_vs_ewma24 > 0 and p_vs_ewma24 < 0.05 else "EWMA_24H",
            },
            "HAR_vs_EWMA_168H": {
                "dm_stat": round(dm_vs_ewma168, 4),
                "p_value": float(f"{p_vs_ewma168:.4e}"),
                "superior_model": "HAR_24H" if dm_vs_ewma168 > 0 and p_vs_ewma168 < 0.05 else "EWMA_168H",
            },
            "HAR_vs_Lagged_RV": {
                "dm_stat": round(dm_vs_lag, 4),
                "p_value": float(f"{p_vs_lag:.4e}"),
                "superior_model": "HAR_24H" if dm_vs_lag > 0 and p_vs_lag < 0.05 else "Lagged_RV",
            },
        },
        "forward_24h_high_low_range_coverage": coverage_grid,
    }

    with open("research/har_calibration_results.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    return out


if __name__ == "__main__":
    res = run_har_evaluation()
    print("=" * 70)
    print("HAR-24H VOLATILITY CALIBRATION & COVERAGE AUDIT")
    print("=" * 70)
    print(f"Test Period:      {res['sample_period']} (N = {res['n_test_bars']} hours)")
    print(f"Mean Target Vol:  {res['mean_target_annualized_vol']}% annualized")
    print("-" * 70)
    print("QLIKE Loss (lower is better):")
    for m, v in res["qlike_loss"].items():
        print(f"  {m:15s}: {v:.5f}")
    print("-" * 70)
    print("RMSE (lower is better):")
    for m, v in res["rmse_annualized_variance"].items():
        print(f"  {m:15s}: {v:.4f}")
    print("-" * 70)
    print("Diebold-Mariano Tests (HLN correction, h=24):")
    for comp, d_res in res["diebold_mariano_tests"].items():
        print(f"  {comp:18s}: DM={d_res['dm_stat']:+.4f}, p={d_res['p_value']:.4e} -> {d_res['superior_model']}")
    print("-" * 70)
    print("Forward 24H Price Range Coverage by k * sigma_24h:")
    for k_name, c_data in res["forward_24h_high_low_range_coverage"].items():
        print(f"  Range <= {k_name:4s} * sigma_24h: {c_data['empirical_coverage_pct']}% coverage (breach: {c_data['breach_pct']}%)")
    print("=" * 70)

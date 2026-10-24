"""
research/fit_purged_walkforward_drift_model.py — Purged Walk-Forward Drift Model Fitting
========================================================================================
Implements Step 3 of the audit spec:
Fits drift parameter mu_t = beta^T X_t for the First-Passage Diffusion Model
using strictly purged, expanding-window walk-forward cross validation on 2022-2024,
and evaluates out-of-sample on 2025-2026.

Variants counted and logged:
- V1: 1h standardized return (r_1h / sigma_1h)
- V2: 4h standardized return (r_4h / (sigma_1h * 2))
- V3: 24h standardized return (r_24h / (sigma_1h * sqrt(24)))
- V4: Multi-horizon return momentum combination [r_1h, r_4h, r_24h]
- V5: Volatility regime interaction [r_1h, r_4h, vol_ratio]

Purged Cross-Validation Scheme:
- 3 expanding folds across 2022-2024.
- Purge buffer: 24 hours between train and test splits to prevent boundary leakage.
"""

import json
import math
import os
import sys
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression, Ridge

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from research.first_passage_diffusion_model import FirstPassageDiffusionModel

DATA_PATH = "data/raw/ohlcv.parquet"


def compute_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    pos = y_score[y_true == 1]
    neg = y_score[y_true == 0]
    n_pos = len(pos)
    n_neg = len(neg)
    if n_pos == 0 or n_neg == 0:
        return 0.5
    ranks = stats.rankdata(np.concatenate([pos, neg]))
    rank_sum_pos = np.sum(ranks[:n_pos])
    u_stat = rank_sum_pos - (n_pos * (n_pos + 1)) / 2.0
    return float(u_stat / (n_pos * n_neg))


def run_purged_walkforward_fitting() -> Dict[str, Any]:
    df = pd.read_parquet(DATA_PATH)
    df["dt"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("dt").reset_index(drop=True)

    # Segment data to ensure contiguity
    diffs = df["dt"].diff()
    df["seg_id"] = (diffs != pd.Timedelta(hours=1)).cumsum()

    df["r_1h"] = np.log(df["close"] / df["close"].shift(1))
    df["r_4h"] = np.log(df["close"] / df["close"].shift(4))
    df["r_24h"] = np.log(df["close"] / df["close"].shift(24))

    # Rolling hourly volatility within segment
    df["sigma_1h"] = df.groupby("seg_id")["r_1h"].transform(
        lambda s: s.rolling(24, min_periods=24).std()
    )
    df["sigma_168h"] = df.groupby("seg_id")["r_1h"].transform(
        lambda s: s.rolling(168, min_periods=168).std()
    )
    df["vol_ratio"] = df["sigma_1h"] / np.maximum(1e-5, df["sigma_168h"])

    H = 24
    k_tp = 1.5
    k_sl = 1.0

    opens = df["open"].values
    highs = df["high"].values
    lows = df["low"].values
    sigmas = df["sigma_1h"].values
    segs = df["seg_id"].values
    n = len(df)

    # Resolve labels
    outcomes = [None] * n
    for i in range(168, n - H):
        if segs[i] != segs[i + H]:
            continue
        vol = sigmas[i]
        if np.isnan(vol) or vol <= 1e-5:
            continue

        entry_p = opens[i + 1]
        sigma_H = vol * math.sqrt(H)
        b_tp = entry_p * (1.0 + k_tp * sigma_H)
        b_sl = entry_p * (1.0 - k_sl * sigma_H)

        outcome = "TIMEOUT"
        for j in range(i + 1, i + H + 1):
            if highs[j] >= b_tp and lows[j] <= b_sl:
                outcome = "SL"
                break
            elif lows[j] <= b_sl:
                outcome = "SL"
                break
            elif highs[j] >= b_tp:
                outcome = "TP"
                break
        outcomes[i] = outcome

    df["outcome"] = outcomes
    df["year"] = df["dt"].dt.year

    # Normalized features
    df["f_r1"] = df["r_1h"] / np.maximum(1e-4, df["sigma_1h"])
    df["f_r4"] = df["r_4h"] / np.maximum(1e-4, df["sigma_1h"] * 2.0)
    df["f_r24"] = df["r_24h"] / np.maximum(1e-4, df["sigma_1h"] * math.sqrt(24))
    df["f_vol_ratio"] = np.log(np.maximum(0.1, df["vol_ratio"]))

    valid_mask = df["outcome"].notna() & df["f_r1"].notna() & df["f_r4"].notna() & df["f_r24"].notna() & df["f_vol_ratio"].notna()
    df_clean = df[valid_mask].copy().reset_index(drop=True)

    df_clean["y_tp"] = (df_clean["outcome"] == "TP").astype(int)

    # Walk-forward splits
    # Fold 1: Train 2022 (with 24h purge) -> Val 2023
    # Fold 2: Train 2022-2023 (with 24h purge) -> Val 2024
    # Final Out-of-Sample: Train 2022-2024 (with 24h purge) -> Test 2025-2026
    variants = {
        "V1_1h_momentum": ["f_r1"],
        "V2_4h_momentum": ["f_r4"],
        "V3_24h_momentum": ["f_r24"],
        "V4_multi_horizon": ["f_r1", "f_r4", "f_r24"],
        "V5_momentum_vol_interaction": ["f_r1", "f_r4", "f_r24", "f_vol_ratio"],
    }

    variant_results = {}
    fp_model = FirstPassageDiffusionModel()

    for v_name, feat_cols in variants.items():
        # Purged expanding CV
        val_aucs = []
        for train_end_year, val_year in [(2022, 2023), (2023, 2024)]:
            # Purge last 24h of train year
            train_mask = (df_clean["year"] <= train_end_year) & (df_clean["dt"] <= f"{train_end_year}-12-30 23:00:00+00:00")
            val_mask = (df_clean["year"] == val_year)

            X_tr = df_clean.loc[train_mask, feat_cols].values
            y_tr = df_clean.loc[train_mask, "y_tp"].values

            X_val = df_clean.loc[val_mask, feat_cols].values
            y_val = df_clean.loc[val_mask, "y_tp"].values

            # Fit logistic drift
            clf = LogisticRegression(penalty="l2", C=0.1, solver="lbfgs")
            clf.fit(X_tr, y_tr)

            probs_val = clf.predict_proba(X_val)[:, 1]
            val_aucs.append(compute_auc(y_val, probs_val))

        # Final out-of-sample test on 2025-2026
        train_full_mask = (df_clean["year"] <= 2024) & (df_clean["dt"] <= "2024-12-30 23:00:00+00:00")
        test_mask = (df_clean["year"] >= 2025)

        X_train_full = df_clean.loc[train_full_mask, feat_cols].values
        y_train_full = df_clean.loc[train_full_mask, "y_tp"].values

        X_test = df_clean.loc[test_mask, feat_cols].values
        y_test = df_clean.loc[test_mask, "y_tp"].values

        clf_full = LogisticRegression(penalty="l2", C=0.1, solver="lbfgs")
        clf_full.fit(X_train_full, y_train_full)

        probs_test = clf_full.predict_proba(X_test)[:, 1]
        auc_test = compute_auc(y_test, probs_test)

        # Map to diffusion drift: mu_t = logit(p_t) - logit(p_0)
        p0 = float(np.mean(y_train_full))
        logit_p0 = math.log(p0 / (1.0 - p0))
        predicted_drifts = np.log(probs_test / (1.0 - probs_test)) - logit_p0

        coef_dict = {f_name: round(float(c), 4) for f_name, c in zip(feat_cols, clf_full.coef_[0])}
        coef_dict["intercept"] = round(float(clf_full.intercept_[0]), 4)

        variant_results[v_name] = {
            "features": feat_cols,
            "fitted_coefficients": coef_dict,
            "cv_val_aucs": [round(a, 4) for a in val_aucs],
            "cv_val_auc_mean": round(float(np.mean(val_aucs)), 4),
            "out_of_sample_test_auc": round(auc_test, 4),
            "mean_oos_predicted_drift": round(float(np.mean(predicted_drifts)), 4),
            "test_sample_size": len(y_test),
        }

    out = {
        "evaluation_name": "Purged Walk-Forward Drift Model Fitting & Out-of-Sample Validation",
        "validation_protocol": "Purged Expanding Window (2022->2023, 2022-2023->2024, Test: 2025-2026)",
        "purge_embargo_hours": 24,
        "variants_evaluated_count": len(variants),
        "variants": variant_results,
    }

    with open("research/drift_model_walkforward_results.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    return out


if __name__ == "__main__":
    res = run_purged_walkforward_fitting()
    print("=" * 70)
    print("PURGED WALK-FORWARD DRIFT MODEL FITTING (COUNTED VARIANTS)")
    print("=" * 70)
    print(f"Total Variants Evaluated: {res['variants_evaluated_count']}")
    print("-" * 70)
    for v_name, v_data in res["variants"].items():
        print(f"Variant: {v_name}")
        print(f"  Features:       {v_data['features']}")
        print(f"  Coefficients:   {v_data['fitted_coefficients']}")
        print(f"  CV Val AUC:     {v_data['cv_val_auc_mean']:.4f} (folds: {v_data['cv_val_aucs']})")
        print(f"  OOS Test AUC:   {v_data['out_of_sample_test_auc']:.4f} (2025-2026, N = {v_data['test_sample_size']} hours)")
        print("-" * 70)

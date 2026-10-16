"""
research/stage8_data_experiments.py — Stage 8 Historical Data Strategy & Incremental Signal Validation
======================================================================================================
Executes controlled predictive experiments to determine whether new, historically verified data
(specifically historical funding rates and open interest) provides reliable, out-of-sample
incremental predictive signal over the established 4-return-lag baseline.

Pre-registered Experiments:
1. Experiment 1: Canonical 4-Year Full History Comparison (2022–2026, N = 33,919 test bars)
   - Baseline: 4-lag GBDT (ret_1h, ret_4h, ret_24h, ret_168h)
   - Baseline: 4-lag L2 Logistic Regression
   - Challenger 1A: 4-lag GBDT + Point-in-Time Funding Rate Level
   - Challenger 1B: 4-lag GBDT + Funding Rate Level + 7d Z-score + 24h Delta
   - Challenger 1C: 4-lag L2 Logistic Regression + Funding Rate Features

2. Experiment 2: Common Sub-Period Evaluation (2026 OI Overlap, N = 2,831 test bars)
   - Evaluates Baseline vs Funding vs Open Interest on the EXACT common evaluation period.
   - Baseline on Common Period (4 lags)
   - Challenger 2A: Baseline + Open Interest Dynamics (1h change, 24h change, 24h z-score)
   - Challenger 2B: Baseline + Funding Rate Features
   - Challenger 2C: Combined Derivatives (Baseline + Funding + Open Interest)

3. Experiment 3: Multi-Horizon Horizon Sensitivity (1-Hour vs 4-Hour Directional Return)
   - Tests whether slower derivatives positioning signals exhibit stronger predictability at 4h horizon.

4. Experiment 4: Economic Viability and Cost Simulation
   - Evaluates turnover, gross return, and net return under 14 bps and 35 bps transaction friction.
"""

import os
import sys
import time
import json
import math
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any
from scipy import stats

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, roc_auc_score, brier_score_loss, log_loss
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from validation.purged_split import PurgedWalkForwardSplit

OUTPUT_DIR = os.path.join(REPO_ROOT, "experiments", "results", "stage8_data_experiments")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "stage8_experiment_results.json")


def moving_block_bootstrap_diff(
    diffs: np.ndarray,
    block_length: int = 24,
    n_bootstraps: int = 1000,
    alpha: float = 0.05,
    seed: int = 42
) -> Tuple[float, float, float, float]:
    """Computes moving block bootstrap CI and two-sided p-value for paired differences."""
    rng = np.random.default_rng(seed)
    n = len(diffs)
    n_blocks = int(np.ceil(n / block_length))
    max_start = n - block_length
    if max_start <= 0:
        m = float(np.mean(diffs))
        return m, m, 0.0, 1.0

    boot_means = np.empty(n_bootstraps, dtype=np.float64)
    for b in range(n_bootstraps):
        starts = rng.integers(0, max_start + 1, size=n_blocks)
        indices = np.concatenate([np.arange(s, s + block_length) for s in starts])[:n]
        boot_means[b] = np.mean(diffs[indices])

    ci_lower = float(np.percentile(boot_means, 100.0 * (alpha / 2.0)))
    ci_upper = float(np.percentile(boot_means, 100.0 * (1.0 - alpha / 2.0)))
    boot_se = float(np.std(boot_means))
    z = np.mean(diffs) / boot_se if boot_se > 0 else 0.0
    p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(z))))
    return ci_lower, ci_upper, boot_se, p_val


def compute_mcnemar_test(y_true: np.ndarray, pred_a: np.ndarray, pred_b: np.ndarray) -> Tuple[float, float]:
    """Computes McNemar chi-squared statistic and p-value on discordant predictions."""
    correct_a = (pred_a == y_true)
    correct_b = (pred_b == y_true)
    b_only = np.sum(~correct_a & correct_b)
    c_only = np.sum(correct_a & ~correct_b)
    total_discordant = b_only + c_only
    if total_discordant == 0:
        return 0.0, 1.0
    stat = float((abs(b_only - c_only) - 1.0) ** 2 / total_discordant)
    p_val = float(1.0 - stats.chi2.cdf(stat, df=1))
    return stat, p_val


def compute_expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Computes Expected Calibration Error (ECE) across probability bins."""
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for i in range(n_bins):
        mask = (y_prob > bin_edges[i]) & (y_prob <= bin_edges[i + 1])
        cnt = np.sum(mask)
        if cnt > 0:
            acc = np.mean(y_true[mask])
            conf = np.mean(y_prob[mask])
            ece += (cnt / n) * abs(acc - conf)
    return float(ece)


def compute_wilson_ci(k: int, n: int, confidence: float = 0.95) -> List[float]:
    """Calculates Wilson score interval for binomial proportion."""
    if n <= 0:
        return [0.0, 0.0]
    z = stats.norm.ppf((1.0 + confidence) / 2.0)
    p_hat = k / n
    denom = 1.0 + (z**2) / n
    center = (p_hat + (z**2) / (2.0 * n)) / denom
    half = (z * math.sqrt((p_hat * (1.0 - p_hat) + (z**2) / (4.0 * n)) / n)) / denom
    return [round(max(0.0, center - half) * 100.0, 2), round(min(1.0, center + half) * 100.0, 2)]


def holm_bonferroni(p_values: List[float]) -> List[float]:
    """Applies Holm-Bonferroni correction to a list of p-values."""
    m = len(p_values)
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * m
    running_max = 0.0
    for rank, (orig_idx, p) in enumerate(indexed):
        adj_p = min(1.0, p * (m - rank))
        running_max = max(running_max, adj_p)
        adjusted[orig_idx] = round(running_max, 4)
    return adjusted


def prepare_stage8_datasets() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Loads raw OHLCV, historical funding rate, and open interest datasets,
    performs strictly causal point-in-time alignment, and generates feature spaces.
    Returns:
      df_full: Complete 2022–2026 canonical dataset (with 4 lags and funding features)
      df_common_oi: 2026 overlapping dataset (with 4 lags, funding, and OI features)
    """
    raw_ohlcv_path = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
    raw_funding_path = os.path.join(REPO_ROOT, "data", "raw", "binance_funding_2022_2026.parquet")
    raw_oi_path = os.path.join(REPO_ROOT, "data", "raw", "oi.parquet")

    # 1. Base OHLCV
    df_ohlcv = pd.read_parquet(raw_ohlcv_path)
    df_ohlcv["timestamp"] = pd.to_datetime(df_ohlcv["timestamp"], utc=True)
    df_ohlcv = df_ohlcv.sort_values("timestamp").reset_index(drop=True)

    close = df_ohlcv["close"]
    df_ohlcv["ret_1h"] = np.log(close / close.shift(1))
    df_ohlcv["ret_4h"] = np.log(close / close.shift(4))
    df_ohlcv["ret_24h"] = np.log(close / close.shift(24))
    df_ohlcv["ret_168h"] = np.log(close / close.shift(168))

    # 1-Hour and 4-Hour Forward Return Targets
    df_ohlcv["fwd_ret_1h"] = np.log(close.shift(-1) / close)
    df_ohlcv["target_1h"] = (df_ohlcv["fwd_ret_1h"] > 0).astype(int)
    df_ohlcv["t1_1h"] = df_ohlcv["timestamp"] + pd.Timedelta(hours=1)

    df_ohlcv["fwd_ret_4h"] = np.log(close.shift(-4) / close)
    df_ohlcv["target_4h"] = (df_ohlcv["fwd_ret_4h"] > 0).astype(int)
    df_ohlcv["t1_4h"] = df_ohlcv["timestamp"] + pd.Timedelta(hours=4)

    # 2. Historical Funding Rates (Point-in-Time Join)
    df_fund = pd.read_parquet(raw_funding_path)
    # Floor funding settlement timestamp to hourly bar and match dtype exactly
    df_fund["timestamp_settle"] = df_fund["timestamp"].dt.floor("1h").astype(df_ohlcv["timestamp"].dtype)
    df_fund = df_fund.drop_duplicates(subset=["timestamp_settle"]).sort_values("timestamp_settle")

    # Point-in-time merge: at any hour t, we only know funding rates settled at or before t
    df_merged = pd.merge_asof(
        df_ohlcv,
        df_fund[["timestamp_settle", "funding_rate"]],
        left_on="timestamp",
        right_on="timestamp_settle",
        direction="backward"
    )

    # Causal Funding Features
    df_merged["funding_rate_prev"] = df_merged["funding_rate"]
    # 7-day (168h) rolling funding z-score
    roll_mean_7d = df_merged["funding_rate_prev"].rolling(168).mean()
    roll_std_7d = df_merged["funding_rate_prev"].rolling(168).std().replace(0.0, np.nan)
    df_merged["funding_rate_zscore_7d"] = ((df_merged["funding_rate_prev"] - roll_mean_7d) / roll_std_7d).fillna(0.0)
    df_merged["funding_rate_diff_24h"] = (df_merged["funding_rate_prev"] - df_merged["funding_rate_prev"].shift(24)).fillna(0.0)

    # Clean full dataset
    needed_full = [
        "ret_1h", "ret_4h", "ret_24h", "ret_168h",
        "funding_rate_prev", "funding_rate_zscore_7d", "funding_rate_diff_24h",
        "fwd_ret_1h", "target_1h", "t1_1h",
        "fwd_ret_4h", "target_4h", "t1_4h", "timestamp"
    ]
    df_full = df_merged.dropna(subset=needed_full).reset_index(drop=True)

    # 3. Open Interest Overlap Dataset (2026 sub-period)
    df_oi = pd.read_parquet(raw_oi_path)
    df_oi["timestamp"] = pd.to_datetime(df_oi["timestamp"], utc=True).astype(df_full["timestamp"].dtype)
    df_oi = df_oi.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    oi = df_oi["open_interest"]
    df_oi["oi_change_1h"] = np.log(oi / oi.shift(1))
    df_oi["oi_change_24h"] = np.log(oi / oi.shift(24))
    oi_roll_mean_24h = oi.rolling(24).mean()
    oi_roll_std_24h = oi.rolling(24).std().replace(0.0, np.nan)
    df_oi["oi_zscore_24h"] = ((oi - oi_roll_mean_24h) / oi_roll_std_24h).fillna(0.0)

    # Merge OI with df_full strictly on exact hourly timestamp
    df_common_oi = pd.merge(
        df_full,
        df_oi[["timestamp", "open_interest", "oi_change_1h", "oi_change_24h", "oi_zscore_24h"]],
        on="timestamp",
        how="inner"
    )
    needed_oi = needed_full + ["open_interest", "oi_change_1h", "oi_change_24h", "oi_zscore_24h"]
    df_common_oi = df_common_oi.dropna(subset=needed_oi).reset_index(drop=True)

    return df_full, df_common_oi


def run_stage8_experiments():
    print("=" * 80, flush=True)
    print("BTCognitive Stage 8: Historical Data Strategy & Signal Validation", flush=True)
    print("=" * 80, flush=True)

    df_full, df_common_oi = prepare_stage8_datasets()
    print(f"Full Canonical Dataset (2022-2026): {df_full['timestamp'].min()} to {df_full['timestamp'].max()} ({len(df_full):,} bars)", flush=True)
    print(f"Common OI Sub-period Dataset (2026):  {df_common_oi['timestamp'].min()} to {df_common_oi['timestamp'].max()} ({len(df_common_oi):,} bars)", flush=True)

    results: Dict[str, Any] = {
        "timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
        "experiment_1_canonical_history_funding": {},
        "experiment_2_common_period_oi": {},
        "experiment_3_multihorizon_4h": {},
        "experiment_4_economic_viability": {}
    }

    feature_cols_4lags = ["ret_1h", "ret_4h", "ret_24h", "ret_168h"]
    feature_cols_funding_level = ["ret_1h", "ret_4h", "ret_24h", "ret_168h", "funding_rate_prev"]
    feature_cols_funding_all = [
        "ret_1h", "ret_4h", "ret_24h", "ret_168h",
        "funding_rate_prev", "funding_rate_zscore_7d", "funding_rate_diff_24h"
    ]

    # =========================================================================
    # EXPERIMENT 1: CANONICAL 4-YEAR FULL HISTORY (2022–2026)
    # =========================================================================
    print("\n" + "=" * 80, flush=True)
    print("EXPERIMENT 1: CANONICAL 4-YEAR EVALUATION (4 LAGS VS FUNDING RATE)", flush=True)
    print("=" * 80, flush=True)

    splitter_5 = PurgedWalkForwardSplit(n_splits=5, embargo_bars=1)
    ts = df_full["timestamp"]
    t1 = df_full["t1_1h"]
    y_full = df_full["target_1h"]
    fwd_r_full = df_full["fwd_ret_1h"].values
    splits_full = list(splitter_5.split(ts, t1))

    total_test_full = sum(len(te) for _, te in splits_full)
    print(f"Walk-forward splits: 5 folds, total evaluated test bars = {total_test_full:,}", flush=True)

    exp1_models = {
        "baseline_gbdt_4lags": (feature_cols_4lags, "gbdt"),
        "baseline_logistic_4lags": (feature_cols_4lags, "logistic"),
        "challenger_gbdt_funding_level": (feature_cols_funding_level, "gbdt"),
        "challenger_gbdt_funding_all": (feature_cols_funding_all, "gbdt"),
        "challenger_logistic_funding_all": (feature_cols_funding_all, "logistic")
    }

    exp1_preds = {m: [] for m in exp1_models}
    exp1_probs = {m: [] for m in exp1_models}
    exp1_times = {m: 0.0 for m in exp1_models}
    exp1_true = []
    exp1_fwd_ret = []

    for fold_idx, (tr_idx, te_idx) in enumerate(splits_full):
        y_tr = y_full.iloc[tr_idx].values
        y_te = y_full.iloc[te_idx].values
        exp1_true.extend(y_te)
        exp1_fwd_ret.extend(fwd_r_full[te_idx])

        for m_name, (feat_cols, m_type) in exp1_models.items():
            X_tr = df_full.iloc[tr_idx][feat_cols]
            X_te = df_full.iloc[te_idx][feat_cols]

            if m_type == "gbdt":
                clf = GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
            else:
                clf = Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression(C=1.0, random_state=42))])

            t0 = time.perf_counter()
            clf.fit(X_tr, y_tr)
            exp1_times[m_name] += (time.perf_counter() - t0)

            p_te = clf.predict_proba(X_te)[:, 1]
            exp1_probs[m_name].extend(p_te)
            exp1_preds[m_name].extend((p_te >= 0.5).astype(int))

        print(f"  Fold {fold_idx}: Train {len(tr_idx):,} | Test {len(te_idx):,} completed.", flush=True)

    exp1_true = np.array(exp1_true)
    exp1_fwd_ret = np.array(exp1_fwd_ret)
    base_preds_gb = np.array(exp1_preds["baseline_gbdt_4lags"])
    base_correct_gb = (base_preds_gb == exp1_true).astype(int)

    exp1_results = {}
    p_vals_exp1 = []
    keys_exp1 = []

    for m_name in exp1_models:
        preds = np.array(exp1_preds[m_name])
        probs = np.array(exp1_probs[m_name])

        acc = float(accuracy_score(exp1_true, preds) * 100.0)
        bal_acc = float(balanced_accuracy_score(exp1_true, preds) * 100.0)
        auc = float(roc_auc_score(exp1_true, probs))
        brier = float(brier_score_loss(exp1_true, probs))
        logloss = float(log_loss(exp1_true, probs))
        ece = compute_expected_calibration_error(exp1_true, probs)
        train_sec = round(exp1_times[m_name], 2)

        # Fold breakdown
        per_fold = []
        cur = 0
        for _, te_idx in splits_full:
            n_te = len(te_idx)
            per_fold.append(round(float(accuracy_score(exp1_true[cur:cur + n_te], preds[cur:cur + n_te]) * 100.0), 2))
            cur += n_te

        entry = {
            "model": m_name,
            "overall_accuracy_pct": round(acc, 2),
            "balanced_accuracy_pct": round(bal_acc, 2),
            "roc_auc": round(auc, 4),
            "brier_score": round(brier, 4),
            "log_loss": round(logloss, 4),
            "ece": round(ece, 4),
            "train_time_sec": train_sec,
            "per_fold_accuracy": per_fold,
            "per_fold_std": round(float(np.std(per_fold)), 2)
        }

        if m_name != "baseline_gbdt_4lags":
            cand_correct = (preds == exp1_true).astype(int)
            diffs = (cand_correct - base_correct_gb).astype(float) * 100.0
            ci_l, ci_u, se, p_val = moving_block_bootstrap_diff(diffs, block_length=24, n_bootstraps=1000)
            mcnemar_stat, mcnemar_p = compute_mcnemar_test(exp1_true, base_preds_gb, preds)

            entry["paired_vs_baseline_gbdt"] = {
                "mean_delta_pct": round(float(np.mean(diffs)), 2),
                "bootstrap_95_ci": [round(ci_l, 2), round(ci_u, 2)],
                "bootstrap_se": round(se, 3),
                "bootstrap_p_val": round(p_val, 4),
                "mcnemar_stat": round(mcnemar_stat, 4),
                "mcnemar_p_val": round(mcnemar_p, 4)
            }
            p_vals_exp1.append(p_val)
            keys_exp1.append(m_name)

        exp1_results[m_name] = entry
        print(f"  [{m_name}] Acc: {acc:.2f}% | AUC: {auc:.4f} | Brier: {brier:.4f} | Time: {train_sec:.1f}s | Folds: {per_fold}", flush=True)

    # Multiplicity correction
    adj_p = holm_bonferroni(p_vals_exp1)
    for idx, k in enumerate(keys_exp1):
        exp1_results[k]["paired_vs_baseline_gbdt"]["holm_bonferroni_adj_p_val"] = adj_p[idx]
        exp1_results[k]["paired_vs_baseline_gbdt"]["statistically_significant_adjusted"] = bool(adj_p[idx] < 0.05)

    results["experiment_1_canonical_history_funding"] = exp1_results

    # =========================================================================
    # EXPERIMENT 2: COMMON SUB-PERIOD EVALUATION (2026 OPEN INTEREST OVERLAP)
    # =========================================================================
    print("\n" + "=" * 80, flush=True)
    print("EXPERIMENT 2: COMMON 2026 SUB-PERIOD (BASELINE VS FUNDING VS OPEN INTEREST)", flush=True)
    print("=" * 80, flush=True)

    # In df_common_oi, we have 2,831 bars. We run a 3-fold purged walk-forward split strictly on this period.
    splitter_oi = PurgedWalkForwardSplit(n_splits=3, embargo_bars=1)
    ts_oi = df_common_oi["timestamp"]
    t1_oi = df_common_oi["t1_1h"]
    y_oi = df_common_oi["target_1h"]
    fwd_r_oi = df_common_oi["fwd_ret_1h"].values
    splits_oi = list(splitter_oi.split(ts_oi, t1_oi))

    total_test_oi = sum(len(te) for _, te in splits_oi)
    print(f"Common period evaluated test bars = {total_test_oi:,}", flush=True)

    feature_cols_oi = ["ret_1h", "ret_4h", "ret_24h", "ret_168h", "oi_change_1h", "oi_change_24h", "oi_zscore_24h"]
    feature_cols_combined = feature_cols_funding_all + ["oi_change_1h", "oi_change_24h", "oi_zscore_24h"]

    exp2_models = {
        "baseline_common_4lags": feature_cols_4lags,
        "challenger_common_funding": feature_cols_funding_all,
        "challenger_common_open_interest": feature_cols_oi,
        "challenger_common_combined": feature_cols_combined
    }

    exp2_preds = {m: [] for m in exp2_models}
    exp2_probs = {m: [] for m in exp2_models}
    exp2_true = []

    for fold_idx, (tr_idx, te_idx) in enumerate(splits_oi):
        y_tr = y_oi.iloc[tr_idx].values
        y_te = y_oi.iloc[te_idx].values
        exp2_true.extend(y_te)

        for m_name, feat_cols in exp2_models.items():
            X_tr = df_common_oi.iloc[tr_idx][feat_cols]
            X_te = df_common_oi.iloc[te_idx][feat_cols]

            clf = GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
            clf.fit(X_tr, y_tr)

            p_te = clf.predict_proba(X_te)[:, 1]
            exp2_probs[m_name].extend(p_te)
            exp2_preds[m_name].extend((p_te >= 0.5).astype(int))

        print(f"  OI Fold {fold_idx}: Train {len(tr_idx):,} | Test {len(te_idx):,} completed.", flush=True)

    exp2_true = np.array(exp2_true)
    base_oi_correct = (np.array(exp2_preds["baseline_common_4lags"]) == exp2_true).astype(int)

    exp2_results = {}
    p_vals_exp2 = []
    keys_exp2 = []

    for m_name in exp2_models:
        preds = np.array(exp2_preds[m_name])
        probs = np.array(exp2_probs[m_name])

        acc = float(accuracy_score(exp2_true, preds) * 100.0)
        bal_acc = float(balanced_accuracy_score(exp2_true, preds) * 100.0)
        auc = float(roc_auc_score(exp2_true, probs))
        brier = float(brier_score_loss(exp2_true, probs))

        entry = {
            "model": m_name,
            "sample_size": len(exp2_true),
            "overall_accuracy_pct": round(acc, 2),
            "balanced_accuracy_pct": round(bal_acc, 2),
            "roc_auc": round(auc, 4),
            "brier_score": round(brier, 4)
        }

        if m_name != "baseline_common_4lags":
            cand_correct = (preds == exp2_true).astype(int)
            diffs = (cand_correct - base_oi_correct).astype(float) * 100.0
            ci_l, ci_u, se, p_val = moving_block_bootstrap_diff(diffs, block_length=24, n_bootstraps=1000)
            mcnemar_stat, mcnemar_p = compute_mcnemar_test(exp2_true, np.array(exp2_preds["baseline_common_4lags"]), preds)

            entry["paired_vs_baseline_common"] = {
                "mean_delta_pct": round(float(np.mean(diffs)), 2),
                "bootstrap_95_ci": [round(ci_l, 2), round(ci_u, 2)],
                "bootstrap_p_val": round(p_val, 4),
                "mcnemar_p_val": round(mcnemar_p, 4)
            }
            p_vals_exp2.append(p_val)
            keys_exp2.append(m_name)

        exp2_results[m_name] = entry
        print(f"  [{m_name}] Acc: {acc:.2f}% | AUC: {auc:.4f} | Brier: {brier:.4f}", flush=True)

    adj_p2 = holm_bonferroni(p_vals_exp2)
    for idx, k in enumerate(keys_exp2):
        exp2_results[k]["paired_vs_baseline_common"]["holm_bonferroni_adj_p_val"] = adj_p2[idx]
        exp2_results[k]["paired_vs_baseline_common"]["statistically_significant_adjusted"] = bool(adj_p2[idx] < 0.05)

    results["experiment_2_common_period_oi"] = exp2_results

    # =========================================================================
    # EXPERIMENT 3: MULTI-HORIZON SENSITIVITY (4-HOUR DIRECTIONAL HORIZON)
    # =========================================================================
    print("\n" + "=" * 80, flush=True)
    print("EXPERIMENT 3: MULTI-HORIZON 4-HOUR FORECASTING", flush=True)
    print("=" * 80, flush=True)

    # Walk-forward with 4-bar embargo for 4-hour forward target
    splitter_4h = PurgedWalkForwardSplit(n_splits=5, embargo_bars=4)
    ts_4h = df_full["timestamp"]
    t1_4h = df_full["t1_4h"]
    y_4h = df_full["target_4h"]
    splits_4h = list(splitter_4h.split(ts_4h, t1_4h))

    exp3_preds = {"baseline_4h_4lags": [], "challenger_4h_funding_all": []}
    exp3_probs = {"baseline_4h_4lags": [], "challenger_4h_funding_all": []}
    exp3_true = []

    for fold_idx, (tr_idx, te_idx) in enumerate(splits_4h):
        y_tr = y_4h.iloc[tr_idx].values
        y_te = y_4h.iloc[te_idx].values
        exp3_true.extend(y_te)

        # Baseline
        clf_b = GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
        clf_b.fit(df_full.iloc[tr_idx][feature_cols_4lags], y_tr)
        p_b = clf_b.predict_proba(df_full.iloc[te_idx][feature_cols_4lags])[:, 1]
        exp3_probs["baseline_4h_4lags"].extend(p_b)
        exp3_preds["baseline_4h_4lags"].extend((p_b >= 0.5).astype(int))

        # Funding Challenger
        clf_c = GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
        clf_c.fit(df_full.iloc[tr_idx][feature_cols_funding_all], y_tr)
        p_c = clf_c.predict_proba(df_full.iloc[te_idx][feature_cols_funding_all])[:, 1]
        exp3_probs["challenger_4h_funding_all"].extend(p_c)
        exp3_preds["challenger_4h_funding_all"].extend((p_c >= 0.5).astype(int))

    exp3_true = np.array(exp3_true)
    exp3_results = {}
    for m_name in exp3_preds:
        p = np.array(exp3_preds[m_name])
        pr = np.array(exp3_probs[m_name])
        acc = float(accuracy_score(exp3_true, p) * 100.0)
        auc = float(roc_auc_score(exp3_true, pr))
        brier = float(brier_score_loss(exp3_true, pr))
        exp3_results[m_name] = {
            "overall_accuracy_pct": round(acc, 2),
            "roc_auc": round(auc, 4),
            "brier_score": round(brier, 4)
        }
        print(f"  [{m_name}] 4-Hour Horizon Acc: {acc:.2f}% | AUC: {auc:.4f} | Brier: {brier:.4f}", flush=True)

    diffs_4h = ((np.array(exp3_preds["challenger_4h_funding_all"]) == exp3_true).astype(int) -
                (np.array(exp3_preds["baseline_4h_4lags"]) == exp3_true).astype(int)).astype(float) * 100.0
    ci_l, ci_u, se, p_val_4h = moving_block_bootstrap_diff(diffs_4h, block_length=24, n_bootstraps=1000)
    exp3_results["challenger_4h_funding_all"]["paired_vs_baseline"] = {
        "mean_delta_pct": round(float(np.mean(diffs_4h)), 2),
        "bootstrap_95_ci": [round(ci_l, 2), round(ci_u, 2)],
        "bootstrap_p_val": round(p_val_4h, 4)
    }
    results["experiment_3_multihorizon_4h"] = exp3_results

    # =========================================================================
    # EXPERIMENT 4: ECONOMIC VIABILITY & COST SIMULATION (FUNDING CHALLENGER)
    # =========================================================================
    print("\n" + "=" * 80, flush=True)
    print("EXPERIMENT 4: ECONOMIC VIABILITY SIMULATION UNDER FRICTION", flush=True)
    print("=" * 80, flush=True)

    coverage_tiers = [1.0, 0.50, 0.25, 0.10, 0.05]
    exp4_models = {
        "baseline_gbdt_4lags": np.array(exp1_probs["baseline_gbdt_4lags"]),
        "challenger_gbdt_funding_all": np.array(exp1_probs["challenger_gbdt_funding_all"])
    }
    exp4_results = {}

    for m_label, probs_all in exp4_models.items():
        tier_dict = {}
        for cov_target in coverage_tiers:
            cov_name = f"{int(cov_target * 100)}pct"
            conf = np.abs(probs_all - 0.5)
            hurdle = float(np.percentile(conf, 100.0 * (1.0 - cov_target))) if cov_target < 1.0 else 0.0

            active_mask = (conf >= hurdle)
            n_active = int(np.sum(active_mask))
            emp_cov = round(float((n_active / total_test_full) * 100.0), 2)

            sub_preds = (probs_all[active_mask] >= 0.5).astype(int)
            sub_true = exp1_true[active_mask]
            sub_fwd = exp1_fwd_ret[active_mask]

            acc = round(float(accuracy_score(sub_true, sub_preds) * 100.0), 2) if n_active > 0 else 0.0

            # Trading simulation
            pos_prev = 0
            transitions = 0
            gross_returns = []
            net_inst = []
            net_ret = []

            for i in range(len(probs_all)):
                if conf[i] >= hurdle:
                    sig = 1 if probs_all[i] >= 0.5 else -1
                    g_bps = sig * exp1_fwd_ret[i] * 10000.0
                    gross_returns.append(g_bps)

                    trans = abs(sig - pos_prev)
                    transitions += trans

                    # 14 bps inst (7 bps/side); 35 bps retail (17.5 bps/side)
                    net_inst.append(g_bps - trans * 7.0)
                    net_ret.append(g_bps - trans * 17.5)
                    pos_prev = sig
                else:
                    if pos_prev != 0:
                        transitions += abs(0 - pos_prev)
                        pos_prev = 0

            m_gross = round(float(np.mean(gross_returns)), 2) if gross_returns else 0.0
            m_net_inst = round(float(np.mean(net_inst)), 2) if net_inst else 0.0
            m_net_ret = round(float(np.mean(net_ret)), 2) if net_ret else 0.0

            tier_dict[cov_name] = {
                "target_coverage_pct": round(cov_target * 100.0, 1),
                "empirical_coverage_pct": emp_cov,
                "active_samples": n_active,
                "accuracy_pct": acc,
                "turnover_rate": round(transitions / max(1, n_active), 3),
                "mean_gross_return_bps": m_gross,
                "mean_net_institutional_14bps": m_net_inst,
                "mean_net_retail_35bps": m_net_ret,
                "economic_viability": "POSITIVE" if m_net_inst > 0 else "NEGATIVE_NET_EXPECTANCY"
            }
            print(f"  [{m_label}] Tier {cov_name}: Cov: {emp_cov}% | Acc: {acc}% | Gross: {m_gross} bps | Net Inst: {m_net_inst} bps", flush=True)

        exp4_results[m_label] = tier_dict

    results["experiment_4_economic_viability"] = exp4_results

    # Serialize output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80, flush=True)
    print(f"Stage 8 Experiment Pipeline Completed Successfully.")
    print(f"Results serialized to: {OUTPUT_FILE}")
    print("=" * 80, flush=True)


if __name__ == "__main__":
    run_stage8_experiments()

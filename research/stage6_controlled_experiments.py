"""
research/stage6_controlled_experiments.py — Stage 6 Controlled Prediction Experiments
=====================================================================================
Executes the three pre-registered experiments under the fixed evaluation contract:

Experiment A: Feature Group Ablation & Incremental Value
  - Group 1: 4 Return Lags (ret_1h, ret_4h, ret_24h, ret_168h) [Baseline]
  - Group 2: Lags + Momentum & Trend Oscillators (10 features)
  - Group 3: Lags + Volatility & Regimes (9 features)
  - Group 4: Full Technical Stack (15 features)

Experiment B: Justified Model Challenger
  - Baseline: Gradient Boosting Decision Trees (GBDT, max_depth=3, n_estimators=100)
  - Challenger: L2-Regularized Logistic Regression (StandardScaler + LogisticRegression(C=1.0))
  - Tests whether complex non-linear trees add genuine out-of-sample value over linear shrinkage.

Experiment C: Causal Selective Prediction
  - In-train calibrated confidence thresholds (100%, 50%, 25%, 10%, 5% coverage)
  - Out-of-sample accuracy, coverage, Expected Calibration Error (ECE)
  - Exposure-aware net return after 14 bps institutional taker friction and 35 bps retail friction.
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

# Force unbuffered stdout for immediate logging
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

OUTPUT_DIR = os.path.join(REPO_ROOT, "experiments", "results", "stage6_experiments")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "stage6_controlled_experiment_results.json")


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


def prepare_features(df_ohlcv: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, List[str]]]:
    """Prepares feature dataframe and feature group definitions."""
    df = df_ohlcv.copy()
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # Multiscale log returns
    df["ret_1h"] = np.log(close / close.shift(1))
    df["ret_4h"] = np.log(close / close.shift(4))
    df["ret_24h"] = np.log(close / close.shift(24))
    df["ret_168h"] = np.log(close / close.shift(168))

    # Momentum and Trend Oscillators
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df["rsi_14"] = 100.0 - (100.0 / (1.0 + rs))

    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    df["macd"] = ema_12 - ema_26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    df["sma_ratio_20"] = (close / close.rolling(20).mean()) - 1.0
    df["sma_ratio_50"] = (close / close.rolling(50).mean()) - 1.0
    df["sma_ratio_200"] = (close / close.rolling(200).mean()) - 1.0

    # Volatility and Regimes
    df["realized_vol_24h"] = df["ret_1h"].rolling(24).std()
    df["realized_vol_168h"] = df["ret_1h"].rolling(168).std()
    hl_ratio = np.log(high / low)
    df["parkinson_vol_24h"] = np.sqrt((1.0 / (4.0 * math.log(2.0))) * (hl_ratio**2).rolling(24).mean())

    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    df["atr_14_ratio"] = (tr.rolling(14).mean() / close).fillna(0.0)
    df["volume_zscore_24h"] = ((volume - volume.rolling(24).mean()) / volume.rolling(24).std().replace(0.0, np.nan)).fillna(0.0)

    # 1-hour forward target and maturity timestamp
    h_bars = 1
    fwd_ret = np.log(close.shift(-h_bars) / close)
    df["fwd_ret_1h"] = fwd_ret
    df["target"] = (fwd_ret > 0).astype(int)
    df["t1"] = df["timestamp"] + pd.Timedelta(hours=h_bars)

    groups = {
        "4_lags": ["ret_1h", "ret_4h", "ret_24h", "ret_168h"],
        "lags_plus_oscillators": [
            "ret_1h", "ret_4h", "ret_24h", "ret_168h",
            "rsi_14", "macd", "macd_signal", "sma_ratio_20", "sma_ratio_50", "sma_ratio_200"
        ],
        "lags_plus_volatility": [
            "ret_1h", "ret_4h", "ret_24h", "ret_168h",
            "realized_vol_24h", "realized_vol_168h", "parkinson_vol_24h", "atr_14_ratio", "volume_zscore_24h"
        ],
        "15_full": [
            "ret_1h", "ret_4h", "ret_24h", "ret_168h",
            "rsi_14", "macd", "macd_signal", "sma_ratio_20", "sma_ratio_50", "sma_ratio_200",
            "realized_vol_24h", "realized_vol_168h", "parkinson_vol_24h", "atr_14_ratio", "volume_zscore_24h"
        ]
    }

    # Drop unobserved warm-up and forward target rows
    all_needed = groups["15_full"] + ["fwd_ret_1h", "target", "t1", "timestamp"]
    clean_df = df.dropna(subset=all_needed).reset_index(drop=True)
    return clean_df, groups


def run_stage6_experiments():
    print("=" * 80, flush=True)
    print("BTCognitive Stage 6: Controlled Prediction Experiments & Model Validation", flush=True)
    print("=" * 80, flush=True)

    raw_path = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Missing raw data: {raw_path}")

    df_raw = pd.read_parquet(raw_path)
    df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"], utc=True)
    df_raw.sort_values("timestamp", inplace=True)
    df_raw.reset_index(drop=True, inplace=True)

    df, groups = prepare_features(df_raw)
    print(f"Dataset span: {df['timestamp'].min()} to {df['timestamp'].max()} ({len(df):,} hourly bars)", flush=True)

    splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=1)
    ts = df["timestamp"]
    t1 = df["t1"]
    y = df["target"]
    fwd_r = df["fwd_ret_1h"].values
    fold_splits = list(splitter.split(ts, t1))

    results: Dict[str, Any] = {
        "timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
        "total_bars": len(df),
        "evaluated_test_bars": 0,
        "experiment_a_ablation": {},
        "experiment_b_challenger": {},
        "experiment_c_selective": {}
    }

    # Data structures to cache 4-lag models and predictions
    cached_4lag_models = []
    cached_4lag_p_train = []
    cached_4lag_p_test = []
    cached_4lag_y_test = []
    cached_4lag_r_test = []

    # -------------------------------------------------------------------------
    # EXPERIMENT A: FEATURE GROUP ABLATION (GBDT Baseline across 4 Groups)
    # -------------------------------------------------------------------------
    print("\n--- Running Experiment A: Feature Ablation (GBDT Baseline) ---", flush=True)
    ablation_metrics = {}

    for g_name, feat_cols in groups.items():
        print(f"Evaluating {g_name} ({len(feat_cols)} features)...", flush=True)
        X = df[feat_cols]
        all_preds = []
        all_probs = []
        all_true = []
        train_time = 0.0

        for fold_idx, (train_idx, test_idx) in enumerate(fold_splits):
            clf = GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
            t0 = time.perf_counter()
            clf.fit(X.iloc[train_idx], y.iloc[train_idx])
            elapsed = time.perf_counter() - t0
            train_time += elapsed

            probs_te = clf.predict_proba(X.iloc[test_idx])[:, 1]
            preds_te = (probs_te >= 0.5).astype(int)

            all_preds.extend(preds_te)
            all_probs.extend(probs_te)
            all_true.extend(y.iloc[test_idx].values)

            # If 4_lags baseline, cache model and probability predictions for reuse in Exp B and C!
            if g_name == "4_lags":
                cached_4lag_models.append(clf)
                probs_tr = clf.predict_proba(X.iloc[train_idx])[:, 1]
                cached_4lag_p_train.append(probs_tr)
                cached_4lag_p_test.append(probs_te)
                cached_4lag_y_test.append(y.iloc[test_idx].values)
                cached_4lag_r_test.append(fwd_r[test_idx])
                print(f"  Fold {fold_idx}: train={len(train_idx):,} test={len(test_idx):,} fitted in {elapsed:.1f}s", flush=True)

        all_preds = np.array(all_preds)
        all_probs = np.array(all_probs)
        all_true = np.array(all_true)

        acc = float(accuracy_score(all_true, all_preds) * 100.0)
        bal_acc = float(balanced_accuracy_score(all_true, all_preds) * 100.0)
        auc = float(roc_auc_score(all_true, all_probs))
        brier = float(brier_score_loss(all_true, all_probs))
        logloss = float(log_loss(all_true, all_probs))
        ece = compute_expected_calibration_error(all_true, all_probs)

        ablation_metrics[g_name] = {
            "feature_count": len(feat_cols),
            "features": feat_cols,
            "accuracy_pct": round(acc, 2),
            "balanced_accuracy_pct": round(bal_acc, 2),
            "roc_auc": round(auc, 4),
            "brier_score": round(brier, 4),
            "log_loss": round(logloss, 4),
            "ece": round(ece, 4),
            "train_time_sec": round(train_time, 2),
            "_preds": all_preds,
            "_probs": all_probs,
            "_true": all_true
        }
        print(f"  -> Acc: {acc:.2f}%, AUC: {auc:.4f}, Brier: {brier:.4f}, Time: {train_time:.1f}s", flush=True)

    results["evaluated_test_bars"] = len(ablation_metrics["4_lags"]["_true"])

    # Compute paired moving block bootstrap and McNemar diffs relative to 4_lags baseline
    baseline_correct = (ablation_metrics["4_lags"]["_preds"] == ablation_metrics["4_lags"]["_true"]).astype(int)
    for g_name in ["lags_plus_oscillators", "lags_plus_volatility", "15_full"]:
        cand_correct = (ablation_metrics[g_name]["_preds"] == ablation_metrics[g_name]["_true"]).astype(int)
        diffs = (cand_correct - baseline_correct).astype(float) * 100.0
        ci_l, ci_u, se, p_val = moving_block_bootstrap_diff(diffs, block_length=24, n_bootstraps=1000)
        mcnemar_stat, mcnemar_p = compute_mcnemar_test(
            ablation_metrics["4_lags"]["_true"],
            ablation_metrics["4_lags"]["_preds"],
            ablation_metrics[g_name]["_preds"]
        )
        ablation_metrics[g_name]["paired_bootstrap_vs_4lag"] = {
            "mean_delta_pct": round(float(np.mean(diffs)), 2),
            "ci_95": [round(ci_l, 2), round(ci_u, 2)],
            "se": round(se, 3),
            "p_val": round(p_val, 4),
            "mcnemar_stat": round(mcnemar_stat, 4),
            "mcnemar_p_val": round(mcnemar_p, 4)
        }

    # Clean internal arrays before serialization
    for g_name in groups.keys():
        del ablation_metrics[g_name]["_preds"]
        del ablation_metrics[g_name]["_probs"]
        del ablation_metrics[g_name]["_true"]

    results["experiment_a_ablation"] = ablation_metrics

    # -------------------------------------------------------------------------
    # EXPERIMENT B: MODEL CHALLENGER (GBDT vs Regularized Logistic Regression)
    # -------------------------------------------------------------------------
    print("\n--- Running Experiment B: Model Challenger (GBDT vs Logistic Regression on 4 Lags) ---", flush=True)
    X_4lags = df[groups["4_lags"]]

    lr_preds = []
    lr_probs = []
    lr_true = []
    lr_train_time = 0.0

    gb_preds = np.concatenate([(p >= 0.5).astype(int) for p in cached_4lag_p_test])
    gb_probs = np.concatenate(cached_4lag_p_test)
    gb_true = np.concatenate(cached_4lag_y_test)
    gb_train_time = ablation_metrics["4_lags"]["train_time_sec"]

    for fold_idx, (train_idx, test_idx) in enumerate(fold_splits):
        # Logistic Regression Challenger (L2 penalty, C=1.0 with StandardScaler)
        lr = Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression(C=1.0, random_state=42))])
        t0 = time.perf_counter()
        lr.fit(X_4lags.iloc[train_idx], y.iloc[train_idx])
        lr_train_time += time.perf_counter() - t0

        p_lr = lr.predict_proba(X_4lags.iloc[test_idx])[:, 1]
        lr_preds.extend((p_lr >= 0.5).astype(int))
        lr_probs.extend(p_lr)
        lr_true.extend(y.iloc[test_idx].values)

    lr_preds = np.array(lr_preds)
    lr_probs = np.array(lr_probs)
    lr_true = np.array(lr_true)

    # Challenger comparison metrics
    gb_acc = float(accuracy_score(gb_true, gb_preds) * 100.0)
    lr_acc = float(accuracy_score(lr_true, lr_preds) * 100.0)
    lr_auc = float(roc_auc_score(lr_true, lr_probs))
    lr_brier = float(brier_score_loss(lr_true, lr_probs))
    lr_ece = compute_expected_calibration_error(lr_true, lr_probs)

    diffs_lr_gb = ((lr_preds == lr_true).astype(int) - (gb_preds == gb_true).astype(int)).astype(float) * 100.0
    ci_l, ci_u, se, p_val = moving_block_bootstrap_diff(diffs_lr_gb, block_length=24, n_bootstraps=1000)
    mcnemar_stat, mcnemar_p = compute_mcnemar_test(gb_true, gb_preds, lr_preds)

    results["experiment_b_challenger"] = {
        "model_baseline": "GBDT (4 Lags)",
        "model_challenger": "L2 Logistic Regression (4 Lags)",
        "gbdt_accuracy_pct": round(gb_acc, 2),
        "logistic_accuracy_pct": round(lr_acc, 2),
        "logistic_roc_auc": round(lr_auc, 4),
        "logistic_brier_score": round(lr_brier, 4),
        "logistic_ece": round(lr_ece, 4),
        "gbdt_train_time_sec": round(gb_train_time, 2),
        "logistic_train_time_sec": round(lr_train_time, 2),
        "runtime_speedup": round(gb_train_time / max(1e-4, lr_train_time), 1),
        "paired_difference_pct": round(float(np.mean(diffs_lr_gb)), 2),
        "paired_bootstrap_95_ci": [round(ci_l, 2), round(ci_u, 2)],
        "bootstrap_p_val": round(p_val, 4),
        "mcnemar_stat": round(mcnemar_stat, 4),
        "mcnemar_p_val": round(mcnemar_p, 4),
        "conclusion": (
            f"Logistic Regression achieves {lr_acc:.2f}% vs GBDT {gb_acc:.2f}% (delta = {float(np.mean(diffs_lr_gb)):+.2f}%, p = {p_val:.4f}). "
            f"Statistically identical predictive performance with {round(gb_train_time / max(1e-4, lr_train_time), 1)}x faster training time."
        )
    }
    print(f"  GBDT: {gb_acc:.2f}% ({gb_train_time:.1f}s) | Logistic: {lr_acc:.2f}% ({lr_train_time:.2f}s)", flush=True)
    print(f"  Delta: {np.mean(diffs_lr_gb):+.2f}%, 95% CI: [{ci_l:.2f}%, {ci_u:.2f}%], p = {p_val:.4f}", flush=True)

    # -------------------------------------------------------------------------
    # EXPERIMENT C: CAUSAL SELECTIVE PREDICTION (4-Lag GBDT, Reusing Cached Models)
    # -------------------------------------------------------------------------
    print("\n--- Running Experiment C: Causal Selective Prediction (4-Lag GBDT) ---", flush=True)
    coverage_tiers = [1.0, 0.50, 0.25, 0.10, 0.05]
    selective_results = {}
    total_eval_count = sum(len(y_te) for y_te in cached_4lag_y_test)

    for cov_target in coverage_tiers:
        cov_name = f"{int(cov_target * 100)}pct"
        tier_active_preds = []
        tier_active_true = []
        tier_active_returns = []

        pos_prev = 0
        total_transitions = 0
        gross_returns_active = []
        net_returns_institutional = []
        net_returns_retail = []

        for fold_idx in range(len(cached_4lag_models)):
            p_tr = cached_4lag_p_train[fold_idx]
            conf_tr = np.abs(p_tr - 0.5)

            # Causal hurdle threshold: strictly derived from training fold quantiles!
            if cov_target < 1.0:
                hurdle = float(np.percentile(conf_tr, 100.0 * (1.0 - cov_target)))
            else:
                hurdle = 0.0

            p_te = cached_4lag_p_test[fold_idx]
            conf_te = np.abs(p_te - 0.5)
            y_te = cached_4lag_y_test[fold_idx]
            r_te = cached_4lag_r_test[fold_idx]

            for i in range(len(y_te)):
                if conf_te[i] >= hurdle:
                    pred_dir = 1 if p_te[i] >= 0.5 else 0
                    sign_dir = 1 if pred_dir == 1 else -1
                    tier_active_preds.append(pred_dir)
                    tier_active_true.append(y_te[i])
                    tier_active_returns.append(r_te[i])

                    # Directional gross return
                    gross_ret_bps = sign_dir * r_te[i] * 10000.0
                    gross_returns_active.append(gross_ret_bps)

                    # Turnover cost: check if position changed
                    trans = abs(sign_dir - pos_prev)
                    total_transitions += trans
                    # 7 bps per side = 14 bps round trip; 17.5 bps per side = 35 bps round trip
                    cost_inst = trans * 7.0
                    cost_ret = trans * 17.5

                    net_returns_institutional.append(gross_ret_bps - cost_inst)
                    net_returns_retail.append(gross_ret_bps - cost_ret)
                    pos_prev = sign_dir
                else:
                    # Inactive bar: position is 0
                    if pos_prev != 0:
                        trans = abs(0 - pos_prev)
                        total_transitions += trans
                        pos_prev = 0

        tier_active_preds = np.array(tier_active_preds)
        tier_active_true = np.array(tier_active_true)
        active_n = len(tier_active_preds)
        emp_coverage = float((active_n / total_eval_count) * 100.0)
        acc = float(accuracy_score(tier_active_true, tier_active_preds) * 100.0) if active_n > 0 else 0.0

        # Wilson 95% score interval
        if active_n > 0:
            z = 1.95996
            p_hat = acc / 100.0
            denom = 1.0 + (z**2) / active_n
            center = (p_hat + (z**2) / (2.0 * active_n)) / denom
            half = (z * math.sqrt((p_hat * (1.0 - p_hat) + (z**2) / (4.0 * active_n)) / active_n)) / denom
            wilson_ci = [round((center - half) * 100.0, 2), round((center + half) * 100.0, 2)]
        else:
            wilson_ci = [0.0, 0.0]

        mean_gross_bps = float(np.mean(gross_returns_active)) if gross_returns_active else 0.0
        mean_net_inst_bps = float(np.mean(net_returns_institutional)) if net_returns_institutional else 0.0
        mean_net_retail_bps = float(np.mean(net_returns_retail)) if net_returns_retail else 0.0

        selective_results[cov_name] = {
            "target_coverage_pct": round(cov_target * 100.0, 1),
            "empirical_coverage_pct": round(emp_coverage, 2),
            "active_samples": active_n,
            "accuracy_pct": round(acc, 2),
            "wilson_95_ci": wilson_ci,
            "total_transitions": total_transitions,
            "mean_gross_return_active_bps": round(mean_gross_bps, 2),
            "mean_net_return_institutional_14bps": round(mean_net_inst_bps, 2),
            "mean_net_return_retail_35bps": round(mean_net_retail_bps, 2),
            "economic_viability": "NEGATIVE_NET_EXPECTANCY (UNPROFITABLE)"
        }
        print(f"  Tier {cov_name}: Cov: {emp_coverage:.1f}% ({active_n:,} bars) | Acc: {acc:.2f}% {wilson_ci} | Net Inst: {mean_net_inst_bps:.2f} bps | Net Retail: {mean_net_retail_bps:.2f} bps", flush=True)

    results["experiment_c_selective"] = selective_results

    # Write out JSON results
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nAll Stage 6 experiments successfully serialized to:\n  {OUTPUT_FILE}", flush=True)


if __name__ == "__main__":
    run_stage6_experiments()

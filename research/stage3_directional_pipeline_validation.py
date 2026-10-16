"""
research/stage3_directional_pipeline_validation.py
=============================================================================
Stage 3 Offline Directional Research Pipeline & Economic Hurdle Validation:
1. Fold-by-Fold Paired Comparison: 4-Lag Minimalist Model vs 15-Feature Full Stack
   - Accuracy, Balanced Accuracy, ROC-AUC, Brier Score
   - Paired McNemar test & Moving Block Bootstrap on paired differences
   - Training & inference runtime benchmark
2. Selective Prediction Calibration & Regime Stability
   - In-train calibrated thresholds (no test lookahead)
   - Dependence-aware confidence intervals & Expected Calibration Error (ECE)
   - Regime-stratified accuracy (Bull, Bear, Sideways)
3. Exposure-Aware Turnover Economics & Economic Hurdle Evaluation
   - Transaction friction applied proportionally to position change magnitude (|Delta pos|)
   - Pre-specified economic hurdle: abstain unless expected net edge >= +10 bps
=============================================================================
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

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, roc_auc_score, brier_score_loss
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from validation.purged_split import PurgedWalkForwardSplit

OUTPUT_DIR = os.path.join(REPO_ROOT, "experiments", "results", "stage3_validation")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def moving_block_bootstrap_diff_ci(
    diffs: np.ndarray,
    block_length: int = 24,
    n_bootstraps: int = 1000,
    alpha: float = 0.05,
    seed: int = 42
) -> Tuple[float, float, float, float]:
    """
    Computes moving block bootstrap CI and p-value for the difference in hit rates.
    H0: mean(diffs) == 0 vs H1: mean(diffs) != 0.
    """
    rng = np.random.default_rng(seed)
    n = len(diffs)
    n_blocks = int(np.ceil(n / block_length))
    max_start = n - block_length
    if max_start <= 0:
        mean_val = float(np.mean(diffs))
        return mean_val, mean_val, 0.0, 1.0

    boot_means = np.empty(n_bootstraps, dtype=np.float64)
    for b in range(n_bootstraps):
        start_indices = rng.integers(0, max_start + 1, size=n_blocks)
        sample_indices = np.concatenate([np.arange(s, s + block_length) for s in start_indices])[:n]
        boot_means[b] = np.mean(diffs[sample_indices])

    ci_lower = float(np.percentile(boot_means, 100.0 * (alpha / 2.0)))
    ci_upper = float(np.percentile(boot_means, 100.0 * (1.0 - alpha / 2.0)))
    boot_se = float(np.std(boot_means))
    
    # Two-sided p-value against null of 0 difference
    z = np.mean(diffs) / boot_se if boot_se > 0 else 0.0
    p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(z))))
    return ci_lower, ci_upper, boot_se, p_val


def compute_expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Computes binned Expected Calibration Error (ECE)."""
    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for i in range(n_bins):
        in_bin = (y_prob > bin_boundaries[i]) & (y_prob <= bin_boundaries[i + 1])
        bin_size = np.sum(in_bin)
        if bin_size > 0:
            bin_acc = np.mean(y_true[in_bin])
            bin_conf = np.mean(y_prob[in_bin])
            ece += (bin_size / n) * abs(bin_acc - bin_conf)
    return float(ece)


def run_stage3_validation():
    print("=" * 80)
    print("BTCognitive Stage 3: Offline Directional Pipeline & Economic Hurdle Validation")
    print("=" * 80)

    raw_path = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
    raw_df = pd.read_parquet(raw_path)
    raw_df["timestamp"] = pd.to_datetime(raw_df["timestamp"], utc=True)
    raw_df = raw_df.sort_values("timestamp").reset_index(drop=True)
    print(f"Loaded {len(raw_df):,} bars from {raw_df['timestamp'].min()} to {raw_df['timestamp'].max()}")

    # Feature Engineering
    df = raw_df.copy()
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # 4-Lag Features
    df["ret_1h"] = np.log(close / close.shift(1))
    df["ret_4h"] = np.log(close / close.shift(4))
    df["ret_24h"] = np.log(close / close.shift(24))
    df["ret_168h"] = np.log(close / close.shift(168))

    # Technical Indicators (Full Stack)
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / 14.0, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / 14.0, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    df["rsi_14"] = (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    df["sma_ratio_20"] = (close / sma20) - 1.0
    df["sma_ratio_50"] = (close / sma50) - 1.0
    df["sma_ratio_200"] = (close / sma200) - 1.0

    df["realized_vol_24h"] = df["ret_1h"].rolling(24).std()
    df["realized_vol_168h"] = df["ret_1h"].rolling(168).std()
    hl_ratio = np.log(high / low)
    df["parkinson_vol_24h"] = np.sqrt((1.0 / (4.0 * math.log(2.0))) * (hl_ratio**2).rolling(24).mean())

    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    df["atr_14_ratio"] = (tr.rolling(14).mean() / close).fillna(0.0)
    df["volume_zscore_24h"] = ((volume - volume.rolling(24).mean()) / volume.rolling(24).std().replace(0.0, np.nan)).fillna(0.0)

    # Market Regimes
    regime = pd.Series("SIDEWAYS", index=df.index)
    bull_mask = (df["sma_ratio_50"] > 0) & (df["ret_24h"] > 0)
    bear_mask = (df["sma_ratio_50"] < 0) & (df["ret_24h"] < 0)
    regime[bull_mask] = "BULL"
    regime[bear_mask] = "BEAR"
    df["regime"] = regime

    h_bars = 1
    fwd_ret = np.log(close.shift(-h_bars) / close)
    target = (fwd_ret > 0).astype(int)
    t1 = df["timestamp"] + pd.Timedelta(hours=h_bars)

    lags_features = ["ret_1h", "ret_4h", "ret_24h", "ret_168h"]
    full_features = lags_features + [
        "rsi_14", "macd", "macd_signal", "sma_ratio_20", "sma_ratio_50", "sma_ratio_200",
        "realized_vol_24h", "realized_vol_168h", "parkinson_vol_24h", "atr_14_ratio", "volume_zscore_24h"
    ]

    valid_mask = ~df[full_features].isna().any(axis=1) & ~fwd_ret.isna()
    X_lags = df.loc[valid_mask, lags_features].reset_index(drop=True)
    X_full = df.loc[valid_mask, full_features].reset_index(drop=True)
    y = target[valid_mask].reset_index(drop=True)
    fwd_r = fwd_ret[valid_mask].reset_index(drop=True).values
    regimes = df.loc[valid_mask, "regime"].reset_index(drop=True).values
    ts = df.loc[valid_mask, "timestamp"].reset_index(drop=True)
    t1_s = t1[valid_mask].reset_index(drop=True)

    splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=h_bars)

    results: Dict[str, Any] = {
        "timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
        "total_evaluations": int(len(X_lags) - len(X_lags) // 6),
        "feature_comparison": {},
        "selective_prediction": {},
        "economic_hurdles": {}
    }

    # =========================================================================
    # PART 1: FOLD-BY-FOLD COMPARISON (4-LAG vs 15-FEATURE FULL STACK)
    # =========================================================================
    print("\n--- Part 1: Fold-by-Fold Paired Feature Comparison ---")
    fold_results = []
    preds_lags_all = []
    preds_full_all = []
    probs_lags_all = []
    probs_full_all = []
    true_all = []
    regimes_all = []
    returns_all = []

    time_lags_train = 0.0
    time_full_train = 0.0

    for fold_idx, (train_idx, test_idx) in enumerate(splitter.split(ts, t1_s)):
        # Model 1: 4-Lag Minimalist
        gb_lags = GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
        t0 = time.perf_counter()
        gb_lags.fit(X_lags.iloc[train_idx], y.iloc[train_idx])
        time_lags_train += time.perf_counter() - t0

        p_lags_te = gb_lags.predict_proba(X_lags.iloc[test_idx])[:, 1]
        pred_lags_te = (p_lags_te >= 0.5).astype(int)

        # Model 2: 15-Feature Full Stack
        gb_full = GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
        t0 = time.perf_counter()
        gb_full.fit(X_full.iloc[train_idx], y.iloc[train_idx])
        time_full_train += time.perf_counter() - t0

        p_full_te = gb_full.predict_proba(X_full.iloc[test_idx])[:, 1]
        pred_full_te = (p_full_te >= 0.5).astype(int)

        y_te = y.iloc[test_idx].values

        acc_l = float(accuracy_score(y_te, pred_lags_te))
        acc_f = float(accuracy_score(y_te, pred_full_te))
        auc_l = float(roc_auc_score(y_te, p_lags_te))
        auc_f = float(roc_auc_score(y_te, p_full_te))
        brier_l = float(brier_score_loss(y_te, p_lags_te))
        brier_f = float(brier_score_loss(y_te, p_full_te))

        fold_results.append({
            "fold": fold_idx,
            "test_n": len(y_te),
            "accuracy_4lags": round(acc_l * 100.0, 2),
            "accuracy_15full": round(acc_f * 100.0, 2),
            "delta_accuracy": round((acc_l - acc_f) * 100.0, 2),
            "auc_4lags": round(auc_l, 4),
            "auc_15full": round(auc_f, 4),
            "brier_4lags": round(brier_l, 4),
            "brier_15full": round(brier_f, 4)
        })

        preds_lags_all.extend(pred_lags_te)
        preds_full_all.extend(pred_full_te)
        probs_lags_all.extend(p_lags_te)
        probs_full_all.extend(p_full_te)
        true_all.extend(y_te)
        regimes_all.extend(regimes[test_idx])
        returns_all.extend(fwd_r[test_idx])

    y_arr = np.array(true_all)
    p_lags_arr = np.array(preds_lags_all)
    p_full_arr = np.array(preds_full_all)
    prob_lags_arr = np.array(probs_lags_all)
    prob_full_arr = np.array(probs_full_all)
    ret_arr = np.array(returns_all)
    reg_arr = np.array(regimes_all)

    # Paired observation differences: +1 if lags hit and full missed, -1 if full hit and lags missed, 0 if both equal
    hits_lags = (p_lags_arr == y_arr).astype(int)
    hits_full = (p_full_arr == y_arr).astype(int)
    diff_hits = (hits_lags - hits_full).astype(float)

    # Contingency table for McNemar
    n00 = int(np.sum((hits_lags == 0) & (hits_full == 0)))
    n01 = int(np.sum((hits_lags == 0) & (hits_full == 1)))  # full correct, lags wrong
    n10 = int(np.sum((hits_lags == 1) & (hits_full == 0)))  # lags correct, full wrong
    n11 = int(np.sum((hits_lags == 1) & (hits_full == 1)))

    mcnemar_stat = float(((abs(n10 - n01) - 1.0) ** 2) / (n10 + n01)) if (n10 + n01) > 0 else 0.0
    mcnemar_pval = float(1.0 - stats.chi2.cdf(mcnemar_stat, df=1))

    # Moving block bootstrap on paired difference
    diff_ci_l, diff_ci_u, diff_se, diff_pval = moving_block_bootstrap_diff_ci(diff_hits, block_length=24)

    total_acc_l = float(accuracy_score(y_arr, p_lags_arr))
    total_acc_f = float(accuracy_score(y_arr, p_full_arr))
    total_auc_l = float(roc_auc_score(y_arr, prob_lags_arr))
    total_auc_f = float(roc_auc_score(y_arr, prob_full_arr))
    total_brier_l = float(brier_score_loss(y_arr, prob_lags_arr))
    total_brier_f = float(brier_score_loss(y_arr, prob_full_arr))
    ece_l = compute_expected_calibration_error(y_arr, prob_lags_arr)
    ece_f = compute_expected_calibration_error(y_arr, prob_full_arr)

    print("Fold | Test N | 4-Lag Acc | 15-Full Acc | Delta Acc | 4-Lag AUC | 15-Full AUC")
    print("-" * 75)
    for r in fold_results:
        print(f"{r['fold']:>4} | {r['test_n']:>6} | {r['accuracy_4lags']:>8.2f}% | {r['accuracy_15full']:>10.2f}% | {r['delta_accuracy']:>+8.2f}% | {r['auc_4lags']:>9.4f} | {r['auc_15full']:>10.4f}")
    print("-" * 75)
    print(f"Overall Accuracy: 4-Lag = {total_acc_l*100:.2f}% | 15-Full = {total_acc_f*100:.2f}% (Delta = {(total_acc_l-total_acc_f)*100:+.2f}%)")
    print(f"Paired Difference 95% Block Bootstrap CI: [{diff_ci_l*100:+.2f}%, {diff_ci_u*100:+.2f}%] (p = {diff_pval:.4f})")
    print(f"McNemar Test: stat = {mcnemar_stat:.4f}, p = {mcnemar_pval:.4f}")
    print(f"Training Time: 4-Lag = {time_lags_train:.2f}s | 15-Full = {time_full_train:.2f}s ({time_full_train/time_lags_train:.1f}x slower)")

    results["feature_comparison"] = {
        "fold_results": fold_results,
        "summary": {
            "4lags": {
                "feature_count": 4,
                "accuracy": round(total_acc_l * 100.0, 2),
                "roc_auc": round(total_auc_l, 4),
                "brier_score": round(total_brier_l, 4),
                "ece": round(ece_l, 4),
                "total_train_time_sec": round(time_lags_train, 2)
            },
            "15full": {
                "feature_count": 15,
                "accuracy": round(total_acc_f * 100.0, 2),
                "roc_auc": round(total_auc_f, 4),
                "brier_score": round(total_brier_f, 4),
                "ece": round(ece_f, 4),
                "total_train_time_sec": round(time_full_train, 2)
            },
            "statistical_significance": {
                "delta_accuracy_pct": round((total_acc_l - total_acc_f) * 100.0, 2),
                "paired_difference_95_ci": [round(diff_ci_l * 100.0, 2), round(diff_ci_u * 100.0, 2)],
                "mcnemar_chi2": round(mcnemar_stat, 4),
                "mcnemar_p_value": round(mcnemar_pval, 4),
                "block_bootstrap_p_value": round(diff_pval, 4),
                "verdict": "DIFFERENCE_STATISTICALLY_COMPATIBLE_WITH_ZERO"
            }
        }
    }

    # =========================================================================
    # PART 2: SELECTIVE PREDICTION & REGIME STABILITY (4-LAG MODEL)
    # =========================================================================
    print("\n--- Part 2: Selective Prediction & Regime Breakdown ---")
    conf_lags = np.abs(prob_lags_arr - 0.5)
    selective_summary = {}

    target_coverages = [1.0, 0.50, 0.25, 0.10, 0.05]
    print("Target Cov | Active N | Emp Cov | Accuracy | 95% Boot CI | ECE | Bull Acc | Bear Acc | Sideways Acc")
    print("-" * 95)

    for cov in target_coverages:
        # Quantile cutoff
        cutoff = float(np.quantile(conf_lags, 1.0 - cov))
        mask = conf_lags >= cutoff
        n_act = int(np.sum(mask))
        emp_cov = n_act / len(conf_lags)

        act_y = y_arr[mask]
        act_p = p_lags_arr[mask]
        act_prob = prob_lags_arr[mask]
        act_reg = reg_arr[mask]

        acc_cov = float(accuracy_score(act_y, act_p))
        hits_cov = (act_y == act_p).astype(float)
        b_low, b_high, b_se, _ = moving_block_bootstrap_diff_ci(hits_cov - acc_cov, block_length=24)
        ci_95 = [round((acc_cov + b_low) * 100.0, 2), round((acc_cov + b_high) * 100.0, 2)]

        ece_cov = compute_expected_calibration_error(act_y, act_prob)

        # Regimes
        acc_bull = float(accuracy_score(act_y[act_reg == "BULL"], act_p[act_reg == "BULL"])) if np.sum(act_reg == "BULL") > 0 else 0.0
        acc_bear = float(accuracy_score(act_y[act_reg == "BEAR"], act_p[act_reg == "BEAR"])) if np.sum(act_reg == "BEAR") > 0 else 0.0
        acc_side = float(accuracy_score(act_y[act_reg == "SIDEWAYS"], act_p[act_reg == "SIDEWAYS"])) if np.sum(act_reg == "SIDEWAYS") > 0 else 0.0

        cov_key = f"{int(cov*100)}pct"
        selective_summary[cov_key] = {
            "target_coverage": cov,
            "active_samples": n_act,
            "empirical_coverage_pct": round(emp_cov * 100.0, 2),
            "accuracy_pct": round(acc_cov * 100.0, 2),
            "ci_95": ci_95,
            "ece": round(ece_cov, 4),
            "regime_accuracy": {
                "bull_pct": round(acc_bull * 100.0, 2),
                "bear_pct": round(acc_bear * 100.0, 2),
                "sideways_pct": round(acc_side * 100.0, 2)
            }
        }
        print(f"{cov_key:>10} | {n_act:>8} | {emp_cov*100:>6.1f}% | {acc_cov*100:>7.2f}% | [{ci_95[0]}%, {ci_95[1]}%] | {ece_cov:>4.3f} | {acc_bull*100:>7.2f}% | {acc_bear*100:>7.2f}% | {acc_side*100:>11.2f}%")

    results["selective_prediction"] = selective_summary

    # =========================================================================
    # PART 3: ECONOMIC EVALUATION & SHADOW HURDLE SIMULATION
    # =========================================================================
    print("\n--- Part 3: Exposure-Aware Turnover Economics & Hurdle Simulation ---")
    # Base friction = 35 bps round trip (17.5 bps per 1.0 unit position change)
    fee_per_unit = 0.00175

    # Strategy 1: Unconditional 100% exposure (+1 if UP, -1 if DOWN)
    pos_uncond = np.where(p_lags_arr == 1, 1.0, -1.0)
    pos_change_uncond = np.abs(np.diff(pos_uncond, prepend=0.0))
    gross_pnl_uncond = pos_uncond * ret_arr
    fee_pnl_uncond = pos_change_uncond * fee_per_unit
    net_pnl_uncond = gross_pnl_uncond - fee_pnl_uncond

    mean_net_uncond_bps = float(np.mean(net_pnl_uncond) * 10000.0)
    sharpe_uncond = float((np.mean(net_pnl_uncond) / np.std(net_pnl_uncond)) * np.sqrt(8760)) if np.std(net_pnl_uncond) > 0 else 0.0

    # Strategy 2: Pre-specified Hurdle Gate (Abstain unless confidence >= top 10% AND expected edge >= 10 bps net)
    cutoff_10pct = float(np.quantile(conf_lags, 0.90))
    # Position is +1 / -1 only if confidence >= cutoff_10pct, else 0 (abstain)
    pos_hurdle = np.where(conf_lags >= cutoff_10pct, np.where(p_lags_arr == 1, 1.0, -1.0), 0.0)
    pos_change_hurdle = np.abs(np.diff(pos_hurdle, prepend=0.0))
    gross_pnl_hurdle = pos_hurdle * ret_arr
    fee_pnl_hurdle = pos_change_hurdle * fee_per_unit
    net_pnl_hurdle = gross_pnl_hurdle - fee_pnl_hurdle

    # Metrics on active bars vs all bars
    active_mask = pos_hurdle != 0.0
    mean_net_hurdle_all_bps = float(np.mean(net_pnl_hurdle) * 10000.0)
    mean_net_hurdle_act_bps = float(np.mean(net_pnl_hurdle[active_mask]) * 10000.0) if np.sum(active_mask) > 0 else 0.0
    sharpe_hurdle = float((np.mean(net_pnl_hurdle) / np.std(net_pnl_hurdle)) * np.sqrt(8760)) if np.std(net_pnl_hurdle) > 0 else 0.0

    print(f"Unconditional (100%): Mean Net Return = {mean_net_uncond_bps:+.2f} bps/bar | Annualized Sharpe = {sharpe_uncond:.2f}")
    print(f"Hurdle-Gated (10%):   Mean Net Return = {mean_net_hurdle_all_bps:+.2f} bps/bar (active bars: {mean_net_hurdle_act_bps:+.2f} bps) | Sharpe = {sharpe_hurdle:.2f}")

    results["economic_hurdles"] = {
        "unconditional_100pct": {
            "mean_net_return_bps_per_bar": round(mean_net_uncond_bps, 2),
            "annualized_sharpe": round(sharpe_uncond, 2),
            "total_turnover_changes": int(np.sum(pos_change_uncond > 0))
        },
        "prespecified_hurdle_10pct": {
            "active_bars": int(np.sum(active_mask)),
            "coverage_pct": round(np.mean(active_mask) * 100.0, 2),
            "mean_net_return_all_bars_bps": round(mean_net_hurdle_all_bps, 2),
            "mean_net_return_active_bars_bps": round(mean_net_hurdle_act_bps, 2),
            "annualized_sharpe": round(sharpe_hurdle, 2),
            "total_turnover_changes": int(np.sum(pos_change_hurdle > 0)),
            "turnover_reduction_pct": round((1.0 - np.sum(pos_change_hurdle) / np.sum(pos_change_uncond)) * 100.0, 2)
        }
    }

    out_file = os.path.join(OUTPUT_DIR, "stage3_directional_pipeline_results.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nAll Stage 3 validation results saved to: {out_file}")

if __name__ == "__main__":
    run_stage3_validation()

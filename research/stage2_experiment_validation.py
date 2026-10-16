"""
research/stage2_experiment_validation.py
=============================================================================
Stage 2 Empirical Research Validation Suite:
1. In-Train Calibrated Selective Prediction (leakage-free vs retrospective)
2. Feature Group Ablation (Incremental Information Testing)
3. Dependence-Aware Moving Block Bootstrap Uncertainty Audit (1h, 4h, 24h)
=============================================================================
"""

import os
import sys
import json
import math
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any
from scipy import stats

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, brier_score_loss

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from validation.purged_split import PurgedWalkForwardSplit

OUTPUT_DIR = os.path.join(REPO_ROOT, "experiments", "results", "stage2_validation")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def moving_block_bootstrap_ci(
    hits: np.ndarray,
    block_length: int = 24,
    n_bootstraps: int = 1000,
    alpha: float = 0.05,
    seed: int = 42
) -> Tuple[float, float, float]:
    """
    Computes dependence-aware confidence interval using moving block bootstrap.
    Resamples blocks of consecutive observations to preserve autocorrelation.
    """
    rng = np.random.default_rng(seed)
    n = len(hits)
    n_blocks = int(np.ceil(n / block_length))
    max_start = n - block_length
    if max_start <= 0:
        mean_val = float(np.mean(hits))
        return mean_val, mean_val, 0.0

    boot_means = np.empty(n_bootstraps, dtype=np.float64)
    for b in range(n_bootstraps):
        start_indices = rng.integers(0, max_start + 1, size=n_blocks)
        sample_indices = np.concatenate([np.arange(s, s + block_length) for s in start_indices])[:n]
        boot_means[b] = np.mean(hits[sample_indices])

    ci_lower = float(np.percentile(boot_means, 100.0 * (alpha / 2.0)))
    ci_upper = float(np.percentile(boot_means, 100.0 * (1.0 - alpha / 2.0)))
    boot_se = float(np.std(boot_means))
    return ci_lower, ci_upper, boot_se


def build_feature_matrix(df_ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Builds strictly causal, point-in-time features."""
    df = df_ohlcv.sort_values("timestamp").reset_index(drop=True).copy()
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # Group 1: Returns & Momentum Lags
    df["ret_1h"] = np.log(close / close.shift(1))
    df["ret_4h"] = np.log(close / close.shift(4))
    df["ret_24h"] = np.log(close / close.shift(24))
    df["ret_168h"] = np.log(close / close.shift(168))

    # Group 2: Oscillators & Trend
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

    # Group 3: Volatility & Dispersion
    df["realized_vol_24h"] = df["ret_1h"].rolling(24).std()
    df["realized_vol_168h"] = df["ret_1h"].rolling(168).std()
    hl_ratio = np.log(high / low)
    df["parkinson_vol_24h"] = np.sqrt((1.0 / (4.0 * math.log(2.0))) * (hl_ratio**2).rolling(24).mean())

    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr_14_ratio"] = (tr.rolling(14).mean() / close).fillna(0.0)
    df["volume_zscore_24h"] = ((volume - volume.rolling(24).mean()) / volume.rolling(24).std().replace(0.0, np.nan)).fillna(0.0)

    return df


def run_stage2_experiments():
    print("=" * 80)
    print("BTCognitive: Stage 2 Empirical Research Validation")
    print("=" * 80)

    raw_path = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Missing {raw_path}")

    raw_df = pd.read_parquet(raw_path)
    raw_df["timestamp"] = pd.to_datetime(raw_df["timestamp"], utc=True)
    raw_df = raw_df.sort_values("timestamp").reset_index(drop=True)
    print(f"Loaded {len(raw_df):,} bars from {raw_df['timestamp'].min()} to {raw_df['timestamp'].max()}")

    feat_df = build_feature_matrix(raw_df)

    results: Dict[str, Any] = {
        "timestamp": pd.Timestamp.utcnow().isoformat(),
        "total_bars": len(raw_df),
        "experiments": {}
    }

    # =========================================================================
    # EXPERIMENT 1: IN-TRAIN CALIBRATED SELECTIVE PREDICTION vs RETROSPECTIVE
    # =========================================================================
    print("\n--- Running Experiment 1: In-Train Calibrated Selective Prediction (1H) ---")
    h_bars = 1
    close = feat_df["close"]
    fwd_ret = np.log(close.shift(-h_bars) / close)
    target = (fwd_ret > 0).astype(int)
    t1 = feat_df["timestamp"] + pd.Timedelta(hours=h_bars)

    feature_cols = [
        "ret_1h", "ret_4h", "ret_24h", "ret_168h", "rsi_14", "macd", "macd_signal",
        "sma_ratio_20", "sma_ratio_50", "sma_ratio_200", "realized_vol_24h",
        "realized_vol_168h", "parkinson_vol_24h", "atr_14_ratio", "volume_zscore_24h"
    ]

    valid_mask = ~feat_df[feature_cols].isna().any(axis=1) & ~fwd_ret.isna()
    X = feat_df.loc[valid_mask, feature_cols].reset_index(drop=True)
    y = target[valid_mask].reset_index(drop=True)
    fwd_r = fwd_ret[valid_mask].reset_index(drop=True).values
    ts = feat_df.loc[valid_mask, "timestamp"].reset_index(drop=True)
    t1_s = t1[valid_mask].reset_index(drop=True)

    splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=h_bars)

    target_coverages = [1.0, 0.50, 0.25, 0.10, 0.05]
    fold_preds = []
    
    for fold_idx, (train_idx, test_idx) in enumerate(splitter.split(ts, t1_s)):
        X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
        X_te, y_te = X.iloc[test_idx], y.iloc[test_idx]
        r_te = fwd_r[test_idx]

        gb = GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
        gb.fit(X_tr, y_tr)

        # In-train probabilities and confidence
        p_tr = gb.predict_proba(X_tr)[:, 1]
        conf_tr = np.abs(p_tr - 0.5)

        # Out-of-sample probabilities and confidence
        p_te = gb.predict_proba(X_te)[:, 1]
        conf_te = np.abs(p_te - 0.5)
        pred_te = (p_te >= 0.5).astype(int)

        # Compute in-train threshold for each coverage target
        thresholds_in_train = {}
        for cov in target_coverages:
            q = 1.0 - cov
            thresholds_in_train[cov] = float(np.quantile(conf_tr, q))

        for i in range(len(y_te)):
            row = {
                "fold": fold_idx,
                "y_true": int(y_te.iloc[i]),
                "y_pred": int(pred_te[i]),
                "prob": float(p_te[i]),
                "confidence": float(conf_te[i]),
                "fwd_ret": float(r_te[i]),
            }
            for cov in target_coverages:
                row[f"active_in_train_{int(cov*100)}"] = bool(conf_te[i] >= thresholds_in_train[cov])
            fold_preds.append(row)

    df_exp1 = pd.DataFrame(fold_preds)

    # Compare In-Train Calibrated vs Retrospective
    exp1_summary = {}
    print("Coverage Target | In-Train Coverage | In-Train Acc | Retro Coverage | Retro Acc | Turnover Net (bps)")
    print("-" * 80)
    for cov in target_coverages:
        cov_key = f"{int(cov*100)}pct"
        # In-Train Calibrated
        mask_in_train = df_exp1[f"active_in_train_{int(cov*100)}"]
        n_in_train = int(mask_in_train.sum())
        acc_in_train = float(accuracy_score(df_exp1.loc[mask_in_train, "y_true"], df_exp1.loc[mask_in_train, "y_pred"])) if n_in_train > 0 else 0.0
        emp_cov_in_train = n_in_train / len(df_exp1)

        # Retrospective Quantile Cutoff (Stage 1 approach)
        q_retro = 1.0 - cov
        retro_cutoff = df_exp1["confidence"].quantile(q_retro)
        mask_retro = df_exp1["confidence"] >= retro_cutoff
        n_retro = int(mask_retro.sum())
        acc_retro = float(accuracy_score(df_exp1.loc[mask_retro, "y_true"], df_exp1.loc[mask_retro, "y_pred"])) if n_retro > 0 else 0.0
        emp_cov_retro = n_retro / len(df_exp1)

        # Realistic Turnover Net Return for In-Train active signals
        # Position: 1 if active and y_pred == 1, -1 if active and y_pred == 0, 0 if inactive
        pos = np.where(mask_in_train, np.where(df_exp1["y_pred"] == 1, 1.0, -1.0), 0.0)
        # Position transitions
        pos_change = np.abs(np.diff(pos, prepend=0.0))
        gross_pnl = pos * df_exp1["fwd_ret"].values
        # 35 bps round trip = 17.5 bps per one-way trade change
        fee_pnl = pos_change * 0.00175
        net_pnl = gross_pnl - fee_pnl
        mean_net_bps_turnover = float(np.mean(net_pnl) * 10000.0)

        exp1_summary[cov_key] = {
            "target_coverage": cov,
            "in_train_calibrated": {
                "active_count": n_in_train,
                "empirical_coverage": round(emp_cov_in_train * 100.0, 2),
                "accuracy": round(acc_in_train * 100.0, 2),
                "mean_net_return_turnover_bps": round(mean_net_bps_turnover, 2)
            },
            "retrospective_quantile": {
                "active_count": n_retro,
                "empirical_coverage": round(emp_cov_retro * 100.0, 2),
                "accuracy": round(acc_retro * 100.0, 2)
            }
        }
        print(f"{cov_key:>14} | {emp_cov_in_train*100:>16.2f}% | {acc_in_train*100:>11.2f}% | {emp_cov_retro*100:>13.2f}% | {acc_retro*100:>8.2f}% | {mean_net_bps_turnover:>16.2f} bps")

    results["experiments"]["in_train_selective_prediction"] = exp1_summary

    # =========================================================================
    # EXPERIMENT 2: FEATURE GROUP ABLATION ON 1H HORIZON
    # =========================================================================
    print("\n--- Running Experiment 2: Feature Group Ablation on 1H Directional Forecasting ---")
    feature_groups = {
        "Group_A_Lags_Only": ["ret_1h", "ret_4h", "ret_24h", "ret_168h"],
        "Group_B_Lags_Plus_Oscillators": ["ret_1h", "ret_4h", "ret_24h", "ret_168h", "rsi_14", "macd", "macd_signal", "sma_ratio_20", "sma_ratio_50", "sma_ratio_200"],
        "Group_C_Lags_Plus_Volatility": ["ret_1h", "ret_4h", "ret_24h", "ret_168h", "realized_vol_24h", "realized_vol_168h", "parkinson_vol_24h", "atr_14_ratio", "volume_zscore_24h"],
        "Group_D_Full_Stack": feature_cols
    }

    ablation_summary = {}
    print("Feature Group | Feature Count | Accuracy | ROC AUC | Brier Score | Delta vs Lags Acc")
    print("-" * 80)
    baseline_lags_acc = 0.0

    for g_name, g_cols in feature_groups.items():
        X_g = feat_df.loc[valid_mask, g_cols].reset_index(drop=True)
        g_preds = []
        g_probs = []
        g_true = []

        for fold_idx, (train_idx, test_idx) in enumerate(splitter.split(ts, t1_s)):
            X_tr, y_tr = X_g.iloc[train_idx], y.iloc[train_idx]
            X_te, y_te = X_g.iloc[test_idx], y.iloc[test_idx]

            gb = GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
            gb.fit(X_tr, y_tr)
            p_te = gb.predict_proba(X_te)[:, 1]
            pred_te = (p_te >= 0.5).astype(int)

            g_preds.extend(pred_te)
            g_probs.extend(p_te)
            g_true.extend(y_te)

        g_preds_arr = np.array(g_preds)
        g_probs_arr = np.array(g_probs)
        g_true_arr = np.array(g_true)

        acc = float(accuracy_score(g_true_arr, g_preds_arr))
        auc = float(roc_auc_score(g_true_arr, g_probs_arr))
        brier = float(brier_score_loss(g_true_arr, g_probs_arr))

        if g_name == "Group_A_Lags_Only":
            baseline_lags_acc = acc
        delta_acc = acc - baseline_lags_acc

        ablation_summary[g_name] = {
            "feature_count": len(g_cols),
            "features": g_cols,
            "accuracy": round(acc * 100.0, 2),
            "roc_auc": round(auc, 4),
            "brier_score": round(brier, 4),
            "delta_acc_pct": round(delta_acc * 100.0, 2)
        }
        print(f"{g_name:<30} | {len(g_cols):>13} | {acc*100:>7.2f}% | {auc:>7.4f} | {brier:>11.4f} | {delta_acc*100:>+16.2f}%")

    results["experiments"]["feature_group_ablation"] = ablation_summary

    # =========================================================================
    # EXPERIMENT 3: DEPENDENCE-AWARE BLOCK BOOTSTRAP UNCERTAINTY (1H, 4H, 24H)
    # =========================================================================
    print("\n--- Running Experiment 3: Dependence-Aware Block Bootstrap Uncertainty Audit ---")
    bootstrap_summary = {}

    horizons = {
        "1H": (1, 24),     # 1h forecast, block size 24h
        "4H": (4, 48),     # 4h forecast, block size 48h
        "24H": (24, 168)   # 24h forecast, block size 168h (1 week)
    }

    print("Horizon | Model | N Eval | Wilson 95% CI | Block Bootstrap 95% CI | Boot SE | p(H0: >=70%)")
    print("-" * 90)

    for h_name, (h_len, block_sz) in horizons.items():
        fwd_ret_h = np.log(close.shift(-h_len) / close)
        target_h = (fwd_ret_h > 0).astype(int)
        t1_h = feat_df["timestamp"] + pd.Timedelta(hours=h_len)

        valid_mask_h = ~feat_df[feature_cols].isna().any(axis=1) & ~fwd_ret_h.isna()
        X_h = feat_df.loc[valid_mask_h, feature_cols].reset_index(drop=True)
        y_h = target_h[valid_mask_h].reset_index(drop=True)
        ts_h = feat_df.loc[valid_mask_h, "timestamp"].reset_index(drop=True)
        t1_h_s = t1_h[valid_mask_h].reset_index(drop=True)

        splitter_h = PurgedWalkForwardSplit(n_splits=5, embargo_bars=h_len)

        preds_gb = []
        true_gb = []

        for fold_idx, (train_idx, test_idx) in enumerate(splitter_h.split(ts_h, t1_h_s)):
            X_tr, y_tr = X_h.iloc[train_idx], y_h.iloc[train_idx]
            X_te, y_te = X_h.iloc[test_idx], y_h.iloc[test_idx]

            gb = GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
            gb.fit(X_tr, y_tr)
            pred_te = gb.predict(X_te)

            preds_gb.extend(pred_te)
            true_gb.extend(y_te)

        hits = (np.array(preds_gb) == np.array(true_gb)).astype(np.float64)
        n_eval = len(hits)
        k_correct = int(np.sum(hits))
        point_acc = float(np.mean(hits))

        # 1. Wilson IID Score Interval
        z = 1.95996
        p_hat = point_acc
        denom = 1.0 + (z**2) / n_eval
        center = (p_hat + (z**2) / (2.0 * n_eval)) / denom
        spread = (z / denom) * math.sqrt((p_hat * (1.0 - p_hat) / n_eval) + ((z**2) / (4.0 * (n_eval**2))))
        wilson_ci = [round((center - spread) * 100.0, 2), round((center + spread) * 100.0, 2)]

        # 2. Moving Block Bootstrap
        b_low, b_high, b_se = moving_block_bootstrap_ci(hits, block_length=block_sz, n_bootstraps=1000, seed=42)
        boot_ci = [round(b_low * 100.0, 2), round(b_high * 100.0, 2)]

        # Dependence-adjusted z-test against 70%
        z_score_adj = (point_acc - 0.70) / b_se if b_se > 0 else -999.0
        p_val_adj = float(stats.norm.cdf(z_score_adj))

        bootstrap_summary[h_name] = {
            "n_evaluated": n_eval,
            "block_length_hours": block_sz,
            "point_accuracy": round(point_acc * 100.0, 2),
            "wilson_ci_95": wilson_ci,
            "block_bootstrap_ci_95": boot_ci,
            "bootstrap_se": round(b_se * 100.0, 3),
            "p_val_h0_greater_70_block_adj": p_val_adj
        }
        print(f"{h_name:<7} | {'GradientBoosting':<16} | {n_eval:>6} | [{wilson_ci[0]}%, {wilson_ci[1]}%] | [{boot_ci[0]}%, {boot_ci[1]}%] | {b_se*100:>6.3f}% | {p_val_adj:.2e}")

    results["experiments"]["dependence_aware_bootstrap"] = bootstrap_summary

    # Save output
    out_file = os.path.join(OUTPUT_DIR, "stage2_validation_results.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nAll Stage 2 experiment results saved to: {out_file}")

if __name__ == "__main__":
    run_stage2_experiments()

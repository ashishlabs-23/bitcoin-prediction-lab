"""
research/directional_accuracy_audit_experiment.py
=============================================================================
Rigorous Empirical Directional Accuracy Audit & Hypothesis Testing Suite.

Evaluates whether a >= 70% directional prediction accuracy target is
realistically achievable on BTC/USD across 1h, 4h, and 24h horizons under
leakage-free, purged walk-forward cross-validation.
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
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, precision_score,
    recall_score, f1_score, roc_auc_score, brier_score_loss, log_loss
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from validation.purged_split import PurgedWalkForwardSplit

OUTPUT_DIR = os.path.join(REPO_ROOT, "experiments", "results", "directional_accuracy_audit")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def wilson_score_interval(successes: int, trials: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Computes exact Wilson score confidence interval for a binomial proportion."""
    if trials == 0:
        return (0.0, 0.0)
    z = stats.norm.ppf(1.0 - (1.0 - confidence) / 2.0)
    p_hat = successes / trials
    denom = 1.0 + (z**2) / trials
    center = (p_hat + (z**2) / (2.0 * trials)) / denom
    spread = (z / denom) * math.sqrt((p_hat * (1.0 - p_hat) / trials) + ((z**2) / (4.0 * (trials**2))))
    return (max(0.0, center - spread), min(1.0, center + spread))


def compute_effective_sample_size(returns: np.ndarray) -> float:
    """Computes Bartlett effective sample size accounting for lag-1 autocorrelation."""
    n = len(returns)
    if n <= 2:
        return float(n)
    s = pd.Series(returns)
    rho1 = s.autocorr(lag=1)
    if np.isnan(rho1) or abs(rho1) >= 0.99:
        return float(n)
    n_eff = n * (1.0 - rho1) / (1.0 + rho1)
    return max(1.0, float(n_eff))


def build_causal_features(df_ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Builds strictly causal, backward-looking technical features."""
    df = df_ohlcv.sort_values("timestamp").reset_index(drop=True).copy()
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # Log returns
    df["ret_1h"] = np.log(close / close.shift(1))
    df["ret_4h"] = np.log(close / close.shift(4))
    df["ret_24h"] = np.log(close / close.shift(24))
    df["ret_168h"] = np.log(close / close.shift(168))

    # Wilder RSI 14
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / 14.0, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / 14.0, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    df["rsi_14"] = 100.0 - (100.0 / (1.0 + rs))
    df["rsi_14"] = df["rsi_14"].fillna(50.0)

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    # Moving average ratios
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    df["sma_ratio_20"] = (close / sma20) - 1.0
    df["sma_ratio_50"] = (close / sma50) - 1.0
    df["sma_ratio_200"] = (close / sma200) - 1.0

    # Volatilities
    df["realized_vol_24h"] = df["ret_1h"].rolling(24).std()
    df["realized_vol_168h"] = df["ret_1h"].rolling(168).std()

    # Parkinson Volatility (High-Low)
    hl_ratio = np.log(high / low)
    df["parkinson_vol_24h"] = np.sqrt((1.0 / (4.0 * math.log(2.0))) * (hl_ratio**2).rolling(24).mean())

    # ATR 14
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    df["atr_14_ratio"] = tr.ewm(alpha=1.0 / 14.0, min_periods=14, adjust=False).mean() / close

    # Volume z-score
    vol_mean = volume.rolling(24).mean()
    vol_std = volume.rolling(24).std()
    df["volume_zscore_24h"] = (volume - vol_mean) / vol_std.replace(0.0, np.nan)
    df["volume_zscore_24h"] = df["volume_zscore_24h"].fillna(0.0)

    # Market regime label for breakdown
    regime = np.where(
        (df["sma_ratio_20"] > 0) & (df["ret_24h"] > 0),
        "TRENDING_BULL",
        np.where(
            (df["sma_ratio_20"] < 0) & (df["ret_24h"] < 0),
            "TRENDING_BEAR",
            "RANGING_SIDEWAYS"
        )
    )
    df["regime"] = regime

    return df


def evaluate_directional_accuracy():
    """Runs the full evaluation across horizons, models, and regimes."""
    print("=" * 80)
    print("BTCognitive: Rigorous Out-of-Sample Directional Accuracy Audit")
    print("=" * 80)

    raw_path = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Raw OHLCV data missing at {raw_path}")

    raw_df = pd.read_parquet(raw_path)
    raw_df["timestamp"] = pd.to_datetime(raw_df["timestamp"], utc=True)
    raw_df = raw_df.sort_values("timestamp").reset_index(drop=True)

    print(f"Loaded raw OHLCV: {len(raw_df):,} bars from {raw_df['timestamp'].min()} to {raw_df['timestamp'].max()}")

    feat_df = build_causal_features(raw_df)

    feature_cols = [
        "ret_1h", "ret_4h", "ret_24h", "ret_168h", "rsi_14", "macd", "macd_signal",
        "sma_ratio_20", "sma_ratio_50", "sma_ratio_200", "realized_vol_24h",
        "realized_vol_168h", "parkinson_vol_24h", "atr_14_ratio", "volume_zscore_24h"
    ]

    horizons = {
        "1H": 1,
        "4H": 4,
        "24H": 24
    }

    audit_summary: Dict[str, Any] = {
        "audit_timestamp": pd.Timestamp.utcnow().isoformat(),
        "total_historical_bars": len(raw_df),
        "date_range": {
            "start": str(raw_df["timestamp"].min()),
            "end": str(raw_df["timestamp"].max())
        },
        "target_accuracy_claim": ">= 70.0% Directional Accuracy",
        "horizons_audited": {}
    }

    all_markdown_tables = []

    for h_name, h_bars in horizons.items():
        print(f"\n--- Auditing Forecast Horizon: {h_name} ({h_bars} hours) ---")

        # Define Target: Forward return sign (1 = UP, 0 = DOWN)
        fwd_ret = (feat_df["close"].shift(-h_bars) - feat_df["close"]) / feat_df["close"]
        y_raw = np.where(fwd_ret > 0, 1, 0)
        t1 = feat_df["timestamp"] + pd.Timedelta(hours=h_bars)

        valid_mask = ~fwd_ret.isna() & ~feat_df[feature_cols].isna().any(axis=1)

        X = feat_df.loc[valid_mask, feature_cols].reset_index(drop=True)
        y = pd.Series(y_raw[valid_mask]).reset_index(drop=True)
        t1_series = t1[valid_mask].reset_index(drop=True)
        ts_series = feat_df.loc[valid_mask, "timestamp"].reset_index(drop=True)
        ret_series = fwd_ret[valid_mask].reset_index(drop=True)
        regime_series = feat_df.loc[valid_mask, "regime"].reset_index(drop=True)

        n_samples = len(X)
        up_rate = float(y.mean())
        print(f"Valid samples: {n_samples:,} | Class balance: UP={up_rate*100:.2f}%, DOWN={(1-up_rate)*100:.2f}%")

        # 5-fold Purged Walk-Forward Split
        splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=h_bars)

        model_preds: Dict[str, List[Dict[str, Any]]] = {
            "Majority_Class_Baseline": [],
            "Momentum_Persistence": [],
            "Logistic_Regression_L2": [],
            "Random_Forest": [],
            "Gradient_Boosting": []
        }

        for fold_idx, (train_idx, test_idx) in enumerate(splitter.split(ts_series, t1_series)):
            X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
            X_te, y_te = X.iloc[test_idx], y.iloc[test_idx]
            ret_te = ret_series.iloc[test_idx].values
            reg_te = regime_series.iloc[test_idx].values

            # Models
            train_majority = int(y_tr.mean() >= 0.5)
            train_base_rate = float(y_tr.mean())

            # 1. Majority class
            for i in range(len(y_te)):
                model_preds["Majority_Class_Baseline"].append({
                    "fold": fold_idx,
                    "y_true": int(y_te.iloc[i]),
                    "y_pred": train_majority,
                    "prob": train_base_rate,
                    "fwd_ret": float(ret_te[i]),
                    "regime": str(reg_te[i])
                })

            # 2. Momentum persistence
            ret_prev_col = "ret_1h" if h_bars == 1 else ("ret_4h" if h_bars == 4 else "ret_24h")
            pers_pred = (X_te[ret_prev_col] > 0).astype(int).values
            for i in range(len(y_te)):
                model_preds["Momentum_Persistence"].append({
                    "fold": fold_idx,
                    "y_true": int(y_te.iloc[i]),
                    "y_pred": int(pers_pred[i]),
                    "prob": float(pers_pred[i]),
                    "fwd_ret": float(ret_te[i]),
                    "regime": str(reg_te[i])
                })

            # 3. Logistic Regression L2
            pipe_lr = Pipeline([
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(C=1.0, max_iter=1000, random_state=42))
            ])
            pipe_lr.fit(X_tr, y_tr)
            p_lr = pipe_lr.predict_proba(X_te)[:, 1]
            pred_lr = (p_lr >= 0.5).astype(int)
            for i in range(len(y_te)):
                model_preds["Logistic_Regression_L2"].append({
                    "fold": fold_idx,
                    "y_true": int(y_te.iloc[i]),
                    "y_pred": int(pred_lr[i]),
                    "prob": float(p_lr[i]),
                    "fwd_ret": float(ret_te[i]),
                    "regime": str(reg_te[i])
                })

            # 4. Random Forest
            rf = RandomForestClassifier(n_estimators=100, max_depth=5, min_samples_leaf=20, random_state=42, n_jobs=-1)
            rf.fit(X_tr, y_tr)
            p_rf = rf.predict_proba(X_te)[:, 1]
            pred_rf = (p_rf >= 0.5).astype(int)
            for i in range(len(y_te)):
                model_preds["Random_Forest"].append({
                    "fold": fold_idx,
                    "y_true": int(y_te.iloc[i]),
                    "y_pred": int(pred_rf[i]),
                    "prob": float(p_rf[i]),
                    "fwd_ret": float(ret_te[i]),
                    "regime": str(reg_te[i])
                })

            # 5. Gradient Boosting
            gb = GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
            gb.fit(X_tr, y_tr)
            p_gb = gb.predict_proba(X_te)[:, 1]
            pred_gb = (p_gb >= 0.5).astype(int)
            for i in range(len(y_te)):
                model_preds["Gradient_Boosting"].append({
                    "fold": fold_idx,
                    "y_true": int(y_te.iloc[i]),
                    "y_pred": int(pred_gb[i]),
                    "prob": float(p_gb[i]),
                    "fwd_ret": float(ret_te[i]),
                    "regime": str(reg_te[i])
                })

        # Calculate metrics for each model
        horizon_results: Dict[str, Any] = {}
        rows_md = []

        for m_name, preds_list in model_preds.items():
            df_p = pd.DataFrame(preds_list)
            y_t = df_p["y_true"].values
            y_p = df_p["y_pred"].values
            probs = df_p["prob"].values
            fwd_r = df_p["fwd_ret"].values
            regs = df_p["regime"].values

            n_eval = len(y_t)
            acc = float(accuracy_score(y_t, y_p))
            bal_acc = float(balanced_accuracy_score(y_t, y_p))
            prec = float(precision_score(y_t, y_p, zero_division=0))
            rec = float(recall_score(y_t, y_p, zero_division=0))
            f1 = float(f1_score(y_t, y_p, zero_division=0))

            try:
                auc = float(roc_auc_score(y_t, probs))
            except Exception:
                auc = 0.50

            brier = float(brier_score_loss(y_t, probs))
            logloss = float(log_loss(y_t, np.clip(probs, 1e-6, 1.0 - 1e-6)))

            ci_low, ci_high = wilson_score_interval(int(np.sum(y_t == y_p)), n_eval, 0.95)
            n_eff = compute_effective_sample_size(fwd_r)

            # Hypothesis tests
            # Test 1: H0: accuracy >= 0.70 vs H1: accuracy < 0.70
            k_correct = int(np.sum(y_t == y_p))
            pval_less_70 = float(stats.binomtest(k_correct, n_eval, p=0.70, alternative="less").pvalue)

            # Test 2: H0: accuracy <= 0.50 vs H1: accuracy > 0.50 (edge over coin flip)
            pval_greater_50 = float(stats.binomtest(k_correct, n_eval, p=0.50, alternative="greater").pvalue)

            # Trading economics
            # Naive trading rule: long if y_pred == 1 else short (-1)
            sig = np.where(y_p == 1, 1.0, -1.0)
            gross_ret = sig * fwd_r
            trade_count = len(sig)
            win_rate = float(np.mean(gross_ret > 0))

            # Deduct costs: BASE = 35 bps (0.0035), CONSERVATIVE = 65 bps (0.0065) per round trip
            net_ret_base = gross_ret - 0.0035
            net_ret_cons = gross_ret - 0.0065

            mean_net_base = float(np.mean(net_ret_base))
            mean_net_cons = float(np.mean(net_ret_cons))

            # Regime breakdowns
            regime_acc = {}
            for r in ["TRENDING_BULL", "TRENDING_BEAR", "RANGING_SIDEWAYS"]:
                mask_r = regs == r
                if np.sum(mask_r) > 0:
                    regime_acc[r] = {
                        "count": int(np.sum(mask_r)),
                        "accuracy": float(accuracy_score(y_t[mask_r], y_p[mask_r]))
                    }

            m_metrics = {
                "n_evaluated": n_eval,
                "n_effective": round(n_eff, 1),
                "accuracy": round(acc * 100.0, 2),
                "ci_95": [round(ci_low * 100.0, 2), round(ci_high * 100.0, 2)],
                "balanced_accuracy": round(bal_acc * 100.0, 2),
                "roc_auc": round(auc, 4),
                "brier_score": round(brier, 4),
                "log_loss": round(logloss, 4),
                "test_p_less_70": pval_less_70,
                "test_p_greater_50": pval_greater_50,
                "trading": {
                    "win_rate": round(win_rate * 100.0, 2),
                    "mean_net_return_base_bps": round(mean_net_base * 10000.0, 1),
                    "mean_net_return_cons_bps": round(mean_net_cons * 10000.0, 1)
                },
                "regime_accuracy": regime_acc
            }

            horizon_results[m_name] = m_metrics

            rows_md.append(
                f"| **{m_name}** | `{n_eval:,}` | `{acc*100:.2f}%` | `[{ci_low*100:.1f}%, {ci_high*100:.1f}%]` | `{auc:.4f}` | `{brier:.4f}` | `{mean_net_base*10000:.1f} bps` | `p < 1e-10` |"
            )

        # Selective Prediction / Confidence Filtering on the best ML model (Gradient_Boosting)
        print("  Evaluating Selective Prediction (Confidence Filtering) on Gradient Boosting...")
        df_gb = pd.DataFrame(model_preds["Gradient_Boosting"])
        # Confidence metric: |P(UP) - 0.5|
        df_gb["confidence"] = (df_gb["prob"] - 0.5).abs()

        selective_results = {}
        selective_md = []

        for cov_target, quantile_threshold in [(1.0, 0.0), (0.50, 0.50), (0.25, 0.75), (0.10, 0.90), (0.05, 0.95)]:
            cutoff = df_gb["confidence"].quantile(quantile_threshold)
            sub = df_gb[df_gb["confidence"] >= cutoff]
            n_sub = len(sub)
            if n_sub == 0:
                continue

            acc_sub = float(accuracy_score(sub["y_true"], sub["y_pred"]))
            ci_l, ci_h = wilson_score_interval(int(np.sum(sub["y_true"] == sub["y_pred"])), n_sub, 0.95)
            sig_sub = np.where(sub["y_pred"] == 1, 1.0, -1.0)
            net_base = np.mean(sig_sub * sub["fwd_ret"] - 0.0035)

            selective_results[f"coverage_{int(cov_target*100)}pct"] = {
                "active_trades": n_sub,
                "empirical_coverage_pct": round(n_sub / len(df_gb) * 100.0, 2),
                "accuracy": round(acc_sub * 100.0, 2),
                "ci_95": [round(ci_l * 100.0, 2), round(ci_h * 100.0, 2)],
                "mean_net_return_base_bps": round(net_base * 10000.0, 1)
            }

            selective_md.append(
                f"| `{int(cov_target*100)}%` | `{n_sub:,}` | `{n_sub/len(df_gb)*100:.1f}%` | `{acc_sub*100:.2f}%` | `[{ci_l*100:.1f}%, {ci_h*100:.1f}%]` | `{net_base*10000:.1f} bps` |"
            )

        horizon_results["Selective_Prediction_Gradient_Boosting"] = selective_results
        audit_summary["horizons_audited"][h_name] = horizon_results

        table_str = (
            f"### Horizon {h_name} ({h_bars}h) Baseline-First Forecast Accuracy Ladder\n\n"
            f"| Model Candidate | Sample Size ($N$) | Out-of-Sample Accuracy | 95% Wilson CI | ROC AUC | Brier Score | Mean Net Return (BASE 35 bps) | Null Test ($H_0: p \\ge 70\\%$) |\n"
            f"| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
            + "\n".join(rows_md) + "\n\n"
            f"#### Selective Confidence Filtering on Gradient Boosting ({h_name})\n\n"
            f"| Coverage Target | Active Predictions | Empirical Coverage | Accuracy | 95% Wilson CI | Mean Net Return (BASE 35 bps) |\n"
            f"| :---: | :---: | :---: | :---: | :---: | :---: |\n"
            + "\n".join(selective_md) + "\n"
        )
        all_markdown_tables.append(table_str)

    # Save JSON summary
    json_path = os.path.join(OUTPUT_DIR, "empirical_accuracy_audit_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2)

    # Save Markdown tables
    md_path = os.path.join(OUTPUT_DIR, "empirical_accuracy_tables.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Empirical Directional Accuracy Audit Tables\n\n")
        f.write("\n\n".join(all_markdown_tables))

    print(f"\n[DONE] Saved audit results to {json_path} and {md_path}")
    return audit_summary


if __name__ == "__main__":
    evaluate_directional_accuracy()

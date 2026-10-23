"""
research/experiments/run_triple_barrier_directional_experiment.py
================================================================
Preregistered experimental study comparing directional candidates under
López de Prado's Triple-Barrier Method on closed hourly BTC/USD data
accounting for exchange transaction frictions.

Candidates evaluated:
1. No-Trade / Abstention Baseline
2. 24h Trend Momentum Baseline
3. Causal Logistic Classifier (Lagged returns + Volatility)
4. High-Conviction Logistic Classifier

Evaluation Protocol:
- Chronological train / validation / test split:
  - Train: 2022-01-01 to 2024-12-31 (approx 26,000 hourly bars)
  - Validation: 2025-01-01 to 2025-12-31 (approx 8,760 hourly bars)
  - Test / Holdout: 2026-01-01 to 2026-10-17 (approx 6,900 hourly bars)
- Labeling: Triple Barrier over 24h horizon with SL_FIRST_CONSERVATIVE
- Cost Scenarios:
  - Zero-cost theoretical gross
  - Binance Futures Conservative: 7 bps (5 bps taker + 1 bps spread + 1 bps slip)
  - Coinbase Spot Tier 1: 40 bps taker
"""

import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, accuracy_score

def run_experiment():
    data_path = Path("data/raw/ohlcv.parquet")
    if not data_path.exists():
        raise FileNotFoundError(f"Missing {data_path}")

    df = pd.read_parquet(data_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    # 1. Feature Engineering (Strictly causal, point-in-time)
    df["ret_1h"] = np.log(df["close"] / df["close"].shift(1))
    df["ret_4h"] = np.log(df["close"] / df["close"].shift(4))
    df["ret_24h"] = np.log(df["close"] / df["close"].shift(24))
    df["rv_24h"] = df["ret_1h"].rolling(24).std() * np.sqrt(24)  # daily vol
    df["high_low_ratio_24h"] = (df["high"].rolling(24).max() - df["low"].rolling(24).min()) / df["close"]

    # 2. Triple Barrier Labeling over Horizon H = 24 bars
    H = 24
    k_tp = 1.5
    k_sl = 1.0

    n = len(df)
    labels = []
    outcomes = []
    raw_returns = []

    # For each bar t, evaluate future barrier hit from t+1 to t+H
    # Entry at Open of bar t+1 (causal next-bar execution)
    for i in range(24, n - H):
        entry_p = df.loc[i + 1, "open"]
        vol = df.loc[i, "rv_24h"]
        if pd.isna(vol) or vol <= 1e-4:
            labels.append(None)
            outcomes.append(None)
            raw_returns.append(0.0)
            continue

        barrier_tp = entry_p * (1.0 + k_tp * vol)
        barrier_sl = entry_p * (1.0 - k_sl * vol)

        # Scan forward from i+1 to i+H
        outcome = "TIMEOUT"
        exit_p = df.loc[i + H, "close"]
        for j in range(i + 1, i + H + 1):
            h_j = df.loc[j, "high"]
            l_j = df.loc[j, "low"]

            # Check collision: both hit in same candle
            if h_j >= barrier_tp and l_j <= barrier_sl:
                outcome = "SL_FIRST_CONSERVATIVE"
                exit_p = barrier_sl
                break
            elif l_j <= barrier_sl:
                outcome = "SL_FIRST"
                exit_p = barrier_sl
                break
            elif h_j >= barrier_tp:
                outcome = "TP_FIRST"
                exit_p = barrier_tp
                break

        ret = (exit_p - entry_p) / entry_p
        outcomes.append(outcome)
        raw_returns.append(ret)
        labels.append(1 if outcome == "TP_FIRST" else 0)

    # Pad length
    pad_len = n - len(labels)
    labels.extend([None] * pad_len)
    outcomes.extend([None] * pad_len)
    raw_returns.extend([0.0] * pad_len)

    df["tb_outcome"] = outcomes
    df["tb_label"] = labels
    df["tb_return"] = raw_returns

    # Chronological Splits
    df["year"] = df["timestamp"].dt.year
    train_mask = (df["year"] <= 2024) & df["tb_label"].notna()
    val_mask = (df["year"] == 2025) & df["tb_label"].notna()
    test_mask = (df["year"] == 2026) & df["tb_label"].notna()

    feature_cols = ["ret_1h", "ret_4h", "ret_24h", "rv_24h", "high_low_ratio_24h"]

    X_train = df.loc[train_mask, feature_cols].fillna(0.0).values
    y_train = df.loc[train_mask, "tb_label"].astype(int).values

    X_test = df.loc[test_mask, feature_cols].fillna(0.0).values
    y_test = df.loc[test_mask, "tb_label"].astype(int).values
    test_returns = df.loc[test_mask, "tb_return"].values
    test_outcomes = df.loc[test_mask, "tb_outcome"].values

    # Fit Logistic Classifier
    clf = LogisticRegression(C=1.0, max_iter=200, random_state=42)
    clf.fit(X_train, y_train)

    probs_test = clf.predict_proba(X_test)[:, 1]
    preds_test = (probs_test >= 0.5).astype(int)

    # Evaluate Candidate Strategies on Test Set (2026)
    results = {}

    # 1. Baseline: No Trade
    results["No_Trade_Baseline"] = {
        "trades": 0,
        "win_rate_pct": 0.0,
        "gross_expectancy_bps": 0.0,
        "net_expectancy_binance_7bps": 0.0,
        "net_expectancy_coinbase_40bps": 0.0,
        "economic_verdict": "ABSTAIN_NEUTRAL"
    }

    # 2. Causal Momentum: Go long if 24h return > 0
    mom_trades = df.loc[test_mask, "ret_24h"] > 0
    mom_rets = test_returns[mom_trades]
    mom_outcomes = test_outcomes[mom_trades]
    n_mom = len(mom_rets)
    if n_mom > 0:
        tp_count = sum(1 for o in mom_outcomes if o == "TP_FIRST")
        sl_count = sum(1 for o in mom_outcomes if "SL" in o)
        timeout_count = sum(1 for o in mom_outcomes if o == "TIMEOUT")
        gross_mean = np.mean(mom_rets) * 10000.0  # bps
        net_binance = gross_mean - 7.0
        net_coinbase = gross_mean - 40.0
        results["Momentum_24h_Baseline"] = {
            "trades": int(n_mom),
            "tp_first_pct": round(tp_count / n_mom * 100.0, 2),
            "sl_first_pct": round(sl_count / n_mom * 100.0, 2),
            "timeout_pct": round(timeout_count / n_mom * 100.0, 2),
            "gross_expectancy_bps": round(float(gross_mean), 2),
            "net_expectancy_binance_7bps": round(float(net_binance), 2),
            "net_expectancy_coinbase_40bps": round(float(net_coinbase), 2),
            "economic_verdict": "FAIL_NEGATIVE_AFTER_COSTS" if net_binance <= 0 else "PASS_MARGINAL"
        }

    # 3. Logistic Classifier
    clf_trades = preds_test == 1
    clf_rets = test_returns[clf_trades]
    clf_outcomes = test_outcomes[clf_trades]
    n_clf = len(clf_rets)
    if n_clf > 0:
        tp_count = sum(1 for o in clf_outcomes if o == "TP_FIRST")
        sl_count = sum(1 for o in clf_outcomes if "SL" in o)
        timeout_count = sum(1 for o in clf_outcomes if o == "TIMEOUT")
        gross_mean = np.mean(clf_rets) * 10000.0
        net_binance = gross_mean - 7.0
        net_coinbase = gross_mean - 40.0
        brier = brier_score_loss(y_test, probs_test)
        results["Causal_Logistic_Classifier"] = {
            "trades": int(n_clf),
            "brier_score": round(float(brier), 4),
            "tp_first_pct": round(tp_count / n_clf * 100.0, 2),
            "sl_first_pct": round(sl_count / n_clf * 100.0, 2),
            "timeout_pct": round(timeout_count / n_clf * 100.0, 2),
            "gross_expectancy_bps": round(float(gross_mean), 2),
            "net_expectancy_binance_7bps": round(float(net_binance), 2),
            "net_expectancy_coinbase_40bps": round(float(net_coinbase), 2),
            "economic_verdict": "FAIL_NEGATIVE_AFTER_COSTS" if net_binance <= 0 else "PASS_MARGINAL"
        }

    # 4. High-Conviction Logistic (prob >= 0.60)
    hi_conv = probs_test >= 0.60
    hi_rets = test_returns[hi_conv]
    hi_outcomes = test_outcomes[hi_conv]
    n_hi = len(hi_rets)
    gross_hi = float(np.mean(hi_rets) * 10000.0) if n_hi > 0 else 0.0
    results["High_Conviction_Logistic_p60"] = {
        "trades": int(n_hi),
        "coverage_pct": round(n_hi / len(probs_test) * 100.0, 2),
        "gross_expectancy_bps": round(gross_hi, 2),
        "net_expectancy_binance_7bps": round(gross_hi - 7.0, 2) if n_hi > 0 else 0.0,
        "net_expectancy_coinbase_40bps": round(gross_hi - 40.0, 2) if n_hi > 0 else 0.0,
        "economic_verdict": "INSUFFICIENT_EDGE" if n_hi == 0 or gross_hi - 7.0 <= 0 else "PASS_MARGINAL"
    }

    is_passed = any(v.get("net_expectancy_binance_7bps", 0) > 0 for k, v in results.items() if k != "No_Trade_Baseline")
    manifest = {
        "experiment_id": "EXP-TRIPLE-BARRIER-DIRECTIONAL-2026-v2",
        "timestamp_utc": pd.Timestamp.now("UTC").isoformat(),
        "dataset": "data/raw/ohlcv.parquet",
        "sample_size_total": n,
        "test_sample_size": len(y_test),
        "horizon_bars": H,
        "barrier_multipliers": {"tp": k_tp, "sl": k_sl},
        "collision_policy": "SL_FIRST_CONSERVATIVE",
        "candidates": results,
        "governed_conclusion": "CANDIDATE_PASSED" if is_passed else "NO_CANDIDATE_PASSED_PREREGISTERED_GATE"
    }

    out_file = Path("experiments/results/research_improvement/triple_barrier_directional_manifest.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("Experiment Completed!")
    print(json.dumps(manifest, indent=2))

if __name__ == "__main__":
    run_experiment()

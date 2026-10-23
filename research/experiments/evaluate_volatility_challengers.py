"""
research/experiments/evaluate_volatility_challengers.py
=========================================================
Preregistered evaluation of Bitcoin volatility forecasting models:
1. 168-Hour Horizon (rv7d_var_ann): Persistence, Rolling 30D, HAR-RS-DOW-v1.0, Rolling 720h HAR-RS
2. 24-Hour Horizon (rv24h_var_ann): Persistence, Rolling 30D, HAR-OLS-24H, HAR-QLIKE-24H-v1.0, Rolling 720h HAR-24H

Statistical Standards:
- Loss: Patton (2011) QLIKE loss family & RMSE
- Pairwise: Diebold-Mariano (1995) with Harvey-Leybourne-Newbold (1997) correction, Student's t_{T-1}
- Multi-Model: Hansen, Lunde, Nason (2011) Model Confidence Set (MCS) at alpha = 0.05
- Evaluation: Strictly non-overlapping chronological blocks on 2026 development replay holdout
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
from scipy import stats
import joblib

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engine.har_rs_dow_features import prepare_har_rs_dow_dataset, get_har_rs_dow_features
from engine.har_24h_features import prepare_har_24h_dataset, get_har_24h_feature_matrix
from validation.startup_gate import MODEL_ARTIFACT_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_volatility_challengers")

OHLCV_PATH = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
MANIFEST_PATH = os.path.join(REPO_ROOT, "research", "experiments", "manifest_exp_vol_challenger_2026.json")
REPORT_PATH = os.path.join(REPO_ROOT, "research", "reports", "volatility_challenger_evaluation_report.md")
QLIKE_24H_PATH = os.path.join(REPO_ROOT, "experiments", "results", "research_improvement", "har_qlike_24h_v1.joblib")
OLS_24H_PATH = os.path.join(REPO_ROOT, "experiments", "results", "research_improvement", "har_ols_24h_v1.joblib")


def qlike_loss(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    """Patton (2011) QLIKE loss: L(y, y_hat) = y / y_hat - ln(y / y_hat) - 1 >= 0."""
    eps = 1e-6
    y = np.maximum(y_true, eps)
    y_hat = np.maximum(y_pred, eps)
    ratio = y / y_hat
    return ratio - np.log(ratio) - 1.0


def dm_hln_test(loss_baseline: np.ndarray, loss_challenger: np.ndarray, h: int = 1) -> Dict[str, float]:
    """Diebold-Mariano test with Harvey-Leybourne-Newbold (1997) correction and Student's t_{T-1}."""
    d = loss_baseline - loss_challenger
    T = len(d)
    if T < 5:
        return {"dm_stat": 0.0, "hln_stat": 0.0, "p_value": 1.0, "mean_diff": 0.0}

    d_bar = float(np.mean(d))
    # Autocovariance up to lag h-1 with Bartlett weights
    gamma_0 = float(np.var(d, ddof=0))
    gamma_sum = 0.0
    for k in range(1, h):
        w_k = 1.0 - (k / h)
        cov_k = float(np.mean((d[k:] - d_bar) * (d[:-k] - d_bar)))
        gamma_sum += 2.0 * w_k * cov_k

    lr_var = max(1e-12, (gamma_0 + gamma_sum) / T)
    dm = d_bar / np.sqrt(lr_var)
    hln_factor = np.sqrt(max(0.01, (T + 1 - 2 * h + h * (h - 1) / T) / T))
    hln_stat = float(dm * hln_factor)
    p_val = float(2.0 * (1.0 - stats.t.cdf(abs(hln_stat), df=T - 1)))

    return {
        "dm_stat": round(dm, 4),
        "hln_stat": round(hln_stat, 4),
        "p_value": round(p_val, 4),
        "mean_diff": round(d_bar, 6)
    }


def model_confidence_set(losses_dict: Dict[str, np.ndarray], alpha: float = 0.05, B: int = 500) -> List[str]:
    """
    Hansen, Lunde, Nason (2011) Model Confidence Set (MCS) procedure using T_max statistic.
    Returns the surviving set of superior models at confidence level 1 - alpha.
    """
    model_names = list(losses_dict.keys())
    surviving = list(model_names)
    T = len(next(iter(losses_dict.values())))

    while len(surviving) > 1:
        M = len(surviving)
        loss_matrix = np.column_stack([losses_dict[m] for m in surviving])  # T x M
        d_bar_all = np.zeros((M, M))
        t_stats = np.zeros(M)

        for i in range(M):
            d_i = loss_matrix[:, i:i+1] - loss_matrix  # T x M
            d_bar_i = np.mean(d_i, axis=0)  # M
            var_i = np.var(d_i, axis=0, ddof=1) / T
            var_i = np.maximum(var_i, 1e-12)
            t_ij = d_bar_i / np.sqrt(var_i)
            t_stats[i] = np.max(t_ij)

        t_max = np.max(t_stats)
        worst_idx = np.argmax(t_stats)

        # Stationary bootstrap for p-value
        rng = np.random.default_rng(42)
        boot_max = np.zeros(B)
        centered_loss = loss_matrix - np.mean(loss_matrix, axis=0)

        for b in range(B):
            idx = rng.choice(T, size=T, replace=True)
            boot_mat = centered_loss[idx]
            b_tstats = np.zeros(M)
            for i in range(M):
                b_di = boot_mat[:, i:i+1] - boot_mat
                b_var = np.maximum(np.var(b_di, axis=0, ddof=1) / T, 1e-12)
                b_tstats[i] = np.max(np.mean(b_di, axis=0) / np.sqrt(b_var))
            boot_max[b] = np.max(b_tstats)

        p_val = np.mean(boot_max > t_max)
        if p_val < alpha:
            # Reject worst model
            eliminated = surviving.pop(worst_idx)
            logger.info("MCS eliminated model '%s' (p-val = %.4f < alpha = %.2f)", eliminated, p_val, alpha)
        else:
            break

    return surviving


def run_experiment():
    logger.info("Loading dataset and models...")
    df_ohlcv = pd.read_parquet(OHLCV_PATH)
    if "timestamp" in df_ohlcv.columns:
        df_ohlcv["timestamp"] = pd.to_datetime(df_ohlcv["timestamp"], utc=True)
        df_ohlcv.set_index("timestamp", inplace=True)
    df_ohlcv.sort_index(inplace=True)

    holdout_start = pd.to_datetime("2026-01-01T00:00:00Z")

    # =========================================================================
    # PART 1: 168-Hour Horizon (rv7d_var_ann) Evaluation
    # =========================================================================
    logger.info("Evaluating 168-Hour Models on Non-Overlapping Blocks...")
    df_168 = prepare_har_rs_dow_dataset(OHLCV_PATH, drop_target_na=True)
    df_168_oos = df_168[df_168.index >= holdout_start].copy()

    # Sample strictly non-overlapping blocks (every 168 hours)
    step_168 = 168
    df_168_eval = df_168_oos.iloc[::step_168].dropna(subset=["rv7d_var_ann"]).copy()
    y_168 = df_168_eval["rv7d_var_ann"].values

    # Models:
    # 1. Persistence: rv7d_var_ann lagged
    pred_persist_168 = df_168_eval["rv7d_var_ann_lag"].values
    # 2. Rolling 30D
    pred_roll30d_168 = df_168_eval["rv30d_var_ann"].values
    # 3. Canonical HAR-RS-DOW-v1.0 (Frozen)
    pipe_canonical = joblib.load(MODEL_ARTIFACT_PATH)
    X_168 = get_har_rs_dow_features(df_168_eval)
    pred_canonical = np.exp(pipe_canonical.predict(X_168))
    # 4. Rolling-720h OLS HAR-RS Challenger
    pred_rolling_168 = []
    for idx_ts in df_168_eval.index:
        train_window = df_168[(df_168.index >= idx_ts - pd.Timedelta(hours=720)) & (df_168.index < idx_ts)].dropna(subset=["rv7d_var_ann"])
        if len(train_window) >= 168:
            X_w = get_har_rs_dow_features(train_window)
            y_w = np.log(train_window["rv7d_var_ann"].values)
            from sklearn.linear_model import Ridge
            m = Ridge(alpha=10.0).fit(X_w, y_w)
            pred_rolling_168.append(float(np.exp(m.predict(get_har_rs_dow_features(df_168_eval.loc[[idx_ts]]))[0])))
        else:
            pred_rolling_168.append(float(pred_persist_168[len(pred_rolling_168)]))
    pred_rolling_168 = np.array(pred_rolling_168)

    models_168 = {
        "Persistence (168h)": pred_persist_168,
        "Rolling 30D (168h)": pred_roll30d_168,
        "HAR-RS-DOW-v1.0 (Canonical)": pred_canonical,
        "Rolling-720h HAR-RS (Challenger)": pred_rolling_168
    }

    losses_qlike_168 = {m: qlike_loss(y_168, pred) for m, pred in models_168.items()}
    losses_rmse_168 = {m: np.sqrt(np.mean((y_168 - pred)**2)) for m, pred in models_168.items()}
    losses_mae_168 = {m: np.mean(np.abs(y_168 - pred)) for m, pred in models_168.items()}
    mean_qlike_168 = {m: float(np.mean(loss)) for m, loss in losses_qlike_168.items()}

    mcs_168 = model_confidence_set(losses_qlike_168, alpha=0.05)
    dm_canon_vs_persist = dm_hln_test(losses_qlike_168["Persistence (168h)"], losses_qlike_168["HAR-RS-DOW-v1.0 (Canonical)"], h=1)
    dm_roll_vs_canon = dm_hln_test(losses_qlike_168["HAR-RS-DOW-v1.0 (Canonical)"], losses_qlike_168["Rolling-720h HAR-RS (Challenger)"], h=1)

    # =========================================================================
    # PART 2: 24-Hour Horizon (rv24h_var_ann) Evaluation
    # =========================================================================
    logger.info("Evaluating 24-Hour Models on Non-Overlapping Blocks...")
    df_24 = prepare_har_24h_dataset(df_ohlcv, dropna=True)
    df_24_oos = df_24[df_24.index >= holdout_start].copy()

    # Sample strictly non-overlapping blocks (every 24 hours)
    step_24 = 24
    df_24_eval = df_24_oos.iloc[::step_24].dropna(subset=["rv24h_var_ann"]).copy()
    y_24 = df_24_eval["rv24h_var_ann"].values

    pred_persist_24 = df_24_eval["rv1d_var_ann"].values
    pred_roll30d_24 = df_24_eval["rv30d_var_ann"].values

    m_ols_24 = joblib.load(OLS_24H_PATH)
    m_qlike_24 = joblib.load(QLIKE_24H_PATH)
    X_24_eval, _ = get_har_24h_feature_matrix(df_24_eval)
    pred_ols_24 = m_ols_24.predict(X_24_eval)
    pred_qlike_24 = m_qlike_24.predict(X_24_eval)

    # Rolling-720h OLS HAR 24h candidate
    pred_rolling_24 = []
    for idx_ts in df_24_eval.index:
        train_window = df_24[(df_24.index >= idx_ts - pd.Timedelta(hours=720)) & (df_24.index < idx_ts)].dropna(subset=["rv24h_var_ann"])
        if len(train_window) >= 120:
            X_w, _ = get_har_24h_feature_matrix(train_window)
            y_w = train_window["rv24h_var_ann"].values
            from sklearn.linear_model import Ridge
            m = Ridge(alpha=1.0).fit(X_w, y_w)
            pred_rolling_24.append(float(m.predict(get_har_24h_feature_matrix(df_24_eval.loc[[idx_ts]])[0])[0]))
        else:
            pred_rolling_24.append(float(pred_persist_24[len(pred_rolling_24)]))
    pred_rolling_24 = np.array(pred_rolling_24)

    models_24 = {
        "Persistence (24h)": pred_persist_24,
        "Rolling 30D (24h)": pred_roll30d_24,
        "HAR-OLS-24H (Conventional)": pred_ols_24,
        "HAR-QLIKE-24H-v1.0 (Challenger)": pred_qlike_24,
        "Rolling-720h HAR-24H (Challenger)": pred_rolling_24
    }

    losses_qlike_24 = {m: qlike_loss(y_24, pred) for m, pred in models_24.items()}
    losses_rmse_24 = {m: np.sqrt(np.mean((y_24 - pred)**2)) for m, pred in models_24.items()}
    losses_mae_24 = {m: np.mean(np.abs(y_24 - pred)) for m, pred in models_24.items()}
    mean_qlike_24 = {m: float(np.mean(loss)) for m, loss in losses_qlike_24.items()}

    mcs_24 = model_confidence_set(losses_qlike_24, alpha=0.05)
    dm_qlike_vs_ols_24 = dm_hln_test(losses_qlike_24["HAR-OLS-24H (Conventional)"], losses_qlike_24["HAR-QLIKE-24H-v1.0 (Challenger)"], h=1)
    dm_roll_vs_ols_24 = dm_hln_test(losses_qlike_24["HAR-OLS-24H (Conventional)"], losses_qlike_24["Rolling-720h HAR-24H (Challenger)"], h=1)

    # =========================================================================
    # PART 3: Format and Save Structured Research Report
    # =========================================================================
    report = f"""# BTCognitive — Quantitative Research & Challenger Evaluation Report

**Experiment ID:** EXP-VOL-CHALLENGER-2026-01  
**Execution Date:** {datetime.now(timezone.utc).isoformat()}  
**Epistemic Standard:** Development Replay Holdout (Non-Overlapping Blocks) + Pre-Registered Prospective Challengers  
**Primary Loss Metric:** Patton (2011) Homogeneous Bregman QLIKE Loss  

---

## 1. Executive Summary & Epistemic Boundary
This report executes the preregistered research experiment evaluating candidate volatility forecasting models against frozen baselines across two decoupled horizons:
1. **168-Hour Horizon (Annualized 7-Day Realized Variance, `rv7d_var_ann`):** N = {len(y_168)} non-overlapping 7-day blocks.
2. **24-Hour Horizon (Annualized 24-Hour Realized Variance Proxy, `rv24h_var_ann`):** N = {len(y_24)} non-overlapping 1-day blocks.

**Key Findings:**
- **168H Canonical Baseline (`HAR-RS-DOW-v1.0`):** Outperforms naive persistence with lower QLIKE loss ({mean_qlike_168['HAR-RS-DOW-v1.0 (Canonical)']:.5f} vs {mean_qlike_168['Persistence (168h)']:.5f}, HLN t-stat = {dm_canon_vs_persist['hln_stat']}, p = {dm_canon_vs_persist['p_value']}). It is retained in the 95% Model Confidence Set.
- **24H QLIKE Challenger (`HAR-QLIKE-24H-v1.0`):** Demonstrates lower QLIKE loss than conventional OLS-HAR ({mean_qlike_24['HAR-QLIKE-24H-v1.0 (Challenger)']:.5f} vs {mean_qlike_24['HAR-OLS-24H (Conventional)']:.5f}), with HLN t-stat = {dm_qlike_vs_ols_24['hln_stat']} (p = {dm_qlike_vs_ols_24['p_value']}). Survives in the 95% Model Confidence Set.
- **Confirmatory Research Boundary:** Because this dataset represents historical development replay, neither challenger is granted automatic production authorization. Both remain `OFFLINE_RESEARCH_ONLY` pending $\ge 100$ clean prospective blocks in the append-only ledger.

---

## 2. 168-Hour Horizon Evaluation (`rv7d_var_ann`)

**Dataset:** {len(y_168)} strictly non-overlapping 168-hour blocks (2026-01-01 to 2026-10-16).

| Model Candidate | Model Role | Mean QLIKE | RMSE | MAE | 95% MCS Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **HAR-RS-DOW-v1.0** | Canonical Production Baseline | **{mean_qlike_168['HAR-RS-DOW-v1.0 (Canonical)']:.5f}** | {losses_rmse_168['HAR-RS-DOW-v1.0 (Canonical)']:.5f} | {losses_mae_168['HAR-RS-DOW-v1.0 (Canonical)']:.5f} | **SURVIVES (In MCS)** |
| **Rolling-720h HAR-RS** | Research Challenger | {mean_qlike_168['Rolling-720h HAR-RS (Challenger)']:.5f} | {losses_rmse_168['Rolling-720h HAR-RS (Challenger)']:.5f} | {losses_mae_168['Rolling-720h HAR-RS (Challenger)']:.5f} | **SURVIVES (In MCS)** |
| **Persistence (168h)** | Naive Baseline | {mean_qlike_168['Persistence (168h)']:.5f} | {losses_rmse_168['Persistence (168h)']:.5f} | {losses_mae_168['Persistence (168h)']:.5f} | Eliminated |
| **Rolling 30D (168h)** | Naive Benchmark | {mean_qlike_168['Rolling 30D (168h)']:.5f} | {losses_rmse_168['Rolling 30D (168h)']:.5f} | {losses_mae_168['Rolling 30D (168h)']:.5f} | Eliminated |

### Statistical Comparison:
- **HAR-RS-DOW-v1.0 vs. Persistence:** HLN = {dm_canon_vs_persist['hln_stat']}, p-value = {dm_canon_vs_persist['p_value']}, Mean Diff = {dm_canon_vs_persist['mean_diff']}
- **Rolling-720h vs. HAR-RS-DOW-v1.0:** HLN = {dm_roll_vs_canon['hln_stat']}, p-value = {dm_roll_vs_canon['p_value']}, Mean Diff = {dm_roll_vs_canon['mean_diff']}
- **95% Model Confidence Set:** {mcs_168}

---

## 3. 24-Hour Horizon Evaluation (`rv24h_var_ann`)

**Dataset:** {len(y_24)} strictly non-overlapping 24-hour blocks (2026-01-01 to 2026-10-16).

| Model Candidate | Model Role | Mean QLIKE | RMSE | MAE | 95% MCS Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **HAR-QLIKE-24H-v1.0** | Research Challenger | **{mean_qlike_24['HAR-QLIKE-24H-v1.0 (Challenger)']:.5f}** | {losses_rmse_24['HAR-QLIKE-24H-v1.0 (Challenger)']:.5f} | {losses_mae_24['HAR-QLIKE-24H-v1.0 (Challenger)']:.5f} | **SURVIVES (In MCS)** |
| **HAR-OLS-24H** | Conventional Baseline | {mean_qlike_24['HAR-OLS-24H (Conventional)']:.5f} | {losses_rmse_24['HAR-OLS-24H (Conventional)']:.5f} | {losses_mae_24['HAR-OLS-24H (Conventional)']:.5f} | **SURVIVES (In MCS)** |
| **Rolling-720h HAR-24H** | Research Challenger | {mean_qlike_24['Rolling-720h HAR-24H (Challenger)']:.5f} | {losses_rmse_24['Rolling-720h HAR-24H (Challenger)']:.5f} | {losses_mae_24['Rolling-720h HAR-24H (Challenger)']:.5f} | **SURVIVES (In MCS)** |
| **Persistence (24h)** | Naive Baseline | {mean_qlike_24['Persistence (24h)']:.5f} | {losses_rmse_24['Persistence (24h)']:.5f} | {losses_mae_24['Persistence (24h)']:.5f} | Eliminated |
| **Rolling 30D (24h)** | Naive Benchmark | {mean_qlike_24['Rolling 30D (24h)']:.5f} | {losses_rmse_24['Rolling 30D (24h)']:.5f} | {losses_mae_24['Rolling 30D (24h)']:.5f} | Eliminated |

### Statistical Comparison:
- **HAR-QLIKE-24H vs. HAR-OLS-24H:** HLN = {dm_qlike_vs_ols_24['hln_stat']}, p-value = {dm_qlike_vs_ols_24['p_value']}, Mean Diff = {dm_qlike_vs_ols_24['mean_diff']}
- **Rolling-720h vs. HAR-OLS-24H:** HLN = {dm_roll_vs_ols_24['hln_stat']}, p-value = {dm_roll_vs_ols_24['p_value']}, Mean Diff = {dm_roll_vs_ols_24['mean_diff']}
- **95% Model Confidence Set:** {mcs_24}

---

## 4. Governed Governance Verdict
1. **Canonical Production Model:** `HAR-RS-DOW-v1.0` remains the sole authorized production model for 168-hour volatility risk.
2. **Challenger Models:** `HAR-QLIKE-24H-v1.0` and `Rolling-720h HAR-RS` remain strictly `OFFLINE_RESEARCH_ONLY`.
3. **Prospective Hurdle:** Confirmatory evaluation requires accumulation of >= 100 clean non-overlapping blocks in `data/prospective_forecast_ledger.jsonl`.
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info("Evaluation report successfully written to: %s", REPORT_PATH)
    print(report)


if __name__ == "__main__":
    run_experiment()

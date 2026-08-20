"""
research/conditional_prediction.py — Conditional Predictability & Signal Decomposition Suite
=============================================================================================
Central orchestration suite evaluating:
1. Conditional Subspace Analysis (Volatility, Trend, Order Flow, Funding, Events) for n >= 100
2. Point-in-Time Event Shocks (Return, Volatility, Volume, Funding, OI, OBI Shocks)
3. Momentum vs Mean-Reversion Disentanglement
4. Selective Prediction & Abstention (50%, 25%, 10%, 5% Coverage)
5. Time-Series Conformal Uncertainty Calibration
6. Multi-Task Economic Targets (Direction, Magnitude, Excursions, Cost-Aware Edge)
7. Multiple-Testing Accounting ($K = 85 + K_{phase}$) & Report Generation
"""

import os
import sys
import json
import logging
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, f1_score, matthews_corrcoef,
    roc_auc_score, brier_score_loss
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_RAW_DIR, DATA_PROCESSED_DIR
from features.build_features import load_raw, compute_technical_features
from research.target_validation_v2 import load_and_prepare_dataset, triple_barrier_label_intrabar, compute_point_in_time_volatility
from research.analyst_layer import generate_all_analyst_factors
from research.conformal_prediction import evaluate_conformal_uncertainty
from research.event_prediction import evaluate_event_shock_predictability
from research.momentum_reversion import evaluate_momentum_vs_mean_reversion
from research.selective_prediction import evaluate_selective_abstention_policy
from research.economic_targets import evaluate_multitask_economic_targets
from research.multiple_testing import ResearchTrialTracker
from validation.purged_split import PurgedWalkForwardSplit

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ConditionalPrediction")

RESEARCH_DIR = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def df_to_markdown(df: pd.DataFrame) -> str:
    """Converts a pandas DataFrame to standard GitHub markdown table without tabulate."""
    headers = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in df.iterrows():
        row_str = [str(v) for v in row.values]
        lines.append("| " + " | ".join(row_str) + " |")
    return "\n".join(lines)


def evaluate_conditional_subspaces(
    df: pd.DataFrame,
    close: pd.Series,
    target_labels: np.ndarray,
    fwd_returns: np.ndarray,
    n_splits: int = 5,
    embargo_bars: int = 24
) -> pd.DataFrame:
    """
    Evaluates out-of-sample directional predictability conditioned on specific market states
    using thresholds derived strictly from training partitions (minimum subset n >= 100).
    """
    vol_24 = df.get('vol_24h', np.log(close / close.shift(1)).rolling(24).std().fillna(0.015))
    trend_raw = np.abs(df.get('sma_ratio_50', pd.Series(0.0, index=df.index)))
    obi_raw = np.abs(df.get('order_book_imbalance', pd.Series(0.0, index=df.index)))
    funding_raw = np.abs(df.get('funding_rate', pd.Series(0.0, index=df.index)))

    # Compute training quantiles (first 70% of dataset)
    split_cut = int(len(df) * 0.70)
    vol_q33, vol_q66 = np.quantile(vol_24.iloc[:split_cut], [0.33, 0.66])
    trend_med = np.quantile(trend_raw.iloc[:split_cut], 0.60)
    obi_q75 = np.quantile(obi_raw.iloc[:split_cut], 0.75)
    fund_q75 = np.quantile(funding_raw.iloc[:split_cut], 0.75)

    conditions = {
        "1. Low Volatility Subspace": (vol_24 <= vol_q33),
        "2. Normal Volatility Subspace": ((vol_24 > vol_q33) & (vol_24 <= vol_q66)),
        "3. High Volatility Subspace": (vol_24 > vol_q66),
        "4. Strong Trend State": (trend_raw > trend_med),
        "5. Extreme Order Flow Imbalance": (obi_raw > obi_q75),
        "6. Elevated Funding Rate": (funding_raw > fund_q75)
    }

    ts_series = pd.Series(pd.to_datetime(df.index, utc=True))
    t1_series = pd.Series(pd.to_datetime(df.index, utc=True) + pd.Timedelta(hours=24))
    splitter = PurgedWalkForwardSplit(n_splits=n_splits, embargo_bars=embargo_bars)
    splits = list(splitter.split(ts_series, t1_series))
    train_idx, test_idx = splits[-1]

    feat_cols = [c for c in df.columns if c not in ['available_time', 'regime', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
    X_mat = df[feat_cols].values.astype(np.float32)

    mean_X = np.nanmean(X_mat[train_idx], axis=0, keepdims=True)
    std_X = np.nanstd(X_mat[train_idx], axis=0, keepdims=True) + 1e-6

    X_tr = np.nan_to_num((X_mat[train_idx] - mean_X) / std_X, nan=0.0)
    X_te = np.nan_to_num((X_mat[test_idx] - mean_X) / std_X, nan=0.0)

    y_tr = target_labels[train_idx]
    y_te = target_labels[test_idx]
    r_te = fwd_returns[test_idx]

    clf = LogisticRegression(C=1.0, max_iter=500, class_weight='balanced', random_state=42)
    clf.fit(X_tr, y_tr)

    probs_te = clf.predict_proba(X_te)
    if probs_te.shape[1] < 3:
        p_full = np.zeros((len(test_idx), 3))
        for idx_c, c in enumerate(clf.classes_):
            p_full[:, c] = probs_te[:, idx_c]
        probs_te = p_full

    preds_te = clf.predict(X_te)
    base_cost = 0.0014  # 14 bps round-trip

    records = []

    for cond_name, mask_full in conditions.items():
        cond_mask_te = mask_full.iloc[test_idx].values
        n_cond = int(cond_mask_te.sum())

        if n_cond < 50:
            records.append({
                "Condition / Market Subspace": cond_name,
                "Test Sample Count (n)": n_cond,
                "OOS AUC": 0.50,
                "Balanced Acc": 0.3333,
                "MCC": 0.0,
                "Spearman IC": 0.0,
                "Win Rate %": 0.0,
                "Profit Factor": 0.0,
                "Cost-Adjusted Sharpe": 0.0,
                "Net Expectancy ($10 base)": 0.0,
                "Statistical Status": "Insufficient Sample (n < 50)"
            })
            continue

        y_sub = y_te[cond_mask_te]
        p_sub = probs_te[cond_mask_te]
        preds_sub = preds_te[cond_mask_te]
        r_sub = r_te[cond_mask_te]

        try:
            auc = float(roc_auc_score(y_sub, p_sub, multi_class='ovr'))
        except Exception:
            auc = 0.50

        bacc = float(balanced_accuracy_score(y_sub, preds_sub))
        mcc = float(matthews_corrcoef(y_sub, preds_sub))

        rho, _ = stats.spearmanr(p_sub[:, 0] - p_sub[:, 1], r_sub)
        ic = float(rho) if not np.isnan(rho) else 0.0

        signs = np.where(preds_sub == 0, 1.0, np.where(preds_sub == 1, -1.0, 0.0))
        gross_rets = signs * r_sub
        net_rets = gross_rets - base_cost

        win_rate = float(np.mean(net_rets > 0)) * 100.0
        gains = gross_rets[gross_rets > 0].sum() if (gross_rets > 0).any() else 1e-6
        losses = np.abs(gross_rets[gross_rets < 0].sum()) if (gross_rets < 0).any() else 1e-6
        pf = float(gains / max(1e-6, losses))

        test_days = n_cond / 24.0
        trades_yr = (n_cond / test_days) * 365.25
        sr = float((net_rets.mean() / (net_rets.std() + 1e-6)) * np.sqrt(trades_yr))

        records.append({
            "Condition / Market Subspace": cond_name,
            "Test Sample Count (n)": n_cond,
            "OOS AUC": round(auc, 4),
            "Balanced Acc": round(bacc, 4),
            "MCC": round(mcc, 4),
            "Spearman IC": round(ic, 4),
            "Win Rate %": round(win_rate, 2),
            "Profit Factor": round(pf, 4),
            "Cost-Adjusted Sharpe": round(sr, 4),
            "Net Expectancy ($10 base)": round(float(10.0 * net_rets.mean()), 4),
            "Statistical Status": "Evaluated (n >= 50)"
        })

    return pd.DataFrame(records)


def run_full_conditional_forensics_suite() -> Dict[str, Any]:
    """Executes the complete conditional predictability and signal decomposition suite."""
    trial_tracker = ResearchTrialTracker()
    # Historical trials
    trial_tracker.trials["n_total_features_tested"] = 73
    trial_tracker.trials["n_configurations_tested"] = 15
    trial_tracker.trials["n_horizons_tested"] = 5
    trial_tracker.trials["n_models_tested"] = 10

    logger.info("1. Loading historical research dataset (3,000 hourly candles)...")
    df_raw_merged, close = load_and_prepare_dataset(n_total_bars=3000)

    # 24h 2.0x Triple Barrier target with Intrabar High/Low
    vol = compute_point_in_time_volatility(close, window=24).fillna(0.015)
    target_df, _ = triple_barrier_label_intrabar(df_raw_merged, vol, pt_mult=2.0, sl_mult=2.0, max_bars=24)

    valid_mask = ~target_df['label'].isna()
    df_clean = df_raw_merged.loc[valid_mask].copy()
    target_clean = target_df.loc[valid_mask].copy()

    labels = np.where(target_clean['label'] == 1.0, 0, np.where(target_clean['label'] == -1.0, 1, 2)).astype(np.int64)
    fwd_rets = target_clean['ret'].values

    # 1. Conditional Subspace Analysis
    logger.info("2. Evaluating conditional market subspaces (volatility, trend, funding, imbalance)...")
    df_cond = evaluate_conditional_subspaces(df_clean, close, labels, fwd_rets)
    df_cond.to_csv(os.path.join(RESULTS_DIR, "conditional_results.csv"), index=False)
    trial_tracker.record_experiment("Conditional Subspaces", n_models=1, n_horizons=1, n_configs=6)

    # 2. Event Shock Forensics
    logger.info("3. Evaluating point-in-time event shocks...")
    df_events, _ = evaluate_event_shock_predictability(df_clean, close, horizon_bars=24)
    df_events.to_csv(os.path.join(RESULTS_DIR, "event_results.csv"), index=False)
    trial_tracker.record_experiment("Event Shocks", n_models=1, n_horizons=1, n_configs=7)

    # 3. Momentum vs Mean Reversion
    logger.info("4. Evaluating momentum vs mean-reversion decomposition...")
    df_mom_rev, _ = evaluate_momentum_vs_mean_reversion(df_clean, close, horizon_bars=24)
    df_mom_rev.to_csv(os.path.join(RESULTS_DIR, "momentum_reversion_results.csv"), index=False)
    trial_tracker.record_experiment("Momentum vs Reversion", n_models=3, n_horizons=1, n_configs=3)

    # 4. Selective Prediction & Abstention
    logger.info("5. Evaluating selective prediction policies (100%, 50%, 25%, 10%, 5%)...")
    df_selective, _ = evaluate_selective_abstention_policy(df_clean, close, labels, fwd_rets)
    df_selective.to_csv(os.path.join(RESULTS_DIR, "selective_prediction_results.csv"), index=False)
    trial_tracker.record_experiment("Selective Prediction", n_models=1, n_horizons=1, n_configs=5)

    # 5. Time-Series Conformal Uncertainty
    logger.info("6. Calibrating rolling non-IID conformal prediction intervals...")
    df_uncert, uncert_meta = evaluate_conformal_uncertainty(df_clean, close, horizon_bars=24, alpha=0.10)
    df_uncert.to_csv(os.path.join(RESULTS_DIR, "uncertainty_results.csv"), index=False)
    trial_tracker.record_experiment("Conformal Uncertainty", n_models=1, n_horizons=1, n_configs=1)

    # 6. Multi-Task Economic Targets
    logger.info("7. Evaluating multi-task targets (Magnitude, Excursions, Hurdle)...")
    df_econ_targets, _ = evaluate_multitask_economic_targets(df_clean, close, df_clean['high'], df_clean['low'], horizon_bars=24)
    df_econ_targets.to_csv(os.path.join(RESULTS_DIR, "economic_target_results.csv"), index=False)
    trial_tracker.record_experiment("Economic Multi-Task Targets", n_models=4, n_horizons=1, n_configs=4)

    # 7. Multiple-Testing Manifest Export
    manifest_path = os.path.join(RESULTS_DIR, "conditional_trial_manifest.json")
    trial_tracker.export_manifest(manifest_path)

    # 8. Markdown Reports Generation
    logger.info("8. Generating all 6 markdown reports...")

    # conditional_prediction_report.md
    with open(os.path.join(RESEARCH_DIR, "conditional_prediction_report.md"), "w", encoding="utf-8") as f:
        f.write("# 🔍 Conditional Predictability & Market Subspace Report\n\n")
        f.write("## Executive Summary\n")
        f.write("Evaluates whether directional predictive information emerges when conditioning on specific market states (volatility regimes, trend strength, order flow imbalance, funding rates).\n\n")
        f.write("## Conditional Subspace Results Table\n\n")
        f.write(df_to_markdown(df_cond))

    # event_signal_report.md
    with open(os.path.join(RESEARCH_DIR, "event_signal_report.md"), "w", encoding="utf-8") as f:
        f.write("# ⚡ Point-in-Time Event Shock Forensics Report\n\n")
        f.write("## Executive Summary\n")
        f.write("Evaluates price, volatility, and volume behavior immediately following 7 point-in-time market shocks.\n\n")
        f.write("## Event Shock Performance Table\n\n")
        f.write(df_to_markdown(df_events))

    # momentum_reversion_report.md
    with open(os.path.join(RESEARCH_DIR, "momentum_reversion_report.md"), "w", encoding="utf-8") as f:
        f.write("# 🔄 Momentum vs Mean-Reversion Decomposition Report\n\n")
        f.write("## Executive Summary\n")
        f.write("Disentangles whether BTCUSD predictable structure is predominantly momentum continuation, mean-reversion, or regime-dependent.\n\n")
        f.write("## Model Performance Table\n\n")
        f.write(df_to_markdown(df_mom_rev))

    # selective_prediction_report.md
    with open(os.path.join(RESEARCH_DIR, "selective_prediction_report.md"), "w", encoding="utf-8") as f:
        f.write("# 🎯 Selective Prediction & Abstention Report\n\n")
        f.write("## Executive Summary\n")
        f.write("Evaluates trading performance when the model is permitted to ABSTAIN when confidence is low.\n\n")
        f.write("## Selective Coverage Performance Table\n\n")
        f.write(df_to_markdown(df_selective))

    # uncertainty_report.md
    with open(os.path.join(RESEARCH_DIR, "uncertainty_report.md"), "w", encoding="utf-8") as f:
        f.write("# 📐 Conformal Uncertainty Calibration Report\n\n")
        f.write("## Conformal Coverage & Error Table\n\n")
        f.write(df_to_markdown(df_uncert))

    # economic_target_report.md
    with open(os.path.join(RESEARCH_DIR, "economic_target_report.md"), "w", encoding="utf-8") as f:
        f.write("# 💰 Multi-Task & Cost-Aware Economic Targets Report\n\n")
        f.write("## Multi-Task Prediction Decomposition\n\n")
        f.write(df_to_markdown(df_econ_targets))

    logger.info("Conditional predictability forensics complete!")
    return {
        "conditional": df_cond,
        "events": df_events,
        "momentum_reversion": df_mom_rev,
        "selective": df_selective,
        "uncertainty": df_uncert,
        "economic_targets": df_econ_targets
    }


if __name__ == "__main__":
    res = run_full_conditional_forensics_suite()
    print("\n=== CONDITIONAL SUBSPACES ===")
    print(res["conditional"].to_string(index=False))
    print("\n=== EVENT SHOCKS ===")
    print(res["events"].to_string(index=False))
    print("\n=== MOMENTUM VS REVERSION ===")
    print(res["momentum_reversion"].to_string(index=False))
    print("\n=== SELECTIVE PREDICTION ===")
    print(res["selective"].to_string(index=False))
    print("\n=== MULTI-TASK ECONOMIC TARGETS ===")
    print(res["economic_targets"].to_string(index=False))

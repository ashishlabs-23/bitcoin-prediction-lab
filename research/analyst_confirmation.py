"""
research/analyst_confirmation.py — Analyst Layer Confirmation & Independent Holdout Validation
=============================================================================================
Central orchestration suite evaluating:
1. Independent Confirmation Set Evaluation (Models A, B, C, D)
2. Conditional Information Residualization (Distinguishing compression from independent alpha)
3. Horizon-Specialized Models (1-4h, 12-24h, 24-48h)
4. Calibrated Economic Execution, Thresholds & Cost Sensitivity
5. Monthly & Regime Stability + Block Bootstrap (10,000 resamples)
6. Multiple Testing Accounting & DSR (K = 77 + K_phase)
7. Manifest & Markdown Report Generation
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
from research.conditional_information import evaluate_conditional_analyst_information
from research.horizon_models import evaluate_horizon_specialized_models
from research.analyst_economic_test import run_threshold_and_cost_sweep
from research.analyst_stability import evaluate_analyst_regime_and_monthly_stability, run_block_bootstrap_and_permutation_test
from research.multiple_testing import ResearchTrialTracker
from validation.purged_split import PurgedWalkForwardSplit

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AnalystConfirmation")

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


def run_analyst_confirmation_suite() -> Dict[str, Any]:
    """Executes the complete analyst confirmation and holdout validation suite."""
    trial_tracker = ResearchTrialTracker()
    # Record previous historical trials
    trial_tracker.trials["n_total_features_tested"] = 73
    trial_tracker.trials["n_configurations_tested"] = 7
    trial_tracker.trials["n_horizons_tested"] = 5
    trial_tracker.trials["n_models_tested"] = 7

    logger.info("1. Loading historical research dataset (3,000 hourly candles)...")
    df_raw_merged, close = load_and_prepare_dataset(n_total_bars=3000)

    # 24h 2.0x Triple Barrier target with Intrabar High/Low
    vol = compute_point_in_time_volatility(close, window=24).fillna(0.015)
    target_df, _ = triple_barrier_label_intrabar(df_raw_merged, vol, pt_mult=2.0, sl_mult=2.0, max_bars=24)

    valid_mask = ~target_df['label'].isna()
    df_clean = df_raw_merged.loc[valid_mask].copy()
    target_clean = target_df.loc[valid_mask].copy()

    # Map labels: 1.0 (BUY) -> 0, -1.0 (SELL) -> 1, 0.0 (HOLD) -> 2
    labels = np.where(target_clean['label'] == 1.0, 0, np.where(target_clean['label'] == -1.0, 1, 2)).astype(np.int64)
    fwd_rets = target_clean['ret'].values

    # Feature sets
    base_cols = [c for c in df_clean.columns if c not in ['available_time', 'regime', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df_raw = df_clean[base_cols].copy()
    df_analyst = generate_all_analyst_factors(df_clean)

    # Minimal Signal Set (Pruned 6 top uncorrelated factors)
    minimal_cols = ['tech_trend_score', 'tech_momentum_score', 'tech_breakout_score', 'of_imbalance_score', 'deriv_funding_pressure', 'sent_sentiment_score']
    df_minimal = df_analyst[minimal_cols].copy()

    models_dict = {
        "MODEL A (Raw Technical Features)": df_raw,
        "MODEL B (Analyst Factors Only)": df_analyst,
        "MODEL C (Raw Technical + Analyst Factors)": pd.concat([df_raw, df_analyst], axis=1),
        "MODEL D (Minimal Signal Set - 6 Factors)": df_minimal
    }

    # Strict partition: Walk-Forward CV (first 2,694 bars) vs Untouched Confirmation Holdout (last 250 bars)
    n_total = len(df_clean)
    holdout_size = 250
    cv_end = n_total - holdout_size

    df_cv = df_clean.iloc[:cv_end]
    labels_cv = labels[:cv_end]
    rets_cv = fwd_rets[:cv_end]

    df_holdout = df_clean.iloc[cv_end:]
    labels_holdout = labels[cv_end:]
    rets_holdout = fwd_rets[cv_end:]

    holdout_start = df_holdout.index[0]
    holdout_end = df_holdout.index[-1]
    logger.info(f"Independent Confirmation Set: {len(df_holdout)} bars ({holdout_start} to {holdout_end})")

    logger.info("2. Evaluating Models A, B, C, D on Walk-Forward CV & Independent Confirmation Holdout...")
    ts_cv = pd.Series(pd.to_datetime(df_cv.index, utc=True))
    t1_cv = pd.Series(pd.to_datetime(target_clean['t1'].iloc[:cv_end].values, utc=True))
    splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=24)
    splits = list(splitter.split(ts_cv, t1_cv))

    confirmation_records = []

    for m_name, feat_df in models_dict.items():
        X_all = feat_df.values.astype(np.float32)
        n_f = feat_df.shape[1]

        # 1. Walk-Forward CV Performance
        wf_aucs = []
        wf_baccs = []
        wf_mccs = []
        wf_briers = []
        wf_sharpes = []
        wf_nets = []

        for train_idx, test_idx in splits:
            mean_X = np.nanmean(X_all[train_idx], axis=0, keepdims=True)
            std_X = np.nanstd(X_all[train_idx], axis=0, keepdims=True) + 1e-6

            X_tr = np.nan_to_num((X_all[train_idx] - mean_X) / std_X, nan=0.0)
            X_te = np.nan_to_num((X_all[test_idx] - mean_X) / std_X, nan=0.0)

            y_tr = labels_cv[train_idx]
            y_te = labels_cv[test_idx]
            r_te = rets_cv[test_idx]

            clf = LogisticRegression(C=1.0, max_iter=500, class_weight='balanced', random_state=42)
            clf.fit(X_tr, y_tr)

            probs = clf.predict_proba(X_te)
            if probs.shape[1] < 3:
                p_full = np.zeros((len(test_idx), 3))
                for idx_c, c in enumerate(clf.classes_):
                    p_full[:, c] = probs[:, idx_c]
                probs = p_full

            preds = clf.predict(X_te)
            try:
                auc = float(roc_auc_score(y_te, probs, multi_class='ovr'))
            except Exception:
                auc = 0.50

            bacc = float(balanced_accuracy_score(y_te, preds))
            mcc = float(matthews_corrcoef(y_te, preds))

            y_oh = np.zeros((len(test_idx), 3))
            for i, c in enumerate(y_te):
                y_oh[i, c] = 1.0
            brier = float(np.mean(np.sum((probs - y_oh) ** 2, axis=1)))

            signs = np.where(preds == 0, 1.0, np.where(preds == 1, -1.0, 0.0))
            net_rets = signs * r_te - (0.0014 * (signs != 0.0))
            sr = float((net_rets.mean() / (net_rets.std() + 1e-6)) * np.sqrt(8766.0))

            wf_aucs.append(auc)
            wf_baccs.append(bacc)
            wf_mccs.append(mcc)
            wf_briers.append(brier)
            wf_sharpes.append(sr)
            wf_nets.append(net_rets.mean())

        # 2. Independent Confirmation Holdout Evaluation (Trained on full CV partition)
        mean_cv = np.nanmean(X_all[:cv_end], axis=0, keepdims=True)
        std_cv = np.nanstd(X_all[:cv_end], axis=0, keepdims=True) + 1e-6

        X_train_full = np.nan_to_num((X_all[:cv_end] - mean_cv) / std_cv, nan=0.0)
        X_holdout = np.nan_to_num((X_all[cv_end:] - mean_cv) / std_cv, nan=0.0)

        clf_holdout = LogisticRegression(C=1.0, max_iter=500, class_weight='balanced', random_state=42)
        clf_holdout.fit(X_train_full, labels_cv)

        probs_ho = clf_holdout.predict_proba(X_holdout)
        if probs_ho.shape[1] < 3:
            p_full = np.zeros((len(labels_holdout), 3))
            for idx_c, c in enumerate(clf_holdout.classes_):
                p_full[:, c] = probs_ho[:, idx_c]
            probs_ho = p_full

        preds_ho = clf_holdout.predict(X_holdout)
        try:
            auc_ho = float(roc_auc_score(labels_holdout, probs_ho, multi_class='ovr'))
        except Exception:
            auc_ho = 0.50

        bacc_ho = float(balanced_accuracy_score(labels_holdout, preds_ho))
        mcc_ho = float(matthews_corrcoef(labels_holdout, preds_ho))

        signs_ho = np.where(preds_ho == 0, 1.0, np.where(preds_ho == 1, -1.0, 0.0))
        net_ho = signs_ho * rets_holdout - (0.0014 * (signs_ho != 0.0))
        sr_ho = float((net_ho.mean() / (net_ho.std() + 1e-6)) * np.sqrt(8766.0))

        trial_tracker.record_experiment(m_name, n_models=1, n_horizons=1, n_configs=2)

        confirmation_records.append({
            "Model Variant": m_name,
            "Features": n_f,
            "CV Mean AUC": round(float(np.mean(wf_aucs)), 4),
            "CV AUC Std": round(float(np.std(wf_aucs)), 4),
            "CV Balanced Acc": round(float(np.mean(wf_baccs)), 4),
            "CV MCC": round(float(np.mean(wf_mccs)), 4),
            "CV Cost-Adj Sharpe": round(float(np.mean(wf_sharpes)), 4),
            "Holdout AUC": round(auc_ho, 4),
            "Holdout Balanced Acc": round(bacc_ho, 4),
            "Holdout MCC": round(mcc_ho, 4),
            "Holdout Cost-Adj Sharpe": round(sr_ho, 4),
            "Holdout Net Expectancy ($10 base)": round(float(10.0 * net_ho.mean()), 4)
        })

    df_conf = pd.DataFrame(confirmation_records)
    df_conf.to_csv(os.path.join(RESULTS_DIR, "analyst_confirmation.csv"), index=False)

    # 3. Conditional Information Residualization Test
    logger.info("3. Running conditional information residualization test...")
    df_cond, cond_meta = evaluate_conditional_analyst_information(df_raw, df_analyst, close, horizon_bars=24)
    df_cond.to_csv(os.path.join(RESULTS_DIR, "analyst_factor_incremental.csv"), index=False)

    # 4. Horizon-Specialized Models
    logger.info("4. Evaluating horizon-specialized models...")
    df_horizons, _ = evaluate_horizon_specialized_models(pd.concat([df_raw, df_analyst], axis=1), close)
    df_horizons.to_csv(os.path.join(RESULTS_DIR, "horizon_model_results.csv"), index=False)

    # 5. Economic Execution & Threshold Sweep
    logger.info("5. Running threshold and cost-sensitivity sweep...")
    df_thresh, df_cost, econ_meta = run_threshold_and_cost_sweep(df_analyst, labels, fwd_rets)
    df_thresh.to_csv(os.path.join(RESULTS_DIR, "analyst_economic_results.csv"), index=False)

    # 6. Monthly & Regime Stability + Block Bootstrap
    logger.info("6. Running stability audit and block bootstrap...")
    df_mon, df_reg = evaluate_analyst_regime_and_monthly_stability(df_analyst, close, df_clean.get('regime', pd.Series('Sideways', index=df_clean.index)))
    df_mon.to_csv(os.path.join(RESULTS_DIR, "analyst_stability.csv"), index=False)

    boot_meta = run_block_bootstrap_and_permutation_test(labels_holdout, probs_ho, rets_holdout)

    # 7. Multiple Testing Accounting Manifest
    manifest_path = os.path.join(RESULTS_DIR, "analyst_confirmation_manifest.json")
    trial_tracker.export_manifest(manifest_path)

    # 8. Markdown Reports Generation
    logger.info("7. Generating all 4 markdown research reports...")

    # analyst_confirmation_report.md
    with open(os.path.join(RESEARCH_DIR, "analyst_confirmation_report.md"), "w", encoding="utf-8") as f:
        f.write("# 🏆 Analyst Layer Confirmation & Independent Holdout Report\n\n")
        f.write("## Executive Summary\n")
        f.write("Evaluates the deterministic Analyst Layer against raw features across 5 walk-forward CV folds and a strictly untouched independent confirmation holdout set ($n=250$).\n\n")
        f.write("## Model Confirmation Performance Table\n\n")
        f.write(df_to_markdown(df_conf))
        f.write("\n\n## Independent Holdout Block Bootstrap & Permutation Test\n\n")
        f.write(f"- **Holdout Observed AUC**: `{boot_meta['observed_auc']:.4f}`\n")
        f.write(f"- **Bootstrap 95% Confidence Interval**: `[{boot_meta['bootstrap_auc_95_ci'][0]:.4f}, {boot_meta['bootstrap_auc_95_ci'][1]:.4f}]` (Excludes 0.50: **{boot_meta['ci_excludes_random_0_5']}**)\n")
        f.write(f"- **Block Permutation p-value**: `{boot_meta['block_permutation_p_value']:.4f}` (Rejects null: **{boot_meta['rejects_null_at_0_05']}**)\n")

    # conditional_signal_report.md
    with open(os.path.join(RESEARCH_DIR, "conditional_signal_report.md"), "w", encoding="utf-8") as f:
        f.write("# 🔬 Conditional Information & Factor Residualization Report\n\n")
        f.write("## Executive Summary\n")
        f.write("Tests whether Analyst factors contain genuinely new independent information or represent non-linear representation compression of raw OHLCV features.\n\n")
        f.write("## Factor Residualization Table\n\n")
        f.write(df_to_markdown(df_cond))
        f.write(f"\n\n### Primary Determination: **{cond_meta['dominant_role']}**\n")
        f.write(f"- Mean Raw Factor IC: `{cond_meta['mean_raw_factor_ic']:.4f}`\n")
        f.write(f"- Mean Residual Factor IC: `{cond_meta['mean_residual_factor_ic']:.4f}`\n")

    # horizon_specialization_report.md
    with open(os.path.join(RESEARCH_DIR, "horizon_specialization_report.md"), "w", encoding="utf-8") as f:
        f.write("# ⏳ Horizon-Specialized Models & Multi-Head Report\n\n")
        f.write("## Specialized Model Performance\n\n")
        f.write(df_to_markdown(df_horizons))

    # analyst_economic_report.md
    with open(os.path.join(RESEARCH_DIR, "analyst_economic_report.md"), "w", encoding="utf-8") as f:
        f.write("# 💰 Analyst Layer Economic & Threshold Execution Report\n\n")
        f.write("## Confidence Threshold Execution (14 bps round-trip drag)\n\n")
        f.write(df_to_markdown(df_thresh))
        f.write("\n\n## Round-Trip Cost Sensitivity\n\n")
        f.write(df_to_markdown(df_cost))
        f.write(f"\n\n**Break-Even Round-Trip Cost**: `{econ_meta['break_even_cost_bps']:.2f} bps`\n")

    logger.info("Analyst confirmation suite complete!")
    return {
        "confirmation": df_conf,
        "conditional": df_cond,
        "horizons": df_horizons,
        "economic_thresh": df_thresh,
        "stability": df_mon,
        "bootstrap": boot_meta
    }


if __name__ == "__main__":
    res = run_analyst_confirmation_suite()
    print("\n=== CONFIRMATION TABLE ===")
    print(res["confirmation"].to_string(index=False))
    print("\n=== BOOTSTRAP STATS ===")
    print(res["bootstrap"])

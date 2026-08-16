"""
Ablation Study Module for bitcoin-prediction-lab.

Evaluates incremental feature importance by comparing cumulative feature groups:
1. ohlcv_only (base OHLCV price & volume columns)
2. plus_technical (OHLCV + technical indicators)
3. plus_derivatives (OHLCV + technical + derivatives features)
"""

import os
import sys
from typing import Dict, List
import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, brier_score_loss
from xgboost import XGBClassifier

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR
from models.train_baselines import make_dataset
from validation.purged_split import PurgedWalkForwardSplit


def run_ablation(feature_groups: Dict[str, List[str]]) -> pd.DataFrame:
    """
    feature_groups example: {'ohlcv_only': [...col names...], 'plus_technical':
    [...], 'plus_derivatives': [...]} — cumulative column sets.
    For each group, subsets X to those columns, runs run_model_ladder's
    XGBoost path only (for runtime), records mean OOS roc_auc and brier.
    Returns a DataFrame ranked by roc_auc descending, saved to
    {RESULTS_DIR}/ablation_results.csv.
    """
    X, y, t1 = make_dataset(horizon_bars=24)
    timestamps = pd.Series(X.index)
    splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=24)

    results = []

    for group_name, cols in feature_groups.items():
        valid_cols = [c for c in cols if c in X.columns]
        if not valid_cols:
            print(f"Warning: No valid columns found for feature group '{group_name}'.")
            continue

        X_sub = X[valid_cols]

        aucs = []
        briers = []

        for train_idx, test_idx in splitter.split(timestamps, t1):
            X_tr, y_tr = X_sub.iloc[train_idx], y.iloc[train_idx]
            X_te, y_te = X_sub.iloc[test_idx], y.iloc[test_idx]

            if len(np.unique(y_tr)) < 2 or len(np.unique(y_te)) < 2:
                continue

            model = XGBClassifier(n_estimators=100, eval_metric='logloss', random_state=42, n_jobs=-1)
            model.fit(X_tr, y_tr)
            p_te = model.predict_proba(X_te)[:, 1]

            try:
                auc = roc_auc_score(y_te, p_te)
                brier = brier_score_loss(y_te, p_te)
                aucs.append(auc)
                briers.append(brier)
            except Exception:
                pass

        mean_auc = float(np.mean(aucs)) if len(aucs) > 0 else np.nan
        mean_brier = float(np.mean(briers)) if len(briers) > 0 else np.nan

        results.append({
            'group': group_name,
            'n_features': len(valid_cols),
            'roc_auc': mean_auc,
            'brier': mean_brier
        })

    res_df = pd.DataFrame(results).sort_values('roc_auc', ascending=False).reset_index(drop=True)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_csv = os.path.join(RESULTS_DIR, "ablation_results.csv")
    res_df.to_csv(out_csv, index=False)
    print(f"Saved ablation study results to {out_csv}")

    return res_df


if __name__ == "__main__":
    print("Inspecting feature matrix columns for ablation study...")
    X_sample, _, _ = make_dataset(horizon_bars=24)
    all_cols = X_sample.columns.tolist()
    print("Available columns in X:", all_cols)

    ohlcv_cols = [c for c in ['open', 'high', 'low', 'close', 'volume'] if c in all_cols]
    tech_cols = [c for c in ['ret_1h', 'ret_4h', 'ret_24h', 'rsi_14', 'macd', 'macd_signal', 'sma_ratio_20', 'sma_ratio_50', 'realized_vol_24h', 'volume_zscore_24h'] if c in all_cols]
    deriv_cols = [c for c in ['funding_rate', 'funding_rate_change_24h', 'open_interest', 'oi_pct_change_24h'] if c in all_cols]

    feature_groups = {
        'ohlcv_only': ohlcv_cols,
        'plus_technical': ohlcv_cols + tech_cols,
        'plus_derivatives': ohlcv_cols + tech_cols + deriv_cols
    }

    print("\nRunning ablation study across cumulative feature groups...")
    ablation_df = run_ablation(feature_groups)

    print("\n--- Ablation Study Results (Ranked by ROC AUC Descending) ---")
    print(ablation_df)

    has_3_rows = len(ablation_df) == 3
    no_nans_auc = not ablation_df['roc_auc'].isna().any()

    if has_3_rows and no_nans_auc:
        print("\nPASS: Ablation study completed with 3 rows and valid ROC AUC scores.")
    else:
        print("\nFAIL: Ablation study checks failed.")

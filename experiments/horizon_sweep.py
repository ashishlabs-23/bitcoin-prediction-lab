"""
Prediction Horizon Sweep Module for bitcoin-prediction-lab.

Evaluates model performance across multiple forward prediction horizons:
1h, 4h, 8h, 12h, 24h, 48h, 72h.
For each horizon, re-computes triple barrier labels, evaluates XGBoost cross-validation,
runs backtest simulation, and saves results to experiments/results/horizon_sweep.csv.
"""

import os
import sys
from typing import List
import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, brier_score_loss
from xgboost import XGBClassifier

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR, DATA_PROCESSED_DIR
from features.build_features import load_raw, compute_technical_features, compute_derivatives_features, merge_features
from labeling.targets import realized_vol, triple_barrier_label
from validation.purged_split import PurgedWalkForwardSplit
from backtest.simulate import position_size, run_backtest


def run_horizon_sweep(horizons: List[int] = [1, 4, 8, 12, 24, 48, 72]) -> pd.DataFrame:
    """
    Runs model training and backtesting across multiple prediction horizons.
    Returns a DataFrame of performance metrics per horizon.
    """
    features_df = pd.read_parquet(os.path.join(DATA_PROCESSED_DIR, "features.parquet"), engine="pyarrow")
    features_clean = features_df.dropna().copy()

    vol = realized_vol(features_clean['close'], window=24)
    feature_cols = [c for c in features_clean.columns if c not in ['timestamp', 'available_time']]

    results = []

    for h in horizons:
        lbl_df = triple_barrier_label(features_clean['close'], vol, pt_mult=2.0, sl_mult=2.0, max_bars=h)

        X = features_clean[feature_cols].copy()
        y_raw = lbl_df['label']
        t1 = lbl_df['t1']

        valid_mask = ~y_raw.isna()
        X = X.loc[valid_mask].reset_index(drop=True)
        y = (y_raw.loc[valid_mask] == 1.0).astype(int).reset_index(drop=True)
        t1_clean = t1.loc[valid_mask].reset_index(drop=True)
        timestamps_clean = features_clean.loc[valid_mask, 'timestamp'].reset_index(drop=True)
        prices_clean = features_clean.loc[valid_mask, 'close'].reset_index(drop=True)

        if len(X) < 100:
            print(f"Warning: Insufficient valid samples ({len(X)}) for horizon {h}h.")
            continue

        splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=max(h, 12))

        aucs = []
        briers = []
        all_test_preds = []
        all_test_indices = []

        for train_idx, test_idx in splitter.split(timestamps_clean, t1_clean):
            X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
            X_te, y_te = X.iloc[test_idx], y.iloc[test_idx]

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
                all_test_preds.extend(p_te)
                all_test_indices.extend(test_idx)
            except Exception:
                pass

        mean_auc = float(np.mean(aucs)) if len(aucs) > 0 else np.nan
        mean_brier = float(np.mean(briers)) if len(briers) > 0 else np.nan

        # Backtest simulation on concatenated test fold predictions
        if len(all_test_preds) > 0:
            test_prices = prices_clean.iloc[all_test_indices]
            signals = position_size(np.array(all_test_preds), method="prob_scaled")
            pos_series = pd.Series(signals, index=test_prices.index)
            bt = run_backtest(test_prices, pos_series, fee_bps=5.0, slippage_bps=5.0)

            total_ret = bt['total_return']
            sharpe = bt['sharpe']
            max_dd = bt['max_drawdown']
            turnover = bt['turnover']
        else:
            total_ret, sharpe, max_dd, turnover = 0.0, 0.0, 0.0, 0.0

        results.append({
            'horizon_bars': h,
            'horizon_name': f"{h}H",
            'n_samples': len(X),
            'roc_auc': mean_auc,
            'brier': mean_brier,
            'total_return': total_ret,
            'sharpe': sharpe,
            'max_drawdown': max_dd,
            'turnover': turnover
        })

    res_df = pd.DataFrame(results).sort_values('roc_auc', ascending=False).reset_index(drop=True)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_csv = os.path.join(RESULTS_DIR, "horizon_sweep.csv")
    res_df.to_csv(out_csv, index=False)
    print(f"Saved horizon sweep results to {out_csv}")

    return res_df


if __name__ == "__main__":
    print("\nRunning Prediction Horizon Sweep (1h, 4h, 8h, 12h, 24h, 48h, 72h)...")
    sweep_df = run_horizon_sweep()

    print("\n--- Prediction Horizon Sweep Results (Ranked by ROC AUC Descending) ---")
    print(sweep_df[['horizon_name', 'n_samples', 'roc_auc', 'brier', 'total_return', 'sharpe', 'max_drawdown']].to_string(index=False))

    if len(sweep_df) > 0 and not sweep_df['roc_auc'].isna().all():
        print("\nPASS: Prediction horizon sweep completed successfully.")
    else:
        print("\nFAIL: Prediction horizon sweep failed.")

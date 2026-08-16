"""
Baseline Model Ladder Module for bitcoin-prediction-lab.

Evaluates baseline machine learning models (No Skill, Persistence, Logistic Regression,
Random Forest, and XGBoost) using Purged Walk-Forward Cross-Validation.
"""

import os
import sys
from typing import Tuple
import pandas as pd
import numpy as np

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, brier_score_loss

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_PROCESSED_DIR, RESULTS_DIR
from labeling.targets import triple_barrier_label, realized_vol
from validation.purged_split import PurgedWalkForwardSplit


def make_dataset(horizon_bars: int = 24) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Loads features.parquet, computes triple_barrier_label with default params,
    aligns X (feature columns only — drop timestamp/available_time from the
    feature matrix, keep them for indexing), y (binary: 1 if label==1, 0 if
    label in (-1, 0) — collapse to "profitable long" vs "not" for this baseline
    pass; note this simplification in a comment), and t1 (for the splitter).
    Drops rows where label is NaN. Returns (X, y, t1) with aligned indices.
    """
    features_path = os.path.join(DATA_PROCESSED_DIR, "features.parquet")
    if not os.path.exists(features_path):
        raise FileNotFoundError(f"Features file not found at {features_path}. Run features/build_features.py first.")

    df = pd.read_parquet(features_path, engine="pyarrow")
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

    close = pd.Series(df['close'].values, index=df['timestamp'], name="close")
    vol = realized_vol(close, window=24)
    tb_df = triple_barrier_label(close, vol, pt_mult=2.0, sl_mult=2.0, max_bars=horizon_bars)

    # Binary classification target: 1 if triple-barrier label is 1 (profitable long hit upper barrier),
    # 0 if label in (-1, 0) (stop loss hit or vertical timeout). This simplifies multi-class labeling
    # to a "profitable long" vs "not" task for baseline model ladder evaluation.
    y_series = (tb_df['label'] == 1.0).astype(int)
    t1_series = tb_df['t1']

    # Exclude non-feature columns (timestamp/available_time) and microstructure features requiring L2 orderbook
    microstructure_cols = ['bid_ask_spread_pct', 'order_book_imbalance', 'taker_buy_ratio', 'vpin']
    feature_cols = [c for c in df.columns if c not in ['timestamp', 'available_time'] + microstructure_cols]
    X_df = df.set_index('timestamp')[feature_cols].copy()

    # Drop rows where triple barrier label is NaN (undecidable end of series)
    valid_mask = ~tb_df['label'].isna()
    X = X_df.loc[valid_mask]
    y = y_series.loc[valid_mask]
    t1 = t1_series.loc[valid_mask]

    return X, y, t1


def make_meta_dataset(horizon_bars: int = 24) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """
    Creates a Meta-Labeling Dataset:
    1. Primary Rule Signal: EMA20/EMA50 crossover (or sma_ratio_20 sign).
       primary_signal = +1 (LONG) if sma_ratio_20 > 0 else -1 (SHORT).
    2. Meta-Label Target (y_meta):
       1 if triple barrier outcome matches primary_signal direction (TP hit), 0 otherwise.
    Returns (X, y_meta, primary_signal, t1).
    """
    features_path = os.path.join(DATA_PROCESSED_DIR, "features.parquet")
    if not os.path.exists(features_path):
        raise FileNotFoundError(f"Features file not found at {features_path}.")

    df = pd.read_parquet(features_path, engine="pyarrow")
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

    close = pd.Series(df['close'].values, index=df['timestamp'], name="close")
    vol = realized_vol(close, window=24)
    tb_df = triple_barrier_label(close, vol, pt_mult=2.0, sl_mult=2.0, max_bars=horizon_bars)

    # Primary rule-based signal: +1 (LONG) if sma_ratio_20 > 0 else -1 (SHORT)
    sma_ratio = df.set_index('timestamp')['sma_ratio_20']
    primary_sig = np.where(sma_ratio > 0, 1.0, -1.0)
    primary_series = pd.Series(primary_sig, index=df['timestamp'])

    # Meta-label: 1 if triple-barrier label matches primary signal direction, 0 otherwise
    meta_label = (tb_df['label'] == primary_series).astype(int)
    t1_series = tb_df['t1']

    feature_cols = [c for c in df.columns if c not in ['timestamp', 'available_time']]
    X_df = df.set_index('timestamp')[feature_cols].copy()

    valid_mask = ~tb_df['label'].isna()
    X = X_df.loc[valid_mask]
    y_meta = meta_label.loc[valid_mask]
    prim_sig = primary_series.loc[valid_mask]
    t1 = t1_series.loc[valid_mask]

    return X, y_meta, prim_sig, t1


def run_model_ladder(
    X: pd.DataFrame,
    y: pd.Series,
    t1: pd.Series,
    n_splits: int = 5,
    embargo_bars: int = 24
) -> pd.DataFrame:
    """
    For each fold from PurgedWalkForwardSplit, train and evaluate:
      - no_skill: predicts the train fold's positive class base rate for every
        test row
      - persistence: predicts 1 if the most recent ret_1h in X > 0 else 0
      - logreg: sklearn LogisticRegression (with StandardScaler in a Pipeline)
      - random_forest: sklearn RandomForestClassifier(n_estimators=300)
      - xgboost: xgboost.XGBClassifier (reasonable defaults, eval_metric='logloss')
    For each (fold, model) pair compute accuracy, roc_auc, and brier_score_loss
    on the test fold. Handle the case where a test fold has only one class
    present (roc_auc undefined) by recording NaN for that metric, not crashing.
    Returns a long-format DataFrame: columns ['fold', 'model', 'accuracy',
    'roc_auc', 'brier'].
    Also saves this DataFrame to {RESULTS_DIR}/baseline_ladder_results.csv.
    """
    timestamps = pd.Series(X.index)
    splitter = PurgedWalkForwardSplit(n_splits=n_splits, embargo_bars=embargo_bars)

    results = []

    for fold, (train_idx, test_idx) in enumerate(splitter.split(timestamps, t1)):
        X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
        X_te, y_te = X.iloc[test_idx], y.iloc[test_idx]

        models = {
            'no_skill': 'no_skill',
            'persistence': 'persistence',
            'logreg': Pipeline([('scaler', StandardScaler()), ('clf', LogisticRegression(max_iter=1000, random_state=42))]),
            'random_forest': RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1),
            'xgboost': XGBClassifier(n_estimators=100, eval_metric='logloss', random_state=42, n_jobs=-1)
        }

        train_base_rate = y_tr.mean()

        for m_name, model in models.items():
            if m_name == 'no_skill':
                p_te = np.full(len(y_te), train_base_rate)
                y_pred = (p_te >= 0.5).astype(int)
            elif m_name == 'persistence':
                if 'ret_1h' in X_te.columns:
                    y_pred = (X_te['ret_1h'] > 0).astype(int)
                else:
                    y_pred = np.zeros(len(y_te), dtype=int)
                p_te = y_pred.astype(float)
            else:
                model.fit(X_tr, y_tr)
                p_te = model.predict_proba(X_te)[:, 1]
                y_pred = model.predict(X_te)

            acc = accuracy_score(y_te, y_pred)
            brier = brier_score_loss(y_te, p_te)

            if len(np.unique(y_te)) < 2:
                auc = np.nan
            else:
                try:
                    auc = roc_auc_score(y_te, p_te)
                except Exception:
                    auc = np.nan

            results.append({
                'fold': fold,
                'model': m_name,
                'accuracy': acc,
                'roc_auc': auc,
                'brier': brier
            })

    results_df = pd.DataFrame(results)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_csv = os.path.join(RESULTS_DIR, "baseline_ladder_results.csv")
    results_df.to_csv(out_csv, index=False)
    print(f"Saved baseline ladder results to {out_csv}")

    return results_df


if __name__ == "__main__":
    print("Building dataset...")
    X, y, t1 = make_dataset(horizon_bars=24)
    print(f"Dataset shape: X={X.shape}, y={y.shape}, t1={t1.shape}")

    print("\nRunning baseline model ladder cross-validation...")
    results_df = run_model_ladder(X, y, t1, n_splits=5, embargo_bars=24)

    print("\nFull Results (25 rows expected):")
    print(results_df)

    summary_df = results_df.groupby('model')[['roc_auc', 'accuracy', 'brier']].mean().sort_values('roc_auc', ascending=False)
    print("\n--- Model Summary Table (Mean Across Folds, Sorted by ROC AUC Descending) ---")
    print(summary_df)

    ml_models = ['logreg', 'random_forest', 'xgboost']
    completed_folds = results_df[results_df['model'].isin(ml_models)]['fold'].nunique()
    ml_completed_all = completed_folds == 5

    if ml_completed_all and len(results_df) >= 25:
        print("\nPASS: Baseline model ladder completed all folds without error.")
    else:
        print("\nFAIL: Baseline model ladder checks failed.")

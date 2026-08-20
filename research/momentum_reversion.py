"""
research/momentum_reversion.py — Momentum vs Mean-Reversion Decomposition Engine
=================================================================================
Disentangles whether BTCUSD predictability is predominantly:
1. MODEL A: Momentum Continuation (Trend alignment, Volume expansion, Breakout intensity)
2. MODEL B: Mean Reversion (RSI extremes <30 or >70, Bollinger Band extension, Standardization spikes)
3. MODEL C: Regime-Conditioned Hybrid
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score, balanced_accuracy_score, matthews_corrcoef
from typing import Dict, List, Tuple, Any

from validation.purged_split import PurgedWalkForwardSplit


def evaluate_momentum_vs_mean_reversion(
    df: pd.DataFrame,
    close: pd.Series,
    horizon_bars: int = 24,
    n_splits: int = 5,
    embargo_bars: int = 24
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates pure Momentum vs pure Mean-Reversion across purged walk-forward folds.
    """
    close_aligned = close.loc[df.index]
    fwd_ret = np.log(close_aligned.shift(-horizon_bars) / close_aligned).fillna(0.0)
    vol = np.log(close_aligned / close_aligned.shift(1)).rolling(24).std().fillna(0.015)
    y_dir = np.where(fwd_ret > 1.5 * vol, 0, np.where(fwd_ret < -1.5 * vol, 1, 2))

    # Feature Subspaces
    mom_cols = [c for c in ['ret_1h', 'ret_4h', 'ret_24h', 'sma_ratio_20', 'sma_ratio_50', 'vwap_ratio', 'vol_z_24h', 'tech_trend_score', 'tech_breakout_score'] if c in df.columns]
    rev_cols = [c for c in ['rsi_14', 'stoch_k', 'stoch_d', 'bb_pct_20', 'bb_width_20', 'tech_momentum_score', 'deriv_funding_pressure'] if c in df.columns]

    if not mom_cols:
        mom_cols = df.columns[:5]
    if not rev_cols:
        rev_cols = df.columns[5:10]

    configs = [
        {"name": "MODEL A (Pure Momentum Continuation)", "cols": mom_cols},
        {"name": "MODEL B (Pure Mean Reversion)", "cols": rev_cols},
        {"name": "MODEL C (Hybrid Confluence)", "cols": list(set(mom_cols + rev_cols))}
    ]

    ts_series = pd.Series(pd.to_datetime(df.index, utc=True))
    t1_series = pd.Series(pd.to_datetime(df.index, utc=True) + pd.Timedelta(hours=24))
    splitter = PurgedWalkForwardSplit(n_splits=n_splits, embargo_bars=embargo_bars)
    splits = list(splitter.split(ts_series, t1_series))

    records = []

    for cfg in configs:
        X_mat = df[cfg["cols"]].values.astype(np.float32)
        fold_aucs = []
        fold_baccs = []
        fold_mccs = []
        fold_sharpes = []
        fold_nets = []

        for train_idx, test_idx in splits:
            mean_X = np.nanmean(X_mat[train_idx], axis=0, keepdims=True)
            std_X = np.nanstd(X_mat[train_idx], axis=0, keepdims=True) + 1e-6

            X_tr = np.nan_to_num((X_mat[train_idx] - mean_X) / std_X, nan=0.0)
            X_te = np.nan_to_num((X_mat[test_idx] - mean_X) / std_X, nan=0.0)

            y_tr = y_dir[train_idx]
            y_te = y_dir[test_idx]
            r_te = fwd_ret.iloc[test_idx].values

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

            signs = np.where(preds == 0, 1.0, np.where(preds == 1, -1.0, 0.0))
            net_rets = signs * r_te - (0.0014 * (signs != 0.0))
            sr = float((net_rets.mean() / (net_rets.std() + 1e-6)) * np.sqrt(8766.0))

            fold_aucs.append(auc)
            fold_baccs.append(bacc)
            fold_mccs.append(mcc)
            fold_sharpes.append(sr)
            fold_nets.append(net_rets.mean())

        records.append({
            "Hypothesis Model": cfg["name"],
            "Features Used": len(cfg["cols"]),
            "Mean OOS AUC": round(float(np.mean(fold_aucs)), 4),
            "AUC Std": round(float(np.std(fold_aucs)), 4),
            "Mean Balanced Acc": round(float(np.mean(fold_baccs)), 4),
            "Mean MCC": round(float(np.mean(fold_mccs)), 4),
            "Cost-Adjusted Sharpe": round(float(np.mean(fold_sharpes)), 4),
            "Net Expectancy ($10 base)": round(float(10.0 * np.mean(fold_nets)), 4)
        })

    return pd.DataFrame(records), {"dominant_driver": "Mean Reversion" if records[1]["Mean OOS AUC"] > records[0]["Mean OOS AUC"] else "Momentum"}

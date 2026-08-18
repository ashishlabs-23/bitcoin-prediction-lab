"""
Regime Detector Module for bitcoin-prediction-lab.

Maps continuous market states into discrete market regimes:
1. TRENDING_BULL (strong positive trend + positive momentum)
2. TRENDING_BEAR (strong negative trend + negative momentum)
3. HIGH_VOLATILITY (high volatility state)
4. BREAKOUT (elevated leverage / OI expansion + high volume z-score)
5. RANGING (low/medium volatility + neutral trend)

Evaluates baseline model performance per market regime and saves results to experiments/results/regime_performance.csv.
"""

import os
import sys
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, accuracy_score, brier_score_loss
from xgboost import XGBClassifier

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR, DATA_PROCESSED_DIR
from models.market_state import compute_market_states
from models.train_baselines import make_dataset
from validation.purged_split import PurgedWalkForwardSplit
from backtest.simulate import position_size, run_backtest


def predict_regime_probabilities(
    df: pd.DataFrame,
    onchain_valuation: Optional[Dict[str, Any]] = None,
    macro_prior_scale: float = 0.60
) -> pd.DataFrame:
    """
    Computes soft, continuous regime membership probabilities for each row in df.
    Optionally applies macro on-chain cycle bias (MVRV / NUPL) scaled by macro_prior_scale.
    Returns a DataFrame with columns:
    ['HIGH_VOLATILITY', 'BREAKOUT', 'TRENDING_BULL', 'TRENDING_BEAR', 'RANGING']
    where each row sums to 1.0.
    """
    states_df = compute_market_states(df)
    trend = states_df.get('trend_score', pd.Series(0.0, index=df.index)).fillna(0.0).values
    vol_state = states_df.get('volatility_state', pd.Series('MEDIUM', index=df.index)).values
    ret_vol = df.get('realized_vol_24h', pd.Series(0.01, index=df.index)).fillna(0.01).values

    n = len(df)
    logits = np.zeros((n, 5))

    # Regimes: 0: HIGH_VOLATILITY, 1: BREAKOUT, 2: TRENDING_BULL, 3: TRENDING_BEAR, 4: RANGING
    for i in range(n):
        t_val = trend[i]
        v_val = vol_state[i]

        # Logit scaling per regime
        logits[i, 0] = (ret_vol[i] * 100.0) if v_val == 'HIGH' else (ret_vol[i] * 50.0)
        logits[i, 1] = abs(t_val) * 3.0 if (v_val == 'HIGH' or abs(t_val) > 0.2) else abs(t_val) * 1.5
        logits[i, 2] = max(0.0, t_val * 4.0)
        logits[i, 3] = max(0.0, -t_val * 4.0)
        logits[i, 4] = max(0.0, 1.5 - abs(t_val) * 3.0)

    # Apply macro on-chain valuation bias scaled by source reliability/weight
    cycle_phase = None
    influence_weight = 1.0
    if onchain_valuation and isinstance(onchain_valuation, dict):
        cycle_phase = onchain_valuation.get('cycle_phase')
        influence_weight = float(onchain_valuation.get('influence_weight', 1.0))
    elif 'cycle_phase' in df.columns:
        cycle_phase = df['cycle_phase'].iloc[-1]

    if influence_weight > 0.0 and cycle_phase is not None:
        effective_scale = macro_prior_scale * influence_weight
        if cycle_phase == 'CAPITULATION':
            # Macro value zone: soft positive prior on accumulation, soft penalty on late shorting
            logits[:, 2] += effective_scale
            logits[:, 3] = np.maximum(0.0, logits[:, 3] - (effective_scale * 0.67))
        elif cycle_phase == 'EUPHORIA':
            # Macro overextended zone: soft positive prior on high volatility, soft penalty on top chasing
            logits[:, 0] += effective_scale
            logits[:, 2] = np.maximum(0.0, logits[:, 2] - (effective_scale * 0.67))

    # Softmax over logits to convert into smooth probabilities
    exp_logits = np.exp(logits - np.max(logits, axis=1, keepdims=True))
    probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)

    cols = ['HIGH_VOLATILITY', 'BREAKOUT', 'TRENDING_BULL', 'TRENDING_BEAR', 'RANGING']
    return pd.DataFrame(probs, index=df.index, columns=cols)


def classify_regimes(
    df: pd.DataFrame,
    onchain_valuation: Optional[Dict[str, Any]] = None
) -> pd.Series:
    """Classifies each row of df into discrete market regimes with macro on-chain confluence."""
    states_df = compute_market_states(df)

    trend = states_df.get('trend_score', pd.Series(0.0, index=df.index))
    vol_state = states_df.get('volatility_state', pd.Series('MEDIUM', index=df.index))
    mom_state = states_df.get('momentum_state', pd.Series('NEUTRAL', index=df.index))
    lev_state = states_df.get('leverage_state', pd.Series('NORMAL', index=df.index))

    cycle_phase = None
    influence_weight = 1.0
    if onchain_valuation and isinstance(onchain_valuation, dict):
        cycle_phase = onchain_valuation.get('cycle_phase')
        influence_weight = float(onchain_valuation.get('influence_weight', 1.0))
    elif 'cycle_phase' in df.columns:
        cycle_phase = df['cycle_phase'].iloc[-1]

    regimes = []
    for idx in range(len(df)):
        t_val = trend.iloc[idx]
        v_val = vol_state.iloc[idx]
        m_val = mom_state.iloc[idx]
        l_val = lev_state.iloc[idx]

        if v_val == 'HIGH':
            regimes.append('HIGH_VOLATILITY')
        elif l_val == 'ELEVATED' and abs(t_val) > 0.2:
            regimes.append('BREAKOUT')
        elif t_val > 0.15 and m_val != 'NEGATIVE':
            regimes.append('TRENDING_BULL')
        elif t_val < -0.15 and m_val != 'POSITIVE':
            # If in verified macro capitulation value zone, block aggressive bear chasing unless panic breakdown
            if influence_weight > 0.0 and cycle_phase == 'CAPITULATION' and t_val > -0.35:
                regimes.append('RANGING')
            else:
                regimes.append('TRENDING_BEAR')
        else:
            regimes.append('RANGING')

    return pd.Series(regimes, index=df.index, name='regime')



def evaluate_regime_performance() -> pd.DataFrame:
    """
    Evaluates XGBoost cross-validation performance broken down by market regime.
    Returns a summary DataFrame saved to RESULTS_DIR/regime_performance.csv.
    """
    features_df = pd.read_parquet(os.path.join(DATA_PROCESSED_DIR, "features.parquet"))
    features_clean = features_df.dropna().copy()
    features_clean['regime'] = classify_regimes(features_clean)
    features_clean = features_clean.set_index('timestamp')

    X, y, t1 = make_dataset(horizon_bars=24)
    timestamps = pd.Series(X.index)
    prices = features_clean.loc[X.index, 'close'].reset_index(drop=True)
    regimes = features_clean.loc[X.index, 'regime'].reset_index(drop=True)

    splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=24)

    all_y_true = []
    all_y_prob = []
    all_regimes = []
    all_prices = []

    for train_idx, test_idx in splitter.split(timestamps, t1):
        X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
        X_te, y_te = X.iloc[test_idx], y.iloc[test_idx]

        if len(np.unique(y_tr)) < 2 or len(np.unique(y_te)) < 2:
            continue

        model = XGBClassifier(n_estimators=100, eval_metric='logloss', random_state=42, n_jobs=-1)
        model.fit(X_tr, y_tr)
        p_te = model.predict_proba(X_te)[:, 1]

        all_y_true.extend(y_te.values)
        all_y_prob.extend(p_te)
        all_regimes.extend(regimes.iloc[test_idx].values)
        all_prices.extend(prices.iloc[test_idx].values)

    eval_df = pd.DataFrame({
        'y_true': all_y_true,
        'y_prob': all_y_prob,
        'regime': all_regimes,
        'price': all_prices
    })

    regime_records = []

    for reg_name, group in eval_df.groupby('regime'):
        n_samples = len(group)
        if n_samples < 5:
            continue

        y_t = group['y_true'].values
        y_p = group['y_prob'].values

        acc = accuracy_score(y_t, y_p > 0.5)
        brier = brier_score_loss(y_t, y_p)

        try:
            auc = roc_auc_score(y_t, y_p) if len(np.unique(y_t)) > 1 else np.nan
        except Exception:
            auc = np.nan

        signals = position_size(y_p, method="prob_scaled")
        bt = run_backtest(pd.Series(group['price'].values), pd.Series(signals), fee_bps=5.0, slippage_bps=5.0)

        regime_records.append({
            'regime': reg_name,
            'n_samples': n_samples,
            'roc_auc': auc,
            'accuracy': acc,
            'brier': brier,
            'total_return': bt['total_return'],
            'sharpe': bt['sharpe'],
            'max_drawdown': bt['max_drawdown']
        })

    res_df = pd.DataFrame(regime_records).sort_values('roc_auc', ascending=False).reset_index(drop=True)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_csv = os.path.join(RESULTS_DIR, "regime_performance.csv")
    res_df.to_csv(out_csv, index=False)
    print(f"Saved regime performance evaluation to {out_csv}")

    return res_df


if __name__ == "__main__":
    print("\nRunning Regime Performance Evaluation...")
    regime_df = evaluate_regime_performance()

    print("\n--- Regime-Conditional Performance Summary ---")
    print(regime_df[['regime', 'n_samples', 'roc_auc', 'accuracy', 'brier', 'total_return', 'sharpe']].to_string(index=False))

    if len(regime_df) > 0 and not regime_df['roc_auc'].isna().all():
        print("\nPASS: Regime-conditional performance evaluation completed successfully.")
    else:
        print("\nFAIL: Regime evaluation failed.")

"""
Backtest & Strategy Simulation Module for bitcoin-prediction-lab.

Implements position sizing algorithms, backtest execution with 1-bar execution lag,
transaction fee and slippage costs, and cost sensitivity grid evaluations.
"""

import os
import sys
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR
from xgboost import XGBClassifier
from models.train_baselines import make_dataset
from validation.purged_split import PurgedWalkForwardSplit
from models.risk_metrics import sharpe_ratio, maximum_drawdown



def check_position_closure_high_low(
    direction: str,
    tp: float,
    sl: float,
    candle_high: float,
    candle_low: float
) -> Dict[str, Any]:
    """
    Evaluates whether a position was closed on candle high/low prices:
    LONG:  closed if high >= TP or low <= SL
    SHORT: closed if low <= TP or high >= SL
    Returns dict: {'closed': bool, 'reason': 'TP_HIT' | 'SL_HIT' | None, 'close_price': float}
    """
    if tp <= 0 or sl <= 0 or candle_high <= 0 or candle_low <= 0:
        return {'closed': False, 'reason': None, 'close_price': 0.0}

    dir_upper = str(direction).upper()
    if dir_upper == "LONG":
        if candle_high >= tp:
            return {'closed': True, 'reason': 'TP_HIT', 'close_price': tp}
        elif candle_low <= sl:
            return {'closed': True, 'reason': 'SL_HIT', 'close_price': sl}
    elif dir_upper == "SHORT":
        if candle_low <= tp:
            return {'closed': True, 'reason': 'TP_HIT', 'close_price': tp}
        elif candle_high >= sl:
            return {'closed': True, 'reason': 'SL_HIT', 'close_price': sl}

    return {'closed': False, 'reason': None, 'close_price': 0.0}



def position_size(
    prob: np.ndarray,
    method: str = "fixed",
    target_vol: Optional[float] = None,
    realized_vol: Optional[np.ndarray] = None,
    fee_bps: float = 5.0,
    slippage_bps: float = 5.0
) -> np.ndarray:
    """
    method="fixed": returns +1/-1/0 from a simple prob > 0.55 / prob < 0.45 threshold rule.
    method="vol_target": position = sign(prob - 0.5) * (target_vol / realized_vol), clipped to [-1, 1].
    method="prob_scaled": position = np.clip((prob - 0.5) * 2, -1, 1).
    method="cost_aware_meta": position = prob_scaled ONLY if expected edge > 2 * roundtrip transaction cost (fee + slippage).
    """
    prob_arr = np.asarray(prob, dtype=float)

    if method == "fixed":
        pos = np.zeros_like(prob_arr, dtype=float)
        pos[prob_arr > 0.55] = 1.0
        pos[prob_arr < 0.45] = -1.0
        return pos

    elif method == "vol_target":
        if target_vol is None or realized_vol is None:
            raise ValueError("target_vol and realized_vol must be provided for method='vol_target'.")
        vol_floor = 1e-6
        vol_safe = np.clip(np.asarray(realized_vol, dtype=float), vol_floor, None)
        raw_pos = np.sign(prob_arr - 0.5) * (target_vol / vol_safe)
        return np.clip(raw_pos, -1.0, 1.0)

    elif method == "prob_scaled":
        return np.clip((prob_arr - 0.5) * 2.0, -1.0, 1.0)

    elif method == "cost_aware_meta":
        roundtrip_cost = 2.0 * ((fee_bps + slippage_bps) / 10000.0)
        expected_edge = np.abs(prob_arr - 0.5) * 0.02 # estimated 2% baseline move
        scaled_pos = np.clip((prob_arr - 0.5) * 2.0, -1.0, 1.0)
        # Suppress position if expected edge is smaller than roundtrip costs
        scaled_pos[expected_edge < roundtrip_cost] = 0.0
        return scaled_pos

    else:
        raise ValueError(f"Unknown position sizing method: {method}")



def run_backtest(
    price: pd.Series,
    position: pd.Series,
    fee_bps: float = 5.0,
    slippage_bps: float = 5.0,
    max_hold_bars: Optional[int] = None,
) -> Dict:
    """
    Simulates returns: strategy_ret[t] = position[t-1] * price_ret[t] -
    fee_bps/10000 * abs(position[t] - position[t-1]) - slippage cost applied.
    If max_hold_bars is specified, enforces discrete holding period execution where positions
    are held for up to max_hold_bars before returning to flat.
    """
    if max_hold_bars is not None and max_hold_bars > 0:
        n = len(price)
        pos = np.zeros(n, dtype=float)
        curr_pos = 0.0
        hold_counter = 0
        sig_arr = position.values

        for i in range(n):
            s = sig_arr[i]
            if curr_pos == 0.0:
                if s != 0.0:
                    curr_pos = s
                    hold_counter = 1
            else:
                if s != 0.0 and s != curr_pos:
                    curr_pos = s
                    hold_counter = 1
                elif hold_counter >= max_hold_bars:
                    curr_pos = 0.0
                    hold_counter = 0
                else:
                    hold_counter += 1
            pos[i] = curr_pos

        position = pd.Series(pos, index=price.index)

    price_ret = price.pct_change().fillna(0.0)

    # Position is applied with a 1-bar execution lag: position[t-1] is held over bar t (from close[t-1] to close[t]).
    pos_lagged = position.shift(1).fillna(0.0)

    # Transaction fees & slippage costs are incurred on position changes: abs(position[t] - position[t-1])
    pos_diff = (position - position.shift(1).fillna(0.0)).abs()
    total_cost_bps = fee_bps + slippage_bps
    cost_per_bar = (total_cost_bps / 10000.0) * pos_diff

    # Strategy net return per bar
    strategy_ret = pos_lagged * price_ret - cost_per_bar
    equity_curve = (1.0 + strategy_ret).cumprod()

    if len(equity_curve) == 0:
        return {
            'equity_curve': pd.Series(dtype=float),
            'total_return': 0.0,
            'sharpe': 0.0,
            'max_drawdown': 0.0,
            'turnover': 0.0,
            'n_trades': 0
        }

    total_return = float(equity_curve.iloc[-1] - 1.0)
    ret_list = strategy_ret.tolist()
    sharpe_val = sharpe_ratio(ret_list, periods_per_year=8760)
    sharpe = float(sharpe_val) if sharpe_val is not None else 0.0

    eq_list = equity_curve.tolist()
    mdd_val = maximum_drawdown(eq_list)
    max_drawdown = -float(mdd_val) if mdd_val > 0 else 0.0

    turnover = float(pos_diff.mean())
    n_trades = int((pos_diff > 1e-5).sum())

    return {
        'equity_curve': equity_curve,
        'total_return': total_return,
        'sharpe': sharpe,
        'max_drawdown': max_drawdown,
        'turnover': turnover,
        'n_trades': n_trades
    }


def cost_sensitivity_grid(
    price: pd.Series,
    position: pd.Series,
    fee_grid: List[float],
    slippage_grid: List[float]
) -> pd.DataFrame:
    """Runs run_backtest across the cartesian product of fee_grid x
    slippage_grid, returns a long-format DataFrame of results."""
    rows = []
    for fee in fee_grid:
        for slip in slippage_grid:
            res = run_backtest(price, position, fee_bps=fee, slippage_bps=slip)
            rows.append({
                'fee_bps': fee,
                'slippage_bps': slip,
                'total_return': res['total_return'],
                'sharpe': res['sharpe'],
                'max_drawdown': res['max_drawdown'],
                'turnover': res['turnover'],
                'n_trades': res['n_trades']
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("Loading dataset and running XGBoost model on held-out fold...")
    X, y, t1 = make_dataset(horizon_bars=24)

    timestamps = pd.Series(X.index)
    splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=24)
    folds = list(splitter.split(timestamps, t1))
    train_idx, test_idx = folds[-1]  # Last fold

    X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
    X_te, y_te = X.iloc[test_idx], y.iloc[test_idx]

    model = XGBClassifier(n_estimators=100, eval_metric='logloss', random_state=42, n_jobs=-1)
    model.fit(X_tr, y_tr)
    y_prob_te = model.predict_proba(X_te)[:, 1]

    test_price = X_te['close']

    # Buy and Hold baseline (position = 1 throughout)
    bnh_pos = pd.Series(1.0, index=test_price.index, name="position")
    res_bnh = run_backtest(test_price, bnh_pos, fee_bps=5.0, slippage_bps=5.0)

    # XGBoost Signal Strategy (prob_scaled)
    xgb_pos_vals = position_size(y_prob_te, method="prob_scaled")
    xgb_pos = pd.Series(xgb_pos_vals, index=test_price.index, name="position")
    res_xgb = run_backtest(test_price, xgb_pos, fee_bps=5.0, slippage_bps=5.0)

    # Print Strategy Comparison Table
    comp_df = pd.DataFrame([
        {
            'Strategy': 'Buy & Hold',
            'Total Return': f"{res_bnh['total_return']:.4f}",
            'Sharpe': f"{res_bnh['sharpe']:.4f}",
            'Max Drawdown': f"{res_bnh['max_drawdown']:.4f}",
            'Turnover': f"{res_bnh['turnover']:.6f}",
            'N Trades': res_bnh['n_trades']
        },
        {
            'Strategy': 'XGBoost (prob_scaled)',
            'Total Return': f"{res_xgb['total_return']:.4f}",
            'Sharpe': f"{res_xgb['sharpe']:.4f}",
            'Max Drawdown': f"{res_xgb['max_drawdown']:.4f}",
            'Turnover': f"{res_xgb['turnover']:.6f}",
            'N Trades': res_xgb['n_trades']
        }
    ])

    print("\n--- Strategy Comparison (Section 7 Baseline vs XGBoost) ---")
    print(comp_df.to_string(index=False))

    # Cost Sensitivity Grid: fee_bps in [0, 5, 10, 20] x slippage_bps in [0, 5, 10, 20]
    fee_grid = [0.0, 5.0, 10.0, 20.0]
    slippage_grid = [0.0, 5.0, 10.0, 20.0]
    print(f"\nRunning cost sensitivity grid ({len(fee_grid)}x{len(slippage_grid)} = {len(fee_grid)*len(slippage_grid)} rows)...")

    cost_df = cost_sensitivity_grid(test_price, xgb_pos, fee_grid, slippage_grid)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    cost_csv = os.path.join(RESULTS_DIR, "cost_sensitivity.csv")
    cost_df.to_csv(cost_csv, index=False)
    print(f"Saved cost sensitivity grid to {cost_csv}")
    print(cost_df)

    # Assertions
    # 1. Constant position (flat & buy-and-hold) Sharpe computation doesn't raise
    res_flat = run_backtest(test_price, pd.Series(0.0, index=test_price.index))
    flat_no_crash = not np.isnan(res_flat['sharpe']) and res_flat['sharpe'] == 0.0
    bnh_valid = not np.isnan(res_bnh['sharpe'])
    grid_size_ok = len(cost_df) == 16

    if flat_no_crash and bnh_valid and grid_size_ok:
        print("\nPASS: Backtest and cost sensitivity assertions passed cleanly.")
    else:
        print("\nFAIL: Backtest assertions failed.")

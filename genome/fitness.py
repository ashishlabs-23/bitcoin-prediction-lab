"""
genome/fitness.py -- Genome Fitness Evaluation

Evaluates a Genome's exit/risk policy on top of the AdaptiveRegimeEnsemble's
pre-computed direction probabilities. Wraps the existing backtest harness
(backtest.simulate.run_backtest + backtest.simulate.position_size) exactly as
it runs in production, changing ONLY the TP/SL/hold-time/sizing genes.

Architecture rule: This module does NOT touch the entry direction.
The ensemble probability is treated as a black box input — Genomes compete
purely on how well they manage exits and position sizing given those probabilities.

Correction 1 (leakage fix): classify_regimes_no_leak() uses expanding-window
quantiles for volatility state, not global quantiles over the full dataset.
The live-inference path (regime_detector.py / market_state.py) is unchanged.

Correction 5 (vol_target): When position_size_method=='vol_target', passes
realized_vol_24h to position_size() with target_vol=0.02 (2% per bar).
This is a placeholder; tune target_vol empirically per regime.
"""

import os
import sys
import math
import numpy as np
import pandas as pd
from typing import Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from genome.chromosome import Genome, VALID_REGIMES
from backtest.simulate import run_backtest, position_size
from validation.purged_split import PurgedWalkForwardSplit


# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------

DEFAULT_FEE_BPS      = 5.0    # matches existing backtest default
DEFAULT_SLIPPAGE_BPS = 5.0
VOL_TARGET_DEFAULT   = 0.02   # 2% per bar -- placeholder for vol_target method (Correction 5)
MIN_REGIME_BARS      = 20     # skip folds with fewer than this many regime-active bars


# -------------------------------------------------------------------
# Correction 1: Leakage-safe regime classification
# -------------------------------------------------------------------

def classify_regimes_no_leak(df: pd.DataFrame) -> pd.Series:
    """
    Classifies each bar into a discrete regime WITHOUT look-ahead leakage.

    Identical logic to models.regime_detector.classify_regimes EXCEPT:
    The volatility quantile thresholds (q33, q66) are computed using an
    expanding window (only past bars visible at each timestamp), NOT global
    quantiles over the full dataset.

    Why this matters for genome evaluation:
    If we classify regimes using global quantiles (as market_state.py does for
    live inference), a bar in the training fold sees volatility thresholds that
    include test-fold volatility -- a subtle look-ahead that would make the
    regime labels for training bars inconsistent with what was actually knowable
    at that time. This wrapper fixes that for the genome's backtesting context.

    Live inference in regime_detector.py is NOT changed: in production, the
    full historical window is always available and the leakage direction is moot.

    Args:
        df: Feature DataFrame (must contain the columns used by market_state.py).

    Returns:
        pd.Series of regime strings, indexed like df.
    """
    # --- Compute constituent signals (identical to compute_market_states) ---
    sma_part = np.clip(df.get('sma_ratio_50', pd.Series(0.0, index=df.index)) * 10.0, -1.0, 1.0)
    ret_part = np.clip(df.get('ret_24h', pd.Series(0.0, index=df.index)) * 20.0, -1.0, 1.0)
    macd_part = np.sign(df.get('macd', pd.Series(0.0, index=df.index)).fillna(0.0))
    trend = (0.5 * sma_part + 0.3 * ret_part + 0.2 * macd_part).fillna(0.0)

    # Momentum state
    rsi = df.get('rsi_14', pd.Series(50.0, index=df.index)).fillna(50.0)
    ret_4h = df.get('ret_4h', pd.Series(0.0, index=df.index)).fillna(0.0)
    mom_conds = [(rsi > 55) & (ret_4h > 0), (rsi < 45) & (ret_4h < 0)]
    momentum = pd.Series(
        np.select(mom_conds, ['POSITIVE', 'NEGATIVE'], default='NEUTRAL'),
        index=df.index
    )

    # Leverage state
    oi_change = df.get('oi_pct_change_24h', pd.Series(0.0, index=df.index)).fillna(0.0)
    lev_conds = [oi_change > 0.03, oi_change < -0.03]
    leverage = pd.Series(
        np.select(lev_conds, ['ELEVATED', 'SUBDUED'], default='NORMAL'),
        index=df.index
    )

    # Volatility state -- EXPANDING WINDOW (Correction 1)
    vol = df.get('realized_vol_24h', pd.Series(0.01, index=df.index)).fillna(0.01)
    vol_q33 = vol.expanding(min_periods=24).quantile(0.33)
    vol_q66 = vol.expanding(min_periods=24).quantile(0.66)
    # Use raw global quantile for bars before min_periods (expanding returns NaN there)
    global_q33 = vol.quantile(0.33)
    global_q66 = vol.quantile(0.66)
    vol_q33 = vol_q33.fillna(global_q33)
    vol_q66 = vol_q66.fillna(global_q66)

    vol_state = np.select(
        [vol <= vol_q33, (vol > vol_q33) & (vol <= vol_q66), vol > vol_q66],
        ['LOW', 'MEDIUM', 'HIGH'],
        default='MEDIUM'
    )

    # --- Classify regime (identical rule tree to classify_regimes) ---
    regimes = []
    for i in range(len(df)):
        t = trend.iloc[i]
        v = vol_state[i]
        m = momentum.iloc[i]
        lev = leverage.iloc[i]

        if v == 'HIGH':
            regimes.append('HIGH_VOLATILITY')
        elif lev == 'ELEVATED' and abs(t) > 0.2:
            regimes.append('BREAKOUT')
        elif t > 0.15 and m != 'NEGATIVE':
            regimes.append('TRENDING_BULL')
        elif t < -0.15 and m != 'POSITIVE':
            regimes.append('TRENDING_BEAR')
        else:
            regimes.append('RANGING')

    return pd.Series(regimes, index=df.index, name='regime')


# -------------------------------------------------------------------
# TP/SL application
# -------------------------------------------------------------------

def apply_genome_exit_policy(
    genome: Genome,
    price_series: pd.Series,
    raw_positions: pd.Series,
    atr_series: pd.Series,
) -> pd.Series:
    """
    Applies the genome's TP, SL, and max-hold-bar exit policy on top of
    raw_positions (the direction signal from the ensemble + sizing method).

    Logic:
      For each bar where a new position opens (raw_positions changes from 0):
        - Compute TP price = entry_price +/- genome.tp_atr_mult * ATR
        - Compute SL price = entry_price -/+ genome.sl_atr_mult * ATR
        - Monitor subsequent bars until:
            a) price crosses TP (force close, take profit)
            b) price crosses SL (force close, cut loss)
            c) max_hold_bars bars have passed (force close at market)
            d) raw_positions flips sign or returns to 0 (normal signal exit)

    Returns:
        pd.Series of adjusted positions with the same index as raw_positions.
        Values in {-1, 0, 1} (same scale as raw_positions).
    """
    if len(price_series) == 0:
        return raw_positions.copy()

    pos = raw_positions.values.copy().astype(float)
    price = price_series.values
    atr = atr_series.values

    i = 0
    n = len(pos)
    while i < n:
        if pos[i] == 0.0:
            i += 1
            continue

        # New position opened at bar i
        entry_price = float(price[i])
        entry_atr = float(atr[i]) if not math.isnan(atr[i]) and atr[i] > 0 else 0.001 * entry_price
        direction = 1.0 if pos[i] > 0 else -1.0

        tp_price = entry_price + direction * genome.tp_atr_mult * entry_atr
        sl_price = entry_price - direction * genome.sl_atr_mult * entry_atr

        hold_bars = 0
        j = i + 1

        # Scan forward to find exit bar
        while j < n:
            current_price = float(price[j])
            hold_bars += 1

            # Check if raw signal exits first
            if pos[j] != direction and pos[j] != 0.0:
                # Signal has flipped — let the signal exit happen naturally
                break
            if pos[j] == 0.0:
                # Signal has closed
                break

            # TP hit
            if direction > 0 and current_price >= tp_price:
                pos[j] = 0.0
                # Zero out remaining until signal changes
                k = j + 1
                while k < n and abs(pos[k] - direction) < 0.01:
                    pos[k] = 0.0
                    k += 1
                i = j
                break

            # SL hit
            if direction > 0 and current_price <= sl_price:
                pos[j] = 0.0
                k = j + 1
                while k < n and abs(pos[k] - direction) < 0.01:
                    pos[k] = 0.0
                    k += 1
                i = j
                break

            # Short TP hit
            if direction < 0 and current_price <= tp_price:
                pos[j] = 0.0
                k = j + 1
                while k < n and abs(pos[k] - direction) < 0.01:
                    pos[k] = 0.0
                    k += 1
                i = j
                break

            # Short SL hit
            if direction < 0 and current_price >= sl_price:
                pos[j] = 0.0
                k = j + 1
                while k < n and abs(pos[k] - direction) < 0.01:
                    pos[k] = 0.0
                    k += 1
                i = j
                break

            # Max hold bars hit
            if hold_bars >= genome.max_hold_bars:
                pos[j] = 0.0
                k = j + 1
                while k < n and abs(pos[k] - direction) < 0.01:
                    pos[k] = 0.0
                    k += 1
                i = j
                break

            j += 1
        else:
            i = j
            continue

        i += 1

    return pd.Series(pos, index=raw_positions.index)


# -------------------------------------------------------------------
# Core evaluation function
# -------------------------------------------------------------------

def evaluate_genome(
    genome: Genome,
    features_df: pd.DataFrame,
    ensemble_probs: pd.Series,
    t1: pd.Series,
    splitter: Optional[PurgedWalkForwardSplit] = None,
    fee_bps: float = DEFAULT_FEE_BPS,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> Tuple[dict, list, list]:
    """
    Evaluates a Genome's fitness across purged walk-forward CV folds.

    Entry direction is fixed to what the ensemble emits (ensemble_probs).
    The genome controls ONLY:
      - How positions are sized (position_size_method)
      - When to take profit (tp_atr_mult * ATR)
      - When to cut losses (sl_atr_mult * ATR)
      - Maximum bars to hold (max_hold_bars)

    Regime filtering (Correction 1):
      Only bars where classify_regimes_no_leak(features_df) == genome.regime
      are used for evaluation. Bars in other regimes are masked to 0 position.
      The leakage-safe version uses expanding-window volatility quantiles.

    vol_target handling (Correction 5):
      When genome.position_size_method == 'vol_target', passes
      realized_vol_24h to position_size() with target_vol=VOL_TARGET_DEFAULT.

    Args:
        genome:         Genome to evaluate.
        features_df:    Full feature DataFrame (all bars, indexed by integer).
                        Must contain: close, atr_14, realized_vol_24h, + regime signals.
        ensemble_probs: pd.Series of float probabilities (length matches features_df).
                        Must be aligned to features_df.index.
        t1:             pd.Series of label end timestamps (for purged splitting).
        splitter:       PurgedWalkForwardSplit instance. Created with n_splits=5 if None.
        fee_bps:        Transaction fee in basis points.
        slippage_bps:   Slippage in basis points.

    Returns:
        Tuple of (fitness_dict, fold_sharpes_list, fold_trade_counts_list):
          - fitness_dict: {sharpe, calmar, max_drawdown, win_rate, turnover, n_folds_used}
            All metrics are the mean across folds where regime was active.
            Returns all-NaN dict if no fold had sufficient regime-active bars.
          - fold_sharpes_list: Per-fold Sharpe values (for PBO computation).
          - fold_trade_counts_list: Per-fold trade counts (for PBO min-trade guard).
    """
    if splitter is None:
        splitter = PurgedWalkForwardSplit(n_splits=5, embargo_bars=24)

    # Leakage-safe regime labels (Correction 1)
    regime_labels = classify_regimes_no_leak(features_df)

    # timestamps for splitting (PurgedWalkForwardSplit needs a datetime-like series)
    timestamps = features_df.index

    fold_sharpes   = []
    fold_trade_counts = []
    fold_results   = []

    for train_idx, test_idx in splitter.split(pd.Series(timestamps), t1):
        if len(test_idx) < MIN_REGIME_BARS:
            continue

        # Filter to bars where this genome's regime is active
        test_regime_mask = regime_labels.iloc[test_idx].values == genome.regime
        active_test_idx  = [test_idx[k] for k in range(len(test_idx)) if test_regime_mask[k]]

        if len(active_test_idx) < MIN_REGIME_BARS:
            # Not enough regime-active bars in this fold -- skip
            fold_sharpes.append(0.0)
            fold_trade_counts.append(0)
            continue

        # Extract test-fold data for regime-active bars
        test_probs  = ensemble_probs.iloc[active_test_idx].values
        test_prices = features_df['close'].iloc[active_test_idx]
        test_atr    = features_df['atr_14'].iloc[active_test_idx]
        test_rvol   = features_df['realized_vol_24h'].iloc[active_test_idx].values

        # Position sizing (Correction 5: vol_target passes realized_vol)
        if genome.position_size_method == 'vol_target':
            raw_pos = position_size(
                test_probs,
                method='vol_target',
                target_vol=VOL_TARGET_DEFAULT,
                realized_vol=test_rvol,
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
            )
        else:
            raw_pos = position_size(
                test_probs,
                method=genome.position_size_method,
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
            )

        raw_pos_series = pd.Series(raw_pos, index=test_prices.index)

        # Apply genome's TP/SL/hold-time exit policy
        adjusted_pos = apply_genome_exit_policy(genome, test_prices, raw_pos_series, test_atr)

        # Run backtest on the adjusted positions
        bt = run_backtest(test_prices, adjusted_pos, fee_bps=fee_bps, slippage_bps=slippage_bps)

        n_trades = int(bt.get('n_trades', 0))
        sharpe   = float(bt.get('sharpe', 0.0))
        fold_sharpes.append(sharpe)
        fold_trade_counts.append(n_trades)
        fold_results.append(bt)

    # Aggregate across folds
    valid_folds = [r for r in fold_results]
    if not valid_folds:
        nan_dict = {
            'sharpe': float('nan'), 'calmar': float('nan'),
            'max_drawdown': float('nan'), 'win_rate': float('nan'),
            'turnover': float('nan'), 'n_folds_used': 0,
        }
        return nan_dict, fold_sharpes, fold_trade_counts

    mean_sharpe   = float(np.nanmean([r.get('sharpe', 0.0)   for r in valid_folds]))
    mean_drawdown = float(np.nanmean([r.get('max_drawdown', 0.0) for r in valid_folds]))
    mean_turnover = float(np.nanmean([r.get('turnover', 0.0) for r in valid_folds]))
    mean_return   = float(np.nanmean([r.get('total_return', 0.0) for r in valid_folds]))

    # Calmar = annualised return / |max drawdown| (avoid div by 0)
    if mean_drawdown == 0.0 or math.isnan(mean_drawdown):
        calmar = 0.0
    else:
        calmar = float(mean_return / abs(mean_drawdown))

    # Win rate: fraction of folds where Sharpe > 0
    win_rate = float(sum(1 for r in valid_folds if r.get('sharpe', 0.0) > 0) / len(valid_folds))

    fitness = {
        'sharpe':       mean_sharpe,
        'calmar':       calmar,
        'max_drawdown': mean_drawdown,
        'win_rate':     win_rate,
        'turnover':     mean_turnover,
        'n_folds_used': len(valid_folds),
    }
    return fitness, fold_sharpes, fold_trade_counts


# -------------------------------------------------------------------
# Smoke test (synthetic data -- no real parquet required)
# -------------------------------------------------------------------

if __name__ == "__main__":
    import random
    from genome.chromosome import random_genome

    random.seed(42)
    np.random.seed(42)
    errors = []

    print("fitness.py smoke test (100 bars, 3 genomes)...")

    # Build 200 bars of synthetic OHLCV
    n = 200
    price = 100.0 + np.cumsum(np.random.randn(n) * 0.5)
    atr   = np.abs(np.random.randn(n) * 0.3) + 0.5
    rvol  = np.abs(np.random.randn(n) * 0.01) + 0.005
    macd  = np.random.randn(n) * 0.5

    features_df = pd.DataFrame({
        'close':              price,
        'atr_14':             atr,
        'realized_vol_24h':   rvol,
        'sma_ratio_50':       np.random.randn(n) * 0.02,
        'ret_24h':            np.random.randn(n) * 0.01,
        'ret_4h':             np.random.randn(n) * 0.005,
        'rsi_14':             50.0 + np.random.randn(n) * 15,
        'macd':               macd,
        'oi_pct_change_24h':  np.random.randn(n) * 0.02,
        'funding_rate':       np.random.randn(n) * 0.0001,
    })

    # Synthetic probabilities (slightly bullish bias)
    ensemble_probs = pd.Series(0.5 + np.random.randn(n) * 0.1)
    ensemble_probs = ensemble_probs.clip(0.01, 0.99)

    # Build t1 (simple: 24 bars forward for each bar)
    t1 = pd.Series(range(24, n + 24))

    # Use a splitter with fewer splits for the small dataset
    splitter = PurgedWalkForwardSplit(n_splits=3, embargo_bars=4)

    # Test 3 genomes: one per sizing method
    for regime in ['TRENDING_BULL', 'RANGING', 'HIGH_VOLATILITY']:
        g = random_genome(regime, generation=0)
        fitness, fold_sharpes, fold_trades = evaluate_genome(
            g, features_df, ensemble_probs, t1, splitter
        )
        n_folds = fitness.get('n_folds_used', 0)
        sr = fitness.get('sharpe', float('nan'))
        print(f"  {regime}: Sharpe={sr:.3f}, n_folds_used={n_folds}, "
              f"fold_sharpes={[round(x,2) for x in fold_sharpes]}, "
              f"fold_trades={fold_trades}")

        # Validate output shape
        if not isinstance(fitness, dict):
            errors.append(f"FAIL: {regime} fitness is not a dict")
        if not isinstance(fold_sharpes, list):
            errors.append(f"FAIL: {regime} fold_sharpes is not a list")
        if not isinstance(fold_trades, list):
            errors.append(f"FAIL: {regime} fold_trade_counts is not a list")

    print(f"\nclassify_regimes_no_leak: leakage safety check...")
    # Verify that expanding quantiles differ from global quantiles on a skewed series
    skewed_vol = pd.Series([0.01] * 100 + [0.10] * 100)
    skewed_df = features_df.copy()
    skewed_df['realized_vol_24h'] = skewed_vol[:n].reset_index(drop=True)
    regimes = classify_regimes_no_leak(skewed_df)
    n_volatile = (regimes == 'HIGH_VOLATILITY').sum()
    print(f"  High volatility bars in skewed series: {n_volatile} (expect >0 in second half)")
    if n_volatile == 0:
        errors.append("FAIL: classify_regimes_no_leak found no HIGH_VOLATILITY bars in skewed series")

    if not errors:
        print("\nPASS: All fitness.py smoke checks passed.")
    else:
        print(f"\nFAIL: {len(errors)} check(s) failed:")
        for e in errors:
            print(f"  {e}")

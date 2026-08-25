"""
End-to-End Integration Smoke Test Suite for bitcoin-prediction-lab.

Verifies that:
1. Every package module imports cleanly without error.
2. The core end-to-end pipeline (features -> labels -> purged split -> model -> backtest)
   runs cleanly on synthetic data without network requests.
3. Phase 2 Market State, Regime Detector, Adaptive Ensemble, and Market Memory modules run without error.
4. Network-dependent exchange fetch functions operate as expected (marked @pytest.mark.network).
"""

import sys
import os
import pytest
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_module_imports():
    """
    1. Import every module built across Phase 1 and Phase 2 and assert each imports without raising.
    """
    import data.ingest
    import data.audit_data
    import features.build_features
    import features.audit_features
    import labeling.targets
    import validation.purged_split
    import models.train_baselines
    import models.market_state
    import models.regime_detector
    import models.ensemble
    import calibration.calibrate
    import backtest.simulate
    import backtest.market_memory
    import experiments.statistical_checks
    import experiments.ablation_study
    import experiments.horizon_sweep
    import models.uncertainty
    import models.counterfactual
    import models.event_engine
    import genome

    assert data.ingest is not None
    assert data.audit_data is not None
    assert features.build_features is not None
    assert features.audit_features is not None
    assert labeling.targets is not None
    assert validation.purged_split is not None
    assert models.train_baselines is not None
    assert models.market_state is not None
    assert models.regime_detector is not None
    assert models.ensemble is not None
    assert calibration.calibrate is not None
    assert backtest.simulate is not None
    assert backtest.market_memory is not None
    assert experiments.statistical_checks is not None
    assert experiments.ablation_study is not None
    assert experiments.horizon_sweep is not None


def test_synthetic_pipeline_end_to_end():
    """
    2. Build a small synthetic OHLCV DataFrame (200 hourly rows, random walk price)
       directly in the test — don't hit the network — and run it through:
       compute_technical_features -> triple_barrier_label ->
       PurgedWalkForwardSplit.split -> a single LogisticRegression fit/predict on
       one fold -> run_backtest on the resulting signal.
       Assert this full synthetic pipeline completes with no exception and produces
       a backtest dict with a non-null 'sharpe' key.
    """
    from features.build_features import compute_technical_features
    from labeling.targets import realized_vol, triple_barrier_label
    from validation.purged_split import PurgedWalkForwardSplit
    from backtest.simulate import position_size, run_backtest

    # Generate synthetic 200-hour random walk OHLCV dataset
    np.random.seed(42)
    timestamps = pd.date_range("2023-01-01 00:00:00", periods=200, freq="1h", tz="UTC")
    returns = np.random.normal(0.0002, 0.005, size=200)
    price_path = 20000.0 * np.exp(np.cumsum(returns))

    ohlcv_df = pd.DataFrame({
        "timestamp": timestamps,
        "open": price_path * (1 - 0.001),
        "high": price_path * (1 + 0.002),
        "low": price_path * (1 - 0.002),
        "close": price_path,
        "volume": np.random.uniform(10, 100, size=200),
        "available_time": timestamps + pd.Timedelta(hours=1)
    })

    # Step 1: Compute technical features
    feats_df = compute_technical_features(ohlcv_df)
    feats_clean = feats_df.dropna().copy()

    # Step 2: Calculate realized vol & triple barrier labels
    vol = realized_vol(feats_clean['close'], window=24)
    lbl_df = triple_barrier_label(feats_clean['close'], vol, pt_mult=2.0, sl_mult=2.0, max_bars=24)

    # Align X, y, t1
    feature_cols = [c for c in feats_clean.columns if c not in ['timestamp', 'available_time']]
    X = feats_clean[feature_cols].copy()
    y_raw = lbl_df['label']
    t1 = lbl_df['t1']

    # Filter out NaNs in labels
    valid_mask = ~y_raw.isna()
    X = X.loc[valid_mask].reset_index(drop=True)
    y = (y_raw.loc[valid_mask] == 1.0).astype(int).reset_index(drop=True)
    t1_clean = t1.loc[valid_mask].reset_index(drop=True)
    timestamps_clean = feats_clean.loc[valid_mask, 'timestamp'].reset_index(drop=True)

    assert len(X) > 0, "Synthetic dataset after filtering NaNs must not be empty."

    # Step 3: Purged Walk-Forward Split
    splitter = PurgedWalkForwardSplit(n_splits=3, embargo_bars=12)
    folds = list(splitter.split(timestamps_clean, t1_clean))
    train_idx, test_idx = folds[0]

    X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
    X_te, y_te = X.iloc[test_idx], y.iloc[test_idx]

    # Step 4: Model Training (LogisticRegression)
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=100))
    clf.fit(X_tr, y_tr)
    y_prob_te = clf.predict_proba(X_te)[:, 1]

    # Step 5: Position Sizing & Backtest Simulation
    signals = position_size(y_prob_te, method="prob_scaled")
    test_price = feats_clean.loc[valid_mask, 'close'].iloc[test_idx]
    pos_series = pd.Series(signals, index=test_price.index)

    bt_results = run_backtest(test_price, pos_series, fee_bps=5.0, slippage_bps=5.0)

    # Verification assertions
    assert isinstance(bt_results, dict), "run_backtest must return a dictionary."
    assert "sharpe" in bt_results, "Backtest output dictionary must contain 'sharpe' key."
    assert bt_results["sharpe"] is not None, "'sharpe' value must not be None."


def test_phase2_market_state_and_regime_detector():
    """
    3. Test Phase 2 Market State calculation, Regime Detector, and Market Memory logging.
    """
    from models.market_state import compute_market_states
    from models.regime_detector import classify_regimes
    from models.ensemble import AdaptiveRegimeEnsemble
    from backtest.market_memory import record_prediction, load_market_memory

    # Create dummy dataframe with necessary feature columns
    np.random.seed(42)
    df = pd.DataFrame({
        'close': np.random.uniform(20000, 30000, 50),
        'sma_ratio_50': np.random.normal(0.01, 0.05, 50),
        'ret_24h': np.random.normal(0.005, 0.02, 50),
        'macd': np.random.normal(10, 5, 50),
        'realized_vol_24h': np.random.uniform(0.005, 0.03, 50),
        'rsi_14': np.random.uniform(40, 70, 50),
        'ret_4h': np.random.normal(0.001, 0.01, 50),
        'funding_rate': np.random.normal(0.0001, 0.0002, 50),
        'oi_pct_change_24h': np.random.normal(0.01, 0.04, 50)
    })

    states_df = compute_market_states(df)
    assert 'trend_score' in states_df.columns
    assert 'volatility_state' in states_df.columns

    regimes = classify_regimes(df)
    assert len(regimes) == 50

    ens = AdaptiveRegimeEnsemble()
    X_dummy = pd.DataFrame(np.random.randn(50, 5))
    y_dummy = pd.Series(np.random.randint(0, 2, 50))
    ens.fit(X_dummy, y_dummy)

    p_bull = ens.predict_proba_regime(X_dummy.iloc[:5], 'TRENDING_BULL')
    assert len(p_bull) == 5

    rec_df = record_prediction(
        timestamp="2026-08-13 12:00:00+00:00",
        price=116500.0,
        regime="TRENDING_BULL",
        raw_prob=0.68,
        calibrated_prob=0.72,
        decision="TAKE_LONG",
        actual_return=0.0084,
        was_correct=True,
        pnl=84.0
    )
    assert not rec_df.empty


@pytest.mark.network
def test_network_ingestion():
    """
    4. Light network test that fetches real OHLCV data from Binance via ccxt.
    Exposed only when running pytest with network tests enabled.
    """
    pytest.importorskip("ccxt")
    from data.ingest import fetch_ohlcv

    df = fetch_ohlcv("binance", "BTC/USDT", "1h", "2024-01-01T00:00:00Z")

    assert isinstance(df, pd.DataFrame), "fetch_ohlcv must return a pandas DataFrame."
    assert len(df) > 0, "fetch_ohlcv must return > 0 rows for valid timeframe."
    expected_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'available_time']
    assert list(df.columns) == expected_cols, f"Columns must match {expected_cols}"

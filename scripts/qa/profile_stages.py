import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
import pandas as pd
from api.routes_tournament import (
    _load_historical_1h_bars,
    _post_analyse_market,
    AnalyseRequestModel
)
from engine.regime_strategy_tournament import (
    _closed_candle_window_hash,
    check_data_freshness_and_gaps,
    MarketRegimeClassifier,
    execute_integrated_analyse_and_tournament,
    analyse_current_market
)

def profile():
    print("=== Sub-Stage Profile Breakdown ===")
    
    # Stage 1: Parquet Read
    t0 = time.perf_counter()
    df = _load_historical_1h_bars()
    t_load = time.perf_counter() - t0
    print(f"1. Parquet Load: {t_load:.4f}s (Rows: {len(df)})")
    
    # Stage 2: First Hash (Cold)
    t0 = time.perf_counter()
    h = _closed_candle_window_hash(df)
    t_hash_cold = time.perf_counter() - t0
    print(f"2. Vector Hash (Cold): {t_hash_cold:.4f}s")
    
    # Stage 3: Second Hash (Warm - memory allocated)
    t0 = time.perf_counter()
    h2 = _closed_candle_window_hash(df)
    t_hash_warm = time.perf_counter() - t0
    print(f"3. Vector Hash (Warm): {t_hash_warm:.4f}s")
    
    # Stage 4: Freshness Check with Reused Fingerprint
    t0 = time.perf_counter()
    fresh = check_data_freshness_and_gaps(df, dataset_fingerprint=h)
    t_fresh = time.perf_counter() - t0
    print(f"4. Freshness Check: {t_fresh:.4f}s")
    
    # Stage 5: Regime Classifier
    t0 = time.perf_counter()
    regime = MarketRegimeClassifier.classify(df)
    t_regime = time.perf_counter() - t0
    print(f"5. Market Regime Classifier: {t_regime:.4f}s")
    
    # Stage 6: analyse_current_market
    t0 = time.perf_counter()
    ana_res = analyse_current_market(df, live_price=76985.40)
    t_ana = time.perf_counter() - t0
    print(f"6. analyse_current_market: {t_ana:.4f}s")
    
    # Stage 7: Full execute_integrated_analyse_and_tournament
    t0 = time.perf_counter()
    integ_res = execute_integrated_analyse_and_tournament(df_1h=df, live_price=76985.40)
    t_integ = time.perf_counter() - t0
    print(f"7. execute_integrated_analyse_and_tournament: {t_integ:.4f}s")
    
    # Stage 8: Full _post_analyse_market Cold
    t0 = time.perf_counter()
    # Use a dummy fresh request to bypass any digest cache
    post_res = _post_analyse_market(AnalyseRequestModel(live_price=76985.40, force_fresh_tournament=True))
    t_post = time.perf_counter() - t0
    print(f"8. Full _post_analyse_market (force_fresh=True): {t_post:.4f}s")

if __name__ == "__main__":
    profile()


"""
Global configuration module for bitcoin-prediction-lab.
Contains core constants used across data fetching, feature engineering, modeling, and backtesting.
"""

SYMBOL: str = "BTC/USD"
EXCHANGE: str = "binance"
TIMEFRAME: str = "1h"
DATA_START: str = "2022-01-01T00:00:00Z"
DATA_RAW_DIR: str = "data/raw"
DATA_PROCESSED_DIR: str = "data/processed"
RESULTS_DIR: str = "experiments/results"
GENOME_DIR: str = "experiments/genome"

if __name__ == "__main__":
    checks_passed = True
    
    if SYMBOL == "BTC/USD":
        print("PASS: SYMBOL == 'BTC/USD'")
    else:
        print(f"FAIL: SYMBOL expected 'BTC/USD', got '{SYMBOL}'")
        checks_passed = False
        
    if EXCHANGE == "binance":
        print("PASS: EXCHANGE == 'binance'")
    else:
        print(f"FAIL: EXCHANGE expected 'binance', got '{EXCHANGE}'")
        checks_passed = False

    if TIMEFRAME == "1h":
        print("PASS: TIMEFRAME == '1h'")
    else:
        print(f"FAIL: TIMEFRAME expected '1h', got '{TIMEFRAME}'")
        checks_passed = False

    if DATA_START == "2022-01-01T00:00:00Z":
        print("PASS: DATA_START == '2022-01-01T00:00:00Z'")
    else:
        print(f"FAIL: DATA_START expected '2022-01-01T00:00:00Z', got '{DATA_START}'")
        checks_passed = False

    if checks_passed:
        print("PASS: All config smoke checks passed.")
    else:
        print("FAIL: Config smoke checks failed.")

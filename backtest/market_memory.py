"""
Market Memory Engine for bitcoin-prediction-lab.

Maintains a permanent, persistent database of model predictions, market regimes, decisions, and actual outcomes:
- prediction_id (e.g. pred_20260813_1400)
- timestamp
- candle_time
- price
- regime
- raw_prob
- calibrated_prob
- decision (TAKE_LONG / TAKE_SHORT / SKIP)
- actual_return
- was_correct
- pnl
- direction
- tp
- sl
- model_version (e.g. xgb_v2.1)
- feature_version (e.g. features_v3)
- regime_version (e.g. regime_v1)
"""

import os
import sys
import uuid
import time
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from contextlib import contextmanager

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR

DEFAULT_COLUMNS = [
    'prediction_id', 'timestamp', 'candle_time', 'price', 'regime', 'raw_prob',
    'calibrated_prob', 'decision', 'actual_return', 'was_correct', 'pnl',
    'direction', 'tp', 'sl', 'model_version', 'feature_version', 'regime_version',
    'context_vector_json'
]


def get_memory_file() -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    return os.path.join(RESULTS_DIR, "market_memory.csv")


@contextmanager
def file_lock(lock_filepath: str, timeout: float = 5.0):
    """Simple cross-platform spinlock context manager for atomic file access."""
    start_time = time.time()
    while True:
        try:
            # Create exclusive lock file
            fd = os.open(lock_filepath, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.close(fd)
            break
        except OSError:
            if time.time() - start_time > timeout:
                break
            time.sleep(0.05)
    try:
        yield
    finally:
        if os.path.exists(lock_filepath):
            try:
                os.remove(lock_filepath)
            except OSError:
                pass


def record_prediction(
    timestamp: str,
    price: float,
    regime: str,
    raw_prob: float,
    calibrated_prob: float,
    decision: str,
    actual_return: float = 0.0,
    was_correct: bool = True,
    pnl: float = 0.0,
    direction: str = "LONG",
    tp: float = 0.0,
    sl: float = 0.0,
    prediction_id: str = None,
    candle_time: str = None,
    model_version: str = "xgb_v2.1",
    feature_version: str = "features_v3",
    regime_version: str = "regime_v1",
    context_vector_json: str = None,
) -> pd.DataFrame:
    """Appends a new versioned prediction record to Market Memory CSV atomically."""
    memory_csv = get_memory_file()
    lock_file = memory_csv + ".lock"

    if not prediction_id:
        dt_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        prediction_id = f"pred_{dt_str}_{str(uuid.uuid4())[:4]}"

    import json
    if context_vector_json is None:
        context_vector_json = json.dumps({
            "regime": regime,
            "raw_prob": raw_prob,
            "direction": direction,
            "price": price
        })

    new_record = {
        'prediction_id': str(prediction_id),
        'timestamp': str(timestamp),
        'candle_time': str(candle_time if candle_time else timestamp),
        'price': float(price),
        'regime': str(regime),
        'raw_prob': float(raw_prob),
        'calibrated_prob': float(calibrated_prob),
        'decision': str(decision),
        'actual_return': float(actual_return),
        'was_correct': bool(was_correct),
        'pnl': float(pnl),
        'direction': str(direction),
        'tp': float(tp),
        'sl': float(sl),
        'model_version': str(model_version),
        'feature_version': str(feature_version),
        'regime_version': str(regime_version),
        'context_vector_json': str(context_vector_json)
    }

    with file_lock(lock_file):
        if os.path.exists(memory_csv):
            try:
                df = pd.read_csv(memory_csv)
            except Exception:
                df = pd.DataFrame()
            # Ensure schema compatibility with missing columns
            for col in DEFAULT_COLUMNS:
                if not df.empty and col not in df.columns:
                    df[col] = np.nan
            df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
        else:
            df = pd.DataFrame([new_record])

        # Write to temporary file first then sync and rename for atomic write
        tmp_csv = memory_csv + ".tmp"
        with open(tmp_csv, "w", newline="", encoding="utf-8") as f:
            df.to_csv(f, index=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_csv, memory_csv)

    return df


def load_market_memory() -> pd.DataFrame:
    """Loads historical Market Memory predictions atomically."""
    memory_csv = get_memory_file()
    lock_file = memory_csv + ".lock"

    if os.path.exists(memory_csv):
        with file_lock(lock_file):
            try:
                df = pd.read_csv(memory_csv)
                for col in DEFAULT_COLUMNS:
                    if col not in df.columns:
                        df[col] = np.nan
                return df
            except Exception:
                pass
    return pd.DataFrame(columns=DEFAULT_COLUMNS)


def query_similar_context(current_context: dict, top_k: int = 20) -> pd.DataFrame:
    """
    Retrieves historical Market Memory outcomes under similar market contexts
    using regime and state similarity.

    Returns DataFrame of matching historical records.
    """
    mem_df = load_market_memory()
    if mem_df.empty:
        return mem_df

    target_regime = current_context.get('regime', '')
    if target_regime:
        matching = mem_df[mem_df['regime'] == target_regime]
        if not matching.empty:
            return matching.tail(top_k)

    return mem_df.tail(top_k)


def update_prediction_outcome(prediction_id: str, actual_return: float, was_correct: bool, pnl: float) -> bool:
    """Updates an existing prediction record's actual return, correctness, and PnL atomically."""
    memory_csv = get_memory_file()
    lock_file = memory_csv + ".lock"

    if os.path.exists(memory_csv):
        with file_lock(lock_file):
            try:
                df = pd.read_csv(memory_csv)
                mask = df['prediction_id'] == str(prediction_id)
                if mask.any():
                    df.loc[mask, 'actual_return'] = float(actual_return)
                    df.loc[mask, 'was_correct'] = bool(was_correct)
                    df.loc[mask, 'pnl'] = float(pnl)
                    tmp_csv = memory_csv + ".tmp"
                    with open(tmp_csv, "w", newline="", encoding="utf-8") as f:
                        df.to_csv(f, index=False)
                        f.flush()
                        os.fsync(f.fileno())
                    os.replace(tmp_csv, memory_csv)
                    return True
            except Exception as e:
                print(f"Error updating prediction outcome: {e}")
    return False


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test_memory.csv")
        original_get_memory_file = get_memory_file
        get_memory_file = lambda: test_file
        try:
            record_prediction(
                timestamp="2026-08-14 12:00:00+00:00",
                price=64000.0,
                regime="TRENDING_BULL",
                raw_prob=0.68,
                calibrated_prob=0.72,
                decision="TAKE_LONG",
                actual_return=0.0084,
                was_correct=True,
                pnl=84.0,
                direction="LONG",
                tp=64960.0,
                sl=63360.0
            )
            mem_df = load_market_memory()
            print("Market Memory Records:")
            print(mem_df.tail(3))
            print("PASS: Market Memory Engine test completed cleanly.")
        finally:
            get_memory_file = original_get_memory_file


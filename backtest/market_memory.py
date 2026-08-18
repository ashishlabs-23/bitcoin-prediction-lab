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
    'context_vector_json', 'macro_cycle', 'mvrv_val', 'nupl_val',
    'data_reliability', 'regime_certainty', 'model_agreement', 'volatility_stress',
    'composite_quality_score', 'expected_return_gross_pct', 'expected_return_net_pct',
    'outcome_resolved', 'outcome_resolved_at', 'data_source'
]


def get_memory_file() -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    return os.path.join(RESULTS_DIR, "market_memory.csv")


def get_stress_trials_file() -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    return os.path.join(RESULTS_DIR, "stress_trials.csv")


STRESS_TRIAL_COLUMNS = [
    'trial_id', 'timestamp', 'price', 'direction', 'decision', 'probability',
    'tp', 'sl', 'macro_shock', 'volatility_mult', 'liquidity_shock_pct',
    'hypothetical_return', 'was_correct', 'pnl_bps', 'data_source'
]


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
    macro_cycle: str = "NEUTRAL",
    mvrv_val: float = 1.85,
    nupl_val: float = 0.42,
    data_reliability: float = 1.0,
    regime_certainty: float = 1.0,
    model_agreement: float = 1.0,
    volatility_stress: float = 1.0,
    composite_quality_score: float = 1.0,
    expected_return_gross_pct: float = 0.10,
    expected_return_net_pct: float = 0.00,
    outcome_resolved: bool = False,
    outcome_resolved_at: str = None
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
            "price": price,
            "macro_cycle": macro_cycle
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
        'context_vector_json': str(context_vector_json),
        'macro_cycle': str(macro_cycle),
        'mvrv_val': float(mvrv_val),
        'nupl_val': float(nupl_val),
        'data_reliability': float(data_reliability),
        'regime_certainty': float(regime_certainty),
        'model_agreement': float(model_agreement),
        'volatility_stress': float(volatility_stress),
        'composite_quality_score': float(composite_quality_score),
        'expected_return_gross_pct': float(expected_return_gross_pct),
        'expected_return_net_pct': float(expected_return_net_pct),
        'outcome_resolved': bool(outcome_resolved),
        'outcome_resolved_at': str(outcome_resolved_at) if outcome_resolved_at else None,
        'data_source': 'live_terminal'
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
                    df.loc[mask, 'outcome_resolved'] = True
                    df.loc[mask, 'outcome_resolved_at'] = datetime.now(timezone.utc).isoformat()
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


def resolve_pending_outcomes(current_price: float, current_time_str: str, horizon_hours: int = 4) -> int:
    """
    Two-phase outcome resolver: Scans unresolved prediction records.
    If current_time - prediction_time >= horizon_hours (e.g. 4h or 24h),
    computes actual return, checks correctness, and marks outcome_resolved = True.
    Returns the number of records resolved.
    """
    memory_csv = get_memory_file()
    lock_file = memory_csv + ".lock"

    if not os.path.exists(memory_csv):
        return 0

    resolved_count = 0
    try:
        now_ts = pd.Timestamp(current_time_str).tz_localize(None) if pd.Timestamp(current_time_str).tz is None else pd.Timestamp(current_time_str).tz_convert(None)
    except Exception:
        now_ts = pd.Timestamp.now()

    with file_lock(lock_file):
        try:
            df = pd.read_csv(memory_csv)
            for col in DEFAULT_COLUMNS:
                if col not in df.columns:
                    df[col] = np.nan

            unresolved_mask = (df['outcome_resolved'] == False) | (df['outcome_resolved'].isna())
            if not unresolved_mask.any():
                return 0

            for idx in df[unresolved_mask].index:
                row_ts_str = str(df.loc[idx, 'timestamp'])
                try:
                    row_ts = pd.Timestamp(row_ts_str).tz_localize(None) if pd.Timestamp(row_ts_str).tz is None else pd.Timestamp(row_ts_str).tz_convert(None)
                except Exception:
                    continue

                diff_hours = (now_ts - row_ts).total_seconds() / 3600.0
                if diff_hours >= horizon_hours:
                    entry_p = float(df.loc[idx, 'price'])
                    if entry_p > 0:
                        raw_ret = (float(current_price) - entry_p) / entry_p
                        direction = str(df.loc[idx, 'direction']).upper()
                        if direction == "LONG":
                            strat_ret = raw_ret - 0.0010  # 10 bps fee
                            was_corr = raw_ret > 0
                        elif direction == "SHORT":
                            strat_ret = -raw_ret - 0.0010
                            was_corr = raw_ret < 0
                        else:  # SKIP
                            strat_ret = 0.0
                            # For SKIP, was_corr = True if avoiding the trade saved money or flat
                            was_corr = abs(raw_ret) < 0.005

                        df.loc[idx, 'actual_return'] = round(raw_ret, 6)
                        df.loc[idx, 'pnl'] = round(strat_ret * 10000.0, 2)  # bps pnl
                        df.loc[idx, 'was_correct'] = was_corr
                        df.loc[idx, 'outcome_resolved'] = True
                        df.loc[idx, 'outcome_resolved_at'] = current_time_str
                        resolved_count += 1

            if resolved_count > 0:
                tmp_csv = memory_csv + ".tmp"
                with open(tmp_csv, "w", newline="", encoding="utf-8") as f:
                    df.to_csv(f, index=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_csv, memory_csv)
        except Exception as e:
            print(f"Error resolving pending outcomes: {e}")

    return resolved_count


def record_stress_trial(
    trial_id: str,
    timestamp: str,
    price: float,
    direction: str,
    decision: str,
    probability: float,
    tp: float,
    sl: float,
    macro_shock: str,
    volatility_mult: float,
    liquidity_shock_pct: float,
    hypothetical_return: float,
    was_correct: bool,
    pnl_bps: float,
    data_source: str = "synthetic_arena"
) -> None:
    """Appends a synthetic Monte Carlo stress experiment trial to separate results/stress_trials.csv."""
    stress_csv = get_stress_trials_file()
    lock_file = stress_csv + ".lock"

    new_row = {
        'trial_id': str(trial_id),
        'timestamp': str(timestamp),
        'price': float(price),
        'direction': str(direction),
        'decision': str(decision),
        'probability': float(probability),
        'tp': float(tp),
        'sl': float(sl),
        'macro_shock': str(macro_shock),
        'volatility_mult': float(volatility_mult),
        'liquidity_shock_pct': float(liquidity_shock_pct),
        'hypothetical_return': float(hypothetical_return),
        'was_correct': bool(was_correct),
        'pnl_bps': float(pnl_bps),
        'data_source': str(data_source)
    }

    with file_lock(lock_file):
        if os.path.exists(stress_csv) and os.path.getsize(stress_csv) > 0:
            try:
                df = pd.read_csv(stress_csv)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            except Exception:
                df = pd.DataFrame([new_row], columns=STRESS_TRIAL_COLUMNS)
        else:
            df = pd.DataFrame([new_row], columns=STRESS_TRIAL_COLUMNS)

        tmp_csv = stress_csv + ".tmp"
        with open(tmp_csv, "w", newline="", encoding="utf-8") as f:
            df.to_csv(f, index=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_csv, stress_csv)


def load_stress_trials(limit: int = 100) -> pd.DataFrame:
    """Loads recorded synthetic stress trials from results/stress_trials.csv."""
    stress_csv = get_stress_trials_file()
    if not os.path.exists(stress_csv) or os.path.getsize(stress_csv) == 0:
        return pd.DataFrame(columns=STRESS_TRIAL_COLUMNS)
    try:
        df = pd.read_csv(stress_csv)
        return df.tail(limit)
    except Exception:
        return pd.DataFrame(columns=STRESS_TRIAL_COLUMNS)


def sanitize_market_memory() -> int:
    """Purges any synthetic arena rows or simulated artifacts from market_memory.csv to guarantee zero contamination."""
    memory_csv = get_memory_file()
    if not os.path.exists(memory_csv) or os.path.getsize(memory_csv) == 0:
        return 0
    lock_file = memory_csv + ".lock"
    purged_count = 0
    with file_lock(lock_file):
        try:
            df = pd.read_csv(memory_csv)
            initial_len = len(df)
            # Purge any row starting with SIM_ARENA_ or tagged synthetic_arena
            clean_df = df[~df['regime'].astype(str).str.startswith("SIM_ARENA_")].copy()
            if 'data_source' in clean_df.columns:
                clean_df = clean_df[clean_df['data_source'] != 'synthetic_arena'].copy()
            else:
                clean_df['data_source'] = 'live_terminal'
            purged_count = initial_len - len(clean_df)
            if purged_count > 0 or 'data_source' not in df.columns:
                tmp_csv = memory_csv + ".tmp"
                with open(tmp_csv, "w", newline="", encoding="utf-8") as f:
                    clean_df.to_csv(f, index=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_csv, memory_csv)
        except Exception as e:
            print(f"Error sanitizing market memory: {e}")
    return purged_count


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


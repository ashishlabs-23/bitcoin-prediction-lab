"""
backtest/market_memory.py — Dual-Layer Market Memory Engine
===========================================================
High-performance dual-layer memory persistence:
1. Operational Layer: SQLite with WAL mode (fast atomic concurrent reads/writes)
2. Export & File Layer: Synchronized CSV & Parquet for testing, ML datasets and reproducibility.
"""

import os
import sys
import uuid
import time
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR

logger = logging.getLogger("btcognitive.market_memory")

DB_PATH = os.path.join(RESULTS_DIR, "market_memory.db")
CSV_PATH = os.path.join(RESULTS_DIR, "market_memory.csv")
EXPORTS_DIR = os.path.join(RESULTS_DIR, "exports")

DEFAULT_COLUMNS = [
    'prediction_id', 'timestamp', 'candle_time', 'price', 'regime', 'raw_prob',
    'calibrated_prob', 'decision', 'actual_return', 'was_correct', 'pnl',
    'direction', 'tp', 'sl', 'model_version', 'feature_version', 'regime_version',
    'context_vector_json', 'macro_cycle', 'mvrv_val', 'nupl_val',
    'data_reliability', 'regime_certainty', 'model_agreement', 'volatility_stress',
    'composite_quality_score', 'expected_return_gross_pct', 'expected_return_net_pct',
    'outcome_resolved', 'outcome_resolved_at', 'data_source'
]

STRESS_TRIAL_COLUMNS = [
    'trial_id', 'timestamp', 'price', 'direction', 'decision', 'probability',
    'tp', 'sl', 'macro_shock', 'volatility_mult', 'liquidity_shock_pct',
    'hypothetical_return', 'was_correct', 'pnl_bps', 'data_source'
]


def get_memory_file() -> str:
    """Returns CSV filepath for backwards compatibility and test isolation."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    return CSV_PATH


def get_stress_trials_file() -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    return os.path.join(RESULTS_DIR, "stress_trials.csv")


def _get_db(db_file: Optional[str] = None) -> sqlite3.Connection:
    """Returns thread-safe SQLite connection with WAL mode enabled."""
    target_db = db_file or DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target_db)), exist_ok=True)
    conn = sqlite3.connect(target_db, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def _init_tables(conn: sqlite3.Connection):
    """Initializes operational tables in SQLite."""
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                prediction_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                candle_time TEXT,
                price REAL NOT NULL,
                regime TEXT NOT NULL,
                raw_prob REAL NOT NULL,
                calibrated_prob REAL NOT NULL,
                decision TEXT NOT NULL,
                actual_return REAL DEFAULT 0.0,
                was_correct INTEGER DEFAULT 1,
                pnl REAL DEFAULT 0.0,
                direction TEXT NOT NULL,
                tp REAL,
                sl REAL,
                model_version TEXT,
                feature_version TEXT,
                regime_version TEXT,
                context_vector_json TEXT,
                macro_cycle TEXT,
                mvrv_val REAL,
                nupl_val REAL,
                data_reliability REAL,
                regime_certainty REAL,
                model_agreement REAL,
                volatility_stress REAL,
                composite_quality_score REAL,
                expected_return_gross_pct REAL,
                expected_return_net_pct REAL,
                outcome_resolved INTEGER DEFAULT 0,
                outcome_resolved_at TEXT,
                data_source TEXT DEFAULT 'live_terminal'
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pred_ts ON predictions(timestamp);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pred_resolved ON predictions(outcome_resolved);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pred_regime ON predictions(regime);")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS stress_trials (
                trial_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                direction TEXT NOT NULL,
                decision TEXT NOT NULL,
                probability REAL NOT NULL,
                tp REAL,
                sl REAL,
                macro_shock TEXT,
                volatility_mult REAL,
                liquidity_shock_pct REAL,
                hypothetical_return REAL,
                was_correct INTEGER,
                pnl_bps REAL,
                data_source TEXT DEFAULT 'synthetic_arena'
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS range_forecasts (
                forecast_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL DEFAULT 'BTCUSD',
                horizon TEXT NOT NULL DEFAULT '24h',
                current_price REAL NOT NULL,
                upper_p10 REAL,
                upper_p25 REAL,
                upper_p50 REAL,
                upper_p75 REAL,
                upper_p90 REAL,
                lower_p10 REAL,
                lower_p25 REAL,
                lower_p50 REAL,
                lower_p75 REAL,
                lower_p90 REAL,
                uncertainty REAL,
                coverage_confidence REAL,
                market_regime TEXT,
                data_quality TEXT,
                degraded INTEGER DEFAULT 0,
                model_version TEXT,
                created_at TEXT NOT NULL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rf_ts ON range_forecasts(timestamp);")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS excursion_forecasts (
                forecast_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL DEFAULT 'BTCUSD',
                horizon TEXT NOT NULL DEFAULT '24h',
                mfe_p10 REAL,
                mfe_p25 REAL,
                mfe_p50 REAL,
                mfe_p75 REAL,
                mfe_p90 REAL,
                mae_p10 REAL,
                mae_p25 REAL,
                mae_p50 REAL,
                mae_p75 REAL,
                mae_p90 REAL,
                exp_mfe REAL,
                exp_mae REAL,
                model_version TEXT,
                created_at TEXT NOT NULL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ef_ts ON excursion_forecasts(timestamp);")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS uncertainty_forecasts (
                forecast_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL DEFAULT 'BTCUSD',
                interval_width REAL,
                relative_uncertainty REAL,
                data_quality_score REAL,
                forecast_state TEXT,
                created_at TEXT NOT NULL
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS forecast_outcomes (
                outcome_id TEXT PRIMARY KEY,
                forecast_id TEXT NOT NULL,
                prediction_timestamp TEXT NOT NULL,
                resolution_timestamp TEXT NOT NULL,
                actual_high REAL NOT NULL,
                actual_low REAL NOT NULL,
                actual_close REAL NOT NULL,
                actual_mfe REAL NOT NULL,
                actual_mae REAL NOT NULL,
                mfe_error REAL,
                mae_error REAL,
                upper_covered INTEGER NOT NULL,
                lower_covered INTEGER NOT NULL,
                path_contained INTEGER NOT NULL,
                regime TEXT,
                data_quality TEXT,
                created_at TEXT NOT NULL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fo_fc_id ON forecast_outcomes(forecast_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fo_ts ON forecast_outcomes(prediction_timestamp);")


try:
    _conn = _get_db()
    _init_tables(_conn)
    _conn.close()
except Exception:
    pass


# ---------------------------------------------------------------------------
# Core Operational Operations
# ---------------------------------------------------------------------------

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
    """Appends a new versioned prediction record into SQLite WAL and syncs CSV."""
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

    record_dict = {
        'prediction_id': str(prediction_id),
        'timestamp': str(timestamp),
        'candle_time': str(candle_time if candle_time else timestamp),
        'price': float(price),
        'regime': str(regime),
        'raw_prob': float(raw_prob),
        'calibrated_prob': float(calibrated_prob),
        'decision': str(decision),
        'actual_return': float(actual_return),
        'was_correct': 1 if was_correct else 0,
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
        'outcome_resolved': 1 if outcome_resolved else 0,
        'outcome_resolved_at': str(outcome_resolved_at) if outcome_resolved_at else None,
        'data_source': 'live_terminal'
    }

    # 1. Insert into SQLite
    conn = _get_db()
    _init_tables(conn)
    try:
        with conn:
            cols = list(record_dict.keys())
            placeholders = ", ".join(["?" for _ in cols])
            query = f"INSERT OR REPLACE INTO predictions ({', '.join(cols)}) VALUES ({placeholders})"
            conn.execute(query, list(record_dict.values()))
    except Exception as e:
        logger.error(f"Error inserting prediction into SQLite: {e}")
    finally:
        conn.close()

    # 2. Sync to CSV for testing & external exports
    csv_file = get_memory_file()
    try:
        rec_for_df = record_dict.copy()
        rec_for_df['was_correct'] = bool(was_correct)
        rec_for_df['outcome_resolved'] = bool(outcome_resolved)
        new_row_df = pd.DataFrame([rec_for_df])
        if os.path.exists(csv_file) and os.path.getsize(csv_file) > 0:
            existing = pd.read_csv(csv_file)
            combined = pd.concat([existing, new_row_df], ignore_index=True)
        else:
            combined = new_row_df
        combined.to_csv(csv_file, index=False)
    except Exception as e:
        logger.warning(f"Error syncing prediction to CSV: {e}")

    return load_market_memory()


def load_market_memory() -> pd.DataFrame:
    """Loads historical Market Memory predictions."""
    csv_file = get_memory_file()
    # If a specific/custom CSV exists (e.g. during pytest monkeypatch), load directly from it
    if os.path.exists(csv_file) and os.path.getsize(csv_file) > 0:
        try:
            df = pd.read_csv(csv_file)
            for col in DEFAULT_COLUMNS:
                if col not in df.columns:
                    df[col] = np.nan
            if 'was_correct' in df.columns:
                df['was_correct'] = df['was_correct'].astype(bool)
            if 'outcome_resolved' in df.columns:
                df['outcome_resolved'] = df['outcome_resolved'].astype(bool)
            return df
        except Exception:
            pass

    conn = _get_db()
    _init_tables(conn)
    try:
        df = pd.read_sql_query("SELECT * FROM predictions ORDER BY timestamp ASC", conn)
        df['was_correct'] = df['was_correct'].astype(bool)
        df['outcome_resolved'] = df['outcome_resolved'].astype(bool)
        return df
    except Exception as e:
        logger.error(f"Error loading market memory from SQLite: {e}")
        return pd.DataFrame(columns=DEFAULT_COLUMNS)
    finally:
        conn.close()


def query_similar_context(current_context: dict, top_k: int = 20) -> pd.DataFrame:
    """Retrieves historical Market Memory outcomes under similar market contexts."""
    conn = _get_db()
    target_regime = current_context.get('regime', '')
    try:
        if target_regime:
            df = pd.read_sql_query(
                "SELECT * FROM predictions WHERE regime = ? ORDER BY timestamp DESC LIMIT ?",
                conn,
                params=(target_regime, top_k)
            )
            if not df.empty:
                return df.iloc[::-1].reset_index(drop=True)
        df = pd.read_sql_query("SELECT * FROM predictions ORDER BY timestamp DESC LIMIT ?", conn, params=(top_k,))
        return df.iloc[::-1].reset_index(drop=True)
    except Exception as e:
        logger.error(f"Error querying similar context: {e}")
        return pd.DataFrame(columns=DEFAULT_COLUMNS)
    finally:
        conn.close()


def update_prediction_outcome(prediction_id: str, actual_return: float, was_correct: bool, pnl: float) -> bool:
    """Updates an existing prediction record atomically in SQLite & CSV."""
    conn = _get_db()
    try:
        with conn:
            cur = conn.execute("""
                UPDATE predictions
                SET actual_return = ?, was_correct = ?, pnl = ?, outcome_resolved = 1, outcome_resolved_at = ?
                WHERE prediction_id = ?
            """, (float(actual_return), 1 if was_correct else 0, float(pnl), datetime.now(timezone.utc).isoformat(), str(prediction_id)))
            updated = cur.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating prediction outcome: {e}")
        updated = False
    finally:
        conn.close()

    csv_file = get_memory_file()
    if os.path.exists(csv_file):
        try:
            df = pd.read_csv(csv_file)
            mask = df['prediction_id'] == str(prediction_id)
            if mask.any():
                df.loc[mask, 'actual_return'] = float(actual_return)
                df.loc[mask, 'was_correct'] = bool(was_correct)
                df.loc[mask, 'pnl'] = float(pnl)
                df.loc[mask, 'outcome_resolved'] = True
                df.loc[mask, 'outcome_resolved_at'] = datetime.now(timezone.utc).isoformat()
                df.to_csv(csv_file, index=False)
        except Exception:
            pass

    return updated


def resolve_pending_outcomes(current_price: float, current_time_str: str, horizon_hours: int = 4) -> int:
    """
    Two-phase outcome resolver: Queries unresolved records,
    computes return, and marks outcome_resolved = 1.
    """
    conn = _get_db()
    resolved_count = 0

    try:
        now_ts = pd.Timestamp(current_time_str).tz_localize(None) if pd.Timestamp(current_time_str).tz is None else pd.Timestamp(current_time_str).tz_convert(None)
    except Exception:
        now_ts = pd.Timestamp.now()

    try:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT prediction_id, timestamp, price, direction FROM predictions WHERE outcome_resolved = 0").fetchall()
        
        updates = []
        for r in rows:
            p_id, ts_str, entry_p, direction = r[0], r[1], float(r[2]), str(r[3]).upper()
            try:
                row_ts = pd.Timestamp(ts_str).tz_localize(None) if pd.Timestamp(ts_str).tz is None else pd.Timestamp(ts_str).tz_convert(None)
            except Exception:
                continue

            diff_hours = (now_ts - row_ts).total_seconds() / 3600.0
            if diff_hours >= horizon_hours and entry_p > 0:
                raw_ret = (float(current_price) - entry_p) / entry_p
                if direction == "LONG":
                    strat_ret = raw_ret - 0.0010
                    was_corr = 1 if raw_ret > 0 else 0
                elif direction == "SHORT":
                    strat_ret = -raw_ret - 0.0010
                    was_corr = 1 if raw_ret < 0 else 0
                else:
                    strat_ret = 0.0
                    was_corr = 1 if abs(raw_ret) < 0.005 else 0

                pnl = round(strat_ret * 10000.0, 2)
                updates.append((round(raw_ret, 6), was_corr, pnl, current_time_str, p_id))

        if updates:
            with conn:
                conn.executemany("""
                    UPDATE predictions
                    SET actual_return = ?, was_correct = ?, pnl = ?, outcome_resolved = 1, outcome_resolved_at = ?
                    WHERE prediction_id = ?
                """, updates)
            resolved_count = len(updates)
    except Exception as e:
        logger.error(f"Error resolving pending outcomes in SQLite: {e}")
    finally:
        conn.close()

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
    """Inserts a synthetic Monte Carlo stress experiment trial into SQLite & stress_trials.csv."""
    stress_file = get_stress_trials_file()
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

    # 1. Sync to stress_trials.csv
    try:
        new_df = pd.DataFrame([new_row])
        if os.path.exists(stress_file) and os.path.getsize(stress_file) > 0:
            existing = pd.read_csv(stress_file)
            combined = pd.concat([existing, new_df], ignore_index=True)
        else:
            combined = new_df
        combined.to_csv(stress_file, index=False)
    except Exception as e:
        logger.warning(f"Error writing to stress_trials.csv: {e}")

    # 2. Insert into SQLite
    conn = _get_db()
    _init_tables(conn)
    try:
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO stress_trials (
                    trial_id, timestamp, price, direction, decision, probability,
                    tp, sl, macro_shock, volatility_mult, liquidity_shock_pct,
                    hypothetical_return, was_correct, pnl_bps, data_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(trial_id), str(timestamp), float(price), str(direction), str(decision), float(probability),
                float(tp), float(sl), str(macro_shock), float(volatility_mult), float(liquidity_shock_pct),
                float(hypothetical_return), 1 if was_correct else 0, float(pnl_bps), str(data_source)
            ))
    except Exception as e:
        logger.error(f"Error recording stress trial in SQLite: {e}")
    finally:
        conn.close()


def load_stress_trials(limit: int = 100) -> pd.DataFrame:
    """Loads recorded synthetic stress trials from stress_trials.csv or SQLite."""
    stress_csv = get_stress_trials_file()
    if os.path.exists(stress_csv) and os.path.getsize(stress_csv) > 0:
        try:
            df = pd.read_csv(stress_csv)
            if 'was_correct' in df.columns:
                df['was_correct'] = df['was_correct'].astype(bool)
            return df.tail(limit)
        except Exception:
            pass

    conn = _get_db()
    _init_tables(conn)
    try:
        df = pd.read_sql_query("SELECT * FROM stress_trials ORDER BY timestamp DESC LIMIT ?", conn, params=(limit,))
        df['was_correct'] = df['was_correct'].astype(bool)
        return df.iloc[::-1].reset_index(drop=True)
    except Exception as e:
        logger.error(f"Error loading stress trials: {e}")
        return pd.DataFrame(columns=STRESS_TRIAL_COLUMNS)
    finally:
        conn.close()


def sanitize_market_memory() -> int:
    """Purges any synthetic arena rows or simulated artifacts from predictions."""
    csv_file = get_memory_file()
    purged_count = 0
    if os.path.exists(csv_file) and os.path.getsize(csv_file) > 0:
        try:
            df = pd.read_csv(csv_file)
            initial_len = len(df)
            clean_df = df[~df['regime'].astype(str).str.startswith("SIM_ARENA_")].copy()
            if 'data_source' in clean_df.columns:
                clean_df = clean_df[clean_df['data_source'] != 'synthetic_arena'].copy()
            else:
                clean_df['data_source'] = 'live_terminal'
            purged_count = initial_len - len(clean_df)
            if purged_count > 0 or 'data_source' not in df.columns:
                clean_df.to_csv(csv_file, index=False)
        except Exception as e:
            logger.error(f"Error sanitizing CSV market memory: {e}")

    conn = _get_db()
    try:
        with conn:
            cur = conn.execute("DELETE FROM predictions WHERE regime LIKE 'SIM_ARENA_%' OR data_source = 'synthetic_arena'")
            if cur.rowcount > purged_count:
                purged_count = cur.rowcount
    except Exception as e:
        logger.error(f"Error sanitizing SQLite market memory: {e}")
    finally:
        conn.close()

    return purged_count


def export_market_memory_datasets(target_csv: Optional[str] = None, target_parquet: Optional[str] = None):
    """Exports SQLite operational memory to Parquet & CSV for external ML tools."""
    df = load_market_memory()
    if df.empty:
        return

    csv_dest = target_csv or CSV_PATH
    try:
        df.to_csv(csv_dest, index=False)
    except Exception as e:
        logger.warning(f"Failed exporting to CSV: {e}")

    try:
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        pq_dest = target_parquet or os.path.join(EXPORTS_DIR, "market_memory.parquet")
        df.to_parquet(pq_dest, index=False, engine="pyarrow")
    except Exception as e:
        logger.warning(f"Failed exporting to Parquet: {e}")

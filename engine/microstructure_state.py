"""
engine/microstructure_state.py — MEIE Layer 1: Continuous Z-Score State Vector
===============================================================================
Normalizes raw microstructure signals into a rolling z-score vector:
    s_t = [z_hawkes, z_ofi, z_vpin, z_depth, z_spread, z_impact]

Design constraints (Ponytail):
  - NO thresholds. Pure normalization only. Thresholds live in preregistration docs.
  - NO new dependencies. Uses numpy + sqlite3 already used project-wide.
  - Reads from existing data sources: hawkes_shadow_session outputs and aggTrades-derived proxies.
  - Rolling window: 168 candles (168 × 1-min = 2.8h), stored in meie_memory.db.

Preregistration reference: results/meie_event01_preregistration.md (MEIE-EVENT-01-v1.0)
"""

import os
import sys
import sqlite3
import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR

logger = logging.getLogger("btcognitive.microstructure_state")

MEIE_DB_PATH = os.path.join(RESULTS_DIR, "meie_memory.db")
ROLLING_WINDOW = 168  # candles — locked in preregistration MEIE-EVENT-01-v1.0


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MicrostructureStateVector:
    """Continuous z-score state vector for one candle tick. No thresholds — pure signal."""
    timestamp: str
    price: float

    # Raw signals (before normalization, for auditability)
    raw_hawkes_intensity: float  # lambda_buy + lambda_sell
    raw_ofi: float               # buyer fraction (0..1) from aggTrades
    raw_vpin: float              # rolling VPIN (0..1)
    raw_depth: float             # volume proxy for top-of-book depth
    raw_spread: float            # (high - low) / close per candle
    raw_impact: float            # |close - open| / volume

    # Z-scores over trailing 168-candle window
    z_hawkes: float
    z_ofi: float
    z_vpin: float
    z_depth: float    # negative = thin (low volume)
    z_spread: float
    z_impact: float

    # Metadata
    window_n: int        # actual samples in rolling window (may be < 168 early on)
    data_quality: str    # VALID | DEGRADED | INSUFFICIENT

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# DB initialization (separate meie_memory.db, isolated from arena_memory.db)
# ---------------------------------------------------------------------------

def _get_meie_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(MEIE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(MEIE_DB_PATH, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def _init_meie_db():
    conn = _get_meie_db()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS microstructure_raw (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                raw_hawkes REAL NOT NULL,
                raw_ofi REAL NOT NULL,
                raw_vpin REAL NOT NULL,
                raw_depth REAL NOT NULL,
                raw_spread REAL NOT NULL,
                raw_impact REAL NOT NULL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_msr_ts ON microstructure_raw(timestamp);")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meie_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                event_type TEXT NOT NULL,
                z_hawkes REAL NOT NULL,
                z_ofi REAL NOT NULL,
                z_vpin REAL NOT NULL,
                z_depth REAL NOT NULL,
                z_spread REAL NOT NULL,
                z_impact REAL NOT NULL,
                window_n INTEGER NOT NULL,
                data_quality TEXT NOT NULL,
                direction TEXT DEFAULT 'AMBIGUOUS',
                outcome_15m REAL,
                outcome_30m REAL,
                resolved INTEGER DEFAULT 0
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_me_ts ON meie_events(timestamp);")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meie_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                tp_price REAL NOT NULL,
                sl_price REAL NOT NULL,
                ev_predicted_bps REAL NOT NULL,
                gross_pnl_bps REAL,
                fee_bps REAL DEFAULT 10.0,
                slippage_bps REAL,
                net_pnl_bps REAL,
                exit_reason TEXT,
                resolved INTEGER DEFAULT 0
            );
        """)
    conn.close()


_init_meie_db()


# ---------------------------------------------------------------------------
# Raw signal persistence
# ---------------------------------------------------------------------------

def _store_raw(timestamp: str, price: float,
               raw_hawkes: float, raw_ofi: float, raw_vpin: float,
               raw_depth: float, raw_spread: float, raw_impact: float):
    conn = _get_meie_db()
    try:
        with conn:
            conn.execute(
                "INSERT INTO microstructure_raw "
                "(timestamp, price, raw_hawkes, raw_ofi, raw_vpin, raw_depth, raw_spread, raw_impact) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                (timestamp, price, raw_hawkes, raw_ofi, raw_vpin, raw_depth, raw_spread, raw_impact)
            )
    finally:
        conn.close()


def _load_rolling_window() -> Dict[str, np.ndarray]:
    """Loads last ROLLING_WINDOW rows of raw signals from meie_memory.db."""
    conn = _get_meie_db()
    try:
        cur = conn.execute(
            "SELECT raw_hawkes, raw_ofi, raw_vpin, raw_depth, raw_spread, raw_impact "
            "FROM microstructure_raw ORDER BY id DESC LIMIT ?;",
            (ROLLING_WINDOW,)
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return {}
    arr = np.array(rows, dtype=np.float64)
    return {
        "hawkes": arr[:, 0],
        "ofi": arr[:, 1],
        "vpin": arr[:, 2],
        "depth": arr[:, 3],
        "spread": arr[:, 4],
        "impact": arr[:, 5],
    }


# ---------------------------------------------------------------------------
# Z-score normalization (safe: std=0 → z=0)
# ---------------------------------------------------------------------------

def _zscore(value: float, series: np.ndarray) -> float:
    if len(series) < 2:
        return 0.0
    mu, sigma = float(np.mean(series)), float(np.std(series, ddof=1))
    if sigma < 1e-10:
        return 0.0
    return float((value - mu) / sigma)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def compute_state_vector(
    timestamp: str,
    price: float,
    candle: Dict[str, Any],
    hawkes_snapshot: Optional[Dict[str, Any]] = None,
    vpin_snapshot: Optional[float] = None,
) -> MicrostructureStateVector:
    """
    Computes the z-score state vector for one candle tick.

    Args:
        timestamp: ISO-8601 candle close timestamp.
        price: Close price of the candle.
        candle: Dict with keys: high, low, close, open, volume.
        hawkes_snapshot: Optional dict from HawkesShadowSession with
                         keys lambda_buy, lambda_sell (floats).
        vpin_snapshot: Optional float, latest rolling VPIN [0..1].

    Returns:
        MicrostructureStateVector with z-scores and data quality label.
    """
    high = float(candle.get("high", price))
    low = float(candle.get("low", price))
    close = float(candle.get("close", price))
    open_ = float(candle.get("open", price))
    volume = max(1e-8, float(candle.get("volume", 1.0)))

    # Raw signal extraction
    if hawkes_snapshot:
        lb = max(0.0, float(hawkes_snapshot.get("lambda_buy", 0.0)))
        ls = max(0.0, float(hawkes_snapshot.get("lambda_sell", 0.0)))
        raw_hawkes = lb + ls
        total = lb + ls
        raw_ofi = (lb - ls) / max(1e-8, total)  # signed imbalance in [−1, +1]
    else:
        raw_hawkes = 0.0
        raw_ofi = 0.0

    raw_vpin = float(np.clip(vpin_snapshot or 0.30, 0.0, 1.0))
    raw_depth = volume                              # higher volume = deeper book proxy
    raw_spread = (high - low) / max(1e-8, close)  # normalized candle range
    raw_impact = abs(close - open_) / volume       # price-per-unit-volume

    # Store to rolling window
    _store_raw(timestamp, price, raw_hawkes, raw_ofi, raw_vpin,
               raw_depth, raw_spread, raw_impact)

    # Load window and compute z-scores
    window = _load_rolling_window()
    n = len(window.get("hawkes", []))

    if n < 10:
        dq = "INSUFFICIENT"
    elif n < ROLLING_WINDOW:
        dq = "DEGRADED"
    else:
        dq = "VALID"

    z_hawkes = _zscore(raw_hawkes, window.get("hawkes", np.array([raw_hawkes])))
    z_ofi    = _zscore(raw_ofi,    window.get("ofi",    np.array([raw_ofi])))
    z_vpin   = _zscore(raw_vpin,   window.get("vpin",   np.array([raw_vpin])))
    z_depth  = _zscore(raw_depth,  window.get("depth",  np.array([raw_depth])))
    z_spread = _zscore(raw_spread, window.get("spread", np.array([raw_spread])))
    z_impact = _zscore(raw_impact, window.get("impact", np.array([raw_impact])))

    return MicrostructureStateVector(
        timestamp=timestamp,
        price=price,
        raw_hawkes_intensity=raw_hawkes,
        raw_ofi=raw_ofi,
        raw_vpin=raw_vpin,
        raw_depth=raw_depth,
        raw_spread=raw_spread,
        raw_impact=raw_impact,
        z_hawkes=z_hawkes,
        z_ofi=z_ofi,
        z_vpin=z_vpin,
        z_depth=z_depth,
        z_spread=z_spread,
        z_impact=z_impact,
        window_n=n,
        data_quality=dq,
    )

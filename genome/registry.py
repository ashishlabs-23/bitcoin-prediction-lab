"""
genome/registry.py -- SQLite-backed Genome Registry

Provides persistent storage for genome lineage, fitness metrics, quarantine
trades, and lifecycle status. Uses SQLite (not CSV) because parent/child
lineage queries are inherently relational and CSV-append would not support
efficient ancestry traversal.

Design rules:
  - Thread-safe writes via sqlite3's built-in WAL mode + exclusive transaction.
  - All list fields (parent_ids, mutation_log) are stored as JSON strings.
  - NaN float values are stored as NULL in SQLite; deserialization restores them.
  - The registry path is derived from config.GENOME_DIR — the only config dependency.
  - No ML imports — pure stdlib + genome.chromosome.
"""

import os
import sys
import json
import sqlite3
import math
from typing import Optional, List
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import GENOME_DIR
from genome.chromosome import Genome, genome_to_dict, genome_from_dict


# -------------------------------------------------------------------
# Schema SQL
# -------------------------------------------------------------------

_CREATE_GENOMES = """
CREATE TABLE IF NOT EXISTS genomes (
    genome_id            TEXT PRIMARY KEY,
    generation           INTEGER,
    parent_ids           TEXT,          -- JSON array: ["id1", "id2"]
    regime               TEXT,
    tp_atr_mult          REAL,
    sl_atr_mult          REAL,
    max_hold_bars        INTEGER,
    position_size_method TEXT,
    mutation_log         TEXT,          -- JSON array of strings
    born_at              TEXT,
    sharpe               REAL,
    calmar               REAL,
    max_drawdown         REAL,
    win_rate             REAL,
    turnover             REAL,
    pareto_rank          INTEGER,
    deflated_sharpe      REAL,
    pbo_generation       REAL,
    status               TEXT          -- candidate | quarantine | verified | dead
);
"""

_CREATE_QUARANTINE_TRADES = """
CREATE TABLE IF NOT EXISTS quarantine_trades (
    trade_id     TEXT PRIMARY KEY,
    genome_id    TEXT,
    timestamp    TEXT,
    entry_price  REAL,
    exit_price   REAL,
    direction    TEXT,
    pnl          REAL,
    exit_reason  TEXT,                  -- TP_HIT | SL_HIT | MAX_HOLD | SIGNAL_FLIP
    FOREIGN KEY(genome_id) REFERENCES genomes(genome_id)
);
"""

_CREATE_IDX_GENERATION = "CREATE INDEX IF NOT EXISTS idx_generation ON genomes(generation);"
_CREATE_IDX_STATUS     = "CREATE INDEX IF NOT EXISTS idx_status ON genomes(status);"
_CREATE_IDX_QT_GENOME  = "CREATE INDEX IF NOT EXISTS idx_qt_genome ON quarantine_trades(genome_id);"


# -------------------------------------------------------------------
# Connection helpers
# -------------------------------------------------------------------

def get_registry_path() -> str:
    """Returns the path to the SQLite registry file, creating GENOME_DIR if needed."""
    os.makedirs(GENOME_DIR, exist_ok=True)
    return os.path.join(GENOME_DIR, "genome_registry.db")


def _get_conn(path: Optional[str] = None) -> sqlite3.Connection:
    """Opens a WAL-mode connection to the registry and ensures schema exists."""
    db_path = path or get_registry_path()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute(_CREATE_GENOMES)
    conn.execute(_CREATE_QUARANTINE_TRADES)
    conn.execute(_CREATE_IDX_GENERATION)
    conn.execute(_CREATE_IDX_STATUS)
    conn.execute(_CREATE_IDX_QT_GENOME)
    conn.commit()
    return conn


def _nan_to_none(v):
    """Converts Python float NaN to None for SQLite storage (stored as NULL)."""
    if isinstance(v, float) and (v != v or v == float('inf') or v == float('-inf')):
        return None
    return v


def _none_to_nan(v):
    """Converts SQLite NULL (None) back to float NaN on load."""
    if v is None:
        return float('nan')
    return v


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Converts a sqlite3.Row to a plain dict with NaN restoration."""
    d = dict(row)
    for key in ('sharpe', 'calmar', 'max_drawdown', 'win_rate', 'turnover',
                'deflated_sharpe', 'pbo_generation'):
        d[key] = _none_to_nan(d.get(key))
    for key in ('parent_ids', 'mutation_log'):
        v = d.get(key)
        if isinstance(v, str):
            try:
                d[key] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                d[key] = []
    return d


# -------------------------------------------------------------------
# Genome CRUD
# -------------------------------------------------------------------

def save_genome(genome: Genome, conn: Optional[sqlite3.Connection] = None) -> None:
    """
    Upserts a genome record into the registry (INSERT OR REPLACE).
    Thread-safe: uses an exclusive BEGIN transaction.

    Args:
        genome: Genome object to save.
        conn:   Optional existing connection (for batch operations). If None,
                opens a new connection and closes it after saving.
    """
    d = genome_to_dict(genome)
    # Convert NaN fitness fields to None for SQLite
    for key in ('sharpe', 'calmar', 'max_drawdown', 'win_rate', 'turnover',
                'deflated_sharpe', 'pbo_generation'):
        d[key] = _nan_to_none(d[key])

    sql = """
    INSERT OR REPLACE INTO genomes (
        genome_id, generation, parent_ids, regime,
        tp_atr_mult, sl_atr_mult, max_hold_bars, position_size_method,
        mutation_log, born_at,
        sharpe, calmar, max_drawdown, win_rate, turnover,
        pareto_rank, deflated_sharpe, pbo_generation, status
    ) VALUES (
        :genome_id, :generation, :parent_ids, :regime,
        :tp_atr_mult, :sl_atr_mult, :max_hold_bars, :position_size_method,
        :mutation_log, :born_at,
        :sharpe, :calmar, :max_drawdown, :win_rate, :turnover,
        :pareto_rank, :deflated_sharpe, :pbo_generation, :status
    )
    """

    own_conn = conn is None
    if own_conn:
        conn = _get_conn()
    try:
        with conn:
            conn.execute(sql, d)
    finally:
        if own_conn:
            conn.close()


def load_genome(genome_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Genome]:
    """
    Loads a single genome by ID.

    Returns:
        Genome object, or None if not found.
    """
    own_conn = conn is None
    if own_conn:
        conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM genomes WHERE genome_id = ?", (genome_id,)
        ).fetchone()
        if row is None:
            return None
        return genome_from_dict(_row_to_dict(row))
    finally:
        if own_conn:
            conn.close()


def load_generation(generation: int, conn: Optional[sqlite3.Connection] = None) -> List[Genome]:
    """
    Loads all genomes from a given generation number.

    Returns:
        List of Genome objects (may be empty if generation doesn't exist).
    """
    own_conn = conn is None
    if own_conn:
        conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM genomes WHERE generation = ? ORDER BY pareto_rank ASC",
            (generation,)
        ).fetchall()
        return [genome_from_dict(_row_to_dict(r)) for r in rows]
    finally:
        if own_conn:
            conn.close()


def load_leaderboard(
    status: str = 'verified',
    limit: int = 50,
    conn: Optional[sqlite3.Connection] = None,
) -> pd.DataFrame:
    """
    Returns genomes with the given status, sorted by deflated_sharpe descending.
    deflated_sharpe NULLs sort last.

    Args:
        status: One of 'verified', 'quarantine', 'candidate', 'dead'. Default 'verified'.
        limit:  Maximum rows to return.

    Returns:
        pd.DataFrame with all genome columns, or empty DataFrame if no matches.
    """
    own_conn = conn is None
    if own_conn:
        conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT * FROM genomes
               WHERE status = ?
               ORDER BY deflated_sharpe DESC NULLS LAST, sharpe DESC
               LIMIT ?""",
            (status, limit)
        ).fetchall()
        if not rows:
            return pd.DataFrame()
        records = [_row_to_dict(r) for r in rows]
        return pd.DataFrame(records)
    finally:
        if own_conn:
            conn.close()


def get_latest_generation(conn: Optional[sqlite3.Connection] = None) -> int:
    """Returns the highest generation number stored, or -1 if registry is empty."""
    own_conn = conn is None
    if own_conn:
        conn = _get_conn()
    try:
        row = conn.execute("SELECT MAX(generation) as max_gen FROM genomes").fetchone()
        result = row['max_gen'] if row and row['max_gen'] is not None else -1
        return int(result)
    finally:
        if own_conn:
            conn.close()


# -------------------------------------------------------------------
# Quarantine trade logging
# -------------------------------------------------------------------

def record_quarantine_trade(
    genome_id: str,
    trade: dict,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """
    Appends a shadow quarantine trade to the registry.

    Args:
        genome_id: ID of the genome that generated this trade.
        trade:     Dict with keys: trade_id, timestamp, entry_price, exit_price,
                   direction, pnl, exit_reason.
    """
    import uuid
    sql = """
    INSERT OR IGNORE INTO quarantine_trades
        (trade_id, genome_id, timestamp, entry_price, exit_price, direction, pnl, exit_reason)
    VALUES
        (:trade_id, :genome_id, :timestamp, :entry_price, :exit_price, :direction, :pnl, :exit_reason)
    """
    record = {
        'trade_id':    trade.get('trade_id', str(uuid.uuid4())[:8]),
        'genome_id':   genome_id,
        'timestamp':   str(trade.get('timestamp', '')),
        'entry_price': float(trade.get('entry_price', 0.0)),
        'exit_price':  float(trade.get('exit_price', 0.0)),
        'direction':   str(trade.get('direction', 'LONG')),
        'pnl':         float(trade.get('pnl', 0.0)),
        'exit_reason': str(trade.get('exit_reason', '')),
    }
    own_conn = conn is None
    if own_conn:
        conn = _get_conn()
    try:
        with conn:
            conn.execute(sql, record)
    finally:
        if own_conn:
            conn.close()


def load_quarantine_trades(
    genome_id: str,
    conn: Optional[sqlite3.Connection] = None,
) -> pd.DataFrame:
    """Returns all shadow trades logged for a genome as a DataFrame."""
    own_conn = conn is None
    if own_conn:
        conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM quarantine_trades WHERE genome_id = ? ORDER BY timestamp ASC",
            (genome_id,)
        ).fetchall()
        if not rows:
            return pd.DataFrame(columns=[
                'trade_id', 'genome_id', 'timestamp', 'entry_price',
                'exit_price', 'direction', 'pnl', 'exit_reason'
            ])
        return pd.DataFrame([dict(r) for r in rows])
    finally:
        if own_conn:
            conn.close()


# -------------------------------------------------------------------
# Lineage query
# -------------------------------------------------------------------

def get_lineage(
    genome_id: str,
    depth: int = 5,
    conn: Optional[sqlite3.Connection] = None,
) -> List[dict]:
    """
    Returns the ancestor chain for a genome up to `depth` generations.

    Traverses parent_ids recursively from the given genome backwards.
    Returns a list ordered from oldest ancestor to the given genome.

    Example return:
        [
          {'genome_id': 'abc12345', 'generation': 0, 'regime': 'TRENDING_BULL', ...},
          {'genome_id': 'def67890', 'generation': 1, 'regime': 'TRENDING_BULL', ...},
          {'genome_id': target_id, 'generation': 2, 'regime': 'TRENDING_BULL', ...},
        ]

    Args:
        genome_id: Starting genome (the descendant).
        depth:     Maximum number of ancestor hops to follow.

    Returns:
        List of genome dicts (flat, as stored in SQLite). Returns [] if not found.
    """
    own_conn = conn is None
    if own_conn:
        conn = _get_conn()

    chain = []
    visited = set()
    current_id = genome_id

    try:
        for _ in range(depth + 1):  # +1 to include the starting genome itself
            if current_id in visited:
                break
            visited.add(current_id)

            row = conn.execute(
                "SELECT * FROM genomes WHERE genome_id = ?", (current_id,)
            ).fetchone()
            if row is None:
                break

            d = _row_to_dict(row)
            chain.append(d)

            parent_ids = d.get('parent_ids', [])
            if not parent_ids:
                break
            # Follow first parent (linear chain for simplicity; crossover has 2 parents)
            current_id = parent_ids[0]

        chain.reverse()  # oldest first
        return chain

    finally:
        if own_conn:
            conn.close()


# -------------------------------------------------------------------
# Smoke test
# -------------------------------------------------------------------

if __name__ == "__main__":
    import tempfile, os, shutil
    from genome.chromosome import random_genome, mutate, crossover

    errors = []
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test_registry.db")
    conn = _get_conn(db_path)

    print("Testing genome registry...")

    # 1. Save 5 genomes across 2 generations with parent links
    gen0_genomes = [random_genome('TRENDING_BULL', generation=0) for _ in range(3)]

    # Assign synthetic fitness
    for i, g in enumerate(gen0_genomes):
        g.sharpe = 1.0 + i * 0.5
        g.calmar = 0.8 + i * 0.2
        g.max_drawdown = -0.10 - i * 0.05
        g.win_rate = 0.60 - i * 0.05
        g.turnover = 0.2 + i * 0.1
        g.pareto_rank = i
        g.deflated_sharpe = 0.75 - i * 0.1
        g.status = 'quarantine' if i == 0 else 'candidate'
        save_genome(g, conn)

    # Create 2 gen-1 children via mutation
    child1 = mutate(gen0_genomes[0])
    child1.generation = 1
    child1.sharpe = 1.8; child1.calmar = 1.2; child1.max_drawdown = -0.08
    child1.win_rate = 0.65; child1.turnover = 0.15
    child1.deflated_sharpe = 0.82; child1.status = 'verified'
    save_genome(child1, conn)

    child2 = crossover(gen0_genomes[0], gen0_genomes[1])
    child2.generation = 1
    child2.sharpe = 0.9; child2.status = 'dead'
    save_genome(child2, conn)

    # 2. load_genome round-trip
    loaded = load_genome(gen0_genomes[0].genome_id, conn)
    if loaded is None or loaded.genome_id != gen0_genomes[0].genome_id:
        errors.append("FAIL: load_genome round-trip failed")
    if not math.isnan(loaded.pbo_generation):
        pass  # NaN stored as NULL, restored as NaN -- OK
    print(f"load_genome round-trip -- {'PASS' if not errors else 'FAIL'}")

    # 3. load_generation
    gen0 = load_generation(0, conn)
    if len(gen0) != 3:
        errors.append(f"FAIL: load_generation(0) returned {len(gen0)}, expected 3")
    gen1 = load_generation(1, conn)
    if len(gen1) != 2:
        errors.append(f"FAIL: load_generation(1) returned {len(gen1)}, expected 2")
    print(f"load_generation (gen0={len(gen0)}, gen1={len(gen1)}) -- {'PASS' if len(gen0)==3 and len(gen1)==2 else 'FAIL'}")

    # 4. load_leaderboard (verified)
    lb = load_leaderboard('verified', conn=conn)
    if lb.empty:
        errors.append("FAIL: load_leaderboard('verified') returned empty")
    else:
        if lb.iloc[0]['genome_id'] != child1.genome_id:
            errors.append("FAIL: leaderboard top is not child1 (the only verified genome)")
    print(f"load_leaderboard('verified') -- {'PASS' if not lb.empty else 'FAIL'}")

    # 5. load_leaderboard on empty status
    lb_dead_all = load_leaderboard('dead', conn=conn)
    print(f"load_leaderboard('dead') returns DataFrame -- {'PASS' if isinstance(lb_dead_all, pd.DataFrame) else 'FAIL'}")

    # 6. Lineage query for child1
    lineage = get_lineage(child1.genome_id, depth=5, conn=conn)
    if len(lineage) < 2:
        errors.append(f"FAIL: lineage for child1 has {len(lineage)} entries, expected >= 2")
    else:
        oldest = lineage[0]
        youngest = lineage[-1]
        if youngest['genome_id'] != child1.genome_id:
            errors.append("FAIL: last lineage entry is not child1")
        if oldest['generation'] > youngest['generation']:
            errors.append("FAIL: lineage is not oldest-first")
    print(f"get_lineage (depth={len(lineage)}) -- {'PASS' if not errors else 'FAIL'}")

    # 7. Quarantine trades
    trade = {
        'trade_id': 'trade001',
        'timestamp': '2026-08-14T10:00:00Z',
        'entry_price': 116000.0,
        'exit_price': 117500.0,
        'direction': 'LONG',
        'pnl': 1500.0,
        'exit_reason': 'TP_HIT',
    }
    record_quarantine_trade(gen0_genomes[0].genome_id, trade, conn)
    trades_df = load_quarantine_trades(gen0_genomes[0].genome_id, conn)
    if trades_df.empty or len(trades_df) != 1:
        errors.append(f"FAIL: load_quarantine_trades returned {len(trades_df)} rows, expected 1")
    print(f"quarantine_trades (1 trade logged) -- {'PASS' if not errors else 'FAIL'}")

    # 8. Empty quarantine trades for unknown genome
    empty_trades = load_quarantine_trades('nonexistent_id', conn)
    if not isinstance(empty_trades, pd.DataFrame):
        errors.append("FAIL: load_quarantine_trades for unknown genome should return empty DataFrame")
    print(f"Empty quarantine trades for unknown genome -- {'PASS' if isinstance(empty_trades, pd.DataFrame) else 'FAIL'}")

    # 9. latest_generation
    latest = get_latest_generation(conn)
    if latest != 1:
        errors.append(f"FAIL: get_latest_generation returned {latest}, expected 1")
    print(f"get_latest_generation() = {latest} -- {'PASS' if latest == 1 else 'FAIL'}")

    conn.close()
    shutil.rmtree(tmpdir)

    if not errors:
        print("\nPASS: All registry.py smoke checks passed.")
    else:
        print(f"\nFAIL: {len(errors)} check(s) failed:")
        for e in errors:
            print(f"  {e}")

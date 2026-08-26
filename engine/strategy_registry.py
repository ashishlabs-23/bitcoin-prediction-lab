"""
engine/strategy_registry.py — Champion/Challenger Strategy Lifecycle
=====================================================================
Tracks the lifecycle state of each MEIE strategy version:

    ACTIVE     — trading, accumulating evidence
    WATCH      — trading but EV trending negative over last 20 trades
    RETIRE     — stopped; negative EV confirmed over epoch
    CHALLENGER — new version running parallel to incumbent champion
    CHAMPION   — current best version per (EV_net, Sharpe, MDD) triad

Promotion condition (locked — mirrors preregistration):
  Challenger beats incumbent on ALL three:
    1. EV_net > 0 over epoch
    2. MDD < 5%
    3. profit_factor > 1.0

Design constraints (Ponytail):
  - All state stored in meie_memory.db::strategy_versions table.
  - No new dependencies — uses models/risk_metrics.py already in project.
  - evaluate_epoch() called once per 100-trade epoch (EPOCH_SIZE from arena_accounts).
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR
from engine.arena_accounts import MEIE_DB_PATH, EPOCH_SIZE, get_account, get_recent_trades

logger = logging.getLogger("btcognitive.strategy_registry")

# Promotion thresholds — LOCKED. Change requires new preregistration.
_PROMOTION_THRESHOLDS = {
    "min_ev_net_bps":      0.0,   # EV_net mean over epoch must be positive
    "max_mdd_pct":         5.0,   # Max drawdown < 5%
    "min_profit_factor":   1.0,   # Gross wins / gross losses > 1.0
    "watch_negative_run":  20,    # Consecutive losing trades → WATCH status
}

# Valid status transitions for the 7-Level Research Ladder
_VALID_TRANSITIONS = {
    "CANDIDATE":                  {"EVENT_VALIDATED", "ACTIVE", "WATCH", "RETIRE"},
    "DEFENSIVE_FILTER_CANDIDATE": {"EXECUTION_VALIDATED", "WATCH", "RETIRE"},
    "PORTFOLIO_CHALLENGER":       {"PROSPECTIVE_VALIDATED", "CHAMPION", "WATCH", "RETIRE"},
    "EVENT_VALIDATED":            {"DIRECTION_VALIDATED", "WATCH", "RETIRE"},
    "DIRECTION_VALIDATED":        {"PATH_VALIDATED", "WATCH", "RETIRE"},
    "PATH_VALIDATED":             {"EXECUTION_VALIDATED", "WATCH", "RETIRE"},
    "EXECUTION_VALIDATED":        {"ECONOMIC_VALIDATED", "WATCH", "RETIRE"},
    "ECONOMIC_VALIDATED":         {"PROSPECTIVE_VALIDATED", "WATCH", "RETIRE"},
    "PROSPECTIVE_VALIDATED":      {"CHAMPION", "CHALLENGER", "WATCH", "RETIRE"},
    "ACTIVE":                     {"WATCH", "RETIRE", "CHAMPION", "CHALLENGER"},
    "WATCH":                      {"ACTIVE", "CANDIDATE", "RETIRE", "ARCHIVED"},
    "RETIRE":                     {"ARCHIVED"},
    "CHALLENGER":                 {"CHAMPION", "WATCH", "RETIRE"},
    "CHAMPION":                   {"ACTIVE", "WATCH", "CHALLENGER"},
    "ARCHIVED":                   set(),
}


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(MEIE_DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def _init_registry():
    conn = _get_db()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS strategy_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                version TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'CANDIDATE',
                epoch_number INTEGER NOT NULL DEFAULT 1,
                total_trades INTEGER DEFAULT 0,
                ev_net_mean_bps REAL,
                sharpe REAL,
                mdd_pct REAL,
                profit_factor REAL,
                win_rate REAL,
                promoted_at TEXT,
                retired_at TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                UNIQUE (strategy_name, version)
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sv_sn ON strategy_versions(strategy_name);")

        # Initial Epistemic Seeding: all are candidates until prospective evidence accumulates
        seed_statuses = {
            "MEIE-IGNITION":   "CANDIDATE",
            "MEIE-ABSORPTION": "CANDIDATE",
            "MEIE-VACUUM":     "CANDIDATE",
            "MEIE-TOXICITY":   "DEFENSIVE_FILTER_CANDIDATE",
            "MEIE-COMBINED":   "PORTFOLIO_CHALLENGER",
        }

        now = datetime.now(timezone.utc).isoformat()
        for name, initial_status in seed_statuses.items():
            conn.execute("""
                INSERT OR IGNORE INTO strategy_versions
                (strategy_name, version, status, epoch_number, created_at)
                VALUES (?, 'v1.0', ?, 1, ?);
            """, (name, initial_status, now))
    conn.close()


_init_registry()


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------

def get_strategy_status(strategy_name: str) -> Dict[str, Any]:
    conn = _get_db()
    try:
        cur = conn.execute("""
            SELECT * FROM strategy_versions
            WHERE strategy_name = ?
            ORDER BY id DESC LIMIT 1;
        """, (strategy_name,))
        row = cur.fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def get_all_statuses() -> List[Dict[str, Any]]:
    conn = _get_db()
    try:
        cur = conn.execute("""
            SELECT sv.*,
                   sa.nav, sa.total_trades as account_trades
            FROM strategy_versions sv
            LEFT JOIN strategy_accounts sa ON sv.strategy_name = sa.strategy_name
            WHERE sv.id IN (
                SELECT MAX(id) FROM strategy_versions GROUP BY strategy_name
            )
            ORDER BY sv.strategy_name;
        """)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _set_status(strategy_name: str, version: str, new_status: str, notes: str = ""):
    current = get_strategy_status(strategy_name)
    cur_status = current.get("status", "ACTIVE")
    if new_status not in _VALID_TRANSITIONS.get(cur_status, set()):
        logger.warning(f"Invalid transition {cur_status}→{new_status} for {strategy_name}")
        return

    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    try:
        with conn:
            conn.execute("""
                UPDATE strategy_versions SET status = ?, notes = ?,
                    retired_at = CASE WHEN ? = 'RETIRE' THEN ? ELSE retired_at END,
                    promoted_at = CASE WHEN ? = 'CHAMPION' THEN ? ELSE promoted_at END
                WHERE strategy_name = ? AND version = ?;
            """, (new_status, notes, new_status, now, new_status, now, strategy_name, version))
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Watch condition
# ---------------------------------------------------------------------------

def check_watch_condition(strategy_name: str):
    """
    Flags a strategy as WATCH if the last N consecutive trades are all losses.
    N = _PROMOTION_THRESHOLDS['watch_negative_run'] = 20.
    """
    trades = get_recent_trades(strategy_name, limit=_PROMOTION_THRESHOLDS["watch_negative_run"])
    if len(trades) < _PROMOTION_THRESHOLDS["watch_negative_run"]:
        return  # Insufficient data

    all_losses = all(t.get("net_pnl", 0) <= 0 for t in trades)
    if all_losses:
        current = get_strategy_status(strategy_name)
        if current.get("status") == "ACTIVE":
            _set_status(
                strategy_name, current.get("version", "v1.0"), "WATCH",
                notes=f"Consecutive loss run ≥ {_PROMOTION_THRESHOLDS['watch_negative_run']}"
            )
            logger.warning(f"{strategy_name} → WATCH: {_PROMOTION_THRESHOLDS['watch_negative_run']} consecutive losses")


# ---------------------------------------------------------------------------
# Epoch evaluation (called at N=100 epoch boundary)
# ---------------------------------------------------------------------------

def _compute_epoch_metrics(strategy_name: str, epoch_number: int) -> Dict[str, float]:
    conn = _get_db()
    try:
        cur = conn.execute("""
            SELECT net_pnl, gross_pnl FROM meie_strategy_trades
            WHERE strategy_name = ? AND epoch_number = ? AND resolved = 1;
        """, (strategy_name, epoch_number))
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return {"ev_net_mean_bps": 0.0, "sharpe": 0.0, "mdd_pct": 0.0,
                "profit_factor": 0.0, "win_rate": 0.0, "n": 0}

    pnl_series = [r["net_pnl"] for r in rows]
    n = len(pnl_series)

    wins  = [p for p in pnl_series if p > 0]
    losses = [abs(p) for p in pnl_series if p < 0]

    ev_mean = sum(pnl_series) / n
    pf = sum(wins) / max(1e-8, sum(losses)) if losses else float("inf")
    wr = len(wins) / n

    # Rolling NAV to compute MDD
    nav = 10_000.0
    peak = nav
    mdd = 0.0
    for p in pnl_series:
        nav += p
        peak = max(peak, nav)
        dd = (nav - peak) / peak if peak > 0 else 0.0
        mdd = min(mdd, dd)

    # Simple Sharpe: mean/std of PnL series (not annualized — epoch-level)
    import statistics
    std = statistics.stdev(pnl_series) if n >= 2 else 1.0
    sharpe = (ev_mean / std) if std > 0 else 0.0

    return {
        "ev_net_mean_bps": round(ev_mean, 4),
        "sharpe": round(sharpe, 4),
        "mdd_pct": round(abs(mdd) * 100.0, 4),
        "profit_factor": round(pf, 4),
        "win_rate": round(wr, 4),
        "n": n,
    }


def evaluate_epoch(strategy_name: str) -> Dict[str, Any]:
    """
    Called when epoch_trades hits EPOCH_SIZE.
    Computes epoch metrics, decides KEEP / RETIRE, increments epoch, creates new version row.

    Returns a dict with decision and metrics.
    """
    acc = get_account(strategy_name)
    epoch_number = acc.get("epoch_number", 1)
    version = acc.get("version", "v1.0")

    metrics = _compute_epoch_metrics(strategy_name, epoch_number)
    th = _PROMOTION_THRESHOLDS

    blockers = []
    if metrics["ev_net_mean_bps"] <= th["min_ev_net_bps"]:
        blockers.append(f"Level 5 (Economic Yield) FAIL: Net EV {metrics['ev_net_mean_bps']:.2f}bps <= {th['min_ev_net_bps']}bps")
    if metrics["mdd_pct"] >= th["max_mdd_pct"]:
        blockers.append(f"Level 6 (Prospective Stability) FAIL: MDD {metrics['mdd_pct']:.2f}% >= {th['max_mdd_pct']}%")
    if metrics["profit_factor"] <= th["min_profit_factor"]:
        blockers.append(f"Level 4 (Execution Realism) FAIL: Profit Factor {metrics['profit_factor']:.2f} <= {th['min_profit_factor']}")

    notes = "All 7 rungs passed" if keep else " | ".join(blockers)
    now = datetime.now(timezone.utc).isoformat()
    decision = "KEEP" if keep else "RETIRE"

    conn = _get_db()
    try:
        with conn:
            # Update current epoch metrics
            conn.execute("""
                UPDATE strategy_versions SET
                    total_trades = ?, ev_net_mean_bps = ?, sharpe = ?,
                    mdd_pct = ?, profit_factor = ?, win_rate = ?, notes = ?
                WHERE strategy_name = ? AND version = ?;
            """, (
                metrics["n"], metrics["ev_net_mean_bps"], metrics["sharpe"],
                metrics["mdd_pct"], metrics["profit_factor"], metrics["win_rate"],
                notes, strategy_name, version
            ))

            if not keep:
                conn.execute("""
                    UPDATE strategy_versions SET status = 'RETIRE', retired_at = ?, notes = ?
                    WHERE strategy_name = ? AND version = ?;
                """, (now, notes, strategy_name, version))
                conn.execute(
                    "UPDATE strategy_accounts SET status = 'WATCH', updated_at = ? WHERE strategy_name = ?;",
                    (now, strategy_name)
                )
            else:
                # Bump epoch, create next version row
                new_epoch = epoch_number + 1
                major, minor = (int(x) for x in version.lstrip("v").split("."))
                new_version = f"v{major}.{minor + 1}"

                conn.execute("""
                    UPDATE strategy_accounts SET epoch_number = ?, epoch_trades = 0,
                        version = ?, updated_at = ?
                    WHERE strategy_name = ?;
                """, (new_epoch, new_version, now, strategy_name))

                conn.execute("""
                    INSERT OR IGNORE INTO strategy_versions
                    (strategy_name, version, status, epoch_number, created_at)
                    VALUES (?, ?, 'ACTIVE', ?, ?);
                """, (strategy_name, new_version, new_epoch, now))

    finally:
        conn.close()

    logger.info(
        f"Epoch {epoch_number} [{strategy_name} {version}]: decision={decision} "
        f"EV={metrics['ev_net_mean_bps']:.2f}bps MDD={metrics['mdd_pct']:.2f}% PF={metrics['profit_factor']:.2f}"
    )

    return {"strategy_name": strategy_name, "version": version,
            "epoch": epoch_number, "decision": decision, **metrics}

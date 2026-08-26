"""
engine/risk_budget.py — Per-Strategy Daily Risk Budget Enforcer
===============================================================
Implements the risk-budget framework described in the user's architecture:

    Daily risk budget  = 0.50% of per-account NAV
    Max single-trade   = 0.20% of account NAV
    Daily drawdown stop = 0.75% → halt rest of UTC day
    Max concurrent positions = 2 per account

Design constraints (Ponytail):
  - State stored in meie_memory.db::meie_daily_risk (resets at UTC midnight).
  - can_trade() returns (bool, reason) — never throws.
  - position_size_usd() returns the computed size in USD for risk-budget compliance.
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime, timezone, date
from typing import Tuple, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR

logger = logging.getLogger("btcognitive.risk_budget")

MEIE_DB_PATH = os.path.join(RESULTS_DIR, "meie_memory.db")

# Locked parameters (per implementation plan)
DAILY_RISK_BUDGET_PCT    = 0.0050   # 0.50% of account NAV
MAX_SINGLE_TRADE_LOSS    = 0.0020   # 0.20% of account NAV
DAILY_DRAWDOWN_STOP      = 0.0075   # 0.75% daily drawdown → halt
MAX_CONCURRENT_POSITIONS = 2        # per account


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(MEIE_DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def _init_risk_tables():
    conn = _get_db()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meie_daily_risk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                utc_date TEXT NOT NULL,
                risk_spent_usd REAL DEFAULT 0.0,
                daily_loss_usd REAL DEFAULT 0.0,
                halted INTEGER DEFAULT 0,
                UNIQUE (strategy_name, utc_date)
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mdr_snd ON meie_daily_risk(strategy_name, utc_date);")
    conn.close()


_init_risk_tables()


def _today_utc() -> str:
    return date.today().isoformat()


def _get_or_create_daily_record(strategy_name: str) -> Dict[str, Any]:
    today = _today_utc()
    conn = _get_db()
    try:
        with conn:
            conn.execute("""
                INSERT OR IGNORE INTO meie_daily_risk
                (strategy_name, utc_date, risk_spent_usd, daily_loss_usd, halted)
                VALUES (?, ?, 0.0, 0.0, 0);
            """, (strategy_name, today))
        cur = conn.execute(
            "SELECT * FROM meie_daily_risk WHERE strategy_name = ? AND utc_date = ?;",
            (strategy_name, today)
        )
        return dict(cur.fetchone())
    finally:
        conn.close()


def compute_position_size(account_nav: float, stop_distance_pct: float) -> float:
    """
    Computes position size in USD such that a full SL hit costs at most MAX_SINGLE_TRADE_LOSS of NAV.

    Args:
        account_nav:       Current virtual NAV of the strategy account.
        stop_distance_pct: Fractional distance from entry to SL (e.g., 0.015 = 1.5%).

    Returns:
        Position size in USD (may be small when stop is wide).
    """
    max_loss_usd     = account_nav * MAX_SINGLE_TRADE_LOSS
    stop_dist        = max(0.001, stop_distance_pct)
    size_usd         = max_loss_usd / stop_dist
    return round(size_usd, 2)


def can_trade(
    strategy_name: str,
    account_nav: float,
    proposed_size_usd: float,
    current_open_positions: int,
    c2_risk_multiplier: float = 1.0,
) -> Tuple[bool, str]:
    """
    Returns (True, "") if the account is allowed to open a trade,
    or (False, reason) if blocked by any risk rule.

    Args:
        strategy_name:         Name of the strategy account.
        account_nav:           Current NAV of the account.
        proposed_size_usd:     Position size the payoff engine wants to open.
        current_open_positions: Number of currently open positions for this account.
        c2_risk_multiplier:    Risk multiplier from C2/Observatory (0.0 to 1.0).
    """
    try:
        # Rule 0: C2 Macro Risk Gate
        if c2_risk_multiplier <= 0.0:
            return False, "C2 Risk Gate: High uncertainty / degraded calibration -> mandatory ABSTAIN"

        # Rule 1: Max concurrent positions
        if current_open_positions >= MAX_CONCURRENT_POSITIONS:
            return False, f"Max concurrent positions reached ({current_open_positions}/{MAX_CONCURRENT_POSITIONS})"

        # Rule 2: Check daily risk record
        rec = _get_or_create_daily_record(strategy_name)

        # Rule 3: Already halted today
        if rec.get("halted", 0):
            return False, f"Account halted for UTC day {rec['utc_date']} (daily drawdown stop hit)"

        # Rule 4: Daily drawdown stop
        daily_loss = rec.get("daily_loss_usd", 0.0)
        if daily_loss > 0 and account_nav > 0:
            daily_loss_pct = daily_loss / account_nav
            if daily_loss_pct >= DAILY_DRAWDOWN_STOP:
                _halt_account(strategy_name, rec["utc_date"])
                return False, f"Daily drawdown stop: {daily_loss_pct*100:.2f}% ≥ {DAILY_DRAWDOWN_STOP*100:.2f}%"

        # Rule 5: Daily risk budget (scaled by C2 risk multiplier)
        risk_spent = rec.get("risk_spent_usd", 0.0)
        daily_budget = account_nav * DAILY_RISK_BUDGET_PCT * c2_risk_multiplier
        if risk_spent + proposed_size_usd * MAX_SINGLE_TRADE_LOSS > daily_budget:
            return False, (
                f"Daily risk budget exhausted: spent={risk_spent:.2f} "
                f"budget={daily_budget:.2f} (C2 scale={c2_risk_multiplier:.1f})"
            )

        # Rule 6: Single trade max size
        max_size = account_nav * MAX_SINGLE_TRADE_LOSS / max(0.001, proposed_size_usd / account_nav)
        if proposed_size_usd > account_nav * 0.10:  # Hard cap: no single trade > 10% NAV
            return False, f"Position size {proposed_size_usd:.0f} > 10% of NAV {account_nav:.0f}"

        return True, ""

    except Exception as e:
        logger.warning(f"can_trade [{strategy_name}] exception: {e}")
        return False, f"Risk check error: {e}"


def record_trade_opened(strategy_name: str, position_size_usd: float):
    """Records that a trade was opened, consuming part of the daily risk budget."""
    today = _today_utc()
    risk_increment = position_size_usd * MAX_SINGLE_TRADE_LOSS
    conn = _get_db()
    try:
        with conn:
            conn.execute("""
                UPDATE meie_daily_risk
                SET risk_spent_usd = risk_spent_usd + ?
                WHERE strategy_name = ? AND utc_date = ?;
            """, (risk_increment, strategy_name, today))
    finally:
        conn.close()


def record_trade_closed(strategy_name: str, net_pnl: float):
    """Updates daily P&L tracker after a trade closes."""
    today = _today_utc()
    loss = max(0.0, -net_pnl)  # Only record losses for drawdown tracking
    conn = _get_db()
    try:
        with conn:
            conn.execute("""
                UPDATE meie_daily_risk
                SET daily_loss_usd = daily_loss_usd + ?
                WHERE strategy_name = ? AND utc_date = ?;
            """, (loss, strategy_name, today))
    finally:
        conn.close()


def _halt_account(strategy_name: str, utc_date: str):
    conn = _get_db()
    try:
        with conn:
            conn.execute("""
                UPDATE meie_daily_risk SET halted = 1
                WHERE strategy_name = ? AND utc_date = ?;
            """, (strategy_name, utc_date))
    finally:
        conn.close()
    logger.warning(f"[{strategy_name}] HALTED for {utc_date} — daily drawdown stop triggered")


def get_daily_summary(strategy_name: str) -> Dict[str, Any]:
    """Returns today's risk budget state for a strategy."""
    rec = _get_or_create_daily_record(strategy_name)
    return {
        "strategy_name": strategy_name,
        "utc_date": rec["utc_date"],
        "risk_spent_usd": rec["risk_spent_usd"],
        "daily_loss_usd": rec["daily_loss_usd"],
        "halted": bool(rec["halted"]),
        "daily_budget_pct": DAILY_RISK_BUDGET_PCT * 100.0,
        "daily_drawdown_stop_pct": DAILY_DRAWDOWN_STOP * 100.0,
        "max_concurrent": MAX_CONCURRENT_POSITIONS,
    }

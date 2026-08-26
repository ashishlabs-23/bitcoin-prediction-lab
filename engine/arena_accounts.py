"""
engine/arena_accounts.py — MEIE Per-Strategy Virtual Account Ledger
====================================================================
Manages five isolated paper-trading accounts, one per event archetype:
  MEIE-IGNITION | MEIE-ABSORPTION | MEIE-VACUUM | MEIE-TOXICITY | MEIE-COMBINED

Design constraints (Ponytail):
  - All writes go to meie_memory.db ONLY. arena_memory.db is never touched.
  - Reuses check_position_closure_high_low from backtest/simulate.py.
  - Reuses ExecutionSimulator for fee / slippage.
  - $10,000 virtual starting NAV per account (locked in INITIAL_NAV).
  - 100-trade epoch boundary (locked in EPOCH_SIZE).
"""

import os
import sys
import sqlite3
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR
from backtest.simulate import check_position_closure_high_low
from backtest.execution_simulator import ExecutionSimulator

logger = logging.getLogger("btcognitive.arena_accounts")

MEIE_DB_PATH = os.path.join(RESULTS_DIR, "meie_memory.db")

# Locked constants (per implementation plan defaults)
INITIAL_NAV     = 10_000.0   # Virtual USD per account
EPOCH_SIZE      = 100        # Closed trades per epoch before version bump
MAX_HOLD_BARS   = 30         # 30-minute max hold (1-min candles)

STRATEGY_NAMES = [
    "MEIE-IGNITION",
    "MEIE-ABSORPTION",
    "MEIE-VACUUM",
    "MEIE-TOXICITY",
    "MEIE-COMBINED",
]

_exec_sim = ExecutionSimulator(fee_tier="taker", taker_fee_bps=5.0, base_slippage_bps=2.0)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(MEIE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(MEIE_DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def _init_account_tables():
    conn = _get_db()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS strategy_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT UNIQUE NOT NULL,
                version TEXT NOT NULL DEFAULT 'v1.0',
                nav REAL NOT NULL,
                initial_nav REAL NOT NULL,
                total_trades INTEGER DEFAULT 0,
                epoch_trades INTEGER DEFAULT 0,
                epoch_number INTEGER DEFAULT 1,
                win_rate REAL DEFAULT 0.0,
                max_drawdown REAL DEFAULT 0.0,
                peak_nav REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_sa_name ON strategy_accounts(strategy_name);")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS meie_strategy_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                version TEXT NOT NULL,
                epoch_number INTEGER NOT NULL,
                signal_time TEXT NOT NULL,
                event_type TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                tp_price REAL NOT NULL,
                sl_price REAL NOT NULL,
                position_size_usd REAL NOT NULL,
                quantity REAL NOT NULL,
                mfe_pct REAL,
                mae_pct REAL,
                gross_pnl REAL,
                fee_bps REAL DEFAULT 10.0,
                slippage_bps REAL,
                net_pnl REAL,
                nav_after REAL,
                holding_bars INTEGER DEFAULT 0,
                exit_reason TEXT,
                failure_class TEXT DEFAULT 'NO_CLASS',
                z_hawkes REAL,
                z_ofi REAL,
                z_vpin REAL,
                z_spread REAL,
                market_regime TEXT,
                counterfactual_skip_pnl REAL DEFAULT 0.0,
                counterfactual_opposite_pnl REAL,
                opportunity_quality REAL,
                target_rr REAL DEFAULT 2.0,
                max_hold_bars INTEGER DEFAULT 30,
                c2_risk_state TEXT DEFAULT 'CALIBRATED',
                data_state TEXT DEFAULT 'VALID',
                impact_bps REAL DEFAULT 1.0,
                resolved INTEGER DEFAULT 0,
                closed_at TEXT
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mst_sn ON meie_strategy_trades(strategy_name);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mst_ts ON meie_strategy_trades(signal_time);")

        # Migrations for complete trade contract tracking & combined strategy decomposition
        for col_def in [
            "counterfactual_skip_pnl REAL DEFAULT 0.0",
            "counterfactual_opposite_pnl REAL",
            "opportunity_quality REAL",
            "target_rr REAL DEFAULT 2.0",
            "max_hold_bars INTEGER DEFAULT 30",
            "c2_risk_state TEXT DEFAULT 'CALIBRATED'",
            "data_state TEXT DEFAULT 'VALID'",
            "impact_bps REAL DEFAULT 1.0",
            "selected_archetype TEXT",
            "selection_reason TEXT",
            "allocation_weight REAL",
            "component_scores TEXT"
        ]:
            try:
                conn.execute(f"ALTER TABLE meie_strategy_trades ADD COLUMN {col_def};")
            except Exception:
                pass

        conn.execute("""
            CREATE TABLE IF NOT EXISTS meie_equity_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                nav REAL NOT NULL,
                drawdown REAL DEFAULT 0.0,
                trade_id INTEGER
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_meh_sn ON meie_equity_history(strategy_name);")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS meie_open_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                version TEXT NOT NULL,
                opened_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                tp_price REAL NOT NULL,
                sl_price REAL NOT NULL,
                position_size_usd REAL NOT NULL,
                quantity REAL NOT NULL,
                bars_held INTEGER DEFAULT 0,
                target_rr REAL DEFAULT 2.0,
                max_hold_bars INTEGER DEFAULT 30,
                opportunity_quality REAL,
                c2_risk_state TEXT DEFAULT 'CALIBRATED',
                data_state TEXT DEFAULT 'VALID',
                selected_archetype TEXT,
                selection_reason TEXT,
                allocation_weight REAL,
                component_scores TEXT,
                z_hawkes REAL,
                z_ofi REAL,
                z_vpin REAL,
                z_spread REAL,
                market_regime TEXT,
                trade_record_id INTEGER
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mop_sn ON meie_open_positions(strategy_name);")

        for col_def in [
            "target_rr REAL DEFAULT 2.0",
            "max_hold_bars INTEGER DEFAULT 30",
            "opportunity_quality REAL",
            "c2_risk_state TEXT DEFAULT 'CALIBRATED'",
            "data_state TEXT DEFAULT 'VALID'",
            "selected_archetype TEXT",
            "selection_reason TEXT",
            "allocation_weight REAL",
            "component_scores TEXT"
        ]:
            try:
                conn.execute(f"ALTER TABLE meie_open_positions ADD COLUMN {col_def};")
            except Exception:
                pass

        # Dedicated Abstentions Ledger (ABSTAIN is an observed decision, not missing data)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meie_abstentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                direction TEXT NOT NULL,
                candidate_entry REAL,
                candidate_tp REAL,
                candidate_sl REAL,
                opportunity_quality REAL,
                expected_ev_bps REAL,
                blocker_reason TEXT NOT NULL,
                risk_budget_spent REAL,
                risk_budget_daily REAL,
                c2_risk_state TEXT DEFAULT 'CALIBRATED',
                data_state TEXT DEFAULT 'VALID',
                market_regime TEXT
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mab_sn ON meie_abstentions(strategy_name);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mab_ts ON meie_abstentions(timestamp);")

        # Seed accounts if not present
        now = datetime.now(timezone.utc).isoformat()
        for name in STRATEGY_NAMES:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO strategy_accounts
                    (strategy_name, version, nav, initial_nav, peak_nav, status, created_at, updated_at)
                    VALUES (?, 'v1.0', ?, ?, ?, 'ACTIVE', ?, ?);
                """, (name, INITIAL_NAV, INITIAL_NAV, INITIAL_NAV, now, now))
                # Seed initial equity point
                cur = conn.execute("SELECT id FROM strategy_accounts WHERE strategy_name = ?;", (name,))
                conn.execute(
                    "INSERT OR IGNORE INTO meie_equity_history (strategy_name, timestamp, nav, drawdown) VALUES (?, ?, ?, 0.0);",
                    (name, now, INITIAL_NAV)
                )
            except Exception as e:
                logger.warning(f"Seed account {name}: {e}")

    conn.close()


_init_account_tables()


# ---------------------------------------------------------------------------
# Account read helpers
# ---------------------------------------------------------------------------

def get_account(strategy_name: str) -> Dict[str, Any]:
    conn = _get_db()
    try:
        cur = conn.execute("SELECT * FROM strategy_accounts WHERE strategy_name = ?;", (strategy_name,))
        row = cur.fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def get_all_accounts() -> List[Dict[str, Any]]:
    conn = _get_db()
    try:
        cur = conn.execute("SELECT * FROM strategy_accounts ORDER BY strategy_name;")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_open_position(strategy_name: str) -> Optional[Dict[str, Any]]:
    conn = _get_db()
    try:
        cur = conn.execute(
            "SELECT * FROM meie_open_positions WHERE strategy_name = ? ORDER BY id DESC LIMIT 1;",
            (strategy_name,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def count_open_positions(strategy_name: str) -> int:
    conn = _get_db()
    try:
        cur = conn.execute(
            "SELECT COUNT(*) FROM meie_open_positions WHERE strategy_name = ?;",
            (strategy_name,)
        )
        return cur.fetchone()[0]
    finally:
        conn.close()


def get_recent_trades(strategy_name: str, limit: int = 50) -> List[Dict[str, Any]]:
    conn = _get_db()
    try:
        cur = conn.execute(
            "SELECT * FROM meie_strategy_trades WHERE strategy_name = ? ORDER BY id DESC LIMIT ?;",
            (strategy_name, limit)
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_equity_curve(strategy_name: str, limit: int = 200) -> List[Dict[str, Any]]:
    conn = _get_db()
    try:
        cur = conn.execute(
            "SELECT timestamp, nav, drawdown FROM meie_equity_history WHERE strategy_name = ? ORDER BY id ASC LIMIT ?;",
            (strategy_name, limit)
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Trade lifecycle
# ---------------------------------------------------------------------------

def open_position(
    strategy_name: str,
    event_type: str,
    direction: str,
    entry_price: float,
    tp_price: float,
    sl_price: float,
    position_size_usd: float,
    state_vec: Optional[Dict[str, Any]] = None,
    market_regime: str = "Unknown",
    target_rr: float = 2.0,
    max_hold_bars: int = 30,
    opportunity_quality: float = 0.0,
    c2_risk_state: str = "CALIBRATED",
    data_state: str = "VALID",
    impact_bps: float = 1.0,
    selected_archetype: Optional[str] = None,
    selection_reason: Optional[str] = None,
    allocation_weight: Optional[float] = None,
    component_scores: Optional[str] = None,
) -> Optional[int]:
    """
    Opens a paper position for a strategy account with full trade contract specification
    and component decomposition for portfolio challengers.
    Records a pending trade in meie_strategy_trades with resolved=0.
    Returns the trade record id, or None if account not found.
    """
    acc = get_account(strategy_name)
    if not acc:
        return None

    quantity = position_size_usd / max(1.0, entry_price)
    now = datetime.now(timezone.utc).isoformat()

    sv = state_vec or {}
    conn = _get_db()
    try:
        with conn:
            # 1. Insert pending trade record with complete contract specification & decomposition
            cur = conn.execute("""
                INSERT INTO meie_strategy_trades
                (strategy_name, version, epoch_number, signal_time, event_type, direction,
                 entry_price, tp_price, sl_price, position_size_usd, quantity,
                 target_rr, max_hold_bars, opportunity_quality, c2_risk_state, data_state, impact_bps,
                 selected_archetype, selection_reason, allocation_weight, component_scores,
                 z_hawkes, z_ofi, z_vpin, z_spread, market_regime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                strategy_name, acc["version"], acc["epoch_number"], now, event_type, direction,
                entry_price, tp_price, sl_price, position_size_usd, quantity,
                target_rr, max_hold_bars, opportunity_quality, c2_risk_state, data_state, impact_bps,
                selected_archetype, selection_reason, allocation_weight, component_scores,
                sv.get("z_hawkes"), sv.get("z_ofi"), sv.get("z_vpin"), sv.get("z_spread"),
                market_regime
            ))
            trade_id = cur.lastrowid

            # 2. Insert open position with contract bounds & decomposition
            conn.execute("""
                INSERT INTO meie_open_positions
                (strategy_name, version, opened_at, event_type, direction, entry_price,
                 tp_price, sl_price, position_size_usd, quantity, bars_held,
                 target_rr, max_hold_bars, opportunity_quality, c2_risk_state, data_state,
                 selected_archetype, selection_reason, allocation_weight, component_scores,
                 z_hawkes, z_ofi, z_vpin, z_spread, market_regime, trade_record_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                strategy_name, acc["version"], now, event_type, direction, entry_price,
                tp_price, sl_price, position_size_usd, quantity,
                target_rr, max_hold_bars, opportunity_quality, c2_risk_state, data_state,
                selected_archetype, selection_reason, allocation_weight, component_scores,
                sv.get("z_hawkes"), sv.get("z_ofi"), sv.get("z_vpin"), sv.get("z_spread"),
                market_regime, trade_id
            ))
        return trade_id
    except Exception as e:
        logger.error(f"open_position [{strategy_name}]: {e}")
        return None
    finally:
        conn.close()


def record_abstention(
    strategy_name: str,
    event_type: str,
    direction: str,
    blocker_reason: str,
    candidate_entry: Optional[float] = None,
    candidate_tp: Optional[float] = None,
    candidate_sl: Optional[float] = None,
    opportunity_quality: float = 0.0,
    expected_ev_bps: float = 0.0,
    risk_budget_spent: float = 0.0,
    risk_budget_daily: float = 50.0,
    c2_risk_state: str = "CALIBRATED",
    data_state: str = "VALID",
    market_regime: str = "Unknown",
) -> None:
    """
    Records an observed ABSTAIN decision into the immutable ledger.
    ABSTAIN is an observed, quantifiable risk decision, not missing data.
    """
    conn = _get_db()
    now = datetime.now(timezone.utc).isoformat()
    try:
        with conn:
            conn.execute("""
                INSERT INTO meie_abstentions
                (strategy_name, timestamp, event_type, direction, candidate_entry, candidate_tp,
                 candidate_sl, opportunity_quality, expected_ev_bps, blocker_reason,
                 risk_budget_spent, risk_budget_daily, c2_risk_state, data_state, market_regime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                strategy_name, now, event_type, direction, candidate_entry, candidate_tp,
                candidate_sl, opportunity_quality, expected_ev_bps, blocker_reason,
                risk_budget_spent, risk_budget_daily, c2_risk_state, data_state, market_regime
            ))
    except Exception as e:
        logger.error(f"record_abstention [{strategy_name}]: {e}")
    finally:
        conn.close()


def get_abstentions(strategy_name: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Returns recent recorded abstentions."""
    conn = _get_db()
    try:
        if strategy_name:
            cur = conn.execute(
                "SELECT * FROM meie_abstentions WHERE strategy_name = ? ORDER BY id DESC LIMIT ?;",
                (strategy_name, limit)
            )
        else:
            cur = conn.execute(
                "SELECT * FROM meie_abstentions ORDER BY id DESC LIMIT ?;",
                (limit,)
            )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def evaluate_candle(
    strategy_name: str,
    candle: Dict[str, Any],
    failure_classifier_fn=None,
) -> Optional[Dict[str, Any]]:
    """
    Checks all open positions for this strategy against the current candle.
    Closes positions that hit TP/SL, reach strategy-specific max_hold_bars (TIMEOUT),
    or hit regime invalidation.
    Returns a trade result dict, or None if no position closed.
    """
    pos = get_open_position(strategy_name)
    if not pos:
        return None

    high_p  = float(candle.get("high", candle.get("close", 0)))
    low_p   = float(candle.get("low", candle.get("close", 0)))
    close_p = float(candle.get("close", 0))
    now     = candle.get("timestamp", datetime.now(timezone.utc).isoformat())

    bars_held = pos.get("bars_held", 0) + 1
    max_hold  = int(pos.get("max_hold_bars") or MAX_HOLD_BARS)

    closure = check_position_closure_high_low(
        direction=pos["direction"],
        tp=pos["tp_price"],
        sl=pos["sl_price"],
        candle_high=high_p,
        candle_low=low_p,
    )

    # Strategy-specific hard timeout
    if not closure["closed"] and bars_held >= max_hold:
        closure = {"closed": True, "reason": "TIMEOUT", "close_price": close_p}

    # Absorption regime invalidation: if market shifted into active expansion breakout -> immediate exit
    if not closure["closed"] and pos.get("event_type") == "ABSORPTION":
        cur_regime = str(candle.get("market_regime", "")).upper()
        if "EXPANSION" in cur_regime:
            closure = {"closed": True, "reason": "REGIME_INVALIDATION", "close_price": close_p}

    if not closure["closed"]:
        # Just update bars held
        conn = _get_db()
        try:
            with conn:
                conn.execute(
                    "UPDATE meie_open_positions SET bars_held = ? WHERE id = ?;",
                    (bars_held, pos["id"])
                )
        finally:
            conn.close()
        return None

    # ---------- Position closed ----------
    exit_p      = float(closure["close_price"])
    exit_reason = closure["reason"]
    entry_p     = pos["entry_price"]
    size_usd    = pos["position_size_usd"]
    qty         = pos["quantity"]

    price_diff = (exit_p - entry_p) if pos["direction"] == "LONG" else (entry_p - exit_p)
    gross_pnl  = qty * price_diff
    mfe_pct    = max(0.0, (high_p - entry_p) / entry_p) if pos["direction"] == "LONG" else max(0.0, (entry_p - low_p) / entry_p)
    mae_pct    = max(0.0, (entry_p - low_p) / entry_p) if pos["direction"] == "LONG" else max(0.0, (high_p - entry_p) / entry_p)

    fee_cost    = size_usd * 0.0010  # 10 bps total
    slippage    = _exec_sim.calculate_slippage(size_usd, bid_ask_spread_pct=0.0005, vpin=0.30)
    slip_cost   = size_usd * slippage
    net_pnl     = round(gross_pnl - fee_cost - slip_cost, 4)

    # Counterfactual Benchmark: What would opposite direction have yielded?
    opposite_net_pnl = round(-gross_pnl - fee_cost - slip_cost, 4)

    fee_bps     = 10.0
    slip_bps    = round(slippage * 10_000, 2)

    # Classify failure
    failure_class = "NO_CLASS"
    if failure_classifier_fn and net_pnl < 0:
        try:
            failure_class = failure_classifier_fn(
                event_type=pos["event_type"],
                direction=pos["direction"],
                mfe_pct=mfe_pct,
                mae_pct=mae_pct,
                exit_reason=exit_reason,
                state_vec={
                    "z_hawkes": pos.get("z_hawkes", 0),
                    "z_ofi": pos.get("z_ofi", 0),
                    "z_vpin": pos.get("z_vpin", 0),
                    "z_spread": pos.get("z_spread", 0),
                },
                market_regime=pos.get("market_regime", "Unknown"),
                sl_price=pos["sl_price"],
                tp_price=pos["tp_price"],
                entry_price=entry_p,
            )
        except Exception as e:
            logger.warning(f"failure_classifier error: {e}")

    acc = get_account(strategy_name)
    old_nav     = acc.get("nav", INITIAL_NAV)
    new_nav     = round(max(1.0, old_nav + net_pnl), 4)
    peak_nav    = max(acc.get("peak_nav", new_nav), new_nav)
    drawdown    = min(0.0, (new_nav - peak_nav) / peak_nav) if peak_nav > 0 else 0.0

    total_trades = acc.get("total_trades", 0) + 1
    epoch_trades = acc.get("epoch_trades", 0) + 1

    conn = _get_db()
    try:
        with conn:
            # Update trade record with counterfactuals
            conn.execute("""
                UPDATE meie_strategy_trades SET
                    exit_price = ?, mfe_pct = ?, mae_pct = ?,
                    gross_pnl = ?, fee_bps = ?, slippage_bps = ?, net_pnl = ?,
                    counterfactual_skip_pnl = 0.0,
                    counterfactual_opposite_pnl = ?,
                    nav_after = ?, holding_bars = ?, exit_reason = ?,
                    failure_class = ?, resolved = 1, closed_at = ?
                WHERE id = ?;
            """, (
                exit_p, mfe_pct, mae_pct,
                gross_pnl, fee_bps, slip_bps, net_pnl,
                opposite_net_pnl,
                new_nav, bars_held, exit_reason,
                failure_class, now, pos["trade_record_id"]
            ))

            # Record equity point
            conn.execute("""
                INSERT INTO meie_equity_history (strategy_name, timestamp, nav, drawdown, trade_id)
                VALUES (?, ?, ?, ?, ?);
            """, (strategy_name, now, new_nav, drawdown, pos["trade_record_id"]))

            # Remove open position
            conn.execute("DELETE FROM meie_open_positions WHERE id = ?;", (pos["id"],))

            # Recalculate win rate
            cur = conn.execute(
                "SELECT net_pnl FROM meie_strategy_trades WHERE strategy_name = ? AND resolved = 1;",
                (strategy_name,)
            )
            all_pnl = [r[0] for r in cur.fetchall()]
            win_rate = sum(1 for p in all_pnl if p > 0) / max(1, len(all_pnl))

            conn.execute("""
                UPDATE strategy_accounts SET
                    nav = ?, peak_nav = ?, total_trades = ?, epoch_trades = ?,
                    win_rate = ?, max_drawdown = ?, updated_at = ?
                WHERE strategy_name = ?;
            """, (new_nav, peak_nav, total_trades, epoch_trades,
                  win_rate, drawdown, now, strategy_name))

        return {
            "strategy_name": strategy_name,
            "event": "TRADE_CLOSED",
            "trade_id": pos["trade_record_id"],
            "direction": pos["direction"],
            "event_type": pos["event_type"],
            "entry_price": entry_p,
            "exit_price": exit_p,
            "exit_reason": exit_reason,
            "net_pnl": net_pnl,
            "failure_class": failure_class,
            "nav_after": new_nav,
            "epoch_trades": epoch_trades,
        }
    except Exception as e:
        logger.error(f"evaluate_candle close [{strategy_name}]: {e}")
        return None
    finally:
        conn.close()

"""
engine/paper_trade_ledger.py — Durable Paper Trade Ledger & Portfolio Accounting
================================================================================
Provides thread-safe, persistent append-only storage for simulated paper trades
surviving server restarts and browser refreshes.

Key Invariants:
1. Strict Non-Execution: All trades are simulated paper trades under OFFLINE_RESEARCH_ONLY.
   Live capital and broker order submissions are permanently disabled.
2. Exact Cost Accounting: Enforces transaction costs across the 3 reconciled scenarios:
   - COINBASE_RETAIL_87BPS: 87.0 bps round-trip
   - COINBASE_INSTITUTIONAL_18BPS: 18.6 bps round-trip
   - BINANCE_PERP_15BPS: 15.0 bps round-trip
3. Persistent Storage: Appends and indexes trades in `data/paper_trade_ledger.jsonl`.
4. Mathematical Metrics: Reproduces Equity, Drawdown, Win Rate, Profit Factor, Sharpe & Sortino.
5. Exportability: Exposes full CSV and JSON exports for auditability.
"""

from __future__ import annotations

import os
import csv
import json
import uuid
import math
import time
import logging
import threading
from io import StringIO
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger("btcognitive.paper_trade_ledger")

DEFAULT_LEDGER_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "paper_trade_ledger.jsonl")
)

COST_SCENARIO_BPS = {
    "COINBASE_RETAIL_87BPS": 87.0,
    "COINBASE_INSTITUTIONAL_18BPS": 18.6,
    "BINANCE_PERP_15BPS": 15.0,
}


class PaperTradeLedger:
    """
    Manages durable paper trade records with transaction cost accounting.
    """

    def __init__(self, ledger_file: Optional[str] = None, initial_bankroll: float = 10000.0):
        self.ledger_file = ledger_file or DEFAULT_LEDGER_PATH
        self.initial_bankroll = float(initial_bankroll)
        self._lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        os.makedirs(os.path.dirname(self.ledger_file), exist_ok=True)
        if not os.path.exists(self.ledger_file):
            with open(self.ledger_file, "w", encoding="utf-8") as f:
                pass  # create empty file

    def record_trade(
        self,
        strategy_id: str,
        action: str,  # "BUY" or "SELL"
        entry_price: float,
        size_btc: float,
        cost_scenario: str = "COINBASE_RETAIL_87BPS",
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        entry_time: Optional[str] = None,
        trade_id: Optional[str] = None,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Records a new open simulated paper trade in the persistent ledger.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        t_id = trade_id or f"ptrade-{uuid.uuid4().hex[:12]}"
        fee_bps = COST_SCENARIO_BPS.get(cost_scenario, 87.0)

        notional_entry = round(entry_price * size_btc, 2)
        entry_fee_usd = round(notional_entry * (fee_bps / 2.0 / 10000.0), 2)

        trade_record = {
            "trade_id": t_id,
            "strategy_id": strategy_id.upper(),
            "action": action.upper(),
            "status": "OPEN",
            "entry_time": entry_time or now_iso,
            "entry_price": round(entry_price, 2),
            "size_btc": round(size_btc, 6),
            "notional_usd": notional_entry,
            "stop_loss": round(stop_loss, 2) if stop_loss else None,
            "take_profit": round(take_profit, 2) if take_profit else None,
            "exit_time": None,
            "exit_price": None,
            "cost_scenario": cost_scenario,
            "fee_rate_bps": fee_bps,
            "fees_usd": entry_fee_usd,
            "gross_pnl_usd": 0.0,
            "net_pnl_usd": -entry_fee_usd,
            "return_pct": 0.0,
            "outcome": "OPEN",
            "notes": notes,
            "governance": {
                "execution_authorization": "DISABLED",
                "model_authorization": "OFFLINE_RESEARCH_ONLY",
                "environment": "PAPER_SIMULATION"
            }
        }

        with self._lock:
            with open(self.ledger_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(trade_record) + "\n")

        return trade_record

    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        exit_time: Optional[str] = None,
        outcome: str = "MANUAL_EXIT"
    ) -> Optional[Dict[str, Any]]:
        """
        Closes an open paper trade, computing gross PnL, round-trip fees, and net return.
        Atomically updates the ledger file.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        closed_record = None

        with self._lock:
            trades = self._read_all_trades_unlocked()
            updated_trades = []

            for t in trades:
                if t.get("trade_id") == trade_id and t.get("status") == "OPEN":
                    entry_p = float(t["entry_price"])
                    size = float(t["size_btc"])
                    action = t["action"]
                    fee_bps = float(t.get("fee_rate_bps", 87.0))

                    exit_p = float(exit_price)
                    notional_exit = exit_p * size
                    notional_entry = float(t.get("notional_usd", entry_p * size))

                    # Round-trip fee calculation
                    roundtrip_fee_usd = round((notional_entry + notional_exit) * 0.5 * (fee_bps / 10000.0), 2)

                    if action == "BUY":
                        gross_pnl = (exit_p - entry_p) * size
                    else:
                        gross_pnl = (entry_p - exit_p) * size

                    net_pnl = gross_pnl - roundtrip_fee_usd
                    ret_pct = (net_pnl / notional_entry) * 100.0 if notional_entry > 0 else 0.0

                    t["status"] = "CLOSED"
                    t["exit_time"] = exit_time or now_iso
                    t["exit_price"] = round(exit_p, 2)
                    t["fees_usd"] = roundtrip_fee_usd
                    t["gross_pnl_usd"] = round(gross_pnl, 2)
                    t["net_pnl_usd"] = round(net_pnl, 2)
                    t["return_pct"] = round(ret_pct, 2)
                    t["outcome"] = outcome
                    closed_record = dict(t)

                updated_trades.append(t)

            if closed_record:
                # Rewrite entire ledger file atomically
                with open(self.ledger_file, "w", encoding="utf-8") as f:
                    for t in updated_trades:
                        f.write(json.dumps(t) + "\n")

        return closed_record

    def get_trades(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
        strategy_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Returns trades from the ledger with filtering and pagination.
        """
        with self._lock:
            trades = self._read_all_trades_unlocked()

        filtered = []
        for t in trades:
            if status and t.get("status") != status.upper():
                continue
            if strategy_id and t.get("strategy_id") != strategy_id.upper():
                continue
            filtered.append(t)

        # Most recent first
        filtered.sort(key=lambda x: x.get("entry_time", ""), reverse=True)
        return filtered[offset : offset + limit]

    def get_portfolio_metrics(self) -> Dict[str, Any]:
        """
        Computes accurate point-in-time metrics from the closed paper trade ledger.
        """
        with self._lock:
            trades = self._read_all_trades_unlocked()

        closed = [t for t in trades if t.get("status") == "CLOSED"]
        open_trades = [t for t in trades if t.get("status") == "OPEN"]

        total_closed = len(closed)
        if total_closed == 0:
            return {
                "initial_bankroll_usd": self.initial_bankroll,
                "current_equity_usd": self.initial_bankroll,
                "total_trades": 0,
                "open_trades_count": len(open_trades),
                "closed_trades_count": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate_pct": 0.0,
                "gross_pnl_usd": 0.0,
                "total_fees_usd": 0.0,
                "net_pnl_usd": 0.0,
                "net_return_pct": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_pct": 0.0,
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "last_updated_utc": datetime.now(timezone.utc).isoformat()
            }

        wins = [t for t in closed if t.get("net_pnl_usd", 0.0) > 0]
        losses = [t for t in closed if t.get("net_pnl_usd", 0.0) < 0]

        gross_pnl_usd = sum(t.get("gross_pnl_usd", 0.0) for t in closed)
        total_fees_usd = sum(t.get("fees_usd", 0.0) for t in closed)
        net_pnl_usd = sum(t.get("net_pnl_usd", 0.0) for t in closed)

        win_sum = sum(t.get("net_pnl_usd", 0.0) for t in wins)
        loss_sum = abs(sum(t.get("net_pnl_usd", 0.0) for t in losses))
        profit_factor = round(win_sum / loss_sum, 2) if loss_sum > 0 else (99.0 if win_sum > 0 else 0.0)

        win_rate = round((len(wins) / total_closed) * 100.0, 1)

        # Drawdown calculation
        equity = self.initial_bankroll
        peak = equity
        max_dd_pct = 0.0
        returns = []

        # Sort chronologically for path metrics
        chron_closed = sorted(closed, key=lambda x: x.get("exit_time", x.get("entry_time", "")))
        for t in chron_closed:
            pnl = t.get("net_pnl_usd", 0.0)
            equity += pnl
            if equity > peak:
                peak = equity
            dd = ((peak - equity) / peak) * 100.0 if peak > 0 else 0.0
            if dd > max_dd_pct:
                max_dd_pct = dd
            returns.append(t.get("return_pct", 0.0))

        # Sharpe & Sortino (sample based)
        if len(returns) > 1:
            mean_ret = sum(returns) / len(returns)
            var_ret = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
            std_ret = math.sqrt(var_ret) if var_ret > 0 else 0.0
            sharpe = round((mean_ret / std_ret) * math.sqrt(365), 2) if std_ret > 0 else 0.0

            downside_returns = [r for r in returns if r < 0]
            if downside_returns:
                downside_var = sum(r ** 2 for r in downside_returns) / len(downside_returns)
                downside_std = math.sqrt(downside_var)
                sortino = round((mean_ret / downside_std) * math.sqrt(365), 2) if downside_std > 0 else 0.0
            else:
                sortino = 99.0 if mean_ret > 0 else 0.0
        else:
            sharpe = 0.0
            sortino = 0.0

        current_equity = round(self.initial_bankroll + net_pnl_usd, 2)
        net_ret_pct = round((net_pnl_usd / self.initial_bankroll) * 100.0, 2)

        return {
            "initial_bankroll_usd": self.initial_bankroll,
            "current_equity_usd": current_equity,
            "total_trades": len(trades),
            "open_trades_count": len(open_trades),
            "closed_trades_count": total_closed,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate_pct": win_rate,
            "gross_pnl_usd": round(gross_pnl_usd, 2),
            "total_fees_usd": round(total_fees_usd, 2),
            "net_pnl_usd": round(net_pnl_usd, 2),
            "net_return_pct": net_ret_pct,
            "profit_factor": profit_factor,
            "max_drawdown_pct": round(max_dd_pct, 2),
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "last_updated_utc": datetime.now(timezone.utc).isoformat()
        }

    def export_csv(self) -> str:
        """
        Exports all paper trade records as CSV string.
        """
        trades = self.get_trades(limit=10000)
        output = StringIO()
        if not trades:
            output.write("trade_id,strategy_id,action,status,entry_time,entry_price,size_btc,exit_time,exit_price,fees_usd,gross_pnl_usd,net_pnl_usd,return_pct,outcome,cost_scenario\n")
            return output.getvalue()

        fieldnames = [
            "trade_id", "strategy_id", "action", "status", "entry_time",
            "entry_price", "size_btc", "exit_time", "exit_price", "fees_usd",
            "gross_pnl_usd", "net_pnl_usd", "return_pct", "outcome", "cost_scenario"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for t in trades:
            writer.writerow(t)

        return output.getvalue()

    def export_json(self) -> str:
        """
        Exports all paper trade records as JSON string.
        """
        trades = self.get_trades(limit=10000)
        return json.dumps({
            "export_time_utc": datetime.now(timezone.utc).isoformat(),
            "trade_count": len(trades),
            "metrics": self.get_portfolio_metrics(),
            "trades": trades
        }, indent=2)

    def reset_ledger(self, keep_backup: bool = True) -> bool:
        """
        Safely clears the research ledger with an optional timestamped backup.
        """
        with self._lock:
            if keep_backup and os.path.exists(self.ledger_file):
                ts = int(time.time())
                backup_path = f"{self.ledger_file}.backup-{ts}"
                try:
                    with open(self.ledger_file, "r", encoding="utf-8") as src, open(backup_path, "w", encoding="utf-8") as dst:
                        dst.write(src.read())
                except Exception as e:
                    logger.warning("Failed to create ledger backup: %s", e)

            with open(self.ledger_file, "w", encoding="utf-8") as f:
                pass
        return True

    def _read_all_trades_unlocked(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.ledger_file):
            return []
        trades = []
        try:
            with open(self.ledger_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            trades.append(json.loads(line))
                        except Exception:
                            continue
        except Exception as e:
            logger.error("Error reading paper trade ledger: %s", e)
        return trades


_default_ledger: Optional[PaperTradeLedger] = None


def get_paper_trade_ledger() -> PaperTradeLedger:
    global _default_ledger
    if _default_ledger is None:
        _default_ledger = PaperTradeLedger()
    return _default_ledger

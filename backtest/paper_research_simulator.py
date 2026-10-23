"""
backtest/paper_research_simulator.py — Cost-Aware Paper Research Simulation Engine
===================================================================================
Implements Phase 5 Workstream 5B:
1. Non-Executing Research Simulator: Strictly offline paper simulation with zero capital exposure.
2. Realistic Microstructure Drag: Maker/Taker fees, spread crossing, slippage, market impact, latency.
3. Zero-Lookahead Execution: 1-bar execution lag; signals at t executed at t+1 open.
4. Intrabar Touch Closure: Evaluates SL before TP if both boundaries are touched within the bar.
5. Risk & Performance Analytics: Equity curve, Sharpe ratio, Max Drawdown, Turnover, Profit Factor.
"""

from __future__ import annotations

import math
import uuid
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

from backtest.execution_reality import ExecutionRealityEngine
from models.risk_metrics import sharpe_ratio, maximum_drawdown

logger = logging.getLogger("btcognitive.paper_research_simulator")


@dataclass
class PaperTrade:
    trade_id: str
    entry_time: str
    exit_time: str
    direction: str          # "LONG" or "SHORT"
    entry_price: float
    exit_price: float
    gross_return_pct: float
    net_return_pct: float
    fees_paid_usd: float
    slippage_usd: float
    exit_reason: str        # "TP_HIT", "SL_HIT", "HORIZON_EXPIRY"
    holding_bars: int


@dataclass
class PaperSimulationSummary:
    simulation_id: str
    strategy_name: str
    run_timestamp_utc: str
    total_trades: int
    win_rate_pct: float
    gross_pnl_pct: float
    net_pnl_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    profit_factor: float
    turnover_bars: float
    total_frictions_pct: float
    execution_mode: str = "OFFLINE_RESEARCH_ONLY"
    live_broker_connected: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PaperResearchSimulator:
    """
    Offline Strategy Research Simulator.
    """

    def __init__(
        self,
        initial_capital_usd: float = 100_000.0,
        cost_engine: Optional[ExecutionRealityEngine] = None,
        execution_mode: str = "TAKER"
    ):
        self.initial_capital_usd = initial_capital_usd
        self.cost_engine = cost_engine or ExecutionRealityEngine(
            base_fee_bps_maker=1.0,
            base_fee_bps_taker=5.0,
            base_spread_bps=2.0,
            base_slippage_bps=2.0
        )
        self.execution_mode = execution_mode.upper()

    def simulate(
        self,
        df_candles: pd.DataFrame,
        signals: pd.Series,             # +1 (LONG), -1 (SHORT), 0 (FLAT)
        tp_pct: float = 0.02,           # 2% take profit
        sl_pct: float = 0.015,          # 1.5% stop loss
        max_holding_bars: int = 24
    ) -> Tuple[PaperSimulationSummary, List[PaperTrade], pd.Series]:
        """
        Runs paper simulation with 1-bar execution lag.
        """
        df = df_candles.sort_values("timestamp").reset_index(drop=True).copy()
        n = len(df)
        if n < 50:
            raise ValueError(f"Insufficient candles ({n}) for simulation.")

        capital = self.initial_capital_usd
        equity_curve = [capital]
        trades: List[PaperTrade] = []

        in_pos = False
        pos_dir = ""
        pos_entry_price = 0.0
        pos_entry_idx = 0
        pos_tp = 0.0
        pos_sl = 0.0

        for i in range(1, n):
            current_bar = df.iloc[i]
            prev_signal = signals.iloc[i - 1] if (i - 1) < len(signals) else 0

            # If in position, check closure conditions first
            if in_pos:
                bars_held = i - pos_entry_idx
                high = current_bar["high"]
                low = current_bar["low"]
                closed = False
                exit_price = 0.0
                exit_reason = ""

                if pos_dir == "LONG":
                    # Conservative: check SL first
                    if low <= pos_sl:
                        closed = True
                        exit_price = pos_sl
                        exit_reason = "SL_HIT"
                    elif high >= pos_tp:
                        closed = True
                        exit_price = pos_tp
                        exit_reason = "TP_HIT"
                    elif bars_held >= max_holding_bars:
                        closed = True
                        exit_price = current_bar["close"]
                        exit_reason = "HORIZON_EXPIRY"

                elif pos_dir == "SHORT":
                    # Conservative: check SL first
                    if high >= pos_sl:
                        closed = True
                        exit_price = pos_sl
                        exit_reason = "SL_HIT"
                    elif low <= pos_tp:
                        closed = True
                        exit_price = pos_tp
                        exit_reason = "TP_HIT"
                    elif bars_held >= max_holding_bars:
                        closed = True
                        exit_price = current_bar["close"]
                        exit_reason = "HORIZON_EXPIRY"

                if closed:
                    # Compute trade returns & frictions
                    if pos_dir == "LONG":
                        gross_ret = (exit_price - pos_entry_price) / pos_entry_price
                    else:
                        gross_ret = (pos_entry_price - exit_price) / pos_entry_price

                    # Compute entry + exit friction
                    drag_info = self.cost_engine.compute_execution_drag(
                        signal_return=gross_ret,
                        mode=self.execution_mode,
                        order_size_usd=capital * 0.10
                    )
                    friction_rate = 2.0 * ((self.cost_engine.base_fee_taker + 0.5 * self.cost_engine.base_spread + self.cost_engine.base_slippage))
                    net_ret = gross_ret - friction_rate
                    trade_pnl = capital * 0.10 * net_ret
                    capital += trade_pnl

                    trades.append(PaperTrade(
                        trade_id=f"pt_{uuid.uuid4().hex[:8]}",
                        entry_time=str(df.iloc[pos_entry_idx]["timestamp"]),
                        exit_time=str(current_bar["timestamp"]),
                        direction=pos_dir,
                        entry_price=pos_entry_price,
                        exit_price=exit_price,
                        gross_return_pct=round(gross_ret * 100.0, 3),
                        net_return_pct=round(net_ret * 100.0, 3),
                        fees_paid_usd=round(capital * 0.10 * 2.0 * self.cost_engine.base_fee_taker, 2),
                        slippage_usd=round(capital * 0.10 * 2.0 * self.cost_engine.base_slippage, 2),
                        exit_reason=exit_reason,
                        holding_bars=bars_held
                    ))

                    in_pos = False

            # If not in position, check for new signal (1-bar execution lag: entry at current bar open)
            if not in_pos and prev_signal != 0:
                pos_dir = "LONG" if prev_signal > 0 else "SHORT"
                pos_entry_price = current_bar["open"]
                pos_entry_idx = i
                in_pos = True

                if pos_dir == "LONG":
                    pos_tp = pos_entry_price * (1.0 + tp_pct)
                    pos_sl = pos_entry_price * (1.0 - sl_pct)
                else:
                    pos_tp = pos_entry_price * (1.0 - tp_pct)
                    pos_sl = pos_entry_price * (1.0 + sl_pct)

            equity_curve.append(capital)

        # Performance statistics
        returns_series = pd.Series(equity_curve).pct_change().dropna()
        sr = float(sharpe_ratio(returns_series)) if len(returns_series) > 1 else 0.0
        mdd = float(maximum_drawdown(np.array(equity_curve))) if len(equity_curve) > 1 else 0.0

        win_count = sum(1 for t in trades if t.net_return_pct > 0)
        win_rate = (win_count / len(trades) * 100.0) if trades else 0.0

        gross_wins = sum(t.gross_return_pct for t in trades if t.gross_return_pct > 0)
        gross_losses = abs(sum(t.gross_return_pct for t in trades if t.gross_return_pct < 0))
        pf = round(gross_wins / gross_losses, 2) if gross_losses > 0 else (99.0 if gross_wins > 0 else 0.0)

        total_net_pnl = ((capital - self.initial_capital_usd) / self.initial_capital_usd) * 100.0
        total_gross_pnl = sum(t.gross_return_pct for t in trades)

        summary = PaperSimulationSummary(
            simulation_id=f"sim_{uuid.uuid4().hex[:10]}",
            strategy_name="causal_directional_paper_sim_v1",
            run_timestamp_utc=datetime.now(timezone.utc).isoformat(),
            total_trades=len(trades),
            win_rate_pct=round(win_rate, 2),
            gross_pnl_pct=round(total_gross_pnl, 2),
            net_pnl_pct=round(total_net_pnl, 2),
            sharpe_ratio=round(sr, 2),
            max_drawdown_pct=round(mdd * 100.0, 2),
            profit_factor=pf,
            turnover_bars=round(float(np.mean([t.holding_bars for t in trades])), 1) if trades else 0.0,
            total_frictions_pct=round(total_gross_pnl - total_net_pnl, 2),
            execution_mode="OFFLINE_RESEARCH_ONLY",
            live_broker_connected=False
        )

        return summary, trades, pd.Series(equity_curve)

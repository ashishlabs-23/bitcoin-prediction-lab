"""
backtest/execution_reality.py — Level 4 & 5 Execution Reality & Adverse Selection Layer
======================================================================================
Models microstructure execution drag and passive fill mechanics:
  1. MAKER vs. TAKER execution mode separation.
  2. Adverse Selection: P(fill before adverse move | S_t, Q_t).
  3. Execution Drag decomposition:
     Execution Drag = EV_signal - EV_exec
     where EV_exec = EV_signal - Fee - Spread - Impact - Slippage - Latency - AdverseSelection
  4. Levels 4 & 5 Validation gates.
"""

import os
import sys
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import pandas as pd


class ExecutionRealityEngine:
    """
    Simulates realistic microstructure execution costs, adverse selection on passive fills,
    and market impact across order sizes.
    """

    def __init__(
        self,
        base_fee_bps_maker: float = 1.0,
        base_fee_bps_taker: float = 5.0,
        base_spread_bps: float = 2.0,
        base_slippage_bps: float = 2.0,
        base_latency_ms: float = 50.0
    ):
        self.base_fee_maker = base_fee_bps_maker / 10000.0
        self.base_fee_taker = base_fee_bps_taker / 10000.0
        self.base_spread = base_spread_bps / 10000.0
        self.base_slippage = base_slippage_bps / 10000.0
        self.base_latency_ms = base_latency_ms

    def estimate_maker_fill_probability(
        self,
        vpin: float,
        book_imbalance: float,
        vol_shock: float
    ) -> Tuple[float, float]:
        """
        Estimates:
          1. P(fill): Probability that limit order gets matched.
          2. P(fill_before_adverse): Probability that order fills WITHOUT immediate adverse move.
        """
        # High VPIN and one-sided imbalance increases overall fill probability but increases toxicity
        p_fill = float(np.clip(0.60 + 0.20 * book_imbalance - 0.10 * vol_shock, 0.10, 0.95))
        
        # Adverse fill penalty: probability of adverse selection scales with VPIN
        p_adverse_given_fill = float(np.clip(0.30 + 0.40 * vpin + 0.15 * abs(vol_shock), 0.10, 0.85))
        p_fill_favorable = float(p_fill * (1.0 - p_adverse_given_fill))

        return p_fill, p_fill_favorable

    def compute_execution_drag(
        self,
        signal_return: float,
        mode: str = "TAKER",
        order_size_usd: float = 10000.0,
        spread_bps: Optional[float] = None,
        vpin: float = 0.5,
        book_imbalance: float = 0.0,
        vol_shock: float = 0.0,
        cost_multiplier: float = 1.0,
        latency_ms: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculates exact net executable EV after deducting all microstructure frictions.
        """
        mult = cost_multiplier
        spread = (spread_bps / 10000.0 if spread_bps is not None else self.base_spread) * mult
        lat_ms = latency_ms if latency_ms is not None else self.base_latency_ms

        # 1. Market Impact (Square root model: impact ~ Y * sigma * sqrt(size / ADV))
        # Scaled impact in basis points
        adv_usd = 50_000_000.0 # $50M daily liquidity reference
        impact = float(0.10 * np.sqrt(max(100.0, order_size_usd) / adv_usd) * 0.01) * mult

        # 2. Latency Drag (approx 0.05 bps per 10ms of latency during volatility)
        latency_drag = float((lat_ms / 10.0) * (0.05 / 10000.0) * max(1.0, abs(vol_shock))) * mult

        is_taker = mode.upper() == "TAKER"

        if is_taker:
            fee = self.base_fee_taker * mult
            half_spread = 0.5 * spread
            slippage = (self.base_slippage + 0.5 * abs(vol_shock) * 0.0002) * mult
            adverse_selection = 0.0 # Absorbed in spread crossing for market orders
            p_fill = 1.0 # Market orders execute immediately

            total_friction = fee + half_spread + impact + slippage + latency_drag
            net_return = signal_return - total_friction
        else: # MAKER
            fee = self.base_fee_maker * mult # Lower maker fee / rebate
            half_spread = -0.5 * spread # Maker captures the half-spread if filled
            slippage = 0.0
            p_fill, p_favorable = self.estimate_maker_fill_probability(vpin, book_imbalance, vol_shock)
            
            # Adverse selection drag on filled orders: price moves against quote by fraction of spread
            adverse_selection = float(spread * (1.0 - p_favorable / max(0.01, p_fill))) * mult
            total_friction = fee + half_spread + impact + adverse_selection + latency_drag

            # Expected maker EV weighted by fill probability
            net_return = p_fill * (signal_return - total_friction)

        exec_drag = float(signal_return - net_return)

        return {
            "mode": mode.upper(),
            "signal_return_bps": round(signal_return * 10000.0, 2),
            "net_return_bps": round(net_return * 10000.0, 2),
            "execution_drag_bps": round(exec_drag * 10000.0, 2),
            "p_fill": round(p_fill, 4),
            "cost_breakdown_bps": {
                "fee": round(fee * 10000.0, 2),
                "spread_cross": round(half_spread * 10000.0, 2),
                "impact": round(impact * 10000.0, 2),
                "slippage": round(slippage * 10000.0, 2) if is_taker else 0.0,
                "adverse_selection": round(adverse_selection * 10000.0, 2),
                "latency_drag": round(latency_drag * 10000.0, 2)
            },
            "valid_l4_execution": bool(p_fill > 0.40),
            "valid_l5_economic": bool(net_return > 0.0)
        }

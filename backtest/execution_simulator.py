"""
Microstructure-Aware Execution Simulator for bitcoin-prediction-lab.

Models realistic order execution under real-world market dynamics:
- Bid-Ask Spread cost drag (Corwin-Schultz / L2 depth)
- Volume-dependent slippage (market order impact)
- VIP Exchange Fee Tiers (Maker vs Taker)
- Latency execution delay (1-bar or millisecond proxy)
- Dynamic ATR-based Take Profit (TP) & Stop Loss (SL) bounds
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional


class ExecutionSimulator:
    def __init__(
        self,
        fee_tier: str = "taker",
        maker_fee_bps: float = 2.0,
        taker_fee_bps: float = 5.0,
        base_slippage_bps: float = 2.0,
        latency_bars: int = 1
    ):
        self.fee_tier = fee_tier
        self.maker_fee_bps = maker_fee_bps
        self.taker_fee_bps = taker_fee_bps
        self.base_slippage_bps = base_slippage_bps
        self.latency_bars = latency_bars

    def calculate_effective_fee(self, is_maker: bool = False) -> float:
        """Returns fee in decimal format (e.g. 5 bps = 0.0005)."""
        fee_bps = self.maker_fee_bps if is_maker else self.taker_fee_bps
        return fee_bps / 10000.0

    def calculate_slippage(
        self,
        order_size_usdt: float,
        bid_ask_spread_pct: float = 0.0005,
        vpin: float = 0.20
    ) -> float:
        """
        Calculates non-linear market impact slippage based on position size, bid-ask spread, and VPIN toxicity.
        Returns total slippage cost in decimal format.
        """
        half_spread = max(0.0001, bid_ask_spread_pct / 2.0)
        size_impact = np.sqrt(max(1.0, order_size_usdt / 100000.0)) * (self.base_slippage_bps / 10000.0)
        toxicity_multiplier = 1.0 + max(0.0, (vpin - 0.5) * 2.0)
        
        total_slippage = (half_spread + size_impact) * toxicity_multiplier
        return float(total_slippage)

    def execute_order(
        self,
        side: str,
        price: float,
        order_size_usdt: float = 10000.0,
        bid_ask_spread_pct: float = 0.0005,
        vpin: float = 0.20,
        is_maker: bool = False
    ) -> Dict[str, Any]:
        """
        Executes a simulated buy or sell order and returns fill details.
        """
        fee_rate = self.calculate_effective_fee(is_maker=is_maker)
        slippage_rate = self.calculate_slippage(order_size_usdt, bid_ask_spread_pct, vpin)
        
        side_upper = side.upper()
        if side_upper in ["BUY", "LONG"]:
            fill_price = price * (1.0 + slippage_rate)
        else: # SELL / SHORT
            fill_price = price * (1.0 - slippage_rate)
            
        fee_cost = order_size_usdt * fee_rate
        slippage_cost = order_size_usdt * slippage_rate
        total_friction = fee_cost + slippage_cost

        return {
            'side': side_upper,
            'base_price': price,
            'fill_price': fill_price,
            'fee_rate': fee_rate,
            'slippage_rate': slippage_rate,
            'fee_cost_usdt': fee_cost,
            'slippage_cost_usdt': slippage_cost,
            'total_friction_usdt': total_friction,
            'total_friction_bps': (total_friction / order_size_usdt) * 10000.0
        }

    def compute_dynamic_tp_sl(
        self,
        entry_price: float,
        direction: str,
        atr: float,
        tp_mult: float = 2.0,
        sl_mult: float = 1.5,
        regime: str = "TRENDING_BULL"
    ) -> Dict[str, float]:
        """
        Computes ATR-based dynamic Take Profit and Stop Loss levels adjusted for regime volatility.
        """
        regime_mult = 1.2 if "HIGH_VOLATILITY" in regime else 1.0
        effective_tp_mult = tp_mult * regime_mult
        effective_sl_mult = sl_mult * regime_mult
        
        dir_upper = direction.upper()
        if dir_upper == "LONG":
            tp = entry_price + (atr * effective_tp_mult)
            sl = entry_price - (atr * effective_sl_mult)
        else: # SHORT
            tp = entry_price - (atr * effective_tp_mult)
            sl = entry_price + (atr * effective_sl_mult)

        return {
            'tp_price': max(0.0, tp),
            'sl_price': max(0.0, sl),
            'tp_dist_pct': abs(tp - entry_price) / entry_price,
            'sl_dist_pct': abs(sl - entry_price) / entry_price,
        }

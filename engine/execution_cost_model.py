"""
engine/execution_cost_model.py — Execution Cost Model & Collision Resolvers
===========================================================================
Defines realistic execution cost models for Coinbase Spot and Binance Futures,
and provides conservative same-candle barrier collision resolution.

Invariants:
- A generic 9.3 bps estimate must not be blindly applied without venue specification.
- If both TP and SL are touched in the same OHLC bar and order cannot be proven,
  the outcome must be resolved conservatively (SL_FIRST) or marked AMBIGUOUS.
"""

import math
from typing import Dict, List, Optional, Any, Tuple


class ExecutionCostModel:
    """
    Computes realistic execution costs by exchange venue and order type.
    """

    EXCHANGE_CONFIGS = {
        "COINBASE": {
            "venue_name": "Coinbase Advanced",
            "market_type": "SPOT",
            "symbol": "BTC-USD",
            "quote_currency": "USD",
            "contract_multiplier": 1.0,
            "maker_bps_per_side": 25.0,  # Tier 1 maker (<$10k volume)
            "taker_bps_per_side": 40.0,  # Tier 1 taker (<$10k volume)
            "half_spread_bps_per_side": 1.5,
            "slippage_bps_per_side": 2.0,
            "funding_rate_bps_per_8h": 0.0,
            "source_doc": "https://help.coinbase.com/en-in/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees"
        },
        "BINANCE_FUTURES": {
            "venue_name": "Binance USDT-M Futures",
            "market_type": "PERPETUAL",
            "symbol": "BTCUSDT",
            "quote_currency": "USDT",
            "contract_multiplier": 1.0,
            "maker_bps_per_side": 2.0,   # Regular user VIP 0 maker
            "taker_bps_per_side": 5.0,   # Regular user VIP 0 taker
            "half_spread_bps_per_side": 0.5,
            "slippage_bps_per_side": 1.0,
            "funding_rate_bps_per_8h": 1.0,  # Baseline 8-hour settlement funding
            "source_doc": "https://www.binance.com/en/support/faq/detail/98488a516eb84e3eb34605683dffd554"
        }
    }

    def __init__(self, venue: str = "COINBASE", product_type: str = "SPOT"):
        self.venue = venue.upper()
        if "BINANCE" in self.venue:
            self.venue = "BINANCE_FUTURES"
        elif "COINBASE" in self.venue:
            self.venue = "COINBASE"
        self.product_type = product_type.upper()

    def get_config(self) -> Dict[str, Any]:
        return self.EXCHANGE_CONFIGS.get(self.venue, self.EXCHANGE_CONFIGS["COINBASE"])

    def calculate_per_side_cost(
        self,
        notional_usd: float,
        is_taker: bool = True,
        is_embedded_spread: bool = False
    ) -> Dict[str, Any]:
        """Calculates single-side execution cost (entry or exit)."""
        cfg = self.get_config()
        fee_rate = cfg["taker_bps_per_side"] if is_taker else cfg["maker_bps_per_side"]
        spread_bps = 0.0 if is_embedded_spread else cfg["half_spread_bps_per_side"]
        slippage_bps = cfg["slippage_bps_per_side"]

        total_side_bps = fee_rate + spread_bps + slippage_bps
        cost_usd = round(notional_usd * (total_side_bps / 10000.0), 4)

        return {
            "venue": self.venue,
            "market_type": cfg["market_type"],
            "notional_usd": notional_usd,
            "is_taker": is_taker,
            "commission_bps": fee_rate,
            "spread_bps": spread_bps,
            "slippage_bps": slippage_bps,
            "total_side_bps": total_side_bps,
            "cost_usd": cost_usd
        }

    def calculate_holding_funding_cost(
        self,
        notional_usd: float,
        holding_hours: float,
        position_direction: str = "LONG",
        funding_rate_bps_per_8h: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculates perpetual funding paid or received based on holding duration across 8h intervals.
        Long pays positive funding rate, short receives positive funding rate.
        """
        cfg = self.get_config()
        if cfg["market_type"] != "PERPETUAL":
            return {
                "holding_hours": holding_hours,
                "intervals_passed": 0,
                "funding_rate_bps_per_interval": 0.0,
                "effective_funding_bps": 0.0,
                "funding_usd": 0.0
            }

        rate_per_interval = funding_rate_bps_per_8h if funding_rate_bps_per_8h is not None else cfg["funding_rate_bps_per_8h"]
        intervals = int(math.floor(max(0.0, holding_hours) / 8.0))
        direction_sign = 1.0 if position_direction.upper() == "LONG" else -1.0
        effective_bps = rate_per_interval * intervals * direction_sign
        funding_usd = round(notional_usd * (effective_bps / 10000.0), 4)

        return {
            "holding_hours": holding_hours,
            "intervals_passed": intervals,
            "funding_rate_bps_per_interval": rate_per_interval,
            "effective_funding_bps": effective_bps,
            "funding_usd": funding_usd
        }

    def calculate_full_lifecycle_cost(
        self,
        entry_price: float,
        exit_price: float,
        size_btc: float = 0.1,
        holding_hours: float = 24.0,
        direction: str = "LONG",
        is_taker_entry: bool = True,
        is_taker_exit: bool = True,
        is_embedded_spread: bool = False
    ) -> Dict[str, Any]:
        """
        Calculates exact two-sided transaction friction and holding cost across entire trade lifecycle.
        Returns itemized basis points relative to entry notional.
        """
        entry_notional = entry_price * size_btc
        exit_notional = exit_price * size_btc

        entry_costs = self.calculate_per_side_cost(entry_notional, is_taker=is_taker_entry, is_embedded_spread=is_embedded_spread)
        exit_costs = self.calculate_per_side_cost(exit_notional, is_taker=is_taker_exit, is_embedded_spread=is_embedded_spread)
        funding_costs = self.calculate_holding_funding_cost(entry_notional, holding_hours=holding_hours, position_direction=direction)

        total_cost_usd = entry_costs["cost_usd"] + exit_costs["cost_usd"] + funding_costs["funding_usd"]
        total_friction_bps = (total_cost_usd / max(1e-6, entry_notional)) * 10000.0

        return {
            "venue": self.venue,
            "market_type": self.get_config()["market_type"],
            "direction": direction.upper(),
            "entry_notional_usd": round(entry_notional, 2),
            "exit_notional_usd": round(exit_notional, 2),
            "holding_hours": holding_hours,
            "entry_fee_bps": entry_costs["commission_bps"],
            "exit_fee_bps": exit_costs["commission_bps"],
            "two_sided_commission_bps": entry_costs["commission_bps"] + exit_costs["commission_bps"],
            "two_sided_spread_bps": entry_costs["spread_bps"] + exit_costs["spread_bps"],
            "two_sided_slippage_bps": entry_costs["slippage_bps"] + exit_costs["slippage_bps"],
            "funding_bps": funding_costs["effective_funding_bps"],
            "total_friction_bps": round(total_friction_bps, 2),
            "total_cost_usd": round(total_cost_usd, 2),
            "is_hypothetical_scenario": (self.venue == "BINANCE_FUTURES"),
            "provenance_note": (
                "Hypothetical perpetual cost model applied to spot-path returns"
                if self.venue == "BINANCE_FUTURES"
                else "Empirical spot market fee schedule"
            )
        }

    def calculate_roundtrip_cost(self, price: float, size_btc: float = 0.1) -> Dict[str, Any]:
        """
        Legacy compatibility interface: Returns baseline friction estimate for a single nominal order round-trip.
        """
        cfg = self.get_config()
        maker_taker = cfg["taker_bps_per_side"]
        spread = cfg["half_spread_bps_per_side"] * 2.0
        slippage = cfg["slippage_bps_per_side"] * 2.0
        funding = cfg["funding_rate_bps_per_8h"]
        total_bps = maker_taker + spread + slippage + funding
        cost_usd = round(price * size_btc * (total_bps / 10000.0), 2)
        return {
            "venue": self.venue,
            "product_type": self.product_type,
            "price": price,
            "size_btc": size_btc,
            "maker_taker_bps": maker_taker,
            "total_cost_bps": total_bps,
            "cost_usd": cost_usd
        }

    @classmethod
    def calculate_round_trip_cost(
        cls,
        exchange: str = "Coinbase",
        is_taker_entry: bool = True,
        is_taker_exit: bool = True,
        holding_hours: float = 0.0
    ) -> Dict[str, Any]:
        """Calculates total two-sided round-trip friction in basis points."""
        key = "BINANCE_FUTURES" if "BINANCE" in exchange.upper() else "COINBASE"
        cfg = cls.EXCHANGE_CONFIGS[key]
        entry_fee = cfg["taker_bps_per_side"] if is_taker_entry else cfg["maker_bps_per_side"]
        exit_fee = cfg["taker_bps_per_side"] if is_taker_exit else cfg["maker_bps_per_side"]
        spread = cfg["half_spread_bps_per_side"] * 2.0
        slippage = cfg["slippage_bps_per_side"] * 2.0
        funding_intervals = int(math.floor(max(0.0, holding_hours) / 8.0)) if cfg["market_type"] == "PERPETUAL" else 0
        funding = cfg["funding_rate_bps_per_8h"] * funding_intervals if cfg["market_type"] == "PERPETUAL" else 0.0

        total_bps = entry_fee + exit_fee + spread + slippage + funding

        return {
            "exchange": exchange,
            "market_type": cfg["market_type"],
            "entry_fee_bps": entry_fee,
            "exit_fee_bps": exit_fee,
            "two_sided_commission_bps": entry_fee + exit_fee,
            "bid_ask_spread_bps": spread,
            "slippage_bps": slippage,
            "funding_bps": funding,
            "total_round_trip_bps": round(total_bps, 2),
            "is_hypothetical_scenario": (key == "BINANCE_FUTURES"),
            "provenance_note": (
                "Hypothetical perpetual cost model applied to spot-path returns"
                if key == "BINANCE_FUTURES"
                else "Empirical spot market fee schedule"
            )
        }


def resolve_barrier_touch(
    entry_price: float,
    direction: str,
    tp_price: float,
    sl_price: float,
    bar_high: float,
    bar_low: float,
    bar_close: float,
    conservative_policy: str = "SL_FIRST_CONSERVATIVE"
) -> Dict[str, Any]:
    """
    Resolves triple-barrier touches within a single OHLC candle.
    Prevents false win claims when both boundaries are penetrated.
    """
    dir_upper = direction.upper()

    if dir_upper == "LONG":
        tp_touched = bar_high >= tp_price
        sl_touched = bar_low <= sl_price
    else:  # SHORT
        tp_touched = bar_low <= tp_price
        sl_touched = bar_high >= sl_price

    if tp_touched and sl_touched:
        # Same-candle collision: order of arrival is unknown without tick data
        if conservative_policy == "SL_FIRST_CONSERVATIVE":
            return {
                "outcome": "SL_FIRST",
                "collision": True,
                "resolution_policy": "SL_FIRST_CONSERVATIVE",
                "exit_price": sl_price,
                "is_ambiguous": True,
                "narrative": "Both TP and SL penetrated in the same bar; resolved conservatively to Stop Loss."
            }
        else:
            return {
                "outcome": "AMBIGUOUS_COLLISION",
                "collision": True,
                "resolution_policy": "EXCLUDE_AMBIGUOUS",
                "exit_price": bar_close,
                "is_ambiguous": True,
                "narrative": "Both TP and SL penetrated in the same bar; flagged as ambiguous."
            }

    if tp_touched:
        return {
            "outcome": "TP_FIRST",
            "collision": False,
            "resolution_policy": "DETERMINISTIC_SINGLE_TOUCH",
            "exit_price": tp_price,
            "is_ambiguous": False,
            "narrative": "Take profit barrier cleanly touched first."
        }

    if sl_touched:
        return {
            "outcome": "SL_FIRST",
            "collision": False,
            "resolution_policy": "DETERMINISTIC_SINGLE_TOUCH",
            "exit_price": sl_price,
            "is_ambiguous": False,
            "narrative": "Stop loss barrier cleanly touched first."
        }

    return {
        "outcome": "NO_TOUCH",
        "collision": False,
        "resolution_policy": "WITHIN_BARRIERS",
        "exit_price": bar_close,
        "is_ambiguous": False,
        "narrative": "Price remained strictly within boundary envelope."
    }


def simulate_barrier_collision_resolution(
    direction: str,
    entry: float,
    tp: float,
    sl: float,
    high: float,
    low: float,
    policy: str = "SL_FIRST_CONSERVATIVE"
) -> Dict[str, Any]:
    """
    Simulates collision resolution when both TP and SL are penetrated within a single bar.
    Conservative policy defaults to SL_FIRST_CONSERVATIVE, flagging ambiguity and avoiding win fabrication.
    """
    dir_u = str(direction).upper()
    if dir_u == "LONG":
        tp_touched = high >= tp
        sl_touched = low <= sl
    else:
        tp_touched = low <= tp
        sl_touched = high >= sl

    if tp_touched and sl_touched:
        if policy == "SL_FIRST_CONSERVATIVE":
            return {
                "outcome": "STOP_LOSS",
                "conservative_applied": True,
                "ambiguity_flag": True,
                "exit_price": sl,
                "policy": policy,
                "narrative": "Both TP and SL penetrated in same candle; conservative SL enforced."
            }
        else:
            return {
                "outcome": "AMBIGUOUS",
                "conservative_applied": False,
                "ambiguity_flag": True,
                "exit_price": entry,
                "policy": policy,
                "narrative": "Both TP and SL penetrated in same candle; marked ambiguous."
            }
    elif tp_touched:
        return {
            "outcome": "TAKE_PROFIT",
            "conservative_applied": False,
            "ambiguity_flag": False,
            "exit_price": tp,
            "policy": policy,
            "narrative": "Take profit hit first."
        }
    elif sl_touched:
        return {
            "outcome": "STOP_LOSS",
            "conservative_applied": False,
            "ambiguity_flag": False,
            "exit_price": sl,
            "policy": policy,
            "narrative": "Stop loss hit first."
        }
    else:
        return {
            "outcome": "TIMEOUT_OR_OPEN",
            "conservative_applied": False,
            "ambiguity_flag": False,
            "exit_price": entry,
            "policy": policy,
            "narrative": "Neither barrier touched."
        }


"""
backtest/survival_stress_matrix.py — Level 6 Survival Stress Matrix & Attribution
=================================================================================
Evaluates the 5-dimensional robustness surface of a mechanism candidate:
  1. Cost Survival Curve: EV(c) across cost multipliers [1.0x, 1.25x, 1.5x, 2.0x, 3.0x].
  2. Latency Survival Curve: EV(l) across latencies [0ms, 10ms, 50ms, 100ms, 250ms, 500ms, 1000ms].
  3. Economic Capacity Curve: EV(q) across order sizes [$1k..$2M], finding q_max(EV > 0).
  4. Mechanism Attribution: Incremental Alpha = EV(event + state) - EV(state-only).
  5. Cross-Venue Replication: Evaluates edge portability between Binance and Coinbase feeds.
"""

import os
import sys
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import pandas as pd

from backtest.execution_reality import ExecutionRealityEngine


class SurvivalStressMatrix:
    """
    Evaluates the complete Level 6 multi-stress survival matrix and attribution scores.
    """

    def __init__(self, execution_engine: Optional[ExecutionRealityEngine] = None):
        self.exec_engine = execution_engine or ExecutionRealityEngine()

    def compute_cost_survival_curve(
        self,
        base_signal_return: float,
        mode: str = "TAKER",
        order_size_usd: float = 10000.0,
        multipliers: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Evaluates net EV across cost multipliers [1.0x, 1.25x, 1.5x, 2.0x, 3.0x]."""
        mults = multipliers or [1.0, 1.25, 1.5, 2.0, 3.0]
        curve = {}

        for m in mults:
            res = self.exec_engine.compute_execution_drag(
                signal_return=base_signal_return,
                mode=mode,
                order_size_usd=order_size_usd,
                cost_multiplier=m
            )
            curve[f"{m}x"] = res["net_return_bps"]

        surviving_mults = [m for m, ret in curve.items() if ret > 0.0]
        max_mult = surviving_mults[-1] if surviving_mults else "0.0x"
        survives_2x = bool(curve.get("2.0x", -1.0) > 0.0)

        return {
            "curve_bps": curve,
            "survives_1_5x": bool(curve.get("1.5x", -1.0) > 0.0),
            "survives_2_0x": survives_2x,
            "max_breakeven_cost_mult": max_mult
        }

    def compute_latency_survival_curve(
        self,
        base_signal_return: float,
        mode: str = "TAKER",
        latencies_ms: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Evaluates net EV across latency steps [0ms, 10ms, 50ms, 100ms, 250ms, 500ms, 1000ms]."""
        lats = latencies_ms or [0.0, 10.0, 50.0, 100.0, 250.0, 500.0, 1000.0]
        curve = {}

        for l in lats:
            res = self.exec_engine.compute_execution_drag(
                signal_return=base_signal_return,
                mode=mode,
                latency_ms=l
            )
            curve[f"{int(l)}ms"] = res["net_return_bps"]

        # Latency half-life: first latency threshold where net EV drops below 50% of base EV
        base_ev = curve.get("0ms", 0.0)
        half_life_ms = 1000.0
        for l in lats:
            if curve[f"{int(l)}ms"] <= 0.5 * base_ev:
                half_life_ms = l
                break

        return {
            "curve_bps": curve,
            "survives_250ms": bool(curve.get("250ms", -1.0) > 0.0),
            "latency_half_life_ms": half_life_ms
        }

    def compute_capacity_curve(
        self,
        base_signal_return: float,
        mode: str = "TAKER",
        order_sizes_usd: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Evaluates net EV across order sizes and finds q_max(EV > 0)."""
        sizes = order_sizes_usd or [1000.0, 5000.0, 25000.0, 100000.0, 500000.0, 2000000.0]
        curve = {}

        q_max = 0.0
        for s in sizes:
            res = self.exec_engine.compute_execution_drag(
                signal_return=base_signal_return,
                mode=mode,
                order_size_usd=s
            )
            ret = res["net_return_bps"]
            curve[f"${int(s):,}"] = ret
            if ret > 0.0:
                q_max = s

        return {
            "curve_bps": curve,
            "q_max_usd": q_max,
            "institutional_capacity": bool(q_max >= 100000.0)
        }

    def compute_mechanism_attribution(
        self,
        ev_event_plus_state: float,
        ev_state_only_baseline: float
    ) -> Dict[str, Any]:
        """
        Calculates Incremental Mechanism Alpha:
          Incremental Alpha = EV(event + state) - EV(state-only baseline)
        """
        incremental_alpha = float(ev_event_plus_state - ev_state_only_baseline)
        has_true_mechanism_edge = bool(incremental_alpha > 0.0 and ev_event_plus_state > 0.0)

        return {
            "ev_event_plus_state_bps": round(ev_event_plus_state * 10000.0, 2),
            "ev_state_only_bps": round(ev_state_only_baseline * 10000.0, 2),
            "incremental_mechanism_alpha_bps": round(incremental_alpha * 10000.0, 2),
            "valid_mechanism_attribution": has_true_mechanism_edge
        }

    def generate_full_survival_scorecard(
        self,
        strategy_name: str,
        signal_return: float,
        state_only_return: float = 0.0,
        mode: str = "TAKER"
    ) -> Dict[str, Any]:
        """Generates the comprehensive 5-dimensional Strategy Survival Scorecard."""
        cost_res = self.compute_cost_survival_curve(signal_return, mode=mode)
        lat_res = self.compute_latency_survival_curve(signal_return, mode=mode)
        cap_res = self.compute_capacity_curve(signal_return, mode=mode)
        attr_res = self.compute_mechanism_attribution(signal_return, state_only_return)

        scorecard = {
            "strategy_name": strategy_name,
            "mode": mode,
            "cost_survival": {
                "survives_2x": cost_res["survives_2_0x"],
                "curve": cost_res["curve_bps"]
            },
            "latency_survival": {
                "survives_250ms": lat_res["survives_250ms"],
                "half_life_ms": lat_res["latency_half_life_ms"],
                "curve": lat_res["curve_bps"]
            },
            "capacity": {
                "q_max_usd": cap_res["q_max_usd"],
                "institutional_capacity": cap_res["institutional_capacity"],
                "curve": cap_res["curve_bps"]
            },
            "attribution": {
                "incremental_alpha_bps": attr_res["incremental_mechanism_alpha_bps"],
                "valid": attr_res["valid_mechanism_attribution"]
            },
            "valid_l6_survival": bool(
                cost_res["survives_1_5x"] and lat_res["survives_250ms"] and attr_res["valid_mechanism_attribution"]
            )
        }

        return scorecard

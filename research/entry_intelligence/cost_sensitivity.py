"""
research/entry_intelligence/cost_sensitivity.py
================================================
Execution-cost sensitivity analysis for entry quality metrics.

Evaluates net expected value across the five standard BTCognitive
execution cost scenarios, clearly labelling unverified assumptions.

RESEARCH BOUNDARY: OFFLINE_RESEARCH_ONLY.
"""

from __future__ import annotations

import pandas as pd
from typing import Dict, Any, List

from research.entry_intelligence.entry_quality_metrics import EntryQualityMetrics


# Five canonical execution cost scenarios
COST_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "SCEN_0_FRICTIONLESS": {
        "description": "Idealized zero friction — theoretical upper bound (research only).",
        "maker_fee_bps": 0.0,
        "taker_fee_bps": 0.0,
        "half_spread_bps": 0.0,
        "slippage_bps": 0.0,
        "adverse_selection_bps": 0.0,
        "round_trip_bps": 0.0,
        "verified": False,
        "warning": "THEORETICAL ONLY — not achievable in production.",
    },
    "SCEN_1_BINANCE_VIP0": {
        "description": "Binance Spot VIP 0 standard retail tier.",
        "maker_fee_bps": 10.0,
        "taker_fee_bps": 10.0,
        "half_spread_bps": 1.0,
        "slippage_bps": 1.0,
        "adverse_selection_bps": 0.0,
        "round_trip_bps": 24.0,
        "verified": True,
        "warning": None,
    },
    "SCEN_2_COINBASE_ADV": {
        "description": "Coinbase Advanced retail taker — conservative baseline.",
        "maker_fee_bps": 25.0,
        "taker_fee_bps": 40.0,
        "half_spread_bps": 2.5,
        "slippage_bps": 1.0,
        "adverse_selection_bps": 0.0,
        "round_trip_bps": 87.0,
        "verified": True,
        "warning": None,
    },
    "SCEN_3_PASSIVE_MAKER": {
        "description": "Hypothetical passive maker limit order with adverse selection haircut.",
        "maker_fee_bps": 15.0,
        "taker_fee_bps": 15.0,
        "half_spread_bps": 0.0,
        "slippage_bps": 0.0,
        "adverse_selection_bps": 6.0,
        "round_trip_bps": 36.0,
        "verified": False,
        "warning": (
            "UNVERIFIED RESEARCH SCENARIO: Assumes 6.0 bps adverse selection haircut "
            "and unverified limit fill probability. Limit orders may not fill when the "
            "market moves most favourably (Winner's Curse). "
            "Do not treat as verified execution cost."
        ),
    },
    "SCEN_4_STRESSED_VOL": {
        "description": "Stressed volatility / liquidity crisis — worst-case stress test.",
        "maker_fee_bps": 40.0,
        "taker_fee_bps": 80.0,
        "half_spread_bps": 10.0,
        "slippage_bps": 15.0,
        "adverse_selection_bps": 12.0,
        "round_trip_bps": 197.0,
        "verified": False,
        "warning": "STRESS TEST SCENARIO — represents tail liquidity conditions.",
    },
}


class CostSensitivityAnalyzer:
    """
    Sweeps all five standard cost scenarios and returns comparative EV table.

    Args:
        excursion_df: Output of ExcursionCalculator.compute_batch().
        barrier_df: Output of TripleBarrierLabeler.label_batch().
        tp_pct: Take-profit distance (%) used in EV calculation.
        sl_pct: Stop-loss distance (%) used in EV calculation.
    """

    def __init__(
        self,
        excursion_df: pd.DataFrame,
        barrier_df: pd.DataFrame,
        tp_pct: float = 1.5,
        sl_pct: float = 0.75,
    ) -> None:
        self._exc = excursion_df
        self._bar = barrier_df
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct

    def analyze_all_scenarios(self) -> List[Dict[str, Any]]:
        """
        Compute EV for each scenario and return sorted list (best to worst net EV).
        """
        results = []
        for scenario_id, meta in COST_SCENARIOS.items():
            metrics = EntryQualityMetrics(
                excursion_df=self._exc,
                barrier_df=self._bar,
                cost_scenario=scenario_id,
                round_trip_bps=meta["round_trip_bps"],
            )
            ev = metrics.net_expected_value(self.tp_pct, self.sl_pct)
            results.append({
                "scenario_id": scenario_id,
                "description": meta["description"],
                "round_trip_bps": meta["round_trip_bps"],
                "verified": meta["verified"],
                "net_ev_bps": ev.get("net_ev_bps"),
                "net_ev_pct": ev.get("net_ev_pct"),
                "p_tp": ev.get("p_tp"),
                "p_sl": ev.get("p_sl"),
                "warning": meta.get("warning"),
            })
        results.sort(key=lambda r: (r["net_ev_bps"] is None, -(r["net_ev_bps"] or 0)))
        return results

    def to_dataframe(self) -> pd.DataFrame:
        """Return scenario sweep results as a DataFrame."""
        return pd.DataFrame(self.analyze_all_scenarios())

    @staticmethod
    def get_scenario_metadata(scenario_id: str) -> Dict[str, Any]:
        """Return metadata for a specific cost scenario."""
        if scenario_id not in COST_SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario_id}")
        return COST_SCENARIOS[scenario_id].copy()


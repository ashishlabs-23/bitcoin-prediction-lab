"""
models/mechanism_hypotheses.py — Market Mechanism Hypotheses Engine (Level 1)
=============================================================================
Implements the 5 core market mechanism hypotheses:
  1. IGNITION: Volatility transition / breakout from compression.
  2. ABSORPTION: Heavy aggressive order flow met with stationary price action.
  3. VACUUM: Order-book liquidity depletion triggering discontinuous jump dislocation.
  4. TOXICITY: Sustained toxic flow persistence with adverse queue depletion.
  5. COMBINED: Mechanism consensus orchestrator.

Evaluates Level 1 Event Validity:
  Tests whether event E_t induces a statistically and economically distinct
  conditional distribution P(Y | E_t) != P(Y).
"""

import os
import sys
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import pandas as pd
from scipy import stats


class MechanismDetector:
    """
    Detects market mechanism events from two-speed state representations.
    """

    def __init__(
        self,
        ignition_vol_shock: float = 1.5,
        absorption_flow_shock: float = 1.5,
        vacuum_spread_shock: float = 1.5,
        toxicity_vpin_shock: float = 1.5,
        funding_rate_shock: float = 1.8,
        hawkes_jump_shock: float = 1.8
    ):
        self.ignition_vol_shock = ignition_vol_shock
        self.absorption_flow_shock = absorption_flow_shock
        self.vacuum_spread_shock = vacuum_spread_shock
        self.toxicity_vpin_shock = toxicity_vpin_shock
        self.funding_rate_shock = funding_rate_shock
        self.hawkes_jump_shock = hawkes_jump_shock

    def detect_events(self, state_df: pd.DataFrame) -> pd.DataFrame:
        """
        Scans state DataFrame and produces binary event trigger columns for all mechanisms:
          - E_IGNITION (volatility compression breakout)
          - E_ABSORPTION (passive orderbook absorption)
          - E_VACUUM (liquidity depletion / spread jump)
          - E_TOXICITY (toxic flow / adverse selection)
          - E_FUNDING_SQUEEZE (perpetual funding rate / liquidation cascade)
          - E_HAWKES_JUMP (self-exciting jump point process acceleration)
          - E_COMBINED (consensus)
        """
        events = pd.DataFrame(index=state_df.index)

        # 1. IGNITION: Low prior vol (compression) followed by positive vol shock
        vol_pct = state_df.get("V_volatility_level_pct", pd.Series(0.5, index=state_df.index))
        vol_shock = state_df.get("V_volatility_shock", pd.Series(0.0, index=state_df.index))
        events["E_IGNITION"] = ((vol_pct.shift(1) < 0.40) & (vol_shock > self.ignition_vol_shock)).astype(int)

        # 2. ABSORPTION: Flow shock (high VPIN or high taker ratio shock) with low vol shock (price stall)
        flow_shock = state_df.get("F_taker_ratio_shock", pd.Series(0.0, index=state_df.index)).abs()
        events["E_ABSORPTION"] = ((flow_shock > self.absorption_flow_shock) & (vol_shock.abs() < 0.5)).astype(int)

        # 3. VACUUM: Severe spread shock + high volume/volatility shock
        spread_shock = state_df.get("L_spread_shock", pd.Series(0.0, index=state_df.index))
        events["E_VACUUM"] = ((spread_shock > self.vacuum_spread_shock) & (vol_shock > 1.0)).astype(int)

        # 4. TOXICITY: High VPIN shock or high VPIN persistence
        vpin_shock = state_df.get("F_vpin_shock", pd.Series(0.0, index=state_df.index))
        vpin_pers = state_df.get("F_vpin_persistence", pd.Series(0, index=state_df.index))
        events["E_TOXICITY"] = ((vpin_shock > self.toxicity_vpin_shock) | (vpin_pers >= 3)).astype(int)

        # 5. FUNDING_SQUEEZE: Extreme funding rate dislocation / over-leveraged crowding
        funding_shock = state_df.get("D_funding_shock", pd.Series(0.0, index=state_df.index)).abs()
        events["E_FUNDING_SQUEEZE"] = ((funding_shock > self.funding_rate_shock) | (state_df.get("D_funding_rate", pd.Series(0.0, index=state_df.index)).abs() > 0.0005)).astype(int)

        # 6. HAWKES_JUMP: Self-exciting point process jump acceleration
        hawkes_intensity = state_df.get("H_hawkes_intensity_shock", pd.Series(0.0, index=state_df.index))
        events["E_HAWKES_JUMP"] = (hawkes_intensity > self.hawkes_jump_shock).astype(int)

        # 7. COMBINED: Any mechanism active
        events["E_COMBINED"] = (
            events["E_IGNITION"] | events["E_ABSORPTION"] | events["E_VACUUM"] | 
            events["E_TOXICITY"] | events["E_FUNDING_SQUEEZE"] | events["E_HAWKES_JUMP"]
        ).astype(int)

        return events

    def test_event_validity_l1(
        self,
        events: pd.Series,
        forward_returns: pd.Series,
        min_events: int = 20
    ) -> Dict[str, Any]:
        """
        Level 1 Event Validity Test:
        Performs Kolmogorov-Smirnov and Mann-Whitney U tests to determine whether
        the conditional distribution P(R | E=1) statistically diverges from baseline P(R).
        """
        mask = events.astype(bool)
        n_events = int(mask.sum())

        if n_events < min_events:
            return {
                "valid_l1": False,
                "n_events": n_events,
                "reason": f"Insufficient event occurrences: {n_events} < {min_events}",
                "ks_pvalue": 1.0,
                "mwu_pvalue": 1.0,
                "conditional_vol_ratio": 1.0
            }

        r_cond = forward_returns[mask].dropna()
        r_uncond = forward_returns[~mask].dropna()

        if len(r_cond) < min_events or len(r_uncond) < min_events:
            return {
                "valid_l1": False,
                "n_events": n_events,
                "reason": "Insufficient return samples for statistical test",
                "ks_pvalue": 1.0,
                "mwu_pvalue": 1.0,
                "conditional_vol_ratio": 1.0
            }

        # 1. Kolmogorov-Smirnov test (distributional shape divergence)
        ks_stat, ks_pval = stats.ks_2samp(r_cond, r_uncond)

        # 2. Mann-Whitney U test (median / location shift)
        mwu_stat, mwu_pval = stats.mannwhitneyu(r_cond, r_uncond, alternative="two-sided")

        # 3. Volatility / tail ratio
        std_cond = float(r_cond.std())
        std_uncond = float(r_uncond.std()) if float(r_uncond.std()) > 0 else 1e-6
        vol_ratio = float(std_cond / std_uncond)

        # Statistical significance at alpha = 0.05
        is_significant = (ks_pval < 0.05) or (mwu_pval < 0.05) or (vol_ratio > 1.30 or vol_ratio < 0.75)

        return {
            "valid_l1": bool(is_significant),
            "n_events": n_events,
            "event_frequency_pct": round((n_events / len(events)) * 100.0, 2),
            "ks_statistic": round(float(ks_stat), 4),
            "ks_pvalue": round(float(ks_pval), 6),
            "mwu_pvalue": round(float(mwu_pval), 6),
            "mean_conditional_return": round(float(r_cond.mean()), 6),
            "mean_unconditional_return": round(float(r_uncond.mean()), 6),
            "conditional_vol_ratio": round(vol_ratio, 3)
        }

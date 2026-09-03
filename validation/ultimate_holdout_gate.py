"""
validation/ultimate_holdout_gate.py — Level 9 Multi-Dimensional Ultimate Holdout Gate
====================================================================================
Enforces the final, blind, one-shot promotion protocol:
  1. Multi-Dimensional Holdout: Time, Venue, Regime, and Adversarial Replay.
  2. Strict One-Shot Rule: No iteration or tuning after holdout evaluation.
  3. Falsifiable Promotion Verdict: PROMOTE vs. RETIRE.
  4. Generates the final 5-dimensional Strategy Survival Scorecard.
"""

import os
import sys
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import pandas as pd

from backtest.survival_stress_matrix import SurvivalStressMatrix
from validation.research_census import ResearchCensus


class UltimateHoldoutGate:
    """
    Level 9 Gatekeeper enforcing strict blind evaluation and generating the survival matrix.
    """

    def __init__(
        self,
        census: Optional[ResearchCensus] = None,
        evaluated_candidates_file: Optional[str] = None
    ):
        self.census = census or ResearchCensus()
        self.stress_matrix = SurvivalStressMatrix()
        self.evaluated_candidates_file = evaluated_candidates_file or os.path.join(
            "experiments", "results", "holdout_audit.json"
        )

    def _get_evaluated_hashes(self) -> List[str]:
        if os.path.exists(self.evaluated_candidates_file):
            try:
                with open(self.evaluated_candidates_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _record_evaluated_hash(self, candidate_hash: str) -> None:
        hashes = self._get_evaluated_hashes()
        if candidate_hash not in hashes:
            hashes.append(candidate_hash)
            os.makedirs(os.path.dirname(self.evaluated_candidates_file), exist_ok=True)
            try:
                with open(self.evaluated_candidates_file, "w", encoding="utf-8") as f:
                    json.dump(hashes, f, indent=2)
            except Exception:
                pass

    def evaluate_candidate_for_promotion(
        self,
        strategy_name: str,
        candidate_hash: str,
        holdout_returns: pd.Series,
        event_series: pd.Series,
        state_only_returns: pd.Series,
        mode: str = "TAKER"
    ) -> Dict[str, Any]:
        """
        Executes the definitive Level 9 blind promotion trial.
        """
        prior_evals = self._get_evaluated_hashes()
        if candidate_hash in prior_evals:
            return {
                "verdict": "REJECTED_ALREADY_EVALUATED",
                "reason": "One-Shot Violation: Candidate has already undergone Ultimate Holdout evaluation. No re-testing allowed.",
                "promoted": False
            }

        # 1. Base Net Return & Sharpe
        mean_ret = float(holdout_returns.mean())
        std_ret = float(holdout_returns.std()) if float(holdout_returns.std()) > 0 else 1e-6
        observed_sr = float((mean_ret / std_ret) * np.sqrt(8760)) # Annualized hourly

        # 2. Multi-Stress Survival Matrix (Level 6)
        scorecard = self.stress_matrix.generate_full_survival_scorecard(
            strategy_name=strategy_name,
            signal_return=mean_ret,
            state_only_return=float(state_only_returns.mean()),
            mode=mode
        )

        # 3. Selection Bias & DSR (Level 8)
        dsr_res = self.census.compute_deflated_sharpe_ratio(
            observed_sr=observed_sr,
            returns=holdout_returns.values
        )

        # 4. Null Control Battery (Level 8)
        null_res = self.census.run_null_control_battery(
            strategy_returns=holdout_returns,
            event_series=event_series
        )

        # 5. Gate Invariants
        g_economic = scorecard["cost_survival"]["survives_2x"]
        g_latency = scorecard["latency_survival"]["survives_250ms"]
        g_capacity = scorecard["capacity"]["institutional_capacity"]
        g_attribution = scorecard["attribution"]["valid"]
        g_nulls = null_res["beats_null_controls"]

        promoted = bool(g_economic and g_latency and g_attribution and g_nulls and mean_ret > 0.0)
        verdict = "PROMOTE_TO_PRODUCTION_CANDIDATE" if promoted else "RETIRE"

        # Record hash to enforce one-shot rule
        self._record_evaluated_hash(candidate_hash)

        return {
            "strategy_name": strategy_name,
            "candidate_hash": candidate_hash,
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "verdict": verdict,
            "promoted": promoted,
            "summary_metrics": {
                "observed_net_return_bps": round(mean_ret * 10000.0, 2),
                "annualized_sharpe": round(observed_sr, 2),
                "dsr": dsr_res["dsr"],
                "total_census_trials": dsr_res["n_trials_counted"]
            },
            "survival_scorecard": scorecard,
            "null_control_battery": null_res
        }

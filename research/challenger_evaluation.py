"""
research/challenger_evaluation.py — 8-Criteria Challenger Evaluation & Promotion Gate
====================================================================================
Formalizes the 8-point promotion gate for offline model candidates:
1. MFE Error Superiority (MAE)
2. MAE Error Superiority (MAE)
3. Quantile Pinball Loss
4. Single-Sided P90 Coverage Calibration
5. Joint Full-Path Containment (Target >= 78.87%)
6. Interval Sharpness (Winkler Score / Range Width)
7. Market Regime Invariance
8. Volatility Tier Invariance

Outputs formal promotion/rejection verdict.
"""

import os
import sys
import logging
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.challenger_registry import challenger_registry

logger = logging.getLogger("ChallengerEvaluation")


class ChallengerEvaluator:
    """
    Evaluates candidate models against production baseline across 8 strict criteria.
    """

    def evaluate_candidate(
        self,
        candidate_version: str,
        cand_mfe_error: float,
        cand_mae_error: float,
        cand_pinball_loss: float,
        cand_p90_cov: float,
        cand_path_cov: float,
        cand_width: float,
        cand_regime_stable: bool,
        cand_vol_stable: bool
    ) -> Dict[str, Any]:
        prod = challenger_registry.get_production_model()
        prod_metrics = prod.validation_metrics if prod else {}

        prod_mfe_err = float(prod_metrics.get("mfe_error", 0.4120))
        prod_path_cov = float(prod_metrics.get("joint_path_containment", 90.32))
        prod_width = float(prod_metrics.get("mean_width", 5.92))

        gate_results = [
            {"Criterion": "1. MFE Error Superiority", "Requirement": f"< {prod_mfe_err:.4f}%", "Candidate Value": f"{cand_mfe_error:.4f}%", "Pass": cand_mfe_error <= prod_mfe_err},
            {"Criterion": "2. MAE Error Superiority", "Requirement": "< 0.6000%", "Candidate Value": f"{cand_mae_error:.4f}%", "Pass": cand_mae_error <= 0.6000},
            {"Criterion": "3. Quantile Pinball Loss", "Requirement": "< 0.0500", "Candidate Value": f"{cand_pinball_loss:.4f}", "Pass": cand_pinball_loss <= 0.0500},
            {"Criterion": "4. Single-Sided P90 Coverage", "Requirement": ">= 88.0%", "Candidate Value": f"{cand_p90_cov:.1f}%", "Pass": cand_p90_cov >= 88.0},
            {"Criterion": "5. Joint Path Containment", "Requirement": ">= 78.87%", "Candidate Value": f"{cand_path_cov:.1f}%", "Pass": cand_path_cov >= 78.87},
            {"Criterion": "6. Interval Sharpness", "Requirement": f"<= {prod_width:.2f}%", "Candidate Value": f"{cand_width:.2f}%", "Pass": cand_width <= prod_width},
            {"Criterion": "7. Regime Stability", "Requirement": "Stable across all regimes", "Candidate Value": "Verified" if cand_regime_stable else "Failed", "Pass": cand_regime_stable},
            {"Criterion": "8. Volatility Stability", "Requirement": "Stable across all tiers", "Candidate Value": "Verified" if cand_vol_stable else "Failed", "Pass": cand_vol_stable}
        ]
        df_gates = pd.DataFrame(gate_results)
        all_passed = all(r["Pass"] for r in gate_results)

        verdict = "PROMOTE_TO_PRODUCTION" if all_passed else "REJECT_MAINTAIN_CURRENT_PRODUCTION"

        return {
            "candidate_version": candidate_version,
            "gate_matrix": df_gates,
            "all_passed": all_passed,
            "promotion_verdict": verdict
        }


challenger_evaluator = ChallengerEvaluator()

"""
tests/test_challenger_registry.py — Unit Tests for Challenger Registry & Promotion Gate
========================================================================================
Verifies:
1. Challenger registry retrieval and model status queries
2. 8-criteria challenger evaluation gate logic
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.challenger_registry import challenger_registry, ModelRegistryEntry
from research.challenger_evaluation import challenger_evaluator


def test_challenger_registry_retrieval():
    prod = challenger_registry.get_production_model()
    assert isinstance(prod, ModelRegistryEntry)
    assert prod.deployment_status == "PRODUCTION"
    assert prod.version == "v3.0.0-excursion-ridge-conformal"

    all_models = challenger_registry.list_all_models()
    assert len(all_models) >= 3


def test_challenger_promotion_gate_rejection_on_higher_error():
    result = challenger_evaluator.evaluate_candidate(
        candidate_version="v3.9.0-test-weak",
        cand_mfe_error=0.6500,  # Worse than production 0.4120
        cand_mae_error=0.6200,
        cand_pinball_loss=0.0600,
        cand_p90_cov=82.0,
        cand_path_cov=70.0,
        cand_width=7.50,
        cand_regime_stable=True,
        cand_vol_stable=True
    )

    assert result["all_passed"] is False
    assert result["promotion_verdict"] == "REJECT_MAINTAIN_CURRENT_PRODUCTION"

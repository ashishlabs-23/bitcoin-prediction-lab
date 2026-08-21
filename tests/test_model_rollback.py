"""
tests/test_model_rollback.py — Unit Tests for Production Model Rollback Simulation
==================================================================================
Verifies:
1. Rollback simulation: Production -> Challenger Promoted -> Failure -> Rollback
2. Preserves database history and restores previous production model safely
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.challenger_registry import ChallengerRegistry


def test_production_model_rollback_simulation():
    reg = ChallengerRegistry()

    # Register candidate & promote to production
    reg.register_candidate(
        model_id="risky_candidate",
        version="v3.8.0-risky-candidate",
        model_name="Risky Candidate Model",
        training_period="2024-2025",
        feature_schema=["vol_24h"],
        target_definition="24h MFE",
        calibration_method="Conformal",
        validation_metrics={"mfe_error": 0.4000}
    )
    reg.promote_to_challenger("v3.8.0-risky-candidate", "Promoted to challenger")
    new_prod = reg.promote_to_production("v3.8.0-risky-candidate", "Promoted to production")
    assert new_prod.version == "v3.8.0-risky-candidate"

    # Simulate production degradation and rollback
    restored_prod = reg.rollback(reason="Observed live coverage degradation.")
    assert restored_prod is not None
    assert restored_prod.version == "v3.0.0-excursion-ridge-conformal"
    assert restored_prod.deployment_status == "PRODUCTION"

    # Check that failed version is retired
    failed_entry = reg.get_model("v3.8.0-risky-candidate")
    assert failed_entry.deployment_status == "RETIRED"

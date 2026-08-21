"""
tests/test_model_registry.py — Unit Tests for Model Registry Lifecycle Operations
=================================================================================
Verifies:
1. Registration of candidates
2. Promotion to challenger and production
3. Audit logging of state transitions
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.challenger_registry import ChallengerRegistry, ModelRegistryEntry


def test_model_registry_lifecycle_flow():
    reg = ChallengerRegistry()

    # 1. Register candidate
    entry = reg.register_candidate(
        model_id="test_candidate",
        version="v3.9.9-test",
        model_name="Test Model",
        training_period="2024-2025",
        feature_schema=["vol_24h"],
        target_definition="24h MFE",
        calibration_method="Conformal",
        validation_metrics={"mfe_error": 0.4000}
    )
    assert entry.deployment_status == "CANDIDATE"

    # 2. Promote to challenger
    chal = reg.promote_to_challenger("v3.9.9-test", "Passed initial screen.")
    assert chal is not None
    assert chal.deployment_status == "CHALLENGER"

    # 3. Promote to production
    prod = reg.promote_to_production("v3.9.9-test", "Passed 8-point promotion gate.")
    assert prod is not None
    assert prod.deployment_status == "PRODUCTION"
    assert prod.rollback_target == "v3.0.0-excursion-ridge-conformal"

    # 4. Check audit log
    history = reg.get_model_history()
    assert len(history) >= 3

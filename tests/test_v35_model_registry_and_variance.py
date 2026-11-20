"""V35.3: Model Registry Identity, Baseline Demotion, and Non-Negative Variance Floor Tests."""
import numpy as np
import pytest
from models.authoritative_model_registry import (
    ModelClassification,
    AuthorizationStatus,
    get_active_baseline_model,
    get_active_production_model,
    get_model_identity,
    list_authoritative_models,
)
from models.challengers.har_qlike_24h_challenger import (
    ConventionalHAR24H,
    HARQLIKE24HChallenger,
)


def test_active_baseline_model_is_standard_har():
    """Verify Standard-HAR-v1.0 is registered as ACTIVE_BASELINE_MODEL."""
    base = get_active_baseline_model()
    assert base.canonical_id == "Standard-HAR-v1.0"
    assert base.classification == ModelClassification.BASELINE_VOLATILITY
    assert base.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY
    assert not base.directional_prediction_capability


def test_har_rs_dow_demoted_to_unpromoted_challenger():
    """Verify HAR-RS-DOW-v1.0 is demoted to unpromoted research challenger."""
    dow = get_model_identity("HAR-RS-DOW-v1.0")
    assert dow is not None
    assert dow.classification == ModelClassification.RESEARCH_CHALLENGER_UNPROMOTED
    assert dow.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY
    assert "0.2632" in dow.output_interpretation or "0.2632" in dow.empirical_validation_summary


def test_backward_compatible_production_alias():
    """Verify get_active_production_model returns baseline with offline research status."""
    prod = get_active_production_model()
    assert prod.canonical_id == "Standard-HAR-v1.0"
    assert prod.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY


def test_non_negative_variance_floor_conventional_har():
    """Verify ConventionalHAR24H.predict never outputs values <= 0, NaN, or Inf even under extreme inputs."""
    model = ConventionalHAR24H()
    # Mock fitted beta with extreme negative weights
    model.beta = np.array([-50.0, -20.0, -15.0, -10.0])
    model.intercept = -50.0

    X_extreme = np.array([
        [100.0, 50.0, 20.0],
        [-100.0, -50.0, -20.0],
        [0.0, 0.0, 0.0],
        [1e6, 1e6, 1e6],
    ])

    preds = model.predict(X_extreme)
    assert len(preds) == 4
    assert np.all(preds > 0.0)
    assert np.all(preds >= 1e-6)
    assert not np.any(np.isnan(preds))
    assert not np.any(np.isinf(preds))


def test_non_negative_variance_floor_har_qlike():
    """Verify HARQLIKE24HChallenger.predict never collapses <= 0."""
    model = HARQLIKE24HChallenger()
    model.beta = np.array([-30.0, -10.0, -5.0, -2.0])
    model.intercept = -30.0

    X_test = np.random.randn(100, 3) * 50.0
    preds = model.predict(X_test)
    assert len(preds) == 100
    assert np.all(preds >= 1e-6)
    assert not np.any(np.isnan(preds))


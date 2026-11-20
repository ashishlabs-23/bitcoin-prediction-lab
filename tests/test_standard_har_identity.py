import pytest

from models.authoritative_model_registry import (
    ArtifactStatus,
    AuthorizationStatus,
    ModelClassification,
    ModelArtifactUnavailableError,
    get_active_baseline_model,
    get_active_production_model,
    get_model_identity,
    is_production_authorized,
    resolve_model_artifact_path,
)


def test_standard_har_identity_is_registered_but_artifact_is_blocked():
    model = get_active_baseline_model()

    assert model.canonical_id == "Standard-HAR-v1.0"
    assert model.classification == ModelClassification.BASELINE_VOLATILITY
    assert model.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY
    assert model.artifact_status == ArtifactStatus.UNAVAILABLE_BLOCKED
    assert model.artifact_rel_path == "experiments/results/freeze/standard_har_v1.joblib"
    assert model.artifact_sha256 is None
    assert model.scientific_contract_hash is None
    assert "unavailable" in model.empirical_validation_summary.lower()
    assert get_active_production_model().authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY
    assert is_production_authorized() is False


def test_standard_har_serialized_identity_does_not_claim_verified_digests():
    record = get_model_identity("Standard-HAR-v1.0")
    assert record is not None

    serialized = record.to_dict()
    assert serialized["artifact_status"] == "UNAVAILABLE_BLOCKED"
    assert serialized["artifact_sha256"] is None
    assert serialized["scientific_contract_hash"] is None


def test_unavailable_standard_har_is_rejected_before_artifact_filesystem_lookup(monkeypatch):
    def forbidden_filesystem_lookup(*args, **kwargs):
        raise AssertionError("Blocked model artifact must not be accessed.")

    monkeypatch.setattr("models.authoritative_model_registry.os.path.isfile", forbidden_filesystem_lookup)

    with pytest.raises(ModelArtifactUnavailableError, match="not verified and available"):
        resolve_model_artifact_path("Standard-HAR-v1.0")


def test_har_rs_dow_remains_separate_unpromoted_challenger():
    model = get_model_identity("HAR-RS-DOW-v1.0")

    assert model is not None
    assert model.classification == ModelClassification.RESEARCH_CHALLENGER_UNPROMOTED
    assert model.authorization_status == AuthorizationStatus.OFFLINE_RESEARCH_ONLY
    assert model.artifact_rel_path == "experiments/results/freeze/har_rs_dow_v1.joblib"
    assert model.artifact_sha256 is not None

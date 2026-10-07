import json
from pathlib import Path

from research.entry_tp_sl.environment_fingerprint import build_fingerprint

TRACK_ROOT = Path(__file__).resolve().parents[2] / "research" / "entry_tp_sl"


def test_environment_lock_has_exact_pins_and_hashes():
    lock_text = (TRACK_ROOT / "requirements.lock").read_text(encoding="utf-8")
    assert "--require-hashes" in lock_text
    for package, version in {
        "numpy": "2.3.2",
        "pandas": "3.0.5",
        "lightgbm": "4.7.0",
        "scikit-learn": "1.9.0",
        "pytest": "8.4.1",
    }.items():
        assert f"{package}=={version} --hash=sha256:" in lock_text


def test_snapshot_template_fails_closed_without_a_real_file():
    manifest = json.loads((TRACK_ROOT / "dataset_manifest.template.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "DATA_UNAVAILABLE"
    assert manifest["availability"]["local_snapshot_present"] is False
    assert manifest["availability"]["sha256"] is None
    assert manifest["storage"]["selected_backend"] is None
    assert manifest["exclusions"] == {
        "har_ohlcv_reused": False,
        "iv7d_used": False,
        "har_artifacts_used": False,
    }


def test_manifest_schemas_and_failure_states_are_declared():
    import jsonschema

    dataset_schema = json.loads((TRACK_ROOT / "schemas" / "dataset_manifest.schema.json").read_text(encoding="utf-8"))
    provenance_schema = json.loads((TRACK_ROOT / "schemas" / "provenance.schema.json").read_text(encoding="utf-8"))
    dataset_template = json.loads((TRACK_ROOT / "dataset_manifest.template.json").read_text(encoding="utf-8"))
    provenance_template = json.loads((TRACK_ROOT / "provenance.template.json").read_text(encoding="utf-8"))
    statuses = provenance_schema["properties"]["status"]["enum"]

    jsonschema.Draft202012Validator.check_schema(dataset_schema)
    jsonschema.Draft202012Validator.check_schema(provenance_schema)
    jsonschema.validate(dataset_template, dataset_schema)
    jsonschema.validate(provenance_template, provenance_schema)
    assert dataset_schema["properties"]["track_id"]["const"] == "BTC-ENTRY-TP-SL-V3"
    assert dataset_schema["properties"]["bars"]["properties"]["decision_interval_seconds"]["const"] == 900
    assert dataset_schema["properties"]["bars"]["properties"]["path_interval_seconds"]["maximum"] == 60
    assert {"PROVENANCE_FAILURE", "DATA_UNAVAILABLE", "MODEL_FAILURE", "NO_SIGNAL"}.issubset(statuses)


def test_environment_fingerprint_is_deterministic():
    first = build_fingerprint()
    second = build_fingerprint()
    assert first["environment_sha256"] == second["environment_sha256"]
    assert set(first["inputs_sha256"]) == {
        ".python-version",
        "requirements.in",
        "requirements.lock",
        "runtime.env",
        "environment_fingerprint.py",
    }
    assert first["python_expected"] == "3.13.14"
    assert first["status"] == "READY"

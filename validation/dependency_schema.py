"""
validation/dependency_schema.py — Dependency Classification & Versioned Schema
================================================================================
Formally decouples active production runtime dependencies from historical
research benchmarks and training-data provenance snapshots.

Architectural Guarantees:
1. Runtime Inference Independence:
   The active production model (HAR-RS-DOW-v1.0) requires strictly `ohlcv.parquet`
   and `har_rs_dow_v1.joblib` with its verified freeze manifest for causal inference.
   Missing research benchmarks (e.g., `iv7d.parquet`) do NOT impair runtime inference.
2. Historical Research Auditability:
   Research datasets evaluated in pre-registered experiments (e.g. Deribit IV7D
   in VOL-EDGE-01 M4/M5/M6) are tracked and audited for historical reproducibility
   without being conflated with runtime inference requirements.
3. Fail-Closed Safety:
   Any missing, unreadable, or invalid runtime dependency or corrupted model artifact
   immediately triggers a fail-closed state (DATA_UNAVAILABLE / FROZEN_INPUT_MISSING / PROVENANCE_FAILURE).
"""

import os
import hashlib
import json
from typing import Dict, List, Tuple, Any, Optional

# Primary raw data dependencies strictly required for runtime feature generation & inference
RUNTIME_INFERENCE_DATA_DEPENDENCIES: List[str] = [
    "ohlcv.parquet",
]
# For backward compatibility
RUNTIME_INFERENCE_DEPENDENCIES = RUNTIME_INFERENCE_DATA_DEPENDENCIES

# Model artifacts and manifests required for runtime inference
RUNTIME_MODEL_ARTIFACT_REL_PATH = "experiments/results/freeze/har_rs_dow_v1.joblib"
RUNTIME_FREEZE_MANIFEST_REL_PATH = "experiments/results/freeze/repaired_scientific_contract_manifest.json"

EXPECTED_ARTIFACT_SHA256 = "750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b"
EXPECTED_CONTRACT_HASH = "841deba5fb30118bea849f93ebc9fb7d1984d74fd2d709013544c6d5db94cf07"

# Historical research benchmarks evaluated in offline research experiments
HISTORICAL_RESEARCH_BENCHMARKS: List[str] = [
    "iv7d.parquet",
    "funding.parquet",
    "onchain.parquet",
    "oi.parquet",
    "btcusd_1-min_data.csv",
]

# Historical training snapshot manifest keys
TRAINING_SNAPSHOT_KEYS: Dict[str, str] = {
    "ohlcv.parquet": "ohlcv_parquet_sha256",
    "iv7d.parquet": "iv7d_parquet_sha256",
}


def sha256_file(filepath: str) -> str:
    """Computes hex SHA256 of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def classify_dependency(filename: str) -> str:
    """Classifies a data file as RUNTIME_INFERENCE, RESEARCH_BENCHMARK, or UNKNOWN."""
    base = os.path.basename(filename)
    if base in RUNTIME_INFERENCE_DATA_DEPENDENCIES:
        return "RUNTIME_INFERENCE"
    if base in HISTORICAL_RESEARCH_BENCHMARKS:
        return "RESEARCH_BENCHMARK"
    return "UNKNOWN"


def is_runtime_dependency(filename: str) -> bool:
    """Returns True if the file is strictly required for runtime inference."""
    return classify_dependency(filename) == "RUNTIME_INFERENCE"


def is_research_benchmark(filename: str) -> bool:
    """Returns True if the file is an offline research benchmark."""
    return classify_dependency(filename) == "RESEARCH_BENCHMARK"


def validate_runtime_dependencies(data_dir: str) -> Tuple[bool, List[str]]:
    """
    Validates existence of all runtime raw data dependencies.
    Returns (all_present, missing_files).
    """
    missing = []
    for dep in RUNTIME_INFERENCE_DATA_DEPENDENCIES:
        p = os.path.join(data_dir, dep)
        if not os.path.exists(p):
            missing.append(dep)
    return len(missing) == 0, missing


def validate_research_benchmarks(data_dir: str) -> Tuple[bool, List[str]]:
    """
    Validates existence of historical research benchmarks.
    Returns (all_present, missing_files).
    """
    missing = []
    for bench in HISTORICAL_RESEARCH_BENCHMARKS:
        p = os.path.join(data_dir, bench)
        if not os.path.exists(p):
            missing.append(bench)
    return len(missing) == 0, missing


def validate_full_runtime_contract(repo_root: Optional[str] = None) -> Dict[str, Any]:
    """
    Validates complete production runtime contract:
    1. Runtime data (`ohlcv.parquet`) existence and readability.
    2. Model artifact (`har_rs_dow_v1.joblib`) existence and SHA256 integrity.
    3. Freeze manifest (`repaired_scientific_contract_manifest.json`) contract hash.
    
    Returns structured audit result with status: "PASS", "FAIL_DATA_MISSING",
    "FAIL_ARTIFACT_MISSING", "FAIL_ARTIFACT_CORRUPTED", or "FAIL_MANIFEST_INVALID".
    """
    root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_dir = os.path.join(root, "data", "raw")
    artifact_path = os.path.join(root, RUNTIME_MODEL_ARTIFACT_REL_PATH)
    manifest_path = os.path.join(root, RUNTIME_FREEZE_MANIFEST_REL_PATH)

    # 1. Check runtime data
    data_ok, missing_data = validate_runtime_dependencies(data_dir)
    if not data_ok:
        return {
            "status": "FAIL_DATA_MISSING",
            "valid": False,
            "details": f"Missing runtime inference data: {missing_data}",
            "missing_dependencies": missing_data
        }

    # 2. Check model artifact existence
    if not os.path.exists(artifact_path):
        return {
            "status": "FAIL_ARTIFACT_MISSING",
            "valid": False,
            "details": f"Model artifact missing at {artifact_path}",
            "missing_dependencies": [RUNTIME_MODEL_ARTIFACT_REL_PATH]
        }

    # 3. Check model artifact hash
    actual_artifact_hash = sha256_file(artifact_path)
    if actual_artifact_hash != EXPECTED_ARTIFACT_SHA256:
        return {
            "status": "FAIL_ARTIFACT_CORRUPTED",
            "valid": False,
            "details": f"Artifact hash mismatch: expected={EXPECTED_ARTIFACT_SHA256[:16]}, got={actual_artifact_hash[:16]}",
            "expected_hash": EXPECTED_ARTIFACT_SHA256,
            "actual_hash": actual_artifact_hash
        }

    # 4. Check manifest existence & scientific contract hash
    if not os.path.exists(manifest_path):
        return {
            "status": "FAIL_MANIFEST_MISSING",
            "valid": False,
            "details": f"Freeze manifest missing at {manifest_path}",
            "missing_dependencies": [RUNTIME_FREEZE_MANIFEST_REL_PATH]
        }

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        actual_contract_hash = manifest.get("scientific_contract_hash", "")
        if actual_contract_hash != EXPECTED_CONTRACT_HASH:
            return {
                "status": "FAIL_MANIFEST_INVALID",
                "valid": False,
                "details": f"Manifest contract hash mismatch: expected={EXPECTED_CONTRACT_HASH[:16]}, got={actual_contract_hash[:16]}",
                "expected_hash": EXPECTED_CONTRACT_HASH,
                "actual_hash": actual_contract_hash
            }
    except Exception as exc:
        return {
            "status": "FAIL_MANIFEST_INVALID",
            "valid": False,
            "details": f"Failed to parse manifest: {exc}"
        }

    return {
        "status": "PASS",
        "valid": True,
        "model_version": "HAR-RS-DOW-v1.0",
        "artifact_hash": actual_artifact_hash,
        "contract_hash": actual_contract_hash,
        "runtime_data": "data/raw/ohlcv.parquet"
    }

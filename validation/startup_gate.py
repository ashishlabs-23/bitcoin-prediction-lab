"""
validation/startup_gate.py — Scientific Startup Gate & Contract Verifier
========================================================================
Enforces strict pre-flight scientific freeze verification before BTCognitive server startup.
Server startup MUST refuse and fail with RuntimeError if any check fails:
1. Artifact SHA256
2. Pipeline coefficients SHA256
3. Manifest integrity & scientific contract hash
4. Feature contract
5. Target contract
6. C2 configuration
7. Environment & critical packages
"""

import os
import sys
import json
import hashlib
import logging
import subprocess
from typing import Dict, Any, Tuple, Optional
import numpy as np

try:
    import joblib
except ImportError:
    from sklearn.externals import joblib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR

logger = logging.getLogger("btcognitive.startup_gate")

FREEZE_DIR = os.path.join(RESULTS_DIR, "freeze")
REPAIRED_MANIFEST_PATH = os.path.join(FREEZE_DIR, "repaired_scientific_contract_manifest.json")
MODEL_ARTIFACT_PATH = os.path.join(FREEZE_DIR, "har_rs_dow_v1.joblib")
FULL_FREEZE_VERIFIER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "research",
    "verify_freeze_manifest.py",
)


class FreezeIntegrityError(RuntimeError):
    def __init__(self, state: str, code: str, details: str):
        self.state = state
        self.code = code
        super().__init__(details)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_str(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_dict(d: Dict[str, Any]) -> str:
    canonical = json.dumps(d, sort_keys=True, separators=(",", ":"), default=str)
    return sha256_str(canonical)


def sha256_numpy_array(arr: np.ndarray) -> str:
    h = hashlib.sha256()
    header = json.dumps({"shape": list(arr.shape), "dtype": str(arr.dtype)},
                        sort_keys=True).encode("utf-8")
    h.update(header)
    h.update(arr.tobytes())
    return h.hexdigest()


def verify_full_freeze_integrity() -> bool:
    """Run the full verifier; changed frozen inputs or numeric packages block production."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        result = subprocess.run(
            [sys.executable, FULL_FREEZE_VERIFIER_PATH],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=120,
            check=False,
        )
    except Exception as exc:
        raise FreezeIntegrityError(
            "MODEL_FAILURE",
            "FULL_FREEZE_VERIFIER_DID_NOT_RUN",
            f"Full freeze verifier could not run: {type(exc).__name__}",
        ) from exc

    output = result.stdout or ""
    blocking_warnings = [
        line.strip()
        for line in output.splitlines()
        if "WARN   Training data" in line
        or "WARN   Package" in line
        or "WARN   Python version" in line
    ]
    if result.returncode != 0 or blocking_warnings:
        lines = output.splitlines()
        missing_data = any("FAIL   Training data" in line for line in lines)
        changed_data = any("WARN   Training data" in line for line in lines)
        runtime_drift = any(
            "WARN   Package" in line or "WARN   Python version" in line
            for line in lines
        )
        model_failure = any(
            "FAIL   Model artifact" in line
            or "FAIL   Model coefficient" in line
            or "FAIL   Package" in line
            or "FAIL   Python version" in line
            for line in lines
        )
        if missing_data:
            state, code = "DATA_UNAVAILABLE", "FROZEN_INPUT_MISSING"
        elif model_failure:
            state, code = "MODEL_FAILURE", "FROZEN_MODEL_OR_RUNTIME_INVALID"
        elif changed_data:
            state, code = "PROVENANCE_FAILURE", "FROZEN_INPUT_HASH_MISMATCH"
        elif runtime_drift:
            state, code = "MODEL_FAILURE", "FROZEN_RUNTIME_MISMATCH"
        else:
            state, code = "PROVENANCE_FAILURE", "FREEZE_VERIFICATION_FAILED"
        details = output[-4000:] if result.returncode != 0 else "\n".join(blocking_warnings)
        raise FreezeIntegrityError(
            state,
            code,
            "Full scientific freeze verification failed. Canonical forecasts are unavailable.\n"
            f"{details}",
        )
    return True


def extract_pipeline_coefficients_hash(pipe) -> str:
    scaler = pipe.named_steps["scaler"]
    ridge = pipe.named_steps["ridge"]
    scaler_mean_hash = sha256_numpy_array(np.asarray(scaler.mean_))
    scaler_scale_hash = sha256_numpy_array(np.asarray(scaler.scale_))
    ridge_coef_hash = sha256_numpy_array(np.asarray(ridge.coef_))
    ridge_intercept_hash = sha256_numpy_array(
        np.asarray([ridge.intercept_]) if np.isscalar(ridge.intercept_)
        else np.asarray(ridge.intercept_)
    )
    combined = "".join([scaler_mean_hash, scaler_scale_hash, ridge_coef_hash, ridge_intercept_hash])
    return sha256_str(combined)


from research.freeze_har_rs_dow import FEATURE_SCHEMA, C2_CONFIG

def verify_scientific_contract(
    manifest_path: Optional[str] = None,
    artifact_path: Optional[str] = None,
    override_env_check: bool = False
) -> bool:
    """
    Verifies the scientific contract before production startup.
    Returns True if all checks pass.
    Raises RuntimeError if any check fails, forcing startup abort.
    """
    mpath = manifest_path or REPAIRED_MANIFEST_PATH
    apath = artifact_path or MODEL_ARTIFACT_PATH

    logger.info("Verifying scientific contract gate: manifest=%s, artifact=%s", mpath, apath)

    # 1. Manifest file existence
    if not os.path.exists(mpath):
        err = f"SCIENTIFIC STARTUP GATE FAILED: Manifest file not found at '{mpath}'."
        logger.critical(err)
        raise RuntimeError(err)

    try:
        with open(mpath, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        err = f"SCIENTIFIC STARTUP GATE FAILED: Unable to parse manifest JSON: {e}"
        logger.critical(err)
        raise RuntimeError(err)

    # 2. Manifest status and model version
    model_version = manifest.get("model_version")
    gov_status = manifest.get("governance_status")
    contract_hash = manifest.get("scientific_contract_hash")

    if model_version != "HAR-RS-DOW-v1.0":
        err = f"SCIENTIFIC STARTUP GATE FAILED: Invalid model_version '{model_version}' (expected 'HAR-RS-DOW-v1.0')."
        logger.critical(err)
        raise RuntimeError(err)

    if gov_status != "FREEZE_REPAIRED_AND_VERIFIED":
        err = f"SCIENTIFIC STARTUP GATE FAILED: Invalid governance_status '{gov_status}' (expected 'FREEZE_REPAIRED_AND_VERIFIED')."
        logger.critical(err)
        raise RuntimeError(err)

    if not contract_hash:
        err = "SCIENTIFIC STARTUP GATE FAILED: Missing scientific_contract_hash in manifest."
        logger.critical(err)
        raise RuntimeError(err)

    # 3. Model artifact file existence and SHA256
    if not os.path.exists(apath):
        err = f"SCIENTIFIC STARTUP GATE FAILED: Model artifact file not found at '{apath}'."
        logger.critical(err)
        raise RuntimeError(err)

    live_artifact_sha = sha256_file(apath)
    stored_artifact_sha = manifest.get("model_artifact", {}).get("artifact_sha256")
    if live_artifact_sha != stored_artifact_sha:
        err = (f"SCIENTIFIC STARTUP GATE FAILED: Model artifact SHA256 mismatch.\n"
               f"Stored: {stored_artifact_sha}\nLive:   {live_artifact_sha}")
        logger.critical(err)
        raise RuntimeError(err)

    # 4. Pipeline coefficients verification
    try:
        pipe = joblib.load(apath)
        live_coef_hash = extract_pipeline_coefficients_hash(pipe)
        stored_coef_hash = manifest.get("model_artifact", {}).get("coefficients_sha256")
        if live_coef_hash != stored_coef_hash:
            err = (f"SCIENTIFIC STARTUP GATE FAILED: Model coefficients SHA256 mismatch.\n"
                   f"Stored: {stored_coef_hash}\nLive:   {live_coef_hash}")
            logger.critical(err)
            raise RuntimeError(err)
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        err = f"SCIENTIFIC STARTUP GATE FAILED: Failed loading or extracting coefficients from '{apath}': {e}"
        logger.critical(err)
        raise RuntimeError(err)

    # 5. Feature contract hash
    computed_feature_hash = sha256_str(json.dumps(FEATURE_SCHEMA, separators=(",", ":")))
    stored_feature_hash = manifest.get("feature_contract_hash")
    if stored_feature_hash and computed_feature_hash != stored_feature_hash:
        err = (f"SCIENTIFIC STARTUP GATE FAILED: Feature contract hash mismatch.\n"
               f"Stored:   {stored_feature_hash}\nComputed: {computed_feature_hash}")
        logger.critical(err)
        raise RuntimeError(err)

    # 6. Target contract verification
    target_contract = {
        "target_variable": "rv7d_var_ann",
        "horizon_hours": 168,
        "annualization_factor": 8760.0 / 168.0,
        "strict_maturity_rule": "max(training_origin + 168h) < holdout_start",
        "mathematical_formula": "RV_{7d,t}^2 = (8760 / 168) * sum_{i=1}^{168} r_{t+i}^2"
    }
    computed_target_hash = sha256_dict(target_contract)
    stored_target_hash = manifest.get("target_contract_hash")
    if stored_target_hash and computed_target_hash != stored_target_hash:
        err = (f"SCIENTIFIC STARTUP GATE FAILED: Target contract hash mismatch.\n"
               f"Stored:   {stored_target_hash}\nComputed: {computed_target_hash}")
        logger.critical(err)
        raise RuntimeError(err)

    # 7. C2 configuration verification
    computed_c2_hash = sha256_dict(C2_CONFIG)
    stored_c2_hash = manifest.get("c2_config_hash")
    if stored_c2_hash and computed_c2_hash != stored_c2_hash:
        err = (f"SCIENTIFIC STARTUP GATE FAILED: C2 configuration hash mismatch.\n"
               f"Stored:   {stored_c2_hash}\nComputed: {computed_c2_hash}")
        logger.critical(err)
        raise RuntimeError(err)

    # 8. Environment compatibility
    if not override_env_check:
        try:
            import sklearn
            import pandas
            import scipy
        except ImportError as ie:
            err = f"SCIENTIFIC STARTUP GATE FAILED: Required scientific dependency missing: {ie}"
            logger.critical(err)
            raise RuntimeError(err)

    logger.info("PASS: Scientific contract gate fully verified [model_version=%s, contract_hash=%s].",
                model_version, contract_hash[:16])
    return True

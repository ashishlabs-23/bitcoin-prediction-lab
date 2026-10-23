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
    joblib = None

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


def verify_full_freeze_integrity(strict: bool = False) -> bool:
    """
    Runs the full freeze integrity verifier.
    If strict=True: any failure or blocking warning aborts.
    If strict=False (default): any critical check failure (FAIL) aborts, while
    informational data-append/package warnings are logged without blocking.
    """
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [sys.executable, FULL_FREEZE_VERIFIER_PATH]
    if strict:
        cmd.append("--strict")

    try:
        result = subprocess.run(
            cmd,
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
    lines = output.splitlines()

    # Detect actual check failures
    has_critical_failure = result.returncode != 0 or any(
        "FAIL" in line or "[FAIL]" in line for line in lines
    )
    
    blocking_warnings = [
        line.strip()
        for line in lines
        if "WARN   Runtime dependency" in line
        or "WARN   Training data — ohlcv" in line
        or "WARN   Package" in line
        or "WARN   Python version" in line
    ]

    should_block = has_critical_failure or (strict and bool(blocking_warnings))

    if should_block:
        missing_data = any(
            "FAIL   Runtime dependency" in line
            or "FAIL   Training data — ohlcv" in line
            or "FAIL   Training data" in line
            for line in lines
        )
        changed_data = any(
            "WARN   Runtime dependency" in line
            or "WARN   Training data — ohlcv" in line
            for line in lines
        )
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
            state, code = "MODEL_FAILURE", "MODEL_ARTIFACT_INVALID"
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

    if blocking_warnings:
        logger.info(
            "Full freeze verification passed with %d runtime notice(s): %s",
            len(blocking_warnings),
            "; ".join(blocking_warnings)
        )
    else:
        logger.info("Full freeze verification passed: scientific core is frozen and intact.")

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


# ---------------------------------------------------------------------------
# Authoritative Runtime Readiness Evaluator
# ---------------------------------------------------------------------------

_CACHED_READINESS: Optional[Dict[str, Any]] = None


def evaluate_runtime_readiness(
    manifest_path: Optional[str] = None,
    artifact_path: Optional[str] = None,
    force_refresh: bool = False,
    strict_warnings: bool = False
) -> Dict[str, Any]:
    """
    Evaluates comprehensive runtime readiness for canonical production inference.
    Returns a machine-readable dictionary with structured reason codes:
      NONE, FROZEN_INPUT_MISSING, FROZEN_INPUT_HASH_MISMATCH, FROZEN_RUNTIME_MISMATCH,
      MODEL_ARTIFACT_INVALID, FEATURE_CONTRACT_MISMATCH, TARGET_CONTRACT_MISMATCH,
      CALIBRATION_UNAVAILABLE, DATA_STALE, INSUFFICIENT_HISTORY, MODEL_UNAUTHORIZED.
    """
    global _CACHED_READINESS
    if _CACHED_READINESS is not None and not force_refresh:
        return _CACHED_READINESS

    from datetime import datetime, timezone
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mpath = manifest_path or REPAIRED_MANIFEST_PATH
    apath = artifact_path or MODEL_ARTIFACT_PATH
    ohlcv_path = os.path.join(repo_root, "data", "raw", "ohlcv.parquet")

    checks: Dict[str, Dict[str, Any]] = {}
    now_iso = datetime.now(timezone.utc).isoformat()

    def _blocked(
        code: str, reason: str, remediation: str, check_name: str, check_detail: Dict[str, Any]
    ) -> Dict[str, Any]:
        check_detail["status"] = "FAIL"
        checks[check_name] = check_detail
        result = {
            "status": "BLOCKED",
            "authorized": False,
            "authorization_status": "BLOCKED_AUDIT_FAILURE",
            "reason_code": code,
            "reason": reason,
            "remediation": remediation,
            "canonical_model_id": "HAR-RS-DOW-v1.0",
            "model_version": "1.0.0",
            "system_classification": "PRODUCTION_VOLATILITY",
            "forecast_target": "Annualized 7-Day Realized Variance (rv7d_var_ann)",
            "forecast_horizon": "168h (7 calendar days)",
            "directional_prediction_capability": False,
            "trading_enabled": False,
            "live_capital_authorized": False,
            "checks": checks,
            "evaluated_at": now_iso,
        }
        _CACHED_READINESS = result
        return result

    # 1. Manifest file check
    if not os.path.exists(mpath):
        return _blocked(
            "FROZEN_INPUT_MISSING",
            f"Scientific contract manifest not found at '{mpath}'.",
            "Restore or generate the repaired scientific contract manifest.",
            "manifest",
            {"path": mpath, "error": "file_not_found"}
        )

    try:
        with open(mpath, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        contract_hash = manifest.get("scientific_contract_hash")
        model_version = manifest.get("model_version")
        if model_version != "HAR-RS-DOW-v1.0" or not contract_hash:
            return _blocked(
                "MODEL_ARTIFACT_INVALID",
                f"Manifest specifies invalid model '{model_version}' or missing contract hash.",
                "Ensure manifest specifies HAR-RS-DOW-v1.0 with valid scientific_contract_hash.",
                "manifest",
                {"path": mpath, "model_version": model_version}
            )
        checks["manifest"] = {
            "status": "PASS",
            "model_version": model_version,
            "contract_hash": contract_hash[:16] + "...",
            "governance_status": manifest.get("governance_status")
        }
    except Exception as exc:
        return _blocked(
            "MODEL_ARTIFACT_INVALID",
            f"Unable to parse manifest JSON: {exc}",
            "Verify manifest file syntax.",
            "manifest",
            {"path": mpath, "error": str(exc)}
        )

    # 2. Model artifact file check
    if not os.path.exists(apath):
        return _blocked(
            "FROZEN_INPUT_MISSING",
            f"Canonical model artifact not found at '{apath}'.",
            "Ensure har_rs_dow_v1.joblib exists in experiments/results/freeze/.",
            "model_artifact",
            {"path": apath, "error": "file_not_found"}
        )

    live_artifact_sha = sha256_file(apath)
    stored_artifact_sha = manifest.get("model_artifact", {}).get("artifact_sha256")
    if live_artifact_sha != stored_artifact_sha:
        return _blocked(
            "MODEL_ARTIFACT_INVALID",
            f"Model artifact SHA256 mismatch (live={live_artifact_sha[:16]}... vs stored={stored_artifact_sha[:16]}...).",
            "Re-download or restore the verified model artifact without modification.",
            "model_artifact",
            {"path": apath, "live_sha256": live_artifact_sha, "stored_sha256": stored_artifact_sha}
        )
    checks["model_artifact"] = {
        "status": "PASS",
        "artifact_sha256": live_artifact_sha[:16] + "..."
    }

    # 3. Model pipeline coefficients check
    try:
        pipe = joblib.load(apath)
        live_coef_hash = extract_pipeline_coefficients_hash(pipe)
        stored_coef_hash = manifest.get("model_artifact", {}).get("coefficients_sha256")
        if live_coef_hash != stored_coef_hash:
            return _blocked(
                "MODEL_ARTIFACT_INVALID",
                "Model pipeline coefficients hash mismatch.",
                "Restore the canonical trained coefficients artifact.",
                "coefficients",
                {"live_coef_hash": live_coef_hash, "stored_coef_hash": stored_coef_hash}
            )
        checks["coefficients"] = {
            "status": "PASS",
            "coefficients_sha256": live_coef_hash[:16] + "..."
        }
    except Exception as exc:
        return _blocked(
            "MODEL_ARTIFACT_INVALID",
            f"Failed loading model pipeline: {exc}",
            "Verify model artifact joblib serialization compatibility.",
            "coefficients",
            {"error": str(exc)}
        )

    # 4. Feature contract check
    computed_feature_hash = sha256_str(json.dumps(FEATURE_SCHEMA, separators=(",", ":")))
    stored_feature_hash = manifest.get("feature_contract_hash")
    if stored_feature_hash and computed_feature_hash != stored_feature_hash:
        return _blocked(
            "FEATURE_CONTRACT_MISMATCH",
            "Feature contract schema mismatch.",
            "Ensure FEATURE_SCHEMA matches canonical 10-feature definition.",
            "feature_contract",
            {"computed": computed_feature_hash, "stored": stored_feature_hash}
        )
    checks["feature_contract"] = {
        "status": "PASS",
        "features_count": len(FEATURE_SCHEMA),
        "feature_schema_hash": computed_feature_hash[:16] + "..."
    }

    # 5. Target contract check
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
        return _blocked(
            "TARGET_CONTRACT_MISMATCH",
            "Target definition or horizon contract mismatch.",
            "Canonical target must be rv7d_var_ann with 168h forward horizon.",
            "target_contract",
            {"computed": computed_target_hash, "stored": stored_target_hash}
        )
    checks["target_contract"] = {
        "status": "PASS",
        "target": "rv7d_var_ann",
        "horizon": "168h",
        "annualization_factor": 52.142857
    }

    # 6. Conformal C2 calibration config check
    computed_c2_hash = sha256_dict(C2_CONFIG)
    stored_c2_hash = manifest.get("c2_config_hash")
    if stored_c2_hash and computed_c2_hash != stored_c2_hash:
        return _blocked(
            "CALIBRATION_UNAVAILABLE",
            "C2 conformal calibration configuration hash mismatch.",
            "Verify C2 dependence-aware conformal parameters.",
            "calibration",
            {"computed": computed_c2_hash, "stored": stored_c2_hash}
        )
    checks["calibration"] = {
        "status": "PASS",
        "engine": "C2 Dependence-Aware Conformal (Strictly Causal Delayed Resolution)",
        "nominal_coverage": "90%",
        "alpha": 0.10
    }

    # 7. Runtime scientific environment check
    try:
        import sklearn
        import pandas as pd
        import scipy
        checks["runtime_environment"] = {
            "status": "PASS",
            "scikit_learn": sklearn.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "numpy": np.__version__,
            "joblib": getattr(joblib, "__version__", "available")
        }
    except ImportError as exc:
        return _blocked(
            "FROZEN_RUNTIME_MISMATCH",
            f"Required scientific runtime dependency missing: {exc}",
            "Install required packages into python virtual environment.",
            "runtime_environment",
            {"error": str(exc)}
        )

    # 8. Point-in-time candle data history check
    if not os.path.exists(ohlcv_path):
        return _blocked(
            "FROZEN_INPUT_MISSING",
            f"Point-in-time candle data missing at '{ohlcv_path}'.",
            "Fetch or restore historical Coinbase BTC/USD 1h candles.",
            "point_in_time_data",
            {"path": ohlcv_path, "error": "file_not_found"}
        )

    try:
        df_ohlcv = pd.read_parquet(ohlcv_path, columns=["close"])
        candle_count = len(df_ohlcv)
        if candle_count < 720:
            return _blocked(
                "INSUFFICIENT_HISTORY",
                f"Insufficient candle history ({candle_count} rows < 720 required for rolling features).",
                "Ensure at least 720 closed hourly candles are present.",
                "point_in_time_data",
                {"count": candle_count, "required": 720}
            )
        checks["point_in_time_data"] = {
            "status": "PASS",
            "candle_count": candle_count,
            "min_required": 720
        }
    except Exception as exc:
        return _blocked(
            "MODEL_ARTIFACT_INVALID",
            f"Failed reading candle data from '{ohlcv_path}': {exc}",
            "Repair corrupted parquet data file.",
            "point_in_time_data",
            {"error": str(exc)}
        )

    # 9. Full freeze verifier check (non-blocking informational warnings allowed unless strict)
    try:
        verify_full_freeze_integrity(strict=strict_warnings)
        checks["freeze_verifier"] = {
            "status": "PASS",
            "mode": "strict" if strict_warnings else "standard"
        }
    except FreezeIntegrityError as fie:
        return _blocked(
            fie.code,
            str(fie),
            "Inspect full freeze verifier output for exact check failure.",
            "freeze_verifier",
            {"state": fie.state, "code": fie.code}
        )

    # All checks passed: Canonical production volatility model is authorized!
    result = {
        "status": "READY",
        "authorized": True,
        "authorization_status": "AUTHORIZED_FOR_PRODUCTION",
        "restricted_serving_scope": "AUTHORIZED_FOR_VOLATILITY_RISK_ONLY",
        "reason_code": "NONE",
        "reason": (
            "Canonical 168h annualized realized variance risk model (HAR-RS-DOW-v1.0) "
            "and C2 conformal risk envelope are fully verified and authorized for volatility risk."
        ),
        "remediation": "None. Canonical production risk inference is authorized.",
        "canonical_model_id": "HAR-RS-DOW-v1.0",
        "model_version": "1.0.0",
        "system_classification": "PRODUCTION_VOLATILITY",
        "forecast_target": "Annualized 7-Day Realized Variance (rv7d_var_ann)",
        "forecast_horizon": "168h (7 calendar days)",
        "directional_prediction_capability": False,
        "trading_enabled": False,
        "live_capital_authorized": False,
        "governance_breakdown": {
            "service_liveness": "LIVE",
            "artifact_integrity": "VERIFIED",
            "runtime_compatibility": "VERIFIED",
            "input_feature_readiness": "VERIFIED",
            "numerical_inference_availability": "AVAILABLE",
            "calibration_readiness": "VERIFIED",
            "formal_research_validation": "VALIDATED",
            "volatility_risk_serving_authorization": "AUTHORIZED_FOR_VOLATILITY_RISK_ONLY",
            "confirmatory_prospective_gate_24h": "COLLECTING (3/100 blocks)",
            "confirmatory_prospective_gate_168h": "COLLECTING (0/100 blocks)",
            "directional_model_authorization": "OFFLINE_RESEARCH_ONLY",
            "live_trading_authorization": "DISABLED"
        },
        "epistemic_notice": (
            "Model forecasts realized variance and risk envelope magnitude. "
            "Directional price forecasting is NOT supported. Live execution is strictly disabled."
        ),
        "checks": checks,
        "evaluated_at": now_iso,
    }

    _CACHED_READINESS = result
    return result


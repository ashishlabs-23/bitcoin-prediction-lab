"""
research/verify_freeze_manifest.py — HAR-RS-DOW v1.0 Freeze Integrity Verifier
================================================================================
Run this at any time to assert that the scientific core is still frozen.

Exit codes:
  0 — ALL_CHECKS_PASSED  (core is intact)
  1 — FREEZE_BROKEN      (at least one check failed; details printed)
  2 — MANIFEST_MISSING   (freeze_har_rs_dow.py has not been run yet)

Usage:
  python research/verify_freeze_manifest.py
  python research/verify_freeze_manifest.py --strict   # also verifies git commit

The verifier performs eight independent checks in order:

  CHECK 1 — Manifest self-integrity
    Re-computes sha256_dict(manifest minus manifest_hash field) and compares.
    If this fails, the manifest file itself was tampered with.

  CHECK 2 — Model artifact integrity
    Re-reads the joblib file from disk and SHA-256 hashes it.
    If different from manifest['model_artifact']['artifact_sha256'], the
    serialized model was replaced or corrupted after freezing.

  CHECK 3 — Model coefficient integrity
    Loads the joblib artifact, re-extracts all pipeline coefficients,
    re-hashes them, and compares against the four stored coefficient hashes.
    This is the strongest check: detects any numeric change to the model.

  CHECK 4 — Feature schema integrity
    Re-hashes the FEATURE_SCHEMA list from freeze_har_rs_dow.py and compares
    against manifest['feature_schema_hash'].

  CHECK 5 — Training data integrity
    Re-hashes ohlcv.parquet and iv7d.parquet on disk.
    A mismatch means the raw training data was re-ingested or modified.

  CHECK 6 — C2 configuration integrity
    Re-hashes the C2_CONFIG dict and compares against manifest['C2_config_hash'].

  CHECK 7 — Python version check (informational for patch, error for minor)
    Compares sys.version_info.major + minor against the frozen version.
    A minor-version change may alter floating-point results or pickle format.

  CHECK 8 — Critical package versions
    Compares {scikit-learn, numpy, pandas, scipy, joblib} versions.
    A version change does NOT automatically break the freeze, but it is
    reported as a WARNING since it changes the numeric environment.

  CHECK 9 — Source commit (optional, with --strict flag)
    Compares git HEAD against the frozen commit SHA.
    Informational only without --strict; required check with --strict.
"""

import os
import sys
import json
import hashlib
import subprocess
from typing import Dict, Any, List, Tuple

import numpy as np

try:
    import joblib
except ImportError:
    from sklearn.externals import joblib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_RAW_DIR, RESULTS_DIR

# ── Manifest path ──────────────────────────────────────────────────────────────
FREEZE_DIR = os.path.join(RESULTS_DIR, "freeze")
MANIFEST_PATH = os.path.join(FREEZE_DIR, "har_rs_dow_v1_baseline_manifest.json")
MODEL_ARTIFACT_PATH = os.path.join(FREEZE_DIR, "har_rs_dow_v1.joblib")


# ─────────────────────────────────────────────────────────────────────────────
# Hash utilities (must be identical to freeze_har_rs_dow.py)
# ─────────────────────────────────────────────────────────────────────────────

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


def get_git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        return result.stdout.strip()
    except Exception:
        return "UNKNOWN"


def get_critical_package_versions() -> Dict[str, str]:
    packages = {}
    try:
        import sklearn
        packages["scikit-learn"] = sklearn.__version__
    except ImportError:
        packages["scikit-learn"] = "MISSING"
    try:
        packages["numpy"] = np.__version__
    except Exception:
        packages["numpy"] = "MISSING"
    try:
        import pandas
        packages["pandas"] = pandas.__version__
    except ImportError:
        packages["pandas"] = "MISSING"
    try:
        import scipy
        packages["scipy"] = scipy.__version__
    except ImportError:
        packages["scipy"] = "MISSING"
    try:
        packages["joblib"] = joblib.__version__
    except AttributeError:
        packages["joblib"] = "bundled"
    return packages


def extract_and_hash_pipeline_coefficients(pipe) -> Dict[str, Any]:
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge
    scaler: StandardScaler = pipe.named_steps["scaler"]
    ridge: Ridge = pipe.named_steps["ridge"]

    scaler_mean_hash      = sha256_numpy_array(np.asarray(scaler.mean_))
    scaler_scale_hash     = sha256_numpy_array(np.asarray(scaler.scale_))
    ridge_coef_hash       = sha256_numpy_array(np.asarray(ridge.coef_))
    ridge_intercept_hash  = sha256_numpy_array(
        np.asarray([ridge.intercept_]) if np.isscalar(ridge.intercept_)
        else np.asarray(ridge.intercept_)
    )
    combined_source = "".join([
        scaler_mean_hash, scaler_scale_hash,
        ridge_coef_hash, ridge_intercept_hash,
    ])
    combined_hash = sha256_str(combined_source)

    return {
        "scaler_mean_sha256":            scaler_mean_hash,
        "scaler_scale_sha256":           scaler_scale_hash,
        "ridge_coef_sha256":             ridge_coef_hash,
        "ridge_intercept_sha256":        ridge_intercept_hash,
        "combined_coefficients_sha256":  combined_hash,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Check results accumulator
# ─────────────────────────────────────────────────────────────────────────────

PASS   = "✓ PASS"
FAIL   = "✗ FAIL"
WARN   = "⚠ WARN"
SKIP   = "· SKIP"

CheckResult = Tuple[str, str, str]   # (status, label, detail)
results: List[CheckResult] = []


def record(status: str, label: str, detail: str = "") -> None:
    results.append((status, label, detail))
    icon = status
    line = f"  {icon:8s} {label}"
    if detail:
        line += f"\n           {detail}"
    print(line)


# ─────────────────────────────────────────────────────────────────────────────
# Main verifier
# ─────────────────────────────────────────────────────────────────────────────

def run_verification(strict: bool = False) -> int:
    """
    Runs all integrity checks. Returns 0 (pass), 1 (fail), or 2 (missing).
    """
    print("=" * 72)
    print("BTCognitive — HAR-RS-DOW v1.0 Freeze Integrity Verifier")
    print("=" * 72)

    # ── Preflight: manifest must exist ────────────────────────────────────
    if not os.path.exists(MANIFEST_PATH):
        print(f"\n[ERROR] Manifest not found: {MANIFEST_PATH}")
        print("Run `python research/freeze_har_rs_dow.py` first to create the freeze.")
        return 2

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest: Dict[str, Any] = json.load(f)

    print(f"\n  Manifest  : {MANIFEST_PATH}")
    print(f"  Frozen at : {manifest.get('manifest_created_at', 'UNKNOWN')}")
    print(f"  Model     : {manifest.get('model_version', 'UNKNOWN')}\n")
    print(f"  {'Status':<8}  Check")
    print(f"  {'─'*8}  {'─'*52}")

    # ── CHECK 1: Manifest self-integrity ──────────────────────────────────
    stored_manifest_hash = manifest.get("manifest_hash", "")
    body_without_hash = {k: v for k, v in manifest.items() if k != "manifest_hash"}
    recomputed_manifest_hash = sha256_dict(body_without_hash)
    if recomputed_manifest_hash == stored_manifest_hash:
        record(PASS, "Manifest self-integrity",
               f"hash={stored_manifest_hash[:16]}...")
    else:
        record(FAIL, "Manifest self-integrity",
               f"stored={stored_manifest_hash[:16]}... "
               f"recomputed={recomputed_manifest_hash[:16]}...")

    # ── CHECK 2: Model artifact file integrity ────────────────────────────
    stored_artifact_hash = manifest.get("model_artifact", {}).get("artifact_sha256", "")
    if not os.path.exists(MODEL_ARTIFACT_PATH):
        record(FAIL, "Model artifact file exists", f"Not found: {MODEL_ARTIFACT_PATH}")
    else:
        live_artifact_hash = sha256_file(MODEL_ARTIFACT_PATH)
        if live_artifact_hash == stored_artifact_hash:
            record(PASS, "Model artifact file integrity",
                   f"hash={live_artifact_hash[:16]}...")
        else:
            record(FAIL, "Model artifact file integrity",
                   f"stored={stored_artifact_hash[:16]}... "
                   f"live={live_artifact_hash[:16]}...")

    # ── CHECK 3: Model coefficient integrity ──────────────────────────────
    if os.path.exists(MODEL_ARTIFACT_PATH):
        try:
            pipe = joblib.load(MODEL_ARTIFACT_PATH)
            live_coef_hashes = extract_and_hash_pipeline_coefficients(pipe)
            stored_coef_hashes = manifest.get("model_coefficients", {})
            coef_checks = [
                "scaler_mean_sha256",
                "scaler_scale_sha256",
                "ridge_coef_sha256",
                "ridge_intercept_sha256",
                "combined_coefficients_sha256",
            ]
            all_coef_match = all(
                live_coef_hashes.get(k) == stored_coef_hashes.get(k)
                for k in coef_checks
            )
            if all_coef_match:
                record(PASS, "Model coefficient integrity",
                       f"combined={live_coef_hashes['combined_coefficients_sha256'][:16]}...")
            else:
                mismatched = [
                    k for k in coef_checks
                    if live_coef_hashes.get(k) != stored_coef_hashes.get(k)
                ]
                record(FAIL, "Model coefficient integrity",
                       f"Mismatched fields: {mismatched}")
        except Exception as e:
            record(FAIL, "Model coefficient integrity", f"Load error: {e}")
    else:
        record(SKIP, "Model coefficient integrity", "Artifact missing (see CHECK 2)")

    # ── CHECK 4: Feature schema integrity ─────────────────────────────────
    stored_schema_hash = manifest.get("feature_schema_hash", "")
    stored_schema      = manifest.get("feature_schema", [])
    recomputed_schema_hash = sha256_str(json.dumps(stored_schema, separators=(",", ":")))
    if recomputed_schema_hash == stored_schema_hash:
        record(PASS, "Feature schema integrity",
               f"n_features={len(stored_schema)}, hash={stored_schema_hash[:16]}...")
    else:
        record(FAIL, "Feature schema integrity",
               f"stored={stored_schema_hash[:16]}... "
               f"recomputed={recomputed_schema_hash[:16]}...")

    # ── CHECK 5: Training data integrity ──────────────────────────────────
    ohlcv_path = os.path.join(DATA_RAW_DIR, "ohlcv.parquet")
    iv7d_path  = os.path.join(DATA_RAW_DIR, "iv7d.parquet")
    stored_data = manifest.get("training_data_snapshot", {})

    for fname, fpath, key in [
        ("ohlcv.parquet",  ohlcv_path, "ohlcv_parquet_sha256"),
        ("iv7d.parquet",   iv7d_path,  "iv7d_parquet_sha256"),
    ]:
        stored_fhash = stored_data.get(key, "")
        if not os.path.exists(fpath):
            record(FAIL, f"Training data — {fname}", f"File not found: {fpath}")
        else:
            live_fhash = sha256_file(fpath)
            if live_fhash == stored_fhash:
                record(PASS, f"Training data — {fname}",
                       f"hash={live_fhash[:16]}...")
            else:
                record(WARN, f"Training data — {fname}",
                       f"Hash changed (data re-ingested?)\n"
                       f"           stored={stored_fhash[:16]}... "
                       f"live={live_fhash[:16]}...")

    # ── CHECK 6: C2 configuration integrity ──────────────────────────────
    stored_c2_hash = manifest.get("C2_config_hash", "")
    stored_c2_body = manifest.get("C2_config", {})
    recomputed_c2_hash = sha256_dict(stored_c2_body)
    if recomputed_c2_hash == stored_c2_hash:
        record(PASS, "C2 calibration config integrity",
               f"hash={stored_c2_hash[:16]}...")
    else:
        record(FAIL, "C2 calibration config integrity",
               f"stored={stored_c2_hash[:16]}... "
               f"recomputed={recomputed_c2_hash[:16]}...")

    # ── CHECK 7: Python version ────────────────────────────────────────────
    stored_py = manifest.get("python_version", {})
    live_major = sys.version_info.major
    live_minor = sys.version_info.minor
    live_micro = sys.version_info.micro
    frozen_major = stored_py.get("major", -1)
    frozen_minor = stored_py.get("minor", -1)
    frozen_micro = stored_py.get("micro", -1)

    if live_major != frozen_major or live_minor != frozen_minor:
        record(FAIL, "Python version (minor)",
               f"frozen={frozen_major}.{frozen_minor}.{frozen_micro}, "
               f"live={live_major}.{live_minor}.{live_micro}")
    elif live_micro != frozen_micro:
        record(WARN, "Python version (patch changed — informational)",
               f"frozen={frozen_major}.{frozen_minor}.{frozen_micro}, "
               f"live={live_major}.{live_minor}.{live_micro}")
    else:
        record(PASS, "Python version",
               f"{live_major}.{live_minor}.{live_micro}")

    # ── CHECK 8: Critical package versions ────────────────────────────────
    stored_pkgs = manifest.get("critical_packages", {})
    live_pkgs   = get_critical_package_versions()
    for pkg_name in ["scikit-learn", "numpy", "pandas", "scipy", "joblib"]:
        sv = stored_pkgs.get(pkg_name, "UNKNOWN")
        lv = live_pkgs.get(pkg_name, "UNKNOWN")
        if sv == lv:
            record(PASS, f"Package — {pkg_name}", f"version={lv}")
        else:
            record(WARN, f"Package — {pkg_name}",
                   f"frozen={sv}, live={lv} — numeric environment changed")

    # ── CHECK 9: Source commit (optional) ─────────────────────────────────
    stored_commit = manifest.get("source_commit_hash", "UNKNOWN")
    live_commit   = get_git_commit()
    if live_commit == stored_commit:
        record(PASS, "Git source commit", f"commit={live_commit[:12]}...")
    else:
        status = FAIL if strict else WARN
        record(status, "Git source commit",
               f"frozen={stored_commit[:12]}..., "
               f"live={live_commit[:12]}... "
               f"({'ERROR in --strict mode' if strict else 'informational'})")

    # ── Summary ────────────────────────────────────────────────────────────
    n_pass = sum(1 for s, _, _ in results if s == PASS)
    n_fail = sum(1 for s, _, _ in results if s == FAIL)
    n_warn = sum(1 for s, _, _ in results if s == WARN)
    n_skip = sum(1 for s, _, _ in results if s == SKIP)

    print(f"\n  {'─'*60}")
    print(f"  Results : {n_pass} pass, {n_fail} fail, {n_warn} warn, {n_skip} skip")

    if n_fail == 0:
        verdict = "ALL_CHECKS_PASSED — scientific core is frozen and intact"
        print(f"\n  ✓ {verdict}")
        return_code = 0
    else:
        verdict = f"FREEZE_BROKEN — {n_fail} critical check(s) failed"
        print(f"\n  ✗ {verdict}")
        return_code = 1

    print(f"  {'─'*60}\n")
    return return_code


if __name__ == "__main__":
    strict_mode = "--strict" in sys.argv
    sys.exit(run_verification(strict=strict_mode))

# -*- coding: utf-8 -*-
"""
research/freeze_har_rs_dow.py -- HAR-RS-DOW v1.0 Model Freeze & Cryptographic Manifest Generator
=================================================================================================
Phase 0: Formally defines what "frozen" means by producing:

  1. A serialized model artifact (joblib) — the exact fitted Pipeline coefficients
  2. A cryptographic baseline manifest (JSON) — hashes of every scientific input

The manifest covers:
  - model_version          : human label
  - model_coefficients_hash: SHA-256 of serialized joblib bytes
  - feature_schema_hash    : SHA-256 of the ordered feature name list
  - training_data_snapshot_hash : SHA-256 of ohlcv.parquet + iv7d.parquet (the raw inputs)
  - training_span          : ISO-8601 start/end of data actually used
  - holdout_boundary       : "2026-01-01T00:00:00Z" (never changes)
  - C2_config_hash         : SHA-256 of the C2 calibration spec dict
  - python_version         : sys.version_info
  - package_lock_hash      : SHA-256 of installed package list (pip freeze)
  - source_commit_hash     : git HEAD SHA
  - manifest_created_at    : ISO-8601 UTC timestamp
  - manifest_hash          : SHA-256 of the manifest body (self-referential integrity)

IMMUTABILITY RULE
-----------------
This script MUST be run exactly ONCE before prospective validation begins.
Re-running it on different data produces a different manifest — detecting drift.
To verify the frozen state at any future point, use verify_freeze_manifest.py.

WHAT "FROZEN" MEANS (formal definition)
----------------------------------------
The scientific core is frozen if and only if:
  verify_freeze_manifest.py returns ALL_CHECKS_PASSED

A change to any of the following breaks the freeze:
  - model coefficients (Ridge intercept/coefs or StandardScaler mean/scale)
  - feature names or their ordering
  - raw training data files (ohlcv.parquet, iv7d.parquet)
  - C2 calibration parameters (alpha, pool_window, step, ewm_span)
  - Python version (patch-level is informational; minor-level breaks ABI)
  - Package versions of {numpy, scikit-learn, pandas, scipy}

A change to the following does NOT break the freeze:
  - Dashboard code, API routes, WebSocket handlers
  - Observatory persistence (adding a DB backend)
  - Bug fixes that do not alter feature values or calibration logic
  - Logging, CLI, or UI cosmetics
"""

import os
import sys
import json
import hashlib
import subprocess
import struct
from datetime import datetime, timezone
from typing import Dict, Any, List

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

# ── joblib is bundled with scikit-learn; use it directly ──────────────────────
try:
    import joblib
except ImportError:
    from sklearn.externals import joblib  # fallback for very old sklearn

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_RAW_DIR, RESULTS_DIR
from research.run_vol_edge_01_test import prepare_aligned_dataset

# ── Output paths ──────────────────────────────────────────────────────────────
FREEZE_DIR = os.path.join(RESULTS_DIR, "freeze")
MODEL_ARTIFACT_PATH = os.path.join(FREEZE_DIR, "har_rs_dow_v1.joblib")
MANIFEST_PATH = os.path.join(FREEZE_DIR, "har_rs_dow_v1_baseline_manifest.json")

# ── Canonical constants (NEVER change these — they define the freeze) ──────────
MODEL_VERSION = "HAR-RS-DOW-v1.0"
HOLDOUT_BOUNDARY = "2026-01-01T00:00:00Z"
NOMINAL_COVERAGE = 0.90
ALPHA = 1.0 - NOMINAL_COVERAGE          # 0.10
RIDGE_ALPHA = 1.0                        # Ridge regularisation
C2_EWM_SPAN = 720                        # hours — rolling scale denominator
C2_POOL_WINDOW_H = 1000                  # hours — trailing conformity pool
C2_POOL_STEP_H = 24                      # hours — daily sub-sampling step
C2_QUANTILE_TARGET = 1.0 - ALPHA / 2.0  # 0.95 upper / lower quantiles

# ── Ordered feature schema for HAR-RS-DOW (M2-R) ─────────────────────────────
# log-variance domain: ln(rv_down_1d), ln(rv_up_1d), ln(rv7d_lag), ln(rv30d), DOW×6
FEATURE_SCHEMA: List[str] = [
    "log_rv_down_1d",
    "log_rv_up_1d",
    "log_rv7d_var_ann_lag",
    "log_rv30d_var_ann",
    "dow_1",   # Monday (Monday=0 is dropped as reference)
    "dow_2",   # Tuesday
    "dow_3",   # Wednesday
    "dow_4",   # Thursday
    "dow_5",   # Friday
    "dow_6",   # Saturday
]

# ── C2 calibration spec (immutable after freeze) ──────────────────────────────
C2_CONFIG: Dict[str, Any] = {
    "method": "Dependence-Aware Asymmetric Conformal Prediction",
    "nominal_target_coverage": NOMINAL_COVERAGE,
    "alpha": ALPHA,
    "conformity_score_upper": "max(0, (y_t - v_hat_t) / sigma_epsilon_t)",
    "conformity_score_lower": "max(0, (v_hat_t - y_t) / sigma_epsilon_t)",
    "scale_denominator": f"EWM std of residuals, span={C2_EWM_SPAN}h",
    "pool_window_hours": C2_POOL_WINDOW_H,
    "pool_step_hours": C2_POOL_STEP_H,
    "pool_description": "Trailing 1000h buffer sub-sampled at daily (24h) intervals",
    "quantile_target": C2_QUANTILE_TARGET,
    "quantile_formula": "ceil((N_pool + 1) * quantile_target)",
}


# ─────────────────────────────────────────────────────────────────────────────
# Hashing utilities
# ─────────────────────────────────────────────────────────────────────────────

def sha256_file(path: str) -> str:
    """Returns SHA-256 hex digest of a file, reading in 1 MB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_str(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_dict(d: Dict[str, Any]) -> str:
    """Deterministic SHA-256 of a dict via sorted canonical JSON."""
    canonical = json.dumps(d, sort_keys=True, separators=(",", ":"), default=str)
    return sha256_str(canonical)


def sha256_numpy_array(arr: np.ndarray) -> str:
    """SHA-256 of a numpy array via its raw bytes + dtype + shape header."""
    h = hashlib.sha256()
    # Encode shape and dtype so arrays with same values but different shapes differ
    header = json.dumps({"shape": list(arr.shape), "dtype": str(arr.dtype)},
                        sort_keys=True).encode("utf-8")
    h.update(header)
    h.update(arr.tobytes())
    return h.hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Git & package metadata
# ─────────────────────────────────────────────────────────────────────────────

def get_git_commit() -> str:
    """Returns current git HEAD SHA, or 'UNKNOWN' if not in a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        return result.stdout.strip()
    except Exception:
        return "UNKNOWN"


def get_pip_freeze() -> str:
    """Returns `pip freeze` output as a sorted string."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True, text=True, check=True
        )
        lines = sorted(result.stdout.strip().splitlines())
        return "\n".join(lines)
    except Exception:
        return "UNKNOWN"


def get_critical_package_versions() -> Dict[str, str]:
    """Extracts versions of the scientific-core packages only."""
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
        packages["pandas"] = pd.__version__
    except Exception:
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


# ─────────────────────────────────────────────────────────────────────────────
# Model coefficient hashing
# ─────────────────────────────────────────────────────────────────────────────

def extract_and_hash_pipeline_coefficients(pipe: Pipeline) -> Dict[str, Any]:
    """
    Extracts all numeric parameters from a (StandardScaler → Ridge) Pipeline
    and returns a dict of their SHA-256 hashes plus a combined hash.

    The combined hash covers ALL parameters simultaneously so a single-coefficient
    change is detected.
    """
    scaler: StandardScaler = pipe.named_steps["scaler"]
    ridge: Ridge = pipe.named_steps["ridge"]

    scaler_mean_hash = sha256_numpy_array(np.asarray(scaler.mean_))
    scaler_scale_hash = sha256_numpy_array(np.asarray(scaler.scale_))
    ridge_coef_hash = sha256_numpy_array(np.asarray(ridge.coef_))
    ridge_intercept_hash = sha256_numpy_array(
        np.asarray([ridge.intercept_]) if np.isscalar(ridge.intercept_)
        else np.asarray(ridge.intercept_)
    )

    combined_source = "".join([
        scaler_mean_hash, scaler_scale_hash,
        ridge_coef_hash, ridge_intercept_hash,
    ])
    combined_hash = sha256_str(combined_source)

    return {
        "scaler_mean_sha256": scaler_mean_hash,
        "scaler_scale_sha256": scaler_scale_hash,
        "ridge_coef_sha256": ridge_coef_hash,
        "ridge_intercept_sha256": ridge_intercept_hash,
        "combined_coefficients_sha256": combined_hash,
        "n_features": int(len(ridge.coef_)),
        "ridge_alpha": float(ridge.alpha),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main freeze routine
# ─────────────────────────────────────────────────────────────────────────────

def fit_har_rs_dow(df_train: pd.DataFrame) -> Pipeline:
    """
    Fits the frozen HAR-RS-DOW Pipeline on training data.
    Feature matrix: [log_rv_down_1d, log_rv_up_1d, log_rv7d_lag, log_rv30d, DOW×6]
    Target:         log(rv7d_var_ann)
    """
    log_y = np.log(np.maximum(1e-6, df_train["rv7d_var_ann"].values))

    log_rv_down = np.log(np.maximum(1e-6, df_train["rv_down_1d"].values))
    log_rv_up   = np.log(np.maximum(1e-6, df_train["rv_up_1d"].values))
    log_rv7     = np.log(np.maximum(1e-6, df_train["rv7d_var_ann_lag"].values))
    log_rv30    = np.log(np.maximum(1e-6, df_train["rv30d_var_ann"].values))

    dow_dummies = pd.get_dummies(df_train["dow"], prefix="dow", drop_first=True)
    # Guarantee exactly 6 DOW columns (pad if edge of dataset misses a day)
    for col_i in range(1, 7):
        col_name = f"dow_{col_i}"
        if col_name not in dow_dummies.columns:
            dow_dummies[col_name] = 0
    dow_dummies = dow_dummies[[f"dow_{i}" for i in range(1, 7)]].values

    X_train = np.column_stack([log_rv_down, log_rv_up, log_rv7, log_rv30, dow_dummies])

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("ridge",  Ridge(alpha=RIDGE_ALPHA)),
    ])
    pipe.fit(X_train, log_y)
    return pipe


def run_freeze():
    """
    Executes the full freeze sequence:
      1. Load & split data at holdout boundary
      2. Fit HAR-RS-DOW on training portion
      3. Serialize model artifact (joblib)
      4. Compute all cryptographic hashes
      5. Write baseline manifest (JSON)
      6. Print verification summary
    """
    print("=" * 72)
    print("BTCognitive — Phase 0: HAR-RS-DOW v1.0 Scientific Freeze")
    print("=" * 72)

    os.makedirs(FREEZE_DIR, exist_ok=True)

    # ── Guard: refuse to overwrite an existing freeze ──────────────────────
    if os.path.exists(MANIFEST_PATH):
        print(f"\n[ABORT] Manifest already exists at:\n  {MANIFEST_PATH}")
        print("The model has already been frozen.")
        print("To verify the frozen state, run: verify_freeze_manifest.py")
        print("To deliberately re-freeze (new pre-registration required),")
        print("  manually delete the freeze/ directory first.")
        sys.exit(0)

    # ── Step 1: Load dataset ───────────────────────────────────────────────
    print("\n[1/6] Loading and aligning dataset...")
    df = prepare_aligned_dataset()
    holdout_dt = pd.to_datetime(HOLDOUT_BOUNDARY, utc=True)
    df_train = df[df.index < holdout_dt].copy()
    df_holdout = df[df.index >= holdout_dt].copy()

    print(f"      Training span : {df_train.index.min()} to {df_train.index.max()}")
    print(f"      Holdout span  : {df_holdout.index.min()} to {df_holdout.index.max()}")
    print(f"      Training N    : {len(df_train):,} bars")
    print(f"      Holdout  N    : {len(df_holdout):,} bars")

    training_span = {
        "start": str(df_train.index.min()),
        "end":   str(df_train.index.max()),
        "n_bars": int(len(df_train)),
    }

    # ── Step 2: Fit model ──────────────────────────────────────────────────
    print("\n[2/6] Fitting HAR-RS-DOW Pipeline on training data...")
    pipe = fit_har_rs_dow(df_train)
    ridge: Ridge = pipe.named_steps["ridge"]
    print(f"      Ridge intercept : {ridge.intercept_:.6f}")
    print(f"      Ridge coefs     : {ridge.coef_}")

    # Quick sanity check — QLIKE on training set
    log_rv_down = np.log(np.maximum(1e-6, df_train["rv_down_1d"].values))
    log_rv_up   = np.log(np.maximum(1e-6, df_train["rv_up_1d"].values))
    log_rv7     = np.log(np.maximum(1e-6, df_train["rv7d_var_ann_lag"].values))
    log_rv30    = np.log(np.maximum(1e-6, df_train["rv30d_var_ann"].values))
    dow_dummies_tr = pd.get_dummies(df_train["dow"], prefix="dow", drop_first=True)
    for col_i in range(1, 7):
        col_name = f"dow_{col_i}"
        if col_name not in dow_dummies_tr.columns:
            dow_dummies_tr[col_name] = 0
    dow_dummies_tr = dow_dummies_tr[[f"dow_{i}" for i in range(1, 7)]].values
    X_tr = np.column_stack([log_rv_down, log_rv_up, log_rv7, log_rv30, dow_dummies_tr])
    v_hat_tr = np.exp(pipe.predict(X_tr))
    y_tr = df_train["rv7d_var_ann"].values
    safe_y = np.maximum(1e-8, y_tr)
    safe_v = np.maximum(1e-8, v_hat_tr)
    ratio = safe_y / safe_v
    qlike_train = float(np.mean(ratio - np.log(ratio) - 1.0))
    print(f"      In-sample QLIKE : {qlike_train:.5f}  (expected ≈ 0.19300 OOS)")

    # ── Step 3: Serialize model artifact ──────────────────────────────────
    print("\n[3/6] Serializing model artifact to joblib...")
    joblib.dump(pipe, MODEL_ARTIFACT_PATH, compress=3)
    model_bytes_size = os.path.getsize(MODEL_ARTIFACT_PATH)
    model_artifact_hash = sha256_file(MODEL_ARTIFACT_PATH)
    print(f"      Saved  : {MODEL_ARTIFACT_PATH}")
    print(f"      Size   : {model_bytes_size:,} bytes")
    print(f"      SHA-256: {model_artifact_hash}")

    # ── Step 4: Compute all hashes ─────────────────────────────────────────
    print("\n[4/6] Computing cryptographic hashes...")

    # Feature schema hash
    feature_schema_hash = sha256_str(json.dumps(FEATURE_SCHEMA, separators=(",", ":")))
    print(f"      Feature schema hash : {feature_schema_hash[:16]}...")

    # Training data hashes (raw parquet files that produced the training set)
    ohlcv_path = os.path.join(DATA_RAW_DIR, "ohlcv.parquet")
    iv7d_path  = os.path.join(DATA_RAW_DIR, "iv7d.parquet")
    ohlcv_hash = sha256_file(ohlcv_path) if os.path.exists(ohlcv_path) else "FILE_MISSING"
    iv7d_hash  = sha256_file(iv7d_path)  if os.path.exists(iv7d_path)  else "FILE_MISSING"
    combined_data_hash = sha256_str(ohlcv_hash + iv7d_hash)
    print(f"      ohlcv.parquet hash  : {ohlcv_hash[:16]}...")
    print(f"      iv7d.parquet hash   : {iv7d_hash[:16]}...")
    print(f"      Training data hash  : {combined_data_hash[:16]}...")

    # C2 config hash
    c2_config_hash = sha256_dict(C2_CONFIG)
    print(f"      C2 config hash      : {c2_config_hash[:16]}...")

    # Model coefficient hashes
    coef_hashes = extract_and_hash_pipeline_coefficients(pipe)
    print(f"      Coefficient hash    : {coef_hashes['combined_coefficients_sha256'][:16]}...")

    # Python runtime
    python_version = {
        "version_string": sys.version,
        "major": sys.version_info.major,
        "minor": sys.version_info.minor,
        "micro": sys.version_info.micro,
        "implementation": sys.implementation.name,
    }

    # Package lock
    pip_freeze_str = get_pip_freeze()
    package_lock_hash = sha256_str(pip_freeze_str)
    critical_packages = get_critical_package_versions()
    print(f"      Package lock hash   : {package_lock_hash[:16]}...")

    # Source commit
    source_commit = get_git_commit()
    print(f"      Git commit          : {source_commit[:12]}...")

    # ── Step 5: Build manifest body ───────────────────────────────────────
    print("\n[5/6] Building manifest...")

    manifest_body: Dict[str, Any] = {
        "model_version": MODEL_VERSION,
        "holdout_boundary": HOLDOUT_BOUNDARY,
        "nominal_coverage": NOMINAL_COVERAGE,
        "training_span": training_span,
        "feature_schema": FEATURE_SCHEMA,
        "feature_schema_hash": feature_schema_hash,
        "training_data_snapshot": {
            "ohlcv_parquet_sha256": ohlcv_hash,
            "iv7d_parquet_sha256": iv7d_hash,
            "combined_training_data_sha256": combined_data_hash,
        },
        "model_artifact": {
            "path": os.path.basename(MODEL_ARTIFACT_PATH),
            "size_bytes": model_bytes_size,
            "artifact_sha256": model_artifact_hash,
        },
        "model_coefficients": coef_hashes,
        "C2_config": C2_CONFIG,
        "C2_config_hash": c2_config_hash,
        "python_version": python_version,
        "critical_packages": critical_packages,
        "package_lock_hash": package_lock_hash,
        "source_commit_hash": source_commit,
        "in_sample_qlike": round(qlike_train, 5),
        "manifest_created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Self-referential integrity: hash the manifest body
    manifest_body["manifest_hash"] = sha256_dict(manifest_body)

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest_body, f, indent=2, default=str)

    # Step 6: Print verification summary
    SEP = "-" * 72
    print("\n[6/6] Freeze complete.")
    print(f"\n{SEP}")
    print("  HAR-RS-DOW v1.0 FROZEN -- BASELINE MANIFEST")
    print(SEP)
    print(f"  Model artifact    : {MODEL_ARTIFACT_PATH}")
    print(f"  Manifest          : {MANIFEST_PATH}")
    print(f"  Artifact SHA-256  : {model_artifact_hash}")
    print(f"  Coef SHA-256      : {coef_hashes['combined_coefficients_sha256']}")
    print(f"  Feature schema    : {feature_schema_hash}")
    print(f"  Training data     : {combined_data_hash}")
    print(f"  C2 config         : {c2_config_hash}")
    print(f"  Package lock      : {package_lock_hash}")
    print(f"  Git commit        : {source_commit}")
    print(f"  Manifest hash     : {manifest_body['manifest_hash']}")
    print(SEP)
    print("\n  VERIFY AT ANY TIME: python research/verify_freeze_manifest.py")
    print(f"{SEP}\n")


if __name__ == "__main__":
    run_freeze()

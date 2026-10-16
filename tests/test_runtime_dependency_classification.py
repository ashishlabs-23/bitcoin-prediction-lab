"""
tests/test_runtime_dependency_classification.py
=============================================================================
Regression & Acceptance Test Suite for Runtime Dependency Classification.
Verifies that:
1. ohlcv.parquet is classified as RUNTIME_INFERENCE and is strictly required.
2. iv7d.parquet is classified as RESEARCH_BENCHMARK (historical VOL-EDGE-01).
3. Missing iv7d.parquet does NOT block runtime freeze verification.
4. In --audit-all mode, missing iv7d.parquet is flagged for research reproducibility.
5. Missing ohlcv.parquet correctly FAILS closed.
6. The active model feature schema contains zero implied volatility features.
=============================================================================
"""

import os
import sys
import subprocess
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from validation.dependency_schema import (
    classify_dependency,
    is_runtime_dependency,
    is_research_benchmark,
    validate_runtime_dependencies,
    validate_research_benchmarks,
    RUNTIME_INFERENCE_DEPENDENCIES,
    HISTORICAL_RESEARCH_BENCHMARKS
)
from research.freeze_har_rs_dow import FEATURE_SCHEMA


def test_dependency_classification_rules():
    """Verifies that data files are correctly categorized."""
    assert classify_dependency("ohlcv.parquet") == "RUNTIME_INFERENCE"
    assert classify_dependency("data/raw/ohlcv.parquet") == "RUNTIME_INFERENCE"
    assert is_runtime_dependency("ohlcv.parquet") is True
    assert is_research_benchmark("ohlcv.parquet") is False

    assert classify_dependency("iv7d.parquet") == "RESEARCH_BENCHMARK"
    assert classify_dependency("data/raw/iv7d.parquet") == "RESEARCH_BENCHMARK"
    assert is_research_benchmark("iv7d.parquet") is True
    assert is_runtime_dependency("iv7d.parquet") is False

    assert classify_dependency("funding.parquet") == "RESEARCH_BENCHMARK"
    assert classify_dependency("onchain.parquet") == "RESEARCH_BENCHMARK"
    assert is_research_benchmark("funding.parquet") is True
    assert is_runtime_dependency("funding.parquet") is False

    assert classify_dependency("unknown_data.parquet") == "UNKNOWN"


def test_runtime_dependencies_presence():
    """Verifies that all runtime inference dependencies exist in data/raw."""
    data_dir = os.path.join(REPO_ROOT, "data", "raw")
    all_present, missing = validate_runtime_dependencies(data_dir)
    assert all_present is True, f"Missing required runtime dependencies: {missing}"
    assert "ohlcv.parquet" not in missing


def test_research_benchmark_isolation():
    """Verifies that iv7d is identified as an offline research benchmark."""
    data_dir = os.path.join(REPO_ROOT, "data", "raw")
    _, missing_benchmarks = validate_research_benchmarks(data_dir)
    # iv7d.parquet is missing from disk; this must be recognized without affecting runtime deps
    assert "iv7d.parquet" in missing_benchmarks


def test_active_model_feature_schema_contains_zero_iv():
    """Guarantees that HAR-RS-DOW contains zero implied volatility features."""
    for feat in FEATURE_SCHEMA:
        assert "iv" not in feat.lower(), f"Unexpected IV feature '{feat}' in HAR-RS-DOW schema"
        assert "deribit" not in feat.lower(), f"Unexpected Deribit feature '{feat}' in schema"


def test_freeze_verifier_runtime_mode_exit_code():
    """
    Verifies that running verify_freeze_manifest.py in runtime mode
    does NOT fail due to missing iv7d.parquet research benchmark.
    """
    verifier_path = os.path.join(REPO_ROOT, "research", "verify_freeze_manifest.py")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    res = subprocess.run(
        [sys.executable, "-X", "utf8", verifier_path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=30
    )
    # In runtime mode, exit code must be 0 (all critical checks passed)
    assert res.returncode == 0, f"Verifier failed in runtime mode:\n{res.stdout}\n{res.stderr}"
    assert "ALL_CHECKS_PASSED" in res.stdout
    assert "Research benchmark — iv7d.parquet (informational)" in res.stdout


def test_freeze_verifier_audit_all_mode_flags_missing_benchmark():
    """
    Verifies that running verify_freeze_manifest.py with --audit-all
    correctly flags missing iv7d.parquet for research reproducibility.
    """
    verifier_path = os.path.join(REPO_ROOT, "research", "verify_freeze_manifest.py")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    res = subprocess.run(
        [sys.executable, "-X", "utf8", verifier_path, "--audit-all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=30
    )
    # In audit-all mode, exit code must be 1 (audit failure due to missing benchmark)
    assert res.returncode == 1
    assert "FAIL   Research benchmark — iv7d.parquet" in res.stdout
    assert "FREEZE_BROKEN — 1 critical check(s) failed" in res.stdout


def test_missing_runtime_dependency_fails_closed(tmp_path):
    """Verifies that missing runtime dependencies fail closed with accurate diagnostics."""
    empty_dir = str(tmp_path / "empty_raw")
    os.makedirs(empty_dir, exist_ok=True)
    all_present, missing = validate_runtime_dependencies(empty_dir)
    assert all_present is False
    assert "ohlcv.parquet" in missing

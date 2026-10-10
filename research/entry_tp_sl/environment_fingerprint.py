"""Deterministic fingerprint for the isolated Entry/TP/SL research environment."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path
from typing import Any

TRACK_ROOT = Path(__file__).resolve().parent
INPUT_FILES = (
    ".python-version",
    "requirements.in",
    "requirements.lock",
    "runtime.env",
    "environment_fingerprint.py",
)
REQUIRED_DISTRIBUTIONS = (
    "numpy",
    "pandas",
    "scipy",
    "scikit-learn",
    "lightgbm",
    "pytest",
    "pytest-asyncio",
    "anyio",
    "pytest-timeout",
    "jsonschema",
    "hypothesis",
)


def build_fingerprint() -> dict[str, Any]:
    files = {}
    for relative_path in INPUT_FILES:
        content = (TRACK_ROOT / relative_path).read_bytes()
        files[relative_path] = hashlib.sha256(content).hexdigest()

    expected_python = (TRACK_ROOT / ".python-version").read_text(encoding="ascii").strip()
    actual_python = platform.python_version()
    packages = {}
    for distribution in REQUIRED_DISTRIBUTIONS:
        try:
            packages[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            packages[distribution] = None

    payload = {
        "track_id": "BTC-ENTRY-TP-SL-V3",
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python_expected": expected_python,
        "python_actual": actual_python,
        "inputs_sha256": files,
        "installed_distributions": packages,
    }
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    environment_sha256 = hashlib.sha256(canonical_payload).hexdigest()
    environment_ready = (
        actual_python == expected_python
        and all(version is not None for version in packages.values())
    )

    return {
        **payload,
        "environment_sha256": environment_sha256,
        "status": "READY" if environment_ready else "LOCKED_NOT_INSTANTIATED",
    }


if __name__ == "__main__":
    print(json.dumps(build_fingerprint(), indent=2, sort_keys=True))

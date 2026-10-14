"""README must describe the current monitor without unsupported research claims."""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

README_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "README.md"))


def test_readme_contract_presence():
    assert os.path.exists(README_PATH)

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "BTCognitive serves one web frontend" in content
    assert "Frozen model inputs remain unverified" in content
    assert "Production forecasts remain blocked" in content
    assert "calibrated 90% confidence interval" in content
    assert "do not add fabricated prices, performance metrics, confidence scores, datasets" in content.casefold()
    assert "Read-only market-data access; no broker/order execution" in content
    assert "Provider outages, stale observations and insufficient history must result in explicit unavailable states" in content
    assert "v3.0.0-ridge-volatility-context" not in content
    assert "VALIDATED_PRODUCTION_RANGE_SYSTEM" not in content

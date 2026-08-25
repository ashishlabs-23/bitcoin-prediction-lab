"""
tests/test_readme_contract.py — Unit Tests for Canonical README Contract Integrity
==================================================================================
Verifies that README.md contains:
1. Production model and 24h horizon
2. 5m Hawkes shadow model status
3. Zero real-trading and directional alpha disclaimers
4. Validation methodology, MFE/MAE excursion definitions, and volatility context
5. Foundation model research findings and stop rule
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

README_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "README.md"))


def test_readme_contract_presence():
    assert os.path.exists(README_PATH)

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Core system declarations
    assert "v3.0.0-ridge-volatility-context" in content
    assert "v1.0.0-challenger-hawkes-microstructure" in content
    assert "VALIDATED_PRODUCTION_RANGE_SYSTEM" in content
    assert "VALIDATED_SHADOW_MODEL" in content
    assert "FOUNDATION_RESEARCH" in content

    # Metrics & Definitions
    assert "MFE" in content
    assert "MAE" in content
    assert "Winkler Score" in content
    assert "Volatility Term Structure" in content
    assert "0.3980%" in content
    assert "605.10" in content

    # Disclaimers & Safety Invariants
    assert "It does not claim guaranteed direction or profitable automated trading" in content
    assert "Zero Real-Money Trading" in content
    assert "Zero Automatic Retraining" in content
    assert "Zero Automatic Promotion" in content
    assert "Zero Probability Blending" in content
    assert "NO MEASURABLE EDGE" in content
    assert "PRODUCT_FROZEN" in content

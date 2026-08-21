"""
tests/test_regime_contract.py — Unit Tests for Canonical Regime Contract
=======================================================================
Verifies that:
- Every V3 neural detector label maps deterministically to a CanonicalRegime.
- normalize_regime is idempotent for CanonicalRegime and canonical strings.
- Unknown/ambiguous regimes (e.g. "NORMAL") raise RegimeContractError.
- No silent fallbacks exist.
"""

import pytest
from models.regime_contract import (
    CanonicalRegime,
    RegimeContractError,
    normalize_regime,
    is_valid_regime,
    all_canonical_values,
    all_v3_labels,
    V3_TO_CANONICAL
)

def test_v3_to_canonical_mapping_completeness():
    expected_v3 = {
        "Strong Uptrend": CanonicalRegime.TRENDING_BULL,
        "Weak Uptrend": CanonicalRegime.TRENDING_BULL,
        "Sideways": CanonicalRegime.RANGING,
        "Accumulation": CanonicalRegime.RANGING,
        "Distribution": CanonicalRegime.RANGING,
        "High Volatility": CanonicalRegime.HIGH_VOLATILITY,
        "Capitulation": CanonicalRegime.TRENDING_BEAR
    }
    for v3_label, expected_canonical in expected_v3.items():
        assert normalize_regime(v3_label) == expected_canonical
        assert is_valid_regime(v3_label) is True

def test_canonical_idempotence():
    for cr in CanonicalRegime:
        assert normalize_regime(cr) == cr
        assert normalize_regime(cr.value) == cr
        assert is_valid_regime(cr.value) is True

def test_unknown_regime_raises_error():
    invalid_inputs = ["NORMAL", "RANDOM_REGIME", "", "Bullish", "Bearish", "CHOP"]
    for inv in invalid_inputs:
        with pytest.raises(RegimeContractError):
            normalize_regime(inv)
        assert is_valid_regime(inv) is False

def test_all_canonical_values():
    vals = all_canonical_values()
    assert "TRENDING_BULL" in vals
    assert "TRENDING_BEAR" in vals
    assert "RANGING" in vals
    assert "HIGH_VOLATILITY" in vals
    assert "BREAKOUT" in vals
    assert len(vals) == 5

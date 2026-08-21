"""
models/regime_contract.py — Canonical Regime Vocabulary
=========================================================
Single source of truth for all regime string values in the BTCognitive system.

V3 Neural Detector outputs 7 human-readable regime labels.
All downstream runtime code (ensemble, inference, position manager, etc.)
must use the 5 CanonicalRegime values defined here.

DO NOT use raw string literals for regime names in runtime code.
Use CanonicalRegime.<VALUE> or normalize_regime() instead.
"""

from __future__ import annotations
import os
import sys
from enum import Enum
from typing import Union

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ---------------------------------------------------------------------------
# Canonical Regime Enum
# ---------------------------------------------------------------------------

class CanonicalRegime(str, Enum):
    """
    The 5 canonical market regime identifiers used throughout the runtime system.
    These are the ONLY valid regime strings in:
      - ensemble routing
      - inference service
      - position manager
      - opportunity detector
      - market memory records
    """
    TRENDING_BULL   = "TRENDING_BULL"
    TRENDING_BEAR   = "TRENDING_BEAR"
    RANGING         = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    BREAKOUT        = "BREAKOUT"


# ---------------------------------------------------------------------------
# V3 Neural Detector -> Canonical Mapping
# ---------------------------------------------------------------------------

# Semantic rationale for each mapping:
#   "Strong Uptrend"  -> TRENDING_BULL:   High ADX + positive EMA slope. Bull ensemble branch.
#   "Weak Uptrend"    -> TRENDING_BULL:   Directional upside with lower conviction. Same branch.
#   "Sideways"        -> RANGING:         Lateral price action. Range-bound ensemble branch.
#   "Accumulation"    -> RANGING:         Sideways base-building. Treated identically by ensemble.
#   "Distribution"    -> RANGING:         Late-cycle sideways. Treated identically by ensemble.
#   "High Volatility" -> HIGH_VOLATILITY: Exact semantic match.
#   "Capitulation"    -> TRENDING_BEAR:   Sharp downside event. Nearest bear equivalent.
#
# NOTE: "BREAKOUT" has NO V3 source. It may be emitted by genome/fitness heuristics only.
#       It remains a valid CanonicalRegime value for those consumers.

V3_TO_CANONICAL: dict[str, CanonicalRegime] = {
    "Strong Uptrend":  CanonicalRegime.TRENDING_BULL,
    "Weak Uptrend":    CanonicalRegime.TRENDING_BULL,
    "Sideways":        CanonicalRegime.RANGING,
    "Accumulation":    CanonicalRegime.RANGING,
    "Distribution":    CanonicalRegime.RANGING,
    "High Volatility": CanonicalRegime.HIGH_VOLATILITY,
    "Capitulation":    CanonicalRegime.TRENDING_BEAR,
}

# All valid canonical string values (V2-style, for O(1) lookup)
_CANONICAL_VALUES: frozenset[str] = frozenset(r.value for r in CanonicalRegime)

# All valid V3 source labels (for validation)
_V3_LABELS: frozenset[str] = frozenset(V3_TO_CANONICAL.keys())


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class RegimeContractError(ValueError):
    """
    Raised when an unknown regime string is encountered.
    This is a HARD ERROR — the system must not silently fall back to a default
    regime because that would corrupt ensemble routing.
    """
    pass


# ---------------------------------------------------------------------------
# normalize_regime() — The primary public API
# ---------------------------------------------------------------------------

def normalize_regime(raw: Union[str, CanonicalRegime]) -> CanonicalRegime:
    """
    Maps any regime string (V3 neural label or V2/canonical string) to a
    CanonicalRegime enum value.

    Rules:
      - If already a CanonicalRegime: returned as-is (idempotent).
      - If a V3 label: mapped via V3_TO_CANONICAL.
      - If a canonical string literal: returned as CanonicalRegime.
      - If unknown: raises RegimeContractError (NO silent fallback).

    Args:
        raw: Raw regime string from classify_regimes() or genome/fitness code.

    Returns:
        CanonicalRegime enum value.

    Raises:
        RegimeContractError: If the string does not map to any known regime.
    """
    # Already a CanonicalRegime instance
    if isinstance(raw, CanonicalRegime):
        return raw

    raw_str = str(raw).strip()

    # Direct canonical string match (idempotent for V2 strings like "TRENDING_BULL")
    if raw_str in _CANONICAL_VALUES:
        return CanonicalRegime(raw_str)

    # V3 neural label -> canonical
    if raw_str in V3_TO_CANONICAL:
        return V3_TO_CANONICAL[raw_str]

    # Unknown -> hard error, never silent fallback
    raise RegimeContractError(
        f"REGIME_CONTRACT_ERROR: Unknown regime '{raw_str}'. "
        f"Valid V3 labels: {sorted(_V3_LABELS)}. "
        f"Valid canonical values: {sorted(_CANONICAL_VALUES)}. "
        f"If this is a new regime, update V3_TO_CANONICAL in models/regime_contract.py."
    )


def is_valid_regime(raw: str) -> bool:
    """Returns True if the string maps to a valid CanonicalRegime, False otherwise."""
    try:
        normalize_regime(raw)
        return True
    except RegimeContractError:
        return False


def all_canonical_values() -> list[str]:
    """Returns sorted list of all canonical regime string values."""
    return sorted(_CANONICAL_VALUES)


def all_v3_labels() -> list[str]:
    """Returns sorted list of all V3 neural detector output labels."""
    return sorted(_V3_LABELS)


# ---------------------------------------------------------------------------
# Self-test (run as script)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Regime Contract Self-Test")
    print()

    errors = []

    # Test all V3 labels
    for v3, expected in V3_TO_CANONICAL.items():
        result = normalize_regime(v3)
        status = "PASS" if result == expected else "FAIL"
        if status == "FAIL":
            errors.append(f"  {v3} -> {result} (expected {expected})")
        print(f"  {status}: '{v3}' -> {result.value}")

    print()

    # Test idempotence for all canonical values
    for cr in CanonicalRegime:
        result = normalize_regime(cr.value)
        status = "PASS" if result == cr else "FAIL"
        if status == "FAIL":
            errors.append(f"  Idempotence fail: {cr.value} -> {result}")
        print(f"  {status}: '{cr.value}' (idempotent) -> {result.value}")

    print()

    # Test unknown raises error
    try:
        normalize_regime("NORMAL")
        errors.append("  FAIL: 'NORMAL' should raise RegimeContractError")
        print("  FAIL: 'NORMAL' did not raise RegimeContractError")
    except RegimeContractError as e:
        print(f"  PASS: 'NORMAL' raises RegimeContractError correctly")

    print()
    if errors:
        print(f"FAIL: {len(errors)} errors")
        for e in errors:
            print(e)
    else:
        print("PASS: All regime contract checks passed.")

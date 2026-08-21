"""
tests/test_market_state_context.py — Unit Tests for Market State Context Validation
===================================================================================
Verifies:
1. Contextual value validation of volatility term structure
2. Final decision CASE C (Volatility term structure is the dominant useful cross-horizon bridge)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.market_state_context_validation import evaluate_market_state_context


def test_market_state_context_evaluation():
    df_ctx, meta = evaluate_market_state_context()

    assert len(df_ctx) == 3
    assert meta["verdict"] == "CASE_C_VOLATILITY_TERM_STRUCTURE_IS_DOMINANT_BRIDGE"
    assert meta["is_hypothesis_supported"] is True

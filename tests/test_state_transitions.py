"""
tests/test_state_transitions.py — Unit Tests for Volatility State Transition Probabilities
==========================================================================================
Verifies:
1. Generation of Markov state transition matrix
2. Persistence and duration metrics per volatility state
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.state_transition_analysis import calculate_state_transitions


def test_state_transition_matrix_calculation():
    df_trans, meta = calculate_state_transitions()

    assert len(df_trans) == 4
    assert meta["is_matrix_valid"] is True
    assert "Mean Duration" in df_trans.columns

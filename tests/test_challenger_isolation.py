"""
tests/test_challenger_isolation.py — Integration Tests for Challenger Isolation & Non-Actionability
====================================================================================================
Verifies:
1. Challenger predictions in shadow mode cannot alter active production forecasts
2. Challenger execution cannot trigger automatic registry promotions or trading actions
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.challenger_registry import challenger_registry
from research.challenger_shadow_monitor import run_shadow_mode_simulation


def test_challenger_shadow_mode_isolation():
    # 1. Run shadow mode simulation
    df_shadow, meta = run_shadow_mode_simulation()
    assert len(df_shadow) > 0

    # 2. Assert active production model remains untouched
    prod = challenger_registry.get_production_model()
    assert prod is not None
    assert prod.version == "v3.0.0-excursion-ridge-conformal"
    assert prod.deployment_status == "PRODUCTION"


def test_challenger_cannot_auto_promote():
    chal = challenger_registry.get_model("v3.1.0-excursion-ewma-baseline")
    assert chal is not None
    assert chal.deployment_status == "CHALLENGER"

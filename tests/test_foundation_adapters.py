"""
tests/test_foundation_adapters.py — Unit Tests for Foundation Model Adapters
============================================================================
Verifies:
1. Interface conformance for TimesFM, Moirai, and Chronos adapters
2. Input preparation, forecasting, validation, and provenance generation
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.foundation.timesfm_adapter import timesfm_adapter
from models.foundation.moirai_adapter import moirai_adapter
from models.foundation.chronos_adapter import chronos_adapter
from models.interfaces.foundation_forecaster import FoundationForecast


def test_timesfm_adapter_forecast():
    inputs = timesfm_adapter.prepare_input([65000.0 + i for i in range(150)], context_hours=120)
    fc = timesfm_adapter.forecast(65200.0, inputs)

    assert isinstance(fc, FoundationForecast)
    assert fc.model_name == "TimesFM 2.5"
    assert timesfm_adapter.validate_output(fc) is True
    assert fc.upper_p90_price > fc.lower_p90_price


def test_moirai_adapter_forecast():
    inputs = moirai_adapter.prepare_input([65000.0 + i for i in range(150)], context_hours=120)
    fc = moirai_adapter.forecast(65200.0, inputs)

    assert isinstance(fc, FoundationForecast)
    assert fc.model_name == "Moirai 2.0"
    assert moirai_adapter.validate_output(fc) is True


def test_chronos_adapter_forecast():
    inputs = chronos_adapter.prepare_input([65000.0 + i for i in range(150)], context_hours=120)
    fc = chronos_adapter.forecast(65200.0, inputs)

    assert isinstance(fc, FoundationForecast)
    assert fc.model_name == "Chronos-2"
    assert chronos_adapter.validate_output(fc) is True

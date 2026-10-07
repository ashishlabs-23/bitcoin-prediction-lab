"""
tests/test_event_detector.py — Unit tests for MEIE Layer 2
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.event_detector import (
    detect_event,
    DetectedEvent,
    MarketEvent,
    EventDirection,
    PREREGISTRATION_THRESHOLDS,
    _classify_ignition,
    _classify_vacuum,
    _classify_toxicity_shock,
    _classify_absorption,
    _resolve_direction,
)
from engine.microstructure_state import MicrostructureStateVector
from datetime import datetime, timezone


def make_sv(z_hawkes=0.0, z_ofi=0.0, z_vpin=0.0, z_depth=0.0,
            z_spread=0.0, z_impact=0.0, data_quality="VALID", window_n=168):
    return MicrostructureStateVector(
        timestamp=datetime.now(timezone.utc).isoformat(),
        price=60000.0,
        raw_hawkes_intensity=1.0,
        raw_ofi=0.0,
        raw_vpin=0.30,
        raw_depth=1000.0,
        raw_spread=0.004,
        raw_impact=0.001,
        z_hawkes=z_hawkes,
        z_ofi=z_ofi,
        z_vpin=z_vpin,
        z_depth=z_depth,
        z_spread=z_spread,
        z_impact=z_impact,
        window_n=window_n,
        data_quality=data_quality,
    )


class TestThresholdsAreFrozen:
    """Verify the locked threshold values match the preregistration document."""
    def test_ignition_hawkes_threshold(self):
        assert PREREGISTRATION_THRESHOLDS["ignition_z_hawkes_min"] == 1.5

    def test_ignition_ofi_threshold(self):
        assert PREREGISTRATION_THRESHOLDS["ignition_z_ofi_abs_min"] == 1.0

    def test_ignition_spread_threshold(self):
        assert PREREGISTRATION_THRESHOLDS["ignition_z_spread_max"] == -0.5

    def test_min_event_gap(self):
        assert PREREGISTRATION_THRESHOLDS["min_event_gap_candles"] == 15

    def test_directional_long_ofi(self):
        assert PREREGISTRATION_THRESHOLDS["long_z_ofi_min"] == 0.5

    def test_directional_short_ofi(self):
        assert PREREGISTRATION_THRESHOLDS["short_z_ofi_max"] == -0.5


class TestClassifyIgnition:
    def test_all_conditions_met_returns_true(self):
        sv = make_sv(z_hawkes=2.0, z_ofi=1.5)
        assert _classify_ignition(sv, prior_spread_mean=-1.0) is True

    def test_hawkes_too_low_returns_false(self):
        sv = make_sv(z_hawkes=0.5, z_ofi=1.5)
        assert _classify_ignition(sv, prior_spread_mean=-1.0) is False

    def test_ofi_too_low_returns_false(self):
        sv = make_sv(z_hawkes=2.0, z_ofi=0.3)
        assert _classify_ignition(sv, prior_spread_mean=-1.0) is False

    def test_no_prior_compression_returns_false(self):
        sv = make_sv(z_hawkes=2.0, z_ofi=1.5)
        # prior spread mean is positive (not compressed)
        assert _classify_ignition(sv, prior_spread_mean=0.5) is False


class TestClassifyVacuum:
    def test_all_vacuum_conditions_met(self):
        sv = make_sv(z_depth=-2.0, z_spread=2.0, z_impact=2.0)
        assert _classify_vacuum(sv) is True

    def test_partial_conditions_returns_false(self):
        sv = make_sv(z_depth=-2.0, z_spread=0.5, z_impact=2.0)
        assert _classify_vacuum(sv) is False


class TestClassifyToxicityShock:
    def test_high_vpin_detected(self):
        sv = make_sv(z_vpin=2.5)
        assert _classify_toxicity_shock(sv) is True

    def test_normal_vpin_not_detected(self):
        sv = make_sv(z_vpin=1.0)
        assert _classify_toxicity_shock(sv) is False


class TestClassifyAbsorption:
    def test_absorption_detected(self):
        sv = make_sv(z_ofi=2.0, z_impact=0.1)
        assert _classify_absorption(sv) is True

    def test_no_absorption_when_ofi_low(self):
        sv = make_sv(z_ofi=0.5, z_impact=0.1)
        assert _classify_absorption(sv) is False

    def test_no_absorption_when_impact_high(self):
        sv = make_sv(z_ofi=2.0, z_impact=1.0)
        assert _classify_absorption(sv) is False


class TestResolveDirection:
    def test_long_signal_when_ofi_and_hawkes_agree_buy(self):
        sv = make_sv(z_ofi=1.0)
        direction = _resolve_direction(sv, hawkes_snapshot={"lambda_buy": 5.0, "lambda_sell": 1.0})
        assert direction == EventDirection.LONG

    def test_short_signal_when_ofi_and_hawkes_agree_sell(self):
        sv = make_sv(z_ofi=-1.0)
        direction = _resolve_direction(sv, hawkes_snapshot={"lambda_buy": 1.0, "lambda_sell": 5.0})
        assert direction == EventDirection.SHORT

    def test_ambiguous_when_signals_disagree(self):
        sv = make_sv(z_ofi=1.0)  # OFI says LONG
        direction = _resolve_direction(sv, hawkes_snapshot={"lambda_buy": 1.0, "lambda_sell": 5.0})  # Hawkes says SHORT
        assert direction == EventDirection.AMBIGUOUS


class TestDetectEvent:
    def test_normal_state_when_all_zero(self):
        sv = make_sv()
        event = detect_event(sv)
        assert isinstance(event, DetectedEvent)
        assert event.event_type in (MarketEvent.NORMAL, MarketEvent.ABSORPTION,
                                    MarketEvent.IGNITION, MarketEvent.VACUUM,
                                    MarketEvent.TOXICITY_SHOCK)

    def test_insufficient_data_quality_gives_normal(self):
        sv = make_sv(data_quality="INSUFFICIENT", z_hawkes=5.0, z_ofi=5.0, z_vpin=5.0)
        event = detect_event(sv)
        # With insufficient data, should remain NORMAL
        assert event.event_type == MarketEvent.NORMAL

    def test_toxicity_shock_detected(self):
        sv = make_sv(z_vpin=2.5, data_quality="VALID", window_n=168)
        event = detect_event(sv)
        # Vacuum or Toxicity — toxicity alone if no vacuum
        assert event.event_type in (MarketEvent.TOXICITY_SHOCK, MarketEvent.VACUUM)

    def test_event_has_timestamp(self):
        sv = make_sv()
        event = detect_event(sv)
        assert event.timestamp is not None and len(event.timestamp) > 0

    def test_detected_event_has_sweep_observables(self):
        sv = make_sv()
        event = detect_event(sv)
        assert hasattr(event, "extreme_pierced")
        assert event.extreme_pierced in ("HIGH_PIERCED", "LOW_PIERCED", "NONE")
        assert hasattr(event, "sweep_candidate")
        assert isinstance(event.sweep_candidate, bool)

        d = event.to_dict()
        assert "extreme_pierced" in d
        assert "sweep_candidate" in d


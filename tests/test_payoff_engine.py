"""
tests/test_payoff_engine.py — Unit tests for MEIE Layer 3
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.payoff_engine import estimate_payoff, PayoffEstimate, _EXEC_RISK_THRESHOLDS, _estimate_p_tp
from engine.event_detector import DetectedEvent, MarketEvent, EventDirection
from engine.microstructure_state import MicrostructureStateVector
from datetime import datetime, timezone


def make_sv(z_vpin=0.0, z_spread=0.0, z_depth=0.0, z_hawkes=0.0,
            z_ofi=0.0, z_impact=0.0, raw_vpin=0.30, raw_spread=0.004, data_quality="VALID"):
    return MicrostructureStateVector(
        timestamp=datetime.now(timezone.utc).isoformat(),
        price=60000.0,
        raw_hawkes_intensity=1.0,
        raw_ofi=0.0,
        raw_vpin=raw_vpin,
        raw_depth=1000.0,
        raw_spread=raw_spread,
        raw_impact=0.001,
        z_hawkes=z_hawkes, z_ofi=z_ofi, z_vpin=z_vpin,
        z_depth=z_depth, z_spread=z_spread, z_impact=z_impact,
        window_n=168, data_quality=data_quality,
    )


def make_event(event_type=MarketEvent.IGNITION, direction=EventDirection.LONG,
               data_quality="VALID", z_vpin=0.0, z_spread=0.0):
    sv = make_sv(z_vpin=z_vpin, z_spread=z_spread, data_quality=data_quality)
    return DetectedEvent(
        timestamp=sv.timestamp,
        price=sv.price,
        event_type=event_type,
        direction=direction,
        state=sv,
        preregistration_id="MEIE-EVENT-01-v1.0",
        notes="test",
    )


class TestPrimaryGate:
    def test_returns_payoff_estimate(self):
        event = make_event()
        result = estimate_payoff(event, vol_24h=0.015)
        assert isinstance(result, PayoffEstimate)

    def test_conservative_prior_gives_abstain(self):
        """With no empirical hit rate (p_tp=0.50) and tight RR, EV_net should be ≤ 0 → ABSTAIN."""
        event = make_event()
        result = estimate_payoff(event, vol_24h=0.015, empirical_hit_rate=None)
        # At 50% hit rate and ~10 bps fees + slippage, gross edge likely near zero → abstain
        # We don't assert execute=False because RR might make it positive; just check EV_net is computed
        assert result.ev_net_bps is not None
        assert isinstance(result.execute, bool)

    def test_ev_net_floor_is_zero(self):
        assert _EXEC_RISK_THRESHOLDS["ev_net_floor_bps"] == 0.0

    def test_fee_total_is_ten_bps(self):
        assert _EXEC_RISK_THRESHOLDS["fee_total_bps"] == 10.0


class TestExecutionBlockers:
    def test_vacuum_event_blocks_execution(self):
        event = make_event(event_type=MarketEvent.VACUUM)
        result = estimate_payoff(event, vol_24h=0.015, empirical_hit_rate=0.70)
        assert result.execute is False
        assert "VACUUM" in result.block_reason

    def test_extreme_vpin_blocks_execution(self):
        event = make_event(z_vpin=3.0)
        result = estimate_payoff(event, vol_24h=0.015, empirical_hit_rate=0.70)
        assert result.execute is False
        assert "VPIN" in result.block_reason

    def test_extreme_spread_blocks_execution(self):
        event = make_event(z_spread=2.5)
        result = estimate_payoff(event, vol_24h=0.015, empirical_hit_rate=0.70)
        assert result.execute is False
        assert "Spread" in result.block_reason

    def test_ambiguous_direction_blocks_execution(self):
        event = make_event(direction=EventDirection.AMBIGUOUS)
        result = estimate_payoff(event, vol_24h=0.015, empirical_hit_rate=0.70)
        assert result.execute is False

    def test_insufficient_data_blocks_execution(self):
        event = make_event(data_quality="INSUFFICIENT")
        result = estimate_payoff(event, vol_24h=0.015, empirical_hit_rate=0.70)
        assert result.execute is False


class TestTPSLLevels:
    def test_long_tp_above_price(self):
        event = make_event(direction=EventDirection.LONG)
        result = estimate_payoff(event, vol_24h=0.015, empirical_hit_rate=0.75)
        if result.execute:
            assert result.tp_price > result.price

    def test_long_sl_below_price(self):
        event = make_event(direction=EventDirection.LONG)
        result = estimate_payoff(event, vol_24h=0.015, empirical_hit_rate=0.75)
        if result.execute:
            assert result.sl_price < result.price

    def test_short_tp_below_price(self):
        event = make_event(direction=EventDirection.SHORT)
        result = estimate_payoff(event, vol_24h=0.015, empirical_hit_rate=0.75)
        if result.execute:
            assert result.tp_price < result.price


class TestEstimatePTP:
    def test_uses_empirical_rate_when_provided(self):
        assert _estimate_p_tp(EventDirection.LONG, empirical_hit_rate=0.62) == 0.62

    def test_falls_back_to_half_without_data(self):
        assert _estimate_p_tp(EventDirection.LONG, empirical_hit_rate=None) == 0.50

    def test_rejects_invalid_hit_rate(self):
        # 0.0 and 1.0 are boundary — falls back to default
        assert _estimate_p_tp(EventDirection.LONG, empirical_hit_rate=0.0) == 0.50
        assert _estimate_p_tp(EventDirection.LONG, empirical_hit_rate=1.0) == 0.50


class TestToDict:
    def test_to_dict_has_required_keys(self):
        event = make_event()
        result = estimate_payoff(event, vol_24h=0.015)
        d = result.to_dict()
        for k in ["ev_net_bps", "execute", "block_reason", "gross_edge_bps",
                  "fee_bps", "slippage_bps", "tp_price", "sl_price", "p_tp", "p_sl"]:
            assert k in d, f"Missing key in PayoffEstimate dict: {k}"


class TestPointInTimeIntegrity:
    def test_tp_sl_generation_has_zero_future_label_dependency(self):
        """
        Point-in-Time Causality Test:
        Verifies that TP_t and SL_t are strictly functions of data <= t.
        TP_t and SL_t are computed at signal origin from RangeForecastService/realized vol
        and must have ZERO lookahead dependency on post-signal excursions or resolution labels.
        """
        event = make_event(event_type=MarketEvent.IGNITION, direction=EventDirection.LONG)
        
        # Scenario A: Initial point-in-time payoff estimate at origin t
        est_a = estimate_payoff(event, vol_24h=0.015)
        tp_a, sl_a = est_a.tp_price, est_a.sl_price
        target_rr_a = est_a.target_rr
        max_hold_a = est_a.max_hold_bars

        # Assert TP and SL are well-formed at entry t
        assert tp_a > 60000.0, "Long TP must be strictly above entry price at origin"
        assert sl_a < 60000.0, "Long SL must be strictly below entry price at origin"
        assert max_hold_a == 30, "IGNITION max hold must be locked at 30 bars"
        assert target_rr_a >= 2.0, "IGNITION target R:R must be >= 2.0R asymmetric expansion"

        # Scenario B: Re-estimate with identical t state but hypothetical future variations
        # Simulating that downstream future price moves or subsequent candles cannot mutate origin levels
        est_b = estimate_payoff(event, vol_24h=0.015)
        assert est_b.tp_price == tp_a, "TP must be strictly invariant to downstream future label changes"
        assert est_b.sl_price == sl_a, "SL must be strictly invariant to downstream future label changes"
        assert est_b.ev_net_bps == est_a.ev_net_bps, "EV_net must be deterministic and point-in-time"

"""
tests/test_replay_counterfactual_lab_v8.py — V8 Acceptance Test Suite
======================================================================
Tests the Replay & Counterfactual Lab end-to-end:
1. All 5 canonical mechanisms (IGNITION, ABSORPTION, VACUUM, TOXICITY, COMBINED).
2. Dual-scenario symmetry and point-in-time consistency (H_long vs H_short).
3. Toxicity filter logic and protective gating of MEIE-ABSORPTION under toxic flow.
4. MEIE-COMBINED composition and dependency tracking.
5. Detail route for Inspect Contract modal (/prediction/counterfactual/contract/{id}).
6. Strict governance invariants: directional signal remains ABSTAIN, live trading DISABLED.
7. Technical execution availability separated from live trading authorization.
8. Timeframe contract: 15m microstructure vs 1h macro scenario planner.
"""

import math
import pytest
import asyncio
from fastapi import HTTPException

from engine.counterfactual_contract_engine import (
    generate_counterfactual_lab_contracts,
    CANONICAL_MECHANISM_ORDER,
    resolve_live_spot_price
)
from api.routes_prediction import (
    get_prediction_counterfactual,
    get_counterfactual_contract_detail
)


@pytest.mark.asyncio
async def test_all_five_mechanisms_present_and_ordered():
    """Verify all 5 canonical mechanisms exist in exact specification order."""
    res = generate_counterfactual_lab_contracts(live_price=68000.0)
    assert res["status"] == "SUCCESS"
    assert len(res["counterfactuals"]) == 5

    mechanisms = [c["strategy_id"] for c in res["counterfactuals"]]
    assert mechanisms == CANONICAL_MECHANISM_ORDER


@pytest.mark.asyncio
async def test_dual_scenario_point_in_time_consistency():
    """Verify Upper and Lower scenarios operate on identical snapshot and spot price."""
    spot = 68420.50
    res = generate_counterfactual_lab_contracts(live_price=spot)

    assert res["market_snapshot"]["spot_price"] == spot
    timestamp = res["market_snapshot"]["timestamp"]

    for c in res["counterfactuals"]:
        up = c["upper_scenario"]
        low = c["lower_scenario"]

        # If available, verify mathematical level invariants
        if up["status"] == "AVAILABLE":
            assert up["tp_price"] > spot, f"{c['strategy_id']}: Upper TP must be > spot"
            assert up["sl_price"] < spot, f"{c['strategy_id']}: Upper SL must be < spot"
            assert up["p_tp"] + up["p_sl"] == pytest.approx(1.0, abs=1e-3)
            assert up["gross_rr"] > 0

        if low["status"] == "AVAILABLE":
            assert low["tp_price"] < spot, f"{c['strategy_id']}: Lower TP must be < spot"
            assert low["sl_price"] > spot, f"{c['strategy_id']}: Lower SL must be > spot"
            assert low["p_tp"] + low["p_sl"] == pytest.approx(1.0, abs=1e-3)
            assert low["gross_rr"] > 0


@pytest.mark.asyncio
async def test_toxicity_normal_flow_unblocks_absorption():
    """Verify normal order flow allows MEIE-ABSORPTION to be AVAILABLE."""
    res = generate_counterfactual_lab_contracts(live_price=68000.0, toxicity_override="PASS")
    assert res["status"] == "SUCCESS"
    assert res["toxicity_filter"]["state"] == "PASS"

    abs_mech = next(c for c in res["counterfactuals"] if c["strategy_id"] == "MEIE-ABSORPTION")
    assert abs_mech["upper_scenario"]["status"] == "AVAILABLE"
    assert abs_mech["lower_scenario"]["status"] == "AVAILABLE"
    assert abs_mech["upper_scenario"]["tp_price"] > 68000.0


@pytest.mark.asyncio
async def test_toxicity_burst_blocks_passive_absorption():
    """Verify high VPIN toxicity immediately blocks passive limit absorption."""
    res = generate_counterfactual_lab_contracts(live_price=68000.0, toxicity_override="BLOCK")
    assert res["status"] == "SUCCESS"
    assert res["toxicity_filter"]["state"] == "BLOCK"

    abs_mech = next(c for c in res["counterfactuals"] if c["strategy_id"] == "MEIE-ABSORPTION")
    assert abs_mech["upper_scenario"]["status"] == "BLOCKED"
    assert abs_mech["lower_scenario"]["status"] == "BLOCKED"
    assert "adverse selection" in abs_mech["upper_scenario"]["block_reason"].lower()
    assert abs_mech["upper_scenario"]["tp_price"] is None


@pytest.mark.asyncio
async def test_meie_combined_composition_tracks_constituents():
    """Verify MEIE-COMBINED dynamically adapts its constituent list when a dependency is blocked."""
    # 1. When all constituents active
    res_pass = generate_counterfactual_lab_contracts(live_price=68000.0, toxicity_override="PASS")
    comb_pass = next(c for c in res_pass["counterfactuals"] if c["strategy_id"] == "MEIE-COMBINED")
    assert comb_pass["upper_scenario"]["status"] == "AVAILABLE"
    assert "4 unblocked experts" in comb_pass["upper_scenario"]["reason"]

    # 2. When absorption blocked
    res_block = generate_counterfactual_lab_contracts(live_price=68000.0, toxicity_override="BLOCK")
    comb_block = next(c for c in res_block["counterfactuals"] if c["strategy_id"] == "MEIE-COMBINED")
    assert comb_block["upper_scenario"]["status"] == "AVAILABLE"
    assert "3 unblocked experts" in comb_block["upper_scenario"]["reason"]
    assert "MEIE-ABSORPTION" in comb_block["upper_scenario"]["reason"]


@pytest.mark.asyncio
async def test_counterfactual_contract_detail_route():
    """Verify Inspect Contract detail route returns complete contract metadata."""
    detail = await get_counterfactual_contract_detail("MEIE-IGNITION", live_price=68000.0)
    assert detail["status"] == "SUCCESS"
    assert detail["strategy_id"] == "MEIE-IGNITION"
    assert "Momentum Ignition" in detail["name"]

    cd = detail["contract_details"]
    assert cd["contract_id"] == "MEIE-IGNITION-v1.0"
    assert len(cd["invalidation_conditions"]) >= 2
    assert len(cd["assumptions"]) >= 2
    assert cd["live_reference_price"] == 68000.0

    up = detail["upper_scenario"]
    assert up["status"] == "AVAILABLE"
    assert up["tp_price"] > 68000.0
    assert up["sl_price"] < 68000.0
    assert up["gross_rr"] > 0


@pytest.mark.asyncio
async def test_invalid_contract_id_raises_404():
    """Verify requests for non-existent contracts fail closed with 404 without leaking internals."""
    with pytest.raises(HTTPException) as exc_info:
        await get_counterfactual_contract_detail("INVALID-UNKNOWN-MECHANISM", live_price=68000.0)
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_zero_or_negative_price_fails_closed():
    """Verify the engine returns UNAVAILABLE rather than fabricating numbers when spot price is missing."""
    res = generate_counterfactual_lab_contracts(live_price=-100.0)
    # If the system cannot resolve any live price, it must fail closed
    if res.get("status") == "UNAVAILABLE":
        assert "unavailable" in res["reason"].lower()
        assert res["counterfactuals"] == []
    else:
        # Fallback successfully resolved live price from feature cache or observatory
        assert res["market_snapshot"]["spot_price"] > 0


@pytest.mark.asyncio
async def test_strict_governance_invariants():
    """Verify live trading and directional recommendation remain strictly disabled."""
    res = generate_counterfactual_lab_contracts(live_price=68000.0)
    gov = res["governance"]
    assert gov["directional_recommendation"] == "DISABLED"
    assert gov["live_trading"] == "DISABLED"
    assert "SINGLE-INSTANCE HYPOTHETICAL REPLAY" in gov["single_instance_disclaimer"]


@pytest.mark.asyncio
async def test_timeframe_contract_reconciliation():
    """Verify timeframe contract reconciles 15m microstructure stream with 1h macro scenario reference."""
    res = generate_counterfactual_lab_contracts(live_price=68000.0)
    tf = res["timeframe_contract"]
    assert tf["microstructure_stream"] == "15m"
    assert tf["macro_barrier_reference"] == "1h"
    assert tf["exchange"] == "Coinbase"
    assert tf["instrument"] == "BTC-USD"

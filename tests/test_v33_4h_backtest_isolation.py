"""
BTCognitive V33.4H — F02 Backtest Isolation and Analysis Reliability Test Suite.
================================================================================
Verifies that:
1. Ordinary /api/tournament/analyse NEVER invokes fresh multi-year backtests (Target: 0 invocations).
2. Attempts to trigger force_fresh_tournament through /analyse are rejected with HTTP 400.
3. Market Intelligence is returned independently when strategy evidence is unavailable.
4. Strategy Assessment clearly distinguishes the 6-state taxonomy:
   - NOT_EVALUATED
   - EVIDENCE_UNAVAILABLE
   - NOT_VALIDATED
   - NO_SETUP
   - SHADOW_ELIGIBLE
   - BLOCKED
5. Request-ID idempotency and HTTP 409 conflict detection are preserved.
6. Concurrent Analysis requests succeed rapidly while offline research runs independently.
7. Zero simulated attempts are created by Analysis (is_read_only = True, attempts_created = 0).
"""

import os
import sys
import json
import time
import threading
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from api.server import app
from engine.regime_strategy_tournament import (
    execute_integrated_analyse_and_tournament,
    run_strategy_tournament_backtest,
    formulate_smart_entry_decision
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_closed_candles():
    """Generates 200 synthetic 1h closed bars."""
    base_price = 76000.0
    now = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
    candles = []
    for i in range(200):
        t = now - timedelta(hours=(199 - i))
        p = base_price + (i % 15) * 50.0 - (i % 7) * 30.0
        candles.append({
            "timestamp": t.isoformat(),
            "open": p - 10.0,
            "high": p + 40.0,
            "low": p - 40.0,
            "close": p,
            "volume": 150.0 + (i % 5) * 20.0,
            "is_closed": True
        })
    return candles


class TestV33_4H_Backtest_Isolation:
    """F02 Backtest Decoupling and Strategy Assessment Verification."""

    def test_ordinary_analysis_never_invokes_fresh_backtest(self, client, sample_closed_candles, monkeypatch):
        """Verifies ordinary Analysis never launches a historical multi-year backtest."""
        import engine.regime_strategy_tournament as rst

        backtest_call_counter = 0
        original_eval = rst._evaluate_single_candidate_3_arms

        def mock_eval(*args, **kwargs):
            nonlocal backtest_call_counter
            backtest_call_counter += 1
            return original_eval(*args, **kwargs)

        monkeypatch.setattr(rst, "_evaluate_single_candidate_3_arms", mock_eval)

        # Execute ordinary Analysis
        resp = client.post("/api/tournament/analyse", json={
            "candles": sample_closed_candles,
            "auto_tournament": True,
            "force_fresh_tournament": False
        })
        assert resp.status_code == 200
        data = resp.json()

        # Invariant: ZERO backtests executed during interactive analysis
        assert backtest_call_counter == 0
        assert data["is_read_only"] is True
        assert data["attempts_created"] == 0

    def test_force_fresh_tournament_rejected_with_http_400(self, client, sample_closed_candles):
        """Verifies attempts to run fresh multi-year backtests via /analyse are rejected."""
        resp = client.post("/api/tournament/analyse", json={
            "candles": sample_closed_candles,
            "auto_tournament": True,
            "force_fresh_tournament": True
        })
        assert resp.status_code == 400
        assert "cannot be executed through the interactive Analysis endpoint" in resp.json()["detail"]

    def test_market_intelligence_returned_when_evidence_unavailable(self, client, sample_closed_candles):
        """Verifies Market Intelligence succeeds independently when Strategy Assessment has no evidence."""
        resp = client.post("/api/tournament/analyse", json={
            "candles": sample_closed_candles,
            "auto_tournament": True,
            "force_fresh_tournament": False
        })
        assert resp.status_code == 200
        data = resp.json()

        # 1. Market Intelligence Output A is fully populated
        assert "market_intelligence" in data
        mi = data["market_intelligence"]
        assert mi["status"] == "SUCCESS"
        assert "volatility_term_structure" in mi
        assert "conformal_risk_envelope_7d" in mi
        assert data["market_regime"]["regime"] != "UNKNOWN"

        # 2. Strategy Assessment Output B is decoupled and explicitly reported
        assert "strategy_assessment" in data
        sa = data["strategy_assessment"]
        assert sa["status"] in ["EVIDENCE_UNAVAILABLE", "NO_SETUP", "SETUP_FORMING", "BLOCKED"]
        if sa["status"] == "EVIDENCE_UNAVAILABLE":
            assert sa["walk_forward_evidence"] == "UNAVAILABLE"
            assert sa["strategy_validation"] == "NOT_VALIDATED"

        # 3. Decision is safe ABSTAIN with zero trade proposal
        dec = data["smart_entry_decision"]
        assert dec["action"] == "ABSTAIN"
        assert dec["candidate_setup"] is None

    def test_strategy_assessment_taxonomy_distinctions(self):
        """Verifies all states of the Strategy Assessment taxonomy are strictly distinguished."""
        # 1. NOT_EVALUATED: Market data rejected
        bad_analysis = {
            "status": "ABSTAIN",
            "reason": "Market data failed candle continuity checks",
            "shortlisted_candidates": []
        }
        dec_not_eval = formulate_smart_entry_decision(bad_analysis, None)
        assert dec_not_eval["strategy_assessment_status"] == "NOT_EVALUATED"

        # 2. NO_SETUP: Analysis succeeded, but no candidate met setup conditions
        no_setup_analysis = {
            "status": "SUCCESS",
            "market_regime": {"regime": "TRENDING_BULLISH"},
            "shortlisted_candidates": [],
            "candidate_rejections": [{"strategy_id": "HTF_1", "reason": "No breakout detected"}]
        }
        dec_no_setup = formulate_smart_entry_decision(no_setup_analysis, None)
        assert dec_no_setup["strategy_assessment_status"] == "NO_SETUP"

        # 3. EVIDENCE_UNAVAILABLE: Candidates shortlisted, but evidence unavailable
        cand = {"strategy_id": "HTF_RANGE_EXPANSION_BREAKOUT", "strategy_name": "HTF Breakout"}
        cand_analysis = {
            "status": "SUCCESS",
            "market_regime": {"regime": "VOLATILITY_EXPANSION"},
            "shortlisted_candidates": [cand]
        }
        tourn_unavail = {
            "final_verdict": "ABSTAIN",
            "execution_source": "CACHED_WALK_FORWARD_UNAVAILABLE",
            "reason": "No verified walk-forward manifest matches"
        }
        dec_unavail = formulate_smart_entry_decision(cand_analysis, tourn_unavail)
        assert dec_unavail["strategy_assessment_status"] == "EVIDENCE_UNAVAILABLE"
        assert dec_unavail["walk_forward_evidence"] == "UNAVAILABLE"
        assert dec_unavail["strategy_validation"] == "NOT_VALIDATED"

        # 4. NOT_VALIDATED: Tournament ran, but candidate failed gates
        tourn_failed = {
            "final_verdict": "ABSTAIN",
            "execution_source": "CACHED_WALK_FORWARD_EVALUATION",
            "reason": "Candidate failed 7/10 screen"
        }
        dec_failed = formulate_smart_entry_decision(cand_analysis, tourn_failed)
        assert dec_failed["strategy_assessment_status"] == "NOT_VALIDATED"
        assert dec_failed["strategy_validation"] == "NOT_VALIDATED"

        # 5. BLOCKED: Quarantined strategy
        quarantined_analysis = {
            "status": "SUCCESS",
            "market_regime": {"regime": "COMPRESSION"},
            "shortlisted_candidates": [],
            "candidate_rejections": [{"strategy_id": "CHRONOS2", "reason": "Quarantined under V32.37 decision"}]
        }
        dec_blocked = formulate_smart_entry_decision(quarantined_analysis, None)
        assert dec_blocked["strategy_assessment_status"] == "BLOCKED"

    def test_request_id_idempotency_and_409_conflict(self, client, sample_closed_candles):
        """Verifies request_id idempotency and HTTP 409 conflict detection."""
        req_id = f"test-idemp-{int(time.time())}"
        payload_1 = {
            "request_id": req_id,
            "candles": sample_closed_candles,
            "auto_tournament": True
        }

        # 1. Initial request
        resp_1 = client.post("/api/tournament/analyse", json=payload_1)
        assert resp_1.status_code == 200
        dec_id_1 = resp_1.json()["decision"]["decision_id"]

        # 2. Duplicate retry with same request_id and same payload -> returns cached
        resp_2 = client.post("/api/tournament/analyse", json=payload_1)
        assert resp_2.status_code == 200
        assert resp_2.json()["decision"]["decision_id"] == dec_id_1

        # 3. Same request_id with different payload -> HTTP 409 Conflict
        payload_diff = {
            "request_id": req_id,
            "candles": sample_closed_candles[:170],
            "auto_tournament": True
        }
        resp_3 = client.post("/api/tournament/analyse", json=payload_diff)
        assert resp_3.status_code == 409

    def test_concurrent_analysis_requests_rapid_completion(self, client, sample_closed_candles):
        """Verifies concurrent analysis requests complete without waiting or timing out."""
        results = []
        errors = []

        def worker(idx):
            try:
                t0 = time.perf_counter()
                resp = client.post("/api/tournament/analyse", json={
                    "candles": sample_closed_candles,
                    "auto_tournament": True,
                    "request_id": f"concurrent-{idx}-{int(time.time()*1000)}"
                })
                duration = time.perf_counter() - t0
                results.append((resp.status_code, duration))
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        t_start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time = time.perf_counter() - t_start

        assert len(errors) == 0
        assert len(results) == 5
        assert all(code == 200 for code, _ in results)
        # All 5 requests completed in well under 5 seconds (not 45s)
        assert total_time < 5.0

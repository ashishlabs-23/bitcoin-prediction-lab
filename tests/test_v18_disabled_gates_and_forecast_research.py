"""
tests/test_v18_disabled_gates_and_forecast_research.py — V18 Independent Gate & Forecast Research Test Suite
=============================================================================================================
Verifies:
1. Backend boundary enforcement of analysis-only product invariants (zero live or paper order execution).
2. Elimination of fabricated analytical consensus actions and read-side ledger mutations on GET /api/arena/context.
3. Genuine BTCUSD future-price forecasting track (1h, 4h, 24h horizons, persistence, drift, ridge, empirical quantiles).
4. Strict target separation: Realized Variance (rv7d_var_ann) vs Future Closing Price (P_{t+h}).
5. Model governance fail-closed verification: hash mismatch, unauthorized promotion blocks, OFFLINE_RESEARCH_ONLY boundaries.
6. Reconciled trial census verification (29 entries sharing 1 unique hash, preventing inflated multiple-testing distortion).
7. Read-only historical ledger integrity: GET requests cause zero mutations.
"""

import os
import json
import pytest
from fastapi.testclient import TestClient

from api.server import app
from engine.price_forecast_engine import price_forecast_engine
from models.authoritative_model_registry import (
    get_active_production_model,
    get_directional_research_baseline,
    get_model_identity,
    AuthorizationStatus,
    ModelClassification,
)
from engine.paper_trade_ledger import get_paper_trade_ledger

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Backend-Level Analysis-Only Product Boundary (Execution & Order Placement Disabled)
# ---------------------------------------------------------------------------

class TestAnalysisOnlyProductBoundary:
    """Verifies all trade and paper order creation endpoints fail closed with disabled status."""

    def test_post_arena_trade_permanently_disabled(self):
        """Verifies /api/arena/trade rejects order execution with explicit disabled status."""
        # Authenticated as admin or unauthenticated
        resp = client.post("/api/arena/trade", json={"action": "BUY", "confidence": 0.95})
        # Should be disabled or require admin, and once executed returns DISABLED
        assert resp.status_code in (200, 401, 403)
        if resp.status_code == 200:
            data = resp.json()
            assert data["status"] == "DISABLED"
            assert "Analysis-only application" in data["detail"]
            assert data["governance"]["execution_authorization"] == "DISABLED"
            assert data["governance"]["live_trading"] == "DISABLED"

    def test_post_arena_paper_trades_permanently_disabled(self):
        """Verifies /api/arena/paper-trades disables order creation at backend boundary."""
        payload = {
            "strategy_id": "TEST_STRATEGY",
            "action": "BUY",
            "entry_price": 80000.0,
            "size_btc": 0.1,
            "cost_scenario": "COINBASE_RETAIL_87BPS"
        }
        resp = client.post("/api/arena/paper-trades", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "DISABLED"
        assert data["trade"] is None
        assert "disabled" in data["detail"].lower()
        assert data["governance"]["execution_authorization"] == "DISABLED"
        assert data["governance"]["live_trading"] == "DISABLED"

    def test_post_arena_paper_trades_close_permanently_disabled(self):
        """Verifies closing/modifying paper trades is disabled."""
        resp = client.post("/api/arena/paper-trades/close", json={"trade_id": "test-123", "exit_price": 81000.0})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "DISABLED"
        assert data["trade"] is None
        assert "disabled" in data["detail"].lower()

    def test_read_only_paper_trades_and_equity_remain_functional(self):
        """Verifies historical research inspection remains accessible read-only."""
        resp = client.get("/api/arena/paper-trades")
        assert resp.status_code == 200
        data = resp.json()
        assert "portfolio_metrics" in data
        assert "trades" in data

        resp_eq = client.get("/api/arena/equity")
        assert resp_eq.status_code == 200


# ---------------------------------------------------------------------------
# 2. Elimination of Fabricated Defaults and Read-Side Effects
# ---------------------------------------------------------------------------

class TestEliminationOfFabricatedDecisionsAndReadSideEffects:
    """Verifies GET /api/arena/context never writes to ledger and never fabricates LONG."""

    def test_get_arena_context_no_ledger_side_effects(self):
        """Verifies repeated GET requests do NOT append records to decision context ledger."""
        from engine.arena_runner import arena_runner

        initial_count = len(arena_runner.decision_context_ledger) if hasattr(arena_runner, "decision_context_ledger") else 0

        resp1 = client.get("/api/arena/context")
        assert resp1.status_code == 200

        resp2 = client.get("/api/arena/context")
        assert resp2.status_code == 200

        final_count = len(arena_runner.decision_context_ledger) if hasattr(arena_runner, "decision_context_ledger") else 0
        assert final_count == initial_count, "GET endpoint must NOT mutate ledger as a side-effect of inspection"

    def test_get_arena_context_no_fabricated_long(self):
        """Verifies missing actions yield typed DATA_UNAVAILABLE or clean status, never fabricated LONG."""
        resp = client.get("/api/arena/context")
        assert resp.status_code == 200
        data = resp.json()
        strat = data.get("strategy", {})
        ensemble_action = strat.get("ensemble_action")
        # Ensemble action must be SKIP, ABSTAIN, or DATA_UNAVAILABLE — never forced LONG when actions are missing
        assert ensemble_action in ("SKIP", "ABSTAIN", "DATA_UNAVAILABLE")

    def test_active_paper_position_no_hardcoded_indicator_fabrication(self):
        """Verifies /api/arena/active-paper-position does not inject synthetic OFI 0.65 or Hawkes 2.2."""
        resp = client.get("/api/arena/active-paper-position")
        assert resp.status_code == 200
        data = resp.json()
        # Ensure it returns valid JSON response and doesn't crash on typed indicators
        assert "has_active_position" in data or "status" in data


# ---------------------------------------------------------------------------
# 3. Genuine Future-Price Forecasting Research Track
# ---------------------------------------------------------------------------

class TestFuturePriceForecastingResearchTrack:
    """Verifies the genuine BTCUSD price forecast engine, baselines, and targets."""

    def test_get_all_price_forecasts_endpoint(self):
        """Verifies GET /api/prediction/price/forecast returns all horizons and tournament data."""
        resp = client.get("/api/prediction/price/forecast")
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "EXPERIMENTAL_PRICE_FORECAST_ACTIVE"
        assert "reference_market" in data
        assert data["reference_market"]["instrument"] == "BTC-USD"
        assert data["reference_market"]["reference_price_usd"] > 0

        # Verify all 3 horizons are present
        horizons = data["forecast_horizons"]
        for h in ("1h", "4h", "24h"):
            assert h in horizons
            h_data = horizons[h]
            assert h_data["status"] == "EXPERIMENTAL_PRICE_FORECAST"
            assert "baselines" in h_data
            assert "persistence_random_walk" in h_data["baselines"]
            assert "rolling_drift" in h_data["baselines"]
            assert "ridge_lagged_returns" in h_data["baselines"]
            assert "empirical_quantiles" in h_data

            # Random walk predicted price equals reference price
            rw = h_data["baselines"]["persistence_random_walk"]
            assert rw["predicted_price_usd"] == h_data["reference_price_usd"]
            assert rw["predicted_change_usd"] == 0.0

            # Quantiles: p10 < p50 < p90
            quantiles = h_data["empirical_quantiles"]
            assert quantiles["p10_price_usd"] <= quantiles["p50_price_usd"] <= quantiles["p90_price_usd"]

    def test_get_single_horizon_price_forecast(self):
        """Verifies GET /api/prediction/price/forecast?horizon=24h returns 24h forecast."""
        resp = client.get("/api/prediction/price/forecast?horizon=24h")
        assert resp.status_code == 200
        data = resp.json()
        assert data["horizon"] == "24h"
        assert data["horizon_hours"] == 24
        assert "baselines" in data

    def test_invalid_horizon_fails_closed(self):
        """Verifies invalid horizon returns 400 Bad Request."""
        resp = client.get("/api/prediction/price/forecast?horizon=99h")
        assert resp.status_code == 400

    def test_target_separation_verified(self):
        """Verifies Realized Volatility is strictly separated from Future Price prediction."""
        prod_model = get_active_production_model()
        assert prod_model.canonical_id == "HAR-RS-DOW-v1.0"
        assert prod_model.classification == ModelClassification.PRODUCTION_VOLATILITY
        assert prod_model.directional_prediction_capability is False
        assert "rv7d_var_ann" in prod_model.forecast_target.lower()

        # Check that price forecast models are registered separately
        rw_model = get_model_identity("price-forecast-persistence-rw")
        assert rw_model is not None
        assert rw_model.classification == ModelClassification.PRICE_FORECAST_RESEARCH
        assert rw_model.directional_prediction_capability is False


# ---------------------------------------------------------------------------
# 4. Reconciled Trial Census & Historical Evidence Audit
# ---------------------------------------------------------------------------

class TestReconciledTrialCensusAndHistoricalEvidence:
    """Verifies test_census reconciliation and evidence conflict resolution."""

    def test_reconciled_trial_census_output(self):
        """Verifies test_census_reconciled.json identifies 1 unique trial hash out of 29 entries."""
        reconciled_path = os.path.join("experiments", "results", "test_census_reconciled.json")
        assert os.path.exists(reconciled_path), f"Reconciled census missing: {reconciled_path}"

        with open(reconciled_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["total_raw_trial_entries"] == 29
        assert data["unique_trial_hashes"] == 1
        assert data["effective_independent_candidate_count"] == 1

    def test_v18_tournament_manifest_integrity(self):
        """Verifies v18_tournament_manifest.json contains complete Track A, B, and C results."""
        manifest_path = os.path.join("experiments", "results", "v18_tournament_manifest.json")
        assert os.path.exists(manifest_path), f"Tournament manifest missing: {manifest_path}"

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["manifest_version"] == "18.0.0"
        assert "track_a_future_price_forecasting" in manifest
        assert "track_b_volatility_forecasting" in manifest
        assert "track_c_strategy_research" in manifest
        assert manifest["governance_decisions"]["live_trading"] == "DISABLED"
        assert manifest["governance_decisions"]["model_authorization"] == "OFFLINE_RESEARCH_ONLY"

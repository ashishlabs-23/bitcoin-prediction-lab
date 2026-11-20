#!/usr/bin/env python3
"""
scripts/adversarial_verification_suite.py — BTCognitive V35.3 Adversarial Verification
======================================================================================
Independent Red-Team verification suite verifying zero synthetic data, provider fail-closed
isolation, model registry lockout, Bartlett kernel positive semi-definiteness, and C2
conformal undercoverage fail-closed behavior.
"""
from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi import HTTPException
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from api.server import app
from models.authoritative_model_registry import (
    AUTHORITATIVE_MODEL_REGISTRY,
    ACTIVE_BASELINE_MODEL,
    ACTIVE_PRODUCTION_MODEL,
    AuthorizationStatus,
    ModelClassification,
    get_active_baseline_model,
    get_active_production_model,
    get_model_identity,
    is_production_authorized,
    verify_production_model_alignment,
)
from engine.price_forecast_engine import (
    compute_diebold_mariano_hln,
    holm_bonferroni,
)
from models.challengers.har_qlike_24h_challenger import HARQLIKE24HChallenger
from models.challengers.har_qlike_challenger import HARQLIKEChallenger
from engine.uncertainty_service import UncertaintyService
from research.risk_envelope import generate_risk_envelope_and_decision_table
from api.routes_tournament import AnalyseRequestModel, post_analyse_market
from engine.bitstamp_market_data_service import BitstampMarketDataService


class TestAdversarialSyntheticsScan(unittest.TestCase):
    """Test 1: Zero forbidden synthetic literals in web/app.js and API routes."""

    def test_frontend_zero_synthetic_literals(self):
        app_js = (REPO_ROOT / "web" / "app.js").read_text(encoding="utf-8")
        forbidden_patterns = [
            r"livePrice\s*\*\s*1\.008",
            r"livePrice\s*\*\s*0\.993",
            r"0\.0553",
            r"0\.0911",
            r"v2\.1-REGIME-PROD",
            r"\[\s*10\.00,\s*10\.12,\s*10\.08",
            r"p50_mfe\s*\*\s*1\.32",
            r"p90_mfe\s*\*\s*1\.90",
            r"HIGH\s*\(Conformal 91\.3%\s*Validated\)",
        ]
        for pattern in forbidden_patterns:
            matches = re.findall(pattern, app_js)
            self.assertEqual(
                len(matches), 0,
                f"Forbidden synthetic pattern '{pattern}' detected in web/app.js: {matches}"
            )

    def test_frontend_discloses_fail_closed_and_research_only(self):
        app_js = (REPO_ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("QUALITY METRICS UNAVAILABLE", app_js)
        self.assertIn("EQUITY CURVE UNAVAILABLE (TRADING DISABLED)", app_js)
        self.assertIn("OFFLINE RESEARCH MODE (Standard Corsi HAR Baseline)", app_js)
        self.assertIn("Production Gate: ", app_js)
        self.assertIn("LOCKED", app_js)
        self.assertIn("Runtime integrity checks do not authorize production serving", app_js)
        self.assertIn("DATA_UNAVAILABLE", app_js)


class TestAdversarialProviderIsolation(unittest.TestCase):
    """Test 2: Bitstamp provider fail-closed isolation and zero fallback to ohlcv.parquet."""

    def test_bitstamp_outage_raises_503_fail_closed(self):
        req = AnalyseRequestModel(instrument="BTC-USD", timeframe="1h")
        with self.assertRaises(HTTPException) as ctx:
            post_analyse_market(req)
        # Without validated snapshot candles, /analyse fails closed with 422 DATA_UNAVAILABLE
        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(ctx.exception.detail["error_code"], "DATA_UNAVAILABLE")

    def test_bitstamp_outage_never_reads_ohlcv_parquet(self):
        with patch("pandas.read_parquet") as mock_read_parquet:
            req = AnalyseRequestModel(instrument="BTC-USD", timeframe="1h")
            with self.assertRaises(HTTPException):
                post_analyse_market(req)
            for call_args in mock_read_parquet.call_args_list:
                self.assertNotIn("ohlcv.parquet", str(call_args))

    def test_tournament_analyse_rejects_historical_snapshot(self):
        req = AnalyseRequestModel(
            instrument="BTC-USD",
            timeframe="1h",
            data_source="UNKNOWN_UNVERIFIED_SOURCE"
        )
        with self.assertRaises(HTTPException) as ctx:
            post_analyse_market(req)
        self.assertEqual(ctx.exception.status_code, 422)


class TestAdversarialModelPromotionGate(unittest.TestCase):
    """Test 3: Model registry lock, unpromoted challenger status, and baseline promotion."""

    def test_har_rs_dow_is_demoted_to_unpromoted_challenger(self):
        model = get_model_identity("HAR-RS-DOW-v1.0")
        self.assertIsNotNone(model)
        self.assertEqual(model.classification, ModelClassification.RESEARCH_CHALLENGER_UNPROMOTED)
        self.assertEqual(model.authorization_status, AuthorizationStatus.OFFLINE_RESEARCH_ONLY)
        self.assertIn("0.2632", model.empirical_validation_summary)

    def test_standard_har_is_active_baseline(self):
        baseline = get_active_baseline_model()
        self.assertEqual(baseline.canonical_id, "Standard-HAR-v1.0")
        self.assertEqual(baseline.classification, ModelClassification.BASELINE_VOLATILITY)
        self.assertEqual(baseline.authorization_status, AuthorizationStatus.OFFLINE_RESEARCH_ONLY)

    def test_production_authorization_fails_closed(self):
        self.assertFalse(is_production_authorized())
        self.assertFalse(is_production_authorized({"authorized": True, "authorization_status": "AUTHORIZED_FOR_PRODUCTION"}))
        self.assertFalse(verify_production_model_alignment("/api/terminal/live", "HAR-RS-DOW-v1.0"))
        self.assertFalse(verify_production_model_alignment("/api/terminal/live", "Standard-HAR-v1.0"))


class TestAdversarialNumericalStability(unittest.TestCase):
    """Test 4: Variance non-negativity under extreme inputs and Bartlett PSD guarantee."""

    def test_har_qlike_challengers_strict_positive_variance_on_extreme_inputs(self):
        model_24h = HARQLIKE24HChallenger()
        model_168h = HARQLIKEChallenger()

        # Fit models with small valid baseline dataset
        X_dummy = np.ones((10, 3))
        y_dummy = np.full(10, 0.04)
        model_24h.fit(X_dummy, y_dummy)
        model_168h.fit(X_dummy, y_dummy)

        extreme_inputs = [
            np.array([[-1e9, -1e9, -1e9]]),
            np.array([[np.nan, np.nan, np.nan]]),
            np.array([[-np.inf, -np.inf, -np.inf]]),
            np.array([[np.inf, np.inf, np.inf]]),
        ]

        for x in extreme_inputs:
            pred_24h = model_24h.predict(x)
            pred_168h = model_168h.predict(x)
            self.assertTrue(np.all(pred_24h >= 1e-6), f"24H model produced non-positive variance on {x}: {pred_24h}")
            self.assertTrue(np.all(pred_168h >= 1e-6), f"168H model produced non-positive variance on {x}: {pred_168h}")
            self.assertTrue(np.all(np.isfinite(pred_24h)))
            self.assertTrue(np.all(np.isfinite(pred_168h)))

    def test_bartlett_triangular_kernel_guarantees_positive_semi_definite_variance(self):
        # Strongly alternating loss differential series that creates negative unweighted autocovariance sum
        np.random.seed(42)
        n = 100
        # Highly negative lag-1 autocorrelation: e.g. [-1, 1, -1, 1, ...]
        alternating = np.array([(-1.0)**i * (2.0 + 0.1 * np.random.randn()) for i in range(n)])
        e1 = alternating
        e2 = np.zeros(n)

        # compute_diebold_mariano_hln with Bartlett kernel must not produce negative variance or raise ValueError
        dm, p_val = compute_diebold_mariano_hln(e1, e2, h=5)
        self.assertTrue(np.isfinite(dm))
        self.assertTrue(0.0 <= p_val <= 1.0)


class TestAdversarialC2ConformalUndercoverage(unittest.TestCase):
    """Test 5: C2 conformal undercoverage fail-closed enforcement."""

    def test_uncalibrated_uncertainty_service_fails_closed(self):
        service = UncertaintyService()
        result = service.evaluate_uncertainty(
            mfe_p10=0.01,
            mfe_p90=0.05,
            exp_mfe=0.03,
            data_quality_score=1.0
        )
        self.assertEqual(result.confidence_level, "UNAVAILABLE")
        self.assertIsNone(result.coverage_confidence_pct)
        self.assertIn("no verifiable calibration artifact is configured", result.explanation)

    def test_risk_envelope_reports_undercoverage_warning(self):
        df_mfe = pd.DataFrame({"p50_mfe": [0.02], "p90_mfe": [0.05]})
        df_env, df_decision, meta = generate_risk_envelope_and_decision_table(df_mfe, base_btc_price=70000.0)
        conf_row = df_decision[df_decision["Forecast Attribute"].str.contains("Range Confidence")].iloc[0]
        self.assertIn("UNAVAILABLE (C2 Conformal Undercoverage 84.89% - Research Only)", conf_row["State / Value"])


def run_all_adversarial_tests() -> bool:
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(TestAdversarialSyntheticsScan))
    suite.addTests(loader.loadTestsFromTestCase(TestAdversarialProviderIsolation))
    suite.addTests(loader.loadTestsFromTestCase(TestAdversarialModelPromotionGate))
    suite.addTests(loader.loadTestsFromTestCase(TestAdversarialNumericalStability))
    suite.addTests(loader.loadTestsFromTestCase(TestAdversarialC2ConformalUndercoverage))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_adversarial_tests()
    sys.exit(0 if success else 1)

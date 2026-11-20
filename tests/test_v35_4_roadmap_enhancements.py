"""
tests/test_v35_4_roadmap_enhancements.py — Verification of V35.4 Econometric & API Improvements
=================================================================================================
Validates:
1. Unified terminal bundle endpoint GET /api/terminal/bundle.
2. WebSocket tick event symbol alignment to BTC-USD in CandleManager.
3. Parkinson volatility annualization parameterization in strategy_signal_engine.
4. Frequency-based annualization (freq="1h", freq="1d") across Sharpe, Sortino, and Calmar ratios.
5. Content Security Policy and ErrorBoundary integration markers.
"""

import math
import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.server import app
from api.candle_manager import CandleManager
from engine.strategy_signal_engine import compute_parkinson_volatility
from models.risk_metrics import sharpe_ratio, sortino_ratio, calmar_ratio


def test_terminal_bundle_endpoint():
    """Verify /api/terminal/bundle returns atomic consolidated state with governance."""
    client = TestClient(app)
    res = client.get("/api/terminal/bundle")
    assert res.status_code == 200
    data = res.json()
    assert data["bundle_version"] == "v35.4"
    assert "governance" in data
    assert data["governance"]["live_trading"] == "DISABLED"
    assert data["governance"]["execution_authorization"] == "DISABLED"
    assert data["governance"]["authoritative_provider"] == "BITSTAMP"
    assert "terminal_live" in data
    assert "system_status" in data
    assert "authoritative_models" in data


def test_candle_manager_tick_symbol_alignment():
    """Verify CandleManager constructs tick events with symbol 'BTC-USD'."""
    cm = CandleManager(interval_seconds=60)
    tick_event, closed_event = cm.process_tick(price=85000.0, volume=1.2)
    assert tick_event["symbol"] == "BTC-USD"
    assert tick_event["price"] == 85000.0


def test_parkinson_volatility_annualization():
    """Verify Parkinson volatility annualize=True scales by sqrt(8760)."""
    highs = np.array([105.0] * 24, dtype=np.float64)
    lows = np.array([95.0] * 24, dtype=np.float64)
    vol_raw = compute_parkinson_volatility(highs, lows, annualize=False)
    vol_ann = compute_parkinson_volatility(highs, lows, annualize=True)
    expected_scale = math.sqrt(8760.0)
    assert abs(vol_ann / vol_raw - expected_scale) < 1e-4


def test_sharpe_and_calmar_freq_annualization():
    """Verify freq='1h' annualizes with 8760 and freq='1d' with 365."""
    returns = [0.001, -0.0005, 0.002, 0.0008, -0.0003]
    equity = [100.0, 100.1, 100.05, 100.25, 100.33, 100.30]

    # Sharpe
    sr_1h = sharpe_ratio(returns, freq="1h")
    sr_1d = sharpe_ratio(returns, freq="1d")
    assert abs(sr_1h / sr_1d - math.sqrt(8760 / 365)) < 0.05

    # Sortino
    so_1h = sortino_ratio(returns, freq="1h")
    so_1d = sortino_ratio(returns, freq="1d")
    assert abs(so_1h / so_1d - math.sqrt(8760 / 365)) < 0.05

    # Calmar
    calmar_1h = calmar_ratio(returns, equity, freq="1h")
    calmar_1d = calmar_ratio(returns, equity, freq="1d")
    assert abs(calmar_1h / calmar_1d - (8760 / 365)) < 0.05


def test_frontend_csp_and_error_boundary():
    """Verify that index.html contains Content-Security-Policy and app.js contains AppErrorBoundary."""
    with open("web/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    assert "Content-Security-Policy" in html

    with open("web/app.js", "r", encoding="utf-8") as f:
        js = f.read()
    assert "class AppErrorBoundary" in js
    assert "AppErrorBoundary" in js

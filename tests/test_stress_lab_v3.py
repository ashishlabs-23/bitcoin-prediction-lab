"""
tests/test_stress_lab_v3.py — Unit Tests for BTCognitive V3 Stress Testing Laboratory
=====================================================================================
Validates:
  - Generation of all 5 stress test scenarios (Flash Crash, Low Liquidity, High Volatility, News Shock, Funding Spike)
  - Measurement of Prediction Stability, Confidence Collapse, Expert Switching, and Drawdown
  - Markdown report generation
  - PDF report generation
"""

import os
import sys
import pytest
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.stress_lab import StressTestScenario, StressTestingLab, run_stress_test_suite


def test_stress_scenarios_generation():
    """Validates that all 5 scenario shock tensor generators return valid shapes without NaN."""
    base = StressTestScenario.generate_baseline(n_samples=10, seq_len=120, n_features=32)
    assert base.shape == (10, 120, 32)
    assert not np.isnan(base).any()

    # 1. Flash Crash
    crash = StressTestScenario.apply_flash_crash(base)
    assert crash.shape == base.shape
    assert crash[:, -1, 5].mean() > base[:, -1, 5].mean() # Volume spike
    assert crash[:, -1, 0].mean() < base[:, -1, 0].mean() # Price drop

    # 2. Low Liquidity
    low_liq = StressTestScenario.apply_low_liquidity(base)
    assert low_liq.shape == base.shape
    assert low_liq[:, :, 9].mean() > base[:, :, 9].mean() # Spread widening

    # 3. High Volatility
    high_vol = StressTestScenario.apply_high_volatility(base)
    assert high_vol.shape == base.shape
    assert high_vol[:, :, 6].mean() > base[:, :, 6].mean() # ATR surge

    # 4. News Shock
    news = StressTestScenario.apply_news_shock(base)
    assert news.shape == base.shape
    assert news[:, -1, 12].mean() < -0.80 # Negative sentiment crash

    # 5. Funding Spike
    funding = StressTestScenario.apply_funding_spike(base)
    assert funding.shape == base.shape
    assert funding[:, :, 10].mean() > base[:, :, 10].mean() # Funding surge


def test_stress_metrics_measurement():
    """Validates computation of stability, confidence collapse, expert switching, and drawdown."""
    lab = StressTestingLab()
    base = StressTestScenario.generate_baseline(n_samples=15)
    crash = StressTestScenario.apply_flash_crash(base)

    res = lab.run_scenario("Flash Crash Test", base, crash)
    assert isinstance(res, dict)

    expected_keys = [
        "scenario", "prediction_stability_pct", "baseline_confidence",
        "shock_confidence", "confidence_collapse_pct", "dominant_expert",
        "dominant_expert_weight_pct", "max_drawdown_pct", "survival_verdict"
    ]
    for k in expected_keys:
        assert k in res

    assert 0.0 <= res["prediction_stability_pct"] <= 100.0
    assert 0.0 <= res["confidence_collapse_pct"] <= 100.0
    assert res["max_drawdown_pct"] >= 0.0
    assert res["dominant_expert"] in ["TrendExpert", "BreakoutExpert", "ScalpingExpert", "VolatilityExpert", "NewsExpert"]


def test_stress_reports_generation(tmp_path):
    """Validates that Markdown and PDF reports are generated and formatted correctly."""
    lab = StressTestingLab()
    results = lab.run_all_scenarios(n_samples=10)
    assert len(results) == 5 # All 5 scenarios evaluated

    md_path = str(tmp_path / "stress_report.md")
    pdf_path = str(tmp_path / "stress_report.pdf")

    # Generate Markdown
    md_res = lab.generate_markdown_report(results, filepath=md_path)
    assert os.path.exists(md_path)
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    assert "Stress Testing Laboratory Report" in md_content
    assert "Flash Crash" in md_content
    assert "High Volatility" in md_content

    # Generate PDF
    pdf_res = lab.generate_pdf_report(results, filepath=pdf_path)
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 500 # Valid non-empty PDF file

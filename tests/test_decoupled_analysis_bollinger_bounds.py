from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import engine.decoupled_analysis_engine as analysis_module
from engine.decoupled_analysis_engine import DecoupledAnalysisEngine


def _closed_candles():
    now = datetime.now(timezone.utc)
    closes = [100.0 + index * 0.05 for index in range(30)]
    return pd.DataFrame(
        {
            "timestamp": [
                (now - timedelta(hours=29 - index)).isoformat()
                for index in range(30)
            ],
            "open": closes,
            "high": [value + 1.0 for value in closes],
            "low": [value - 1.0 for value in closes],
            "close": closes,
            "volume": np.full(30, 1.0),
        }
    )


def _analysis_engine(monkeypatch, classifier_result):
    engine = DecoupledAnalysisEngine()
    monkeypatch.setattr(
        analysis_module.MarketRegimeClassifier,
        "classify",
        lambda _candles: classifier_result,
    )
    monkeypatch.setattr(
        analysis_module,
        "check_data_freshness_and_gaps",
        lambda *_args, **_kwargs: {
            "is_fresh": True,
            "observed_age_seconds": 60.0,
            "has_candle_gaps": False,
            "candle_gap_count": 0,
        },
    )
    engine.range_service.generate_forecast = lambda **_kwargs: SimpleNamespace(
        upper_p10=101.0,
        upper_p50=102.0,
        upper_p90=103.0,
        lower_p10=99.0,
        lower_p50=98.0,
        lower_p90=97.0,
    )
    return engine


@pytest.mark.parametrize(
    "bounds",
    [
        {},
        {"bb_lower": 90.0, "bb_mid": float("nan"), "bb_upper": 110.0},
        {"bb_lower": 100.0, "bb_mid": 100.0, "bb_upper": 110.0},
        {"bb_lower": 90.0, "bb_mid": 100.0, "bb_upper": float("inf")},
        {"bb_lower": True, "bb_mid": 100.0, "bb_upper": 110.0},
        {"bb_lower": 0.0, "bb_mid": 100.0, "bb_upper": 110.0},
        {"bb_lower": 90.0, "bb_mid": 100.0, "bb_upper": 10**10000},
    ],
)
def test_missing_or_invalid_bounds_are_unavailable_and_not_exposed_as_levels(
    monkeypatch, bounds
):
    classifier_result = {
        "regime": "RANGE_BOUND",
        "bbw": 0.02,
        "adx": 20.0,
        "atr": 2.0,
        **bounds,
    }
    engine = _analysis_engine(monkeypatch, classifier_result)
    candles = _closed_candles()
    intelligence = engine.compute_market_intelligence_report(candles, live_price=101.45)

    regime = intelligence["volatility_regime"]
    assert regime["bollinger_bounds_status"] == "UNAVAILABLE"
    assert regime["bollinger_bounds_reason_code"] == "MISSING_OR_INVALID_BOLLINGER_BOUNDS"
    assert regime["bb_lower"] is None
    assert regime["bb_mid"] is None
    assert regime["bb_upper"] is None

    authorization = engine.evaluate_five_question_trade_authorization(
        df_closed=candles,
        live_price=101.45,
        market_intel=intelligence,
    )
    q3 = authorization["five_question_evaluation"]["question_3_entry_location"]
    assert q3["state"] == "FAIL"
    assert q3["status"] == "BLOCKED_BOLLINGER_BOUNDS_UNAVAILABLE"
    assert q3["support_price"] is None
    assert q3["resistance_price"] is None


def test_valid_bounds_are_preserved_in_market_intelligence_and_levels(monkeypatch):
    classifier_result = {
        "regime": "RANGE_BOUND",
        "bbw": 0.02,
        "adx": 20.0,
        "atr": 2.0,
        "bb_lower": 90.0,
        "bb_mid": 100.0,
        "bb_upper": 110.0,
    }
    engine = _analysis_engine(monkeypatch, classifier_result)
    candles = _closed_candles()
    intelligence = engine.compute_market_intelligence_report(candles, live_price=101.45)

    regime = intelligence["volatility_regime"]
    assert regime["bollinger_bounds_status"] == "AVAILABLE"
    assert regime["bollinger_bounds_reason_code"] is None
    assert (regime["bb_lower"], regime["bb_mid"], regime["bb_upper"]) == (90.0, 100.0, 110.0)

    authorization = engine.evaluate_five_question_trade_authorization(
        df_closed=candles,
        live_price=101.45,
        market_intel=intelligence,
    )
    q3 = authorization["five_question_evaluation"]["question_3_entry_location"]
    assert q3["support_price"] == 90.0
    assert q3["resistance_price"] == 110.0
    assert q3["status"] == "ACCEPTABLE"

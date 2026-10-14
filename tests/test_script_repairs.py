import pandas as pd
import pytest

from scripts.regime_heatmap import classify_regime


def test_regime_heatmap_requires_its_calibrated_trend_feature():
    row = pd.Series({
        "sma_ratio_20": 0.2,
        "realized_vol_24h": 0.01,
        "rsi_14": 65.0,
    })

    with pytest.raises(ValueError, match="trend_score"):
        classify_regime(row)


def test_regime_heatmap_uses_supported_trend_score_thresholds():
    row = pd.Series({
        "trend_score": 0.31,
        "realized_vol_24h": 0.01,
        "rsi_14": 61.0,
    })

    assert classify_regime(row) == "BREAKOUT"

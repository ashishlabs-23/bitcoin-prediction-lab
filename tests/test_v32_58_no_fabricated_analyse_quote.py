"""V32.58: Verify POST /api/tournament/analyse never falls back to an invented market quote."""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from unittest.mock import patch
from api.routes_tournament import AnalyseRequestModel, post_analyse_market
from engine.bitstamp_market_data_service import BitstampMarketDataService


def test_analyse_market_without_candles_or_live_price_raises_400(monkeypatch):
    """When neither client candles nor upstream Bitstamp bars are available, reject cleanly instead of using 80000.0."""
    with patch.object(
        BitstampMarketDataService,
        "get_or_refresh_bitstamp_data",
        return_value=(False, None, {"error_code": "MARKET_DATA_UNAVAILABLE", "detail": "Simulated upstream failure"})
    ):
        req = AnalyseRequestModel(
            instrument="BTC-USD",
            timeframe="1h",
            candles=None,
            live_price=None,
        )

        with pytest.raises(HTTPException) as exc_info:
            post_analyse_market(req)

        assert exc_info.value.status_code in (400, 503)
        detail_str = str(exc_info.value.detail)
        assert ("Market data unavailable" in detail_str or "BITSTAMP_RETRIEVAL_FAILED" in detail_str)

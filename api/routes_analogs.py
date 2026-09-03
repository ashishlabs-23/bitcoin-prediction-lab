"""
api/routes_analogs.py — Historical Analog Retrieval API Route (Read-Only)
=========================================================================
Exposes the non-predictive, descriptive historical analog engine over REST:
- GET /research/analogs: Retrieves k=20 nearest historical volatility regimes
  and their realized forward 24h path excursions (MFE/MAE).
"""

import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from research.historical_analogs import get_analog_engine

logger = logging.getLogger("btcognitive.routes_analogs")
router = APIRouter(prefix="/research", tags=["Research Analogs"])


@router.get("/analogs")
def get_historical_analogs(
    k: int = Query(20, ge=1, le=50, description="Maximum number of historical analogs to retrieve"),
    min_similarity: float = Query(0.35, ge=0.0, le=1.0, description="Minimum similarity threshold (0.0 to 1.0)"),
    min_separation_days: float = Query(14.0, ge=0.0, le=90.0, description="Minimum temporal separation in days between analogs"),
    p10_pct: float = Query(-5.0, description="Current lower P10 band percentage for containment check"),
    p90_pct: float = Query(5.0, description="Current upper P90 band percentage for containment check")
):
    """
    Retrieves genuine historical market volatility regimes clearing the similarity threshold.
    DESCRIPTIVE ONLY — NOT A FORECAST.
    """
    try:
        engine = get_analog_engine()
        result = engine.find_analogs(
            max_k=k,
            min_similarity=min_similarity,
            min_separation_days=min_separation_days,
            current_p10_p90_band=(p10_pct / 100.0, p90_pct / 100.0)
        )
        return result
    except Exception as e:
        logger.error(f"Error in /research/analogs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve historical analogs.")

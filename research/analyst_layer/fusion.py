"""
research/analyst_layer/fusion.py — Analyst Layer Factor Fusion Engine
====================================================================
Combines the 4 specialized deterministic analysts into a unified 12-factor matrix:
- Technical Factors (3)
- Order Flow Factors (3)
- Derivatives Factors (3)
- Sentiment & Event Factors (3)
"""

import pandas as pd

from .technical import compute_technical_analyst_factors
from .orderflow import compute_orderflow_analyst_factors
from .derivatives import compute_derivatives_analyst_factors
from .sentiment import compute_sentiment_analyst_factors


def generate_all_analyst_factors(df: pd.DataFrame) -> pd.DataFrame:
    """Computes and concatenates all 12 deterministic analyst factors."""
    tech_f = compute_technical_analyst_factors(df)
    of_f = compute_orderflow_analyst_factors(df)
    deriv_f = compute_derivatives_analyst_factors(df)
    sent_f = compute_sentiment_analyst_factors(df)

    fused = pd.concat([tech_f, of_f, deriv_f, sent_f], axis=1)
    return fused.ffill().fillna(0.0)

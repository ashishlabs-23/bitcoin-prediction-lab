"""
models/experts/__init__.py — BTCognitive V3 Mixture of Experts Module
====================================================================
"""

from models.experts.trend import TrendExpert
from models.experts.breakout import BreakoutExpert
from models.experts.scalping import ScalpingExpert
from models.experts.volatility import VolatilityExpert
from models.experts.news import NewsExpert

EXPERT_CLASSES = {
    "trend": TrendExpert,
    "breakout": BreakoutExpert,
    "scalping": ScalpingExpert,
    "volatility": VolatilityExpert,
    "news": NewsExpert
}

__all__ = [
    "TrendExpert",
    "BreakoutExpert",
    "ScalpingExpert",
    "VolatilityExpert",
    "NewsExpert",
    "EXPERT_CLASSES"
]

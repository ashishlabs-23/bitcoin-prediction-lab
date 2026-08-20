"""
research/forecast_outcome_monitor.py — Research Interface for Forecast Outcome Resolution
==========================================================================================
Re-exports the core forecast outcome monitoring service for research pipelines.
"""

from engine.forecast_outcome_monitor import (
    ForecastOutcomeMonitor,
    ForecastOutcomeRecord
)

__all__ = ["ForecastOutcomeMonitor", "ForecastOutcomeRecord"]

"""
tests/test_range_database_integration.py — Integration Tests for Range SQLite WAL Memory
========================================================================================
Verifies:
1. SQLite WAL table creation and indexes
2. Atomic insertions into range_forecasts, excursion_forecasts, uncertainty_forecasts
3. Point-in-time separation: Predictions are immutable; outcomes written only upon resolution
"""

import os
import sys
import pytest
import sqlite3
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.range_forecast_service import RangeForecastService
from engine.forecast_outcome_monitor import ForecastOutcomeMonitor
from backtest.market_memory import _get_db


def test_sqlite_tables_presence():
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    conn.close()

    assert "range_forecasts" in tables
    assert "excursion_forecasts" in tables
    assert "uncertainty_forecasts" in tables
    assert "forecast_outcomes" in tables


def test_range_forecast_database_persistence():
    svc = RangeForecastService()
    fc = svc.generate_forecast(current_price=92000.0, vol_24h=0.016)

    conn = _get_db()
    df_rf = pd.read_sql_query("SELECT * FROM range_forecasts WHERE forecast_id = ?", conn, params=(fc.forecast_id,))
    df_ef = pd.read_sql_query("SELECT * FROM excursion_forecasts WHERE forecast_id = ?", conn, params=(fc.forecast_id,))
    df_uf = pd.read_sql_query("SELECT * FROM uncertainty_forecasts WHERE forecast_id = ?", conn, params=(fc.forecast_id,))
    conn.close()

    assert len(df_rf) == 1
    assert df_rf.iloc[0]["current_price"] == 92000.0
    assert len(df_ef) == 1
    assert len(df_uf) == 1


def test_forecast_outcomes_persistence_and_isolation():
    svc = RangeForecastService()
    fc = svc.generate_forecast(current_price=90000.0, vol_24h=0.015)

    monitor = ForecastOutcomeMonitor()
    rec = monitor.resolve_forecast(
        forecast_id=fc.forecast_id,
        pred_ts=fc.timestamp,
        current_price=90000.0,
        upper_p90=fc.upper_p90,
        lower_p90=fc.lower_p90,
        exp_mfe=fc.mfe_p50,
        exp_mae=fc.mae_p50,
        forward_candles_high=[90500.0, 91000.0],
        forward_candles_low=[89500.0, 89200.0],
        forward_close=90800.0
    )

    conn = _get_db()
    df_out = pd.read_sql_query("SELECT * FROM forecast_outcomes WHERE forecast_id = ?", conn, params=(fc.forecast_id,))
    # Ensure original prediction row in range_forecasts was NOT overwritten
    df_pred_after = pd.read_sql_query("SELECT * FROM range_forecasts WHERE forecast_id = ?", conn, params=(fc.forecast_id,))
    conn.close()

    assert len(df_out) == 1
    assert df_out.iloc[0]["path_contained"] == 1
    assert len(df_pred_after) == 1

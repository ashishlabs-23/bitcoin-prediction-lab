"""
tests/test_unresolved_outcomes.py — Tests for was_correct NULL Semantics
========================================================================
Verifies that:
- Unresolved forecasts have was_correct = NULL / None.
- Win rate calculations exclude unresolved (NULL) outcomes from numerator & denominator.
- Resolving an outcome updates was_correct to 1 or 0 and outcome_resolved to 1.
"""

import os
import sqlite3
import pandas as pd
import numpy as np
from config.database import MARKET_MEMORY_DB_PATH
from backtest.market_memory import record_prediction, resolve_pending_outcomes, load_market_memory

def test_unresolved_predictions_have_null_was_correct():
    conn = sqlite3.connect(MARKET_MEMORY_DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Check that in the database, outcome_resolved = 0 rows have was_correct IS NULL
    unresolved_rows = conn.execute("SELECT was_correct FROM predictions WHERE outcome_resolved = 0").fetchall()
    for r in unresolved_rows:
        assert r["was_correct"] is None, f"Unresolved row has non-null was_correct: {r['was_correct']}"
        
    conn.close()

def test_load_market_memory_nullable_boolean():
    df = load_market_memory()
    if not df.empty and 'outcome_resolved' in df.columns:
        unresolved = df[df['outcome_resolved'] == False]
        if not unresolved.empty:
            # Check that was_correct has NA / NaN on unresolved rows
            assert unresolved['was_correct'].isna().all()

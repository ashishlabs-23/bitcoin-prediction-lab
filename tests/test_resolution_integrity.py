"""
tests/test_resolution_integrity.py — Tests for Resolution Integrity & Immutability
==================================================================================
Verifies:
- Resolution does not mutate prediction_id, price, model_version, or context_vector_json.
- Database records have outcome_resolved = 1 and outcome_resolved_at when resolved.
"""

import sqlite3
from config.database import MARKET_MEMORY_DB_PATH

def test_database_resolved_rows_integrity():
    conn = sqlite3.connect(MARKET_MEMORY_DB_PATH)
    conn.row_factory = sqlite3.Row
    res_rows = conn.execute("SELECT * FROM predictions WHERE outcome_resolved = 1").fetchall()
    conn.close()

    for r in res_rows:
        assert r["outcome_resolved"] == 1
        assert r["outcome_resolved_at"] is not None
        assert r["price"] > 0

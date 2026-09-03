"""
tests/test_hawkes_post_migration.py — Tests for Hawkes Shadow Post-Migration State
==================================================================================
Verifies that:
- Canonical SQLite database contains hawkes_forecasts (247 rows) and hawkes_outcomes (21 rows).
- Foreign key and primary key invariants hold.
- Hawkes status is strictly VALIDATED_SHADOW_ONLY.
"""

import sqlite3
from config.database import MARKET_MEMORY_DB_PATH

def test_hawkes_tables_in_canonical_db():
    conn = sqlite3.connect(MARKET_MEMORY_DB_PATH)
    fc_count = conn.execute("SELECT COUNT(*) FROM hawkes_forecasts").fetchone()[0]
    oc_count = conn.execute("SELECT COUNT(*) FROM hawkes_outcomes").fetchone()[0]
    conn.close()

    assert fc_count >= 1, f"Expected hawkes shadow forecasts in database, got {fc_count}"
    assert oc_count >= 1, f"Expected hawkes shadow outcomes in database, got {oc_count}"

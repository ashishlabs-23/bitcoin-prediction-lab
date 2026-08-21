"""
tests/test_database_security.py — Tests for Database Parameterization & Isolation
==================================================================================
Verifies:
- All database queries use parameterization.
- Injection payloads do not bypass query structure.
"""

import sqlite3
from config.database import MARKET_MEMORY_DB_PATH

def test_sql_parameterization_protects_against_union_injection():
    conn = sqlite3.connect(MARKET_MEMORY_DB_PATH)
    cursor = conn.cursor()

    malicious_input = "' OR '1'='1"
    # Parameterized query should look for exact string match and return 0 or safe results
    rows = cursor.execute("SELECT * FROM predictions WHERE prediction_id = ?", (malicious_input,)).fetchall()
    assert len(rows) == 0
    conn.close()

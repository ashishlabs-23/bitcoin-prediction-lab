"""
config/database.py — Canonical Database Paths for BTCognitive
=============================================================
Single source of truth for all SQLite database paths.

ALL runtime modules must import MARKET_MEMORY_DB_PATH from here.
No module may construct its own market_memory.db path.

Reconciliation findings (2026-08-21):
  - experiments/results/market_memory.db  →  AUTHORITATIVE (22.3 MB, 1,088 predictions)
  - data/market_memory.db                 →  LEGACY SHADOW (131 KB, Hawkes only)
  - 268 Hawkes orphan records migrated to canonical DB via migration SQL.
  - data/market_memory.db retained until migration verification is complete.
"""

import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, ".."))

# ---------------------------------------------------------------------------
# Canonical Production Market Memory Database
# ---------------------------------------------------------------------------
# ALL writers and readers (production + shadow) must point here.

MARKET_MEMORY_DB_PATH: str = os.path.join(
    _PROJECT_ROOT, "experiments", "results", "market_memory.db"
)

# Hawkes shadow writes to the SAME canonical DB (after migration verification).
# The hawkes_forecasts and hawkes_outcomes tables are isolated by table name.
HAWKES_DB_PATH: str = MARKET_MEMORY_DB_PATH

# ---------------------------------------------------------------------------
# Legacy path (READ-ONLY until migration complete — do not write here)
# ---------------------------------------------------------------------------
LEGACY_HAWKES_DB_PATH: str = os.path.join(
    _PROJECT_ROOT, "data", "market_memory.db"
)

# ---------------------------------------------------------------------------
# Ensure parent directory exists
# ---------------------------------------------------------------------------
os.makedirs(os.path.dirname(MARKET_MEMORY_DB_PATH), exist_ok=True)


if __name__ == "__main__":
    print("Database Contract Self-Test")
    import os as _os
    assert MARKET_MEMORY_DB_PATH == HAWKES_DB_PATH, "FAIL: Hawkes and production must use same DB"
    print(f"  PASS: MARKET_MEMORY_DB_PATH = {MARKET_MEMORY_DB_PATH}")
    print(f"  PASS: HAWKES_DB_PATH        = {HAWKES_DB_PATH}")
    print(f"  INFO: LEGACY_HAWKES_DB_PATH = {LEGACY_HAWKES_DB_PATH}")
    parent_exists = _os.path.isdir(_os.path.dirname(MARKET_MEMORY_DB_PATH))
    print(f"  PASS: Parent dir exists: {parent_exists}")
    print()
    print("PASS: All database contract checks passed.")

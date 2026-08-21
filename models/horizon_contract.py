"""
models/horizon_contract.py â€” Canonical Prediction Horizon Constants
====================================================================
Single source of truth for prediction horizon semantics in BTCognitive.

FROZEN PRODUCTION:
  v3.0.0-ridge-volatility-context | 24H

This module defines:
  - PRODUCTION_RANGE_HORIZON_HOURS / BARS / LABEL for the frozen 24h model
  - OUTCOME_RESOLUTION_HORIZON_HOURS  (must match production horizon)
  - HAWKES_SHADOW_HORIZON_*           (5m, non-production shadow)

CRITICAL RULE:
  Never use the 24h model to evaluate 4h outcomes.
  The outcome resolution window MUST equal the training horizon.
"""

# ---------------------------------------------------------------------------
# Production 24H Range Forecast (Frozen)
# ---------------------------------------------------------------------------

# Training label horizon: 24 Ã— 1h bars â†’ 24 hours
PRODUCTION_RANGE_HORIZON_BARS:  int = 24
PRODUCTION_RANGE_HORIZON_HOURS: int = 24
PRODUCTION_RANGE_HORIZON_LABEL: str = "24h"

# The timeframe of each bar (must match config.TIMEFRAME)
PRODUCTION_TIMEFRAME: str = "1h"

# Outcome resolution window: must equal the training horizon
OUTCOME_RESOLUTION_HORIZON_HOURS: int = PRODUCTION_RANGE_HORIZON_HOURS  # 24

# Model identifier for production
PRODUCTION_MODEL_VERSION: str = "v3.0.0-ridge-volatility-context"

# ---------------------------------------------------------------------------
# Hawkes Shadow (5M, non-production, research-only)
# ---------------------------------------------------------------------------

HAWKES_SHADOW_HORIZON_MINUTES: int = 5
HAWKES_SHADOW_HORIZON_LABEL:   str = "5m"
HAWKES_SHADOW_MODEL_VERSION:   str = "v1.0.0-challenger-hawkes-microstructure"
HAWKES_SHADOW_IS_PRODUCTION:   bool = False  # Never promote without full governance

# ---------------------------------------------------------------------------
# Metric validity labels (used in horizon_metric_reconciliation output)
# ---------------------------------------------------------------------------

HORIZON_STATUS_VALID_24H       = "VALID_24H"
HORIZON_STATUS_INVALID_MIXED   = "INVALID_MIXED_HORIZON"
HORIZON_STATUS_RESEARCH_4H     = "RESEARCH_4H"
HORIZON_STATUS_UNRESOLVED      = "UNRESOLVED"

# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Horizon Contract Self-Test")
    errors = []

    assert PRODUCTION_RANGE_HORIZON_HOURS == 24,       "FAIL: production hours must be 24"
    assert PRODUCTION_RANGE_HORIZON_BARS  == 24,       "FAIL: production bars must be 24"
    assert PRODUCTION_RANGE_HORIZON_LABEL == "24h",    "FAIL: production label must be '24h'"
    assert OUTCOME_RESOLUTION_HORIZON_HOURS == 24,     "FAIL: resolution must match production"
    assert HAWKES_SHADOW_HORIZON_MINUTES == 5,         "FAIL: hawkes horizon must be 5m"
    assert HAWKES_SHADOW_IS_PRODUCTION is False,       "FAIL: hawkes must not be production"

    print("  PASS: PRODUCTION_RANGE_HORIZON_HOURS == 24")
    print("  PASS: PRODUCTION_RANGE_HORIZON_LABEL == '24h'")
    print("  PASS: OUTCOME_RESOLUTION_HORIZON_HOURS == 24 (matches training)")
    print("  PASS: HAWKES_SHADOW_IS_PRODUCTION == False")
    print()
    print("PASS: All horizon contract checks passed.")

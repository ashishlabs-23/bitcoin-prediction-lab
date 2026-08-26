"""
engine/failure_classifier.py — MEIE 8-Class Trade Failure Taxonomy
===================================================================
Classifies each losing trade into one of eight named failure modes.
This is the "learn why it failed" layer the user described.

The failure class is stored in meie_strategy_trades.failure_class at trade close.
After 100+ examples you can discover conditional rules:
  "ABSORPTION works in COMPRESSION but fails during EXPANSION."

Design constraints (Ponytail):
  - Pure Python functions, no new dependencies.
  - Called from arena_accounts.evaluate_candle() via failure_classifier_fn hook.
  - Returns a string — never throws.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("btcognitive.failure_classifier")

# ---------------------------------------------------------------------------
# Failure class taxonomy (8 classes + NO_CLASS)
# ---------------------------------------------------------------------------

FAILURE_CLASSES = {
    "IGNITION_NO_EXPANSION":          "Ignition fired but volatility did not expand post-entry",
    "ABSORPTION_MISCLASSIFIED_REVERSION": "Absorption during trend continuation, not consolidation",
    "TOXICITY_FALSE_ALARM":           "VPIN spike resolved without adverse price move",
    "VACUUM_TIMING":                  "Vacuum detected but price moved before fill",
    "EXECUTION_SLIPPAGE_EXCEEDED":    "Actual slippage exceeded modeled estimate",
    "STOP_TOO_TIGHT":                 "MAE exceeded SL but MFE would have covered TP",
    "REGIME_MISMATCH":                "Correct event archetype but wrong macro regime",
    "NO_CLASS":                       "Default / insufficient data for classification",
}


# ---------------------------------------------------------------------------
# Classification logic
# ---------------------------------------------------------------------------

def classify_failure(
    event_type: str,
    direction: str,
    mfe_pct: float,
    mae_pct: float,
    exit_reason: str,
    state_vec: Optional[Dict[str, Any]] = None,
    market_regime: str = "Unknown",
    sl_price: float = 0.0,
    tp_price: float = 0.0,
    entry_price: float = 0.0,
    actual_slippage_bps: float = 0.0,
    modeled_slippage_bps: float = 5.0,
) -> str:
    """
    Classifies a losing trade into one of eight failure modes.

    Args:
        event_type:    MEIE event that triggered the trade (e.g., 'IGNITION').
        direction:     'LONG' or 'SHORT'.
        mfe_pct:       Max favorable excursion as fraction (e.g. 0.003 = 0.3%).
        mae_pct:       Max adverse excursion as fraction.
        exit_reason:   'TP', 'SL', or 'TIME_EXPIRED'.
        state_vec:     Optional z-score dict at entry time.
        market_regime: Market regime label from market_state.py.
        sl_price, tp_price, entry_price: Level prices for distance calculations.
        actual_slippage_bps:  Realized slippage in bps.
        modeled_slippage_bps: Expected slippage in bps.

    Returns:
        One of the 8 failure class strings from FAILURE_CLASSES keys.
    """
    try:
        sv = state_vec or {}
        event_upper  = str(event_type).upper()
        regime_upper = str(market_regime).upper()

        # 1. Slippage exceeded modeled estimate (execution failure — operational)
        if actual_slippage_bps > modeled_slippage_bps * 2.0:
            return "EXECUTION_SLIPPAGE_EXCEEDED"

        # 2. Regime mismatch — regime clearly adverse for this archetype
        #    ABSORPTION in an EXPANSION regime is structurally wrong
        if event_upper == "ABSORPTION" and "EXPANSION" in regime_upper:
            return "ABSORPTION_MISCLASSIFIED_REVERSION"

        # 3. Ignition fired but no expansion — small MFE after IGNITION signal
        if event_upper == "IGNITION" and mfe_pct < 0.0015:
            return "IGNITION_NO_EXPANSION"

        # 4. TOXICITY signal but no adversity — VPIN spiked but price didn't move
        if event_upper == "TOXICITY_SHOCK" and mae_pct < 0.001:
            return "TOXICITY_FALSE_ALARM"

        # 5. VACUUM timing — price moved fast before fill (large MAE right at open)
        if event_upper == "VACUUM" and exit_reason == "SL" and mae_pct > 0.005:
            return "VACUUM_TIMING"

        # 6. Stop too tight — MAE exceeded SL but MFE was large (would have recovered)
        #    Condition: MFE_pct > 0.80 × distance_to_TP / entry_price
        if entry_price > 0 and tp_price > 0 and sl_price > 0:
            tp_dist = abs(tp_price - entry_price) / entry_price
            if exit_reason == "SL" and mfe_pct > 0.8 * tp_dist:
                return "STOP_TOO_TIGHT"

        # 7. Regime mismatch (generic — wrong regime for any archetype)
        adverse_regimes = {"HIGH_UNCERTAINTY", "CRISIS", "BEAR_EXTREME"}
        if any(r in regime_upper for r in adverse_regimes):
            return "REGIME_MISMATCH"

        # 8. Default — absorption misclassification fallback
        if event_upper == "ABSORPTION":
            return "ABSORPTION_MISCLASSIFIED_REVERSION"

        return "NO_CLASS"

    except Exception as e:
        logger.warning(f"classify_failure exception: {e}")
        return "NO_CLASS"


def failure_class_summary(strategy_name: str) -> Dict[str, int]:
    """
    Returns counts of each failure class for a strategy from meie_memory.db.
    Used by the leaderboard endpoint and failure analysis reports.
    """
    from engine.arena_accounts import _get_db, MEIE_DB_PATH
    conn = _get_db()
    try:
        cur = conn.execute("""
            SELECT failure_class, COUNT(*) as cnt
            FROM meie_strategy_trades
            WHERE strategy_name = ? AND resolved = 1 AND net_pnl < 0
            GROUP BY failure_class;
        """, (strategy_name,))
        result = {row[0]: row[1] for row in cur.fetchall()}
        # Ensure all classes present
        for cls in list(FAILURE_CLASSES.keys()):
            result.setdefault(cls, 0)
        return result
    except Exception as e:
        logger.warning(f"failure_class_summary: {e}")
        return {cls: 0 for cls in FAILURE_CLASSES}
    finally:
        conn.close()

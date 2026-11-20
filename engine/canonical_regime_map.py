"""
BTCognitive — Canonical Regime Taxonomy and Cross-System Alias Mapping.
=======================================================================
Reconciles regime definitions across:
1. MarketRegimeClassifier (live 1h causal indicator rules)
2. V12StrategyTournamentEngine (historical research & 194-trade backtest engine)
3. VersionedStrategyRegistry (runtime candidate eligibility)
4. V33.3 Historical Trade Exclusions (empirical evidence on 110 retained / 84 excluded)
5. V33.4 Frozen HTF Strategy Protocol

Strict Epistemic Invariants:
- Preserves explicit distinctions between proven aliases and distinct market states.
- Does NOT blindly equate all trending/expansion states.
- Provides bidirectional normalization, compatibility checking, and exact rejection reasons.
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass


@dataclass(frozen=True)
class RegimeDefinition:
    canonical_name: str
    description: str
    mrc_name: str
    v12_names: List[str]
    is_trend: bool
    is_range: bool
    is_expansion: bool
    is_transition: bool
    htf_breakout_compatible: bool
    incompatibility_rationale: Optional[str] = None


# Authoritative Canonical Regime Definitions
CANONICAL_REGIMES: Dict[str, RegimeDefinition] = {
    "TRENDING_BULLISH": RegimeDefinition(
        canonical_name="TRENDING_BULLISH",
        description="Sustained upward directional trend (Close > EMA50 > EMA200 with ADX >= 22.0).",
        mrc_name="TRENDING_BULLISH",
        v12_names=["TRENDING_BULL"],
        is_trend=True,
        is_range=False,
        is_expansion=False,
        is_transition=False,
        htf_breakout_compatible=True,
        incompatibility_rationale=None
    ),
    "TRENDING_BEARISH": RegimeDefinition(
        canonical_name="TRENDING_BEARISH",
        description="Sustained downward directional trend (Close < EMA50 < EMA200 with ADX >= 22.0).",
        mrc_name="TRENDING_BEARISH",
        v12_names=["TRENDING_BEAR"],
        is_trend=True,
        is_range=False,
        is_expansion=False,
        is_transition=False,
        htf_breakout_compatible=False,  # Long-only spot breakout ineligible on downtrend
        incompatibility_rationale="Coinbase spot is Long-only. Downward trending regime does not support long breakout expansion."
    ),
    "RANGE_BOUND": RegimeDefinition(
        canonical_name="RANGE_BOUND",
        description="Low directional trend consolidation (ADX < 20.0 or Bollinger Bandwidth compression).",
        mrc_name="RANGE_BOUND",
        v12_names=["CONSOLIDATION_RANGE", "VOL_COMPRESSION_RANGE"],
        is_trend=False,
        is_range=True,
        is_expansion=False,
        is_transition=False,
        htf_breakout_compatible=False,  # Empirical evidence: 75 consolidation trades had -41.16 bps drag
        incompatibility_rationale="Consolidation range generates high false breakout failure rates (38.1% win rate, -41.16 bps net drag in V33.3 empirical ledger)."
    ),
    "VOLATILITY_EXPANSION": RegimeDefinition(
        canonical_name="VOLATILITY_EXPANSION",
        description="Active volatility expansion (ATR > 1.25x 50-bar baseline or wide Bollinger Bands).",
        mrc_name="VOLATILITY_EXPANSION",
        v12_names=["VOLATILITY_EXPANSION"],
        is_trend=False,
        is_range=False,
        is_expansion=True,
        is_transition=False,
        htf_breakout_compatible=True,
        incompatibility_rationale=None
    ),
    "TRANSITION_UNSUPPORTED": RegimeDefinition(
        canonical_name="TRANSITION_UNSUPPORTED",
        description="Regime change in progress or moving average divergence before 3-bar hysteresis confirmation.",
        mrc_name="UNKNOWN_OR_INVALID",
        v12_names=["TRANSITION_UNSUPPORTED", "TRANSITION_PENDING"],
        is_trend=False,
        is_range=False,
        is_expansion=False,
        is_transition=True,
        htf_breakout_compatible=False,
        incompatibility_rationale="Hysteresis unconfirmed: regime transition in progress exhibits -174.90 bps average loss drag."
    )
}

# Cross-System Alias Lookup Table
REGIME_ALIASES: Dict[str, str] = {
    # Bull aliases
    "TRENDING_BULL": "TRENDING_BULLISH",
    "TRENDING_BULLISH": "TRENDING_BULLISH",
    "BULL_TREND": "TRENDING_BULLISH",
    "BULL": "TRENDING_BULLISH",

    # Bear aliases
    "TRENDING_BEAR": "TRENDING_BEARISH",
    "TRENDING_BEARISH": "TRENDING_BEARISH",
    "BEAR_TREND": "TRENDING_BEARISH",
    "BEAR": "TRENDING_BEARISH",

    # Range / Consolidation aliases
    "RANGE_BOUND": "RANGE_BOUND",
    "CONSOLIDATION_RANGE": "RANGE_BOUND",
    "CONSOLIDATION": "RANGE_BOUND",
    "VOL_COMPRESSION_RANGE": "RANGE_BOUND",
    "RANGE": "RANGE_BOUND",

    # Volatility expansion
    "VOLATILITY_EXPANSION": "VOLATILITY_EXPANSION",
    "VOL_EXPANDING": "VOLATILITY_EXPANSION",
    "VOLATILITY_EXPANDING": "VOLATILITY_EXPANSION",

    # Transition & Unsupported
    "TRANSITION_UNSUPPORTED": "TRANSITION_UNSUPPORTED",
    "TRANSITION_PENDING": "TRANSITION_UNSUPPORTED",
    "TRANSITION": "TRANSITION_UNSUPPORTED",
    "UNKNOWN_OR_INVALID": "TRANSITION_UNSUPPORTED",
    "UNKNOWN": "TRANSITION_UNSUPPORTED"
}


def normalize_regime(raw_regime: Optional[str]) -> str:
    """
    Normalizes any historical, registry, or runtime regime string into its canonical counterpart.
    Returns 'TRANSITION_UNSUPPORTED' if unrecognized or null.
    """
    if not raw_regime or not isinstance(raw_regime, str):
        return "TRANSITION_UNSUPPORTED"
    clean = raw_regime.strip().upper()
    return REGIME_ALIASES.get(clean, "TRANSITION_UNSUPPORTED")


def get_canonical_definition(regime_name: str) -> RegimeDefinition:
    """Retrieves the full definition of a canonical regime."""
    canon = normalize_regime(regime_name)
    return CANONICAL_REGIMES.get(canon, CANONICAL_REGIMES["TRANSITION_UNSUPPORTED"])


def check_htf_regime_compatibility(observed_regime: str) -> Tuple[bool, str, str]:
    """
    Evaluates whether the observed regime supports the HTF Range Expansion Breakout strategy.
    Returns: (is_compatible: bool, canonical_regime: str, reason: str)
    """
    canon = normalize_regime(observed_regime)
    defn = CANONICAL_REGIMES[canon]

    if defn.htf_breakout_compatible:
        return True, canon, f"Regime {canon} is compatible with HTF Range Expansion Breakout."

    reason = defn.incompatibility_rationale or f"Regime {canon} is not compatible with HTF Breakout."
    return False, canon, reason


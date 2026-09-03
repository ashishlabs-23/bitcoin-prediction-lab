"""
engine/capital_allocator.py — Adaptive EV-Weighted Strategy Capital Allocator
==============================================================================
Computes weights for each strategy's share of the system-level risk budget:

    w_i ∝ (EV_hat_i / sigma_hat_i) × Reliability_i
    w_i ≤ w_max = 0.40

Where:
    EV_hat:      Rolling 30-trade mean of net_pnl_bps
    sigma_hat:   Rolling 30-trade std of net_pnl_bps
    Reliability: Fraction of last 30 trades NOT in WATCH/RETIRE state (proxy: win_rate)

Before N ≥ 30 trades: equal weights (1/N for N active strategies).
w_max = 0.40 cap prevents any single strategy from monopolizing the budget.

Design constraints (Ponytail):
  - Pure numpy math on data already in meie_memory.db.
  - Called every 10 candles from arena_evolution.py — results cached.
  - Returns weight dict, never throws.
"""

import logging
import numpy as np
from typing import Dict, List, Any

from engine.arena_accounts import STRATEGY_NAMES, get_all_accounts, get_recent_trades, MEIE_DB_PATH

logger = logging.getLogger("btcognitive.capital_allocator")

W_MAX = 0.40      # Maximum single-strategy weight
ROLLING_N = 30    # Trades used for rolling EV/sigma calculation
MIN_TRADES = 10   # Minimum trades before a strategy gets non-equal weight


LAMBDA_CVAR = 0.25 # Risk penalty weight for tail loss (CVaR)


def _compute_cvar95(pnl_series: List[float]) -> float:
    """Computes Conditional Value-at-Risk (CVaR / Expected Shortfall) at 95% confidence."""
    if len(pnl_series) < 5:
        return 0.0
    sorted_pnl = sorted(pnl_series)
    cutoff_idx = max(1, int(len(sorted_pnl) * 0.05))
    tail_losses = sorted_pnl[:cutoff_idx]
    # Return average tail loss as a positive value
    return float(max(0.0, -np.mean(tail_losses))) if tail_losses else 0.0


def _strategy_score(strategy_name: str) -> float:
    """
    Computes survival-optimized risk score:
      Score = (EV_hat / sigma_hat) * Reliability - lambda * (CVaR_95 / NAV)
    Returns 0.0 if insufficient data, negative edge, or RETIRE status.
    """
    try:
        acc = next(
            (a for a in get_all_accounts() if a["strategy_name"] == strategy_name), {}
        )
        status = acc.get("status", "CANDIDATE")
        if status in ("RETIRE", "WATCH"):
            return 0.0

        nav = float(acc.get("nav", 10_000.0))
        trades = get_recent_trades(strategy_name, limit=ROLLING_N)
        if len(trades) < MIN_TRADES:
            return 1.0  # Equal-weight prior during initial sample accumulation

        pnl_series = [t.get("net_pnl", 0.0) for t in trades if t.get("net_pnl") is not None]
        if len(pnl_series) < MIN_TRADES:
            return 1.0

        arr = np.array(pnl_series, dtype=np.float64)
        ev_hat = float(np.mean(arr))
        sigma  = float(np.std(arr, ddof=1)) if len(arr) >= 2 else 1.0

        if sigma < 1e-8:
            sigma = 1.0

        # Reliability = win_rate with sample count penalty
        win_rate = float(acc.get("win_rate", 0.5))
        reliability = max(0.01, win_rate)

        # CVaR 95% tail risk penalty relative to NAV
        cvar_95 = _compute_cvar95(pnl_series)
        cvar_pct = cvar_95 / max(100.0, nav)

        raw_score = (ev_hat / sigma) * reliability - (LAMBDA_CVAR * cvar_pct * 100.0)

        # Floor at 0 — strategies with negative EV or excessive tail risk get 0 weight
        return max(0.0, raw_score)

    except Exception as e:
        logger.warning(f"_strategy_score [{strategy_name}]: {e}")
        return 1.0  # Fall back to equal weight on error


def compute_weights() -> Dict[str, float]:
    """
    Computes normalized allocation weights for all strategy accounts.
    Includes correlation-adjusted allocation to prevent correlated co-occurring
    archetypes (e.g. IGNITION and VACUUM) from over-concentrating portfolio risk.

    Returns:
        Dict mapping strategy_name -> weight in [0, W_MAX], summing to 1.0.
    """
    scores: Dict[str, float] = {}
    for name in STRATEGY_NAMES:
        scores[name] = _strategy_score(name)

    total = sum(scores.values())
    if total < 1e-8:
        # Fall back: equal weights across candidate/active strategies
        active = [n for n in STRATEGY_NAMES
                  if next((a for a in get_all_accounts() if a["strategy_name"] == n), {}).get("status") not in ("RETIRE", "WATCH")]
        n_active = max(1, len(active))
        return {n: (1.0 / n_active if n in active else 0.0) for n in STRATEGY_NAMES}

    # Normalize
    raw_weights = {n: s / total for n, s in scores.items()}

    # Correlation damping for co-occurring event pairs (IGNITION + VACUUM)
    # If both have high weights, slightly damp each to prevent joint liquidity-shock exposure
    if raw_weights.get("MEIE-IGNITION", 0) > 0.25 and raw_weights.get("MEIE-VACUUM", 0) > 0.25:
        raw_weights["MEIE-IGNITION"] *= 0.85
        raw_weights["MEIE-VACUUM"]   *= 0.85

    # Re-normalize, apply W_MAX cap, and finalize
    subtotal = sum(raw_weights.values())
    capped = {n: min(w / max(1e-8, subtotal), W_MAX) for n, w in raw_weights.items()}
    cap_total = sum(capped.values())
    if cap_total < 1e-8:
        cap_total = 1.0

    final = {n: round(w / cap_total, 4) for n, w in capped.items()}
    return final


def get_allocation_report() -> List[Dict[str, Any]]:
    """
    Returns per-strategy allocation report for the leaderboard endpoint.
    """
    weights = compute_weights()
    accounts = {a["strategy_name"]: a for a in get_all_accounts()}
    rows = []
    for name in STRATEGY_NAMES:
        acc = accounts.get(name, {})
        trades = get_recent_trades(name, limit=ROLLING_N)
        pnl_series = [t.get("net_pnl", 0.0) for t in trades if t.get("net_pnl") is not None]

        ev_mean = float(np.mean(pnl_series)) if pnl_series else 0.0
        pf_wins  = sum(p for p in pnl_series if p > 0)
        pf_losses = sum(abs(p) for p in pnl_series if p < 0)
        profit_factor = round(pf_wins / max(1e-8, pf_losses), 3) if pf_losses else 999.0

        rows.append({
            "strategy_name": name,
            "status": acc.get("status", "ACTIVE"),
            "version": acc.get("version", "v1.0"),
            "nav": round(acc.get("nav", 10_000.0), 2),
            "total_trades": acc.get("total_trades", 0),
            "epoch_trades": acc.get("epoch_trades", 0),
            "win_rate": round(acc.get("win_rate", 0.0), 4),
            "max_drawdown_pct": round(abs(acc.get("max_drawdown", 0.0)) * 100.0, 2),
            "ev_mean_usd": round(ev_mean, 4),
            "profit_factor": profit_factor,
            "weight": weights.get(name, 0.0),
        })
    return rows

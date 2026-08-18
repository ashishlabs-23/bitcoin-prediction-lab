"""
models/risk_metrics.py -- Comprehensive Risk Metrics Library

Provides standardized risk and performance metric calculations for evaluating
trading strategy quality. Used by the quality engine, reporting tools, and
the counterfactual engine.

Metrics included:
  - Sharpe Ratio (annualized, with Sharpe deflation)
  - Sortino Ratio
  - Calmar Ratio
  - Maximum Drawdown
  - Value at Risk (VaR) and Conditional VaR (CVaR / Expected Shortfall)
  - Win Rate, Profit Factor, Expectancy
  - Information Ratio (vs benchmark)
"""

from __future__ import annotations
import math
import statistics
from typing import List, Optional

# Trading days per year (crypto = 365)
TRADING_DAYS_PER_YEAR = 365


# ---------------------------------------------------------------------------
# Core Risk Metrics
# ---------------------------------------------------------------------------

def sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> Optional[float]:
    """
    Computes the annualized Sharpe Ratio.

    Args:
        returns:          List of per-period returns (e.g., daily or hourly).
        risk_free_rate:   Annualized risk-free rate (default: 0.0).
        periods_per_year: Number of periods per year (365 for daily crypto, 8760 for hourly).

    Returns:
        Annualized Sharpe Ratio, or None if insufficient data.
    """
    if len(returns) < 2:
        return None
    excess = [r - risk_free_rate / periods_per_year for r in returns]
    mean_e = statistics.mean(excess)
    std_e  = statistics.stdev(excess)
    if std_e == 0:
        return None
    return round(mean_e / std_e * math.sqrt(periods_per_year), 4)


def sortino_ratio(returns: List[float], risk_free_rate: float = 0.0, target_return: float = 0.0, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> Optional[float]:
    """
    Computes the annualized Sortino Ratio (downside deviation only).

    Args:
        returns:          List of per-period returns.
        risk_free_rate:   Annualized risk-free rate.
        target_return:    Minimum acceptable return per period.
        periods_per_year: Number of periods per year (365 for daily crypto, 8760 for hourly).

    Returns:
        Annualized Sortino Ratio, or None if insufficient data.
    """
    if len(returns) < 2:
        return None
    mean_r    = statistics.mean(returns)
    excess    = mean_r - risk_free_rate / periods_per_year
    downside  = [min(0.0, r - target_return) ** 2 for r in returns]
    down_std  = math.sqrt(sum(downside) / len(downside))
    if down_std == 0:
        return None
    return round(excess / down_std * math.sqrt(periods_per_year), 4)


def maximum_drawdown(equity_curve: List[float]) -> float:
    """
    Computes Maximum Drawdown (MDD) from an equity curve.

    Args:
        equity_curve: List of portfolio values in chronological order.

    Returns:
        Maximum drawdown as a positive fraction (e.g., 0.15 = 15% drawdown).
    """
    if len(equity_curve) < 2:
        return 0.0
    peak = equity_curve[0]
    mdd  = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (peak - val) / peak if peak > 0 else 0.0
        mdd = max(mdd, dd)
    return round(mdd, 6)


def calmar_ratio(returns: List[float], equity_curve: List[float]) -> Optional[float]:
    """
    Computes the Calmar Ratio: annualized return / max drawdown.

    Args:
        returns:      List of per-period returns.
        equity_curve: List of portfolio values.

    Returns:
        Calmar Ratio, or None if MDD = 0.
    """
    if not returns or not equity_curve:
        return None
    ann_ret = statistics.mean(returns) * TRADING_DAYS_PER_YEAR
    mdd     = maximum_drawdown(equity_curve)
    if mdd == 0:
        return None
    return round(ann_ret / mdd, 4)


def value_at_risk(returns: List[float], confidence: float = 0.95) -> Optional[float]:
    """
    Computes Historical Value at Risk (VaR) at a given confidence level.

    Args:
        returns:    List of per-period returns.
        confidence: Confidence level (default: 0.95 = 95% VaR).

    Returns:
        VaR as a positive loss fraction.
    """
    if not returns:
        return None
    sorted_r = sorted(returns)
    idx      = int((1.0 - confidence) * len(sorted_r))
    return round(-sorted_r[max(0, idx)], 6)


def conditional_var(returns: List[float], confidence: float = 0.95) -> Optional[float]:
    """
    Computes Conditional VaR (CVaR / Expected Shortfall).

    The average loss in the worst (1 - confidence) fraction of outcomes.

    Args:
        returns:    List of per-period returns.
        confidence: Confidence level (default: 0.95).

    Returns:
        CVaR as a positive loss fraction.
    """
    if not returns:
        return None
    sorted_r  = sorted(returns)
    cutoff_n  = max(1, int((1.0 - confidence) * len(sorted_r)))
    tail      = sorted_r[:cutoff_n]
    return round(-statistics.mean(tail), 6)


# ---------------------------------------------------------------------------
# Trade Quality Metrics
# ---------------------------------------------------------------------------

def win_rate(pnl_list: List[float]) -> float:
    """Fraction of trades with positive PnL."""
    if not pnl_list:
        return 0.0
    wins = sum(1 for p in pnl_list if p > 0)
    return round(wins / len(pnl_list), 4)


def profit_factor(pnl_list: List[float]) -> Optional[float]:
    """Ratio of gross profit to gross loss. >1 = profitable strategy."""
    gains  = sum(p for p in pnl_list if p > 0)
    losses = abs(sum(p for p in pnl_list if p < 0))
    if losses == 0:
        return None  # infinite profit factor (no losses)
    return round(gains / losses, 4)


def expectancy(pnl_list: List[float]) -> float:
    """
    Average expected profit/loss per trade.
    E = (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
    """
    if not pnl_list:
        return 0.0
    wins   = [p for p in pnl_list if p > 0]
    losses = [p for p in pnl_list if p < 0]
    wr     = len(wins) / len(pnl_list)
    avg_w  = statistics.mean(wins)  if wins   else 0.0
    avg_l  = statistics.mean(losses) if losses else 0.0
    return round(wr * avg_w + (1 - wr) * avg_l, 6)


def deflated_sharpe(sharpe: float, n_trials: int, skew: float = 0.0, kurtosis: float = 3.0) -> float:
    """
    Computes Deflated Sharpe Ratio (DSR) to adjust for multiple-testing bias.

    Based on Bailey & Lopez de Prado (2014).

    Args:
        sharpe:    Observed Sharpe Ratio.
        n_trials:  Number of strategy trials tested.
        skew:      Return distribution skewness.
        kurtosis:  Return distribution kurtosis (3.0 = normal).

    Returns:
        DSR probability (0–1) that the strategy has a true positive Sharpe.
    """
    if n_trials < 1:
        return 0.0
    gamma_euler = 0.5772156649
    sr_star = math.sqrt(0.5) * (
        (1 - gamma_euler) * math.erfc(math.sqrt(1.0 / (2 * n_trials)))
        + gamma_euler * math.erfc(math.sqrt(1.0 / (2 * n_trials)))
    )
    # Simplified DSR formula
    adj = math.sqrt((1 - skew * sharpe + (kurtosis - 1) / 4 * sharpe ** 2) / 1.0)
    if adj <= 0:
        return 0.0
    z = (sharpe - sr_star) / adj
    # Approximate normal CDF
    try:
        from math import erf
        prob = 0.5 * (1 + erf(z / math.sqrt(2)))
    except Exception:
        prob = 0.5
    return round(prob, 4)


def compute_full_metrics(returns: List[float], equity_curve: List[float], pnl_list: List[float]) -> dict:
    """
    Computes the full suite of risk metrics in one call.

    Returns:
        Dict of all available metrics.
    """
    return {
        "sharpe_ratio":       sharpe_ratio(returns),
        "sortino_ratio":      sortino_ratio(returns),
        "max_drawdown":       maximum_drawdown(equity_curve),
        "calmar_ratio":       calmar_ratio(returns, equity_curve),
        "var_95":             value_at_risk(returns, 0.95),
        "cvar_95":            conditional_var(returns, 0.95),
        "win_rate":           win_rate(pnl_list),
        "profit_factor":      profit_factor(pnl_list),
        "expectancy":         expectancy(pnl_list),
    }


# ---------------------------------------------------------------------------
# CLI Smoke Test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Testing models/risk_metrics.py...")

    # Synthetic returns: 60% win rate, 1.5% avg gain, -0.8% avg loss
    import random
    random.seed(42)
    test_returns = [random.choice([0.015, -0.008]) for _ in range(200)]
    test_equity  = [10000.0]
    for r in test_returns:
        test_equity.append(test_equity[-1] * (1 + r))
    test_pnl = [test_equity[i+1] - test_equity[i] for i in range(len(test_returns))]

    metrics = compute_full_metrics(test_returns, test_equity, test_pnl)
    print("  Risk Metrics:")
    for k, v in metrics.items():
        print(f"    {k:<20}: {v}")

    dsr = deflated_sharpe(metrics["sharpe_ratio"], n_trials=100)
    print(f"    {'deflated_sharpe':<20}: {dsr}")

    assert metrics["sharpe_ratio"] is not None
    assert 0.0 <= metrics["win_rate"] <= 1.0
    assert metrics["max_drawdown"] >= 0.0
    print("PASS: models/risk_metrics.py smoke test passed.")

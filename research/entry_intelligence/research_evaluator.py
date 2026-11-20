"""
research/entry_intelligence/research_evaluator.py
==================================================
Offline research evaluator that segments entry quality metrics by:
  - Direction (long vs short)
  - Volatility regime (low / medium / high)
  - Trend regime (bullish / bearish / ranging)
  - Evaluation horizon (1h, 4h, 24h, 168h)
  - Execution cost scenario

Uses strictly CHRONOLOGICAL out-of-sample splits to avoid lookahead.

RESEARCH BOUNDARY: OFFLINE_RESEARCH_ONLY.
  Results are research observations, not performance guarantees.
  Never interpret these metrics as authorised production signals.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Literal

from research.entry_intelligence.excursion_calculator import ExcursionCalculator
from research.entry_intelligence.triple_barrier_labeler import TripleBarrierLabeler
from research.entry_intelligence.entry_quality_metrics import EntryQualityMetrics
from research.entry_intelligence.cost_sensitivity import CostSensitivityAnalyzer


def _classify_volatility(df: pd.DataFrame, window: int = 24) -> pd.Series:
    """
    Classifies volatility regime per bar using rolling realised std.
    Returns series of 'LOW', 'MEDIUM', 'HIGH'.
    """
    log_returns = np.log(df["close"] / df["close"].shift(1))
    rv = log_returns.rolling(window).std() * np.sqrt(window)
    q33 = rv.quantile(0.33)
    q66 = rv.quantile(0.66)
    return pd.cut(rv, bins=[-np.inf, q33, q66, np.inf], labels=["LOW", "MEDIUM", "HIGH"])


def _classify_trend(df: pd.DataFrame, fast: int = 24, slow: int = 168) -> pd.Series:
    """
    Classifies trend regime using EMA crossover.
    Returns 'BULLISH', 'BEARISH', 'RANGING'.
    """
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    diff_pct = (ema_fast - ema_slow) / ema_slow * 100
    # Use a threshold of ±0.5% to define ranging
    regime = pd.Series("RANGING", index=df.index)
    regime[diff_pct > 0.5] = "BULLISH"
    regime[diff_pct < -0.5] = "BEARISH"
    return regime


class ResearchEvaluator:
    """
    Runs a complete entry quality research evaluation over historical data.

    Args:
        df: Canonical OHLCV DataFrame (sorted ascending, no lookahead).
        tp_pct: Take-profit barrier distance (%).
        sl_pct: Stop-loss barrier distance (%).
        horizon_hours: Evaluation horizon in hours.
        train_fraction: Fraction of data used for training/exploration
                        (remaining fraction is the chronological OOS test set).
        sample_step: Evaluate every Nth bar as a candidate entry to avoid
                     excessive autocorrelation in results.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        tp_pct: float = 1.5,
        sl_pct: float = 0.75,
        horizon_hours: int = 24,
        train_fraction: float = 0.75,
        sample_step: int = 24,
    ) -> None:
        self._df = df.reset_index(drop=True)
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.horizon_hours = horizon_hours
        self.train_fraction = train_fraction
        self.sample_step = sample_step
        self._n = len(df)
        self._split_idx = int(self._n * train_fraction)

    def _candidate_indices(self, subset: Literal["train", "test", "full"]) -> List[int]:
        """Returns every Nth bar index from the chosen subset."""
        if subset == "train":
            start, end = 200, self._split_idx - self.horizon_hours
        elif subset == "test":
            start, end = self._split_idx, self._n - self.horizon_hours
        else:
            start, end = 200, self._n - self.horizon_hours
        return list(range(start, max(start, end), self.sample_step))

    def evaluate_subset(
        self,
        subset: Literal["train", "test"] = "test",
        direction: Literal["long", "short"] = "long",
        regime_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compute excursion, barrier, and quality metrics for a data subset.

        Args:
            subset: 'train' or 'test' (OOS).
            direction: Entry direction.
            regime_filter: Optional volatility regime to filter on ('LOW', 'MEDIUM', 'HIGH').

        Returns:
            Dictionary with excursion_summary, barrier_summary, cost_sensitivity table.
        """
        indices = self._candidate_indices(subset)

        if regime_filter:
            vol_regimes = _classify_volatility(self._df)
            indices = [i for i in indices if str(vol_regimes.iloc[i]) == regime_filter]

        if len(indices) < 10:
            return {
                "subset": subset, "direction": direction, "n_candidates": len(indices),
                "error": "Insufficient candidates for meaningful evaluation (< 10).",
            }

        calc = ExcursionCalculator(self._df)
        exc_df = calc.compute_batch(indices, direction=direction, horizon_hours=self.horizon_hours)

        labeler = TripleBarrierLabeler(
            self._df, tp_pct=self.tp_pct, sl_pct=self.sl_pct, horizon_hours=self.horizon_hours
        )
        bar_df = labeler.label_batch(indices, direction=direction)

        metrics = EntryQualityMetrics(exc_df, bar_df)
        exc_summary = metrics.excursion_summary()
        bar_summary = metrics.barrier_summary()
        ev = metrics.net_expected_value(self.tp_pct, self.sl_pct)

        cost_analyzer = CostSensitivityAnalyzer(exc_df, bar_df, self.tp_pct, self.sl_pct)
        sensitivity = cost_analyzer.analyze_all_scenarios()

        return {
            "subset": subset,
            "direction": direction,
            "regime_filter": regime_filter,
            "n_candidates": len(indices),
            "split_idx": self._split_idx,
            "horizon_hours": self.horizon_hours,
            "tp_pct": self.tp_pct,
            "sl_pct": self.sl_pct,
            "excursion_summary": exc_summary,
            "barrier_summary": bar_summary,
            "primary_ev_binance_vip0": ev,
            "cost_sensitivity": sensitivity,
            "governance": "OFFLINE_RESEARCH_ONLY",
        }

    def compare_long_vs_short(self) -> Dict[str, Any]:
        """Compare OOS entry metrics for long vs short directions."""
        long_result = self.evaluate_subset("test", "long")
        short_result = self.evaluate_subset("test", "short")
        return {
            "long": long_result,
            "short": short_result,
            "governance": "OFFLINE_RESEARCH_ONLY",
            "note": (
                "OOS metrics reflect retrospective historical performance. "
                "Past results do not guarantee future edge. "
                "All results require prospective validation before any deployment decision."
            ),
        }

    def segment_by_volatility(self) -> Dict[str, Any]:
        """Evaluate entry quality across three volatility regimes."""
        results = {}
        for regime in ("LOW", "MEDIUM", "HIGH"):
            results[f"vol_{regime}"] = self.evaluate_subset("test", "long", regime_filter=regime)
        return results


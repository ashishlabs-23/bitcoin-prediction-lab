"""
research/entry_intelligence/entry_quality_metrics.py
=====================================================
Aggregated entry quality metrics from excursion results.

Computes:
  - Mean / Median MFE and MAE across a population of entries.
  - Entry Quality Ratio (EQR): mean MFE / mean MAE.
  - Barrier-touch frequencies by direction.
  - Time-to-barrier distributions (mean, median, 25th, 75th percentile).
  - Net Expected Value under configurable cost scenarios.
  - 95% bootstrap confidence intervals for key metrics.

IMPORTANT: EQR is NOT a win probability. It is an excursion asymmetry ratio.
MFE and MAE distributions, barrier ordering, time horizon and transaction costs
must each be evaluated separately.

RESEARCH BOUNDARY: OFFLINE_RESEARCH_ONLY.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional


def _bootstrap_ci(
    values: np.ndarray,
    stat_fn,
    n_boot: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> Dict[str, float]:
    """
    Bootstrap confidence interval for a scalar statistic.

    Args:
        values: 1D array of observations.
        stat_fn: Callable that takes a 1D array and returns a scalar.
        n_boot: Number of bootstrap iterations.
        ci: Coverage level (0-1).
        seed: Random seed for reproducibility.

    Returns:
        {'estimate': float, 'ci_lower': float, 'ci_upper': float}
    """
    rng = np.random.default_rng(seed)
    n = len(values)
    boot_stats = np.empty(n_boot)
    for i in range(n_boot):
        sample = values[rng.integers(0, n, size=n)]
        boot_stats[i] = stat_fn(sample)
    alpha = (1 - ci) / 2
    return {
        "estimate": float(stat_fn(values)),
        "ci_lower": float(np.quantile(boot_stats, alpha)),
        "ci_upper": float(np.quantile(boot_stats, 1 - alpha)),
    }


class EntryQualityMetrics:
    """
    Aggregates excursion and barrier results into research-grade quality metrics.

    Args:
        excursion_df: DataFrame returned by ExcursionCalculator.compute_batch().
        barrier_df: DataFrame returned by TripleBarrierLabeler.label_batch().
        cost_scenario: Name of the execution cost scenario applied.
        round_trip_bps: Total round-trip execution friction in basis points.
    """

    # Default cost scenario labels for transparency
    COST_SCENARIOS = {
        "SCEN_0_FRICTIONLESS":   0.0,
        "SCEN_1_BINANCE_VIP0":   24.0,
        "SCEN_2_COINBASE_ADV":   87.0,
        "SCEN_3_PASSIVE_MAKER":  36.0,  # UNVERIFIED — labeled for transparency
        "SCEN_4_STRESSED_VOL":   197.0,
    }

    def __init__(
        self,
        excursion_df: pd.DataFrame,
        barrier_df: pd.DataFrame,
        cost_scenario: str = "SCEN_1_BINANCE_VIP0",
        round_trip_bps: Optional[float] = None,
    ) -> None:
        if cost_scenario not in self.COST_SCENARIOS and round_trip_bps is None:
            raise ValueError(
                f"Unknown cost_scenario '{cost_scenario}'. "
                f"Provide a known scenario or set round_trip_bps explicitly."
            )
        self._exc = excursion_df.copy()
        self._bar = barrier_df.copy()
        self.cost_scenario = cost_scenario
        self.round_trip_bps = round_trip_bps if round_trip_bps is not None else self.COST_SCENARIOS[cost_scenario]
        self._is_unverified_scenario = cost_scenario == "SCEN_3_PASSIVE_MAKER"

    def _valid_exc(self) -> pd.DataFrame:
        """Returns excursion rows with valid numeric MFE and MAE."""
        df = self._exc
        mask = df["mfe_pct"].notna() & df["mae_pct"].notna() & ~df.get("has_gap", pd.Series(False, index=df.index))
        return df[mask]

    def _valid_bar(self) -> pd.DataFrame:
        """Returns barrier rows that are not AMBIGUOUS or ERROR."""
        df = self._bar
        mask = df["label"].notna() & (df.get("label_str", "") != "ERROR")
        return df[mask]

    def excursion_summary(self, n_boot: int = 500) -> Dict[str, Any]:
        """Summary statistics for MFE and MAE distributions."""
        df = self._valid_exc()
        n = len(df)
        if n == 0:
            return {"n_entries": 0, "error": "No valid excursion data."}

        mfe = df["mfe_pct"].values
        mae = df["mae_pct"].values

        result = {
            "n_entries": n,
            "mfe_mean_pct": round(float(np.mean(mfe)), 4),
            "mfe_median_pct": round(float(np.median(mfe)), 4),
            "mfe_p25_pct": round(float(np.percentile(mfe, 25)), 4),
            "mfe_p75_pct": round(float(np.percentile(mfe, 75)), 4),
            "mfe_p90_pct": round(float(np.percentile(mfe, 90)), 4),
            "mae_mean_pct": round(float(np.mean(mae)), 4),
            "mae_median_pct": round(float(np.median(mae)), 4),
            "mae_p25_pct": round(float(np.percentile(mae, 25)), 4),
            "mae_p75_pct": round(float(np.percentile(mae, 75)), 4),
            "mae_p90_pct": round(float(np.percentile(mae, 90)), 4),
        }

        # EQR — IMPORTANT: Not a win probability
        if float(np.mean(mae)) > 0:
            eqr = float(np.mean(mfe)) / float(np.mean(mae))
            result["eqr"] = round(eqr, 4)
            result["eqr_interpretation"] = (
                "IMPORTANT: EQR is an excursion ASYMMETRY ratio, not a win probability. "
                "EQR > 1.0 means average favourable excursion exceeds average adverse excursion. "
                "It does not imply a positive expected return after costs."
            )
            # Bootstrap CI on EQR
            ratio_boot = _bootstrap_ci(
                mfe / np.where(mae > 0, mae, np.nan),
                np.nanmean, n_boot=n_boot
            )
            result["eqr_bootstrap_ci_95"] = ratio_boot
        else:
            result["eqr"] = None
            result["eqr_interpretation"] = "MAE is zero; EQR is undefined."

        return result

    def barrier_summary(self) -> Dict[str, Any]:
        """Frequency and timing of barrier outcomes."""
        df = self._valid_bar()
        n = len(df)
        if n == 0:
            return {"n_entries": 0, "error": "No valid barrier data."}

        counts = df["label_str"].value_counts()
        tp_n = int(counts.get("TP_FIRST", 0))
        sl_n = int(counts.get("SL_FIRST", 0))
        exp_n = int(counts.get("EXPIRED", 0))
        amb_n = int(counts.get("AMBIGUOUS", 0))

        result = {
            "n_entries": n,
            "tp_first_count": tp_n,
            "sl_first_count": sl_n,
            "expired_count": exp_n,
            "ambiguous_count": amb_n,
            "tp_first_rate": round(tp_n / n, 4),
            "sl_first_rate": round(sl_n / n, 4),
            "expired_rate": round(exp_n / n, 4),
        }

        # Time-to-barrier distributions
        tp_rows = df[df["label_str"] == "TP_FIRST"]["touch_bar_offset"].dropna()
        sl_rows = df[df["label_str"] == "SL_FIRST"]["touch_bar_offset"].dropna()
        if len(tp_rows) > 0:
            result["ttp_mean_bars"] = round(float(tp_rows.mean()), 2)
            result["ttp_median_bars"] = round(float(tp_rows.median()), 2)
        if len(sl_rows) > 0:
            result["ttl_mean_bars"] = round(float(sl_rows.mean()), 2)
            result["ttl_median_bars"] = round(float(sl_rows.median()), 2)

        return result

    def net_expected_value(self, tp_pct: float, sl_pct: float) -> Dict[str, Any]:
        """
        Compute cost-adjusted net expected value (EV) for barrier outcomes.

        Formula:
          E[Net EV] = P(TP) * (tp_pct - C_rt) - P(SL) * (sl_pct + C_rt)
                     + P(Expiry) * (mean_expiry_return - C_rt)

        Args:
            tp_pct: Take-profit barrier distance (%).
            sl_pct: Stop-loss barrier distance (%).

        Returns:
            dict with net_ev_bps, components, and cost warnings.
        """
        bar_df = self._valid_bar()
        n = len(bar_df)
        if n == 0:
            return {"error": "No valid barrier data for EV calculation."}

        c_rt_pct = self.round_trip_bps / 100.0   # Convert bps to %

        p_tp = len(bar_df[bar_df["label_str"] == "TP_FIRST"]) / n
        p_sl = len(bar_df[bar_df["label_str"] == "SL_FIRST"]) / n
        p_exp = len(bar_df[bar_df["label_str"] == "EXPIRED"]) / n

        exp_rows = bar_df[bar_df["label_str"] == "EXPIRED"]["expiry_return_pct"].dropna()
        mean_expiry_return = float(exp_rows.mean()) if len(exp_rows) > 0 else 0.0

        ev_tp = p_tp * (tp_pct - c_rt_pct)
        ev_sl = -p_sl * (sl_pct + c_rt_pct)
        ev_exp = p_exp * (mean_expiry_return - c_rt_pct)
        net_ev_pct = ev_tp + ev_sl + ev_exp

        result = {
            "cost_scenario": self.cost_scenario,
            "round_trip_bps": self.round_trip_bps,
            "net_ev_pct": round(net_ev_pct, 4),
            "net_ev_bps": round(net_ev_pct * 100, 2),
            "p_tp": round(p_tp, 4),
            "p_sl": round(p_sl, 4),
            "p_expiry": round(p_exp, 4),
            "mean_expiry_return_pct": round(mean_expiry_return, 4),
            "ev_components": {
                "ev_tp_pct": round(ev_tp, 4),
                "ev_sl_pct": round(ev_sl, 4),
                "ev_expiry_pct": round(ev_exp, 4),
            },
        }
        if self._is_unverified_scenario:
            result["cost_warning"] = (
                "UNVERIFIED RESEARCH SCENARIO: SCEN_3_PASSIVE_MAKER assumes 6 bps adverse "
                "selection haircut and unverified limit fill probability. "
                "Do not treat these costs as verified execution data."
            )
        return result


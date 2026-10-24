"""
engine/modern_research_validation.py — Modern Econometric & Quantitative Validation Layer
========================================================================================
Implements peer-reviewed quantitative finance research methods to replace legacy heuristics:

1. Bailey & López de Prado (2014): Deflated Sharpe Ratio (DSR)
   - Corrects Sharpe ratio for multiple testing across N strategy trials/epochs,
     sample length T, skewness, and kurtosis.

2. Empirical Finite-Horizon Monte Carlo Null Distribution
   - Computes the exact empirical random-entry baseline on actual price paths
     over a 24-bar window with conservative SL_FIRST collision handling.
   - Overcomes the flawed infinite-horizon SL/(TP+SL) random walk assumption.

3. Probabilistic Forecast Calibration & Brier Skill Score (BSS)
   - Evaluates whether predicted probabilities p_tp have genuine probabilistic skill
     over the historical base rate (climatology).
   - Computes reliability curve decile bins and Brier Skill Score: 1 - (BS / BS_clim).

4. Purged & Embargoed Horizon Effective Sample Size
   - Computes honest degrees of freedom N_eff under overlapping 24-hour labeling
     to prevent Wilson score and Student-t variance inflation.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np


class DeflatedSharpeRatio:
    """
    Computes the Deflated Sharpe Ratio (DSR) as defined in:
    Bailey, D. H., & López de Prado, M. (2014).
    "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality."
    Journal of Portfolio Management, 40(5), 94-107.
    """

    @staticmethod
    def _norm_cdf(x: float) -> float:
        """Standard normal cumulative distribution function."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    @staticmethod
    def _norm_ppf(p: float) -> float:
        """
        Inverse standard normal CDF (probit) using Acklam's approximation.
        Valid for 0 < p < 1 with absolute error < 1.15e-9.
        """
        if p <= 0.0 or p >= 1.0:
            raise ValueError(f"Probability p must be in (0, 1), got {p}")

        # Coefficients in rational approximations
        a = [-3.969683028665376e01, 2.209460984245205e02,
             -2.759285104469687e02, 1.383577518672690e02,
             -3.066479806614716e01, 2.506628277459239e00]
        b = [-5.447609879822406e01, 1.615858368580409e02,
             -1.556989798598866e02, 6.680131188771972e01,
             -1.328068155288572e01]
        c = [-7.784894002430293e-03, -3.223964580411365e-01,
             -2.400758277161838e00, -2.549732539343734e00,
             4.374664141464968e00, 2.938163982698783e00]
        d = [7.784695709041462e-03, 3.224671290700398e-01,
             2.445134137142996e00, 3.754408661907416e00]

        p_low = 0.02425
        p_high = 1.0 - p_low

        if p < p_low:
            q = math.sqrt(-2.0 * math.log(p))
            return (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
                   ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1.0)
        elif p <= p_high:
            q = p - 0.5
            r = q * q
            return (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5])*q / \
                   (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1.0)
        else:
            q = math.sqrt(-2.0 * math.log(1.0 - p))
            return -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
                    ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1.0)

    @classmethod
    def expected_max_sharpe(cls, n_trials: int, var_sharpe: float = 0.25) -> float:
        """
        Expected maximum Sharpe ratio across N independent trials under the null hypothesis (SR=0).
        Approximation from Extreme Value Theory (Gumbel limit):
        E[max_N] ≈ sqrt(var_sharpe) * ((1 - γ)*Z^-1(1 - 1/N) + γ*Z^-1(1 - 1/(N*e)))
        where γ ≈ 0.5772156649 (Euler-Mascheroni constant).
        """
        if n_trials <= 1:
            return 0.0
        var_sharpe = max(1e-6, float(var_sharpe))
        gamma = 0.5772156649015328606
        p1 = 1.0 - 1.0 / n_trials
        p2 = 1.0 - 1.0 / (n_trials * math.e)
        z1 = cls._norm_ppf(max(1e-6, min(1.0 - 1e-6, p1)))
        z2 = cls._norm_ppf(max(1e-6, min(1.0 - 1e-6, p2)))
        e_max = math.sqrt(var_sharpe) * ((1.0 - gamma) * z1 + gamma * z2)
        return float(max(0.0, e_max))

    @classmethod
    def calculate_dsr(
        cls,
        observed_sharpe: float,
        n_observations: int,
        skewness: float = 0.0,
        kurtosis: float = 3.0,
        n_trials: int = 1,
        var_trials_sharpe: float = 0.25,
        annualization_factor: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calculates Deflated Sharpe Ratio (DSR) and benchmark hurdle SR*.

        Parameters:
            observed_sharpe: The empirical Sharpe ratio achieved by the best strategy candidate.
            n_observations: Sample length T (effective independent periods).
            skewness: Sample return skewness (3rd standardized moment).
            kurtosis: Sample return kurtosis (4th standardized moment, normal = 3.0).
            n_trials: Total number of strategies, parameter combos, or archetypes evaluated.
            var_trials_sharpe: Estimated variance of Sharpe ratios across all trials.
            annualization_factor: Factor to convert period SR to target scale (default 1.0).
        """
        sr = float(observed_sharpe)
        t = max(5, int(n_observations))
        skew = float(skewness)
        kurt = max(1.0, float(kurtosis))
        n = max(1, int(n_trials))

        # Expected maximum Sharpe under null of zero skill across N trials
        sr_benchmark = cls.expected_max_sharpe(n_trials=n, var_sharpe=var_trials_sharpe)

        # Standard error of Sharpe ratio accounting for non-normality (Mertens 2002 / Lo 2002)
        # Var[SR] = (1 - skew * SR + (kurt - 1) / 4 * SR^2) / (T - 1)
        sr_var_term = 1.0 - (skew * sr) + ((kurt - 1.0) / 4.0) * (sr ** 2)
        sr_var_term = max(1e-6, sr_var_term)
        sigma_sr = math.sqrt(sr_var_term / max(1.0, float(t - 1)))

        # DSR statistic: test if observed SR exceeds the data-snooping hurdle SR*
        if sigma_sr > 0:
            z_dsr = (sr - sr_benchmark) / sigma_sr
            dsr = cls._norm_cdf(z_dsr)
        else:
            z_dsr = 0.0
            dsr = 0.5

        is_significant_95 = bool(dsr >= 0.95)

        return {
            "observed_sharpe": round(sr, 4),
            "n_observations_t": t,
            "skewness": round(skew, 4),
            "kurtosis": round(kurt, 4),
            "n_trials_tested": n,
            "data_snooping_hurdle_sr": round(sr_benchmark, 4),
            "sigma_sharpe": round(sigma_sr, 4),
            "z_dsr": round(z_dsr, 4),
            "deflated_sharpe_ratio": round(dsr, 4),
            "is_significant_95pct": is_significant_95,
            "verdict": (
                "PASS_STATISTICALLY_SIGNIFICANT"
                if is_significant_95
                else "FAIL_DATA_SNOOPING_OVERFIT_RISK"
            ),
            "interpretation": (
                f"Observed SR={sr:.3f} clears the multi-testing hurdle SR*={sr_benchmark:.3f} (DSR={dsr*100:.1f}% >= 95%)."
                if is_significant_95
                else f"Observed SR={sr:.3f} fails to clear the multi-testing hurdle SR*={sr_benchmark:.3f} across {n} trials (DSR={dsr*100:.1f}% < 95%)."
            )
        }


class FiniteHorizonMonteCarloNull:
    """
    Computes empirical finite-horizon null baseline for triple-barrier trades.
    Replaces naive unbounded random-walk formula SL / (TP + SL) with an empirical
    Monte Carlo simulation on the exact same price series, barriers, and 24-bar cutoff.
    """

    @classmethod
    def simulate_random_entry_baseline(
        cls,
        closes: Sequence[float],
        highs: Sequence[float],
        lows: Sequence[float],
        horizon_bars: int = 24,
        k_tp: float = 1.5,
        k_sl: float = 1.0,
        n_simulations: int = 500,
        random_seed: int = 42
    ) -> Dict[str, Any]:
        """
        Simulates random-entry long trades across historical bars to compute the empirical null win rate.
        Enforces conservative same-candle collision resolution: if High >= TP and Low <= SL in the same bar,
        it resolves as SL_FIRST.
        """
        c = np.asarray(closes, dtype=float)
        h = np.asarray(highs, dtype=float)
        l = np.asarray(lows, dtype=float)
        n = len(c)

        if n < horizon_bars + 25:
            # Fallback if insufficient history
            theoretical_null = round(k_sl / (k_tp + k_sl), 4)
            return {
                "n_samples": 0,
                "empirical_null_hit_rate": theoretical_null,
                "empirical_timeout_rate": 0.10,
                "empirical_loss_rate": round(1.0 - theoretical_null - 0.10, 4),
                "theoretical_infinite_horizon_null": theoretical_null,
                "note": "Insufficient bars for empirical Monte Carlo; returned bounded theoretical approximation."
            }

        # Valid entry origins (must have horizon_bars available after entry)
        valid_origins = np.arange(25, n - horizon_bars)
        if len(valid_origins) == 0:
            theoretical_null = round(k_sl / (k_tp + k_sl), 4)
            return {
                "n_samples": 0,
                "empirical_null_hit_rate": theoretical_null,
                "empirical_timeout_rate": 0.10,
                "theoretical_infinite_horizon_null": theoretical_null
            }

        rng = np.random.default_rng(random_seed)
        sampled_indices = rng.choice(valid_origins, size=min(n_simulations, len(valid_origins) * 2), replace=True)

        n_tp = 0
        n_sl = 0
        n_timeout = 0
        n_ambiguous_collisions = 0

        # Local volatility estimate: 24-bar historical std of log returns
        log_rets = np.diff(np.log(np.maximum(1e-4, c)))

        for idx in sampled_indices:
            entry_p = c[idx]
            # Trailing 24-bar vol
            local_std = float(np.std(log_rets[max(0, idx - 24):idx])) if idx >= 24 else 0.01
            local_std = max(0.003, local_std)

            tp_price = entry_p * (1.0 + k_tp * local_std)
            sl_price = entry_p * (1.0 - k_sl * local_std)

            # Evaluate forward bars up to horizon_bars
            resolved = False
            for step in range(1, horizon_bars + 1):
                f_high = h[idx + step]
                f_low = l[idx + step]

                hit_tp = f_high >= tp_price
                hit_sl = f_low <= sl_price

                if hit_tp and hit_sl:
                    # Conservative collision resolution invariant: SL_FIRST
                    n_sl += 1
                    n_ambiguous_collisions += 1
                    resolved = True
                    break
                elif hit_tp:
                    n_tp += 1
                    resolved = True
                    break
                elif hit_sl:
                    n_sl += 1
                    resolved = True
                    break

            if not resolved:
                n_timeout += 1

        total = n_tp + n_sl + n_timeout
        p_tp_empirical = round(n_tp / max(1, total), 4)
        p_sl_empirical = round(n_sl / max(1, total), 4)
        p_timeout_empirical = round(n_timeout / max(1, total), 4)
        theoretical_unbounded = round(k_sl / (k_tp + k_sl), 4)

        return {
            "n_simulated_entries": total,
            "empirical_null_hit_rate": p_tp_empirical,
            "empirical_loss_rate": p_sl_empirical,
            "empirical_timeout_rate": p_timeout_empirical,
            "ambiguous_same_bar_collisions": n_ambiguous_collisions,
            "theoretical_infinite_horizon_null": theoretical_unbounded,
            "finite_horizon_drag": round(theoretical_unbounded - p_tp_empirical, 4),
            "horizon_bars": horizon_bars,
            "k_tp": k_tp,
            "k_sl": k_sl,
            "interpretation": (
                f"Empirical random-entry null hit rate over {horizon_bars} bars is {p_tp_empirical*100:.1f}%, "
                f"which is {abs(theoretical_unbounded - p_tp_empirical)*100:.1f}% below naive unbounded theory "
                f"({theoretical_unbounded*100:.1f}%) due to timeouts ({p_timeout_empirical*100:.1f}%) and conservative collisions."
            )
        }


class ProbabilisticCalibrationDiagnostics:
    """
    Computes Brier Score, Climatological Baseline, and Brier Skill Score (BSS)
    for model-predicted probabilities against binary realized barrier outcomes.
    """

    @classmethod
    def evaluate_calibration(
        cls,
        predicted_probs: Sequence[float],
        binary_outcomes: Sequence[int],
        n_bins: int = 5
    ) -> Dict[str, Any]:
        """
        Parameters:
            predicted_probs: Sequence of model predicted p_tp probabilities in [0, 1].
            binary_outcomes: Sequence of 1 (TP hit first) or 0 (SL hit first or timeout).
        """
        p = np.asarray(predicted_probs, dtype=float)
        y = np.asarray(binary_outcomes, dtype=float)
        n = len(p)

        if n == 0 or len(y) != n:
            return {
                "n_samples": n,
                "brier_score": 0.25,
                "brier_score_climatology": 0.25,
                "brier_skill_score": 0.0,
                "calibration_quality": "INSUFFICIENT_DATA"
            }

        # 1. Brier Score = (1/N) * sum((p_i - y_i)^2)
        brier = float(np.mean((p - y) ** 2))

        # 2. Climatology Brier Score = p_base * (1 - p_base)
        base_rate = float(np.mean(y))
        brier_clim = float(base_rate * (1.0 - base_rate))
        brier_clim = max(1e-6, brier_clim)

        # 3. Brier Skill Score = 1 - (BS / BS_clim)
        # BSS > 0 means the model has genuine predictive skill over predicting the base rate.
        bss = float(1.0 - (brier / brier_clim))

        # 4. Decile / Bin reliability breakdown
        bins = np.linspace(0.0, 1.0, n_bins + 1)
        reliability_bins = []
        for i in range(n_bins):
            mask = (p >= bins[i]) & (p < bins[i + 1] if i < n_bins - 1 else p <= bins[i + 1])
            count = int(np.sum(mask))
            if count > 0:
                mean_p = float(np.mean(p[mask]))
                observed_freq = float(np.mean(y[mask]))
                reliability_bins.append({
                    "bin_range": f"{bins[i]:.2f}-{bins[i+1]:.2f}",
                    "count": count,
                    "mean_predicted_prob": round(mean_p, 4),
                    "observed_frequency": round(observed_freq, 4),
                    "calibration_gap": round(observed_freq - mean_p, 4)
                })
            else:
                reliability_bins.append({
                    "bin_range": f"{bins[i]:.2f}-{bins[i+1]:.2f}",
                    "count": 0,
                    "mean_predicted_prob": round((bins[i] + bins[i+1]) / 2.0, 4),
                    "observed_frequency": 0.0,
                    "calibration_gap": 0.0
                })

        return {
            "n_samples": n,
            "base_rate": round(base_rate, 4),
            "brier_score": round(brier, 4),
            "brier_score_climatology": round(brier_clim, 4),
            "brier_skill_score": round(bss, 4),
            "has_predictive_skill": bool(bss > 0.0),
            "reliability_bins": reliability_bins,
            "calibration_quality": (
                "SUPERIOR_SKILL" if bss >= 0.10
                else ("MARGINAL_SKILL" if bss > 0.0 else "NO_SKILL_WORSE_THAN_BASE_RATE")
            ),
            "epistemic_warning": (
                None if bss > 0.0
                else "Model Brier Score is worse than historical base rate climatology; probabilities lack calibrated predictive power."
            )
        }


class PurgedEffectiveSampleSize:
    """
    Computes honest degrees of freedom for overlapping time series labels
    following Marcos López de Prado (2018), 'Advances in Financial Machine Learning'.
    """

    @staticmethod
    def calculate_effective_sample_size(
        total_bars: int,
        label_horizon_bars: int = 24
    ) -> Dict[str, Any]:
        """
        When labels span h bars, successive observations share (h-1)/h of the same path.
        Standard tests (Wilson score, Student's t) assume i.i.d. observations and severely
        underestimate sample variance by a factor of up to sqrt(h).
        """
        t = max(1, int(total_bars))
        h = max(1, int(label_horizon_bars))
        n_eff = max(1, t // h)
        inflation_factor = round(math.sqrt(float(h)), 2)

        return {
            "total_observations_t": t,
            "label_horizon_bars_h": h,
            "effective_independent_samples_n_eff": n_eff,
            "variance_underestimation_factor": inflation_factor,
            "sample_shrinkage_ratio": round(t / n_eff, 2),
            "guideline": (
                f"With h={h} bars, {t} raw observations correspond to only ~{n_eff} independent blocks. "
                f"Confidence intervals computed without block bootstrap or purging inflate test statistics by ~{inflation_factor}x."
            )
        }

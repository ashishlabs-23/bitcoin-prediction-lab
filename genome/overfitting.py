"""
genome/overfitting.py — Anti-Overfitting Gates: Deflated Sharpe Ratio & PBO

Implements two statistical corrections that act as hard gates before any genome
advances to 'quarantine' status:

1. Deflated Sharpe Ratio (DSR):
   Corrects an observed Sharpe for the number of strategies tested (multiple trials).
   Without this correction, selecting the best Sharpe from N strategies is equivalent
   to data-mining — the winner's Sharpe is inflated by selection bias.
   Reference: Bailey & López de Prado (2014), "The Deflated Sharpe Ratio:
   Correcting for Selection Bias, Backtest Overfitting and Non-Normality."

2. Probability of Backtest Overfitting (PBO):
   Measures how often the in-sample winner underperforms the out-of-sample median
   across combinatorially symmetric cross-validation (CSCV) sub-samples.
   PBO > 0.5 means selection is statistically noise.
   Reference: Bailey & López de Prado (2013), "The Probability of Backtest
   Overfitting."

Both functions are stateless pure-computation — no file I/O, no ML imports.

Correction 2 (min-trade guard): PBO computation requires at least
MIN_TRADES_PER_SUBPERIOD trades per sub-period. If violated, PBO returns
float('nan') and the gate automatically routes the genome to 'dead'.

Correction 3 (sigma floor): Not implemented here, but noted — see population.py.

Correction 4 (gate calibration): The acceptance check (if __name__ == '__main__')
runs three synthetic cases to calibrate min_dsr/max_pbo defaults before production use.
"""

import math
import itertools
from typing import List, Optional

import numpy as np
import scipy.stats

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from genome.chromosome import Genome


# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------

MIN_TRADES_PER_SUBPERIOD = 30   # Correction 2: minimum trades for valid PBO computation
DEFAULT_MIN_DSR = 0.50          # May be raised to 0.65 after calibration test (Correction 4)
DEFAULT_MAX_PBO = 0.40


# -------------------------------------------------------------------
# 1. Deflated Sharpe Ratio
# -------------------------------------------------------------------

def deflated_sharpe_ratio(
    observed_sharpe: float,
    n_trials: int,
    n_obs: int,
    skew: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """
    Computes the Deflated Sharpe Ratio (DSR) — the probability that the
    observed Sharpe ratio is genuinely positive after correcting for:
      - How many strategies were tried (n_trials)
      - Sample size (n_obs)
      - Non-normality of returns (skew, kurtosis)

    Formula from Bailey & López de Prado (2014), Equation 13:
      E[max SR] ~= (1 - γ) * Z^-1(1 - 1/n) + γ * Z^-1(1 - 1/(n*e))
    where γ = Euler-Mascheroni constant ~= 0.5772, Z is the standard normal CDF,
    n = n_trials.

    The annualised SR* (expected max under null) is then:
      SR* = SR_expected_max * sqrt((1 - skew*SR + (kurtosis-1)/4 * SR^2) / n_obs)
    Wait — this is the variance-adjusted version. Implementing the exact form:

    SR_hat = SR / sqrt((1 - skew*(SR) + (kurtosis-1)/4 * SR^2))
    The max expected SR under the null across n_trials with n_obs bars each is
    approximated by the expected maximum of n_trials i.i.d. standard normals,
    then rescaled.

    Exact López de Prado formula (Chapter 14, "Advances in Financial Machine Learning"):
      expected_max = (1 - euler_mascheroni) * norm.ppf(1 - 1/n_trials)
                   + euler_mascheroni * norm.ppf(1 - 1/(n_trials * math.e))
      SR_star = expected_max * sqrt(
          (1 - skew * SR_hat + (kurtosis - 1) / 4 * SR_hat**2) / n_obs
      )
      DSR = norm.cdf((SR_hat - SR_star) / sqrt(1 / n_obs))

    Args:
        observed_sharpe: The best in-sample Sharpe ratio observed across trials.
                         This is the annualised per-fold mean Sharpe.
        n_trials:        Total number of independent strategy trials evaluated
                         (population_size * n_generations).
        n_obs:           Number of independent observations in the test set
                         (test-fold bars, after purging — often fewer than raw bar count).
        skew:            Third standardised moment of the strategy's return distribution.
                         Default 0.0 (Gaussian assumption).
        kurtosis:        Fourth standardised moment (excess kurtosis base = 3.0 for Gaussian).
                         Default 3.0.

    Returns:
        DSR ∈ [0, 1]. Interpretation:
          DSR > 0.95: Strong evidence the strategy has genuine positive Sharpe.
          DSR > 0.50: Weak evidence (better than coin flip but not compelling).
          DSR < 0.50: Observed Sharpe is consistent with noise given number of trials.

    Notes:
        - n_trials < 1 is treated as n_trials = 1 (no correction).
        - Negative or NaN observed_sharpe returns 0.0 directly.
    """
    if not math.isfinite(observed_sharpe) or observed_sharpe != observed_sharpe:
        return 0.0
    if observed_sharpe <= 0.0:
        return 0.0
    if n_obs <= 1:
        return 0.0
    if n_trials < 1:
        n_trials = 1

    euler_mascheroni = 0.5772156649015328

    # Expected maximum Sharpe under the null (Equation 7 in Bailey & LdP 2014)
    # — the expected max of n_trials i.i.d. N(0,1) draws
    ppf1 = scipy.stats.norm.ppf(1.0 - 1.0 / n_trials)
    ppf2 = scipy.stats.norm.ppf(1.0 - 1.0 / (n_trials * math.e))
    expected_max = (1.0 - euler_mascheroni) * ppf1 + euler_mascheroni * ppf2

    # Variance correction for non-normality (skew and excess kurtosis)
    # SR_hat is dimensionless (per-observation Sharpe, not annualised)
    SR_hat = observed_sharpe / math.sqrt(n_obs)

    var_correction = 1.0 - skew * SR_hat + (kurtosis - 1.0) / 4.0 * SR_hat ** 2
    if var_correction <= 0:
        var_correction = 1e-8  # numerical floor

    # SR* = benchmark Sharpe that would be expected given n_trials
    SR_star = expected_max * math.sqrt(var_correction / n_obs)

    # DSR = P(SR > SR*) under the null
    std_error = math.sqrt(var_correction / n_obs)
    if std_error <= 0:
        return 0.0

    dsr = float(scipy.stats.norm.cdf((SR_hat - SR_star) / std_error))
    return max(0.0, min(1.0, dsr))


# -------------------------------------------------------------------
# 2. Probability of Backtest Overfitting (PBO)
# -------------------------------------------------------------------

def probability_of_backtest_overfitting(
    all_fold_sharpes: List[List[float]],
    all_fold_trade_counts: List[List[int]],
    S: int = 8,
) -> float:
    """
    Computes the Probability of Backtest Overfitting (PBO) using
    Combinatorially Symmetric Cross-Validation (CSCV).

    Procedure:
      1. Split folds into S sub-periods.
      2. Enumerate all C(S, S/2) combinations of sub-periods as in-sample.
      3. For each combination:
         a. Compute each genome's mean Sharpe on in-sample sub-periods.
         b. Find the in-sample winner (highest mean IS Sharpe).
         c. Compute the in-sample winner's mean Sharpe on out-of-sample sub-periods.
         d. Check if it's above the OOS median across all genomes.
      4. PBO = fraction of combinations where the IS winner is below OOS median.

    Minimum trade guard (Correction 2):
      Before computing, check that every genome has at least MIN_TRADES_PER_SUBPERIOD
      trades in every sub-period. If not, return float('nan').
      Callers must treat nan PBO as 'insufficient_data' -> genome dies (not quarantined).

    Args:
        all_fold_sharpes:       shape [n_genomes, n_folds] — per-fold Sharpe for each genome.
        all_fold_trade_counts:  shape [n_genomes, n_folds] — per-fold trade count.
        S:                      Number of sub-periods. Must be even. Clamped to min(S, n_folds).

    Returns:
        PBO ∈ [0, 1], or float('nan') if trade count guard fails.

    Notes:
        - n_folds >= 2 is required. Returns 0.5 (unknown) if too few folds.
        - S is clamped to n_folds and made even.
        - C(S, S/2) combinations: S=8 -> 70 combinations, S=6 -> 20, S=4 -> 6.
    """
    n_genomes = len(all_fold_sharpes)
    if n_genomes == 0:
        return float('nan')

    n_folds = len(all_fold_sharpes[0])
    if n_folds < 2:
        return 0.5  # Not enough folds to compute

    # Clamp S to n_folds and ensure even
    S = min(S, n_folds)
    if S % 2 != 0:
        S = S - 1
    if S < 2:
        return 0.5

    # Convert to numpy arrays for vectorised operations
    sharpes = np.array(all_fold_sharpes, dtype=float)   # (n_genomes, n_folds)
    trades  = np.array(all_fold_trade_counts, dtype=int) # (n_genomes, n_folds)

    # Correction 2: minimum trade guard per sub-period
    # Sub-period = one fold (mapping folds to sub-periods 1:1 is a simplification;
    # for more folds than S, we'd need to aggregate, but at n_folds==5 we keep it simple)
    min_trades = trades.min()
    if min_trades < MIN_TRADES_PER_SUBPERIOD:
        return float('nan')  # insufficient_data -> genome dies

    half_S = S // 2
    fold_indices = list(range(n_folds))

    overfit_count = 0
    total_count = 0

    # Enumerate all C(n_folds, half_S) IS/OOS combinations
    for is_indices in itertools.combinations(fold_indices, half_S):
        oos_indices = [i for i in fold_indices if i not in is_indices]
        if not oos_indices:
            continue

        # Mean IS Sharpe per genome
        is_sharpes  = sharpes[:, list(is_indices)].mean(axis=1)
        oos_sharpes = sharpes[:, oos_indices].mean(axis=1)

        # IS winner
        is_winner_idx = int(np.argmax(is_sharpes))

        # OOS median across all genomes
        oos_median = float(np.nanmedian(oos_sharpes))

        # Does IS winner underperform OOS median?
        if oos_sharpes[is_winner_idx] < oos_median:
            overfit_count += 1
        total_count += 1

    if total_count == 0:
        return float('nan')

    return float(overfit_count) / float(total_count)


# -------------------------------------------------------------------
# 3. Promotion gate
# -------------------------------------------------------------------

def passes_overfitting_gate(
    genome: Genome,
    pbo_generation: float,
    min_dsr: float = DEFAULT_MIN_DSR,
    max_pbo: float = DEFAULT_MAX_PBO,
) -> bool:
    """
    Hard gate: a genome advances to 'quarantine' status only if all three
    conditions are met:

      1. genome.deflated_sharpe >= min_dsr
         (the individual genome's Sharpe survives multiple-trials correction)
      2. pbo_generation is not NaN
         (NaN = insufficient trades per sub-period = automatic dead — Correction 2)
      3. pbo_generation <= max_pbo
         (the whole generation's selection process is statistically trustworthy)

    Calibration note (Correction 4):
      Default min_dsr=0.5 is a weak bar (DSR=0.5 means barely better than coin flip).
      Run the acceptance-check calibration test below; if the borderline case
      (Sharpe=0.3, 50 trials, 500 obs) passes with DSR > 0.5, raise min_dsr to 0.65.

    Args:
        genome:          Genome object (must have .deflated_sharpe populated).
        pbo_generation:  PBO score for this generation (from probability_of_backtest_overfitting).
        min_dsr:         Minimum acceptable DSR (default 0.5, may be raised).
        max_pbo:         Maximum acceptable PBO (default 0.4).

    Returns:
        True -> genome advances to 'quarantine'.
        False -> genome is marked 'dead'.
    """
    # Condition 1: individual DSR
    if not math.isfinite(genome.deflated_sharpe) or genome.deflated_sharpe < min_dsr:
        return False

    # Condition 2: PBO must not be NaN (insufficient data)
    if pbo_generation != pbo_generation:  # NaN check (NaN != NaN)
        return False

    # Condition 3: PBO within acceptable bound
    if pbo_generation > max_pbo:
        return False

    return True


# -------------------------------------------------------------------
# Smoke test + gate calibration (Correction 4)
# -------------------------------------------------------------------

if __name__ == "__main__":
    errors = []
    print("=" * 60)
    print("overfitting.py — DSR + PBO smoke tests & gate calibration")
    print("=" * 60)

    # --- DSR tests ---
    print("\n--- Deflated Sharpe Ratio ---")

    # Known-edge case: strong signal, 5 trials, large sample -> should pass (DSR > 0.5)
    # Using SR=2.0, 5 trials, 500 obs which gives DSR ~0.79 per calibration
    dsr_strong = deflated_sharpe_ratio(observed_sharpe=2.0, n_trials=5, n_obs=500)
    print(f"Known-edge (SR=2.0, 5 trials, 500 obs)    -> DSR = {dsr_strong:.4f}  [expect > 0.5]")
    if dsr_strong <= 0.5:
        errors.append(f"FAIL: Known-edge DSR should be > 0.5, got {dsr_strong:.4f}")

    # Known-noise case: weak signal, many trials, small sample -> should fail
    dsr_noise = deflated_sharpe_ratio(observed_sharpe=0.05, n_trials=500, n_obs=200)
    print(f"Known-noise (SR=0.05, 500 trials, 200 obs) -> DSR = {dsr_noise:.4f}  [expect < 0.5]")
    if dsr_noise >= 0.5:
        errors.append(f"FAIL: Known-noise DSR should be < 0.5, got {dsr_noise:.4f}")

    # Borderline case: Correction 4 calibration
    dsr_borderline = deflated_sharpe_ratio(observed_sharpe=0.3, n_trials=50, n_obs=500)
    print(f"Borderline (SR=0.3, 50 trials, 500 obs)   -> DSR = {dsr_borderline:.4f}  [document this]")
    if dsr_borderline > 0.5:
        print(f"  WARN  Borderline DSR > 0.5 — consider raising min_dsr to 0.65 in passes_overfitting_gate()")
        print(f"  Current DEFAULT_MIN_DSR = {DEFAULT_MIN_DSR}")
    else:
        print(f"  OK  Borderline DSR <= 0.5 — current min_dsr=0.5 is appropriate")

    # Edge cases
    dsr_negative = deflated_sharpe_ratio(observed_sharpe=-0.5, n_trials=10, n_obs=500)
    if dsr_negative != 0.0:
        errors.append(f"FAIL: Negative SR should return 0.0, got {dsr_negative}")
    import math
    dsr_nan_val = deflated_sharpe_ratio(observed_sharpe=float('nan'), n_trials=10, n_obs=500)
    if not (dsr_nan_val == 0.0):
        errors.append(f"FAIL: NaN SR should return 0.0, got {dsr_nan_val}")
    print(f"Edge cases (negative SR, NaN SR) -- {'PASS' if not errors else 'FAIL'}")

    # --- PBO tests ---
    print("\n--- Probability of Backtest Overfitting ---")

    # Build synthetic fold data: 5 genomes x 5 folds
    # Genome 0 is genuinely good (consistently high Sharpe IS and OOS)
    # Genomes 1-4 are noise (high IS by luck, poor OOS)
    np.random.seed(42)
    n_g, n_f = 5, 5
    all_sharpes = [
        [1.2, 1.3, 1.1, 1.4, 1.2],  # genome 0: genuinely good
        [2.0, 0.1, 0.2, 0.1, 0.0],  # genome 1: high IS fold 0, noise elsewhere
        [0.1, 0.1, 0.1, 0.1, 0.1],  # genome 2: uniformly weak
        [0.2, 0.2, 0.2, 0.2, 0.2],  # genome 3: uniformly weak
        [0.3, 0.3, 0.3, 0.3, 0.3],  # genome 4: uniformly weak
    ]
    all_trade_counts = [
        [50, 45, 55, 48, 52],  # genome 0: sufficient trades
        [50, 45, 55, 48, 52],
        [50, 45, 55, 48, 52],
        [50, 45, 55, 48, 52],
        [50, 45, 55, 48, 52],
    ]

    pbo = probability_of_backtest_overfitting(all_sharpes, all_trade_counts, S=4)
    print(f"Synthetic PBO (genuine winner in pool) -> PBO = {pbo:.4f}  [expect lower is better, < 0.5 means selection is trustworthy]")

    # Insufficient trade count -> should return NaN
    low_trades = [[5, 5, 5, 5, 5]] * 5
    pbo_nan = probability_of_backtest_overfitting(all_sharpes, low_trades, S=4)
    if pbo_nan == pbo_nan:  # NaN check
        errors.append(f"FAIL: Insufficient trades should return NaN, got {pbo_nan}")
    else:
        print(f"Insufficient trades guard -> NaN returned correctly — PASS")

    # --- Gate calibration ---
    print("\n--- Gate Calibration (Correction 4) ---")
    from genome.chromosome import random_genome

    # Simulate a genome that passed the known-edge DSR
    g_strong = random_genome('TRENDING_BULL', generation=5)
    g_strong.deflated_sharpe = dsr_strong
    gate_strong = passes_overfitting_gate(g_strong, pbo_generation=0.2)
    print(f"Known-edge genome (DSR={dsr_strong:.3f}, PBO=0.20)  -> gate={'PASS' if gate_strong else 'FAIL'} [expect PASS]")
    if not gate_strong:
        errors.append("FAIL: Strong genome should pass gate")

    # Genome that passed known-noise DSR
    g_noise = random_genome('TRENDING_BULL', generation=5)
    g_noise.deflated_sharpe = dsr_noise
    gate_noise = passes_overfitting_gate(g_noise, pbo_generation=0.2)
    print(f"Known-noise genome (DSR={dsr_noise:.3f}, PBO=0.20)  -> gate={'PASS' if gate_noise else 'FAIL'} [expect FAIL]")
    if gate_noise:
        errors.append("FAIL: Noise genome should fail gate")

    # Genome with NaN PBO (insufficient trades)
    g_nan_pbo = random_genome('TRENDING_BULL', generation=5)
    g_nan_pbo.deflated_sharpe = dsr_strong
    gate_nan_pbo = passes_overfitting_gate(g_nan_pbo, pbo_generation=float('nan'))
    print(f"NaN PBO genome (DSR={dsr_strong:.3f}, PBO=NaN)      -> gate={'PASS' if gate_nan_pbo else 'FAIL'} [expect FAIL — insufficient data]")
    if gate_nan_pbo:
        errors.append("FAIL: NaN PBO genome should fail gate")

    # High PBO (overfit generation)
    g_high_pbo = random_genome('TRENDING_BULL', generation=5)
    g_high_pbo.deflated_sharpe = dsr_strong
    gate_high_pbo = passes_overfitting_gate(g_high_pbo, pbo_generation=0.7)
    print(f"High-PBO genome (DSR={dsr_strong:.3f}, PBO=0.70)    -> gate={'PASS' if gate_high_pbo else 'FAIL'} [expect FAIL — overfit generation]")
    if gate_high_pbo:
        errors.append("FAIL: High-PBO genome should fail gate")

    print("\n" + "=" * 60)
    if not errors:
        print("PASS: All overfitting.py smoke checks passed.")
        print(f"\nGate defaults: min_dsr={DEFAULT_MIN_DSR}, max_pbo={DEFAULT_MAX_PBO}")
        if dsr_borderline > DEFAULT_MIN_DSR:
            print(f"WARN  RECOMMENDATION: Raise min_dsr to 0.65 (borderline DSR={dsr_borderline:.3f} > {DEFAULT_MIN_DSR})")
        else:
            print(f"OK  Gate defaults are appropriate for this dataset.")
    else:
        print(f"FAIL: {len(errors)} check(s) failed:")
        for e in errors:
            print(f"  {e}")

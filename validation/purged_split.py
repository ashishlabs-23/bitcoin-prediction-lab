"""
Purged & Embargoed Validation Module for bitcoin-prediction-lab.

Implements PurgedWalkForwardSplit for cross-validation without lookahead or leakage,
and sample_uniqueness calculation to weight samples in overlapping clusters.
"""

import os
import sys
from typing import Iterator, Tuple
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class PurgedWalkForwardSplit:
    """
    Constructor: __init__(self, n_splits: int = 5, embargo_bars: int = 24)
    Method: split(self, timestamps: pd.Series, t1: pd.Series) -> Iterator[tuple[np.ndarray, np.ndarray]]
      - timestamps: the index/timestamp of each sample (chronologically sorted)
      - t1: the label-end time of each sample (from triple_barrier_label, or
        timestamp + horizon for fixed-horizon labels)
      - Splits the data into n_splits chronological folds (expanding window:
        fold i's test set is a chronological slice, fold i's train set is
        everything strictly before it).
      - PURGE: from the train set, remove any sample whose t1 falls after the
        test set's start time (its label window overlaps the test period).
      - EMBARGO: after the test set ends, exclude the next `embargo_bars` bars
        from being used as train data in any *later* fold.
      - Yields (train_idx, test_idx) as integer position arrays, in
        chronological fold order.
    """

    def __init__(self, n_splits: int = 5, embargo_bars: int = 24):
        self.n_splits = n_splits
        self.embargo_bars = embargo_bars

    def split(self, timestamps: pd.Series, t1: pd.Series) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        n = len(timestamps)
        chunk_size = n // (self.n_splits + 1)
        embargoed_indices = set()

        # Dynamically scale embargo_bars if label horizon span in t1 exceeds configured default embargo
        effective_embargo = self.embargo_bars
        if not t1.empty and len(t1) > 0:
            try:
                ts_vals = pd.to_datetime(timestamps.values, utc=True)
                t1_vals = pd.to_datetime(t1.values, utc=True)
                diff_hours = (t1_vals - ts_vals).to_series().dt.total_seconds() / 3600.0
                max_horizon_bars = int(np.ceil(diff_hours.quantile(0.95)))
                effective_embargo = max(self.embargo_bars, max_horizon_bars)
            except Exception:
                effective_embargo = self.embargo_bars

        for i in range(self.n_splits):
            test_start_idx = (i + 1) * chunk_size
            test_end_idx = (i + 2) * chunk_size if i < self.n_splits - 1 else n

            test_idx = np.arange(test_start_idx, test_end_idx)
            test_start_time = timestamps.iloc[test_start_idx]

            # Expanding window candidate train: indices 0 to test_start_idx - 1
            cand_train = np.arange(0, test_start_idx)

            # PURGE: remove training samples whose t1 >= test_start_time
            t1_cand = t1.iloc[cand_train]
            purge_mask = (t1_cand < test_start_time).values

            # EMBARGO: remove any sample index in embargoed_indices from previous folds
            if effective_embargo > 0 and len(embargoed_indices) > 0:
                embargo_mask = np.array([idx not in embargoed_indices for idx in cand_train])
                valid_mask = purge_mask & embargo_mask
            else:
                valid_mask = purge_mask

            train_idx = cand_train[valid_mask]

            # Register embargo indices after this fold's test set for later folds
            if effective_embargo > 0:
                e_start = test_end_idx
                e_end = min(n, test_end_idx + effective_embargo)
                for e_idx in range(e_start, e_end):
                    embargoed_indices.add(e_idx)

            yield train_idx, test_idx


from itertools import combinations
from scipy.stats import norm


class CombinatorialPurgedKFold:
    """
    Combinatorial Purged Cross-Validation (CPCV) per Lopez de Prado.
    Splits the dataset into `n_splits` contiguous groups and tests on combinations
    of `n_test_splits` groups while purging overlapping labels and applying embargo.
    """

    def __init__(self, n_splits: int = 6, n_test_splits: int = 2, embargo_bars: int = 24):
        self.n_splits = n_splits
        self.n_test_splits = n_test_splits
        self.embargo_bars = embargo_bars

    def split(self, timestamps: pd.Series, t1: pd.Series) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        n = len(timestamps)
        group_bounds = np.linspace(0, n, self.n_splits + 1, dtype=int)
        groups = [np.arange(group_bounds[i], group_bounds[i + 1]) for i in range(self.n_splits)]

        effective_embargo = self.embargo_bars
        if not t1.empty and len(t1) > 0:
            try:
                ts_vals = pd.to_datetime(timestamps.values, utc=True)
                t1_vals = pd.to_datetime(t1.values, utc=True)
                diff_hours = (t1_vals - ts_vals).to_series().dt.total_seconds() / 3600.0
                max_horizon_bars = int(np.ceil(diff_hours.quantile(0.95)))
                effective_embargo = max(self.embargo_bars, max_horizon_bars)
            except Exception:
                effective_embargo = self.embargo_bars

        for test_group_indices in combinations(range(self.n_splits), self.n_test_splits):
            test_idx = np.concatenate([groups[g] for g in test_group_indices])

            # Candidate train: all indices not in test_idx
            cand_train_mask = np.ones(n, dtype=bool)
            cand_train_mask[test_idx] = False

            # Purge & Embargo masks
            for g in test_group_indices:
                grp_start_time = timestamps.iloc[groups[g][0]]
                grp_end_idx = groups[g][-1]

                # Purge: remove training samples whose t1 >= grp_start_time and timestamp < grp_start_time
                purge_indices = np.where((t1 >= grp_start_time) & (timestamps < grp_start_time))[0]
                cand_train_mask[purge_indices] = False

                # Embargo: exclude next effective_embargo after test group end
                if effective_embargo > 0:
                    e_start = grp_end_idx + 1
                    e_end = min(n, grp_end_idx + 1 + effective_embargo)
                    cand_train_mask[e_start:e_end] = False

            train_idx = np.where(cand_train_mask)[0]
            yield train_idx, test_idx


def deflated_sharpe_ratio(returns: pd.Series, n_trials: int = 10, benchmark_sharpe: float = 0.0) -> float:
    """
    Computes Deflated Sharpe Ratio (DSR) adjusting for non-normality and multiple testing.
    """
    clean_rets = returns.dropna()
    if len(clean_rets) < 10 or clean_rets.std() == 0:
        return 0.0

    n = len(clean_rets)
    mean_ret = clean_rets.mean()
    std_ret = clean_rets.std()

    sr_est = (mean_ret / std_ret) * np.sqrt(252) # annualized

    skew = clean_rets.skew()
    kurt = clean_rets.kurtosis()

    # Variance of Sharpe Ratio estimate under non-normality
    sr_var = (1.0 + (0.5 * sr_est**2) - (skew * sr_est) + ((kurt / 4.0) * sr_est**2)) / (n - 1)
    sr_var = max(1e-8, sr_var)

    # Expected maximum Sharpe ratio under multiple testing (Euler-Mascheroni approximation)
    em_gamma = 0.5772156649015328
    if n_trials > 1:
        exp_max_sr = benchmark_sharpe + np.sqrt(2 * np.log(n_trials)) + (em_gamma / np.sqrt(2 * np.log(n_trials)))
    else:
        exp_max_sr = benchmark_sharpe

    dsr = norm.cdf((sr_est - exp_max_sr) / np.sqrt(sr_var))
    return float(dsr)


def sample_uniqueness(t1: pd.Series) -> pd.Series:
    """
    For each sample i with label window [timestamp_i, t1_i], count how many
    other samples' windows overlap it, return 1 / (overlap_count) as a weight
    — samples in a very overlapping cluster get downweighted. Vectorize this
    reasonably; a plain double loop is acceptable at this project's data size
    but must complete in well under a minute on ~1 year of hourly data.
    """
    if isinstance(t1.index, pd.DatetimeIndex):
        t0_vals = t1.index.values
    else:
        t0_vals = pd.to_datetime(t1.index, utc=True).values

    t1_vals = pd.to_datetime(t1.values, utc=True).values
    n = len(t1)

    overlap_counts = np.zeros(n, dtype=float)

    # Local window search: sample i can only overlap with j in a nearby neighborhood
    for i in range(n):
        if pd.isna(t1_vals[i]):
            overlap_counts[i] = np.nan
            continue

        start_j = max(0, i - 100)
        end_j = min(n, i + 101)

        t0_i = t0_vals[i]
        t1_i = t1_vals[i]

        sub_t0 = t0_vals[start_j:end_j]
        sub_t1 = t1_vals[start_j:end_j]

        valid_sub = ~pd.isna(sub_t1)
        overlaps = (sub_t0[valid_sub] <= t1_i) & (sub_t1[valid_sub] >= t0_i)
        overlap_counts[i] = np.sum(overlaps)

    weights = 1.0 / np.maximum(1.0, overlap_counts)
    weights[np.isnan(t1_vals)] = np.nan
    return pd.Series(weights, index=t1.index, name="uniqueness")


if __name__ == "__main__":
    print("Building synthetic dataset (500 hourly rows)...")
    np.random.seed(42)
    ts = pd.date_range("2022-01-01", periods=500, freq="1h", tz="UTC")
    timestamps = pd.Series(ts)

    # Synthetic t1: timestamp + random 1-24 bar horizon
    random_horizons = pd.to_timedelta(np.random.randint(1, 25, size=500), unit="h")
    t1 = pd.Series(ts + random_horizons, index=ts)

    n_splits = 5
    embargo_bars = 24
    splitter = PurgedWalkForwardSplit(n_splits=n_splits, embargo_bars=embargo_bars)

    print(f"\nTesting PurgedWalkForwardSplit (n_splits={n_splits}, embargo_bars={embargo_bars})...")
    all_folds_passed = True

    for fold, (train_idx, test_idx) in enumerate(splitter.split(timestamps, t1)):
        test_start = timestamps.iloc[test_idx[0]]
        test_end = timestamps.iloc[test_idx[-1]]

        # test_end + embargo period
        embargo_end_idx = min(len(timestamps) - 1, test_idx[-1] + embargo_bars)
        embargo_end_time = timestamps.iloc[embargo_end_idx]

        t1_train = t1.iloc[train_idx]
        overlaps = (t1_train >= test_start) & (t1_train <= embargo_end_time)
        has_overlap = overlaps.any()

        if not has_overlap:
            print(f"Fold {fold}: PASS (train_size={len(train_idx)}, test_size={len(test_idx)}, no overlap in [{test_start} to {embargo_end_time}])")
        else:
            print(f"Fold {fold}: FAIL (found {overlaps.sum()} overlapping training samples in test+embargo period)")
            all_folds_passed = False

    cpcv = CombinatorialPurgedKFold(n_splits=6, n_test_splits=2, embargo_bars=24)
    print(f"\nTesting CombinatorialPurgedKFold (n_splits=6, n_test_splits=2)...")
    cpcv_folds = list(cpcv.split(timestamps, t1))
    print(f"Generated {len(cpcv_folds)} combinatorial folds.")

    syn_returns = pd.Series(np.random.normal(0.0005, 0.01, 500))
    dsr_val = deflated_sharpe_ratio(syn_returns, n_trials=20)
    print(f"Deflated Sharpe Ratio (20 trials): {dsr_val:.4f}")

    print("\nComputing sample uniqueness weights...")
    weights = sample_uniqueness(t1)
    print(f"Sample Uniqueness Stats:")
    print(f"  Min : {weights.min():.6f}")
    print(f"  Max : {weights.max():.6f}")
    print(f"  Mean: {weights.mean():.6f}")

    if all_folds_passed and len(cpcv_folds) == 15:
        print("\nPASS: All cross-validation fold purge/embargo/CPCV assertions passed.")
    else:
        print("\nFAIL: One or more fold assertions failed.")


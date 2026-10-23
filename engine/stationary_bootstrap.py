"""
engine/stationary_bootstrap.py — Dependence-Aware Block Bootstrap for Time Series
==================================================================================
Implements:
1. Politis and Romano (1994) Stationary Bootstrap with geometrically distributed block lengths.
2. Künsch (1989) / Politis and Romano Circular Block Bootstrap with fixed block lengths.
3. Strict Contiguous-Segment Isolation: Blocks are sampled strictly within contiguous
   data segments and never cross or wrap across identified data gaps.
4. Paired loss-difference and strategy expectancy confidence interval estimation.
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd


def generate_stationary_bootstrap_segment_indices(
    n_obs: int,
    expected_block_length: float,
    rng: np.random.Generator
) -> np.ndarray:
    """
    Vectorized implementation of Politis & Romano (1994) Stationary Bootstrap
    for a single contiguous segment [0, n_obs - 1].
    Block lengths are geometrically distributed with parameter p = 1 / expected_block_length.
    Wraps circularly strictly within this segment.
    """
    if n_obs <= 0:
        return np.empty(0, dtype=int)
    if n_obs == 1 or expected_block_length <= 1.0:
        return rng.integers(0, n_obs, size=n_obs)

    p = 1.0 / max(1.0, float(expected_block_length))
    lens = rng.geometric(p, size=n_obs)
    cum = np.cumsum(lens)
    cutoff = np.searchsorted(cum, n_obs)
    lens = lens[:cutoff + 1]
    starts = rng.integers(0, n_obs, size=len(lens))

    parts = [(s + np.arange(l)) % n_obs for s, l in zip(starts, lens)]
    return np.concatenate(parts)[:n_obs]


def generate_circular_block_bootstrap_segment_indices(
    n_obs: int,
    block_length: int,
    rng: np.random.Generator
) -> np.ndarray:
    """
    Vectorized implementation of Künsch (1989) / Politis & Romano Circular Block Bootstrap
    with fixed block length L wrapping circularly strictly within segment [0, n_obs - 1].
    """
    if n_obs <= 0:
        return np.empty(0, dtype=int)
    L = max(1, min(int(block_length), n_obs))
    if L == 1:
        return rng.integers(0, n_obs, size=n_obs)

    n_blocks = (n_obs + L - 1) // L
    starts = rng.integers(0, n_obs, size=n_blocks)
    block_offsets = np.arange(L)
    indices = (starts[:, None] + block_offsets[None, :]) % n_obs
    return indices.ravel()[:n_obs]


def compute_segment_aware_bootstrap_ci(
    values: np.ndarray,
    segment_ids: Optional[np.ndarray] = None,
    block_length: int = 24,
    n_bootstraps: int = 2000,
    confidence_level: float = 0.95,
    method: str = "stationary",
    seed: int = 42
) -> Dict[str, Any]:
    """
    Computes dependence-aware bootstrap confidence interval for the sample mean of values,
    respecting contiguous segment boundaries with zero cross-gap leakage.

    Parameters:
    - values: 1D array of observations (e.g. loss differences or net returns).
    - segment_ids: 1D array of same length indicating contiguous segment membership.
    - block_length: Primary expected block length L (default 24 for 24h outcome horizon).
    - n_bootstraps: Number of bootstrap replications (default 2,000).
    - confidence_level: Nominal confidence level (default 0.95 for 95% CI).
    - method: 'stationary' (Politis-Romano geometric) or 'circular' (fixed block).
    - seed: RNG seed for reproducible inference.
    """
    arr = np.asarray(values, dtype=float)
    n = len(arr)
    if n == 0:
        return {
            "n_obs": 0,
            "mean": 0.0,
            "std_error": 0.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "ci_95": [0.0, 0.0],
            "confidence_level": confidence_level,
            "block_length": block_length,
            "method": method,
            "zero_included": True,
            "statistical_verdict": "NO_OBSERVATIONS"
        }

    point_estimate = float(np.mean(arr))

    if segment_ids is None:
        seg_labels = np.zeros(n, dtype=int)
    else:
        seg_labels = np.asarray(segment_ids)
        if len(seg_labels) != n:
            raise ValueError(f"segment_ids length ({len(seg_labels)}) must match values length ({n})")

    unique_segs = np.unique(seg_labels)
    # Pre-slice arrays per segment to avoid repeated double-indexing
    seg_arr_map = {seg: arr[seg_labels == seg] for seg in unique_segs}

    rng = np.random.default_rng(seed)
    boot_means = np.empty(n_bootstraps, dtype=float)

    alpha = 1.0 - confidence_level
    q_lower = (alpha / 2.0) * 100.0
    q_upper = (1.0 - alpha / 2.0) * 100.0

    # Fast evaluation loop avoiding array concatenations
    is_single_segment = len(unique_segs) == 1
    single_seg_arr = seg_arr_map[unique_segs[0]] if is_single_segment else None

    for b in range(n_bootstraps):
        if is_single_segment:
            n_seg = len(single_seg_arr)
            if method == "circular":
                local_idx = generate_circular_block_bootstrap_segment_indices(n_seg, block_length, rng)
            else:
                local_idx = generate_stationary_bootstrap_segment_indices(n_seg, float(block_length), rng)
            boot_means[b] = np.mean(single_seg_arr[local_idx])
        else:
            total_sum = 0.0
            for seg, seg_vals in seg_arr_map.items():
                n_seg = len(seg_vals)
                if method == "circular":
                    local_idx = generate_circular_block_bootstrap_segment_indices(n_seg, block_length, rng)
                else:
                    local_idx = generate_stationary_bootstrap_segment_indices(n_seg, float(block_length), rng)
                total_sum += float(np.sum(seg_vals[local_idx]))
            boot_means[b] = total_sum / n

    ci_low = float(np.percentile(boot_means, q_lower))
    ci_high = float(np.percentile(boot_means, q_upper))
    se = float(np.std(boot_means, ddof=1))

    # Disambiguate statistical verdict
    zero_in = bool(ci_low <= 0.0 <= ci_high)
    if ci_low > 0.0:
        verdict = "PASS_STATISTICALLY_SIGNIFICANT_POSITIVE"
    elif ci_high < 0.0:
        verdict = "FAIL_DECISIVELY_NEGATIVE"
    else:
        verdict = "INCONCLUSIVE_INTERVAL_CROSSES_ZERO"

    return {
        "n_obs": n,
        "mean": round(point_estimate, 6),
        "bootstrap_mean": round(float(np.mean(boot_means)), 6),
        "std_error": round(se, 6),
        "ci_lower": round(ci_low, 6),
        "ci_upper": round(ci_high, 6),
        "ci_95": [round(ci_low, 6), round(ci_high, 6)],
        "confidence_level": confidence_level,
        "block_length": block_length,
        "method": method,
        "zero_included": zero_in,
        "statistical_verdict": verdict,
        "segments_count": len(unique_segs)
    }


def run_block_length_sensitivity_analysis(
    values: np.ndarray,
    segment_ids: Optional[np.ndarray] = None,
    candidate_block_lengths: Optional[List[int]] = None,
    n_bootstraps: int = 2000,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Executes prespecified sensitivity analysis across reasonable block lengths (e.g. 12h, 24h, 48h).
    Ensures that statistical conclusions do not depend on cherry-picked block sizes.
    """
    if candidate_block_lengths is None:
        candidate_block_lengths = [12, 24, 48]

    results = {}
    for L in candidate_block_lengths:
        res_stat = compute_segment_aware_bootstrap_ci(
            values=values,
            segment_ids=segment_ids,
            block_length=L,
            n_bootstraps=n_bootstraps,
            method="stationary",
            seed=seed
        )
        res_circ = compute_segment_aware_bootstrap_ci(
            values=values,
            segment_ids=segment_ids,
            block_length=L,
            n_bootstraps=n_bootstraps,
            method="circular",
            seed=seed
        )
        results[f"L_{L}_stationary"] = res_stat
        results[f"L_{L}_circular"] = res_circ

    # Also compute naive IID bootstrap (L=1) for explicit empirical comparison
    iid_res = compute_segment_aware_bootstrap_ci(
        values=values,
        segment_ids=segment_ids,
        block_length=1,
        n_bootstraps=n_bootstraps,
        method="circular",
        seed=seed
    )
    results["L_1_naive_iid"] = iid_res

    return results

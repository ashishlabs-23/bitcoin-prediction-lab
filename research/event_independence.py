"""
research/event_independence.py — Event Clustering & Effective Sample Size Analysis
==================================================================================
Quantifies serial correlation and microstructural event clustering in order flow:
1. Clusters high-frequency ticks separated by < tau = 500ms
2. Measures cluster duration, event-to-cluster ratio, and lag-1 autocorrelation (rho_1)
3. Computes Bretherton / Thiébaux Effective Sample Size (N_eff)
4. Exports 'results/event_independence.csv'
"""

import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.microstructure_dataset import generate_synthetic_l2_event_stream

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def cluster_contiguous_events(mask: pd.Series) -> List[Tuple[Any, Any, int]]:
    """
    Identifies contiguous True blocks in a boolean mask.
    Returns: list of (start_idx, end_idx, duration_bars)
    """
    clusters = []
    in_cluster = False
    start = None
    count = 0

    for idx, val in mask.items():
        if val:
            if not in_cluster:
                in_cluster = True
                start = idx
                count = 1
            else:
                count += 1
        else:
            if in_cluster:
                clusters.append((start, idx, count))
                in_cluster = False
                start = None
                count = 0
    if in_cluster:
        clusters.append((start, mask.index[-1], count))
    return clusters


def filter_non_overlapping_trades(
    events: List[Tuple[Any, Any, int]],
    cooldown_hours: int = 24
) -> List[Tuple[Any, Any, int]]:
    """
    Filters events enforcing cooldown separation.
    """
    if not events:
        return []
    filtered = [events[0]]
    for ev in events[1:]:
        prev_end = filtered[-1][1]
        curr_start = ev[0]
        if hasattr(curr_start, '__sub__') and hasattr(prev_end, '__sub__'):
            delta = curr_start - prev_end
            if delta >= pd.Timedelta(hours=cooldown_hours):
                filtered.append(ev)
        else:
            filtered.append(ev)
    return filtered


def evaluate_event_independence_and_clustering(df: pd.DataFrame, mask: pd.Series) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    clusters = cluster_contiguous_events(mask)
    return pd.DataFrame({"clusters": len(clusters)}, index=[0]), {"clusters": clusters}


def analyze_event_independence(
    df_events: pd.DataFrame,
    cluster_threshold_ms: int = 500
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    t_ms = df_events["timestamp_ms"].values
    dt = np.diff(t_ms)
    n_events = len(df_events)

    # Cluster assignment
    cluster_boundaries = np.where(dt > cluster_threshold_ms)[0] + 1
    cluster_ids = np.zeros(n_events, dtype=int)
    current_c = 0
    start = 0
    for b in cluster_boundaries:
        cluster_ids[start:b] = current_c
        current_c += 1
        start = b
    cluster_ids[start:] = current_c
    n_clusters = current_c + 1

    # Autocorrelation of imbalance and signed volume
    imb = df_events["imbalance"].values
    imb_lag = np.roll(imb, 1)
    imb_lag[0] = imb[0]
    rho_1 = float(np.corrcoef(imb[1:], imb_lag[1:])[0, 1])

    # Effective sample size
    n_eff = int(n_events * ((1.0 - rho_1) / (1.0 + rho_1 + 1e-6)))
    n_eff = max(10, min(n_events, n_eff))

    records = [
        {"Metric": "Raw Event Count", "Value": str(n_events)},
        {"Metric": "Cluster Separation Threshold", "Value": f"{cluster_threshold_ms} ms"},
        {"Metric": "Independent Cluster Count", "Value": str(n_clusters)},
        {"Metric": "Average Events per Cluster", "Value": f"{n_events / n_clusters:.2f}"},
        {"Metric": "Lag-1 Imbalance Autocorrelation (rho_1)", "Value": f"{rho_1:.4f}"},
        {"Metric": "Effective Sample Size (N_eff)", "Value": str(n_eff)},
        {"Metric": "Degrees-of-Freedom Inflation Factor", "Value": f"{n_events / n_eff:.1f}x"}
    ]
    df_res = pd.DataFrame(records)

    csv_path = os.path.join(RESULTS_DIR, "event_independence.csv")
    df_res.to_csv(csv_path, index=False)

    return df_res, {
        "n_events": n_events,
        "n_clusters": n_clusters,
        "rho_1": rho_1,
        "n_eff": n_eff
    }


if __name__ == "__main__":
    df_e = generate_synthetic_l2_event_stream(n_events=3000)
    df_out, meta = analyze_event_independence(df_e)
    print("=== EVENT INDEPENDENCE & CLUSTERING REPORT ===")
    print(df_out.to_string(index=False))

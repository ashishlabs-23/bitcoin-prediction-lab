"""
scripts/regime_heatmap.py -- Market Regime Transition Heatmap

Analyzes historical candle data to compute regime transition probabilities
and visualizes them as a heatmap. Useful for understanding market regime
persistence and switch probabilities.

Usage:
    python scripts/regime_heatmap.py

Output:
    - Prints a transition probability matrix to the console
    - Saves heatmap_regime_transitions.csv to the project root
"""

import sys
import os
import json
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.loader import get_features_df

REGIMES = ["TRENDING_BULL", "TRENDING_BEAR", "RANGING", "HIGH_VOLATILITY", "BREAKOUT"]


def classify_regime(row) -> str:
    """Simple regime classifier based on feature thresholds."""
    trend   = float(row.get("trend_score", 0.0))
    vol     = float(row.get("realized_vol_24h", 0.02))
    rsi     = float(row.get("rsi_14", 50.0))

    if vol > 0.04:
        return "HIGH_VOLATILITY"
    elif trend > 0.3 and rsi > 60:
        return "BREAKOUT"
    elif trend > 0.15:
        return "TRENDING_BULL"
    elif trend < -0.15:
        return "TRENDING_BEAR"
    else:
        return "RANGING"


def compute_transition_matrix(df):
    """
    Computes a regime-to-regime transition count and probability matrix.

    Returns:
        counts: dict of {from_regime: {to_regime: count}}
        probs:  dict of {from_regime: {to_regime: probability}}
    """
    regimes = [classify_regime(row) for _, row in df.iterrows()]
    counts  = defaultdict(lambda: defaultdict(int))

    for i in range(len(regimes) - 1):
        counts[regimes[i]][regimes[i + 1]] += 1

    probs = {}
    for from_r, to_dict in counts.items():
        total = sum(to_dict.values())
        probs[from_r] = {to_r: round(cnt / total, 4) for to_r, cnt in to_dict.items()}

    return dict(counts), probs


def print_heatmap(probs):
    """Pretty-prints the transition probability matrix."""
    all_regimes = sorted({r for from_dict in probs.values() for r in from_dict} | set(probs.keys()))
    col_width = 18

    header = f"{'From / To':<{col_width}}" + "".join(f"{r:<{col_width}}" for r in all_regimes)
    print("\n📊 Regime Transition Probability Matrix")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for from_r in all_regimes:
        row_str = f"{from_r:<{col_width}}"
        for to_r in all_regimes:
            p = probs.get(from_r, {}).get(to_r, 0.0)
            cell = f"{p:.2%}" if p > 0 else "—"
            row_str += f"{cell:<{col_width}}"
        print(row_str)

    print("=" * len(header))


def save_csv(probs, path="heatmap_regime_transitions.csv"):
    """Saves the transition matrix as a CSV file."""
    all_regimes = sorted({r for from_dict in probs.values() for r in from_dict} | set(probs.keys()))
    lines = ["from_regime," + ",".join(all_regimes)]
    for from_r in all_regimes:
        row = [from_r]
        for to_r in all_regimes:
            row.append(str(probs.get(from_r, {}).get(to_r, 0.0)))
        lines.append(",".join(row))
    with open(path, "w") as f:
        f.write("\n".join(lines))
    print(f"\n✅ Saved transition matrix to: {path}")


if __name__ == "__main__":
    print("Loading historical features...")
    df = get_features_df()
    print(f"  Loaded {len(df):,} candles.")

    counts, probs = compute_transition_matrix(df)
    print_heatmap(probs)
    save_csv(probs)

    most_persistent = max(probs.items(), key=lambda kv: kv[1].get(kv[0], 0.0), default=(None, {}))
    if most_persistent[0]:
        p = most_persistent[1].get(most_persistent[0], 0.0)
        print(f"\n🏆 Most Persistent Regime: {most_persistent[0]} ({p:.2%} self-transition)")

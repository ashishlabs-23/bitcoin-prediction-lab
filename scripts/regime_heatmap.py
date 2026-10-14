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

from models.train_baselines import make_dataset

REGIMES = ["TRENDING_BULL", "TRENDING_BEAR", "RANGING", "HIGH_VOLATILITY", "BREAKOUT"]


def classify_regime(row) -> str:
    """Classify rows only when the feature dataset contains the calibrated trend score."""
    required = ("trend_score", "realized_vol_24h", "rsi_14")
    missing = [name for name in required if name not in row]
    if missing:
        raise ValueError(
            "Regime classification requires processed features "
            f"{', '.join(missing)}; rebuild the supported feature dataset first."
        )
    trend = float(row["trend_score"])
    vol = float(row["realized_vol_24h"])
    rsi = float(row["rsi_14"])

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
    print("Loading processed feature history...")
    df, _, _ = make_dataset()
    print(f"  Loaded {len(df):,} feature rows.")
    required_features = {"trend_score", "realized_vol_24h", "rsi_14"}
    missing_features = required_features.difference(df.columns)
    if missing_features:
        raise SystemExit(
            "Processed feature dataset is incompatible; missing required features: "
            + ", ".join(sorted(missing_features))
        )

    counts, probs = compute_transition_matrix(df)
    print_heatmap(probs)
    save_csv(probs)

    most_persistent = max(probs.items(), key=lambda kv: kv[1].get(kv[0], 0.0), default=(None, {}))
    if most_persistent[0]:
        p = most_persistent[1].get(most_persistent[0], 0.0)
        print(f"\n🏆 Most Persistent Regime: {most_persistent[0]} ({p:.2%} self-transition)")

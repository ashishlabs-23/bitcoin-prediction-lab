"""
scripts/signal_quality_report.py -- AI Signal Quality Audit

Generates a detailed quality audit of the AI prediction engine's recent signals.
Analyzes signal consistency, direction distribution, confidence metrics, and
TP/SL coverage to help diagnose prediction engine health.

Usage:
    python scripts/signal_quality_report.py [--days N]

Output:
    - Console report with quality breakdown
    - signal_quality_report.json in project root
"""

import sys
import os
import json
import argparse
from datetime import datetime, timezone, timedelta
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def load_prediction_db():
    """Load prediction records from the SQLite market memory database."""
    try:
        from models.market_memory import load_recent_predictions
        records = load_recent_predictions(limit=500)
        return records
    except Exception as e:
        print(f"⚠️  Could not load prediction DB: {e}")
        return []


def analyze_signals(records, days=7):
    """
    Analyzes recent signal records for quality metrics.

    Args:
        records: List of prediction record dicts.
        days:    Number of days to look back.

    Returns:
        Dict of quality metrics.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = []
    for r in records:
        try:
            ts = datetime.fromisoformat(r.get("timestamp", ""))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                recent.append(r)
        except (ValueError, TypeError):
            continue

    total = len(recent)
    if total == 0:
        return {"error": "No recent predictions found", "total": 0}

    directions = Counter(r.get("direction", "SKIP") for r in recent)
    decisions  = Counter(r.get("decision", "SKIP") for r in recent)
    tp_present = sum(1 for r in recent if r.get("tp") is not None)
    sl_present = sum(1 for r in recent if r.get("sl") is not None)

    probs = [float(r["raw_prob"]) for r in recent if r.get("raw_prob") is not None]
    avg_prob     = round(sum(probs) / len(probs), 4) if probs else None
    high_conf    = sum(1 for p in probs if p > 0.65)
    low_conf     = sum(1 for p in probs if p < 0.52)

    correct      = sum(1 for r in recent if r.get("was_correct"))
    accuracy     = round(correct / total, 4) if total > 0 else None

    return {
        "period_days":     days,
        "total_signals":   total,
        "direction_dist":  dict(directions),
        "decision_dist":   dict(decisions),
        "tp_coverage_pct": round(tp_present / total * 100, 1),
        "sl_coverage_pct": round(sl_present / total * 100, 1),
        "avg_probability": avg_prob,
        "high_conf_signals": high_conf,
        "low_conf_signals":  low_conf,
        "signal_accuracy":   accuracy,
        "generated_at":    datetime.now(timezone.utc).isoformat()
    }


def print_report(metrics):
    """Pretty-prints the signal quality report to console."""
    print("\n" + "="*60)
    print("  📊 AI SIGNAL QUALITY AUDIT REPORT")
    print("="*60)

    if "error" in metrics:
        print(f"  ⚠️  {metrics['error']}")
        return

    print(f"  Period:          Last {metrics['period_days']} day(s)")
    print(f"  Total Signals:   {metrics['total_signals']}")
    print(f"  TP Coverage:     {metrics['tp_coverage_pct']}%")
    print(f"  SL Coverage:     {metrics['sl_coverage_pct']}%")
    print(f"  Avg Probability: {metrics['avg_probability']:.1%}" if metrics['avg_probability'] else "  Avg Probability: N/A")
    print(f"  High Confidence: {metrics['high_conf_signals']} signals (>65%)")
    print(f"  Low Confidence:  {metrics['low_conf_signals']} signals (<52%)")
    print(f"  Signal Accuracy: {metrics['signal_accuracy']:.1%}" if metrics['signal_accuracy'] is not None else "  Signal Accuracy: N/A")
    print()
    print("  Direction Distribution:")
    for d, cnt in sorted(metrics['direction_dist'].items()):
        pct = round(cnt / metrics['total_signals'] * 100, 1)
        bar = "█" * int(pct / 5)
        print(f"    {d:<16} {bar:<20} {cnt:>4} ({pct:.1f}%)")
    print("="*60)


def save_report(metrics, path="signal_quality_report.json"):
    """Save the report as JSON."""
    with open(path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\n✅ Saved report to: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate signal quality audit report")
    parser.add_argument("--days", type=int, default=7, help="Number of days to analyze (default: 7)")
    args = parser.parse_args()

    records = load_prediction_db()
    metrics = analyze_signals(records, days=args.days)
    print_report(metrics)
    save_report(metrics)

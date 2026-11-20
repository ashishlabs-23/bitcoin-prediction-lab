#!/usr/bin/env python3
"""
scripts/generate_walk_forward_manifest.py
==========================================
Generates a RETROSPECTIVE walk-forward manifest for V32.73 entry intelligence research.

IMPORTANT GOVERNANCE NOTICE
----------------------------
This manifest is classified: RETROSPECTIVE_DEVELOPMENT_REPLAY
It covers data that was available during the development period (2022-2026).
It CANNOT and MUST NOT be used to:
  - Override or bypass the Analysis abstention gate in engine/regime_strategy_tournament.py
  - Substitute for confirmatory prospective evidence (minimum 100 clean non-overlapping blocks)
  - Authorize any model for production use
  - Justify directional trading signals

The Analysis abstention gate (lines 1162-1204 of engine/regime_strategy_tournament.py)
is a scientifically mandatory safeguard and must not be circumvented.
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
BACKFILLED_PATH = os.path.join(REPO_ROOT, "data", "raw", "ohlcv_backfilled.parquet")
OUTPUT_DIR = os.path.join(REPO_ROOT, "engine", "manifests")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "v32_73_retrospective_walk_forward_manifest.json")

print("=" * 70)
print("  BTCognitive V32.73 — Retrospective Walk-Forward Manifest Generator")
print("  Classification: RETROSPECTIVE_DEVELOPMENT_REPLAY")
print("  NOT FOR PRODUCTION USE — NOT CONFIRMATORY EVIDENCE")
print("=" * 70)
print()

# ---------------------------------------------------------------------------
# Verify dataset exists and compute SHA256
# ---------------------------------------------------------------------------
if not os.path.isfile(BACKFILLED_PATH):
    print(f"ERROR: Backfilled dataset not found at: {BACKFILLED_PATH}")
    sys.exit(1)

print(f"Computing SHA256 of: {BACKFILLED_PATH}")
sha256 = hashlib.sha256(open(BACKFILLED_PATH, "rb").read()).hexdigest()
print(f"  SHA256: {sha256}")
print()

# Verify known hash
KNOWN_HASH = "1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c"
if sha256 != KNOWN_HASH:
    print(f"WARNING: Hash mismatch vs known V32.73 hash ({KNOWN_HASH})")
    print("         Proceeding, but investigate dataset provenance.")
else:
    print("  Hash matches V32.73 canonical backfilled dataset. [OK]")
print()

# ---------------------------------------------------------------------------
# Dataset metadata
# ---------------------------------------------------------------------------
try:
    import pandas as pd
    df = pd.read_parquet(BACKFILLED_PATH)
    n_rows = len(df)
    first_ts = str(df.index[0]) if hasattr(df.index, '__len__') else "UNKNOWN"
    last_ts = str(df.index[-1]) if hasattr(df.index, '__len__') else "UNKNOWN"
    # Try common timestamp columns
    if "timestamp" in df.columns:
        first_ts = str(df["timestamp"].iloc[0])
        last_ts = str(df["timestamp"].iloc[-1])
    elif "open_time" in df.columns:
        first_ts = str(df["open_time"].iloc[0])
        last_ts = str(df["open_time"].iloc[-1])
    print(f"Dataset shape: {n_rows} rows x {len(df.columns)} columns")
    print(f"  First timestamp: {first_ts}")
    print(f"  Last timestamp:  {last_ts}")
    print()
except Exception as e:
    print(f"WARNING: Could not read parquet metadata: {e}")
    n_rows = "UNKNOWN"
    first_ts = "UNKNOWN"
    last_ts = "UNKNOWN"

# ---------------------------------------------------------------------------
# Active strategy registry (V32.73 state)
# ---------------------------------------------------------------------------
ACTIVE_STRATEGIES = [
    "TSMOM_DONCHIAN_24H_168H",
    "RANGE_BOLLINGER_REVERSION_20H",
    "ATR_VOLATILITY_BREAKOUT_12H",
    "HTF_RANGE_EXPANSION_BREAKOUT",
]

QUARANTINED_STRATEGIES = [
    "CHRONOS2_FOUNDATION",  # quarantined — insufficient evidence
]

# ---------------------------------------------------------------------------
# Walk-forward fold definitions
# 5 chronological expanding folds, 24h embargo between train and test
# NOTE: These folds are on the backfilled dataset (42,177 rows, ends 2026-10-24)
# ---------------------------------------------------------------------------
FOLDS = [
    {
        "fold_id": 1,
        "train_start": "2022-01-01T00:00:00Z",
        "train_end": "2023-06-30T23:00:00Z",
        "embargo_start": "2023-07-01T00:00:00Z",
        "embargo_end": "2023-07-01T23:00:00Z",  # 24h embargo
        "test_start": "2023-07-02T00:00:00Z",
        "test_end": "2023-12-31T23:00:00Z",
        "fold_type": "EXPANDING_TRAIN",
        "purpose": "Early OOS generalization — 2023 H2 regime",
    },
    {
        "fold_id": 2,
        "train_start": "2022-01-01T00:00:00Z",
        "train_end": "2023-12-31T23:00:00Z",
        "embargo_start": "2024-01-01T00:00:00Z",
        "embargo_end": "2024-01-01T23:00:00Z",
        "test_start": "2024-01-02T00:00:00Z",
        "test_end": "2024-06-30T23:00:00Z",
        "fold_type": "EXPANDING_TRAIN",
        "purpose": "2024 H1 bull regime generalization",
    },
    {
        "fold_id": 3,
        "train_start": "2022-01-01T00:00:00Z",
        "train_end": "2024-06-30T23:00:00Z",
        "embargo_start": "2024-07-01T00:00:00Z",
        "embargo_end": "2024-07-01T23:00:00Z",
        "test_start": "2024-07-02T00:00:00Z",
        "test_end": "2024-12-31T23:00:00Z",
        "fold_type": "EXPANDING_TRAIN",
        "purpose": "2024 H2 post-halving regime generalization",
    },
    {
        "fold_id": 4,
        "train_start": "2022-01-01T00:00:00Z",
        "train_end": "2024-12-31T23:00:00Z",
        "embargo_start": "2025-01-01T00:00:00Z",
        "embargo_end": "2025-01-01T23:00:00Z",
        "test_start": "2025-01-02T00:00:00Z",
        "test_end": "2025-06-30T23:00:00Z",
        "fold_type": "EXPANDING_TRAIN",
        "purpose": "2025 H1 regime shift generalization",
    },
    {
        "fold_id": 5,
        "train_start": "2022-01-01T00:00:00Z",
        "train_end": "2025-06-30T23:00:00Z",
        "embargo_start": "2025-07-01T00:00:00Z",
        "embargo_end": "2025-07-01T23:00:00Z",
        "test_start": "2025-07-02T00:00:00Z",
        "test_end": "2026-03-31T23:00:00Z",
        "fold_type": "EXPANDING_TRAIN",
        "purpose": "Most recent OOS window — do not use for model selection",
    },
]

# ---------------------------------------------------------------------------
# Build the manifest
# ---------------------------------------------------------------------------
generation_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

manifest = {
    "manifest_id": "v32_73_retrospective_walk_forward",
    "milestone": "V32.73",
    "generation_utc": generation_utc,

    # ---- CRITICAL CLASSIFICATION ----
    "evidence_classification": "RETROSPECTIVE_DEVELOPMENT_REPLAY",
    "is_confirmatory": False,
    "evidence_role": "RETROSPECTIVE_DEVELOPMENT_REPLAY",
    "prevents_abstention_gate_bypass": True,
    "abstention_gate_note": (
        "This manifest is for exploratory research only. "
        "It MUST NOT be used to override or bypass the Analysis abstention gate "
        "in engine/regime_strategy_tournament.py (lines 1162-1204). "
        "The abstention gate requires a prospective, confirmatory walk-forward manifest "
        "with minimum 100 non-overlapping clean blocks of prospective evidence."
    ),

    # ---- MODEL AUTHORIZATION ----
    "model_authorization": "OFFLINE_RESEARCH_ONLY",
    "live_trading": "DISABLED",
    "production_deployment": "BLOCKED",

    # ---- DATASET PROVENANCE ----
    "dataset": {
        "path": "data/raw/ohlcv_backfilled.parquet",
        "sha256": sha256,
        "known_hash_v32_73": KNOWN_HASH,
        "hash_match": sha256 == KNOWN_HASH,
        "n_rows": n_rows,
        "frequency": "1H",
        "symbol": "BTCUSD",
        "first_timestamp": first_ts,
        "last_timestamp": last_ts,
        "provenance": "Backfilled continuous hourly OHLCV — NOT a raw exchange feed",
        "redistribution_rights": "PRIVATE_OFFLINE_RESEARCH_ONLY",
    },

    # ---- NOMENCLATURE MAP (V26 -> V32.73) ----
    "strategy_nomenclature_map": {
        "v26_strategies": [
            "NO_TRADE_BENCHMARK",
            "TS_MOM_TREND",
            "TRUE_DUAL_SMA_REFERENCE",
            "SHORT_HORIZON_MEAN_REVERSION",
            "VOL_COMPRESSION_BREAKOUT",
            "REGIME_ADAPTIVE_ROUTER",
        ],
        "v32_73_active_strategies": ACTIVE_STRATEGIES,
        "v32_73_quarantined_strategies": QUARANTINED_STRATEGIES,
        "mapping_note": (
            "V26 strategies operated on a different dataset (41,273-row, SHA43c8881b). "
            "V32.73 strategies are re-specified from scratch on the 42,177-row backfilled dataset. "
            "No V26 strategy results should be imported into V32.73 evaluation."
        ),
    },

    # ---- FOLD DEFINITIONS ----
    "fold_count": len(FOLDS),
    "embargo_hours": 24,
    "embargo_rule": "24-hour gap between train_end and test_start at each fold",
    "expanding_train": True,
    "folds": FOLDS,

    # ---- PURGE RULES ----
    "purge_rules": {
        "embargo_hours": 24,
        "purge_method": "CHRONOLOGICAL_GAP",
        "label_overlap_forbidden": True,
        "future_data_forbidden": True,
        "causal_boundary": (
            "All features must be computed from data available at or before the "
            "bar preceding the entry bar (t_feature <= t_issue < t_maturity). "
            "Triple-barrier labels use t_entry+1 OPEN as fill price."
        ),
    },

    # ---- ENTRY INTELLIGENCE TARGETS ----
    "entry_intelligence": {
        "research_targets": [
            "EQR_binary_threshold_1.5",  # excursion_quality_ratio > 1.5
            "triple_barrier_label",       # TP_FIRST=+1, SL_FIRST=-1, EXPIRED=0
            "mfe_regression",             # continuous MFE pct
            "mae_regression",             # continuous MAE pct
        ],
        "tp_pct": 1.5,
        "sl_pct": 0.75,
        "horizon_hours": 24,
        "note": "EQR is NOT a win probability. Barrier ratios are research hypotheses.",
    },
}

# ---------------------------------------------------------------------------
# Write manifest
# ---------------------------------------------------------------------------
os.makedirs(OUTPUT_DIR, exist_ok=True)
with open(OUTPUT_PATH, "w") as f:
    json.dump(manifest, f, indent=2)

print(f"Manifest written to: {OUTPUT_PATH}")
print()
print("=" * 70)
print("  GOVERNANCE REMINDER")
print("=" * 70)
print("  Classification : RETROSPECTIVE_DEVELOPMENT_REPLAY")
print("  Confirmatory   : NO")
print("  Model auth     : OFFLINE_RESEARCH_ONLY")
print("  Abstention gate: MUST NOT BE BYPASSED")
print("  Live trading   : DISABLED")
print()
print("  This manifest cannot serve as confirmatory evidence.")
print("  Minimum 100 non-overlapping prospective blocks are required")
print("  before the Analysis abstention gate can be reviewed.")
print("  Current prospective evidence: 7 / 100 blocks (7.0%)")
print("=" * 70)

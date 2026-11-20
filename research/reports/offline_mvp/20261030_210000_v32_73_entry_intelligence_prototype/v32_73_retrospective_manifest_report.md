# V32.73 — Retrospective Walk-Forward Manifest Report

**Milestone:** V32.73 — Entry Intelligence Prototype & Test Reliability  
**Date:** 2026-10-30  
**Classification:** RETROSPECTIVE_DEVELOPMENT_REPLAY | OFFLINE_RESEARCH_ONLY  
**Manifest file:** `engine/manifests/v32_73_retrospective_walk_forward_manifest.json`

---

> [!IMPORTANT]
> **This manifest is RETROSPECTIVE_DEVELOPMENT_REPLAY.**
> It cannot substitute for confirmatory prospective evidence.
> It must NOT be used to override the Analysis abstention gate.
> Current prospective evidence: 7 / 100 non-overlapping blocks (7.0%).

---

## 1. Purpose

This report documents the design, provenance, and governance constraints of the
retrospective walk-forward manifest generated for V32.73 entry intelligence research.
The manifest provides a chronological fold structure for offline exploratory analysis
using the backfilled OHLCV dataset. It establishes purge rules and embargo specs that
must be respected in any downstream model training experiment.

---

## 2. Dataset Provenance

| Property | Value |
|---|---|
| File | `data/raw/ohlcv_backfilled.parquet` |
| SHA256 | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` |
| Rows | 42,177 |
| Frequency | 1H (hourly) |
| Symbol | BTCUSD |
| First timestamp | 2022-01-01 00:00:00+00:00 |
| Last timestamp | 2026-10-24 08:00:00+00:00 |
| Provenance | Backfilled continuous hourly OHLCV |
| Redistribution rights | PRIVATE_OFFLINE_RESEARCH_ONLY |

**Note:** The raw feed (`data/raw/ohlcv.parquet`, SHA256 `c007cd613bec...`, 42,233 rows,
ends 2026-10-26) is a distinct file. The backfilled version is preferred for walk-forward
splits because gaps have been filled and continuity is verified.

---

## 3. Strategy Nomenclature Map

### 3.1 V26 Canonical Manifest Strategies

The V26 canonical strategy manifest (`experiments/results/v26_canonical_strategy_manifest.json`)
was computed on a **different dataset** (41,273 rows, SHA `43c8881b...`). It cannot be
adapted or reused for V32.73 experiments.

| V26 Strategy ID | V32.73 Status |
|---|---|
| NO_TRADE_BENCHMARK | Not carried forward (different dataset) |
| TS_MOM_TREND | Superseded by TSMOM_DONCHIAN_24H_168H |
| TRUE_DUAL_SMA_REFERENCE | Retired |
| SHORT_HORIZON_MEAN_REVERSION | Superseded by RANGE_BOLLINGER_REVERSION_20H |
| VOL_COMPRESSION_BREAKOUT | Superseded by ATR_VOLATILITY_BREAKOUT_12H |
| REGIME_ADAPTIVE_ROUTER | Superseded by HTF_RANGE_EXPANSION_BREAKOUT |

### 3.2 V32.73 Active Strategy Registry

| V32.73 Strategy ID | Status |
|---|---|
| TSMOM_DONCHIAN_24H_168H | ACTIVE |
| RANGE_BOLLINGER_REVERSION_20H | ACTIVE |
| ATR_VOLATILITY_BREAKOUT_12H | ACTIVE |
| HTF_RANGE_EXPANSION_BREAKOUT | ACTIVE |
| CHRONOS2_FOUNDATION | QUARANTINED — insufficient prospective evidence |

---

## 4. Walk-Forward Fold Definitions

5 chronological expanding folds. 24-hour embargo between train end and test start.

| Fold | Train Start | Train End | Test Start | Test End | Purpose |
|---|---|---|---|---|---|
| 1 | 2022-01-01 | 2023-06-30 | 2023-07-02 | 2023-12-31 | Early OOS — 2023 H2 |
| 2 | 2022-01-01 | 2023-12-31 | 2024-01-02 | 2024-06-30 | 2024 H1 bull regime |
| 3 | 2022-01-01 | 2024-06-30 | 2024-07-02 | 2024-12-31 | 2024 H2 post-halving |
| 4 | 2022-01-01 | 2024-12-31 | 2025-01-02 | 2025-06-30 | 2025 H1 regime shift |
| 5 | 2022-01-01 | 2025-06-30 | 2025-07-02 | 2026-03-31 | Most recent OOS window |

> [!WARNING]
> Fold 5 is the most recent OOS window. It must NOT be used for model selection.
> Use only for final generalization assessment after hyperparameters are locked
> using folds 1–4.

---

## 5. Purge Rules and Embargo Specification

| Rule | Value |
|---|---|
| Embargo hours | 24 hours |
| Purge method | CHRONOLOGICAL_GAP |
| Label overlap | Forbidden — no triple-barrier labels may span the embargo gap |
| Future data | Forbidden — all features must be computed from data at or before the entry bar |
| Causal boundary | `t_feature <= t_issue < t_maturity` |
| Fill price | OPEN of bar `entry_idx + 1` (next bar after entry bar) |

---

## 6. Evidence Classification and Governance

| Property | Value |
|---|---|
| Evidence classification | RETROSPECTIVE_DEVELOPMENT_REPLAY |
| Is confirmatory | NO |
| Model authorization | OFFLINE_RESEARCH_ONLY |
| Abstention gate bypass | PROHIBITED |
| Live trading | DISABLED |

### 6.1 Why This Manifest Cannot Unlock the Abstention Gate

The Analysis abstention gate (`engine/regime_strategy_tournament.py` lines 1162-1204)
requires a **confirmatory, prospective** walk-forward manifest — one generated on
data that was not available at model development time. The V32.73 manifest covers
2022–2026, the entire development period. This data was retrospectively available
during research. Therefore:

- All performance statistics computed on these folds are **development-phase estimates**.
- They are subject to look-ahead bias at the research design level, even if causal
  boundaries are respected within each fold.
- They cannot be used to justify production deployment, signal generation, or
  bypassing the `ABSTAIN` output of the Analysis button.

### 6.2 Prospective Evidence Status

| Metric | Value |
|---|---|
| Target blocks for confirmatory gate | 100 |
| Current post-repair blocks (V32.73) | 7 |
| Progress | 7.0% |
| Expected time to gate (at ~1 block/day) | ~93 days |
| Confirmatory gate status | NOT_STARTED → COLLECTING |

---

## 7. Manifest File Reference

The manifest JSON was generated by `scripts/generate_walk_forward_manifest.py` and
written to `engine/manifests/v32_73_retrospective_walk_forward_manifest.json`.

Key fields:
```json
{
  "manifest_id": "v32_73_retrospective_walk_forward",
  "evidence_classification": "RETROSPECTIVE_DEVELOPMENT_REPLAY",
  "is_confirmatory": false,
  "prevents_abstention_gate_bypass": true,
  "model_authorization": "OFFLINE_RESEARCH_ONLY",
  "live_trading": "DISABLED"
}
```

---

*End of retrospective manifest report.*


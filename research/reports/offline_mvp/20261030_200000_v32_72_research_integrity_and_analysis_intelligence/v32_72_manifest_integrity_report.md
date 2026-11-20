# BTCognitive V32.72 — Workstream 1: Walk-Forward Manifest Integrity & Pre-Registration Audit

**Milestone:** V32.72 Research Integrity & Analysis Intelligence  
**Date:** 30 October 2026  
**Auditor:** Quantitative Research Engineer & Lead Orchestrator  
**Status:** COMPLETE — PRE-REGISTRATION BOUNDARIES & DATASET PROVENANCE AUDITED  

---

## Executive Summary

This investigation addresses **Management Issue A**: *"Manifest generation is not automatically validation. We must establish whether the manifest is genuinely pre-registered relative to the evaluation it governs. A manifest created after inspecting the same evaluation results cannot automatically serve as independent confirmatory evidence."*

We conducted a forensic code and manifest audit across historical and active candidates, tracing dataset provenance, strategy nomenclature, temporal splitting boundaries, and purge/embargo rules.

**Key Finding:** 
The repository contains two conflicting strategy nomenclatures:
1. **Legacy V26 Manifest (`experiments/results/v26_canonical_strategy_manifest.json`):** Evaluated `TS_MOM_TREND` and `VOL_COMPRESSION_BREAKOUT` over a 41,273-row Coinbase raw parquet dataset.
2. **Active Runtime Registry (`engine/regime_strategy_tournament.py`):** Registers `TSMOM_DONCHIAN_24H_168H`, `RANGE_BOLLINGER_REVERSION_20H`, `ATR_VOLATILITY_BREAKOUT_12H`, and `HTF_RANGE_EXPANSION_BREAKOUT`.

Because no pre-registered manifest exists for the active runtime strategies on the canonical 42,233-row backfilled dataset, any manifest generated today constitutes **retrospective exploratory fitting / development replay**, NOT confirmatory validation.

Therefore, the Analysis engine's fail-closed `ABSTAIN` behavior is **scientifically mandatory** and must remain active until prospective out-of-sample data is accumulated.

---

## 1. Strategy Identity & Nomenclature Mapping

The table below reconciles the historical V26 strategy identifiers with the active V32 strategy registry:

| Legacy ID (V26 Manifest) | Active Registry ID (V32.48+) | Mathematical Implementation | Status / Compatibility |
| :--- | :--- | :--- | :--- |
| `TS_MOM_TREND` | `TSMOM_DONCHIAN_24H_168H` | V26 was Dual-EMA crossover (24h/168h); V32 is 24h/168h Donchian channel breakout with ATR filter. | **DIVERGENT ALGORITHM**: Cannot reuse V26 manifest metrics. |
| `VOL_COMPRESSION_BREAKOUT` | `ATR_VOLATILITY_BREAKOUT_12H` | 12-hour ATR compression threshold with directional breakout. | **PARAMETER SHIFT**: Lookback window modified from 24h to 12h. |
| *(None)* | `RANGE_BOLLINGER_REVERSION_20H` | Bollinger Band (20-period, 2.0 std) mean reversion with RSI confirmation. | **NEW CANDIDATE**: Zero pre-registered historical splits. |
| *(None)* | `HTF_RANGE_EXPANSION_BREAKOUT` | Multi-timeframe daily range expansion. | **NEW CANDIDATE**: Zero pre-registered historical splits. |
| `CHRONOS2_FOUNDATION` | `CHRONOS2_FOUNDATION` | Amazon Chronos-2 zero-shot foundation model. | **QUARANTINED**: Permanently disqualified under V32.37 governance decision. |

**Inference:** The active strategies are structurally different implementations from the legacy V26 algorithms. Reusing or aliasing the V26 manifest would fabricate false historical pedigree.

---

## 2. Dataset Provenance & Cryptographic Hashes

A valid walk-forward manifest must cryptographically bind to its underlying source data:

| Dataset Asset | Expected Historical SHA-256 (V26) | Canonical Verified SHA-256 (Active) | Total Rows | Audit Status |
| :--- | :--- | :--- | :--- | :--- |
| `data/raw/ohlcv.parquet` | `43c8881b...` | `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f` | 42,233 | Historical baseline raw |
| `data/raw/ohlcv_backfilled.parquet` | *(Unbackfilled in V26)* | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | 42,233 | Canonical continuous dataset |

The canonical research dataset has 42,233 continuous hourly bars (spanning 2022-01-01 to 2026-10-26 UTC). The historical V26 manifest was computed on an older 41,273-row slice ending in mid-2026.

---

## 3. Chronological Splits, Purge, and Embargo Specifications

To prevent data snooping and auto-correlation leakage in future exploratory walk-forward runs:

```
[Fold 1: Train 2022-01 to 2023-06] ──[24h Embargo]──> [Fold 1 Test: 2023-07 to 2023-12]
[Fold 2: Train 2022-01 to 2023-12] ──[24h Embargo]──> [Fold 2 Test: 2024-01 to 2024-06]
[Fold 3: Train 2022-01 to 2024-06] ──[24h Embargo]──> [Fold 3 Test: 2024-07 to 2024-12]
[Fold 4: Train 2022-01 to 2024-12] ──[24h Embargo]──> [Fold 4 Test: 2025-01 to 2025-06]
[Fold 5: Train 2022-01 to 2025-06] ──[24h Embargo]──> [Fold 5 Test: 2025-07 to 2026-03]
```

### Pre-Registration Rules:
1. **Purging:** Any training observations whose forward 24-hour return window overlaps with test fold start are purged.
2. **Embargo:** A 24-hour buffer ($t_{\text{test\_end}}$ to $t_{\text{test\_end}} + 24$) is placed after each test window to eliminate serial dependence.
3. **Information Barrier:** Indicator parameters (ATR, ADX, Bollinger bandwidth) must be calculated strictly with causal filters ($\text{adjust}=\text{False}$, $t \le \text{bar}_i$).

---

## 4. Confirmatory vs. Exploratory Classification

In accordance with BTCognitive Prime Directive §2 (Epistemic Principles):
- **Exploratory Evidence:** Any manifest derived from historical data (including 2022–2026 replay) is **retrospective development data**.
- **Confirmatory Evidence:** ONLY out-of-sample forward observations collected post-freeze via `data/prospective_entry_ledger_v2.jsonl` qualify as confirmatory evidence.

### Pre-Registration Decision:
Because generating a manifest today would occur *after* the dataset and models are known, it cannot be labeled "pre-registered confirmatory". It must be explicitly stamped:  
`evidence_classification: RETROSPECTIVE_DEVELOPMENT_REPLAY`

---

## 5. Governed Recommendation

1. **Do not fabricate pre-registration:** The tournament engine must continue to output `gate_status: "ABSTAIN_UNVERIFIED_MANIFEST"` for production decision routes.
2. **Specification Schema:** When generated in V32.73, the manifest schema must record:
   - `dataset_sha256`: `1e722f33734a...`
   - `generation_utc`: Exact runtime ISO timestamp
   - `is_confirmatory`: `false`
   - `evidence_role`: `OFFLINE_RESEARCH_EXPLORATORY`


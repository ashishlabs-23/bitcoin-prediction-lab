# BTCognitive V32.71 — Priority 6: Research Integrity, Shadow Monitoring & Provenance Report

**Milestone:** V32.71 Core Intelligence Remediation  
**Date:** 30 October 2026  
**Auditor:** Quantitative Research Engineer & Lead Orchestrator  
**Status:** COMPLETE — RESEARCH INTEGRITY & PROVENANCE STRICTLY VERIFIED  

---

## Executive Summary

This report assesses the integrity of BTCognitive's research ledgers, data collectors, prospective shadow monitors, and governance quarantine manifests.

**Key Finding:** 
1. All research data assets remain intact and protected.
2. The prospective shadow runners (`ShadowFeedRunner`, `ProspectiveWorker`) strictly enforce append-only immutability.
3. Training/validation splits maintain total physical isolation from prospective test ledgers.
4. Live broker trading remains permanently disabled by architectural design.

---

## 1. Status of Collectors and Background Runners

### `ShadowFeedRunner` (`engine/shadow_feed_runner.py`)
- **Function:** Captures live/simulated market ticks and emits hourly closed candle events.
- **Operating Boundary:** Runs in local loopback environment.
- **Fail-Safe Mechanism:** In fixture and offline modes, network calls are blocked. If an invalid or non-monotonic timestamp is encountered, the runner fails closed.

### `ProspectiveWorker` (`engine/prospective_worker.py`)
- **Function:** Records forward-looking model forecasts and subsequently evaluates realized outcomes once the maturity horizon ($t+24$ or $t+168$) has elapsed.
- **Ledger Destination:** `data/prospective_entry_ledger_v2.jsonl`.
- **Integrity Rule:** Records are strictly append-only. Existing entries cannot be updated in-place; outcome resolutions are appended as separate `OUTCOME_RESOLVED` events referencing the initial forecast `uuid`.

---

## 2. Protected Research Ledgers & Quarantine Manifests

BTCognitive enforces cryptographic verification over six critical data assets:
1. `data/raw/ohlcv.parquet` (Historical baseline raw data)
2. `data/raw/ohlcv_pre_backfill_backup.parquet` (Pre-backfill preservation copy)
3. `data/raw/ohlcv_backfilled.parquet` (Canonical continuous research dataset)
4. `data/prospective_entry_ledger.jsonl` (V1 prospective evaluation ledger)
5. `data/prospective_shadow_v1.jsonl` (V1 shadow run output)
6. `data/prospective_entry_ledger_v2.jsonl` (Active V2 prospective evaluation ledger)

### Hash Verification Results:
As documented in `v32_71_protected_hash_verification.json`, **100% of these files match their authoritative SHA-256 baseline hashes bit-for-bit**. No tampering, overwriting, or silent data mutation has occurred.

---

## 3. Retrospective vs. Prospective Evidence Boundary

To prevent overfitting and false discoveries, BTCognitive governance strictly separates evidence categories:

| Evidence Class | Datasets Included | Permitted Usage | Governance Status |
| :--- | :--- | :--- | :--- |
| **Development / Training Data** | 2021-03 to 2024-12 (`ohlcv_backfilled.parquet`) | Model fitting, parameter estimation, feature selection. | Retrospective (Subject to discovery bias) |
| **Retrospective Out-of-Sample** | 2025-01 to 2026-03 (`ohlcv_backfilled.parquet`) | Purged validation, baseline comparison, stress testing. | Development Replay (NOT confirmatory) |
| **Prospective Confirmatory** | `prospective_entry_ledger_v2.jsonl` | True out-of-sample statistical gate. | **Confirmatory Gate: Requires $\ge 100$ non-overlapping blocks post-freeze** |

Currently, prospective data accumulation is in status: `COLLECTING` (insufficient sample size for final confirmatory sign-off, but fully verified in collection mechanics).

---

## 4. Live Trading & Execution Isolation

- **Exchange/Broker APIs:** None configured, imported, or accessible in runtime paths.
- **API Keys / Secrets:** No live private keys exist in repository configs.
- **Order Execution Engine:** Purely local simulation with deterministic logging.
- **Operational Verdict:** Live capital deployment is **DISABLED**.


# BTCognitive V32.63 — Feature Value & Calculation Correctness Audit Report

**Date:** 29 October 2026  
**Auditor / Lead Orchestrator:** BTCognitive Lead Research Orchestrator  
**Audit Identifier:** `20261029_223400_audit`  
**Location:** `BTCognitive/research/reports/v32_63_feature_value_audit/20261029_223400_audit/`  
**Execution Environment:** Windows 11, Python 3.13.14 (`.venv_win`), pytest-8.4.1  
**Authoritative SHA-256 (Canonical Raw):** `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f`  

---

## 1. Executive Summary

This audit establishes, with reproducible test evidence and hand-computed golden fixtures, (1) what every feature in BTCognitive does, (2) whether it contributes real user value, and (3) whether its underlying data and calculations are numerically correct.

### Key Discoveries & Milestones:
1. **The Row Count Mystery Reconciled:** The canonical raw dataset (`data/raw/ohlcv.parquet`) contains exactly **42,233 rows** spanning `2022-01-01 00:00:00 UTC` to `2026-10-26 16:00:00 UTC` with **zero interior gaps, zero NaNs, and zero Infs**. The 42,237-row figure cited in prior documents belongs to the V2/V3 research parquet (`data/research/..._v2`), which extends 17 hours further (`2026-10-27 09:00 UTC`) but lacks 13 hours across 3 historical gaps ($42,233 = 42,237 + 13 - 17$). Both datasets are internally consistent.
2. **10/10 Unit Tests Passed:** Pytest suite `tests/test_v32_63_calculation_correctness.py` passed all 10 tests in 32.51 seconds. EMA, True Range, Bollinger Bandwidth, Parkinson Volatility, Wilson 95% Confidence Intervals, and Break-Even Win Rate match hand-computed analytical fixtures within $10^{-4}$ tolerance.
3. **Causal Invariance Verified:** Donchian channels strictly use `shift(1)` to exclude bar $t$. Zero lookahead bias was detected.
4. **Analyse Workflow Non-Destructive:** Triggering the complete 7-step Analyse pipeline on 42,233 bars returns in ~2.1 seconds, creates zero simulated attempts (`attempts_created == 0`), and produces zero bytes of ledger mutation.
5. **Protected Files Bit-Identical:** All 6 protected research datasets and prospective ledgers were verified bit-for-bit identical before and after the audit via SHA-256 manifests.

---

## 2. Answers to the Six Mandatory Concluding Questions

### Question 1: How many rows are actually in `data/raw/ohlcv.parquet`, and what explains the conflicting 42,233 vs. 42,237 reports?
**Authoritative Answer:**
`data/raw/ohlcv.parquet` contains exactly **42,233 rows** (SHA-256: `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f`).

The explanation is an empirical difference between two distinct files in the repository:
- `data/raw/ohlcv.parquet` (the backend's active candle source) terminates at `2026-10-26 16:00:00 UTC` and has the 13 historical gap candles backfilled, yielding 42,233 contiguous hourly bars.
- `data/research/coinbase_btc_usd_hourly_verified_v2/coinbase_btc_usd_hourly.parquet` (and `v3`) extends 17 hours further to `2026-10-27 09:00:00 UTC` (+17 bars), but preserves 3 unbackfilled historical gaps totaling 13 missing candles (-13 bars).
- Mathematical proof: $42,233 + 17 - 13 = 42,237$. Prior reports conflated the two file paths.

---

### Question 2: What are the exact timestamp bounds of the dataset relative to the audit date?
**Authoritative Answer:**
- **Start Timestamp:** `2022-01-01 00:00:00+00:00` (UTC)
- **End Timestamp:** `2026-10-26 16:00:00+00:00` (UTC)
- **Audit Date:** `29 October 2026, 22:34 UTC+05:30` (approx `17:04 UTC`)
- **Temporal Status:** The data terminates **73.07 hours (3.04 days)** prior to this audit. The dataset represents **retrospective historical replay data**, not a live real-time market feed.

---

### Question 3: Which technical indicators and calculations are verified numerically correct vs. which have discrepancies?
**Authoritative Answer:**
- **Verified Numerically Correct (Exact Parity):**
  - **EMA (20/50/200):** Matches standard recursive $\alpha = 2/(N+1)$ formulation ($< 10^{-6}$ error).
  - **ATR-14:** Matches Wilder's True Range handling of normal candles, gap-ups, and gap-downs ($< 10^{-4}$ error).
  - **Donchian 24h Channels:** Verified strict causal non-lookahead via `.shift(1)`.
  - **Bollinger Bands (20, 2):** Matches standard population deviation conventions.
  - **Parkinson Volatility:** Matches analytical high-low realized variance.
  - **Wilson Score 95% CI:** Exact analytical quadratic formula match ($7/10 \implies [0.3968, 0.8922]$).
  - **Break-Even Win Rate:** Exact match across 0 bps (40.0%), 27 bps (52.9%), 87 bps (81.6%), and 187 bps (129.4%).
- **Documented Variance:**
  - **ADX-14:** The market regime classifier in `engine/regime_strategy_tournament.py` applies the full second Wilder smoothing pass and matches standard TA-Lib ADX. However, `engine/strategy_signal_engine.py` terminates at the $DX$ stage. The core product decision path operates on the verified tournament ADX.

---

### Question 4: Does the "Analyse" button perform causal calculations without lookahead or ledger mutations?
**Authoritative Answer:**
**YES.**
- Verified via `test_09_offline_analyse_zero_mutations` using FastAPI `TestClient`.
- The endpoint completes the 7-step workflow (data validation $\to$ regime classification $\to$ candidate shortlisting $\to$ 7/10 screening $\to$ cost evaluation $\to$ smart entry decision) on closed historical bars.
- Invariance: `attempts_created == 0`, and file byte size of `data/prospective_entry_ledger.jsonl` was identical before and after execution (1,141 bytes).

---

### Question 5: What is the recommended disposition of features for the Offline Research Mode MVP?
**Authoritative Answer:**
1. **Core MVP (Keep & Prioritize):**
   - Historical Candlestick Chart (TradingView Lightweight Charts v4.1.3).
   - Core Indicator Overlays (EMA-20/50/200, Donchian 24h, Bollinger Bands, ATR-14).
   - Market Regime Classifier & 7/10 Preliminary Strategy Screen with Wilson 95% CIs.
   - Execution Cost & Friction Model (Friction in R & Break-Even Win Rate).
   - "Analyse" Button Workflow.
   - Terminal Governance & Model Authorization Fail-Closed Enforcement.
2. **Secondary Research Mode (Retain Privately, Do Not Expose Publicly):**
   - Manual Trade Journal & User Position Copilot.
   - Prospective Shadow Collector (`prospective_shadow_v1.jsonl`).
3. **Deferred / Excluded:**
   - External Multi-Exchange Spot Comparator (fails offline; defer until licensed feed).
   - Coinbase L2 Orderbook Depth Collector (high bandwidth/cost; unneeded for hourly MVP).
   - Coinbase 15m Adapter (requires 1-min raw ingestion; out of scope for hourly parquet).
4. **Quarantined:**
   - Amazon Chronos-2 Foundation Model (inferior to HAR-RS-DOW; high compute; quarantined).

---

### Question 6: What are the authoritative governance decisions for V32.63?
**Authoritative Decisions:**
1. **Research Experiment:** `PASS` (Feature Value & Calculation Correctness verified) and `RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY`.
2. **Prospective Evidence:** `COLLECTING` (Ledgers preserved bit-identical; awaiting post-freeze observations).
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY` (Permanent hard lock).
4. **Live Trading:** `DISABLED` (Strict non-execution; zero capital deployment).

---

## 3. Deliverables Manifest

All 10 required artifacts have been generated in `research/reports/v32_63_feature_value_audit/20261029_223400_audit/`:
1. `commands_and_environment.txt` — Python 3.13.14, Windows 11, commit `25d483f`
2. `git_status_before.txt` & `git_status_after.txt` — Main branch integrity preserved
3. `protected_hash_manifest_before.json` & `protected_hash_manifest_after.json` — 6/6 hashes bit-identical
4. `dataset_integrity_report.md` — Complete row-count & gap reconciliation
5. `feature_inventory.csv` — Full 22-column registry of 28 platform capabilities
6. `feature_dependency_map.md` — UI $\to$ API $\to$ Engine $\to$ Data lineage diagrams
7. `calculation_contracts.md` — Canonical mathematical formulas & warm-up contracts
8. `golden_calculation_cases.json` — Deterministic test fixtures with exact hand-calculated targets
9. `tests/test_v32_63_calculation_correctness.py` — Pytest suite (10/10 passed)
10. `indicator_parity_report.md` — TA-Lib / numpy reference comparison
11. `feature_value_assessment.md` — 0–3 scoring and strategic roadmap
12. `test_evidence_matrix.csv` & `known_issues.csv` — Execution trace and issue registers
13. `report.md` — Executive summary and governance decisions


# V32.73 — Manager Handover

**Milestone:** V32.73 — Entry Intelligence Prototype & Test Reliability  
**Date:** 2026-10-30  
**Prepared by:** BTCognitive Research Orchestrator  
**For review by:** Product Manager

---

## Four Governed Decisions

| Decision | Status |
|---|---|
| Research Experiment | **READY_FOR_V32_74** |
| Prospective Evidence | **COLLECTING** — 7 / 100 blocks (7.0%) |
| Model Authorization | **OFFLINE_RESEARCH_ONLY** |
| Live Trading | **DISABLED** |

---

## 1. What V32.73 Established

### 1.1 Test Reliability — Resolved

| Issue | Root Cause | Fix | Result |
|---|---|---|---|
| `test_matrix_f` FAIL (1) | Wrong SHA256 — test used backfilled hash for raw parquet path | Corrected expected hash in test_v32_48 | PASS |
| 4 longitudinal tests `assert 7 == 0` | Tests written at 0-blocks; DB legitimately grew to 7 blocks | Monkeypatch to isolate from live DB (intent preserved) | PASS |

**Before:** 29 pass / 1 fail (V32.47+48) + 4 fail / 2 pass (longitudinal) = 5 failures  
**After:** 36 pass / 0 fail across all 5 test files

No test assertion was weakened. The 7 live prospective blocks are documented and
counted toward the 100-block confirmatory gate.

### 1.2 Entry Intelligence Module — Designed and Verified

Five production-quality research modules implemented in `research/entry_intelligence/`:

| Module | Function |
|---|---|
| `excursion_calculator.py` | MFE/MAE/EQR computation with causal next-bar fill |
| `triple_barrier_labeler.py` | TP/SL/EXPIRED/AMBIGUOUS labels with gap exclusion |
| `entry_quality_metrics.py` | Aggregation, bootstrap CIs, 5-scenario net EV |
| `cost_sensitivity.py` | 5 fee scenarios including UNVERIFIED passive maker |
| `research_evaluator.py` | OOS splits, volatility regime segmentation |

All modules verified with real data from `ohlcv.parquet` (42,233 rows).

### 1.3 Empirical Research Observations

**These are retrospective development-data observations. They are NOT performance guarantees.**

| Metric | LONG | SHORT |
|---|---|---|
| TP_FIRST frequency | 27.5% | 25.0% |
| SL_FIRST frequency | 62.0% | 61.5% |
| EXPIRED frequency | 9.5% | 12.5% |
| AMBIGUOUS | 1.0% | 1.0% |
| Gross EV (pre-cost) | **-0.053%** per trade | **-0.086%** per trade |
| EQR mean | 10.02 | 5.29 |

The negative gross EV reflects **uniform bar sampling** — not a strategy signal.
A strategy filter is expected to select a subset of bars with higher conditional
TP frequency. Whether that is achievable is the V32.74 research question.

### 1.4 Walk-Forward Manifest — Generated

`engine/manifests/v32_73_retrospective_walk_forward_manifest.json` was generated
by `scripts/generate_walk_forward_manifest.py`. Classification:
`RETROSPECTIVE_DEVELOPMENT_REPLAY`. It contains 5 expanding folds with 24h embargo
on the backfilled parquet (42,177 rows).

**This manifest cannot unlock the Analysis abstention gate.** The gate requires
a confirmatory, prospective manifest backed by 100+ non-overlapping clean blocks.

### 1.5 Protected Files — Bit-Identical (Start and End)

All 6 protected research datasets and ledgers verified unchanged at both the start
and end of V32.73 execution.

| File | SHA256 | Status |
|---|---|---|
| `data/raw/ohlcv.parquet` | `c007cd61...` | PASS |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b...` | PASS |
| `data/raw/ohlcv_backfilled.parquet` | `1e722f33...` | PASS |
| `data/prospective_entry_ledger.jsonl` | `91c3aed9...` | PASS |
| `data/prospective_shadow_v1.jsonl` | `e3b0c442...` | PASS |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c...` | PASS |

---

## 2. What V32.73 Did NOT Establish

| Gap | Status |
|---|---|
| Model training | NOT DONE — V32.73 is a design and research module milestone only |
| Confirmatory EV evidence | NOT AVAILABLE — requires 100+ prospective blocks |
| Volatility regime segmentation | Designed, not executed — deferred to V32.74 |
| Entry signal filter | NOT DESIGNED — uniform sampling only in V32.73 |
| 5 SQLite concurrency test fixes | Deferred — test infrastructure, not research gate |
| 4 provenance dimension test fixes | Deferred — legacy row count expectations |
| 4 timestamp staleness test fixes | Deferred — need virtual clock fixture |

---

## 3. Remaining Known Test Failures (Out of V32.73 Scope)

| Group | Count | Deferred to |
|---|---|---|
| test_experiment_integrity_v4 | 4 | V32.74 |
| test_stage8_data_experiments | 1 | V32.74 |
| test_scenario_freshness_and_contract_v7 | 4 | V32.74 |
| test_scenario_planner_and_inference_v6 | 5+ | V32.74 |
| SQLite concurrency / missing / corrupt DB | 5 | V32.74 |

None of these failures affect the entry intelligence prototype or the V32.73 research findings.

---

## 4. Invariants Maintained

| Invariant | Status |
|---|---|
| Analysis abstention gate | INTACT — not modified |
| No live trading | CONFIRMED |
| No external API calls | CONFIRMED |
| No git commits | CONFIRMED |
| No protected file modification | CONFIRMED (verified by SHA256) |
| Model authorization | OFFLINE_RESEARCH_ONLY |
| EQR described as win probability | NEVER — explicit disclaimer in all reports |
| SCEN_3_PASSIVE_MAKER | Labeled UNVERIFIED throughout |
| Manifest labeled retrospective | CONFIRMED |

---

## 5. V32.74 Recommended Scope

Based on V32.73 findings, V32.74 should:

**P0 — Complete test isolation (deferred from V32.73):**
- Fix provenance dimension tests (update legacy row count expectations to 42,233)
- Fix timestamp staleness tests (virtual clock fixture in conftest.py)
- Fix SQLite concurrency tests (production error handling improvements)

**P1 — Entry signal research:**
- Design a causal entry signal filter using the V32.73 feature schema
- Run the ResearchEvaluator with actual signal filtering (not uniform sampling)
- Produce conditional TP/SL frequencies under the signal
- Report with EQR bootstrap CIs (median, not mean)

**P2 — Volatility regime segmentation:**
- Execute `ResearchEvaluator.segment_by_volatility()` on the full dataset
- Report label distributions by regime (low/mid/high vol)

**P3 — Training specification:**
- Implement the V32.73 model training specification (4 targets, 8 features, 5-fold OOS)
- Do NOT promote any model — V32.74 is training execution only

**Governance — unchanged:**
- Continue prospective evidence collection (target: 100 blocks)
- No abstention gate review until 100 confirmatory prospective blocks
- Model authorization: OFFLINE_RESEARCH_ONLY
- Live trading: DISABLED

---

## 6. Prospective Evidence Position

| Metric | Value |
|---|---|
| Target blocks (confirmatory gate) | 100 |
| Current blocks (end of V32.73) | **7** |
| Progress | **7.0%** |
| Estimated completion (at ~1/day) | ~93 days |
| Gate status | COLLECTING |

The 7 blocks are legitimate post-repair prospective evidence accumulated by the
shadow collector since August 2026. They count toward the 100-block gate and must
not be discarded or reset.

---

*End of V32.73 Manager Handover.*


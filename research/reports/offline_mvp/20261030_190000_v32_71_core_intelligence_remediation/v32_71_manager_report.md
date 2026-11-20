# BTCognitive V32.71 — Product Manager Milestone & Handover Report

**Milestone:** V32.71 Core Intelligence Remediation  
**Date:** 30 October 2026  
**Auditor & Orchestrator:** Senior Quantitative Research Engineer & Lead Orchestrator  
**Baseline Git Commit:** `25d483f4c3646661b57311de9d0b53d2be881adb` on `main`  
**Application Context:** Private, offline-first BTC/USD research and trading-analysis application (127.0.0.1:8000)  

---

## 1. Executive Summary & Final Governed Decision

Following the Product Manager's decision on the V32.70 audit, milestone **V32.71 Core Intelligence Remediation** has been executed end-to-end. 

All technical investigations into the Analysis button abstention gate, the directional model performance deficit, the execution cost and payoff engines, test suite reliability, local training infrastructure, and research data provenance have been completed. All six canonical protected datasets and ledgers were cryptographically verified and remain **100% bit-identical**.

### Final Governed Decisions:
1. **Milestone Handover Verdict:** **`READY_FOR_V32_72`**  
   *(The root causes of all identified weaknesses are isolated, proven safe, and equipped with rigorous, verified engineering solutions for implementation in V32.72).*
2. **Research Experiment Status:** **`RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY`**  
   *(The directional model `directional-gbm-4lag-v1` must not be promoted due to negative economic expectancy (-13.09 bps/bar); the volatility model `HAR-RS-DOW` is retained as primary baseline).*
3. **Prospective Evidence Status:** **`COLLECTING`**  
   *(Prospective ledgers are actively accumulating; confirmatory evaluation requires $\ge 100$ non-overlapping blocks post-freeze).*
4. **Model Authorization:** **`OFFLINE_RESEARCH_ONLY`**  
   *(No model is authorized for automated or production trading).*
5. **Live Broker Execution:** **`DISABLED`**  
   *(Permanently out of scope).*

---

## 2. Status of Key Remediation Priorities

| Priority | Focus Area | Investigation Finding | Remediation Resolution |
| :--- | :--- | :--- | :--- |
| **P0** | **Analysis Gate & Tournament** | The `ABSTAIN` verdict at lines 1162–1204 of `regime_strategy_tournament.py` is an **intentional epistemic safety gate** that prevents dangerous mock heuristics (`i % 3 != 0`) from fabricating live trading signals. | **Retain gate**; generate an aligned offline walk-forward manifest (`v32_canonical_walk_forward_manifest.json`) matching active candidate names in V32.72. |
| **P0** | **Directional Model Deficit** | `directional-gbm-4lag-v1` achieves 53.28% out-of-sample accuracy across 33,919 bars, but high turnover (12,873 changes) and 7–14 bps fee friction generate **-13.09 bps/bar** net return and -23.37 Sharpe. | **Do not promote**. Keep directional model in `OFFLINE_RESEARCH_ONLY`. Re-target models toward volatility and persistent regime filtering. |
| **P1** | **Execution Cost & Payoff** | Execution cost model defaults to conservative 60–87 bps Coinbase taker fees. Payoff engine properly enforces $\mathbb{E}[\text{Net EV}] > 0$. | Add Maker (15–25 bps) with adverse selection haircuts in V32.72. |
| **P1** | **Test Reliability** | 17 tests blocked on obsolete pre-backfill row counts (40,902 vs 42,233 canonical rows); 5 SQLite tests failed on relative paths. | Reconciled in report; parameterize dataset dimensions and use in-memory SQLite fixtures in V32.72. |
| **P2** | **Training Infrastructure** | HAR-RS-DOW and LightGBM train fast on CPU (< 10s). Deep learning (TFT/Mamba) is disconnected and unsuited for low SNR financial series. | Archive deep learning prototypes; retain CPU-compatible statistical and tree models. |
| **P1** | **Research Integrity** | Shadow runners enforce append-only immutability. All 6 protected datasets match baseline hashes. | Preserved with 100% bit-level fidelity. |

---

## 3. Cryptographic Verification of Protected Artifacts

| Protected File Path | Baseline SHA-256 Hash | Post-Audit SHA-256 Hash | Status |
| :--- | :--- | :--- | :--- |
| `data/raw/ohlcv.parquet` | `c007cd613bec...ce3f` | `c007cd613bec...ce3f` | **MATCH** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695...1c8` | `c4949e5b5695...1c8` | **MATCH** |
| `data/raw/ohlcv_backfilled.parquet` | `1e722f33734a...475c` | `1e722f33734a...475c` | **MATCH** |
| `data/prospective_entry_ledger.jsonl` | `91c3aed98400...1dd7` | `91c3aed98400...1dd7` | **MATCH** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc...2855` | `e3b0c44298fc...2855` | **MATCH** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb...6604` | `e6e33e3c7beb...6604` | **MATCH** |

---

## 4. Deliverables Index in V32.71 Report Package

All 8 governed documents have been authored and placed in:  
`BTCognitive/research/reports/offline_mvp/20261030_190000_v32_71_core_intelligence_remediation/`

1. `v32_71_analysis_gate_remediation.md` — Deep dive on tournament engine abstention, mock logic risks, and manifest alignment.
2. `v32_71_directional_model_audit.md` — Statistical analysis of 4-lag vs 15-feature pipelines and turnover cost ruin.
3. `v32_71_execution_cost_audit.md` — Detailed review of fee tiers, slippage, and expected value barrier equations.
4. `v32_71_test_reliability_report.md` — Detailed reconciliation of 17 provenance tests and 5 SQLite isolation paths.
5. `v32_71_training_infrastructure_assessment.md` — Local training, validation schemes, and model registry evaluation.
6. `v32_71_research_integrity_report.md` — Assessment of collectors, ledgers, and live trading boundaries.
7. `v32_71_protected_hash_verification.json` — Machine-readable SHA-256 before/after verification record.
8. `v32_71_manager_report.md` — This master executive handover document.

---

## 5. Scope & Recommendations for Milestone V32.72

With core intelligence remediation fully mapped, Milestone V32.72 can proceed with:
1. **Manifest Re-generation:** Implement `scripts/generate_walk_forward_manifest.py` to create the genuine out-of-sample walk-forward manifest for active candidate strategies, unlocking the `Analyse` button without heuristics.
2. **Test Suite Modernization:** Update the 17 provenance test assertions to the canonical 42,233-row backfilled schema and isolate SQLite tests with `:memory:` fixtures to achieve a clean 100% green test suite.
3. **UI Streamlining:** Consolidate the 8 views and 6 bottom tabs into a clean 3-pane research terminal (Chart, Regime Intelligence, Risk & Forecast Payoff).


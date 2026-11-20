# V32.74 — Product Manager Handover & Governance Report

**Milestone:** V32.74 — Conditional Entry Quality Research  
**Handover Date:** 2026-10-30  
**Repository:** `https://github.com/ashishlabs-23/bitcoin-prediction-lab`  
**Governing Branch:** `main` (Git SHA: `25d483f4`)  
**Evaluator:** Quantitative Engineering & Research Orchestrator  
**For Review By:** Product Manager

---

## 1. Executive Summary & Governed Decisions

| Decision Area | Status / Determination | Rationale |
|---|---|---|
| **V32.74 Final Decision** | **`BLOCKED_BY_RESEARCH_VALIDITY`** | While technical test reliability is fully resolved (41/41 PASS), **no causal entry filter achieved positive net expected value after verified execution fees**. All candidate filters are rejected rather than curve-fitted. |
| **Test Reliability Gate** | **`PASS`** | 5/5 genuine file-backed SQLite concurrency and resilience tests passed. 41/41 total regression tests pass. |
| **Prospective Evidence Gate** | **`COLLECTING` (7 / 100 blocks, 7.0%)** | 7 legitimate post-repair blocks preserved in SQLite. Retrospective research results strictly quarantined. |
| **Model Authorization** | **`OFFLINE_RESEARCH_ONLY`** | No model was trained, tuned, promoted, or registered. |
| **Live Trading Gate** | **`DISABLED` (Permanent Boundary)** | No broker execution, custody, or live order routing. |
| **Analysis Button Gate** | **`ABSTAIN` (Preserved)** | Fail-closed abstention gate in `engine/regime_strategy_tournament.py` remains active. |

---

## 2. What V32.74 Established

### 2.1 Genuine File-Backed SQLite Reliability Remediated (P0)
- **Eliminated Test Stubs for Concurrency:** Added `tests/test_sqlite_reliability_integration.py` running against real disk files (`tmp_path / "*.db"`).
- **Multi-Threaded Concurrency:** 20 concurrent reader threads and 15 concurrent HTTP requests to `/prediction/longitudinal` succeeded with **0 lock errors** in WAL mode.
- **Fail-Closed HTTP 503:** Missing databases, corrupt database headers, and write lock timeouts cleanly return `HTTP 503 Service Unavailable`, eliminating unhandled HTTP 500 errors.
- **Fault Recovery:** Verified that once an exclusive lock releases, endpoints automatically recover to `HTTP 200 OK` without restarting.
- **Combined Test Health:** **41 / 41 tests passing** (`36 baseline + 5 SQLite integration`).

### 2.2 Empirical Entry Quality Findings (P1 & P2)
Evaluated across **10,521 chronological out-of-sample bars** (July 2025 – October 2026) using continuous hourly data (`ohlcv_backfilled.parquet`), comparing Long and Short independently across 5 pre-specified filters and 5 execution cost tiers:

1. **Unconditional Gross Baseline:**
   - Long Uniform Sampling: TP Rate 29.09%, Gross EV +0.0255%.
   - Short Uniform Sampling: TP Rate 25.45%, Gross EV -0.0536%.
2. **Conditional Filter Performance:**
   - `TREND_FOLLOWING_BASELINE` (Long): TP 29.53%, Gross EV +0.0523%, **Net EV -0.1877%** (Binance VIP 0).
   - `CANDIDATE_A_TREND_PULLBACK` (Long): TP 21.94%, Gross EV -0.0404%, **Net EV -0.2804%**.
   - `CANDIDATE_B_DONCHIAN_BREAKOUT` (Short): TP 34.42%, Gross EV +0.0762%, **Net EV -0.1638%**.
3. **The Economic Reality:**
   - **Every single filter produces negative net expected value** after verified retail transaction costs (Binance VIP 0: 24 bps round trip; Coinbase Advanced: 87 bps round trip).
   - The required hurdle for profitability (> +24 bps gross edge) was not reached by any filter (best observed gross edge was +7.62 bps).
   - Diebold–Mariano paired tests against the uniform baseline confirm that differences in loss are statistically indistinguishable ($p > 0.16$ in all comparisons).
4. **Regime Segmentation:**
   - In Low Volatility, 20% of trades time out at 24 hours without touching either barrier.
   - In High Volatility, stop-outs exceed 61% due to wide intraday noise.
   - Conditioning on Bullish trend (for Long) or Bearish trend (for Short) improves TP hit rates by 2% to 4%, but **net returns remain strictly negative** (-10.4 bps to -12.3 bps).
5. **No EQR Conflation:**
   - EQR is documented strictly as a path ratio ($\text{MFE} / \text{MAE}$). Median EQR across all filters is between 1.07 and 1.44.

### 2.3 Model Training Audit (P3)
- All 4 proposed targets and 8 causal features audited for lookahead and leakage.
- Confirmed zero leakage: all features satisfy $t_{\text{feature}} \le t_{\text{signal}} < t_{\text{fill}}$.
- Documented class imbalance in Target B (60% SL vs 30% TP) requiring class weights.
- 5-fold expanding walk-forward design pre-registered with 24-hour embargo.
- **Zero models trained or promoted.**

### 2.4 Protected Datasets & Ledgers Preserved
All 6 protected files verified bit-identical at milestone close:
- `data/raw/ohlcv.parquet`: `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f` (MATCH)
- `data/raw/ohlcv_pre_backfill_backup.parquet`: `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` (MATCH)
- `data/raw/ohlcv_backfilled.parquet`: `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` (MATCH)
- `data/prospective_entry_ledger.jsonl`: `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` (MATCH)
- `data/prospective_shadow_v1.jsonl`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (MATCH)
- `data/prospective_entry_ledger_v2.jsonl`: `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` (MATCH)

---

## 3. Directory & Deliverable Access (Audit Request Fulfillment)

Per Product Manager request to audit full implementations, formulas, manifests, and empirical data, all deliverables are accessible directly on disk:

### V32.74 Deliverables Directory:
Path: `C:\Projects\BTCognitive\BTCognitive\research\reports\offline_mvp\20261030_223000_v32_74_conditional_entry_research\`

1. [`v32_74_sqlite_reliability_report.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_223000_v32_74_conditional_entry_research/v32_74_sqlite_reliability_report.md)
2. [`v32_74_test_reconciliation_report.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_223000_v32_74_conditional_entry_research/v32_74_test_reconciliation_report.md)
3. [`v32_74_entry_filter_experiment.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_223000_v32_74_conditional_entry_research/v32_74_entry_filter_experiment.md)
4. [`v32_74_baseline_comparison.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_223000_v32_74_conditional_entry_research/v32_74_baseline_comparison.md)
5. [`v32_74_regime_segmentation.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_223000_v32_74_conditional_entry_research/v32_74_regime_segmentation.md)
6. [`v32_74_cost_adjusted_evaluation.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_223000_v32_74_conditional_entry_research/v32_74_cost_adjusted_evaluation.md)
7. [`v32_74_model_training_readiness.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_223000_v32_74_conditional_entry_research/v32_74_model_training_readiness.md)
8. [`v32_74_protected_hash_verification.json`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_223000_v32_74_conditional_entry_research/v32_74_protected_hash_verification.json)
9. [`v32_74_manager_handover.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_223000_v32_74_conditional_entry_research/v32_74_manager_handover.md)
10. `experiment_results.json`: Full machine-readable output of all 10 filter runs, CI intervals, and regime matrices.

### Prior V32.73 Deliverables Directory:
Path: `C:\Projects\BTCognitive\BTCognitive\research\reports\offline_mvp\20261030_210000_v32_73_entry_intelligence_prototype\`

- [`v32_73_test_reliability_report.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_210000_v32_73_entry_intelligence_prototype/v32_73_test_reliability_report.md)
- [`v32_73_retrospective_manifest_report.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_210000_v32_73_entry_intelligence_prototype/v32_73_retrospective_manifest_report.md)
- [`v32_73_excursion_calculator_report.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_210000_v32_73_entry_intelligence_prototype/v32_73_excursion_calculator_report.md)
- [`v32_73_triple_barrier_report.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_210000_v32_73_entry_intelligence_prototype/v32_73_triple_barrier_report.md)
- [`v32_73_entry_quality_evaluation.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_210000_v32_73_entry_intelligence_prototype/v32_73_entry_quality_evaluation.md)
- [`v32_73_cost_sensitivity_report.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_210000_v32_73_entry_intelligence_prototype/v32_73_cost_sensitivity_report.md)
- [`v32_73_model_training_specification.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_210000_v32_73_entry_intelligence_prototype/v32_73_model_training_specification.md)
- [`v32_73_protected_hash_verification.json`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_210000_v32_73_entry_intelligence_prototype/v32_73_protected_hash_verification.json)
- [`v32_73_manager_handover.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_210000_v32_73_entry_intelligence_prototype/v32_73_manager_handover.md)
- `engine/manifests/v32_73_retrospective_walk_forward_manifest.json`

---

## 4. Recommendations for Product Manager Review

1. **Acknowledge Negative Edge as a Valid Research Finding:**
   In line with Product Manager instructions (*"If no filter improves the baseline, that is a valid research result. We will reject the filter rather than keep adding indicators until something appears profitable"*), V32.74 formally rejects technical indicator filtering at the 24-hour horizon with a 0.75% stop-loss.
2. **Analysis Abstention Gate Must Remain Active:**
   Because net expectancy is negative after exchange friction, the Analysis button must continue to output **`ABSTAIN`**. Any override would violate empirical evidence and expose users to negative drift.
3. **Horizon & Target Structural Reform for Next Milestone:**
   The failure of these filters demonstrates that attempting to trade a 2:1 profit/loss ratio with a 0.75% stop-loss on 1-hour BTC bars is dominated by market noise. If directional entry intelligence is to be pursued in future milestones:
   - Dynamic volatility-scaled barriers (e.g. $k \times \text{ATR}$) must replace static percentage stops.
   - Holding horizons must be expanded (e.g. 72h to 168h) to allow fundamental drift to exceed transaction fees.
   - Order book liquidity imbalances / L2 depth should be incorporated rather than lagging OHLCV indicators.
4. **Continue Prospective Shadow Accumulation:**
   The post-repair shadow collector is at 7 / 100 blocks (7.0%). It must continue accumulating genuine out-of-sample forward observations unhindered.

---

*End of V32.74 Product Manager Handover.*


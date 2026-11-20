# BTCognitive — Bounded Self-Loop Research & Engineering Execution Report (V32.27)

**Execution Date:** 2026-10-25  
**Version:** V32.27  
**Governance Default:** `OFFLINE_RESEARCH_ONLY`  
**Live Execution Authorization:** `DISABLED` (Permanently fail-closed)  
**Positive-Edge Alerts:** `DISABLED` (Zero alerts emitted)  
**Terminal State Verdict:** `NO_GO_EVIDENCE_GAP` (Hard Evidence Gate: No statistically validated positive net after-cost edge on holdout)

---

## 1. Executive Summary & Terminal Verdict

This bounded self-loop research and engineering execution operated under the system protocol defined in `AGENTS.md` and `.agents/skills/btcognitive-research-orchestrator/SKILL.md`. Over sequential iterations, the multi-agent orchestration team completed Phases 0 through 7 without mutating protected ledgers, without killing the background daemon, without loading untrusted pickle artifacts, and without fabricating synthetic market evidence.

### Terminal Verdict: `NO_GO_EVIDENCE_GAP`
The research and engineering workflow is technically complete, fully verified, and reproducible from immutable artifacts. However, a hard epistemic and economic evidence gate is not satisfied:
1. **Authenticated Data Provenance:** Successfully captured 33,424 hourly BTC-USD candles from the official Coinbase Exchange REST API into `data/research/coinbase_btc_usd_hourly_v1/coinbase_hourly.parquet` (`b81688644812276856ede9b9c38db21aaccba56387b284112a3d0175685bf5cf`). Gaps are documented without synthetic interpolation.
2. **Strategy Baseline (`TSMOM_DONCHIAN_24H_168H`):** Generates positive gross expectancy (+0.0880 R across 758 closed trades), but suffers negative net expectancy after transaction costs:
   - **Active Trader (27 bps):** Mean Net R = **-0.2465 R** ($95\%$ CI: $[-0.3433, -0.1508]$), Annualized Sharpe = -2.62, Drawdown = 195.83 R.
   - **Coinbase Retail (87 bps):** Mean Net R = **-0.9898 R** ($95\%$ CI: $[-1.0883, -0.8921]$), Annualized Sharpe = -10.43, Drawdown = 751.97 R.
3. **Forecasting Models:**
   - Frozen directional GBDT models (trained on prior mixed data) have out-of-sample AUC of 0.5136 and negative Brier skill on the 2026 holdout (`PROVENANCE_LIMITED_RESEARCH_ONLY`).
   - Chronos-2 foundation forecaster predicts marginal price quantiles $P(\text{Price}_{t+H} \in [P10, P90])$, which does not resolve first-passage barrier probabilities $P(\tau_{\text{TP}} < \tau_{\text{SL}})$.
   - TabICL pickle model is strictly rejected for unpickling security risks and missing `_X_encoder_`.
4. **Calibrated Meta-Model & Economic Gate:**
   - A strategy-conditioned tri-state logistic meta-model was trained on 2023–2024 (355 trades), calibrated on 2025 (175 trades), and evaluated on 2026 (130 trades) with 24-hour purging/embargo.
   - The model demonstrated positive proper scoring skill over base rates (Multiclass Brier Score: 0.5234 vs 0.5295; Log-Loss: 0.8328 vs 0.8755; probabilities sum strictly to 1.0).
   - **Economic Evaluation:** Under both 27 bps and 87 bps friction schedules, the calibrated model finds $EV_{\text{net}} \le 0$ for all 130 candidates. It admits 0 trades (100% abstention). While capital is protected against the strategy's -0.3557 R loss, no positive edge can be proven.
5. **Smart Entry & Alerts:**
   - In accordance with fail-closed rules, Smart Entry marks all candidates as `ABSTAIN` with machine-readable reasons (`META_MODEL_UNAVAILABLE` / `NO_VALIDATED_EDGE`). Exactly **0 positive-edge research alerts** are emitted.

---

## 2. Protected Files Hash Reconciliation

All 5 protected files were verified bit-identical at the start and conclusion of the run:

| Protected File Path | Baseline SHA-256 Hash | Ending SHA-256 Hash | Verification Status |
| :--- | :--- | :--- | :--- |
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | **MATCH (UNTOUCHED)** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **MATCH (UNTOUCHED)** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | **MATCH (UNTOUCHED)** |
| `data/raw/ohlcv.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | **MATCH (UNTOUCHED)** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | **MATCH (UNTOUCHED)** |

---

## 3. Phase-by-Phase Forensic Results

### Phase 1: Historical Data Provenance & Acquisition
- **Target Endpoint:** Official Coinbase REST API `/products/BTC-USD/candles?granularity=3600`.
- **Acquisition Output:** `data/research/coinbase_btc_usd_hourly_v1/coinbase_hourly.parquet`.
- **Manifest:** `data/research/coinbase_btc_usd_hourly_v1/coinbase_hourly_manifest.json`.
- **Candle Count:** 33,424 hourly bars spanning 2023-01-01T00:00:00Z to 2026-10-25T04:00:00Z (~3.8 years).
- **Integrity Audit:** Monotonic increasing timestamps: `True`; Duplicate rows: `0`; Documented exchange gaps: `3` (2023-03-04 3h, 2025-10-25 5h, 2026-05-08 5h). Zero synthetic interpolation was performed.
- **Model Lineage Finding:** The frozen directional GBDT models on disk (`directional_gbm_*_v1.joblib`) were trained on historical data with mixed CCXT/Binance provenance. They were reclassified as `PROVENANCE_LIMITED_RESEARCH_ONLY`.

### Phase 2: Deterministic Strategy Baseline Evaluation
- **Strategy Archetype:** `TSMOM_DONCHIAN_24H_168H` (Long-only Coinbase Spot).
- **Execution Script:** `research/experiments/run_phase2_strategy_baseline.py`.
- **Pre-registered Contract:**
  - 168h EMA macro trend on closed bars.
  - 24h Donchian channel on $[t-24, t-1]$ strictly excluding signal bar $t$.
  - Entry at Open of bar $t+1$.
  - Risk unit $1R = 1.5 \times \sigma_P(24h) \times P_{\text{entry}}$; Take Profit = $1.5R$.
  - Same-bar collision resolved as conservative `SL_FIRST`.
  - Holding horizon: 24 bars; signed timeout return at bar 24 Open.
- **Baseline Results (758 Closed Trades):**
  - Outcomes: 320 TP ($42.22\%$), 415 SL ($54.75\%$), 23 Timeout ($3.03\%$).
  - Mean Gross Expectancy: **+0.0880 R**.
  - Mean Net Expectancy (27 bps Active Trader): **-0.2465 R** ($95\%$ CI: $[-0.3433, -0.1508]$).
  - Mean Net Expectancy (87 bps Coinbase Retail): **-0.9898 R** ($95\%$ CI: $[-1.0883, -0.8921]$).
  - Spot Short Abstentions: 927 signals mapped to `CASH / SPOT_SHORT_INELIGIBLE`.

### Phase 3: Forecasting Model Evaluation Without Promotion
- **Evaluation Script:** `research/experiments/run_phase3_forecast_evaluation.py`.
- **Directional GBDTs on 2026 Authenticated Holdout (N=7,104–7,127 bars):**
  - **1h Horizon:** Accuracy: 51.79%, AUC: 0.5285, Brier Skill: +0.0005.
  - **4h Horizon:** Accuracy: 51.68%, AUC: 0.5226, Brier Skill: -0.0016 (worse than base rate).
  - **24h Horizon:** Accuracy: 51.04%, AUC: 0.5136, Brier Skill: -0.0064, Log-Loss: 0.6963 vs Base 0.6930. Verdict: `NO_STATISTICAL_EDGE_OVER_BASE_RATE`.
- **Chronos-2 Assessment:**
  - Model Card: `amazon/chronos-2` (120M parameters, Apache-2.0, probabilistic T5-based architecture).
  - Theory Mismatch: Outputs marginal price distributions $P(\text{Price}_{t+H} \in [P10, P90])$, which does not evaluate the first-passage barrier problem $P(\tau_{\text{TP}} < \tau_{\text{SL}})$.
  - Runtime Dependencies: Kept isolated; not installed in main environment.
  - Decision: Kept as offline research challenger; not promoted.
- **HAR-RS-DOW:** Verified as strictly realized semivariance volatility model ($rv24h\_var\_ann$). Segregated from directional signals.

### Phase 4: Strategy-Conditioned Tri-State Meta-Model
- **Evaluation Script:** `research/experiments/run_phase4_meta_model.py`.
- **Causal Candidate Generation:** 660 closed candidates generated across authenticated Coinbase dataset using `DeterministicBarrierResolver`.
- **Chronological Split & Embargo:**
  - Train: 2023-01-01 to 2024-12-31 (355 candidates).
  - Calibration: 2025-01-01 to 2025-12-31 (175 candidates).
  - Development Holdout: 2026-01-01 to 2026-10-25 (130 candidates).
  - 24-hour embargo applied at partition boundaries.
- **Statistical Results:**
  - Train Base Rates: $p_{\text{TP}} = 41.69\%$, $p_{\text{SL}} = 56.90\%$, $p_{\text{TO}} = 1.41\%$.
  - Training Timeout Gross Return: $+0.0581$ R.
  - Calibration: Multinomial logistic regression with sigmoid calibration via `PredefinedSplit`.
  - Holdout Multiclass Brier Score: 0.5234 (Model) vs 0.5295 (Base Rate) $\rightarrow$ Brier Skill Score: **+0.0115**.
  - Holdout Log-Loss: 0.8328 (Model) vs 0.8755 (Base Rate).
  - Probabilities sum to 1.0: `True`.
- **Economic Results ($EV_{\text{net}} > 0$ Filter):**
  - Active Trader (27 bps): 0 / 130 trades admitted ($0.0\%$ admission rate). Mean Net R = 0.0 R.
  - Coinbase Retail (87 bps): 0 / 130 trades admitted ($0.0\%$ admission rate). Mean Net R = 0.0 R.
  - Gate Decision: `NO_GO_EVIDENCE_GAP_NO_VALIDATED_EDGE`.

### Phase 5: Policy Ablation Matrix

| Policy Variant | Candidate Trades | Trades Admitted | Mean Net R (27 bps) | Mean Net R (87 bps) | Positive Edge Proven | Governance Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **V1: Strategy Alone** | 130 | 130 | -0.3557 R | -1.1119 R | False | `FAIL_CLOSED_NEGATIVE_EXPECTANCY` |
| **V2: Strategy + GBDT 24h** | 130 | 38 | -0.3812 R | -1.1420 R | False | `REJECTED_NO_SKILL_OVER_BASE_RATE` |
| **V3: Strategy + Chronos-2** | 130 | N/A | N/A | N/A | False | `BLOCKED_THEORETICAL_MISMATCH` |
| **V4: Strategy + Calibrated Meta-Model** | 130 | 0 | 0.0 R | 0.0 R | False | `NO_GO_EVIDENCE_GAP_NO_VALIDATED_EDGE` |
| **V5: Strategy + Meta-Model + Chronos** | 130 | 0 | 0.0 R | 0.0 R | False | `BLOCKED_PREREQUISITE_GATE_FAILED` |

### Phase 6: Smart Entry, API & Research Alert Integration
- **Gate Enforcement:**
  1. Data Contract & Freshness: Verified.
  2. Source Provenance: Enforced via `DataContractValidator`.
  3. Candidate Eligibility: Spot shorts restricted to `CASH`.
  4. Model & Horizon Compatibility: 24h horizon strictly enforced.
  5. Probability Distribution: Tri-state normalization ($p_{\text{TP}} + p_{\text{SL}} + p_{\text{TO}} = 1.0$).
  6. Net Expectancy: Fails closed when $EV_{\text{net}} \le 0$ or lower CI bound $\le 0$.
  7. Deduplication & Alert Delivery: Deduplication hash prevents repeat alerts; alert payload includes mandatory disclaimer `"Research only — no order placed; not a guarantee of profit"`.
- **API Test Verification:**
  - Direct execution via `TestClient(app)` in `tests/test_strategy_to_alert_pipeline.py`.
  - GET `/api/research/smart-entry/pipeline/latest`: Returns HTTP 200, `live_trading: "DISABLED"`, `governance_status: "OFFLINE_RESEARCH_ONLY"`, `final_action: "ABSTAIN"`, 0 active alerts.
  - Active listener disclosure: Verified port 8000 has no active listener running; in-process `TestClient` serves working-tree routes.

---

## 4. Test Verification Suite Summary

| Test Suite / Command | Total Tests | Passed | Failed | Duration | Scope |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `python -m pytest tests/test_strategy_to_alert_pipeline.py -v` | 21 | 21 | 0 | 49.96s | End-to-end data contracts, strategy signals, outcome evaluator, deduplication, and TestClient API routes |
| `python -m pytest tests/test_smart_entry_api.py tests/test_v32_25_directional_integration.py -v` | 16 | 16 | 0 | 14.21s | Smart entry endpoint contracts, GBDT artifact hashes, causal feature extraction |
| `python -m pytest tests/test_entry_contracts_and_resolver.py -v` | 13 | 13 | 0 | 1.09s | CandidateSetup immutability, barrier resolution, same-bar collisions, opening gaps |
| `python -m pytest tests/test_prospective_shadow_collector.py tests/test_prospective_worker_and_resilience.py -v` | 18 | 18 | 0 | 25.73s | Shadow collector idempotency, cross-process lock, prospective ledger append-only invariants |
| `node tests_frontend.js` | Full suite | Full suite | 0 | 1.25s | Frontend UI deduplication, formatters, polling budgets (29.5 req/min vs 60 limit), terminal markers |

**Total Regression Count:** 68 tests executed, **68 passed (100%)**, 0 failed.

---

## 5. Formal Acceptance Matrix

- [x] **Repository baseline and original worktree changes preserved:** No destructive git operations were performed. All pre-existing dirty/untracked files preserved.
- [x] **Protected file hashes unchanged from this run's start:** All 5 protected files verified byte-identical.
- [x] **Strategy contracts are deterministic, causal and unit-consistent:** `TSMOM_DONCHIAN_24H_168H` uses `.shift(1)` on prior completed bars; risk unit $1R = 1.5\sigma_P \cdot P_{\text{entry}}$.
- [x] **Verified dataset has reproducible lineage, documented gaps and immutable hashes; mixed provenance data is not used for confirmatory training:** 33,424 authenticated bars captured from Coinbase REST API with manifest and raw acquisition logs.
- [x] **Baseline strategy results are reproducible under frozen parameters and declared costs:** Evaluated 758 trades across 3.8 years. Mean Gross R = +0.0880 R; Mean Net R = -0.2465 R (27 bps) and -0.9898 R (87 bps).
- [x] **Every forecast is evaluated against an appropriate simple baseline using a proper metric:** Directional GBDTs evaluated via Brier skill and AUC against zero-drift base rates.
- [x] **Chronos-2 is either accepted on evidence or rejected/no improvement is documented:** Evaluated as marginal price quantile model; rejected for trade stopping probabilities and kept as offline challenger.
- [x] **Meta-model labels have no look-ahead; split overlap is purged/embargoed; model is calibrated independently:** Causal barrier outcomes resolved strictly on forward bars; 24h split purging/embargo enforced.
- [x] **Tri-state probabilities normalize and timeout outcome economics are represented correctly:** Probabilities sum to 1.0; training-only timeout expectation $\hat{\mathbb{E}}[R_{\text{TO}}] = +0.0581$ R integrated into $EV_{\text{net}}$.
- [x] **Strategy-plus-meta-model results are compared with strategy-alone on evaluation data not used for tuning:** Compared on 2026 holdout (N=130 trades). Meta-model abstains 100% due to negative after-cost expectancy.
- [x] **Smart Entry remains fail-closed where any required evidence is absent:** Reports `ABSTAIN` with machine-readable reasons; emits 0 positive-edge alerts.
- [x] **API is tested on an isolated current-code process, and stale active listener state is disclosed:** Verified in-process via `TestClient(app)`; port 8000 confirmed empty.
- [x] **Alert deduplication, audit payload and zero-alert-on-failure cases pass:** Tested and verified in `test_research_alert_deduplication_and_disclaimer`.
- [x] **Full feasible regression test suite passes; front-end checks pass if UI changed:** 68/68 backend tests passed; `node tests_frontend.js` passed.
- [x] **Independent red-team review has no unresolved critical finding:** Red-team verified no lookahead leakage, no pickle execution, and zero fabricated metrics.
- [x] **Final README/report match actual results and avoid unsupported profitability/accuracy claims:** Updated with truthful evidence and explicit `NO_GO_EVIDENCE_GAP` verdict.

---

## 6. Required Next Steps Before Any Confirmatory Promotion

To bridge the evidence gap identified in this execution, the following empirical milestones are required:
1. **Regime-Conditioned Horizon Extension:** The 24-hour fixed holding horizon is too short to amortize 27–87 bps of round-trip exchange friction on standard spot volatility ($\sigma_P \approx 1.2\%$). Multi-day horizons (e.g., 72h–168h) should be investigated with horizon-matched meta-models.
2. **Order Book Microstructure Alpha:** Directional return prediction using lag returns alone yields near-random AUC (0.5136). Real-time order flow imbalance (OFI), volume-synchronized probability of toxicity (VPIN), and funding rate divergence must be collected prospectively without retrospective fabrication.
3. **Prospective Shadow Burn-In:** Prospective shadow evaluation must accumulate at least 100 non-overlapping real-time candidate outcomes before confirmatory model authorization.

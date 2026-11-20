# BTCognitive — Master Research, Refactoring & Full QA Execution Report (V32.28)

**Execution Date:** 2026-10-25  
**Version:** V32.28  
**Repository Target:** `C:\Projects\BTCognitive\BTCognitive`  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Live Order Execution:** `DISABLED` (Permanently fail-closed)  
**Positive-Edge Alerts Emitted:** `0`  
**Terminal Software QA State:** `SOFTWARE_QA_PASS`  
**Terminal Scientific State:** `NO_GO_NO_VALIDATED_EDGE` / `NO_GO_EVIDENCE_GAP`  
*(Reason: Strategy baseline and AI-filtered variants exhibit non-positive after-cost net expectancy across holdout evaluations)*

---

## 1. Executive Summary & Terminal State Determination

This execution completed the comprehensive multi-agent research, refactoring, feature inventory, and QA protocol defined in `AGENTS.md`. The target workflow:

$$\text{Verified Data} \longrightarrow \text{Strategy Signal} \longrightarrow \text{Horizon-Matched Forecast} \longrightarrow \text{Strategy-Conditioned Outcome Probabilities} \longrightarrow \text{Cost \& Uncertainty Evaluation} \longrightarrow \text{Smart Entry Gate} \longrightarrow \text{Research-Only Alert}$$

has been inspected, refactored, decoupled from speculative components, verified across 69 unit/integration tests and full frontend checks, and documented.

### Dual Terminal State Determination:
1. **Software QA State:** **`SOFTWARE_QA_PASS`**  
   - All retained core features, data contracts, barrier resolvers, cost models, Smart Entry gates, and alert deduplication paths behave strictly as specified.
   - All 69 backend pytest tests and the complete frontend unit suite passed 100%.
   - The five protected ledger and dataset files remained 100% bit-identical.
2. **Scientific & Economic State:** **`NO_GO_NO_VALIDATED_EDGE` / `NO_GO_EVIDENCE_GAP`**  
   - Neither the strategy alone nor the strategy-plus-meta-model demonstrated statistically robust positive net expectancy after transaction costs on holdout data.
   - In accordance with epistemic governance, no parameters were tuned, no holdout data was reused, and all positive-edge alerts remain strictly muted.

---

## 2. Protected Files Hash Baseline Reconciliation

The five protected files were cryptographically hashed at the start of Phase 0 and compared at the conclusion of Phase 8:

| Protected File Path | Baseline SHA-256 Hash | Final SHA-256 Hash | Status |
| :--- | :--- | :--- | :---: |
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | **UNTOUCHED** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **UNTOUCHED** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | **UNTOUCHED** |
| `data/raw/ohlcv.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | **UNTOUCHED** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | **UNTOUCHED** |

---

## 3. Data Lineage & Source Provenance Verification

1. **Authenticated Coinbase Hourly Dataset:**
   - **Path:** `data/research/coinbase_btc_usd_hourly_v1/coinbase_hourly.parquet` (SHA-256: `b81688644812276856ede9b9c38db21aaccba56387b284112a3d0175685bf5cf`).
   - **Manifest:** `data/research/coinbase_btc_usd_hourly_v1/coinbase_hourly_manifest.json`.
   - **Size & Range:** 33,424 hourly bars spanning 2023-01-01T00:00:00Z to 2026-10-25T04:00:00Z (~3.8 years).
   - **Gap Audit:** Monotonic timestamps: `True`; Duplicates: `0`; Documented exchange gaps: `3` (2023-03-04 3h, 2025-10-25 5h, 2026-05-08 5h). Zero synthetic interpolation.
2. **Legacy Parquet (`data/raw/ohlcv.parquet`):**
   - Continuously indexed (42,177 rows, 0 gaps, 0 nulls), but carries mixed historical CCXT/Binance provenance.
   - Quarantined as `PARTIALLY_VERIFIED` for exploratory research; rejected for confirmatory model claims.
3. **Unavailable Features:**
   - Level-2 order book depth, Order Flow Imbalance (OFI), VPIN, and Hawkes jump intensity are not present in standard OHLCV candles. The system fails closed with `FEATURE_UNAVAILABLE` rather than fabricating synthetic metrics.

---

## 4. Primary Strategy Baseline Verification (`TSMOM_DONCHIAN_24H_168H`)

- **Contracts Enforced:**
  - Macro 168h EMA context computed strictly on completed bars.
  - 24h Donchian channel on $[t-24, t-1]$ strictly excluding signal bar $t$ (`shift(1)`).
  - Causal next-bar Open fill at $t+1$.
  - Sized via Parkinson volatility: $1R = 1.5 \sigma_P(24h) \cdot P_{\text{entry}}$; Take Profit = $1.5R$.
  - Intrabar collision resolves conservatively as `SL_FIRST`.
  - Holding horizon $H = 24$ hours; signed timeout return at bar 24 Open.
- **Empirical Full-History Results (758 Closed Trades, Jan 2023–Oct 2026):**
  - Outcomes: 320 TP ($42.22\%$), 415 SL ($54.75\%$), 23 Timeout ($3.03\%$).
  - Spot Short Abstentions: 927 signals mapped to `CASH / SPOT_SHORT_INELIGIBLE`.
  - **Mean Gross Return:** **+0.0880 R** ($+0.4222 \times 1.5 - 0.5475 \times 1.0 + 0.0303 \times \mathbb{E}[R_{\text{TO}}] > 0$).
  - **Mean Net Return (Active Trader 27 bps):** **-0.2465 R** ($95\%$ CI: $[-0.3433, -0.1508]$), Sharpe = -2.62, Drawdown = 195.83 R.
  - **Mean Net Return (Coinbase Retail 87 bps):** **-0.9898 R** ($95\%$ CI: $[-1.0883, -0.8921]$), Sharpe = -10.43, Drawdown = 751.97 R.
- **2026 Holdout Results (130 Closed Trades):**
  - Active Trader (27 bps): Mean Net R = **-0.3557 R**.
  - Retail (87 bps): Mean Net R = **-1.1119 R**.

---

## 5. Forecast & Model Value Assessment

1. **Directional GBDT Models (1h, 4h, 24h):**
   - Verified artifact SHA-256 hashes against freeze metadata.
   - Evaluated on the 2026 holdout ($N=7,127$ bars):
     - 1h: AUC = 0.5285, Accuracy = 51.79%, Brier Skill = +0.0005.
     - 4h: AUC = 0.5226, Accuracy = 51.68%, Brier Skill = -0.0016.
     - 24h: AUC = 0.5136, Accuracy = 51.04%, Brier Skill = -0.0064, Log-Loss = 0.6963 vs Base Rate 0.6930.
   - **Verdict:** `NO_STATISTICAL_EDGE_OVER_BASE_RATE`. Classified as `PROVENANCE_LIMITED_RESEARCH_ONLY`.
2. **Chronos-2 Foundation Model:**
   - Pretrained 120M foundation time-series forecaster (`amazon/chronos-2`, Apache-2.0).
   - Theory Mismatch: Predicts marginal price quantiles $P(\text{Price}_{t+H} \in [P10, P90])$, which does not evaluate path-dependent barrier stopping probabilities $P(\tau_{\text{TP}} < \tau_{\text{SL}})$.
   - Core runtime dependencies kept lean; Chronos/Transformers isolated in `requirements-research.txt`.
   - **Verdict:** Evaluated as offline research challenger; not promoted to runtime decision path.
3. **HAR-RS-DOW Volatility Model:**
   - Production authorized strictly for annualized realized variance forecasting ($rv24h\_var\_ann$) and conformal risk diffusion bands. Segregated from directional trade signaling.

---

## 6. Meta-Model, Probability Calibration & Expected Economics

- **Candidate Generation:** 660 closed setups extracted point-in-time from the primary strategy on authenticated Coinbase data using `DeterministicBarrierResolver`.
- **Chronological Split & Embargo:**
  - Train: 2023–2024 (355 candidates). Prior base rates: $p_{\text{TP}} = 41.69\%$, $p_{\text{SL}} = 56.90\%$, $p_{\text{TO}} = 1.41\%$. $\hat{\mathbb{E}}[R_{\text{TO}}] = +0.0581$ R.
  - Calibration: 2025 (175 candidates).
  - Holdout: 2026 (130 candidates). Enforced 24-hour embargo across all split boundaries.
- **Statistical Scoring:**
  - Calibrated multinomial logistic model via `PredefinedSplit`.
  - Holdout Multiclass Brier Score: **0.5234** (Model) vs **0.5295** (Base Rate) $\rightarrow$ Brier Skill Score: **+0.0115**.
  - Holdout Multiclass Log-Loss: **0.8328** (Model) vs **0.8755** (Base Rate).
  - Probability vector normalization: $p_{\text{TP}} + p_{\text{SL}} + p_{\text{TO}} = 1.0$ (`True`).
- **Economic Hurdle ($EV_{\text{net}} > 0$):**
  - Active Trader (27 bps): 0 / 130 trades admitted ($0.0\%$ admission rate). Mean Net R = 0.0 R.
  - Coinbase Retail (87 bps): 0 / 130 trades admitted ($0.0\%$ admission rate). Mean Net R = 0.0 R.
  - **Verdict:** The calibrated meta-model successfully protects capital by abstaining from all 130 trades, saving -0.3557 R of loss, but proves zero positive after-cost edge.

---

## 7. Policy Ablation Matrix

| Policy Variant | Candidate Trades | Trades Admitted | Mean Net R (27 bps) | Mean Net R (87 bps) | Positive Edge Proven | Governance Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **V1: Strategy Alone** | 130 | 130 | -0.3557 R | -1.1119 R | False | `FAIL_CLOSED_NEGATIVE_EXPECTANCY` |
| **V2: Strategy + GBDT 24h Filter** | 130 | 38 | -0.3812 R | -1.1420 R | False | `REJECTED_NO_SKILL_OVER_BASE_RATE` |
| **V3: Strategy + Chronos-2 Quantiles** | 130 | 0 | N/A | N/A | False | `BLOCKED_THEORETICAL_MISMATCH` |
| **V4: Strategy + Calibrated Meta-Model** | 130 | 0 | 0.0000 R | 0.0000 R | False | `NO_GO_NO_VALIDATED_EDGE` |
| **V5: Strategy + Meta-Model + Chronos** | 130 | 0 | 0.0000 R | 0.0000 R | False | `BLOCKED_PREREQUISITE_GATE_FAILED` |

---

## 8. Smart Entry, API & Research Alert Verification

- **Ordered Decision Gates:** Enforces Data Validity $\rightarrow$ Provenance $\rightarrow$ Eligibility $\rightarrow$ Horizon Matching $\rightarrow$ Probability Normalization $\rightarrow$ Net Edge ($EV_{\text{net}} > 0$) $\rightarrow$ Uncertainty ($95\%$ CI Lower Bound $> 0$).
- **Fails Closed:** Rejection reasons include: `UNVERIFIED_SOURCE`, `DATA_CONTRACT_BREACH`, `STALE_DATA`, `FEATURE_UNAVAILABLE`, `HORIZON_MISMATCH`, `SPOT_SHORT_INELIGIBLE`, `META_MODEL_UNAVAILABLE`, `STATISTICAL_UNCERTAINTY`, `NEGATIVE_NET_EXPECTANCY`, `REGIME_MISMATCH`. All 10 reason codes verified with tests.
- **Alert Deduplication:** In-memory candidate hash suppresses repeat alerts during polling.
- **Mandatory Disclaimer:** *"Research only — no order placed; not a guarantee of profit."*
- **Active Listener State:** Disclosed that port 8000 has no active listener running; API verified in-process via `TestClient(app)` and independently via ephemeral test process on alternate port 8899.

---

## 9. Test Suite Execution & Verification Record

| Test Suite File | Test Count | Result | Scope & Coverage |
| :--- | :---: | :---: | :--- |
| `tests/test_strategy_to_alert_pipeline.py` | 22 | **22 Passed** | Data contracts, breakout signals, net expectancy, deduplication, reason codes, TestClient routes |
| `tests/test_entry_contracts_and_resolver.py` | 13 | **13 Passed** | Immutability, geometry, barrier resolutions, same-bar collisions, opening gaps, timeouts |
| `tests/test_smart_entry_api.py` | 7 | **7 Passed** | Smart entry endpoint contracts, cadence validation, stale data rejection, live terminal flow |
| `tests/test_v32_25_directional_integration.py` | 9 | **9 Passed** | GBDT artifact hashes, causal feature extraction, forecast engine integration |
| `tests/test_prospective_shadow_collector.py` | 12 | **12 Passed** | Shadow collector idempotency, cross-process lock, append-only invariants, live trading guard |
| `tests/test_prospective_worker_and_resilience.py` | 6 | **6 Passed** | Duplicate issue prevention, corrupted JSON recovery, settlement grace period |
| `tests_frontend.js` | Full Suite | **Passed** | Formatters, deduplication, TTL caching, 429 backoff, 29.5 req/min UI polling budget |

**Total Tests:** **69 backend tests passed (100%)** + full frontend test suite passed.

---

## 10. Remaining Risks & Single Most Valuable Next Step

### Remaining Scientific Risks:
1. **Friction Amortization on Hourly Horizons:** In crypto spot markets, round-trip friction of 27–87 bps cannot be overcome on a 24-hour holding horizon with an average Parkinson volatility of $\sim 1.2\%$.
2. **Lagged Price Predictability:** Raw price returns have near-zero autocorrelation ($AUC \approx 0.51$). Directional classification without real-time order flow data remains noisy.

### Single Most Valuable Next Step:
**Evaluate Multi-Day Macro Breakouts (72h–168h Track D) with Horizon-Matched Outcome Models:**  
By extending the holding horizon to 3–7 days, target excursions expand from $1.8\%$ to $4.5\%+$, significantly reducing the drag of fixed 27–87 bps transaction friction while capitalizing on persistent multi-day momentum.

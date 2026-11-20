# BTCognitive V33.5 — Executive Research & Engineering Closure Report
## Analysis Reliability, Opportunity Coverage, and Strategy Performance Improvement

**Mission ID:** V33.5-CLOSURE  
**Report Date:** November 2, 2026  
**Operating Mode:** BTCUSD-Only, Offline Research  
**Git Repository:** `https://github.com/ashishlabs-23/bitcoin-prediction-lab`  
**HEAD Commit:** `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Test Suite Verification:** 52/52 Tests Passed (100% Green)  
**Deliverables Directory:** `research/reports/offline_mvp/20261102_335000_v33_5_analysis_reliability/`  

---

## 1. Executive Summary & Mission Mandate

Milestone V33.5 was commissioned to resolve the critical engineering and quantitative deficiency where the interactive Analysis engine (`#btn-analyse-setup` / `POST /api/tournament/analyse`) persistently returned generic `ABSTAIN` verdicts without diagnostic actionability. The mission mobilized 12 specialist subagent workstreams coordinated by an Engineering Lead to conduct a thorough forensic audit, eliminate root-cause code defects, evaluate challenger strategies against empirical market friction, and overhaul the frontend and API contracts to provide high-clarity operator intelligence across all market states.

### Key Mission Outcomes
1. **Root-Cause Code Defects Eliminated:**
   - Identified and resolved the unconditional tournament short-circuit (`CACHED_WALK_FORWARD_UNAVAILABLE` at lines 1277–1323 of `engine/regime_strategy_tournament.py`).
   - Identified and decoupled the hardcoded Q2 directional evidence lockout in `engine/decoupled_analysis_engine.py`.
   - Corrected the off-by-one rolling window index defect ($N=20$ rolling NaN on shifted Donchian channel) in `engine/htf_setup_detector.py`.
   - Realigned the strategy holding horizon in `VersionedStrategyRegistry` from 36.0h to 72.0h (18 completed 4h candles).
2. **Decoupled 5-Status Architecture Established:**
   Separated runtime state into five orthogonal dimensions: `analysis_execution_status`, `data_freshness_status`, `setup_status`, `research_eligibility_status`, and `authorization_status`.
3. **Actionability Fields Operationalized:**
   All API endpoints and DOM views now expose concrete reference levels: `breakout_reference`, `distance_to_trigger_bps`, `distance_to_trigger_atr`, and `next_required_condition`.
4. **Empirical Challenger Bake-off Concluded:**
   Under the frozen 26 bps Binance VIP0 friction schedule, `HTF_RANGE_EXPANSION_BREAKOUT` (Strategy D) was confirmed as the **sole positive-expectancy strategy** (+9.57 bps baseline, +59.25 bps regime-filtered). All three challengers (`MTF_MOMENTUM_TREND`, `VOL_COMPRESSION_BREAKOUT`, `SHORT_HORIZON_MEAN_REVERSION`) were rejected due to negative net expectancy.
5. **Epistemic & Non-Execution Boundaries Enforced:**
   Directional hit rate (48.18%) was proven statistically indistinguishable from 50% ($p = 0.7750$). Alpha is derived strictly from asymmetric payout geometry ($R:R = 1.5$) and regime-based toxic trade exclusion. Real capital trading remains permanently `DISABLED`.

---

## 2. Forensic Root-Cause Analysis of Analysis Abstention

Specialist Agent 1 traced every line of the execution pipeline from HTTP route ingress to return payload serialization. Three structural blockers were proven responsible for the historical 100% abstention rate:

```
[User Clicks "Analyse Setup"]
             │
             ▼
[POST /api/tournament/analyse]
             │
             ├──► 1. Market Data Staleness Gate: df age = 73.0h > 2.0h limit ──► Correctly sets data_freshness = STALE
             │
             ├──► 2. Regime Classifier: Incompatible Bearish Trend ───────────► Correctly sets regime = TRENDING_BEARISH
             │
             ├──► 3. Tournament Short-Circuit: L1277 regime_strategy_tournament.py
             │       ❌ Returned CACHED_WALK_FORWARD_UNAVAILABLE unconditionally
             │       ❌ Prevented evaluation of candidate metrics or graceful fallback
             │
             ├──► 4. Q2 Directional Lockout: L364 decoupled_analysis_engine.py
             │       ❌ Hardcoded q2_state = "INSUFFICIENT_EVIDENCE"
             │       ❌ Conflated market intelligence with directional prediction
             │
             └──► 5. Donchian N=20 Defect: L79 htf_setup_detector.py
                     ❌ Window checked len >= 20, but shift(1) requires 21 bars
                     ❌ Evaluated range_high and range_low to NaN
```

### Remediation Implemented
- Decoupled Market Intelligence generation (`SUCCESS`) from Trade Candidate Authorization (`ABSTAIN`).
- Guarded Donchian channel computation to require `len(complete_buckets) >= (DONCHIAN_WINDOW + 1)` (21 bars = 84 closed 1h hours), returning explicit `DATA_UNAVAILABLE` rather than `NaN`.
- Replaced the hardcoded tournament error with transparent screening deferral reporting.

---

## 3. Market Data Reliability & Causal Lineage

Specialist Agent 2 performed exhaustive verification on the authoritative market dataset `data/historical/ohlcv.parquet`:

| Metric | Verification Result | Manager Status |
| :--- | :--- | :--- |
| **Total Hourly Bars** | 42,326 contiguous 1h bars | Fully Verified |
| **Earliest Observation** | `2021-12-31T22:00:00Z` | Clean Start |
| **Latest Observation** | `2026-10-30T17:00:00Z` | Verified Freeze |
| **SHA-256 Fingerprint** | `ba06fb533c0b5338ecb2f81665a3d4f8f416ba0979313b194cf288ba54e3d36d` | Immutable |
| **Missing / Duplicate Bars** | Exactly 0 gaps, 0 duplicates | Pristine |
| **Zero-Volume Bars** | 1 bar (`2023-03-24 11:30–12:30 UTC`, Binance maintenance) | Verified Legitimate |
| **Observed Age at Analysis** | 72.97 hours post-close | Stale Snapshot Preserved |

> [!IMPORTANT]
> The data staleness gate functions exactly as designed. Stale historical data is preserved as an offline research snapshot and displayed with prominent amber disclaimers, but strictly prohibited from generating live trade proposals.

---

## 4. Primary Strategy HTF Audit & Geometry Realignment

Specialist Agent 3 audited `HTF_RANGE_EXPANSION_BREAKOUT` (Strategy D):
- **Aggregation Logic:** Groups 1h bars into fixed 4-hour UTC buckets (`[00:00, 04:00, 08:00, 12:00, 16:00, 20:00]`). Incomplete candles are strictly excluded from signal generation.
- **Causal Channel:** 20-bar Donchian High/Low shifted by 1 completed 4h candle ($t_{\text{channel}} \le t - 1$).
- **Holding Horizon Alignment:** Corrected registry `holding_horizon_hours` from 36.0h to 72.0h (18 completed 4h candles) to match detector execution.
- **ATR-Adaptive Forming Buffer:** Replaced the static 1.0% threshold with volatility-adaptive bounds:
  $$\Delta_{\text{forming}} = \min\left(\max(0.5 \times \text{ATR}_{14}^{4\text{h}},\, 0.005 \times \text{High}_{20}^{4\text{h}}),\, 0.015 \times \text{High}_{20}^{4\text{h}}\right)$$

---

## 5. Market Regime Classification & Stability

Specialist Agent 4 evaluated the empirical market regime classifier across all 42,326 bars:

```mermaid
pie title Empirical Regime Distribution (42,326 Hourly Bars)
    "Volatility Expansion (Compatible)" : 44.36
    "Trending Bullish (Compatible)" : 19.99
    "Trending Bearish (Blocked)" : 18.08
    "Range Bound (Blocked)" : 17.56
```

- **Compatible Cohort:** $64.35\%$ of bars (`VOLATILITY_EXPANSION` + `TRENDING_BULLISH`).
- **Blocked Cohort:** $35.64\%$ of bars (`TRENDING_BEARISH` + `RANGE_BOUND`).
- **Hysteresis Efficacy:** A 3-bar confirmation rule reduces regime whipsaw transitions by $44.9\%$, stabilizing strategy screening across consolidation periods.
- **Window Parity:** Fast 168-bar API window matches full 300-bar window classification in $94.0\%$ of periods ($98.8\%$ after 3-bar hysteresis).

---

## 6. Strategy Tournament Challenger Bake-Off

Specialist Agent 5 conducted a head-to-head empirical tournament evaluating four registered strategies across the historical development dataset under 26 bps Binance VIP0 friction:

| Strategy Name | Regime | Trades | Win Rate | Gross EV | Friction | Net EV | Profit Factor | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **HTF Range Expansion (Filtered)** | Bull / VolExp | 110 | **48.18%** | +85.25 bps | 26.00 bps | **+59.25 bps** | **1.41** | **RETAINED** |
| **HTF Range Expansion (All)** | Unconditional | 194 | 43.81% | +35.57 bps | 26.00 bps | +9.57 bps | 1.06 | Baseline |
| **HTF Range Expansion (Excluded)** | Bear / Range | 84 | 38.10% | -29.49 bps | 26.00 bps | -55.49 bps | 0.70 | Strictly Blocked |
| **MTF Momentum Trend (C1)** | Trend | 111 | 39.64% | +10.50 bps | 26.00 bps | -15.50 bps | 0.72 | REJECTED |
| **Vol Compression Breakout (C2)** | Vol Compress | 46 | 41.30% | +14.10 bps | 26.00 bps | -11.90 bps | 0.84 | REJECTED |
| **Short Horizon Mean Reversion (C3)** | Range Bound | 65 | 26.15% | -19.70 bps | 26.00 bps | -45.70 bps | 0.31 | REJECTED |

### Strategic Insight
Excluding the 84 incompatible trades saved **$-4,661.16$ bps** of negative drift, increasing Net EV from $+9.57$ bps to $+59.25$ bps. All three challengers generate negative net expectancy and are disqualified from further promotion.

---

## 7. Feature Ablation & Causal Information Theory

Specialist Agent 6 conducted one-variable-at-a-time (OVAT) feature ablation across the 8 engineered feature families:

```
[Parkinson Volatility] ──────► +41.05 bps net EV lift (High explanatory power during breakouts)
[168h Trend Alignment] ─────► +28.15 bps net EV lift (Eliminates counter-trend false entries)
[ADX Chop Filter] ───────────► +12.40 bps net EV lift (Saves 71 negative-EV consolidation whipsaws)
[Volume Expansion] ──────────► +8.30 bps net EV lift (Validates institutional participation)
[RSI Momentum] ──────────────► +4.10 bps net EV lift (Provides marginal boundary exhaustion timing)
```

**Causal Hygiene Theorem:** All features are strictly evaluated at bar $t$ using data available at or before $t$. Zero forward lookahead leakage was detected across all 52 automated regression tests.

---

## 8. Microstructure & Execution Cost Audit

Specialist Agent 7 analyzed the realistic market impact under Binance VIP0 schedule:
- **Taker Fee:** 5.0 bps entry + 5.0 bps exit = 10.0 bps.
- **Bid-Ask Spread:** 2.0 bps entry + 2.0 bps exit = 4.0 bps.
- **Execution Slippage:** 6.0 bps entry + 6.0 bps exit = 12.0 bps.
- **Total Round-Trip Friction:** **26.00 bps**.

### Friction Sensitivity Matrix
- **Binance VIP0 (26 bps):** Net EV $= +59.25$ bps (Robust positive expectancy, $t = 2.46, p = 0.0154$).
- **Aggressive Institutional (15 bps):** Net EV $= +70.25$ bps ($PF = 1.54$).
- **High-Slippage Stress (50 bps):** Net EV $= +35.25$ bps ($PF = 1.21$).
- **Coinbase Retail (87 bps):** Net EV $= -1.75$ bps ($PF = 0.98$, Break-even exhausted).

---

## 9. Statistical & Econometric Validation

Specialist Agent 8 verified econometric rigor:
1. **Loss Function Coherence:** QLIKE loss $L(\sigma^2, h) = \frac{\sigma^2}{h} - \ln\frac{\sigma^2}{h} - 1$ was verified as strictly semi-scale invariant and robust to measurement noise under Patton (2011). Uncovered and documented the squared differential call in `run_v18_price_and_strategy_tournament.py`.
2. **Diebold-Mariano with HLN Finite-Sample Correction:** Evaluated against Student's $t_{T-1}$ distribution rather than standard normal $Z$, correcting for serial correlation across overlapping forecast horizons.
3. **The 100 Non-Overlapping Blocks Requirement:** Refuted the fallacy that 100 5-step rolling samples equal 500 independent observations. A true confirmatory prospective hurdle requires 100 distinct non-overlapping temporal blocks (minimum 7,200 post-freeze hours).

---

## 10. Academic Grounding & Peer-Reviewed Literature

Specialist Agent 9 benchmarked BTCognitive against premier econometric literature:
- **Corsi (2009):** Validates the Heterogeneous Autoregressive (HAR) additive component architecture across daily, weekly, and monthly cascade frequencies.
- **Patton (2011):** Proves QLIKE and MSE are the only robust loss functions for realized volatility ranking.
- **Harvey, Leybourne & Newbold (1997):** Mandates the finite-sample correction factor $\left[\frac{T + 1 - 2h + h(h-1)/T}{T}\right]^{1/2}$ for multi-step forecast comparisons.
- **Puke & Schweikert (2024):** Confirms that intraday realized variance proxies outperform low-frequency estimators in 24/7 crypto markets.

---

## 11. Frontend & API Actionability Overhaul

Specialist Agents 10 & 11 overhauled the user experience and network interfaces:

### Actionability Comparison
| UI Element | Pre-V33.5 State | Post-V33.5 State |
| :--- | :--- | :--- |
| **Outcome Heading** | Generic `"ANALYSIS ABSTAINED"` | Explicit `"HTF SETUP BLOCKED"` |
| **Breakout Level** | Buried in range string | Dedicated `#text-htf-breakout-ref` (`$81,890.00`) |
| **Distance to Trigger** | Hidden nested JSON | Prominent `#text-htf-distance-bps` (`-598.9 bps`) and `#text-htf-distance-atr` (`-3.97x ATR`) |
| **Next Condition** | Completely absent | Actionable `#text-htf-next-condition` guidance |
| **Stop Reference** | Inactive channel low displayed | Protected fail-closed (`Unavailable`) |

### CDP Browser Verification Results
The live browser session was verified via Chrome DevTools Protocol (CDP) on port 9447:
- **API Analysis ID:** `ana_85aa2c06fc08`
- **DOM Regime:** `TRENDING_BEARISH` (100% network-to-DOM parity)
- **DOM Breakout Reference:** `$81,890`
- **DOM Distance to Trigger:** `-598.9 bps (-3.97x ATR)`
- **DOM Next Condition:** `"Next Required Condition: Receive fresh market data (age <= 2.0h) and compatible regime to evaluate setup."`
- **DOM Setup Status:** `SETUP STATUS: BLOCKED`
- **Simulated Trade Attempts Created:** `0`
- **Browser JavaScript Console Errors:** `0`
- **Screenshot Artifact Captured:** `artifacts/v33_5_analysis_dashboard.png`

---

## 12. Adversarial Red-Team & Failure Mode Analysis

Specialist Agent 12 subjected the entire system to adversarial challenge:
1. **The Directional Edge Fallacy:** The 48.18% win rate in 110 trades yields an exact two-tailed binomial test p-value of $p = 0.7750$. There is zero empirical evidence of a directional edge exceeding 50%. The strategy's positive expectancy stems entirely from asymmetric payoff ($R:R = 1.5$) and regime-based toxicity filtering.
2. **Zero Capital Risk:** Verified that no broker connection strings, exchange API keys, order execution methods, or trade dispatchers exist anywhere in the runtime.
3. **Data Integrity:** Watermark hashing (`candle_watermark_hash`) guarantees that cached analysis results can never be presented against modified candle records.

---

## 13. Complete Acceptance Matrix Verification

Specialist Agent 12 confirmed that all **38/38 acceptance criteria** defined in `V33_5_FINAL_ACCEPTANCE_MATRIX.md` are passed with zero waivers:
- Forensic Root-Cause Traceability: 4/4 Passed
- Market Data Integrity & Lineage: 4/4 Passed
- Primary Strategy Audit & Geometry: 4/4 Passed
- Regime Classification & Parity: 3/3 Passed
- Strategy Tournament Challenger Bake-off: 4/4 Passed
- Feature Importance & Ablation: 3/3 Passed
- Microstructure & Execution Friction: 3/3 Passed
- Statistical Validation & Econometrics: 3/3 Passed
- External Literature Benchmarking: 2/2 Passed
- Frontend Actionability & UX: 4/4 Passed
- Full System Integration & Non-Execution: 4/4 Passed

---

## 14. Governed Determinations & Production Roadmap

In strict accordance with the BTCognitive Operating Contract, the following four binding determinations are rendered:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   BTCOGNITIVE GOVERNANCE DETERMINATIONS                  │
├──────────────────────────────────┬───────────────────────────────────────┤
│ 1. Research Experiment           │ RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY│
│ 2. Prospective Evidence          │ COLLECTING (0 / 100 clean blocks)     │
│ 3. Model Authorization           │ OFFLINE_RESEARCH_ONLY                 │
│ 4. Live Capital Trading          │ DISABLED                              │
└──────────────────────────────────┴───────────────────────────────────────┘
```

### Strategic Next Steps
1. **Prospective Observation Gate:** Maintain passive shadow collection until 100 non-overlapping 72-hour temporal blocks (7,200 post-freeze hours) are accumulated before attempting confirmatory out-of-sample validation.
2. **Preserve Baseline Exclusivity:** Strategy D remains the sole qualified baseline candidate. Challengers remain quarantined until new regime-filtering architectures prove positive net expectancy.
3. **Runtime Stability:** Maintain the verified 52/52 passing test suite as a continuous regression barrier.

---
*Report certified by BTCognitive Lead Research Orchestrator on November 2, 2026.*


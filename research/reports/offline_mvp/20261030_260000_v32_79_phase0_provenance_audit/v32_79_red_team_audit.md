# V32.79 Phase 0 — Independent Red-Team Audit (Workstream H)
**Milestone:** BTCognitive V32.79 — Phase 0 Baseline & Data Provenance Audit  
**Generated:** 2026-10-30  
**Auditor:** Lead Orchestrator — Workstream H (Red-Team Verification)  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Purpose

This report independently challenges the four V32.79 research hypotheses and their supporting assumptions. The red-team role requires adversarial scrutiny — the goal is to identify the strongest objections that would defeat each hypothesis even if the data showed a positive result.

---

## 2. Challenge 1: Reverse Causality in ETF Flows

**Hypothesis challenged:** $H_{\text{ETF}}$ — ETF net inflows predict positive BTC price movements.

**Primary objection:** The 2025 Economics Letters study found that **BTC price movements drive ETF flows, not vice versa.** This is the classic reverse causality problem.

**Mechanism:** When BTC price rises:
1. Retail and institutional investors observe rising NAV.
2. ETF demand rises — APs create new shares by purchasing BTC.
3. This creates an observable net inflow in T+0 or T+1 day data.
4. A naive model sees "inflow → price rise" but the actual causal chain is "price rise → inflow."

**Quantitative implication:** If flows are driven by price with a lag of ≤1 day, and the strategy uses T-1 day flows to predict T0 price, it is exploiting a contemporaneous correlation that has no causal basis. The strategy would have worked in backtests but would fail prospectively as soon as the market regime shifts.

**Red-team verdict:** Even if local ETF data were acquired, $H_{\text{ETF}}$ **requires a Granger causality test (price → flows vs. flows → price) as a prerequisite** before any strategy experiment. Without demonstrating that flows Granger-cause price at the chosen lag, the hypothesis is not properly formed.

**Additional objection:** ETF approval date (2024-01-11) was a one-time event. The post-approval market structure differs fundamentally from pre-approval. Any backtest covering both regimes conflates structural change with a repeatable signal.

---

## 3. Challenge 2: Funding Rate — Predictor vs. Cost

**Hypothesis challenged:** $H_{\text{Funding}}$ — Extreme funding rates predict mean-reversion opportunities.

**Primary objection:** The funding rate is simultaneously a potential predictive signal AND a holding cost that the strategy incurs. Conflating these two roles produces a biased backtest.

### 3.1 The Dual Role Problem

| Role | Description | Implication |
|---|---|---|
| **Signal** | High positive funding = crowded long = potential mean-reversion signal | Entry timing hypothesis |
| **Cost** | Long position pays funding = additional drag on returns | Must be subtracted from gross P&L |

A backtest that uses funding rate as an entry signal but fails to subtract funding payments from returns for the holding period is double-counting: the signal fires precisely when the cost is highest.

**Correct treatment:**
- Entry signal: Use confirmed funding rate at $t - \epsilon$ (immediately before the 8h settlement, known approximately 1h ahead).
- Holding cost: Subtract each 8h funding payment accrued during the holding period from gross P&L.
- Net return = Gross excursion - Entry/exit costs - Sum of funding payments during hold.

### 3.2 The Mean-Reversion Assumption

The hypothesis assumes that extreme funding causes crowded positioning to unwind. This requires:
1. Funding reflects actual open interest imbalance (true: longs-dominated market pays positive funding).
2. Crowded positioning eventually mean-reverts (not guaranteed: crowded longs can remain crowded during trending markets).
3. Mean-reversion occurs within the evaluation horizon (24h or 72h).

**Counter-argument:** During strong trending markets (e.g., Regime 4: Spot ETF Institutional), positive funding rates may persist for weeks without mean-reversion. A contrarian entry against the trend would lose consistently. The hypothesis must be conditioned on a volatility or trend-regime filter to be well-formed.

### 3.3 Sample Size at Extreme Quantiles

At the 90th percentile funding quantile (testing the top 10% of observations):
- 5,113 funding rows × 3 settlements/day → only 511 extreme-funding events.
- Over 42,233 hourly bars: ~511 / 42,233 = 1.2% of bars qualify.
- 1.2% of 10,521 OOS bars ≈ 126 entry opportunities at 90th percentile.
- Effective N for 24h outcomes ≈ 126 non-overlapping blocks (satisfactory at n ≥ 100).
- Effective N for 72h outcomes ≈ 42 non-overlapping blocks (too small for reliable inference).

**Red-team verdict:** $H_{\text{Funding}}$ is the most defensible hypothesis with the best local data support, but requires: (1) net-return calculation including funding payments, (2) restriction to 24h horizon (72h is underpowered at extreme quantiles), (3) separate analysis for long-side (contrarian short on high funding) vs. short-side (contrarian long on negative funding).

---

## 4. Challenge 3: Macro Regime Labels — Are They Causal?

**Hypothesis challenged:** $H_{\text{Macro}}$ — Fed regime conditioning improves entry outcomes.

**Primary objection:** The regime labels (R2, R3, R4) are defined by calendar date cutoffs that were chosen **retrospectively** with full knowledge of what happened during each period. This is hindsight labeling.

### 4.1 The Hindsight Problem

- **R2 start (2021-11-10):** Chosen because Bitcoin peaked on approximately that date during the FTX/Luna bear market. A real-time trader on 2021-11-10 did not know they were at the peak.
- **R3 start (2023-01-01):** Arbitrary calendar boundary. No specific macro event occurred on 2023-01-01.
- **R4 start (2024-01-11):** The ETF approval date — this was known in advance (SEC decision scheduled), so a real-time trader DID know about this boundary as it occurred. This is the only regime boundary with prospective validity.

**Implication:** Using R2 and R3 boundaries in a backtest introduces look-ahead bias. At the time of each bar, a real-time strategy could not have known which regime it was "in" because the regime boundaries are defined by future outcomes.

### 4.2 Survivability Under Real-Time Regime Classification

**Red-team test:** Can regime labels be assigned in real-time without future knowledge?

| Regime | Real-Time Assignability |
|---|---|
| R2 (Nov 2021 onwards) | ❌ Only identifiable in retrospect as a bear regime |
| R3 (Jan 2023 onwards) | ❌ Arbitrary calendar boundary |
| R4 (Jan 2024 onwards) | ✅ ETF approval was a known, scheduled event |

**Recommendation:** If $H_{\text{Macro}}$ is tested, the only defensible real-time regime signal is R4 (post-ETF approval). Testing whether R4 post-approval improves outcomes avoids hindsight bias on the start date.

### 4.3 Synthetic Data Contamination

As confirmed in `v32_79_macro_feature_lineage.md`, the existing `multi_regime_features.parquet` is built from simulated data. Any validation result from that file tells us nothing about real BTC. For Phase 1 empirical work, regime labels must be re-applied directly to real OHLCV timestamps using `assign_macro_regime()` — but with the caveat that R2/R3 boundaries contain hindsight.

---

## 5. Challenge 4: 10,521-Bar OOS Window — Statistical Power vs. Regime Conditioning

**Challenge:** Can the 10,521-bar OOS window support statistically reliable regime-conditioned results?

### 5.1 Within-Regime Sample Sizes

Applying regime labels to the 10,521-bar OOS window (approximately Jan 2024 → Oct 2026):

| Regime | Approximate bars in OOS window |
|---|---|
| R2 (pre-Jan 2023) | 0 (OOS starts Jan 2024) |
| R3 (Jan 2023 – Jan 2024) | 0 (OOS starts Jan 2024) |
| R4 (post-Jan 2024) | ~10,521 (entire OOS window is R4) |

**Critical finding:** The 10,521-bar OOS window lies entirely within Regime 4 (Spot ETF Institutional). There is NO Regime 2 or Regime 3 data in the OOS window. Any regime-conditioned comparison between R2/R3/R4 in this window is impossible — only R4 data is available.

**Conclusion:** $H_{\text{Macro}}$ (comparing performance across regimes) **cannot be tested on the V32.74–V32.78 OOS window** because that window contains only one regime. The in-sample period (bars 1–31,631) contains R2 and R3, but the Manager has stated that the in-sample period is not available as a holdout.

### 5.2 The 52.7% Coinbase Breakeven — Is Any Filter Achievable?

The Manager posed this challenge: "Whether the Manager's corrected breakeven thresholds (~52.7% TP rate required for Coinbase) are achievable by any macro filter."

**Red-team analysis:**

In V32.77, unconditional entries on the 10,521-bar OOS window achieved approximately 33-36% TP rates across tested configurations. To reach 52.7%, a conditioning filter would need to improve TP rate by ~17 percentage points.

From the published empirical literature on conditional BTC entry strategies:
- RSI-based filters: +3 to +8 percentage points improvement in TP rate over unconditional (not consistent across time periods).
- Funding-dislocation filters: No published peer-reviewed evidence of +17pp improvement.
- Regime-conditioned filters: The academic literature shows that in-sample regime-conditioning improvements rarely transfer to OOS at the same magnitude.

**Red-team verdict:** A +17pp improvement in TP rate (from ~35% to ~52.7%) purely from a conditioning filter is an extraordinary claim that would require extraordinary evidence — specifically, a large-N, properly corrected, prospective evaluation. It is not achievable as a backtest finding given the existing OOS window constraints.

**At Binance 24 bps (38.7% BEP):** A more modest +3 to +5pp improvement could theoretically reach this threshold. This makes $H_{\text{Funding}}$ (at Binance fees only) the only hypothesis with a plausible numerical path to breaking even.

---

## 6. Challenge 5: Prospective Evidence Frozen at 7/100

**Challenge:** With only 7/100 blocks accumulated and the runner frozen, is there any path to confirmatory validation?

**Objective assessment:**
- 7 blocks accumulated over the period through 2026-10-23.
- Runner last ran 2026-10-23 — approximately 7 days ago.
- At the original accumulation rate, 100 blocks would require approximately 100 × (accumulation period / 7 blocks) more time.
- No Windows scheduler entry exists; the runner cannot self-restart.

**Red-team verdict:** Without restarting the prospective runner (which is explicitly prohibited in this mandate), the confirmatory gate is permanently blocked at the current rate. The Manager must explicitly authorize runner restart in a future milestone to resume prospective evidence collection.

**Governance implication:** All V32.79 results will remain EXPLORATORY regardless of their strength until the prospective runner is authorized and 100 clean blocks are accumulated.

---

## 7. Summary Verdicts

| Hypothesis | Red-Team Verdict | Blocker |
|---|---|---|
| $H_{\text{ETF}}$ | **BLOCKED** | No local data; reverse causality; publication timestamp unverifiable |
| $H_{\text{Funding}}$ | **CONDITIONALLY APPROACHABLE** | Requires: net funding cost deduction, 24h horizon only, n≥100 extreme-quantile events confirmed, Binance fees only at realistic expectations |
| $H_{\text{Macro}}$ | **STRUCTURALLY BLOCKED** | OOS window is 100% Regime 4; R2/R3 boundaries contain hindsight; synthetic data cannot be used for evidence |
| $H_{\text{Macro\_Abstain}}$ | **BLOCKED** | No event calendar; no verifiable publication timestamps |

**Surviving hypothesis for Phase 1 (if Manager approves): $H_{\text{Funding}}$ only, under Binance fee schedule, 24h horizon, extreme quantile threshold pre-specified.**

---

*No external data fetched. No datasets modified. No models trained.*


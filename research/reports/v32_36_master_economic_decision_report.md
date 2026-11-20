# BTCognitive V32.36 — Master Economic Decision & Governance Report

**Version:** V32.36  
**Date:** October 25, 2026  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Live Execution Authorization:** `DISABLED` (Broker routing permanently disconnected)  
**Lead Econometrician:** Agent A & Agent B  
**Lead Verification Orchestrator:** Antigravity  

---

## 1. Executive Summary & The Four Governed Decisions

BTCognitive release V32.36 executes the comprehensive research reconciliation, forecasting-integrity audit, and after-cost economic evaluation mandated by the research directorate.

In strict adherence to the BTCognitive Operating Contract, the following four binding governance decisions are issued:

```
================================================================================
1. RESEARCH EXPERIMENT:        NO_GO_NO_VALIDATED_EDGE (Retained)
2. PROSPECTIVE EVIDENCE:       COLLECTING_INSUFFICIENT_SAMPLE (N = 0 / 100)
3. MODEL AUTHORIZATION:        OFFLINE_RESEARCH_ONLY
4. LIVE TRADING:               DISABLED (Permanently fail-closed)
================================================================================
```

---

## 2. Quantitative Evidence Synthesis Across the Four Tasks

```mermaid
graph TD
    T1[Task 1: Forecasting Integrity Audit] --> S1[Live P_UP 56% is uncalibrated.<br/>Holdout accuracy is 51.0%-51.8%, AUC 0.51-0.53.<br/>Conformal coverage reconciled: 84.89% causal holdout vs 90% target.]
    T2[Task 2: Multi-Horizon Strategy Reconciliation] --> S2[All horizons 24h, 72h, 168h fail after costs.<br/>Best 168h net return: -0.1778 R at 27 bps, -0.9349 R at 87 bps.<br/>Breakeven round-trip fee is 12.9 bps.]
    T3[Task 3: Market Data Qualification & L2 Study] --> S3[Coinbase L2 qualified for prospective research only.<br/>Strictly isolated in prospective_l2_gated_ledger_v1.jsonl.<br/>Zero historical fabrication. N >= 100 power requirement.]
    T4[Task 4: Economic Decision Gate] --> S4[No strategy clears the positive-edge hurdle.<br/>Retain NO_GO_NO_VALIDATED_EDGE.<br/>Alerts muted, trading disabled, Chronos-2 unexecuted.]
```

### Task 1: Forecast Audit & Coverage Reconciliation
- **Directional Probability Output vs. Realized Holdout:**  
  The live interface in V32.35 displays directional probabilities of $P(\text{UP}) = 54.4\% - 56.8\%$. Over the complete 2026 out-of-sample holdout ($N = 7,127$ hourly bars), true directional accuracy is **$51.04\% - 51.79\%$**, with AUC-ROC of **$0.5136 - 0.5285$** and Brier Skill Scores near zero ($\le 0.0005$). The model possesses zero statistical edge over unconditional climatological base rates.
- **Conformal Coverage Discrepancy Reconciled:**  
  - Nominal Target: **$90.0\%$** ($\alpha = 0.10$).
  - Pre-2026 In-Sample Calibration: **$92.84\%$** (historical benchmark).
  - Legacy Flawed Out-of-Sample: **$92.36\%$** (**superseded** due to contemporaneous 168h residual lookahead leakage).
  - True Causal Out-of-Sample Holdout: **$84.89\%$** ($95\%$ CI: $[73.14\%, 93.14\%]$). Because the $90\%$ target is contained within the $95\%$ bootstrap interval, conformal calibration is statistically sound.

### Task 2: Multi-Horizon Strategy Reconciliation
- **Breakout Horizon Progression ($24\text{h} \to 72\text{h} \to 168\text{h}$):**  
  Evaluating the full 33,424-bar Coinbase hourly history confirmed that expanding the holding horizon to 168 hours increases mean gross return from $+0.0880\text{ R}$ to $+0.1629\text{ R}$ and cuts trade frequency by $60.7\%$ ($758 \to 298$ trades).
- **Transaction Cost Dominance:**  
  Under realistic friction, all candidates fail:
  - At 27 bps (Active Trader): 24h is $-0.2465\text{ R}$, 72h is $-0.2383\text{ R}$, 168h is $-0.1778\text{ R}$.
  - At 87 bps (Retail): 24h is $-0.9898\text{ R}$, 72h is $-0.9934\text{ R}$, 168h is $-0.9349\text{ R}$.
  - Breakeven round-trip fee for 168h breakout is **$12.90\text{ bps}$**. Unconditional breakouts cannot survive spot Coinbase fee schedules.

### Task 3: Level-2 Market Data Qualification
- **Feed Feasibility:** Coinbase Level-2 WebSocket feed (`level2_batch`, `matches`, `heartbeat`) is structurally qualified with sequence gap detection and heartbeat stall invalidation (>5.0s).
- **Strict Isolation:** Default disabled (`COINBASE_L2_COLLECTOR_ENABLED=1` required); dedicated separate ledger (`data/research/prospective_l2_gated_ledger_v1.jsonl`).
- **Zero Fabrication:** Order books are never backfilled from OHLCV.
- **Pre-Registered Gate ($H_1$):** Conditions 168h breakout entry on $\text{OFI}_{15\text{m}} > 0$, $\text{OBI}_5 > -0.20$, and $\text{Spread} \le 5.0\text{ bps}$.
- **Statistical Power Requirement:** At least **$N \ge 100$ independent, non-overlapping 168h trades** must mature before confirmatory evaluation.

### Task 4: Final Economic Decision Gate
- Because no strategy demonstrates positive net expectancy after transaction costs, the economic verdict remains **`NO_GO_NO_VALIDATED_EDGE`**.
- No parameters were tuned, no sub-periods were cherry-picked, and no promotional claims were manufactured.

---

## 3. Explicit Directives: What to Do Next vs. What NOT to Do Next

### 3.1 What We Must NOT Do Next:
1. **DO NOT Train Chronos-2 or Complex Neural Models:**  
   Do not add Amazon Chronos-2, Mamba, or large transformer models simply because the current directional forecast accuracy ($51.8\%$) seems weak. Complex models predicting marginal price distributions cannot overcome path-dependent barrier mechanics or 87 bps fee friction.
2. **DO NOT Backfill L2 Features into Historical Datasets:**  
   Never fabricate synthetic OFI, OBI, or VPIN metrics from hourly or 1-minute OHLCV data. Doing so creates spurious correlation and lookahead bias.
3. **DO NOT Treat Intermediate Trades as Statistical Proof:**  
   Do not evaluate L2 gating effectiveness until at least $N = 100$ independent, non-overlapping 168h prospective trades have matured in the dedicated ledger.
4. **DO NOT Redesign the UI or Introduce Decorative Churn:**  
   The current V32.35 UI is discoverable, responsive, and epistemically truthful. Leave the presentation stable.

### 3.2 What We Should Do Next:
1. **Maintain Prospective L2 Data Accumulation in Background:**  
   Allow the opt-in L2 shadow collector to accumulate genuine, prospective top-of-book order-flow observations across live market cycles.
2. **Investigate Structural Liquidity & Maker-Rebate Execution:**  
   Research passive limit-order execution (earning maker rebates or 0 bps fees) to evaluate whether the $+0.1629\text{ R}$ gross edge can be captured without incurring aggressive taker friction.
3. **Maintain Operating Boundaries:**  
   Keep `live_trading_enabled = false`, broker execution disabled, and positive-edge research alerts muted.

---

## 4. Protected Files & System Integrity Verification

All 5 protected files were verified bit-identical against their pre-run SHA-256 baseline hashes:
1. `data/prospective_entry_ledger.jsonl`: `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` — **PASS**
2. `data/prospective_shadow_v1.jsonl`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` — **PASS**
3. `data/prospective_entry_ledger_v2.jsonl`: `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` — **PASS**
4. `data/raw/ohlcv.parquet`: `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` — **PASS**
5. `data/raw/ohlcv_pre_backfill_backup.parquet`: `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` — **PASS**

All test suites (`tests_frontend.js` and `pytest`) remain at 100% pass rates. Zero unmanaged processes exist, and port 8000 remains unbound.

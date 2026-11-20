# V32.79 Phase 0 — ETF Flow Availability Audit (Workstream C)
**Milestone:** BTCognitive V32.79 — Phase 0 Baseline & Data Provenance Audit  
**Generated:** 2026-10-30  
**Auditor:** Lead Orchestrator — Workstream C (ETF Flow)  
**Classification:** OFFLINE_RESEARCH_ONLY  

> [!IMPORTANT]
> **Determination: $H_{\text{ETF}}$ is `BLOCKED_BY_PROVENANCE`. No ETF/ETP flow dataset exists locally. External acquisition is prohibited under `OFFLINE_RESEARCH_ONLY`.**

---

## 1. Search Methodology

A comprehensive search was conducted across all 407 files in the `data/` directory tree. Search criteria included the following keywords in filenames and directory names (case-insensitive):

- `etf`, `etp`, `flow`
- `farside` (primary public ETF flow tracker)
- `ishares`, `grayscale`, `ark`, `21shares`
- `blackrock`, `fidelity`, `invesco`, `bitwise`

**Command executed (Python):**
```python
for root, dirs, files in os.walk('data'):
    for fn in files:
        fp = os.path.join(root, fn)
        if any(k in fn.lower() for k in ['etf','etp','flow','farside','ishares','grayscale','ark','21share']):
            etf_found.append(fp)
```

---

## 2. Search Result

**ETF/ETP flow files found: NONE**

The only match on keyword "etf" was `data/market_memory.db` — this is a SQLite database for backtest market memory, not an ETF flow dataset.

**Result: No local ETF/ETP flow data exists in any format (CSV, parquet, JSON, SQLite table).**

---

## 3. Research Context — Why ETF Flow Data Is Non-Trivial to Acquire

Even if `OFFLINE_RESEARCH_ONLY` were waived, the following challenges would apply:

### 3.1 Publication Timestamp Ambiguity

The Manager cited a 2025 Economics Letters study (Economist Letters, 2025) finding that Bitcoin price movements were a **primary driver of daily spot ETP flows** rather than the reverse. This creates a severe reverse causality problem.

Farside Investors (primary public source) states that its daily US spot Bitcoin ETF flow figures are updated "in real time, typically during the evening and night in US time." This means:
- A date-only flow record (e.g., "2024-01-12: $520M net inflow") provides no sub-daily publication timestamp.
- The strategy cannot determine whether a 09:00 UTC trade decision could have used the prior day's ETF flow figure — Farside may not have published it yet.
- The minimum defensible lag would be **T+1 day** (use prior business day's flow for the current day's trade). This significantly attenuates any signal.

### 3.2 Coverage Gaps

Public ETF data only begins from the first US spot Bitcoin ETF approval date: **2024-01-11**. This limits any ETF flow study to post-approval data only. The OHLCV checkpoint contains approximately 9.6 months of post-approval data (Jan 2024 → Oct 2026 = ~24,288 hourly bars). However, ETF data at daily granularity provides at most ~650 daily observations — insufficient to overcome the multiple-comparison correction burden if multiple ETF metrics are tested.

### 3.3 Instrument-to-Exchange Mapping

ETF flows are recorded in USD terms at the fund level (e.g., IBIT, GBTC, FBTC). Converting to hourly BTCUSD price impact requires estimating when each fund's AP (Authorized Participant) purchases or sells underlying BTC on exchange. This lag is unobservable from public data.

---

## 4. Formal Determination

| Criterion | Status |
|---|---|
| ETF flow data present locally | ❌ ABSENT |
| External acquisition permitted | ❌ PROHIBITED (OFFLINE_RESEARCH_ONLY) |
| Could be constructed from public data? | ⚠️ In principle, but timestamp provenance cannot be verified offline |
| Reverse causality concern | ⚠️ HIGH — Economics Letters 2025 finding that BTC price drives ETF flows |
| Minimum defensible lag (T+1) applicable? | ⚠️ Would require daily granularity with T+1 availability assumption |

**$H_{\text{ETF}}$ Determination: `BLOCKED_BY_PROVENANCE`**

Rationale:
1. No local dataset exists.
2. External acquisition is prohibited.
3. Even if data were available, publication timestamp provenance cannot be established from offline sources.
4. The reverse causality risk (price → flows, not flows → price) means this hypothesis requires extra-careful causal design that cannot be validated without fresh data.

**Recommendation:** If the Manager lifts the `OFFLINE_RESEARCH_ONLY` constraint in a future milestone, the minimum defensible protocol would be:
1. Acquire Farside daily flow data with documented retrieval timestamps.
2. Apply T+1 availability lag (use day D-1 flow for day D trades).
3. Restrict analysis to post-2024-01-11 period only.
4. Use a Granger causality test as a prerequisite before any strategy experiment.
5. Apply DM-HLN with Newey-West SE correction given the daily autocorrelation in flow series.

---

*No external data fetched. No datasets modified. No models trained.*


# V32.79 Phase 0 — Macro Event Calendar Audit (Workstream D)
**Milestone:** BTCognitive V32.79 — Phase 0 Baseline & Data Provenance Audit  
**Generated:** 2026-10-30  
**Auditor:** Lead Orchestrator — Workstream D (Macro Event Calendar)  
**Classification:** OFFLINE_RESEARCH_ONLY  

> [!IMPORTANT]
> **Determination: $H_{\text{Macro\_Abstain}}$ is `BLOCKED_BY_PROVENANCE`. No FOMC/CPI event calendar exists locally. Without a verifiable publication timestamp for each event, a causal entry abstention filter cannot be constructed.**

---

## 1. Search Methodology

A search was conducted across all files in the `data/` directory (407 files) for any macro event calendar. Keyword search included: `fomc`, `cpi`, `macro`, `event`, `calendar`, `fed`, `federal`, `reserve`.

---

## 2. Search Result

**Macro event calendar files found: NONE**

Files that matched the keyword search but are NOT macro calendars:
- `data/research/l2_stream/l2_burnin_events_20261025_135844.jsonl` — L2 order book burn-in event log (matched "event")
- `data/research/l2_stream/l2_burnin_events_20261025_140347.jsonl` — same type
- `data/research/l2_stream/l2_burnin_events_20261025_140437.jsonl` — same type
- `data/research/user_positions/user_position_events.jsonl` — user position events (matched "event")

None of these contain FOMC meeting dates, CPI release times, or any Federal Reserve announcement schedule.

---

## 3. Research Context — Why Macro Calendars Require Sub-Hour Timestamps

The Manager's proposed $H_{\text{Macro\_Abstain}}$ hypothesis (abstain from entries within a window around FOMC/CPI releases) requires:

### 3.1 Minimum Defensible Protocol

To avoid lookahead, the protocol requires:
1. **Pre-scheduled event times** — FOMC meeting dates and CPI release times are known in advance (published by the Federal Reserve and BLS respectively). This pre-scheduled knowledge is causal.
2. **Sub-hour release timestamps** — The exact release minute matters. CPI is released at 08:30 ET (13:30 UTC) on scheduled dates. FOMC statements are released at approximately 14:00–14:30 ET on meeting dates. Press conferences follow.
3. **Blackout window definition** — A "±2h" or "±4h" abstention window around each event requires the exact release timestamp, not just the date.
4. **No same-hour contamination** — If a 09:00 UTC bar closes at 09:00 UTC and the CPI is released at 08:30 UTC, the 09:00 UTC close-to-close return embeds the CPI reaction. The bar opened at 08:00 UTC — partially pre-release.

### 3.2 Federal Reserve Working Paper Evidence

A 2026 Federal Reserve working paper (cited in Manager's V32.79 brief) reports:
- Increased cryptocurrency volatility, trading volume, and bid-ask spreads around US monetary, inflation, and labour-market announcements.
- This supports the economic hypothesis that macro events create elevated risk.
- But it also means any entry made inside the announcement window faces higher adverse excursion risk — consistent with the proposed abstention filter.

### 3.3 Practical Implementation Requirements

| Required Input | Status |
|---|---|
| FOMC meeting schedule (future-known dates) | ❌ No local file |
| CPI release schedule (BLS scheduled dates) | ❌ No local file |
| Sub-hour release timestamps (ET/UTC) | ❌ No local file |
| Blackout window definition (±Nh) | ❌ Not yet defined |
| Historical confirmation of actual release times | ❌ Not available offline |

---

## 4. Formal Determination

| Criterion | Status |
|---|---|
| Macro event calendar present locally | ❌ ABSENT |
| External acquisition permitted | ❌ PROHIBITED (OFFLINE_RESEARCH_ONLY) |
| Pre-scheduled dates constructible from memory? | ⚠️ FOMC dates are publicly known, but offline construction risks errors and cannot be verified |
| Sub-hour timestamps establishable offline? | ❌ Cannot be verified without live data |

**$H_{\text{Macro\_Abstain}}$ Determination: `BLOCKED_BY_PROVENANCE`**

Rationale:
1. No local event calendar exists.
2. External acquisition is prohibited.
3. Even if FOMC/CPI dates were hand-coded from memory, the exact release minute (required for a well-defined abstention window on hourly candles) cannot be verified offline.
4. Without verifiable publication timestamps, the abstention filter could inadvertently embed lookahead (e.g., abstaining from a bar that partially precedes the announcement).

**Recommendation for future research:** If approved, the minimum defensible acquisition protocol is:
1. Download the FRED/BLS economic calendar with release timestamps.
2. Cross-validate against Federal Reserve press release timestamps (all public and archived).
3. Express all times in UTC.
4. Define abstention window: enter `ABSTAIN` for bars where `event_time - W ≤ bar_open < event_time + W`, where $W$ is the blackout window (propose $W$ = 2h pre-event, 4h post-event as a starting point).
5. Validate that the blackout window does not eliminate >5% of bars (diminishing returns concern).

---

*No external data fetched. No datasets modified. No models trained.*


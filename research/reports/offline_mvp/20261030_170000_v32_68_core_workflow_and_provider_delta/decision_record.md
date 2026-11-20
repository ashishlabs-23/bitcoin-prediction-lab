# BTCognitive V32.68 — Governed Decision Record

**Decision Date:** 30 October 2026  
**Milestone:** V32.68 — Offline Core-Workflow Verification & Provider Rights Delta  
**Lead Multi-Agent Orchestrator:** BTCognitive Research & Governance Team  

---

## 1. Five Mandatory Milestone Decisions

### Decision 1: `OFFLINE_WORKFLOW_QA`
- **Verdict:** `PASS`
- **Evidence:**
  - 8/8 core workflow scenarios passed via real Headless Chrome CDP automation in `DATA_MODE=fixture`.
  - Analyse button debouncing verified; 0 rapid duplicate invocations leaked to backend.
  - 30 consecutive warm benchmark repetitions executed with 0 errors. Total end-to-end latency: median ($p_{50}$) = 82.36 ms, $p_{90}$ = 110.86 ms, $p_{95}$ = 131.66 ms, max = 171.77 ms (well below 500 ms SLA).
  - First-perceptual feedback rendered in 215.1 ms (< 300 ms SLA).
  - Outage and staleness guards verified fail-closed (0 synthetic or $80,000 quotes fabricated).

### Decision 2: `PROVIDER_RIGHTS`
- **Verdict:** `BLOCKED` (Commercial Contract Negotiation Required)
- **Evidence:**
  - Expanded survey evaluated 18 provider/dataset options across 14 legal and technical dimensions.
  - Bitstamp Data Licence Agreement (DLA) is the strongest candidate for direct BTC/USD spot 1m exchange data; requires formal bilateral contract execution.
  - CoinGecko Paid API is the strongest candidate for aggregated multi-venue benchmarking, but expressly prohibits foundation AI model training and raw redistribution.
  - Free/public tiers (CoinGecko Demo, Twelve Data Basic, CCXT library wrappers, Binance Vision archives under CC BY-NC-SA 4.0) fail commercial redistribution and AI derived-feature requirements.
  - 10 binding licence questions formulated and ready for vendor procurement outreach.

### Decision 3: `PUBLIC_CHART_MVP`
- **Verdict:** `NO-GO`
- **Evidence:**
  - Public market-data redistribution is legally prohibited without an active, counter-signed commercial licence.
  - Ingress data lane remains safely configured to fail-closed (`DATA_MODE=provider` blocks outbound requests until provider configuration is approved).
  - Public launch gate remains locked until provider agreement is executed.

### Decision 4: `ENTRY_SIMULATION`
- **Verdict:** `EXCLUDED_FROM_PUBLIC_MVP`
- **Evidence:**
  - "Enter (Simulated)" workflow is verified safe as an internal research paper-trading simulator writing solely to `smart_entry_attempts.jsonl`.
  - Absolutely 0 broker or exchange order APIs exist in the codebase, and 0 trading calls were observed across 143 network requests.
  - To prevent user confusion and maintain strict regulatory separation, entry simulation remains restricted to offline research and is excluded from the public read-only charting MVP.

### Decision 5: `MARKET_EDGE_VALIDATION`
- **Verdict:** `NOT_ESTABLISHED`
- **Evidence:**
  - The 90% directional return hit rate remains an unverified research hypothesis.
  - Volatility forecasting accuracy (QLIKE, RMSE) must never be conflated with directional return prediction.
  - Models remain under `OFFLINE_RESEARCH_ONLY` authorization. Live trading is permanently disabled.

---

## 2. Sign-off & Audit Trail

- **Data Integrity:** All 6 protected research datasets and prospective ledgers bit-identical (`MATCH`).
- **Failure Inventory:** All 47 historical IDs reconciled with 0 active defects.
- **Git Working Tree:** HEAD at `25d483f4c3646661b57311de9d0b53d2be881adb` on `main`; 0 destructive git actions taken.


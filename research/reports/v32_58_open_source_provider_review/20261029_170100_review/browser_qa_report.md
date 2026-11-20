# BTCognitive Real Browser QA & Visual Evidence Report (V32.58)

**Audit Date:** 29 October 2026  
**Auditor:** BTCognitive Lead Research Orchestrator  
**Execution Engine:** Headless Chrome via `scripts/qa/v32_58_browser_qa_runner.py` on dynamic loopback port.

---

## 1. Multi-Viewport & Scenario Execution Summary

By decoupling browser verification from external live data rights, all critical charting and forecast UI pathways were comprehensively tested using isolated deterministic QA fixtures:

| Scenario ID | Viewport | Target Verification State | Exit Code | Screenshot Size | Quality Assertions | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NORMAL_DESKTOP** | 1280x800 | Fresh 1h OHLCV candles, volume histogram, matching forecast origin, directional marker | 0 | 296,013 bytes | Chart rendered, markers aligned, no fake quotes | **PASS** |
| **MOBILE_375PX** | 375x667 | Mobile responsive layout, touch-friendly zoom controls, clean overlay stacking | 0 | 116,119 bytes | No horizontal scroll, controls legible, clean nav | **PASS** |
| **TIMEFRAME_MISMATCH** | 1280x800 | 15m forecast origin on 1h chart; marker withheld from unaligned candle | 0 | 330,344 bytes | No misplaced marker; `#chart-ai-forecast-overlay` displays warning & horizon | **PASS** |
| **DATA_STALE** | 1280x800 | Market data age > 2h without fresh updates; `STALE` status displayed | 0 | 304,689 bytes | Stale badge visible; price chart remains available; unanchored forecast | **PASS** |
| **PROVIDER_UNAVAILABLE** | 1280x800 | Complete upstream provider outage; fail-closed `DATA_UNAVAILABLE` | 0 | 316,910 bytes | Zero fabricated quotes ($80,000 strictly absent); price is null; clean error UI | **PASS** |

---

## 2. Visual Artifacts & DOM Verification

All screenshots are stored in the unique audit artifacts directory:
- Desktop Normal Chart: `research/reports/v32_58_open_source_provider_review/20261029_170100_review/screenshots/chart_desktop_normal.png`
- Mobile Viewport (375x667): `research/reports/v32_58_open_source_provider_review/20261029_170100_review/screenshots/chart_mobile_375px.png`
- Timeframe Mismatch Guard: `research/reports/v32_58_open_source_provider_review/20261029_170100_review/screenshots/chart_timeframe_mismatch.png`
- Stale Market Data Handling: `research/reports/v32_58_open_source_provider_review/20261029_170100_review/screenshots/chart_data_stale.png`
- Provider Unavailable State: `research/reports/v32_58_open_source_provider_review/20261029_170100_review/screenshots/chart_provider_unavailable.png`

### DOM Assertions Confirmed:
1. `#btc-lwc-chart` mounts cleanly and initializes TradingView Lightweight Charts canvas.
2. `#chart-ai-forecast-overlay` strictly enforces fail-closed state display.
3. Hardcoded quote strings (`$80,000` or `80000.0`) are **strictly absent** during provider outage states.
4. Primary navigation remains cleanly scoped to informational market monitoring (`#nav-how-it-works` present; real order placement tools absent).


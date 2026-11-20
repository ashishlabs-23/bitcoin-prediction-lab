# BTCognitive V37.4 — Manager Final Acceptance Report

**Assessment date:** 2026-11-04  
**Decision:** `PARTIAL_PASS` — public Bitstamp protocol reachability was demonstrated, but the live ingestion supply chain and real application path were not implemented or verified.

## Executive decision

BTCognitive's original institutional-grade BTCUSD intelligence and quantitative risk-analysis vision remains intact. No route, feature, engine, or dataset was removed or replaced. No code change was made during this run; the deliverables document verified defects and a real bounded feed smoke without misrepresenting them as an integrated implementation.

The most important new finding is that the three actual Bitstamp trades received in the smoke had event timestamps roughly **226 seconds older** than receipt time. The WebSocket subscription works at the protocol level, but freshness did not pass. Also, the Bitstamp official documentation and substantive data-use terms were inaccessible; persistence and model-research rights are not cleared.

A 30-minute soak was started but stopped before completion; it exited without writing its summary. No soak acceptance is claimed.

## Decisions and statuses

| Area | Status | Evidence |
|---|---|---|
| Project scope | `PRESERVED` | No core feature, route, engine, or research module removed. |
| Canonical source | `BITSTAMP_BTCUSD_PROVISIONAL` | Owner-specified initial source and public WebSocket smoke; official docs, rights, and freshness remain open. |
| Bitstamp live reachability | `PARTIAL_PASS` | `live_trades_btcusd` acknowledgement and three actual messages; event timestamps lagged receipt by ~226.08 seconds. |
| Continuous app ingestion | `NOT_VERIFIED` | No repository-owned persistent connection/candle/API integration was implemented. |
| Secondary sources | `DEFERRED` | Coinbase AI/ML terms restriction; Gemini and Kraken rights/compatibility remain unresolved. No venue series mixed. |
| Historical data | `UNVERIFIED` | Existing local provenance limits stand; no row-level dataset audit or research selection was performed. |
| API/frontend | `NOT_VERIFIED` | No actual live feed sample reached FastAPI or the chart. |
| Engine integration | `NOT_VERIFIED` | Existing engine input limitations and synthetic-default risks remain. |
| Regression suite | `PARTIAL` | 42 focused Python tests passed, one stale protected-hash expectation failed; frontend tests and syntax checks passed. |
| Research experiment | `INCONCLUSIVE` | No admissible historical evaluation. |
| Prospective evidence | `NOT_STARTED` | No prospective ledger writes. |
| Model authorization | `OFFLINE_RESEARCH_ONLY` | No promotion or validation claim. |
| Live trading | `DISABLED` | No broker, order, or execution path enabled or used. |

## Definition-of-done matrix

| ID | Criterion | Status |
|---|---|---|
| D1 | Primary BTCUSD exchange feed connects | `PARTIAL_PASS` — a bounded direct Bitstamp public socket connected, not an application-owned feed. |
| D2 | Actual trade observations received and parsed | `PARTIAL_PASS` — three messages parsed; source timestamps were stale relative to receipt. |
| D3 | Raw observations preserve exchange and receive timestamps | `PARTIAL_PASS` — observed transiently in smoke output; no application record/persistence. |
| D4 | Duplicate events handled deterministically | `NOT_VERIFIED` |
| D5 | One-minute candles constructed correctly | `NOT_VERIFIED` |
| D6 | Missing intervals/stale data detected | `NOT_VERIFIED` in production code; smoke identified timestamp delay manually. |
| D7 | Same-source historical recovery and provenance | `NOT_VERIFIED`; terms/recovery semantics unresolved. |
| D8 | Secondary feeds remain independent | `PASS` for no cross-venue combining; new secondary shadow feeds were not enabled. |
| D9 | Existing FastAPI exposes actual observations and quality | `NOT_VERIFIED` |
| D10 | Existing engines receive compatible validated data | `NOT_VERIFIED` |
| D11 | Existing frontend charts display actual API observations | `NOT_VERIFIED` |
| D12 | Existing routes/features remain available | `PASS` for no removals; targeted route tests ran. |
| D13 | Reconnect/error/recovery tests pass | `NOT_VERIFIED`; no new ingestion implementation exists. |
| D14 | Actual application integration tested | `NOT_VERIFIED`; no real FastAPI/live feed run. |
| D15 | Live smoke or soak recorded | `PARTIAL_PASS` for bounded smoke; 30-minute soak not completed. |
| D16 | Protected hashes and Git state remain intact | `PASS` for test guard and unchanged protected files; see integrity note below. |

## Source and dataset decisions

- **Bitstamp** remains provisional primary, not rights-cleared. Do not persist, redistribute, or use it for model research until terms and event-time semantics are confirmed.
- **Coinbase** must not be used for AI/ML development, training, validation, or benchmarking without express written consent under its reviewed 2026 Market Data Terms.
- **Gemini/Kraken** remain candidates only; the reviewed evidence does not settle the intended research rights.
- **Cryptofeed** was not added because it is AGPL-3.0-or-later and owner licensing approval was not obtained.
- Existing minute/hourly datasets remain inadmissible for Track B/confirmatory analysis absent provenance resolution. No historical observations were used for selection.

Full source evidence is in [V37_4_EXCHANGE_SOURCE_AND_LICENSING_REPORT.md](./V37_4_EXCHANGE_SOURCE_AND_LICENSING_REPORT.md); historical candidate status is in [V37_4_QA_AND_PROVENANCE_REPORT.md](./V37_4_QA_AND_PROVENANCE_REPORT.md).

## Test and repository evidence

- `.\.venv_win\Scripts\pytest.exe -q -p no:cacheprovider -m "not network and not quarantined" tests\test_v32_61_provider_adapter_poc.py tests\test_v32_66_provider_contract.py tests\test_candle_manager.py tests\test_coinbase_l2_collector_and_gating.py tests\test_market_monitor_routes.py` — **42 passed, 1 failed**. The sole failure is a stale hard-coded SHA expected by `test_protected_artifacts_bit_level_invariance`; it expected `c007...`, while the unchanged checkout's `data/raw/ohlcv.parquet` hashes to `ba06...`. We did not modify the dataset or test expectation. The pytest protected-file guard reported an unchanged before/after manifest digest.
- `npm test` — passed.
- `npm run check` — passed.
- Full suite — not run and not claimed as passing.
- Branch/HEAD remain `milestone/v35.3-critical-remediation` / `25d483f4c3646661b57311de9d0b53d2be881adb`.
- No code files were changed; six V37.4 reports are the only intentional repository additions. No staged files or deletions are intended.
- Baseline full status is preserved outside the repository at `C:\Users\Ashish\.copilot\session-state\51eedde1-236e-4970-84a5-a1b2daff43ad\v37_4_preflight_git_status.txt`.

## Changed files

Only these new V37.4 reports were created:

- [V37_4_EXCHANGE_SOURCE_AND_LICENSING_REPORT.md](./V37_4_EXCHANGE_SOURCE_AND_LICENSING_REPORT.md)
- [V37_4_EXISTING_DATA_FLOW_AUDIT.md](./V37_4_EXISTING_DATA_FLOW_AUDIT.md)
- [V37_4_LIVE_INGESTION_REPORT.md](./V37_4_LIVE_INGESTION_REPORT.md)
- [V37_4_API_FRONTEND_INTEGRATION_REPORT.md](./V37_4_API_FRONTEND_INTEGRATION_REPORT.md)
- [V37_4_QA_AND_PROVENANCE_REPORT.md](./V37_4_QA_AND_PROVENANCE_REPORT.md)
- [V37_4_MANAGER_FINAL_ACCEPTANCE_REPORT.md](./V37_4_MANAGER_FINAL_ACCEPTANCE_REPORT.md)

No change was made to authentication identity, which remains `single_user_local` per the owner decision in prior context; no multi-user architecture was introduced.

## Required next implementation sequence

1. Confirm Bitstamp official message timestamp/side semantics and data-use terms; resolve the ~226-second lag before enabling analysis consumption.
2. Implement a bounded Bitstamp feed service through the existing observation contract, with duplicate/out-of-order handling and source-separated one-minute candle quality.
3. Use same-source REST recovery only after rights and exact candle timestamp semantics are confirmed; keep historical writes out of protected datasets.
4. Add status/candle handoff through existing FastAPI contracts and integrate the active chart/ticker without disturbing route aliases or existing screens.
5. Gate every engine on its actual input/history; fix synthetic-default statuses before exposing those outputs as observed intelligence.
6. Resolve the stale protected-hash test expectation by reconciling its expected digest with the protected baseline—do not modify `data/raw/ohlcv.parquet`.
7. Complete a fresh bounded soak, actual FastAPI API sample, local real-browser rendering, and focused regression rerun before a higher acceptance.

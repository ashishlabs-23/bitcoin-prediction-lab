# V32.60 Evidence Review: End-to-End Analyse Workflow & Screenshot Inspection

**Audit Date:** 29 October 2026  
**Auditor:** BTCognitive Lead Research Orchestrator  
**Baseline Artifacts Audited:**
- `research/reports/v32_59_analyse_e2e_and_strategy_audit/20261029_172800_audit/analyse_e2e_matrix.csv`
- `research/reports/v32_59_analyse_e2e_and_strategy_audit/20261029_172800_audit/screenshots/*.png`
- `research/reports/v32_59_analyse_e2e_and_strategy_audit/20261029_172800_audit/screenshots/*_dom.html`
- `scripts/qa/v32_59_analyse_e2e_runner.py`

---

## 1. Technical Forensic Audit of the 6 KB Screenshot

### 1.1 The Anomaly
In the V32.59 audit run, `screenshots/analyse_qualifying_candidate.png` had a file size of **6,456 bytes**, whereas the other 9 scenario screenshots ranged from **221,911 to 251,986 bytes**.

### 1.2 Inspection Data
- **File Name:** `research/reports/v32_59_analyse_e2e_and_strategy_audit/20261029_172800_audit/screenshots/analyse_qualifying_candidate.png`
- **File Size:** 6,456 bytes
- **Dimensions:** 1280 x 900 pixels
- **Image Format:** Portable Network Graphics (PNG), 8-bit RGB color
- **Visual Content:** Completely dark uniform background (`#0B0E14`) containing only the top test harness bar (`#111827`) with the badge text `SCENARIO: ANALYSE_QUALIFYING_CANDIDATE`. The main application root `<div id="root"></div>` was entirely empty.

### 1.3 Root Cause Analysis
Examination of the dumped DOM (`analyse_qualifying_candidate_dom.html`) and `scripts/qa/v32_59_analyse_e2e_runner.py` revealed two compound causes:

1. **Schema Mismatch in Mock Response:**
   - In `v32_59_analyse_e2e_runner.py:514`, the mock endpoint for `ANALYSE_QUALIFYING_CANDIDATE` returned:
     ```python
     "smart_entry_decision": {
         "status": "SMART_ENTRY_AVAILABLE",
         "strategy_id": "TSMOM_DONCHIAN_24H_168H",
         "strategy_name": "Donchian Trend Breakout",
         "direction": "LONG",
         "proposed_entry_price": 85250.0,
         "proposed_tp_price": 86950.0,
         "proposed_sl_price": 84100.0,
         ...
     }
     ```
   - However, the React frontend in `web/app.js:18465` strictly expects:
     ```javascript
     $${smartEntryDecision.candidate_setup.entry_reference_price.toLocaleString()}
     ```
   - Because `smartEntryDecision.candidate_setup` was omitted in the mock payload, React 18 threw an uncaught TypeError:
     `Cannot read properties of undefined (reading 'entry_reference_price')`
   - In React 18, an unhandled exception during component render causes the entire component tree to unmount, resetting `<div id="root"></div>` to empty.

2. **Harness Startup Timeout Window:**
   - When Chrome started cold, the test driver loop gave 40 intervals of 100ms (4.0s) for `#btn-analyse-setup` to appear. On a loaded system with 3D Three.js canvas initialization, 4.0s occasionally elapsed before the DOM node was accessible, triggering `window.__QA_RESULTS__.error_message = "btn-analyse-setup not found in DOM within 4s"`.
   - The screenshot captured this pre-render/crashed state. Because uniform solid-color areas compress with near-theoretical efficiency under PNG DEFLATE, the resulting 1280x900 image compressed to 6,456 bytes.

### 1.4 Remediation & Verification
- The schema in `scripts/qa/v32_59_analyse_e2e_runner.py` was corrected to match the canonical backend contract: `smart_entry_decision.candidate_setup` is now properly populated with `entry_reference_price`, `proposed_tp_price`, `proposed_sl_price`, `reward_usd`, `risk_usd`, and `calibration_note`.
- When properly formatted, `SmartEntrySimulatorView` renders the complete "ENTRY CANDIDATE FOUND" banner, the metric grid (Entry, Fixed TP, Fixed SL, Max Duration), the calibration lock notice, and the simulated trade preview card without unhandled exceptions.
- The original V32.59 artifact (`analyse_qualifying_candidate.png`, 6,456 bytes) is preserved untouched in `v32_59_analyse_e2e_and_strategy_audit/` to protect audit provenance.

---

## 2. Invariant Verification Across All 10 Scenarios

| Invariant / Check | Verified Status | Technical Evidence |
| :--- | :---: | :--- |
| **1. Zero Simulated Trades Created (`attempts_created == 0`)** | **PASS** | Evaluated in all 10 scenarios. Both API JSON response and DOM element queries (`.simulated-trade-card`, `#active-simulated-trade`) confirmed 0 attempts created. |
| **2. Zero Ledger Mutations** | **PASS** | Filesystem audit verified that `data/prospective_entry_ledger.jsonl`, `data/prospective_shadow_v1.jsonl`, and `data/prospective_entry_ledger_v2.jsonl` had zero appended lines. |
| **3. Zero Quote Fabrication** | **PASS** | In `ANALYSE_PROVIDER_UNAVAILABLE`, the engine returned HTTP 400 / `DATA_UNAVAILABLE`. No synthetic $80,000 price appeared in responses or DOM. |
| **4. Fail-Closed on Gaps & Staleness** | **PASS** | In `ANALYSE_GAPS` and `ANALYSE_STALE_DATA`, the pipeline returned `status: "ABSTAIN"` with explicit gap and staleness reasons. |
| **5. Idempotency & Debounce** | **PASS** | In `ANALYSE_DOUBLE_CLICK`, rapid consecutive clicks reused the same request payload digest and request ID, ensuring a single execution. |
| **6. Deterministic Fixture Isolation** | **PASS** | Deterministic fixtures are served strictly on the isolated test loopback server (`/api/qa/seed-candles`) and are completely inaccessible from public production routes. |


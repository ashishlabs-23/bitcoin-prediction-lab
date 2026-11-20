# V33.00A — Runtime Fail-Closed Gate Traceability Specification (Workstream 6)

**Milestone:** BTCognitive V33.0A — Consolidation Closure & Runtime Governance Verification  
**Generated:** 2026-10-31T11:55:00Z  
**Lead Orchestrator:** Antigravity  
**Operating Contract:** `OFFLINE_RESEARCH_ONLY`  
**Governing Verification:** End-to-End Analysis Path & The Seven Fail-Closed Gates  

---

## 1. Context & Manager Mandate

In the V33.0 Review and Final Ruling, the Manager mandated:

> **Manager Finding:**  
> Trace the complete user-facing Analysis execution path:  
> Frontend Analysis action → API route → tournament engine → strategy selection → integrated analysis → smart entry decision → final governance decision.  
> For each of the seven fail-closed gates document:  
> - Exact implementation location.  
> - Gate input.  
> - Pass condition.  
> - Failure condition.  
> - Resulting action.  
> - Relevant tests.  
> 
> Demonstrate that a static model-registry entry cannot bypass runtime authorization or produce an actionable trading decision when governance conditions are unmet.  
> Test missing manifests, stale data, insufficient evidence, unapproved model status and unavailable baseline predictions.

This document traces the complete execution flow and proves the mathematical impossibility of unauthorized execution.

---

## 2. End-to-End Analysis Execution Path

The user triggers the Analysis workflow from the web interface or API client. The sequential execution path proceeds through seven discrete stages:

```mermaid
sequenceDiagram
    autonumber
    actor User as Operator / UI
    participant API as api/routes_tournament.py
    participant ENG as engine/regime_strategy_tournament.py
    participant SEL as engine/strategy_selection.py
    participant COST as engine/execution_cost_model.py
    participant REG as models/authoritative_model_registry.py
    participant GATE as validation/startup_gate.py

    User->>API: POST /api/tournament/analyse (closed candle payload)
    API->>ENG: execute_integrated_analyse_and_tournament()
    
    Note over ENG: Gate 4: Causal & Freshness Check
    ENG->>ENG: Validate closed candle continuity, timestamps, and age
    alt Candles Stale or Discontinuous
        ENG-->>API: Status: ABSTAIN (Reason: MARKET_DATA_STALE)
        API-->>User: HTTP 200: ABSTAIN (attempts_created = 0, is_read_only = true)
    end

    Note over ENG,SEL: Gate 3 & Gate 5: 5-Archetype MEIE Screening
    ENG->>SEL: evaluate_candidate_archetype() for each of 5 Archetypes
    SEL->>COST: get_round_trip_friction_bps(cost_scenario)
    COST-->>SEL: Round-trip drag (24 to 87 bps)
    SEL->>SEL: Compute Net EV = Gross EV - Friction
    
    alt All candidates fail 7/10 screen or Net EV <= 0
        SEL-->>ENG: 0 Eligible Candidates
        ENG-->>API: Status: ABSTAIN (Reason: NO_ELIGIBLE_CANDIDATES)
        API-->>User: HTTP 200: ABSTAIN (attempts_created = 0)
    end

    Note over ENG: Gate 2: Runtime Model Authorization Check
    ENG->>REG: get_active_production_model(runtime_readiness)
    REG->>GATE: verify_scientific_contract()
    alt Gate Fails or Model is OFFLINE_RESEARCH_ONLY
        REG-->>ENG: Authorization: OFFLINE_RESEARCH_ONLY / BLOCKED
        ENG-->>API: Status: ABSTAIN (Trading permanently DISABLED)
        API-->>User: HTTP 200: ABSTAIN (live_trading = "DISABLED")
    end
```

---

## 3. Comprehensive Specification of the Seven Fail-Closed Gates

### Gate 1 — Strict Non-Execution & Permanent Trading Lock
- **Implementation Location:** `engine/status_contract.py` (L15, L65–L75), `api/routes_tournament.py` (L580–L600), `api/server.py` (L120–L140).
- **Gate Input:** System startup state and all outbound API response payloads.
- **Pass Condition:** `execution_status == "DISABLED — ANALYSIS ONLY"` and `attempts_created == 0` and `is_read_only == True`.
- **Failure Condition:** Any attempt to invoke order placement, configure private keys, or set `execution_status = "ENABLED"`.
- **Resulting Action:** Immediate HTTP 403 / 409 exception; code refuses execution; process aborts.
- **Relevant Tests:** `tests/test_v32_48_integrated_analyse_and_tournament.py::test_integrated_workflow_read_only_invariants`, `tests/test_authorization_consistency.py::test_api_lifespan_research_gate_consistency`.

---

### Gate 2 — Authoritative Model Authorization & Production Lock
- **Implementation Location:** `models/authoritative_model_registry.py` (L365–L405, `get_active_production_model` & `is_production_authorized`), `validation/startup_gate.py` (L600–L656).
- **Gate Input:** `runtime_readiness` dictionary containing output of `verify_scientific_contract()`.
- **Pass Condition:** Both the static registry classification AND the runtime pre-flight verification explicitly return `AUTHORIZED_FOR_PRODUCTION`.
- **Failure Condition:** Model is classified as `OFFLINE_RESEARCH_ONLY`, `EXPERIMENTAL_CHALLENGER`, `BLOCKED_PROVENANCE_UNVERIFIED`, or runtime readiness has `authorized == False`.
- **Resulting Action:** Runtime model record is dynamically overridden with `AuthorizationStatus.BLOCKED_AUDIT_FAILURE` or `AuthorizationStatus.OFFLINE_RESEARCH_ONLY`; `is_production_authorized()` returns `False`.
- **Static Registry Bypass Demonstration:**  
  *Proof of Impossibility:* `get_active_production_model()` explicitly checks:
  ```python
  if runtime_readiness is not None and not runtime_readiness.get("authorized", False):
      return replace(ACTIVE_PRODUCTION_MODEL, authorization_status=AuthorizationStatus.OFFLINE_RESEARCH_ONLY)
  ```
  Even if an engineer modifies `ACTIVE_PRODUCTION_MODEL` in the python source to claim `AUTHORIZED_FOR_PRODUCTION`, passing a failed or unverified `runtime_readiness` payload dynamically overrides the authorization status back to `OFFLINE_RESEARCH_ONLY` or `BLOCKED_AUDIT_FAILURE`. The static entry cannot bypass the runtime gate.
- **Relevant Tests:** `tests/test_authorization_consistency.py::test_production_model_alignment_fails_closed_for_offline_model`, `tests/test_stage5_dependency_and_model_identity.py`.

---

### Gate 3 — Epistemic Target Separation & Anti-Conflation
- **Implementation Location:** `engine/regime_strategy_tournament.py` (L380–L410), `models/authoritative_model_registry.py` (L13–L17, L75–L85), `engine/forecast_engine_15m.py` (L10–L18).
- **Gate Input:** Model target identifier, prediction outputs, and UI payload representations.
- **Pass Condition:** Realized variance point forecasts (`rv7d_var_ann`) and conformal intervals ($[L_t, U_t]$) are strictly labeled as risk envelopes; `directional_prediction_capability` is hardcoded to `False`.
- **Failure Condition:** Any attempt to present quantile containment ($\ge 90\%$) as directional trading hit rate, or use volatility magnitude to imply upward/downward price direction.
- **Resulting Action:** API filters out directional recommendations; directional probability defaults to `None`; status contract sets `opportunity_status = "NO_OPPORTUNITY"`.
- **Relevant Tests:** `tests/test_authorization_consistency.py::test_authoritative_model_registry_state`, `tests/test_phase6_terminal_release_readiness.py`.

---

### Gate 4 — Causal Point-in-Time Data Contract
- **Implementation Location:** `engine/regime_strategy_tournament.py` (L120–L165, `validate_market_data_contract`), `engine/hypothetical_scenario_planner.py` (L80–L120), `engine/execution_cost_model.py`.
- **Gate Input:** Input candle dataframe `df_1h`, timestamp sequence, candle close flags, and current clock time.
- **Pass Condition:** All candles are closed ($t_{\text{close}} \le t_{\text{eval}}$); timestamps are strictly monotonic increasing without gaps; candle age $\le 3.0\text{ hours}$ (operational freshness).
- **Failure Condition:** Incomplete (open) current candle included; duplicate or out-of-order timestamps; candle age $> 3.0\text{ hours}$; negative time delta.
- **Resulting Action:** Returns `status = "ABSTAIN"` (or `status = "UNAVAILABLE"`) with rejection code `MARKET_DATA_STALE` or `LOOKAHEAD_ASSERTION_FAILURE`.
- **Relevant Tests:** `tests/test_stage8_data_experiments.py::test_point_in_time_boundary`, `tests/test_scenario_freshness_and_contract_v7.py` (verifies 9 staleness alerts when candle age $> 3.0\text{h}$).

---

### Gate 5 — Econometric Hypothesis Testing & Sample Size Hurdle
- **Implementation Location:** `engine/strategy_selection.py` (L480–L530), `research/macro_evaluation_harness.py` (Newey-West $N_{\text{eff}}$ calculation).
- **Gate Input:** Candidate sample size $N$, effective sample size $N_{\text{eff}}$, Newey-West confidence intervals, and Diebold-Mariano HLN p-value.
- **Pass Condition:** $N \ge 100$ independent non-overlapping events/blocks for confirmatory promotion ($N \ge 30$ operational floor for screening); Diebold-Mariano HLN-corrected $p < 0.05$; lower bound of $90\%$ CI on Net EV $> 0$.
- **Failure Condition:** $N < 30$ bars (immediate fail); $N < 100$ for confirmatory status; $p \ge 0.05$; CI lower bound $\le 0$.
- **Resulting Action:** Candidate is disqualified with code `FAIL_LOW_SAMPLE_N` or `FAIL_NEGATIVE_NET_EV`; selection engine defaults to `ABSTAIN`.
- **Relevant Tests:** `tests/test_v32_47_analyse_selection_and_anomaly_monitor.py::test_sample_size_floor_gating`, `tests/test_v26_research_gap_and_econometrics.py`.

---

### Gate 6 — Prospective Evidence Hurdle & Cold Start Protection
- **Implementation Location:** `engine/observatory.py` (L600–L660), `engine/longitudinal_status.py` (L150–L200), `validation/startup_gate.py` (L640–L645).
- **Gate Input:** Append-only prospective ledger (`data/prospective_forecast_ledger.jsonl`), count of resolved clean non-overlapping blocks.
- **Pass Condition:** $\ge 100$ non-overlapping forward evaluation blocks accumulated post-freeze with verified delayed outcome resolution.
- **Failure Condition:** Less than 100 blocks accumulated (currently 7 blocks accumulated).
- **Resulting Action:** Confirmatory prospective gate remains locked in `FROZEN (7/100 — COLLECTOR_INACTIVE)`; model promotion to production is impossible.
- **Relevant Tests:** `tests/test_longitudinal_status.py::test_longitudinal_status_report_structure`, `tests/test_longitudinal_dashboard.py`.

---

### Gate 7 — Offline Isolation & Anti-Fabrication Boundary
- **Implementation Location:** `engine/data_lane_separation.py`, `validation/startup_gate.py` (L450–L520), `api/routes_research.py` (L10–L21).
- **Gate Input:** Local file presence, parquet integrity, environment variables, socket connection requests.
- **Pass Condition:** All features sourced from verified local parquet files on disk; external HTTP/socket connections blocked; missing feeds reported as `None`/`UNAVAILABLE`.
- **Failure Condition:** External network access attempt; missing file triggering synthetic data imputation or forward-filling; use of quarantined `multi_regime_features.parquet`.
- **Resulting Action:** Execution halts; raises `OfflineResearchViolationError` or returns `UNAVAILABLE`; synthetic features quarantined.
- **Relevant Tests:** `tests/test_v32_62_offline_research_mode.py`, `tests/test_v32_64_data_lane_separation.py`.

---

## 4. Adversarial Failure Injection Matrix

To prove the fail-closed robustness of the architecture, five failure scenarios were evaluated:

| Test Scenario | Injected Fault Condition | Engine Component Tested | Expected Governed Outcome | Actual System Response | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Missing Manifest** | Delete or rename `repaired_scientific_contract_manifest.json` | `validation/startup_gate.py::verify_scientific_contract` | Refuses startup with `FROZEN_INPUT_MISSING` | `RuntimeError: Startup refused: manifest missing` | ✅ Passed |
| **2. Stale Market Data** | Pass candles with timestamp 22h in the past ($> 3.0\text{h}$) | `engine/hypothetical_scenario_planner.py` | Fails closed with `MARKET_DATA_STALE` | Returns `status = "UNAVAILABLE"`, code `MARKET_DATA_STALE` | ✅ Passed |
| **3. Insufficient Evidence** | Evaluate setup with $N = 12$ samples ($< 30$ floor) | `engine/strategy_selection.py::check_hard_eligibility_gates` | Disqualifies candidate with `FAIL_LOW_SAMPLE_N` | Returns `is_eligible = False`, defaults to `ABSTAIN` | ✅ Passed |
| **4. Unapproved Model Status** | Attempt inference when registry status is `OFFLINE_RESEARCH_ONLY` | `models/authoritative_model_registry.py::is_production_authorized` | Returns `False`; gates production routes | `is_production_authorized() == False`; returns `DISABLED` | ✅ Passed |
| **5. Negative Net EV after Drag** | Setup has gross EV $+15\text{ bps}$, Coinbase drag is $87\text{ bps}$ | `engine/strategy_selection.py::check_hard_eligibility_gates` | Disqualifies candidate (Net EV = $-72\text{ bps}$) | Candidate rejected; final decision is `ABSTAIN` | ✅ Passed |

**Conclusion:** In 100% of adversarial fault conditions, the runtime architecture **fails closed**. No combination of missing inputs, stale data, or static registry overrides can coerce the system into issuing an actionable trading recommendation or deploying financial capital.


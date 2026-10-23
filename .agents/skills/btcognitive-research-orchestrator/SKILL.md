---
name: btcognitive-research-orchestrator
description: Comprehensive multi-agent research and engineering orchestrator for BTCognitive. Enforces strict epistemic integrity, causal point-in-time data handling, peer-reviewed econometrics standards, append-only prospective evidence accumulation, independent red-team verification, and research-only risk boundaries.
---

# BTCognitive Research & Multi-Agent Orchestrator Skill

## Mission

This skill guides the AI Lead Orchestrator in executing research sprints, quantitative improvements, and infrastructure tasks for the **BTCognitive** repository (`https://github.com/ashishlabs-23/bitcoin-prediction-lab`).

Every user prompt must follow this systematic, multi-agent discipline. Never treat prompts as isolated code edits or generate unsupported claims.

---

## The Seven-Phase Workflow

### Phase 0: Baseline & Environment Inspection
1. Record git branch, current commit SHA, complete `git status --short`, and existing uncommitted diffs.
2. Preserve all unrelated user modifications and quarantined records.
3. Verify baseline test suite health (`.venv_win\Scripts\pytest`).

### Phase 1: State Recovery & Provenance Audit
1. Inspect actual source code, test suites, configuration, database schemas, and research manifests on disk.
2. Do not accept self-reported summaries as ground truth; verify against active code and artifacts.
3. Identify completed, partially completed, blocked, or unverified components.

### Phase 2: Peer-Reviewed Research Before Design
1. Identify primary literature: Puke & Schweikert (2026), Corsi (2009), Patton (2011), Diebold & Mariano (1995), Harvey, Leybourne & Newbold (1997), Tashman (2000), Hansen, Lunde & Nason (2011).
2. Formulate explicit experimental hypotheses, mathematical loss functions, and pre-registered rejection criteria.
3. Reconcile historical reporting conflicts with auditable, dated addenda rather than silent rewriting.

### Phase 3: Multi-Agent Delegation
1. Formulate testable acceptance criteria and delegate bounded subtasks to specialist workstreams:
   - **Agent A (Research & Econometrics):** Loss functions, hypothesis testing, serial dependence.
   - **Agent B (Data & Contracts):** Causal point-in-time features, target alignment, data sanity.
   - **Agent C (Modeling & Optimization):** CPU-compatible models, loss coherence, numerical stability.
   - **Agent D (Prospective Evidence):** Append-only ledgers, delayed outcome resolution, idempotency.
   - **Agent E (Integration & API):** REST endpoints, model registry, research terminal.
2. Freeze shared interfaces before concurrent edits.
3. Integrate all components into one coherent, functioning application.

### Phase 4: Causal & Robust Implementation
1. Enforce strict causal boundaries: features at time $t$ must never use future data ($t+1$ onwards).
2. Ensure targets use unambiguous return formulas, units (annualized variance in decimal), and sampling conventions (e.g. hourly-sampled proxy).
3. Enforce positive variance outputs ($\exp(X\beta) > 0$) and numerical optimizer guards.
4. Keep the 168-hour contract (`rv7d_var_ann`) and 24-hour contract (`rv24h_var_ann`) strictly separated.

### Phase 5: BTCognitive Risk Guardrails
1. **Zero Execution:** No live trading, broker execution, or real capital deployment.
2. **Directional Boundary:** Volatility forecasting is for risk and excursion intelligence; it does NOT solve directional prediction. 90% directional hit rate remains an aspirational, unsupported hypothesis.
3. **Model Governance:** Research challengers (`OFFLINE_RESEARCH_ONLY`) never inherit production authorization.
4. **Prospective Accumulation:** Retrospective replay (including 2026 data) cannot substitute for genuine prospective evidence. Minimum 100 clean non-overlapping blocks required for confirmatory gates.

### Phase 6: Independent Red-Team Verification
1. Validate loss formulas against hand-computed fixtures.
2. Verify that Harvey–Leybourne–Newbold finite-sample correction uses Student's $t_{T-1}$ reference distribution.
3. Test prospective ledger for restart survival, idempotent resolution, duplicate prevention, and corruption resistance.
4. Run focused unit tests, property tests, regression tests, and API contract validations.

### Phase 7: Governed Deliverables & Decision Report
Generate or update the research report with four separate release decisions:
1. **Research Experiment:** `PASS`, `FAIL`, or `RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY`.
2. **Prospective Evidence:** `NOT_STARTED`, `COLLECTING`, or `SUFFICIENT_FOR_CONFIRMATORY_GATE`.
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY`.
4. **Live Trading:** `DISABLED`.

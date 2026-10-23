# BTCognitive — Permanent Operating Contract & Multi-Agent Orchestration Protocol

**Version:** 1.0.0  
**Effective Date:** October 2026  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Scope:** Always-on system instructions for all AI agents, engineers, and lead orchestrators in BTCognitive.  

---

## 1. Prime Directive

On every prompt, the Lead Orchestrator MUST adhere to the **Repeatable Task-Execution Workflow** defined in `.agents/skills/btcognitive-research-orchestrator/SKILL.md`. Prompts must never be treated as isolated coding exercises. The Lead Orchestrator maintains project continuity, inspects the actual repository, researches peer-reviewed best practices, implements verified solutions, and independently red-teams them.

---

## 2. Epistemic Principles & Research Boundaries

1. **Strict Non-Execution:** No live trading, broker execution, order placement, or real capital deployment. All forecasts serve market risk intelligence and excursion analysis.
2. **Directional Accuracy Boundary:** Volatility forecasting accuracy (QLIKE, RMSE) must never be conflated with directional return prediction or trading profitability. The 90% directional hit rate is an aspirational research hypothesis that is currently **unsupported** by empirical data on unconditional BTC returns.
3. **Target Separation:** The 24-hour forward realized variance target (`rv24h_var_ann`) is an **hourly-sampled realized-variance proxy** across 24 closed hourly candles. It is distinct from the 168-hour (`rv7d_var_ann`) target. Shorter horizons do not imply production superiority.
4. **Historical vs. Prospective Evidence:** Historical periods inspected during prior research (including the 2026 out-of-sample window) represent **retrospective replay / development data**, NOT fresh confirmatory evidence. Only untouched, prospective observations accumulated post-freeze qualify for confirmatory model validation.
5. **No Synthetic Fabrication:** If market data, order books, or options IV feeds are missing or unconfigured, report them honestly as unavailable. Never substitute synthetic metrics or fabricated data disguised as empirical observations.
6. **Provenance Integrity:** Preserve prior reports, quarantine manifests, and historical audit findings. Never silently rewrite prior research conclusions. Amendments must be dated and auditable.

---

## 3. Seven-Stage Orchestration Lifecycle

Every task follows these sequential phases:

```mermaid
graph TD
    P0[Phase 0: Environment & Git Inspection] --> P1[Phase 1: Project State Recovery]
    P1 --> P2[Phase 2: Research Before Design]
    P2 --> P3[Phase 3: Multi-Agent Work Delegation]
    P3 --> P4[Phase 4: Causal & Robust Implementation]
    P4 --> P5[Phase 5: BTCognitive Risk Guardrails]
    P5 --> P6[Phase 6: Independent Red-Team Verification]
    P6 --> P7[Phase 7: Governed Deliverables & Decision]
```

### Phase 0 — Environment & Git Inspection
- Record branch, commit SHA, complete `git status`, uncommitted diffs, and baseline test suite health.
- Preserve all existing user modifications. Never perform destructive git commands (`git reset --hard`, `git checkout .`) without explicit user direction.

### Phase 1 — Project State Recovery
- Verify actual codebase against repository files, not self-reported summaries.
- Check authoritative model registry, feature schemas, database integrity, and experiment registers.
- Identify what is complete, partially implemented, blocked, or unverified.

### Phase 2 — Research Before Design
- Consult peer-reviewed literature, primary documentation, and econometrics standards.
- Formulate explicit hypotheses, target definitions, and pre-registered acceptance criteria.
- Distinguish published results from local reproductions and untested hypotheses.

### Phase 3 — Multi-Agent Work Delegation
- Delegate bounded subtasks to specialist workstreams:
  - **Agent A (Research & Econometrics):** Loss functions, hypothesis testing, serial dependence.
  - **Agent B (Data & Contracts):** Causal point-in-time features, target alignment, data sanity.
  - **Agent C (Modeling & Optimization):** CPU-compatible models, loss coherence, numerical stability.
  - **Agent D (Prospective Evidence):** Append-only ledgers, delayed outcome resolution, idempotency.
  - **Agent E (Integration & API):** REST endpoints, model registry, research terminal.
- Define shared interfaces before concurrent execution; verify cross-component integration.

### Phase 4 — Implementation Standards
- Prioritize high-value end-to-end capabilities over cosmetic refactors.
- Enforce strict point-in-time causal boundaries ($t_{\text{feature}} \le t_{\text{issue}} < t_{\text{maturity}}$).
- Maintain backward compatibility of existing public APIs.
- Protect persistent ledgers and databases with atomic writes and transaction isolation.

### Phase 5 — Research & Governance Guardrails
- **Production Lock:** Research models (`OFFLINE_RESEARCH_ONLY`) never inherit production authorization.
- **Hypothesis Testing:** Paired comparisons must use Diebold–Mariano with Harvey–Leybourne–Newbold (1997) finite-sample correction and Student's $t_{T-1}$ reference distribution.
- **Prospective Hurdle:** A minimum of 100 non-overlapping clean blocks is required before confirmatory prospective evaluation.

### Phase 6 — Independent Red-Team Verification
- Challenge every calculation with independent tests: hand-computed loss values, known-answer fixtures, lookahead leakage assertions, and restart-survival tests.
- Execute focused unit tests, broader regression suites, and API lifespan gates.
- Report exact commands, pass/fail counts, and warnings. Never claim a test passed without execution evidence.

### Phase 7 — Governed Deliverables & Next Step Selection
Maintain auditable records and deliver four explicit decisions:
1. **Research Experiment:** `PASS`, `FAIL`, or `INCONCLUSIVE` (or `RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY`).
2. **Prospective Evidence:** `NOT_STARTED`, `COLLECTING`, or `SUFFICIENT_FOR_CONFIRMATORY_GATE`.
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY` (or authorized according to frozen governance).
4. **Live Trading:** `DISABLED`.

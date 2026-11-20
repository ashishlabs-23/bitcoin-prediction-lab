# Prospective Shadow Evaluation Protocol V1.2 — Proposal for Human Review

**Status:** Proposal only; not approved, not effective, and does not amend frozen Protocol V1.1
**Governance tier:** `OFFLINE_RESEARCH_ONLY`
**Execution authorization:** `DISABLED — ANALYSIS ONLY`
**Target:** `HTF_RANGE_EXPANSION_BREAKOUT`
**Prepared:** 2026-10-23 as part of V31.0 research closure

## Purpose

Resolve the sample-unit, confirmatory-threshold, bootstrap, and benchmark ambiguities identified in V30.9 without changing V1.1 automatically. This proposal intentionally leaves the numerical confirmatory sample threshold **unset** until the estimand, dependence model, and precision/power analysis are approved. A count of 100 trade outcomes is not established as adequate by this proposal.

## 1. Evidence units and eligibility

1. A **candidate** is an immutable decision-time setup and is not a realized performance observation.
2. A **completed outcome** is one resolved candidate with a valid fill assumption and exit, measured after the decision and the full outcome window. Pending candidates are not counted.
3. A **confirmatory eligible outcome** must be prospective and post-freeze, tied to the frozen strategy/data contract, have a quality-approved resolution, and not be marked `GAP_EXCLUDED` or otherwise excluded by the approved policy.
4. In-position gating prevents overlapping exposure windows; it does not establish independent observations. The report must distinguish total eligible outcomes from any dependence-adjusted information estimate.
5. Candles, forecast-origin days, candidate setups, completed trade outcomes, calendar-time portfolio intervals, and bootstrap resampling blocks are separate units and must never be called “blocks” without a qualifier.
6. Historical replay and old 2026 observations are development evidence, not fresh prospective confirmation.

## 2. Confirmatory threshold: decision deferred

The former “100 non-overlapping clean blocks” wording is not carried forward as a trade threshold. It originated in a forecast protocol with horizon-spaced forecast origins; it does not specify a strategy-trade sample.

Before assigning a trade-outcome threshold, the protocol owner must approve:

- the primary estimand and target population;
- the minimum economically meaningful effect, in a single unit (proposed primary reporting unit: net basis points per eligible outcome under the frozen primary venue-cost scenario);
- the precision or power target and assumptions about outcome variance, serial dependence, event frequency, and exclusions;
- the confidence-interval procedure, one-sided/two-sided decision, alpha, and handling of repeated looks;
- simulation or analytical power/precision evidence showing how the proposed count behaves under plausible null and alternative processes.

Do not infer “adequate power” from a rule of thumb, non-overlap alone, an illustrative AR(1) autocorrelation, or the number of bootstrap replicates.

## 3. Stationary bootstrap

- \(E[L]\) is the expected geometric resampling-block length in **eligible outcome observations**, not a multiplier on the evidence count.
- Do not calculate a required sample as `100 × E[L]`.
- Freeze the method, segment construction, block-length selection rationale, sensitivity values, resample count, and interval type before confirmatory evaluation.
- Segment labels must reflect genuine contiguous eligible outcome sequences; missing/gap-excluded windows must not be bridged as if observations were adjacent.
- Report raw \(N\), eligible/excluded counts and reasons, and uncertainty. Any \(N_{\mathrm{eff}}\) estimate is descriptive unless its dependence estimator and assumptions are separately validated.

## 4. Estimand and benchmark alignment

### Primary strategy estimand (proposed)

Mean net return per eligible completed outcome for the frozen strategy, under the frozen and instrument-matched primary cost scenario. Report both basis points and net R as distinct measures; never combine them. The primary cost arithmetic, return denominator, fee timing, funding treatment, and fill assumptions must be explicit.

### Paired strategy comparison

Choose one primary comparison before evaluation:

- **Trade-matched excursion:** benchmark uses the same instrument and exact entry/exit timestamps for each eligible strategy outcome; or
- **Calendar-time portfolio:** both strategy and benchmark are sampled on one common calendar grid, include flat/cash intervals, and use the same return compounding and fee conventions.

These answer different questions. One is not a substitute for the other; a non-primary alternative may be reported as a sensitivity analysis.

Use DM-HLN only when both series are aligned observations of the same preregistered target/loss at a common horizon and the long-run variance estimator is appropriate. A variable-duration trade-return comparison is not automatically a forecast-loss DM test. If these requirements do not hold, use the approved paired bootstrap/interval method and label the estimand accordingly.

For DM-HLN, freeze the loss differential sign, horizon, HAC/long-run variance estimator, lag treatment, HLN correction, sample size \(T\), tail, and reference distribution. For a one-step forecast comparison, the small-sample factor is \(\sqrt{(T-1)/T}\) with Student's \(t_{T-1}\); specifying that factor alone does not establish a valid comparison.

## 5. Costs and instrument compatibility

- The primary cost scenario applies only to its named venue and product. Spot BTC-USD and BTCUSDT perpetual returns/fills are not interchangeable.
- Separate documented fees from estimated spread, slippage, adverse selection, funding, and fill probability.
- Treat maker outcomes as scenarios unless time-stamped order-book/trade data can support queue and fill modeling. Do not assign a successful maker fill solely because a historical bar touched a limit.
- Include pessimistic/base/optimistic sensitivity without selecting the best scenario after seeing the holdout.
- Do not fabricate unavailable quote, funding, or fill observations. Report missing inputs explicitly.

## 6. Interim monitoring and stopping

- Keep the existing 50-outcome negative-expectancy/drawdown rule, if approved by the protocol owner, as a **safety pause** only. A pause is not a confirmatory rejection or success decision.
- Define drawdown on an explicitly specified equity series, return unit, starting capital convention, and handling of flat periods.
- Predefine interim review times and either an alpha-spending/sequential method or state that no efficacy conclusion is permitted at interim looks.
- Test both pause branches (expectancy and drawdown), boundary values, missing/invalid outcomes, and restart persistence.
- Freeze any futility rule and require a valid upper confidence bound; do not infer futility from a point estimate alone.

## 7. Multiplicity, meta-models, and selection

- Register every candidate, feature set, barrier setting, model, cost case, and tried configuration before analyzing holdout results.
- Perform feature selection, preprocessing, hyperparameter search, and calibration inside chronological training folds only. Purge/embargo overlapping labels and retain one final untouched holdout.
- Apply a predeclared multiplicity policy to the full strategy/model comparison family.
- Use PBO/CSCV or Deflated Sharpe only when the number and structure of trials and partitions satisfy the method's assumptions; report inputs and limitations. These methods do not repair leakage or a mislabeled dataset.
- A higher win rate is not a sufficient criterion. Report incremental net expectancy, uncertainty, calibration, drawdown, turnover, exposure, and abstention versus the frozen baseline and zero exposure.

## 8. Confirmatory gate implementation and audit trail

Until V1.2 is formally approved and an automated/manual gate is specified, status must remain **`BLOCKED — PROTOCOL CLARIFICATION REQUIRED`**. The gate must not infer approval from an empty or malformed ledger, from tests alone, or from a candidate count.

After approval, the gate report should include:

- protocol/version hash and frozen strategy specification hash;
- input/source/config hashes and venue/product identity;
- eligible resolved outcome count, pending candidates, exclusions/reasons, and collection period;
- estimand, cost model, CI method, dependence assumptions, and every interim look;
- the preregistered decision criteria and exact calculation outputs;
- independent test evidence for formula fixtures, gap handling, duplicate prevention, restart survival, and gate decisions.

Amendments must be dated and append-only. Preserve V1.1 and earlier reports unchanged.

## 9. Required approval before effectiveness

The protocol owner must resolve the threshold/precision analysis, estimand and benchmark choice, primary venue-cost schedule, repeated-look rule, and implementation/test responsibilities. No automatic V1.1 replacement, live-trading authorization, or deployment follows from this proposal.

## V31.1 addendum — decision matrix for human review (2026-10-23)

This dated addendum does not amend frozen V1.1 and is not an approval of V1.2. The detailed decision matrix is in `protocol_v1_2_decision_matrix_v31_1.md`. Its provisional recommendation is to use common-window calendar-time net return difference for the primary strategy-performance estimand, with trade-level net R and barrier/excursion summaries as secondary descriptive measures. The protocol owner must approve the benchmark, allocation and exposure contract, minimum relevant effect, uncertainty method, dependence assumptions, and interim-look policy before any confirmatory gate is implemented.

No trade count, block count, or effective sample-size threshold is adopted. A bootstrap expected block length is a resampling/dependence parameter, not a sample-size multiplier. DM-HLN is not proposed as a generic test for variable-duration trade returns; it is reserved for a separately specified, aligned forecast-loss estimand. V1.1 and this proposal remain unchanged in authority until explicit human approval.

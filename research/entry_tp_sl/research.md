# BTCognitive — Entry + TP/SL Research Plan v3 (Red-Teamed)

**Status:** RESEARCH PLAN — **NOT READY FOR MODEL TRAINING** (Gate G0 must pass first; see §0.2)  
**Date:** 2026-10-07  
**Supersedes:** v2 (same date)  
**Scope:** BTC perpetual/spot intraday decision research, 15-minute decision cadence, 1-minute (or finer) path resolution  
**Primary objective:** Build and test a selective, cost-aware system that proposes an entry, side, TP and SL, and can abstain. A **negative result is an acceptable and fully reportable outcome.**

---

## Part I — Red-Team Review of v2

v2 is a strong skeleton. It was reviewed for internal contradictions, statistical loopholes, execution-realism gaps, process gaps, and worst-case behavior. Findings are ranked **S1 (invalidates results) → S3 (weakens results)**. Each is resolved in Part II.

### I.1 Contradictions and structural defects

| ID | Sev | Defect in v2 | Resolution (v3 §) |
|---|---|---|---|
| D1 | S1 | Status says "READY FOR IMPLEMENTATION" while §0 admits: missing `iv7d.parquet`, changed OHLCV hash, numeric drift, unreconciled freeze manifests, **repo-wide pytest stalled at 73%**. A plan cannot be "ready" on a foundation with no trustworthy test result. | §0.2 Gate G0 |
| D2 | S1 | "Stage B" is used twice (triple-barrier labeling AND meta-model). Phase numbers (6A–6J) and stage letters (A–E) are not mapped to each other. Ambiguity in a contract document is a researcher degree of freedom. | §2 renamed stages, §28 mapped |
| D3 | S1 | **Barrier grid vs. one model.** The meta-labeler is trained for "a fixed barrier contract" but Stage C evaluates P(TP first) over a grid of pairs. v2 never says whether this is K models, or barriers fed as features. Barriers-as-features lets the model interpolate geometry it never saw and makes P non-monotone in TP width. | §7.3 |
| D4 | S1 | **Optimizer's curse / winner's curse.** Picking the barrier pair with the highest *predicted* net EV from a grid selects the pair with the largest positive prediction error. Reported expectancy will be upward-biased even on clean out-of-sample data unless selection is evaluated on data the selector never saw. | §8.2 |
| D5 | S1 | **Label asymmetry.** `y=1 if TP_FIRST else 0` lumps TIMEOUT with SL_FIRST. P(TP first) is not comparable across geometries (different TP/SL ratios change base rates), and TIMEOUT is *not* a loss of 1R — it exits at market with a signed, cost-bearing P&L. A classifier on this label cannot give net EV without extra assumptions. | §7.2 |
| D6 | S1 | **Dependency on a blocked component.** The plan says the research path "must use the existing `resolution_service`" — the same stack with unreconciled manifests and legacy endpoints. | §6.1, G0 |
| D7 | S2 | **Foundation-model facts are time-stamped claims presented as settled** (release months, layers, license text). They can be stale or wrong by implementation time, and Phase 6J happens months later. | §14 |
| D8 | S2 | Claim ladder order is odd: C5 (prospective) precedes C6 (selection-adjusted). Selection adjustment is a *precondition* for interpreting anything, not a later step. "Positive" is never numerically defined. | §26 |
| D9 | S2 | "BTCUSD/BTCUSDT" treated as one thing. Inverse (BTC-margined), linear USDT perp, and spot have different P&L math, funding, basis, margin, and liquidity. | §3.1 |

### I.2 Statistical loopholes

| ID | Sev | Loophole | Resolution |
|---|---|---|---|
| L1 | S1 | **Setup detector is a hidden hyperparameter space.** Sweep lookback, pierce threshold, reclaim definition, range window, range-break tolerance, re-entry rule: each is a researcher degree of freedom. v2 only counts "experiments tried" for models, not detector variants. | §4.3 frozen detector spec; every variant counts as a trial |
| L2 | S1 | **Event overlap / concurrency.** Consecutive 15-min bars frequently all trigger the same sweep. Labels overlap, trades overlap, and the effective N collapses. v2 mentions "effective N" but gives no mechanism (no uniqueness weights, no one-position rule, no cluster definition). | §5.4, §19 |
| L3 | S1 | **Statistical power is not checked against feasibility.** A rough calc (below) shows the prospective stage is likely infeasible at realistic trade frequency. | §19.2, §24 |
| L4 | S1 | **Pretraining contamination of foundation models.** Chronos-2 / TimesFM / Toto / Kronos may have seen BTC history that overlaps your test or holdout window. Any "edge" in that overlap is leakage. v2 does not require test windows to postdate the checkpoint's training cutoff. | §14.3 |
| L5 | S1 | **Holdout contamination by prior work.** The HAR-RS-DOW program and the previous MFE/MAE plan already examined BTC data. If the "sealed" holdout period overlaps any period previously inspected, it is not sealed. | §25 |
| L6 | S2 | **Beta masquerading as alpha.** BTC has strong drift and regime trends. A long-biased setup in a bull sample "beats" random entry. B0 randomizes timestamps but not necessarily side/exposure. | §13 B0 matched design + beta-neutral report |
| L7 | S2 | **Abstention selection bias.** Evaluating only on accepted trades with a tuned threshold overstates performance. Coverage–expectancy tradeoff must be shown across the *whole* threshold range, with the threshold frozen on validation only. | §12.2 |
| L8 | S2 | **Single primary hypothesis only vs. B3.** Beating a fixed ATR rule is not enough: the setup+meta-model may merely beat a weak baseline while losing to "setup, all candidates, no model" or to costs alone. | §18.1 gated comparison chain |
| L9 | S2 | **DSR/PBO assume enough trials and independent-ish returns.** With few trades per config, DSR is unstable; PBO via CSCV needs many comparable configs. Neither is a magic fix. | §18.3 + block bootstrap + SPA test |
| L10 | S2 | **Calibration leakage.** Calibrator fit on the same fold the threshold is tuned on, with overlapping labels, produces optimistic reliability curves. | §12.1 three-way split |
| L11 | S2 | **Regime subgroup fishing.** §23 asks for many subgroup analyses (vol × trend × session × setup). Without correction this guarantees some "significant" cell. | §23 subgroup analyses are descriptive unless pre-registered |
| L12 | S3 | LightGBM overfits tiny event sets; feature importance is treated as informative. | §7.4 |
| L13 | S3 | Profit factor and Sharpe are outlier-sensitive and ill-defined with few trades. | §21 CI via block bootstrap |

### I.3 Execution / data realism gaps

| ID | Sev | Gap | Resolution |
|---|---|---|---|
| E1 | S1 | **15-minute OHLC cannot resolve TP/SL order for tight barriers.** With intraday-vol-scaled barriers, same-bar double touches can be a large fraction of events. Tie-break policy then *is* the result. | §6.3: resolve on 1-min (or tick) data; 15-min only for decisions |
| E2 | S1 | **Decision latency ignored.** "Decide at closed bar, fill at next executable price" assumes zero compute + network delay. Features (OFI, VPIN, book imbalance) at bar close are not instantly available. | §10.2 explicit latency parameter |
| E3 | S1 | **Derivatives/microstructure data publication lag.** Funding, open interest, liquidation, and book snapshots are often sampled at irregular intervals, backfilled, or revised. Using the final historical value at `t0` is lookahead. | §9.1 point-in-time (PIT) feature store requirement |
| E4 | S2 | Maker/limit entries have adverse selection and non-fill bias. "Limit entry at structural level" will look great if non-fills are dropped (fills occur disproportionately when price keeps going against you). | §3.2 |
| E5 | S2 | **Stops fill with gaps/slippage;** liquidation price vs. SL distance under leverage is not modeled; exchange outages, ADL, auto-deleveraging, and funding timestamps are absent. | §10 |
| E6 | S2 | **Cost-to-barrier ratio.** If round-trip cost is a large fraction of the TP/SL distance, break-even win probability is high and the edge requirement is implausible. v2 never states the break-even formula or a feasibility gate. | §9.2 |
| E7 | S2 | **Timezones / bar labeling.** Bar open-time vs. close-time stamps differ by vendor; "session" definitions in local time introduce DST artifacts. | §9.1 |
| E8 | S2 | **Regime breaks.** ETF-era microstructure, halving cycles, and venue changes make old data a different market. | §19.4, §20 |
| E9 | S3 | Numeric-runtime drift already observed in the repo threatens determinism claims. | §15.2 |

### I.4 Process and governance gaps

| ID | Sev | Gap | Resolution |
|---|---|---|---|
| P1 | S1 | **No numeric success or kill criteria.** "Positive, robust, selection-adjusted" is unfalsifiable until thresholds are fixed. | §0.3 |
| P2 | S1 | **No go/no-go gates between phases.** v2 runs 6A→6J linearly; sunk cost pushes the project to continue a dead idea. | §28 gates |
| P3 | S2 | **No "who guards the holdout" mechanism** — policy only, no technical control. | §25 |
| P4 | S2 | **No position-lifecycle failure policy.** "Fail closed" works for *entering*. If the system has an open position and loses data/model/connection, "abstain" is not a safe action. | §11.3 |
| P5 | S2 | Single-point-of-truth resolver is good, but no *independent* verification of it. | §6.1 differential oracle |
| P6 | S3 | No compute/time budget, no data licensing check, no owner/roles. | §0.4 |

---

## Part II — Revised Plan (v3)

## 0. Relationship to Previous Work, Gates, and Kill Criteria

### 0.1 Separation rule

Do not convert the 7-day annualized realized-variance (HAR-RS-DOW) contract into a 15-minute entry/TP/SL contract. This is a **new research track** with its own target, dataset snapshot, provenance, model versions, and evaluation protocol. The HAR product path remains `CANONICALIZATION_BLOCKED` and is **out of scope** here.

### 0.2 Gate G0 — Foundation Integrity (blocks everything)

No model training, no detector tuning, no baseline results until all are true:

1. **Isolated research environment** with locked dependency file (hashes), pinned Python/NumPy/LightGBM versions, and a numeric tolerance policy (see §15.2).
2. **Research-track dataset snapshot** created fresh (own hash, own manifest). It must **not** reuse the changed-hash OHLCV source or any artifact from the blocked HAR path.
3. **`iv7d` and any IV-derived feature are excluded** until their provenance is repaired. No imputation, no proxy.
4. **Test-suite triage:** the stalled repository-wide pytest run is root-caused (identify the hanging test via per-test timeouts, e.g. `pytest --timeout` + `-p no:randomly` bisect), quarantined with a documented reason, and the new `tests/entry_tp_sl/` suite runs **independently and completes** in CI.
5. **Resolver decision recorded:** either (a) reconcile `resolution_service` and re-freeze, or (b) write a versioned research resolver and run a differential test against it (§6.1). The decision, hash, and date are committed.
6. **Data-rights check:** license for every data source and for each foundation-model checkpoint is recorded.

### 0.3 Pre-registered success and kill criteria (fill numeric values at G1; no change afterward)

| Item | Definition |
|---|---|
| Minimum economically meaningful effect | `E_min` = net expectancy ≥ **X R per trade** after the conservative cost scenario (suggested starting point: 0.05–0.10 R) |
| "Positive" | Lower bound of one-sided **95% block-bootstrap CI** (or Holm-adjusted) of net expectancy > 0 **and** point estimate ≥ `E_min` |
| Futility stop | If at the pre-registered interim look the upper CI bound < `E_min`, or setup yield is below `N_min`, **stop the track** and publish the negative result |
| Cost feasibility stop | If median round-trip cost / SL distance exceeds **C_max** (suggested 0.25) for the candidate barrier grid, drop that grid |
| Time/compute budget | Max wall-clock and GPU/CPU hours per phase; exceeding triggers review, not silent extension |

### 0.4 Roles

Even for a solo project, name: **Researcher** (builds), **Auditor** (separate review pass or script that checks pre-registration vs. code), **Holdout custodian** (controls holdout key; may be an automated hash-lock + access log).

---

## 1. Research Question

Given only information available at decision time `t0` (including realistic data and compute latency), can BTCognitive identify a selective BTC trade for which the chosen side, entry, TP and SL have **positive net-of-cost expectancy on unseen data**, beyond what (a) random entry, (b) the rule alone, and (c) costs/beta alone explain?

Not: exact price prediction; 90% accuracy; MFE/MAE regression as the final target; a model that trades every bar.

Allowed outputs: `NO_SETUP`, `ABSTAIN`, `UNAVAILABLE` (and the reasons in §12.3).

---

## 2. Decision Architecture (stage letters renamed to avoid collision)

```text
MARKET DATA (point-in-time)
   │
   ▼
S0  FEATURE SNAPSHOT @ t0  (+ latency stamp)
   │
   ▼
S1  SETUP DETECTOR (rule-based; owns the side hypothesis)
   ├─ NO SETUP ─────────────► ABSTAIN
   ▼
S2  META-MODEL (accept/reject the proposed side)
   ├─ LOW/UNCERTAIN ────────► ABSTAIN
   ▼
S3  BARRIER SELECTION (pre-registered grid + frozen rule)
   ▼
S4  COST + EXECUTION FILTER (incl. break-even feasibility)
   ├─ FAIL ─────────────────► ABSTAIN
   ▼
S5  SIZING / RISK / ACCOUNT-LEVEL CONSTRAINTS
   ▼
TRADE CONTRACT ──► POSITION LIFECYCLE MANAGER (§11.3) ──► CANONICAL R_t
```

The setup detector owns the side. The meta-model decides whether (and later how strongly) to act. It never flips the side in the first build.

---

## 3. Entry Definition

### 3.1 Instrument freeze

Choose **one** instrument/venue contract for the primary experiment (e.g., linear USDT perpetual on venue V). Record: contract type (linear/inverse/spot), margin mode, tick size, fee schedule version, funding interval and timestamp convention. Other instruments are separate experiments. For USDT-quoted products, record the USDT/USD basis as a risk note.

### 3.2 Entry convention (frozen)

- Decision on a **closed** 15-minute bar.
- Fill model: marketable order at **next 1-minute bar open + modeled latency and slippage** (primary). Latency parameter `Δ_lat` is explicit (e.g., 1–5 s data + compute + network), and the fill price uses the first executable price at or after `t0 + Δ_lat`.
- **Limit/retest entries are a separate later factor** and must model **non-fill**: report fill rate, and count non-fills as "no trade" *with* the opportunity cost explicitly analyzed, never silently dropped. Adverse-selection must be measured (fills conditional on price trading through the limit).

---

## 4. Setup Detector (S1)

### 4.1 Families

- A1 Liquidity Sweep / Reclaim
- A2 Range Reclaim

### 4.2 Constraints

Causal, observable at `t0`. `sweep_candidate` stays observational (not "absorption"). No BOS/CHoCH, FVG, VWAP, order blocks, candlestick libraries, or learned patterns in the first build.

### 4.3 Frozen detector specification (new)

Before any outcome is looked at, write and hash a **detector spec**:

- exact lookback windows (bars), pivot definition, pierce threshold (in ATR or ticks), reclaim definition (close beyond reference by ≥ δ), range definition (window, percentile or high/low), re-entry confirmation rule;
- **cooldown** between setups of the same family/side;
- **deduplication rule** (§5.4);
- allowed value grids for any parameter that is tuned (each tested value counts as a trial).

Detector parameters may be tuned **only** on the training window, and every tuned variant increments the trial counter.

---

## 5. Triple-Barrier Labeling

### 5.1 Outcome states

`TP_FIRST`, `SL_FIRST`, `TIMEOUT`, plus `UNRESOLVED_INTRABAR` and `DATA_GAP` as explicit non-outcomes with pre-registered handling.

### 5.2 Record per candidate

`entry_timestamp`, `entry_price (simulated fill)`, `side`, `TP barrier`, `SL barrier`, `vertical barrier`, `first_touch_timestamp`, `touch_price`, `resolution_state`, `exit_fill_price (simulated)`, `net_R`, `execution_cost_metadata`, `detector_spec_hash`.

### 5.3 Barrier construction

`TP = k_tp × σ_t0`, `SL = k_sl × σ_t0`, with σ causal and computed from bars **strictly ≤ t0** (never including the entry bar). Benchmark ATR, realized vol, EWMA vol as a *pre-registered* factor, not post-hoc choice. Structural stop extension (`SL = structural ± c·σ`) is a later factor with `c` frozen before its test.

### 5.4 Overlap and uniqueness (new)

- **One open position per instrument** in the primary backtest; candidates generated while a position is open are logged but not traded.
- Define an **opportunity cluster**: setups of the same side within `W` bars (pre-registered) form one cluster; statistical inference uses cluster-level outcomes (first eligible setup only, pre-registered).
- Compute **average uniqueness weights** (López de Prado) for model training; report effective N = Σ uniqueness.
- Purge/embargo must cover **label horizon + cluster window**.

---

## 6. Resolution Semantics

### 6.1 Single authority + independent oracle

The canonical resolver is the sole production authority for realized outcomes. Additionally:

- Implement a **slow, simple reference resolver** (pure Python loop, no vectorization) used only in tests. Property-based tests (Hypothesis) generate random paths and require canonical == reference for all inputs. This catches vectorization bugs the fixtures miss.
- No separate TP/SL logic may exist in model, backtest, reporting, or UI code. Add a **static test** that greps/AST-checks for forbidden duplicate barrier comparisons outside the resolver module.

### 6.2 Required edge-case fixtures

All of v2's 11 cases, plus: gap through barrier (open beyond TP/SL), barrier exactly at entry price, zero/negative distance after rounding to tick size, timeout bar equality, DST/clock-change day, partial-bar at data end, bar with `high<low` or NaN, and **negative-price/zero-volume** corrupted bars (must fail closed).

### 6.3 Resolution data resolution

Decisions use 15-minute features; **path resolution uses 1-minute bars minimum** (tick/aggTrade if available). Tie handling:

- `OBSERVED_ORDER` when sub-bar sequence is determinable.
- `UNRESOLVED_INTRABAR` → **pre-registered conservative policy: SL-first** for the primary result.
- Always publish the **ambiguity rate** and the TP-first sensitivity. If conclusions flip between policies, the result is classified **non-robust** (C4 not achieved).

---

## 7. Meta-Labeler (S2)

### 7.1 Inputs

Proposed side, causal feature snapshot (PIT only), setup metadata (family, age of sweep, distance), volatility regime, session, microstructure (OFI, impact, VPIN, book imbalance), derivatives context (funding, OI) **only if PIT-verified**, optional probabilistic volatility features.

### 7.2 Targets (revised)

Primary: **net outcome in R** under the conservative cost scenario, with a three-class auxiliary `{TP_FIRST, SL_FIRST, TIMEOUT}` model. Decision EV is computed as:

```text
EV_net = p_TP · R_TP_net + p_SL · R_SL_net + p_TO · E[R_TO_net | timeout]
```

where `R_*_net` include costs and slippage, and `E[R_TO_net]` is estimated from timeout outcomes (not assumed 0, not assumed −1). Binary `TP_FIRST vs. rest` is retained only as a diagnostic and for comparison with v2.

### 7.3 One model per barrier pair (not barriers-as-features)

For a small grid (≤ 9 pairs), train **separate models per pair** (or one multi-output model with identical features and a pair-index treated as a categorical *only if* validated against separate models). Reason: avoids the model extrapolating geometry and keeps each probability interpretable. Every model counts as a trial.

### 7.4 LightGBM discipline

- Fixed hyperparameter search budget (e.g., ≤ 30 configs) logged in the trial counter.
- Shallow trees, strong regularization, `min_child_samples` tied to **effective N**, early stopping on a purged validation fold only.
- Monotone constraints where economically defensible and pre-registered.
- `deterministic=True`, `force_row_wise=True`, fixed seeds, fixed thread count.
- Feature importance/SHAP is **descriptive**, never evidence of edge.
- Compare against a **regularized logistic regression** with the same features (B4-lite) — if GBM does not beat it out-of-sample, prefer the simpler model.

---

## 8. Barrier Selection (S3)

### 8.1 Grid

Pre-registered grid (e.g., `k_tp ∈ {a,b,c}`, `k_sl ∈ {d,e,f}`), horizon fixed.

### 8.2 Selection without winner's curse

- The **selection rule** (argmax EV_net subject to constraints) is frozen.
- Selection performance is evaluated in a **nested** manner: the grid choice for a fold is made using only data prior to that fold, then evaluated on the fold. Report the realized-minus-predicted EV gap (**optimism gap**); a large positive gap invalidates the selector.
- Also report the **fixed single best pair** and the **median-pair** performance as controls; the selector must beat the median pair out-of-sample.
- Apply **shrinkage** to predicted EV (e.g., subtract a pre-registered multiple of its standard error) before argmax.

### 8.3 Constraints in the rule

Minimum EV margin over cost, minimum reward/risk geometry, **break-even feasibility** (§9.2), execution viability, maximum adverse move, size/margin constraints, maximum holding time.

---

## 9. Net-of-Cost Decision Rule

### 9.1 Point-in-time data and cost inputs

- **PIT feature store:** each feature stored with `event_time` and `available_time`. Training/backtest joins use `available_time ≤ t0 + Δ_lat`. A test fails if any feature has `available_time > decision time`.
- All timestamps UTC, bar-label convention (open vs. close time) documented and tested; sessions defined in fixed UTC windows.
- Costs parameterized by venue, tier, maker/taker, side, order type, spread, vol-shock state, size, holding duration, funding. No universal "8–10 bps" constant.

### 9.2 Break-even gate (new)

For long with TP distance `T`, SL distance `S`, round-trip cost `C` (all in price units or R):

```text
p_breakeven (ignoring timeout) = (S + C) / (T + S)
```

Require `p_model_lower_bound > p_breakeven + margin`, where the lower bound comes from the calibrated model uncertainty. Log the distribution of `C/S` per candidate; drop barrier grids violating `C/S ≤ C_max`.

### 9.3 Cost scenarios

Three pre-registered scenarios, **conservative is primary**: optimistic / base / conservative (stop slippage as a multiple of normal slippage, taker both sides, stressed spread). Promotion requires positive expectancy at the conservative scenario.

---

## 10. Execution Reality

### 10.1 Components

Entry: expected fill, spread, slippage. Exit: TP fill (maker/taker, may not fill when merely touched), SL adverse slippage (higher in shocks). Hold: funding **at actual funding timestamps** (a position open across the stamp pays; one closed before does not). Market impact: size-dependent.

### 10.2 Latency

Explicit `Δ_lat` for data + compute + order transit; sensitivity grid (e.g., 0.5 s, 2 s, 10 s, 60 s). If edge disappears at plausible latency, it is not executable.

### 10.3 Leverage, margin and tail mechanics

Model liquidation price vs. SL distance (SL must be reachable before liquidation with a buffer), maintenance margin, ADL risk, exchange outage/halt scenarios, weekend/thin-liquidity spreads, and **gap-through-stop** events (fill at worse than trigger). Barrier touch price and simulated fill price are always separate fields.

---

## 11. Sizing, Risk, and Lifecycle

### 11.1 Sizing

Fixed-fraction-of-risk primary; vol-targeted challenger; fractional Kelly later. Sizing may not rescue a negative-expectancy signal: **the pre-sizing (1R-per-trade) expectancy must itself be positive** before any sizing result is reported.

### 11.2 Limits

Max risk/trade, max concurrent exposure, daily loss limit, consecutive-loss guard, kill switch, **max drawdown stop** (account-level, pre-registered).

### 11.3 Position lifecycle failure policy (new)

"Abstain" is not a safe action when a position is open. Pre-register behavior for: data feed loss, model failure, resolver error, exchange API failure, clock skew, and kill-switch activation:

- **Flatten policy** (market close at best available) vs. **hold-with-exchange-side stop** (stops live on the exchange, not in the bot). Primary: exchange-side bracket orders where supported.
- Heartbeat/watchdog; stale-data threshold; maximum time without confirmation.
- Paper trading with **live fills comparison** (simulated vs. actual) before any capital, and a separate approval.

---

## 12. Calibration and Abstention

### 12.1 Data splits for calibration

Three disjoint, time-ordered blocks inside training history: **train → calibrate → threshold-select**, with purge/embargo between each. The holdout never touches any of them. Re-calibrate only as part of a new model version.

### 12.2 Diagnostics

Brier, log loss, reliability curve, calibration intercept/slope (with CIs via block bootstrap), ECE with documented binning, precision/recall at threshold, coverage. Show the **full coverage–expectancy curve** over thresholds, not only the selected point; the threshold is frozen from validation. Report results for **all candidates** (no abstention) alongside accepted trades so selection effects are visible.

### 12.3 Abstention codes

`NO_SETUP`, `MODEL_UNCERTAIN`, `EV_BELOW_COST`, `EXECUTION_UNSAFE`, `RISK_LIMIT`, `DATA_UNAVAILABLE`, `PROVENANCE_FAILURE`, `MODEL_FAILURE`, `LATENCY_EXCEEDED`, `BREAKEVEN_INFEASIBLE`.

---

## 13. Baselines

| ID | Baseline | Notes |
|---|---|---|
| B0 | **Matched random entry** | Same eligibility, barriers, horizon, costs, sizing, **and matched on side distribution, time-of-day, volatility regime, and cluster rules.** Run also with *random side* and with *same side as setup* to separate side skill from timing skill |
| B0b | **Always-long / always-short at same frequency** | Quantifies BTC drift/beta |
| B1 | Volatility-only | Fixed geometry |
| B2 | EWMA/GARCH vol-scaled barriers; HAR-RV only when the target is RV | |
| B3 | Fixed structural/ATR rule, same setup, **no model** | Equivalent to "take all candidates" |
| B3b | **Setup + trivial filters** (e.g., session filter only) | Shows whether ML adds beyond simple rules |
| B4-lite | Regularized logistic regression meta-model | |
| B4 | LightGBM meta-model | First learned challenger |
| B5+ | Foundation-model features | Only after B0–B4 are clean |

Also report a **beta-neutral** view: long and short legs separately, and performance with and without the strongest trending months.

---

## 14. Foundation-Model Policy

### 14.1 Status

Challengers/features only. Not decision makers.

### 14.2 Verification as an artifact, not prose

v2's model facts (TimesFM 3.0, Toto 2.0, Chronos-2, Kronos: release dates, sizes, licenses, covariate support) are **as-of v2 claims**. Before Phase 6J, create `model_verification.json` per model with: source URL, commit hash/checkpoint ID, access date, license text hash, declared training-data cutoff (if any), supported features (covariates, multivariate, fine-tuning), and who verified it. Anything unverified is excluded. Re-verify at use time.

### 14.3 Pretraining-contamination rule (new)

Any evaluation window (including holdout and prospective) for a foundation model **must be strictly after the checkpoint's documented training cutoff**. If the cutoff is undocumented, treat the model as **contaminated for all historical windows**: it may only be evaluated **prospectively**. Kronos' public BTC demo and the pretraining on exchange K-lines are explicitly a contamination risk for any historical BTC backtest.

### 14.4 Licensing

TimesFM 3.0 weights (non-commercial license per v2): research only, no production. Re-read the actual license text before use. Apache/MIT components still require attribution compliance.

### 14.5 Test design

Use as features (forecast quantiles, predicted vol) and ask whether they add information **beyond** realized-volatility features via nested model comparison, with compute/latency cost reported (a 15-minute strategy cannot depend on a model that takes minutes to run).

---

## 15. Pytest and Determinism

### 15.1 Layers

Software correctness (pytest) ≠ research evidence. Pytest cannot move a claim up the ladder.

### 15.2 Determinism

- Locked environment; record BLAS/thread settings; LightGBM deterministic flags.
- **Tolerance policy:** exact equality for labels and accounting integer-math (use integer ticks/satoshis or `Decimal` for P&L); defined `rtol/atol` for model probabilities; decision payloads must match after rounding to a frozen precision.
- Replay test across two clean environments (container rebuild) to catch the numeric-runtime drift already observed in the repo.

### 15.3 Required tests (v2 list plus)

- Property-based resolver vs. reference oracle (§6.1).
- PIT feature availability test (§9.1).
- **Shuffle test:** shuffling labels within time blocks must collapse performance to ≈ cost-adjusted zero (catches hidden leakage).
- **Time-shift test:** shifting features forward by one bar must *change* results; an unexpected improvement indicates lookahead.
- **Placebo setups:** run the detector on time-reversed or randomly relocated events; edge must vanish.
- Split-integrity with purge = label horizon + cluster window.
- Marker discipline: `-m "not backtest"` fast; `-m backtest` slow; per-test timeouts mandatory (the stalled-run lesson).

### 15.4 Failure behavior

Fail closed: `DATA_UNAVAILABLE`, `PROVENANCE_FAILURE`, `MODEL_FAILURE`, `NO_SIGNAL`. No numeric fallback. (Open positions follow §11.3.)

---

## 16. Proposed Repository Layout (additions to v2)

```text
research/entry_tp_sl/
  barrier_contract.py   triple_barrier.py   reference_resolver.py   (test-only oracle)
  setup_detector.py     detector_spec.py
  pit_features.py       meta_labeler.py     barrier_selector.py
  execution_model.py    cost_scenarios.py   lifecycle.py
  backtest_runner.py    evaluation.py       preregistration.py   trial_ledger.py
tests/entry_tp_sl/
  (v2 tests) + test_reference_oracle.py  test_pit_availability.py
  test_placebo.py  test_shuffle_leakage.py  test_time_shift.py
  test_cluster_uniqueness.py  test_lifecycle_failure.py  test_cost_feasibility.py
```

**`trial_ledger.py` (new):** append-only, hash-chained log of every detector variant, feature set, hyperparameter config, barrier pair, threshold, and model version tried. Source of truth for `N_trials` in DSR/PBO.

---

## 17. Cross-Validation

Walk-forward + purging + embargo. Purge window ≥ max(label horizon, cluster window, feature lookback leakage). For selection-heavy stages add Combinatorial Purged CV. Random splits prohibited. Report fold-by-fold results; a single aggregated number hides regime failure.

---

## 18. Multiple Testing and Inference

### 18.1 Gated comparison chain (primary hypotheses, closed testing order)

All must hold, tested in this fixed order (fixed-sequence procedure, no alpha spent twice):

1. Setup rule (B3) net expectancy > matched random (B0) — *does the setup carry timing information?*
2. LightGBM meta-model (B4) > B3 — *does the model add value over taking all candidates?*
3. B4 > B4-lite — *is complexity justified?*
4. B4 net expectancy ≥ `E_min` and CI lower bound > 0 at conservative costs.

### 18.2 Family control

Holm for the finite pre-specified family; BH-FDR for explicitly exploratory screening (labeled exploratory; cannot support C3+).

### 18.3 Selection-bias analysis

DSR (with trial count from the ledger, with skew/kurtosis, using trade-level or cluster-level returns), PBO via CSCV where enough comparable configs exist, plus **Hansen SPA / White Reality Check** against the benchmark. Use **stationary/block bootstrap** CIs for all dependent-return metrics. State when DSR/PBO are unreliable (few trades, few configs) rather than reporting a number anyway.

### 18.4 Subgroup rule

Regime/session/setup subgroup analyses are **descriptive**, unless pre-registered with their own correction. No post-hoc subgroup promotion.

---

## 19. Sample Size and Power

### 19.1 Protocol

Pilot → estimate expectancy, per-trade SD (in R), dependence (cluster ACF), effective N → Monte Carlo power → required independent trades → freeze stopping rule.

### 19.2 Feasibility reality check (illustrative, must be redone with pilot data)

For a one-sided test, α = 0.05, power = 0.80, per-trade SD ≈ 1R:

```text
delta = 0.10 R → n ≈ 620 independent trades
delta = 0.05 R → n ≈ 2,470
delta = 0.02 R → n ≈ 15,400
n ≈ ((1.645 + 0.842) / δ)²     δ = true net expectancy in R
δ = 0.10 R → n ≈ 620 independent trades
δ = 0.05 R → n ≈ 2,470
δ = 0.02 R → n ≈ 15,400
```

These are *before* Holm/selection penalties and clustering, so real requirements are higher. At **3 independent trades/day**, a 0.05 R edge needs ≈ **820 days** of prospective data; at 1/day, ≈ 6.8 years. Consequence: the prospective stage must be designed as **sequential testing** (alpha-spending / SPRT with pre-registered boundaries) or the track must target a larger minimum effect size; otherwise C5 is unattainable by construction.

### 19.3 Arms

A1–A5 paired ablation arms split the sample and multiply comparisons. Prospective primary arm = one pre-specified arm; other arms are exploratory.

### 19.4 Data window

Pre-register the training data start (e.g., exclude pre-regime-change eras if justified *ex ante*). Document structural breaks (venue changes, ETF launch, major microstructure/fee changes). Do not choose the window after seeing results.

---

## 20. Retraining Lifecycle

TRAIN → CALIBRATE → LOCK → PROSPECTIVE TEST → SCHEDULED RETRAIN → NEW VERSION. The walk-forward evaluation must **simulate the exact production retraining cadence**; a retrained model is a new version (and a new trial). Version record fields as in v2, plus `trial_ledger_hash` and `calibration_split_hash`. **Drift monitors** (feature PSI, calibration slope on recent trades, realized-vs-predicted EV) trigger *review*, not automatic retraining.

---

## 21. Metrics

Primary: net expectancy/trade, net expectancy per unit **realized** risk (R computed from actual simulated fill-to-stop distance, not nominal), max drawdown, profit factor, selection-adjusted risk-adjusted metric. All reported with **block-bootstrap CIs**. Profit factor and Sharpe are reported with outlier-robust companions (median R, trimmed mean, CVaR 5%). Tail metrics: worst-day, worst-trade, longest losing streak, time-under-water. Secondary list as v2.

---

## 22. Cost-Stress and Sensitivity Matrix

Dimensions: fee tier, spread, slippage, **stop slippage multiple**, funding, latency, size, vol shock, **tie-break policy**, **barrier grid perturbation (±10–20%)**, **detector parameter perturbation**, **start-date shift**. A candidate is robust only if the sign of expectancy holds across a pre-registered fraction of the matrix (e.g., ≥ 80% of cells) and at the conservative corner.

---

## 23. Regime Analysis

Evaluate by volatility bucket (low/normal/high/extreme), trend vs. range, session, and by calendar epoch (e.g., per year/halving cycle). Descriptive unless pre-registered (§18.4). A regime-only edge is allowed **only if the regime classifier is causal and pre-registered**, and the regime filter is then part of the strategy and counted as a trial.

---

## 24. Prospective Experiment

Lock protocol → collect observations with no changes. Record fields as in v2 plus `latency_measured`, `data_available_time`, `simulated_vs_live_fill_gap`. Sequential monitoring boundaries are pre-registered (§19.2). Any model/feature/threshold change creates a new versioned arm with its own sample clock. Paper-trade fills should be compared with an actual small-size live fill study **only after** a separate risk approval.

---

## 25. Sealed Holdout

- Holdout period starts **after** the most recent date of any data previously examined by *any* prior BTCognitive study (HAR program, MFE/MAE plan). Record this boundary and prove it by the provenance ledger.
- **Technical control:** holdout data stored encrypted or hash-sealed; decryption key held by the custodian; every access logged; the evaluation script is frozen and hash-checked before opening.
- Opened **once**. If opened for any reason other than the promotion test (e.g., debugging), the holdout is burned and a new one must be collected prospectively.
- The sealed holdout must itself meet the §19 power requirement; if it cannot, state that it can only *fail* a candidate, not confirm it.

---

## 26. Claim Ladder (re-ordered)

| Level | Claim | Required evidence |
|---|---|---|
| C0 | Software/accounting correctness | Pytest + oracle + replay (G0, 6B) |
| C1 | Statistical association | Setup vs. matched random (B0), placebo controls pass |
| C2 | Conditional predictability | Out-of-sample calibration/skill vs. B3 and B4-lite |
| C3 | Executable edge | Net positive at **conservative** costs and latency; CI lower bound > 0 |
| C4 | Robust edge | Survives §22 sensitivity matrix, both tie-break policies, regime/epoch splits |
| C5 | Selection-adjusted evidence | Holm/SPA, DSR, PBO (where valid), optimism-gap check |
| C6 | Prospective edge | Pre-registered future data, sequential boundary crossed |
| C7 | Sealed-holdout promotion | Single opening, protocol-compliant |

"Positive" always means per §0.3. Pytest cannot raise a claim above C0.

---

## 27. Explicitly Rejected for the First Build

Direct `[entry, TP, SL]` regression; RL trading; OU-based barrier optimization; tiered exits; trailing stops; large neural ensembles; many foundation models; dozens of indicators; automatic feature search; automatic model evolution; accuracy/win-rate targets; **limit-entry strategies without non-fill modeling; multi-instrument pooling; leverage optimization; any live capital.**

---

## 28. Phases with Go/No-Go Gates

| Phase | Work | Gate to proceed |
|---|---|---|
| **6-0 (G0)** | Foundation integrity (§0.2) | All six items complete |
| **6A** | Contract freeze: `EntryOpportunity`, `TripleBarrier`, `ExecutionCost`, `BacktestAccounting`, `DetectorSpec`, `Lifecycle`; hash all; define date splits, primary hypotheses, success/kill numbers, trial ledger | Auditor confirms code matches pre-registration |
| **6B** | Deterministic triple-barrier engine + exhaustive fixtures + oracle + property tests | Oracle agreement 100%; tie-ambiguity rate measured and acceptable (or 1-min/tick data acquired) |
| **6B2** *(new)* | **Data audit + feasibility pilot**: event counts per setup, cluster counts, effective N, cost/barrier ratios, ambiguity rate, power simulation | **Kill/redesign if** `N_effective < N_min` or `C/S > C_max` for all grids |
| **6C** | Setup detector (A1, A2) + placebo tests | Placebo edge ≈ 0; detector hash frozen |
| **6D** | Baselines B0, B0b, B1, B2, B3, B3b under identical costs | If B3 ≤ B0 after costs (no timing info), **stop or redesign setups** — do not proceed to ML |
| **6E** | Logistic (B4-lite) then LightGBM (B4) meta-labeler + calibration | Beats B3 out-of-sample with CI; otherwise stop ML |
| **6F** | Barrier selection with nested evaluation | Optimism gap within pre-set tolerance; beats median pair |
| **6G** | Execution, latency, leverage/liquidation, risk, lifecycle | Positive at conservative scenario |
| **6H** | Purged walk-forward + sensitivity matrix + selection analysis | C5 criteria met |
| **6I** | Prospective run (sequential) | Boundary crossed or futility stop |
| **6J** | Foundation-model challengers (contamination rule §14.3) | Incremental value over RV features, within latency budget |
| **6K** | Sealed holdout opening | Single opening → promotion event |

Stage↔phase map: S1↔6C, S2↔6E, S3↔6F, S4/S5↔6G.

---

## 29. Promotion Packet (extended)

- **[DATA]** dataset hash, PIT audit, coverage, missing-data report, structural-break log
- **[PROTOCOL]** experiment, detector-spec, feature, barrier, execution-cost, lifecycle hashes; pre-registration timestamp precedes first outcome look
- **[MODEL]** artifact hash, training cutoff, retraining schedule, calibration split hash, trial-ledger hash
- **[VALIDATION]** purged walk-forward, embargo, effective N, primary metric + block-bootstrap CI, shuffle/time-shift/placebo results, optimism gap
- **[ECONOMICS]** net expectancy (conservative costs), drawdown, tail metrics, profit factor, full sensitivity matrix, tie-break sensitivity, latency sensitivity
- **[SELECTION]** trial count, Holm/fixed-sequence results, SPA/RC, DSR, PBO (or reason unavailable)
- **[EXECUTION]** simulated-vs-paper-live fill gap
- **[PROSPECTIVE]** sequential monitoring log
- **[HOLDOUT]** sealed result, access log

---

## 30. Worst-Case / Pre-Mortem Plan

| # | Failure scenario | Early indicator | Pre-registered response |
|---|---|---|---|
| W1 | **No edge exists.** Setups are no better than random after costs (most likely outcome for 15-min BTC). | B3 ≤ B0 at gate 6D | Stop. Publish negative result. Do not tune detectors to rescue it. |
| W2 | **Costs eat the edge.** Barriers too tight relative to spread/fees/slippage. | `C/S` high in 6B2 | Widen horizon/barriers, move to coarser timeframe as a *new* track, or stop. |
| W3 | **Tie-break policy decides the result.** | Large `UNRESOLVED_INTRABAR` rate; sign flips between policies | Acquire tick/1-min data; else mark non-robust and stop. |
| W4 | **Hidden leakage** (PIT violation, rolling normalization, HTF-bar partial leakage). Results look too good. | Time-shift test improves; shuffle test fails to collapse | Freeze results, root-cause, discard affected experiments, log in ledger. |
| W5 | **Backtest overfit / selection bias.** Great in-sample, collapses on holdout. | Large optimism gap; DSR/SPA fail | Do not open holdout again; treat holdout as burned if re-tuned. |
| W6 | **Regime change** (liquidity regime, fee change, ETF-flow dominance). | Calibration slope drift, per-epoch sign flip | Pause; new model version only via pre-registered retrain; consider the edge dead if epoch-unstable. |
| W7 | **Holdout contamination** (prior studies overlap, or accidental peek). | Provenance ledger shows overlap/access | Declare holdout burned; require fresh prospective data. |
| W8 | **Foundation-model leakage** from pretraining data. | Suspiciously strong results only in historical window | Restrict to prospective evaluation; exclude from claims. |
| W9 | **Flash crash / gap through stop** (stop fills at multiples of risk). | Stress matrix tail losses; max-adverse > R budget | Cap size by tail-loss budget, require exchange-side stops, add volatility-shock abstention. |
| W10 | **Infrastructure failure with open position** (feed/API/clock). | Watchdog heartbeat gaps | Lifecycle policy §11.3: exchange-side bracket + flatten; no new entries until audit passes. |
| W11 | **Under-powered prospective stage** gives an ambiguous verdict. | Power simulation (6B2) | Sequential design, larger `E_min`, or accept that C6 cannot be reached; no "looks good" promotion. |
| W12 | **Process drift:** thresholds, grids or windows quietly changed after seeing results. | Auditor diff between pre-registration and code/ledger | Invalidate affected results; re-register as a new experiment. |
| W13 | **Environment/numeric drift** breaks replay. | Replay test fails in rebuilt container | Pin and rebuild; no result is citable until replay passes. |
| W14 | **Sunk-cost continuation.** | Phase gate fails but work continues | Gates are binding; a failed gate requires written exception approved by Auditor, not Researcher. |

**Worst-case acceptance statement:** If W1, W2, or W3 triggers at its gate, the correct outcome is a documented negative result. This is a successful research outcome, not a project failure.

---

## 31. Source Verification Notes

External sources named in v2 (Google TimesFM repository/model card, Datadog Toto, Amazon Chronos, Kronos repository and arXiv paper, Bailey et al. on PBO, Bailey & López de Prado on DSR) must be re-verified and recorded as artifacts per §14.2 at the time of use. Additional methodological references to cite in the protocol: López de Prado (purged/combinatorial CV, triple-barrier, meta-labeling, uniqueness weights); White (2000) Reality Check; Hansen (2005) SPA; Politis & Romano (stationary bootstrap). Claims not directly verified by primary sources are excluded from decision logic.

---

## 32. Research Status

```text
CURRENT PROJECT STATUS
----------------------
Frozen HAR product path:       CANONICALIZATION_BLOCKED (out of scope)
New Entry/TP/SL track:         PLAN v3 — BLOCKED ON GATE G0
Primary model:                 LIGHTGBM META-LABELER (after logistic baseline)
Primary target:                NET R / 3-STATE FIRST-TOUCH (binary TP_FIRST diagnostic only)
Primary setup families:        SWEEP/RECLAIM + RANGE RECLAIM (frozen DetectorSpec)
Barrier method:                PRE-SPECIFIED GRID, ONE MODEL PER PAIR, NESTED SELECTION
Outcome authority:             CANONICAL RESOLVER + INDEPENDENT REFERENCE ORACLE
Path data resolution:          1-MINUTE (OR FINER) FOR RESOLUTION
Backtest harness:              PYTEST (correctness only)
Scientific proof:              NOT ESTABLISHED
Production authorization:      NO
Capital authorization:         NO
```

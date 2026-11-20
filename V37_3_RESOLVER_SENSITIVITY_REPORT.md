# V37.3 — Resolver Sensitivity Report

**Workstream:** 3 — Resolver semantics

**Date:** 2026-11-04

**Disposition:** Read-only semantic analysis; no resolver or contract amendment proposed as effective

**Scope:** Six unresolved semantics in the frozen entry/TP/SL research track

## Executive summary

Static inspection finds that the frozen materials define some key boundaries but leave material interpretations unresolved or in tension with implementation. The current pipeline and resolver cannot by themselves settle those questions. This report therefore supplies deterministic, synthetic boundary cases and candidate outcomes only. All candidate outcomes are **non-authoritative** and carry one or more of `AMBIGUOUS`, `CENSORED`, `INCOMPLETE`, or `OWNER_DECISION_REQUIRED`.

No frozen contract, ledger, implementation, test, or prior report was changed. No holdout data, raw market observations, or prospective ledger entries were accessed. No diagnostic script was necessary; calculations below are direct arithmetic on stated synthetic inputs, not an execution of the resolver.

## Evidence basis and limitations

- **Frozen wording:** `research/entry_tp_sl/decision_contract.json`, `entry_execution_contract.json`, `outcome_accounting_contract.json`, `instrument_contract.json`, `PREREGISTRATION_v1.md`, and `detector_spec.py`. The freeze manifest lists hashes for the contracts (`contract_freeze_manifest.json:2–9`); this work did not edit or recalculate those hashes.
- **Implementation behavior:** `run_full_research_pipeline.py`, `setup_detector.py`, `triple_barrier.py`, and `reference_resolver.py`, cited per issue below.
- **Prior decision context:** `V37_1_CONTRACT_OWNER_DECISIONS.md` §§1–6 independently records the outstanding owner questions. It is context, not a substitute for the frozen contracts or current source.
- **Not established:** Runtime conformance, source-data timestamp alignment, empirical frequency or impact, any performance estimate, or the authoritative interpretation of an omitted contract detail. No tests, replay, holdout inspection, ledger inspection, network access, or full-suite baseline were performed. The worktree had pre-existing modifications outside this report; the scoped contract and resolver files were clean in the inspected worktree.

Statuses below are this report's research labels, **not** resolver enum values or frozen contract states. Price examples use idealized prices and are not observations or estimates of market behavior.

## Findings and deterministic boundary sensitivities

### 1. Decision, entry, and candle timestamp alignment

**Frozen definition.** `decision_contract.json:15–21` calls `t0` the exact close timestamp of the completed 15-minute bar, sets the fill label to `t0 + 60s` and describes it as the open of the immediate next 1-minute execution bar, and defines the first path interval as `(t0+60s, t0+120s]`. Separately, `instrument_contract.json:30–33` defines 1-minute timestamps as interval-close labels: timestamp `t` represents `(t-60s,t]`.

**Implementation.** The pipeline resamples to 15-minute rows and retains the last 1-minute `Timestamp` (`run_full_research_pipeline.py:58–66`), looks up an exact row at `t0+60`, takes that row's `Open`, and starts the path at the next row (`:110–126`). The builder stores `entry_timestamp=t0` and `fill_timestamp=t0+60` (`triple_barrier.py:71–72`); resolvers ignore bars timestamped at or before that fill label (`triple_barrier.py:125–126`; `reference_resolver.py:43–45`).

**Synthetic boundary.** Let `t0=900` seconds. Close-stamped rows at 960, 1020, and 1080 represent intervals `(900,960]`, `(960,1020]`, and `(1020,1080]`. Let their Opens be 100.00, 101.00, and 100.50. With pair 01, `sigma=1%`, LONG, and the engine's BASE 5-bps entry adjustment:

| Candidate mapping | Selected row / modeled entry | First examined path row | Synthetic first-path OHLC | Candidate gross outcome |
|---|---:|---:|---|---|
| Current exact-label selection (`t0+60`) | 960 / 100.05 | 1020 | O=100.50, H=101.50, L=99.50, C=100.20 | `TP_FIRST`, +1R |
| If `t0+60` is a physical open instant under interval-close row labels | 1020 / 101.0505 | 1080 | O=100.50, H=101.50, L=99.50, C=100.20 | `SL_FIRST`, −1R |

This illustrates a possible 2R gross-label swing from the row mapping alone; it is not evidence that either mapping is correct. The 960-row Open is at the interval's start (`t0`), whereas the contract's fill label is `t0+60`; the contract does not explicitly say whether `fill_timestamp` is a physical instant or a close-label for the execution candle. It also does not reconcile the first path interval with whether the execution candle itself is in the barrier path.

**Status:** `AMBIGUOUS`, `OWNER_DECISION_REQUIRED`. Confirm whether timestamps name physical events or bar intervals, which exact row supplies the fill, whether the fill candle's range is excluded, and what `entry_timestamp` means. Missing exact fill rows are silently skipped by the pipeline (`:110–113`), rather than emitted as the contract's `DATA_GAP` (`entry_execution_contract.json:15–19`).

### 2. Two distinct 2% rules: A1 sweep ceiling and entry-gap cancellation

**Frozen definition.** A1 config sets a 0.05% minimum and 2.00% maximum sweep, with a two-bar reclaim window (`detector_spec.py:16–23`). Separately, the execution contract says fill at actual Open and cancel when the entry gap exceeds a 2.0% cap (`entry_execution_contract.json:15–19`). That execution rule does not specify the comparison price, denominator, whether the gap is absolute or trade-adverse only, or an explicit equality rule.

**Implementation.** The detector computes low-side penetration relative to prior swing low or high-side penetration relative to prior swing high; the A1 comparisons are inclusive at both thresholds (`setup_detector.py:87–108`). The pipeline passes the selected Open to the builder (`run_full_research_pipeline.py:110–116`); neither it nor `build_trade_contract` supplies a gap reference or enforces the execution cap (`triple_barrier.py:25–54`).

**Synthetic boundaries.**

1. **A1 sweep calculation:** prior swing low = 100.00. A low of 99.95 is a 0.05% penetration and is included by the implementation; 98.00 is exactly 2.00% and is included; 97.99 is 2.01% and is excluded. These comparisons concern the A1 structural sweep only.
2. **Entry gap candidates:** reference close = 100.00 and fill Opens = 98.01, 98.00, and 97.99 for a LONG. Relative-to-close absolute gaps are 1.99%, 2.00%, and 2.01%. Under a “cancel only if exceeded” interpretation, the first two fill and the last cancels. A one-sided adverse-gap rule for a LONG gives the same result for these downward gaps, but differs for upward gaps: Open 102.00 is 2.00% absolute and potentially a favorable gap for a LONG; a SHORT treats it as adverse. If the denominator instead is a swing level of 99.00, Open 102.00 is 3.03%, not 2.00%.

The examples show that an unprovided reference and direction rule can change cancellation; they do not prescribe decision-close, swing level, or another denominator. In the actual implementation, all these entry-gap cases proceed to contract construction if a fill row exists.

**Status:** `AMBIGUOUS`, `OWNER_DECISION_REQUIRED`. Keep A1's sweep ceiling distinct from execution-gap control. Owner must define the entry-gap reference/denominator, directionality, equality treatment, and precedence with the “fill at actual Open” rule. No current implementation outcome can be reported as enforcing the 2% execution cap.

### 3. Opening gap versus same-candle TP/SL dual touch

**Frozen definition.** Barrier touches use 1-minute High/Low comparisons (`PREREGISTRATION_v1.md:89–91`). An unobservable same-bar dual touch is `SL_FIRST`, must record collision and unresolved-order flags, and requires a TP-first sensitivity (`PREREGISTRATION_v1.md:96–99`; `outcome_accounting_contract.json:97–102`). The frozen materials do not state whether an Open already beyond one barrier overrides later dual-touch extremes, nor its exit-state semantics.

**Implementation.** Both resolvers test dual touch before single-touch opening-gap handling (`triple_barrier.py:157–173`; `reference_resolver.py:63–76`). For a LONG dual-touch bar, the engine chooses the lower/stop boundary unless Open is itself through the lower barrier; an Open above the upper/target does not override the SL-first result (`triple_barrier.py:165–173`). The reference oracle follows the same ordering (`reference_resolver.py:63–76`). The engine's TP-first sensitivity is not part of this resolver branch; it returns the conservative result.

**Synthetic boundaries.** Use LONG entry 100.00, TP 101.00, SL 99.00. First, an opening-gap/dual-touch bar is `O=102, H=103, L=98, C=100`: both barriers' ranges are touched, but Open is already above TP.

| Opening-gap/dual-touch interpretation | Outcome/exit | Gross R (1R=$1) |
|---|---|---:|
| Current dual-touch-first implementation | `SL_FIRST`, exit at 99.00, collision and unresolved-order true | −1R |
| Open-is-first candidate, using actual Open as exit | Open-gap TP at 102.00 | +2R |

For the separately required TP-first sensitivity, use an ordinary unresolved bar `O=100, H=102, L=98, C=100` (Open is inside both barriers). SL-first is −1R and TP-first is +1R, a 2R bound. On the opening-gap fixture, the Open-first actual-price candidate differs from the current SL-first result by 3R. Neither alternate is asserted to be the frozen primary rule. A symmetric SHORT opening-gap fixture (entry 100, TP 99, SL 101, `O=98,H=102,L=97`) has the same conflict in reverse direction.

**Status:** `AMBIGUOUS`, `OWNER_DECISION_REQUIRED`. Confirm whether an opening crossing takes temporal precedence over later intrabar extremes; if so, specify outcome state, exit price, and collision flags. Independently confirm where and how the mandated TP-first sensitivity is to be reported. Do not treat the current `SL_FIRST` result as resolving the opening-gap question.

### 4. Incomplete horizon and missing candles

**Frozen definition.** Pair 01 requires 240 minutes / 240 1-minute bars (`outcome_accounting_contract.json:83–86`). Timeout is at the exact close of the 240th bar and uses the realized return, not a fixed −1R (`PREREGISTRATION_v1.md:104–110`; `outcome_accounting_contract.json:91–95`). A missing fill must fail closed as `DATA_GAP` (`entry_execution_contract.json:15–19`). The intake manifest requires fail-closed handling beyond a gap “tolerance” but gives no numeric tolerance (`data_intake_manifest.json:17–18`).

**Implementation.** The engine skips bars up through the fill label, but does not check the first forward timestamp against an expected timestamp; its `expected_next_ts` variable is initialized but unused (`triple_barrier.py:113–129`). It permits up to three missing minutes between included rows (`:129–136`), counts observed rows toward the horizon (`:137–146`), and returns `DATA_GAP` only if no-touch coverage is shorter than `H−3` (`:318–320`). The oracle has the corresponding inter-row `>240s` rejection and `H−3` cutoff (`reference_resolver.py:49–56, 208–210`). The pipeline omits missing-fill opportunities (`run_full_research_pipeline.py:110–113`).

**Synthetic boundaries (no barrier touched).**

| Path supplied for primary H=240 | Current code behavior | Exact-240-minute candidate |
|---|---|---|
| 236 contiguous observations | `DATA_GAP` | `INCOMPLETE` |
| 237 contiguous observations, ending at fill+237m | `TIMEOUT` at that last close | `INCOMPLETE`; no exact 240th-bar close |
| 240 observations with one interior 3-minute omission | Accepted; can end at fill+243m | `INCOMPLETE` or gap-policy outcome; elapsed endpoint is exceeded |
| First forward minute absent, then 240 contiguous observations beginning at fill+2m | First gap is not checked; 240 rows can be counted and end at fill+241m | `INCOMPLETE` pending first-observation and tolerance rule |

The current 237-row timeout allowance can resolve a no-touch outcome three minutes early. Counting 240 observations through an internal omission can move the endpoint three minutes late. The absent-first-row case is not governed by the resolver's inter-row gap check. An early observed barrier hit may return before horizon coverage is established; whether missing later bars matter after a terminal barrier hit is also not expressly reconciled.

**Status:** `INCOMPLETE`, `CENSORED`, `OWNER_DECISION_REQUIRED`. Decide elapsed-time endpoint versus valid-observation count, numeric/cumulative versus consecutive gap tolerance, whether 237–239 rows may time out, treatment of missing first path rows, and whether an early terminal hit is admissible despite later missing coverage. The table does not convert an incomplete path into a valid outcome.

### 5. Fee, spread, and slippage allocation

**Frozen definition.** BASE lists entry/exit fees 10+10 bps, entry/exit slippage 5+5 bps, half-spread 2.5 bps on each side, totaling 35 bps. CONSERVATIVE lists fees 15+15, slippage 10+15, half-spread 5 bps each side, totaling 65 bps (`entry_execution_contract.json:21–41`; `PREREGISTRATION_v1.md:120–129`). Net R subtracts the all-in round-trip fraction divided by `k_SL × sigma` (`outcome_accounting_contract.json:91–95`). The contract does not state whether each component changes execution prices, is included in the aggregate deduction, or both.

**Implementation.** For BASE, the builder adjusts LONG entry Open upward by 5 bps (SHORT downward), then anchors barriers to this adjusted entry (`triple_barrier.py:47–68`). Resolution also deducts the complete 35- or 65-bps aggregate from gross R (`triple_barrier.py:150–152, 179–182, 328–330`; `reference_resolver.py:57–60, 80–81`). Exit slippage is not separately applied to the exit price in these paths.

**Synthetic sensitivity.** Let raw Open = 100.00, LONG, `sigma=1%`, pair 01, and a barrier TP exit exactly +1R from the modeled entry. BASE builder entry becomes 100.05, so its upper barrier is 101.0505 at the builder's four-decimal precision (`triple_barrier.py:56–68`). The instrument contract separately specifies a $0.01 tick (`instrument_contract.json:20–24`); this example does not settle how barriers should be aligned to that tick. Resolver's all-in cost is `0.0035 / 0.01 = 0.35R`; current net is `1.00−0.35 = +0.65R`. If entry slippage is embodied in the 100.05 modeled fill and removed once from the residual aggregate, the remaining 30 bps cost is `0.30R`, producing `+0.70R`. The difference is 0.05R. Under CONSERVATIVE, the analogous arithmetic is 1.00−0.65=+0.35R as implemented versus 1.00−0.55=+0.45R if the embedded 10-bps entry slippage is excluded from a residual aggregate: 0.10R. These are allocation alternatives, not a claim that either accurately models realized execution.

**Status:** `AMBIGUOUS`, `OWNER_DECISION_REQUIRED`. Provide a component-level accounting map specifying entry/exit price adjustments versus cash deductions and prove that every fee, spread side, and slippage component is counted exactly once. Until then, the current net-R values are implementation outputs, not a settled cost interpretation.

### 6. A1 reclaim-confirmation timing

**Frozen definition.** `detector_spec.py:16–23` sets `reclaim_confirmation_window=2`, described as reclaim “within 2 bars (30m).” It does not say whether this means two bars including the sweep bar or two later bars, nor specify a pending-sweep expiry/invalidating condition.

**Implementation.** A1 emits only when the current 15-minute candle both sweeps and closes back across the prior swing boundary (`setup_detector.py:87–108`). It does not consult `reclaim_confirmation_window` or retain a pending sweep. An emitted event's decision timestamp is the current bar timestamp (`:143–145`).

**Synthetic boundary.** Prior swing low = 100.00. Sweep bar `i`: Low=99.80 (0.20% sweep), Close=99.90 (not reclaimed). Bar `i+1`: Low=99.95, Close=99.98 (not reclaimed). Bar `i+2`: Low=100.00, Close=100.10 (reclaimed, but does not itself sweep below 100).

| Candidate meaning | Result |
|---|---|
| Current same-candle implementation | No A1 event on `i`, `i+1`, or `i+2`; later bars do not independently meet the sweep condition. |
| Two-bar window counts sweep bar `i` as first | No confirmation within `i`–`i+1`; expire without an event. |
| Two subsequent completed bars after sweep | Confirmation on `i+2`; event timestamp shifts 30 minutes from sweep; downstream feature snapshot and fill eligibility also shift. |

If confirmation instead occurs on `i+1`, a two-bar-inclusive and two-subsequent-bar interpretation can both accept it but still differ on how long an unconfirmed setup remains pending. These alternatives change event inclusion and timing; they are not equivalent labels for the same opportunity.

**Status:** `AMBIGUOUS`, `OWNER_DECISION_REQUIRED`. Decide whether the count includes the sweep candle, the exact close-based confirmation condition, pending-sweep invalidation/reset, event timestamp, and when features, cooldown, and order eligibility begin. Do not silently substitute the current same-bar rule for the declared two-bar window.

## Governance disposition

- **Research Experiment:** `INCONCLUSIVE` — this workstream evaluates semantic sensitivity only; no experiment or empirical outcome analysis was run.
- **Prospective Evidence:** `NOT_STARTED` for this resolver-sensitivity workstream; this is not a determination of the project-wide ledger status.
- **Model Authorization:** `OFFLINE_RESEARCH_ONLY`.
- **Live Trading:** `DISABLED`.

No candidate in this report changes a frozen contract or authorizes product scope reduction. Resolution requires explicit owner decisions and, if the frozen meaning changes, a dated and auditable contract amendment. Historical evidence, holdout observations, and prospective ledger evidence remain outside this report's conclusions.

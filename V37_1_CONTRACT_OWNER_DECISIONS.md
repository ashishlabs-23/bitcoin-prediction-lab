# V37.1 — Contract Owner Decision Package

**Review role:** Agent 3  
**Review mode:** Strict read-only; decision package only  
**Date:** 2026-11-04  
**Repository state at review:** `milestone/v35.3-critical-remediation`, commit `25d483f4c3646661b57311de9d0b53d2be881adb`. The worktree was already broadly modified; none of the scoped `research/entry_tp_sl` files below was modified.  
**Disposition:** No contract, implementation, test, manifest, dataset, or prior report was changed. This file is the only requested deliverable.

## Evidence and scope

- **Frozen-contract evidence — high confidence:** The current `decision_contract.json`, `entry_execution_contract.json`, `outcome_accounting_contract.json`, `instrument_contract.json`, `PREREGISTRATION_v1.md`, `resolver_contract.md`, and `resolver_decision.md` hashes match their entries in `contract_freeze_manifest.json`. That manifest identifies the 2026-10-07 freeze. The contracts' frozen status is distinguished below from statements in implementation code.
- **Implementation evidence — high confidence:** Direct inspection of the named source files and exact line ranges below. The implementation is evidence of current behavior, not authority to fill contract omissions.
- **Interpretive conclusions — medium confidence:** Timestamp alignment implications are derived from the explicit interval-close convention and source resampling/selection code. No raw observation rows were opened to test actual sample alignment.
- **Not performed:** No tests, replay, network access, holdout access, or observation-row access.

## Owner decisions required

The frozen documents settle parts of these questions but leave material semantics unresolved or disagree with the implementation. All changes to a frozen interpretation require owner approval and an auditable contract amendment/version decision. Recommendations below are proposals only, not current contract rules.

### 1. Signal, decision-candle, and eligible-fill timestamps

**Explicit frozen facts**

- `decision_contract.json` labels `t0` as the completed 15-minute decision-bar close; features may use data available no later than that timestamp; signal generation and order submission are instantaneous at `t0`; the fill is described as `t0 + 60 seconds` at the immediate next 1-minute bar open; the first path observation is `(t0 + 60s, t0 + 120s]` (`decision_contract.json:14–24`).
- 1-minute timestamps are explicitly **interval-close** timestamps, and timestamp `t` denotes the completed interval `(t-60s, t]` (`instrument_contract.json:29–33`). The instrument contract selects `Open` for entry and `High`/`Low` for barriers (`instrument_contract.json:20–23`).
- A1 setup events take their timestamp from the current input row (`setup_detector.py:143–145`).

**Implementation evidence and ambiguity**

- The pipeline resamples on the 1-minute datetime index with `resample('15min')`, takes the last source `Timestamp`, and does not specify resampling `closed`/`label` semantics (`run_full_research_pipeline.py:58–66`). The detector uses the current row's timestamp and stores it on the event (`setup_detector.py:69–71, 143–145`); the pipeline then treats it as `t0` (`run_full_research_pipeline.py:101–112`).
- For each setup, the pipeline looks for an exact 1-minute timestamp equal to `t0 + 60`, uses that row's `Open`, and starts path bars at the following row (`run_full_research_pipeline.py:110–126`). The contract builder sets `entry_timestamp = decision_timestamp` and `fill_timestamp = decision_timestamp + 60` (`triple_barrier.py:71–72`).
- This leaves unresolved whether `fill_timestamp` is the actual execution instant or the close-time label of the bar whose `Open` is used. Under the instrument's interval-close convention, the row labelled `t0+60` represents a completed interval ending then; its `Open` is at the interval's start. The implementation's timestamp selection and the contract's “open at `t0+60`” wording therefore need an explicit common convention. The resampling code also does not itself establish that its carried `Timestamp` is the intended 15-minute close.
- If the exact fill timestamp is absent, the research pipeline silently skips the setup (`run_full_research_pipeline.py:110–113`); the execution contract instead specifies a missing fill bar as `FAIL_CLOSED_DATA_GAP` (`entry_execution_contract.json:15–19`; `PREREGISTRATION_v1.md:58–60`).

**Technically defensible alternatives and consequences**

1. Define `t0` as the actual UTC close instant of the completed 15-minute candle, align aggregation to that close, and define the fill as the next eligible bar's actual open instant. This makes the causal sequence explicit but may change which 1-minute row supplies the fill and path.
2. Define timestamps as bar labels rather than physical event instants, explicitly map each label to its represented interval, and keep the existing row-selection behavior only if it matches that mapping. This preserves current indexing where compatible, but requires clarifying event-time fields and fill eligibility.
3. Keep the current pipeline behavior pending owner clarification. This preserves implementation output but cannot establish that the fill occurred after signal submission.

**Safe recommendation (not contract):** Do not treat a fill as eligible until the owner reconciles physical event times with bar-label times and confirms the 15-minute aggregation boundary. Emit a fail-closed missing-fill outcome rather than silently dropping the setup.

**Approval required:** Yes.

**Exact owner decisions:** Is `t0` the actual 15-minute close instant or an aggregate label? Does the timestamp on an execution row identify its opening instant or its closing instant for purposes of fill eligibility? Which precise bar is eligible for the fill, and which subsequent intervals enter the path? Should a missing eligible bar be recorded as `DATA_GAP` rather than omitted?

### 2. A1 2% limits, entry-gap reference/direction, inclusivity, and cancellation precedence

**Explicit frozen facts**

- The A1 detector specification fixes a minimum sweep of `0.0005`, maximum sweep of `0.0200`, a two-bar reclaim confirmation window, and a four-bar cooldown (`detector_spec.py:16–23`). Registration calls the maximum 2.0% and describes low-sweep LONG/high-sweep SHORT (`setup_registration.md:10–16`).
- Separately, the execution contract says `FILL_AT_ACTUAL_OPEN`, `max_allowed_entry_gap_pct: 2.0`, and `cancellation_on_gap_exceeded: true`; it does not identify a reference price, whether direction is absolute or trade-adverse, equality treatment, or which rule takes precedence when a breach is also an opening gap (`entry_execution_contract.json:15–19`).

**Implementation evidence and ambiguity**

- For A1 sweep size, the implementation measures low-side penetration from `swing_low` and high-side penetration from `swing_high`, using `sweep_min_pct <= penetration <= sweep_max_pct`; the sweep beyond the level is strict (`setup_detector.py:87–108`). This describes the current detector behavior, not the missing entry-gap definition.
- The pipeline takes the selected next-row open and passes it into contract construction without a 2% entry-gap check or cancellation (`run_full_research_pipeline.py:110–133`). `build_trade_contract` validates the open as a positive finite price and applies directional entry slippage, but does not check the execution contract's gap cap (`triple_barrier.py:25–54`).
- Thus, there are two distinct 2% concepts: the A1 sweep-magnitude ceiling, whose current implementation has a denominator and inclusive upper comparison, and the execution-gap cap, whose denominator, direction, boundary, and precedence are unspecified and not enforced by this pipeline.

**Technically defensible alternatives and consequences**

1. Compare the next open to the completed decision-candle close, in either direction. This is straightforward to audit but may cancel favorable as well as adverse gaps.
2. Compare to the A1 swing reference. This ties the gap to setup structure but may conflate a sweep measured from a swing with execution displacement from the signal price.
3. Compare to the immediately preceding 1-minute close. This reflects the last sampled market close but may be inconsistent with a decision signal based on the 15-minute candle close.
4. Apply the limit only to adverse movement in the setup's side, or apply it to absolute movement in either direction. The former retains favorable gaps; the latter is symmetric.
5. Treat the threshold as breached only when strictly beyond 2.0%, or at 2.0% and beyond. The execution contract's word “exceeded” suggests but does not conclusively settle equality.
6. On a breached gap, cancel before any fill is constructed, or record an actual-open fill and separately flag the breach. The former honors cancellation as a no-fill; the latter honors actual-open fill language but conflicts with cancellation.

**Safe recommendation (not contract):** Do not build an outcome for any entry gap until the owner fixes reference, direction, equality, and precedence as one rule. If the owner selects cancellation, make cancellation precede fill-price/slippage construction; if no approved rule exists, classify the opportunity as unresolved rather than infer a fill. Keep the A1 sweep cap separate.

**Approval required:** Yes.

**Exact owner decisions:** What price is the 2% entry-gap reference? Is the check absolute or adverse-only? Does exactly 2.0% pass or cancel? Does cancellation override “fill at actual open,” and what outcome/state represents cancellation? Should the A1 sweep cap's existing swing-level measure remain independent of the entry-gap cap?

### 3. Opening gaps versus intrabar dual-touch ambiguity

**Explicit frozen facts**

- The preregistration uses 1-minute High/Low touch tests (`PREREGISTRATION_v1.md:89–91`). It says to follow observed sub-minute order when available and to resolve an unobservable dual touch within one 1-minute bar as `SL_FIRST`, recording collision metadata and running TP-first sensitivity (`PREREGISTRATION_v1.md:96–99`; `outcome_accounting_contract.json:97–102`).
- The selected instrument path is 1-minute OHLCV (`instrument_contract.json:20–33`); no sub-minute source is declared in that contract.

**Implementation evidence and ambiguity**

- Both resolvers first determine whether High and Low touch both barriers. The engine's dual-touch branch runs before its single-touch open-gap handling (`triple_barrier.py:157–173`); the reference oracle likewise checks dual touch first (`reference_resolver.py:63–76`).
- The engine records an opening crossing via the `bar.open` comparisons (`triple_barrier.py:160–162, 203`) and uses the opening price for the selected stop side only in specified stop-gap cases (`triple_barrier.py:165–173`). A dual-touch bar that opens beyond the favorable barrier is still assigned the conservative stop-side result by the earlier dual-touch branch.
- The contracts settle unobservable same-bar dual touches but do not expressly say whether an observed bar open crossing is a chronologically known first touch that supersedes later high/low dual-touch ambiguity. “If sub-minute ticks exist” does not specify whether a bar-open observation alone is sufficient.

**Technically defensible alternatives and consequences**

1. Treat a barrier already crossed at the bar open as the first observable event, before resolving later intrabar extremes. This honors the open as a known point but requires exit-price/state semantics for an opening gap.
2. Apply conservative SL-first whenever the bar's full High/Low range touches both barriers, regardless of its open. This matches the current branch order and is conservative, but can disregard an open that already reveals a favorable barrier crossing.
3. Mark such bars separately as opening-gap/dual-touch unresolved and report bounds rather than force one primary ordering. This preserves ambiguity but requires an additional state/endpoint treatment.

**Safe recommendation (not contract):** Treat an opening price that crosses one barrier as the first observable event, then apply SL-first only to a later same-bar dual touch whose order is not observable. Require the owner to decide the gap exit price and state before using this rule.

**Approval required:** Yes; the existing frozen dual-touch rule does not fully settle this precedence.

**Exact owner decisions:** Does a barrier crossed at `Open` precede later High/Low touches? How is the opening-gap exit price represented? Does an opening gap that reaches one barrier followed by both-barrier High/Low extremes remain `SL_FIRST`, follow the known open event, or receive a distinct unresolved classification?

### 4. Timeout, missing candles, and incomplete horizons

**Explicit frozen facts**

- The primary horizon is 240 1-minute bars (`outcome_accounting_contract.json:82–86`). Timeout exits at the exact close of the 240th 1-minute bar and is not hard-coded to -1R (`PREREGISTRATION_v1.md:104–110`; `outcome_accounting_contract.json:91–95`).
- A missing fill bar fails closed as `DATA_GAP` (`entry_execution_contract.json:15–19`; `PREREGISTRATION_v1.md:58–60`). The intake manifest says gaps greater than tolerance fail closed but does not state that tolerance numerically (`data_intake_manifest.json:17–18`).
- `resolver_contract.md` is explicitly marked `DRAFT_CONTRACT — NOT SCIENTIFICALLY FROZEN` (`resolver_contract.md:1–8`); it is not used here to fill the frozen gap-tolerance omission.

**Implementation evidence and ambiguity**

- The pipeline skips an opportunity if the exact fill row is absent and builds at most 240 subsequent path bars (`run_full_research_pipeline.py:110–126`).
- The engine allows gaps of up to three missing minute bars between observed path bars and fails for larger gaps (`triple_barrier.py:129–136`). It uses up to 240 observed bars; if no barrier is touched, it fails only when fewer than 237 bars are present, otherwise times out at the last available bar's close (`triple_barrier.py:137–146, 318–355`). The oracle has the corresponding >240-second gap check and 237-bar cutoff (`reference_resolver.py:50–56, 208–246`).
- As written, a no-touch path with 237–239 observed bars can be called `TIMEOUT` before the stated 240th bar; a path with small internal gaps can extend past the stated 240-minute elapsed horizon while still counting 240 observed bars. The implementation therefore does not uniquely define whether the horizon is elapsed time or observed-bar count. A barrier hit before the coverage check is returned as an outcome even if later horizon bars are absent.

**Technically defensible alternatives and consequences**

1. Require the full 240-minute elapsed window through the contract endpoint for timeout; an incomplete no-touch path is `DATA_GAP`. This honors the exact 240th-bar timeout language but can reduce resolved cases.
2. Define the horizon as 240 valid observations and permit a specified number of missing candles. This retains more outcomes but can shift timeout in elapsed time.
3. Define a wall-clock endpoint and a separately frozen internal-gap tolerance; preserve early barrier resolutions only when the observed path up to the hit is sufficient. This is more explicit but needs both tolerance and event-order rules.
4. Convert missing fill-bar opportunities to a structured `DATA_GAP` outcome or preserve the current skip. The former is auditable; the latter loses the failed-fill count from the opportunity record.

**Safe recommendation (not contract):** Until the owner reconciles elapsed time with bar count, do not report an incomplete no-touch horizon as `TIMEOUT`; fail it closed as incomplete data. Record a missing eligible fill as `DATA_GAP`, rather than silently omitting it.

**Approval required:** Yes, especially to set the numeric internal-gap tolerance and reconcile current behavior with the exact timeout endpoint.

**Exact owner decisions:** Is the horizon 240 elapsed minutes or 240 valid path bars? What is the permitted internal missing-bar tolerance and is it consecutive or cumulative? Can 237–239 bars establish timeout? How are small gaps handled relative to the endpoint? May early barrier outcomes be accepted without full future coverage? Should absent fill rows yield a recorded `DATA_GAP`?

### 5. Entry/exit fees, spread, slippage, and embedded fill adjustments

**Explicit frozen facts**

- BASE specifies 10 bps entry and exit taker fees, 5 bps entry and exit slippage, 2.5 bps half-spread on each side, and a 35 bps total round trip. CONSERVATIVE specifies 15/15 bps fees, 10/15 bps slippage, 5 bps half-spread each side, and 65 bps total (`entry_execution_contract.json:21–41`; `PREREGISTRATION_v1.md:120–129`).
- Costs are positive deductions and net R subtracts the configured round-trip cost fraction (`outcome_accounting_contract.json:91–95`; `barrier_contract.py:35–62`).

**Implementation evidence and ambiguity**

- Contract construction adjusts the next 1-minute open in the trade direction by the scenario's entry-slippage amount and uses that adjusted value as `entry_price` (`triple_barrier.py:47–55`). Barriers are then anchored to that entry price (`triple_barrier.py:56–68`).
- Resolution also deducts the entire configured `total_round_trip_cost_fraction`/bps from gross outcomes (`triple_barrier.py:150–152, 181–182, 328–330`; `reference_resolver.py:58–60, 81`). Exit slippage, fees, and spread are not separately applied to the exit price in these paths.
- Consequently, entry slippage is represented in the fill-price basis and also included in the all-in round-trip deduction. Whether this is intentional double counting, or whether the aggregate deduction should exclude the embedded entry adjustment, is not stated. Nor does the contract define whether OHLC `Open` is a raw reference price to which spread/slippage should be applied or an already executable price. No quote-level data was inspected.

**Technically defensible alternatives and consequences**

1. Keep the observed/open reference price as the gross entry basis and deduct each configured cost once in aggregate. This is simple but leaves exit execution represented only by a cost proxy.
2. Keep the entry price adjusted for entry slippage and deduct only the remaining costs. This avoids counting that entry-slippage component twice, but changes the current all-in cost deduction.
3. Embed entry and exit execution adjustments in respective prices, then deduct only costs not embedded in those prices. This is leg-explicit but needs a consistent spread/slippage convention and can change outcomes materially.
4. Keep current arithmetic as intentional conservative stress, but label it as such and explicitly acknowledge that entry slippage is embedded and also deducted. This avoids an unapproved code change but does not resolve whether it matches the frozen accounting contract.

**Safe recommendation (not contract):** Adopt a component-by-component accounting table with each fee/spread/slippage component applied exactly once, identifying whether it changes a price or is deducted from gross return. Until approved, mark net accounting as unresolved; do not silently infer that the present all-in deduction excludes embedded slippage.

**Approval required:** Yes.

**Exact owner decisions:** Is the 1-minute `Open` a raw reference price or an executable fill price? Is entry slippage embedded in `entry_price`, included in the all-in round-trip deduction, or both intentionally? How are exit slippage and the half-spread applied? Are the BASE/CONSERVATIVE aggregates intended as a single deduction or componentized costs? Confirm whether current apparent entry-slippage duplication is intended.

### 6. Delayed A1 reclaim and confirmation

**Explicit frozen facts**

- `detector_spec.py` declares `reclaim_confirmation_window = 2` with the description “Must reclaim within 2 bars (30m)” (`detector_spec.py:16–23`).
- The registration document characterizes A1 as a sweep followed by an “immediate mean-reverting candle close inside range” and fixes the 24-bar swing window, 0.05%–2.0% sweep range, and four-bar cooldown (`setup_registration.md:8–16`).

**Implementation evidence and ambiguity**

- The detector checks the current 15-minute candle for a strict sweep and a close back across the swing level; it accepts the sweep-size endpoints inclusively (`setup_detector.py:87–108`). The event timestamp is that same current candle's timestamp (`setup_detector.py:143–145`).
- The detector does not read `reclaim_confirmation_window` or retain a pending sweep for later bars. In current code, A1 is same-candle sweep-and-reclaim; no delayed reclaim/confirmation event can be emitted.
- The frozen specification's “within 2 bars” does not state whether the sweep bar is included in those two bars, whether the next one or two closes can confirm, what invalidates a pending sweep, or whether the signal/decision time moves to the later confirmation close. Registration's “immediate” wording and current same-bar code do not settle the meaning of the two-bar parameter.

**Technically defensible alternatives and consequences**

1. Same-candle only. This matches the current implementation and “immediate” language but leaves the two-bar parameter unused and may exclude delayed setups.
2. Allow reclaim on the sweep candle or either of the next two completed candles. This uses the declared window but changes setup count, timestamp, feature snapshot, cooldown timing, and downstream eligible fill.
3. Count the sweep candle as the first of two bars, allowing only the next completed bar as delayed confirmation. This gives “within two bars” a narrower interpretation but is still not explicit.
4. Retain the sweep as pending only until a specified invalidation event or close; specify that event and whether a further adverse sweep resets or cancels it. This is more complete but needs additional frozen state-transition rules.

**Safe recommendation (not contract):** Do not emit delayed A1 signals until a state machine and event-time rule are approved. As a conservative interim interpretation only, retain same-candle confirmation and describe it as such; this does not resolve or implement the frozen two-bar window.

**Approval required:** Yes. The frozen detector specification and the registered/current behavior need reconciliation before labels are treated as the same setup definition.

**Exact owner decisions:** Does the two-bar window include the sweep candle? Which completed candle(s) may confirm? What exact close condition confirms? What invalidates/resets an unconfirmed sweep? Is the decision timestamp the sweep close or reclaim-confirmation close? When do features, cooldown, and order eligibility begin?

## Inspected paths and boundaries

**Contract and specification paths:** `research/entry_tp_sl/contract_freeze_manifest.json`, `decision_contract.json`, `entry_execution_contract.json`, `outcome_accounting_contract.json`, `instrument_contract.json`, `data_intake_manifest.json`, `PREREGISTRATION_v1.md`, `resolver_contract.md`, `resolver_decision.md`, `detector_spec.py`, and `setup_registration.md`.

**Implementation paths:** `research/entry_tp_sl/setup_detector.py`, `barrier_contract.py`, `triple_barrier.py`, `reference_resolver.py`, and `run_full_research_pipeline.py`.

No observations, sample rows, test files, manifests outside the listed contract metadata, or existing research reports were opened. No test, replay, network, or holdout operation was performed.

## Stop condition

This review ends at the owner-decision package. No implementation or contract changes are authorized by this report. Research experiment status, prospective evidence status, and model authorization are not evaluated here; live trading remains outside scope and disabled.

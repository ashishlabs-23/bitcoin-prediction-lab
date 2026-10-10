# Agent A — Data, Timestamps, and Resolver Audit

**Mode:** Read-only code audit. No experiment was run; no holdout outcome values were inspected.

## Findings

### High — 15-minute resampling creates unverified/partial decision bars
- **Evidence:** `run_full_research_pipeline.py:58-67` uses default left-closed, left-labelled `15min` resampling over close-stamped rows, then `.dropna()` without checking a 15-row count. The data manifest records `VERIFIED_60S_BAR_CLOSE` at `data_intake_manifest.json:16`; the preregistration requires 15-minute decisions at exact quarter-hour close boundaries in `PREREGISTRATION_v1.md:37-45`.
- **Impact:** Group membership and retained `Timestamp` can be offset from intended decision boundaries; non-null OHLC does not establish a complete 15-minute candle.
- **Reproduction:** Build 1-minute close-stamped rows at `:01` through `:30`, resample with the current expression, and inspect group membership/row counts and resulting decision timestamps.
- **Correction:** Resample close-stamped bars into right-closed/right-labelled quarter-hour windows; count expected source bars and exclude partial groups explicitly. Add boundary and partial-group fixtures.

### High — entry open maps to the wrong close-stamped row
- **Evidence:** The runner looks up `Timestamp == t0 + 60` and takes that row's `Open` at `run_full_research_pipeline.py:110-115`. For close-stamped data, the bar opening at `t0 + 60` is timestamped `t0 + 120`. The runner then starts path bars at `pos_fill + 1` at `:117-126`.
- **Impact:** Entry Open and path intervals are shifted relative to the registered `t_fill = t0 + 60` convention; the fill candle's post-open OHLC can be omitted.
- **Reproduction:** A fixture with explicit interval start/end and a touch in the fill candle shows current row lookup differs from the candle opening at `t_fill`.
- **Correction:** Map bar close timestamp to interval open explicitly; select the row with close timestamp `fill_timestamp + 60`, use its Open for fill, and include its OHLC as the first post-fill minute path bar.

### High — entry slippage is applied twice
- **Evidence:** `triple_barrier.py:51-58` adjusts the entry price by entry slippage; `triple_barrier.py:168-181` later subtracts the frozen total round-trip cost fraction, which already includes entry slippage in `FROZEN_COST_PARAMS` (`barrier_contract.py:35-54`). Preregistration specifies Open as fill-price basis and total fees/slippage/spread as deductions (`PREREGISTRATION_v1.md:49-60, 128-138`).
- **Impact:** Entry slippage is included in both the entry price and the aggregate cost deduction.
- **Reproduction:** Construct an entry at a known Open and compare realized net R with the accounting identity using one entry-slippage deduction.
- **Correction:** Keep the registered Open fill basis and deduct the aggregate frozen cost once, or formally revise accounting in a new preregistration.

### Medium — gap and horizon behavior differs between engine and oracle / registered policy
- **Evidence:** Engine gap detection uses integer division at `triple_barrier.py:128-135`; oracle rejects deltas greater than 240 seconds at `reference_resolver.py:45-53`. Engine counts observed bars toward horizon and allows `horizon_bars - 3` timeout bars (`triple_barrier.py:317-322`); the preregistration says gaps up to three minutes are forward-filled with zero volume and defines a fixed elapsed-time timeout (`PREREGISTRATION_v1.md:90-98, 211-213`).
- **Impact:** For off-cadence gaps, differential results can disagree; accepting fewer observations moves the timeout beyond the registered elapsed horizon.
- **Reproduction:** Differential test using timestamp deltas of 241 seconds; separate timeout fixture with permitted missing minutes and exact elapsed horizon.
- **Correction:** Implement one shared timestamp/gap policy matching the preregistration, including explicit synthetic zero-volume bars where prescribed, and test both resolvers.

### Verification status
- Dataset file was present and the targeted SHA-256 test passed during this audit.
- No contract file was modified. The run remains blocked pending repairs and gates.

# BTCognitive V36.1 — Trade Outcome Model Design

## Status

Design only. No model was trained, tuned, calibrated, or evaluated. The future model is a candidate-conditional outcome model, not a generic BTC direction forecast. Existing binary B4 implementations estimate an accept/reject target and cannot be relabeled as calibrated TP/SL/timeout class probabilities.

## Two-stage decision architecture

1. **Stage 1 — approved setup logic:** a frozen candidate generator proposes a timestamp, side, setup ID, reference price, and reason. Existing `StructuralSetupDetector` A1 sweep/reclaim and A2 range/reclaim are explicitly research candidates. Do not reactivate deprecated strategies or allow the stage-two classifier to invent direction.
2. **Stage 2 — candidate outcome model:** an independently versioned model consumes only PIT features available at decision time and estimates `P(TP_FIRST)`, `P(SL_FIRST)`, and `P(TIMEOUT)` conditional on the fixed candidate/contract. It may abstain; it cannot change the setup's side, entry rule, barrier geometry, or contract.

The trade evaluator must fail closed if the three class outputs are missing, malformed, not normalized, uncalibrated, or from the wrong model/contract version. Directional probabilities, volatility forecasts, heuristic regime confidence, and fixed range multipliers are not substitutes.

## Frozen candidate and outcome semantics already present

Use the existing research contracts as a starting point, not a new unregistered contract:

- Instrument: BTC/USD only; decision cadence is completed 15-minute bars on UTC `:00/:15/:30/:45`.
- Entry: signal is generated at the closed 15m decision-bar timestamp `t0`; marketable taker fill is modeled at the next 1m bar open, `t0 + 60 seconds`. Missing fill bar fails closed. Gap-open fills use actual open; >2% gap cancels.
- Side: long/short comes from the approved setup detector. No same-bar hindsight.
- Primary scale: `ATR_14_15M / Close_t0`.
- Primary barrier pair: TP 1.0x / SL 1.0x / 240-minute horizon. The frozen secondary grid defines other pairs/horizons; each counts as a separate model/configuration for multiplicity.
- Outcome labels: `TP_FIRST`, `SL_FIRST`, `TIMEOUT`. An unresolved same-candle dual touch is conservatively `SL_FIRST` and carries collision/unresolved-order metadata; run required TP-first sensitivity separately. Gaps exit using actual open semantics in resolver contract.
- Timeout: exit at horizon close, with realized gross R from signed price movement; never hardcode timeout as -1R.
- Position policy: maximum one open position per instrument; concurrent candidates abstain. No pyramiding, averaging down, trailing stop, partial exit, or dynamic barrier adjustment under frozen contract.
- Cost assumptions: frozen `BASE` 35 bps round trip and `CONSERVATIVE` 65 bps round trip. They are scenario assumptions, not measured current costs. Use exact entry/exit fee, slippage, and half-spread definitions in `entry_execution_contract.json`; do not tune costs to outcomes.
- Net R: frozen `gross_r - round_trip_cost_fraction/(sl_multiplier*sigma_t0)`.
- Data gaps/invalid contract/provenance failure are not one of the three outcomes. Return a failure/exclusion state with reason; do not silently map them to timeout.

## Causal feature and label construction

Feature cutoff equals the completed decision timestamp. Require `available_timestamp <= decision_timestamp`; no forming bar, post-fill bar, future target, or asynchronous record published later may enter features. Keep feature construction and path-resolution code separate. Persist labels with setup ID, decision/fill/outcome timestamp, barrier pair, resolver version, ambiguity flag, source hashes, and contract hashes. Use source coverage and gap checks; no synthetic 1m path from 15m/1h OHLC.

Overlapping candidates are handled under the frozen one-position rule: while a position is open, later candidates are rejected/abstained rather than treated as independent trades. For statistical evaluation, purge training labels whose complete outcome interval overlaps a validation/test interval, and embargo at least the maximum label horizon plus fill delay; also cluster remaining opportunities by overlapping/nearby episode. If a valid non-overlapping sample is too small, report insufficient effective sample size rather than weaken policy.

## Probability and decision output

The probability vector must satisfy finite values in `[0,1]`, sum-to-one tolerance fixed in advance, and model/data/contract identity. Report class probabilities with calibration state and uncertainty. Any EV calculation uses the registered class-specific net-R outcomes and frozen cost scenario; threshold is chosen only on training/validation data, then frozen before test. A candidate is rejected or `NO_TRADE` on absent source, failed risk/cost gate, unavailable class probability, or failed calibrated utility hurdle.

## Model lifecycle

No model gets promoted because it beats one historical slice. Require preregistration, exact source/model lineage, reproducible clean rerun, chronological walk-forward results, multiplicity adjustment, robust subgroup diagnostics, probability calibration and decision-utility evidence, independent review, then authorized prospective registration. Live trading remains disabled and outside this design.

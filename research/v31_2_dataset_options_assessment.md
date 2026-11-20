# BTCognitive V31.2 — Dataset Options Assessment

**Date:** 2026-10-23  
**Status:** Research-only assessment; no strategy implementation, no promotion, no live trading.

## Objective

Evaluate the viable dataset options without implementing new strategy logic. The purpose is to identify whether any single source can credibly satisfy the source, timing, and provenance gates.

## Option A — Remediate Bitstamp provenance and timestamp semantics

### Evidence currently available
- The Bitstamp dataset is structurally clean and has a local manifest and hash trail.
- A provenance template records unresolved timestamp and `available_time` fields.
- Historical G0 and V31.1 documentation show contradictory conclusions about the same source.

### Unresolved blockers
- Timestamp meaning is not fixed: open time, close time, bucket start, or available time are not consistently declared.
- Rights and usage scope are not resolved with a final, explicit source-chain record.
- The missing `available_time` contract prevents point-in-time validation.

### Research questions it could legitimately support
- A bar-level dataset with explicit `open`/`close` timestamps and a documented availability rule.
- A historical spot price study that does not claim intrabar TP/SL precision.

### Claims it cannot support
- Same-bar TP/SL resolution.
- A validated 1-minute decision path unless the exact timestamp and availability contract is proven.
- Any claim that the source is interchangeable with Coinbase or Binance data.

### Minimum evidence needed to proceed
- authoritative data-source metadata;
- clear timezone and open/close semantics;
- explicit research-permission wording;
- manifest + hash + timeline coverage check.

### Recommendation
- `UNSUPPORTED UNTIL RESOLVED`.

## Option B — Qualify Coinbase 15-minute data for a narrow 15-minute-context study

### Evidence currently available
- The dataset has a documented 15-minute bucket semantics.
- The adapter shows a bucket-start convention and a 15-minute feature cadence.
- This can support contextual research around a wider horizon, provided the path remains distinctly separate from the 1-minute entry contract.

### Unresolved blockers
- This is not a substitute for the preregistered 1-minute entry path.
- The local research permissions, source rights, and permitted-use chain are not fully established.
- The dataset cannot carry claims about intrabar or 1-minute barrier resolution.

### Research questions it could legitimately support
- 15-minute regime or context features.
- A study explicitly scoped to 15-minute decision windows.

### Claims it cannot support
- A 1-minute entry/TP/SL model.
- A source-equivalence claim with Bitstamp or Binance.

### Minimum evidence needed to proceed
- permission plus source provenance for the actual snapshot;
- explicit bucket semantics and source timezone capture;
- a frozen manifest and coverage summary.

### Recommendation
- `ALLOWED ONLY AS EXPLORATORY, 15-MINUTE CONTEXT STUDY`.

## Option C — Qualify a single Binance dataset as a completely separate research dataset

### Evidence currently available
- Binance BTCUSDT 1-hour candles are directly ingested with a clear timestamp and `available_time` rule.
- The repository has a distinct ingestion script for authentic Binance historical data.

### Unresolved blockers
- The active V12 strategy path labels the data as Coinbase BTC-USD, which is a venue mismatch.
- The project has not formally accepted Binance as the single, separate research dataset and not as a replacement for Coinbase or Bitstamp.
- The dataset’s legal-use scope and source provenance are not fully documented for this repository’s research contract.

### Research questions it could legitimately support
- a separate hourly BTCUSDT study with clear venue identity and a distinct instrument contract;
- a research path that avoids cross-venue substitution.

### Claims it cannot support
- a claim that it is the same dataset as Coinbase BTC-USD or Bitstamp BTC/USD;
- any direct 1-minute entry interpretation if the source is 1-hour only.

### Minimum evidence needed to proceed
- authoritative venue and symbol contract;
- source provenance and legal-use summary;
- manifest and gap/coverage reporting;
- separate holdout and replay gate for the Binance-only path.

### Recommendation
- `POSSIBLE ONLY AS DISTINCT, EXPLICIT BINANCE-ONLY RESEARCH PATH`.

## Option D — Stop dataset-dependent research until a defensible source is established

### Evidence currently available
- There is no single accepted source with fully resolved identity and timing semantics.
- There are direct contradictions across historical reports, data manifests, and downstream code assumptions.

### Unresolved blockers
- Source identity mismatch.
- Timestamp and availability rule conflicts.
- missing or invalid integrity baseline.
- unresolved rights and version provenance.

### Research questions it could legitimately support
- a careful evidence-gate investigation;
- source identity and manifest cleanup;
- isolated review before strategy work.

### Claims it cannot support
- any strategy, tournament, or performance claim.

### Minimum evidence needed to proceed
- a valid single-dataset contract recognized by independent review.

### Recommendation
- `BEST CURRENT POSITION`.

## Comparative recommendation

The most defensible choice is Option D as the current default. The repository is not ready for any source-dependent replay or strategy evaluation until one dataset passes all gates. Option B can be considered for an exploratory 15-minute context study only, and Option C can be considered only if a distinct Binance-only contract is formally registered. Option A remains blocked because the timestamp and rights questions are still unresolved.

## Final decision

**`BLOCKED — SOURCE OR CONTRACT UNVERIFIED`**.

The project should remain in research-only, no-promotion mode until a single accepted dataset has passed the G1–G11 acceptance checklist.

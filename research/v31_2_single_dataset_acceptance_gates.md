# BTCognitive V31.2 — Single-Dataset Acceptance Gates

**Date:** 2026-10-23  
**Status:** Research-only gatebook; no strategy work, no live behavior, no dataset promotion.

## Purpose

This document defines the minimum evidence required before any single dataset may be used for isolated replay or historical research. The goal is to prevent venue mismatch, point-in-time leakage, and performance claims that are unsupported by the actual source contract.

## Gate definitions

### G1 — Venue and instrument identity
- **Pass criterion:** one source is uniquely identified end to end as a single venue/instrument/market-type combination.
- **Evidence required:** explicit source name, symbol, quote currency, market type, and artifact mapping.
- **Verification method:** compare file path, source metadata, exchange symbol, instrument design, and contract assumptions.
- **Approver:** research lead + data provenance reviewer.
- **Failure disposition:** fail closed; do not treat the source as interchangeable with any other venue or product.

### G2 — Timestamp semantics
- **Pass criterion:** timestamp meaning, timezone, timezone conversion, and interval boundaries are fully documented and consistent with the actual source.
- **Evidence required:** source documentation or primary source evidence for the timestamp field, timezone offset, `open_time`, `close_time`, or bucket semantics, and the chosen `available_time` rule.
- **Verification method:** inspect raw columns and source docs; verify whether timestamps are open, close, or bucket-start, and whether a decision time is before or after the bar close.
- **Approver:** replay reviewer.
- **Failure disposition:** fail closed; do not infer a time convention when unresolved.

### G3 — Point-in-time availability
- **Pass criterion:** all features and labels are built only from information known at the simulated decision time.
- **Evidence required:** `available_time` or equivalent decision-time rule, processed time semantics, and explicit timing between ingestion and feature generation.
- **Verification method:** check the contract for whether a bar is eligible only after it is completed and after it is available in the source feed.
- **Approver:** causal design reviewer.
- **Failure disposition:** fail closed; any future or same-bar claim is rejected unless the contract is explicit and verified.

### G4 — Data integrity
- **Pass criterion:** duplicates, ordering, missing bars, gaps, malformed rows, and coverage boundaries are measured and documented.
- **Evidence required:** row counts, first/last timestamps, missing-bar counts, duplicates, null/NaN checks, and coverage intervals.
- **Verification method:** run deterministic data checks that fail on duplicates, ordering issues, or gaps not explicitly allowed by protocol.
- **Approver:** data integrity reviewer.
- **Failure disposition:** fail closed; do not proceed with a source that cannot show coverage boundaries and missing-bar handling.

### G5 — Provenance and permitted use
- **Pass criterion:** the exact artifact version, source chain, date of acquisition, and permitted research scope are documented.
- **Evidence required:** manifest file, source URL or canonical provider, acquisition date, licensing or terms, and version ID.
- **Verification method:** verify artifact hash plus source record; if rights or scope is unclear, treat as not eligible.
- **Approver:** repository owner + research governance reviewer.
- **Failure disposition:** fail closed; no research use without documented permission.

### G6 — Deterministic replay
- **Pass criterion:** identical inputs and configuration produce identical outputs under a frozen data manifest and time bounds.
- **Evidence required:** source hash, manifest hash, ordered `timestamp` sequence, deterministic config hash, and reproducibility check results.
- **Verification method:** rerun the replay on the same manifest and confirm identical outputs or event-level decisions.
- **Approver:** replay and reproducibility reviewer.
- **Failure disposition:** fail closed; no ambiguous or non-deterministic replay path.

### G7 — Holdout integrity
- **Pass criterion:** all splits are chronological, time-bound, and do not leak information across feature generation, labels, or model selection.
- **Evidence required:** holdout dates, purge rules, and explicit blocking of future information.
- **Verification method:** verify feature windows, label horizons, and validation/test boundaries are separated and non-overlapping by the chosen protocol.
- **Approver:** statistical governance reviewer.
- **Failure disposition:** fail closed; no evaluation using contaminated splits.

### G8 — Barrier-resolution limitations
- **Pass criterion:** the contract clearly states what the chosen data granularity can and cannot establish about TP/SL ordering and same-bar outcomes.
- **Evidence required:** explicit statement of whether the source resolves intrabar or only bar-level events.
- **Verification method:** compare the source granularity to the research question and to the barrier logic.
- **Approver:** research lead.
- **Failure disposition:** fail closed; a bar-level path cannot be claimed as an intrabar path.

### G9 — Execution-cost assumptions
- **Pass criterion:** fees, spread, slippage, funding, and fill assumptions are separated into observed, sourced, or hypothetical scenarios.
- **Evidence required:** instrument-specific cost scenarios and the exact assumptions attached to each one.
- **Verification method:** verify that the cost model is tied to a single instrument contract and not mixed across venues/products.
- **Approver:** economics reviewer.
- **Failure disposition:** fail closed; hypothetical or cross-venue cost assumptions cannot be treated as proven execution quality.

### G10 — Integrity baseline
- **Pass criterion:** protected-file tracking and repository state are anchored to a valid baseline and hash provenance.
- **Evidence required:** valid SHA-256 and a traceable file inventory at the start of the research milestone.
- **Verification method:** confirm the hash matches a known-good baseline and that protected files were not mutated.
- **Approver:** repository integrity reviewer.
- **Failure disposition:** fail closed; missing or malformed baseline evidence blocks the milestone.

### G11 — Independent review
- **Pass criterion:** each gate must be independently reviewed rather than accepted by the same code path that consumes the dataset.
- **Evidence required:** a human or independent reviewer sign off on each gate and the documented evidence.
- **Verification method:** review records, source evidence, and issue logs.
- **Approver:** independent red-team reviewer.
- **Failure disposition:** fail closed; no self-assertion is accepted as proof.

## Current status

| Gate | Status |
|---|---|
| G1 | FAIL |
| G2 | UNVERIFIED |
| G3 | UNVERIFIED |
| G4 | PARTIAL |
| G5 | FAIL |
| G6 | UNVERIFIED |
| G7 | UNVERIFIED |
| G8 | UNVERIFIED |
| G9 | UNVERIFIED |
| G10 | FAIL |
| G11 | UNVERIFIED |

## Decision

No dataset is approved for isolated replay yet. The single-source acceptance contract must be satisfied before any research proceeds beyond audit and documentation.

## Safe next action

1. Choose exactly one source candidate.
2. Freeze its source identity, timestamp semantics, and `available_time` rule.
3. Create the manifest and hash evidence.
4. Re-run the gate checklist with independent review.
5. Only then move to isolated replay.

This is a documentation gate, not an authorization to tune strategies or claim a valid edge.

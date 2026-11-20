# BTCognitive Research Integrity Decision

**Decision date:** 2026-11-05  
**Overall research integrity state:** `INCONCLUSIVE`; milestone `BLOCKED`.

## Standard HAR identity and forecasting performance

- Registered model identity: `Standard-HAR-v1.0`, Standard Corsi HAR-RV volatility baseline.
- Artifact: expected path `experiments/results/freeze/standard_har_v1.joblib`; exact original artifact not found.
- Artifact hash / scientific-contract hash: unavailable. Former registry placeholders were not verified digests.
- Runtime registry state: `UNAVAILABLE_BLOCKED`; no inference or performance attribution is permitted.
- `HAR-RS-DOW-v1.0` is a distinct, unpromoted research challenger. It is not a substitute Standard HAR artifact.
- Standard HAR out-of-sample performance: **NOT ESTABLISHED**.
- The archived 52.14% one-hour directional result is neither current Standard HAR performance nor prospective evidence.

Volatility forecasting metrics must not be interpreted as directional return accuracy or trading profitability. No model promotion, statistical gate relaxation, or holdout-based model selection occurred in this remediation.

## Entry/TP/SL point-in-time timing

Source timestamp role and availability-time semantics are unresolved. The dataset template states timestamp role unknown/unverified; the intake record does not establish raw timestamp semantics or an availability rule; the frozen contract uses the close of a completed 15-minute bar. Existing resampling defaults and last-row timestamp aggregation do not prove admissible decision/fill timing.

The production pipeline now fails before reading the CSV or generating features, labels, outcomes, ledger entries, or reports. It does not accept a caller-created `verified=True` timing contract as authorization. Fixture-only feature calculations remain separate. Resampling (`label`, `closed`, `origin`), raw-to-decision timestamp mapping, availability aggregation, and the frozen `t0 + 60s` fill mapping remain **blocked** pending authoritative source evidence and owner approval.

## R1 data identity

`data/raw/ohlcv.parquet` remains unchanged from its saved preflight digest: `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057`. The protected-data test expects `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f`. The file is ignored/untracked and no authoritative approved source manifest resolves the discrepancy. Preserve both file and assertion; do not claim R1 integrity PASS until provenance is reconciled.

The full Python suite also reported that `models/checkpoints/meta.pt` and `models/checkpoints/regime.pt` changed during execution. Individual pre-run hashes were not included in preflight, so their prior contents and attribution cannot be established. Their current digests are recorded in `BTC_WORKTREE_BASELINE.json`. Do not load, restore, overwrite, or rely on these artifacts until an authorized owner resolves the integrity event.

## Calibration, regimes, and evidence

- C2 calibration: unavailable; no calibrated coverage claim is made.
- Excursion outputs: `UNVALIDATED_HEURISTIC` unless independently supported by their own validation gate.
- Prospective evidence: 0 clean prospective blocks reported; state `NOT_STARTED`.
- Existing historical/replay evidence remains retrospective and is not confirmatory.
- The full suite's protected hash failure and broad failures prevent declaring the entire analysis/research pipeline validated.
- No provider connection, live market request, external-network permission, broker, order placement, or capital execution was used.

## Governance decision

| Decision | State |
|---|---|
| Research experiment | `INCONCLUSIVE` |
| Prospective evidence | `NOT_STARTED` - 0 clean blocks |
| Model authorization | `OFFLINE_RESEARCH_ONLY` |
| Live trading | `DISABLED` |
| Standard HAR measured forecasting performance | `NOT ESTABLISHED` |

Owner evidence/approval required before confirmatory HAR evaluation: exact original Standard HAR artifact and provenance, reproducible evaluation protocol, and explicit resolution of the checkpoint and OHLCV integrity records.

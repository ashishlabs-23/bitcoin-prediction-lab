# Agent E — Provenance and Reporting Audit

**Mode:** Read-only audit. No report was regenerated; holdout outcome values were not inspected.

## Findings

### High — repeated trial IDs conflate different runs
- **Evidence:** `trial_ledger.jsonl` contains 17 valid hash-chain entries, but IDs repeat, including `TRIAL_B0_RANDOM_P01` (events 1 and 9) and `TRIAL_B4_LIGHTGBM_BASE_P01` (events 7 and 15). The latter records count 0 and later count 1,553. Runner constructs deterministic IDs at `run_full_research_pipeline.py:350-361`.
- **Correction:** Give each run a unique immutable ID; key trial events by run ID and reject duplicate IDs or represent retries/supersession explicitly. Preserve old rows.

### Medium — model ledger rows do not bind results to frozen inputs/configuration
- **Evidence:** Root ledger record stores initial hashes, but model records lack run-specific dataset, contract, code, environment, result artifact and barrier configuration hashes. Existing writer now snapshots `barrier_configuration` at `walk_forward_engine.py:65-68`, but historical rows remain unchanged.
- **Correction:** Each new run/trial event must record run ID, input/code/environment/config hashes, model parameters, threshold, fold dates, counts and result artifact hash.

### Medium — report claims conflict with its own conclusion and code
- **Evidence:** Report's B3 row says “Confirmed” (`final_research_report.md:44`), but its conclusion admits no significance test (`:63`). Generator hardcodes that label at `run_full_research_pipeline.py:455`.
- **Correction:** Report descriptive comparisons unless a registered test and adjusted p-value support a confirmatory claim.

### High — custody status is false relative to runner behavior
- **Evidence:** Runner processes all paths before splitting (`run_full_research_pipeline.py:101-202`), prints holdout count and writes `SEALED_UNTOUCHED` (`:365-375`). This establishes code access, not whether the outcome metrics were used to tune.
- **Correction:** Reclassify as `HOLDOUT_CUSTODY_UNVERIFIED`; prevent future development pipeline reads/writes of holdout records; preserve a dated audit event.

### Medium — report and generator status are inconsistent
- **Evidence:** Current report/decision say metrics were not regenerated and are unverified; generator embeds a C2 claim and different promotion status (`run_full_research_pipeline.py:416-418`) and overwrites report/decision (`:478-497`).
- **Correction:** Fail closed on missing validated run artifact; render claims only from verified result/provenance objects.

## Verified facts
- The trial ledger's existing parent-hash chain and event indexes were valid on inspection.
- Dataset hash test passed in this audit; no holdout values were read.

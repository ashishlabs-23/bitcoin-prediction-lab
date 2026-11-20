# BTCognitive V36.3 — Manager Gate Decision

## Decision summary

The existing Entry/TP/SL workstream is **reusable**, and the previously reported resolver hash discrepancies are resolved as Windows line-ending normalization. However, the full data-to-label pipeline is **not yet reproducible or contract-conformant**. The primary evidence blocker is the unverified provenance and open/close timestamp role of the 1m dataset; that uncertainty changes the execution-bar mapping. Contract decisions about costs, gap tolerance, spot shorts, and detector semantics also remain. Historical holdout custody is `UNVERIFIABLE`, and published results cannot be reconciled to a reproducible cohort.

### Phase feasibility choices

| Choice | Decision | Reason |
|---|---|---|
| A. Reproducible and contract-conformant | **No** | Static source shows entry mapping, entry-gap cancellation, open-gap collision order, path completeness/horizon, and cost-accounting deviations. No tests or run were performed to prove otherwise. |
| B. Reusable after a narrow resolver correction | **Not yet approvable** | Core resolver bytes are recoverable, but the required fix is not resolver-only: dataset timestamp semantics, 15m resampling, entry-row selection, cost representation, gap policy, and A1 confirmation require evidence or owner decisions. |
| C. Blocked by unavailable data provenance | **Yes — critical path** | The CSV hash matches local manifests, but source authenticity and exact timestamp role are not established by original acquisition records. The choice of close-vs-open semantics changes both `t0+60s` entry price and first path bar. |
| D. Blocked by irrecoverable implementation or holdout provenance | **Partly** | Resolver source implementation is recoverable from Git; it is not irrecoverable. Old holdout custody remains unverifiable and should not be used as confirmatory evidence absent independent access evidence. |

## Exact blockers

1. **Data evidence:** `provenance.template.json` has no source commit, immutable source object, digest, timestamp role, or availability rule; `dataset_manifest.template.json` says the archive was not present when candidate provenance was created. Later `data_intake_manifest.json` claims the 1m file is a verified close-stamped snapshot, but the repository contains no original acquisition payload or source-side proof. The data classification remains `UNVERIFIED`.
2. **Entry-time mapping:** `instrument_contract.json` says close-stamped minute rows; `run_full_research_pipeline.py::run` uses the row timestamped `t0+60s` Open as fill. That Open is pre-fill under interval-close labeling. If labels are interval-open instead, the same code skips the first post-fill bar. A source/timestamp decision must precede the correction.
3. **Contract owner decisions:** The 2% entry-gap reference price, short-sale admissibility on BTC/USD spot, allowed missing-bar tolerance, price rounding, and cost treatment need explicit choices. Current `build_trade_contract` has no decision-close input, applies entry slippage to price, and later subtracts total friction including that slippage.
4. **Holdout and result lineage:** The holdout is not independently isolated; the current pipeline computes full-sample outcomes before partition. The report’s hard-coded 3,842 opportunity claim conflicts with N=20,244; duplicate trial IDs have changed B4 counts from zero to 1,553 and B4-lite from 216 to 2,916; the promotion expectancy range conflicts with final report/ledger values. None is suitable as a verified performance result.

## Smallest justified next task

**Do not begin code changes yet.** The smallest next task is a bounded **evidence-and-owner-decision closure** (no replay, model work, or frozen-file edits):

1. Locate within already-authorized local project records the exact Kaggle v745 acquisition identity and timestamp-role documentation; establish whether CSV timestamps denote interval open or close and define availability time. If evidence does not exist, record `UNVERIFIED`/reject this CSV for confirmatory labels rather than infer semantics.
2. Obtain owner decisions for entry gap denominator, short spot treatment, gap tolerance, tick rounding, and whether frozen costs are applied once to raw Open or partly embedded in execution price.
3. Freeze a mapping table for `t0`, 15m aggregate timestamp, fill bar Open, and first path row. Check it against the immutable contracts without rewriting them; any contract change requires a dated, auditable amendment rather than silent edits.
4. Mark the existing 2025–2026 holdout unavailable for confirmatory use unless independent custody/access logs establish it was not exposed. The accessible CSV and generated labels cannot be retroactively made sealed.
5. Preserve old reports and ledger entries; record their counts and results as unreconciled historical claims. Do not rerun the current output-writing pipeline to “settle” them.

### First code task after the evidence gate

If steps 1–3 close, authorize one isolated contract-conformance change to the **existing** `research/entry_tp_sl` path (not a new resolver): align resampling and fill lookup to the verified timestamp role; enforce entry-gap cancellation and one-time cost accounting; resolve opening gaps before dual-touch ambiguity; enforce the ratified path-gap and exact-horizon rules; align A1 with its frozen confirmation window; preserve fail-closed statuses. Add the synthetic fixtures in `V36_3_FROZEN_CONTRACT_CONFORMANCE.md` as deterministic acceptance tests. Keep product `engine/barrier_resolver.py` and its Coinbase assumptions separate. Output must go to a new disposable location and must not overwrite manifests, ledgers, holdout artifacts, or protected databases.

Before any evaluation, separately reconcile the old trial records and preregister a source/code/config/environment identity, purge/embargo, calibration separation, overlap accounting, and dependence-aware precision plan. If the historic holdout is unverified, it cannot be used to confirm a model.

## Governance and claims

- Research experiment: `INCONCLUSIVE` — no experiment was executed in V36.3.
- Prospective evidence: `NOT ESTABLISHED` by this audit.
- Model authorization: `OFFLINE_RESEARCH_ONLY`.
- Analysis mode: `ANALYSIS_ONLY`.
- C2: disabled.
- Live trading, broker integration, and order placement: disabled.
- Standard HAR accuracy: `NOT ESTABLISHED`.
- No research validation, profitability, predictive accuracy, or production readiness is claimed.

BLOCKED — PRECISE EVIDENCE OR CONTRACT DEFICIENCY

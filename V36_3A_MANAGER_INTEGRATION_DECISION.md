# BTCognitive V36.3A — Manager Integration Decision

## Primary decision

**BLOCKED — ORIGINAL DATA PROVENANCE UNVERIFIABLE**

The existing research architecture remains technically reusable, but it is not ready for market-data outcome labels or a new confirmatory evaluation. The critical unresolved issue is the one-minute file’s source chain and timestamp role: its digest binds the local bytes to repository manifests, but does not authenticate the provider or prove interval-open/close semantics. That ambiguity changes the row used for `t0+60s` fill and the first path observation.

## Independent reconciliation of specialist findings

| Workstream | Specialist conclusion | Main-agent independent cross-check | Integrated assessment |
|---|---|---|---|
| Agent A — data provenance | Local digest match; Kaggle/Bitstamp claim and timestamp semantics remain unverified; repository records conflict. | Recomputed current CSV digest and size: `1bf91f…d1287`, 393,952,273 bytes. Verified intake manifest matches. Compared `instrument_contract.json` close-stamp assertion against candidate/provenance templates’ unknown/null semantics and G0’s prior unavailable statement. | **Agreed.** `UNVERIFIED` is the correct dataset classification for source authenticity and event/availability-time semantics. Structural validity is not a substitute. |
| Agent B — resolver/contracts | CRLF/LF normalization explains two raw digest differences; source bytes recoverable; recorded commit pointer is wrong. Identified gaps in fill mapping, 2% gap, open-first collision, incomplete horizon, costs, PIT, A1 window, and short semantics. | Directly checked `core.autocrlf=true`, normalized hashes, `git ls-tree` for `cd1017…`, current `run_full_research_pipeline.py` row indexing, resolver cost and horizon logic, and frozen contract fields. | **Agreed with nuance.** This is not a corrupted or irrecoverable resolver. No correction should start until timestamp semantics and the listed owner decisions are frozen. Exact-horizon and first-path checks are required by the frozen horizon; opening-gap priority and cost representation need explicit interpretation to avoid silent policy changes. |
| Agent C — claims/custody | Custody `UNVERIFIABLE`; counts and B4 claim conflict; pilot aggregate not independently verified; no prospective sample proved. | Cross-checked `final_research_report.md`, `PROMOTION_DECISION.md`, ledger repetitions, and runner’s sequence: construct all labeled records, select trades, partition by date, fit on research partition, then write custody manifest. No holdout row/sample was opened. | **Agreed.** Do not treat prior results as reproducible or the old holdout as confirmatory. Code structure undermines isolation claims, though no evidence establishes exactly who inspected which heldout labels. |

No material contradiction among specialists changes the primary decision. “Unverified” does not mean the data is fabricated; it means the source/semantics have not been independently evidenced. The resolver hash issue is explained; the manifest’s commit pointer and test-execution evidence remain defects in provenance metadata.

## What data provenance blocks

The provenance issue blocks **admissible label generation and confirmatory performance claims based on this CSV**. It does not block:

- Static engineering work that does not use market outcomes.
- Synthetic, deterministic contract tests after semantic decisions.
- Reconstructing the existing source bytes from Git.
- A future dataset-based study using another dataset with verified BTC/USD instrument, source/provider, timestamp semantics, interval availability, and complete provenance.

It would be misleading to make labels from the present file and call them verified Bitstamp outcomes. No current Coinbase hourly file substitutes for Bitstamp 1m path data.

### Evidence needed to unblock data

Use already-authorized local evidence or provide an equivalent source package:

1. Immutable Kaggle v745 source archive/object identity and source-side digest tied to the local CSV digest.
2. Publisher/updater source revision and acquisition record that explain exactly how the file was obtained.
3. Authoritative timestamp definition for this exact export: bar-open or bar-close, UTC, and `available_time`.
4. A hash-bound structural report for duplicates, missing/irregular intervals, OHLC constraints, and explicit tolerance.
5. A timestamp-to-contract mapping for each 15m decision close, its fill Open at `t0+60s`, and subsequent path intervals.

If unavailable, the alternative is a new, provenance-bearing 1m BTC/USD source snapshot with explicit bar semantics. Do not assume Kaggle metadata, a filename, or a hash is sufficient; do not silently substitute another venue.

## Exact contract-owner decisions required

Resolve these in a dated decision record before code changes; do not invent answers:

1. **Entry gap:** reference price/denominator for the 2% comparison and treatment at exactly 2.00%.
2. **Slippage accounting:** whether the execution price remains the raw next-bar Open and all 35/65 bps are deducted once, or whether entry slippage is embedded in price with a correspondingly reduced residual friction deduction.
3. **Path gaps:** whether any missing path minute invalidates the outcome, or the exact allowed consecutive-gap tolerance and how the vertical horizon is measured when gaps occur.
4. **Opening gap vs same-bar collision:** whether an observable Open already beyond a barrier resolves first before SL-first is applied to genuinely unobservable intrabar order.
5. **Spot shorts:** whether short labels are purely hypothetical or whether a specific spot borrowing mechanism, eligibility, and cost are in scope.
6. **Price rounding:** whether entry/barriers are quantized to the instrument’s $0.01 tick before touch logic.
7. **A1 confirmation:** whether the two-bar window includes the sweep bar and exactly which subsequent bars may confirm; current code only accepts same-bar sweep/reclaim.

Frozen 240/120-bar timeout endpoints, realized timeout R, side-specific barrier geometry, and fail-closed missing fill are already stated. Their implementation should conform; do not amend these contract terms to accommodate code.

## Holdout and historical evidence gate

Custody classification remains **`UNVERIFIABLE`**, not `VERIFIED`. The available record declares a sealed interval but supplies no access history or separate object. The current runner constructs outcomes before date partitioning, so it is not a holdout protection mechanism. Existing reports provide conflicting denominators and metrics; no corrected performance result is selected.

Treat the 2025–2026 interval as **not available for confirmatory claims** unless independent access logs, object boundaries, and a valid protocol demonstrate non-exposure. Because its raw source is present and code generates outcomes before partition, a claim of `SEALED_UNTOUCHED` cannot be accepted from the manifest alone. Future confirmatory evidence requires a genuinely segregated or prospective dataset, not a retroactive rewrite of the old custody assertion.

## Dependency-ordered plan

### Gate 1 — Close provenance (no code changes)

- Obtain the source evidence above and identify interval timestamp role.
- If impossible, formally retain `UNVERIFIED` and source a separately documented dataset before any outcome labels.
- Keep all old output and frozen records unchanged.

### Gate 2 — Record owner decisions (no implementation yet)

- Ratify the seven interpretation items above without rewriting frozen files.
- If any decision changes a frozen requirement, create an auditable, dated amendment outside the protected frozen artifacts, with explicit versioning and sign-off.

### Gate 3 — Narrow correction in existing `research/entry_tp_sl` path

Only after Gates 1–2: align 15m resampling and minute fill/path selection; enforce the 2% gap rule; make first-path and exact 120/240-minute completeness explicit; resolve observable opens before ambiguous collisions if ratified; account for execution costs once; enforce PIT availability; and implement the frozen A1 confirmation semantics. Do not create a second resolver or conflate the product `engine/barrier_resolver.py`.

### Gate 4 — Synthetic acceptance, then reproducible isolated evaluation design

- Add the specialist’s deterministic synthetic edge cases for long/short, exact touches, gaps, collisions, missing first/interior bars, exact horizon, cost accounting, PIT future-perturbation, A1 window, and gap threshold.
- Only then design a non-mutating evaluation runner with unique run identity and new isolated output location; never rerun the current pipeline that writes reports, holdout manifest, prospective readiness, and ledger.
- Before any evaluation, preregister cohort/overlap definitions, chronological folds, purge/embargo, calibration separation, inference method, and a valid holdout boundary. Do not use the existing unverifiable holdout.

### Gate 5 — Research evidence

Any later run is retrospective research only unless it uses untouched/segregated confirmatory evidence. Reconcile trial IDs and old sample definitions without overwriting prior reports. No model training, calibration, promotion, C2, or production authorization is approved by V36.3A.

## Specialist completion

- **Agent A — BTCUSD Data Provenance:** complete; dataset `UNVERIFIED`.
- **Agent B — Resolver and Frozen Contract:** complete; source hashes explained/recoverable, commit pointer incorrect, contract fixes gated by evidence and owner decisions.
- **Agent C — Holdout and Statistical Claims:** complete; custody `UNVERIFIABLE`, several claims `CONFLICTING`, no replacement result calculated.
- **Main agent:** independently cross-checked the digest, repository baseline, recorded commit tree, source timestamp/cost/horizon logic, and holdout/report claims; integrated all three findings.

## Integrity and scope verification

Before any work, baseline was branch `milestone/v35.3-critical-remediation`, HEAD `25d483f4c3646661b57311de9d0b53d2be881adb`, 1,708 Git status entries, and 409 protected-file hashes. Final comparison: all pre-existing status entries unchanged; only the four V36.3A reports added; all 409 protected hashes match; branch and HEAD unchanged. No tests, replay, training, network calls, holdout-observation inspection, or protected-file writes occurred.

**Governance:** `OFFLINE_RESEARCH_ONLY`; `ANALYSIS_ONLY`; C2 disabled; live trading, broker integration, and order placement disabled. No accuracy, profitability, or production-readiness claim is made.

BLOCKED — ORIGINAL DATA PROVENANCE UNVERIFIABLE

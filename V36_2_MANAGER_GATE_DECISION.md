# BTCognitive V36.2 — Manager Gate Decision

## Executive determination

Some of the existing architecture is reusable, and the repository contains enough local OHLCV to make further historical work feasible in principle. It does **not** presently support a defensible re-run or a probability-model evaluation: the minute-source semantics are unresolved, current resolver hashes do not match the implementation manifest, frozen contract rules are not all implemented, holdout custody is unproven, and prior sample/performance records conflict.

### Answers to the manager’s questions

1. **What already works at code level?**  
   Frozen V3 trade contracts are detailed and their declared file hashes match. A 15m A1/A2 candidate detector, PIT-feature builder, research triple-barrier resolver, independent reference resolver, baseline classifiers, product outcome evaluator, risk components, and a long 1m BTC/USD-declared local file all exist. A number of tests target these areas, but they were not run here. The product evaluator appropriately abstains if outcome probabilities are missing.

2. **What is specified but not implemented?**  
   The frozen entry-gap cancel rule is not enforced by the research builder; the A1 two-bar confirmation rule is not implemented as specified; exact incomplete-path/horizon and gap-first semantics need enforcement; TP-first sensitivity, purge/embargo, untouched holdout custody, complete run provenance, and a calibrated three-class outcome model are not established. Standard HAR’s registry identity is not backed by a local artifact.

3. **What is implemented but lacks validation?**  
   The detector, PIT calculations, barrier code, costs/accounting, classifiers, regime and risk features, and monitoring are implemented to varying degrees. Test files and old manifests do not validate current bytes. The 6B hashes for two current resolvers mismatch; no V36.2 tests or full runner were executed.

4. **Which features can run with admissible data?**  
   Conditional historical OHLCV calculations can run on a matching cadence after timestamp and provenance requirements are enforced. The Coinbase V2/V3 hourly data is the strongest long-span hourly source, with 13 explicit gaps and a data identity different from frozen HAR-RS-DOW training. The 15m Coinbase file supports a shorter, different-venue calculation. The 1m file hash matches the V3 intake manifest and is structurally continuous; source authenticity and candle-time semantics still gate outcome labels. No live/current-market, order-book, derivatives, liquidation, or on-chain features are supported by this audit.

5. **Which features are blocked by missing or incompatible data?**  
   L2/microstructure, funding/OI, liquidations, sentiment/on-chain, and current provider retrieval. Standard HAR is blocked by its absent artifact. HAR-RS-DOW’s artifact bytes are identified but its training OHLCV digest does not match current raw data and IV7d input is absent. Hourly data cannot substitute for 15m decisions or 1m path labels.

6. **Is the existing entry/exit research architecture reusable?**  
   **Yes, as the single existing starting point, not as a validated runnable pipeline.** Reuse the frozen V3 contract, `research/entry_tp_sl/setup_detector.py`, `pit_features.py`, and `TripleBarrierEngine`/reference oracle after reconciliation. Do not substitute `engine/barrier_resolver.py`, whose product contract differs. Do not reuse the existing B4 metrics or holdout claims as validated evidence.

7. **What is the single most important blocker?**  
   There is no reproducible, auditable tuple linking the present data bytes and candle semantics, frozen contracts, current resolver implementation, protected holdout, run configuration, and reported outcomes. Until that is established, neither old performance claims nor newly generated labels are trustworthy.

8. **What exact next implementation task is justified?**  
   After lineage/custody clarification, make a **contract-conformance correction to the existing `research/entry_tp_sl` path only**: enforce the frozen A1 confirmation and entry-gap/cost semantics; fix first-forward-bar gap ordering and exact horizon/incomplete-path handling; add deterministic tests including TP-first sensitivity; then provide a non-mutating runner specification with isolated output paths. No new model, feature combination, training, promotion, product integration, or replay is justified yet.

9. **What evidence must pass before that task can begin?**  
   - Written source and candle-open/close timestamp reconciliation for the hash-pinned 1m CSV against the frozen entry contract; if not verifiable, document rejection/downgrade rather than assume.
   - Resolve the frozen 35/65 bps accounting interpretation and confirm the intended A1 confirmation/candidate rules without changing the historical contract silently.
   - Establish whether the old holdout was truly isolated; if not, mark it exposed and not confirmatory.
   - Preserve and map the existing report/ledger contradictions to exact input, source and configuration versions; append an auditable reconciliation, never rewrite old results.
   - Define an isolated test/output location and verify the planned implementation cannot touch the prospective ledger, market-memory DB, frozen datasets/manifests, or holdout.

## Feasibility selection

**Critical path: D — blocked pending precise dataset/contract/evidence lineage resolution, followed by C — reuse and validate the existing entry/exit pipeline.** This does not mean creating another pipeline or changing the frozen contract. A separate hourly volatility analysis could later use a suitable, explicitly selected hourly dataset, but it does not unblock V3 trade outcome work or Standard HAR evaluation.

The local V3 1m dataset is byte-consistent with its intake manifest, but independent acquisition and candle-boundary semantics are not established by the audit evidence. The two lineages must not be conflated: the user-reported Bitstamp identity is manifest-declared; verified Coinbase V2 is a separate venue/source. The 1m label path is therefore promising but not yet admissible as definitive outcome evidence.

No sample-count threshold is introduced. Existing `feasibility_audit.md` and `research.md` state different sample-size figures (250 trades versus an illustrative ~620 IID trades for a 0.10R effect at one-sided 5% alpha/80% power). Before evaluation, reconcile the preregistered MDE and desired precision, then derive a block/cluster-aware effective sample and confidence-interval plan using development data only. A raw trade count is not an independence guarantee.

## Governing status

- **Research experiment:** `INCONCLUSIVE` — no experiment/replay was run; prior evidence conflicts and is not reproduced.
- **Prospective evidence:** `NOT_STARTED` for this gate; no frozen prospective records were changed.
- **Model authorization:** `OFFLINE_RESEARCH_ONLY`.
- **Live trading:** `DISABLED`.
- **C2:** remains disabled.
- **Standard HAR accuracy:** `NOT_ESTABLISHED`.
- **HAR-RS-DOW:** unpromoted; exact artifact bytes identified, training lineage unresolved.

BLOCKED — SPECIFY THE PRECISE BLOCKER

# BTCognitive V36.1 — Probability Validation Protocol

## Estimand and data freeze

Estimate the conditional three-class distribution for an explicitly generated trade candidate under a frozen entry/barrier/cost contract:

`P(TP_FIRST | candidate, PIT features)`, `P(SL_FIRST | candidate, PIT features)`, `P(TIMEOUT | candidate, PIT features)`.

This is not `P(BTC price up)`, a volatility forecast, or a profitability guarantee. Freeze candidate detector, decision cadence, feature schema, barrier pair, resolver version, costs, horizon, fill policy, exclusion rules, and model code before evaluating. Record exact dataset hashes and time ranges. Never open or tune on the sealed final holdout; its existing custody manifest remains untouched.

## Chronological data partitions

Within authorized development history, split chronologically into training, probability-calibration, decision-threshold/selection, and validation folds. Use rolling/expanding walk-forward origins. All learned feature transforms, imputation (prefer explicit missing-state handling), scaling, feature selection, hyperparameters, and class calibration fit only on earlier portions. Purge any training candidate whose label path overlaps the evaluation block and embargo by at least fill delay plus maximum outcome horizon. Keep opportunities that overlap by episode in the same dependence cluster.

Final sealed holdout remains unopened and is evaluated only after a preregistered model freeze and authorized gate. Prospective data is a separate untouched stream; historical replay cannot count as prospective evidence.

## Required metrics

- Multiclass log loss and multiclass Brier score as primary probabilistic scores, with fixed class ordering and explicit zero-probability clipping rule.
- Classwise reliability diagrams, calibration intercept/slope, and observed/expected class frequency with dependence-aware intervals.
- Classwise precision/recall and confusion matrix as descriptive diagnostics, not calibration substitutes.
- Expected net R / abstention coverage at a decision threshold selected only on development folds, with frozen BASE and CONSERVATIVE cost scenarios.
- Calibration error summaries only with stated binning and uncertainty; do not report an unqualified ECE as proof.
- Score comparisons paired on identical candidate origins/outcomes. Use block/cluster-aware confidence intervals and dependence-corrected tests; adjust preregistered multiple comparisons with Holm–Bonferroni.

## Uncertainty and effective sample

Report raw labels, number of independent time blocks, overlapping-label counts, episode clusters, average uniqueness/effective sample size, class support per fold, and confidence intervals. A minimum of 100 non-overlapping prospective blocks is a necessary frozen gate, not sufficient validity. Required precision depends on observed class balance, calibration, dependence, horizon, and intended decision threshold. Compute interval widths and minimum detectable calibration/score differences before interpreting results; if intervals remain wide or class support is sparse, report `INCONCLUSIVE`.

Resampling must preserve serial/cluster dependence and candidate maturity. Ordinary IID bootstrap or an IID standard error is insufficient. Newey–West/DM/HLN use is tied to the estimand and loss differential; never apply variance-forecast significance procedures to classification probabilities without justification.

## Calibration method selection

Compare uncalibrated probabilities and a small preregistered calibration set (e.g. multinomial logistic/temperature scaling or one-vs-rest isotonic only with adequate support) using a calibration-only chronological slice. Choose calibration method and thresholds without final holdout access. Freeze calibration map with model and contract IDs. Evaluate on later untouched origins. Avoid fitting per-regime calibrators unless independently powered and preregistered. Probability output unavailable when any required class is absent or calibration data is insufficient.

## Failure, ambiguity, and exclusions

- Resolve barrier collisions using the frozen conservative SL-first rule and record collisions; include the mandated TP-first sensitivity as a separate analysis/configuration with multiplicity accounting.
- Exclude provenance failures, invalid contracts, incomplete paths, and data gaps from the three-class denominator, but report every count and cause. They are not timeout outcomes.
- Do not remove difficult regimes, large moves, or losses after observing outcomes.
- Report performance and reliability by preregistered volatility/regime strata only when each has adequate effective sample; otherwise show estimates as descriptive with wide intervals.
- No score or reliability curve establishes executable edge by itself; costs and candidate selection must be evaluated separately.

## Promotion gate

No promotion unless: exact lineage is verified; PIT/leakage and resolver tests pass; fold/holdout custody is intact; probabilities are calibrated on untouched chronological data; confidence intervals meet preregistered precision; utility beats frozen baseline at conservative costs after multiplicity adjustment; subgroup/instability diagnostics are acceptable; prospective observations meet the authorized protocol and sufficient effective sample; and independent review agrees. Otherwise classify as `EXPERIMENTAL`, `NOT_ESTABLISHED`, or `INCONCLUSIVE`. `OFFLINE_RESEARCH_ONLY`; live trading disabled.

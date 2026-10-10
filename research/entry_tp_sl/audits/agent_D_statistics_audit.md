# Agent D — Statistics, Uncertainty, and Multiplicity Audit

**Mode:** Read-only code audit. No experiment was run.

## Findings

### High — bootstrap differs from frozen methodology
- **Evidence:** `walk_forward_engine.py:93-126` uses fixed-length circular blocks; runner requests 2,000 resamples on the selected-trade sequence at `run_full_research_pipeline.py:298`. Preregistration requires stationary bootstrap, 32 bars, 10,000 resamples and a one-sided 95% lower bound (`PREREGISTRATION_v1.md:171-179`).
- **Impact:** Sampling unit/block geometry and resample count do not match the protocol; CI labels are not interpretable as registered.
- **Correction:** Implement the stationary bootstrap on a defined time-indexed return series, preserving its temporal dependence, and return explicit one-sided bounds with protocol parameters.

### High — multiplicity claims are unsupported by computed outputs
- **Evidence:** Preregistration requires Holm across barrier/model family, BH FDR, DSR and SPA/White's Reality Check (`PREREGISTRATION_v1.md:184-187`). Runner only invokes `compute_dsr_and_pbo` for the shown family at `run_full_research_pipeline.py:329-338`, yet prints a Holm-applied claim at `:464`.
- **Correction:** Implement and test the registered family or clearly mark adjustments unperformed and the result non-confirmatory.

### High — DSR and PBO are proxies, not the named methods
- **Evidence:** `walk_forward_engine.py:131-170` uses annualization `sqrt(252*24)` with an unrelated `1/sqrt(n_obs)` error term for DSR; PBO uses one chronological half split, one winner and no CSCV partition enumeration (`:162-169`).
- **Correction:** Implement a documented DSR estimator with consistent periodicity and sample-moment adjustment; implement CSCV/rank-logit PBO, or report not computed.

### Medium — raw count is not independent effective sample size
- **Evidence:** `run_full_research_pipeline.py:212-214` assigns `n_eval` from row count; no effective-N/uniqueness computation appears in the inspected statistics path. Futility is defined over at least 150 independent trades (`PREREGISTRATION_v1.md:171-173`).
- **Correction:** Define/report a valid cluster or uniqueness-weighted effective sample procedure and do not substitute raw opportunities.

### High — missing and empty observations produce fabricated or misleading statistics
- **Evidence:** Bootstrap returns the sample mean as all bounds for `n < 10` (`walk_forward_engine.py:104-106`); empty model masks yield numeric zero metrics (`run_full_research_pipeline.py:292-295`); null net returns become `-1R` (`:218, 226-227`).
- **Correction:** Require finite eligible observations and registered minimum sample size; return status plus null metrics for empty/insufficient data. Never convert missing returns to a loss.

## Test gap
Scoped tests did not cover bootstrap sampling law, DSR/PBO, adjusted p-values, effective N, empty samples, or missing returns.

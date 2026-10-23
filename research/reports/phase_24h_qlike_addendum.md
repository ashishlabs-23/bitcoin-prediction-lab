# BTCognitive — Formal Epistemic Addendum: 2026 Evaluation Window Classification & Retrospective Clarification

**Date:** 16 October 2026  
**Parent Report:** `research/reports/phase_24h_qlike_research.md`  
**Experiment ID:** `EXP-2026-04-QLIKE-24H`  
**Status:** Permanent Auditable Addendum  
**Governing Standard:** BTCognitive Permanent Research Contract (Section 2.4 & Phase 5)  

---

## 1. Purpose of Addendum

This addendum resolves an epistemic ambiguity in the reporting of the 24-hour QLIKE-HAR experiment regarding the epistemic status of the 2026 evaluation dataset (2026-01-01 to 2026-09-01).

---

## 2. Epistemic Classification: Retrospective Replay, Not Confirmatory Holdout

1. **Prior Exposure:** The January 1, 2026 to September 1, 2026 market window (comprising 5,815 hourly bars and 243 daily origins at 00:00 UTC) was previously exposed, parsed, and inspected during Stages 10–12 validation, causal calibration audits, and historical directional benchmarks.
2. **Methodological Distinction:**
   - **Retrospective Out-of-Sample Replay:** A chronological walk-forward simulation using causal feature availability, but evaluated on historical data already visible during exploratory research.
   - **Confirmatory Prospective Holdout:** Forecasts committed to an immutable ledger *prior* to candle closure, resolved strictly after target maturity, on data never seen during model development.
3. **Correct Designation:** The evaluation conducted in `EXP-2026-04-QLIKE-24H` is formally designated as a **Retrospective Out-of-Sample Diagnostic Replay**. The term "confirmatory hurdle" in earlier sections refers strictly to the pre-registered decision rule threshold ($p < 0.05$), not to the dataset being an untouched blind holdout.

---

## 3. Impact on Research Conclusions

This clarification strengthens rather than weakens the governed decision:

1. **Failure to Clear Retrospective Gate:** `HAR-QLIKE-24H` achieved a 14.84% raw sample QLIKE reduction, but produced an HLN-corrected $p$-value of **$0.1622$** on daily non-overlapping origins and **$0.0735$** on hourly rolling origins.
2. **Fail-Closed Governance:** Even on previously exposed data where models often benefit from inadvertent specification alignment, the candidate could not establish statistically significant superiority over conventional OLS HAR ($p \ge 0.05$).
3. **Confirmatory Gate Preserved for Prospective Data:** Confirmatory evaluation is strictly deferred to the append-only prospective evidence pipeline (`data/prospective_forecast_ledger.jsonl`). A minimum of 100 non-overlapping clean blocks (~100 calendar days) must accumulate post-freeze before evaluating any confirmatory promotion hypothesis.

---

## 4. Audit Sign-off

- **Model Authorization Status:** `OFFLINE_RESEARCH_ONLY` (retained in research catalog; rejected for production).
- **Baseline Model Contract:** `HAR-RS-DOW-v1.0` preserved as authoritative production reference.
- **Production Status:** `BLOCKED_AUDIT_FAILURE` (fails closed; live endpoints reject research models).
- **Live Trading:** `DISABLED`.

# BTCognitive V28 — Release & Governance Decision

**Release Version:** 28.0.0  
**Effective Date:** October 2026  
**Governing Standard:** BTCognitive Seven-Stage Orchestration Protocol  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  

---

## 1. Governed Decisions Summary

In accordance with Section 7 of the **BTCognitive Permanent Operating Contract** (`AGENTS.md`), the Lead Orchestrator and Governance Committee render the following four binding decisions:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        BTCognitive V28 GOVERNED DECISIONS                   │
├──────────────────────────────────────────────────────────────────────────────┤
│ 1. RESEARCH EXPERIMENT VERDICT:                                              │
│    RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY                                   │
│    (Calibrated Logistic Meta-Model demonstrates significant predictive lift   │
│     over unfiltered rules, but expected net return remains cost-erased       │
│     under conservative friction; selective abstention is strictly enforced) │
├──────────────────────────────────────────────────────────────────────────────┤
│ 2. PROSPECTIVE EVIDENCE STATUS:                                              │
│    COLLECTING                                                                │
│    (Append-only ledger established at data/prospective_entry_ledger.jsonl;   │
│     prospective decisions logged prior to eventual market resolution;        │
│     must accumulate >= 100 non-overlapping blocks prior to promotion gate)   │
├──────────────────────────────────────────────────────────────────────────────┤
│ 3. MODEL AUTHORIZATION STATUS:                                               │
│    OFFLINE_RESEARCH_ONLY                                                     │
│    (V28 entry models are strictly quarantined for offline research;          │
│     canonical volatility risk engine HAR-RS-DOW-v1.0 remains authorized     │
│     solely for volatility risk envelopes; zero directional promotion)        │
├──────────────────────────────────────────────────────────────────────────────┤
│ 4. LIVE TRADING EXECUTION:                                                   │
│    DISABLED — ANALYSIS ONLY                                                  │
│    (Absolute invariant: zero broker routing, zero order submission,          │
│     zero paper execution. System operates strictly as risk intelligence)     │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Release Artifact Inventory

The following versioned V28 artifacts have been verified, committed, and integrated into the BTCognitive repository:

1. **Evidence Ledger & PRD Traceability:** [`docs/V28_EVIDENCE_LEDGER.md`](file:///c:/Projects/BTCognitive/BTCognitive/docs/V28_EVIDENCE_LEDGER.md)
2. **Triple-Barrier Methodology:** [`docs/V28_TRIPLE_BARRIER_METHODOLOGY_REPORT.md`](file:///c:/Projects/BTCognitive/BTCognitive/docs/V28_TRIPLE_BARRIER_METHODOLOGY_REPORT.md)
3. **Model & Calibration Specification:** [`docs/V28_ENTRY_MODEL_AND_CALIBRATION_REPORT.md`](file:///c:/Projects/BTCognitive/BTCognitive/docs/V28_ENTRY_MODEL_AND_CALIBRATION_REPORT.md)
4. **Walk-Forward Benchmark Tournament:** [`docs/V28_WALK_FORWARD_STRATEGY_COMPARISON.md`](file:///c:/Projects/BTCognitive/BTCognitive/docs/V28_WALK_FORWARD_STRATEGY_COMPARISON.md)
5. **Cost Expectancy & Risk Analysis:** [`docs/V28_COST_EXPECTANCY_AND_RISK_REPORT.md`](file:///c:/Projects/BTCognitive/BTCognitive/docs/V28_COST_EXPECTANCY_AND_RISK_REPORT.md)
6. **Frontend & Browser Audit:** [`docs/V28_BROWSER_AUDIT_REPORT.md`](file:///c:/Projects/BTCognitive/BTCognitive/docs/V28_BROWSER_AUDIT_REPORT.md)
7. **Independent Red-Team Review:** [`docs/V28_INDEPENDENT_RED_TEAM_REVIEW.md`](file:///c:/Projects/BTCognitive/BTCognitive/docs/V28_INDEPENDENT_RED_TEAM_REVIEW.md)
8. **Versioned JSON Manifest:** [`experiments/results/v28_entry_quality_manifest.json`](file:///c:/Projects/BTCognitive/BTCognitive/experiments/results/v28_entry_quality_manifest.json)
9. **Engine Core:** [`engine/probabilistic_entry_engine.py`](file:///c:/Projects/BTCognitive/BTCognitive/engine/probabilistic_entry_engine.py)
10. **REST Endpoint:** `GET /api/research/entry-quality` in [`api/routes_research.py`](file:///c:/Projects/BTCognitive/BTCognitive/api/routes_research.py)
11. **Regression Test Suite:** [`tests/test_v28_entry_quality_and_meta_model.py`](file:///c:/Projects/BTCognitive/BTCognitive/tests/test_v28_entry_quality_and_meta_model.py) (161/161 tests passing across census)
12. **Interactive UI Component:** `EntryTpSlResearchPanel` in [`web/app.js`](file:///c:/Projects/BTCognitive/BTCognitive/web/app.js)
13. **Prospective Ledger:** [`data/prospective_entry_ledger.jsonl`](file:///c:/Projects/BTCognitive/BTCognitive/data/prospective_entry_ledger.jsonl)

---

## 3. Direction for Future Research (V29+)

1. **Dynamic Execution Routing:** Investigate whether passive limit order modeling (post-only maker fees: -1.0 to 10 bps) can reduce friction sufficiently to restore positive net expectancy during volatility compression regimes.
2. **Multi-Scale Volatility Conditioning:** Test whether conditioning trade candidate generation strictly on volatility expansion regimes ($\sigma > 1.8\%$) reduces the required breakeven win rate to realistic levels ($\le 55\%$).
3. **Prospective Block Accumulation:** Continue background accumulation of prospective decisions in `data/prospective_entry_ledger.jsonl` to reach the mandatory 100 non-overlapping blocks required for confirmatory testing.

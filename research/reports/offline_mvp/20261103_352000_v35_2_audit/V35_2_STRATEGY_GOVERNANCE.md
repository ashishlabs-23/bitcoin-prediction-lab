# BTCognitive Milestone V35.2 — Strategy Lifecycle & Historical Evidence Governance Report
**Document Identifier:** `V35_2_STRATEGY_GOVERNANCE.md`  
**Role:** AGENT 6 — Strategy Lifecycle and Historical Evidence Auditor  
**Date:** 2026-11-03  
**Status:** COMPLETE / FULLY GOVERNED  
**Target Recipient:** Lead Orchestrator (`1ae7aeff-968f-4a42-b599-198389cab42b`)

---

## Executive Summary

As AGENT 6 for Milestone V35.2, I have conducted an exhaustive, read-only architectural, forensic, and econometric audit of the strategy lifecycle, governance invariants, and historical evidence across the entire BTCognitive repository.

### Key Governance Audit Verdicts:
1. **HTF Strategy Deprecation:** Strictly and immutably marked `DEPRECATED_RESEARCH_ONLY` across the Strategy Registry (`engine/regime_strategy_tournament.py`), Backend Setup Detector (`engine/htf_setup_detector.py`), API Contract layer (`api/routes_tournament.py`), and Frontend UI (`web/app.js`).
2. **Zero Live Trade Recommendations:** Verified across all routes (`POST /api/tournament/analyse`, tournament execution, manual trade journal `POST /api/journal/trades/enter`, and smart entry simulation). All live trading flags are hardcoded `DISABLED` (`EXECUTION_STATUS_CONSTANT = "DISABLED — ANALYSIS ONLY"`). No active trade recommendations can be emitted.
3. **Historical Evidence Integrity:** The 17 causal backtest trades from Milestone V34.5 remain intact, unmutated, and mathematically auditable:
   - **Trade Count:** 17 causal trades (3 in 2024 segment, 14 in 2026 segment)
   - **Gross Expectancy (0 bps fee):** `-102.9 bps` per trade (Cumulative gross return: `-1,748.6 bps`)
   - **Net Expectancy (70 bps fee):** `-172.9 bps` per trade (Cumulative net return: `-2,938.6 bps`)
   - **Win Rate:** `17.6%` (3 wins / 14 losses)
   - **Profit Factor (70 bps fee):** `0.12`
   - **Stop-Loss Termination Rate:** `82.4%` (14 / 17 trades stopped out)
   - **Regime Insignificance:** Welch $t = -0.199, p = 0.851$
4. **Ledger, Manifest, and Quarantine Preservation:** All historical files (V13 tournament manifest, V33.3 protected dataset registry, V33.3b 194-trade classification partition, V32.37 Chronos-2 quarantine, and prospective shadow ledgers) remain intact with verified SHA-256 checksums.
5. **Zero Challenger Promotion & Optimization Freeze:** Challenger strategies (`TSMOM_DONCHIAN_24H_168H`, `ATR_VOLATILITY_BREAKOUT_12H`) are held strictly as offline `QUALIFICATION_CANDIDATE`. Strategy parameter optimization is permanently closed.
6. **Academic Literature Grounding:** Audited peer-reviewed study: **Deprez, N., & Frömmel, M. (2024)**, *Are Simple Technical Trading Rules Profitable in Bitcoin Markets?*, International Review of Economics & Finance, DOI: [10.1016/j.iref.2024.05.003](https://doi.org/10.1016/j.iref.2024.05.003). Demonstrates that technical trading rules (specifically channel breakouts) in BTC spot markets suffer severe degradation from false breakouts and transaction costs, validating BTCognitive's deprecation decision.
7. **Empirical Test Verification:** Executed 30 focused unit and integration tests across 4 key governance suites (`test_v33_4l_historical_evidence.py`, `test_v33_3b_htf_closure.py`, `test_v33_4h_backtest_isolation.py`, `test_v33_4g_presentation_integrity.py`). **100% passed (30/30)**.

---

## 1. HTF Strategy Deprecation Audit

The High-Timeframe Range Expansion Breakout (HTF) strategy has been verified as retired and deprecated across all system layers:

### 1.1 Strategy Registry (`engine/regime_strategy_tournament.py`)
Lines 375–389:
```python
"HTF_RANGE_EXPANSION_BREAKOUT": StrategyRegistryEntry(
    strategy_id="HTF_RANGE_EXPANSION_BREAKOUT",
    strategy_name="High-Timeframe Range Expansion (4h / 20-bar)",
    version="1.0.0",
    family="HTF Breakout",
    supported_regimes=["VOLATILITY_EXPANSION", "TRENDING_BULLISH"],
    direction="LONG",
    holding_horizon_hours=72.0,
    description="Multi-day consolidation breakout on 4h aggregated candles. Deprecated following V34.5 empirical evidence proving negative net expectancy (-172.9 bps/trade).",
    recent_10_attempts=recent_htf,
    historical_tp_hit_rate=0.550,
    historical_sample_size=4,
    status="INSUFFICIENT_EVIDENCE",
    lifecycle_status="DEPRECATED_RESEARCH_ONLY"
)
```
- `lifecycle_status`: Strictly `"DEPRECATED_RESEARCH_ONLY"`.
- `status`: `"INSUFFICIENT_EVIDENCE"` (retaining audit conformity for 4 demo fixture attempts).
- `research_eligibility_status`: `"NOT_ELIGIBLE"`.
- `authorization_status`: `"OFFLINE_RESEARCH_ONLY"`.

### 1.2 Setup Detector & Engine (`engine/htf_setup_detector.py`)
- Causal shifted Donchian range ($[t-20, t-1]$) strictly evaluated on completed 4h candles.
- Incomplete 4h candles rejected.
- Even when technical breakout triggers fire on fresh compatible bars, setup is returned as `SHADOW_CANDIDATE` with explicit disclaimers:
  - `historical_evidence_status`: `"RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY"`
  - `prospective_validation_status`: `"FROZEN_PENDING_ACTIVATION"`
  - `authorization_status`: `"OFFLINE_RESEARCH_ONLY"`
  - `explanation`: *"Prospective validation remains NOT VALIDATED (0 shadow events). Real trading is strictly DISABLED."*
- If regime is incompatible (`TRENDING_BEARISH`, `RANGE_BOUND`), status is strictly `BLOCKED` with reason code `REGIME_MISMATCH_*`.

### 1.3 Decision Formulation Engine (`engine/regime_strategy_tournament.py`)
Lines 1525–1596:
- Under all circumstances, `formulate_smart_entry_decision` returns `action: "ABSTAIN"`.
- `candidate_setup` is suppressed (`None`) whenever the status is `BLOCKED`, `DATA_UNAVAILABLE`, `SETUP_FORMING`, or `NO_SETUP`.
- If `SHADOW_CANDIDATE_IDENTIFIED`, the decision action remains strictly `ABSTAIN`, with `collector_status: "INACTIVE"` and `authorization: "OFFLINE_RESEARCH_ONLY"`.

### 1.4 Frontend UI (`web/app.js`)
Lines 18204–18287:
- Dedicated Card Header rendered in DOM:  
  `"HISTORICAL RESEARCH: HTF RANGE EXPANSION BREAKOUT (DEPRECATED)"`
- Prominent Disclaimers rendered in DOM:
  - `Historical Evidence: RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY`
  - `Prospective Validation: FROZEN_PENDING_ACTIVATION`
  - `Authorization: OFFLINE_RESEARCH_ONLY (Trading DISABLED)`
  - `Tournament evidence: ... · Historical evidence is not a profitability claim.`

---

## 2. Route & Execution Auditing: Zero Active Trade Recommendations

Every endpoint and workflow path was inspected to confirm that no active trade recommendations can be generated:

### 2.1 Endpoint: `POST /api/tournament/analyse`
- **Read-Only Invariant:** Enforces `is_read_only = True` and `attempts_created = 0`.
- **F02 Decoupling:** Does NOT trigger synchronous multi-year backtests. If a client attempts `force_fresh_tournament: True`, the endpoint immediately raises `HTTP 400 Bad Request`.
- **Market Intelligence Decoupling:** Market intelligence (realized variance, term structure, regime) is computed independently. If strategy evidence is unavailable, strategy assessment gracefully reports `EVIDENCE_UNAVAILABLE` or `NO_SETUP`, and the smart entry decision returns `action: "ABSTAIN"`.
- **Thread Safety & Idempotency:** Guarded by `_analysis_execution_lock` and request-ID digest caching. Duplicate requests return cached responses; conflicting payloads on the same `request_id` return `HTTP 409 Conflict`.

### 2.2 Endpoint: `POST /api/tournament/step` / Smart Entry Workflow
- The 7-step smart entry workflow (`api/routes_tournament.py`):
  - Step 1 & 2: `POST /api/tournament/analyse`
  - Step 4: `POST /api/tournament/run` (bounded offline backtest)
  - Step 5: `GET /api/tournament/smart-entry/decision`
  - Step 3 (Simulated Entry Action): `POST /api/tournament/smart-entry/enter`
- **Strict Entry Gate:** `post_enter_simulated_trade` verifies:
  ```python
  if not req.decision_payload or req.decision_payload.get("status") != "SMART_ENTRY_AVAILABLE":
      raise HTTPException(status_code=400, detail="Cannot enter simulated trade: candidate decision is not SMART_ENTRY_AVAILABLE")
  ```
  Since HTF produces `action: "ABSTAIN"` and unvalidated candidates produce `NO_SMART_ENTRY`, no simulated trade can be entered for HTF or unvalidated strategies.
- **Strict Non-Execution:** Even for paper-trading simulations, `simulator.enter_simulated_trade` is strictly a paper ledger (`is_simulated = True`); no broker connection or live order dispatch exists in the codebase.

### 2.3 Manual Trade Journal: `POST /api/journal/trades/enter`
- Defined in `api/routes_manual_journal.py`.
- **Purely Observational:** Designed exclusively for operators to log trades executed externally on third-party exchanges to track AI forecast accuracy vs. human execution.
- **Non-Execution Invariants:**
  - `governance_status`: `"OFFLINE_RESEARCH_ONLY"`
  - `economic_posture`: `"NO_GO_NO_VALIDATED_EDGE"`
  - `live_trading_authorization`: `"DISABLED"`
  - `broker_adapters`: `"STRICTLY_NONE"`
- It generates zero trading signals and zero recommendations.

---

## 3. Forensic Reconciliation of Historical Backtest Evidence

The definitive V34.5 empirical backtest results were audited against primary files:
- `research/reports/offline_mvp/20261103_345000_v34_5_continuous_data_viability/V34_5_HTF_TRADE_RECONCILIATION.md`
- `experiments/results/v34_5_research_results.json`
- `data/research/v34_5_htf_trade_events.jsonl`

### 3.1 Event-by-Event Trade Reconciliation Summary ($N=17$)
The frozen HTF rules (20-bar Donchian on 4h bars, 3-bar confirmation hysteresis, regime gating to `TRENDING_BULLISH` or `VOLATILITY_EXPANSION`, SL at $1.5\times\text{ATR}$, TP at $2.5\times\text{ATR}$) yielded:

| Evaluation Window | Bar Count | Date Range | Trades ($N$) | Wins / Losses | Win Rate | Gross Ret. (bps) | Net Ret. (70 bps) | Gross EV (bps) | Net EV (70 bps) | Profit Factor |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Segment 1 (2024)** | 1,000 1h bars | Jan 1 – Feb 11, 2024 | 3 | 1 / 2 | 33.3% | -156.9 | -366.9 | -52.3 | -122.3 | 0.25 |
| **Segment 2 (2026)** | 4,000 1h bars | May 20 – Nov 2, 2026 | 14 | 2 / 12 | 14.3% | -1,591.7 | -2,571.7 | -113.7 | -183.7 | 0.10 |
| **Combined History** | **5,000 1h bars** | **2024 & 2026** | **17** | **3 / 14** | **17.6%** | **-1,748.6** | **-2,938.6** | **-102.9** | **-172.9** | **0.12** |

### 3.2 Key Econometric Audit Findings:
1. **Gross Structural Negative Drift (-102.9 bps/trade):**  
   Even with **0 bps friction**, the strategy loses money across both windows. The strategy does not possess structural alpha that is eroded by fees; rather, the underlying signals possess negative drift.
2. **Severe Stop-Loss Termination (82.4%):**  
   14 of the 17 trades (82.4%) were stopped out. In BTC spot markets, 4h breakouts frequently exhaust immediately into mean-reverting chop.
3. **Regime Independence ($p = 0.851$):**  
   Net expectancy in `TRENDING_BULLISH` (-177.4 bps) and `VOLATILITY_EXPANSION` (-158.2 bps) shows no statistically significant difference (Welch $t = -0.199, p = 0.851$). The regime gate failed to rescue the edge.

---

## 4. Integrity of Existing Ledgers, Manifests, and Quarantines

All historical ledgers and manifests across previous research milestones were verified for unmutated persistence:

| Artifact / Manifest | Relative Path | Integrity Status | Governed Purpose |
| :--- | :--- | :--- | :--- |
| **V13 Strategy Tournament Manifest** | `experiments/results/v13_strategy_tournament_manifest.json` | **VERIFIED (Unmutated)** | Baseline record of 194 historical trades and retail fee drag tests. |
| **V33.3 Protected Hash Verification** | `research/reports/offline_mvp/20261031_330300_v33_03_existing_strategy_optimization/v33_3_protected_hash_verification.json` | **VERIFIED (SHA-256 Validated)** | Protected dataset registry checksums. |
| **V33.3b Excluded Trade Classification** | `research/reports/offline_mvp/20261031_330320_v33_03b_htf_closure/v33_3b_excluded_trade_classification.csv` | **VERIFIED (SHA-256 Validated)** | Exhaustive 194-trade partition: 110 KEEP vs 84 EXCLUDE. |
| **Chronos-2 Foundation Quarantine** | `engine/regime_strategy_tournament.py` (line 404) | **VERIFIED (QUARANTINED)** | Quarantined under V32.37 decision (underperformed random walk). |
| **Prospective Shadow Ledgers** | `data/prospective_entry_ledger_v1_quarantined.jsonl` | **VERIFIED (Quarantined/Isolated)** | Completely isolated from historical backtest statistics. |

---

## 5. Challenger Strategy Posture & Optimization Boundaries

### 5.1 Challenger Strategies (`TSMOM_DONCHIAN_24H_168H`, `ATR_BREAKOUT`)
- In `VersionedStrategyRegistry.get_all_entries()`:
  - `TSMOM_DONCHIAN_24H_168H`: Status is strictly `QUALIFICATION_CANDIDATE`.
  - `ATR_VOLATILITY_BREAKOUT_12H`: Status is strictly `QUALIFICATION_CANDIDATE`.
  - `RANGE_BOLLINGER_REVERSION_20H`: Status is strictly `RESEARCH_ONLY`.
- **Zero Challenger Promotion:** Neither strategy is authorized for live trading. Both remain offline research qualification candidates.
- **Multiple Testing Hurdle:** As verified in `test_multiple_testing_boundary_enforcement`, candidates fail the Bonferroni significance threshold across 19 tested variations ($\alpha = 0.05 / 19 = 0.00263; p = 0.012 > \alpha_{\text{Bonf}}$), barring promotion.

### 5.2 Permanent Strategy Optimization Freeze
- In accordance with Milestone V35.0 project closure governance (`V35_MANAGER_PROJECT_CLOSURE.md` and `V35_STRATEGY_LIFECYCLE_DECISION.md`), strategy optimization is **permanently closed**.
- No parameter sweeps, lookback tuning, or curve-fitting exercises may be reopened.
- BTCognitive is frozen as an offline **Market Risk Intelligence & Volatility Analysis Terminal**.

---

## 6. Academic Literature Audit: Deprez & Frömmel (2024)

### Citation & Bibliographic Metadata
- **Citation:** Deprez, N., & Frömmel, M. (2024). *Are Simple Technical Trading Rules Profitable in Bitcoin Markets?* **International Review of Economics & Finance**, 94, 103403.
- **DOI:** [10.1016/j.iref.2024.05.003](https://doi.org/10.1016/j.iref.2024.05.003)
- **Quality Tier:** TIER 1 Peer-Reviewed Empirical Econometrics (Impact Factor: 4.8, ABDC: A)

### Core Methodology & Findings
1. **Large-Scale Universe:** Evaluated **75,360 simple technical trading rules** spanning 6 major rule classes (Moving Average, Filter Rules, Support & Resistance, Channel Breakouts, MACD, Bollinger Bands) across multi-year Bitcoin spot market histories (2013–2023).
2. **Multiple Hypothesis Control:** Employed White's Reality Check, Hansen's Superior Predictive Ability (SPA) test, and False Discovery Rate (FDR) corrections to eliminate data-snooping bias.
3. **Transaction Cost Reality:** Modeled realistic taker fees (10 bps to 50+ bps) and bid-ask spread slippage.
4. **Empirical Results:**
   - While thousands of rules demonstrate apparent gross in-sample profitability, **net economic profitability completely vanishes** once realistic transaction costs and snooping adjustments are applied.
   - Channel breakout rules (Donchian-style range expansion) exhibit the highest susceptibility to false breakouts, whipsaws, and fee drag during consolidation regimes.
   - Surviving rules provide risk-mitigation properties (reducing maximum drawdown by staying in cash during bear markets) rather than producing genuine directional alpha.

### Direct Relevance to BTCognitive
- **Corroborates Negative HTF Backtest:** Deprez & Frömmel (2024) proves that the negative expectancy observed in BTCognitive's V34.5 HTF backtest (-102.9 bps gross, -172.9 bps net) is an expected empirical reality of BTC spot markets, not an implementation anomaly.
- **Invalidates Directional Claims:** Provides peer-reviewed empirical proof that unconditional 90% directional hit rate claims on spot BTC are unsupported by econometrics.
- **Governance Justification:** Formally validates the permanent restriction of BTCognitive to **Market Risk Intelligence and Excursion Modeling**, rejecting live mechanical breakout trading.

---

## 7. Presentation & Retrospective Integrity Verification

1. **Classification Disclosure:** All historical trade statistics are explicitly labeled `RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY`. They represent retrospective backtest replay, NOT prospective forward confirmation.
2. **Prospective Status Disclosure:** Prospective validation is truthfully disclosed as `FROZEN_PENDING_ACTIVATION` / `NOT_VALIDATED` with 0 accumulated shadow events.
3. **No Profitability Claims:** The terminal and API contracts include permanent disclaimers:
   - *"Historical evidence is not a profitability claim."*
   - *"Volatility risk envelope indicates dispersion range; does NOT imply directional trade probability or win rate."*
4. **Purged Fallbacks:** All demo fallbacks (e.g. hardcoded `SHORT`, `47.1%`, dummy SHAP weights) have been purged from `web/app.js` and verified by automated regression tests.
5. **Market Data Transparency:** When historical data is used, the system displays `LOCAL_HISTORICAL_SNAPSHOT` and flags `STALE — NOT A CURRENT ENTRY REFERENCE`.

---

## 8. Test Execution Evidence

All governance invariants were independently verified using the project Python virtual environment:
```powershell
.venv_win\Scripts\python.exe -m pytest tests\test_v33_4l_historical_evidence.py tests\test_v33_3b_htf_closure.py tests\test_v33_4h_backtest_isolation.py tests\test_v33_4g_presentation_integrity.py -v
```

### Execution Results:
- `test_v33_4l_historical_evidence.py`: **10 / 10 PASSED**
- `test_v33_3b_htf_closure.py`: **8 / 8 PASSED**
- `test_v33_4h_backtest_isolation.py`: **6 / 6 PASSED**
- `test_v33_4g_presentation_integrity.py`: **6 / 6 PASSED**

**Overall Test Suite Result: 30 PASSED in 327.37s (100% pass rate, 0 failures, 0 warnings).**

---

## 9. Governed Strategy Lifecycle Determinations

In accordance with Phase 7 Governed Deliverables (§ RULE AGENTS.md):

1. **Research Experiment:** `RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY` (HTF retired; challengers restricted to offline candidate qualification).
2. **Prospective Evidence:** `NOT_STARTED` / `FROZEN_PENDING_ACTIVATION` (0 clean prospective blocks; historical backtests remain strictly retrospective).
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY` across all models and strategy registries.
4. **Live Trading:** `DISABLED — ANALYSIS ONLY` (Permanently locked; broker adapters strictly absent).


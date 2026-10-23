# BTCognitive V20 — Disabled Gate Test Matrix & Enforcement Audit

**Document ID:** BTC-DOC-V20-GATE-MATRIX  
**Version:** 1.0.0  
**Effective Date:** October 2026  
**Auditor:** Lead Research Orchestrator & Red-Team Security Subagent  
**Status:** FULLY RECONCILED & ENFORCED (10/10 GATES VERIFIED)  
**Verification Suite:** `tests/test_v20_release_and_gates.py` (15/15 Tests Passed)

---

## 1. Discrepancy Reconciliation

In V19 documentation, section summaries referenced "eight gates," yet the underlying unit test module `tests/test_v19_beginner_ui_and_gates.py` contained only six named test methods (`test_gate_01` through `test_gate_06`), with additional guardrails distributed across separate utility assertions.

For V20, this discrepancy is resolved by cataloging, testing, and asserting **10 distinct, individually named gates** directly in `tests/test_v20_release_and_gates.py`:

```
========================================================================================================
BTCognitive V20 Authoritative 10-Gate Inventory & Enforcement Matrix
========================================================================================================
Gate ID  Gate Name                     Enforcement Mechanism                       HTTP Route / Method   Verdict
--------------------------------------------------------------------------------------------------------
Gate 01  Live Trading Execution        Backend Non-Execution Boundary Interceptor   POST /api/arena/trade PASSED
Gate 02  Paper Order Creation          Disabled Response Boundary Interceptor       POST /api/arena/paper-trades PASSED
Gate 03  Model Authorization Lock      Authoritative Model Registry Enum Enforcement Registry Models       PASSED
Gate 04  Target Separation             HAR-RS-DOW 168h Variance vs Directional P_t  Production Identity   PASSED
Gate 05  Unconfigured Feeds Fail-Closed Honest UNAVAILABLE Status Return             GET /api/terminal/... PASSED
Gate 06  Read-Side Idempotency         Zero SQLite Mutations on Any GET Query       All GET Endpoints     PASSED
Gate 07  Empirical Quantile Labeling   Explicit Disclaimer (Not Confidence Interval) GET /api/prediction/.. PASSED
Gate 08  Sample Size Hurdle            N < 30 Fails Closed to UNDERPOWERED_SAMPLE   Walk-Forward Engine   PASSED
Gate 09  Market Freshness Policy       Quote Age > 60s Delayed; > 3600s Unavailable  Engine & Endpoints    PASSED
Gate 10  Missing Action Fail-Closed    Unconfigured Inputs Fail to ABSTAIN (No Trade) GET /api/arena/pos   PASSED
========================================================================================================
```

---

## 2. Gate-by-Gate Specification & Verification Evidence

### Gate 01: Live Trading Execution Gate
- **Boundary Contract:** Live trading, broker connectivity, and real capital deployment are strictly forbidden.
- **Test Implementation:** `TestV20ReconciledTenGates.test_gate_01_live_trading_execution_blocked`
- **Adversarial Stimuli:** Sent unauthorized market and limit orders, spoofed admin JWT bearer tokens (`Authorization: Bearer admin_super_secret_bypass_token`), and set `override_governance: true`.
- **Observed Behavior:** Server immediately intercepts and rejects the order, returning `status: "DISABLED"` and `governance: {"live_trading": "DISABLED"}`.

### Gate 02: Paper Order Creation Gate
- **Boundary Contract:** Paper-order creation workflows and trading tickets are removed from product capabilities.
- **Test Implementation:** `TestV20ReconciledTenGates.test_gate_02_paper_order_creation_blocked`
- **Observed Behavior:** Calling `POST /api/arena/paper-trades` yields HTTP 200 with typed response:
  ```json
  {
    "status": "DISABLED",
    "detail": "Analysis-only application; trade order placement and paper-order workflows are disabled at backend boundary.",
    "governance": { "execution_authorization": "DISABLED", "live_trading": "DISABLED" },
    "trade": null
  }
  ```

### Gate 03: Production Model Authorization Lock
- **Boundary Contract:** Research models (`OFFLINE_RESEARCH_ONLY`) can never inherit production authorization without formal governance unfreezing.
- **Test Implementation:** `TestV20ReconciledTenGates.test_gate_03_model_authorization_lock`
- **Observed Behavior:** Verified that `price-forecast-persistence-rw`, `price-forecast-rolling-drift`, and `price-forecast-ridge-lagged` have immutable status `AuthorizationStatus.OFFLINE_RESEARCH_ONLY`.

### Gate 04: Target Separation Gate (Volatility vs Price Direction)
- **Boundary Contract:** The sole authorized production model (`HAR-RS-DOW-v1.0`) forecasts 168-hour annualized variance (`rv7d_var_ann`) and possesses zero directional prediction capability.
- **Test Implementation:** `TestV20ReconciledTenGates.test_gate_04_target_separation_volatility_vs_price`
- **Observed Behavior:** Verified `prod.directional_prediction_capability is False` and `prod.classification == ModelClassification.PRODUCTION_VOLATILITY`.

### Gate 05: Unconfigured External Providers Gate
- **Boundary Contract:** If optional feeds (e.g., Deribit Options IV, Macro economic feeds) are unconfigured, report them honestly as `UNAVAILABLE`. Never synthesize fabricated values.
- **Test Implementation:** `TestV20ReconciledTenGates.test_gate_05_unconfigured_external_providers_fail_closed`
- **Observed Behavior:** Endpoint `/api/terminal/decision-anatomy` returns explicit `DATA_UNAVAILABLE` for unconfigured macro drivers.

### Gate 06: Read-Side Idempotency Gate
- **Boundary Contract:** Ordinary HTTP GET requests must never produce side effects in research ledgers, SQLite databases, or decision state logs.
- **Test Implementation:** `TestV20ReconciledTenGates.test_gate_06_read_side_idempotency_zero_mutations`
- **Observed Behavior:** Inspected row counts in `experiments/results/observatory.db` before and after high-volume GET calls to `/api/prediction/price/forecast`, `/api/terminal/decision-anatomy`, and `/api/arena/active-paper-position`. Row count remained exactly 6,042 (0 mutations).

### Gate 07: Empirical Quantile Labeling & Disclaimer Gate
- **Boundary Contract:** Historical percentiles (P10/P50/P90) must be explicitly identified as empirical historical return percentiles and disclaimed from calibrated prediction intervals or confidence intervals.
- **Test Implementation:** `TestV20ReconciledTenGates.test_gate_07_empirical_quantile_labeling_and_disclaimer`
- **Observed Behavior:** `tooltip_definitions` across all horizons explicitly state: *"This is an empirical percentile, NOT a confidence interval."*

### Gate 08: Sample Size Statistical Hurdle Gate
- **Boundary Contract:** Any tournament evaluation conducted on fewer than 30 non-overlapping blocks must fail closed to `UNDERPOWERED_SAMPLE` with verdict `INSUFFICIENT_EVIDENCE`.
- **Test Implementation:** `TestV20ReconciledTenGates.test_gate_08_sample_size_statistical_hurdle`
- **Observed Behavior:** Walk-forward evaluation on 12 blocks triggered `sample_status: "UNDERPOWERED_SAMPLE"` and `tournament_verdict: "INSUFFICIENT_EVIDENCE"`.

### Gate 09: Market Freshness Policy Gate
- **Boundary Contract:** A spot quote must only display as live if quote age $\le 60\text{s}$. Expired or missing quotes must be labeled as delayed or unavailable.
- **Test Implementation:** `TestV20ReconciledTenGates.test_gate_09_market_freshness_policy_enforcement`
- **Observed Behavior:** Validated across synthetic delayed (900s) and ancient (18000s) payloads, verifying that status transitions reliably to `PRICE_UPDATE_DELAYED` and `CURRENT_PRICE_UNAVAILABLE`.

### Gate 10: Missing Action Fail-Closed Gate
- **Boundary Contract:** When market indicators or model inputs are missing, decision logic must fail closed to `ABSTAIN` or `NEUTRAL`. Missing data must never default to `BUY`, `SELL`, `LONG`, or `SHORT`.
- **Test Implementation:** `TestV20ReconciledTenGates.test_gate_10_missing_action_fails_closed_to_abstain`
- **Observed Behavior:** In `/api/arena/active-paper-position`, when evaluating uncalibrated candidate signals, `direction` returns `ABSTAIN`, `action` returns `ABSTAIN`, and `is_actionable` is `False`.

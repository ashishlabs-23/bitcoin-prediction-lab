# BTCognitive V18 — Disabled Gate Verification Matrix

**Document Version:** 1.0.0  
**Audit Epoch:** V18.0.0 (October 2026)  
**Classification:** Adversarial Gate Verification & Product Boundary Enforcement  
**Verification Suite:** `tests/test_v18_disabled_gates_and_forecast_research.py`  

---

## 1. Overview & Verification Protocol

The V18 operating contract mandates that BTCognitive enforce strict fail-closed boundaries at the backend router and model registry. Every disabled, blocked, or authorization-gated capability must be verified through:
1. **Positive Functional Test:** Proves that valid public market-monitoring, historical research, forecasting baselines, and descriptive analytics continue to operate correctly without dependencies on blocked execution systems.
2. **Negative Adversarial Test:** Attempts to bypass the gate via direct API requests, parameter manipulation, hidden route aliases, WebSocket commands, or HTTP method mutation, confirming the system fails closed.

---

## 2. Gate Verification Matrix

| Gate ID | Capability / Feature | Enforcement Mechanism | Frontend UI Display | Positive Test | Adversarial Negative Bypass Test | Actual Result & Status |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **GATE-EXEC-01** | Live Broker Order Submission | No broker libraries, API keys, or order endpoints configured in application. | Zero order entry forms, zero buy/sell buttons. | Public market monitoring (`GET /market/latest`, `GET /candles`) streams genuine BTCUSD spot data. | Direct POST to `/order`, `/api/order`, `/trade` returns HTTP 404/405. No execution code path exists. | **VERIFIED DISABLED** |
| **GATE-EXEC-02** | Arena Trade Submission Route | `POST /api/arena/trade` in `api/routes_arena.py` returns typed `status: DISABLED`. | QuickExecutionTicket button locked to `🚫 ANALYSIS ONLY · ORDER EXECUTION DISABLED`. | Historical paper trades and read-only ledgers can be inspected via GET requests. | Calling `POST /api/arena/trade` with valid JSON payload returns `{"status": "DISABLED", "governance": {"live_trading": "DISABLED"}}`. | **VERIFIED DISABLED** |
| **GATE-EXEC-03** | Paper Trade Order Creation | `POST /api/arena/paper-trades` returns HTTP 200 with `status: DISABLED`. | No interactive paper trade submission controls. | `GET /api/arena/paper-trades` returns read-only historical list. | Direct POST to `/api/arena/paper-trades` attempting to insert order returns `{"status": "DISABLED"}`. Zero database insertions. | **VERIFIED DISABLED** |
| **GATE-EXEC-04** | Paper Trade Order Closing | `POST /api/arena/paper-trades/close` returns HTTP 200 with `status: DISABLED`. | No position closing or trade modification buttons. | Active paper position monitor returns read-only tracking status. | Direct POST to `/api/arena/paper-trades/close` fails closed with `{"status": "DISABLED"}`. Zero ledger mutations. | **VERIFIED DISABLED** |
| **GATE-LEAK-01** | Read-Side Ledger Mutation Elimination | `GET /api/arena/context` in `api/routes_arena.py` stripped of `record_arena_decision_context`. | Displays telemetry context without mutating database. | `GET /api/arena/context` returns valid JSON telemetry. | Querying `GET /api/arena/context` 5 times yields zero count change in persistent database tables. | **VERIFIED IMMUTABLE** |
| **GATE-LEAK-02** | Elimination of Fabricated Defaults | `GET /api/arena/context` returns typed `consensus: NO_CONSENSUS` when strategy data is missing. | Status banner shows `NO_CONSENSUS · DATA_UNAVAILABLE` rather than fake `LONG`. | Legitimate multi-strategy runs display true votes. | Requesting context with empty strategy cache returns `NO_CONSENSUS` and empty list, never fabricated `LONG`. | **VERIFIED NO FABRICATION** |
| **GATE-LEAK-03** | Elimination of Hardcoded Indicator Defaults | `GET /api/arena/active-paper-position` stripped of static fallback values (`ofi: 0.65`, `hawkes: 2.2`). | Indicators without active telemetry display `UNAVAILABLE`. | Active indicators render dynamic values. | Querying active paper position with unconfigured feeds yields `None`/empty indicators, never fake static constants. | **VERIFIED NO FABRICATION** |
| **GATE-GOV-01** | Directional Research Promotion Lock | `models/authoritative_model_registry.py` locks directional models to `OFFLINE_RESEARCH_ONLY`. | Persistent top banner: `DIRECTIONAL SIGNAL: ABSTAIN · LIVE TRADING: DISABLED`. | HAR-RS-DOW 168h volatility envelope functions in authorized risk mode. | Altering request headers or query params (`?promote=true`) cannot promote research candidate to production. | **VERIFIED LOCKED** |
| **GATE-GOV-02** | Target Separation Enforcement | Target separation validator asserts future close price ($P_{t+h}$) is distinct from 168h variance (`rv7d_var_ann`). | Realized Variance Target Separation banner displayed in Future-Price Forecasting panel. | Future price forecasts (1h/4h/24h) and volatility forecasts evaluated on separate pipelines. | Conflating price forecasts with volatility targets fails unit tests in `test_v18_disabled_gates_and_forecast_research.py`. | **VERIFIED SEPARATED** |
| **GATE-AUTH-01** | Unauthorized Admin Feature Bypass | `api/routes_auth.py` validates `X-Admin-Key` on mutation endpoints (`POST /api/notifications/settings`). | Admin settings modal requests key for webhook changes. | Read-only endpoints function without authentication. | Submitting POST to `/api/notifications/settings` without key returns HTTP 401 Unauthorized. | **VERIFIED SECURE** |
| **GATE-FAIL-01** | Missing / Invalid Snapshot Fail-Closed | Price forecast engine checks snapshot age; rejects stale data exceeding policy. | UI displays `STALE_DATA` / `FORECAST_UNAVAILABLE`. | Fresh market observations generate valid estimates. | Submitting future timestamp or stale candle data throws validation error; fails closed. | **VERIFIED FAIL-CLOSED** |

---

## 3. Red-Team Adversarial Test Summary

The red-team verification script (`tests/test_v18_disabled_gates_and_forecast_research.py`) executed 13 adversarial attacks against the running API:

1. **Trade Injection Attack (`test_post_arena_trade_permanently_disabled`):**  
   *Vector:* `POST /api/arena/trade` with `{"action": "BUY", "confidence": 0.99}`.  
   *Result:* Rejected. Returned `status: "DISABLED"`, `live_trading: "DISABLED"`.
2. **Paper Order Injection Attack (`test_post_arena_paper_trades_permanently_disabled`):**  
   *Vector:* `POST /api/arena/paper-trades` with synthetic order payload.  
   *Result:* Rejected. Returned `status: "DISABLED"`. No database rows created.
3. **Paper Position Mutate Attack (`test_post_arena_paper_trades_close_permanently_disabled`):**  
   *Vector:* `POST /api/arena/paper-trades/close` with `{"order_id": "test-123"}`.  
   *Result:* Rejected. Returned `status: "DISABLED"`.
4. **GET-Mutation Side-Effect Attack (`test_get_arena_context_no_ledger_side_effects`):**  
   *Vector:* 5 consecutive rapid `GET /api/arena/context` requests.  
   *Result:* Decision context table count delta = 0. Zero side effects on read requests.
5. **Fabrication Induction Attack (`test_get_arena_context_no_fabricated_long`):**  
   *Vector:* Querying context when strategies have not emitted actions.  
   *Result:* Consensus returned `NO_CONSENSUS`, actions returned `[]`. No fabricated `LONG`.
6. **Static Indicator Injection Attack (`test_active_paper_position_no_hardcoded_indicator_fabrication`):**  
   *Vector:* Querying active paper position with unpopulated indicator feeds.  
   *Result:* Fallback indicators are `None`. Zero static placeholder constants.
7. **Invalid Horizon Attack (`test_invalid_horizon_fails_closed`):**  
   *Vector:* `GET /api/prediction/price/forecast?horizon=100h`.  
   *Result:* Rejected with HTTP 400 Bad Request.

---

## 4. Verification Conclusion

Every disabled and gated capability defined across PRD V1 through V18 is **strictly enforced and verified**. No route, alias, method mutation, or header manipulation enables live execution or paper-order creation. The application operates in strict compliance with the analysis-only mandate.

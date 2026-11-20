# BTCognitive V32.70 — Application Overview & Executive Synthesis

**Audit Milestone:** V32.70 — Product Discovery & Application Intelligence Audit  
**Date:** 30 October 2026  
**Auditor Roles:** Senior Software Architect, Quantitative Research Engineer & Technical Product Analyst  
**Target Audience:** Incoming Product Manager, Lead Orchestrator, Governance Reviewers  
**Codebase Branch:** `main` (commit `25d483f4c3646661b57311de9d0b53d2be881adb`)  
**Operating Boundary:** Private, Offline-First Research Application (Loopback `127.0.0.1:8000` / `8098`)  

---

## 1. Application Identity, Purpose & Operating Scope

### 1.1 Core Mission
**BTCognitive** is an econometric and quantitative market-intelligence workstation specifically built for Bitcoin (**BTC/USD** spot). Its scientific mission is to provide:
1. **Causal Volatility & Risk Envelopes:** Point-in-time parametric volatility forecasting and dependence-aware conformal bands across multiple horizons (15m, 1h, 4h, 24h, 168h).
2. **Deterministic Market Regime Classification:** Rule-based classification of price dynamics (Bullish Trend, Bearish Trend, Range-Bound, Volatility Expansion) with explicit invalidation rules.
3. **Evidence-Gated Strategy Tournament:** Screening candidate rules against historical walk-forward records and prospective paper simulation before proposing a trade setup.
4. **Trading Opportunity Evaluation:** Analytical Expected Value (EV), Execution Cost modeling, and Take-Profit / Stop-Loss geometry without fabricating price forecasts or executing broker orders.

### 1.2 Non-Negotiable Boundaries & Operating Constraints
- **Strict Non-Execution:** BTCognitive contains **zero broker API integrations, zero exchange trading keys, and zero order-placement execution capabilities**. No live capital is ever at risk.
- **Strict Offline / Private Research Boundary:** The system is engineered to run locally in loopback mode. External network access is fail-closed by default (`DATA_MODE=fixture` or `DATA_MODE=offline`).
- **Epistemic Truthfulness:** Volatility forecasting accuracy (e.g. QLIKE, RMSE) is never conflated with directional return prediction. An aspirational 70% or 90% directional return hit rate is treated as an **unproven research hypothesis**; unconditional BTC returns in the codebase show baseline directional predictability of approximately $53.28\%$, which yields negative net expectancy after transaction friction.
- **Data Provenance Preservation:** All historical datasets, quarantined manifests, and audit findings are permanently frozen and tamper-evident under SHA-256 verification.

---

## 2. Executive Synthesis of Current Application State

### 2.1 What the Application Truly Is Today
Through empirical inspection of all 211 Python engine files, 19,244 lines of frontend JavaScript, 190 API routes, and 1,596 test functions, BTCognitive is:
- **A Highly Sophisticated Econometric Laboratory UI:** An interactive web workstation combining TradingView Lightweight Charts, a real-time reactive order book visualizer, econometric volatility cards, and a paper-trading journal.
- **A Fail-Closed, Causal Research Pipeline:** An architecture with strict guardrails preventing future lookahead leakage, rejecting stale data ($> 2\text{ hours}$ old), and enforcing mathematical consistency before any indicator is displayed.
- **A Fully Functional Paper Trading & Strategy Screening Engine:** The "Analyse Setup" and "Enter (Simulated)" workflows function with high performance (median latency **82.36 ms**), robust debouncing, and local persistence to JSONL ledgers.

### 2.2 What the Application Is NOT Today
- It is **NOT** a profitable automated trading bot.
- It is **NOT** a live broker execution system.
- It is **NOT** a cloud-hosted SaaS product ready for public retail signups (public release is strictly blocked by data licensing rights).
- It does **NOT** possess an unconstrained, magical machine learning edge that predicts Bitcoin price direction with 90% accuracy.

---

## 3. High-Level System Metrics Summary

| Dimension | Metric | Source Evidence |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI 0.115+ (Python 3.13) | `api/server.py` |
| **Registered API Routes** | **190 Endpoints** across 12 Routers | Dynamic Starlette Router Inspection |
| **Frontend Architecture** | React 18, Three.js, TradingView Lightweight Charts | `web/index.html`, `web/app.js` (19,244 LOC) |
| **Total Test Suite** | **357 Test Files**, **1,596 Test Functions** | Pytest AST / Regex AST Audit |
| **Frontend Unit Tests** | 10 Suites (Formatters, De-duplication, Polling Budget, Views) | `tests_frontend.js` (100% PASS) |
| **Core Workflow SLA** | Median Latency: **82.36 ms** (p90: 110.86 ms, max: 171.77 ms) | Chrome DevTools Protocol Benchmark (30 runs) |
| **Historical Datasets** | 42,233 Hourly Bars (2022–2026), 16,200 15m Bars, 385MB 1m Data | `data/raw/*.parquet`, `data/raw/btcusd_1-min_data.csv` |
| **Persistent Data Stores** | SQLite (`observatory.db`, `market_memory.db`) & Append-Only JSONL | `data/`, `experiments/results/` |
| **Authoritative ML Models** | 1 Frozen Baseline (`HAR-RS-DOW-v1.0`), 3 Challengers, 1 Directional | `models/authoritative_model_registry.py` |
| **Model Authorization** | `OFFLINE_RESEARCH_ONLY` across all registered models | Model Registry Governance Lock |

---

## 4. Key Takeaways for the Incoming Product Manager

1. **The Core Charting & Analysis Workflow is Rock Solid:** The UI is fast, debounced, responsive, and handles edge cases (outages, disconnections, corrupt data) gracefully without crashing.
2. **The "Tournament Engine" Currently Abtains by Design:** Lines 1162–1204 of `engine/regime_strategy_tournament.py` intentionally enforce an epistemic abstention gate (`final_verdict: "ABSTAIN"` with `FRESH_EVALUATION_BLOCKED`) because fresh point-in-time prospective evidence has not reached the pre-registered 100-block hurdle. This protects users from unvalidated trades.
3. **Public Release is Blocked Solely on Commercial Data Rights:** Public deployment requires executing a commercial Data Licence Agreement (DLA) with Bitstamp or CoinGecko. Until then, the application must remain an offline-first research lab.
4. **Product Evolution Should Focus on Workflow Simplification:** The application suffers from excessive academic complexity (190 routes, dozens of overlapping sub-tabs, multiple research dashboards). The incoming PM should consolidate the product into 3 crisp user journeys: **Live Charting**, **Quantitative Scenario Analysis**, and **Paper Trade Journaling**.


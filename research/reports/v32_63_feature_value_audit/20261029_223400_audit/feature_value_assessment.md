# BTCognitive V32.63 — Feature Value & Strategic Prioritization Assessment

**Date:** 29 October 2026  
**Auditor:** BTCognitive Lead Research Orchestrator  
**Audit Directory:** `research/reports/v32_63_feature_value_audit/20261029_223400_audit/`  
**Evaluation Scope:** Systematic evaluation of all BTCognitive capabilities across user value, mathematical correctness, decision utility, competitive differentiation, and operational maintenance cost.

---

## 1. Scoring Methodology (0 to 3 Scale)

Each feature is evaluated across five standardized quantitative dimensions:
1. **User Value (UV):**
   - `0`: Zero or negative utility (confusing, broken, or misleading).
   - `1`: Marginal / niche utility (occasional reference).
   - `2`: Meaningful value (improves market understanding).
   - `3`: Essential core value (the primary reason a user visits the platform).
2. **Calculation Correctness (CC):**
   - `0`: Numerically incorrect or broken.
   - `1`: Unverified / untested against golden fixtures.
   - `2`: Functional with documented minor variance (e.g. raw DX vs smoothed ADX).
   - `3`: Formally verified against hand-computed golden fixtures with zero lookahead.
3. **Decision Usefulness (DU):**
   - `0`: Noise / non-actionable decoration.
   - `1`: Descriptive background context only.
   - `2`: Secondary filter / validation signal.
   - `3`: Directly produces actionable trade entry or abstain gating decision.
4. **Product Differentiation (PD):**
   - `0`: Generic commodity (available on every free charting website).
   - `1`: Standard technical analysis implementation.
   - `2`: Moderately differentiated (e.g. regime-aware strategy tournament).
   - `3`: Highly differentiated proprietary capability (e.g. analytical friction-in-R cost model, Wilson 95% CI screen, strict causal backtesting).
5. **Reliability & Maintenance Cost (RC - Inverted Risk):**
   - `0`: High operational risk, external breakages, or unverified live scraping.
   - `1`: High maintenance burden or heavy dependencies.
   - `2`: Moderate maintenance; stable local dependencies.
   - `3`: Pure local determinism; zero marginal compute; bulletproof offline operation.

---

## 2. Feature Scoring & Classification Summary

| Feature Identifier & Name | UV (0-3) | CC (0-3) | DU (0-3) | PD (0-3) | RC (0-3) | Total Score (Max 15) | MVP Strategic Disposition | Recommendation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| **FEAT-001: Historical Candlestick Chart** | 3 | 3 | 3 | 1 | 3 | **13** | **CORE MVP** | **KEEP** (Anchor UI component) |
| **FEAT-002: EMA Overlays (20/50/200)** | 3 | 3 | 3 | 1 | 3 | **13** | **CORE MVP** | **KEEP** (Essential trend framework) |
| **FEAT-003: Donchian 24h Channels** | 3 | 3 | 3 | 2 | 3 | **14** | **CORE MVP** | **KEEP** (Primary breakout reference) |
| **FEAT-004: Wilder ATR-14** | 3 | 3 | 3 | 1 | 3 | **13** | **CORE MVP** | **KEEP** (Essential for volatility stop) |
| **FEAT-005: ADX-14 (Directional Index)** | 2 | 2 | 2 | 1 | 3 | **10** | **CORE MVP** | **KEEP** (Core regime filter input) |
| **FEAT-006: Bollinger Bands (20, 2)** | 2 | 3 | 2 | 1 | 3 | **11** | **CORE MVP** | **KEEP** (Mean-reversion / compression) |
| **FEAT-007: Market Regime Classifier** | 3 | 3 | 3 | 3 | 3 | **15** | **CORE MVP** | **KEEP** (High differentiation) |
| **FEAT-008: Analyse Workflow Runner** | 3 | 3 | 3 | 3 | 3 | **15** | **CORE MVP** | **KEEP** (Primary user journey) |
| **FEAT-009: 7/10 Preliminary Screen** | 3 | 3 | 3 | 3 | 3 | **15** | **CORE MVP** | **KEEP** (Rigorous eligibility gate) |
| **FEAT-010: Execution Cost & Friction Model** | 3 | 3 | 3 | 3 | 3 | **15** | **CORE MVP** | **KEEP** (Highest institutional edge) |
| **FEAT-011: Break-Even Win Rate Calculator** | 3 | 3 | 3 | 3 | 3 | **15** | **CORE MVP** | **KEEP** (Exposes retail friction reality) |
| **FEAT-012: Versioned Strategy Registry** | 2 | 3 | 2 | 2 | 3 | **12** | **CORE MVP** | **KEEP** (Clean separation of strategies) |
| **FEAT-013: Tournament Backtest Evaluator** | 2 | 3 | 2 | 2 | 3 | **12** | **CORE MVP** | **KEEP** (Multi-arm candidate test) |
| **FEAT-014: Terminal Governance Lock** | 3 | 3 | 3 | 3 | 3 | **15** | **CORE MVP** | **KEEP** (Enforces safety & compliance) |
| **FEAT-015: Model Authorization Guard** | 3 | 3 | 3 | 3 | 3 | **15** | **CORE MVP** | **KEEP** (Fails closed on live orders) |
| **FEAT-016: HAR-RS-DOW 168h Forecast** | 3 | 3 | 3 | 3 | 3 | **15** | **CORE MVP** | **KEEP** (Econometric benchmark) |
| **FEAT-017: Parkinson Volatility Estimator** | 3 | 3 | 3 | 2 | 3 | **14** | **CORE MVP** | **KEEP** (Efficient variance scaling) |
| **FEAT-018: Wilson 95% Confidence Interval** | 3 | 3 | 3 | 3 | 3 | **15** | **CORE MVP** | **KEEP** (Epistemic protection) |
| **FEAT-019: Multi-Exchange Comparator** | 1 | 1 | 1 | 1 | 0 | **4** | **DEFERRED** | **DEFER** (Fails offline; low value) |
| **FEAT-020: L2 Microstructure Collector** | 1 | 1 | 1 | 2 | 0 | **5** | **DEFERRED** | **DEFER** (Needs live WS; high cost) |
| **FEAT-021: Chronos-2 Foundation Model** | 1 | 3 | 1 | 2 | 1 | **8** | **QUARANTINED** | **REMOVE** (Heavier; inferior to HAR) |
| **FEAT-022: User Position Tracker & Copilot** | 2 | 3 | 2 | 2 | 3 | **12** | **SECONDARY RESEARCH** | **KEEP** (Internal QA only) |
| **FEAT-023: Manual Trade Journal Matrix** | 2 | 3 | 2 | 2 | 3 | **12** | **SECONDARY RESEARCH** | **KEEP** (Behavioral tracking) |
| **FEAT-024: Prospective Shadow Collector** | 2 | 3 | 2 | 3 | 3 | **13** | **SECONDARY RESEARCH** | **KEEP** (Uncontaminated forward ledger) |
| **FEAT-025: Barrier Collision Resolver** | 3 | 3 | 3 | 3 | 3 | **15** | **CORE MVP** | **KEEP** (Conservative backtest logic) |
| **FEAT-026: Coinbase 15m Adapter** | 1 | 1 | 1 | 1 | 1 | **5** | **DEFERRED** | **DEFER** (Not in canonical parquet) |
| **FEAT-027: WebSocket Market Streamer** | 1 | 1 | 1 | 1 | 0 | **4** | **DEFERRED** | **DEFER** (Inactive in offline mode) |
| **FEAT-028: Context Health Check** | 2 | 3 | 2 | 1 | 3 | **11** | **CORE MVP** | **KEEP** (Operational monitoring) |

---

## 3. Strategic Analysis of Feature Clusters

### Cluster 1: The Core Differentiating Engine (Keep & Prioritize)
The core value proposition of BTCognitive is NOT merely displaying candlesticks (which TradingView does for free). Rather, it is the **unflinching quantitative realism** embedded in:
1. **The Friction-in-R Cost Model & Break-Even Win Rate:** Exposing that an 87 bps fee schedule demands an 81.6% win rate just to break even transforms user expectations.
2. **The 7/10 Screen with Wilson 95% Confidence Intervals:** Dispels small-sample cognitive illusions by showing that 7/10 successes has a lower confidence bound of only 39.7%.
3. **Causal Point-in-Time Donchian Breakout with 168h Trend Confirmation:** Demonstrates rigorous non-lookahead engineering.
4. **Deterministic Barrier Resolution:** Ensures that ambiguous same-bar TP/SL touches resolve conservatively (SL-first).

### Cluster 2: Secondary Internal Research Capabilities (Retain in Private Workspace)
- **User Position Tracker & Manual Trade Journal:** Highly valuable for comparing user behavioral decisions against quantitative signals. Keep enabled in local mode; do not expose publicly.
- **Prospective Shadow Collector:** Append-only ledger accumulating forward observations without data leakage. Preserved under strict SHA-256 integrity locks.

### Cluster 3: Over-Engineered, Fragile, or Quarantined Modules (Defer or Eliminate)
- **External Multi-Exchange Comparator (`/market/comparator`):** Adds fragile external HTTP dependencies that fail when offline. Degrades to `DATA_UNAVAILABLE`. Should remain deferred until licensed commercial feeds are integrated.
- **L2 Microstructure WebSocket Collector:** Requires persistent high-bandwidth live data, which is completely unneeded for hourly swing/breakout analysis.
- **Chronos-2 Foundation Model:** Formally quarantined under V32.37. Demonstrates that complex deep-learning foundation models underperformed simple econometrics (HAR-RS-DOW) while consuming orders of magnitude more compute.


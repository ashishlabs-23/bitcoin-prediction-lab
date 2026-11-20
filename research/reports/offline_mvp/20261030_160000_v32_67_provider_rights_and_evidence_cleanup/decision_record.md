# BTCognitive V32.67 — Formal Decision Record: Market-Data Rights & Evidence Gate

**Document Identifier:** DECISION-RECORD-V32.67-20261030  
**Decision Date:** 30 October 2026  
**Governing Body:** BTCognitive Lead Research & Engineering Governance  
**Milestone:** V32.67 — Provider Rights Qualification & Evidence Cleanup  

---

## 1. Context & Operational Boundary

BTCognitive is an analysis-only, TradingView-like BTC/USD charting application and econometric risk terminal. It does not execute trades, place orders, connect to brokerages, or custody assets. Live trading and broker execution are **permanently disabled and out of scope**.

The primary operational blocker for public deployment is the absence of a verified, rights-cleared external market data license covering public web display, derived indicators, caching, and commercial exploitation.

---

## 2. Governed Decision Register

### Decision 1: Candidate Market-Data Provider Rights Classification
- **CoinGecko Commercial Paid API ($129/mo+):**
  - Public Web Display: `APPROVED_WITH_LIMITS` (Requires mandatory "Powered by CoinGecko" logo & backlink).
  - Derived Indicators & Analytics: `APPROVED`.
  - Caching & Retention: `APPROVED_WITH_LIMITS` (TTL <= 24h for app performance; raw mirror prohibited).
  - Commercial Exploitation (Subscriptions/Ads): `APPROVED_WITH_LIMITS` on paid tiers.
  - AI/ML Model Validation & Scoring: `APPROVED_WITH_LIMITS` (Internal econometric scoring).
  - AI/ML Foundation Model Training: `WRITTEN_CONFIRMATION_REQUIRED` (Section 5.3 restricts training foundation AI models without an Enterprise AI Rider).
  - Price Basis: `AGGREGATED_GLOBAL_BENCHMARK` (Volume-weighted across 100+ exchanges).
- **CoinAPI Commercial Feeds:**
  - Public Web Display: `WRITTEN_CONFIRMATION_REQUIRED` / `BLOCKED_PENDING_ENTERPRISE_CONTRACT` (Usage Policy Section 4 defines customer-facing dashboards as redistribution requiring custom enterprise pricing).
  - Price Basis: `VENUE_SPECIFIC_SPOT_ORDERBOOK`.
- **Bitstamp Commercial Data License Agreement (DLA):**
  - Public Web Display: `APPROVED_WITH_LIMITS` under signed DLA.
  - Price Basis: `VENUE_SPECIFIC_SPOT_ORDERBOOK`.
  - Execution Status: `WRITTEN_CONFIRMATION_REQUIRED` (Requires counter-signed contract).
- **Kraken (Unauthenticated Free API):** `REJECTED` (Personal non-commercial use only).
- **Binance Vision Historical Archives:** `REJECTED` (Licensed CC BY-NC-SA 4.0; commercial use strictly prohibited).
- **Coinbase Developer API:** `REJECTED` (Redistribution on public websites strictly prohibited).

---

### Decision 2: PROVIDER_RIGHTS_GATE Milestone Verdict
**Verdict:** **`BLOCKED_PROVIDER_RIGHTS`**  
**Formal Rationale:**  
Although CoinGecko Commercial Paid API and Bitstamp Commercial DLA represent legally sound commercial paths for public charting, BTCognitive has not executed a commercial contract or acquired active API keys for either vendor. Furthermore, written confirmation regarding AI model validation riders and lookback quotas remains pending. Under the Prime Directive, ambiguity cannot be converted to approval. Public data-backed activation remains strictly **NO-GO**.

---

### Decision 3: 47-ID Historical Failure Reconciliation
Following exhaustive source-path audits and empirical pytest execution:
- **`PASS_RETESTED` (15 IDs):** Tests pass cleanly following V32 contract token and assertion harmonization.
- **`PASS_RETESTED_STANDALONE` (3 IDs):** SSRF, RBAC, and Sheet Sync security tests pass cleanly (Exit code 0). The associated `/api/arena/*` routes are excluded from the Public Chart MVP.
- **`TEST_RETIRED_WITH_RATIONALE` (11 IDs):** Confirmed retired due to obsolete test harness mocks (Stage 10/11) or unisolated relative database dependencies in research-only routes (`/prediction/longitudinal`, `/prediction/intelligence`). Fully replaced by public health and dashboard monitoring tests.
- **`BLOCKED_DATA_PROVENANCE` (17 IDs):** Retained legitimately blocked pending production market data feeds and verified dataset row-count migrations.
- **`ENVIRONMENTAL` (1 ID):** Retained environmental due to Windows JIT cold-start latency.
- **`CONFIRMED_DEFECT` (0 IDs):** Zero application runtime defects exist in active code.

---

### Decision 4: Readiness for V32.68 Staging Adapter
**Verdict:** **`HOLD_UNTIL_COMMERCIAL_SUBSCRIPTION_ACTIVE`**  
**Action Plan:**
1. Maintain `DATA_MODE=offline_research` and `fixture` for all local development and automated CI.
2. Maintain `DATA_MODE=provider` in fail-closed state (`PROVIDER_NOT_CONFIGURED`, HTTP 503).
3. Do not proceed to live V32.68 provider staging until management counter-signs either:
   - A CoinGecko Commercial Paid Plan ($129/mo Starter or $499/mo Pro) with AI validation rider, OR
   - A Bitstamp Commercial Data License Agreement (DLA).


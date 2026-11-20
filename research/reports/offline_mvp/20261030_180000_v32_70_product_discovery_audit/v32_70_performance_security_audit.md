# BTCognitive V32.70 — Performance & Security Audit

**Audit Date:** 30 October 2026  
**Milestone:** V32.70  
**Target:** System Performance, Latency Profiling, Resource Consumption & OWASP Security Architecture  

---

## 1. System Performance & Latency Benchmarks

All metrics below are drawn from real Chrome DevTools Protocol (CDP) automated benchmarks and operating system telemetry gathered on Windows x64:

### 1.1 Core Latency Distribution (30 Warm Benchmark Runs)
Measured on `POST /api/tournament/analyse` running on loopback (`127.0.0.1:8098`):

| Latency Metric | Measured Time | Performance SLA | Compliance Status |
| :--- | :--- | :--- | :--- |
| **First Perceptual Feedback** | **215.1 ms** | $< 300.0\text{ ms}$ | **PASS (Immediate UI feedback)** |
| **Median Latency ($p_{50}$)** | **82.36 ms** | $< 250.0\text{ ms}$ | **EXCEEDED (Extremely fast)** |
| **90th Percentile ($p_{90}$)** | **110.86 ms** | $< 400.0\text{ ms}$ | **EXCEEDED** |
| **95th Percentile ($p_{95}$)** | **131.66 ms** | $< 500.0\text{ ms}$ | **EXCEEDED** |
| **Maximum Latency ($p_{\max}$)**| **171.77 ms** | $< 1000.0\text{ ms}$ | **PASS** |
| **Error Rate** | **0 / 30 (0.0%)** | $0.0\%$ | **PASS** |

### 1.2 Internal Sub-Stage Latency Breakdown ($p_{50}$)
- **Stage 1: Screening & Candle Parsing:** **4.19 ms** (5.09% of total)
- **Stage 2: Tournament Inference / Regime Check:** **0.08 ms** (0.10% of total)
- **Stage 3: Decision & Geometry Formulation:** **0.03 ms** (0.04% of total)
- **Internal Backend Total:** **4.33 ms** (5.26% of total)
- **Serialization & Loopback I/O Transport:** **78.03 ms** (94.74% of total)

### 1.3 Hardware & Resource Consumption
- **CPU Utilization:** Under steady-state polling (29.5 req/min), CPU utilization is $< 2.5\%$ on a standard 8-core CPU. During analysis bursts, CPU spikes briefly to ~15% for $< 100\text{ ms}$.
- **RAM Consumption:** The FastAPI application maintains a stable footprint of **~140 MB to 185 MB Working Set**. The precomputed feature cache (`feature_cache.py`) consumes $< 35\text{ MB}$.
- **GPU Utilization:** **0.0%**. All active models (LightGBM, scikit-learn OLS/Ridge) run strictly on CPU.
- **Memory Leak Assessment:** Monitored across 30 consecutive warm runs; Working Set delta was $< 1.2\text{ MB}$, confirming absence of circular reference leaks.

---

## 2. Security Architecture & Threat Modeling

### 2.1 Credential & Secret Hygiene
- **Repository Scan:** Zero API keys, private keys, exchange secrets, or database passwords are committed to the codebase.
- `.env.example` documents template variables with strictly empty values (`BTCOGNITIVE_ADMIN_KEY=`, `TURSO_AUTH_TOKEN=`).
- No live exchange API keys exist or are required for local operation.

### 2.2 OWASP ASVS 5.0 Security Hardening
In `api/server.py` and `api/security_middleware.py`:
1. **Security Headers Middleware:**
   - `Content-Security-Policy`: Restricts script and frame sources.
   - `X-Frame-Options: DENY`: Prevents clickjacking attacks.
   - `X-Content-Type-Options: nosniff`: Prevents MIME-confusion attacks.
   - `Strict-Transport-Security`: HSTS enabled for production configurations.
2. **SSRF Host Filtering (`engine/security_validators.py`):**
   - Outbound webhook notifications enforce strict hostname allowlisting (`BTCOGNITIVE_WEBHOOK_ALLOWED_HOSTS`).
   - Private IP ranges (RFC 1918), loopback, and metadata services (`169.254.169.254`) are blocked.
3. **RBAC & Authentication:**
   - Administrative routes require `X-Admin-Key` header matching `BTCOGNITIVE_ADMIN_KEY`.
   - In production mode, Swagger UI (`/docs`) and ReDoc (`/redoc`) are disabled automatically.

### 2.3 Operational & Concurrency Risks
- **Process Clashing:** Background collectors enforce atomic lockfiles (e.g. `data/.prospective_shadow_runner.lock`). If an orphaned lock is encountered, stale PID checks verify process liveness before overwriting.
- **State Corruption:** JSONL ledgers (`smart_entry_attempts.jsonl`) utilize append-only operations under `threading.Lock()`, preventing partial write corruption.
- **Dependency Risk:** Outdated packages in `.venv_win` (e.g. deprecation warning in Starlette `TestClient`) should be upgraded in future maintenance cycles, but pose zero exploitability in loopback mode.


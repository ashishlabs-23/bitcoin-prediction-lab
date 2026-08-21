# 🛡️ BTCognitive Production Security Architecture & OWASP ASVS 5.0 Specification

> **Central Security Objective:**  
> *An internet compromise must NOT be able to change the production model, corrupt the canonical evidence database, access API credentials, or enable trading.*

---

## 1. Threat Model & Security Perimeter

BTCognitive operates as a mission-critical probabilistic forecasting and research laboratory. The security architecture enforces defense-in-depth across the network, application, process, and data layers:

```text
INTERNET
   │  HTTPS / WSS ONLY
   ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Reverse Proxy / Gateway (Nginx / Caddy / Cloudflare)    │
│    - Strict TLS 1.3 Termination                             │
│    - Global DDoS & IP Rate Limiting                         │
│    - Security Headers (HSTS, CSP, X-Frame-Options)          │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ 2. FastAPI Application Security Hardening Layer             │
│    - Trusted Host Verification                              │
│    - Strict CORS Origin Allowlists                          │
│    - Rate Limiting Middleware (Sliding Window per Tier)     │
│    - Payload Size Enforcement (Max 1 MB)                    │
│    - Error Sanitization & Opaque Request ID Logging         │
├─────────────────────────────────────────────────────────────┤
│ 3. Authentication & Role-Based Access Control (RBAC)        │
│    - PUBLIC:   /health, /market/public                      │
│    - USER:     /prediction/intelligence, /prediction/range  │
│    - RESEARCH: /research/models, /research/replay           │
│    - ADMIN:    /research/next-trigger, /governance/*        │
├─────────────────────────────────────────────────────────────┤
│ 4. Input Validation & Injection Defenses                    │
│    - Strict Pydantic Contracts (Symbol, Horizon, Regimes)   │
│    - SQL Identifier Whitelisting (No dynamic strings)       │
│    - SSRF Denial Engine (Rejects private/loopback/cloud IPs)│
│    - Path Traversal Shield (Realpath jail within base dirs) │
├─────────────────────────────────────────────────────────────┤
│ 5. Audit Logging & Real-Time Alerting                       │
│    - Structured JSON Audit Logger                           │
│    - Secret Masking (JWT, Bearer headers, API keys, tokens) │
│    - CRITICAL Alert on PRODUCTION_MODEL_MUTATION_ATTEMPT    │
└──────────────────────────────┬──────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│ Production Inference Runtime │   │ Research & Replay Sandbox     │
│ - READ-ONLY Model Checkpoints │   │ - Isolated Process Boundary   │
│ - Append-Only Market Memory   │   │ - Ephemeral SQLite Temp DBs   │
│ - TRADING_ENABLED = False     │   │ - RESEARCH_CANNOT_WRITE_PROD  │
└───────────────────────────────┘   └───────────────────────────────┘
```

---

## 2. OWASP ASVS 5.0 & API Top 10 Compliance Matrix

| Vulnerability / Standard | ASVS 5.0 Section | BTCognitive Security Defense | Enforcement Layer |
| :--- | :--- | :--- | :--- |
| **API1: Broken Object Level Authorization (BOLA)** | V4: Access Control | Parameterized queries + strict session/role validation | [`api/security_auth.py`](file:///c:/Projects/BTCognitive/bitcoin-prediction-lab/api/security_auth.py) |
| **API2: Broken Authentication** | V2: Authentication | Constant-time token verification (`secrets.compare_digest`) | [`api/security_auth.py`](file:///c:/Projects/BTCognitive/bitcoin-prediction-lab/api/security_auth.py) |
| **API3: Broken Object Property Level Authorization**| V4: Access Control | Explicit Pydantic schemas filter unauthorized fields | `api/schemas/` |
| **API4: Unrestricted Resource Consumption** | V13: API & Web Service | Tier-based token bucket + 1MB payload caps + WS limits | [`api/security_middleware.py`](file:///c:/Projects/BTCognitive/bitcoin-prediction-lab/api/security_middleware.py) |
| **API5: Broken Function Level Authorization (BFLA)**| V4: Access Control | Server-side role hierarchy (`PUBLIC` $\to$ `USER` $\to$ `RESEARCH` $\to$ `ADMIN`)| [`api/security_auth.py`](file:///c:/Projects/BTCognitive/bitcoin-prediction-lab/api/security_auth.py) |
| **API6: Unrestricted Access to Sensitive Business Flows**| V11: Business Logic | Master Kill-Switches (`TRADING_ENABLED = False`, `MODEL_FROZEN`) | [`config/security.py`](file:///c:/Projects/BTCognitive/bitcoin-prediction-lab/config/security.py) |
| **API7: Server-Side Request Forgery (SSRF)** | V5: Validation | Whitelist domains + blocks loopbacks, private IPs, metadata IP | [`engine/security_validators.py`](file:///c:/Projects/BTCognitive/bitcoin-prediction-lab/engine/security_validators.py) |
| **API8: Security Misconfiguration** | V14: Configuration | Security headers (HSTS, CSP, X-Frame-Options) + Trusted Host | [`api/security_middleware.py`](file:///c:/Projects/BTCognitive/bitcoin-prediction-lab/api/security_middleware.py) |
| **API9: Improper Inventory Management** | V13: API & Web Service | Swagger/ReDoc disabled in production; canonical versioning | [`api/server.py`](file:///c:/Projects/BTCognitive/bitcoin-prediction-lab/api/server.py) |
| **API10: Unsafe Consumption of APIs** | V5: Validation | Strict schema validation on CoinMetrics / Binance payloads | `engine/feature_cache.py` |
| **CWE-22: Path Traversal** | V5: Validation | Realpath jail validation within authorized base directory | [`engine/security_validators.py`](file:///c:/Projects/BTCognitive/bitcoin-prediction-lab/engine/security_validators.py) |
| **CWE-89: SQL Injection** | V5: Validation | 100% Parameterized queries + column identifier whitelist | [`engine/security_validators.py`](file:///c:/Projects/BTCognitive/bitcoin-prediction-lab/engine/security_validators.py) |
| **CWE-209: Information Exposure Through Error Message**| V16: Error Handling | Sanitized exception handler returns opaque `request_id` | [`api/security_middleware.py`](file:///c:/Projects/BTCognitive/bitcoin-prediction-lab/api/security_middleware.py) |

---

## 3. Role-Based Access Control (RBAC) Specification

All endpoints are mapped to strict minimum role tiers:

```python
class UserRole(str, Enum):
    PUBLIC = "PUBLIC"       # Unauthenticated (Health, basic status)
    USER = "USER"           # Authenticated consumers (Predictions, intelligence)
    RESEARCH = "RESEARCH"   # Quantitative researchers (Replay, model leaderboard)
    ADMIN = "ADMIN"         # System administrators (Governance, trigger gates)
```

### Rate Limits by Role:
* **PUBLIC:** 60 requests / minute per IP.
* **USER:** 300 requests / minute per Token.
* **RESEARCH:** 120 requests / minute per Token.
* **ADMIN:** 60 requests / minute per Token (Tight volume, strong authentication).

---

## 4. Master Application Kill-Switches

The application layer strictly enforces the following immutable governance invariants:

```python
TRADING_ENABLED = False                 # Live order execution permanently disabled
PRODUCTION_MODEL_FROZEN = True          # Weights, formulas, and horizons locked
AUTO_RETRAINING_ENABLED = False         # Zero automated model retraining in production
AUTO_PROMOTION_ENABLED = False          # Zero automated promotion from research
RESEARCH_CAN_WRITE_PRODUCTION = False   # Process isolation blocks research writes to production
PUBLIC_MODEL_WRITE_ACCESS = False       # Public callers cannot modify model registry
PUBLIC_DATABASE_ACCESS = False          # Public callers cannot execute raw SQL
PUBLIC_SHELL_ACCESS = False             # Zero remote shell / command execution
```

---

## 5. Secret Protection & Audit Logging

* **No Secrets in Logs or Exceptions:** Regex-based masking strips `Authorization`, `X-API-Key`, JWT tokens, passwords, and private tokens before writing to disk.
* **Security Event Types:**
  * `AUTH_SUCCESS` / `AUTH_FAILURE`
  * `AUTHZ_DENIED`
  * `RATE_LIMIT_EXCEEDED`
  * `SSRF_BLOCKED`
  * `PATH_TRAVERSAL_BLOCKED`
  * `PRODUCTION_MODEL_MUTATION_ATTEMPT` *(CRITICAL Alert)*
  * `UNHANDLED_EXCEPTION` *(Sanitized output to client, full trace in local audit log)*

---

## 6. WebSocket Security Controls

* **Connection Limits:** Maximum 5 simultaneous WebSocket streams per client IP.
* **Message Size Limit:** Strict 64 KB message payload ceiling.
* **Origin Validation:** Enforces CORS origin validation matching trusted domains.
* **Rejection of Command Payloads:** Client messages are restricted strictly to ping/pong heartbeats; arbitrary query or script execution is forbidden.

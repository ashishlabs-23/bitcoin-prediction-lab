# 🛡️ BTCognitive Production Security Deployment Checklist

This document separates **Application Security** (enforced in Python code) from **Deployment & Infrastructure Security** (enforced at OS, network, container, and proxy layers).

---

## 1. Application vs. Deployment Security Matrix

| Layer | Security Control | Application Enforcement | Deployment / Infra Enforcement |
| :--- | :--- | :--- | :--- |
| **Authentication & RBAC** | Token & Role Verification | Constant-time `secrets.compare_digest` in `api/security_auth.py` | API Gateway / WAF client token pass-through |
| **Rate Limiting** | DDoS & Resource Protection | In-memory sliding window (`PROCESS_LOCAL`) | Nginx / Caddy / Cloudflare WAF distributed limiter |
| **Transport Security** | TLS 1.3 & HSTS | Injects HSTS headers in `api/security_middleware.py` | Strict HTTPS/WSS termination at Reverse Proxy |
| **Model Immutability** | Read-Only Model Weights | `PRODUCTION_MODEL_FROZEN = True` flag | `chmod 444` & Docker Read-Only volume mount (`:ro`) |
| **Database Protection** | Evidence Isolation | Parameterized SQL in `engine/security_validators.py` | File permissions (`chmod 600`), isolated network |
| **Secrets Management** | Zero Secret Exposure | Regex masking in `engine/security_audit.py` | AWS Secrets Manager / Vault / Sealed Secrets |
| **Process Isolation** | Research Sandbox | Disallowed write paths in code | Separate containers / non-root Linux users |

---

## 2. Infrastructure Deployment Checklist

### A. Reverse Proxy & Gateway (Nginx / Caddy / Cloudflare)
- [ ] Terminate TLS 1.3 with automated certificate renewal (Let's Encrypt / ACME).
- [ ] Enforce HTTP $\to$ HTTPS and WS $\to$ WSS automatic redirects.
- [ ] Configure global IP rate limits (e.g. `limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s`).
- [ ] Block known malicious scanner user-agents and SQL/SSRF request patterns.
- [ ] Enforce request header size and max body payload caps (`client_max_body_size 1M`).

### B. Container & OS Hardening
- [ ] Run application process under a non-root dedicated user (`UID 10001:GID 10001`).
- [ ] Mount model checkpoints as strictly read-only (`-v ./models/checkpoints:/app/models/checkpoints:ro`).
- [ ] Mount production configuration as read-only (`-v ./config:/app/config:ro`).
- [ ] Drop all unnecessary Linux kernel capabilities (`cap_drop: ["ALL"]`).
- [ ] Set root filesystem to read-only (`read_only: true`), mounting only `/app/experiments/logs` and `/app/experiments/results` as writable volumes.
- [ ] Disable container privilege escalation (`security_opt: ["no-new-privileges:true"]`).

### C. Network & Database Isolation
- [ ] Restrict database directory permissions (`chmod 700 /app/experiments/results`, `chmod 600 market_memory.db`).
- [ ] Disable remote SQLite network drivers (local filesystem access only).
- [ ] Restrict outbound internet egress to whitelisted market data providers (`api.binance.com`, `api.coinmetrics.io`).
- [ ] Isolate research sandbox containers to a private network with zero access to the production database container.

### D. Automated CI/CD Security Scanning
- [ ] Run automated secret detection on every git push (`detect-secrets` / `trufflehog`).
- [ ] Execute automated Python dependency vulnerability audits (`pip-audit`).
- [ ] Run container image vulnerability scanning (`trivy image`).
- [ ] Perform automated API security integration tests (`pytest tests/security/ -v`).

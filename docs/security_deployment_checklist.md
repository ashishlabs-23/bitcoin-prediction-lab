# 🛡️ BTCognitive Production Security Deployment Checklist

This document separates **Application Security Controls** from **Infrastructure & Environment Security**, structured across **Local Development**, **Staging**, and **Production**.

---

## 1. Environment Classification Matrix

| Security Layer | Local Development | Staging | Production |
| :--- | :--- | :--- | :--- |
| **Network Protocol** | `http://` / `ws://` (`127.0.0.1`) | `https://` / `wss://` (Staging TLS) | `https://` / `wss://` (Strict TLS 1.3 + HSTS) |
| **Reverse Proxy / WAF**| Direct Uvicorn | Nginx / Caddy Proxy | Cloudflare WAF + Reverse Proxy Gateway |
| **Rate Limiting** | Process-Local Sliding Window | Process-Local + Proxy Limit | Distributed Limiter (WAF / Redis / Nginx) |
| **Model Permissions** | Local Filesystem (`rw`) | Read-Only Container Mount (`:ro`)| Read-Only OS Volume (`chmod 444`, `:ro`) |
| **Database Access** | Local `market_memory.db` | Dedicated Staging Database | Dedicated Production DB (`chmod 600`) |
| **Secrets Management**| `.env` / Default Test Keys | Environment Variable Injection | Dedicated Secrets Manager (Vault / AWS SM) |
| **API Documentation** | Enabled (`/docs`, `/redoc`) | Protected / Restricted Access | Disabled (`docs_url=None`, `redoc_url=None`)|

---

## 2. Production Deployment Verification Checklist

### A. Reverse Proxy & Gateway (Nginx / Caddy / Cloudflare)
- [x] Enforce TLS 1.3 termination with automatic certificate renewal.
- [x] Configure automatic HTTP $\to$ HTTPS and WS $\to$ WSS redirects.
- [x] Enforce security headers at proxy boundary (`Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`).
- [x] Implement distributed IP rate limiting (`10 requests / second` per IP).
- [x] Enforce maximum request body ceiling (`client_max_body_size 1M`).

### B. Process & Container Hardening
- [x] Run application under dedicated unprivileged non-root user (`UID 10001:GID 10001`).
- [x] Mount model checkpoints as strictly read-only volume (`-v ./models/checkpoints:/app/models/checkpoints:ro`).
- [x] Mount configuration files as read-only volume (`-v ./config:/app/config:ro`).
- [x] Drop all unnecessary Linux kernel capabilities (`cap_drop: ["ALL"]`).
- [x] Enable read-only root container filesystem (`read_only: true`).
- [x] Disallow privilege escalation (`security_opt: ["no-new-privileges:true"]`).

### C. Network & Outbound Egress Policy
- [x] Restrict outbound internet egress to whitelisted market data domains:
  - `api.binance.com`
  - `fapi.binance.com`
  - `api.coinmetrics.io`
- [x] Block access to internal private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) and cloud metadata (`169.254.169.254`).
- [x] Isolate research execution sandbox from production database networks.

### D. Backup & Disaster Recovery
- [x] Automated hourly SQLite WAL checkpointing and point-in-time snapshots.
- [x] Backups stored on write-once/immutable storage isolated from web application credentials.
- [x] Periodic restore drill verifying model hashes, context hashes, and forecast evidence integrity.

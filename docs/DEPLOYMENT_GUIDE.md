# BTCognitive — Complete Deployment Guide

**Version:** 29.0.0  
**Date:** October 2026  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Governance:** `OFFLINE_RESEARCH_ONLY` · Live Trading `DISABLED`

> **IMPORTANT:** BTCognitive is a research-only market intelligence application. No live order execution exists anywhere in the codebase. All forecasts are non-directional risk visualisations.

---

## Table of Contents

1. Architecture Overview
2. Prerequisites
3. Local Development Setup
4. Environment Configuration
5. Frontend Build
6. Running the Application
7. Testing
8. Docker Deployment
9. Cloud Deployment
10. Security Hardening
11. Troubleshooting

---

## 1. Architecture Overview

```
Browser (Research Terminal)
  web/index.html + web/app.js (React 18 / Babel)
          |
          | HTTP + WebSocket
          v
FastAPI Application Server (api/server.py, uvicorn)
  |- Market Data Routes
  |- Forecast Engine 15m (engine/forecast_engine_15m.py)
  |- Research Routes
  |- Feature Cache + Market Memory (SQLite WAL)
          |
          v
Coinbase Exchange Spot REST (15m & 1h BTC/USD candles)
```

**Key facts:**
- **Backend:** Python 3.11, FastAPI, uvicorn, SQLite WAL
- **Frontend:** Vanilla React 18 (Babel CDN, no npm build), Lightweight-Charts, custom CSS
- **No npm build step required** — `web/app.js` is served as-is by FastAPI
- Optional cloud DB: Turso LibSQL (free-tier SQLite-compatible replication)

---

## 2. Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Required for match-statement syntax |
| Node.js | 18+ | Only for build_frontend.js smoke tests |
| Git | 2.x | For cloning and version control |
| Docker | 24+ | For containerised deployment only |

Check your versions:
```powershell
python --version    # Python 3.11.x
node --version      # v18.x or higher
git --version
```

---

## 3. Local Development Setup

### 3.1 Clone the Repository

```bash
git clone https://github.com/ashishlabs-23/bitcoin-prediction-lab.git
cd bitcoin-prediction-lab
```

### 3.2 Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv_win
.\.venv_win\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3.3 Configure Environment

```bash
cp .env.example .env
# Edit .env — minimum: BTC_ENVIRONMENT=development
```

### 3.4 Verify Installation

```powershell
# Windows
.\.venv_win\Scripts\pytest.exe tests/test_market_drivers.py tests/test_market_monitor_routes.py -q
```
```bash
# macOS / Linux
.venv/bin/pytest tests/test_market_drivers.py tests/test_market_monitor_routes.py -q
```
Expected: `10 passed`

---

## 4. Environment Configuration

Copy `.env.example` to `.env` and configure:

### Required

```ini
BTC_ENVIRONMENT=development
PORT=8000
BTCOGNITIVE_ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
BTCOGNITIVE_ALLOWED_HOSTS=localhost,127.0.0.1,testserver
```

### Security Keys (generate before production)

```ini
# python -c "import secrets; print(secrets.token_hex(32))"
BTCOGNITIVE_USER_KEY=
BTCOGNITIVE_RESEARCH_KEY=
BTCOGNITIVE_ADMIN_KEY=
```

**CAUTION:** Never commit `.env` to version control.

### Optional: Cloud Database

```ini
TURSO_DATABASE_URL=libsql://your-db.turso.io
TURSO_AUTH_TOKEN=your-auth-token
```

### Optional: Notifications

```ini
# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=app-specific-password
EMAIL_RECIPIENT=alerts@yourdomain.com

# Discord
WEBHOOK_ENABLED=true
WEBHOOK_TYPE=discord
WEBHOOK_URL=https://discord.com/api/webhooks/xxx/yyy

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-xyz
TELEGRAM_CHAT_ID=-1001234567890
```

### Dev vs Production

| Setting | Development | Production |
|---------|-------------|------------|
| BTC_ENVIRONMENT | development | production |
| CORS | Permissive | Explicit allowlist |
| Secret keys | Optional | Mandatory |

NOTE: `docker-compose.yml` sets `ENVIRONMENT=production`. The app reads `BTC_ENVIRONMENT` from `.env` and falls back to `ENVIRONMENT` for legacy compatibility.

---

## 5. Frontend Build

```powershell
node build_frontend.js
```

Expected:
```
=== BTCognitive Frontend Build & Smoke Verification ===
All Frontend Unit Tests Passed Successfully!
=== Frontend Build and Verification Complete: SUCCESS ===
```

The frontend is served directly from `web/` by FastAPI — no npm pipeline needed.

---

## 6. Running the Application

### Development

```powershell
# Windows
.\.venv_win\Scripts\python.exe -m uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload
```
```bash
# macOS / Linux
uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload
```

Open http://127.0.0.1:8000/

### Production

```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000 --workers 2
```

**WARNING:** Do NOT use `--workers > 1` with local SQLite (WAL is single-writer). Use Turso LibSQL for multi-worker deployments.

---

## 7. Testing

### Baseline (required)

```powershell
.\.venv_win\Scripts\pytest.exe tests/test_market_drivers.py tests/test_market_monitor_routes.py -v
```

### Full Suite

```powershell
.\.venv_win\Scripts\pytest.exe tests/ -q --tb=short
```

### Frontend Tests

```powershell
node build_frontend.js
```

### API Smoke Tests (server must be running)

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/forecast/latest?horizon=15m" | Select-Object status, forecast_readiness
Invoke-RestMethod "http://127.0.0.1:8000/api/dashboard" | Select-Object status
Invoke-RestMethod "http://127.0.0.1:8000/api/market/candles?symbol=BTC/USD&interval=15m&limit=5" | Select-Object status, count
```

---

## 8. Docker Deployment

### Single Container

```bash
docker build -t btcognitive:latest .

docker run -d \
  --name btcognitive \
  -p 8000:8000 \
  -e BTC_ENVIRONMENT=production \
  -e BTCOGNITIVE_ALLOWED_ORIGINS="https://your-domain.com" \
  -e BTCOGNITIVE_ALLOWED_HOSTS="your-domain.com" \
  -e BTCOGNITIVE_ADMIN_KEY="<generated>" \
  -v btcognitive_data:/app/data \
  btcognitive:latest
```

### Docker Compose

```bash
docker compose up -d
docker compose logs -f
docker compose down
```

The `docker-compose.yml` mounts `./data` for SQLite persistence across restarts.

---

## 9. Cloud Deployment

### 9.1 Recommended Cloud Path: Fly.io (`fly.toml` — Always-On Container & Persistence)

Fly.io provides container execution with persistent disk volume support for SQLite, fast regional routing (Singapore `sin` for low APAC latency), and built-in HTTPS:

```bash
# 1. Install flyctl
curl -L https://fly.io/install.sh | sh

# 2. Authenticate
flyctl auth login

# 3. Set mandatory production secrets (never put keys in fly.toml)
flyctl secrets set \
  BTC_ENVIRONMENT=production \
  BTCOGNITIVE_ADMIN_KEY="<32-byte-hex-key>" \
  BTCOGNITIVE_ALLOWED_ORIGINS="https://btcognitive-engine.fly.dev" \
  BTCOGNITIVE_ALLOWED_HOSTS="btcognitive-engine.fly.dev"

# 4. Deploy using the multi-stage Dockerfile
flyctl deploy
```

- **Health probe:** Configured at `GET /health` on port 8000 (grace period 15s, interval 30s).
- **Resource sizing:** 512MB RAM (`shared-cpu-1x`), 1 machine minimum (`min_machines_running = 1` prevents cold starts).

### 9.2 Render.com (`render.yaml` — Free Tier Web Service)

Connect your GitHub repo to Render. The `render.yaml` infrastructure-as-code file specifies:
- Python 3.11 runtime (`PYTHON_VERSION: 3.11.9`)
- Build command: `pip install --no-cache-dir -r requirements.txt`
- Start command: `uvicorn api.server:app --host 0.0.0.0 --port $PORT --workers 1`
- Health check path: `/ping` (configured in `render.yaml`, returns `{"pong": true, "timestamp": ...}`)

Set in Render Dashboard:
```
BTC_ENVIRONMENT=production
BTCOGNITIVE_ADMIN_KEY=<generated>
BTCOGNITIVE_ALLOWED_ORIGINS=https://your-app.onrender.com
BTCOGNITIVE_ALLOWED_HOSTS=your-app.onrender.com
```

> **NOTE:** Render free tier spins down after 15 minutes of inactivity. For continuous market monitoring and persistent SQLite audit ledgers, Fly.io or a dedicated VPS is strongly recommended.

### 9.3 Railway.app

```bash
npm install -g @railway/cli
railway login
railway up
```

Uses `Dockerfile` automatically.

### 9.4 Netlify (frontend only)

```bash
netlify deploy --dir=web --prod
```

The `netlify.toml` proxies `/api/*` to your backend. Set the backend URL in the redirect rule.

**IMPORTANT:** WebSocket connections must use `wss://` in production.

### 9.5 Ubuntu/Debian VPS (systemd)

```bash
rsync -av --exclude='.venv_win' --exclude='*.pyc' . ubuntu@server:/home/ubuntu/btcognitive/
cd /home/ubuntu/btcognitive
python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env && nano .env
```

Create `/etc/systemd/system/btcognitive.service`:
```ini
[Unit]
Description=BTCognitive Research Terminal
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/btcognitive
EnvironmentFile=/home/ubuntu/btcognitive/.env
ExecStart=/home/ubuntu/btcognitive/.venv/bin/uvicorn api.server:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable btcognitive
sudo systemctl start btcognitive
```

Nginx reverse proxy with WebSocket support:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable HTTPS: `sudo certbot --nginx -d your-domain.com`

---

## 10. Security Hardening

Built-in OWASP ASVS 5.0 middleware (`api/security_middleware.py`):

| Protection | Implementation |
|------------|----------------|
| CORS | Explicit allowlist — no wildcards |
| Rate Limiting | 60 req/min public, 300/min admin |
| Security Headers | CSP, HSTS, X-Frame-Options, X-XSS-Protection |
| Trusted Hosts | Host-header poisoning prevention |
| Exception Sanitisation | Zero stack-trace leakage |
| WebSocket Limits | Per-IP connection caps + message size caps |

Before going public:
1. Set `BTCOGNITIVE_ADMIN_KEY` (32+ byte hex)
2. Set exact `BTCOGNITIVE_ALLOWED_ORIGINS` (no trailing slash, no wildcards)
3. Set exact `BTCOGNITIVE_ALLOWED_HOSTS`
4. Enable TLS (nginx/cloud LB)
5. Review `docs/security_architecture.md` and `docs/security_deployment_checklist.md`

---

## 11. Troubleshooting

### Chart shows no forecast overlay

1. Verify server is running: `Invoke-RestMethod http://127.0.0.1:8000/health`
2. Check forecast API: `Invoke-RestMethod "http://127.0.0.1:8000/api/forecast/latest?horizon=15m"` — expect `status: FORECAST_AVAILABLE_RESEARCH_ONLY` with 5 points
3. Open browser devtools console — look for JavaScript errors

**V29 fix (applied):** `ChartTopBar` crashed with `TypeError: Cannot read properties of null (reading 'rsi')` because `useState(null)` bypasses ES6 default parameters. Fixed by `const indicators = latestIndicators ?? {};` inside the function body. Verified browser: forecast dashed cyan line + upper/lower bands render correctly.

### Coinbase data unavailable

If the Coinbase REST API is unreachable:
- Forecast endpoint returns `status: DATA_UNAVAILABLE` (correct fail-closed behaviour)
- Test connectivity: `Invoke-RestMethod "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=900&limit=3"`

### SQLite locked error (multi-worker)

Use `--workers 1` with uvicorn for local SQLite, or provision Turso and set `TURSO_DATABASE_URL` + `TURSO_AUTH_TOKEN`.

### Port 8000 in use

```powershell
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess | ForEach-Object { Get-Process -Id $_.OwningProcess }
Stop-Process -Id <PID> -Force
```

---

## Appendix: API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health probe |
| `/api/dashboard` | GET | Full market dashboard |
| `/api/forecast/latest` | GET | Forecast contract (`?horizon=15m\|1h\|4h\|24h`) |
| `/api/market/candles` | GET | OHLCV history (`?symbol=BTC/USD&interval=15m\|1h&limit=N`) |
| `/api/research/entry-quality` | GET | V28 probabilistic entry quality |
| `/api/arena/active-paper-position` | GET | Active paper position |
| `/ws/market-stream` | WS | Live price + alert stream |

Full Swagger UI: `http://127.0.0.1:8000/docs`

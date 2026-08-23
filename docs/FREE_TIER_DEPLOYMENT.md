# 🌐 BTCognitive: $0/Month Production Deployment Guide

This guide details how to deploy BTCognitive entirely on **$0/month free-tier infrastructure** with 99.9% uptime, zero cold-start latency, multi-exchange failover, and persistent cloud storage.

---

## 🏗️ Free-Tier Architecture Overview

```mermaid
graph TD
    User([User Browser]) -->|Global CDN (Free)| Netlify[Netlify / Cloudflare Pages<br>Static Frontend UI (web/)]
    User -->|REST / WebSockets| Backend[Koyeb or Render Free Tier<br>FastAPI Backend + ML Inference]
    
    UptimeRobot[UptimeRobot / Cron-Job.org<br>Free 5m HTTP Ping] -->|GET /ping| Backend
    
    Backend -->|LibSQL / HTTPS| Turso[(Turso Cloud SQLite<br>9 GB Free, 1B reads/mo)]
    Backend -->|Multi-Exchange Failover| Feeds[Exchange Feeds<br>Binance -> Coinbase -> Kraken -> Bybit]
```

---

## 1. 🚀 Frontend Deployment (Netlify) — $0/Month

Netlify provides 100 GB/month bandwidth, instant automated HTTPS, and continuous Git deployment.

### Steps:
1. Push your repository to GitHub.
2. Log into [Netlify](https://app.netlify.com) and click **"Add new site"** $\to$ **"Import an existing project"**.
3. Select your GitHub repository (`bitcoin-prediction-lab`).
4. Netlify will automatically detect [netlify.toml](file:///c:/Projects/BTCognitive/bitcoin-prediction-lab/netlify.toml) with:
   - **Publish directory**: `web`
   - **Build command**: *(leave blank)*
5. Click **"Deploy site"**. Your terminal will be live at `https://your-site-name.netlify.app`.

---

## 2. ⚡ Backend Engine Deployment (Koyeb or Render) — $0/Month

### Option A: Koyeb (Recommended — Always-On, No Sleep)
Koyeb provides 1 free micro instance with 512 MB RAM that **never spins down**.

1. Create a free account at [Koyeb.com](https://www.koyeb.com).
2. Click **"Create App"** $\to$ **"GitHub"**.
3. Select your repository.
4. Set Build Type to **Dockerfile** (or Python with build command `pip install -r requirements.txt` and start command `uvicorn api.server:app --host 0.0.0.0 --port 8000 --workers 1`).
5. Add Environment Variables:
   - `BTC_ENVIRONMENT`: `production`
   - `PORT`: `8000`
   - `ALLOWED_ORIGINS`: `https://your-site-name.netlify.app`
6. Click **"Deploy"**.

---

### Option B: Render (Automated via `render.yaml`)
1. Create a free account at [Render.com](https://render.com).
2. Click **"New"** $\to$ **"Blueprint"** and connect your repository.
3. Render will automatically parse [render.yaml](file:///c:/Projects/BTCognitive/bitcoin-prediction-lab/render.yaml).
4. Deploy the free web service.

---

## 3. 💾 Persistent Database (Turso Cloud SQLite) — $0/Month (Optional)

By default, the backend stores predictions in local SQLite (`experiments/results/market_memory.db`). To persist records across container rebuilds for $0:

1. Create a free account at [Turso.tech](https://turso.tech).
2. Create a new database:
   ```bash
   turso db create btcognitive-memory
   turso db show btcognitive-memory --url
   turso db tokens create btcognitive-memory
   ```
3. Set environment variables on your backend (Koyeb/Render):
   - `TURSO_DATABASE_URL`: `libsql://btcognitive-memory-[username].turso.io`
   - `TURSO_AUTH_TOKEN`: `your-turso-jwt-token`

---

## 4. ⏱️ Keep-Alive Monitor (Preventing Container Sleep) — $0/Month

If deploying on Render (which spins down after 15 minutes of inactivity):

1. Create a free account at [UptimeRobot.com](https://uptimerobot.com) or [Cron-job.org](https://cron-job.org).
2. Add a new **HTTP(s) Monitor**:
   - **URL**: `https://<your-backend-domain>/ping`
   - **Monitoring Interval**: Every 5 or 10 minutes
   - **Alert Type**: HTTP 200 OK
3. **Result**: The lightweight `/ping` endpoint responds in `<2ms` with zero CPU overhead, keeping your free backend container active 24/7.

---

## 5. 🛡️ Multi-Exchange Geo-Failover Verification

When running on US or EU cloud servers where Binance endpoints might be geo-restricted or rate-limited, BTCognitive automatically cascades through:
1. **Binance REST / Coin-M** (`dapi.binance.com`)
2. **Coinbase Spot API** (`api.coinbase.com`)
3. **Kraken Public REST** (`api.kraken.com`)
4. **Bybit Spot / Linear** (`api.bybit.com`)

No API keys or manual failover configuration required.

# Production Deployment Guide

Instructions for deploying the **BTCognitive** AI Inference Engine across cloud providers.

---

## 1. Netlify Static UI Hosting

1. Deploy the `web/` folder to Netlify:
   ```bash
   netlify deploy --dir=web --prod
   ```
2. Configure custom domain and HTTPS.

---

## 2. Docker Cloud Deployment (Render / Railway / Fly.io)

1. Build container image:
   ```bash
   docker build -t btcognitive-engine .
   ```
2. Run container:
   ```bash
   docker run -d -p 8000:8000 --name btcognitive btcognitive-engine
   ```

---

## 3. Systemd Service (Ubuntu / Debian VPS)

Create `/etc/systemd/system/btcognitive.service`:
```ini
[Unit]
Description=BTCognitive AI Inference Service
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/bitcoin-prediction-lab
ExecStart=/home/ubuntu/bitcoin-prediction-lab/venv/bin/uvicorn api.server:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

# BTCognitive — AI-Powered Bitcoin Market Intelligence & Inference Lab

[![Live Netlify Demo](https://img.shields.io/badge/Netlify-Live%20App-00C7B7?style=for-the-badge&logo=netlify&logoColor=white)](https://btcognitive-prediction-lab.netlify.app)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-2.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-Native%20Quantile-EB5424?style=for-the-badge)](https://xgboost.readthedocs.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**BTCognitive** is an institutional-grade quantitative machine learning research platform and live trading terminal for Bitcoin (`BTC/USD`). It combines purged walk-forward cross-validation, regime-aware ensemble models (Random Forest + XGBoost Quantile), SHAP explainability, atomic market memory, and multi-channel high-profit conviction alerts.

---

## 🌟 Key Features

* **🔬 Institutional Quantitative Core:**
  * **Adaptive Regime Ensemble:** Gated model switching across Trending Bull, Trending Bear, Mean Reverting, and High-Volatility regimes.
  * **Purged & Embargoed Cross-Validation:** Eliminates serial correlation and informational leakage across overlapping prediction horizons.
  * **Deflated Sharpe Ratio (DSR) & PBO:** Deflates performance metrics against multi-testing trial inflation.
  * **Dynamic ATR Risk Buffers:** Calculates volatility-adapted Take-Profit (TP) and Stop-Loss (SL) targets.

* **⚡ Real-Time Trading Terminal:**
  * **Lightweight TradingView Charts:** Real-time 20 & 50 EMAs with dynamic AI forecast ribbons.
  * **4-Factor Uncertainty Decomposition:** Quantifies Data Reliability, Regime Certainty, Model Agreement, and Volatility Stress.
  * **What-If Scenario Simulator:** Interactive slider sandbox to simulate price shocks and macro events.
  * **Acoustic Radar & Multi-Channel Alerts:** Synthesized audio fanfares, OS desktop push notifications, Discord & Telegram webhooks.

---

## 🏗️ Architecture Topology

```
                      ┌───────────────────────────────────────────────┐
                      │          Live Market Feeds (Binance / CB)     │
                      └──────────────────────┬────────────────────────┘
                                             │ (WebSocket / REST)
                                             ▼
                      ┌───────────────────────────────────────────────┐
                      │    CandleStateManager & Feature Pipeline      │
                      │    - Microstructure Ingestion                 │
                      │    - Volatility & Momentum Oscillators        │
                      └──────────────────────┬────────────────────────┘
                                             │
                                             ▼
                      ┌───────────────────────────────────────────────┐
                      │       Adaptive Regime Inference Ensemble      │
                      │       - Random Forest Classifier              │
                      │       - XGBoost Quantile Regressors           │
                      │       - SHAP Explainer & Uncertainty Decomp   │
                      └──────────────┬─────────────────┬──────────────┘
                                     │                 │
            ┌────────────────────────▼───┐         ┌───▼──────────────────────────┐
            │   FastAPI REST & WS Engine │         │  Multi-Channel Dispatcher    │
            │   http://localhost:8000    │         │  Discord / Telegram / Email  │
            └────────────────┬───────────┘         └──────────────────────────────┘
                             │
                             ▼
            ┌────────────────────────────────────┐
            │   Web Terminal UI (Three.js/React) │
            │   https://btcognitive-prediction-  │
            │   lab.netlify.app                  │
            └────────────────────────────────────┘
```

---

## 🚀 Quickstart Guide

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/ashishlabs-23/bitcoin-prediction-lab.git
cd bitcoin-prediction-lab

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Launch Local FastAPI Engine & UI
```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser to access the live terminal.

### 3. Run with Docker Compose
```bash
docker-compose up --build
```

### 4. Interactive CLI Tool
```bash
# Get engine health & latency
python cli.py health

# Get real-time AI prediction & uncertainty narrative
python cli.py predict

# Get current market regime state
python cli.py regime
```

---

## 🧪 Running Automated Tests
```bash
pytest -v
```

---

## 📄 License
Distributed under the **MIT License**. See `LICENSE` for details.

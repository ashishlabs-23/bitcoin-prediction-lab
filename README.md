# BTCognitive — AI-Powered Bitcoin Market Intelligence & Inference Lab

[![Live Netlify Demo](https://img.shields.io/badge/Netlify-Live%20App-00C7B7?style=for-the-badge&logo=netlify&logoColor=white)](https://btcognitive-prediction-lab.netlify.app)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![FastAPI 2.0](https://img.shields.io/badge/FastAPI-2.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![XGBoost Native Quantile](https://img.shields.io/badge/XGBoost-Native%20Quantile-EB5424?style=for-the-badge&logo=xgboost&logoColor=white)](https://xgboost.readthedocs.io)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com)
[![Fly.io Ready](https://img.shields.io/badge/Fly.io-Cloud%20Backend-24185B?style=for-the-badge&logo=fly.io&logoColor=white)](https://fly.io)
[![Tests Passing](https://img.shields.io/badge/Pytest-Passing-46A2F1?style=for-the-badge&logo=pytest&logoColor=white)](#-running-automated-tests)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**BTCognitive** is an institutional-grade quantitative machine learning research platform and real-time trading terminal for Bitcoin (`BTC/USD`). It combines purged walk-forward cross-validation, an adaptive regime-switching ensemble (Random Forest + XGBoost Quantile), SHAP feature explainability, atomic market memory, Kelly Criterion position sizing, Deflated Sharpe Ratio (DSR) overfitting controls, and a multi-channel high-profit conviction notification dispatcher.

---

## 🌟 Key Features

### 🔬 Institutional Quantitative Core
* **Adaptive Regime Ensemble:** Gated model switching across 4 market states: **Trending Bull**, **Trending Bear**, **Mean Reverting (Ranging)**, and **High-Volatility**.
* **Purged & Embargoed Cross-Validation:** Eliminates serial correlation and informational lookahead leakage across overlapping time-series prediction horizons.
* **Deflated Sharpe Ratio (DSR) & PBO:** Deflates performance metrics against multi-testing trial inflation using the Bailey & López de Prado methodology.
* **Kelly Criterion Position Manager:** Fractional Kelly position sizing engine with regime-aware allocation caps (RANGING: max 8%, HIGH_VOL: max 5%) and RiskOverlay drawdown guardrails.
* **4-Factor Uncertainty Decomposition:** Quantifies real-time signal confidence by dissecting **Data Reliability**, **Regime Certainty**, **Model Agreement**, and **Volatility Stress**.
* **SHAP Explainer:** Real-time feature attribution identifying exact indicator drivers behind every directional bias.

### ⚡ Real-Time Trading Terminal & UX
* **Lightweight TradingView Charts:** Real-time OHLCV visualization with 20/50 EMAs, Bollinger Bands, and dynamic AI forecast ribbons.
* **What-If Scenario Sandbox:** Interactive shock simulator allowing traders to stress-test model predictions under simulated price volatility and macro events.
* **Counterfactual Engine & Reference TP/SL:** Computes volatility-adapted Take-Profit (TP) and Stop-Loss (SL) targets, displaying reference bounds even during `SKIP` regime decisions.
* **Multi-Channel Notification Dispatcher:** Real-time event notifications via Email (SMTP), WebSockets, OS WebPush, Discord, and Telegram webhooks with 15-minute anti-spam deduplication.

---

## 🧠 5-Stage Decision Pipeline Architecture

Every trading decision processed by BTCognitive undergoes a strict 5-stage hierarchical filtering pipeline to prevent false breakouts and control downside risk:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. Primary Signal (EMA Crossover / Trend Score)                                 │
│    "Does a candidate directional trade setup exist?"                           │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 2. Meta-Label Classifier (AdaptiveRegimeEnsemble)                               │
│    "Should this specific primary signal be trusted under current conditions?"   │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 3. Regime Gate (Regime Detector)                                                │
│    "Is the current market state suitable? (RANGING state forces a SKIP decision)"│
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 4. Macro Event Gate (Event Engine)                                              │
│    "Is there an active LIQUIDATION_CASCADE or MACRO_VOLATILITY_SPIKE hazard?"  │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 5. Genome Layer & Kelly Manager (SQLite Registry)                               │
│    "Calculate exact position size, leverage, TP/SL targets, and max hold time"  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Architecture Topology

```
                       ┌───────────────────────────────────────────────┐
                       │       Live Market Feeds (Binance / Coinbase)  │
                       └──────────────────────┬────────────────────────┘
                                              │ (WebSocket / REST)
                                              ▼
                       ┌───────────────────────────────────────────────┐
                       │    CandleStateManager & Feature Pipeline      │
                       │    - Microstructure & Volatility Features      │
                       │    - Technical Oscillators (RSI, MACD, ATR)    │
                       └──────────────────────┬────────────────────────┘
                                              │
                                              ▼
                       ┌───────────────────────────────────────────────┐
                       │      Adaptive Regime Inference Engine         │
                       │      - Random Forest Classifier               │
                       │      - XGBoost Quantile Regressors            │
                       │      - Kelly Sizer & SHAP Explainer           │
                       └──────────────┬─────────────────┬──────────────┘
                                      │                 │
             ┌────────────────────────▼───┐         ┌───▼──────────────────────────┐
             │   FastAPI REST & WS Engine │         │  Multi-Channel Dispatcher    │
             │   http://localhost:8000    │         │  Email / WebPush / Webhooks  │
             └────────────────┬───────────┘         └──────────────────────────────┘
                              │
                              ▼
             ┌────────────────────────────────────┐
             │   Web Terminal UI (React / Netlify)│
             │   https://btcognitive-prediction-  │
             │   lab.netlify.app                  │
             └────────────────────────────────────┘
```

---

## 📂 Repository Directory Structure

```
bitcoin-prediction-lab/
├── api/                        # FastAPI REST & WebSocket Backend
│   ├── server.py               # Central FastAPI application server & route handlers
│   ├── notifications.py        # Multi-channel notification dispatcher (Email, WebSockets, Webhooks)
│   └── genome_routes.py        # Genome registry, DSR, and PBO endpoints
├── models/                     # Machine Learning & Quantitative Core
│   ├── market_intelligence.py  # Model orchestrator, feature engine & regime classifier
│   ├── opportunity_detector.py # High-profit conviction opportunity scoring engine
│   ├── position_manager.py     # Kelly Criterion position sizer & drawdown guardrails
│   ├── risk_metrics.py         # Comprehensive risk performance library (Sharpe, Sortino, DSR, VaR)
│   ├── counterfactual.py       # Genome counterfactual table & reference TP/SL generator
│   ├── train_baselines.py      # Purged walk-forward baseline trainers (RF, LogReg, XGBoost)
│   ├── governance.py           # Model health monitoring & performance governance
│   ├── export_onnx.py          # ONNX model export & runtime converter
│   └── generate_ensemble_probs.py # Ensemble probability prediction pipeline
├── backtest/                   # Realistic Execution & Cost Simulator
│   └── execution_simulator.py  # Discrete hold backtest engine with fee & slippage modeling
├── genome/                     # Strategy Overfitting & Evolution Registry
│   ├── registry.py             # SQLite WAL-backed strategy genome database
│   └── overfitting.py          # PBO & Deflated Sharpe Ratio computation
├── scripts/                    # Research & Diagnostic Tools
│   ├── regime_heatmap.py       # Regime transition probability matrix generator
│   └── signal_quality_report.py# Signal quality & TP/SL coverage diagnostic auditor
├── tests/                      # Automated Pytest Suite
│   ├── test_features.py        # Feature engineering unit tests
│   ├── test_position_manager.py# Kelly Criterion position manager unit tests
│   ├── test_risk_metrics.py    # Risk metric library unit tests
│   ├── test_execution_simulator.py # Execution simulator unit tests
│   └── test_market_memory_atomic.py # Market memory logging unit tests
├── cli.py                      # Interactive Terminal CLI Application
├── Dockerfile                  # Production Container Image Spec
├── docker-compose.yml          # Multi-container Compose Orchestration
├── fly.toml                    # Fly.io Cloud Backend Deployment Config
├── requirements.txt            # Python Dependencies Specification
├── pytest.ini                  # Pytest Runner Configuration
└── WORKING_CONTEXT.md          # Persistent Empirical Ground-Truth Memory
```

---

## 🔌 REST & WebSocket API Reference

| Endpoint | Method | Description |
|---|:---:|---|
| `/health` | `GET` | System health check, model load status, and inference latency |
| `/prediction/latest` | `GET` | Live AI directional prediction, regime state, and confidence narrative |
| `/prediction/counterfactual` | `GET` | Multi-genome counterfactual performance table with reference TP/SL |
| `/regime` | `GET` | Current market regime classification and volatility metrics |
| `/features` | `GET` | Real-time computed feature matrix and indicator values |
| `/market-memory` | `GET` | Historical atomic market memory log of executed forecasts |
| `/notifications/test` | `POST` | Trigger test notification across Email, WebSockets, and Webhooks |
| `/ws/feed` | `WS` | Real-time WebSocket stream for candle updates and live predictions |

---

## 📊 Confirmed Quantitative Audit & Cost Sensitivity Matrix

Evaluated on **10 Purged Walk-Forward Cross-Validation Folds** (640 total test bars, 387 out-of-fold samples):

| Sizing Strategy | Fee (bps) | Slippage (bps) | Total Return | Sharpe Ratio | Max Drawdown | Total Trades |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Unfiltered Continuous (`prob_scaled`)** | 0.0 | 0.0 | **+7.81%** | **+5.46** | -3.18% | 553 |
| **Unfiltered Continuous (`prob_scaled`)** | 5.0 | 5.0 | **-8.13%** | **-6.10** | -11.09% | 553 |
| **Discrete Hold (`max_hold=24`)** | 0.0 | 0.0 | **+10.58%** | **+5.89** | -3.86% | **81** |
| **Discrete Hold (`max_hold=24`)** | 5.0 | 5.0 | **-4.71%** | **-2.72** | -9.24% | **81** |
| **Meta-Labeled Ensemble (`p >= 0.54`)** | 5.0 | 5.0 | **-4.53%** | **-3.68** | **-2.43%** | **31** |

> ⚠️ **Audit Takeaway**: Naive continuous per-bar rebalancing suffers severe friction decay under realistic fees (5 bps fee + 5 bps slip). Discrete hold period execution (`max_hold_bars=24`) reduces trade turnover by **85%** and serves as the production baseline.

---

## 🚀 Quickstart Guide

### 1. Clone Repository & Install Dependencies
```bash
git clone https://github.com/ashishlabs-23/bitcoin-prediction-lab.git
cd bitcoin-prediction-lab

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Launch Local FastAPI Backend
```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser or view Swagger documentation at **[http://localhost:8000/docs](http://localhost:8000/docs)**.

---

### 3. Interactive Terminal CLI
```bash
# Check engine health and latency
python cli.py health

# Get live AI prediction and risk narrative
python cli.py predict

# Check current market regime
python cli.py regime

# Inspect latest feature values
python cli.py features
```

---

### 4. Run with Docker & Docker Compose
```bash
# Build and run container stack
docker-compose up --build -d

# View container logs
docker-compose logs -f
```

---

### 5. Production Cloud Deployment

* **Frontend (Netlify):** Live at **[https://btcognitive-prediction-lab.netlify.app](https://btcognitive-prediction-lab.netlify.app)**. Automatically deploys on pushes to `main`.
* **Backend (Fly.io):** Pre-configured via `fly.toml`. To deploy the production backend:
  ```bash
  flyctl auth login
  flyctl apps create btcognitive-engine --org personal
  flyctl deploy
  ```

---

## 🧪 Running Automated Tests

Run the full pytest suite to verify feature generation, position sizers, risk metric calculations, and market memory logging:

```bash
# Run pytest suite
python -m pytest -v
```

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for full details.

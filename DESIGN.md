# BTCognitive — Technical & Visual System Design Document
## Institutional Terminal Architecture, Visual Hierarchy, WebGL Topology & Frontend Engineering

**Document Status:** Production / Canonical  
**Version:** 2.0.0  
**Design Reference:** Institutional Dark Glass / Bloomberg Terminal Meets Linear & TradingView  
**Repository:** `https://github.com/ashishlabs-23/bitcoin-prediction-lab`  

---

## 1. Architectural Topology & Data Flow

BTCognitive is designed around strict separation of concerns between real-time market data ingestion, causal feature engineering, econometric inference, and client-side visualization.

```mermaid
graph TD
    subgraph Market Data Layer
        EX[Bitstamp WebSocket Spot BTC/USD] -->|Raw Ticks| INGEST[engine/market_data_feed.py]
        INGEST -->|1m Aggregation| CACHE[engine/market_data_feed.py Candle Ring Buffer]
    end

    subgraph Research & Model Serving
        CACHE -->|Causal 720h History| FEAT[engine/l2_microstructure_features.py]
        FEAT -->|10-Feature Vector| HAR[models/authoritative_model_registry.py Standard-HAR]
        HAR -->|Forward Variance| CONF[models/conformal_risk_envelope.py C2]
    end

    subgraph API Gateway / FastAPI
        CACHE --> BUNDLE[GET /api/terminal/bundle]
        HAR --> BUNDLE
        CONF --> BUNDLE
        INGEST --> WS[/ws WebSocket Telemetry Hub]
    end

    subgraph Presentation / Browser
        BUNDLE -->|Atomic Snapshot 15s| CLIENT[web/app.js React 18 Engine]
        WS -->|Tick Pulse & Latency| CLIENT
        CLIENT --> CHART[TradingView Lightweight-Charts Canvas]
        CLIENT --> WEBGL[Three.js GPU Particle Field]
        CLIENT --> DRAWER[Decision Anatomy & Risk Radar]
    end
```

---

## 2. Visual Identity & Design System

### 2.1 Color Palette
The interface adopts a high-contrast dark palette tailored for continuous multi-hour analytical sessions without visual fatigue:

| Token | Hex Value | Semantic Purpose |
| :--- | :--- | :--- |
| `--bg-void` | `#020617` | Deepest root canvas; viewport background behind WebGL |
| `--bg-surface` | `#070b14` | Primary card and workspace background with 85% alpha glassmorphism |
| `--bg-elevated` | `#0f172a` | Dropdown menus, modals, active tabs, and table headers |
| `--border-subtle`| `rgba(255, 255, 255, 0.08)` | Card borders and structural grid dividers |
| `--border-focus` | `rgba(56, 189, 248, 0.3)` | Active input borders, highlighted telemetry cards |
| `--brand-cyan` | `#38bdf8` | Primary active accent, telemetry readings, forecast mean lines |
| `--bull-green` | `#10b981` | Up candles, positive MFE excursion, verified research passes |
| `--bear-red` | `#ef4444` | Down candles, MAE drawdown risk, fail-closed alert disclosures |
| `--warn-amber` | `#f59e0b` | High volatility warnings, degraded data indicators, research lock |
| `--text-primary`| `#f8fafc` | Primary metrics, headers, candle values |
| `--text-muted` | `#94a3b8` | Provenance labels, timestamps, parameter keys |

### 2.2 Typography
- **Headings & Brand:** `Outfit`, sans-serif (weights: 400, 600, 700). Geometric, modern, highly legible at institutional scale.
- **Data & Financial Figures:** `JetBrains Mono`, monospace (weights: 400, 500, 700). Fixed-width numbers prevent tabular jitter during live market updates.

---

## 3. Core Workspace Components

```
+-----------------------------------------------------------------------------------------+
| [LOGO] BTCognitive  |  Terminal  Research  Journal  [More v]  |  $88,420.50  0.42ms [LIVE] |
+-----------------------------------------------------------------------------------------+
| [TICKER RIBBON] Spot: $88,420 | 24h Vol: 48.2% | Regime: Trending Bull | Gate: RESEARCH |
+-------------------------------------------------------------+---------------------------+
|                                                             | [DECISION SIDEBAR]        |
|  [TRADINGVIEW LIGHTWEIGHT-CHARTS CANVAS]                   |                           |
|  - Candlestick Series (1m, 5m, 15m, 1h, 4h, 1d)             | Active Vol Model:         |
|  - EMA-20 (Gold), EMA-50 (Blue), EMA-200 (Purple)           | Standard-HAR-v1.0         |
|  - 24h / 168h Conformal Prediction Bands (Cyan Cones)       |                           |
|  - Volatility Excursion Range Overlays                      | Forward 24h Variance:     |
|                                                             | 0.001824 (Ann: 44.8%)     |
|                                                             |                           |
|                                                             | Conformal Coverage:       |
|                                                             | 90.0% Nominal (C2 Causal) |
+-------------------------------------------------------------+---------------------------+
| [BOTTOM DECK]                                                                           |
| [Tab: Strategy Tournament] [Tab: What-If Simulator] [Tab: Order Book Imbalance]         |
+-----------------------------------------------------------------------------------------+
```

### 3.1 TradingView Canvas (`LightweightCandleChart`)
- Renders GPU-accelerated candlestick series supporting 1m, 5m, 15m, 1h, 4h, and 1d intervals.
- Overlay layers:
  - Exponential Moving Averages: EMA-20, EMA-50, EMA-200.
  - Volatility Conformal Bands: Shaded confidence envelopes projected forward 24 hours.
  - Timeframe bucket aggregation engine enforcing UTC boundary alignment (`timestamp % 3600000 === 0`).

### 3.2 3D Particle Topology (`ThreeBackground`)
- WebGL particle field (400 points, dual rotating toruses) providing visual depth behind the glassmorphism workstation.
- **Performance Optimizations:**
  - Evaluates distance via squared Euclidean comparisons ($dx^2 + dy^2 + dz^2 < R^2$), eliminating 80,000 square root calls per frame.
  - Automatically suspends `requestAnimationFrame` execution when `document.hidden === true`.

### 3.3 Root Error Boundary (`AppErrorBoundary`)
- Wraps root application render: `window._btcognitiveRoot.render(h(AppErrorBoundary, null, h(App)))`.
- Catches unhandled runtime presentation errors, displays an institutional error banner with full stack traces, and provides a clean "Reload Terminal" recovery button without blank-screen unmounts.

---

## 4. Frontend State Machine & Networking Strategy

### 4.1 Rate-Limiting & Polling Budget
The FastAPI backend enforces a strict **60 requests per minute** bucket per IP on non-loopback clients. To guarantee zero rate-limit collisions, the client implements:
- **Consolidated Polling:** Subscribes to `GET /api/terminal/bundle` every 15s instead of dispatching 13 independent queries.
- **Client Polling Budget:** Steady-state consumption is **29.5 req/min**, well below the 60 req/min server ceiling.
- **In-Flight Deduplication (`_inflightRequests`):** Redundant concurrent requests for identical endpoints reuse the existing active `Promise`.
- **TTL Response Cache (`_responseCache`):** Identical reads within a 2-second window return cached payloads without dispatching network calls.
- **Exponential Backoff:** If HTTP 429 is encountered, client requests back off exponentially ($2^n \times 1000\text{ ms}$).

### 4.2 WebSocket Heartbeat Protocol
- Endpoint: `ws://{host}/ws`
- Message Types:
  - `TICK`: Lightweight price and volume pulses (`{"type": "TICK", "symbol": "BTC-USD", "price": 88420.5}`).
  - `HEARTBEAT`: 15-second bidirectional ping/pong maintaining connection liveness.
  - Automatic reconnection with jittered exponential backoff upon network interruption.

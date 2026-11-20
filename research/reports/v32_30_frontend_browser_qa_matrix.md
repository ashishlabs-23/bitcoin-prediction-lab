# BTCognitive — Frontend Browser Feature QA & Visual Evidence Matrix (V32.30)

**Date:** 2026-10-25  
**Version:** V32.30  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Live Execution Authorization:** `DISABLED` (Permanently fail-closed)  
**Lead Browser QA Agent:** Agent 6 (Independent Browser Subagent)  
**Test URL:** `http://127.0.0.1:8000/#/terminal`  
**Browser Engine:** Chromium (Playwright / Browser Subagent)  
**Recording Session Artifact:** [browser_qa_v3230_1792911689894.webp](file:///C:/Users/Ashish/.gemini/antigravity-ide/brain/a3386aa4-012c-48fd-9ccc-c71233b8aeaf/browser_qa_v3230_1792911689894.webp)  

---

## 1. Feature-by-Feature Browser Verification Matrix

| # | UI Feature / Panel | Route / View | Verification Steps | Visual & State Evidence | QA Result |
| :-: | :--- | :--- | :--- | :--- | :---: |
| **1** | **Application Load & Title** | `/#/terminal` | Navigated to `http://127.0.0.1:8000/#/terminal`. Checked DOM and `<title>`. | Title rendered: *BTCognitive — Probabilistic Risk Intelligence*. Three.js canvas initialized. | **PASS** |
| **2** | **Header & Governance Indicators** | Top Header Bar | Inspected connection state, live status, and mode badges. | Badges: `LIVE`, `ANALYSIS ONLY`, `OFFLINE_RESEARCH_ONLY`. Live trading explicitly displayed as `DISABLED`. | **PASS** |
| **3** | **Interactive Candlestick Chart** | Forecast View | Inspected TradingView Lightweight Charts canvas and timeframe controls. | Candlesticks render smoothly without jitter; timeframe buttons switch intervals causally. Zero misleading profit overlays. | **PASS** |
| **4** | **Multi-Horizon Forecast Panel** | Forecast View | Toggled between **1H**, **4H**, and **24H Horizon** views. | Point estimates (Persistence baseline, Ridge L2), forecast delta, and empirical price quantiles ($P_{10}, P_{50}, P_{90}$) displayed with proper uncertainty bands. | **PASS** |
| **5** | **Tournament Leaderboard (Track A/C)** | Forecast View | Inspected tournament leaderboards and offline strategy hypothesis cards. | Track A Tournament Leaderboard and Track C Offline Strategy Hypothesis Tournament metrics rendered accurately. | **PASS** |
| **6** | **Market Tab & Evidence Router (AEER)** | Market View | Clicked **Market** tab. Tested presets (`SCALP`, `INTRADAY`, `SWING`, `CYCLE`) and horizon switches (`15m`, `1h`, `4h`, `1d`, `7d`, `CYCLE`). | Dynamic evidence toggles (OFI, Hawkes, VPIN, Liquidations, RV, MVRV, Mayer Multiple) displayed without layout overflow. | **PASS** |
| **7** | **Strategies Tab (MEIE Archetypes)** | Strategies View | Clicked **Strategies** tab. Inspected strategy cards and registry status. | All 5 canonical MEIE strategy archetypes (*MEIE-IGNITION*, *MEIE-COMBINED*, *MEIE-ABSORPTION*, *MEIE-VACUUM*, *MEIE-TOXICITY*) displayed with target R:R, win rates, and scores. | **PASS** |
| **8** | **Trades Tab & Paper Execution Ledger** | Trades View | Clicked **Trades** tab. Inspected live paper execution ledger. | Rendered active paper trade contracts (#1, #2), direction (`LONG`), entry prices, TP/SL levels, exit prices, net P&L, and `TP_HIT` execution status. | **PASS** |
| **9** | **Research Tab & What-If Scenario Lab** | Research View | Clicked **Research** tab. Inspected hypothetical scenario parameters and barrier pairs. | What-If Scenario Lab rendered parameter sliders, barrier pairs, and cost-erased research status. Zero live orders possible. | **PASS** |
| **10** | **Replay Tab & Time Machine** | Replay View | Clicked **Replay** tab. Tested historical decision trace inspector. | Replay Engine Time Machine loaded historical event traces and step navigation controls. | **PASS** |
| **11** | **Arena Tab & Virtual Bankroll** | Arena View | Clicked **Arena** tab. Checked multi-agent experimentation view. | Arena Experimentation view displayed `$10 Virtual Bankroll` with status `ACTIVE`. Multi-agent genetic tournament safely decoupled from Smart Entry. | **PASS** |
| **12** | **Responsive Viewport: 1024x768** | Global | Resized viewport to `1024x768`. Inspected layout wrapping, navigation, and canvas sizing. | Layout adapted cleanly; chart resized without clipping; navigation collapsed gracefully. | **PASS** |
| **13** | **Responsive Viewport: 800x600** | Global | Resized viewport to `800x600`. Inspected narrow viewport layout. | Mobile/compact layout maintained readable typography; zero horizontal body scrollbar overflow. | **PASS** |
| **14** | **Browser Console Health** | Global | Captured full browser console logs during entire interactive session. | **Zero uncaught exceptions. Zero warnings.** Clean console output. | **PASS** |

---

## 2. Screenshot & Visual Artifact Evidence Index

| Screenshot Description | Local File Path | Viewport | Key Visual Feature |
| :--- | :--- | :---: | :--- |
| **Desktop Initial View** | `desktop_terminal_initial_1792911705548.png` | $1536 \times 730$ | Candlestick chart, 1h/4h/24h toggles, governance badges |
| **Market Tab View** | `market_tab_view_1792911719450.png` | $1536 \times 730$ | Evidence router, OFI/VPIN/Hawkes/RV metrics |
| **Strategies Tab View** | `strategies_tab_view_1792911731506.png` | $1536 \times 730$ | 5 Canonical MEIE strategy archetypes |
| **Trades Tab View** | `trades_tab_view_1792911742520.png` | $1536 \times 730$ | Paper execution ledger, trade contracts #1 and #2 |
| **Research Tab View** | `research_tab_view_1792911754134.png` | $1536 \times 730$ | What-If scenario lab, hypothetical research barriers |
| **Replay Tab View** | `replay_tab_view_1792911784505.png` | $1536 \times 730$ | Time machine, historical decision trace inspector |
| **Arena Tab View** | `arena_tab_view_1792911798632.png` | $1536 \times 730$ | Virtual bankroll, experimental tournament status |
| **Responsive 1024x768 View** | `responsive_1024x768_1792911809107.png` | $1024 \times 768$ | Tablet responsive wrapping, chart scaling |
| **Responsive 800x600 View** | `responsive_800x600_1792911823085.png` | $800 \times 600$ | Compact layout, zero horizontal scroll overflow |

---

## 3. Independent Browser QA Verdict

### Browser Subagent Decision: `BROWSER_QA_PASS`
All 14 tested frontend feature areas, tabs, controls, charts, responsive layouts, and console health checks passed 100%. No broken UI states, console errors, or network disconnects were observed. Live trading remained explicitly disabled across all UI views.

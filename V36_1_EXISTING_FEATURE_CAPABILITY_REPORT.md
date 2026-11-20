# BTCognitive V36.1 — Existing Feature Capability Report

## Executive inventory statement

This report is a static, read-only capability inventory. It records 54 grouped registry entries: 10 frontend surface groups, 12 API route groups, and 32 analytical/data/governance capabilities. It is not a claim that every method in the repository has been individually cataloged. The relevant five directories contain 2,226 files / 566 Python files (`engine/` 132, `backtest/` 7, `models/` 47, `config/` 4, `tests/` 376). Each associated test is evidence that a test source exists, not that it passed.

### Registry lifecycle counts

| Classification | Count | Interpretation |
|---|---:|---|
| `ACTIVE_VALIDATED` | 0 | No feature received runtime validation in V36.1. |
| `ACTIVE_UNVALIDATED` | 39 | Source/UI/API capability is present; empirical/runtime validation is not established here. |
| `EXPERIMENTAL` | 8 | Research candidate, model, resolver, or execution simulation; not promoted. |
| `DEPRECATED` | 0 | No new deprecated label inferred from names alone. |
| `DISABLED` | 2 | CoinGecko AI/ML usage gate and C2 calibration outputs. |
| `DATA_UNAVAILABLE` | 4 | L2 microstructure, Bitstamp provider retrieval in this no-network milestone, multimodal streams, and aligned funding/open-interest features. |
| `BROKEN` | 1 | Standard HAR registered artifact is missing or represented by a placeholder identity; its forecast is not reproducible from the registry. |

Counts describe the registry's grouped records, not all source functions or endpoint declarations. A grouped UI/API record may cover multiple controls/routes.

## Frontend capability inventory

`web/index.html` loads `analysis_contract.js` and `app.js`. The static scan found 57 non-App function components plus `App`, and supporting `BackendWSManager`. Components and line anchors:

- **Chart/navigation/alerts:** `LightweightCandleChart` (1379), `LiveBadge` (2699), `ChartTopBar` (2717), `ThreeBackground` (3002), `OpportunityToastContainer` (3210), `NotificationBell` (3321), `NotificationSettingsModal` (3445), `SpotComparatorModal` (3809), `UserAlertsModal` (3888), `Navbar` (4007).
- **Market/decision/prediction:** `InstitutionalTickerBar` (4291), `SystemAtAGlanceCard` (4352), `HeroSection` (4502), `EntryQualityResearchPanel` (4948), `DecisionAnatomyPanel` (5058), `PredictionPanel` (5243), `MarketStateSection` (5580), `ExplainableAIPanel` (5615), `SignalQualityGauge` (5655), `ModelLineageStrip` (5684), `PredictionHistoryTimeline` (5759), `PaperPortfolio` (5938), `FuturePriceForecastingPanel` (8823), `AiForecastRiskOutlookView` (9074), `OrderBookPressureWidget` (9616), `CrossHorizonPatiencePanel` (9983), `AiPredictionEnginePanel` (10184).
- **Workstation/strategy/replay/simulation:** `QuickExecutionTicket` (6105), `CompactWorkstationHeader` (6113), `WorkstationIntentCommandBar` (6188), `AiDualHypothesisPanel` (6323), `ContractInspectionModal` (6777), `AlertDiagnosticsPanel` (6965), `StrategyTournamentDashboard` (7089), `WorkstationDecisionSidebar` (7526), `AiEvidenceInputsBar` (7784), `TradeContractModal` (7965), `ReplayBar` (8019), `HistoricalAnalogsPanel` (8063), `EntryTpSlResearchPanel` (8332), `BottomTabs` (9387), `ReplayCounterfactualLab` (9437), `WhatIfSimulator` (9629), `SideBySideWorkstationContainer` (10710), `TerminalView` (10752), `LiveEquityCurveChart` (11372), `ObservatoryContextPanel` (11493), `ArenaExperimentView` (11675), `SmartEntryPanel` (12546).
- **Research and user workflows:** `L2GatingResearchPanel` (13347), `SmartEntryView` (13474), `ResearchResultsView` (13553), `HowItWorksView` (14512), `PaperTradingDashboardView` (14810), `PositionMonitorView` (15192), `ManualTradeJournalView` (16062), `SmartEntrySimulatorView` (17513).
- **Root:** `App` (19157).

Handler sites: 219 `onClick`, 7 `onSubmit`, 57 `onChange`; these are JSX handler-site counts, not unique user actions. Concrete action families include hash-route navigation, chart interval/overlay controls, dialogs and alert/settings workflows, replay/counterfactual inspection, contract/tournament analysis, simulated smart-entry lifecycle, arena experiments/scenarios/exports, position tracker mutations, smart-entry simulator sync/demo/evaluate, and local focus/3D preferences.

The frontend `createPaperTrade`, `closePaperTrade`, and `executeArenaTrade` helpers return `DISABLED`; this does not establish that every backend paper-trading route is disabled. User-interface names such as "execution" or "live" do not prove external execution.

## API inventory and route reconciliation

Static inspection counted **191 HTTP route decorator operations**, **190 distinct HTTP method + fully prefixed path pairs**, **186 distinct path strings**, and one duplicate method/path declaration: `GET /api/market/comparator` is declared in both `api/market_monitor_routes.py` and `api/routes_market.py`. There is also one WebSocket route (`/ws`) and one static frontend mount; neither is included in the HTTP count. Router registration is in `api/server.py`.

The 12 grouped API sections in [V36_1_FEATURE_REGISTRY.csv](./V36_1_FEATURE_REGISTRY.csv) enumerate the route families. Static path comparison found 93 of the 190 method/path pairs without a direct matching `app.js` URL literal after `/api` and legacy aliases were normalized; this means not directly referenced by this frontend, not necessarily absent from generated OpenAPI or unavailable to other clients. The frontend's statically identified API paths had no unmatched route after alias normalization.

### Frontend API reachability gaps (93 method/path pairs)

- Arena (10): `DELETE /api/arena/paper-trades/reset`; `GET /api/arena/cross-horizon-profile`, `/api/arena/equity`, `/api/arena/meie/state`, `/api/arena/scenario-preview`, `/api/arena/trades`; `POST /api/arena/paper-trades/close`, `/api/arena/scenario-preview`, `/api/arena/sync_google_sheet`, `/api/arena/trade`.
- Dashboard/positions/journal/market (14): `GET /api/dashboard`, `/api/explainability`, `/api/journal/evaluation`, `/api/journal/status`, `/api/journal/trades`, `/api/journal/trades/{trade_id}`, `/api/market-drivers`, `/api/market/dashboard`, `/api/models/authoritative-registry`, `/api/positions/{position_id}`, `/api/status`, `/api/terminal/model-identity`, `/api/terminal/readiness`, `/api/notifications/research-alerts/conditions`.
- Prediction/quality (27): `GET /api/prediction/accuracy`, `/api/prediction/accuracy/history`, `/api/prediction/failures`, `/api/prediction/intelligence`, `/api/prediction/intelligence/health`, `/api/prediction/longitudinal/health`, `/api/prediction/longitudinal/resolution-health`, `/api/prediction/pipeline/layers`, `/api/prediction/range/history`, `/api/quality`, `/api/regime`; legacy-path counterparts include `/prediction/accuracy`, `/prediction/accuracy/history`, `/prediction/failures`, `/prediction/forecast`, `/prediction/horizons`, `/prediction/horizons/health`, `/prediction/intelligence`, `/prediction/intelligence/health`, `/prediction/longitudinal/health`, `/prediction/longitudinal/resolution-health`, `/prediction/market-state`, `/prediction/market-state/history`, `/prediction/multiscale`, `/prediction/multiscale/health`, `/prediction/pipeline/layers`, `/prediction/range/history`.
- Research (20): `GET /api/research/24h-scorecard`, `/api/research/directional-audit`, `/api/research/directional-v4-manifest`, `/api/research/directional-v5-freeze-manifest`, `/api/research/eligibility-audit`, `/api/research/empirical-remediation-report`, `/api/research/entry-tp-sl`, `/api/research/experiments`, `/api/research/forward-status`, `/api/research/foundation-models`, `/api/research/models`, `/api/research/next-trigger`, `/api/research/prospective-ledger`, `/api/research/shadow-ledger`, `/api/research/shadow-status`, `/api/research/smart-entry/pipeline/latest`, `/api/research/statistical-inference-v6-audit`; legacy-path counterparts `/research/foundation-models`, `/research/models`, `/research/next-trigger`; `POST /api/research/smart-entry/pipeline`.
- Tournament (4): `GET /api/tournament/candidates`, `/api/tournament/regime`, `/api/tournament/scenarios`; `POST /api/tournament/run-tournament`.
- Notifications (2): `POST /api/notifications/research-alerts/evaluate`; `GET /api/notifications/research-alerts/conditions`.
- Other (16): `GET /candles`, `/comparator`, `/genome/latest_generation`, `/genome/leaderboard`, `/genome/{genome_id}`, `/genome/{genome_id}/lineage`, `/genome/{genome_id}/quarantine`, `/ping`; `POST /prediction/record`, `/api/journal/trades/enter`, `/api/journal/trades/{trade_id}/adjust`, `/api/journal/trades/{trade_id}/exit`, `/api/arena/sync_google_sheet`, `/api/arena/trade`, `/api/arena/paper-trades/close`.

The route census is a static decorator scan. It is not an API behavior test; selected input/output schemas, error semantics, and frontend display provenance remain endpoint-specific.

## Analytical services, models, and tests

The 32 `ENG-*` rows in the registry cover rolling/PIT features, HAR and semivariance, L2 calculators, directional/volatility/range forecasts, regime/state, setup and strategy generation/selection, barrier labels, binary meta-models, risk/uncertainty, forecast monitoring, market data adapters, persistence, execution simulation, model registry states, C2, funding, and open interest. Specific symbols, inputs, available evidence, endpoint/UI mappings, test filenames, and limitations are recorded per row.

The five-directory static scan found 566 Python source files, including 376 under `tests/`. The capability inventory maps targeted tests only; it does not claim that every test relates to a listed capability or that all 376 test files were reviewed. No tests were run in this milestone.

## Explicit omissions

The 54-row registry is not a method-by-method enumeration of every file/function in the repository. The following directories and feature families require a separate inventory before claiming repository-wide exhaustiveness: `research/`, `training/`, `validation/`, `calibration/`, `labeling/`, `features/`, `models/` beyond cited services, `api/` beyond the 12 route groups, and remaining engine modules not cited in the registry; root configuration, migrations, data manifests, and `web_src/` also need dedicated reconciliation. Several API route internals were only statically grouped, and no response schemas were inferred from names.

Accordingly, "54 discovered features" in the manager report means **54 grouped registry records**, not the total number of software capabilities or functions in BTCognitive.

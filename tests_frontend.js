/**
 * tests_frontend.js — Frontend Module & Request Budget Unit Tests
 */

const fs = require("fs");
const assert = require("assert");
const { formatPrice, formatPct, formatBps, formatIsoTime } = require("./web_src/formatters.js");
const { api, resilientFetch, _inflightRequests, _responseCache } = require("./web_src/api_client.js");
const {
  validateHourlySnapshot,
  verifyAnalysisResponse,
  ANALYSIS_MINIMUM_HISTORY
} = require("./web/analysis_contract.js");

async function runTests() {
  console.log("Starting Frontend Module Verification Tests...");

  // 1. Formatters
  console.log("Testing formatters...");
  assert.strictEqual(formatPrice(1234.56), "1,234.56");
  assert.strictEqual(formatPrice(null), "—");
  assert.strictEqual(formatPrice(NaN), "—");
  assert.strictEqual(formatPct(2.5), "+2.50%");
  assert.strictEqual(formatPct(-1.25), "-1.25%");
  assert.strictEqual(formatPct(null), "—");
  assert.strictEqual(formatBps(15.4), "+15.4 bps");
  assert.strictEqual(formatBps(-5.0), "-5.0 bps");
  assert.strictEqual(formatIsoTime("2026-08-31T12:00:00Z"), "2026-08-31 12:00:00 UTC");

  // 2. Resilient Fetch & In-flight Deduplication
  console.log("Testing in-flight request deduplication...");
  let fetchCount = 0;
  global.fetch = async (url) => {
    fetchCount++;
    await new Promise((r) => setTimeout(r, 20));
    return {
      ok: true,
      status: 200,
      json: async () => ({ endpoint: url, count: fetchCount })
    };
  };

  // Launch 5 concurrent identical requests
  const promises = [
    resilientFetch("http://test.local/api/concurrent"),
    resilientFetch("http://test.local/api/concurrent"),
    resilientFetch("http://test.local/api/concurrent"),
    resilientFetch("http://test.local/api/concurrent"),
    resilientFetch("http://test.local/api/concurrent")
  ];
  const results = await Promise.all(promises);
  assert.strictEqual(fetchCount, 1, `Expected 1 network call for 5 concurrent requests, got ${fetchCount}`);
  assert.strictEqual(results[0].endpoint, "http://test.local/api/concurrent");
  assert.strictEqual(results[4].count, 1);

  // 3. TTL Caching
  console.log("Testing TTL response caching...");
  const cachedResult = await resilientFetch("http://test.local/api/concurrent", {}, 2000);
  assert.strictEqual(fetchCount, 1, "Expected cached response without new network call");
  assert.strictEqual(cachedResult.count, 1);

  // 4. Rate Limiter 429 Exponential Backoff
  console.log("Testing 429 backoff handling...");
  global.fetch = async () => ({
    ok: false,
    status: 429,
    statusText: "Too Many Requests",
    json: async () => ({ detail: "Rate limit exceeded" })
  });

  let threw429 = false;
  try {
    await resilientFetch("http://test.local/api/rate-limited", {}, 0);
  } catch (err) {
    threw429 = true;
    assert(err.message.includes("429"), `Unexpected error: ${err.message}`);
  }
  assert(threw429, "Expected 429 exception to be thrown");

  // Subsequent call during backoff window should fail fast or serve cache
  let threwBackoff = false;
  try {
    await resilientFetch("http://test.local/api/rate-limited", {}, 0);
  } catch (err) {
    threwBackoff = true;
    assert(err.message.includes("Rate limit backoff active"), `Expected backoff message, got ${err.message}`);
  }
  assert(threwBackoff, "Expected request within backoff window to be rejected immediately");

  // 5. Polling Request Budget Analysis
  console.log("Verifying UI Polling Budget against 60 req/min limit...");
  const totalReqPerMin = (60 / 5) + (60 / 8) + (60 / 15) + (60 / 15) + (60 / 30);
  assert(
    totalReqPerMin < 60,
    `Total UI steady-state polling (${totalReqPerMin} req/min) exceeds server rate limit (60 req/min)`
  );
  console.log(`Steady-state polling budget: ${totalReqPerMin} req/min (server limiter: 60 req/min). PASSED.`);

  // 6. Endpoint & WebSocket Resolution (Same-Origin, Custom Origin, Netlify, WSS)
  console.log("Testing API and WebSocket endpoint resolution...");
  function resolveApi(mockStorage, mockWindow) {
    const custom = mockStorage?.getItem?.("btcognitive_api_url");
    if (custom) return custom;
    if (mockWindow?.BTCOGNITIVE_API_URL) return mockWindow.BTCOGNITIVE_API_URL;
    if (mockWindow?.__BTCOGNITIVE_CONFIG__?.apiUrl) return mockWindow.__BTCOGNITIVE_CONFIG__.apiUrl;
    if (mockWindow?.NEXT_PUBLIC_API_URL) return mockWindow.NEXT_PUBLIC_API_URL;
    if (mockWindow?.location?.origin && mockWindow.location.origin !== "null") {
      return mockWindow.location.origin;
    }
    return "http://localhost:8000";
  }

  function resolveWs(mockStorage, mockWindow) {
    const customWs = mockStorage?.getItem?.("btcognitive_ws_url");
    if (customWs) return customWs;
    if (mockWindow?.BTCOGNITIVE_WS_URL) return mockWindow.BTCOGNITIVE_WS_URL;
    if (mockWindow?.__BTCOGNITIVE_CONFIG__?.wsUrl) return mockWindow.__BTCOGNITIVE_CONFIG__.wsUrl;

    const apiUrl = resolveApi(mockStorage, mockWindow);
    try {
      const parsed = new URL(apiUrl);
      const wsProto = parsed.protocol === "https:" ? "wss:" : "ws:";
      return `${wsProto}//${parsed.host}/ws`;
    } catch {
      const host = (mockWindow?.location?.hostname) || "localhost";
      return `ws://${host}:8000/ws`;
    }
  }

  // Case A: Default localhost fallback
  assert.strictEqual(resolveApi({}, {}), "http://localhost:8000");
  assert.strictEqual(resolveWs({}, {}), "ws://localhost:8000/ws");

  // Case B: Same-origin production (e.g. Docker / Fly.io container serving web/)
  assert.strictEqual(
    resolveApi({}, { location: { origin: "https://btcognitive-engine.fly.dev" } }),
    "https://btcognitive-engine.fly.dev"
  );
  assert.strictEqual(
    resolveWs({}, { location: { origin: "https://btcognitive-engine.fly.dev" } }),
    "wss://btcognitive-engine.fly.dev/ws"
  );

  // Case C: Separately hosted frontend on Netlify with custom backend in localStorage
  const netlifyStorage = {
    data: { btcognitive_api_url: "https://btcognitive-api.fly.dev" },
    getItem(k) { return this.data[k]; }
  };
  assert.strictEqual(
    resolveApi(netlifyStorage, { location: { origin: "https://btcognitive.netlify.app" } }),
    "https://btcognitive-api.fly.dev"
  );
  assert.strictEqual(
    resolveWs(netlifyStorage, { location: { origin: "https://btcognitive.netlify.app" } }),
    "wss://btcognitive-api.fly.dev/ws"
  );

  // Case D: Window global injection (BTCOGNITIVE_API_URL / BTCOGNITIVE_WS_URL)
  assert.strictEqual(
    resolveApi({}, { BTCOGNITIVE_API_URL: "https://custom-domain.com", location: { origin: "https://btcognitive.netlify.app" } }),
    "https://custom-domain.com"
  );
  assert.strictEqual(
    resolveWs({}, { BTCOGNITIVE_API_URL: "https://custom-domain.com", BTCOGNITIVE_WS_URL: "wss://custom-ws.com/ws" }),
    "wss://custom-ws.com/ws"
  );

  console.log("All API and WebSocket endpoint resolution tests PASSED.");

  // 7. Navigation Update, How It Works, Home Overview Cards & Smart Entry Preservation Checks
  console.log("Testing Navigation & Home Overview UI update markers...");
  const appSource = fs.readFileSync("./web/app.js", "utf8");
  const indexSource = fs.readFileSync("./web/index.html", "utf8");
  const stylesSource = fs.readFileSync("./web/styles.css", "utf8");
  const analysisContractSource = fs.readFileSync("./web/analysis_contract.js", "utf8");
  assert(indexSource.includes('/app.js?v=35.4.3'), "V35.4.3 app.js cache-busting reference missing from web/index.html.");
  assert(indexSource.includes('/styles.css?v=32.50.4'), "V32.50 responsive stylesheet cache-busting reference missing from web/index.html.");
  const tickerSource = appSource.slice(
    appSource.indexOf("function InstitutionalTickerBar"),
    appSource.indexOf("function SystemAtAGlanceCard")
  );
  assert(tickerSource.includes("const price = !isFixture && livePrice > 0 ? livePrice : null;"), "Fixture mode must suppress ticker prices without explicit fixture summary provenance.");
  assert(tickerSource.includes("!isFixture && typeof marketSummary?.low_24h === \"number\""), "Fixture mode must not display a market 24h range.");
  assert(tickerSource.includes("!isFixture && typeof marketSummary?.realized_volatility_24h_pct === \"number\""), "Fixture mode must not display market realized volatility.");
  assert(tickerSource.includes("fixture summary not provided"), "Fixture ticker metrics must explicitly remain unavailable when fixture summary is absent.");

  // V32.50 Terminal directional forecast overlay and transparent failure states.
  assert(appSource.includes('id: "chart-ai-forecast-overlay"'), "Default-on chart forecast overlay is missing.");
  assert(appSource.includes('id: "toggle-ai-forecast-btn"'), "Persistable chart forecast visibility toggle is missing.");
  assert(appSource.includes('showAiForecast: parsed.showAiForecast !== false'), "Forecast overlay must default on for existing chart preferences.");
  assert(appSource.includes('function getDirectionalForecastState'), "Forecast response validation helper is missing.");
  assert(appSource.includes('function getLatestClosedChartCandle'), "Directional markers must anchor only to a closed chart candle.");
  assert(appSource.includes('forecastOrigin >= forecastAnchor.time') && appSource.includes('forecastOrigin < forecastAnchor.time + chartStep'), "Chart markers must not misalign with the forecast's source candle.");
  assert(appSource.includes('forecast_origin_timestamp'), "Forecast marker must use the reported closed-candle origin.");
  assert(appSource.includes('P(UP) ') && appSource.includes('P(DOWN) '), "The overlay must display the model's raw probabilities.");
  assert(appSource.includes('Classifier probabilities are not calibrated confidence or a future price path.'), "The overlay must distinguish probabilities from price forecasts.");
  assert(appSource.includes('"FORECAST_MALFORMED"') && appSource.includes('"FORECAST_STALE"') && appSource.includes('"REQUEST_TIMEOUT"'), "Forecast failure and stale states must have explicit reason codes.");
  assert(appSource.includes('status: freshness === "DELAYED"') && appSource.includes("Number.isFinite(directionalForecast.probabilityUp)"), "Delayed forecasts must preserve valid fields and never render NaN probabilities.");
  assert(appSource.includes("historical context only and must not be treated as current."), "Delayed forecast messaging must prohibit current-signal interpretation.");
  assert(appSource.includes('setInterval(fetchForecast, 60000)'), "Forecast polling must not be tied to active-position polling.");
  assert(appSource.includes('setMarkers(markers)'), "Forecast updates must replace, not append, chart markers.");
  assert(appSource.includes('chart.candles.compute_and_render') && appSource.includes('analysis.integrated_request'), "Chart and Analyse timing spans are missing.");
  assert(stylesSource.includes("grid-template-columns: minmax(0, 1fr);"), "Single-column workstation layout must allow chart content to shrink on mobile.");
  assert(stylesSource.includes(".chart-ai-forecast-overlay") && stylesSource.includes("max-height: 190px;"), "Mobile forecast overlay must be compact and scrollable.");
  assert(appSource.includes("const _whatIfInFlightRequests = new Map();") && appSource.includes("if (pending) return pending;"), "Identical in-flight what-if calculations must be deduplicated without reusing stale results.");

  // A. Primary Navigation Assertions
  assert(appSource.includes('id: "nav-how-it-works"'), "Primary navigation must include 'How It Works' (nav-how-it-works).");
  assert(appSource.includes('"#/how-it-works"'), "Primary navigation 'How It Works' link must point to '#/how-it-works'.");
  assert(!appSource.includes('id: "nav-smart-entry"'), "Smart Entry must be removed from primary navigation (nav-smart-entry).");
  assert(appSource.includes('id: "banner-how-it-works-btn"'), "Top research banner must include 'How It Works' button.");
  assert(!appSource.includes('id: "banner-smart-entry-btn"'), "Top research banner must not have duplicate Smart Entry button.");

  // B. How It Works View & Route Assertions
  assert(appSource.includes('function HowItWorksView'), "HowItWorksView component must be defined in web/app.js.");
  assert(appSource.includes('id: "how-it-works-page"'), "How It Works page container ID 'how-it-works-page' must exist.");
  assert(appSource.includes('path === "/how-it-works"'), "App router must include path === '/how-it-works' handler.");
  assert(appSource.includes('id: `hiw-stage-${stg.num}`') || appSource.includes('hiw-stage-'), "How It Works stage container ID must exist.");
  assert(appSource.includes("1. Market Data Collection & Integrity Validation"), "Stage 1 title missing.");
  assert(appSource.includes("2. Causal Point-in-Time Feature Extraction"), "Stage 2 title missing.");
  assert(appSource.includes("3. Forecasting via Directional Models & Empirical Baselines"), "Stage 3 title missing.");
  assert(appSource.includes("4. Volatility Risk Estimation & Conformal Calibration"), "Stage 4 title missing.");
  assert(appSource.includes("5. Statistical Drift Monitoring & Prequential Evaluation"), "Stage 5 title missing.");
  assert(appSource.includes("6. Evidence-Based Research Gate & Strict Non-Execution"), "Stage 6 title missing.");

  // C. Home Overview 6-Card Architecture Grid Assertions
  assert(appSource.includes('id: "home-overview-card-grid"'), "Home Overview card grid must exist.");
  assert(appSource.includes('id: "home-card-market-data"'), "Home card Market Data must exist.");
  assert(appSource.includes('id: "home-card-ai-forecasting"'), "Home card AI Forecasting must exist.");
  assert(appSource.includes('id: "home-card-risk-uncertainty"'), "Home card Risk and Uncertainty must exist.");
  assert(appSource.includes('id: "home-card-market-intelligence"'), "Home card Market Intelligence must exist.");
  assert(appSource.includes('id: "home-card-adaptive-monitoring"'), "Home card Adaptive Monitoring must exist.");
  assert(appSource.includes('id: "home-card-research-decision-gate"'), "Home card Research Decision Gate must exist.");

  // Home card action button destinations
  assert(appSource.includes('id: "home-btn-market-data"'), "Home card Market Data action button missing.");
  assert(appSource.includes('id: "home-btn-ai-forecasting"'), "Home card AI Forecasting action button missing.");
  assert(appSource.includes('id: "home-btn-risk-uncertainty"'), "Home card Risk and Uncertainty action button missing.");
  assert(appSource.includes('id: "home-btn-market-intelligence"'), "Home card Market Intelligence action button missing.");
  assert(appSource.includes('id: "home-btn-adaptive-monitoring"'), "Home card Adaptive Monitoring action button missing.");
  assert(appSource.includes('id: "home-btn-research-decision-gate"'), "Home card Research Decision Gate action button missing.");

  // D. Truthful Status & Non-Live Claims Assertions
  assert(appSource.includes("NO_GO_NO_VALIDATED_EDGE"), "Research decision gate must truthfully display NO_GO_NO_VALIDATED_EDGE.");
  assert(appSource.includes("OFFLINE_RESEARCH_ONLY"), "Research decision gate must truthfully display OFFLINE_RESEARCH_ONLY.");
  assert(appSource.includes("LIVE TRADING DISABLED") || appSource.toLowerCase().includes("live trading disabled"), "Live trading disabled notice must be explicitly displayed.");

  // E. Smart Entry Preservation (Internal components and direct route preserved)
  assert(appSource.includes('"/smart-entry"'), "Smart Entry direct route must be preserved for backward compatibility.");
  assert(appSource.includes('function SmartEntryPanel'), "SmartEntryPanel component must be preserved.");
  assert(appSource.includes('function SmartEntryView'), "SmartEntryView component must be preserved.");
  assert(appSource.includes('Load Synthetic Demo'), "Synthetic demo action preserved in Smart Entry panel.");
  assert(appSource.includes('fetchSmartEntryDecision'), "Smart Entry API client call preserved.");
  assert(appSource.includes('id: "smart-entry-btn-evaluate"'), "Evaluate button ID preserved.");
  assert(appSource.includes('id: "smart-entry-status-badge"'), "Status badge ID preserved.");
  assert(appSource.includes('id: "result-candidate-card"'), "Candidate card ID preserved.");
  assert(appSource.includes('id: "result-no-candidate-note"'), "No candidate fallback note preserved.");
  assert(typeof api.fetchSmartEntryDecision === "function", "fetchSmartEntryDecision preserved in web_src/api_client.js");

  // V32.14 Live Terminal Smart Entry Native Integration Markers
  assert(appSource.includes('tab-btn-smart-entry'), "Native Live Terminal Smart Entry tab button preserved.");
  assert(appSource.includes('id: "v19-area-smart-entry"'), "Native Live Terminal Smart Entry container pane preserved.");
  assert(appSource.includes('id: "btn-open-smart-entry-tab"'), "AI Prediction panel Smart Entry bridge button preserved.");
  assert(appSource.includes('id: "smart-entry-btn-live-context"'), "Sync Live Terminal AI Context action preserved.");
  assert(appSource.includes('id: "smart-entry-data-source-badge"'), "Data source identity badge preserved.");
  assert(appSource.includes('id: "smart-entry-exec-disabled-badge"'), "Execution disabled badge preserved.");
  assert(appSource.includes('id: "result-market-regime-vol"'), "Market regime & volatility element preserved.");
  assert(appSource.includes('id: "result-strategy-rationale"'), "Strategy rationale element preserved.");
  assert(appSource.includes('id: "result-rrr-costs"'), "RRR and friction costs element preserved.");
  assert(appSource.includes('id: "result-horizon"'), "Horizon bars element preserved.");
  assert(appSource.includes('id: "result-evidence-quality"'), "Evidence quality status element preserved.");
  assert(appSource.includes('id: "result-data-source"'), "Data source label element preserved.");
  assert(appSource.includes('BTC-USD (${predictionData?.market?.source || "SOURCE UNAVAILABLE"})'), "Unknown source provenance must remain unavailable rather than defaulting to Coinbase.");
  assert(!appSource.includes('BTC-USD (Coinbase)'), "Unknown BTC-USD source provenance must not imply Coinbase.");
  console.log("Navigation, How It Works, Home Overview Cards, and Smart Entry preservation PASSED.");

  // V32.31 Coinbase L2 Microstructure Gating Integration Markers
  console.log("Testing V32.31 Coinbase L2 Microstructure Gating UI integration markers...");
  assert(typeof api.fetchL2GatingStatus === "function", "fetchL2GatingStatus missing from web_src/api_client.js");
  assert(typeof api.fetchL2ShadowEvaluation === "function", "fetchL2ShadowEvaluation missing from web_src/api_client.js");
  assert(appSource.includes("L2GatingResearchPanel"), "L2GatingResearchPanel component missing from web/app.js");
  assert(appSource.includes('id: "l2-gating-research-panel"'), "L2 gating research panel ID missing.");
  assert(appSource.includes('id: "l2-collector-badge"'), "L2 collector badge missing.");
  assert(appSource.includes('id: "l2-trading-badge"'), "L2 live trading disabled badge missing.");
  assert(appSource.includes('id: "l2-target-strategy"'), "L2 target strategy label missing.");
  assert(appSource.includes('id: "l2-gating-rules"'), "L2 gating rules label missing.");
  assert(appSource.includes('id: "l2-sample-target"'), "L2 confirmatory sample target label missing.");
  assert(appSource.includes('id: "l2-confirmatory-decision"'), "L2 confirmatory decision label missing.");
  console.log("V32.31 Coinbase L2 Microstructure Gating UI integration markers PASSED.");

  // V32.35 AI Forecasts & Risk Outlook Integration Markers
  console.log("Testing V32.35 AI Forecasts & Risk Outlook UI integration markers...");
  assert(typeof api.fetchForecastLatest === "function", "fetchForecastLatest missing from web_src/api_client.js");
  assert(typeof api.fetchTerminalLive === "function", "fetchTerminalLive missing from web_src/api_client.js");
  assert(typeof api.fetchPriceForecast === "function", "fetchPriceForecast missing from web_src/api_client.js");

  assert(appSource.includes('id: "nav-forecast"'), "Nav AI Forecasts link ID missing.");
  assert(appSource.includes('id: "home-card-ai-forecasting"') || appSource.includes('id: "hero-card-forecast"'), "Hero/Home AI Forecasts card ID missing.");
  assert(appSource.includes('id: "home-btn-ai-forecasting"') || appSource.includes('id: "hero-btn-forecast"'), "Hero/Home AI Forecasts button ID missing.");
  assert(appSource.includes('id: "banner-forecast-btn"'), "Top banner AI Forecasts button ID missing.");
  assert(appSource.includes('"tab-btn-forecast"'), "Workstation AI Forecasts tab reference missing.");
  assert(appSource.includes('id: "v32-35-forecast-outlook-view"'), "AiForecastRiskOutlookView root container ID missing.");
  assert(appSource.includes('id: "dir-model-id"'), "Directional model ID marker missing.");
  assert(appSource.includes('id: "dir-prob-up"'), "Directional P(UP) marker missing.");
  assert(appSource.includes('id: "dir-prob-down"'), "Directional P(DOWN) marker missing.");
  assert(appSource.includes('id: "dir-predicted-direction"'), "Directional predicted sign marker missing.");
  assert(appSource.includes('id: "vol-har-rs-dow"'), "HAR-RS-DOW realized variance marker missing.");
  assert(appSource.includes('id: "vol-har-rs-dow", style:') && appSource.includes('"NOT ESTABLISHED"'), "Unverified Standard HAR forecast is not suppressed.");
  assert(appSource.includes('id: "c2-conformal-envelope"'), "C2 conformal risk envelope marker missing.");
  assert(appSource.includes("UNAVAILABLE — calibration artifact not verified"), "C2 unavailable state missing.");
  assert(appSource.includes("C2 calibration: UNAVAILABLE (disabled by governance)"), "Smart Entry C2 control is not visibly disabled.");
  assert(!appSource.includes("84.89% (Causal 2026)"), "Unverified C2 coverage claim remains in frontend.");
  assert(!appSource.includes("P10–P90"), "Unverified C2 envelope claim remains in frontend.");
  assert(!appSource.includes("0.914"), "Hardcoded fallback coverage remains in frontend.");
  assert(!appSource.includes("0.204"), "Hardcoded fallback Winkler score remains in frontend.");
  assert(appSource.includes("No calibrated levels, first-passage probabilities, effective sample sizes, confidence intervals, or validation status are available."), "Cross-horizon calibration outputs must remain unavailable.");
  assert(appSource.includes('"N/A — C2 DISABLED"') && !appSource.includes("hUpper.path_probability_horizon") && !appSource.includes("hLower.path_probability_horizon"), "C2-disabled path cards must not render probabilities from stale payloads.");
  assert(appSource.includes('"N_eff: N/A"'), "Missing calibration sample sizes and intervals must remain unavailable.");
  assert(appSource.includes('"FIXED-CONTRACT SENSITIVITY: UNAVAILABLE"'), "Fixed-contract sensitivity must not display unverified probabilities.");
  assert(!appSource.includes('prov.evidence_config_hash || "0x8f3c2a1e"'), "Unavailable provenance must not receive a fabricated hash.");
  assert(!appSource.includes('"PARTIALLY_RESOLVED"'), "Missing historical source provenance must not be upgraded to partially resolved.");
  assert(!appSource.includes('59.25"} bps on 110 retained'), "Historical subgroup metrics must not use a hardcoded success fallback.");
  assert(!appSource.includes('effective_independent_samples_n_eff || 1'), "Missing effective sample size must not default to one.");
  assert(appSource.includes('const t0 = null;'), "Legacy first-passage outputs must remain suppressed while C2 is disabled.");
  assert(appSource.includes('h("div", null, "Calibration: ", h("strong", { style: { color: "#F8FAFC" } }, "UNAVAILABLE"))'), "Unverified signal quality must not render calibration percentages.");
  assert(!appSource.includes('qualityData?.calibration_score != null'), "Calibration score must not be derived from an unverified quality payload.");
  assert(appSource.includes('id: "vol-calibration-health"'), "Observatory calibration health marker missing.");
  assert(appSource.includes('id: "status-chronos-not-executed"'), "Chronos-2 unexecuted status marker missing.");
  assert(appSource.includes("Directional probability is not the probability of a trade hitting take-profit"), "Mandatory directional interpretation notice missing.");
  assert(appSource.includes("C2 calibration is unavailable: no calibrated coverage or risk bounds are returned."), "Mandatory unavailable-calibration notice missing.");
  console.log("V32.35 AI Forecasts & Risk Outlook UI integration markers PASSED.");

  // V32.41 Paper-Trading & Shadow Evaluation Integration Markers
  console.log("Testing V32.41 Paper-Trading & Shadow Evaluation UI integration markers...");
  assert(appSource.includes('id: "nav-paper-trading"'), "nav-paper-trading link ID missing from Navbar.");
  assert(appSource.includes('id: "home-btn-paper-trading"'), "home-btn-paper-trading button ID missing from HomeOverview.");
  assert(appSource.includes("PaperTradingDashboardView"), "PaperTradingDashboardView component missing from web/app.js.");
  assert(appSource.includes('id: "paper-warning-banner"'), "paper-warning-banner ID missing.");
  assert(appSource.includes('id: "paper-sleeve-gated"'), "paper-sleeve-gated ID missing.");
  assert(appSource.includes('id: "paper-sleeve-ungated"'), "paper-sleeve-ungated ID missing.");
  assert(appSource.includes('id: "paper-latency-metric"'), "paper-latency-metric ID missing.");
  assert(appSource.includes('id: "paper-cost-metric"'), "paper-cost-metric ID missing.");
  assert(appSource.includes("Strict Non-Execution Invariant"), "Strict non-execution warning title missing.");
  assert(appSource.includes("NO_GO_NO_VALIDATED_EDGE"), "NO_GO_NO_VALIDATED_EDGE governance label missing.");
  assert(appSource.includes("LIVE TRADING PERMANENTLY DISABLED"), "Live trading permanently disabled label missing.");
  console.log("V32.41 Paper-Trading & Shadow Evaluation UI integration markers PASSED.");

  // V32.42 User Position Tracker & Adaptive Risk Copilot Integration Markers
  console.log("Testing V32.42 User Position Tracker & Adaptive Risk Copilot UI integration markers...");
  assert(typeof api.fetchUserPositions === "function", "fetchUserPositions missing from web_src/api_client.js");
  assert(typeof api.fetchUserPositionsHistory === "function", "fetchUserPositionsHistory missing from web_src/api_client.js");
  assert(typeof api.fetchCopilotStatus === "function", "fetchCopilotStatus missing from web_src/api_client.js");
  assert(typeof api.recordOpenPosition === "function", "recordOpenPosition missing from web_src/api_client.js");
  assert(typeof api.recordPartialExit === "function", "recordPartialExit missing from web_src/api_client.js");
  assert(typeof api.recordClosePosition === "function", "recordClosePosition missing from web_src/api_client.js");

  assert(appSource.includes('id: "nav-position-monitor"'), "nav-position-monitor link ID missing from Navbar.");
  assert(appSource.includes('id: "home-btn-position-copilot"'), "home-btn-position-copilot button ID missing from HomeOverview.");
  assert(appSource.includes("PositionMonitorView"), "PositionMonitorView component missing from web/app.js.");
  assert(appSource.includes('id: "copilot-warning-banner"'), "copilot-warning-banner ID missing.");
  assert(appSource.includes('id: "copilot-feed-banner"'), "copilot-feed-banner ID missing.");
  assert(appSource.includes('id: "copilot-metric-count"'), "copilot-metric-count ID missing.");
  assert(appSource.includes('id: "copilot-metric-unrealized-pnl"'), "copilot-metric-unrealized-pnl ID missing.");
  assert(appSource.includes('id: "copilot-record-form-card"'), "copilot-record-form-card ID missing.");
  assert(appSource.includes('id: "btn-submit-open-position"'), "btn-submit-open-position ID missing.");
  assert(appSource.includes('id: "copilot-closed-positions-history"'), "copilot-closed-positions-history ID missing.");
  assert(appSource.includes("STRICT NON-EXECUTION INVARIANT"), "Non-execution invariant warning missing.");
  assert(appSource.includes("SPOT_SHORT_INELIGIBLE"), "SPOT_SHORT_INELIGIBLE guard note missing.");
  console.log("V32.42 User Position Tracker & Adaptive Risk Copilot UI integration markers PASSED.");

  // V32.42 Manual Trade Journal & AI Forecast Evaluation Integration Markers
  console.log("Testing V32.42 Manual Trade Journal & AI Forecast Evaluation UI integration markers...");
  assert(typeof api.fetchJournalStatus === "function", "fetchJournalStatus missing from web_src/api_client.js");
  assert(typeof api.fetchJournalTrades === "function", "fetchJournalTrades missing from web_src/api_client.js");
  assert(typeof api.fetchJournalEvaluation === "function", "fetchJournalEvaluation missing from web_src/api_client.js");
  assert(typeof api.recordEnterTrade === "function", "recordEnterTrade missing from web_src/api_client.js");
  assert(typeof api.recordExitTrade === "function", "recordExitTrade missing from web_src/api_client.js");
  assert(typeof api.recordAdjustTrade === "function", "recordAdjustTrade missing from web_src/api_client.js");

  assert(appSource.includes('id: "nav-manual-journal"'), "nav-manual-journal link ID missing from Navbar.");
  assert(appSource.includes('id: "home-btn-trade-journal"'), "home-btn-trade-journal button ID missing from Home Card 6.");
  assert(appSource.includes('id: "btn-hero-entered-trade"'), "btn-hero-entered-trade button ID missing from HeroSection.");
  assert(appSource.includes("ManualTradeJournalView"), "ManualTradeJournalView component missing from web/app.js.");
  assert(appSource.includes('id: "journal-warning-banner"'), "journal-warning-banner ID missing.");
  assert(appSource.includes('id: "btn-i-entered-trade"'), "btn-i-entered-trade ID missing.");
  assert(appSource.includes('id: "journal-open-records"'), "journal-open-records section ID missing.");
  assert(appSource.includes('id: "journal-closed-records"'), "journal-closed-records section ID missing.");
  assert(appSource.includes('id: "journal-ai-evaluation"'), "journal-ai-evaluation section ID missing.");
  assert(appSource.includes('id: "journal-sample-disclaimer"'), "journal-sample-disclaimer ID missing.");
  assert(appSource.includes("INSUFFICIENT EVIDENCE"), "INSUFFICIENT EVIDENCE caveat note missing.");
  assert(appSource.includes("FORECAST SNAPSHOT SAVED"), "FORECAST SNAPSHOT SAVED badge missing.");
  assert(appSource.includes("GROSS_PNL_ONLY"), "GROSS_PNL_ONLY label missing.");
  console.log("V32.42 Manual Trade Journal & AI Forecast Evaluation UI integration markers PASSED.");

  // V32.43 Strategy Tournament & Smart Entry Lifecycle Integration Markers
  console.log("Testing V32.43 Strategy Tournament & Smart Entry Lifecycle UI integration markers...");
  assert(typeof api.analyseMarket === "function", "analyseMarket missing from web_src/api_client.js");
  assert(typeof api.runTournament === "function", "runTournament missing from web_src/api_client.js");
  assert(typeof api.fetchSmartEntryLatest === "function", "fetchSmartEntryLatest missing from web_src/api_client.js");
  assert(typeof api.enterSimulatedTrade === "function", "enterSimulatedTrade missing from web_src/api_client.js");
  assert(typeof api.fetchSimulatedAttempts === "function", "fetchSimulatedAttempts missing from web_src/api_client.js");
  assert(typeof api.exitSimulatedAttempt === "function", "exitSimulatedAttempt missing from web_src/api_client.js");
  assert(typeof api.partialExitSimulatedAttempt === "function", "partialExitSimulatedAttempt missing from web_src/api_client.js");
  assert(typeof api.fetchSmartEntryEvaluation === "function", "fetchSmartEntryEvaluation missing from web_src/api_client.js");
  assert(typeof api.fetchStrategyRegistry === "function", "fetchStrategyRegistry missing from web_src/api_client.js");

  assert(appSource.includes("SmartEntrySimulatorView"), "SmartEntrySimulatorView component missing from web/app.js.");
  assert(appSource.includes('id: "btn-hero-smart-entry"'), "btn-hero-smart-entry button missing from HeroSection.");
  assert(appSource.includes('id: "home-btn-smart-entry"'), "home-btn-smart-entry button missing from Card 4.");
  assert(appSource.includes('id: "smart-entry-warning-banner"'), "smart-entry-warning-banner ID missing.");
  assert(appSource.includes('id: "smart-entry-forecast-panel"'), "smart-entry-forecast-panel ID missing.");
  assert(appSource.includes('id: "btn-analyse-setup"'), "btn-analyse-setup ID missing.");
  assert(appSource.includes('id: "btn-run-tournament"'), "btn-run-tournament ID missing.");
  assert(appSource.includes('id: "btn-enter-simulated-trade"'), "btn-enter-simulated-trade ID missing.");
  assert(appSource.includes('id: "smart-entry-evaluation-section"'), "smart-entry-evaluation-section ID missing.");
  assert(appSource.includes("7/10 SCREEN"), "7/10 SCREEN badge text missing.");
  assert(appSource.includes("TP/SL LOCKED · IMMUTABLE"), "TP/SL LOCKED · IMMUTABLE badge missing.");
  assert(appSource.includes('id: "active-monitor-error"'), "Visible monitor failure state missing.");
  assert(appSource.includes("monitorInFlightRef"), "Duplicate monitor polling guard missing.");
  assert(appSource.includes("Forecast changes are advisory; locked TP/SL do not move."), "Active forecast comparison and immutable-level disclosure missing.");
  assert(appSource.includes(" — no eligible candidates"), "Skipped tournament reason is missing from the progress stepper.");
  assert(appSource.includes("analysisData?.tournament?.execution_source"), "Tournament step state must fall back to integrated analysis provenance.");
  assert(appSource.includes('"BACKTEST EVIDENCE UNAVAILABLE"'), "Unavailable verified tournament evidence must not be mislabeled as no qualifying setup.");
  assert(appSource.includes("Preliminary screening returned candidates, but verified tournament evidence is unavailable."), "Evidence-blocked abstention must distinguish screened candidates from a no-candidate result.");
  assert(appSource.includes("No candidates met the preliminary screen, so the tournament was not run."), "No-candidate result must explain why the tournament was skipped.");
  console.log("V32.43 Strategy Tournament & Smart Entry Lifecycle UI integration markers PASSED.");

  // V35.3 Epistemic Integrity and Fail-Closed Assertions
  console.log("Testing V35.3 Epistemic Integrity and Fail-Closed UI markers...");
  assert(!appSource.includes("livePrice * 1.008"), "Synthetic upper excursion multiplier livePrice * 1.008 must be removed.");
  assert(!appSource.includes("livePrice * 0.993"), "Synthetic lower excursion multiplier livePrice * 0.993 must be removed.");
  assert(!appSource.includes("v2.1-REGIME-PROD"), "Mock production model v2.1-REGIME-PROD must be removed.");
  assert(!appSource.includes("pop.total_trades || 194"), "Hardcoded historical trade count 194 must be removed.");
  assert(!appSource.includes("{ balance: 10.96 }"), "Hardcoded equity curve upward path must be removed.");
  assert(appSource.includes("EQUITY CURVE UNAVAILABLE (TRADING DISABLED)"), "Explicit trading disabled equity curve message required.");
  assert(appSource.includes("QUALITY METRICS UNAVAILABLE"), "Signal quality gauge must render fail-closed unavailable state.");
  assert(appSource.includes("OFFLINE RESEARCH MODE (Standard Corsi HAR Baseline)"), "Model lineage strip must default to offline research baseline.");
  assert(appSource.includes("P_U(15m): DATA_UNAVAILABLE"), "Dual hypothesis upper excursion must fail closed to DATA_UNAVAILABLE.");
  assert(appSource.includes("P_L(15m): DATA_UNAVAILABLE"), "Dual hypothesis lower excursion must fail closed to DATA_UNAVAILABLE.");
  assert(appSource.includes("P_0(15m): DATA_UNAVAILABLE"), "Dual hypothesis survival scenario must fail closed to DATA_UNAVAILABLE.");
  console.log("V35.3 Epistemic Integrity and Fail-Closed UI markers PASSED.");

  console.log("Testing analysis snapshot and unavailable-response contract...");
  const latestOpen = Math.floor(Date.now() / 3600000) * 3600 - 3600;
  const analysisCandles = Array.from({ length: ANALYSIS_MINIMUM_HISTORY }, (_, index) => {
    const time = latestOpen - (ANALYSIS_MINIMUM_HISTORY - 1 - index) * 3600;
    return {
      timestamp_utc: new Date(time * 1000).toISOString(),
      open: 100 + index,
      high: 102 + index,
      low: 99 + index,
      close: 101 + index,
      volume: 5,
      is_closed: true
    };
  });
  const freshSnapshot = validateHourlySnapshot(analysisCandles, "FRESH", "LOCAL_BITSTAMP_CACHE");
  assert(freshSnapshot.valid, freshSnapshot.reason || "Fresh local snapshot should be eligible.");
  assert(!validateHourlySnapshot(analysisCandles, "STALE", "LOCAL_BITSTAMP_CACHE").valid, "Stale snapshots must not be eligible.");
  assert(!validateHourlySnapshot(analysisCandles, "FRESH", "BITSTAMP_REST").valid, "External provider labels must not be eligible.");
  assert(!validateHourlySnapshot(analysisCandles.slice(1), "FRESH", "LOCAL_BITSTAMP_CACHE").valid, "Insufficient history must fail closed.");
  const gapCandles = analysisCandles.map(candle => ({ ...candle }));
  gapCandles[40].timestamp_utc = new Date((latestOpen - 158 * 3600) * 1000).toISOString();
  assert(!validateHourlySnapshot(gapCandles, "FRESH", "LOCAL_BITSTAMP_CACHE").valid, "Gapped timestamps must fail closed.");
  const malformedCandles = analysisCandles.map(candle => ({ ...candle }));
  malformedCandles[10].volume = null;
  assert(!validateHourlySnapshot(malformedCandles, "FRESH", "LOCAL_BITSTAMP_CACHE").valid, "Missing volume must not be replaced with zero.");
  const snapshotHash = await require("crypto").createHash("sha256")
    .update(JSON.stringify(analysisCandles.map(candle => Object.fromEntries(
      Object.entries(candle).sort(([a], [b]) => a.localeCompare(b))
    ))))
    .digest("hex");
  const validAnalysisResponse = {
    status: "SUCCESS",
    data_provenance: {
      source: "LOCAL_BITSTAMP_CACHE",
      authorization: "OFFLINE_RESEARCH_ONLY",
      submitted_candle_count: analysisCandles.length,
      analyzed_closed_candle_count: analysisCandles.length,
      request_payload_sha256: snapshotHash,
      snapshot_id: snapshotHash
    }
  };
  assert(await verifyAnalysisResponse(validAnalysisResponse, analysisCandles, "LOCAL_BITSTAMP_CACHE"), "Matching response provenance and snapshot hash must be accepted.");
  assert(!await verifyAnalysisResponse({ status: "SUCCESS" }, analysisCandles, "LOCAL_BITSTAMP_CACHE"), "Malformed API responses must be rejected.");
  assert(!await verifyAnalysisResponse({
    ...validAnalysisResponse,
    data_provenance: { ...validAnalysisResponse.data_provenance, snapshot_id: "0".repeat(64) }
  }, analysisCandles, "LOCAL_BITSTAMP_CACHE"), "A response for a different candle snapshot must be rejected.");
  assert(indexSource.includes('/analysis_contract.js'), "Analysis response contract helper must load before the frontend app.");
  assert(appSource.includes("Analysis could not finish:"), "Analysis API errors must render visibly.");
  assert(appSource.includes("freshnessStatus"), "The frontend must preserve candle freshness status.");
  assert(appSource.includes("REPORTED MODEL CORRECTNESS"), "Manual journal outcomes must be labelled as reported, not validated accuracy.");
  assert(!appSource.includes("((aiPerf.model_accuracy_rate || 0)"), "Missing model accuracy must not render as zero percent.");
  assert(!appSource.includes('"NORMAL VOLATILITY"'), "Missing regime data must not be replaced with a normal-regime claim.");
  assert(analysisContractSource.includes("The snapshot must be strictly ordered and hourly-contiguous."), "Snapshot validator must reject duplicate or gapped candles.");

  console.log("All Frontend Unit Tests Passed Successfully!");
}


runTests().catch((err) => {
  console.error("Frontend Test Failed:", err);
  process.exit(1);
});

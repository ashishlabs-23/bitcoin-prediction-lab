/**
 * web/src/api_client.js — Hardened HTTP Client with Deduplication & Backoff
 * Guarantees request budget adherence under high-frequency polling.
 */

const _inflightRequests = new Map();
const _responseCache = new Map();
let _rateLimitBackoffUntil = 0;
let _rateLimitBackoffDelay = 1000;

function getApiBaseUrl() {
  if (typeof window !== "undefined" && window.__API_BASE__) {
    return window.__API_BASE__.replace(/\/+$/, "");
  }
  if (typeof window !== "undefined" && window.location) {
    return window.location.origin;
  }
  return "http://127.0.0.1:8000";
}

function isTabVisible() {
  if (typeof document === "undefined") return true;
  return !document.hidden;
}

async function resilientFetch(url, options = {}, ttlMs = 1500) {
  const isGet = !options.method || options.method.toUpperCase() === "GET";
  const now = Date.now();

  // If rate-limited (HTTP 429), respect backoff window
  if (now < _rateLimitBackoffUntil && isGet) {
    const cached = _responseCache.get(url);
    if (cached) return Promise.resolve(JSON.parse(JSON.stringify(cached.data)));
    throw new Error(`Rate limit backoff active for ${Math.ceil((_rateLimitBackoffUntil - now) / 1000)}s`);
  }

  // Check TTL cache for GET
  if (isGet && ttlMs > 0) {
    const entry = _responseCache.get(url);
    if (entry && (now - entry.timestamp) < ttlMs) {
      return Promise.resolve(JSON.parse(JSON.stringify(entry.data)));
    }
  }

  // In-flight deduplication: return existing pending promise
  if (isGet && _inflightRequests.has(url)) {
    return _inflightRequests.get(url);
  }

  const promise = (async () => {
    try {
      const res = await fetch(url, options);
      if (res.status === 429) {
        const jitter = Math.random() * 500;
        _rateLimitBackoffUntil = Date.now() + _rateLimitBackoffDelay + jitter;
        _rateLimitBackoffDelay = Math.min(_rateLimitBackoffDelay * 2, 16000);
        throw new Error("HTTP 429 Rate Limit Exceeded");
      }
      _rateLimitBackoffDelay = 1000;
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      const data = await res.json();
      if (isGet && ttlMs > 0) {
        _responseCache.set(url, { timestamp: Date.now(), data });
      }
      return data;
    } finally {
      if (isGet) _inflightRequests.delete(url);
    }
  })();

  if (isGet) _inflightRequests.set(url, promise);
  return promise;
}

const api = {
  async fetchPredictionLatest(live = false) {
    return resilientFetch(`${getApiBaseUrl()}/prediction/latest?live=${live}`);
  },
  async fetchPredictionHistory(limit = 20) {
    return resilientFetch(`${getApiBaseUrl()}/prediction/history?limit=${limit}`);
  },
  async fetchRegimeLatest(live = false) {
    return resilientFetch(`${getApiBaseUrl()}/regime/latest?live=${live}`);
  },
  async fetchExplanationLatest(live = false) {
    return resilientFetch(`${getApiBaseUrl()}/explanation/latest?live=${live}`);
  },
  async fetchQualityLatest(live = false) {
    return resilientFetch(`${getApiBaseUrl()}/quality/latest?live=${live}`);
  },
  async fetchMemory() {
    const d = await resilientFetch(`${getApiBaseUrl()}/memory`);
    return Array.isArray(d) ? d : (d?.memory || []);
  },
  async fetchPortfolio() {
    return resilientFetch(`${getApiBaseUrl()}/portfolio`);
  },
  async fetchMarketLatest() {
    const data = await resilientFetch(`${getApiBaseUrl()}/market/latest`);
    const technical = data?.technical || {};
    return {
      ...data,
      change_pct_24h: typeof technical.momentum_24h_pct === "number" ? technical.momentum_24h_pct : null,
      high_24h: typeof technical.high_24h_usd === "number" ? technical.high_24h_usd : null,
      low_24h: typeof technical.low_24h_usd === "number" ? technical.low_24h_usd : null,
      realized_volatility_24h_pct: typeof technical.realized_volatility_24h_pct === "number"
        ? technical.realized_volatility_24h_pct
        : null
    };
  },
  async fetchCounterfactual(topK = 5) {
    return resilientFetch(`${getApiBaseUrl()}/prediction/counterfactual?top_k=${topK}`);
  },
  async fetchDecisionAnatomy() {
    return resilientFetch(`${getApiBaseUrl()}/api/terminal/decision-anatomy`);
  },
  async fetchWhatIfScenario(tpPrice, slPrice, horizon = "15m", volMult = 1.0, spotPrice = null) {
    return resilientFetch(`${getApiBaseUrl()}/api/arena/what-if-scenario`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tp_price: tpPrice ? Number(tpPrice) : null,
        sl_price: slPrice ? Number(slPrice) : null,
        horizon: horizon,
        vol_multiplier: Number(volMult),
        spot_price: spotPrice ? Number(spotPrice) : null
      })
    }, 0);
  },
  async fetchRangeLatest() {
    return resilientFetch(`${getApiBaseUrl()}/prediction/range`);
  },
  async fetchRangePath(horizon = "24h") {
    return resilientFetch(`${getApiBaseUrl()}/prediction/range/path?horizon=${encodeURIComponent(horizon)}`);
  },
  async fetchRangeHealth() {
    return resilientFetch(`${getApiBaseUrl()}/prediction/range/health`);
  },
  async fetchLongitudinalStatus() {
    return resilientFetch(`${getApiBaseUrl()}/prediction/longitudinal`);
  },
  async fetchDirectionAccuracy() {
    return resilientFetch(`${getApiBaseUrl()}/prediction/direction/accuracy`);
  },
  async fetchAnalogs(k = 20) {
    return resilientFetch(`${getApiBaseUrl()}/research/analogs?k=${k}&min_similarity=0.35`);
  },
  async fetchHealth() {
    return resilientFetch(`${getApiBaseUrl()}/health`);
  },
  async fetchIntelligenceLatest() {
    return resilientFetch(`${getApiBaseUrl()}/intelligence/latest`);
  },
  async fetchReplaySnapshot(timestamp = null) {
    const url = timestamp ? `${getApiBaseUrl()}/replay?timestamp=${encodeURIComponent(timestamp)}` : `${getApiBaseUrl()}/replay`;
    return resilientFetch(url);
  },
  async fetchNotificationsRecent(limit = 20) {
    return resilientFetch(`${getApiBaseUrl()}/api/notifications/recent?limit=${limit}`);
  },
  async fetchNotificationSettings() {
    return resilientFetch(`${getApiBaseUrl()}/api/notifications/settings`);
  },
  async updateNotificationSettings(settings, adminKey) {
    const key = adminKey?.trim();
    if (!key) throw new Error("Admin API key is required to save notification settings.");
    return resilientFetch(`${getApiBaseUrl()}/api/notifications/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": key },
      body: JSON.stringify(settings)
    }, 0);
  },
  async triggerTestAlert(adminKey) {
    const key = adminKey?.trim();
    if (!key) throw new Error("Admin API key is required to send a notification test.");
    return resilientFetch(`${getApiBaseUrl()}/api/notifications/test`, {
      method: "POST",
      headers: { "X-API-Key": key }
    }, 0);
  },
  async fetchActivePaperPosition(strategyName = null, indicators = null, userDirection = "AUTO", horizon = "15m", evidenceMode = "AI_RECOMMEND", signalMode = "live_ai") {
    const params = new URLSearchParams();
    if (strategyName) params.append("strategy_name", strategyName);
    if (indicators && indicators.length > 0) params.append("indicators", indicators.join(","));
    if (userDirection && userDirection !== "AUTO") params.append("user_direction", userDirection);
    if (horizon) params.append("horizon", horizon);
    if (evidenceMode && evidenceMode !== "AI_RECOMMEND") params.append("evidence_mode", evidenceMode);
    if (signalMode) params.append("signal_mode", signalMode);
    const qs = params.toString() ? `?${params.toString()}` : "";
    return resilientFetch(`${getApiBaseUrl()}/api/arena/active-paper-position${qs}`);
  },
  async fetchArenaTradeMarkers(limit = 100, strategyName = null) {
    const url = strategyName
      ? `${getApiBaseUrl()}/api/arena/trade-markers?limit=${limit}&strategy_name=${encodeURIComponent(strategyName)}`
      : `${getApiBaseUrl()}/api/arena/trade-markers?limit=${limit}`;
    return resilientFetch(url);
  },
  async fetchStrategySummary() {
    return resilientFetch(`${getApiBaseUrl()}/api/arena/strategy-summary`);
  },
  async runArenaExperiment(payload = {}) {
    return resilientFetch(`${getApiBaseUrl()}/api/arena/experiment`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }, 0);
  },
  async fetchLineage() {
    return resilientFetch(`${getApiBaseUrl()}/api/lineage`);
  },
  async fetchMemoryStats() {
    return resilientFetch(`${getApiBaseUrl()}/memory/stats`);
  },
  async fetchArenaContext() {
    return resilientFetch(`${getApiBaseUrl()}/api/arena/context`);
  },
  async fetchArenaStatus() {
    return resilientFetch(`${getApiBaseUrl()}/api/arena/status`);
  },
  async resetArenaExperiment(adminKey = "") {
    const headers = {};
    if (adminKey) headers["X-API-Key"] = adminKey;
    return resilientFetch(`${getApiBaseUrl()}/api/arena/reset`, { method: "POST", headers }, 0);
  }
};

if (typeof module !== "undefined" && module.exports) {
  module.exports = { api, resilientFetch, getApiBaseUrl, isTabVisible, _inflightRequests, _responseCache };
}

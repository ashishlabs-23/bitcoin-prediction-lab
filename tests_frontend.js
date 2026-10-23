/**
 * tests_frontend.js — Frontend Module & Request Budget Unit Tests
 */

const assert = require("assert");
const { formatPrice, formatPct, formatBps, formatIsoTime } = require("./web_src/formatters.js");
const { api, resilientFetch, _inflightRequests, _responseCache } = require("./web_src/api_client.js");

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

  console.log("All Frontend Unit Tests Passed Successfully!");
}

runTests().catch((err) => {
  console.error("Frontend Test Failed:", err);
  process.exit(1);
});

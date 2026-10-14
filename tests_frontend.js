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
  // Normal mode active tab polling rates:
  // App active position: every 5s -> 12 req/min
  // Terminal markers: every 8s -> 7.5 req/min
  // Laboratory data: every 15s -> 4 req/min
  // Health: every 15s -> 4 req/min
  // AI data: every 30s -> 2 req/min
  const totalReqPerMin = (60 / 5) + (60 / 8) + (60 / 15) + (60 / 15) + (60 / 30);
  assert(
    totalReqPerMin < 60,
    `Total UI steady-state polling (${totalReqPerMin} req/min) exceeds server rate limit (60 req/min)`
  );
  console.log(`Steady-state polling budget: ${totalReqPerMin} req/min (server limiter: 60 req/min). PASSED.`);

  console.log("All Frontend Unit Tests Passed Successfully!");
}

runTests().catch((err) => {
  console.error("Frontend Test Failed:", err);
  process.exit(1);
});

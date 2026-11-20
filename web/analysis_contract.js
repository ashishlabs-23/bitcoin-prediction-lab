(function (root) {
  "use strict";

  const ANALYSIS_MINIMUM_HISTORY = 200;
  const ANALYSIS_SOURCES = new Set(["LOCAL_BITSTAMP_CACHE", "LOCAL_HISTORICAL_SNAPSHOT"]);
  const HOUR_SECONDS = 3600;

  function stableJson(value) {
    if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
    if (value && typeof value === "object") {
      return `{${Object.keys(value).sort().map(key =>
        `${JSON.stringify(key)}:${stableJson(value[key])}`
      ).join(",")}}`;
    }
    const encoded = JSON.stringify(value);
    if (encoded === undefined) throw new TypeError("Snapshot contains a non-JSON value.");
    return encoded;
  }

  function validateHourlySnapshot(candles, freshnessStatus, source, nowSeconds = Date.now() / 1000) {
    if (freshnessStatus !== "FRESH") return { valid: false, reason: "The candle snapshot is not fresh." };
    if (!ANALYSIS_SOURCES.has(source)) return { valid: false, reason: "The candle source is not an accepted local snapshot." };
    if (!Array.isArray(candles) || candles.length < ANALYSIS_MINIMUM_HISTORY) {
      return { valid: false, reason: `${ANALYSIS_MINIMUM_HISTORY} closed hourly candles are required.` };
    }

    let previousTime = null;
    for (const candle of candles) {
      const timestamp = Date.parse(candle?.timestamp_utc || "");
      const values = [candle?.open, candle?.high, candle?.low, candle?.close, candle?.volume];
      if (!Number.isFinite(timestamp) || timestamp % (HOUR_SECONDS * 1000) !== 0 ||
        candle?.is_closed !== true || timestamp / 1000 + HOUR_SECONDS > nowSeconds ||
        !values.every(value => typeof value === "number" && Number.isFinite(value)) ||
        values.slice(0, 4).some(value => value <= 0) || values[4] < 0) {
        return { valid: false, reason: "The snapshot contains an incomplete or malformed candle." };
      }
      const [open, high, low, close] = values;
      if (low > Math.min(open, close) || high < Math.max(open, close) || high < low) {
        return { valid: false, reason: "The snapshot contains invalid OHLC geometry." };
      }
      const time = timestamp / 1000;
      if (previousTime !== null && time - previousTime !== HOUR_SECONDS) {
        return { valid: false, reason: "The snapshot must be strictly ordered and hourly-contiguous." };
      }
      previousTime = time;
    }
    return { valid: true, reason: null };
  }

  async function sha256(value) {
    const serialized = stableJson(value);
    const cryptoApi = root.crypto;
    if (cryptoApi?.subtle && root.TextEncoder) {
      const bytes = new TextEncoder().encode(serialized);
      const digest = await cryptoApi.subtle.digest("SHA-256", bytes);
      return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
    }
    if (typeof require === "function") {
      return require("crypto").createHash("sha256").update(serialized, "utf8").digest("hex");
    }
    throw new Error("This browser cannot verify the analysis snapshot hash.");
  }

  async function verifyAnalysisResponse(response, submittedCandles, source) {
    if (!response || typeof response !== "object" || typeof response.status !== "string") return false;
    const provenance = response.data_provenance;
    if (!provenance || provenance.authorization !== "OFFLINE_RESEARCH_ONLY" ||
      provenance.source !== source || provenance.submitted_candle_count !== submittedCandles.length ||
      provenance.analyzed_closed_candle_count !== submittedCandles.length ||
      typeof provenance.snapshot_id !== "string" ||
      provenance.snapshot_id !== provenance.request_payload_sha256) return false;
    return (await sha256(submittedCandles)) === provenance.snapshot_id;
  }

  const contract = { ANALYSIS_MINIMUM_HISTORY, validateHourlySnapshot, verifyAnalysisResponse };
  root.BTCognitiveAnalysisContract = contract;
  if (typeof module !== "undefined" && module.exports) module.exports = contract;
})(globalThis);

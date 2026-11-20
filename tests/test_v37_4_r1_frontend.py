import shutil
import subprocess
from pathlib import Path


def test_chart_displays_bitstamp_candles_from_api_shaped_observation():
    node = shutil.which("node")
    assert node is not None, "Node.js is required to exercise the active frontend feed and chart."

    app_js = Path(__file__).resolve().parents[1] / "web" / "app.js"
    script = r"""
const fs = require("fs");
const vm = require("vm");
const app = fs.readFileSync(process.argv[1], "utf8");
const apiBody = {
  status: "ACTIVE",
  freshness_status: "FRESH",
  symbol: "BTC/USD",
  exchange: "Bitstamp",
  market_type: "SPOT",
  interval: "1m",
  source: "bitstamp",
  last_event_timestamp: "2026-11-04T15:50:00.250000Z",
  last_receive_timestamp: "2026-11-04T15:50:00.500000Z",
  event_to_receive_delay_seconds: 0.25,
  candles: [{
    time: 1793807400,
    open: 68400.0,
    high: 68430.0,
    low: 68390.0,
    close: 68420.5,
    volume: 0.025,
    is_closed: true,
    source: "bitstamp"
  }]
};

const hookStart = app.indexOf("function useMarketCandleFeed(");
const hookEnd = app.indexOf("// LightweightCandleChart component", hookStart);
const badgeStart = app.indexOf("function LiveBadge(");
const chartStart = app.indexOf("function ChartTopBar(", badgeStart);
const chartEnd = app.indexOf("// Navbar", chartStart);
if ([hookStart, hookEnd, badgeStart, chartStart, chartEnd].some(index => index < 0)) {
  throw new Error("The active market-feed or chart component could not be located.");
}

const state = [];
const refs = [];
let stateIndex = 0;
let refIndex = 0;
let renderCount = 0;
let requestedUrl = null;
function h(type, props, ...children) {
  return { type, props: props || {}, children: children.flat(Infinity) };
}
const context = {
  useState(initial) {
    const index = stateIndex++;
    if (!(index in state)) state[index] = typeof initial === "function" ? initial() : initial;
    return [state[index], value => {
      state[index] = typeof value === "function" ? value(state[index]) : value;
    }];
  },
  useRef(initial) {
    const index = refIndex++;
    if (!(index in refs)) refs[index] = { current: initial };
    return refs[index];
  },
  useCallback(callback) { return callback; },
  useEffect(effect) {
    if (renderCount === 0) effect();
  },
  h,
  formatCandleCountdown(seconds) {
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  },
  INTERVAL_MAP: { "1m": "1m", "5m": "5m", "15m": "15m", "1H": "1h", "4H": "4h", "1D": "1d" },
  INTERVAL_STEP: { "1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400 },
  getApiBaseUrl: () => "http://fixture.local",
  fetch: async url => {
    requestedUrl = url;
    return { ok: true, status: 200, json: async () => apiBody };
  },
  AbortController,
  setTimeout: () => 1,
  clearTimeout: () => {},
  setInterval: () => 1,
  clearInterval: () => {},
  performance,
  Date,
  console
};
vm.createContext(context);
vm.runInContext(app.slice(hookStart, hookEnd) + "\n" + app.slice(badgeStart, chartEnd), context);

async function main() {
  stateIndex = 0;
  refIndex = 0;
  const firstRender = context.useMarketCandleFeed("1m");
  await new Promise(resolve => setImmediate(resolve));
  stateIndex = 0;
  refIndex = 0;
  renderCount = 1;
  const market = context.useMarketCandleFeed("1m");

  if (!requestedUrl.includes("interval=1m")) throw new Error(`Wrong request interval: ${requestedUrl}`);
  if (market.wsStatus !== "ACTIVE" || market.historyStatus !== "ready") {
    throw new Error(`Feed status not rendered as ready: ${market.wsStatus}/${market.historyStatus}`);
  }
  if (market.historySource !== "bitstamp" || market.livePrice !== 68420.5) {
    throw new Error("The API observation source or price was not passed to the chart.");
  }
  if (market.seedCandles.length !== 1 ||
      market.seedCandles[0].open !== 68400 ||
      market.seedCandles[0].high !== 68430 ||
      market.seedCandles[0].low !== 68390 ||
      market.seedCandles[0].close !== 68420.5 ||
      market.seedCandles[0].volume !== 0.025) {
    throw new Error("Actual API OHLCV values were not preserved for chart display.");
  }

  stateIndex = 0;
  refIndex = 0;
  const tree = context.ChartTopBar({
    wsStatus: market.wsStatus,
    activeInterval: "1m",
    livePrice: market.livePrice,
    latestCandleTime: market.seedCandles[0].time,
    exchangeClock: market.exchangeClock,
    chartCandleSnapshot: {
      source: market.historySource,
      status: market.wsStatus,
      freshnessStatus: market.historyFreshness,
      candles: market.seedCandles
    }
  });
  function text(node) {
    if (node == null || node === false || node === true) return "";
    if (Array.isArray(node)) return node.map(text).join("");
    if (typeof node === "string" || typeof node === "number") return String(node);
    if (typeof node.type === "function") return text(node.type(node.props));
    return (node.children || []).map(text).join("");
  }
  const displayed = text(tree);
  for (const expected of ["Bitstamp", "$68,420.50", "ACTIVE"]) {
    if (!displayed.includes(expected)) throw new Error(`Chart display omitted ${expected}.`);
  }
  if (displayed.includes("Coinbase quote:")) {
    throw new Error("Bitstamp observation receipt time is mislabeled as a Coinbase quote.");
  }
}

main().catch(error => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
"""

    result = subprocess.run(
        [node, "-e", script, str(app_js)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout

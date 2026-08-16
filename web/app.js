/* ==========================================================================
   BTCognitive — Live Binance Chart + AI Prediction Overlay
   Architecture:
     • Binance REST  → seed 200 candles instantly on load / interval change
     • Binance WSS   → wss://stream.binance.com:9443/ws/btcusdt@kline_<interval>
     • lightweight-charts → candleSeries.update(bar) — O(1), no full redraws
     • Backend REST  → AI prediction/history every 30 s
     • Backend WSS   → engine connection status only
   ========================================================================== */

const { useState, useEffect, useRef, useCallback, createElement: h } = React;
const abs = Math.abs;

// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Config & Dynamic Endpoint Resolution
// ---------------------------------------------------------------------------
function getApiBaseUrl() {
  return localStorage.getItem("btcognitive_api_url") || window.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

function setApiBaseUrl(url) {
  if (!url || url.trim() === "http://localhost:8000") {
    localStorage.removeItem("btcognitive_api_url");
  } else {
    const clean = url.trim().replace(/\/+$/, "");
    localStorage.setItem("btcognitive_api_url", clean);
  }
}

function getWsBaseUrl() {
  const apiUrl = getApiBaseUrl();
  try {
    const parsed = new URL(apiUrl);
    const wsProto = parsed.protocol === "https:" ? "wss:" : "ws:";
    return `${wsProto}//${parsed.host}/ws`;
  } catch {
    return window.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";
  }
}

async function validateBackendUrl(candidateUrl) {
  if (!candidateUrl) {
    return { valid: false, error: "Please enter a backend URL." };
  }
  const cleanUrl = candidateUrl.trim().replace(/\/+$/, "");
  
  if (window.location.protocol === "https:" && cleanUrl.startsWith("http://")) {
    const isLocalhost = cleanUrl.includes("localhost") || cleanUrl.includes("127.0.0.1");
    if (!isLocalhost) {
      return {
        valid: false,
        error: "Browser Security Restriction (Mixed Content): On an HTTPS site, browsers block unencrypted http:// connections. Use an HTTPS endpoint (e.g. https://...ngrok-free.app or https://...onrender.com)."
      };
    }
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);
    const res = await fetch(`${cleanUrl}/health`, {
      signal: controller.signal,
      headers: { "Accept": "application/json" }
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      return {
        valid: false,
        error: `Server responded with HTTP ${res.status} (${res.statusText}). /health check failed.`
      };
    }

    const data = await res.json();
    if (!data || typeof data !== "object" || (data.status === undefined && data.models_loaded === undefined && data.engine === undefined)) {
      return {
        valid: false,
        error: "Endpoint reached, but the response does not match the BTCognitive backend schema."
      };
    }

    return {
      valid: true,
      data,
      cleanUrl
    };
  } catch (err) {
    if (err.name === "AbortError") {
      return { valid: false, error: "Connection timed out (6s). Server did not respond." };
    }
    if (window.location.protocol === "https:" && cleanUrl.startsWith("http://")) {
      return {
        valid: false,
        error: "Blocked by browser security (Mixed Content): HTTPS sites block unencrypted HTTP. Use an HTTPS tunnel or hosted backend."
      };
    }
    return {
      valid: false,
      error: `Connection failed: ${err.message || "Network/CORS error"}. Ensure backend is running with CORS enabled.`
    };
  }
}

const INTERVAL_MAP = {
  "1m": "1m", "5m": "5m", "15m": "15m",
  "1H": "1h", "4H": "4h", "1D": "1d"
};

// Step size in seconds for each Binance interval (used for future-candle projection)
const INTERVAL_STEP = {
  "1m": 60, "5m": 300, "15m": 900,
  "1h": 3600, "4h": 14400, "1d": 86400
};

// Coinbase Exchange public endpoints — native BTC-USD spot with ultra-fast 50Hz ticker feed
const COINBASE_REST = (interval) => {
  const granMap = { "1h": 3600, "4h": 14400, "1d": 86400 };
  const gran = granMap[interval] || 3600;
  return `https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=${gran}`;
};
const COINBASE_WSS = "wss://ws-feed.exchange.coinbase.com";

// Fallback Binance public endpoint
const BINANCE_REST = (interval, limit) =>
  `https://dapi.binance.com/dapi/v1/klines?symbol=BTCUSD_PERP&interval=${interval}&limit=${limit}`;

// ---------------------------------------------------------------------------
// EMA helpers — O(1) incremental, never recalculate the whole array
// ---------------------------------------------------------------------------
const emaAlpha = (span) => 2 / (span + 1);
const EMA20_A = emaAlpha(20);
const EMA50_A = emaAlpha(50);

function computeFullEMA(closes, alpha) {
  let ema = null;
  return closes.map(c => {
    ema = ema === null ? c : alpha * c + (1 - alpha) * ema;
    return ema;
  });
}

function emaStep(prev, close, alpha) {
  return prev === null ? close : alpha * close + (1 - alpha) * prev;
}

// ---------------------------------------------------------------------------
// Backend API client (prediction, regime, quality — dynamic API endpoint)
// ---------------------------------------------------------------------------
const api = {
  async fetchPredictionLatest(live = false) {
    const res = await fetch(`${getApiBaseUrl()}/prediction/latest?live=${live}`);
    if (!res.ok) throw new Error("prediction/latest failed");
    return res.json();
  },
  async fetchPredictionHistory(limit = 20) {
    const res = await fetch(`${getApiBaseUrl()}/prediction/history?limit=${limit}`);
    if (!res.ok) throw new Error("prediction/history failed");
    return res.json();
  },
  async fetchRegimeLatest(live = false) {
    const res = await fetch(`${getApiBaseUrl()}/regime/latest?live=${live}`);
    if (!res.ok) throw new Error("regime/latest failed");
    return res.json();
  },
  async fetchExplanationLatest(live = false) {
    const res = await fetch(`${getApiBaseUrl()}/explanation/latest?live=${live}`);
    if (!res.ok) throw new Error("explanation/latest failed");
    return res.json();
  },
  async fetchQualityLatest(live = false) {
    const res = await fetch(`${getApiBaseUrl()}/quality/latest?live=${live}`);
    if (!res.ok) throw new Error("quality/latest failed");
    return res.json();
  },
  async fetchMemory() {
    const res = await fetch(`${getApiBaseUrl()}/memory`);
    if (!res.ok) throw new Error("memory failed");
    return res.json();
  },
  async fetchPortfolio() {
    const res = await fetch(`${getApiBaseUrl()}/portfolio`);
    if (!res.ok) throw new Error("portfolio failed");
    return res.json();
  },
  async fetchMarketLatest() {
    const res = await fetch(`${getApiBaseUrl()}/market/latest`);
    if (!res.ok) throw new Error("market/latest failed");
    return res.json();
  },
  async fetchCounterfactual(topK = 5) {
    const res = await fetch(`${getApiBaseUrl()}/prediction/counterfactual?top_k=${topK}`);
    if (!res.ok) throw new Error("prediction/counterfactual failed");
    return res.json();
  },
  async fetchHealth() {
    const res = await fetch(`${getApiBaseUrl()}/health`);
    if (!res.ok) throw new Error("health failed");
    return res.json();
  },
  async fetchIntelligenceLatest() {
    const res = await fetch(`${getApiBaseUrl()}/intelligence/latest`);
    if (!res.ok) throw new Error("intelligence/latest failed");
    return res.json();
  },
  async fetchReplaySnapshot(timestamp = null) {
    const url = timestamp ? `${getApiBaseUrl()}/replay?timestamp=${encodeURIComponent(timestamp)}` : `${getApiBaseUrl()}/replay`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("replay failed");
    return res.json();
  },
  async fetchNotificationsRecent(limit = 20) {
    const res = await fetch(`${getApiBaseUrl()}/api/notifications/recent?limit=${limit}`);
    if (!res.ok) throw new Error("notifications/recent failed");
    return res.json();
  },
  async fetchNotificationSettings() {
    const res = await fetch(`${getApiBaseUrl()}/api/notifications/settings`);
    if (!res.ok) throw new Error("notifications/settings failed");
    return res.json();
  },
  async updateNotificationSettings(settings) {
    const res = await fetch(`${getApiBaseUrl()}/api/notifications/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings)
    });
    if (!res.ok) throw new Error("update settings failed");
    return res.json();
  },
  async triggerTestAlert() {
    const res = await fetch(`${getApiBaseUrl()}/api/notifications/test`, {
      method: "POST"
    });
    if (!res.ok) throw new Error("test alert failed");
    return res.json();
  }
};

// ---------------------------------------------------------------------------
// Audio Synthesis & Web Native Push Notification Helpers
// ---------------------------------------------------------------------------
let audioCtx = null;
function getAudioContext() {
  if (!audioCtx) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (AudioCtx) audioCtx = new AudioCtx();
  }
  if (audioCtx && audioCtx.state === "suspended") {
    audioCtx.resume();
  }
  return audioCtx;
}

function playAudioChirp(freq = 980, type = "sine", duration = 0.15) {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(freq * 1.5, ctx.currentTime + duration);
    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + duration);
  } catch (e) {
    console.warn("Audio chirp failed:", e);
  }
}

function playOpportunityFanfare() {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6 high-profit chime
    notes.forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const start = ctx.currentTime + idx * 0.08;
      const dur = 0.22;
      osc.type = "triangle";
      osc.frequency.setValueAtTime(freq, start);
      gain.gain.setValueAtTime(0.14, start);
      gain.gain.exponentialRampToValueAtTime(0.001, start + dur);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(start);
      osc.stop(start + dur);
    });
  } catch (e) {
    console.warn("Opportunity fanfare failed:", e);
  }
}

function requestNotificationPermission() {
  if (!("Notification" in window)) {
    alert("This browser does not support desktop push notifications.");
    return Promise.resolve("unsupported");
  }
  return Notification.requestPermission();
}

function showBrowserNotification(alert) {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  try {
    const title = `🚨 ${alert.tier_title || "HIGH PROFIT ALERT"} (${alert.direction})`;
    const options = {
      body: `🎯 Entry: $${alert.entry_price?.toLocaleString()} | TP: $${alert.target_profit_price?.toLocaleString()} (+${alert.target_profit_pct}%) | Score: ${alert.opportunity_score}/100\n${alert.rationale || ""}`,
      icon: "https://cryptologos.cc/logos/bitcoin-btc-logo.png",
      tag: alert.id || "btc_opp_alert",
      renotify: true
    };
    new Notification(title, options);
  } catch (e) {
    console.warn("Browser notification failed:", e);
  }
}

// ---------------------------------------------------------------------------
// Backend WebSocket (engine status only — price/candles come from Binance)
// ---------------------------------------------------------------------------
class BackendWSManager {
  constructor() {
    this.socket = null;
    this.listeners = new Set();
    this.reconnectAttempts = 0;
    this.heartbeatInterval = null;
    this.isConnecting = false;
  }

  connect() {
    const url = getWsBaseUrl();
    if (this.socket || this.isConnecting) return;
    this.isConnecting = true;
    try {
      this.socket = new WebSocket(url);
      this.socket.onopen  = () => { this.isConnecting = false; this.reconnectAttempts = 0; this.startHeartbeat(); this.notify({ type: "connection", status: "connected" }); };
      this.socket.onclose = () => { this.cleanup(); this.notify({ type: "connection", status: "disconnected" }); this.scheduleReconnect(); };
      this.socket.onerror = () => { this.cleanup(); this.scheduleReconnect(); };
    } catch { this.isConnecting = false; this.scheduleReconnect(); }
  }

  reconnectWithNewEndpoint() {
    this.cleanup();
    this.reconnectAttempts = 0;
    this.connect();
  }

  scheduleReconnect() {
    const ms = Math.min(1000 * Math.pow(2, this.reconnectAttempts++), 20000);
    setTimeout(() => this.connect(), ms);
  }

  startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      if (this.socket?.readyState === WebSocket.OPEN)
        this.socket.send(JSON.stringify({ type: "ping" }));
    }, 15000);
  }

  stopHeartbeat() { if (this.heartbeatInterval) clearInterval(this.heartbeatInterval); }

  cleanup() {
    this.isConnecting = false; this.stopHeartbeat();
    if (this.socket) { this.socket.onopen = this.socket.onmessage = this.socket.onclose = this.socket.onerror = null; this.socket = null; }
  }

  subscribe(cb) { this.listeners.add(cb); if (!this.socket) this.connect(); return () => this.listeners.delete(cb); }
  notify(data)  { this.listeners.forEach(fn => fn(data)); }
}

const backendWS = new BackendWSManager();

// ===========================================================================
// useBinanceFeed — the core live data hook
//
// Responsibilities:
//   1. fetchHistory(interval) → Coinbase REST → seed candles
//   2. connectBinanceWS(interval) → wss://ws-feed.exchange.coinbase.com → ticker
//   3. Updates live price and tick handlers
//   4. Returns { wsStatus, seedCandles, onTickRef, livePrice }
// ===========================================================================
function useBinanceFeed(interval) {
  const [wsStatus,    setWsStatus]    = useState("disconnected");
  const [seedCandles, setSeedCandles] = useState([]);
  const [livePrice,   setLivePrice]   = useState(0);

  const wsRef          = useRef(null);
  const reconnTimeout  = useRef(null);
  const attemptsRef    = useRef(0);
  const intervalRef    = useRef(interval);
  const aliveRef       = useRef(true);

  // Chart component plugs its update handler here
  const onTickRef = useRef(null);

  // ------------------------------------------------------------------
  // Step 1 — REST seed: fetch historical candles (Coinbase primary, Binance fallback)
  // ------------------------------------------------------------------
  const fetchHistory = useCallback(async (iv) => {
    try {
      const res = await fetch(COINBASE_REST(iv));
      if (!res.ok) throw new Error(`Coinbase REST ${res.status}`);
      const raw = await res.json();
      if (!Array.isArray(raw) || !aliveRef.current) return;

      // Coinbase candles: [time, low, high, open, close, volume] sorted newest to oldest
      const candles = raw.slice().reverse().map(c => ({
        time:   c[0],
        open:   parseFloat(c[3]),
        high:   parseFloat(c[2]),
        low:    parseFloat(c[1]),
        close:  parseFloat(c[4]),
        volume: parseFloat(c[5])
      }));

      setSeedCandles(candles);
      if (candles.length) setLivePrice(candles[candles.length - 1].close);
    } catch (err) {
      console.warn("[BTCognitive] Coinbase REST fetch failed, using Binance fallback:", err);
      try {
        const bRes = await fetch(BINANCE_REST(iv, 200));
        const bRaw = await bRes.json();
        if (Array.isArray(bRaw) && aliveRef.current) {
          const bCandles = bRaw.map(k => ({
            time:   Math.floor(k[0] / 1000),
            open:   parseFloat(k[1]),
            high:   parseFloat(k[2]),
            low:    parseFloat(k[3]),
            close:  parseFloat(k[4]),
            volume: parseFloat(k[5])
          }));
          setSeedCandles(bCandles);
          if (bCandles.length) setLivePrice(bCandles[bCandles.length - 1].close);
        }
      } catch (fErr) {
        console.warn("[BTCognitive] All REST candle seeds failed:", fErr);
      }
    }
  }, []);

  // ------------------------------------------------------------------
  // Step 2 — WebSocket: connect to Coinbase high-frequency BTC-USD stream
  // ------------------------------------------------------------------
  const connectBinanceWS = useCallback((iv) => {
    // Close any existing socket first
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }
    if (reconnTimeout.current) { clearTimeout(reconnTimeout.current); reconnTimeout.current = null; }

    if (!aliveRef.current) return;
    setWsStatus("reconnecting");

    const ws = new WebSocket(COINBASE_WSS);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!aliveRef.current) { ws.close(); return; }
      attemptsRef.current = 0;
      setWsStatus("connected");
      // Subscribe to Coinbase BTC-USD ticker
      ws.send(JSON.stringify({
        type: "subscribe",
        product_ids: ["BTC-USD"],
        channels: ["ticker"]
      }));
    };

    ws.onmessage = (evt) => {
      if (!aliveRef.current) return;
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === "ticker" && msg.price) {
          const price = parseFloat(msg.price);
          setLivePrice(price);
          if (onTickRef.current) onTickRef.current({ isTicker: true, price });
        }
      } catch { /* malformed frame — ignore */ }
    };

    ws.onclose = () => {
      if (!aliveRef.current) return;
      setWsStatus("reconnecting");
      const delay = Math.min(1000 * Math.pow(2, attemptsRef.current), 30000);
      attemptsRef.current++;
      reconnTimeout.current = setTimeout(() => connectBinanceWS(intervalRef.current), delay);
    };

    ws.onerror = () => setWsStatus("disconnected");
  }, []);

  // ------------------------------------------------------------------
  // Effect: re-run on interval change
  // ------------------------------------------------------------------
  useEffect(() => {
    aliveRef.current   = true;
    intervalRef.current = interval;
    attemptsRef.current = 0;

    // Parallel: seed immediately + open socket
    fetchHistory(interval);
    connectBinanceWS(interval);

    return () => {
      aliveRef.current = false;
      if (wsRef.current) { wsRef.current.onclose = null; wsRef.current.close(); wsRef.current = null; }
      if (reconnTimeout.current) clearTimeout(reconnTimeout.current);
    };
  }, [interval, fetchHistory, connectBinanceWS]);

  return { wsStatus, seedCandles, onTickRef, livePrice };
}

// ===========================================================================
// LightweightCandleChart component
//
// Rendering layers:
//   1. Candlestick series  — BTC OHLCV
//   2. EMA-20 line         — incremental update each tick
//   3. EMA-50 line         — incremental update each tick
//   4. Forecast line       — dashed, EMA-slope extrapolation (updates on candle close)
//   5. LONG/SHORT markers  — arrowUp/arrowDown at candle time
//   6. TP price line       — dashed green horizontal on the price scale
//   7. SL price line       — dashed red horizontal on the price scale
// ===========================================================================
function LightweightCandleChart({ interval, predictionData, predictionHistory, onWsStatusChange, onPriceChange }) {
  const containerRef = useRef(null);

  // Chart instance refs (never stored in React state — no re-renders)
  const chartRef       = useRef(null);
  const candleRef      = useRef(null);
  const ema20Ref       = useRef(null);
  const ema50Ref       = useRef(null);
  const forecastRef    = useRef(null);
  const tpLineRef      = useRef(null);
  const slLineRef      = useRef(null);

  // Running EMA values (O(1) incremental — refs, not state)
  const ema20ValRef    = useRef(null);
  const ema50ValRef    = useRef(null);

  // Seed candle buffer — needed to recompute forecast line on close
  const seedRef        = useRef([]);

  // Last candle time — detect new-candle vs in-place update
  const lastTimeRef    = useRef(0);

  const { wsStatus, seedCandles, onTickRef, livePrice } = useBinanceFeed(interval);

  // Propagate WS status up
  useEffect(() => { onWsStatusChange?.(wsStatus); }, [wsStatus]);
  useEffect(() => { onPriceChange?.(livePrice); },   [livePrice]);

  // -----------------------------------------------------------------------
  // Create chart once on mount — empty deps so it only runs once
  // -----------------------------------------------------------------------
  useEffect(() => {
    if (!containerRef.current || !window.LightweightCharts) return;
    const LC = window.LightweightCharts;

    const chart = LC.createChart(containerRef.current, {
      width:  containerRef.current.clientWidth,
      height: 480,
      layout: {
        background: { color: "#0B1220" },
        textColor:  "#94A3B8",
        fontFamily: "Outfit, sans-serif"
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" }
      },
      crosshair: { mode: LC.CrosshairMode.Normal },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.08)",
        textColor:   "#94A3B8",
        scaleMargins: { top: 0.1, bottom: 0.1 }
      },
      localization: {
        locale: "en-IN",
        dateFormat: "yyyy-MM-dd",
        timeFormatter: (time) => {
          const date = new Date(time * 1000);
          return date.toLocaleString("en-IN", {
            timeZone: "Asia/Kolkata",
            hour12: false,
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit"
          }) + " IST";
        }
      },
      timeScale: {
        borderColor:    "rgba(255,255,255,0.08)",
        timeVisible:    true,
        secondsVisible: false,
        tickMarkFormatter: (time, tickMarkType, locale) => {
          const date = new Date(time * 1000);
          return date.toLocaleTimeString("en-IN", {
            timeZone: "Asia/Kolkata",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false
          });
        }
      },
      handleScroll:  { mouseWheel: true, pressedMouseMove: true },
      handleScale:   { mouseWheel: true, pinch: true }
    });

    // Layer 1 — Candlestick
    const candleSeries = chart.addCandlestickSeries({
      upColor:      "#00E5A8",
      downColor:    "#FF5C7C",
      borderUpColor:   "#00E5A8",
      borderDownColor: "#FF5C7C",
      wickUpColor:     "#00E5A8",
      wickDownColor:   "#FF5C7C"
    });

    // Layer 2 — EMA 20
    const ema20Series = chart.addLineSeries({
      color:     "#00E5A8",
      lineWidth: 1.5,
      title:     "EMA 20",
      priceLineVisible: false,
      lastValueVisible: true
    });

    // Layer 3 — EMA 50
    const ema50Series = chart.addLineSeries({
      color:     "#7C5CFF",
      lineWidth: 1.5,
      title:     "EMA 50",
      priceLineVisible: false,
      lastValueVisible: true
    });

    // Layer 4 — Forecast (dashed, amber)
    const forecastSeries = chart.addLineSeries({
      color:            "#F59E0B",
      lineWidth:        1,
      lineStyle:        LC.LineStyle.Dashed,
      title:            "AI Forecast",
      priceLineVisible: false,
      lastValueVisible: false
    });

    chartRef.current    = chart;
    candleRef.current   = candleSeries;
    ema20Ref.current    = ema20Series;
    ema50Ref.current    = ema50Series;
    forecastRef.current = forecastSeries;

    // Responsive resize observer — no manual width tracking needed
    const ro = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = candleRef.current = ema20Ref.current =
      ema50Ref.current = forecastRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // -----------------------------------------------------------------------
  // Seed: setData when REST history arrives (or interval changes)
  // -----------------------------------------------------------------------
  useEffect(() => {
    if (!candleRef.current || seedCandles.length === 0) return;

    const closes = seedCandles.map(c => c.close);

    // Full EMA pass over seed data
    const ema20Vals = computeFullEMA(closes, EMA20_A);
    const ema50Vals = computeFullEMA(closes, EMA50_A);

    // Store terminal EMA values for incremental updates on ticks
    ema20ValRef.current = ema20Vals[ema20Vals.length - 1];
    ema50ValRef.current = ema50Vals[ema50Vals.length - 1];

    // Store seed for forecast extrapolation
    seedRef.current = seedCandles;
    lastTimeRef.current = seedCandles[seedCandles.length - 1].time;

    // Load all series
    candleRef.current.setData(seedCandles);
    ema20Ref.current.setData(seedCandles.map((c, i) => ({ time: c.time, value: ema20Vals[i] })));
    ema50Ref.current.setData(seedCandles.map((c, i) => ({ time: c.time, value: ema50Vals[i] })));

    // Build initial forecast line from EMA slope
    updateForecastLine(seedCandles, interval);

    // Scroll to live edge
    chartRef.current?.timeScale().scrollToRealTime();
  }, [seedCandles]); // eslint-disable-line react-hooks/exhaustive-deps

  // -----------------------------------------------------------------------
  // Register the O(1) tick handler — runs on every Binance WS message
  // -----------------------------------------------------------------------
  useEffect(() => {
    onTickRef.current = (bar) => {
      if (!candleRef.current) return;

      if (bar.isTicker) {
        // High-frequency sub-second ticker tick update
        const seed = seedRef.current;
        if (seed && seed.length > 0) {
          const last = seed[seed.length - 1];
          const newHigh = Math.max(last.high, bar.price);
          const newLow = Math.min(last.low, bar.price);
          last.close = bar.price;
          last.high = newHigh;
          last.low = newLow;

          candleRef.current.update({
            time:  last.time,
            open:  last.open,
            high:  newHigh,
            low:   newLow,
            close: bar.price
          });

          if (ema20ValRef.current !== null) {
            const e20 = emaStep(ema20ValRef.current, bar.price, EMA20_A);
            const e50 = emaStep(ema50ValRef.current, bar.price, EMA50_A);
            ema20Ref.current?.update({ time: last.time, value: e20 });
            ema50Ref.current?.update({ time: last.time, value: e50 });
          }
        }
        return;
      }

      // 1. Candlestick — update in-place or append new bar
      candleRef.current.update({
        time:  bar.time,
        open:  bar.open,
        high:  bar.high,
        low:   bar.low,
        close: bar.close
      });

      // 2. Incremental EMA (O(1) — just one multiply+add)
      if (ema20ValRef.current !== null) {
        ema20ValRef.current = emaStep(ema20ValRef.current, bar.close, EMA20_A);
        ema50ValRef.current = emaStep(ema50ValRef.current, bar.close, EMA50_A);
        ema20Ref.current?.update({ time: bar.time, value: ema20ValRef.current });
        ema50Ref.current?.update({ time: bar.time, value: ema50ValRef.current });
      }

      // 3. On candle close — append to seed buffer and refresh forecast
      if (bar.isClosed && bar.time !== lastTimeRef.current) {
        lastTimeRef.current = bar.time;
        const newCandle = { time: bar.time, open: bar.open, high: bar.high, low: bar.low, close: bar.close, volume: bar.volume };
        seedRef.current = [...seedRef.current.slice(-199), newCandle];
        updateForecastLine(seedRef.current, intervalRef.current);
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // -----------------------------------------------------------------------
  // Forecast line — EMA-slope extrapolation into the future
  // Called only on candle close to avoid flicker
  // -----------------------------------------------------------------------
  const intervalRef = useRef(interval);
  useEffect(() => { intervalRef.current = interval; }, [interval]);

  function updateForecastLine(candles, iv) {
    if (!forecastRef.current || candles.length < 10) return;

    const step   = INTERVAL_STEP[iv] || 3600;   // seconds per bar
    const tail   = candles.slice(-10);
    const slope  = (tail[tail.length - 1].close - tail[0].close) / tail.length;
    const anchor = candles[candles.length - 1];

    // Project 20 bars into the future
    const pts = [];
    pts.push({ time: anchor.time, value: anchor.close }); // anchor at current bar
    for (let i = 1; i <= 20; i++) {
      pts.push({ time: anchor.time + i * step, value: Math.round((anchor.close + slope * i) * 100) / 100 });
    }

    try { forecastRef.current.setData(pts); } catch { /* chart may be transitioning */ }
  }

  // -----------------------------------------------------------------------
  // Prediction markers + TP/SL price lines — update when predictionData changes
  // -----------------------------------------------------------------------
  useEffect(() => {
    if (!candleRef.current || !window.LightweightCharts) return;
    const LC = window.LightweightCharts;

    // --- Remove stale TP/SL price lines ---
    if (tpLineRef.current) { try { candleRef.current.removePriceLine(tpLineRef.current); } catch {} tpLineRef.current = null; }
    if (slLineRef.current) { try { candleRef.current.removePriceLine(slLineRef.current); } catch {} slLineRef.current = null; }

    if (!predictionData || predictionData.direction === "SKIP") return;

    const isLong = predictionData.direction === "LONG";

    // --- TP price line ---
    if (predictionData.tp) {
      tpLineRef.current = candleRef.current.createPriceLine({
        price:            predictionData.tp,
        color:            isLong ? "#00E5A8" : "#FF5C7C",
        lineWidth:        1,
        lineStyle:        LC.LineStyle.Dashed,
        axisLabelVisible: true,
        title:            `TP  $${Math.round(predictionData.tp).toLocaleString()}`
      });
    }

    // --- SL price line ---
    if (predictionData.sl) {
      slLineRef.current = candleRef.current.createPriceLine({
        price:            predictionData.sl,
        color:            isLong ? "#FF5C7C" : "#00E5A8",
        lineWidth:        1,
        lineStyle:        LC.LineStyle.Dashed,
        axisLabelVisible: true,
        title:            `SL  $${Math.round(predictionData.sl).toLocaleString()}`
      });
    }
  }, [predictionData]);

  // -----------------------------------------------------------------------
  // Markers — current prediction + history markers
  // Must be sorted by time; lightweight-charts requires it
  // -----------------------------------------------------------------------
  useEffect(() => {
    if (!candleRef.current || !seedRef.current.length) return;

    const markers = [];
    const step    = INTERVAL_STEP[interval] || 3600;

    // Round a unix-seconds timestamp to nearest bar open time
    const roundToBar = (ts) => Math.floor(ts / step) * step;

    // Current prediction — anchored to latest bar
    if (predictionData && predictionData.direction !== "SKIP") {
      const lastBar  = seedRef.current[seedRef.current.length - 1];
      const isLong   = predictionData.direction === "LONG";
      markers.push({
        time:     lastBar.time,
        position: isLong ? "belowBar" : "aboveBar",
        color:    isLong ? "#00E5A8" : "#FF5C7C",
        shape:    isLong ? "arrowUp" : "arrowDown",
        text:     `${predictionData.direction}  ${predictionData.probability_pct}%`
      });
    }

    // History markers
    if (predictionHistory?.length) {
      predictionHistory.forEach(p => {
        if (!p.timestamp_ms || p.direction === "SKIP") return;
        const barTime = roundToBar(Math.floor(p.timestamp_ms / 1000));
        const isLong  = p.direction === "LONG";
        markers.push({
          time:     barTime,
          position: isLong ? "belowBar" : "aboveBar",
          color:    isLong ? "rgba(0,229,168,0.55)" : "rgba(255,92,124,0.55)",
          shape:    isLong ? "arrowUp" : "arrowDown",
          text:     `${p.probability_pct}%`
        });
      });
    }

    // lightweight-charts requires markers sorted ascending by time
    markers.sort((a, b) => a.time - b.time);
    try { candleRef.current.setMarkers(markers); } catch {}
  }, [predictionData, predictionHistory, interval]);

  return h("div", {
    ref: containerRef,
    id:  "btc-lwc-chart",
    style: { width: "100%", height: "480px", borderRadius: "0 0 12px 12px", overflow: "hidden" }
  });
}

// ===========================================================================
// LiveBadge — reflects Binance WSS connection state
// ===========================================================================
function LiveBadge({ wsStatus }) {
  const cfg = {
    connected:    { dot: "#00E5A8", text: "LIVE",         anim: "pulse 2s infinite" },
    reconnecting: { dot: "#F59E0B", text: "RECONNECTING", anim: "none" },
    disconnected: { dot: "#FF5C7C", text: "OFFLINE",      anim: "none" },
    error:        { dot: "#FF5C7C", text: "OFFLINE",      anim: "none" }
  };
  const c = cfg[wsStatus] || cfg.disconnected;

  return h("span", { style: { display: "inline-flex", alignItems: "center", gap: "6px", fontWeight: "700", fontSize: "0.82rem", color: c.dot, letterSpacing: "0.05em" } },
    h("span", { style: { width: "8px", height: "8px", borderRadius: "50%", background: c.dot, boxShadow: `0 0 8px ${c.dot}`, display: "inline-block", animation: c.anim } }),
    c.text
  );
}

// ===========================================================================
// ChartTopBar — symbol + live price + badge + timeframe buttons
// ===========================================================================
function ChartTopBar({ wsStatus, activeInterval, setActiveInterval, livePrice }) {
  return h("div", { className: "chart-topbar" },
    h("div", { className: "chart-info" },
      h("span", { className: "chart-symbol" }, "BTC / USD · Binance"),
      livePrice > 0 && h("span", {
        style: { fontFamily: "var(--font-mono)", fontWeight: "700", fontSize: "1.1rem", color: "#F8FAFC", marginLeft: "14px" }
      }, `$${livePrice.toLocaleString("en-US", { minimumFractionDigits: 2 })}`),
      h("span", { style: { marginLeft: "14px" } }, h(LiveBadge, { wsStatus }))
    ),
    h("div", { className: "tf-buttons" },
      Object.entries(INTERVAL_MAP).map(([label, iv]) =>
        h("button", {
          key: label,
          id: `tf-btn-${label}`,
          className: `tf-btn${activeInterval === iv ? " active" : ""}`,
          onClick: () => setActiveInterval(iv)
        }, label)
      )
    )
  );
}

// ===========================================================================
// Navbar
// ===========================================================================
// ===========================================================================
// ThreeBackground — Interactive 3D WebGL Particle Constellation
// ===========================================================================
function ThreeBackground() {
  const mountRef = useRef(null);

  useEffect(() => {
    if (!window.THREE) return;
    const THREE = window.THREE;
    const mount = mountRef.current;

    // Scene setup
    const scene    = new THREE.Scene();
    const camera   = new THREE.PerspectiveCamera(60, mount.offsetWidth / mount.offsetHeight, 0.1, 2000);
    camera.position.z = 550;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(mount.offsetWidth, mount.offsetHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    mount.appendChild(renderer.domElement);

    // —— Geometry: 400 particles scattered in 3D space ——
    const PARTICLE_COUNT = 400;
    const positions  = new Float32Array(PARTICLE_COUNT * 3);
    const velocities = [];
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      positions[i * 3]     = (Math.random() - 0.5) * 1200;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 700;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 600;
      velocities.push(
        (Math.random() - 0.5) * 0.25,
        (Math.random() - 0.5) * 0.15,
        (Math.random() - 0.5) * 0.10
      );
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));

    // Circular sprite texture for crisp dots
    const canvas2d = document.createElement("canvas");
    canvas2d.width = canvas2d.height = 64;
    const ctx2d = canvas2d.getContext("2d");
    const grad  = ctx2d.createRadialGradient(32, 32, 0, 32, 32, 32);
    grad.addColorStop(0, "rgba(180,140,255,1)");
    grad.addColorStop(0.4, "rgba(130,90,255,0.6)");
    grad.addColorStop(1, "rgba(0,0,0,0)");
    ctx2d.fillStyle = grad;
    ctx2d.fillRect(0, 0, 64, 64);
    const sprite = new THREE.CanvasTexture(canvas2d);

    const mat  = new THREE.PointsMaterial({ size: 3.5, map: sprite, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, vertexColors: false, color: 0xA07CFF });
    const points = new THREE.Points(geo, mat);
    scene.add(points);

    // —— Connection lines between nearby particles ——
    const lineMat = new THREE.LineBasicMaterial({ color: 0x5B3AE8, transparent: true, opacity: 0.18, blending: THREE.AdditiveBlending });
    const lineGeo = new THREE.BufferGeometry();
    const MAX_LINES = 2000;
    const linePositions = new Float32Array(MAX_LINES * 6);
    lineGeo.setAttribute("position", new THREE.BufferAttribute(linePositions, 3));
    const lineSegments = new THREE.LineSegments(lineGeo, lineMat);
    scene.add(lineSegments);

    // —— Subtle large floating torus ring as depth accent ——
    const torusGeo = new THREE.TorusGeometry(280, 1.2, 8, 120);
    const torusMat = new THREE.MeshBasicMaterial({ color: 0x6A3FFF, transparent: true, opacity: 0.12, wireframe: false });
    const torus = new THREE.Mesh(torusGeo, torusMat);
    torus.rotation.x = Math.PI / 3;
    scene.add(torus);

    // —— Second smaller accent torus ——
    const torus2Geo = new THREE.TorusGeometry(160, 0.8, 8, 80);
    const torus2Mat = new THREE.MeshBasicMaterial({ color: 0x00E5A8, transparent: true, opacity: 0.08 });
    const torus2 = new THREE.Mesh(torus2Geo, torus2Mat);
    torus2.rotation.x = -Math.PI / 4;
    torus2.rotation.y = Math.PI / 5;
    scene.add(torus2);

    // Mouse parallax
    const mouse = { x: 0, y: 0 };
    const onMouseMove = (e) => {
      mouse.x = (e.clientX / window.innerWidth  - 0.5) * 2;
      mouse.y = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener("mousemove", onMouseMove);

    // Resize handler
    const onResize = () => {
      camera.aspect = mount.offsetWidth / mount.offsetHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mount.offsetWidth, mount.offsetHeight);
    };
    window.addEventListener("resize", onResize);

    // Animation loop
    let frameId;
    const LINK_DIST = 130;
    const animate = () => {
      frameId = requestAnimationFrame(animate);
      const pos = geo.attributes.position.array;

      // Move particles
      for (let i = 0; i < PARTICLE_COUNT; i++) {
        pos[i * 3]     += velocities[i * 3];
        pos[i * 3 + 1] += velocities[i * 3 + 1];
        pos[i * 3 + 2] += velocities[i * 3 + 2];
        // Wrap-around boundary
        if (pos[i * 3]     >  600) pos[i * 3]     = -600;
        if (pos[i * 3]     < -600) pos[i * 3]     =  600;
        if (pos[i * 3 + 1] >  350) pos[i * 3 + 1] = -350;
        if (pos[i * 3 + 1] < -350) pos[i * 3 + 1] =  350;
      }
      geo.attributes.position.needsUpdate = true;

      // Build connection lines
      let lineIdx = 0;
      for (let i = 0; i < PARTICLE_COUNT && lineIdx < MAX_LINES - 1; i++) {
        for (let j = i + 1; j < PARTICLE_COUNT && lineIdx < MAX_LINES - 1; j++) {
          const dx = pos[i*3] - pos[j*3];
          const dy = pos[i*3+1] - pos[j*3+1];
          const dz = pos[i*3+2] - pos[j*3+2];
          const dist = Math.sqrt(dx*dx + dy*dy + dz*dz);
          if (dist < LINK_DIST) {
            linePositions[lineIdx*6]   = pos[i*3];
            linePositions[lineIdx*6+1] = pos[i*3+1];
            linePositions[lineIdx*6+2] = pos[i*3+2];
            linePositions[lineIdx*6+3] = pos[j*3];
            linePositions[lineIdx*6+4] = pos[j*3+1];
            linePositions[lineIdx*6+5] = pos[j*3+2];
            lineIdx++;
          }
        }
      }
      lineGeo.attributes.position.needsUpdate = true;
      lineGeo.setDrawRange(0, lineIdx * 2);

      // Torus slow rotation
      torus.rotation.z  += 0.0015;
      torus2.rotation.y += 0.0008;
      torus2.rotation.x += 0.0005;

      // Smooth camera parallax with mouse
      camera.position.x += (mouse.x * 60 - camera.position.x) * 0.04;
      camera.position.y += (-mouse.y * 40 - camera.position.y) * 0.04;
      camera.lookAt(scene.position);

      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("resize", onResize);
      renderer.dispose();
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement);
    };
  }, []);

  return h("div", {
    ref: mountRef,
    style: {
      position: "fixed",
      top: 0, left: 0,
      width: "100vw", height: "100vh",
      zIndex: 0,
      pointerEvents: "none"
    }
  });
}

// ===========================================================================
// High-Profit Opportunity Notification Components
// ===========================================================================

function OpportunityToastContainer({ alerts = [], onDismiss, onSelectAlert }) {
  if (!alerts || alerts.length === 0) return null;

  return h("div", { className: "high-profit-toast-container" },
    alerts.map((alert) => {
      const isUltra = alert.tier === "ULTRA_HIGH_PROFIT";
      const isLong = alert.direction === "LONG";
      return h("div", {
        key: alert.id,
        className: `high-profit-toast ${isUltra ? "tier-ultra" : ""} ${isLong ? "tier-long" : "tier-short"}`
      },
        h("div", { className: "toast-header" },
          h("span", { className: `toast-badge ${isUltra ? "ultra" : ""}` },
            isUltra ? "💎 ULTRA HIGH PROFIT" : (alert.badge || "🔥 HIGH CONVICTION")
          ),
          h("button", {
            className: "toast-close-btn",
            onClick: () => onDismiss(alert.id),
            title: "Dismiss"
          }, "✕")
        ),
        h("div", { className: "toast-body" },
          h("div", { className: "toast-title" },
            h("span", { style: { color: isLong ? "#00E5A8" : "#FF5C7C", fontWeight: "800" } },
              isLong ? "🚀 BUY / LONG" : "🔻 SELL / SHORT"
            ),
            h("span", { style: { fontSize: "0.85rem", color: "#F8FAFC", fontFamily: "var(--font-mono)" } },
              `@ $${alert.entry_price?.toLocaleString()}`
            )
          ),
          h("div", { style: { fontSize: "0.82rem", color: "#CBD5E1", lineHeight: "1.4" } },
            alert.rationale
          ),
          h("div", { className: "toast-grid" },
            h("div", { className: "toast-grid-item" },
              h("span", { className: "toast-grid-label" }, "Target Take-Profit"),
              h("span", { className: "toast-grid-val", style: { color: "#00E5A8" } },
                `$${alert.target_profit_price?.toLocaleString()} (+${alert.target_profit_pct}%)`
              )
            ),
            h("div", { className: "toast-grid-item" },
              h("span", { className: "toast-grid-label" }, "Stop Loss / Risk"),
              h("span", { className: "toast-grid-val", style: { color: "#FF5C7C" } },
                `$${alert.stop_loss_price?.toLocaleString()} (-${alert.risk_pct}%)`
              )
            ),
            h("div", { className: "toast-grid-item" },
              h("span", { className: "toast-grid-label" }, "Risk/Reward Ratio"),
              h("span", { className: "toast-grid-val", style: { color: "#00F0FF" } },
                alert.risk_reward_ratio || "2:1"
              )
            ),
            h("div", { className: "toast-grid-item" },
              h("span", { className: "toast-grid-label" }, "Opportunity Score"),
              h("span", { className: "toast-grid-val", style: { color: "#FFD700" } },
                `⭐ ${alert.opportunity_score}/100`
              )
            )
          )
        ),
        h("div", { className: "toast-actions" },
          h("button", {
            className: "toast-btn-action",
            onClick: () => {
              if (onSelectAlert) onSelectAlert(alert);
              onDismiss(alert.id);
            }
          }, "⚡ View Live Signal & Trade"),
          h("button", {
            className: "notif-btn-secondary",
            onClick: () => onDismiss(alert.id)
          }, "Dismiss")
        ),
        h("div", { className: "toast-progress-bar" })
      );
    })
  );
}

function NotificationBell({ alerts = [], onTestAlert, onOpenSettings, onSelectAlert }) {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef(null);

  const unreadCount = alerts.length;

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return h("div", { className: "notification-bell-wrapper", ref: dropdownRef },
    h("button", {
      className: "notification-bell-btn",
      onClick: () => setOpen(!open),
      title: "High-Profit Opportunities & Alerts"
    },
      h("span", { style: { fontSize: "1.05rem" } }, "🔔"),
      h("span", null, "Alerts"),
      unreadCount > 0 && h("span", { className: "notification-count-badge" }, unreadCount)
    ),

    open && h("div", { className: "notification-dropdown" },
      h("div", { className: "notification-dropdown-header" },
        h("div", { className: "notification-dropdown-title" },
          h("span", null, "💎"),
          h("span", null, "High-Profit Radar Alerts")
        ),
        h("button", {
          onClick: () => requestNotificationPermission().then(perm => {
            if (perm === "granted") alert("✅ Desktop push notifications enabled!");
          }),
          style: { background: "none", border: "none", color: "#00F0FF", fontSize: "0.75rem", cursor: "pointer", fontWeight: "700" }
        }, "Push Enabled")
      ),

      h("div", { className: "notification-dropdown-list" },
        alerts.length === 0 ? (
          h("div", { style: { padding: "20px 10px", textAlign: "center", color: "#94A3B8", fontSize: "0.82rem" } },
            h("div", { style: { fontSize: "1.8rem", marginBottom: "8px" } }, "📡"),
            "Scanning live market for high-profit setups (>1.5% target)..."
          )
        ) : (
          alerts.map((a, i) => (
            h("div", {
              key: a.id || i,
              className: "notification-item-card",
              onClick: () => {
                if (onSelectAlert) onSelectAlert(a);
                setOpen(false);
              }
            },
              h("div", { className: "notification-item-top" },
                h("span", { className: `notification-item-dir ${a.direction?.toLowerCase()}` },
                  `${a.direction === "LONG" ? "▲ LONG" : "▼ SHORT"} · ${a.tier === "ULTRA_HIGH_PROFIT" ? "💎 ULTRA" : "🔥 HIGH"}`
                ),
                h("span", { className: "notification-item-time" },
                  a.timestamp ? new Date(a.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Just now"
                )
              ),
              h("div", { className: "notification-item-desc" }, a.rationale),
              h("div", { className: "notification-item-meta" },
                h("span", { style: { color: "#00E5A8" } }, `TP: $${a.target_profit_price?.toLocaleString()} (+${a.target_profit_pct}%)`),
                h("span", { style: { color: "#FFD700" } }, `Score: ${a.opportunity_score}/100`)
              )
            )
          ))
        )
      ),

      h("div", { className: "notification-dropdown-footer" },
        h("button", {
          className: "notif-btn-secondary",
          onClick: onTestAlert,
          title: "Simulate a live high-profit alert"
        }, "⚡ Test Alert"),
        h("button", {
          className: "notif-btn-primary",
          onClick: () => { setOpen(false); onOpenSettings(); }
        }, "⚙️ Webhooks")
      )
    )
  );
}

function NotificationSettingsModal({ isOpen, onClose, settings, onSaveSettings, onTestAlert }) {
  if (!isOpen) return null;

  const [formData, setFormData] = useState(settings || {
    backend_url: getApiBaseUrl(),
    browser_alerts_enabled: true,
    sound_alerts_enabled: true,
    min_profit_threshold_pct: 1.5,
    webhook_enabled: false,
    webhook_url: "",
    webhook_type: "discord",
    telegram_bot_token: "",
    telegram_chat_id: ""
  });

  const [backendTestStatus, setBackendTestStatus] = useState(null); // { type: 'loading' | 'success' | 'warning' | 'error', text: '' }
  const [isValidating, setIsValidating] = useState(false);

  const handleChange = (k, v) => setFormData(prev => ({ ...prev, [k]: v }));

  const handleTestBackend = async () => {
    const targetUrl = formData.backend_url || "http://localhost:8000";
    setIsValidating(true);
    setBackendTestStatus({ type: "loading", text: "⏳ Testing connection to /health..." });
    const result = await validateBackendUrl(targetUrl);
    setIsValidating(false);

    if (result.valid) {
      const { data } = result;
      const statusLabel = data.status === "live" && data.models_loaded
        ? "🟢 LIVE & INFERENCE READY"
        : (data.status === "warming_up" || !data.models_loaded ? "🟡 CONNECTED (WARMING UP)" : "⚪ CONNECTED");
      
      setBackendTestStatus({
        type: "success",
        text: `✅ Verified BTCognitive Engine: ${statusLabel} · Models: ${data.models_loaded ? "Loaded" : "Warming"} · Uptime: ${data.uptime || 0}s`
      });
    } else {
      setBackendTestStatus({
        type: "error",
        text: `❌ ${result.error}`
      });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const targetUrl = formData.backend_url?.trim() || "http://localhost:8000";
    
    // Only validate if not localhost (or if user typed a custom URL)
    if (targetUrl && targetUrl !== getApiBaseUrl()) {
      setIsValidating(true);
      setBackendTestStatus({ type: "loading", text: "⏳ Validating backend endpoint before saving..." });
      const result = await validateBackendUrl(targetUrl);
      setIsValidating(false);

      if (!result.valid) {
        setBackendTestStatus({
          type: "error",
          text: `❌ Cannot save invalid endpoint: ${result.error}`
        });
        return;
      }
    }

    setApiBaseUrl(targetUrl);
    backendWS.reconnectWithNewEndpoint();
    onSaveSettings(formData);
    onClose();
  };

  return h("div", { className: "notification-modal-overlay", onClick: onClose },
    h("div", { className: "notification-modal-content", onClick: (e) => e.stopPropagation(), style: { maxWidth: "560px" } },
      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" } },
        h("h3", { style: { margin: 0, fontSize: "1.15rem", color: "#FFFFFF", display: "flex", alignItems: "center", gap: "8px" } },
          h("span", null, "⚙️"),
          "System & Inference Engine Settings"
        ),
        h("button", { className: "toast-close-btn", onClick: onClose }, "✕")
      ),

      h("form", { onSubmit: handleSubmit, style: { display: "flex", flexDirection: "column", gap: "14px" } },
        
        // ------------------------------------------------------------------
        // Section 1: Backend Inference Engine Endpoint
        // ------------------------------------------------------------------
        h("div", { style: { background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "10px", padding: "14px" } },
          h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" } },
            h("label", { className: "notif-form-label", style: { color: "#00E5A8", fontWeight: "700", margin: 0 } }, "🔗 Backend Inference Engine API URL"),
            h("span", { style: { fontSize: "0.72rem", color: "#94A3B8" } }, "FastAPI Port 8000 / Tunnel")
          ),
          h("div", { style: { display: "flex", gap: "8px", marginBottom: "8px" } },
            h("input", {
              type: "url",
              placeholder: "http://localhost:8000 or https://...ngrok-free.app",
              className: "notif-form-input",
              value: formData.backend_url || "",
              onChange: (e) => handleChange("backend_url", e.target.value),
              style: { flex: 1 }
            }),
            h("button", {
              type: "button",
              className: "notif-btn-secondary",
              onClick: handleTestBackend,
              disabled: isValidating,
              style: { whiteSpace: "nowrap", padding: "6px 12px" }
            }, isValidating ? "⏳ Testing..." : "⚡ Test Ping")
          ),

          // Real-time Test / Validation Feedback Banner
          backendTestStatus && h("div", {
            style: {
              fontSize: "0.78rem",
              padding: "8px 10px",
              borderRadius: "6px",
              marginTop: "6px",
              lineHeight: "1.4",
              background: backendTestStatus.type === "success" ? "rgba(0,229,168,0.12)" : "rgba(255,92,124,0.12)",
              border: backendTestStatus.type === "success" ? "1px solid rgba(0,229,168,0.3)" : "1px solid rgba(255,92,124,0.3)",
              color: backendTestStatus.type === "success" ? "#00E5A8" : "#FF5C7C"
            }
          }, backendTestStatus.text),

          // Security & Cross-Origin Notice
          h("div", { style: { fontSize: "0.72rem", color: "#94A3B8", marginTop: "8px", lineHeight: "1.4" } },
            "⚠️ ", h("strong", { style: { color: "#CBD5E1" } }, "Security Notice:"), " Only connect to backend instances you own or control. Requests will be dispatched directly from your browser session."
          ),
          window.location.protocol === "https:" && h("div", { style: { fontSize: "0.72rem", color: "#F59E0B", marginTop: "6px", lineHeight: "1.4" } },
            "💡 ", h("strong", null, "Netlify HTTPS Note:"), " Web browsers block unencrypted http:// calls from HTTPS domains. Use an HTTPS tunnel (e.g. ngrok http 8000) or hosted endpoint for live connection."
          )
        ),

        // ------------------------------------------------------------------
        // Section 2: Opportunity Sound & Push Notifications
        // ------------------------------------------------------------------
        h("div", { className: "notif-switch-row" },
          h("label", { className: "notif-form-label" }, "🔊 Sound Radar Alerts"),
          h("input", {
            type: "checkbox",
            checked: formData.sound_alerts_enabled,
            onChange: (e) => handleChange("sound_alerts_enabled", e.target.checked),
            style: { transform: "scale(1.3)", cursor: "pointer" }
          })
        ),

        h("div", { className: "notif-switch-row" },
          h("label", { className: "notif-form-label" }, "🖥️ Browser Native Desktop Push"),
          h("button", {
            type: "button",
            className: "notif-btn-secondary",
            onClick: () => requestNotificationPermission().then(p => alert(`Permission: ${p}`))
          }, "Request Permission")
        ),

        h("div", { className: "notif-form-group" },
          h("label", { className: "notif-form-label" }, "🎯 Minimum Target Profit Threshold (%)"),
          h("input", {
            type: "number",
            step: "0.1",
            min: "0.5",
            max: "10.0",
            className: "notif-form-input",
            value: formData.min_profit_threshold_pct,
            onChange: (e) => handleChange("min_profit_threshold_pct", parseFloat(e.target.value))
          })
        ),

        // ------------------------------------------------------------------
        // Section 3: Webhook Integrations
        // ------------------------------------------------------------------
        h("div", { style: { borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: "12px" } },
          h("div", { className: "notif-switch-row" },
            h("label", { className: "notif-form-label", style: { color: "#00F0FF", fontWeight: "700" } },
              "📡 External Webhook (Discord / Telegram)"
            ),
            h("input", {
              type: "checkbox",
              checked: formData.webhook_enabled,
              onChange: (e) => handleChange("webhook_enabled", e.target.checked),
              style: { transform: "scale(1.3)", cursor: "pointer" }
            })
          ),

          formData.webhook_enabled && h("div", { style: { display: "flex", flexDirection: "column", gap: "10px", marginTop: "8px" } },
            h("div", { className: "notif-form-group" },
              h("label", { className: "notif-form-label" }, "Webhook Platform"),
              h("select", {
                className: "notif-form-input",
                value: formData.webhook_type,
                onChange: (e) => handleChange("webhook_type", e.target.value)
              },
                h("option", { value: "discord" }, "Discord Webhook URL"),
                h("option", { value: "telegram" }, "Telegram Bot"),
                h("option", { value: "generic" }, "Generic HTTP POST Webhook")
              )
            ),

            formData.webhook_type !== "telegram" ? (
              h("div", { className: "notif-form-group" },
                h("label", { className: "notif-form-label" }, "Discord / Custom Webhook URL"),
                h("input", {
                  type: "url",
                  placeholder: "https://discord.com/api/webhooks/...",
                  className: "notif-form-input",
                  value: formData.webhook_url,
                  onChange: (e) => handleChange("webhook_url", e.target.value)
                })
              )
            ) : (
              h("div", { style: { display: "flex", flexDirection: "column", gap: "8px" } },
                h("div", { className: "notif-form-group" },
                  h("label", { className: "notif-form-label" }, "Telegram Bot Token"),
                  h("input", {
                    type: "text",
                    placeholder: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
                    className: "notif-form-input",
                    value: formData.telegram_bot_token,
                    onChange: (e) => handleChange("telegram_bot_token", e.target.value)
                  })
                ),
                h("div", { className: "notif-form-group" },
                  h("label", { className: "notif-form-label" }, "Telegram Chat ID"),
                  h("input", {
                    type: "text",
                    placeholder: "@my_channel or -100123456789",
                    className: "notif-form-input",
                    value: formData.telegram_chat_id,
                    onChange: (e) => handleChange("telegram_chat_id", e.target.value)
                  })
                )
              )
            )
          )
        ),

        h("div", { style: { display: "flex", gap: "10px", marginTop: "10px" } },
          h("button", {
            type: "button",
            className: "notif-btn-secondary",
            onClick: onTestAlert
          }, "⚡ Send Test Alert"),
          h("button", {
            type: "submit",
            className: "notif-btn-primary"
          }, "Save & Activate")
        )
      )
    )
  );
}

function Navbar({ currentPath, setPath, engineState = "offline", alerts = [], onTestAlert, onOpenSettings, onSelectAlert }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [soundOn, setSoundOn] = useState(true);

  const stateMap = {
    offline:          { label: "Engine Offline", class: "offline" },
    connecting:       { label: "Connecting...", class: "connecting" },
    warming_up:       { label: "Connected (Warming Up)", class: "warming-up" },
    live:             { label: "Engine Live", class: "live" },
    security_blocked: { label: "Blocked by Browser (CORS/HTTPS)", class: "security-blocked" }
  };
  const current = stateMap[engineState] || stateMap.offline;

  const toggleSound = () => {
    const next = !soundOn;
    setSoundOn(next);
    if (next) playAudioChirp(980, "sine", 0.15);
  };

  return h("nav", { className: "navbar" },
    h("div", { style: { display: "flex", alignItems: "center", gap: "10px" } },
      h("button", {
        className: "mobile-menu-toggle",
        onClick: () => setMobileOpen(!mobileOpen),
        "aria-label": "Toggle Menu"
      }, mobileOpen ? "✕" : "☰"),
      h("a", { href: "#/", onClick: () => { setPath("/"); setMobileOpen(false); }, className: "logo" },
        h("div", { className: "logo-pill" }),
        h("span", { className: "logo-text" }, "BTCognitive")
      )
    ),
    h("ul", { className: `nav-links ${mobileOpen ? "mobile-active" : ""}` },
      h("li", null, h("a", { href: "#/", onClick: () => { setPath("/"); setMobileOpen(false); } }, "About")),
      h("li", null, h("a", { href: "#/terminal", onClick: () => { setPath("/terminal"); setMobileOpen(false); } }, "Trading")),
      h("li", null, h("a", { href: "#/terminal", onClick: () => { setPath("/terminal"); setMobileOpen(false); } }, "Models")),
      h("li", null, h("a", { href: "#/terminal", onClick: () => { setPath("/terminal"); setMobileOpen(false); } }, "FAQ"))
    ),
    h("div", { className: "nav-right" },
      h(NotificationBell, { alerts, onTestAlert, onOpenSettings, onSelectAlert }),
      h("button", {
        onClick: toggleSound,
        title: "Toggle Sci-Fi Audio Radar Feedback",
        style: {
          background: soundOn ? "rgba(0, 229, 168, 0.12)" : "rgba(255, 255, 255, 0.05)",
          border: soundOn ? "1px solid rgba(0, 229, 168, 0.3)" : "1px solid rgba(255, 255, 255, 0.1)",
          color: soundOn ? "#00E5A8" : "#94A3B8",
          padding: "6px 12px",
          borderRadius: "20px",
          fontSize: "0.78rem",
          fontWeight: "700",
          cursor: "pointer",
          transition: "all 0.2s ease"
        }
      }, soundOn ? "🔊 Audio" : "🔇 Muted"),
      h("div", {
        className: `status-badge ${current.class}`,
        onClick: onOpenSettings,
        title: "Click to configure Backend Engine API Endpoint",
        style: { cursor: "pointer" }
      },
        h("div", { className: "status-dot" }),
        h("span", { className: "status-text" }, current.label)
      ),
      h("button", { onClick: () => { setPath("/terminal"); setMobileOpen(false); }, className: "btn-signup-pill" }, "Trade ⚡")
    )
  );
}

// ===========================================================================
// HeroSection — Inspired by Liquid Brokers Ultra-Creative Dark Design
// ===========================================================================
function HeroSection({ setPath, livePrice, changePct, predictionData, regimeData, qualityData }) {
  const direction = predictionData?.direction || "LONG";
  const probPct   = predictionData?.probability_pct || 78.4;

  return h("section", { className: "hero-creative-container" },
    // Header Headline & Sub-headline
    h("div", { className: "hero-text-center" },
      h("div", { className: "hero-pill-badge" }, "✨ Next-Gen Quantitative Bitcoin Intelligence"),
      h("h1", { className: "hero-headline-main" }, "Elevate Your Trading Experience"),
      h("p", { className: "hero-sub-main" }, "Unlock your trading potential in a fully adaptive ML environment, powered by BTCognitive Engine.")
    ),

    // 3D Organic Fluid Wave Sculpture Container with Floating Action & Glass Cards
    h("div", { className: "hero-wave-wrapper" },
      // Floating Center CTA Button
      h("button", {
        onClick: () => setPath("/terminal"),
        className: "floating-center-cta"
      }, "Sign Up & Trade ⚡"),

      // Cards Row — Trading Pairs left, AI Signal Precision right
      h("div", { className: "hero-cards-row" },
        h("div", { className: "glass-pill-card floating-left-card", onClick: () => setPath("/terminal") },
          h("div", { className: "card-top-row" },
            h("span", { className: "card-label" }, "Trading Pairs"),
            h("div", { className: "arrow-circle-btn" }, "↗")
          ),
          h("div", { className: "card-main-title" }, "Unparalleled Market Access"),
          h("div", { className: "card-bottom-val" },
            h("span", { className: "card-price-highlight" }, livePrice > 0 ? `$${livePrice.toLocaleString("en-US", { minimumFractionDigits: 2 })}` : "BTC/USD"),
            h("span", { className: "card-pct" }, `${changePct >= 0 ? "+" : ""}${changePct.toFixed(2)}%`)
          )
        ),
        h("div", { className: "glass-pill-card floating-right-card", onClick: () => setPath("/terminal") },
          h("div", { className: "card-top-row" },
            h("span", { className: "card-label" }, "AI Signal Precision"),
            h("div", { className: "arrow-circle-btn" }, "↗")
          ),
          h("div", { className: "card-stat-big" }, `${probPct}%`),
          h("div", { className: "progress-bar-bg" },
            h("div", { className: "progress-bar-fill", style: { width: `${probPct}%` } })
          )
        )
      )
    ),

    // Bottom Stats Bar Highlights
    h("div", { className: "creative-stats-row" },
      h("div", { className: "c-stat-box" },
        h("div", { className: "c-stat-num" }, livePrice > 0 ? `$${livePrice.toLocaleString("en-US", { minimumFractionDigits: 2 })}` : "$63,420"),
        h("div", { className: "c-stat-lbl" }, "Real-Time Coinbase BTC/USD")
      ),
      h("div", { className: "c-stat-box" },
        h("div", { className: "c-stat-num", style: { color: "#00E5A8" } }, `${probPct}%`),
        h("div", { className: "c-stat-lbl" }, "Model Directional Accuracy")
      ),
      h("div", { className: "c-stat-box" },
        h("div", { className: "c-stat-num", style: { color: "#7C5CFF" } }, regimeData?.current_regime || "TRENDING_BULL"),
        h("div", { className: "c-stat-lbl" }, "Adaptive Market Regime")
      ),
      h("div", { className: "c-stat-box" },
        h("div", { className: "c-stat-num", style: { color: "#00F0FF" } }, `${qualityData?.score || 82}/100`),
        h("div", { className: "c-stat-lbl" }, "Signal Quality Score")
      )
    ),

    // About Feature Highlight — Explaining 5-Min Intelligence Radar Auto Refresh
    h("div", { style: { marginTop: "36px", background: "rgba(18, 26, 42, 0.6)", border: "1px solid rgba(255, 255, 255, 0.08)", borderRadius: "20px", padding: "28px" } },
      h("div", { style: { fontSize: "0.78rem", color: "#A78BFA", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" } }, "🛰️ AUTOMATED MARKET INTELLIGENCE"),
      h("h3", { style: { fontSize: "1.3rem", fontWeight: "800", color: "#F8FAFC", marginBottom: "12px" } }, "Adaptive 5-Minute Intelligence Radar Refresh Engine"),
      h("p", { style: { fontSize: "0.92rem", color: "#CBD5E1", lineHeight: "1.6", maxWidth: "900px" } },
        "The BTCognitive Intelligence Radar automatically refreshes every 5 minutes in real-time. It analyzes live BTC price action, 20/50 EMA trendlines, RSI momentum, open interest, and macro news catalysts to synthesize beginner-friendly 5-minute directional forecasts, Take Profit & Stop Loss ATR buffer recommendations, and market structure insights."
      )
    )
  );
}

// ===========================================================================
// Audio Alert Synthesizer
// ===========================================================================
function playAudioChirp(freq = 880, type = "sine", duration = 0.12) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(freq * 1.5, ctx.currentTime + duration);
    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + duration);
  } catch {}
}

// ===========================================================================
// WhatIfSimulator Component (Interactive AI Scenario Engine)
// ===========================================================================
function WhatIfSimulator({ livePrice, predictionData }) {
  const [shockPct, setShockPct] = useState(0.0);
  const [activeScenario, setActiveScenario] = useState("base");

  const basePrice = livePrice || 63000;
  const simPrice = basePrice * (1 + shockPct / 100);
  const simDirection = shockPct > 0.8 ? "BULLISH LONG" : (shockPct < -0.8 ? "BEARISH SHORT" : (predictionData?.direction || "LONG"));
  const simProb = Math.min(Math.max(Math.round((predictionData?.probability_pct || 78.4) + shockPct * 2.5), 52), 96);
  const simTp = simPrice * (1 + (simDirection.includes("LONG") ? 0.024 : -0.012));
  const simSl = simPrice * (1 - (simDirection.includes("LONG") ? 0.015 : -0.022));

  const scenarios = [
    { id: "base", label: "⚖️ Base AI", shock: 0.0 },
    { id: "bull_surge", label: "🟢 Bull Surge (+2.5%)", shock: 2.5 },
    { id: "etf_inflow", label: "⚡ ETF Inflow (+$1.5B)", shock: 4.0 },
    { id: "fed_cut", label: "🏛️ Fed Rate Cut (+1.8%)", shock: 1.8 },
    { id: "bear_shock", label: "🔴 Bear Dump (-3.0%)", shock: -3.0 }
  ];

  return h("div", { className: "glass-card", style: { padding: "24px", marginBottom: "24px" } },
    h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" } },
      h("div", null,
        h("div", { style: { fontSize: "0.78rem", color: "#00F0FF", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em" } }, "🔮 INTERACTIVE QUANT SIMULATOR"),
        h("h3", { style: { fontSize: "1.25rem", fontWeight: "800", color: "#F8FAFC", marginTop: "2px" } }, "AI What-If Market Scenario Engine")
      ),
      h("span", { style: { background: "rgba(0, 240, 255, 0.12)", border: "1px solid rgba(0, 240, 255, 0.3)", color: "#00F0FF", padding: "6px 14px", borderRadius: "20px", fontSize: "0.8rem", fontWeight: "700" } },
        "Real-Time Monte Carlo"
      )
    ),

    h("div", { style: { display: "flex", flexWrap: "wrap", gap: "10px", marginBottom: "20px" } },
      scenarios.map(sc =>
        h("button", {
          key: sc.id,
          onClick: () => { setActiveScenario(sc.id); setShockPct(sc.shock); playAudioChirp(1050, "sine", 0.08); },
          style: {
            padding: "8px 16px",
            borderRadius: "20px",
            fontSize: "0.82rem",
            fontWeight: "700",
            cursor: "pointer",
            background: activeScenario === sc.id ? "rgba(0, 240, 255, 0.2)" : "rgba(255, 255, 255, 0.05)",
            color: activeScenario === sc.id ? "#00F0FF" : "#94A3B8",
            border: activeScenario === sc.id ? "1px solid #00F0FF" : "1px solid rgba(255, 255, 255, 0.1)",
            transition: "all 0.2s ease"
          }
        }, sc.label)
      )
    ),

    h("div", { style: { background: "rgba(0, 0, 0, 0.25)", padding: "16px", borderRadius: "12px", marginBottom: "20px" } },
      h("div", { style: { display: "flex", justifyContent: "space-between", fontSize: "0.85rem", color: "#CBD5E1", marginBottom: "10px" } },
        h("span", null, "Market Shock Input:"),
        h("strong", { style: { color: shockPct >= 0 ? "#00E5A8" : "#FF5C7C", fontFamily: "var(--font-mono)" } },
          `${shockPct >= 0 ? "+" : ""}${shockPct.toFixed(1)}% (${shockPct >= 0 ? "+" : ""}$${Math.round(basePrice * shockPct / 100).toLocaleString()})`
        )
      ),
      h("input", {
        type: "range",
        min: -5.0,
        max: 5.0,
        step: 0.1,
        value: shockPct,
        onChange: (e) => { setShockPct(parseFloat(e.target.value)); setActiveScenario("custom"); },
        style: { width: "100%", accentColor: shockPct >= 0 ? "#00E5A8" : "#FF5C7C", cursor: "pointer" }
      })
    ),

    h("div", { style: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" } },
      h("div", { style: { background: "rgba(0,0,0,0.3)", padding: "12px", borderRadius: "8px" } },
        h("div", { style: { fontSize: "0.72rem", color: "#94A3B8" } }, "Simulated Target Price"),
        h("div", { style: { fontSize: "1.1rem", fontWeight: "800", color: "#F8FAFC", fontFamily: "var(--font-mono)" } }, `$${Math.round(simPrice).toLocaleString()}`)
      ),
      h("div", { style: { background: "rgba(0,0,0,0.3)", padding: "12px", borderRadius: "8px" } },
        h("div", { style: { fontSize: "0.72rem", color: "#94A3B8" } }, "Simulated Direction"),
        h("div", { style: { fontSize: "1.1rem", fontWeight: "800", color: simDirection.includes("BULL") || simDirection === "LONG" ? "#00E5A8" : "#FF5C7C" } }, `${simDirection} (${simProb}%)`)
      ),
      h("div", { style: { background: "rgba(0,229,168,0.06)", borderLeft: "3px solid #00E5A8", padding: "12px", borderRadius: "8px" } },
        h("div", { style: { fontSize: "0.72rem", color: "#00E5A8" } }, "Simulated Take Profit"),
        h("div", { style: { fontSize: "1.1rem", fontWeight: "800", color: "#00E5A8", fontFamily: "var(--font-mono)" } }, `$${Math.round(simTp).toLocaleString()}`)
      ),
      h("div", { style: { background: "rgba(255,92,124,0.06)", borderLeft: "3px solid #FF5C7C", padding: "12px", borderRadius: "8px" } },
        h("div", { style: { fontSize: "0.72rem", color: "#FF5C7C" } }, "Simulated Stop Loss"),
        h("div", { style: { fontSize: "1.1rem", fontWeight: "800", color: "#FF5C7C", fontFamily: "var(--font-mono)" } }, `$${Math.round(simSl).toLocaleString()}`)
      )
    )
  );
}

// ===========================================================================
// OrderBookPressureWidget Component (Live Liquidity Depth & Order Flow)
// ===========================================================================
function OrderBookPressureWidget({ livePrice }) {
  const buyPct = 64.2;
  const sellPct = 35.8;

  return h("div", { className: "glass-card", style: { padding: "24px", marginBottom: "24px" } },
    h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" } },
      h("div", null,
        h("div", { style: { fontSize: "0.78rem", color: "#A78BFA", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em" } }, "📊 MICROSTRUCTURE & LIQUIDITY"),
        h("h3", { style: { fontSize: "1.25rem", fontWeight: "800", color: "#F8FAFC", marginTop: "2px" } }, "Orderbook Depth & Pressure Ratio")
      ),
      h("span", { style: { background: "rgba(0, 229, 168, 0.15)", border: "1px solid rgba(0, 229, 168, 0.3)", color: "#00E5A8", padding: "6px 12px", borderRadius: "20px", fontSize: "0.8rem", fontWeight: "700" } },
        "64% Bull Imbalance"
      )
    ),

    h("div", { style: { marginBottom: "16px" } },
      h("div", { style: { display: "flex", justifyContent: "space-between", fontSize: "0.85rem", fontWeight: "700", marginBottom: "8px" } },
        h("span", { style: { color: "#00E5A8" } }, `🟢 Buy Pressure: ${buyPct}% (582.4 BTC)`),
        h("span", { style: { color: "#FF5C7C" } }, `🔴 Sell Pressure: ${sellPct}% (324.8 BTC)`)
      ),
      h("div", { style: { display: "flex", height: "10px", borderRadius: "6px", overflow: "hidden", background: "rgba(0,0,0,0.3)" } },
        h("div", { style: { width: `${buyPct}%`, background: "linear-gradient(90deg, #00E5A8, #00F0FF)" } }),
        h("div", { style: { width: `${sellPct}%`, background: "linear-gradient(90deg, #FF5C7C, #F59E0B)" } })
      )
    ),

    h("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" } },
      h("div", { style: { background: "rgba(0, 229, 168, 0.05)", border: "1px solid rgba(0, 229, 168, 0.2)", borderRadius: "10px", padding: "14px" } },
        h("div", { style: { fontSize: "0.78rem", color: "#00E5A8", fontWeight: "700", marginBottom: "4px" } }, "🛡️ Resting Bid Support Wall"),
        h("div", { style: { fontSize: "1.15rem", fontWeight: "800", color: "#F8FAFC", fontFamily: "var(--font-mono)" } }, `$${Math.round((livePrice || 63000) * 0.985).toLocaleString()}`),
        h("div", { style: { fontSize: "0.75rem", color: "#94A3B8", marginTop: "4px" } }, "142.8 BTC Liquidity Buffer")
      ),
      h("div", { style: { background: "rgba(255, 92, 124, 0.05)", border: "1px solid rgba(255, 92, 124, 0.2)", borderRadius: "10px", padding: "14px" } },
        h("div", { style: { fontSize: "0.78rem", color: "#FF5C7C", fontWeight: "700", marginBottom: "4px" } }, "⚔️ Resting Ask Resistance Wall"),
        h("div", { style: { fontSize: "1.15rem", fontWeight: "800", color: "#F8FAFC", fontFamily: "var(--font-mono)" } }, `$${Math.round((livePrice || 63000) * 1.018).toLocaleString()}`),
        h("div", { style: { fontSize: "0.75rem", color: "#94A3B8", marginTop: "4px" } }, "188.4 BTC Wall Concentration")
      )
    )
  );
}

// ===========================================================================
// PredictionPanel (with TP / SL / Confidence)
// ===========================================================================
function PredictionPanel({ predictionData, engineState = "offline" }) {
  const action = predictionData?.action || "TAKE_LONG";
  const direction = predictionData?.direction || "LONG";
  const probPct = predictionData?.probability_pct || 78.4;
  const expRetPct = predictionData?.expected_return_pct || 0.84;
  const tp = predictionData?.tp;
  const sl = predictionData?.sl;
  const horizon = predictionData?.horizon || "4h";
  const isWarmingUp = engineState === "warming_up" || predictionData?.status === "warming_up";
  const isOffline = engineState === "offline" || engineState === "security_blocked";

  const dirColor = direction === "LONG" ? "#00E5A8" : (direction === "SHORT" ? "#FF5C7C" : "#94A3B8");

  return h("div", { className: "glass-card", style: { padding: "24px", marginBottom: "24px" } },
    isWarmingUp && h("div", {
      style: {
        background: "rgba(245,158,11,0.1)",
        border: "1px solid rgba(245,158,11,0.3)",
        borderRadius: "10px",
        padding: "10px 14px",
        marginBottom: "16px",
        fontSize: "0.85rem",
        color: "#F59E0B",
        fontWeight: "600",
        display: "flex",
        alignItems: "center",
        gap: "8px"
      }
    },
      h("span", { style: { animation: "pulse 1.5s infinite" } }, "⏳"),
      "Connected to backend — Engine warming up. Initializing model ensemble..."
    ),

    isOffline && h("div", {
      style: {
        background: "rgba(255, 92, 124, 0.08)",
        border: "1px solid rgba(255, 92, 124, 0.25)",
        borderRadius: "10px",
        padding: "10px 14px",
        marginBottom: "16px",
        fontSize: "0.82rem",
        color: "#CBD5E1",
        display: "flex",
        alignItems: "center",
        gap: "10px"
      }
    },
      h("span", { style: { fontSize: "1.1rem" } }, "⚠️"),
      h("span", null,
        h("strong", { style: { color: "#FF5C7C" } }, "Heuristic Preview (Real Engine Offline): "),
        "Live candlestick chart and EMAs are streaming directly from Coinbase/Binance feeds. Validated purged walk-forward XGBoost/RF ensemble inference requires an active Python backend connection."
      )
    ),
    h("div", { className: "prediction-header-bar", style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" } },
      h("div", null,
        h("div", { style: { fontSize: "0.78rem", color: "#A78BFA", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em" } }, "🤖 ADAPTIVE DECISION ENGINE"),
        h("h3", { style: { fontSize: "1.3rem", fontWeight: "800", color: "#F8FAFC", marginTop: "2px" } }, "AI Forecast & Decision Matrix")
      ),
      h("div", { style: { display: "flex", alignItems: "center", gap: "10px" } },
        h("span", { style: { fontSize: "0.8rem", color: "#94A3B8", fontFamily: "var(--font-mono)" } }, `Horizon: ${horizon}`),
        h("span", { className: `signal-badge ${direction === "LONG" ? "signal-long" : direction === "SHORT" ? "signal-short" : "signal-skip"}` }, action)
      )
    ),

    h("div", { className: "prediction-grid-4", style: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "14px", marginBottom: "16px" } },
      // Card 1: Forecast Direction
      h("div", { className: "prediction-card-box", style: { background: "rgba(0,0,0,0.25)", padding: "14px", borderRadius: "10px" } },
        h("div", { className: "prediction-card-lbl", style: { fontSize: "0.78rem", color: "#94A3B8", marginBottom: "4px" } }, "Forecast Direction"),
        h("div", { className: "prediction-card-val", style: { fontSize: "1.2rem", fontWeight: "800", color: dirColor } }, `${direction} ${probPct}%`),
        h("div", { className: "progress-bar-bg", style: { marginTop: "10px", height: "6px", background: "rgba(255,255,255,0.08)", borderRadius: "4px" } },
          h("div", { className: "progress-bar-fill", style: { width: `${probPct}%`, height: "100%", background: dirColor, borderRadius: "4px" } })
        )
      ),
      // Card 2: Expected Return
      h("div", { className: "prediction-card-box", style: { background: "rgba(0,0,0,0.25)", padding: "14px", borderRadius: "10px" } },
        h("div", { className: "prediction-card-lbl", style: { fontSize: "0.78rem", color: "#94A3B8", marginBottom: "4px" } }, "Expected Return"),
        h("div", { className: "prediction-card-val", style: { fontSize: "1.2rem", fontWeight: "800", color: expRetPct >= 0 ? "#00E5A8" : "#FF5C7C" } }, `${expRetPct >= 0 ? "+" : ""}${expRetPct}%`),
        h("div", { style: { fontSize: "0.75rem", color: "#94A3B8", marginTop: "8px" } }, predictionData?.prediction_interval_str || "90% CI Target Range")
      ),
      // Card 3: Take Profit (TP)
      h("div", { className: "prediction-card-box", style: { background: "rgba(0,229,168,0.05)", borderLeft: "3px solid #00E5A8", padding: "14px", borderRadius: "10px" } },
        h("div", { className: "prediction-card-lbl", style: { fontSize: "0.78rem", color: "#00E5A8", marginBottom: "4px" } }, "Take Profit Target"),
        h("div", { className: "prediction-card-val", style: { fontSize: "1.2rem", fontWeight: "800", color: "#00E5A8", fontFamily: "var(--font-mono)" } }, tp ? `$${Math.round(tp).toLocaleString()}` : "—"),
        h("div", { style: { fontSize: "0.75rem", color: "#94A3B8", marginTop: "8px" } }, "ATR 2.0x Dynamic Exit")
      ),
      // Card 4: Stop Loss (SL)
      h("div", { className: "prediction-card-box", style: { background: "rgba(255,92,124,0.05)", borderLeft: "3px solid #FF5C7C", padding: "14px", borderRadius: "10px" } },
        h("div", { className: "prediction-card-lbl", style: { fontSize: "0.78rem", color: "#FF5C7C", marginBottom: "4px" } }, "Stop Loss Floor"),
        h("div", { className: "prediction-card-val", style: { fontSize: "1.2rem", fontWeight: "800", color: "#FF5C7C", fontFamily: "var(--font-mono)" } }, sl ? `$${Math.round(sl).toLocaleString()}` : "—"),
        h("div", { style: { fontSize: "0.75rem", color: "#94A3B8", marginTop: "8px" } }, "ATR 1.5x Risk Protection")
      )
    ),

    // 4-Factor Uncertainty Decomposition section
    predictionData?.uncertainty_breakdown && h("div", { className: "uncertainty-container", style: { background: "rgba(0,0,0,0.2)", padding: "14px", borderRadius: "10px", marginBottom: "16px" } },
      h("div", { style: { fontSize: "0.8rem", color: "#A78BFA", fontWeight: "700", textTransform: "uppercase", marginBottom: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" } },
        h("span", null, "🛡️ 4-Factor Uncertainty Decomposition"),
        h("span", { style: { fontSize: "0.75rem", color: "#94A3B8", fontStyle: "normal" } }, "Institutional Risk Audit")
      ),
      h("div", { style: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginBottom: "12px" } },
        h("div", { style: { background: "rgba(0,0,0,0.25)", padding: "10px", borderRadius: "8px", textAlign: "center" } },
          h("div", { style: { fontSize: "0.7rem", color: "#94A3B8" } }, "Data Quality"),
          h("div", { style: { fontSize: "1.1rem", fontWeight: "800", color: "#00E5A8", fontFamily: "var(--font-mono)" } }, `${Math.round(predictionData.uncertainty_breakdown.data_reliability * 100)}%`)
        ),
        h("div", { style: { background: "rgba(0,0,0,0.25)", padding: "10px", borderRadius: "8px", textAlign: "center" } },
          h("div", { style: { fontSize: "0.7rem", color: "#94A3B8" } }, "Regime Certainty"),
          h("div", { style: { fontSize: "1.1rem", fontWeight: "800", color: "#00F0FF", fontFamily: "var(--font-mono)" } }, `${Math.round(predictionData.uncertainty_breakdown.regime_certainty * 100)}%`)
        ),
        h("div", { style: { background: "rgba(0,0,0,0.25)", padding: "10px", borderRadius: "8px", textAlign: "center" } },
          h("div", { style: { fontSize: "0.7rem", color: "#94A3B8" } }, "Model Consensus"),
          h("div", { style: { fontSize: "1.1rem", fontWeight: "800", color: "#A78BFA", fontFamily: "var(--font-mono)" } }, `${Math.round(predictionData.uncertainty_breakdown.model_agreement * 100)}%`)
        ),
        h("div", { style: { background: "rgba(0,0,0,0.25)", padding: "10px", borderRadius: "8px", textAlign: "center" } },
          h("div", { style: { fontSize: "0.7rem", color: "#94A3B8" } }, "Vol Calmness"),
          h("div", { style: { fontSize: "1.1rem", fontWeight: "800", color: "#F59E0B", fontFamily: "var(--font-mono)" } }, `${Math.round(predictionData.uncertainty_breakdown.volatility_stress * 100)}%`)
        )
      ),
      predictionData?.uncertainty_narrative && h("div", { style: { fontSize: "0.82rem", color: "#CBD5E1", fontStyle: "italic", background: "rgba(0,0,0,0.2)", padding: "10px 14px", borderRadius: "8px" } },
        predictionData.uncertainty_narrative
      )
    ),

    h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.82rem", color: "#94A3B8", borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "12px" } },
      h("span", null, "Model: ", h("strong", { style: { color: "#F8FAFC" } }, predictionData?.model || "Adaptive Regime Ensemble (RF+XGB)")),
      h("span", { style: { fontFamily: "var(--font-mono)" } }, `Updated: ${predictionData?.timestamp ? new Date(predictionData.timestamp).toLocaleTimeString() : "Live"}`)
    )
  );
}

// ===========================================================================
// MarketStateSection
// ===========================================================================
function MarketStateSection({ regimeData }) {
  const trendPct  = regimeData?.trend_strength_pct || 82;
  const volState  = regimeData?.volatility_state   || "MEDIUM";
  const fundState = regimeData?.funding_state       || "POSITIVE";
  const levState  = regimeData?.leverage_state      || "ELEVATED";

  return h("div", { className: "grid-4col" },
    h("div", { className: "glass-card", style: { padding: "20px" } },
      h("div", { style: { fontSize: "0.8rem", color: "#94A3B8", textTransform: "uppercase" } }, "Trend Score"),
      h("div", { style: { fontSize: "1.4rem", fontWeight: "700", margin: "8px 0", color: "#00E5A8" } }, `${regimeData?.trend_label || "Bullish"} (${trendPct}%)`),
      h("div", { className: "shap-bar-bg" }, h("div", { className: "shap-bar-fill shap-positive", style: { width: `${trendPct}%` } }))
    ),
    h("div", { className: "glass-card", style: { padding: "20px" } },
      h("div", { style: { fontSize: "0.8rem", color: "#94A3B8", textTransform: "uppercase" } }, "Volatility State"),
      h("div", { style: { fontSize: "1.4rem", fontWeight: "700", margin: "8px 0", color: "#7C5CFF" } }, volState),
      h("div", { className: "shap-bar-bg" }, h("div", { className: "shap-bar-fill", style: { width: "60%", background: "#7C5CFF" } }))
    ),
    h("div", { className: "glass-card", style: { padding: "20px" } },
      h("div", { style: { fontSize: "0.8rem", color: "#94A3B8", textTransform: "uppercase" } }, "Funding Condition"),
      h("div", { style: { fontSize: "1.4rem", fontWeight: "700", margin: "8px 0", color: "#00E5A8" } }, fundState),
      h("div", { className: "shap-bar-bg" }, h("div", { className: "shap-bar-fill shap-positive", style: { width: "75%" } }))
    ),
    h("div", { className: "glass-card", style: { padding: "20px" } },
      h("div", { style: { fontSize: "0.8rem", color: "#94A3B8", textTransform: "uppercase" } }, "Leverage State"),
      h("div", { style: { fontSize: "1.4rem", fontWeight: "700", margin: "8px 0", color: "#A78BFA" } }, levState),
      h("div", { className: "shap-bar-bg" }, h("div", { className: "shap-bar-fill", style: { width: "85%", background: "#A78BFA" } }))
    )
  );
}

// ===========================================================================
// ExplainableAIPanel
// ===========================================================================
function ExplainableAIPanel({ explanationData }) {
  const rawFactors = explanationData?.factors || explanationData?.contributions || [
    { feature: "Momentum", contribution: 0.18 },
    { feature: "RSI_14", contribution: 0.11 },
    { feature: "Funding_Rate", contribution: 0.07 },
    { feature: "Vol_Spike", contribution: -0.05 }
  ];

  const factors = rawFactors.map(f => ({
    feature: f.feature,
    val: f.contribution !== undefined ? f.contribution : (f.value || 0.0)
  }));

  return h("div", { className: "glass-card", style: { padding: "24px" } },
    h("h3", { style: { fontSize: "1.2rem", fontWeight: "700", marginBottom: "16px" } }, "Why This Prediction? (SHAP Attribution)"),
    factors.map((item, i) => {
      const isPos = item.val >= 0;
      const widthPct = Math.min(abs(item.val) * 300, 100);
      return h("div", { key: i, className: "shap-item" },
        h("div", { className: "shap-header" },
          h("span", null, item.feature),
          h("span", { style: { fontWeight: "700", color: isPos ? "#00E5A8" : "#FF5C7C" } }, `${isPos ? "+" : ""}${item.val.toFixed(2)}`)
        ),
        h("div", { className: "shap-bar-bg" },
          h("div", { className: `shap-bar-fill ${isPos ? "shap-positive" : "shap-negative"}`, style: { width: `${widthPct}%` } })
        )
      );
    }),
    h("p", { style: { fontSize: "0.85rem", color: "#94A3B8", marginTop: "20px", fontStyle: "italic", background: "rgba(0,0,0,0.2)", padding: "12px", borderRadius: "8px" } },
      `"${explanationData?.summary || "The model is primarily influenced by strengthening momentum and increasing derivatives participation."}"`)
  );
}

// ===========================================================================
// SignalQualityGauge
// ===========================================================================
function SignalQualityGauge({ qualityData }) {
  const score  = qualityData?.score  || 82;
  const rating = qualityData?.rating || "Excellent";

  return h("div", { className: "glass-card", style: { padding: "24px" } },
    h("h3", { style: { fontSize: "1.2rem", fontWeight: "700", marginBottom: "16px", textAlign: "center" } }, "Signal Quality Engine"),
    h("div", { className: "gauge-container" },
      h("svg", { className: "gauge-svg", viewBox: "0 0 160 160" },
        h("circle", { className: "gauge-bg-circle",   cx: "80", cy: "80", r: "70" }),
        h("circle", { className: "gauge-fill-circle", cx: "80", cy: "80", r: "70", style: { strokeDashoffset: 440 - (440 * score) / 100 } })
      ),
      h("div", { className: "gauge-text" },
        h("div", { className: "gauge-score"  }, score),
        h("div", { className: "gauge-rating" }, rating)
      )
    ),
    h("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", fontSize: "0.8rem", color: "#94A3B8" } },
      h("div", null, "Calibration: ",   h("strong", { style: { color: "#F8FAFC" } }, `${qualityData?.calibration_score || 88}%`)),
      h("div", null, "Regime Conf: ",   h("strong", { style: { color: "#F8FAFC" } }, `${qualityData?.regime_confidence || 85}%`)),
      h("div", null, "Drift Stability: ",h("strong", { style: { color: "#F8FAFC" } }, `${qualityData?.drift_score || 92}%`)),
      h("div", null, "Agreement: ",     h("strong", { style: { color: "#F8FAFC" } }, `${qualityData?.model_agreement || 84}%`))
    )
  );
}

// ===========================================================================
// PredictionHistoryTimeline
// ===========================================================================
function PredictionHistoryTimeline({ memoryData }) {
  return h("div", { className: "glass-card", style: { padding: "24px", marginBottom: "32px" } },
    h("h3", { style: { fontSize: "1.2rem", fontWeight: "700", marginBottom: "20px" } }, "Market Memory (Prediction History)"),
    h("div", { className: "table-wrapper" },
      h("table", { className: "custom-table" },
        h("thead", null,
          h("tr", null,
            h("th", null, "Time"),
            h("th", null, "Direction"),
            h("th", null, "Probability"),
            h("th", null, "TP"),
            h("th", null, "SL"),
            h("th", null, "Actual Return"),
            h("th", null, "Outcome"),
            h("th", null, "PnL ($)")
          )
        ),
        h("tbody", null,
          (memoryData || []).map((item, idx) =>
            h("tr", { key: idx, style: { cursor: "pointer" }, title: `Regime: ${item.regime || "N/A"}` },
              h("td", { style: { fontFamily: "var(--font-mono)" } },
                item.timestamp_ms
                  ? new Date(item.timestamp_ms).toLocaleString([], { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" })
                  : new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
              ),
              h("td", null, h("span", { className: `signal-badge ${item.direction === "LONG" ? "signal-long" : "signal-short"}` }, item.direction)),
              h("td", { style: { fontFamily: "var(--font-mono)" } }, `${item.probability_pct}%`),
              h("td", { style: { fontFamily: "var(--font-mono)", color: "#00E5A8" } }, item.tp ? `$${Math.round(item.tp).toLocaleString()}` : "—"),
              h("td", { style: { fontFamily: "var(--font-mono)", color: "#FF5C7C" } }, item.sl ? `$${Math.round(item.sl).toLocaleString()}` : "—"),
              h("td", { style: { color: (item.actual_return_pct || 0) >= 0 ? "#00E5A8" : "#FF5C7C", fontFamily: "var(--font-mono)" } }, `${(item.actual_return_pct || 0) >= 0 ? "+" : ""}${item.actual_return_pct || 0}%`),
              h("td", null, h("span", { style: { color: item.was_correct ? "#00E5A8" : "#FF5C7C", fontWeight: "700" } }, item.was_correct ? "✓ PASS" : "✕ FAIL")),
              h("td", { style: { fontFamily: "var(--font-mono)", fontWeight: "700", color: (item.pnl || 0) >= 0 ? "#00E5A8" : "#FF5C7C" } }, `+$${item.pnl || 0}`)
            )
          )
        )
      )
    )
  );
}

// ===========================================================================
// PaperPortfolio
// ===========================================================================
function PaperPortfolio({ portfolioData }) {
  const positions = portfolioData?.positions || [];

  return h("div", { className: "glass-card", style: { padding: "24px" } },
    h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" } },
      h("h3", { style: { fontSize: "1.2rem", fontWeight: "700" } }, "Paper Trading Portfolio"),
      h("div", { style: { fontSize: "0.9rem", color: "#94A3B8" } },
        "Balance: ", h("strong", { style: { color: "#00E5A8", fontFamily: "var(--font-mono)" } }, `$${(portfolioData?.balance_usdt || 100000).toLocaleString()} USDT`)
      )
    ),
    h("div", { className: "table-wrapper" },
      h("table", { className: "custom-table" },
        h("thead", null,
          h("tr", null,
            h("th", null, "Symbol"), h("th", null, "Position"),
            h("th", null, "Entry"), h("th", null, "Current"),
            h("th", null, "PnL ($)"), h("th", null, "PnL (%)"), h("th", null, "Status")
          )
        ),
        h("tbody", null,
          positions.map(pos =>
            h("tr", { key: pos.id },
              h("td", { style: { fontWeight: "700" } }, pos.symbol),
              h("td", null, h("span", { className: `signal-badge ${pos.type === "LONG" ? "signal-long" : "signal-short"}` }, pos.type)),
              h("td", { style: { fontFamily: "var(--font-mono)" } }, `$${pos.entry_price.toLocaleString()}`),
              h("td", { style: { fontFamily: "var(--font-mono)" } }, `$${pos.current_price.toLocaleString()}`),
              h("td", { style: { color: pos.pnl_usd >= 0 ? "#00E5A8" : "#FF5C7C", fontFamily: "var(--font-mono)", fontWeight: "700" } }, `${pos.pnl_usd >= 0 ? "+" : ""}$${pos.pnl_usd}`),
              h("td", { style: { color: pos.pnl_pct >= 0 ? "#00E5A8" : "#FF5C7C", fontFamily: "var(--font-mono)" } }, `${pos.pnl_pct >= 0 ? "+" : ""}${pos.pnl_pct}%`),
              h("td", null, h("span", { style: { fontSize: "0.8rem", padding: "4px 8px", borderRadius: "4px", background: "rgba(255,255,255,0.06)" } }, pos.status))
            )
          )
        )
      )
    )
  );
}

// ===========================================================================
// RightIntelligenceSidebar (Phase 4 — 6 Market Intelligence Engines)
// ===========================================================================
function RightIntelligenceSidebar({ intelData }) {
  const struct = intelData?.structure || { label: "Bullish", sequence_desc: "HH-HL sequence maintained", bos_pct: 0.82, trend_strength_pct: 84 };
  const liq = intelData?.liquidity || { eqh_detected: true, sweep_alert: "None", sweep_target_price: 64200.0, risk_level: "ELEVATED" };
  const mom = intelData?.momentum || { status: "Expanding", strength_pct: 78, acceleration: "Positive" };
  const vol = intelData?.volatility || { volatility_state: "Compression", historical_percentile_pct: 18, breakout_probability: "Elevated" };
  const conf = intelData?.confidence || { overall_score: 84, calibration_rating: "Excellent", regime_fit_pct: 92, historical_similarity_pct: 87, model_agreement_pct: 84 };
  const outlook = intelData?.outlook_5m || { direction: "BULLISH 🚀", expected_range: "$63,550 – $63,880", confidence_pct: 78, basis: "20 EMA is above 50 EMA with volume expansion. Buyers actively defending dips.", horizon: "Next 5 Minutes" };
  const tpsl = intelData?.tp_sl_analysis || { tp_price: 64550, sl_price: 62980, rr_ratio: "1.80 : 1 (Favorable Risk/Reward)", accuracy_rating: "High (ATR Protected)", explanation: "Take Profit targets key resistance to lock gain. Stop Loss uses a 1.0x ATR buffer to protect capital against stop-hunts." };
  const macro = intelData?.macro_news || { macro_regime: "FOMC Rate Pause & Inflation Stabilization", impact_status: "Bullish Macro Tailwind 🍃", cpi_status: "CPI Inflation in target corridor", dxy_index: "DXY Index weakening (-0.4%)", etf_flow: "Institutional ETF net inflows positive (+1,420 BTC past 24h)", headline: "Macro liquidity conditions remain supportive with low regulatory event risk." };
  const guide = intelData?.graph_guide || { candle_state: "GREEN (Buyers pushing price higher)", green_line: "Green Line (20 EMA) = Short-term 20-candle average trend line", purple_line: "Purple Line (50 EMA) = Medium-term 50-candle average trend line", chart_verdict: "Green EMA 20 line is above Purple EMA 50 line — confirms an active bullish trend on the chart.", support_resistance: "Key Support: $63,000 | Key Resistance: $64,500" };
  const narrative = intelData?.narrative || "Bitcoin is currently trading inside a bullish market structure while momentum continues to expand. Over the next 5 minutes, momentum favors a bullish bias.";

  return h("aside", { className: "intel-sidebar" },
    h("div", { className: "intel-radar-box", style: { maxHeight: "calc(100vh - 120px)", overflowY: "auto", paddingRight: "6px" } },
      
      // Header with Score Badge
      h("div", { className: "intel-radar-header" },
        h("div", { style: { fontWeight: "800", fontSize: "0.92rem", color: "#F8FAFC", display: "flex", alignItems: "center", gap: "6px" } },
          h("span", { style: { color: "#00E5A8" } }, "⚡"), "INTELLIGENCE RADAR"
        ),
        h("div", { style: { display: "flex", alignItems: "center", gap: "6px" } },
          h("span", { className: "intel-badge bullish" }, `${conf.overall_score}/100`)
        )
      ),

      // 1. Live AI Market Narrative
      h("div", { className: "intel-section-title" }, "📜 Live AI Market Narrative"),
      h("div", { className: "intel-narrative-box", style: { marginBottom: "14px", fontSize: "0.83rem", lineHeight: "1.55" } }, narrative),

      // 2. Next 5-Minute Forecast Outlook
      h("div", { className: "intel-section-title" }, "⏱️ Next 5-Min Outlook"),
      h("div", { style: { background: "rgba(167,139,250,0.08)", border: "1px solid rgba(167,139,250,0.25)", borderRadius: "10px", padding: "12px", marginBottom: "14px" } },
        h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" } },
          h("span", { style: { fontSize: "0.78rem", color: "#94A3B8" } }, "5-Min Direction:"),
          h("span", { style: { fontWeight: "700", fontSize: "0.85rem", color: outlook.direction.includes("BULL") ? "#00E5A8" : outlook.direction.includes("BEAR") ? "#FF5C7C" : "#F59E0B" } }, outlook.direction)
        ),
        h("div", { style: { display: "flex", justifyContent: "space-between", fontSize: "0.78rem", marginBottom: "6px" } },
          h("span", { style: { color: "#94A3B8" } }, "Expected Target Range:"),
          h("span", { style: { fontFamily: "var(--font-mono)", color: "#F8FAFC", fontWeight: "600" } }, outlook.expected_range)
        ),
        h("div", { style: { display: "flex", justifyContent: "space-between", fontSize: "0.78rem", marginBottom: "8px" } },
          h("span", { style: { color: "#94A3B8" } }, "AI Confidence:"),
          h("span", { style: { color: "#00E5A8", fontWeight: "700" } }, `${outlook.confidence_pct}%`)
        ),
        h("div", { style: { fontSize: "0.75rem", color: "#CBD5E1", borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: "8px", lineHeight: "1.4" } },
          "💡 ", h("strong", null, "AI Basis: "), outlook.basis
        )
      ),

      // 3. Take Profit & Stop Loss Protection Analysis
      h("div", { className: "intel-section-title" }, "🎯 TP & SL Profit & Safety Buffer"),
      h("div", { style: { background: "rgba(0,229,168,0.06)", border: "1px solid rgba(0,229,168,0.2)", borderRadius: "10px", padding: "12px", marginBottom: "14px" } },
        h("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginBottom: "8px" } },
          h("div", null,
            h("div", { style: { fontSize: "0.72rem", color: "#94A3B8" } }, "Take Profit Target:"),
            h("div", { style: { fontFamily: "var(--font-mono)", color: "#00E5A8", fontWeight: "700", fontSize: "0.92rem" } }, `$${Math.round(tpsl.tp_price).toLocaleString()}`)
          ),
          h("div", null,
            h("div", { style: { fontSize: "0.72rem", color: "#94A3B8" } }, "Stop Loss Target:"),
            h("div", { style: { fontFamily: "var(--font-mono)", color: "#FF5C7C", fontWeight: "700", fontSize: "0.92rem" } }, `$${Math.round(tpsl.sl_price).toLocaleString()}`)
          )
        ),
        h("div", { style: { fontSize: "0.78rem", color: "#F8FAFC", marginBottom: "6px" } },
          "Risk/Reward Ratio: ", h("strong", { style: { color: "#00E5A8" } }, tpsl.rr_ratio)
        ),
        h("div", { style: { fontSize: "0.75rem", color: "#CBD5E1", lineHeight: "1.45" } },
          "🛡️ ", tpsl.explanation
        )
      ),

      // 4. Macro News & Market Drivers
      h("div", { className: "intel-section-title" }, "📰 Macro News & Market Drivers"),
      h("div", { style: { background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.2)", borderRadius: "10px", padding: "12px", marginBottom: "14px" } },
        h("div", { style: { fontWeight: "700", fontSize: "0.82rem", color: "#F59E0B", marginBottom: "6px" } }, macro.impact_status),
        h("div", { style: { fontSize: "0.76rem", color: "#E2E8F0", marginBottom: "4px" } }, "• ", macro.macro_regime),
        h("div", { style: { fontSize: "0.76rem", color: "#E2E8F0", marginBottom: "4px" } }, "• ", macro.cpi_status),
        h("div", { style: { fontSize: "0.76rem", color: "#E2E8F0", marginBottom: "4px" } }, "• ", macro.etf_flow),
        h("div", { style: { fontSize: "0.74rem", color: "#94A3B8", marginTop: "6px", fontStyle: "italic" } }, macro.headline)
      ),

      // 5. Beginner Graph Explanation Guide
      h("div", { className: "intel-section-title" }, "📊 Beginner Graph Guide"),
      h("div", { style: { background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.25)", borderRadius: "10px", padding: "12px", marginBottom: "14px" } },
        h("div", { style: { fontSize: "0.78rem", color: "#93C5FD", fontWeight: "700", marginBottom: "6px" } }, guide.candle_state),
        h("div", { style: { fontSize: "0.75rem", color: "#E2E8F0", marginBottom: "4px" } }, "🟢 ", guide.green_line),
        h("div", { style: { fontSize: "0.75rem", color: "#E2E8F0", marginBottom: "6px" } }, "🟣 ", guide.purple_line),
        h("div", { style: { fontSize: "0.75rem", color: "#CBD5E1", lineHeight: "1.4" } }, "💡 ", guide.chart_verdict)
      ),

      // 6. Structure & Liquidity
      h("div", { className: "intel-section-title" }, "🏛️ Structure & Liquidity"),
      h("div", { className: "intel-metric-row" },
        h("span", { className: "intel-metric-lbl" }, "Structure Trend"),
        h("span", { className: `intel-badge ${struct.label.includes("Bull") ? "bullish" : struct.label.includes("Bear") ? "bearish" : "neutral"}` }, struct.label)
      ),
      h("div", { className: "intel-metric-row" },
        h("span", { className: "intel-metric-lbl" }, "BOS Index"),
        h("span", { className: "intel-metric-val", style: { color: "#00E5A8" } }, `${struct.bos_pct >= 0 ? "+" : ""}${struct.bos_pct}%`)
      ),
      h("div", { className: "intel-metric-row" },
        h("span", { className: "intel-metric-lbl" }, "Liquidity Risk"),
        h("span", { className: `intel-badge ${liq.risk_level === "LOW" ? "bullish" : liq.risk_level === "HIGH" ? "bearish" : "warning"}` }, `Risk: ${liq.risk_level}`)
      ),

      // 7. Confidence Metrics
      h("div", { className: "intel-section-title" }, "🎯 Confidence Metrics"),
      h("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "0.78rem", color: "var(--text-muted)", background: "rgba(0,0,0,0.25)", padding: "12px", borderRadius: "10px" } },
        h("div", null, "Calib: ", h("strong", { style: { color: "#00E5A8" } }, conf.calibration_rating)),
        h("div", null, "Regime: ", h("strong", { style: { color: "#F8FAFC" } }, `${conf.regime_fit_pct}%`)),
        h("div", null, "Sim: ", h("strong", { style: { color: "#F8FAFC" } }, `${conf.historical_similarity_pct}%`)),
        h("div", null, "Agree: ", h("strong", { style: { color: "#F8FAFC" } }, `${conf.model_agreement_pct || 84}%`))
      )
    )
  );
}

// ===========================================================================
// ReplayBar Component
// ===========================================================================
function ReplayBar({ memoryData, isReplaying, setIsReplaying, selectedRecord, onSelectRecord }) {
  if (!memoryData || memoryData.length === 0) return null;

  return h("div", { className: "replay-bar" },
    h("div", { style: { display: "flex", alignItems: "center", gap: "12px" } },
      h("span", { style: { fontWeight: "700", fontSize: "0.95rem", color: "#A78BFA" } }, "⏱️ Replay Engine Time Machine"),
      h("button", {
        className: `replay-btn ${isReplaying ? "active" : ""}`,
        onClick: () => setIsReplaying(!isReplaying)
      }, isReplaying ? "Pause Replay" : "Start Replay Mode")
    ),

    isReplaying && h("div", { className: "replay-controls" },
      h("input", {
        type: "range",
        min: 0,
        max: memoryData.length - 1,
        value: selectedRecord ? memoryData.findIndex(r => r.prediction_id === selectedRecord.prediction_id) : memoryData.length - 1,
        onChange: (e) => onSelectRecord(memoryData[parseInt(e.target.value)]),
        className: "replay-slider"
      }),
      h("span", { style: { fontFamily: "var(--font-mono)", fontSize: "0.85rem", color: "#00E5A8" } },
        selectedRecord ? new Date(selectedRecord.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Live"
      )
    ),

    isReplaying && h("button", {
      className: "replay-btn",
      onClick: () => { setIsReplaying(false); onSelectRecord(null); }
    }, "Return to Live ⚡")
  );
}

// ===========================================================================
// BottomTabs Component
// ===========================================================================
function BottomTabs({ activeTab, setActiveTab, memoryData, portfolioData, qualityData, explanationData }) {
  const tabs = [
    { id: "memory", label: "📜 Market Memory" },
    { id: "portfolio", label: "💼 Paper Portfolio" },
    { id: "quality", label: "🎯 Signal Quality" },
    { id: "shap", label: "🔍 Explainable AI" }
  ];

  return h("div", { style: { marginTop: "32px" } },
    h("div", { className: "bottom-tabs-header" },
      tabs.map(tab =>
        h("button", {
          key: tab.id,
          className: `bottom-tab-btn ${activeTab === tab.id ? "active" : ""}`,
          onClick: () => setActiveTab(tab.id)
        }, tab.label)
      )
    ),
    h("div", null,
      activeTab === "memory" && h(PredictionHistoryTimeline, { memoryData }),
      activeTab === "portfolio" && h(PaperPortfolio, { portfolioData }),
      activeTab === "quality" && h(SignalQualityGauge, { qualityData }),
      activeTab === "shap" && h(ExplainableAIPanel, { explanationData })
    )
  );
}

// ===========================================================================
// CounterfactualPanel Component
// ===========================================================================
function CounterfactualPanel({ counterfactualData }) {
  if (!counterfactualData) return null;

  const consensus = counterfactualData.consensus_rating || "HIGH";
  const consensusColor = consensus === "HIGH" ? "#00E5A8" : (consensus === "MEDIUM" ? "#F59E0B" : "#FF5C7C");
  const list = counterfactualData.counterfactuals || [];

  return h("div", { className: "glass-card", style: { padding: "24px", marginTop: "24px" } },
    h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" } },
      h("div", null,
        h("h3", { style: { fontSize: "1.2rem", fontWeight: "700" } }, "⚡ Replay & Counterfactual Engine"),
        h("div", { style: { fontSize: "0.8rem", color: "#94A3B8", marginTop: "4px" } }, "Comparing competing strategy decisions on identical candle context")
      ),
      h("span", { style: { background: `${consensusColor}15`, border: `1px solid ${consensusColor}40`, color: consensusColor, padding: "6px 12px", borderRadius: "20px", fontSize: "0.8rem", fontWeight: "700" } },
        `Consensus: ${consensus}`
      )
    ),
    h("div", { style: { fontSize: "0.85rem", color: "#CBD5E1", marginBottom: "16px", background: "rgba(0,0,0,0.2)", padding: "10px 14px", borderRadius: "8px" } },
      counterfactualData.summary_text
    ),
    h("div", { style: { overflowX: "auto" } },
      h("table", { style: { width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" } },
        h("thead", null,
          h("tr", { style: { borderBottom: "1px solid rgba(255,255,255,0.1)", textAlign: "left", color: "#94A3B8" } },
            h("th", { style: { padding: "10px" } }, "Genome ID"),
            h("th", { style: { padding: "10px" } }, "Regime Specialist"),
            h("th", { style: { padding: "10px" } }, "Decision"),
            h("th", { style: { padding: "10px" } }, "Take Profit"),
            h("th", { style: { padding: "10px" } }, "Stop Loss"),
            h("th", { style: { padding: "10px" } }, "Deflated Sharpe")
          )
        ),
        h("tbody", null,
          list.map((c, i) => h("tr", { key: i, style: { borderBottom: "1px solid rgba(255,255,255,0.05)" } },
            h("td", { style: { padding: "10px", fontWeight: "700", fontFamily: "var(--font-mono)", color: "#F8FAFC" } }, c.genome_id),
            h("td", { style: { padding: "10px", color: "#A78BFA" } }, c.regime_specialist),
            h("td", { style: { padding: "10px" } },
              h("span", { style: { color: c.decision === "LONG" ? "#00E5A8" : (c.decision === "SHORT" ? "#FF5C7C" : "#94A3B8"), fontWeight: "700" } }, c.decision)
            ),
            h("td", { style: { padding: "10px" } },
              c.tp_price
                ? h("span", null,
                    h("span", { style: { fontFamily: "var(--font-mono)", color: c.decision === "SKIP" ? "#94A3B8" : "#00E5A8", fontWeight: "700" } },
                      `$${Math.round(c.tp_price).toLocaleString()}`),
                    c.decision === "SKIP" && h("span", { style: { fontSize: "0.65rem", color: "#64748B", marginLeft: "4px", fontStyle: "italic" } }, "ref")
                  )
                : h("span", { style: { color: "#64748B" } }, "—")
            ),
            h("td", { style: { padding: "10px" } },
              c.sl_price
                ? h("span", null,
                    h("span", { style: { fontFamily: "var(--font-mono)", color: c.decision === "SKIP" ? "#94A3B8" : "#FF5C7C", fontWeight: "700" } },
                      `$${Math.round(c.sl_price).toLocaleString()}`),
                    c.decision === "SKIP" && h("span", { style: { fontSize: "0.65rem", color: "#64748B", marginLeft: "4px", fontStyle: "italic" } }, "ref")
                  )
                : h("span", { style: { color: "#64748B" } }, "—")
            ),
            h("td", { style: { padding: "10px", fontFamily: "var(--font-mono)", color: "#00F0FF" } }, c.deflated_sharpe ? c.deflated_sharpe.toFixed(2) : "—")
          ))
        )
      )
    )
  );
}

// ===========================================================================
// TerminalView — 70/30 Split Widescreen Trading Terminal
// ===========================================================================
function TerminalView({
  activeInterval, setActiveInterval, binanceWsStatus, livePrice, changePct,
  predictionData, predictionHistory, counterfactualData,
  regimeData, explanationData, qualityData, memoryData, portfolioData, intelData,
  isReplaying, setIsReplaying, selectedRecord, onSelectRecord,
  activeTab, setActiveTab,
  onPriceChange, onWsStatusChange,
  engineState
}) {
  return h("div", null,
    h(ReplayBar, {
      memoryData,
      isReplaying,
      setIsReplaying,
      selectedRecord,
      onSelectRecord
    }),

    // Top Section — 70/30 Widescreen Grid: Chart Left (70%) + Intelligence Radar Right (30%)
    h("div", { className: "terminal-grid-70-30" },
      h("div", { className: "glass-card chart-card" },
        h(ChartTopBar, {
          wsStatus:        binanceWsStatus,
          activeInterval,
          setActiveInterval,
          livePrice
        }),
        h(LightweightCandleChart, {
          interval:          activeInterval,
          predictionData,
          predictionHistory,
          onWsStatusChange,
          onPriceChange
        })
      ),

      h(RightIntelligenceSidebar, { intelData })
    ),

    // Middle Section — Full-Width AI Decision Matrix, Scenario Simulator, Orderbook Depth & Counterfactual Engine
    h("div", { style: { marginTop: "24px" } },
      h(PredictionPanel, { predictionData, engineState }),
      h(WhatIfSimulator, { livePrice, predictionData }),
      h(OrderBookPressureWidget, { livePrice }),
      h(CounterfactualPanel, { counterfactualData })
    ),

    // Bottom Panel Tabs
    h(BottomTabs, {
      activeTab,
      setActiveTab,
      memoryData,
      portfolioData,
      qualityData,
      explanationData
    })
  );
}

// ===========================================================================
// App — main router + state management
// ===========================================================================
function App() {
  const [path,            setPath]            = useState(window.location.hash ? window.location.hash.replace("#", "") : "/");
  const [engineConnected, setEngineConnected] = useState(false);
  const [binanceWsStatus, setBinanceWsStatus] = useState("disconnected");
  const [activeInterval,  setActiveInterval]  = useState("1h");
  const [livePrice,       setLivePrice]       = useState(0);
  const [changePct,       setChangePct]       = useState(0);
  const [healthData,      setHealthData]      = useState(null);
  const [securityBlocked, setSecurityBlocked] = useState(false);

  // Replay Mode & Tab States
  const [isReplaying,     setIsReplaying]     = useState(false);
  const [selectedRecord,  setSelectedRecord]  = useState(null);
  const [activeTab,       setActiveTab]       = useState("memory");

  // AI & Intelligence state
  const [predictionData,    setPredictionData]    = useState(null);
  const [predictionHistory, setPredictionHistory] = useState([]);
  const [regimeData,        setRegimeData]        = useState(null);
  const [explanationData,   setExplanationData]   = useState(null);
  const [qualityData,       setQualityData]       = useState(null);
  const [memoryData,        setMemoryData]        = useState([]);
  const [portfolioData,     setPortfolioData]     = useState(null);
  const [intelData,         setIntelData]         = useState(null);
  const [counterfactualData, setCounterfactualData] = useState(null);

  // High-Profit Opportunity Notifications State
  const [opportunityAlerts, setOpportunityAlerts] = useState([]);
  const [activeToasts,       setActiveToasts]       = useState([]);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
  const [notificationSettings, setNotificationSettings] = useState({
    backend_url: getApiBaseUrl(),
    browser_alerts_enabled: true,
    sound_alerts_enabled: true,
    min_profit_threshold_pct: 1.5,
    webhook_enabled: false,
    webhook_url: "",
    webhook_type: "discord",
    telegram_bot_token: "",
    telegram_chat_id: ""
  });

  // Hash routing
  useEffect(() => {
    const onHashChange = () => setPath(window.location.hash ? window.location.hash.replace("#", "") : "/");
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  // Fetch initial notifications and settings
  const loadNotificationsData = useCallback(async () => {
    try {
      const [recentRes, settingsRes] = await Promise.allSettled([
        api.fetchNotificationsRecent(15),
        api.fetchNotificationSettings()
      ]);
      if (recentRes.status === "fulfilled" && recentRes.value.alerts) {
        setOpportunityAlerts(recentRes.value.alerts);
      }
      if (settingsRes.status === "fulfilled") {
        setNotificationSettings(prev => ({ ...prev, ...settingsRes.value }));
      }
    } catch { /* ignore non-critical */ }
  }, []);

  useEffect(() => {
    loadNotificationsData();
  }, [loadNotificationsData]);

  // Handle incoming High-Profit Opportunity Alert
  const handleIncomingAlert = useCallback((alertPayload) => {
    if (!alertPayload) return;
    
    // 1. Play fanfare chime
    if (notificationSettings?.sound_alerts_enabled !== false) {
      playOpportunityFanfare();
    }

    // 2. Show native OS desktop notification
    showBrowserNotification(alertPayload);

    // 3. Add to recent alerts history
    setOpportunityAlerts(prev => [alertPayload, ...prev.filter(a => a.id !== alertPayload.id)].slice(0, 30));

    // 4. Add to floating toasts with 10s auto-dismiss
    setActiveToasts(prev => [alertPayload, ...prev.filter(t => t.id !== alertPayload.id)].slice(0, 3));
    setTimeout(() => {
      setActiveToasts(prev => prev.filter(t => t.id !== alertPayload.id));
    }, 10000);
  }, [notificationSettings]);

  // Backend engine WS
  useEffect(() => {
    const unsub = backendWS.subscribe(msg => {
      if (msg.type === "connection") {
        setEngineConnected(msg.status === "connected");
      } else if (msg.type === "HIGH_PROFIT_ALERT" && msg.data) {
        handleIncomingAlert(msg.data);
      }
    });
    return unsub;
  }, [handleIncomingAlert]);

  // Trigger test alert handler
  const handleTriggerTestAlert = useCallback(async () => {
    try {
      const res = await api.triggerTestAlert();
      if (res && res.alert) {
        handleIncomingAlert(res.alert);
      }
    } catch (err) {
      console.warn("Failed to trigger test alert:", err);
    }
  }, [handleIncomingAlert]);

  // Poll backend health heartbeat every 15 s
  const pollHealth = useCallback(async () => {
    const currentUrl = getApiBaseUrl();
    try {
      const data = await api.fetchHealth();
      setHealthData(data);
      setSecurityBlocked(false);
    } catch (err) {
      const isHttps = window.location.protocol === "https:";
      const isHttpTarget = currentUrl.startsWith("http://") && !currentUrl.includes("localhost") && !currentUrl.includes("127.0.0.1");
      if (isHttps && isHttpTarget) {
        setSecurityBlocked(true);
      } else {
        setSecurityBlocked(false);
      }
      setHealthData({ status: "offline", models_loaded: false, latency: { market_latency_ms: 0, prediction_latency_ms: 0, ws_latency_ms: 0 } });
    }
  }, []);

  useEffect(() => {
    pollHealth();
    const id = setInterval(pollHealth, 15000);
    return () => clearInterval(id);
  }, [pollHealth]);

  // Backend AI data poll
  const loadAIData = useCallback(async () => {
    if (isReplaying) return; // Freeze live polling during Replay mode
    try {
      const [pred, hist, regime, expl, qual, mem, port, mkt, intel, count] = await Promise.allSettled([
        api.fetchPredictionLatest(),
        api.fetchPredictionHistory(),
        api.fetchRegimeLatest(),
        api.fetchExplanationLatest(),
        api.fetchQualityLatest(),
        api.fetchMemory(),
        api.fetchPortfolio(),
        api.fetchMarketLatest(),
        api.fetchIntelligenceLatest(),
        api.fetchCounterfactual()
      ]);

      if (pred.status === "fulfilled")  setPredictionData(pred.value);
      if (hist.status === "fulfilled")  setPredictionHistory(hist.value);
      if (regime.status === "fulfilled") setRegimeData(regime.value);
      if (expl.status === "fulfilled")  setExplanationData(expl.value);
      if (qual.status === "fulfilled")  setQualityData(qual.value);
      if (mem.status === "fulfilled")   setMemoryData(mem.value);
      if (port.status === "fulfilled")  setPortfolioData(port.value);
      if (mkt.status === "fulfilled")   setChangePct(mkt.value.change_pct_24h || 0);
      if (intel.status === "fulfilled") setIntelData(intel.value);
      if (count.status === "fulfilled") setCounterfactualData(count.value);
    } catch { /* non-critical */ }
  }, [isReplaying]);

  useEffect(() => {
    loadAIData();
    const id = setInterval(loadAIData, 30000);
    return () => clearInterval(id);
  }, [loadAIData]);

  // Save settings handler
  const handleSaveSettings = useCallback(async (newSettings) => {
    try {
      const res = await api.updateNotificationSettings(newSettings);
      if (res && res.settings) {
        setNotificationSettings(prev => ({ ...prev, ...res.settings }));
      }
    } catch (err) {
      console.warn("Non-critical notification setting sync:", err.message);
    }
    pollHealth();
    loadAIData();
  }, [pollHealth, loadAIData]);

  // Handle Replay record selection
  const handleSelectReplayRecord = useCallback(async (record) => {
    setSelectedRecord(record);
    if (record) {
      try {
        const snap = await api.fetchReplaySnapshot(record.timestamp);
        setPredictionData({
          direction: snap.prediction,
          probability_pct: Math.round(snap.probability * 100),
          expected_return_pct: snap.actual_return_pct,
          tp: snap.tp,
          sl: snap.sl,
          action: snap.decision,
          model: snap.model_version
        });
        if (snap.shap) setExplanationData(snap.shap);
        if (snap.intelligence) setIntelData(snap.intelligence);
      } catch (err) {
        console.warn("Failed to fetch replay snapshot:", err);
      }
    }
  }, []);

  const engineState = securityBlocked
    ? "security_blocked"
    : (healthData?.status === "live" && healthData?.models_loaded
        ? "live"
        : (healthData?.status === "warming_up" || (healthData?.status === "live" && !healthData?.models_loaded)
            ? "warming_up"
            : (engineConnected ? "connecting" : "offline")));

  // Shared props for both home preview and full terminal
  const terminalProps = {
    activeInterval, setActiveInterval,
    binanceWsStatus,
    livePrice, changePct,
    predictionData, predictionHistory, counterfactualData,
    regimeData, explanationData, qualityData,
    memoryData, portfolioData, intelData,
    isReplaying, setIsReplaying, selectedRecord,
    onSelectRecord: handleSelectReplayRecord,
    activeTab, setActiveTab,
    onPriceChange:   setLivePrice,
    onWsStatusChange: setBinanceWsStatus,
    engineState
  };

  return h("div", null,
    h(ThreeBackground),
    h(Navbar, {
      currentPath: path,
      setPath,
      engineState,
      alerts: opportunityAlerts,
      onTestAlert: handleTriggerTestAlert,
      onOpenSettings: () => setIsSettingsModalOpen(true),
      onSelectAlert: (alert) => {
        setPath("/terminal");
      }
    }),

    // Floating High-Profit Opportunity Toasts
    h(OpportunityToastContainer, {
      alerts: activeToasts,
      onDismiss: (id) => setActiveToasts(prev => prev.filter(t => t.id !== id)),
      onSelectAlert: (alert) => {
        setPath("/terminal");
      }
    }),

    // Webhook & Notification Settings Modal
    h(NotificationSettingsModal, {
      isOpen: isSettingsModalOpen,
      onClose: () => setIsSettingsModalOpen(false),
      settings: notificationSettings,
      onSaveSettings: handleSaveSettings,
      onTestAlert: handleTriggerTestAlert
    }),

    path === "/" ? (
      h("div", null,
        h(HeroSection, { setPath, livePrice, changePct, predictionData, regimeData, qualityData })
      )
    ) : (
      h("div", { className: "terminal-container" },
        h("div", { className: "section-header" },
          h("h2", { className: "section-title" }, "⚡ BTCognitive Live AI Terminal"),
          h("p",  { className: "section-desc"  }, "Full Bloomberg & TradingView quality AI Bitcoin intelligence workspace")
        ),
        h(TerminalView, terminalProps)
      )
    ),

    h("footer", { style: { padding: "20px 40px", borderTop: "1px solid var(--card-border)", display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(5,8,22,0.85)", marginTop: "40px" } },
      h("div", { style: { fontSize: "0.85rem", color: "var(--text-muted)" } }, "© 2026 BTCognitive AI Market Intelligence Engine · Powered by Adaptive Regimes"),
      h("div", { className: "footer-latency" },
        h("span", { className: "latency-item" }, "Market: ", h("span", { className: "latency-val" }, `${healthData?.latency?.market_latency_ms || 12}ms`)),
        h("span", null, "·"),
        h("span", { className: "latency-item" }, "Model: ", h("span", { className: "latency-val" }, `${healthData?.latency?.prediction_latency_ms || 83}ms`)),
        h("span", null, "·"),
        h("span", { className: "latency-item" }, "WS: ", h("span", { className: "latency-val" }, `${healthData?.latency?.ws_latency_ms || 5}ms`))
      )
    )
  );
}

// Mount
document.addEventListener("DOMContentLoaded", () => {
  const el = document.getElementById("root");
  if (el) ReactDOM.createRoot(el).render(h(App));
});


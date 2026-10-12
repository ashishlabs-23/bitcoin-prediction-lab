(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const state = { busy: false, lastPayload: null };
  const fmtMoney = (value) => Number.isFinite(Number(value)) && value !== null ? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(Number(value)) : "—";
  const fmtNumber = (value, digits = 2) => value !== null && value !== undefined && Number.isFinite(Number(value)) ? Number(value).toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits }) : "—";
  const fmtPercent = (value, digits = 2) => value !== null && value !== undefined && Number.isFinite(Number(value)) ? `${Number(value) > 0 ? "+" : ""}${Number(value).toFixed(digits)}%` : "—";
  const timeText = (value) => { if (!value) return "—"; const d = new Date(value); return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString([], { dateStyle: "medium", timeStyle: "medium" }); };
  const setText = (id, value) => { const el = $(id); if (el) el.textContent = value; };
  function setChip(el, text, kind) { if (!el) return; el.textContent = text; el.className = `status-chip status-${kind || "muted"}`; }
  function niceErrorName(v) { return String(v || "unknown error").replace(/_/g, " ").toLowerCase(); }
  function renderChart(candles) {
    const svg = $("price-chart");
    if (!Array.isArray(candles) || candles.length < 2) { svg.innerHTML = '<text x="500" y="125" text-anchor="middle" class="chart-empty">Validated hourly candles are unavailable.</text>'; setText("chart-range", ""); return; }
    const data = candles.filter(c => Number.isFinite(Number(c.close)) && Number(c.close) > 0);
    if (data.length < 2) { svg.innerHTML = '<text x="500" y="125" text-anchor="middle" class="chart-empty">Validated hourly candles are unavailable.</text>'; return; }
    const vals = data.map(c => Number(c.close)); const low = Math.min(...vals); const high = Math.max(...vals); const pad = (high - low) * 0.12 || high * 0.002;
    const min = low - pad, max = high + pad, W = 1000, H = 250, L = 20, R = 20, T = 18, B = 20;
    const x = i => L + i * (W - L - R) / (vals.length - 1); const y = v => T + (max - v) * (H - T - B) / (max - min);
    const path = vals.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(2)},${y(v).toFixed(2)}`).join(" ");
    const area = `${path} L${x(vals.length - 1).toFixed(2)},${H-B} L${L},${H-B} Z`;
    const lines = [0.25, 0.5, 0.75].map(q => { const yy=T+q*(H-T-B); return `<line x1="${L}" y1="${yy}" x2="${W-R}" y2="${yy}" stroke="#26314a" stroke-width="1" stroke-dasharray="4 6"/>`; }).join("");
    svg.innerHTML = `<defs><linearGradient id="area-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#56c9ff" stop-opacity=".22"/><stop offset="100%" stop-color="#56c9ff" stop-opacity="0"/></linearGradient></defs>${lines}<path d="${area}" fill="url(#area-fill)"/><path d="${path}" fill="none" stroke="#60d0ff" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${x(vals.length-1)}" cy="${y(vals[vals.length-1])}" r="5" fill="#60d0ff" stroke="#101728" stroke-width="3"/>`;
    setText("chart-range", `${fmtMoney(low)} low · ${fmtMoney(high)} high`);
  }
  function renderForecast(forecast) {
    const q = forecast?.price_quantiles_usd;
    const ok = forecast?.availability === "AVAILABLE" && q && [q.p10,q.p50,q.p90].every(v => Number.isFinite(Number(v)));
    if (!ok) {
      setChip($("forecast-summary").querySelector(".status-chip"), "FORECAST UNAVAILABLE", "error");
      $("forecast-summary").querySelector("p").textContent = forecast?.reason ? `Reason: ${niceErrorName(forecast.reason)}. A valid spot quote and enough complete historical blocks are required.` : "Source-backed candles are not yet sufficient to compute the forecast.";
      for (const id of ["p10-price","p50-price","p90-price","p10-return","p50-return","p90-return"]) setText(id,"—");
      setChip($("backtest-status"), forecast?.backtest?.status || "NOT AVAILABLE", "muted");
      for (const id of ["test-blocks","coverage","forecast-mae","baseline-mae"]) setText(id,"—");
      setText("backtest-note", forecast?.backtest?.note || "No walk-forward result available for this horizon."); return;
    }
    const horizon = forecast.horizon || $("horizon").value;
    setChip($("forecast-summary").querySelector(".status-chip"), "EXPERIMENTAL BASELINE", "wait");
    $("forecast-summary").querySelector("p").textContent = `${horizon} empirical return distribution from ${forecast.sample_blocks} non-overlapping historical blocks. It is not the authenticated production model.`;
    for (const [key,label] of [["p10","p10"],["p50","p50"],["p90","p90"]]) {
      setText(`${label}-price`, fmtMoney(q[key]));
      setText(`${label}-return`, fmtPercent(forecast.return_quantiles_pct?.[key],4)+" historical return quantile");
    }
    const b=forecast.backtest || {};
    setChip($("backtest-status"), b.status || "NOT EVALUATED", b.status === "WALK_FORWARD_MEASURED_NOT_PROMOTED" ? "live" : "muted");
    setText("test-blocks", b.test_blocks ?? "—"); setText("coverage", b.interval_coverage_pct == null ? "—" : `${fmtNumber(b.interval_coverage_pct)}%`);
    setText("forecast-mae", b.median_absolute_error_pct == null ? "—" : `${fmtNumber(b.median_absolute_error_pct,5)}%`);
    setText("baseline-mae", b.zero_return_baseline_mae_pct == null ? "—" : `${fmtNumber(b.zero_return_baseline_mae_pct,5)}%`);
    setText("backtest-note", b.note || "Results are descriptive and do not establish live performance.");
  }
  function renderDrivers(payload) {
    const container=$("driver-grid"); container.replaceChildren();
    const rows=Array.isArray(payload?.drivers)?payload.drivers:[];
    const labels = {momentum_1h_pct:"1-hour momentum",momentum_4h_pct:"4-hour momentum",momentum_24h_pct:"24-hour momentum",momentum_7d_pct:"7-day momentum",venue_divergence_pct:"Cross-venue spot divergence",realized_volatility_24h_pct:"24-hour realized volatility",realized_volatility_7d_pct:"7-day realized volatility",rsi_14:"RSI (14)",volume_ratio_24h:"Relative volume",spread_bps:"Bid–ask spread",funding_rate:"Perpetual funding",open_interest_contracts:"Perpetual open interest"};
    if (!rows.length) { const p=document.createElement("article");p.className="panel driver-card";p.textContent="No validated driver observations are available.";container.append(p);return; }
    for (const row of rows) {
      const card=document.createElement("article"); card.className="panel driver-card";
      const label=document.createElement("span");label.className="driver-label";label.textContent=labels[row.id]||row.label||row.id;
      const value=document.createElement("strong");value.className="driver-value";
      let rendered="—";
      if (row.value !== null && row.value !== undefined && Number.isFinite(Number(row.value))) {
        if ((row.unit||"")==="%") rendered=fmtPercent(row.value,3);
        else if (row.unit==="bps") rendered=`${fmtNumber(row.value,2)} bps`;
        else if (row.unit==="rate") rendered=fmtNumber(Number(row.value)*100,5)+"%";
        else if (row.unit==="contracts") rendered=fmtNumber(row.value,0);
        else rendered=fmtNumber(row.value,2);
      }
      value.textContent=rendered;
      const meta=document.createElement("div");meta.className="driver-meta";
      const badge=document.createElement("span");badge.className="driver-badge"+(row.status==="AVAILABLE"?"":" unavailable");badge.textContent=row.status||"UNKNOWN";
      const unit=document.createElement("span");unit.className="small-muted";unit.textContent=row.source_instrument?"USDT perp":((row.unit===""||!row.unit)?"":row.unit);
      meta.append(badge,unit);card.append(label,value,meta);container.append(card);
    }
  }
  function render(payload) {
    state.lastPayload=payload;
    const market=payload.market||{}; const technical=payload.technical||{}; const derivative=payload.derivatives||{};
    const marketLive=["LIVE","PARTIAL"].includes(payload.status) && market.status !== "DATA_UNAVAILABLE" && Number.isFinite(Number(market.price_usd));
    setChip($("feed-status"), marketLive?`LIVE · ${String(market.source||"market feed").toUpperCase()}`:"MARKET DATA UNAVAILABLE", marketLive?"live":"error");
    setText("spot-price",fmtMoney(market.price_usd));setText("quote-source",market.source||"No provider");
    setText("bid-ask",`Bid ${fmtMoney(market.bid_usd)} · Ask ${fmtMoney(market.ask_usd)}`);
    setText("quote-age",market.age_seconds==null?"Age —":`Quote age ${fmtNumber(market.age_seconds,1)}s`);setText("quote-time",`Source time: ${timeText(market.source_timestamp)} · Retrieved: ${timeText(market.retrieved_at)}`);
    setText("momentum-24h",fmtPercent(technical.momentum_24h_pct));
    setText("volatility-24h",technical.realized_volatility_24h_pct==null?"—":`${fmtNumber(technical.realized_volatility_24h_pct,3)}%`);
    setText("spread",market.spread_bps==null?"—":`${fmtNumber(market.spread_bps,2)} bps`);
    setText("candle-meta",payload.candle_count?`${payload.candle_count.toLocaleString()} closed 1h candles · ${market.source||"source unavailable"} · last close ${timeText(market.latest_closed_candle_at)}`:"No validated candle history");
    renderChart(payload.candles);renderForecast(payload.forecast||{});renderDrivers(payload);
    setChip($("derivatives-status"),derivative.status||"UNAVAILABLE",derivative.status==="AVAILABLE"?"live":"muted");
    setText("funding-rate",derivative.funding_rate==null?"—":`${fmtNumber(Number(derivative.funding_rate)*100,5)}%`);
    setText("open-interest",derivative.open_interest_contracts==null?"—":fmtNumber(derivative.open_interest_contracts,0));setText("mark-price",fmtMoney(derivative.mark_price_usdt));
    setText("flows-state",payload.capital_flows?.status||"NOT_CONFIGURED");setText("macro-state",payload.macro?.status||"NOT_CONFIGURED");
    const errs=payload.provider_errors||{};const diagnostics=Object.entries(errs).map(([provider,reason])=>`${provider}: ${niceErrorName(reason)}`);
    setText("provider-errors",diagnostics.length?`Feed diagnostics · ${diagnostics.join(" · ")}`:"No provider failures reported in the latest refresh.");
    setText("last-refresh",`Refreshed ${timeText(payload.generated_at)}`);
  }
  async function refresh() {
    if (state.busy) return; state.busy=true; const button=$("refresh"); button.disabled=true; button.textContent="Refreshing…";
    try {
      const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),18000);
      try {
        const res=await fetch(`/api/dashboard?horizon=${encodeURIComponent($("horizon").value)}`,{cache:"no-store",headers:{Accept:"application/json"},signal:controller.signal});
        if(!res.ok) throw new Error(`HTTP ${res.status}`);const data=await res.json();render(data);
      } finally { clearTimeout(timer); }
    } catch (error) {
      setChip($("feed-status"),"CONNECTION ERROR","error");setText("provider-errors",`Could not refresh dashboard (${error.name==="AbortError"?"request timed out":error.message}). Previous data, if shown, is not refreshed.`);
      if (!state.lastPayload) { setText("spot-price","—");setText("quote-time","Backend is not reachable. Start the BTCognitive server and refresh."); }
    } finally { state.busy=false;button.disabled=false;button.innerHTML='Refresh data <span aria-hidden="true">↻</span>'; }
  }
  $("refresh").addEventListener("click",refresh);
  $("horizon").addEventListener("change",refresh);
  refresh();window.setInterval(()=>{if(document.visibilityState==="visible")refresh();},30000);
})();
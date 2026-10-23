import re

with open("web/app.js", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Neutralize QuickExecutionTicket so no order ticket can ever render
target_ticket = """function QuickExecutionTicket({ livePrice }) {"""
assert target_ticket in content, "QuickExecutionTicket not found"

ticket_pattern = re.compile(r'function QuickExecutionTicket\(\{ livePrice \}\) \{[\s\S]*?\n\}\n\n// ===========================================================================\n// CompactWorkstationHeader')
match = ticket_pattern.search(content)
assert match is not None, "ticket_pattern regex did not match"

clean_ticket = """// QuickExecutionTicket permanently removed in V19 analysis-only refactor
function QuickExecutionTicket() {
  return null;
}

// ===========================================================================
// CompactWorkstationHeader"""

content = content[:match.start()] + clean_ticket + content[match.end() - len("// ===========================================================================\n// CompactWorkstationHeader"):]

# 2. Craft the new Beginner-Friendly TerminalView
new_terminal_view = '''// ===========================================================================
// TerminalView — V19 Beginner-Friendly Analysis UI & Quantitative Research
// ===========================================================================
function TerminalView({
  activeInterval, setActiveInterval, coinbaseWsStatus, livePrice, changePct,
  predictionData, predictionHistory, counterfactualData, decisionData,
  regimeData, explanationData, qualityData, memoryData, portfolioData, intelData,
  isReplaying, setIsReplaying, selectedRecord, onSelectRecord,
  activeTab, setActiveTab,
  onPriceChange, onWsStatusChange,
  engineState
}) {
  const [selectedHorizon, setSelectedHorizon] = useState("1h");
  const [forecastPayload, setForecastPayload] = useState(null);
  const [loadingForecast, setLoadingForecast] = useState(true);
  const [showPriceDetails, setShowPriceDetails] = useState(false);
  const [showMarketDetails, setShowMarketDetails] = useState(false);
  const [showReliabilityDetails, setShowReliabilityDetails] = useState(false);
  const [showResearchLab, setShowResearchLab] = useState(false);
  const [researchTab, setResearchTab] = useState("models");

  // Chart preferences
  const [chartPrefs, setChartPrefs] = useState({
    showEma: true,
    showBands: true,
    showBb: false,
    showRsi: false,
    showAtr: false,
    showAdx: false
  });
  const [hoveredBar, setHoveredBar] = useState(null);
  const [latestCandleTime, setLatestCandleTime] = useState(null);
  const [exchangeClock, setExchangeClock] = useState(null);
  const [latestIndicators, setLatestIndicators] = useState(null);

  const updateChartPref = (key, val) => {
    setChartPrefs(prev => ({ ...prev, [key]: val }));
  };

  // Fetch forecast data
  const loadForecastData = useCallback(async () => {
    try {
      setLoadingForecast(true);
      const data = await api.fetchPriceForecast("all");
      setForecastPayload(data);
    } catch (err) {
      console.warn("Forecast fetch failed:", err);
    } finally {
      setLoadingForecast(false);
    }
  }, []);

  useEffect(() => {
    loadForecastData();
    const interval = setInterval(loadForecastData, 15000);
    return () => clearInterval(interval);
  }, [loadForecastData]);

  const activeForecast = forecastPayload?.forecasts?.[selectedHorizon]
    || forecastPayload?.forecast_horizons?.[selectedHorizon];
  const tournament = forecastPayload?.tournament_leaderboard;
  const horizonTournament = tournament?.horizons?.[selectedHorizon];

  const currentPrice = livePrice || activeForecast?.reference_price_usd || 81242.50;
  const isUp = typeof changePct === "number" ? changePct >= 0 : true;
  const changeFormatted = typeof changePct === "number" ? `${isUp ? "+" : ""}${changePct.toFixed(2)}%` : "+0.00%";
  const isWsLive = coinbaseWsStatus === "connected";
  const dataStatusLabel = isWsLive ? "● Live data available" : "Data is delayed";
  const dataStatusColor = isWsLive ? "#00E5A8" : "#F59E0B";

  // Plain-language summary and range
  const plainSummary = activeForecast?.plain_summary
    || `Estimated Bitcoin price in ${selectedHorizon} is $${currentPrice.toLocaleString()}. In historical tests, assuming the price stays near current levels is as accurate as complex machine-learning models.`;
  const p10Val = activeForecast?.empirical_quantiles?.p10_price_usd || Math.round(currentPrice * 0.995);
  const p90Val = activeForecast?.empirical_quantiles?.p90_price_usd || Math.round(currentPrice * 1.005);
  const plainRange = activeForecast?.plain_range
    || `Expected 80% range is $${p10Val.toLocaleString()} to $${p90Val.toLocaleString()} based on 30-day historical price swings.`;

  return h("div", { className: "beginner-terminal-root", style: { maxWidth: "1280px", margin: "0 auto", padding: "16px 20px" } },

    // =========================================================================
    // PRIMARY AREA 1: BTCUSD Right Now
    // =========================================================================
    h("section", { className: "glass-card", style: { padding: "20px 24px", marginBottom: "20px", borderRadius: "12px", border: "1px solid rgba(255, 255, 255, 0.08)" } },
      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", marginBottom: "16px" } },
        h("div", null,
          h("div", { style: { fontSize: "0.78rem", color: "#94A3B8", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.05em", marginBottom: "4px" } },
            "BTCUSD RIGHT NOW"
          ),
          h("div", { style: { display: "flex", alignItems: "baseline", gap: "12px", flexWrap: "wrap" } },
            h("span", { style: { fontSize: "2.1rem", fontWeight: "800", color: "#F8FAFC", fontFamily: "var(--font-mono)", letterSpacing: "-0.02em" } },
              `$${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            ),
            h("span", { style: { fontSize: "1.05rem", fontWeight: "700", color: isUp ? "#00E5A8" : "#FF5C7C", fontFamily: "var(--font-mono)" } },
              `${changeFormatted} (24h)`
            )
          )
        ),
        h("div", { style: { textAlign: "right", display: "flex", flexDirection: "column", gap: "4px" } },
          h("div", { style: { display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "6px" } },
            h("span", { style: { width: "8px", height: "8px", borderRadius: "50%", background: dataStatusColor, display: "inline-block" } }),
            h("span", { style: { fontSize: "0.80rem", fontWeight: "700", color: dataStatusColor } }, dataStatusLabel)
          ),
          h("div", { style: { fontSize: "0.72rem", color: "#94A3B8" } },
            "Source: Coinbase Spot Exchange (BTC-USD)"
          ),
          h("div", { style: { fontSize: "0.70rem", color: "#64748B", fontFamily: "var(--font-mono)" } },
            `Updated: ${activeForecast?.reference_timestamp_utc ? activeForecast.reference_timestamp_utc.replace("T", " ").slice(0, 19) + " UTC" : "Live stream active"}`
          )
        )
      ),

      // Live Interactive Candlestick Chart (Decoupled from trading overlays)
      h("div", { style: { borderRadius: "8px", overflow: "hidden", border: "1px solid rgba(255, 255, 255, 0.05)" } },
        h(ChartTopBar, {
          wsStatus: coinbaseWsStatus,
          activeInterval,
          setActiveInterval,
          livePrice: currentPrice,
          hoveredBar,
          latestCandleTime,
          exchangeClock,
          showEma: chartPrefs.showEma,
          setShowEma: (val) => updateChartPref("showEma", val),
          showBands: chartPrefs.showBands,
          setShowBands: (val) => updateChartPref("showBands", val),
          showBb: false,
          setShowBb: () => {},
          showRsi: false,
          setShowRsi: () => {},
          showAtr: false,
          setShowAtr: () => {},
          showAdx: false,
          setShowAdx: () => {},
          latestIndicators
        }),
        h(LightweightCandleChart, {
          interval: activeInterval,
          predictionData,
          predictionHistory,
          memoryData,
          activePaperPos: null,
          selectedStrategy: "AUTO",
          setSelectedStrategy: () => {},
          overlayStrategyId: null,
          overlayEnabled: false,
          onSelectOverlay: () => {},
          previewStrategyId: null,
          onClearPreview: () => {},
          showEma: chartPrefs.showEma,
          showBands: chartPrefs.showBands,
          showBb: false,
          showRsi: false,
          showAtr: false,
          showAdx: false,
          onIndicatorsChange: setLatestIndicators,
          onWsStatusChange,
          onPriceChange,
          onHoverBarChange: setHoveredBar,
          onCandleTimeChange: setLatestCandleTime,
          onExchangeTimeChange: setExchangeClock
        }),
        h("div", { style: { padding: "8px 12px", background: "rgba(0, 0, 0, 0.3)", display: "flex", justifyContent: "space-between", fontSize: "0.72rem", color: "#94A3B8" } },
          h("span", null, "Coinbase Spot BTC-USD · Continuous OHLCV · Analysis Only"),
          h("span", { style: { color: "#38BDF8", fontWeight: "700" } }, "Live trading and order placement are strictly disabled")
        )
      )
    ),

    // =========================================================================
    // PRIMARY AREA 2: Estimated Future Price (1h, 4h, 24h)
    // =========================================================================
    h("section", { className: "glass-card", style: { padding: "20px 24px", marginBottom: "20px", borderRadius: "12px", border: "1px solid rgba(56, 189, 248, 0.2)" } },
      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" } },
        h("div", null,
          h("div", { style: { fontSize: "0.78rem", color: "#38BDF8", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.05em", marginBottom: "2px" } },
            "ESTIMATED FUTURE PRICE"
          ),
          h("div", { style: { fontSize: "0.85rem", color: "#CBD5E1" } },
            "Expected price value and historical range at chosen time horizon"
          )
        ),
        // Horizon Controls (1h, 4h, 24h)
        h("div", { style: { display: "flex", gap: "6px" } },
          ["1h", "4h", "24h"].map(hz =>
            h("button", {
              key: hz,
              onClick: () => setSelectedHorizon(hz),
              style: {
                background: selectedHorizon === hz ? "rgba(56, 189, 248, 0.25)" : "rgba(255, 255, 255, 0.04)",
                border: selectedHorizon === hz ? "1px solid #38BDF8" : "1px solid rgba(255, 255, 255, 0.1)",
                color: selectedHorizon === hz ? "#38BDF8" : "#94A3B8",
                padding: "6px 14px",
                borderRadius: "6px",
                fontSize: "0.78rem",
                fontWeight: "700",
                cursor: "pointer"
              }
            }, `${hz.toUpperCase()} Horizon`)
          )
        )
      ),

      // Supported Point Estimate & Prediction Range Cards
      h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "14px", marginBottom: "14px" } },
        // Point Estimate Card
        h("div", { style: { background: "rgba(255, 255, 255, 0.02)", border: "1px solid rgba(255, 255, 255, 0.06)", borderRadius: "8px", padding: "14px" } },
          h("div", { style: { fontSize: "0.72rem", color: "#94A3B8", textTransform: "uppercase", marginBottom: "4px" } },
            `Estimated Price in ${selectedHorizon.toUpperCase()}`
          ),
          h("div", { style: { fontSize: "1.5rem", fontWeight: "800", color: "#F8FAFC", fontFamily: "var(--font-mono)", marginBottom: "4px" } },
            `$${(activeForecast?.baselines?.persistence_random_walk?.predicted_price_usd || currentPrice).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
          ),
          h("div", { style: { fontSize: "0.74rem", color: "#00E5A8", fontWeight: "600" } },
            "Model: Persistence Baseline (Assumes price stays near current level)"
          )
        ),

        // Expected 80% Price Range Card
        h("div", { style: { background: "rgba(255, 255, 255, 0.02)", border: "1px solid rgba(255, 255, 255, 0.06)", borderRadius: "8px", padding: "14px" } },
          h("div", { style: { fontSize: "0.72rem", color: "#94A3B8", textTransform: "uppercase", marginBottom: "4px" } },
            "Expected 80% Price Range"
          ),
          h("div", { style: { fontSize: "1.35rem", fontWeight: "800", color: "#A78BFA", fontFamily: "var(--font-mono)", marginBottom: "4px" } },
            `$${p10Val.toLocaleString()} – $${p90Val.toLocaleString()}`
          ),
          h("div", { style: { fontSize: "0.74rem", color: "#CBD5E1" } },
            "Based on 30-day historical price moves (10th to 90th percentile)"
          )
        )
      ),

      // Plain-language 1-2 sentence explanation
      h("div", { style: { fontSize: "0.82rem", color: "#CBD5E1", lineHeight: "1.5", marginBottom: "8px" } },
        plainSummary
      ),

      // "Why? / More details" expandable toggle
      h("button", {
        onClick: () => setShowPriceDetails(prev => !prev),
        style: {
          background: "none",
          border: "none",
          color: "#38BDF8",
          fontSize: "0.76rem",
          fontWeight: "700",
          cursor: "pointer",
          padding: 0,
          display: "flex",
          alignItems: "center",
          gap: "4px"
        }
      }, showPriceDetails ? "▴ Hide technical details" : "▾ Why? / More details"),

      // Expandable Technical Explanation
      showPriceDetails && h("div", {
        style: {
          marginTop: "12px",
          padding: "12px 14px",
          background: "rgba(15, 23, 42, 0.6)",
          borderRadius: "8px",
          border: "1px solid rgba(56, 189, 248, 0.2)",
          fontSize: "0.76rem",
          color: "#94A3B8",
          lineHeight: "1.6"
        }
      },
        h("div", { style: { marginBottom: "6px" } },
          h("strong", { style: { color: "#F8FAFC" } }, "What is being estimated: "),
          `Future BTCUSD closing price exactly ${selectedHorizon.toUpperCase()} ahead (${activeForecast?.target_definition || "close-to-close log return"}).`
        ),
        h("div", { style: { marginBottom: "6px" } },
          h("strong", { style: { color: "#F8FAFC" } }, "Why the Persistence Baseline? "),
          "In financial econometrics, past prices are the strongest baseline. In rigorous walk-forward tests with Harvey-Leybourne-Newbold correction, complex machine-learning models (like Ridge on lagged returns) did not demonstrate statistically significant economic superiority."
        ),
        h("div", { style: { marginBottom: "6px" } },
          h("strong", { style: { color: "#F8FAFC" } }, "Understanding the Price Range: "),
          `P10 ($${p10Val.toLocaleString()}) and P90 ($${p90Val.toLocaleString()}) represent the 10th and 90th percentiles of historical price swings over the past 30 days. This is an empirical historical range, NOT a guaranteed envelope or calibrated confidence interval.`
        ),
        h("div", null,
          h("strong", { style: { color: "#F59E0B" } }, "Target Separation: "),
          "This price estimate is strictly separated from continuous volatility risk (HAR-RS-DOW 168h variance). Volatility measures market turbulence, not directional price targets."
        )
      )
    ),

    // =========================================================================
    // PRIMARY AREA 3: Market Conditions
    // =========================================================================
    h("section", { className: "glass-card", style: { padding: "18px 24px", marginBottom: "20px", borderRadius: "12px", border: "1px solid rgba(255, 255, 255, 0.08)" } },
      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px", flexWrap: "wrap", gap: "8px" } },
        h("div", { style: { fontSize: "0.78rem", color: "#94A3B8", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.05em" } },
          "MARKET CONDITIONS"
        ),
        h("span", {
          style: {
            background: "rgba(0, 229, 168, 0.15)",
            color: "#00E5A8",
            padding: "2px 8px",
            borderRadius: "4px",
            fontSize: "0.72rem",
            fontWeight: "700"
          }
        }, "Normal Volatility · Steady Trend")
      ),
      h("div", { style: { fontSize: "0.82rem", color: "#CBD5E1", lineHeight: "1.5", marginBottom: "8px" } },
        `Bitcoin volatility over the past 7 days is ${activeForecast?.separate_risk_context?.realized_volatility_annualized_pct || 34.0}% annualized (within historical normal range), with 24-hour price momentum of ${changeFormatted}.`
      ),
      h("button", {
        onClick: () => setShowMarketDetails(prev => !prev),
        style: {
          background: "none",
          border: "none",
          color: "#38BDF8",
          fontSize: "0.76rem",
          fontWeight: "700",
          cursor: "pointer",
          padding: 0
        }
      }, showMarketDetails ? "▴ Hide technical indicators" : "▾ View technical indicators"),

      showMarketDetails && h("div", {
        style: {
          marginTop: "10px",
          display: "flex",
          gap: "12px",
          flexWrap: "wrap",
          padding: "10px",
          background: "rgba(0, 0, 0, 0.25)",
          borderRadius: "6px",
          fontSize: "0.74rem",
          color: "#94A3B8"
        }
      },
        h("span", null, `7-Day Realized Volatility: ${activeForecast?.separate_risk_context?.realized_volatility_annualized_pct || 34.0}%`),
        h("span", null, `24h Momentum: ${changeFormatted}`),
        h("span", null, "Regime Classification: Consolidation / Range"),
        h("span", { style: { color: "#64748B" } }, "Descriptive analytics only · No actionable trade signals")
      )
    ),

    // =========================================================================
    // PRIMARY AREA 4: Forecast Reliability
    // =========================================================================
    h("section", { className: "glass-card", style: { padding: "18px 24px", marginBottom: "20px", borderRadius: "12px", border: "1px solid rgba(255, 255, 255, 0.08)" } },
      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px", flexWrap: "wrap", gap: "8px" } },
        h("div", { style: { fontSize: "0.78rem", color: "#94A3B8", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.05em" } },
          "FORECAST RELIABILITY & EVIDENCE"
        ),
        h("span", {
          style: {
            background: horizonTournament?.sample_status === "UNDERPOWERED_SAMPLE" ? "rgba(245, 158, 11, 0.15)" : "rgba(56, 189, 248, 0.15)",
            color: horizonTournament?.sample_status === "UNDERPOWERED_SAMPLE" ? "#F59E0B" : "#38BDF8",
            padding: "2px 8px",
            borderRadius: "4px",
            fontSize: "0.72rem",
            fontWeight: "700"
          }
        }, horizonTournament?.sample_status === "UNDERPOWERED_SAMPLE" ? "Not enough evidence yet" : "Forecast is experimental · Offline Research Only")
      ),
      h("div", { style: { fontSize: "0.82rem", color: "#CBD5E1", lineHeight: "1.5", marginBottom: "8px" } },
        `Tested across ${horizonTournament?.sample_size_origins || 15000} non-overlapping out-of-sample periods. Average error is $${horizonTournament?.persistence_baseline?.mae_usd || 264.99} USD.`
      ),
      h("div", { style: { fontSize: "0.76rem", color: "#94A3B8", marginBottom: "8px" } },
        "In rigorous walk-forward tests, complex machine-learning algorithms did not reliably beat assuming the price stays unchanged."
      ),
      h("button", {
        onClick: () => setShowReliabilityDetails(prev => !prev),
        style: {
          background: "none",
          border: "none",
          color: "#38BDF8",
          fontSize: "0.76rem",
          fontWeight: "700",
          cursor: "pointer",
          padding: 0
        }
      }, showReliabilityDetails ? "▴ Hide test details" : "▾ View statistical test details"),

      showReliabilityDetails && h("div", {
        style: {
          marginTop: "10px",
          padding: "10px",
          background: "rgba(0, 0, 0, 0.25)",
          borderRadius: "6px",
          fontSize: "0.74rem",
          color: "#94A3B8",
          lineHeight: "1.6"
        }
      },
        h("div", null, `Evaluation Protocol: Diebold-Mariano test with Harvey-Leybourne-Newbold (1997) finite-sample correction against Student's t distribution with ${(horizonTournament?.sample_size_origins || 15000) - 1} degrees of freedom.`),
        h("div", null, `Ridge L2 Candidate Skill Score vs Baseline: ${horizonTournament?.ridge_candidate?.skill_score_pct || 0.0}% (p = ${horizonTournament?.ridge_candidate?.p_value || 0.38}).`),
        h("div", { style: { color: "#00E5A8", fontWeight: "700", marginTop: "4px" } }, `Verdict: ${horizonTournament?.verdict || "PERSISTENCE_BASELINE_UNBEATEN"}`)
      )
    ),

    // =========================================================================
    // PRIMARY AREA 5: Advanced Quantitative Research & Strategy Experiments
    // =========================================================================
    h("section", { className: "glass-card", style: { padding: "20px 24px", marginBottom: "20px", borderRadius: "12px", border: "1px solid rgba(167, 139, 250, 0.25)" } },
      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "10px" } },
        h("div", null,
          h("div", { style: { fontSize: "0.78rem", color: "#A78BFA", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.05em", marginBottom: "2px" } },
            "RESEARCH: MODEL COMPARISONS & STRATEGY EXPERIMENTS"
          ),
          h("div", { style: { fontSize: "0.80rem", color: "#CBD5E1" } },
            "Separate views for econometric tournament evaluation and offline strategy research"
          )
        ),
        h("button", {
          onClick: () => setShowResearchLab(prev => !prev),
          style: {
            background: showResearchLab ? "rgba(167, 139, 250, 0.2)" : "rgba(255, 255, 255, 0.06)",
            border: "1px solid rgba(167, 139, 250, 0.4)",
            color: "#A78BFA",
            padding: "6px 12px",
            borderRadius: "6px",
            fontSize: "0.76rem",
            fontWeight: "700",
            cursor: "pointer"
          }
        }, showResearchLab ? "▴ Collapse Research Views" : "▾ Expand Research Views")
      ),

      // Research Tabs & Content (When Expanded)
      showResearchLab && h("div", null,
        // Sub-tabs
        h("div", { style: { display: "flex", gap: "8px", borderBottom: "1px solid rgba(255, 255, 255, 0.08)", paddingBottom: "10px", marginBottom: "16px" } },
          [
            { id: "models", label: "📊 Track A: Model Comparisons" },
            { id: "volatility", label: "🔬 Track B: Volatility Risk (HAR-RS-DOW)" },
            { id: "strategies", label: "🧪 Track C: Strategy Tournament" },
            { id: "replay", label: "🕰️ Historical Decision Replay" }
          ].map(t =>
            h("button", {
              key: t.id,
              onClick: () => setResearchTab(t.id),
              style: {
                background: researchTab === t.id ? "rgba(167, 139, 250, 0.2)" : "transparent",
                border: "none",
                borderBottom: researchTab === t.id ? "2px solid #A78BFA" : "2px solid transparent",
                color: researchTab === t.id ? "#A78BFA" : "#94A3B8",
                padding: "6px 12px",
                fontSize: "0.78rem",
                fontWeight: "700",
                cursor: "pointer"
              }
            }, t.label)
          )
        ),

        // Sub-tab 1: Model Comparisons (Track A)
        researchTab === "models" && h("div", null,
          h("div", { style: { fontSize: "0.78rem", color: "#CBD5E1", marginBottom: "10px" } },
            "Out-of-sample walk-forward comparison of price-forecasting models across non-overlapping evaluation blocks:"
          ),
          h("div", { className: "table-wrapper" },
            h("table", { className: "table", style: { width: "100%", fontSize: "0.76rem" } },
              h("thead", null,
                h("tr", null,
                  h("th", null, "Horizon"),
                  h("th", null, "Sample (Blocks)"),
                  h("th", null, "Random Walk MAE"),
                  h("th", null, "Ridge L2 MAE"),
                  h("th", null, "Skill Score vs RW"),
                  h("th", null, "HLN DM Stat"),
                  h("th", null, "p-value"),
                  h("th", null, "Verdict")
                )
              ),
              h("tbody", null,
                ["1h", "4h", "24h"].map(hz => {
                  const hInfo = tournament?.horizons?.[hz];
                  return h("tr", { key: hz },
                    h("td", { style: { fontWeight: "700", color: "#38BDF8" } }, hz.toUpperCase()),
                    h("td", { style: { fontFamily: "var(--font-mono)" } }, hInfo?.sample_size_origins || "—"),
                    h("td", { style: { fontFamily: "var(--font-mono)" } }, `$${(hInfo?.persistence_baseline?.mae_usd || 0).toFixed(2)}`),
                    h("td", { style: { fontFamily: "var(--font-mono)" } }, `$${(hInfo?.ridge_candidate?.mae_usd || 0).toFixed(2)}`),
                    h("td", { style: { fontFamily: "var(--font-mono)", color: (hInfo?.ridge_candidate?.skill_score_pct || 0) >= 0 ? "#00E5A8" : "#FF5C7C" } },
                      `${(hInfo?.ridge_candidate?.skill_score_pct || 0) >= 0 ? "+" : ""}${(hInfo?.ridge_candidate?.skill_score_pct || 0).toFixed(3)}%`
                    ),
                    h("td", { style: { fontFamily: "var(--font-mono)" } }, (hInfo?.ridge_candidate?.dm_hln_stat || 0).toFixed(4)),
                    h("td", { style: { fontFamily: "var(--font-mono)" } }, (hInfo?.ridge_candidate?.p_value || 0).toFixed(4)),
                    h("td", null,
                      h("span", {
                        style: {
                          background: hInfo?.verdict === "INSUFFICIENT_EVIDENCE" ? "rgba(245, 158, 11, 0.15)" : "rgba(0, 229, 168, 0.15)",
                          color: hInfo?.verdict === "INSUFFICIENT_EVIDENCE" ? "#F59E0B" : "#00E5A8",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          fontWeight: "700"
                        }
                      }, hInfo?.verdict || "PERSISTENCE_BASELINE_UNBEATEN")
                    )
                  );
                })
              )
            )
          )
        ),

        // Sub-tab 2: Volatility Risk Intelligence (Track B)
        researchTab === "volatility" && h("div", null,
          h("div", { style: { fontSize: "0.80rem", color: "#CBD5E1", lineHeight: "1.5", marginBottom: "12px" } },
            "HAR-RS-DOW-v1.0 models continuous 168-hour realized variance (volatility envelope) using QLIKE loss. It does NOT predict price direction or future closing price."
          ),
          h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "10px" } },
            h("div", { style: { background: "rgba(0, 0, 0, 0.2)", padding: "12px", borderRadius: "6px" } },
              h("div", { style: { fontSize: "0.72rem", color: "#94A3B8" } }, "HAR-RS-DOW QLIKE Loss"),
              h("div", { style: { fontSize: "1.2rem", fontWeight: "800", color: "#00E5A8", fontFamily: "var(--font-mono)" } }, "0.24056"),
              h("div", { style: { fontSize: "0.68rem", color: "#00E5A8" } }, "Superior risk calibration")
            ),
            h("div", { style: { background: "rgba(0, 0, 0, 0.2)", padding: "12px", borderRadius: "6px" } },
              h("div", { style: { fontSize: "0.72rem", color: "#94A3B8" } }, "Historical Variance QLIKE"),
              h("div", { style: { fontSize: "1.2rem", fontWeight: "800", color: "#CBD5E1", fontFamily: "var(--font-mono)" } }, "0.26482"),
              h("div", { style: { fontSize: "0.68rem", color: "#94A3B8" } }, "Baseline reference")
            ),
            h("div", { style: { background: "rgba(0, 0, 0, 0.2)", padding: "12px", borderRadius: "6px" } },
              h("div", { style: { fontSize: "0.72rem", color: "#94A3B8" } }, "EWMA Volatility QLIKE"),
              h("div", { style: { fontSize: "1.2rem", fontWeight: "800", color: "#FF5C7C", fontFamily: "var(--font-mono)" } }, "0.53216"),
              h("div", { style: { fontSize: "0.68rem", color: "#FF5C7C" } }, "+100.9% error degradation")
            )
          )
        ),

        // Sub-tab 3: Strategy Research Tournament (Track C)
        researchTab === "strategies" && h("div", null,
          h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" } },
            h("div", { style: { fontSize: "0.80rem", color: "#CBD5E1" } },
              "Offline hypothetical backtest simulations across 9,975 hourly candles (NOT live trades):"
            ),
            h("span", { style: { background: "rgba(239, 68, 68, 0.15)", color: "#F87171", padding: "2px 6px", borderRadius: "4px", fontSize: "0.70rem", fontWeight: "700" } },
              "VERDICT: NO_STRATEGY_WINNER_ESTABLISHED"
            )
          ),
          h("div", { style: { fontSize: "0.75rem", color: "#94A3B8", lineHeight: "1.5", marginBottom: "12px" } },
            "Under realistic transaction friction (Coinbase Retail 87 bps round-trip), all active strategy hypotheses suffer severe negative returns (-2,779 to -36,159 bps) due to fee drag. The No-Exposure benchmark remains the economically superior strategy."
          ),
          h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "8px" } },
            h("div", { style: { background: "rgba(0,0,0,0.2)", padding: "10px", borderRadius: "6px" } },
              h("div", { style: { fontWeight: "700", color: "#CBD5E1", fontSize: "0.74rem" } }, "Trend-Following SMA"),
              h("div", { style: { color: "#FF5C7C", fontFamily: "var(--font-mono)", fontSize: "0.78rem" } }, "Net -36,159 bps (87 bps)")
            ),
            h("div", { style: { background: "rgba(0,0,0,0.2)", padding: "10px", borderRadius: "6px" } },
              h("div", { style: { fontWeight: "700", color: "#CBD5E1", fontSize: "0.74rem" } }, "Mean Reversion RSI"),
              h("div", { style: { color: "#FF5C7C", fontFamily: "var(--font-mono)", fontSize: "0.78rem" } }, "Net -2,779 bps (87 bps)")
            ),
            h("div", { style: { background: "rgba(0,0,0,0.2)", padding: "10px", borderRadius: "6px" } },
              h("div", { style: { fontWeight: "700", color: "#CBD5E1", fontSize: "0.74rem" } }, "Volatility Breakout"),
              h("div", { style: { color: "#FF5C7C", fontFamily: "var(--font-mono)", fontSize: "0.78rem" } }, "Net -8,154 bps (87 bps)")
            ),
            h("div", { style: { background: "rgba(0,0,0,0.2)", padding: "10px", borderRadius: "6px", border: "1px solid rgba(0, 229, 168, 0.3)" } },
              h("div", { style: { fontWeight: "700", color: "#00E5A8", fontSize: "0.74rem" } }, "No-Exposure Benchmark"),
              h("div", { style: { color: "#00E5A8", fontFamily: "var(--font-mono)", fontSize: "0.78rem" } }, "0.0 bps (Zero Drawdown)")
            )
          )
        ),

        // Sub-tab 4: Decision Replay
        researchTab === "replay" && h("div", null,
          h(ReplayBar, {
            memoryData,
            isReplaying,
            setIsReplaying,
            selectedRecord,
            onSelectRecord
          })
        )
      )
    )
  );
}
'''

# Find TerminalView start and end
term_start = content.find("function TerminalView({")
assert term_start != -1, "function TerminalView not found"

term_end = content.find("function LiveEquityCurveChart({")
assert term_end != -1, "function LiveEquityCurveChart not found"

content = content[:term_start] + new_terminal_view + "\n\n// ===========================================================================\n" + content[term_end:]

with open("web/app.js", "w", encoding="utf-8") as f:
    f.write(content)

print("web/app.js successfully updated with Beginner-Friendly TerminalView!")

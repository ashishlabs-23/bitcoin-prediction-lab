import os

app_js_path = os.path.join("web", "app.js")

with open(app_js_path, "r", encoding="utf-8") as f:
    content = f.read()

# Locate function EntryTpSlResearchPanel
target_start = "function EntryTpSlResearchPanel() {"
start_idx = content.find(target_start)
if start_idx == -1:
    raise ValueError("Could not find function EntryTpSlResearchPanel in web/app.js")

# Find the end of EntryTpSlResearchPanel, which is right before FuturePriceForecastingPanel
target_end = "// FuturePriceForecastingPanel"
end_idx = content.find(target_end, start_idx)
if end_idx == -1:
    raise ValueError("Could not find FuturePriceForecastingPanel after EntryTpSlResearchPanel")

# Scan backwards from end_idx to find the closing bracket and double newline
# Let's inspect the slice
snippet = content[start_idx:end_idx]
print(f"Found EntryTpSlResearchPanel spanning {len(snippet)} chars from {start_idx} to {end_idx}")

new_component = """function EntryTpSlResearchPanel() {
  const [subTab, setSubTab] = useState("evaluator");
  const [side, setSide] = useState("LONG");
  const [k_tp, setKTp] = useState(1.5);
  const [k_sl, setKSl] = useState(1.0);
  const [threshold, setThreshold] = useState(0.60);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchQuality = useCallback(() => {
    setLoading(true);
    setError(null);
    const apiBase = getApiBaseUrl();
    const url = `${apiBase}/api/research/entry-quality?side=${side}&k_tp=${k_tp}&k_sl=${k_sl}&threshold=${threshold}`;
    fetch(url)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(res => {
        setData(res);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [side, k_tp, k_sl, threshold]);

  useEffect(() => {
    fetchQuality();
  }, [fetchQuality]);

  const decision = data?.decision;
  const features = data?.features_evaluated || {};
  const probs = decision?.probabilities || {};
  const recentRecords = data?.recent_prospective_records || [];

  const wfModels = [
    { name: "B0: Matched Random", count: "10,105", winRate: "25.7%", meanNetR: "-1.2112R", ci95: "[-1.2577R, -1.1573R]", pf: "0.07", status: "Negative Expectancy" },
    { name: "B0b: Always Long", count: "10,142", winRate: "26.1%", meanNetR: "-1.1900R", ci95: "[-1.2394R, -1.1336R]", pf: "0.08", status: "Baseline Reference" },
    { name: "B0b: Always Short", count: "10,102", winRate: "25.7%", meanNetR: "-1.2110R", ci95: "[-1.2598R, -1.1549R]", pf: "0.07", status: "Baseline Reference" },
    { name: "B3: Structural Rule (A1/A2)", count: "20,244", winRate: "25.9%", meanNetR: "-1.2005R", ci95: "[-1.2361R, -1.1576R]", pf: "0.07", status: "Unfiltered Rule (B3 > B0)" },
    { name: "B3b: Setup + Trend Filter", count: "1,665", winRate: "18.7%", meanNetR: "-1.5708R", ci95: "[-1.7242R, -1.3850R]", pf: "0.04", status: "Simple Trend Rule" },
    { name: "B4-lite: Logistic Meta-Model", count: "2,916", winRate: "46.9%", meanNetR: "-0.4673R", ci95: "[-0.4984R, -0.4290R]", pf: "0.37", status: "Linear Meta-Model" },
    { name: "B4: LightGBM (BASE: 35 bps)", count: "1,553", winRate: "47.1%", meanNetR: "-0.5678R", ci95: "[-0.6220R, -0.5064R]", pf: "0.29", status: "Primary Candidate (Cost-Erased)" },
    { name: "B4: LightGBM (CONSERVATIVE: 65 bps)", count: "1,553", winRate: "25.2%", meanNetR: "-1.0954R", ci95: "[-1.1657R, -1.0171R]", pf: "0.07", status: "Friction Stressed" }
  ];

  const barrierGrid = [
    { id: "barrier_pair_01", tpSl: "1.0 / 1.0 (Frozen 6A)", meanR: "-0.5678R", ci: "[-0.6220R, -0.5064R]", wr: "47.1%", pf: "0.29" },
    { id: "barrier_pair_02", tpSl: "2.0 / 1.0", meanR: "-0.5683R", ci: "[-0.6262R, -0.5024R]", wr: "37.4%", pf: "0.39" },
    { id: "barrier_pair_03", tpSl: "3.0 / 1.0", meanR: "-0.5813R", ci: "[-0.6379R, -0.5152R]", wr: "31.5%", pf: "0.42" },
    { id: "barrier_pair_04", tpSl: "1.0 / 1.0", meanR: "-0.7523R", ci: "[-0.8201R, -0.6751R]", wr: "39.9%", pf: "0.18" },
    { id: "barrier_pair_05", tpSl: "2.0 / 1.5", meanR: "-0.3842R", ci: "[-0.4284R, -0.3361R]", wr: "38.6%", pf: "0.47" }
  ];

  const taxonomy = [
    { code: "NO_SETUP", name: "No Setup Detected", meaning: "Neither A1 nor A2 structural conditions met at t0." },
    { code: "MODEL_UNCERTAIN", name: "Model Neutral", meaning: "Calibrated probability within neutral uncertainty envelope [47%, 53%]." },
    { code: "EV_BELOW_COST", name: "Edge Cost-Erased", meaning: "Directional edge observed, but net expectancy E[R_net] <= 0 under transaction friction (35-87 bps)." },
    { code: "NEGATIVE_EXPECTANCY_AFTER_COSTS", name: "Negative Expectancy", meaning: "E[R_gross] is insufficient to overcome round-trip friction in R-multiples." },
    { code: "WIN_PROBABILITY_BELOW_SELECTIVE_THRESHOLD", name: "Below Threshold", meaning: "Predicted target-hit probability is below selective filtering hurdle." },
    { code: "EXECUTION_UNSAFE", name: "Execution Risk", meaning: "Spread or slippage exceeds safety bounds." },
    { code: "DATA_UNAVAILABLE", name: "Missing Data", meaning: "Incomplete bar stream or timestamp discontinuity." },
    { code: "PROVENANCE_FAILURE", name: "Integrity Mismatch", meaning: "Dataset SHA-256 hash or contract freeze verification failed." }
  ];

  const isAbstain = decision?.action === "ABSTAIN";

  return h("div", { className: "glass-card", style: { padding: "24px" } },
    // Governance Banner
    h("div", {
      style: {
        background: "rgba(239,68,68,0.12)",
        border: "1px solid rgba(239,68,68,0.35)",
        borderRadius: "10px",
        padding: "16px",
        marginBottom: "20px"
      }
    },
      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" } },
        h("div", null,
          h("div", { style: { color: "#EF4444", fontWeight: "800", fontSize: "0.85rem", letterSpacing: "0.5px" } }, "🔬 BTCognitive V28 — Probabilistic Entry Quality Engine & Selective Trade Research"),
          h("div", { style: { color: "#F8FAFC", fontSize: "1.1rem", fontWeight: "700", marginTop: "4px" } }, "Epistemic Verdict: 70–80% Win Rate Is An Aspirational Hypothesis (Cost-Erased Under Reality)"),
          h("div", { style: { color: "#94A3B8", fontSize: "0.76rem", marginTop: "4px" } }, "Analysis-Only Research Environment • Zero Live Orders • Causal Fills (t0 + dt Next Open) • Conservative SL_FIRST Collisions")
        ),
        h("div", { style: { display: "flex", gap: "8px" } },
          h("span", {
            style: {
              background: "#EF4444",
              color: "#FFFFFF",
              padding: "4px 10px",
              borderRadius: "6px",
              fontWeight: "700",
              fontSize: "0.75rem"
            }
          }, "OFFLINE RESEARCH ONLY"),
          h("span", {
            style: {
              background: "rgba(245, 158, 11, 0.2)",
              color: "#F59E0B",
              border: "1px solid #F59E0B",
              padding: "4px 10px",
              borderRadius: "6px",
              fontWeight: "700",
              fontSize: "0.75rem"
            }
          }, "TRADING DISABLED")
        )
      )
    ),

    // Sub-tab Navigation
    h("div", { style: { display: "flex", gap: "8px", marginBottom: "20px", flexWrap: "wrap", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "10px" } },
      [
        { id: "evaluator", label: "🎯 Candidate Evaluator & Gating" },
        { id: "benchmarks", label: "📊 Walk-Forward Benchmarks (B0-B4)" },
        { id: "grid", label: "📐 Barrier Parameterization Grid" },
        { id: "taxonomy", label: "🏷️ Abstention Taxonomy" },
        { id: "prospective", label: "📜 Prospective Ledger Audit" }
      ].map(t =>
        h("button", {
          key: t.id,
          onClick: () => setSubTab(t.id),
          style: {
            background: subTab === t.id ? "rgba(56,189,248,0.2)" : "transparent",
            border: subTab === t.id ? "1px solid #38BDF8" : "1px solid transparent",
            color: subTab === t.id ? "#38BDF8" : "#94A3B8",
            padding: "6px 14px",
            borderRadius: "6px",
            fontSize: "0.8rem",
            fontWeight: "700",
            cursor: "pointer"
          }
        }, t.label)
      )
    ),

    // 1. Live Evaluator View
    subTab === "evaluator" && h("div", null,
      // Parameter Controls
      h("div", {
        style: {
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: "8px",
          padding: "14px",
          marginBottom: "18px",
          display: "flex",
          flexWrap: "wrap",
          gap: "16px",
          alignItems: "center"
        }
      },
        h("div", { style: { display: "flex", alignItems: "center", gap: "8px" } },
          h("span", { style: { color: "#94A3B8", fontSize: "0.78rem", fontWeight: "600" } }, "Side:"),
          ["LONG", "SHORT"].map(s =>
            h("button", {
              key: s,
              onClick: () => setSide(s),
              style: {
                background: side === s ? (s === "LONG" ? "#10B981" : "#EF4444") : "rgba(255,255,255,0.05)",
                color: side === s ? "#FFF" : "#94A3B8",
                border: "none",
                padding: "4px 12px",
                borderRadius: "4px",
                fontWeight: "700",
                fontSize: "0.75rem",
                cursor: "pointer"
              }
            }, s)
          )
        ),
        h("div", { style: { display: "flex", alignItems: "center", gap: "8px" } },
          h("span", { style: { color: "#94A3B8", fontSize: "0.78rem", fontWeight: "600" } }, "Target (k_TP):"),
          [1.0, 1.5, 2.0, 3.0].map(val =>
            h("button", {
              key: val,
              onClick: () => setKTp(val),
              style: {
                background: k_tp === val ? "#38BDF8" : "rgba(255,255,255,0.05)",
                color: k_tp === val ? "#0F172A" : "#94A3B8",
                border: "none",
                padding: "4px 10px",
                borderRadius: "4px",
                fontWeight: "700",
                fontSize: "0.75rem",
                cursor: "pointer"
              }
            }, `${val}σ`)
          )
        ),
        h("div", { style: { display: "flex", alignItems: "center", gap: "8px" } },
          h("span", { style: { color: "#94A3B8", fontSize: "0.78rem", fontWeight: "600" } }, "Stop (k_SL):"),
          [0.5, 1.0, 1.5].map(val =>
            h("button", {
              key: val,
              onClick: () => setKSl(val),
              style: {
                background: k_sl === val ? "#F59E0B" : "rgba(255,255,255,0.05)",
                color: k_sl === val ? "#0F172A" : "#94A3B8",
                border: "none",
                padding: "4px 10px",
                borderRadius: "4px",
                fontWeight: "700",
                fontSize: "0.75rem",
                cursor: "pointer"
              }
            }, `${val}σ`)
          )
        ),
        h("div", { style: { display: "flex", alignItems: "center", gap: "8px" } },
          h("span", { style: { color: "#94A3B8", fontSize: "0.78rem", fontWeight: "600" } }, "Selective Hurdle (θ):"),
          [0.50, 0.60, 0.70, 0.80].map(val =>
            h("button", {
              key: val,
              onClick: () => setThreshold(val),
              style: {
                background: threshold === val ? "#A855F7" : "rgba(255,255,255,0.05)",
                color: threshold === val ? "#FFF" : "#94A3B8",
                border: "none",
                padding: "4px 10px",
                borderRadius: "4px",
                fontWeight: "700",
                fontSize: "0.75rem",
                cursor: "pointer"
              }
            }, `${Math.round(val*100)}%`)
          )
        ),
        h("button", {
          onClick: fetchQuality,
          style: {
            marginLeft: "auto",
            background: "rgba(56,189,248,0.15)",
            border: "1px solid #38BDF8",
            color: "#38BDF8",
            padding: "4px 14px",
            borderRadius: "4px",
            fontSize: "0.75rem",
            fontWeight: "700",
            cursor: "pointer"
          }
        }, loading ? "Evaluating..." : "🔄 Re-Evaluate")
      ),

      // Decision Card
      loading && h("div", { style: { color: "#94A3B8", padding: "20px", textAlign: "center" } }, "Evaluating point-in-time setup and barrier probabilities..."),
      error && h("div", { style: { color: "#EF4444", padding: "20px" } }, `Error loading entry quality: ${error}`),
      decision && !loading && h("div", null,
        // Verdict Bar
        h("div", {
          style: {
            background: isAbstain ? "rgba(245, 158, 11, 0.12)" : "rgba(16, 185, 129, 0.12)",
            border: isAbstain ? "1px solid rgba(245, 158, 11, 0.4)" : "1px solid rgba(16, 185, 129, 0.4)",
            borderRadius: "8px",
            padding: "16px",
            marginBottom: "16px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "12px"
          }
        },
          h("div", null,
            h("div", { style: { color: isAbstain ? "#F59E0B" : "#10B981", fontWeight: "800", fontSize: "1.05rem" } },
              `DECISION: ${decision.action}`
            ),
            h("div", { style: { color: "#CBD5E1", fontSize: "0.82rem", marginTop: "3px" } },
              `Primary Reason: ${decision.primary_reason}`
            )
          ),
          h("div", { style: { textAlign: "right" } },
            h("div", { style: { color: "#94A3B8", fontSize: "0.75rem" } }, "EXPECTED NET VALUE (E[R_net])"),
            h("div", {
              style: {
                color: decision.expected_net_r > 0 ? "#10B981" : "#EF4444",
                fontSize: "1.25rem",
                fontWeight: "800"
              }
            }, `${decision.expected_net_r > 0 ? "+" : ""}${decision.expected_net_r} R`),
            h("div", { style: { color: "#94A3B8", fontSize: "0.70rem" } }, `Gross: ${decision.expected_gross_r} R | Friction: -${decision.friction_r} R`)
          )
        ),

        // 3-Column Metrics Grid
        h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "14px", marginBottom: "16px" } },
          // Col 1: Setup Geometry
          h("div", { style: { background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "8px", padding: "14px" } },
            h("div", { style: { color: "#38BDF8", fontWeight: "700", fontSize: "0.80rem", marginBottom: "8px" } }, "📐 SETUP GEOMETRY (CAUSAL)"),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, "Candidate Side:"),
              h("strong", { style: { color: decision.side === "LONG" ? "#10B981" : "#EF4444" } }, decision.side)
            ),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, "Executable Entry Ref:"),
              h("strong", { style: { color: "#F8FAFC" } }, `$${decision.entry_reference_price.toLocaleString()}`)
            ),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, `Profit Target (+${decision.k_tp}σ):`),
              h("strong", { style: { color: "#10B981" } }, `$${decision.tp_price.toLocaleString()}`)
            ),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, `Stop Loss (-${decision.k_sl}σ):`),
              h("strong", { style: { color: "#EF4444" } }, `$${decision.sl_price.toLocaleString()}`)
            ),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, "Risk Unit (1R):"),
              h("strong", { style: { color: "#F8FAFC" } }, `$${decision.risk_unit_usd.toFixed(2)}`)
            ),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, "Horizon Limit:"),
              h("strong", { style: { color: "#F8FAFC" } }, "24 Hours (Max Holding)")
            )
          ),

          // Col 2: Calibrated Probabilities
          h("div", { style: { background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "8px", padding: "14px" } },
            h("div", { style: { color: "#A855F7", fontWeight: "700", fontSize: "0.80rem", marginBottom: "8px" } }, "🎯 CALIBRATED PROBABILITIES"),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, "p(Target First):"),
              h("strong", { style: { color: probs.p_tp >= threshold ? "#10B981" : "#F59E0B" } }, `${(probs.p_tp * 100).toFixed(1)}%`)
            ),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, "p(Stop First):"),
              h("strong", { style: { color: "#EF4444" } }, `${(probs.p_sl * 100).toFixed(1)}%`)
            ),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, "p(Timeout / Unresolved):"),
              h("strong", { style: { color: "#94A3B8" } }, `${(probs.p_timeout * 100).toFixed(1)}%`)
            ),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, "Expected Brier Score:"),
              h("strong", { style: { color: "#F8FAFC" } }, probs.brier_score_expected)
            ),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, "Intrabar Collision Rule:"),
              h("strong", { style: { color: "#EF4444" } }, "SL_FIRST (Conservative)")
            ),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, "Calibration Status:"),
              h("strong", { style: { color: "#10B981" } }, "Isotonic Monotonic")
            )
          ),

          // Col 3: Point-in-Time Features
          h("div", { style: { background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "8px", padding: "14px" } },
            h("div", { style: { color: "#10B981", fontWeight: "700", fontSize: "0.80rem", marginBottom: "8px" } }, "⚡ POINT-IN-TIME FEATURES (t0)"),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, "1h Momentum:"),
              h("strong", { style: { color: features.mom_1h >= 0 ? "#10B981" : "#EF4444" } }, `${(features.mom_1h * 100).toFixed(3)}%`)
            ),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, "4h Momentum:"),
              h("strong", { style: { color: features.mom_4h >= 0 ? "#10B981" : "#EF4444" } }, `${(features.mom_4h * 100).toFixed(3)}%`)
            ),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, "24h Momentum:"),
              h("strong", { style: { color: features.mom_24h >= 0 ? "#10B981" : "#EF4444" } }, `${(features.mom_24h * 100).toFixed(3)}%`)
            ),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, "Realized Semi-Var Ratio:"),
              h("strong", { style: { color: "#F8FAFC" } }, features.rs_ratio)
            ),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, "Bollinger Bandwidth:"),
              h("strong", { style: { color: "#F8FAFC" } }, `${(features.bb_width * 100).toFixed(2)}%`)
            ),
            h("div", { style: { display: "flex", justifyContent: "space-between", padding: "3px 0", fontSize: "0.76rem" } },
              h("span", { style: { color: "#94A3B8" } }, "24h Range Position:"),
              h("strong", { style: { color: "#F8FAFC" } }, features.range_pos)
            )
          )
        )
      )
    ),

    // 2. Walk-Forward Benchmarks View
    subTab === "benchmarks" && h("div", { style: { overflowX: "auto" } },
      h("table", { className: "research-table", style: { width: "100%", borderCollapse: "collapse", fontSize: "0.78rem" } },
        h("thead", null,
          h("tr", { style: { borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#94A3B8" } },
            h("th", { style: { textAlign: "left", padding: "8px" } }, "Model / Policy"),
            h("th", { style: { textAlign: "right", padding: "8px" } }, "Sample N"),
            h("th", { style: { textAlign: "right", padding: "8px" } }, "Win Rate"),
            h("th", { style: { textAlign: "right", padding: "8px" } }, "Mean Net R"),
            h("th", { style: { textAlign: "right", padding: "8px" } }, "95% CI (Net R)"),
            h("th", { style: { textAlign: "right", padding: "8px" } }, "Profit Factor"),
            h("th", { style: { textAlign: "left", padding: "8px" } }, "Status")
          )
        ),
        h("tbody", null,
          wfModels.map(m =>
            h("tr", { key: m.name, style: { borderBottom: "1px solid rgba(255,255,255,0.04)" } },
              h("td", { style: { padding: "8px", fontWeight: "600", color: "#F8FAFC" } }, m.name),
              h("td", { style: { textAlign: "right", padding: "8px", color: "#CBD5E1" } }, m.count),
              h("td", { style: { textAlign: "right", padding: "8px", color: m.winRate.startsWith("4") ? "#38BDF8" : "#CBD5E1" } }, m.winRate),
              h("td", { style: { textAlign: "right", padding: "8px", color: "#EF4444", fontWeight: "700" } }, m.meanNetR),
              h("td", { style: { textAlign: "right", padding: "8px", color: "#94A3B8", fontFamily: "JetBrains Mono, monospace" } }, m.ci95),
              h("td", { style: { textAlign: "right", padding: "8px", color: "#CBD5E1" } }, m.pf),
              h("td", { style: { padding: "8px", color: "#F59E0B", fontSize: "0.72rem" } }, m.status)
            )
          )
        )
      )
    ),

    // 3. Grid View
    subTab === "grid" && h("div", { style: { overflowX: "auto" } },
      h("table", { className: "research-table", style: { width: "100%", borderCollapse: "collapse", fontSize: "0.78rem" } },
        h("thead", null,
          h("tr", { style: { borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#94A3B8" } },
            h("th", { style: { textAlign: "left", padding: "8px" } }, "Barrier Pair ID"),
            h("th", { style: { textAlign: "left", padding: "8px" } }, "TP / SL Ratio"),
            h("th", { style: { textAlign: "right", padding: "8px" } }, "Mean Net R"),
            h("th", { style: { textAlign: "right", padding: "8px" } }, "95% CI (Net R)"),
            h("th", { style: { textAlign: "right", padding: "8px" } }, "Win Rate"),
            h("th", { style: { textAlign: "right", padding: "8px" } }, "Profit Factor")
          )
        ),
        h("tbody", null,
          barrierGrid.map(g =>
            h("tr", { key: g.id, style: { borderBottom: "1px solid rgba(255,255,255,0.04)" } },
              h("td", { style: { padding: "8px", color: "#38BDF8", fontFamily: "JetBrains Mono, monospace" } }, g.id),
              h("td", { style: { padding: "8px", fontWeight: "600", color: "#F8FAFC" } }, g.tpSl),
              h("td", { style: { textAlign: "right", padding: "8px", color: "#EF4444", fontWeight: "700" } }, g.meanR),
              h("td", { style: { textAlign: "right", padding: "8px", color: "#94A3B8", fontFamily: "JetBrains Mono, monospace" } }, g.ci),
              h("td", { style: { textAlign: "right", padding: "8px", color: "#CBD5E1" } }, g.wr),
              h("td", { style: { textAlign: "right", padding: "8px", color: "#CBD5E1" } }, g.pf)
            )
          )
        )
      )
    ),

    // 4. Abstention Taxonomy View
    subTab === "taxonomy" && h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px" } },
      taxonomy.map(t =>
        h("div", { key: t.code, style: { background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "8px", padding: "12px" } },
          h("div", { style: { color: "#F59E0B", fontWeight: "800", fontSize: "0.76rem", fontFamily: "JetBrains Mono, monospace" } }, t.code),
          h("div", { style: { color: "#F8FAFC", fontWeight: "700", fontSize: "0.82rem", margin: "3px 0" } }, t.name),
          h("div", { style: { color: "#94A3B8", fontSize: "0.74rem", lineHeight: "1.4" } }, t.meaning)
        )
      )
    ),

    // 5. Prospective Ledger View
    subTab === "prospective" && h("div", { style: { overflowX: "auto" } },
      recentRecords.length === 0 ? (
        h("div", { style: { color: "#94A3B8", padding: "20px", textAlign: "center" } }, "No prospective records found in ledger yet.")
      ) : (
        h("table", { className: "research-table", style: { width: "100%", borderCollapse: "collapse", fontSize: "0.74rem" } },
          h("thead", null,
            h("tr", { style: { borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#94A3B8" } },
              h("th", { style: { textAlign: "left", padding: "6px" } }, "Timestamp (UTC)"),
              h("th", { style: { textAlign: "left", padding: "6px" } }, "Side"),
              h("th", { style: { textAlign: "right", padding: "6px" } }, "Entry Ref"),
              h("th", { style: { textAlign: "right", padding: "6px" } }, "TP Ref"),
              h("th", { style: { textAlign: "right", padding: "6px" } }, "SL Ref"),
              h("th", { style: { textAlign: "right", padding: "6px" } }, "p(TP)"),
              h("th", { style: { textAlign: "right", padding: "6px" } }, "Net E[R]"),
              h("th", { style: { textAlign: "left", padding: "6px" } }, "Action"),
              h("th", { style: { textAlign: "left", padding: "6px" } }, "Reason")
            )
          ),
          h("tbody", null,
            recentRecords.map((r, i) =>
              h("tr", { key: i, style: { borderBottom: "1px solid rgba(255,255,255,0.03)" } },
                h("td", { style: { padding: "6px", color: "#94A3B8", fontFamily: "JetBrains Mono, monospace" } }, r.decision_timestamp_utc ? r.decision_timestamp_utc.slice(0, 19).replace('T', ' ') : "--"),
                h("td", { style: { padding: "6px", fontWeight: "700", color: r.side === "LONG" ? "#10B981" : "#EF4444" } }, r.side),
                h("td", { style: { textAlign: "right", padding: "6px", color: "#CBD5E1" } }, `$${r.entry_reference_price}`),
                h("td", { style: { textAlign: "right", padding: "6px", color: "#10B981" } }, `$${r.tp_price}`),
                h("td", { style: { textAlign: "right", padding: "6px", color: "#EF4444" } }, `$${r.sl_price}`),
                h("td", { style: { textAlign: "right", padding: "6px", color: "#38BDF8" } }, `${(r.probabilities?.p_tp * 100).toFixed(1)}%`),
                h("td", { style: { textAlign: "right", padding: "6px", color: r.expected_net_r > 0 ? "#10B981" : "#EF4444", fontWeight: "700" } }, `${r.expected_net_r} R`),
                h("td", { style: { padding: "6px", color: r.action === "ABSTAIN" ? "#F59E0B" : "#10B981", fontWeight: "700" } }, r.action),
                h("td", { style: { padding: "6px", color: "#94A3B8", fontSize: "0.70rem" } }, r.primary_reason)
              )
            )
          )
        )
      )
    )
  );
}

"""

updated = content[:start_idx] + new_component + content[end_idx:]

with open(app_js_path, "w", encoding="utf-8") as f:
    f.write(updated)

print("Successfully replaced EntryTpSlResearchPanel in web/app.js!")

import sys

with open('web/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

replacements = [
    ('h("section", { className: "glass-card", style: { padding: "20px 24px", marginBottom: "20px", borderRadius: "12px", border: "1px solid rgba(255, 255, 255, 0.08)" } },\n      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", marginBottom: "16px" } },\n        h("div", null,\n          h("div", { style: { fontSize: "0.78rem", color: "#94A3B8", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.05em", marginBottom: "4px" } },\n            "BTCUSD RIGHT NOW"',
     'h("section", { id: "v19-area-btc-now", className: "glass-card", style: { padding: "20px 24px", marginBottom: "20px", borderRadius: "12px", border: "1px solid rgba(255, 255, 255, 0.08)" } },\n      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", marginBottom: "16px" } },\n        h("div", null,\n          h("div", { style: { fontSize: "0.78rem", color: "#94A3B8", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.05em", marginBottom: "4px" } },\n            "BTCUSD RIGHT NOW"'),

    ('h("section", { className: "glass-card", style: { padding: "20px 24px", marginBottom: "20px", borderRadius: "12px", border: "1px solid rgba(56, 189, 248, 0.2)" } },\n      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" } },\n        h("div", null,\n          h("div", { style: { fontSize: "0.78rem", color: "#38BDF8", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.05em", marginBottom: "2px" } },\n            "ESTIMATED FUTURE PRICE"',
     'h("section", { id: "v19-area-future-price", className: "glass-card", style: { padding: "20px 24px", marginBottom: "20px", borderRadius: "12px", border: "1px solid rgba(56, 189, 248, 0.2)" } },\n      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" } },\n        h("div", null,\n          h("div", { style: { fontSize: "0.78rem", color: "#38BDF8", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.05em", marginBottom: "2px" } },\n            "ESTIMATED FUTURE PRICE"'),

    ('h("section", { className: "glass-card", style: { padding: "18px 24px", marginBottom: "20px", borderRadius: "12px", border: "1px solid rgba(255, 255, 255, 0.08)" } },\n      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px", flexWrap: "wrap", gap: "8px" } },\n        h("div", { style: { fontSize: "0.78rem", color: "#94A3B8", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.05em" } },\n          "MARKET CONDITIONS"',
     'h("section", { id: "v19-area-market-conditions", className: "glass-card", style: { padding: "18px 24px", marginBottom: "20px", borderRadius: "12px", border: "1px solid rgba(255, 255, 255, 0.08)" } },\n      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px", flexWrap: "wrap", gap: "8px" } },\n        h("div", { style: { fontSize: "0.78rem", color: "#94A3B8", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.05em" } },\n          "MARKET CONDITIONS"'),

    ('h("section", { className: "glass-card", style: { padding: "18px 24px", marginBottom: "20px", borderRadius: "12px", border: "1px solid rgba(255, 255, 255, 0.08)" } },\n      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px", flexWrap: "wrap", gap: "8px" } },\n        h("div", { style: { fontSize: "0.78rem", color: "#94A3B8", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.05em" } },\n          "FORECAST RELIABILITY & EVIDENCE"',
     'h("section", { id: "v19-area-forecast-reliability", className: "glass-card", style: { padding: "18px 24px", marginBottom: "20px", borderRadius: "12px", border: "1px solid rgba(255, 255, 255, 0.08)" } },\n      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px", flexWrap: "wrap", gap: "8px" } },\n        h("div", { style: { fontSize: "0.78rem", color: "#94A3B8", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.05em" } },\n          "FORECAST RELIABILITY & EVIDENCE"'),

    ('h("section", { className: "glass-card", style: { padding: "20px 24px", marginBottom: "20px", borderRadius: "12px", border: "1px solid rgba(167, 139, 250, 0.25)" } },\n      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "10px" } },\n        h("div", null,\n          h("div", { style: { fontSize: "0.78rem", color: "#A78BFA", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.05em", marginBottom: "2px" } },\n            "RESEARCH: MODEL COMPARISONS & STRATEGY EXPERIMENTS"',
     'h("section", { id: "v19-area-research-tabs", className: "glass-card", style: { padding: "20px 24px", marginBottom: "20px", borderRadius: "12px", border: "1px solid rgba(167, 139, 250, 0.25)" } },\n      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "10px" } },\n        h("div", null,\n          h("div", { style: { fontSize: "0.78rem", color: "#A78BFA", textTransform: "uppercase", fontWeight: "700", letterSpacing: "0.05em", marginBottom: "2px" } },\n            "RESEARCH: MODEL COMPARISONS & STRATEGY EXPERIMENTS"')
]

for orig, rep in replacements:
    if orig not in c:
        print(f"FAILED TO FIND:\n{orig[:60]}")
        sys.exit(1)
    c = c.replace(orig, rep, 1)

with open('web/app.js', 'w', encoding='utf-8') as f:
    f.write(c)
print('Successfully injected v19-area IDs into web/app.js!')

import json

with open(r"C:\Projects\BTCognitive\BTCognitive\scripts\qa\browser_diagnostic_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

first_req = data.get("first_analysis_request", {})
print("=== FIRST ANALYSIS REQUEST ===")
print("URL:", first_req.get("url"))
print("Method:", first_req.get("method"))
print("Duration (ms):", first_req.get("duration_ms"))
print("Status:", first_req.get("status"))

post_data = first_req.get("post_data")
if post_data:
    pd_json = json.loads(post_data)
    print("Request ID:", pd_json.get("request_id"))
    print("Instrument:", pd_json.get("instrument"))
    print("Timeframe:", pd_json.get("timeframe"))
    print("Data Source:", pd_json.get("data_source"))
    print("Live Price:", pd_json.get("live_price"))
    print("Candles Count:", len(pd_json.get("candles") or []))
    print("Auto Tournament:", pd_json.get("auto_tournament"))

body = first_req.get("body_parsed", {})
if isinstance(body, dict):
    print("\n=== FIRST ANALYSIS RESPONSE ===")
    print("Action:", body.get("action"))
    print("Reason:", body.get("reason"))
    print("Market Regime:", body.get("market_regime"))
    print("Shortlisted Candidates:", len(body.get("shortlisted_candidates") or []))
    print("Candidate Rejections:", len(body.get("candidate_rejections") or []))
    print("Tournament Final Verdict:", (body.get("tournament") or {}).get("final_verdict"))
    print("Tournament Execution Source:", (body.get("tournament") or {}).get("execution_source"))
    print("Decision Status:", (body.get("decision") or {}).get("status"))
    print("Decision Action:", (body.get("decision") or {}).get("action"))

repeat_req = data.get("repeat_analysis_request", {})
print("\n=== REPEAT ANALYSIS REQUEST ===")
print("URL:", repeat_req.get("url"))
print("Duration (ms):", repeat_req.get("duration_ms"))
print("Status:", repeat_req.get("status"))
rep_post = repeat_req.get("post_data")
if rep_post:
    rp_json = json.loads(rep_post)
    print("Repeat Request ID:", rp_json.get("request_id"))
    print("Repeat Live Price:", rp_json.get("live_price"))

print("\n=== CONSOLE LOGS ===")
for l in data.get("console_logs", []):
    if l.get("type") in ("error", "warning", "uncaught_exception") or "Timing" in str(l) or "Error" in str(l) or "BTCognitive" in str(l):
        print(f"[{l.get('type')}]", l.get("args"))

print("\n=== POLLING TIMELINE SUMMARY ===")
polling = data.get("polling_timeline", [])
print(f"Total polling events: {len(polling)}")
sent_events = [e for e in polling if e.get("event") == "REQUEST_SENT"]
print(f"Total requests sent: {len(sent_events)}")
if sent_events:
    t0 = sent_events[0]["time"]
    t_end = sent_events[-1]["time"]
    elapsed_sec = t_end - t0
    print(f"Time span: {elapsed_sec:.2f} seconds")
    print(f"Average requests per second: {len(sent_events)/elapsed_sec:.2f}")
    print(f"Calculated requests per minute: {len(sent_events)/elapsed_sec * 60:.1f}")

# Check for 429
resp_429 = [r for r in data.get("completed_requests", []) if r.get("status") == 429]
print(f"HTTP 429 responses detected: {len(resp_429)}")


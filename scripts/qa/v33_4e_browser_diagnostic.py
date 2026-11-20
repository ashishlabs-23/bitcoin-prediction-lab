"""
BTCognitive V33.4E — End-to-End Analysis Failure Investigation
Automated Browser CDP Diagnostic Script.
Exercises the real dashboard UI in headless Chrome via Chrome DevTools Protocol.
Captures network traffic, console errors, polling loops, click interactions, and DOM state.
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
import asyncio
import json
import os
import shutil
import subprocess
import time
import urllib.request
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = os.path.join(os.environ["TEMP"], "chrome_v33_4e_diagnostic")
SERVER_URL = "http://127.0.0.1:8000/"

class BrowserDiagnostics:
    def __init__(self):
        self.proc = None
        self.ws = None
        self.msg_id = 0
        self.pending_commands = {}
        self.console_logs = []
        self.network_requests = {}
        self.completed_requests = []
        self.polling_timeline = []

    def start_chrome(self):
        if os.path.exists(USER_DATA_DIR):
            try:
                shutil.rmtree(USER_DATA_DIR)
            except Exception:
                pass
        cmd = [
            CHROME_PATH,
            "--headless=new",
            "--remote-debugging-port=9222",
            "--remote-allow-origins=*",
            f"--user-data-dir={USER_DATA_DIR}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-gpu",
            "--window-size=1600,1000",
            SERVER_URL
        ]
        print("[BrowserDiag] Spawning Chrome...")
        self.proc = subprocess.Popen(cmd)
        
        # Wait for CDP endpoint
        for _ in range(20):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen("http://127.0.0.1:9222/json") as resp:
                    tabs = json.loads(resp.read().decode())
                    target_tab = next((t for t in tabs if t.get("type") == "page" and "8000" in t.get("url", "")), None)
                    if target_tab:
                        print(f"[BrowserDiag] Found target page tab: {target_tab.get('title')}")
                        return target_tab["webSocketDebuggerUrl"]
            except Exception:
                pass
        raise RuntimeError("Could not connect to Chrome CDP endpoint on port 9222")

    async def send_command(self, method: str, params: dict = None):
        self.msg_id += 1
        cid = self.msg_id
        payload = {"id": cid, "method": method, "params": params or {}}
        future = asyncio.get_event_loop().create_future()
        self.pending_commands[cid] = future
        await self.ws.send(json.dumps(payload))
        return await future

    async def eval_js(self, expression: str):
        res = await self.send_command("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True
        })
        result = res.get("result", {})
        if "exceptionDetails" in result:
            return {"error": result["exceptionDetails"]}
        return result.get("result", {}).get("value")

    async def event_listener(self):
        while True:
            try:
                raw = await self.ws.recv()
                msg = json.loads(raw)
            except Exception:
                break

            if "id" in msg and msg["id"] in self.pending_commands:
                future = self.pending_commands.pop(msg["id"])
                if not future.done():
                    future.set_result(msg)
                continue

            method = msg.get("method")
            params = msg.get("params", {})

            # Console logging
            if method == "Runtime.consoleAPICalled":
                log_entry = {
                    "type": params.get("type"),
                    "args": [a.get("value") for a in params.get("args", [])],
                    "timestamp": time.time()
                }
                self.console_logs.append(log_entry)

            elif method == "Runtime.exceptionThrown":
                self.console_logs.append({
                    "type": "uncaught_exception",
                    "details": params.get("exceptionDetails"),
                    "timestamp": time.time()
                })

            # Network tracking
            elif method == "Network.requestWillBeSent":
                req_id = params.get("requestId")
                req = params.get("request", {})
                req_entry = {
                    "request_id": req_id,
                    "url": req.get("url"),
                    "method": req.get("method"),
                    "post_data": req.get("postData"),
                    "headers": req.get("headers"),
                    "started_at": time.time(),
                    "response": None,
                    "status": None
                }
                self.network_requests[req_id] = req_entry
                if "/api/" in req.get("url", ""):
                    self.polling_timeline.append({
                        "event": "REQUEST_SENT",
                        "url": req.get("url"),
                        "method": req.get("method"),
                        "time": time.time()
                    })

            elif method == "Network.responseReceived":
                req_id = params.get("requestId")
                resp = params.get("response", {})
                if req_id in self.network_requests:
                    req_entry = self.network_requests[req_id]
                    req_entry["status"] = resp.get("status")
                    req_entry["response_headers"] = resp.get("headers")
                    req_entry["finished_at"] = time.time()
                    req_entry["duration_ms"] = round((req_entry["finished_at"] - req_entry["started_at"]) * 1000, 2)
                    self.completed_requests.append(req_entry)
                    if "/api/" in req_entry["url"]:
                        self.polling_timeline.append({
                            "event": "RESPONSE_RECEIVED",
                            "url": req_entry["url"],
                            "status": resp.get("status"),
                            "duration_ms": req_entry["duration_ms"],
                            "time": time.time()
                        })

    async def get_response_body(self, req_id: str):
        try:
            res = await self.send_command("Network.getResponseBody", {"requestId": req_id})
            return res.get("result", {}).get("body")
        except Exception as e:
            return f"<failed to get response body: {e}>"

    async def run(self):
        ws_url = self.start_chrome()
        self.ws = await websockets.connect(ws_url, max_size=20*1024*1024)
        listener_task = asyncio.create_task(self.event_listener())

        # Enable CDP domains
        await self.send_command("Page.enable")
        await self.send_command("Runtime.enable")
        await self.send_command("Log.enable")
        await self.send_command("Network.enable")

        print("[BrowserDiag] CDP enabled. Waiting 6 seconds for initial render & baseline polling...")
        await asyncio.sleep(6)

        # Check DOM element for Smart Entry tab and button
        print("[BrowserDiag] Checking UI state...")
        dom_check = await self.eval_js("""
            (() => {
                const btnAnalyse = document.querySelector('#btn-analyse-setup') || document.querySelector('#btn-analyse-market');
                const tabSmartEntry = document.querySelector('#tab-btn-smart-entry');
                const warningBanner = document.querySelector('#smart-entry-warning-banner');
                const heroAnalyse = document.querySelector('#btn-hero-smart-entry');
                return {
                    url: window.location.href,
                    has_btn_analyse: !!btnAnalyse,
                    btn_id: btnAnalyse ? btnAnalyse.id : null,
                    btn_analyse_text: btnAnalyse ? btnAnalyse.innerText : null,
                    btn_analyse_disabled: btnAnalyse ? btnAnalyse.disabled : null,
                    has_tab_smart_entry: !!tabSmartEntry,
                    tab_smart_entry_active: tabSmartEntry ? tabSmartEntry.classList.contains('active') : null,
                    has_hero_analyse: !!heroAnalyse
                };
            })()
        """)
        print("[BrowserDiag] DOM Check result:", json.dumps(dom_check, indent=2))

        # If not already on smart entry tab, click it
        if not dom_check.get("has_btn_analyse"):
            print("[BrowserDiag] Button #btn-analyse-market not found on current view. Navigating to /smart-entry...")
            nav_result = await self.eval_js("""
                (() => {
                    const heroBtn = document.querySelector('#btn-hero-smart-entry');
                    if (heroBtn) { heroBtn.click(); return 'clicked #btn-hero-smart-entry'; }
                    const tabBtn = document.querySelector('#tab-btn-smart-entry');
                    if (tabBtn) { tabBtn.click(); return 'clicked #tab-btn-smart-entry'; }
                    return 'none found';
                })()
            """)
            print(f"[BrowserDiag] Nav action: {nav_result}")
            await asyncio.sleep(2)

        # Check again
        dom_state = await self.eval_js("""
            (() => {
                const btn = document.querySelector('#btn-analyse-setup') || document.querySelector('#btn-analyse-market');
                const marketState = document.querySelector('#analysis-market-state');
                const progress = document.querySelector('#analysis-progress');
                return {
                    has_btn: !!btn,
                    btn_id: btn ? btn.id : null,
                    btn_text: btn ? btn.innerText : null,
                    btn_disabled: btn ? btn.disabled : null,
                    market_state_text: marketState ? marketState.innerText : null,
                    progress_text: progress ? progress.innerText : null
                };
            })()
        """)
        print("[BrowserDiag] Smart Entry View DOM State:", json.dumps(dom_state, indent=2))

        # Measure baseline polling for 8 seconds
        print("[BrowserDiag] Observing baseline polling behavior for 8 seconds...")
        poll_count_start = len([e for e in self.polling_timeline if e["event"] == "REQUEST_SENT"])
        t_poll_start = time.time()
        await asyncio.sleep(8)
        poll_count_end = len([e for e in self.polling_timeline if e["event"] == "REQUEST_SENT"])
        print(f"[BrowserDiag] Polling requests in 8 seconds: {poll_count_end - poll_count_start}")

        # Now: Part B — Click Analyse Setup exactly once
        print("\n" + "="*60)
        print("[BrowserDiag] EXECUTING PART B: CLICKING 'Analyse Setup' EXACTLY ONCE")
        print("="*60)
        
        click_time = time.time()
        click_result = await self.eval_js("""
            (() => {
                const btn = document.querySelector('#btn-analyse-setup') || document.querySelector('#btn-analyse-market');
                if (!btn) return { error: 'Button #btn-analyse-setup not found in DOM' };
                if (btn.disabled) return { error: 'Button is disabled' };
                btn.click();
                return { success: true, text: btn.innerText, id: btn.id };
            })()
        """)
        print("[BrowserDiag] Click result:", click_result)

        # Wait for the analysis request to be sent, executed, and completed
        print("[BrowserDiag] Waiting for analysis request completion and DOM rendering...")
        analyse_req = None
        for _ in range(40):
            await asyncio.sleep(0.5)
            # Find the POST /api/tournament/analyse request sent after click_time
            matching = [
                r for r in self.completed_requests
                if "/api/tournament/analyse" in r["url"] and r["started_at"] >= (click_time - 0.5)
            ]
            if matching:
                analyse_req = matching[0]
                break

        if not analyse_req:
            print("[BrowserDiag] ERROR: No completed POST /api/tournament/analyse request found within 20s!")
            # Check if there is an in-flight request
            in_flight = [
                r for r in self.network_requests.values()
                if "/api/tournament/analyse" in r["url"] and r["started_at"] >= (click_time - 0.5)
            ]
            print(f"[BrowserDiag] In-flight /api/tournament/analyse requests: {len(in_flight)}")
            for ifr in in_flight:
                print("  In-flight:", ifr["method"], ifr["url"], "started:", ifr["started_at"])
        else:
            print(f"[BrowserDiag] Found completed Analysis request! Status: {analyse_req['status']}, Duration: {analyse_req.get('duration_ms')} ms")
            # Fetch response body
            body = await self.get_response_body(analyse_req["request_id"])
            analyse_req["body_parsed"] = json.loads(body) if body and body.startswith("{") else body
            print(f"[BrowserDiag] Response summary: keys={list(analyse_req['body_parsed'].keys()) if isinstance(analyse_req['body_parsed'], dict) else 'non-json'}")

        # Wait 2 seconds for React to finish rendering
        await asyncio.sleep(2)

        # Inspect post-analysis DOM state
        post_dom = await self.eval_js("""
            (() => {
                const btn = document.querySelector('#btn-analyse-setup') || document.querySelector('#btn-analyse-market');
                const progress = document.querySelector('#analysis-progress');
                const timings = document.querySelector('#analysis-runtime-timings');
                const outcome = document.querySelector('#analysis-outcome-summary');
                const error = document.querySelector('#analysis-error');
                const marketState = document.querySelector('#analysis-market-state');
                return {
                    btn_text: btn ? btn.innerText : null,
                    btn_disabled: btn ? btn.disabled : null,
                    progress_text: progress ? progress.innerText : null,
                    timings_text: timings ? timings.innerText : null,
                    outcome_heading: outcome ? outcome.querySelector('h2')?.innerText : null,
                    outcome_text: outcome ? outcome.innerText : null,
                    error_text: error ? error.innerText : null,
                    market_state_text: marketState ? marketState.innerText : null
                };
            })()
        """)
        print("[BrowserDiag] Post-Analysis DOM State:")
        print(json.dumps(post_dom, indent=2))

        # Check Part B Step 9: Repeat with a new request ID / snapshot
        print("\n" + "="*60)
        print("[BrowserDiag] EXECUTING PART B STEP 9: REPEAT CLICK WITH FRESH REQUEST")
        print("="*60)
        click2_time = time.time()
        click2_result = await self.eval_js("""
            (() => {
                const btn = document.querySelector('#btn-analyse-setup') || document.querySelector('#btn-analyse-market');
                if (!btn) return { error: 'Button #btn-analyse-setup not found in DOM' };
                if (btn.disabled) return { error: 'Button is disabled' };
                btn.click();
                return { success: true, text: btn.innerText, id: btn.id };
            })()
        """)
        print("[BrowserDiag] Second Click result:", click2_result)
        await asyncio.sleep(4)

        repeat_req = [
            r for r in self.completed_requests
            if "/api/tournament/analyse" in r["url"] and r["started_at"] >= (click2_time - 0.5)
        ]
        if repeat_req:
            r2 = repeat_req[0]
            print(f"[BrowserDiag] Repeat request completed! Status: {r2['status']}, Duration: {r2.get('duration_ms')} ms")
            b2 = await self.get_response_body(r2["request_id"])
            r2["body_parsed"] = json.loads(b2) if b2 and b2.startswith("{") else b2
        else:
            print("[BrowserDiag] No completed repeat request found.")

        # Save all results to disk for forensic audit
        out_data = {
            "dom_initial": dom_check,
            "dom_smart_entry": dom_state,
            "post_dom": post_dom,
            "first_analysis_request": analyse_req,
            "repeat_analysis_request": repeat_req[0] if repeat_req else None,
            "polling_timeline": self.polling_timeline,
            "completed_requests": [
                {
                    "url": r["url"],
                    "method": r["method"],
                    "status": r["status"],
                    "duration_ms": r.get("duration_ms"),
                    "started_at": r["started_at"]
                }
                for r in self.completed_requests
            ],
            "console_logs": self.console_logs
        }

        out_path = r"C:\Projects\BTCognitive\BTCognitive\scripts\qa\browser_diagnostic_results.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out_data, f, indent=2)
        print(f"[BrowserDiag] Full diagnostic payload written to {out_path}")

        listener_task.cancel()
        await self.ws.close()

    def cleanup(self):
        if self.proc:
            print("[BrowserDiag] Terminating Chrome...")
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()
            print("[BrowserDiag] Chrome terminated.")

if __name__ == "__main__":
    diag = BrowserDiagnostics()
    try:
        asyncio.run(diag.run())
    finally:
        diag.cleanup()

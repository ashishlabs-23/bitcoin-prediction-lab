"""
BTCognitive V33.4H — F02 Backtest Isolation and Analysis Reliability Browser Verification.
Uses Chrome DevTools Protocol to inspect real headless Chrome rendering and network traffic.
Verifies that:
1. "Analyse Setup" completes rapidly without running fresh historical backtests.
2. Market Intelligence is displayed independently in the DOM.
3. Strategy Assessment status is cleanly surfaced.
4. No simulated attempts are created (is_read_only = True).
5. Zero timeouts or console errors occur.
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
USER_DATA_DIR = os.path.join(os.environ["TEMP"], "chrome_v33_4h_verification")
SERVER_URL = "http://127.0.0.1:8000/"


class V33_4H_BrowserVerifier:
    def __init__(self):
        self.proc = None
        self.ws = None
        self.msg_id = 0
        self.pending_commands = {}
        self.completed_requests = []
        self.network_requests = {}
        self.console_logs = []
        self.results = {}

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
        print("[V33.4H] Spawning headless Chrome...")
        self.proc = subprocess.Popen(cmd)

        for _ in range(25):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen("http://127.0.0.1:9222/json") as resp:
                    tabs = json.loads(resp.read().decode())
                    target_tab = next((t for t in tabs if t.get("type") == "page" and "8000" in t.get("url", "")), None)
                    if target_tab:
                        print(f"[V33.4H] Connected to target page: {target_tab.get('title')}")
                        return target_tab["webSocketDebuggerUrl"]
            except Exception:
                pass
        raise RuntimeError("Failed to connect to Chrome CDP endpoint")

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

            elif method == "Network.requestWillBeSent":
                req_id = params.get("requestId")
                req = params.get("request", {})
                self.network_requests[req_id] = {
                    "request_id": req_id,
                    "url": req.get("url"),
                    "method": req.get("method"),
                    "started_at": time.time()
                }

            elif method == "Network.responseReceived":
                req_id = params.get("requestId")
                resp = params.get("response", {})
                if req_id in self.network_requests:
                    entry = self.network_requests[req_id]
                    entry["status"] = resp.get("status")
                    entry["finished_at"] = time.time()
                    entry["duration_ms"] = round((entry["finished_at"] - entry["started_at"]) * 1000, 2)
                    self.completed_requests.append(entry)

    async def get_response_body(self, req_id: str):
        try:
            res = await self.send_command("Network.getResponseBody", {"requestId": req_id})
            return res.get("result", {}).get("body")
        except Exception as e:
            return f"<failed to get response body: {e}>"

    async def run(self):
        ws_url = self.start_chrome()
        self.ws = await websockets.connect(ws_url, max_size=20*1024*1024)
        asyncio.create_task(self.event_listener())

        await self.send_command("Page.enable")
        await self.send_command("Runtime.enable")
        await self.send_command("Network.enable")

        print("[V33.4H] Waiting 4 seconds for initial render...")
        await asyncio.sleep(4)

        # Navigate to Smart Entry View
        nav = await self.eval_js("""
            (() => {
                const tab = document.querySelector('#tab-btn-smart-entry');
                if (tab) { tab.click(); return 'clicked #tab-btn-smart-entry'; }
                return 'tab not found';
            })()
        """)
        print(f"[V33.4H] Navigation: {nav}")

        # Wait for chart data feed to be ready (up to 12s)
        print("[V33.4H] Polling for chart candle snapshot readiness...")
        for attempt in range(12):
            await asyncio.sleep(1)
            feed_status = await self.eval_js("""
                (() => {
                    const priceEl = document.querySelector('.current-price') || document.querySelector('#header-price');
                    const errEl = document.querySelector('.error-banner');
                    const btn = document.querySelector('#btn-analyse-setup');
                    return {
                        price: priceEl ? priceEl.innerText : null,
                        error: errEl ? errEl.innerText : null,
                        btn_text: btn ? btn.innerText : null,
                        btn_disabled: btn ? btn.disabled : null
                    };
                })()
            """)
            print(f"  [Wait feed {attempt+1}s]: {feed_status}")
            if feed_status and not feed_status.get("btn_disabled"):
                break

        print("\n" + "="*60)
        print("[V33.4H] CLICKING 'Analyse Setup' WITH ISOLATED BACKTEST PIPELINE")
        print("="*60)

        click_time = time.time()
        click_res = await self.eval_js("""
            (() => {
                const btn = document.querySelector('#btn-analyse-setup');
                if (!btn) return { error: 'Button not found' };
                if (btn.disabled) return { error: 'Button is disabled' };
                btn.click();
                return { success: true, text: btn.innerText };
            })()
        """)
        print("[V33.4H] Click action:", click_res)

        # Wait for the analysis request to complete
        analyse_req = None
        for _ in range(40):
            await asyncio.sleep(0.3)
            matching = [
                r for r in self.completed_requests
                if "/api/tournament/analyse" in r["url"] and r["started_at"] >= (click_time - 0.5)
            ]
            if matching:
                analyse_req = matching[0]
                break

        if not analyse_req:
            # Check in-flight or error messages in DOM
            dom_err = await self.eval_js("""
                (() => {
                    const errDiv = document.querySelector('.error-banner') || document.querySelector('#analysis-error');
                    const progressDiv = document.querySelector('#analysis-progress');
                    return {
                        error: errDiv ? errDiv.innerText : null,
                        progress: progressDiv ? progressDiv.innerText : null
                    };
                })()
            """)
            print(f"[V33.4H] DOM State on timeout: {dom_err}")
            print(f"[V33.4H] Recent Console Logs: {self.console_logs[-10:]}")
            raise RuntimeError(f"Analysis request did not complete within 12 seconds! DOM: {dom_err}")

        duration_ms = analyse_req.get("duration_ms", 0)
        status_code = analyse_req.get("status")
        print(f"\n[V33.4H] Analysis Request Completed:")
        print(f"  HTTP Status: {status_code}")
        print(f"  Total Roundtrip Duration: {duration_ms} ms")

        body_str = await self.get_response_body(analyse_req["request_id"])
        body_json = json.loads(body_str) if body_str and body_str.startswith("{") else {}

        # Verify payload invariants
        mi = body_json.get("market_intelligence")
        sa = body_json.get("strategy_assessment")
        is_read_only = body_json.get("is_read_only")
        attempts_created = body_json.get("attempts_created")
        decision = body_json.get("decision", {})

        print(f"\n[V33.4H] Response Payload Invariants:")
        print(f"  is_read_only: {is_read_only} (Expected: True)")
        print(f"  attempts_created: {attempts_created} (Expected: 0)")
        print(f"  Market Intelligence Status: {mi.get('status') if mi else 'MISSING'} (Expected: SUCCESS)")
        print(f"  Strategy Assessment Status: {sa.get('status') if sa else 'MISSING'}")
        print(f"  Decision Action: {decision.get('action')}")
        print(f"  Decision SA Status: {decision.get('strategy_assessment_status')}")

        # Wait 1s for DOM update
        await asyncio.sleep(1.0)

        # Inspect DOM elements
        dom_inspection = await self.eval_js("""
            (() => {
                const miBar = document.querySelector('#analysis-market-intelligence-bar');
                const saBadge = document.querySelector('#badge-strategy-assessment');
                const outcomeCard = document.querySelector('#smart-entry-decision-card');
                const progressDiv = document.querySelector('#analysis-progress');
                const outcomeBadge = document.querySelector('#badge-smart-entry-status');

                return {
                    mi_bar_present: !!miBar,
                    mi_bar_text: miBar ? miBar.innerText : null,
                    sa_badge_present: !!saBadge,
                    sa_badge_text: saBadge ? saBadge.innerText : null,
                    outcome_card_present: !!outcomeCard,
                    outcome_card_text: outcomeCard ? outcomeCard.innerText : null,
                    outcome_badge_text: outcomeBadge ? outcomeBadge.innerText : null,
                    progress_text: progressDiv ? progressDiv.innerText : null
                };
            })()
        """)

        print(f"\n[V33.4H] Rendered DOM Inspection:")
        print(f"  Market Intelligence Bar Present: {dom_inspection.get('mi_bar_present')}")
        print(f"  MI Bar Text: {dom_inspection.get('mi_bar_text')}")
        print(f"  Strategy Assessment Badge: {dom_inspection.get('sa_badge_text')}")
        print(f"  Outcome Badge: {dom_inspection.get('outcome_badge_text')}")
        print(f"  Progress Text: {dom_inspection.get('progress_text', '')[:100]}...")

        # Check console errors
        console_errors = [c for c in self.console_logs if c.get("type") in ["error", "uncaught_exception"]]
        print(f"  Console Errors: {len(console_errors)}")

        # Store test results
        self.results = {
            "test_timestamp": time.time(),
            "http_status": status_code,
            "roundtrip_duration_ms": duration_ms,
            "is_read_only": is_read_only,
            "attempts_created": attempts_created,
            "market_intelligence_status": mi.get("status") if mi else None,
            "strategy_assessment_status": sa.get("status") if sa else None,
            "decision_action": decision.get("action"),
            "dom_mi_bar_present": dom_inspection.get("mi_bar_present"),
            "dom_sa_badge_text": dom_inspection.get("sa_badge_text"),
            "console_errors_count": len(console_errors),
            "verification_pass": (
                status_code == 200
                and duration_ms < 5000  # well below 45,000ms and multi-year backtest (~120,000ms)
                and is_read_only is True
                and attempts_created == 0
                and mi.get("status") == "SUCCESS"
                and len(console_errors) == 0
            )
        }

        with open("scripts/qa/v33_4h_browser_results.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2)

        print("\n" + "="*60)
        print(f"[V33.4H] VERIFICATION RESULT: {'PASSED' if self.results['verification_pass'] else 'FAILED'}")
        print("="*60)

    async def close_async(self):
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait()
            except Exception:
                pass


async def main():
    verifier = V33_4H_BrowserVerifier()
    try:
        await verifier.run()
    finally:
        await verifier.close_async()


if __name__ == "__main__":
    asyncio.run(main())

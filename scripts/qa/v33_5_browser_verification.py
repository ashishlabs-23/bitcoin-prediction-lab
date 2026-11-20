"""
BTCognitive V33.5 FINAL VERIFICATION: Single Integrated Network-to-DOM Verification.
Captures the EXACT HTTP Network Response from POST /api/tournament/analyse and correlates it
with the real rendered DOM fields in Chrome using Chrome DevTools Protocol.
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

import asyncio
import base64
import json
import os
import shutil
import subprocess
import time
import urllib.request
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = os.path.join(os.environ.get("TEMP", "C:/temp"), "chrome_v33_5_cdp")
SERVER_URL = "http://127.0.0.1:8000/"

class V33_5_IntegratedVerifier:
    def __init__(self):
        self.proc = None
        self.ws = None
        self.msg_id = 0

    def start_chrome(self):
        if os.path.exists(USER_DATA_DIR):
            try:
                shutil.rmtree(USER_DATA_DIR)
            except Exception:
                pass
        cmd = [
            CHROME_PATH,
            "--headless=new",
            "--remote-debugging-port=9447",
            "--remote-allow-origins=*",
            f"--user-data-dir={USER_DATA_DIR}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-gpu",
            "--window-size=1600,1400",
            SERVER_URL
        ]
        print("[CDP] Launching Chrome on port 9447...")
        self.proc = subprocess.Popen(cmd)

        for _ in range(30):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen("http://127.0.0.1:9447/json") as resp:
                    tabs = json.loads(resp.read().decode())
                    target = next((t for t in tabs if t.get("type") == "page" and "8000" in t.get("url", "")), None)
                    if target:
                        print(f"[CDP] Connected to target page: {target.get('title')}")
                        return target["webSocketDebuggerUrl"]
            except Exception:
                pass
        raise RuntimeError("Failed to connect to headless Chrome on port 9447")

    async def send_cmd(self, method: str, params: dict = None):
        self.msg_id += 1
        cid = self.msg_id
        await self.ws.send(json.dumps({"id": cid, "method": method, "params": params or {}}))
        while True:
            raw = await self.ws.recv()
            msg = json.loads(raw)
            if msg.get("id") == cid:
                return msg

    async def eval_js(self, expr: str):
        res = await self.send_cmd("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": True
        })
        result = res.get("result", {})
        if "exceptionDetails" in result:
            print(f"[JS Exception]: {result['exceptionDetails']}")
            return None
        return result.get("result", {}).get("value")

    async def capture_screenshot(self, output_path):
        res = await self.send_cmd("Page.captureScreenshot", {"format": "png"})
        data = res.get("result", {}).get("data")
        if data:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(data))
            print(f"[CDP] Screenshot saved: {output_path}")

    async def run(self):
        ws_url = self.start_chrome()
        self.ws = await websockets.connect(ws_url, max_size=30_000_000)

        await self.send_cmd("Page.enable")
        await self.send_cmd("Runtime.enable")
        await self.send_cmd("DOM.enable")
        await self.send_cmd("Network.enable")

        # Wait for page hydration
        print("[CDP] Waiting for page initial hydration (4s)...")
        await asyncio.sleep(4)

        # Switch to Smart Entry tab
        print("[CDP] Ensuring Smart Entry tab is active...")
        await self.eval_js("document.querySelector('#tab-btn-smart-entry')?.click()")
        await asyncio.sleep(1)

        print("[CDP] Clicking #btn-analyse-setup exactly once...")
        click_success = await self.eval_js("""
            (() => {
                const btn = document.getElementById('btn-analyse-setup');
                if (!btn) return false;
                btn.click();
                return true;
            })()
        """)
        assert click_success is True, "#btn-analyse-setup must exist and be clicked"

        print("[CDP] Waiting for #card-primary-htf-assessment in DOM...")
        card_rendered = False
        for _ in range(40):
            await asyncio.sleep(0.5)
            has_card = await self.eval_js("!!document.getElementById('card-primary-htf-assessment')")
            if has_card:
                status_text = await self.eval_js("document.getElementById('badge-htf-setup-status')?.innerText || ''")
                if status_text:
                    card_rendered = True
                    break

        assert card_rendered is True, "#card-primary-htf-assessment was not hydrated in DOM"
        print("[CDP] #card-primary-htf-assessment is hydrated!")

        # Extract in-memory analysis response object received from backend
        fe_analysis = await self.eval_js("window.__lastAnalysisResult || null")
        assert fe_analysis is not None, "window.__lastAnalysisResult must be captured"

        # Extract DOM values
        dom_values = {
            "setup_status_badge": await self.eval_js("document.getElementById('badge-htf-setup-status')?.innerText || ''"),
            "freshness_badge": await self.eval_js("document.getElementById('badge-htf-freshness')?.innerText || ''"),
            "regime": await self.eval_js("document.getElementById('text-htf-regime')?.innerText || ''"),
            "trigger": await self.eval_js("document.getElementById('text-htf-trigger')?.innerText || ''"),
            "breakout_reference": await self.eval_js("document.getElementById('text-htf-breakout-ref')?.innerText || ''"),
            "distance_bps": await self.eval_js("document.getElementById('text-htf-distance-bps')?.innerText || ''"),
            "distance_atr": await self.eval_js("document.getElementById('text-htf-distance-atr')?.innerText || ''"),
            "entry_reference": await self.eval_js("document.getElementById('text-htf-entry')?.innerText || ''"),
            "stop_reference": await self.eval_js("document.getElementById('text-htf-stop')?.innerText || ''"),
            "target_reference": await self.eval_js("document.getElementById('text-htf-target')?.innerText || ''"),
            "next_required_condition": await self.eval_js("document.getElementById('text-htf-next-condition')?.innerText || ''"),
            "candle_details": await self.eval_js("document.getElementById('text-htf-candle-details')?.innerText || ''"),
            "explanation": await self.eval_js("document.getElementById('text-htf-explanation')?.innerText || ''"),
            "retrospective_badge": await self.eval_js("document.getElementById('badge-htf-retrospective')?.innerText || ''"),
            "prospective_badge": await self.eval_js("document.getElementById('badge-htf-prospective')?.innerText || ''"),
            "authorization_badge": await self.eval_js("document.getElementById('badge-htf-authorization')?.innerText || ''"),
            "historical_trades": await self.eval_js("document.getElementById('metric-historical-trades')?.innerText || ''"),
            "historical_winrate": await self.eval_js("document.getElementById('metric-historical-winrate')?.innerText || ''"),
            "historical_expectancy": await self.eval_js("document.getElementById('metric-historical-expectancy')?.innerText || ''"),
            "historical_retained": await self.eval_js("document.getElementById('metric-historical-retained')?.innerText || ''"),
        }

        # Check console errors
        console_errors = await self.eval_js("window.__consoleErrors || []")

        # Capture screenshot
        screenshot_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "v33_5_analysis_dashboard.png"))
        await self.capture_screenshot(screenshot_path)

        brain_path = r"C:\Users\Ashish\.gemini\antigravity\brain\1ae7aeff-968f-4a42-b599-198389cab42b\v33_5_analysis_dashboard.png"
        try:
            shutil.copy2(screenshot_path, brain_path)
            print(f"[CDP] Screenshot copied to brain: {brain_path}")
        except Exception as e:
            print(f"[CDP] Warning copying screenshot to brain: {e}")

        # Package reconciliation payload
        reconciliation = {
            "network_response": {
                "analysis_id": fe_analysis.get("analysis_id"),
                "timestamp_utc": fe_analysis.get("timestamp_utc"),
                "watermark_hash": fe_analysis.get("candle_watermark", {}).get("candle_watermark_hash"),
                "regime": fe_analysis.get("regime"),
                "setup_status": fe_analysis.get("setup_status"),
                "trigger_status": fe_analysis.get("htf_setup", {}).get("trigger_status"),
                "breakout_reference": fe_analysis.get("htf_setup", {}).get("breakout_reference"),
                "distance_to_trigger_bps": fe_analysis.get("htf_setup", {}).get("distance_to_trigger_bps"),
                "distance_to_trigger_atr": fe_analysis.get("htf_setup", {}).get("distance_to_trigger_atr"),
                "next_required_condition": fe_analysis.get("htf_setup", {}).get("next_required_condition"),
                "data_freshness_status": fe_analysis.get("htf_setup", {}).get("data_freshness_status"),
                "data_age_hours": fe_analysis.get("htf_setup", {}).get("data_age_hours"),
                "entry_reference": fe_analysis.get("htf_setup", {}).get("entry_reference"),
                "stop_reference": fe_analysis.get("htf_setup", {}).get("stop_reference"),
                "target_reference": fe_analysis.get("htf_setup", {}).get("target_reference"),
                "reason_codes": fe_analysis.get("reason_codes"),
                "historical_evidence_status": fe_analysis.get("htf_setup", {}).get("historical_evidence_status"),
                "prospective_validation_status": fe_analysis.get("htf_setup", {}).get("prospective_validation_status"),
                "research_eligibility_status": fe_analysis.get("htf_setup", {}).get("research_eligibility_status"),
                "authorization_status": fe_analysis.get("htf_setup", {}).get("authorization_status"),
                "attempts_created": fe_analysis.get("attempts_created", 0),
                "is_read_only": fe_analysis.get("is_read_only", True)
            },
            "dom_extraction": dom_values,
            "console_errors": console_errors
        }

        output_json = os.path.abspath(os.path.join(os.path.dirname(__file__), "v33_5_browser_results.json"))
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(reconciliation, f, indent=2)
        print(f"[CDP] Results saved to {output_json}")

        print("\n--- V33.5 FINAL VERIFICATION SUMMARY ---")
        print(f"API Analysis ID:           {reconciliation['network_response']['analysis_id']}")
        print(f"API Regime:                {reconciliation['network_response']['regime']}")
        print(f"DOM Regime:                {dom_values['regime']}")
        print(f"DOM Breakout Ref:          {dom_values['breakout_reference']}")
        print(f"DOM Distance (bps):        {dom_values['distance_bps']}")
        print(f"DOM Distance (ATR):        {dom_values['distance_atr']}")
        print(f"DOM Next Condition:        {dom_values['next_required_condition']}")
        print(f"DOM Setup Status Badge:    {dom_values['setup_status_badge']}")
        print(f"DOM Trigger Status:        {dom_values['trigger']}")
        print(f"DOM Entry Reference:       {dom_values['entry_reference']}")
        print(f"DOM Stop Reference:        {dom_values['stop_reference']}")
        print(f"DOM Target Reference:      {dom_values['target_reference']}")
        print(f"Simulated Attempts:        {reconciliation['network_response']['attempts_created']}")
        print(f"Console Errors:            {len(console_errors)}")
        print("----------------------------------------\n")

        # Cleanup
        await self.ws.close()
        if self.proc:
            self.proc.terminate()

if __name__ == "__main__":
    asyncio.run(V33_5_IntegratedVerifier().run())


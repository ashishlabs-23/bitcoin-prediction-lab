"""
BTCognitive V33.4L — Historical Evidence Panel Browser Verification.
Uses Chrome DevTools Protocol to inspect real headless Chrome rendering and DOM presentation.
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
USER_DATA_DIR = os.path.join(os.environ.get("TEMP", "C:/temp"), "chrome_v33_4l_cdp")
SERVER_URL = "http://127.0.0.1:8000/"


class V33_4L_BrowserVerifier:
    def __init__(self):
        self.proc = None
        self.ws = None
        self.msg_id = 0
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
            "--remote-debugging-port=9444",
            "--remote-allow-origins=*",
            f"--user-data-dir={USER_DATA_DIR}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-gpu",
            "--window-size=1600,1200",
            SERVER_URL
        ]
        print("[V33.4L] Spawning headless Chrome on port 9444...")
        self.proc = subprocess.Popen(cmd)

        for _ in range(25):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen("http://127.0.0.1:9444/json") as resp:
                    tabs = json.loads(resp.read().decode())
                    target_tab = next((t for t in tabs if t.get("type") == "page" and "8000" in t.get("url", "")), None)
                    if target_tab:
                        print(f"[V33.4L] Connected to target page: {target_tab.get('title')}")
                        return target_tab["webSocketDebuggerUrl"]
            except Exception:
                pass
        raise RuntimeError("Failed to connect to headless Chrome")

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
            print(f"[V33.4L] Screenshot saved to: {output_path}")

    async def run(self):
        ws_url = self.start_chrome()
        self.ws = await websockets.connect(ws_url, max_size=30_000_000)

        await self.send_cmd("Page.enable")
        await self.send_cmd("Runtime.enable")
        await self.send_cmd("DOM.enable")

        print("[V33.4L] Waiting for initial render and data hydration (4s)...")
        await asyncio.sleep(4)

        # Check if panel is already in DOM
        check = await self.eval_js("!!document.getElementById('historical-research-evidence-panel')")
        print(f"[V33.4L] Initial panel check in DOM: {check}")

        if not check:
            print("[V33.4L] Navigating to Smart Entry tab...")
            await self.eval_js("document.querySelector('#tab-btn-smart-entry')?.click()")
            for _ in range(15):
                await asyncio.sleep(0.5)
                check = await self.eval_js("!!document.getElementById('historical-research-evidence-panel')")
                if check:
                    break

        assert check is True, "historical-research-evidence-panel must exist in DOM"
        print("[V33.4L] Panel successfully found in DOM! Extracting metrics...")

        # Extract values
        classification_badge = await self.eval_js("document.getElementById('badge-historical-classification')?.innerText || ''")
        provenance_badge = await self.eval_js("document.getElementById('badge-provenance-status')?.innerText || ''")
        trades_metric = await self.eval_js("document.getElementById('metric-historical-trades')?.innerText || ''")
        winrate_metric = await self.eval_js("document.getElementById('metric-historical-winrate')?.innerText || ''")
        expectancy_metric = await self.eval_js("document.getElementById('metric-historical-expectancy')?.innerText || ''")
        retained_metric = await self.eval_js("document.getElementById('metric-historical-retained')?.innerText || ''")
        setup_assessment_banner = await self.eval_js("document.getElementById('banner-current-setup-assessment')?.innerText || ''")
        prospective_validation_banner = await self.eval_js("document.getElementById('banner-prospective-validation')?.innerText || ''")
        disclaimer_text = await self.eval_js("document.getElementById('disclaimer-historical-evidence')?.innerText || ''")
        panel_full_text = await self.eval_js("document.getElementById('historical-research-evidence-panel')?.innerText || ''")

        print("\n" + "="*70)
        print("BTCognitive V33.4L — EXTRACTED DOM METRICS")
        print("="*70)
        print(f"Classification Badge:       {classification_badge}")
        print(f"Provenance Badge:           {provenance_badge}")
        print(f"Trades Count:               {trades_metric}")
        print(f"Win Rate:                   {winrate_metric}")
        print(f"Net Expectancy:             {expectancy_metric}")
        print(f"Retained / Excluded Metric: {retained_metric}")
        print(f"Setup Assessment Banner:    {setup_assessment_banner}")
        print(f"Prospective Status Banner:  {prospective_validation_banner}")
        print(f"Disclaimer:                 {disclaimer_text}")
        print("="*70 + "\n")

        # Explicit Verification Assertions
        assert "RETROSPECTIVE RESEARCH ONLY — NON-CONFIRMATORY" in classification_badge, f"Badge mismatch: {classification_badge}"
        assert "PARTIALLY_RESOLVED" in provenance_badge, f"Badge mismatch: {provenance_badge}"
        assert "194" in trades_metric, f"Trades count mismatch: {trades_metric}"
        assert "43.81%" in winrate_metric, f"Win rate mismatch: {winrate_metric}"
        assert "+9.57 bps" in expectancy_metric, f"Expectancy mismatch: {expectancy_metric}"
        assert "110 / 84" in retained_metric and "+59.25 bps" in retained_metric, f"Retained mismatch: {retained_metric}"
        assert "Retained Subgroup (110 trades)" in panel_full_text, "Missing retained subgroup text"
        assert "+59.25 bps Net EV" in panel_full_text, "Missing retained Net EV text"
        assert "Excluded Subgroup (84 trades)" in panel_full_text, "Missing excluded subgroup text"
        assert "-55.49 bps Net EV" in panel_full_text, "Missing excluded Net EV text"
        assert "CURRENT SETUP ASSESSMENT" in setup_assessment_banner.upper(), f"Banner mismatch: {setup_assessment_banner}"
        assert "NOT VALIDATED" in prospective_validation_banner, f"Prospective mismatch: {prospective_validation_banner}"
        assert "DISABLED" in disclaimer_text, f"Disclaimer mismatch: {disclaimer_text}"

        # Capture screenshots to both BTCognitive/artifacts and brain artifacts dir
        screenshot_path = os.path.abspath(r"artifacts\v33_4l_historical_evidence_dashboard.png")
        await self.capture_screenshot(screenshot_path)

        brain_screenshot = r"C:\Users\Ashish\.gemini\antigravity\brain\1ae7aeff-968f-4a42-b599-198389cab42b\v33_4l_historical_evidence_dashboard.png"
        try:
            shutil.copy2(screenshot_path, brain_screenshot)
            print(f"[V33.4L] Copied screenshot to brain artifact dir: {brain_screenshot}")
        except Exception as e:
            print(f"[V33.4L] Brain copy notice: {e}")

        self.results = {
            "status": "PASS",
            "verification_milestone": "V33.4L",
            "classification_badge": classification_badge,
            "provenance_badge": provenance_badge,
            "trades_count": trades_metric,
            "win_rate": winrate_metric,
            "net_expectancy": expectancy_metric,
            "retained_metric": retained_metric,
            "setup_assessment_banner": setup_assessment_banner,
            "prospective_validation_banner": prospective_validation_banner,
            "disclaimer_text": disclaimer_text,
            "screenshot_path": screenshot_path,
            "brain_screenshot": brain_screenshot
        }

        with open(r"scripts\qa\v33_4l_browser_results.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2)

        print(">>> ALL V33.4L BROWSER VERIFICATION CHECKS PASSED WITH 100% ACCURACY! <<<")

    def close(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except Exception:
                self.proc.kill()
        print("[V33.4L] Chrome closed.")


async def main():
    verifier = V33_4L_BrowserVerifier()
    try:
        await verifier.run()
    finally:
        verifier.close()

if __name__ == "__main__":
    asyncio.run(main())

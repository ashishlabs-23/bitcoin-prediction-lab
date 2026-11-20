"""
BTCognitive V33.4M — Primary Strategy Analysis Completion Browser Verification.
Uses Chrome DevTools Protocol to trigger 'Analyse Setup' and inspect real DOM rendering
of the Primary Strategy Assessment Card (#card-primary-htf-assessment).
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
USER_DATA_DIR = os.path.join(os.environ.get("TEMP", "C:/temp"), "chrome_v33_4m_cdp")
SERVER_URL = "http://127.0.0.1:8000/"


class V33_4M_BrowserVerifier:
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
            "--remote-debugging-port=9445",
            "--remote-allow-origins=*",
            f"--user-data-dir={USER_DATA_DIR}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-gpu",
            "--window-size=1600,1400",
            SERVER_URL
        ]
        print("[V33.4M] Spawning headless Chrome on port 9445...")
        self.proc = subprocess.Popen(cmd)

        for _ in range(25):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen("http://127.0.0.1:9445/json") as resp:
                    tabs = json.loads(resp.read().decode())
                    target_tab = next((t for t in tabs if t.get("type") == "page" and "8000" in t.get("url", "")), None)
                    if target_tab:
                        print(f"[V33.4M] Connected to target page: {target_tab.get('title')}")
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
            print(f"[V33.4M] Screenshot saved to: {output_path}")

    async def run(self):
        ws_url = self.start_chrome()
        self.ws = await websockets.connect(ws_url, max_size=30_000_000)

        await self.send_cmd("Page.enable")
        await self.send_cmd("Runtime.enable")
        await self.send_cmd("DOM.enable")

        print("[V33.4M] Waiting for initial render and data hydration (4s)...")
        await asyncio.sleep(4)

        # Switch to Smart Entry tab and wait for #btn-analyse-setup
        print("[V33.4M] Ensuring Smart Entry tab is active and #btn-analyse-setup is mounted...")
        btn_ready = False
        for _ in range(20):
            await self.eval_js("document.querySelector('#tab-btn-smart-entry')?.click()")
            await asyncio.sleep(0.5)
            has_btn = await self.eval_js("!!document.getElementById('btn-analyse-setup')")
            if has_btn:
                btn_ready = True
                break

        assert btn_ready is True, "#btn-analyse-setup must be mounted in DOM"

        # Click Analyse Setup button
        print("[V33.4M] Clicking 'Analyse Setup' (#btn-analyse-setup)...")
        click_res = await self.eval_js("""
            (() => {
                const btn = document.getElementById('btn-analyse-setup');
                if (!btn) return false;
                btn.click();
                return true;
            })()
        """)
        print(f"[V33.4M] Click button result: {click_res}")
        assert click_res is True, "btn.click() must succeed"

        # Wait for Analysis request to complete and DOM to update
        print("[V33.4M] Polling for #card-primary-htf-assessment in DOM (up to 30s)...")
        card_found = False
        for _ in range(60):
            await asyncio.sleep(0.5)
            has_card = await self.eval_js("!!document.getElementById('card-primary-htf-assessment')")
            if has_card:
                # Also check that it's visible and populated
                status_text = await self.eval_js("document.getElementById('badge-htf-setup-status')?.innerText || ''")
                if status_text:
                    card_found = True
                    break

        if not card_found:
            err = await self.eval_js("document.body.innerText")
            print(f"[DOM Snapshot on Failure]:\n{err[:500]}")

        assert card_found is True, "#card-primary-htf-assessment must be present and populated in DOM"
        print("[V33.4M] Primary Strategy Assessment Card found! Extracting values...")

        # Extract DOM values
        analysis_id_dom = await self.eval_js("document.getElementById('text-htf-analysis-id')?.innerText || ''")
        outcome_heading = await self.eval_js("document.getElementById('analysis-outcome-heading')?.innerText || ''")
        outcome_sub = await self.eval_js("document.getElementById('analysis-outcome-sub')?.innerText || ''")
        setup_status_badge = await self.eval_js("document.getElementById('badge-htf-setup-status')?.innerText || ''")
        freshness_badge = await self.eval_js("document.getElementById('badge-htf-freshness')?.innerText || ''")
        regime_text = await self.eval_js("document.getElementById('text-htf-regime')?.innerText || ''")
        trigger_text = await self.eval_js("document.getElementById('text-htf-trigger')?.innerText || ''")
        entry_text = await self.eval_js("document.getElementById('text-htf-entry')?.innerText || ''")
        stop_text = await self.eval_js("document.getElementById('text-htf-stop')?.innerText || ''")
        target_text = await self.eval_js("document.getElementById('text-htf-target')?.innerText || ''")
        candle_details = await self.eval_js("document.getElementById('text-htf-candle-details')?.innerText || ''")
        explanation = await self.eval_js("document.getElementById('text-htf-explanation')?.innerText || ''")
        badge_retro = await self.eval_js("document.getElementById('badge-htf-retrospective')?.innerText || ''")
        badge_prosp = await self.eval_js("document.getElementById('badge-htf-prospective')?.innerText || ''")
        badge_auth = await self.eval_js("document.getElementById('badge-htf-authorization')?.innerText || ''")

        # In-memory backend response object
        fe_analysis = await self.eval_js("window.__lastAnalysisResult || null")

        # Also verify historical evidence panel
        hist_trades = await self.eval_js("document.getElementById('metric-historical-trades')?.innerText || ''")
        hist_winrate = await self.eval_js("document.getElementById('metric-historical-winrate')?.innerText || ''")
        hist_expectancy = await self.eval_js("document.getElementById('metric-historical-expectancy')?.innerText || ''")
        hist_retained = await self.eval_js("document.getElementById('metric-historical-retained')?.innerText || ''")

        results = {
            "analysis_id_dom": analysis_id_dom,
            "backend_response": fe_analysis,
            "outcome_heading": outcome_heading,
            "outcome_sub": outcome_sub,
            "setup_status_badge": setup_status_badge,
            "freshness_badge": freshness_badge,
            "regime_text": regime_text,
            "trigger_text": trigger_text,
            "entry_text": entry_text,
            "stop_text": stop_text,
            "target_text": target_text,
            "candle_details": candle_details,
            "explanation": explanation,
            "badge_retrospective": badge_retro,
            "badge_prospective": badge_prosp,
            "badge_authorization": badge_auth,
            "historical_evidence": {
                "trades": hist_trades,
                "winrate": hist_winrate,
                "expectancy": hist_expectancy,
                "retained_subgroup": hist_retained
            }
        }

        print("\n" + "="*70)
        print("BTCognitive V33.4M-R — EXTRACTED ASSESSMENT CARD METRICS")
        print("="*70)
        print(f"Outcome Heading:       {outcome_heading}")
        print(f"Outcome Subtitle:      {outcome_sub}")
        print(f"Setup Status Badge:    {setup_status_badge}")
        print(f"Freshness Badge:       {freshness_badge}")
        print(f"Regime:                {regime_text}")
        print(f"Trigger Status:        {trigger_text}")
        print(f"Entry Reference:       {entry_text}")
        print(f"Stop Reference:        {stop_text}")
        print(f"Target Reference:      {target_text}")
        print(f"Candle Details:        {candle_details}")
        print(f"Explanation:           {explanation}")
        print(f"Retrospective Badge:   {badge_retro}")
        print(f"Prospective Badge:     {badge_prosp}")
        print(f"Authorization Badge:   {badge_auth}")
        print(f"Historical 194 Trades: {hist_trades} trades | Win Rate: {hist_winrate} | All-Trade Exp: {hist_expectancy}")
        print(f"Historical 110 Retained: {hist_retained}")
        print("="*70 + "\n")

        # Save JSON results
        result_file = os.path.join(os.path.dirname(__file__), "v33_4m_browser_results.json")
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"[V33.4M] Verification results written to: {result_file}")

        # Capture screenshot
        screenshot_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "v33_4m_analysis_dashboard.png"))
        await self.capture_screenshot(screenshot_path)

        # Copy to brain artifact directory
        brain_path = r"C:\Users\Ashish\.gemini\antigravity\brain\1ae7aeff-968f-4a42-b599-198389cab42b\v33_4m_analysis_dashboard.png"
        try:
            shutil.copy2(screenshot_path, brain_path)
            print(f"[V33.4M] Copied screenshot to brain artifact directory: {brain_path}")
        except Exception as e:
            print(f"[V33.4M] Warning: Failed to copy to brain path: {e}")

        # Verification assertions
        assert "BLOCKED" in setup_status_badge
        assert "TRENDING_BEARISH" in regime_text
        assert "STALE" in trigger_text or "BLOCKED" in trigger_text
        assert "Unavailable" in stop_text
        assert "Unavailable" in entry_text
        assert "Unavailable" in target_text
        assert "MARKET_DATA_STALE" in freshness_badge or "STALE" in freshness_badge
        assert "194" in hist_trades
        assert "+9.57 bps" in hist_expectancy
        assert "+59.25 bps" in hist_retained
        print("[V33.4M-R] All browser assertions PASSED successfully! Regime, freshness, and stop semantics reconciled.")


def main():
    verifier = V33_4M_BrowserVerifier()
    try:
        asyncio.run(verifier.run())
    finally:
        if verifier.proc:
            print("[V33.4M] Terminating headless Chrome...")
            verifier.proc.terminate()
            try:
                verifier.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                verifier.proc.kill()


if __name__ == "__main__":
    main()

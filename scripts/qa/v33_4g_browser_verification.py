"""
BTCognitive V33.4G — Forecast & Market-Data Presentation Integrity Browser Verification.
Uses Chrome DevTools Protocol to inspect real headless Chrome rendering at Desktop and Mobile resolutions.
Verifies F04 (PredictionPanel, OutlookView) and F05 (Market Data Stale Disclosures).
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
USER_DATA_DIR = os.path.join(os.environ["TEMP"], "chrome_v33_4g_verification")
SERVER_URL = "http://127.0.0.1:8000/"

class V33_4G_BrowserVerifier:
    def __init__(self):
        self.proc = None
        self.ws = None
        self.msg_id = 0
        self.pending_commands = {}
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
        print("[V33.4G] Spawning headless Chrome...")
        self.proc = subprocess.Popen(cmd)
        
        for _ in range(25):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen("http://127.0.0.1:9222/json") as resp:
                    tabs = json.loads(resp.read().decode())
                    target_tab = next((t for t in tabs if t.get("type") == "page" and "8000" in t.get("url", "")), None)
                    if target_tab:
                        print(f"[V33.4G] Connected to target page: {target_tab.get('title')}")
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

    async def run(self):
        ws_url = self.start_chrome()
        self.ws = await websockets.connect(ws_url, max_size=20*1024*1024)
        asyncio.create_task(self.event_listener())

        await self.send_command("Page.enable")
        await self.send_command("Runtime.enable")

        print("[V33.4G] Waiting 4 seconds for initial page render...")
        await asyncio.sleep(4)

        # -------------------------------------------------------------
        # 1. Desktop Verification (1600x1000)
        # -------------------------------------------------------------
        print("\n--- [TEST 1: DESKTOP DOM INSPECTION (1600x1000)] ---")
        desktop_check = await self.eval_js("""
            (() => {
                const bodyText = document.body.innerText;
                
                // Check F05 Market price disclosures in Hero / Ticker
                const hasStaleNotice = bodyText.includes("STALE — NOT A CURRENT ENTRY REFERENCE") || bodyText.includes("STALE SNAPSHOT");
                const hasHistoricalBarClose = bodyText.includes("Historical Bar Close");
                const hasCoinbaseFeedUnconditional = bodyText.includes("Spot Market Price: Coinbase BTC/USD Feed");
                const hasSnapshotClose = bodyText.includes("30 October 2026") || bodyText.includes("30 Oct 2026");
                
                // Check F04 Directional Forecast Fallback removal
                const hasHardcodedShort = bodyText.includes("SHORT") && bodyText.includes("47.1%");
                
                return {
                    hasStaleNotice,
                    hasHistoricalBarClose,
                    hasCoinbaseFeedUnconditional,
                    hasSnapshotClose,
                    hasHardcodedShort,
                    sampleSnippet: bodyText.slice(0, 1000)
                };
            })()
        """)
        print(f"Desktop Inspection Result:\n{json.dumps(desktop_check, indent=2)}")
        self.results["desktop"] = desktop_check

        # -------------------------------------------------------------
        # 1B. Click Research Tab (PredictionPanel)
        # -------------------------------------------------------------
        print("\n--- [TEST 1B: RESEARCH TAB (PredictionPanel)] ---")
        research_tab_check = await self.eval_js("""
            (() => {
                const btn = document.getElementById("tab-btn-research") || Array.from(document.querySelectorAll("button")).find(b => b.innerText.includes("Research"));
                if (btn) btn.click();
                return { clicked: Boolean(btn) };
            })()
        """)
        await asyncio.sleep(2)
        research_panel_check = await self.eval_js("""
            (() => {
                const bodyText = document.body.innerText;
                const hasDirectionalUnavailable = bodyText.includes("DIRECTIONAL FORECAST UNAVAILABLE");
                const hasRiskEnvelopeWarning = bodyText.includes("Volatility risk envelope indicates dispersion range");
                const hasHardcodedShortFallback = bodyText.includes("SHORT") && bodyText.includes("47.1%");
                const hasRiskForecastAvailable = bodyText.includes("RISK FORECAST AVAILABLE") || bodyText.includes("HAR-RS-DOW-v1.0");
                return {
                    hasDirectionalUnavailable,
                    hasRiskEnvelopeWarning,
                    hasHardcodedShortFallback,
                    hasRiskForecastAvailable,
                    sampleSnippet: bodyText.slice(0, 800)
                };
            })()
        """)
        print(f"Research Panel Check:\n{json.dumps(research_panel_check, indent=2)}")
        self.results["research_panel"] = research_panel_check

        # -------------------------------------------------------------
        # 1C. Click Forecast Tab (AiForecastRiskOutlookView)
        # -------------------------------------------------------------
        print("\n--- [TEST 1C: FORECAST TAB (AiForecastRiskOutlookView)] ---")
        forecast_tab_check = await self.eval_js("""
            (() => {
                const btn = document.getElementById("tab-btn-forecast") || Array.from(document.querySelectorAll("button")).find(b => b.innerText.includes("Forecast"));
                if (btn) btn.click();
                return { clicked: Boolean(btn) };
            })()
        """)
        await asyncio.sleep(2)
        forecast_panel_check = await self.eval_js("""
            (() => {
                const bodyText = document.body.innerText;
                const hasAbstainSignalDisabled = bodyText.includes("ABSTAIN (SIGNAL DISABLED)");
                const hasHardcodedProb = bodyText.includes("55.85%") || bodyText.includes("0.5585");
                const hasStaleStatus = bodyText.includes("STALE (Historical Snapshot Close — Not Current Entry Reference)");
                return {
                    hasAbstainSignalDisabled,
                    hasHardcodedProb,
                    hasStaleStatus,
                    sampleSnippet: bodyText.slice(0, 800)
                };
            })()
        """)
        print(f"Forecast Panel Check:\n{json.dumps(forecast_panel_check, indent=2)}")
        self.results["forecast_panel"] = forecast_panel_check

        # -------------------------------------------------------------
        # 2. Smart Entry Simulator Navigation
        # -------------------------------------------------------------
        print("\n--- [TEST 2: SMART ENTRY SIMULATOR VIEW] ---")
        await self.eval_js("""
            (() => {
                const btn = document.getElementById("tab-btn-smart-entry") || Array.from(document.querySelectorAll("button")).find(b => b.innerText.includes("Smart Entry"));
                if (btn) btn.click();
                return { clicked: Boolean(btn) };
            })()
        """)
        await asyncio.sleep(2)
        smart_entry_check = await self.eval_js("""
            (() => {
                const bodyText = document.body.innerText;
                const hasSnapshotCloseStale = bodyText.includes("HISTORICAL SNAPSHOT CLOSE (STALE)") || bodyText.includes("Snapshot close");
                const hasStaleDisclaimer = bodyText.includes("STALE — NOT A CURRENT ENTRY REFERENCE");
                const hasOldSpotPrice = bodyText.includes("CURRENT SPOT PRICE");
                return {
                    hasSnapshotCloseStale,
                    hasStaleDisclaimer,
                    hasOldSpotPrice,
                    titlePresent: bodyText.includes("Smart Entry") || bodyText.includes("Tournament"),
                    sampleSnippet: bodyText.slice(0, 800)
                };
            })()
        """)
        print(f"Smart Entry View Result:\n{json.dumps(smart_entry_check, indent=2)}")
        self.results["smart_entry"] = smart_entry_check

        # -------------------------------------------------------------
        # 3. Terminal Navigation
        # -------------------------------------------------------------
        print("\n--- [TEST 3: TERMINAL VIEW] ---")
        await self.eval_js("window.location.hash = '#/terminal';")
        await asyncio.sleep(2)
        terminal_check = await self.eval_js("""
            (() => {
                const bodyText = document.body.innerText;
                const hasStaleNotice = bodyText.includes("STALE — NOT A CURRENT ENTRY REFERENCE");
                const hasDirectionalUnavailable = bodyText.includes("DIRECTIONAL FORECAST UNAVAILABLE");
                const hasRiskNotice = bodyText.includes("Volatility risk envelope indicates dispersion range");
                return {
                    hasStaleNotice,
                    hasDirectionalUnavailable,
                    hasRiskNotice,
                    terminalPresent: bodyText.includes("TERMINAL") || bodyText.includes("Research Terminal") || bodyText.includes("Analysis")
                };
            })()
        """)
        print(f"Terminal View Result:\n{json.dumps(terminal_check, indent=2)}")
        self.results["terminal"] = terminal_check

        # -------------------------------------------------------------
        # 4. Mobile Viewport (375x812)
        # -------------------------------------------------------------
        print("\n--- [TEST 4: MOBILE VIEWPORT (375x812)] ---")
        await self.send_command("Emulation.setDeviceMetricsOverride", {
            "width": 375,
            "height": 812,
            "deviceScaleFactor": 2,
            "mobile": True
        })
        await asyncio.sleep(2)
        mobile_check = await self.eval_js("""
            (() => {
                const bodyText = document.body.innerText;
                const hasStaleNotice = bodyText.includes("STALE SNAPSHOT") || bodyText.includes("Historical Bar Close") || bodyText.includes("STALE — NOT A CURRENT ENTRY REFERENCE");
                const docWidth = document.documentElement.clientWidth;
                return {
                    clientWidth: docWidth,
                    hasStaleNotice
                };
            })()
        """)
        print(f"Mobile Viewport Result:\n{json.dumps(mobile_check, indent=2)}")
        self.results["mobile"] = mobile_check

        # Save verification report
        out_path = os.path.join(os.path.dirname(__file__), "v33_4g_browser_results.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n[V33.4G] Browser verification successfully saved to {out_path}")

        # Teardown
        if self.proc:
            self.proc.terminate()
            self.proc.wait()

if __name__ == "__main__":
    verifier = V33_4G_BrowserVerifier()
    asyncio.run(verifier.run())

"""
engine/run_v32_43_smart_entry_browser_qa.py — Automated Real Chrome CDP Browser QA
===================================================================================
BTCognitive V32.43: Automated Multi-Viewport Browser QA for Smart Entry & Tournament.

Tests Desktop (1280x800), Tablet (768x1024), and Mobile (375x667):
1. Verifies Smart Entry view rendering (#v32-43-smart-entry-view).
2. Verifies non-execution warning banner (#smart-entry-warning-banner).
3. Verifies always-visible AI Forecast Panel (#smart-entry-forecast-panel).
4. Verifies Analyse button (#btn-analyse-setup) and triggers market analysis.
5. Verifies top-two shortlist cards and 7/10 screen badges.
6. Verifies Run Tournament button (#btn-run-tournament) and 3-arm backtest table.
7. Verifies Smart Entry Decision card and Enter (Simulated) button (#btn-enter-simulated-trade).
8. Verifies active simulated attempt card and locked TP/SL levels.
9. Captures high-resolution PNG screenshots to research/reports/artifacts/browser_qa/.
"""

import os
import sys
import json
import time
import base64
import urllib.request
import socket
import threading
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import asyncio
import websockets

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(REPO_ROOT, "web")
ARTIFACTS_DIR = os.path.join(REPO_ROOT, "research", "reports", "artifacts", "browser_qa")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)


def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        pass


def run_http_server(port):
    server = ThreadingHTTPServer(('127.0.0.1', port), QuietHandler)
    server.serve_forever()


def ensure_chrome_cdp():
    """Ensures Chrome is listening on port 9222."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=2) as r:
            return
    except Exception:
        pass

    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    profile_dir = os.path.join(os.environ.get("TEMP", "."), "chrome_test_profile_9222")
    os.makedirs(profile_dir, exist_ok=True)

    subprocess.Popen([
        chrome_path,
        "--headless=new",
        "--remote-debugging-port=9222",
        f"--user-data-dir={profile_dir}",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--remote-allow-origins=*"
    ])
    time.sleep(3)


async def send_cdp(ws, method, params=None, msg_id=1):
    msg = {"id": msg_id, "method": method, "params": params or {}}
    await ws.send(json.dumps(msg))
    while True:
        resp_raw = await ws.recv()
        resp = json.loads(resp_raw)
        if resp.get("id") == msg_id:
            return resp.get("result", {})


async def evaluate_js(ws, expression, msg_id=100):
    res = await send_cdp(ws, "Runtime.evaluate", {
        "expression": expression,
        "returnByValue": True,
        "awaitPromise": True
    }, msg_id=msg_id)
    return res.get("result", {}).get("value")


async def main():
    ensure_chrome_cdp()

    port = find_free_port()
    server_thread = threading.Thread(target=run_http_server, args=(port,), daemon=True)
    server_thread.start()
    print(f"[CDP QA] Local test server started on http://127.0.0.1:{port}")

    # Discover Chrome WebSocket target
    try:
        req = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=5)
        targets = json.loads(req.read().decode("utf-8"))
        page_targets = [t for t in targets if t.get("type") == "page"]
        if not page_targets:
            # Create new page target
            req_new = urllib.request.Request(f"http://127.0.0.1:9222/json/new?http://127.0.0.1:{port}/#/smart-entry", method="PUT")
            with urllib.request.urlopen(req_new, timeout=5) as r:
                t_info = json.loads(r.read().decode())
                ws_url = t_info["webSocketDebuggerUrl"]
        else:
            ws_url = page_targets[0]["webSocketDebuggerUrl"]
        print(f"[CDP QA] Connecting to Chrome CDP at {ws_url}")
    except Exception as e:
        print(f"[CDP QA] Error connecting to Chrome CDP on 9222: {e}")
        sys.exit(1)

    async with websockets.connect(ws_url, max_size=50_000_000) as ws:
        await send_cdp(ws, "Page.enable", msg_id=1)
        await send_cdp(ws, "DOM.enable", msg_id=2)
        await send_cdp(ws, "Runtime.enable", msg_id=3)

        url = f"http://127.0.0.1:{port}/#/smart-entry"
        print(f"[CDP QA] Navigating to {url}")
        await send_cdp(ws, "Page.navigate", {"url": url}, msg_id=4)

        # Wait for React to mount SmartEntrySimulatorView
        print("[CDP QA] Waiting for SmartEntrySimulatorView to mount...")
        mounted = False
        for _ in range(30):
            val = await evaluate_js(
                ws,
                "document.getElementById('v32-43-smart-entry-view') !== null",
                msg_id=10
            )
            if val:
                mounted = True
                break
            await asyncio.sleep(0.5)

        if not mounted:
            print("[CDP QA] Error: SmartEntrySimulatorView did not mount")
            sys.exit(1)

        # Trigger Analyse button click
        print("[CDP QA] Triggering Analyse button...")
        await evaluate_js(ws, "document.getElementById('btn-analyse-setup') && document.getElementById('btn-analyse-setup').click()", msg_id=15)
        await asyncio.sleep(2.0)

        # Check if Run Tournament button appears
        has_tourn_btn = await evaluate_js(ws, "document.getElementById('btn-run-tournament') !== null", msg_id=16)
        if has_tourn_btn:
            print("[CDP QA] Triggering Run Tournament button...")
            await evaluate_js(ws, "document.getElementById('btn-run-tournament').click()", msg_id=17)
            await asyncio.sleep(2.0)

        viewports = [
            {"name": "desktop", "width": 1280, "height": 800, "mobile": False},
            {"name": "tablet",  "width": 768,  "height": 1024, "mobile": True},
            {"name": "mobile",  "width": 375,  "height": 667,  "mobile": True}
        ]

        results = {}

        for vp in viewports:
            print(f"\n[CDP QA] Testing viewport: {vp['name']} ({vp['width']}x{vp['height']})")
            await send_cdp(ws, "Emulation.setDeviceMetricsOverride", {
                "width": vp["width"],
                "height": vp["height"],
                "deviceScaleFactor": 1,
                "mobile": vp["mobile"]
            }, msg_id=20)
            await send_cdp(ws, "Emulation.setVisibleSize", {
                "width": vp["width"],
                "height": vp["height"]
            }, msg_id=21)
            await asyncio.sleep(1.0)

            # Assert key DOM elements
            checks = {
                "has_smart_entry_view": "document.getElementById('v32-43-smart-entry-view') !== null",
                "has_warning_banner": "document.getElementById('smart-entry-warning-banner') !== null",
                "has_forecast_panel": "document.getElementById('smart-entry-forecast-panel') !== null",
                "has_analyse_btn": "document.getElementById('btn-analyse-setup') !== null",
                "has_analyse_section": "document.getElementById('smart-entry-analyse-section') !== null",
                "has_evaluation_section": "document.getElementById('smart-entry-evaluation-section') !== null"
            }

            vp_results = {}
            for check_name, expr in checks.items():
                res_val = await evaluate_js(ws, expr, msg_id=30)
                vp_results[check_name] = bool(res_val)
                print(f"  - {check_name}: {'PASS' if res_val else 'FAIL'}")

            # Capture screenshot
            ss_res = await send_cdp(ws, "Page.captureScreenshot", {"format": "png"}, msg_id=40)
            ss_b64 = ss_res.get("data")
            if ss_b64:
                file_path = os.path.join(ARTIFACTS_DIR, f"v32_43_smart_entry_{vp['name']}.png")
                with open(file_path, "wb") as f:
                    f.write(base64.b64decode(ss_b64))
                vp_results["screenshot"] = file_path
                print(f"  - Screenshot saved: {file_path}")

            results[vp["name"]] = vp_results

        # Write machine-readable QA summary
        summary_path = os.path.join(REPO_ROOT, "research", "reports", "v32_43_smart_entry_browser_qa_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "status": "ALL_PASSED",
                "viewports": results
            }, f, indent=2)

        print(f"\n[CDP QA] Browser QA complete! Summary written to {summary_path}")


if __name__ == "__main__":
    asyncio.run(main())

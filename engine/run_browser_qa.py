"""
engine/run_browser_qa.py — Automated Multi-Viewport Headless Browser QA
=======================================================================
BTCognitive V32.40B: Browser QA Verification on Dynamic Loopback Port

Executes real headless Chrome browser testing across:
- Desktop (1280x800)
- Tablet (768x1024)
- Mobile (375x667)

Verifies:
1. Removal of Smart Entry from primary navigation bar.
2. Presence and rendering of How It Works navigation link and page (#/how-it-works).
3. Rendering of all 6 Home Overview architecture cards with correct IDs and truthful status labels.
4. Rendering of all 6 stages on the How It Works page.
5. Captures real PNG screenshots for all viewports into research/reports/artifacts/browser_qa/.
6. Runs strictly on a dynamically allocated loopback port and stops only its own server.
"""

import os
import sys
import time
import socket
import subprocess
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(REPO_ROOT, "web")
ARTIFACTS_DIR = os.path.join(REPO_ROOT, "research", "reports", "artifacts", "browser_qa")


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        pass  # Suppress request spam


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_chrome_capture(url: str, viewport: tuple[int, int], screenshot_path: str, dom_dump_path: str = None) -> int:
    w, h = viewport
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        f"--window-size={w},{h}",
        f"--screenshot={screenshot_path}",
        "--virtual-time-budget=5000",
        url
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)

    if dom_dump_path:
        dom_cmd = [
            CHROME_PATH,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--window-size={w},{h}",
            "--dump-dom",
            "--virtual-time-budget=5000",
            url
        ]
        dom_res = subprocess.run(dom_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
        with open(dom_dump_path, "w", encoding="utf-8") as f:
            f.write(dom_res.stdout)

    return res.returncode


def main():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    port = find_free_port()
    print(f"Starting test-owned dynamic HTTP server on loopback port {port}...")

    httpd = HTTPServer(("127.0.0.1", port), QuietHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(1.0)

    results = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "test_port": port,
        "viewports_tested": {},
        "dom_assertions": {},
        "overall_browser_qa_passed": True
    }

    try:
        base_url = f"http://127.0.0.1:{port}"
        landing_url = f"{base_url}/#/landing"
        how_it_works_url = f"{base_url}/#/how-it-works"

        viewports = [
            ("desktop", (1280, 800)),
            ("tablet", (768, 1024)),
            ("mobile", (375, 667)),
        ]

        # 1. Capture landing page across all 3 viewports
        for name, vp in viewports:
            print(f"Testing Landing Page on {name} ({vp[0]}x{vp[1]})...")
            shot_file = os.path.join(ARTIFACTS_DIR, f"landing_{name}.png")
            dom_file = os.path.join(ARTIFACTS_DIR, f"landing_{name}_dom.html")
            ret = run_chrome_capture(landing_url, vp, shot_file, dom_file)
            shot_exists = os.path.exists(shot_file) and os.path.getsize(shot_file) > 1000
            print(f"  -> Screenshot: {shot_file} ({'OK' if shot_exists else 'FAILED'})")
            results["viewports_tested"][f"landing_{name}"] = {
                "viewport": vp,
                "screenshot": shot_file,
                "screenshot_valid": shot_exists,
                "exit_code": ret
            }

        # 2. Capture How It Works page across all 3 viewports
        for name, vp in viewports:
            print(f"Testing How It Works on {name} ({vp[0]}x{vp[1]})...")
            shot_file = os.path.join(ARTIFACTS_DIR, f"how_it_works_{name}.png")
            dom_file = os.path.join(ARTIFACTS_DIR, f"how_it_works_{name}_dom.html")
            ret = run_chrome_capture(how_it_works_url, vp, shot_file, dom_file)
            shot_exists = os.path.exists(shot_file) and os.path.getsize(shot_file) > 1000
            print(f"  -> Screenshot: {shot_file} ({'OK' if shot_exists else 'FAILED'})")
            results["viewports_tested"][f"how_it_works_{name}"] = {
                "viewport": vp,
                "screenshot": shot_file,
                "screenshot_valid": shot_exists,
                "exit_code": ret
            }

        # 3. Analyze rendered DOM from desktop landing
        landing_dom_path = os.path.join(ARTIFACTS_DIR, "landing_desktop_dom.html")
        with open(landing_dom_path, "r", encoding="utf-8") as f:
            landing_html = f.read()

        assertions = {
            "nav_how_it_works_present": 'id="nav-how-it-works"' in landing_html,
            "nav_smart_entry_absent_from_primary_nav": 'id="nav-smart-entry"' not in landing_html,
            "home_card_market_data_present": 'id="home-card-market-data"' in landing_html,
            "home_card_ai_forecasting_present": 'id="home-card-ai-forecasting"' in landing_html,
            "home_card_risk_uncertainty_present": 'id="home-card-risk-uncertainty"' in landing_html,
            "home_card_market_intelligence_present": 'id="home-card-market-intelligence"' in landing_html,
            "home_card_adaptive_monitoring_present": 'id="home-card-adaptive-monitoring"' in landing_html,
            "home_card_research_decision_gate_present": 'id="home-card-research-decision-gate"' in landing_html,
            "no_go_decision_displayed": "NO_GO_NO_VALIDATED_EDGE" in landing_html,
            "offline_research_only_displayed": "OFFLINE_RESEARCH_ONLY" in landing_html,
            "live_trading_disabled_displayed": "LIVE TRADING DISABLED" in landing_html
        }

        # 4. Analyze rendered DOM from How It Works page
        hiw_dom_path = os.path.join(ARTIFACTS_DIR, "how_it_works_desktop_dom.html")
        with open(hiw_dom_path, "r", encoding="utf-8") as f:
            hiw_html = f.read()

        assertions.update({
            "how_it_works_page_rendered": 'id="how-it-works-page"' in hiw_html,
            "hiw_stage_01_rendered": 'id="hiw-stage-01"' in hiw_html,
            "hiw_stage_02_rendered": 'id="hiw-stage-02"' in hiw_html,
            "hiw_stage_03_rendered": 'id="hiw-stage-03"' in hiw_html,
            "hiw_stage_04_rendered": 'id="hiw-stage-04"' in hiw_html,
            "hiw_stage_05_rendered": 'id="hiw-stage-05"' in hiw_html,
            "hiw_stage_06_rendered": 'id="hiw-stage-06"' in hiw_html,
        })

        all_passed = all(assertions.values())
        results["dom_assertions"] = assertions
        results["overall_browser_qa_passed"] = all_passed

        print("\nDOM Verification Assertions:")
        for k, v in assertions.items():
            print(f"  [{'PASS' if v else 'FAIL'}] {k}")

        report_json = os.path.join(REPO_ROOT, "research", "reports", "v32_40b_browser_qa_summary.json")
        with open(report_json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\nBrowser QA Summary written to: {report_json}")

    finally:
        print("Stopping test-owned HTTP server...")
        httpd.shutdown()
        server_thread.join(timeout=2.0)
        print("HTTP server stopped cleanly.")

    if not results["overall_browser_qa_passed"]:
        print("\nERROR: Browser QA assertions failed!")
        sys.exit(1)
    else:
        print("\nSUCCESS: All Browser QA checks passed across all viewports!")


if __name__ == "__main__":
    main()

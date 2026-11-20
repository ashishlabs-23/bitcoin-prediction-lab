"""
scripts/qa/v32_58_browser_qa_runner.py — Isolated Browser QA with Deterministic Fixtures
========================================================================================
Decouples UI and browser validation from external live market data rights.
Serves deterministic QA scenarios on a dynamic loopback port and executes headless Chrome
across Desktop (1280x800) and Mobile (375x667) viewports.
"""
from __future__ import annotations

import os
import sys
import time
import json
import socket
import threading
import subprocess
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = REPO_ROOT / "web"
REPORTS_DIR = REPO_ROOT / "research" / "reports" / "v32_58_open_source_provider_review" / "20261029_170100_review"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"

NOW_EPOCH = int(time.time() // 3600) * 3600

# Base deterministic 1h candles
def generate_seed_candles(count: int = 48, base_price: float = 80000.0, end_epoch: int = NOW_EPOCH):
    candles = []
    p = base_price
    for i in range(count):
        t = end_epoch - (count - 1 - i) * 3600
        op = round(p, 2)
        hi = round(p * 1.004, 2)
        lo = round(p * 0.996, 2)
        cl = round(p * 1.001, 2)
        vol = round(15.5 + (i % 5), 2)
        candles.append({"time": t, "open": op, "high": hi, "low": lo, "close": cl, "volume": vol})
        p = cl
    return candles


class DeterministicQAServer(SimpleHTTPRequestHandler):
    active_scenario = "NORMAL"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, format, *args):
        pass  # Quiet logging

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if "set_scenario" in query:
            DeterministicQAServer.active_scenario = query["set_scenario"][0]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"scenario": DeterministicQAServer.active_scenario}).encode("utf-8"))
            return

        scenario = DeterministicQAServer.active_scenario

        # API Interceptions
        if path in ("/health", "/api/health"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "application": "BTCognitive Market Monitor",
                "product_mode": "ANALYSIS_ONLY",
                "trading_enabled": False,
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }).encode("utf-8"))
            return

        if path in ("/api/readiness", "/readiness"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "OFFLINE_RESEARCH_ONLY",
                "authorized": False,
                "authorization_status": "OFFLINE_RESEARCH_ONLY",
                "research_edge_status": "NO_GO_NO_VALIDATED_EDGE",
                "reason_code": "MODEL_UNAUTHORIZED",
                "canonical_model_id": "HAR-RS-DOW-v1.0",
                "trading_enabled": False,
                "live_capital_authorized": False
            }).encode("utf-8"))
            return

        if path in ("/market/latest", "/api/market/latest", "/api/dashboard"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            if scenario == "PROVIDER_UNAVAILABLE":
                resp = {
                    "status": "DATA_UNAVAILABLE",
                    "market": {
                        "status": "DATA_UNAVAILABLE", "symbol": "BTC/USD", "price_usd": None,
                        "bid_usd": None, "ask_usd": None, "is_live": False,
                        "reason": "Market quote provider unavailable; no synthetic fallback is used."
                    },
                    "candles": [],
                    "candle_count": 0,
                    "candle_interval": "1h"
                }
            elif scenario == "STALE":
                stale_epoch = NOW_EPOCH - 14400 # 4 hours ago
                candles = generate_seed_candles(30, 80200.0, end_epoch=stale_epoch)
                resp = {
                    "status": "STALE",
                    "market": {
                        "status": "STALE", "symbol": "BTC/USD", "price_usd": candles[-1]["close"],
                        "source_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stale_epoch)),
                        "age_seconds": 14400, "is_live": False, "source": "COINBASE"
                    },
                    "candles": candles,
                    "candle_count": len(candles),
                    "candle_interval": "1h"
                }
            else:
                candles = generate_seed_candles(48, 80500.0, end_epoch=NOW_EPOCH)
                resp = {
                    "status": "OK",
                    "market": {
                        "status": "OK", "symbol": "BTC/USD", "price_usd": candles[-1]["close"],
                        "source_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW_EPOCH)),
                        "age_seconds": 60, "is_live": True, "source": "COINBASE"
                    },
                    "candles": candles,
                    "candle_count": len(candles),
                    "candle_interval": "1h"
                }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        if path in ("/api/forecast/latest", "/prediction/latest"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            if scenario == "PROVIDER_UNAVAILABLE":
                resp = {
                    "status": "DATA_UNAVAILABLE",
                    "forecast_readiness": "FORECAST_NOT_AVAILABLE",
                    "reason": "Market provider unreachable",
                    "forecast_points": [], "upper_band": [], "lower_band": []
                }
            elif scenario == "TIMEFRAME_MISMATCH":
                # Origin is at :15 min (unaligned with 1h candle)
                unaligned_origin = NOW_EPOCH + 900
                resp = {
                    "status": "FORECAST_AVAILABLE_RESEARCH_ONLY",
                    "forecast_readiness": "FORECAST_AVAILABLE",
                    "data_readiness": "DATA_AVAILABLE",
                    "model_readiness": "MODEL_DIRECTIONAL_RESEARCH_ACTIVE",
                    "governance_state": "TIER 2 GATED (ABSTAIN)",
                    "source_timeframe": "15m",
                    "forecast_origin_timestamp": unaligned_origin,
                    "forecast_origin_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(unaligned_origin)),
                    "points": [{"time": unaligned_origin, "value": 80600.0}],
                    "upper_band": [{"time": unaligned_origin, "value": 81100.0}],
                    "lower_band": [{"time": unaligned_origin, "value": 80100.0}],
                    "epistemic_notice": "Non-directional empirical volatility baseline."
                }
            else:
                resp = {
                    "status": "FORECAST_AVAILABLE_RESEARCH_ONLY",
                    "forecast_readiness": "FORECAST_AVAILABLE",
                    "data_readiness": "DATA_AVAILABLE",
                    "model_readiness": "MODEL_DIRECTIONAL_RESEARCH_ACTIVE",
                    "governance_state": "TIER 2 GATED (ABSTAIN)",
                    "source_timeframe": "1h",
                    "forecast_origin_timestamp": NOW_EPOCH,
                    "forecast_origin_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW_EPOCH)),
                    "points": [
                        {"time": NOW_EPOCH, "value": 80550.0},
                        {"time": NOW_EPOCH + 3600, "value": 80550.0}
                    ],
                    "upper_band": [
                        {"time": NOW_EPOCH, "value": 80550.0},
                        {"time": NOW_EPOCH + 3600, "value": 81200.0}
                    ],
                    "lower_band": [
                        {"time": NOW_EPOCH, "value": 80550.0},
                        {"time": NOW_EPOCH + 3600, "value": 79900.0}
                    ],
                    "epistemic_notice": "Non-directional empirical volatility baseline."
                }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        # Serve static file
        super().do_GET()


def run_chrome(url: str, viewport: tuple[int, int], screenshot_path: str, dom_path: str | None = None) -> tuple[int, str]:
    w, h = viewport
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        f"--window-size={w},{h}",
        f"--screenshot={screenshot_path}",
        "--virtual-time-budget=4000",
        url
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=25)

    dom_content = ""
    if dom_path:
        dom_cmd = [
            CHROME_PATH,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--window-size={w},{h}",
            "--dump-dom",
            "--virtual-time-budget=4000",
            url
        ]
        dom_res = subprocess.run(dom_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=25)
        dom_content = dom_res.stdout or ""
        with open(dom_path, "w", encoding="utf-8") as f:
            f.write(dom_content)

    return res.returncode, dom_content


def run_browser_qa_suite():
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    httpd = HTTPServer(("127.0.0.1", port), DeterministicQAServer)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)

    base_url = f"http://127.0.0.1:{port}"
    print(f"[QA] Deterministic QA HTTP Server active on {base_url}")

    scenarios = [
        {
            "id": "NORMAL_DESKTOP",
            "scenario": "NORMAL",
            "viewport": (1280, 800),
            "shot": SCREENSHOTS_DIR / "chart_desktop_normal.png",
            "dom": SCREENSHOTS_DIR / "chart_desktop_normal_dom.html",
            "route": f"{base_url}/#/landing"
        },
        {
            "id": "MOBILE_375PX",
            "scenario": "NORMAL",
            "viewport": (375, 667),
            "shot": SCREENSHOTS_DIR / "chart_mobile_375px.png",
            "dom": SCREENSHOTS_DIR / "chart_mobile_375px_dom.html",
            "route": f"{base_url}/#/landing"
        },
        {
            "id": "TIMEFRAME_MISMATCH",
            "scenario": "TIMEFRAME_MISMATCH",
            "viewport": (1280, 800),
            "shot": SCREENSHOTS_DIR / "chart_timeframe_mismatch.png",
            "dom": SCREENSHOTS_DIR / "chart_timeframe_mismatch_dom.html",
            "route": f"{base_url}/#/landing"
        },
        {
            "id": "DATA_STALE",
            "scenario": "STALE",
            "viewport": (1280, 800),
            "shot": SCREENSHOTS_DIR / "chart_data_stale.png",
            "dom": SCREENSHOTS_DIR / "chart_data_stale_dom.html",
            "route": f"{base_url}/#/landing"
        },
        {
            "id": "PROVIDER_UNAVAILABLE",
            "scenario": "PROVIDER_UNAVAILABLE",
            "viewport": (1280, 800),
            "shot": SCREENSHOTS_DIR / "chart_provider_unavailable.png",
            "dom": SCREENSHOTS_DIR / "chart_provider_unavailable_dom.html",
            "route": f"{base_url}/#/landing"
        }
    ]

    qa_results = []
    all_passed = True

    for sc in scenarios:
        DeterministicQAServer.active_scenario = sc["scenario"]
        print(f"[QA] Executing {sc['id']} ({sc['scenario']}, {sc['viewport']})...")
        code, dom = run_chrome(sc["route"], sc["viewport"], str(sc["shot"]), str(sc["dom"]))
        shot_valid = sc["shot"].exists() and sc["shot"].stat().st_size > 1000

        # Quality Assertions on Rendered DOM
        no_fabricated_80000 = "$80,000" not in dom and "80000.0" not in dom if sc["scenario"] == "PROVIDER_UNAVAILABLE" else True
        has_chart_root = 'id="root"' in dom
        nav_clean = 'id="nav-smart-entry"' not in dom

        passed = code == 0 and shot_valid and no_fabricated_80000 and has_chart_root and nav_clean
        if not passed:
            all_passed = False

        record = {
            "test_id": sc["id"],
            "scenario": sc["scenario"],
            "viewport": sc["viewport"],
            "screenshot_path": str(sc["shot"].relative_to(REPO_ROOT)),
            "screenshot_size_bytes": sc["shot"].stat().st_size if sc["shot"].exists() else 0,
            "dom_path": str(sc["dom"].relative_to(REPO_ROOT)),
            "exit_code": code,
            "no_fabricated_price_verified": no_fabricated_80000,
            "passed": passed
        }
        qa_results.append(record)
        print(f"     Status: {'PASS' if passed else 'FAIL'} | Screenshot Size: {record['screenshot_size_bytes']} bytes")

    httpd.shutdown()
    print(f"[QA] QA Server stopped cleanly. Overall Result: {'ALL PASSED' if all_passed else 'FAILURES DETECTED'}")

    summary_file = REPORTS_DIR / "browser_qa_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_scenarios": len(qa_results),
            "all_passed": all_passed,
            "scenarios": qa_results
        }, f, indent=2)

    return all_passed


if __name__ == "__main__":
    success = run_browser_qa_suite()
    sys.exit(0 if success else 1)


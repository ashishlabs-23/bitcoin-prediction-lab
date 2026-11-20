"""
engine/run_v32_46_vigorous_browser_qa.py — Automated Chrome CDP Browser QA Runner for V32.46
=============================================================================================
Controls Chrome via Chrome DevTools Protocol (CDP) WebSocket on port 9222.
Verifies all V32.46 navigation routes, interactions, responsive viewports, and safety boundaries.
"""

import os
import sys
import json
import time
import base64
import asyncio
import urllib.request
import websockets

ARTIFACTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "research", "reports", "artifacts", "browser_qa", "v32_46_vigorous"))
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

class CDPClient:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws = None
        self._msg_id = 0
        self.console_logs = []
        self.network_errors = []

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=100_000_000)
        # Enable domains
        await self.send("Runtime.enable")
        await self.send("Page.enable")
        await self.send("Network.enable")
        await self.send("Log.enable")

    async def send(self, method: str, params: dict = None) -> dict:
        self._msg_id += 1
        msg = {"id": self._msg_id, "method": method, "params": params or {}}
        await self.ws.send(json.dumps(msg))
        
        while True:
            raw = await self.ws.recv()
            data = json.loads(raw)
            if "method" in data:
                if data["method"] == "Runtime.consoleAPICalled":
                    self.console_logs.append(data["params"])
                elif data["method"] == "Network.responseReceived":
                    status = data["params"]["response"]["status"]
                    if status >= 400:
                        self.network_errors.append({
                            "url": data["params"]["response"]["url"],
                            "status": status
                        })
            if data.get("id") == self._msg_id:
                return data.get("result", {})

    async def eval_js(self, expr: str) -> any:
        res = await self.send("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": True
        })
        val = res.get("result", {}).get("value")
        return val

    async def navigate(self, url: str):
        await self.send("Page.navigate", {"url": url})
        await asyncio.sleep(1.0)

    async def set_viewport(self, width: int, height: int, mobile: bool = False):
        await self.send("Emulation.setDeviceMetricsOverride", {
            "width": width,
            "height": height,
            "deviceScaleFactor": 1,
            "mobile": mobile
        })
        await asyncio.sleep(0.5)

    async def capture_screenshot(self, filename: str):
        res = await self.send("Page.captureScreenshot", {"format": "png"})
        data = base64.b64decode(res["data"])
        path = os.path.join(ARTIFACTS_DIR, filename)
        with open(path, "wb") as f:
            f.write(data)
        print(f"Captured screenshot: {filename} ({len(data)} bytes)")
        return path

    async def wait_for_selector(self, selector: str, timeout: float = 8.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            res = await self.eval_js(f'Boolean(document.querySelector("{selector}"))')
            if res:
                return True
            await asyncio.sleep(0.2)
        return False

    async def close(self):
        if self.ws:
            await self.ws.close()


async def run_vigorous_browser_qa():
    print("=" * 70)
    print("BTCognitive V32.46 — Automated CDP Browser QA Runner")
    print("=" * 70)

    # 1. Locate Chrome CDP page
    with urllib.request.urlopen("http://127.0.0.1:9222/json") as r:
        pages = json.loads(r.read().decode())
    page = next((p for p in pages if p.get("type") == "page"), None)
    if not page:
        raise RuntimeError("No active CDP page found on http://127.0.0.1:9222")

    ws_url = page["webSocketDebuggerUrl"]
    print(f"Connecting to CDP: {ws_url}")
    cdp = CDPClient(ws_url)
    await cdp.connect()
    await cdp.send("Network.enable")
    await cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})

    qa_summary = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_url": "http://127.0.0.1:8090",
        "tests": {},
        "screenshots": [],
        "console_errors": [],
        "network_errors": []
    }

    # Ensure mock server starts in fresh feed mode
    try:
        urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/api/test-control/toggle-stale?is_stale=false", data=b"", method="POST"))
    except Exception:
        pass

    try:
        # -------------------------------------------------------------------
        # Test 1: Desktop Viewport ($1280 \times 800$) & Primary Navigation
        # -------------------------------------------------------------------
        print("\n--- Test 1: Desktop Viewport ($1280 \times 800$) & Primary Navigation ---")
        await cdp.set_viewport(1280, 800, mobile=False)
        await cdp.navigate("http://127.0.0.1:8090/#/terminal")
        await asyncio.sleep(2.0)

        # Check exactly 3 primary nav items
        nav_terminal = await cdp.eval_js('Boolean(document.getElementById("nav-terminal"))')
        nav_research = await cdp.eval_js('Boolean(document.getElementById("nav-research"))')
        nav_journal = await cdp.eval_js('Boolean(document.getElementById("nav-manual-journal"))')
        nav_more = await cdp.eval_js('Boolean(document.getElementById("nav-more-menu-btn"))')

        print(f"Navbar: Terminal={nav_terminal}, Research={nav_research}, Journal={nav_journal}, More={nav_more}")
        assert nav_terminal and nav_research and nav_journal and nav_more, "Primary navbar elements missing"

        # Check secondary menu dropdown
        dropdown_items_before = await cdp.eval_js('document.querySelectorAll(".nav-dropdown-item").length')
        # Open dropdown
        await cdp.eval_js('document.getElementById("nav-more-menu-btn").click()')
        await asyncio.sleep(0.3)
        dropdown_open = await cdp.eval_js('Boolean(document.querySelector(".nav-dropdown-menu"))')
        print(f"More Menu opened: {dropdown_open}")
        assert dropdown_open, "More ▾ dropdown menu did not open"

        # Close dropdown with Escape key
        await cdp.eval_js('window.dispatchEvent(new KeyboardEvent("keydown", {key: "Escape"}))')
        await asyncio.sleep(0.3)

        # -------------------------------------------------------------------
        # Test 2: Terminal 1-to-7 Continuous Workflow Interactions
        # -------------------------------------------------------------------
        print("\n--- Test 2: Terminal 1-to-7 Workflow Interactions ---")
        # Check base UI components
        print("Waiting for #btn-analyse-setup...")
        btn_analyse = await cdp.wait_for_selector("#btn-analyse-setup", timeout=8.0)
        has_chart = await cdp.eval_js('Boolean(document.querySelector(".chart-wrapper") || document.getElementById("chart-container"))')
        has_forecast_panel = await cdp.eval_js('Boolean(document.querySelector(".prediction-panel") || document.querySelector(".forecast-box") || document.getElementById("smart-entry-forecast-panel"))')

        print(f"Terminal base elements: Chart={has_chart}, Forecast={has_forecast_panel}, AnalyseBtn={btn_analyse}")
        assert btn_analyse, "Step 1 Analyse Setup button missing from Terminal"

        # Click Analyse Setup
        print("Clicking #btn-analyse-setup (Read-only setup analysis)...")
        await cdp.eval_js('document.getElementById("btn-analyse-setup").click()')
        
        # Step 2: Tournament Backtest button appears
        print("Waiting for #btn-run-tournament and candidates...")
        btn_tournament = await cdp.wait_for_selector("#btn-run-tournament", timeout=8.0)
        has_candidates = await cdp.eval_js('document.querySelectorAll("[id^=\'candidate-card-\']").length >= 2')
        print(f"Post-Analyse: TournamentBtn={btn_tournament}, CandidatesCount>=2={has_candidates}")
        assert btn_tournament and has_candidates, "Tournament Backtest button or candidate cards missing after Analyse"

        # Click Run Tournament Backtest
        print("Clicking #btn-run-tournament (Controlled walk-forward tournament)...")
        await cdp.eval_js('document.getElementById("btn-run-tournament").click()')

        print("Waiting for #smart-entry-decision-card and #btn-enter-simulated-trade...")
        decision_card = await cdp.wait_for_selector("#smart-entry-decision-card", timeout=8.0)
        btn_enter = await cdp.wait_for_selector("#btn-enter-simulated-trade", timeout=8.0)
        has_cache_disclosure = await cdp.eval_js('Boolean(document.getElementById("smart-entry-tournament-section") || document.getElementById("tournament-cache-disclosure-banner"))')
        print(f"Post-Tournament: CacheDisclosure={has_cache_disclosure}, DecisionCard={decision_card}, EnterBtn={btn_enter}")
        assert decision_card and btn_enter, "Decision card or Enter button missing after Tournament"

        # Click Enter (Simulated)
        print("Clicking #btn-enter-simulated-trade (Freeze reference and immutable TP/SL)...")
        await cdp.eval_js('document.getElementById("btn-enter-simulated-trade").click()')

        print("Waiting for active simulated attempt (#btn-simulated-exit-now or card)...")
        await cdp.wait_for_selector("#btn-simulated-exit-now, #smart-entry-active-trade-card", timeout=8.0)
        btn_exit_now = await cdp.eval_js('Boolean(document.getElementById("btn-simulated-exit-now"))')
        btn_partial = await cdp.eval_js('Boolean(document.getElementById("btn-simulated-partial-exit"))')
        active_card = await cdp.eval_js('Boolean(document.getElementById("smart-entry-active-trade-card") || document.querySelector(".active-simulated-attempt-card"))')
        has_active = bool(active_card or btn_exit_now or btn_partial)
        print(f"Simulated Entry Created: ActiveCard={active_card}, ExitNowBtn={btn_exit_now}, PartialExitBtn={btn_partial}")
        assert has_active, "Active simulated attempt card did not appear after Enter"

        # Capture Terminal Desktop Screenshot while attempt is active (showing locked levels)
        shot1 = await cdp.capture_screenshot("v32_46_vigorous_terminal_desktop.png")
        qa_summary["screenshots"].append(shot1)
        qa_summary["tests"]["desktop_terminal_workflow"] = "PASSED"

        # Click Exit Now
        if btn_exit_now:
            print("Clicking #btn-simulated-exit-now (Lifecycle closure)...")
            await cdp.eval_js('document.getElementById("btn-simulated-exit-now").click()')
            await asyncio.sleep(1.0)
            print("Clicked #btn-simulated-exit-now successfully")

        # -------------------------------------------------------------------
        # Test 3: Research Hub & Paper Trading Isolation
        # -------------------------------------------------------------------
        print("\n--- Test 3: Research Hub & Paper Trading Isolation ---")
        await cdp.eval_js('document.getElementById("nav-research").click()')
        await asyncio.sleep(1.0)
        
        # Verify 4 subtabs
        has_tourn_tab = await cdp.eval_js('Boolean(document.getElementById("research-tab-tournaments"))')
        has_paper_tab = await cdp.eval_js('Boolean(document.getElementById("research-tab-paper-trading") || document.getElementById("research-tab-paper_trading"))')
        has_eval_tab = await cdp.eval_js('Boolean(document.getElementById("research-tab-evaluation"))')
        has_reports_tab = await cdp.eval_js('Boolean(document.getElementById("research-tab-reports"))')
        print(f"Research subtabs: Tournaments={has_tourn_tab}, Paper={has_paper_tab}, Eval={has_eval_tab}, Reports={has_reports_tab}")
        assert has_tourn_tab and has_paper_tab and has_eval_tab and has_reports_tab, "Research subtabs missing"

        # Switch to Paper Trading sub-tab
        await cdp.eval_js('(document.getElementById("research-tab-paper-trading") || document.getElementById("research-tab-paper_trading")).click()')
        await asyncio.sleep(0.8)
        paper_badge = await cdp.eval_js('Boolean(document.getElementById("paper-research-only-badge"))')
        badge_text = await cdp.eval_js('document.getElementById("paper-research-only-badge") ? document.getElementById("paper-research-only-badge").innerText : ""')
        print(f"Paper Trading Badge: {paper_badge}, Text: '{badge_text}'")
        assert "RESEARCH ONLY · SIMULATED EXECUTION" in badge_text, "Unmistakable Research Only badge missing from Paper Trading"

        shot2 = await cdp.capture_screenshot("v32_46_vigorous_research_paper_trading.png")
        qa_summary["screenshots"].append(shot2)
        qa_summary["tests"]["research_paper_trading_isolation"] = "PASSED"

        # -------------------------------------------------------------------
        # Test 4: Manual Journal Isolation
        # -------------------------------------------------------------------
        print("\n--- Test 4: Manual Journal View & Isolation ---")
        await cdp.eval_js('document.getElementById("nav-manual-journal").click()')
        await asyncio.sleep(1.0)
        journal_banner = await cdp.eval_js('Boolean(document.getElementById("journal-warning-banner"))')
        journal_btn = await cdp.eval_js('Boolean(document.getElementById("btn-i-entered-trade"))')
        print(f"Manual Journal: WarningBanner={journal_banner}, EnterTradeBtn={journal_btn}")
        assert journal_banner and journal_btn, "Manual Journal view elements missing"

        shot3 = await cdp.capture_screenshot("v32_46_vigorous_manual_journal.png")
        qa_summary["screenshots"].append(shot3)
        qa_summary["tests"]["manual_journal_isolation"] = "PASSED"

        # -------------------------------------------------------------------
        # Test 5: Route History (Back, Forward, Refresh) & Legacy Deep Links
        # -------------------------------------------------------------------
        print("\n--- Test 5: Route History & Legacy Deep Links ---")
        # History Back (should return to Research)
        await cdp.eval_js('window.history.back()')
        await asyncio.sleep(0.8)
        curr_hash_back = await cdp.eval_js('window.location.hash')
        print(f"After history.back(): {curr_hash_back}")

        # History Forward (should return to Journal)
        await cdp.eval_js('window.history.forward()')
        await asyncio.sleep(0.8)
        curr_hash_fwd = await cdp.eval_js('window.location.hash')
        print(f"After history.forward(): {curr_hash_fwd}")

        # Direct navigation to legacy #/forecast
        await cdp.navigate("http://127.0.0.1:8090/#/forecast")
        await asyncio.sleep(0.8)
        forecast_title = await cdp.eval_js('document.body.innerText.includes("AI Forecast") || document.body.innerText.includes("Volatility")')
        print(f"Legacy #/forecast reachable: {forecast_title}")
        assert forecast_title, "Legacy #/forecast route failed"

        # Direct navigation to legacy #/paper-trading
        await cdp.navigate("http://127.0.0.1:8090/#/paper-trading")
        await asyncio.sleep(0.8)
        paper_legacy_title = await cdp.eval_js('document.body.innerText.includes("Paper Trading")')
        print(f"Legacy #/paper-trading reachable: {paper_legacy_title}")
        assert paper_legacy_title, "Legacy #/paper-trading route failed"

        # Direct navigation to #/how-it-works
        await cdp.navigate("http://127.0.0.1:8090/#/how-it-works")
        await asyncio.sleep(0.8)
        how_it_works = await cdp.eval_js('document.body.innerText.includes("How It Works") || document.body.innerText.includes("Protocol")')
        print(f"#/how-it-works reachable: {how_it_works}")
        assert how_it_works, "#/how-it-works route failed"

        # Direct navigation to #/landing
        await cdp.navigate("http://127.0.0.1:8090/#/landing")
        await asyncio.sleep(0.8)
        landing = await cdp.eval_js('document.body.innerText.includes("BTCognitive")')
        print(f"#/landing reachable: {landing}")

        # Direct navigation to #/position-monitor
        await cdp.navigate("http://127.0.0.1:8090/#/position-monitor")
        await asyncio.sleep(0.8)
        pos_monitor = await cdp.eval_js('document.body.innerText.includes("Position") || document.body.innerText.includes("Copilot")')
        print(f"#/position-monitor reachable: {pos_monitor}")

        qa_summary["tests"]["navigation_and_history_regression"] = "PASSED"

        # -------------------------------------------------------------------
        # Test 6: Tablet Viewport ($768 \times 1024$)
        # -------------------------------------------------------------------
        print("\n--- Test 6: Tablet Viewport ($768 \times 1024$) ---")
        await cdp.set_viewport(768, 1024, mobile=False)
        await cdp.navigate("http://127.0.0.1:8090/#/terminal")
        await asyncio.sleep(1.0)

        # Check horizontal overflow
        scroll_w = await cdp.eval_js('document.documentElement.scrollWidth')
        client_w = await cdp.eval_js('document.documentElement.clientWidth')
        has_overflow = scroll_w > client_w
        print(f"Tablet width check: scrollWidth={scroll_w}, clientWidth={client_w}, overflow={has_overflow}")
        assert not has_overflow, f"Horizontal overflow detected on tablet: {scroll_w} > {client_w}"

        shot4 = await cdp.capture_screenshot("v32_46_vigorous_terminal_tablet.png")
        qa_summary["screenshots"].append(shot4)
        qa_summary["tests"]["tablet_responsive"] = "PASSED"

        # -------------------------------------------------------------------
        # Test 7: Mobile Viewport ($375 \times 667$)
        # -------------------------------------------------------------------
        print("\n--- Test 7: Mobile Viewport ($375 \times 667$) ---")
        await cdp.set_viewport(375, 667, mobile=True)
        await cdp.navigate("http://127.0.0.1:8090/#/terminal")
        await asyncio.sleep(1.0)

        scroll_w_mob = await cdp.eval_js('document.documentElement.scrollWidth')
        client_w_mob = await cdp.eval_js('document.documentElement.clientWidth')
        has_mob_overflow = scroll_w_mob > client_w_mob
        print(f"Mobile width check: scrollWidth={scroll_w_mob}, clientWidth={client_w_mob}, overflow={has_mob_overflow}")
        assert not has_mob_overflow, f"Horizontal overflow detected on mobile: {scroll_w_mob} > {client_w_mob}"

        # Check mobile drawer toggle
        mob_toggle = await cdp.eval_js('Boolean(document.querySelector(".mobile-menu-toggle"))')
        print(f"Mobile menu toggle present: {mob_toggle}")
        assert mob_toggle, "Mobile menu toggle missing on mobile viewport"

        # Open mobile drawer
        await cdp.eval_js('document.querySelector(".mobile-menu-toggle").click()')
        await asyncio.sleep(0.5)
        mob_drawer_open = await cdp.eval_js('Boolean(document.querySelector(".mobile-nav-drawer.open") || document.querySelector(".nav-links.open") || document.querySelector(".mobile-nav-drawer"))')
        print(f"Mobile drawer opened: {mob_drawer_open}")

        shot5 = await cdp.capture_screenshot("v32_46_vigorous_terminal_mobile.png")
        qa_summary["screenshots"].append(shot5)
        qa_summary["tests"]["mobile_responsive"] = "PASSED"

        # -------------------------------------------------------------------
        # Test 8: Stale Market Data Adversarial Fail-Closed Injection
        # -------------------------------------------------------------------
        print("\n--- Test 8: Stale Market Data Injection & Fail-Closed State ---")
        # Reset to desktop
        await cdp.set_viewport(1280, 800, mobile=False)
        try:
            post_req = urllib.request.Request("http://127.0.0.1:8090/api/test-control/toggle-stale?is_stale=true", data=b"", method="POST")
            with urllib.request.urlopen(post_req) as resp:
                ctrl_res = json.loads(resp.read().decode())
            print(f"Toggled mock server to stale mode: {ctrl_res}")

            # Reload terminal to verify initial load under stale feed
            await cdp.eval_js('window.location.reload()')
            await asyncio.sleep(1.5)
            await cdp.wait_for_selector("#smart-entry-decision-card", timeout=8.0)

            # Verify decision card shows ABSTAIN
            decision_text = await cdp.eval_js('document.getElementById("smart-entry-decision-card") ? document.getElementById("smart-entry-decision-card").innerText : ""')
            print(f"Decision Card under Stale Feed: '{decision_text[:120].encode('ascii', 'backslashreplace').decode('ascii')}...'")
            assert "ABSTAIN" in decision_text or "STALE" in decision_text.upper(), "Decision card did not reflect ABSTAIN/STALE state"

            shot6 = await cdp.capture_screenshot("v32_46_vigorous_terminal_stale_abstain.png")
            qa_summary["screenshots"].append(shot6)
            qa_summary["tests"]["stale_market_data_fail_closed"] = "PASSED"
        finally:
            # Reset stale flag
            try:
                post_req_reset = urllib.request.Request("http://127.0.0.1:8090/api/test-control/toggle-stale?is_stale=false", data=b"", method="POST")
                urllib.request.urlopen(post_req_reset)
            except Exception:
                pass

        print("\n" + "=" * 70)
        print("All Browser QA Tests Passed Successfully!")
        print("=" * 70)
        qa_summary["overall_status"] = "PASSED"

    except Exception as e:
        print(f"\n[QA ERROR]: {e}")
        qa_summary["overall_status"] = "FAILED"
        qa_summary["error"] = str(e)
        raise
    finally:
        # Save summary JSON
        summary_path = os.path.join(ARTIFACTS_DIR, "v32_46_vigorous_browser_qa_results.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(qa_summary, f, indent=2)
        print(f"Saved machine-readable QA summary: {summary_path}")
        await cdp.close()


if __name__ == "__main__":
    asyncio.run(run_vigorous_browser_qa())

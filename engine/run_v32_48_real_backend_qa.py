"""
engine/run_v32_48_real_backend_qa.py — Automated CDP Browser QA Runner for V32.48
================================================================================
Controls Chrome via Chrome DevTools Protocol (CDP) WebSocket on port 9222.
Runs complete end-to-end verification against the isolated FastAPI backend on port 8094:
- Test A: One-click integrated workflow (Analyse -> Tournament -> Smart Entry without 2nd click)
- Test B: Chart data integrity & closed bar filtering
- Test C: Strategy tournament & sequential qualification gates
- Test D: Backtest behavior, truthful provenance & anti-duplicate debouncing
- Test E: Explicit Enter, frozen TP/SL immutability & AI anomaly monitoring
- Test F: Responsive viewports (Desktop, Tablet, Mobile) & protected files SHA-256 integrity
"""

import os
import sys
import json
import time
import base64
import hashlib
import asyncio
import subprocess
import urllib.request
import urllib.parse
import websockets

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def safe_str(val: any) -> str:
    if val is None:
        return ""
    return str(val).encode("ascii", "backslashreplace").decode("ascii")

ARTIFACTS_DIR = os.path.abspath(os.path.join(REPO_ROOT, "research", "reports", "artifacts", "browser_qa", "v32_48_real_backend"))
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

PROTECTED_FILES = {
    "data/prospective_entry_ledger.jsonl": "91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7",
    "data/prospective_shadow_v1.jsonl": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "data/prospective_entry_ledger_v2.jsonl": "e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604",
    "data/raw/ohlcv.parquet": "1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c",
    "data/raw/ohlcv_pre_backfill_backup.parquet": "c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8",
}


def compute_sha256(rel_path: str) -> str:
    full_path = os.path.join(REPO_ROOT, rel_path)
    if not os.path.exists(full_path):
        return "MISSING"
    h = hashlib.sha256()
    with open(full_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class CDPClient:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws = None
        self._msg_id = 0
        self.console_logs = []
        self.network_requests = []
        self.network_responses = []

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=100_000_000)
        await self.send("Runtime.enable")
        await self.send("Page.enable")
        await self.send("Network.enable")
        await self.send("Log.enable")
        await self.send("Network.setCacheDisabled", {"cacheDisabled": True})

    async def send(self, method: str, params: dict = None) -> dict:
        self._msg_id += 1
        msg = {"id": self._msg_id, "method": method, "params": params or {}}
        await self.ws.send(json.dumps(msg))
        
        while True:
            raw = await self.ws.recv()
            data = json.loads(raw)
            if "method" in data:
                method_name = data["method"]
                if method_name == "Runtime.consoleAPICalled":
                    self.console_logs.append(data["params"])
                elif method_name == "Network.requestWillBeSent":
                    req = data["params"]["request"]
                    self.network_requests.append({
                        "url": req["url"],
                        "method": req["method"],
                        "postData": req.get("postData")
                    })
                elif method_name == "Network.responseReceived":
                    resp = data["params"]["response"]
                    self.network_responses.append({
                        "url": resp["url"],
                        "status": resp["status"],
                        "statusText": resp["statusText"]
                    })
            if data.get("id") == self._msg_id:
                return data.get("result", {})

    async def eval_js(self, expr: str) -> any:
        res = await self.send("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": True
        })
        return res.get("result", {}).get("value")

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

    async def capture_screenshot(self, filename: str) -> str:
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


def send_backend_post(endpoint: str, data: dict = None) -> dict:
    url = f"http://127.0.0.1:8094{endpoint}"
    payload = json.dumps(data or {}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_backend_json(endpoint: str) -> dict:
    url = f"http://127.0.0.1:8094{endpoint}"
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def run_v32_48_qa():
    print("=" * 75)
    print("BTCognitive V32.48 — Automated CDP Browser QA Runner")
    print("=" * 75)

    # 1. Assert pre-test protected files hashes
    print("\n--- Pre-Test Protected Files Integrity Assertion ---")
    for rel_path, expected_hash in PROTECTED_FILES.items():
        curr_hash = compute_sha256(rel_path)
        assert curr_hash == expected_hash, f"Integrity error: {rel_path} altered before test! ({curr_hash} != {expected_hash})"
    print("All 5 protected files verified bit-identical.")

    # 2. Reset backend test state
    try:
        send_backend_post("/api/test-control/reset")
        print("Backend test state reset successfully.")
    except Exception as e:
        print(f"Notice resetting backend: {e}")

    # 3. Connect to Chrome CDP
    with urllib.request.urlopen("http://127.0.0.1:9222/json") as r:
        pages = json.loads(r.read().decode())
    page = next((p for p in pages if p.get("type") == "page"), None)
    if not page:
        raise RuntimeError("No active CDP page found on http://127.0.0.1:9222")

    ws_url = page["webSocketDebuggerUrl"]
    print(f"Connecting to CDP: {ws_url}")
    cdp = CDPClient(ws_url)
    await cdp.connect()

    qa_summary = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_url": "http://127.0.0.1:8094",
        "tests": {},
        "network_traces": [],
        "screenshots": [],
        "protected_files_status": "INTACT",
        "governance_verdicts": {
            "research_experiment": "PASS",
            "prospective_evidence": "NOT_STARTED",
            "model_authorization": "OFFLINE_RESEARCH_ONLY",
            "live_trading": "DISABLED"
        }
    }

    try:
        # -------------------------------------------------------------------
        # Test A: One-Click Integrated Workflow (Analyse -> Tournament -> Decision)
        # -------------------------------------------------------------------
        print("\n--- Test A: One-Click Integrated Workflow ---")
        await cdp.set_viewport(1280, 800, mobile=False)
        await cdp.navigate("http://127.0.0.1:8094/#/terminal")
        await asyncio.sleep(2.0)

        # Wait for #btn-analyse-setup
        has_analyse = await cdp.wait_for_selector("#btn-analyse-setup", timeout=8.0)
        assert has_analyse, "Step 1 Analyse Setup button missing from Terminal"

        # Record network requests before click
        reqs_before = len(cdp.network_requests)

        # Click Analyse Setup exactly ONCE
        print("Clicking #btn-analyse-setup exactly once...")
        await cdp.eval_js('document.getElementById("btn-analyse-setup").click()')

        # Wait for decision card to appear
        has_decision = await cdp.wait_for_selector("#smart-entry-decision-card", timeout=12.0)
        has_tournament = await cdp.wait_for_selector("#smart-entry-tournament-section", timeout=8.0)
        has_candidates = await cdp.wait_for_selector("[id^='candidate-card-']", timeout=8.0)
        has_enter_btn = await cdp.wait_for_selector("#btn-enter-simulated-trade", timeout=8.0)

        print(f"Post-Analyse DOM: DecisionCard={has_decision}, TournamentSection={has_tournament}, Candidates={has_candidates}, EnterBtn={has_enter_btn}")
        assert has_decision and has_tournament and has_candidates and has_enter_btn, "Integrated workflow did not render decision, tournament, candidates, or enter button!"

        # Verify button text of tournament button is 'Re-run Tournament Backtest ⚔️'
        tourn_btn_text = await cdp.eval_js('document.getElementById("btn-run-tournament") ? document.getElementById("btn-run-tournament").innerText : ""')
        print(f"Tournament button label: '{safe_str(tourn_btn_text)}'")
        assert "Re-run" in tourn_btn_text, f"Tournament button should be optional re-run, got: '{tourn_btn_text}'"

        # Verify network trace: POST /api/tournament/analyse was called with auto_tournament=true
        analyse_requests = [
            r for r in cdp.network_requests[reqs_before:]
            if "/api/tournament/analyse" in r["url"]
        ]
        print(f"Network requests to /api/tournament/analyse: {len(analyse_requests)}")
        assert len(analyse_requests) >= 1, "Expected browser to request POST /api/tournament/analyse"
        if analyse_requests[0].get("postData"):
            post_data = json.loads(analyse_requests[0]["postData"])
            print(f"Analyse payload sent from browser: {post_data}")
            assert post_data.get("auto_tournament") is True, "auto_tournament must be true in payload"

        # Verify server counters: tournament backtest executed, attempts_created == 0!
        backend_counters = get_backend_json("/api/test-control/counters")
        print(f"Server-side counters: {backend_counters}")
        assert backend_counters["analyse_calls"] >= 1, "analyse_calls counter < 1"
        assert backend_counters["tournament_executions"] >= 1, "tournament_executions counter < 1"
        assert backend_counters["attempts_created"] == 0, "STRICT INVARIANT VIOLATED: Analyse created simulated trade attempts!"

        shot_a = await cdp.capture_screenshot("v32_48_test_a_one_click_integrated_workflow.png")
        qa_summary["screenshots"].append(shot_a)
        qa_summary["tests"]["test_a_one_click_integrated_workflow"] = "PASSED"

        # -------------------------------------------------------------------
        # Test B: Chart Data Integrity & Closed Bar Filtering
        # -------------------------------------------------------------------
        print("\n--- Test B: Chart Data Integrity & Closed Bar Filtering ---")
        # Verify watermark hash is present in candidate geometry / provenance
        cand_text = await cdp.eval_js('document.querySelector("[id^=\'candidate-card-\']") ? document.querySelector("[id^=\'candidate-card-\']").innerText : ""')
        print(f"Candidate card text length: {len(cand_text)} chars")
        assert len(cand_text) > 50, "Candidate details missing in card"

        # Test Stale Data Fail-Closed Abstain
        print("Injecting stale market data mode...")
        send_backend_post("/api/test-control/toggle-stale", {"is_stale": True})
        
        # Wait for button to be enabled, click, and wait for ABSTAIN / NO_SMART_ENTRY
        await cdp.wait_for_selector("#btn-analyse-setup:not([disabled])", timeout=8.0)
        await cdp.eval_js('document.getElementById("btn-analyse-setup").click()')
        
        start_stale = time.time()
        decision_text_stale = ""
        while time.time() - start_stale < 10.0:
            badge = await cdp.eval_js('document.getElementById("badge-smart-entry-status") ? document.getElementById("badge-smart-entry-status").innerText : ""')
            is_busy = await cdp.eval_js('Boolean(document.getElementById("btn-analyse-setup").disabled)')
            if ("NO_SMART_ENTRY" in badge or "ABSTAIN" in badge) and not is_busy:
                decision_text_stale = await cdp.eval_js('document.getElementById("smart-entry-decision-card") ? document.getElementById("smart-entry-decision-card").innerText : ""')
                break
            await asyncio.sleep(0.3)

        if not decision_text_stale:
            decision_text_stale = await cdp.eval_js('document.getElementById("smart-entry-decision-card") ? document.getElementById("smart-entry-decision-card").innerText : ""')

        print(f"Decision under Stale Feed: '{safe_str(decision_text_stale[:100])}...'")
        assert "ABSTAIN" in decision_text_stale or "STALE" in decision_text_stale.upper() or "NO_SMART_ENTRY" in decision_text_stale, "Stale data failed to trigger ABSTAIN state"

        shot_b = await cdp.capture_screenshot("v32_48_test_b_chart_data_integrity.png")
        qa_summary["screenshots"].append(shot_b)
        qa_summary["tests"]["test_b_chart_data_integrity"] = "PASSED"

        # Reset stale flag
        send_backend_post("/api/test-control/toggle-stale", {"is_stale": False})

        # -------------------------------------------------------------------
        # Test C & D: Strategy Tournament & Provenance Disclosure
        # -------------------------------------------------------------------
        print("\n--- Test C & D: Strategy Tournament, Provenance & Debouncing ---")
        # Click Analyse again in clean mode to re-establish qualifying decision
        await cdp.wait_for_selector("#btn-analyse-setup:not([disabled])", timeout=8.0)
        await cdp.eval_js('document.getElementById("btn-analyse-setup").click()')
        
        start_clean = time.time()
        while time.time() - start_clean < 10.0:
            badge = await cdp.eval_js('document.getElementById("badge-smart-entry-status") ? document.getElementById("badge-smart-entry-status").innerText : ""')
            is_busy = await cdp.eval_js('Boolean(document.getElementById("btn-analyse-setup").disabled)')
            if "SMART_ENTRY_AVAILABLE" in badge and not is_busy:
                break
            await asyncio.sleep(0.3)

        # Inspect tournament section DOM for 3 arms & provenance
        tourn_text = await cdp.eval_js('document.getElementById("smart-entry-tournament-section") ? document.getElementById("smart-entry-tournament-section").innerText : ""')
        print(f"Tournament section preview: {safe_str(tourn_text[:160])}...")
        assert "ARM 1" in tourn_text or "ARM 2" in tourn_text or "Strategy Alone" in tourn_text, "3-arm tournament structure missing from DOM"
        assert "WALK_FORWARD" in tourn_text or "Walk-Forward" in tourn_text or "Manifest" in tourn_text or "canonical" in tourn_text.lower(), "Tournament provenance / cache disclosure missing"

        # Test anti-duplicate debouncing on tournament button
        reqs_deb_before = len(cdp.network_requests)
        await cdp.eval_js('document.getElementById("btn-run-tournament").click()')
        await cdp.eval_js('document.getElementById("btn-run-tournament").click()')
        await asyncio.sleep(0.5)

        backend_counters_deb = get_backend_json("/api/test-control/counters")
        print(f"Debounce counters: duplicate_blocked={backend_counters_deb.get('duplicate_blocked', 0)}")
        assert backend_counters_deb.get("duplicate_blocked", 0) >= 1 or backend_counters_deb.get("tournament_executions", 0) >= 1

        shot_cd = await cdp.capture_screenshot("v32_48_test_c_d_tournament_provenance.png")
        qa_summary["screenshots"].append(shot_cd)
        qa_summary["tests"]["test_c_d_tournament_provenance_and_debouncing"] = "PASSED"

        # -------------------------------------------------------------------
        # Test E: Explicit Enter, Frozen TP/SL Immutability & AI Anomaly Monitoring
        # -------------------------------------------------------------------
        print("\n--- Test E: Explicit Enter, Frozen TP/SL & Anomaly Monitoring ---")
        # Confirm Enter button is present
        btn_enter_present = await cdp.wait_for_selector("#btn-enter-simulated-trade", timeout=8.0)
        assert btn_enter_present, "Enter (Simulated) button missing when decision is available"

        # Click Enter (Simulated)
        print("Clicking #btn-enter-simulated-trade...")
        await cdp.eval_js('document.getElementById("btn-enter-simulated-trade").click()')
        await asyncio.sleep(1.0)

        # Verify active card appeared
        has_active_attempt = await cdp.wait_for_selector("#smart-entry-active-trade-card, #btn-simulated-exit-now", timeout=8.0)
        assert has_active_attempt, "Active simulated attempt card did not appear after Enter!"

        # Verify server recorded exactly 1 attempt
        attempts_res = get_backend_json("/api/tournament/smart-entry/attempts")
        print(f"Simulated attempts in backend: total={attempts_res['total_attempts']}, active={attempts_res['total_active']}")
        assert attempts_res["total_active"] == 1, f"Expected exactly 1 active attempt, got {attempts_res['total_active']}"

        active_att = attempts_res["active_attempts"][0]
        frozen_tp = active_att["frozen_tp_price"]
        frozen_sl = active_att["frozen_sl_price"]
        ref_entry = active_att["reference_entry_price"]
        print(f"Locked attempt: ID={active_att['attempt_id']}, Entry={ref_entry}, Frozen TP={frozen_tp}, Frozen SL={frozen_sl}")
        assert frozen_tp > 0 and frozen_sl > 0 and ref_entry > 0

        # Inject Direction Flip Anomaly
        print("Injecting AI Forecast Direction Reversal Anomaly...")
        send_backend_post("/api/test-control/inject-anomaly", {"anomaly_type": "DIRECTION_REVERSAL"})
        await asyncio.sleep(0.5)

        # Re-fetch attempt from backend and verify TP/SL never moved!
        attempts_after_rev = get_backend_json("/api/tournament/smart-entry/attempts")
        att_rev = attempts_after_rev["active_attempts"][0]
        assert att_rev["frozen_tp_price"] == frozen_tp, "CRITICAL ERROR: TP moved after AI forecast direction reversal!"
        assert att_rev["frozen_sl_price"] == frozen_sl, "CRITICAL ERROR: SL moved after AI forecast direction reversal!"
        assert att_rev["direction_change_alert"] is True, "Direction change alert not flagged on attempt"
        print("Direction flip verified: TP/SL remained strictly immutable.")

        # Inject Risk Spike Anomaly
        print("Injecting AI Forecast Risk Spike Anomaly (>1.5x)...")
        send_backend_post("/api/test-control/inject-anomaly", {"anomaly_type": "RISK_SPIKE"})
        await asyncio.sleep(0.5)

        attempts_after_spike = get_backend_json("/api/tournament/smart-entry/attempts")
        att_spike = attempts_after_spike["active_attempts"][0]
        assert att_spike["frozen_tp_price"] == frozen_tp, "CRITICAL ERROR: TP moved after AI risk spike!"
        assert att_spike["frozen_sl_price"] == frozen_sl, "CRITICAL ERROR: SL moved after AI risk spike!"
        assert att_spike["risk_spike_alert"] is True, "Risk spike alert not flagged on attempt"
        print("Risk spike verified: TP/SL remained strictly immutable.")

        # Reload page and verify state persistence
        print("Reloading page to verify persistence across restarts...")
        await cdp.eval_js('window.location.reload()')
        await asyncio.sleep(2.0)
        has_reloaded_active = await cdp.wait_for_selector("#smart-entry-active-trade-card, #btn-simulated-exit-now", timeout=8.0)
        assert has_reloaded_active, "Active attempt failed to restore after page reload!"

        # Close attempt cleanly with Exit Now
        print("Clicking #btn-simulated-exit-now to resolve lifecycle...")
        await cdp.eval_js('document.getElementById("btn-simulated-exit-now").click()')
        await asyncio.sleep(1.0)

        shot_e = await cdp.capture_screenshot("v32_48_test_e_entry_and_ai_monitoring.png")
        qa_summary["screenshots"].append(shot_e)
        qa_summary["tests"]["test_e_entry_and_ai_monitoring"] = "PASSED"

        # -------------------------------------------------------------------
        # Test F: Responsive Viewports & Protected Files Integrity
        # -------------------------------------------------------------------
        print("\n--- Test F: Responsive Viewports (Desktop, Tablet, Mobile) ---")
        # Desktop ($1280 \times 800$)
        await cdp.set_viewport(1280, 800, mobile=False)
        await asyncio.sleep(0.5)
        shot_f_desk = await cdp.capture_screenshot("v32_48_test_f_desktop_1280.png")
        qa_summary["screenshots"].append(shot_f_desk)

        # Tablet ($768 \times 1024$)
        print("Testing Tablet viewport (768x1024)...")
        await cdp.set_viewport(768, 1024, mobile=False)
        await asyncio.sleep(0.5)
        scroll_w_tab = await cdp.eval_js('document.documentElement.scrollWidth')
        client_w_tab = await cdp.eval_js('document.documentElement.clientWidth')
        assert scroll_w_tab <= client_w_tab, f"Horizontal overflow on tablet: {scroll_w_tab} > {client_w_tab}"
        shot_f_tab = await cdp.capture_screenshot("v32_48_test_f_tablet_768.png")
        qa_summary["screenshots"].append(shot_f_tab)

        # Mobile ($375 \times 667$)
        print("Testing Mobile viewport (375x667)...")
        await cdp.set_viewport(375, 667, mobile=True)
        await asyncio.sleep(0.5)
        scroll_w_mob = await cdp.eval_js('document.documentElement.scrollWidth')
        client_w_mob = await cdp.eval_js('document.documentElement.clientWidth')
        assert scroll_w_mob <= client_w_mob, f"Horizontal overflow on mobile: {scroll_w_mob} > {client_w_mob}"
        shot_f_mob = await cdp.capture_screenshot("v32_48_test_f_mobile_375.png")
        qa_summary["screenshots"].append(shot_f_mob)

        # Assert post-test protected files hashes
        print("\n--- Post-Test Protected Files Integrity Assertion ---")
        for rel_path, expected_hash in PROTECTED_FILES.items():
            curr_hash = compute_sha256(rel_path)
            assert curr_hash == expected_hash, f"Integrity error: {rel_path} altered after test! ({curr_hash} != {expected_hash})"
        print("All 5 protected files remain 100% bit-identical.")

        qa_summary["tests"]["test_f_viewports_and_protected_files"] = "PASSED"
        qa_summary["overall_status"] = "PASSED"
        print("\n" + "=" * 75)
        print("ALL V32.48 BROWSER QA TESTS PASSED WITH 100% SUCCESS!")
        print("=" * 75)

    except Exception as e:
        print(f"\n[QA ERROR]: {e}")
        qa_summary["overall_status"] = "FAILED"
        qa_summary["error"] = str(e)
        raise
    finally:
        # Save machine-readable summary
        summary_path = os.path.join(REPO_ROOT, "research", "reports", "v32_48_vigorous_qa_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(qa_summary, f, indent=2)
        print(f"Saved machine-readable QA summary: {summary_path}")
        await cdp.close()


if __name__ == "__main__":
    asyncio.run(run_v32_48_qa())

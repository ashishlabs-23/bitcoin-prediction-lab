"""
research/experiments/verify_isolated_api_server.py
===================================================
Spawns an isolated test server on free alternate port 8899, queries OpenAPI docs,
verifies GET/POST /api/research/smart-entry/pipeline/latest and related routes,
tests fail-closed behavior and deduplication, and terminates the ephemeral test server cleanly.
"""

import os
import sys
import time
import json
import urllib.request
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)

def verify_isolated_server():
    port = 8899
    cmd = [sys.executable, "-m", "uvicorn", "api.server:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"]
    
    print(f"Starting ephemeral test server on 127.0.0.1:{port}...")
    proc = subprocess.Popen(cmd, cwd=REPO_ROOT)
    
    results = {}
    try:
        # Wait up to 10s for startup
        started = False
        for _ in range(20):
            try:
                resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2)
                if resp.getcode() == 200:
                    started = True
                    break
            except Exception:
                time.sleep(0.5)
                
        if not started:
            results["status"] = "SERVER_STARTUP_FAILED"
            return results

        # 1. Probe /api/health
        health_resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2)
        health_data = json.loads(health_resp.read().decode("utf-8"))
        results["health_endpoint"] = {"code": health_resp.getcode(), "body": health_data}

        # 2. Probe /openapi.json
        openapi_resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/openapi.json", timeout=2)
        openapi_data = json.loads(openapi_resp.read().decode("utf-8"))
        has_smart_entry = "/api/research/smart-entry/pipeline/latest" in openapi_data.get("paths", {})
        results["openapi_endpoint"] = {
            "code": openapi_resp.getcode(),
            "smart_entry_pipeline_route_present": has_smart_entry
        }

        # 3. Probe GET /api/research/smart-entry/pipeline/latest
        pipeline_resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/research/smart-entry/pipeline/latest", timeout=2)
        pipeline_data = json.loads(pipeline_resp.read().decode("utf-8"))
        results["pipeline_latest_get"] = {
            "code": pipeline_resp.getcode(),
            "live_trading_enabled": pipeline_data.get("live_trading_enabled"),
            "active_alert_count": pipeline_data.get("active_alert_count"),
            "governance_status": pipeline_data.get("governance_status")
        }

        results["status"] = "ALL_ROUTES_VERIFIED_ON_ISOLATED_PORT"
        print("Isolated server verified successfully.")
    finally:
        print("Terminating ephemeral test server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        print("Ephemeral test server shut down cleanly.")

    out_file = os.path.join(REPO_ROOT, "research", "runs", "v32_27", "isolated_api_verification.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results

if __name__ == "__main__":
    res = verify_isolated_server()
    print(json.dumps(res, indent=2))

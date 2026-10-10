"""Read-only localhost application for UI inspection without legacy startup."""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "web"
RESEARCH_ROOT = PROJECT_ROOT / "research" / "entry_tp_sl"
AUTHORIZATION_PATH = RESEARCH_ROOT / "run_authorization.json"
CONTRACT_MANIFEST_PATH = RESEARCH_ROOT / "contract_freeze_manifest.json"
IMPLEMENTATION_MANIFEST_PATH = RESEARCH_ROOT / "6B_implementation_manifest.json"
HISTORICAL_REPORT_PATH = RESEARCH_ROOT / "INDEPENDENT_REPAIR_REPORT.md"

app = FastAPI(
    title="BTCognitive Local Safe UI",
    description="Read-only local UI and research-status diagnostics.",
    version="1.0.0",
)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path.name}")
    return value


def _research_status() -> dict[str, Any]:
    try:
        authorization = _read_json(AUTHORIZATION_PATH)
    except FileNotFoundError:
        return {
            "status": "PROVENANCE_FAILURE",
            "authorization": {
                "status": "PROVENANCE_FAILURE",
                "authorized": False,
                "reason": "Research authorization file is missing.",
            },
            "historical_outputs": "HISTORICAL_UNVERIFIED",
            "manifest_integrity": {"status": "PROVENANCE_FAILURE"},
        }
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return {
            "status": "PROVENANCE_FAILURE",
            "authorization": {
                "status": "PROVENANCE_FAILURE",
                "authorized": False,
                "reason": f"Research authorization could not be read: {type(error).__name__}.",
            },
            "historical_outputs": "HISTORICAL_UNVERIFIED",
            "manifest_integrity": {"status": "PROVENANCE_FAILURE"},
        }

    gate_status = authorization.get("status")
    authorized = authorization.get("authorized") is True
    status = (
        "BLOCKED_AUDIT_FAILURE"
        if gate_status == "BLOCKED_AUDIT_FAILURE" and not authorized
        else "PROVENANCE_FAILURE"
    )
    manifest_integrity: dict[str, Any] = {"status": "PROVENANCE_FAILURE"}
    try:
        manifest = _read_json(CONTRACT_MANIFEST_PATH)
        implementation = _read_json(IMPLEMENTATION_MANIFEST_PATH)
        actual_sha256 = hashlib.sha256(CONTRACT_MANIFEST_PATH.read_bytes()).hexdigest()
        embedded_sha256 = manifest.get("manifest_sha256")
        registered_sha256 = implementation.get("contract_manifest_sha256")
        hashes_agree = (
            isinstance(embedded_sha256, str)
            and embedded_sha256 == registered_sha256 == actual_sha256
        )
        manifest_integrity = {
            "status": "VERIFIED" if hashes_agree else "PROVENANCE_FAILURE",
            "actual_file_sha256": actual_sha256,
            "embedded_manifest_sha256": embedded_sha256,
            "registered_sha256": registered_sha256,
            "git_commit_recorded_in_manifest": manifest.get("git_commit"),
        }
    except (OSError, json.JSONDecodeError, ValueError):
        manifest_integrity = {"status": "PROVENANCE_FAILURE"}

    historical_outputs = "HISTORICAL_UNVERIFIED"
    try:
        repair_report = HISTORICAL_REPORT_PATH.read_text(encoding="utf-8")
        if "existing performance metrics remain historical, unverified artifacts" not in repair_report:
            historical_outputs = "PROVENANCE_FAILURE"
    except OSError:
        historical_outputs = "PROVENANCE_FAILURE"

    return {
        "status": status,
        "authorization": {
            "status": gate_status if isinstance(gate_status, str) else "PROVENANCE_FAILURE",
            "authorized": authorized,
            "blocked_findings": authorization.get("blocked_findings", []),
            "protocol_version": authorization.get("protocol_version"),
            "protocol_amendment_id": authorization.get("protocol_amendment_id"),
            "resolver_version": authorization.get("resolver_version"),
            "reason": authorization.get("reason"),
        },
        "historical_outputs": historical_outputs,
        "manifest_integrity": manifest_integrity,
        "current_inference": "DATA_UNAVAILABLE",
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "operational",
        "application": "BTCognitive Local Safe UI",
        "model_inference": "DATA_UNAVAILABLE",
        "market_data": "DATA_UNAVAILABLE",
        "research_validity": "BLOCKED_AUDIT_FAILURE",
        "order_execution": "DISABLED",
    }


@app.get("/ping")
def ping() -> dict[str, Any]:
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/local/status")
def local_status() -> dict[str, Any]:
    research = _research_status()
    return {
        "application": "OPERATIONAL",
        "market_data": "DATA_UNAVAILABLE",
        "model_inference": "DATA_UNAVAILABLE",
        "research": research,
        "order_execution": "DISABLED",
    }


@app.get("/api/market/status")
def market_status() -> dict[str, str]:
    return {
        "status": "DATA_UNAVAILABLE",
        "source": "none",
        "message": "No verified read-only market-data source is enabled in local-safe mode.",
    }


@app.get("/api/research/status")
def research_status() -> dict[str, Any]:
    return _research_status()


@app.get("/api/research/entry-tp-sl")
def research_entry_tp_sl() -> dict[str, Any]:
    research = _research_status()
    response_status = (
        "BLOCKED_AUDIT_FAILURE"
        if research["status"] == "BLOCKED_AUDIT_FAILURE"
        else research["status"]
    )
    return {
        "status": response_status,
        "research_status": response_status,
        "authorization": research["authorization"],
        "historical_outputs": research["historical_outputs"],
        "manifest_integrity": research["manifest_integrity"],
        "market_data": "DATA_UNAVAILABLE",
        "model_inference": "DATA_UNAVAILABLE",
        "hypothetical_signal": None,
        "metrics": None,
        "execution_mode": "PAPER_RESEARCH_ONLY",
        "live_capital_authorized": False,
    }


@app.get("/prediction/latest")
def prediction_latest() -> dict[str, str]:
    return {
        "status": "DATA_UNAVAILABLE",
        "model_inference": "DATA_UNAVAILABLE",
        "message": "No model inference is performed in local-safe mode.",
    }


@app.get("/")
def index() -> HTMLResponse:
    index_path = WEB_ROOT / "index.html"
    try:
        markup = index_path.read_text(encoding="utf-8")
    except OSError:
        return HTMLResponse(
            content="BTCognitive frontend assets are unavailable.",
            status_code=503,
        )

    markup = re.sub(
        r'<script\b(?=[^>]*\bsrc=["\']https://)[^>]*>\s*</script>',
        "",
        markup,
        flags=re.IGNORECASE,
    )
    app_script = '<script src="/app.js?v=10.4"></script>'
    safe_mode_script = (
        '<script>window.BTCOGNITIVE_LOCAL_SAFE_MODE = true;</script>'
        f"{app_script}"
    )
    markup = markup.replace(app_script, safe_mode_script)
    return HTMLResponse(markup)


app.mount("/", StaticFiles(directory=str(WEB_ROOT)), name="web")

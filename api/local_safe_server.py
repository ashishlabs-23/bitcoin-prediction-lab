"""Read-only localhost application for UI inspection without legacy startup."""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
import httpx

from api.bitstamp_readonly import fetch_bitstamp_btcusd_ohlcv
from api.scenario_calculator import calculate_scenario, get_scenario_options


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
            "check": "raw file SHA-256 compared with embedded and registered SHA-256",
            "scope": "manifest hash fields only; listed artifacts and dataset hash not recomputed",
            "discrepancy_does_not_establish_tampering": not hashes_agree,
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
        "current_inference": "MODEL_UNAVAILABLE",
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "operational",
        "application": "BTCognitive Local Safe UI",
        "model_inference": "MODEL_UNAVAILABLE",
        "market_data": "ON_DEMAND",
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
        "market_data": "ON_DEMAND",
        "model_inference": "MODEL_UNAVAILABLE",
        "research": research,
        "order_execution": "DISABLED",
    }


@app.get("/api/market/status")
async def market_status() -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        result = await fetch_bitstamp_btcusd_ohlcv(client)
    newest_bar = result.bars[-1] if result.bars else None
    return {
        "status": result.status.value,
        "venue": result.venue,
        "symbol": result.symbol,
        "source": result.source,
        "price": newest_bar.close if newest_bar is not None and result.status.value == "OK" else None,
        "source_timestamp": result.source_timestamp,
        "source_timestamp_utc": (
            datetime.fromtimestamp(result.source_timestamp, timezone.utc).isoformat()
            if result.source_timestamp is not None
            else None
        ),
        "retrieved_at": result.retrieved_at,
        "retrieved_at_utc": datetime.fromtimestamp(result.retrieved_at, timezone.utc).isoformat(),
        "freshness_limit_seconds": result.freshness_limit_seconds,
        "message": result.message,
    }


@app.get("/api/scenario/options")
def scenario_options() -> dict[str, Any]:
    return {
        "status": "AVAILABLE",
        "barrier_pairs": get_scenario_options(),
        "volatility_input": "ATR in USD, explicitly supplied by the user",
    }


@app.post("/api/scenario/calculate")
def scenario_calculate(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return calculate_scenario(payload)


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
        "model_inference": "MODEL_UNAVAILABLE",
        "current_inference": "MODEL_UNAVAILABLE",
        "hypothetical_signal": None,
        "metrics": None,
        "execution_mode": "PAPER_RESEARCH_ONLY",
        "live_capital_authorized": False,
    }


@app.get("/prediction/latest")
def prediction_latest() -> dict[str, str]:
    return {
        "status": "MODEL_UNAVAILABLE",
        "model_inference": "MODEL_UNAVAILABLE",
        "message": "No provenance-verified model artifact is available; no inference was performed.",
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
        r'<script\b(?=[^>]*\bsrc=["\']https://)[^>]*>.*?</script\s*>',
        "",
        markup,
        flags=re.IGNORECASE | re.DOTALL,
    )
    markup = re.sub(
        r'<link\b(?=[^>]*\bhref=["\']https://)[^>]*>',
        "",
        markup,
        flags=re.IGNORECASE,
    )
    app_script_pattern = re.compile(
        r'<script\b(?=[^>]*\bsrc=["\']/app\.js(?:\?[^"\']*)?["\'])[^>]*>\s*</script>',
        re.IGNORECASE,
    )
    safe_mode_script = (
        '<script>window.BTCOGNITIVE_LOCAL_SAFE_MODE = true;</script>'
        '<script src="/app.js?v=10.5"></script>'
    )
    markup, replacements = app_script_pattern.subn(safe_mode_script, markup, count=1)
    markup = re.sub(
        r'(<link\b(?=[^>]*\brel=["\']stylesheet["\'])[^>]*\bhref=["\'])/styles\.css(?:\?[^"\']*)?(["\'])',
        r"\1/styles.css?local-safe=1\2",
        markup,
        flags=re.IGNORECASE,
    )
    if replacements != 1 or "window.BTCOGNITIVE_LOCAL_SAFE_MODE = true" not in markup:
        return HTMLResponse(
            content="BTCognitive local-safe frontend initialization failed.",
            status_code=503,
        )
    response = HTMLResponse(markup)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' data:; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; font-src 'self' data:; "
        "img-src 'self' data:; connect-src 'self'"
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/styles.css")
def styles() -> Response:
    stylesheet_path = WEB_ROOT / "styles.css"
    try:
        stylesheet = stylesheet_path.read_text(encoding="utf-8")
    except OSError:
        return Response(
            content="BTCognitive stylesheet is unavailable.",
            status_code=503,
            media_type="text/plain",
        )
    stylesheet = re.sub(
        r"^\s*@import\s+url\(\s*['\"]?https://[^)]*\)\s*;?\s*$",
        "",
        stylesheet,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    return Response(
        content=stylesheet,
        media_type="text/css",
        headers={"Cache-Control": "no-store"},
    )


app.mount("/", StaticFiles(directory=str(WEB_ROOT)), name="web")

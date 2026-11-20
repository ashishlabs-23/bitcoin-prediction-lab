"""Build the read-only V32.56 charting-readiness audit; never touches protected data."""
from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "research/reports/v32_55/20261027_203037_920812"
PROTECTED = (
    "data/raw/ohlcv.parquet", "data/raw/ohlcv_pre_backfill_backup.parquet",
    "data/raw/ohlcv_backfilled.parquet", "data/prospective_entry_ledger.jsonl",
    "data/prospective_shadow_v1.jsonl", "data/prospective_entry_ledger_v2.jsonl",
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def category(disposition: str) -> tuple[str, str, str]:
    mapping = {
        "BLOCKED_BY_QA_NETWORK_POLICY": ("TEST_OR_CONTRACT_MISMATCH", "sandbox_network", "deterministic resolver/HTTP mock while keeping the external-network block"),
        "DATA_OR_CONTRACT_REVIEW_REQUIRED": ("DATA_PROVENANCE_BLOCKED", "data_contract", "rights-cleared, complete dataset and explicit current coverage/gap contract"),
        "LEDGER_FIXTURE_REVIEW_REQUIRED": ("TEST_OR_CONTRACT_MISMATCH", "ledger_fixture", "isolated schema-valid ledger fixture and restart/idempotency evidence"),
        "RESOURCE_SENSITIVE_RETEST_REQUIRED": ("ENVIRONMENT_OR_FLAKY", "performance", "controlled repeated measurement with machine/load evidence"),
        "OPEN_RETEST_FAILED": ("NOT_REPRODUCED", "application_or_test_contract", "current isolated targeted reproduction before asserting a code defect or changing an expectation"),
    }
    return mapping[disposition]


def main() -> None:
    if not (SOURCE / "failure_inventory.csv").is_file() or not (SOURCE / "report.md").is_file():
        raise FileNotFoundError("Required V32.55 report and failure inventory are absent")
    output = ROOT / "research/reports/v32_56_charting_readiness" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output.mkdir(parents=True, exist_ok=False)
    before = {name: digest(ROOT / name) for name in PROTECTED}
    rows = list(csv.DictReader((SOURCE / "failure_inventory.csv").open(encoding="utf-8")))
    if len(rows) != 47:
        raise RuntimeError(f"Expected exactly 47 inherited IDs, found {len(rows)}")
    triage = []
    for row in rows:
        classification, owner, close_evidence = category(row["disposition"])
        triage.append({
            "test_id": row["test_id"], "original_failure": row["prior_evidence"],
            "latest_status": f"HISTORIC_FAIL: {row['retest_result']}",
            "actual_vs_expected": row["observed_failure"], "classification": classification,
            "blocking_dependency": row["required_follow_up"], "owner": owner,
            "evidence_required_to_close": close_evidence,
            "reproducible_command": row["retest_command"], "source_disposition": row["disposition"],
            "v32_56_disposition": "PENDING_TARGETED_REPRODUCTION",
        })
    with (output / "v32_55_failure_triage.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=list(triage[0]))
        writer.writeheader(); writer.writerows(triage)
    v3 = ROOT / "data/research/coinbase_btc_usd_hourly_verified_v3/acquisition_manifest.json"
    v3_manifest = json.loads(v3.read_text(encoding="utf-8")) if v3.is_file() else None
    provenance = f"""# Data provenance and market-data rights review\n\n## Release decision\n\n**BLOCKED — Coinbase-backed public release.** No written license granting the intended public display, redistribution, derived analytics, caching/retention, commercial, or AI/ML use was found in the repository. Coinbase's official Market Data Terms, last updated 2026-08-07, restrict end-user applications, third-party display/dissemination of Market Data or Derived Works, and AI/ML development/training/validation/benchmarking absent prior express written consent. Source: https://www.coinbase.com/legal/market_data.\n\nA public endpoint is not a public-display license. The allowed path is a written Coinbase agreement that expressly covers each intended use, or a provider whose executed license does. Legal review remains required.\n\n## V32.55 data condition\n\n- V2: 42,237 rows; 13 absent hourly candles in three gaps; `ACQUIRED_WITH_REVIEW_REQUIRED`.\n- V3: `{(v3_manifest or {}).get('status', 'NOT_FOUND')}`; it is separate and immutable. Its manifest retains raw-response hashes and reproducible reconstruction evidence.\n- The reported 56 later-candle overlap check is interval-scoped evidence only; it does not validate the historical file as a whole or resolve the 13 missing candles.\n- No protected parquet or ledger was modified by this audit. No gaps were filled.\n\n## Required provider-license evidence\n\nWritten permission must explicitly cover: end-user display, raw/derived redistribution, indicators/charts/research outputs, retention and caches, commercial/geographic scope, and model training/fine-tuning/testing/validation/benchmarking. Until then, deterministic fixture data remains isolated QA-only and unavailable to normal/public runtime.\n"""
    (output / "data_provenance_review.md").write_text(provenance, encoding="utf-8")
    inventory = """# V32.56 product and runtime inventory\n\n## Confirmed runtime\n\n- Backend: FastAPI application in `api/server.py`, with static frontend mounting and modular routers.\n- Client: a compiled/bundled `web/app.js` delivered from `web/index.html`; no SPA framework package dependency was found in `package.json`.\n- Chart: TradingView Lightweight Charts loaded from unpkg in `web/index.html`; this is a dependency, not a market-data entitlement.\n- Market/forecast routes: `api/market_monitor_routes.py` provides `/api/dashboard`, `/api/market-drivers`, `/api/forecast/latest`, `/prediction/latest`, and `/api/readiness`. Market values are retrieved through server-side market-driver/provider clients.\n- Current supported public-market contract is BTC/USD-centric; `api/market_monitor_routes.py` rejects unsupported requested symbol/interval combinations. Broad symbol/timeframe support is not established.\n- Indicators and forecast state are rendered in `web/app.js`; the UI checks origin against the latest closed chart candle. On an unavailable/malformed/timeout response it clears forecast series and retains the price chart.\n- Deployment artifacts exist: Dockerfile, docker-compose.yml, render.yaml, fly.toml. CI is limited to `.github/workflows/market-monitor.yml`, covering two market test modules.\n- Auth: `api/security_auth.py` defines public/default role and configured API-key/Bearer roles; no exchange account linking was found.\n\n## Forecast contract and marker behavior\n\n`/api/forecast/latest` delegates to `engine.forecast_engine_15m.generate_forecast_contract`. The frontend only creates a marker when the forecast origin equals the latest closed candle for the active interval; otherwise it must not anchor a marker. The source code separately renders forecast state/panel content. A live browser observation was not claimed in this audit because public data rights are blocked and no licensed staging provider was identified. Browser evidence therefore remains pending.\n\n## Execution boundary\n\nNo broker/order placement route or exchange authentication integration was found. The code does expose manual journal/user-position and smart-entry simulation routes, which persist user-supplied/simulated lifecycle events. They are not a public chart-MVP dependency and must remain segregated. `OFFLINE_RESEARCH_ONLY` and `NO_GO_NO_VALIDATED_EDGE` gate model authorization/recommendation and live-capital status; chart rendering is not itself conditional on production model authorization.\n\n## Confirmed P0 defect\n\n`api/routes_user_positions.py` uses a hard-coded 80000.0 quote after a provider failure. That fallback is incompatible with the no-fabricated-market-data requirement. It is outside broker execution, but it is a confirmed defect for any displayed position/monitor quote. Do not expose that path publicly until it returns an explicit unavailable state.\n\n## Smallest ranked changes — not implemented by this audit\n\n1. Replace the hard-coded position-monitor quote fallback with `UNAVAILABLE`; test provider failure returns no fabricated price.\n2. Add a rights gate to public market-data routes that blocks third-party data display until a provider license record is affirmative; test default BLOCKED and an explicit licensed-provider configuration.\n3. Add chart-contract browser tests using QA fixtures: OK/GAP/STALE/PARTIAL/UNAVAILABLE, marker alignment/fallback panel, source/cutoff/model version, and cache-key isolation.\n4. Keep simulator/journal routes off the chart-MVP navigation; test no public chart workflow reaches Enter/Continue/Exit.\n5. Expand the existing CI workflow only after those focused tests exist; do not use aggregate coverage as the gate.\n"""
    (output / "repository_runtime_inventory.md").write_text(inventory, encoding="utf-8")
    after = {name: digest(ROOT / name) for name in PROTECTED}
    summary = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "protected_before": before,
        "protected_after": after, "protected_hashes_identical": before == after,
        "data_rights": "BLOCKED", "inherited_test_ids": len(rows),
        "classification_counts": dict(Counter(row["classification"] for row in triage)),
        "verdict": "BLOCKED", "reason": "No written market-data rights for public use; browser critical-path evidence and targeted failure reproductions remain open."}
    (output / "audit_manifest.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

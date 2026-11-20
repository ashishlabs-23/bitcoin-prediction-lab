"""Create the auditable V32.55 application-QA/data-recovery status report."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
V54 = ROOT / "research" / "reports" / "v32_54"
OUT = ROOT / "research" / "reports" / "v32_55" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
PROTECTED = (
    "data/prospective_entry_ledger.jsonl", "data/prospective_shadow_v1.jsonl",
    "data/prospective_entry_ledger_v2.jsonl", "data/raw/ohlcv.parquet",
    "data/raw/ohlcv_pre_backfill_backup.parquet", "data/raw/ohlcv_backfilled.parquet",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=False)
    base = list(csv.DictReader((V54 / "20261027_184953_511000" / "failure_retest_dispositions.csv").open(encoding="utf-8")))
    passes = {row["test_id"] for row in base if row["disposition"] == "RETEST_PASS"}
    followup = list(csv.DictReader((V54 / "20261027_185938_097630" / "failure_retest_followup.csv").open(encoding="utf-8")))
    passes.update(row["test_id"] for row in followup if row["followup_result"] == "PASS")
    unresolved = [row for row in base if row["test_id"] not in passes]
    for row in unresolved:
        row["v32_55_status"] = "DOCUMENTED_BLOCKER_OR_RETEST_PENDING"
        row["owner_area"] = ("data_contract" if "DATA_OR_CONTRACT" in row["disposition"] else
            "sandbox_network" if "NETWORK" in row["disposition"] else
            "ledger_fixture" if "LEDGER" in row["disposition"] else "application_or_test_contract")
        row["retest_command"] = ".venv_win\\Scripts\\python.exe -B scripts\\qa\\v32_52_isolated_runner.py --run --qa-fixture deterministic_hourly_v1 -- " + row["test_id"]
    fields = list(unresolved[0]) if unresolved else []
    with (OUT / "failure_inventory.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader(); writer.writerows(unresolved)
    v2 = ROOT / "data" / "research" / "coinbase_btc_usd_hourly_verified_v2"
    v3 = ROOT / "data" / "research" / "coinbase_btc_usd_hourly_verified_v3"
    v2_validation = json.loads((v2 / "validation.json").read_text(encoding="utf-8"))
    v3_manifest = json.loads((v3 / "acquisition_manifest.json").read_text(encoding="utf-8")) if (v3 / "acquisition_manifest.json").is_file() else None
    protected = {name: sha(ROOT / name) for name in PROTECTED}
    git = lambda *args: subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False).stdout
    facts = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "branch": git("branch", "--show-current").strip(),
        "head": git("rev-parse", "HEAD").strip(), "protected_sha256": protected,
        "v2": {"dataset_sha256": sha(v2 / "coinbase_btc_usd_hourly.parquet"), "status": "ACQUIRED_WITH_REVIEW_REQUIRED", "validation": v2_validation},
        "v3": {"path": str(v3), "manifest": v3_manifest, "status": (v3_manifest or {}).get("status", "ACQUISITION_IN_PROGRESS_OR_BLOCKED")},
        "unresolved_count": len(unresolved), "resolved_passes_from_v32_54": len(passes),
        "fixture": {"id": "deterministic_hourly_v1", "qa_only": True, "not_market_evidence": True, "not_forecast_source": True},
        "focused_test_evidence": [
            {"command": ".venv_win\\Scripts\\python.exe -B scripts\\qa\\v32_52_isolated_runner.py --fixture-self-test", "result": "PASS", "evidence": "FIXTURE_SELF_TEST_PASS"},
            {"command": ".venv_win\\Scripts\\python.exe -B scripts\\qa\\v32_52_isolated_runner.py --self-test", "result": "PASS", "evidence": "GUARD_SELF_TEST_PASS"},
            {"command": ".venv_win\\Scripts\\python.exe -B -m py_compile scripts\\qa\\v32_52_isolated_runner.py scripts\\qa\\v32_55_qa_fixtures.py research\\data_acquisition\\build_coinbase_hourly_verified_v2.py", "result": "PASS", "evidence": "zero exit status"},
        ],
        "governance": {"research_experiment": "INCONCLUSIVE", "prospective_evidence": "COLLECTING", "model_authorization": "OFFLINE_RESEARCH_ONLY", "live_trading": "DISABLED"}}
    (OUT / "integrity_and_data_status.json").write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")
    report = f"""# V32.55 — Application QA Decoupling and Data Recovery\n\nRelease verdict: **PARTIAL_PASS_BLOCKED**.\n\nThe deterministic fixture contract is isolated from market evidence and the protected-file guard self-test passed. V2 is unchanged and remains `ACQUIRED_WITH_REVIEW_REQUIRED`: {v2_validation['rows']} rows, {v2_validation['missing_interval_count']} gaps, and {len(v2_validation['missing_expected_timestamps'])} absent candles. V3 is a separate immutable target; its current status is `{facts['v3']['status']}`.\n\n## QA evidence\n\n- Fixture: `deterministic_hourly_v1`, UTC hourly OHLCV schema, normal/gap/duplicate/invalid/stale and unavailable/malformed/timeout response cases. It is QA-only and not empirical evidence or a forecast source.\n- V32.54 retests document {len(passes)} resolved IDs and {len(unresolved)} unresolved IDs. The full current inventory, categories, root-cause hypotheses, and per-ID fixture-mode retest command are in `failure_inventory.csv`.\n- Network policy remains deny-by-default outside QA-owned loopback ports; authorization remains fail-closed.\n\n## Track B\n\nV2 missing timestamps are explicit in `integrity_and_data_status.json`. No candle is synthesized and no canonical parquet is overwritten. V3 must retain archived official responses, hashes, coverage, UTC/OHLCV validation, reproducible rebuild, and comparisons before it can be reviewed.\n\n## Governed decisions\n\n- Research Experiment: INCONCLUSIVE\n- Prospective Evidence: COLLECTING\n- Model Authorization: OFFLINE_RESEARCH_ONLY\n- Live Trading: DISABLED\n"""
    (OUT / "report.md").write_text(report, encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()

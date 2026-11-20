"""Write a post-remediation addendum without altering prior audit artifacts."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTECTED = ("data/raw/ohlcv.parquet", "data/raw/ohlcv_pre_backfill_backup.parquet", "data/raw/ohlcv_backfilled.parquet", "data/prospective_entry_ledger.jsonl", "data/prospective_shadow_v1.jsonl", "data/prospective_entry_ledger_v2.jsonl")

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> None:
    output = ROOT / "research/reports/v32_56_charting_readiness_remediation" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output.mkdir(parents=True, exist_ok=False)
    protected = {path: sha(ROOT / path) for path in PROTECTED}
    result = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "change": "Position-monitor quote-provider failure now returns explicit UNAVAILABLE with null quote fields; it no longer creates a synthetic 80000.0 price.", "targeted_test": "tests/test_v32_56_no_fabricated_position_quote.py", "targeted_test_result": "PASS (1 passed)", "existing_integration_subset": "STOPPED_AFTER_30_SECONDS_DURING_STARTUP; NOT_PASSED", "protected_sha256_after": protected, "data_rights": "BLOCKED", "release_verdict": "BLOCKED"}
    (output / "remediation_evidence.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "remediation_report.md").write_text("# V32.56 targeted P0 remediation\n\nThe position-monitor provider-failure fallback no longer fabricates a market quote. The targeted no-fabrication test passed. This does not change market-data rights, forecast authorization, research validation, or live-trading status. Public Coinbase-backed release remains BLOCKED.\n", encoding="utf-8")
    print(output)

if __name__ == "__main__":
    main()

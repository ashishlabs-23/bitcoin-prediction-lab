#!/usr/bin/env python3
"""
scripts/run_full_regression.py — Authoritative BTCognitive Test Suite Regression Runner
=====================================================================================
Discovers, categorizes, and executes test suites across BTCognitive with bit-level integrity,
exact test inventory enumeration, and structured audit reporting.

Categories:
  - platform:     Core API, Server, Data Verification, Runtime Gates, Failure Injection (53 files)
  - econometric:  HAR Volatility, QLIKE, Loss Functions, Diebold-Mariano, C2 Conformal (35 files)
  - strategy:     Regime Tournament, Smart Entry, HTF Analysis, Paper Simulator (35 files)
  - legacy:       Historical Milestone Tests (V1 to V32 snapshots, 249 files)
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"
ARTIFACTS_DIR = REPO_ROOT / "artifacts"


def extract_test_inventory() -> List[Dict[str, Any]]:
    """Inspects all test files using Python AST to extract exact functions and line counts."""
    inventory = []
    for test_file in sorted(TESTS_DIR.glob("test_*.py")):
        rel_path = str(test_file.relative_to(REPO_ROOT)).replace("\\", "/")
        try:
            tree = ast.parse(test_file.read_text(encoding="utf-8", errors="replace"), filename=str(test_file))
            test_funcs = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]
        except Exception as e:
            test_funcs = [f"PARSE_ERROR: {e}"]

        category = classify_test_file(test_file.name)
        inventory.append({
            "rel_path": rel_path,
            "filename": test_file.name,
            "category": category,
            "test_count": len(test_funcs),
            "test_names": "; ".join(test_funcs)
        })
    return inventory


def classify_test_file(filename: str) -> str:
    """Categorizes a test file into platform, econometric, strategy, or legacy."""
    fn = filename.lower()

    # Legacy (Milestones V1 through V32 snapshots, stage tests)
    # Checked FIRST so legacy milestone suites do not leak into active test runs
    if re.match(r"^test_v(?:[1-9]|[12]\d|3[0-2])_", fn) or fn.startswith("test_stage"):
        return "legacy"

    # Platform & Infrastructure
    if any(k in fn for k in [
        "api", "server", "routes", "bitstamp", "data_verification", "failure_injection",
        "authorization", "startup_gate", "readiness", "monitor", "notification",
        "frontend_contracts", "v33_7", "v33_8", "v35_tardis", "v35_model", "v35_"
    ]):
        return "platform"

    # Strategy & Tournament
    if any(k in fn for k in [
        "tournament", "smart_entry", "htf", "strategy", "paper_trading",
        "scenario_qa", "backtest", "simulated", "order_routing", "trade_journal"
    ]):
        return "strategy"

    # Econometrics & Volatility
    if any(k in fn for k in [
        "econometric", "volatility", "forecast", "qlike", "har_", "conformal",
        "uncertainty", "hawkes", "drift", "chronos", "directional", "loss", "diebold"
    ]):
        return "econometric"

    return "legacy"


def export_inventory_csv(inventory: List[Dict[str, Any]], output_path: Path) -> None:
    """Exports test inventory to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["rel_path", "filename", "category", "test_count", "test_names"])
        writer.writeheader()
        writer.writerows(inventory)
    print(f"[INVENTORY] Exported {len(inventory)} test files to {output_path}")


def run_test_suite(files: List[str], verbose: bool = False) -> Dict[str, Any]:
    """Runs pytest on specified files and returns structured execution metrics."""
    if not files:
        return {"passed": 0, "failed": 0, "skipped": 0, "duration_sec": 0.0, "exit_code": 0}

    cmd = [sys.executable, "-m", "pytest"] + files
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    start_t = time.time()
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    duration = time.time() - start_t

    stdout = proc.stdout
    stderr = proc.stderr
    output = stdout + "\n" + stderr

    # Parse pytest output summary line
    # e.g., "15 passed in 1.23s" or "4 failed, 132 passed in 35.60s"
    import re
    passed = 0
    failed = 0
    skipped = 0

    m_pass = re.search(r"(\d+)\s+passed", output)
    if m_pass:
        passed = int(m_pass.group(1))

    m_fail = re.search(r"(\d+)\s+failed", output)
    if m_fail:
        failed = int(m_fail.group(1))

    m_skip = re.search(r"(\d+)\s+skipped", output)
    if m_skip:
        skipped = int(m_skip.group(1))

    return {
        "files_run": len(files),
        "exit_code": proc.returncode,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "duration_sec": round(duration, 2),
        "raw_output": output if proc.returncode != 0 else stdout.strip()[-300:]
    }


def main():
    parser = argparse.ArgumentParser(description="BTCognitive Full Regression Test Runner")
    parser.add_argument(
        "--category",
        type=str,
        default="platform,econometric,strategy",
        help="Comma-separated test categories: all, platform, econometric, strategy, legacy"
    )
    parser.add_argument("--export-inventory", action="store_true", help="Export test inventory CSV to artifacts/test_inventory.csv")
    parser.add_argument("--verbose", action="store_true", help="Run pytest with -v")
    args = parser.parse_args()

    inventory = extract_test_inventory()
    total_files = len(inventory)
    total_funcs = sum(item["test_count"] for item in inventory)

    print("=" * 70)
    print("BTCognitive V35.3 Regression Test Runner")
    print(f"Total Discovered Test Files: {total_files}")
    print(f"Total Discovered Test Functions: {total_funcs}")
    print("=" * 70)

    # Breakdown by category
    categories_breakdown = {}
    for item in inventory:
        c = item["category"]
        categories_breakdown[c] = categories_breakdown.get(c, 0) + 1

    for c, count in sorted(categories_breakdown.items()):
        print(f"  Category '{c}': {count} files")

    # Export inventory CSV if requested or default
    inventory_path = ARTIFACTS_DIR / "test_inventory.csv"
    export_inventory_csv(inventory, inventory_path)

    # Determine which categories to run
    selected_cats = [c.strip().lower() for c in args.category.split(",")]
    if "all" in selected_cats:
        selected_cats = ["platform", "econometric", "strategy", "legacy"]

    print("-" * 70)
    print(f"Executing Regression for Categories: {selected_cats}")
    print("-" * 70)

    results_by_cat = {}
    overall_passed = 0
    overall_failed = 0
    overall_skipped = 0
    overall_duration = 0.0

    for cat in selected_cats:
        cat_files = [item["rel_path"] for item in inventory if item["category"] == cat]
        print(f"\n[RUNNING] Category '{cat}' ({len(cat_files)} files)...")
        res = run_test_suite(cat_files, verbose=args.verbose)
        results_by_cat[cat] = res

        overall_passed += res["passed"]
        overall_failed += res["failed"]
        overall_skipped += res["skipped"]
        overall_duration += res["duration_sec"]

        status = "PASSED" if res["exit_code"] == 0 else f"FAILED (exit {res['exit_code']})"
        print(f"  [{status}] Passed: {res['passed']}, Failed: {res['failed']}, Skipped: {res['skipped']} ({res['duration_sec']}s)")
        if res["exit_code"] != 0:
            print(f"  Diagnostics:\n{res['raw_output']}\n")

    summary = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_inventory_files": total_files,
        "total_inventory_functions": total_funcs,
        "executed_categories": selected_cats,
        "overall": {
            "passed": overall_passed,
            "failed": overall_failed,
            "skipped": overall_skipped,
            "duration_sec": round(overall_duration, 2),
            "status": "PASS" if overall_failed == 0 else "FAIL"
        },
        "by_category": results_by_cat
    }

    summary_path = ARTIFACTS_DIR / "v35_3_regression_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\n[REPORT] Saved full regression summary to {summary_path}")

    print("=" * 70)
    print(f"FINAL REGRESSION RESULT: {summary['overall']['status']}")
    print(f"Total Passed: {overall_passed} | Total Failed: {overall_failed} | Duration: {round(overall_duration, 2)}s")
    print("=" * 70)

    return 0 if overall_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

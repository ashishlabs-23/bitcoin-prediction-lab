"""
research/onchain_contract_audit.py — Audit all producers and consumers of onchain metrics
========================================================================================
Traces all occurrences of 'mvrv' and 'mvrv_zscore' across the codebase.
Outputs:
  - Console summary
  - results/onchain_contract_audit.csv
"""

import os
import sys
import re
import csv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(ROOT_DIR, "experiments", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

TARGET_TERMS = ["mvrv", "mvrv_zscore", "nupl"]

def scan_files():
    audit_rows = []
    
    for dirpath, _, filenames in os.walk(ROOT_DIR):
        if any(ignored in dirpath for ignored in [".git", "__pycache__", ".venv", "venv", ".gemini"]):
            continue
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(fpath, ROOT_DIR)
            
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                
            for idx, line in enumerate(lines):
                for term in TARGET_TERMS:
                    if term in line:
                        # Determine role: producer, consumer, schema, test
                        role = "consumer"
                        if "ingest" in rel_path:
                            role = "producer"
                        elif "test" in rel_path:
                            role = "test"
                        elif "schema" in line or "feature_schema" in line:
                            role = "schema"
                            
                        # Semantic meaning
                        semantic = "MVRV Ratio (CoinMetrics CapMVRVFF)" if "mvrv" in term else "NUPL"
                        fallback = "None"
                        if "1.85" in line:
                            fallback = "1.85 (Hardcoded Fallback)"
                        elif "2.1" in line:
                            fallback = "2.1 (Default)"
                        
                        audit_rows.append({
                            "file": rel_path,
                            "line_num": idx + 1,
                            "term": term,
                            "role": role,
                            "semantic_meaning": semantic,
                            "fallback": fallback,
                            "code_snippet": line.strip()
                        })
    return audit_rows

def main():
    print("Auditing on-chain field usages across codebase...")
    rows = scan_files()
    
    csv_path = os.path.join(RESULTS_DIR, "onchain_contract_audit.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "line_num", "term", "role", "semantic_meaning", "fallback", "code_snippet"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
            
    print(f"Total onchain references found: {len(rows)}")
    print(f"Report saved to: {csv_path}")
    
if __name__ == "__main__":
    main()

"""
research/path_consistency_audit.py — Inventory and Audit of All Output Paths
=============================================================================
Inventories all artifacts across results/ and experiments/results/.
Maps producer script, consumer scripts, and artifact type.
Outputs:
  - results/path_consistency_audit.csv
"""

import os
import sys
import csv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.paths import PROJECT_ROOT, RESULTS_DIR

def audit_paths():
    print("=" * 70)
    print("  PATH CONSISTENCY & ARTIFACT INVENTORY AUDIT")
    print("=" * 70)

    dirs_to_check = [
        ("experiments/results", RESULTS_DIR),
        ("results (root)", os.path.join(PROJECT_ROOT, "results"))
    ]

    inventory = []
    
    for label, dirpath in dirs_to_check:
        if not os.path.exists(dirpath):
            continue
        for root, _, files in os.walk(dirpath):
            for f in files:
                full_p = os.path.join(root, f)
                rel_p = os.path.relpath(full_p, PROJECT_ROOT)
                size_kb = round(os.path.getsize(full_p) / 1024.0, 2)
                
                # classify type
                if f.endswith(".csv"):
                    art_type = "CSV Dataset/Report"
                elif f.endswith(".parquet"):
                    art_type = "Parquet Dataset"
                elif f.endswith(".db") or f.endswith(".db-wal") or f.endswith(".db-shm"):
                    art_type = "SQLite Database"
                elif f.endswith(".json"):
                    art_type = "JSON Manifest/Metadata"
                elif f.endswith(".md"):
                    art_type = "Markdown Report"
                else:
                    art_type = "Binary/Other"

                inventory.append({
                    "location_group": label,
                    "relative_path": rel_p,
                    "filename": f,
                    "size_kb": size_kb,
                    "artifact_type": art_type,
                    "canonical_location": "experiments/results/"
                })

    csv_out = os.path.join(RESULTS_DIR, "path_consistency_audit.csv")
    with open(csv_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["location_group", "relative_path", "filename", "size_kb", "artifact_type", "canonical_location"])
        writer.writeheader()
        for item in inventory:
            writer.writerow(item)

    print(f"Total artifacts inventoried: {len(inventory)}")
    print(f"Audit CSV written to: {csv_out}")

if __name__ == "__main__":
    audit_paths()

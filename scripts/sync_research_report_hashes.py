#!/usr/bin/env python3
"""Resynchronise ``expected_sha256`` in ``api/routes_research.py`` with the reports on disk.

The allowlisted research reports are immutable evidence: their SHA256 values are pinned in
``REPORT_REGISTRY`` so the API can prove that what it serves is exactly what was reviewed.
Whenever a report is regenerated or an editorial correction is committed, the pin has to be
updated in the same commit -- otherwise ``/api/research/results`` starts reporting
``INTEGRITY_MISMATCH`` for a file that is actually fine (that is exactly what happened to six
reports between 2026-10 and 2026-11-28).

Usage:
    python3 scripts/sync_research_report_hashes.py          # report drift only
    python3 scripts/sync_research_report_hashes.py --write  # rewrite the pinned hashes

Run it from the repository root. It exits non-zero when drift remains (CI-friendly).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_FILE = REPO_ROOT / "api" / "routes_research.py"

# (report_id, relative_path) -> block of the registry entry
_ENTRY_RE = re.compile(r'^    "(?P<rid>[a-z0-9\-]+)": \{$', re.MULTILINE)
_PATH_RE = re.compile(r'^\s*"relative_path": "(?P<path>[^"]+)",$', re.MULTILINE)
_SHA_RE = re.compile(r'^(?P<indent>\s*)"expected_sha256": (?:None|"(?P<sha>[0-9a-f]{64})"),$', re.MULTILINE)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_entries(source: str) -> list[dict]:
    entries = []
    starts = [m.start() for m in _ENTRY_RE.finditer(source)]
    ends = starts[1:] + [len(source)]
    for start, end in zip(starts, ends):
        block = source[start:end]
        rid = _ENTRY_RE.match(block).group("rid")
        path_m = _PATH_RE.search(block)
        sha_m = _SHA_RE.search(block)
        if not path_m or not sha_m:
            continue
        entries.append({
            "rid": rid,
            "path": path_m.group("path"),
            "pinned": sha_m.group("sha"),
            "sha_start": start + sha_m.start("sha") if sha_m.group("sha") else None,
            "line_span": (start + sha_m.start(), start + sha_m.end()),
        })
    return entries


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true", help="rewrite pinned hashes in place")
    args = ap.parse_args(argv)

    source = REGISTRY_FILE.read_text(encoding="utf-8")
    entries = find_entries(source)

    drift, missing, unpinned = [], [], []
    for entry in entries:
        full = REPO_ROOT / entry["path"]
        if not full.is_file():
            missing.append(entry)
            continue
        actual = sha256_of(full)
        if entry["pinned"] is None:
            unpinned.append((entry, actual))
        elif actual != entry["pinned"]:
            drift.append((entry, actual))

    for entry in missing:
        print(f"MISSING  {entry['rid']}: {entry['path']}")
    for entry, actual in unpinned:
        print(f"UNPINNED {entry['rid']}: {entry['path']} -> {actual}")
    for entry, actual in drift:
        print(f"DRIFT    {entry['rid']}: {entry['path']}\n"
              f"         pinned {entry['pinned']}\n         actual {actual}")

    if not drift and not missing and not unpinned:
        print(f"OK: {len(entries)} allowlisted reports match their pinned SHA256.")
        return 0

    if not args.write:
        print("\nRe-run with --write to pin the current contents, then review the diff before committing.")
        return 1

    # Rewrite from the bottom up so earlier offsets stay valid.
    for entry, actual in sorted(drift + unpinned, key=lambda x: x[0]["line_span"][0], reverse=True):
        start, end = entry["line_span"]
        source = source[:start] + f'"expected_sha256": "{actual}",' + source[end:]
    REGISTRY_FILE.write_text(source, encoding="utf-8")
    print(f"\nRewrote {len(drift) + len(unpinned)} pinned hash(es) in {REGISTRY_FILE.relative_to(REPO_ROOT)}.")
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())

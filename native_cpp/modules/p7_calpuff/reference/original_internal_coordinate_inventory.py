#!/usr/bin/env python3
"""Expose bounded, exact vendor source anchors for CALPUFF grid coordinates.

This auditor inspects the immutable original calpuff.for bytes as Latin-1
because the original fixed-form source contains non-UTF8 comments. GitHub's
text file API cannot decode that blob. It only reports relevant source lines;
it does NOT infer relative-grid equations or certify C++ state parity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SOURCE_PATTERNS = {
    "point_internal": re.compile(r"\b(?:XPT1GRD|YPT1GRD)\b", re.I),
    # Original POINTS1 uses XPT1GRD/YPT1GRD in /PT1/. Bare XPT1/
    # YPT1, XPT1KM and YPT1KM are NOT vendor symbols. Do not require
    # invented names and then misclassify a valid vendor source as broken.
    "grid_conversion": re.compile(r"\b(?:GRIDIJ|GETCELL|XORIGKM|YORIGKM|XORIG|YORIG)\b", re.I),
    "puff_position": re.compile(r"\b(?:XPB|YPB)\s*\(", re.I),
}


def inventory(path: Path, report: Path, excerpt_limit: int) -> dict:
    data = path.read_bytes()
    lines = data.decode("latin-1").splitlines()
    matches: dict[str, list[int]] = {}
    for name, pat in SOURCE_PATTERNS.items():
        hits = [i for i, line in enumerate(lines, 1)
                if line and line[0] not in "cC*!" and pat.search(line[:72])]
        if not hits:
            raise AssertionError(f"Missing original CALPUFF source symbol class {name}")
        matches[name] = hits
    locations = set()
    for key in ("point_internal", "grid_conversion"):
        for line in matches[key][:excerpt_limit]:
            locations.update(range(max(1, line - 3), min(len(lines), line + 4) + 1))
    excerpts = [f"{i:06d} {lines[i-1][:72]}" for i in sorted(locations)]
    result = {
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "source_lines": len(lines),
        "point_internal_assignments_for_manual_review": [
            i for i in matches["point_internal"] if re.search(
                r"\b(?:XPT1GRD|YPT1GRD)\s*\([^)]*\)\s*=", lines[i-1][:72], re.I)
        ],
        "matching_line_counts": {name: len(pos) for name, pos in matches.items()},
        "excerpts": excerpts,
        "scope": "SOURCE_INVENTORY_ONLY_NOT_CPP_INTERNAL_STATE_PARITY",
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n")
    print("P7_ORIGINAL_RELATIVE_GRID_SOURCE_INVENTORY=PASS")
    print("P7_ORIGINAL_RELATIVE_GRID_ASSIGNMENT_LINES=" +
          ",".join(str(i) for i in result["point_internal_assignments_for_manual_review"][:15]))
    print("P7_ORIGINAL_RELATIVE_GRID_EXCERPTS_BEGIN")
    print("\n".join(excerpts[:320]))
    print("P7_ORIGINAL_RELATIVE_GRID_EXCERPTS_END")
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--limit", type=int, default=14)
    args = p.parse_args()
    if args.limit < 1 or args.limit > 25:
        p.error("--limit must be in [1,25]")
    inventory(args.source, args.report, args.limit)


if __name__ == "__main__":
    main()

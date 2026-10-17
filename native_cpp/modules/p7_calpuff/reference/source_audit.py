#!/usr/bin/env python3
"""Read-only P7A original CALPUFF source identity and option inventory.

No claim of original numerical execution or CALPUFF source coverage is made.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

VENDOR = Path(__file__).resolve().parents[4] / "engine/vendor/src/CALPUFF_v7.2.1_L150618"
EXPECTED_BLOB = {
    "calpuff.for": "3ce72291d3ed143f5f59ac3b92ec2faaac5dc208",
    "calpuff.inp": "84a5f0bd51df85601c3d7ea90504805eab3150fc",
}
EXTENSIONS = {".for", ".puf", ".inc", ".crd", ".inp"}


def audit(vendor: Path) -> dict:
    if not vendor.is_dir():
        raise FileNotFoundError(f"Original CALPUFF vendor tree missing: {vendor}")
    records = []
    for path in sorted(vendor.iterdir()):
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            continue
        content = path.read_bytes()
        git_blob = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
        if path.name in EXPECTED_BLOB and git_blob != EXPECTED_BLOB[path.name]:
            raise ValueError(f"Original CALPUFF source/control modified: {path.name} {git_blob}")
        records.append({
            "name": path.name,
            "bytes": len(content),
            "git_blob_sha1": git_blob,
            "sha256": hashlib.sha256(content).hexdigest(),
        })
    if not records or any(not any(r["name"] == name for r in records) for name in EXPECTED_BLOB):
        raise ValueError("Original CALPUFF source/control file missing")
    original = (vendor / "calpuff.for").read_text(encoding="latin-1")
    routines = sorted(set(re.findall(r"(?im)^\s{0,6}(?:recursive\s+)?subroutine\s+(\w+)", original)))
    control = (vendor / "calpuff.inp").read_text(encoding="latin-1")
    assignments = sorted(set(re.findall(r"!\s*([A-Za-z]\w*)\s*=", control)))
    return {
        "authority": "CALPUFF_v7.2.1_L150618",
        "stage": "P7A_SOURCE_AUDIT_ONLY",
        "original_fortran_runtime_executed": False,
        "reference_numerical_parity": "NOT_YET_TESTED",
        "required_blob_identities": "PASS",
        "source_files": records,
        "calpuff_for_declared_subroutine_names": routines,
        "bundled_control_assignment_names": assignments,
        "caveat": "This is only an inventory, not an original call graph, unsupported-option audit or frozen Hefei reference.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", type=Path, default=VENDOR)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = audit(args.vendor)
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print("P7A_ORIGINAL_SOURCE_IDENTITY=PASS")
    print("P7A_REFERENCE_PARITY=NOT_YET_TESTED")
    print("files=", len(report["source_files"]), "routines=", len(report["calpuff_for_declared_subroutine_names"]))


if __name__ == "__main__":
    main()

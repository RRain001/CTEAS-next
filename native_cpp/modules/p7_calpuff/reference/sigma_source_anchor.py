#!/usr/bin/env python3
"""Extract verbatim P7D dispersion units from the unmodified vendor source.

P7D reconstructs CALPUFF's MDISP=3 dispersion coefficients (Pasquill-Gifford
rural + McElroy-Pooler/Briggs urban). The originals live inside the vendor
file `engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for`, which also holds
the CALPUFF main program, so they cannot be compiled as a standalone library
directly. This tool extracts the exact source spans of the needed units (no
editing of any kind), records their line range and SHA-256, and can assemble
them into a job-private directory together with the vendor include files so
the *unmodified* text can be compiled into the P7D Fortran oracle.

`--check` fails when the vendor file no longer contains the pinned spans, so a
silent upstream source change can never be mistaken for a passing comparison.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

VENDOR_SUBDIR = "engine/vendor/src/CALPUFF_v7.2.1_L150618"
VENDOR_SOURCE = "calpuff.for"
# Units needed for the MDISP=3 sigma path. The BLOCK DATA unit carries the
# /CSIGMA/ tables (ayurb, xiyurb, azurb, xizurb, nzbrur, xzbrur, azrur,
# bzrur, ayt, syh, szh); SIGSET builds the sigma-z segment junctions and the
# roughness factors; SIGTY/SIGTZ/XVY/XVZ are the coefficient algorithms; WARN
# is called for reset (not fatal) negative increments.
UNITS = {
    "block_data": r"^      BLOCK DATA\s*$",
    "sigset": r"^      subroutine sigset\s*$",
    "sigty": r"^      subroutine sigty\b",
    "sigtz": r"^      subroutine sigtz\b",
    "xvy": r"^      function xvy\b",
    "xvz": r"^      function xvz\b",
    "warn": r"^      subroutine warn\b",
}
# Fixed-form `      end` terminators; `enddo`/`endif`/`end do`/`end if` are not
# unit terminators. Some vendor lines carry sequence numbers in columns 73-80,
# which are tolerated.
END_RE = re.compile(r"^      end(?![a-zA-Z])\s*(\S.*)?$", re.IGNORECASE)
END_KEYWORDS = {
    "do", "if", "where", "select", "selectcase", "type", "block", "module",
    "program", "subroutine", "function", "associate", "forall", "critical",
    "enum", "interface", "team", "parallel",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def vendor_includes(vendor: Path) -> list[str]:
    # The extracted units include a large fraction of the vendor `*.puf`
    # parameter/common files (the BLOCK DATA unit in particular). Every one of
    # them is hashed and staged so the oracle compiles against the pristine
    # vendor text rather than a filtered subset.
    return sorted(path.name for path in vendor.glob("*.puf"))


def find_span(lines: list[str], pattern: str) -> tuple[int, int]:
    headers = [i for i, line in enumerate(lines) if re.match(pattern, line, re.IGNORECASE)]
    if len(headers) != 1:
        raise ValueError(f"expected exactly one unit for {pattern!r}, found {len(headers)}")
    start = headers[0]
    for index in range(start + 1, len(lines)):
        match = END_RE.match(lines[index])
        if not match:
            continue
        remainder = (match.group(1) or "").strip().split()
        if remainder and remainder[0].lower() in END_KEYWORDS:
            continue
        return start, index
    raise ValueError(f"unit starting at line {start + 1} has no terminator")


def extract(vendor: Path) -> tuple[dict, dict[str, str]]:
    source = vendor / VENDOR_SOURCE
    if not source.is_file():
        raise FileNotFoundError(f"original CALPUFF source missing: {source}")
    raw = source.read_bytes()
    lines = raw.decode("latin-1").splitlines()
    manifest: dict = {
        "gate": "P7D_SIGMA_SOURCE_ANCHOR",
        "vendor_source": VENDOR_SOURCE,
        "vendor_source_sha256": sha256_bytes(raw),
        "vendor_include_sha256": {},
        "units": {},
        "mandata_tables": [
            "ayurb", "xiyurb", "azurb", "xizurb", "nzbrur", "xzbrur",
            "azrur", "bzrur", "ayt", "syh", "szh",
        ],
        "not_modified": True,
    }
    spans: dict[str, str] = {}
    for name, pattern in UNITS.items():
        start, end = find_span(lines, pattern)
        text = "\n".join(lines[start:end + 1]) + "\n"
        manifest["units"][name] = {
            "first_line": start + 1,
            "last_line": end + 1,
            "lines": end - start + 1,
            "sha256": sha256_bytes(text.encode("latin-1")),
        }
        spans[name] = text
    for include in vendor_includes(vendor):
        path = vendor / include
        manifest["vendor_include_sha256"][include] = sha256_bytes(path.read_bytes())
    return manifest, spans


def stage(vendor: Path, output: Path, manifest: dict, spans: dict[str, str]) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name, text in spans.items():
        (output / f"vendor_{name}.f").write_bytes(text.encode("latin-1"))
    driver = Path(__file__).with_name("sigma_oracle_driver.f")
    shutil.copy2(driver, output / driver.name)
    for include in manifest["vendor_include_sha256"]:
        shutil.copy2(vendor / include, output / include)
    (output / "sigma_source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    default_root = Path(__file__).resolve().parents[4]
    parser.add_argument("--repo-root", type=Path, default=default_root)
    parser.add_argument("--vendor", type=Path, help=f"vendor source directory (default <repo>/{VENDOR_SUBDIR})")
    parser.add_argument("--manifest", type=Path, help="write the source anchor manifest here")
    parser.add_argument("--check", type=Path, help="compare against this committed manifest and fail on drift")
    parser.add_argument("--stage", type=Path, help="write extracted spans + driver + includes here")
    args = parser.parse_args()
    vendor = args.vendor or args.repo_root / VENDOR_SUBDIR
    manifest, spans = extract(vendor)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    if args.stage:
        stage(vendor, args.stage, manifest, spans)
        print(f"P7D_SIGMA_SOURCE_STAGE={args.stage}")
    if args.check:
        pinned = json.loads(args.check.read_text())
        if pinned != manifest:
            raise SystemExit(
                "P7D vendor dispersion source drift: extracted spans/hashes differ from the "
                "pinned manifest; re-audit before trusting the oracle")
        print("P7D_SIGMA_SOURCE_ANCHOR=PASS units=" + ",".join(sorted(manifest["units"])))
    print("P7D_SIGMA_VENDOR_SHA256=" + manifest["vendor_source_sha256"])
    for name, info in manifest["units"].items():
        print(f"P7D_SIGMA_UNIT {name:10s} lines={info['first_line']}-{info['last_line']} "
              f"sha256={info['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

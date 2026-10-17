#!/usr/bin/env python3
"""Extract verbatim P7I CTSG support units (QATR, TFAC, BLOCK DATA) from the vendor source."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

VENDOR_SUBDIR = "engine/vendor/src/CALPUFF_v7.2.1_L150618"
VENDOR_SOURCE = "calpuff.for"
UNITS = {
    "block_data": r"^      BLOCK DATA\s*$",
    "qatr": r"^      subroutine qatr\b",
    "tfac": r"^      subroutine tfac\b",
    "rotate": r"^      subroutine rotate\b",
}
END_RE = re.compile(r"^      end(?![a-zA-Z])\s*(\S.*)?$", re.IGNORECASE)
END_KEYWORDS = {
    "do", "if", "where", "select", "selectcase", "type", "block", "module",
    "program", "subroutine", "function", "associate", "forall", "critical",
    "enum", "interface", "team", "parallel",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
    raw = source.read_bytes()
    lines = raw.decode("latin-1").splitlines()
    manifest: dict = {
        "gate": "P7I_CTSG_SUPPORT_SOURCE_ANCHOR",
        "vendor_source": VENDOR_SOURCE,
        "vendor_source_sha256": sha256_bytes(raw),
        "units": {},
        "vendor_include_sha256": {},
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
    for include in sorted(path.name for path in vendor.glob("*.puf")):
        manifest["vendor_include_sha256"][include] = sha256_bytes((vendor / include).read_bytes())
    return manifest, spans


def stage(vendor: Path, output: Path, manifest: dict, spans: dict[str, str]) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name, text in spans.items():
        (output / f"vendor_{name}.f").write_bytes(text.encode("latin-1"))
    driver = Path(__file__).with_name("p7i_oracle_driver.f")
    shutil.copy2(driver, output / driver.name)
    for include in manifest["vendor_include_sha256"]:
        shutil.copy2(vendor / include, output / include)
    (output / "p7i_source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    default_root = Path(__file__).resolve().parents[4]
    parser.add_argument("--repo-root", type=Path, default=default_root)
    parser.add_argument("--vendor", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--check", type=Path)
    parser.add_argument("--stage", type=Path)
    args = parser.parse_args()
    vendor = args.vendor or args.repo_root / VENDOR_SUBDIR
    manifest, spans = extract(vendor)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    if args.stage:
        stage(vendor, args.stage, manifest, spans)
        print(f"P7I_SOURCE_STAGE={args.stage}")
    if args.check:
        pinned = json.loads(args.check.read_text())
        if pinned != manifest:
            raise SystemExit("P7I vendor CTSG support source drift: re-audit before trusting the oracle")
        print("P7I_SOURCE_ANCHOR=PASS units=" + ",".join(sorted(manifest["units"])))
    print("P7I_VENDOR_SHA256=" + manifest["vendor_source_sha256"])
    for name, info in manifest["units"].items():
        print(f"P7I_UNIT {name:5s} lines={info['first_line']}-{info['last_line']} sha256={info['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

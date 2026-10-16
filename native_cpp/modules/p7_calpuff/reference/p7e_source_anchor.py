#!/usr/bin/env python3
"""Extract verbatim P7E receptor/sampling/output units from the vendor source.

The units live inside engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for,
which also holds the CALPUFF main program, so they cannot be compiled directly.
This tool slices the exact source spans (no editing), records their line range
and SHA-256, and can stage them with the vendor include files so the
*unmodified* text can be linked into the P7E Fortran oracle:

  PFSAMP  puff-to-receptor sampling integrals
  ERFDIF  error-function difference used by PFSAMP
  WRTI1D / WRTR1D / WRTR2D  dataset record writers (record framing)
"""
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
    "pfsamp": r"^      subroutine pfsamp\b",
    "erfdif": r"^ *function erfdif\b",
    "wrti1d": r"^      subroutine wrti1d\b",
    "wrtr1d": r"^      subroutine wrtr1d\b",
    "wrtr2d": r"^      subroutine wrtr2d\b",
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
    if not source.is_file():
        raise FileNotFoundError(f"original CALPUFF source missing: {source}")
    raw = source.read_bytes()
    lines = raw.decode("latin-1").splitlines()
    manifest: dict = {
        "gate": "P7E_RECEPTOR_SAMPLING_SOURCE_ANCHOR",
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
    driver = Path(__file__).with_name("p7e_oracle_driver.f")
    shutil.copy2(driver, output / driver.name)
    for include in manifest["vendor_include_sha256"]:
        shutil.copy2(vendor / include, output / include)
    (output / "p7e_source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


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
        print(f"P7E_SOURCE_STAGE={args.stage}")
    if args.check:
        pinned = json.loads(args.check.read_text())
        if pinned != manifest:
            raise SystemExit(
                "P7E vendor receptor/sampling source drift: extracted spans/hashes differ from the "
                "pinned manifest; re-audit before trusting the oracle")
        print("P7E_SOURCE_ANCHOR=PASS units=" + ",".join(sorted(manifest["units"])))
    print("P7E_VENDOR_SHA256=" + manifest["vendor_source_sha256"])
    for name, info in manifest["units"].items():
        print(f"P7E_UNIT {name:7s} lines={info['first_line']}-{info['last_line']} "
              f"sha256={info['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

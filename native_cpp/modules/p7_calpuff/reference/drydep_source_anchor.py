#!/usr/bin/env python3
"""Extract verbatim P7F dry-deposition units from the unmodified vendor source.

The MDRY=1 dry deposition path lives inside
engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for, which also contains the
CALPUFF main program, so the units cannot be compiled as a library directly.
This tool slices the exact source spans (no editing of any kind), records their
line range and SHA-256, and can stage the compiled subset together with the
vendor include files so the *unmodified* text can be linked into the P7F
Fortran oracle.

Compiled by the oracle: VDCOMP (the resistance model) and VDP (referenced by
VDCOMP for the particle branch, which P7F refuses). Anchored read-only, because
they cannot be linked without the vendor input reader and are ported by hand:
DRY (uniformly-mixed removal branch), DRYI (time-invariant parameters), RDVD
and VDP1 (user-specified and particle paths, not reconstructed), plus the
BLOCK DATA unit that carries the /DRYGAS/ constants.
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
COMPILED_UNITS = {
    "vdcomp": r"^      subroutine vdcomp\b",
    "vdp": r"^      subroutine vdp\b",
}
ANCHORED_UNITS = {
    "block_data": r"^      BLOCK DATA\s*$",
    "dry": r"^      subroutine dry\b",
    "dryi": r"^      subroutine dryi\b",
    "rdvd": r"^      subroutine rdvd\b",
    "vdp1": r"^      subroutine vdp1\b",
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


def extract(vendor: Path) -> tuple[dict, dict[str, str], dict[str, str]]:
    source = vendor / VENDOR_SOURCE
    if not source.is_file():
        raise FileNotFoundError(f"original CALPUFF source missing: {source}")
    raw = source.read_bytes()
    lines = raw.decode("latin-1").splitlines()
    manifest: dict = {
        "gate": "P7F_DRYDEP_SOURCE_ANCHOR",
        "vendor_source": VENDOR_SOURCE,
        "vendor_source_sha256": sha256_bytes(raw),
        "compiled_units": {},
        "anchored_units": {},
        "vendor_include_sha256": {},
        "not_modified": True,
    }
    compiled: dict[str, str] = {}
    anchored: dict[str, str] = {}
    for name, pattern in COMPILED_UNITS.items():
        start, end = find_span(lines, pattern)
        text = "\n".join(lines[start:end + 1]) + "\n"
        manifest["compiled_units"][name] = {
            "first_line": start + 1,
            "last_line": end + 1,
            "lines": end - start + 1,
            "sha256": sha256_bytes(text.encode("latin-1")),
        }
        compiled[name] = text
    for name, pattern in ANCHORED_UNITS.items():
        start, end = find_span(lines, pattern)
        text = "\n".join(lines[start:end + 1]) + "\n"
        manifest["anchored_units"][name] = {
            "first_line": start + 1,
            "last_line": end + 1,
            "lines": end - start + 1,
            "sha256": sha256_bytes(text.encode("latin-1")),
        }
        anchored[name] = text
    for include in sorted(path.name for path in vendor.glob("*.puf")):
        manifest["vendor_include_sha256"][include] = sha256_bytes((vendor / include).read_bytes())
    return manifest, compiled, anchored


def stage(vendor: Path, output: Path, manifest: dict, compiled: dict[str, str]) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name, text in compiled.items():
        (output / f"vendor_{name}.f").write_bytes(text.encode("latin-1"))
    driver = Path(__file__).with_name("drydep_oracle_driver.f")
    shutil.copy2(driver, output / driver.name)
    for include in manifest["vendor_include_sha256"]:
        shutil.copy2(vendor / include, output / include)
    (output / "drydep_source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


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
    manifest, compiled, _ = extract(vendor)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    if args.stage:
        stage(vendor, args.stage, manifest, compiled)
        print(f"P7F_DRYDEP_SOURCE_STAGE={args.stage}")
    if args.check:
        pinned = json.loads(args.check.read_text())
        if pinned != manifest:
            raise SystemExit(
                "P7F vendor dry-deposition source drift: extracted spans/hashes differ from the "
                "pinned manifest; re-audit before trusting the oracle")
        print("P7F_DRYDEP_SOURCE_ANCHOR=PASS units=" +
              ",".join(sorted(manifest["compiled_units"]) + sorted(manifest["anchored_units"])))
    print("P7F_DRYDEP_VENDOR_SHA256=" + manifest["vendor_source_sha256"])
    for group in ("compiled_units", "anchored_units"):
        for name, info in manifest[group].items():
            print(f"P7F_DRYDEP_UNIT {group[:-1]:8s} {name:6s} lines={info['first_line']}-"
                  f"{info['last_line']} sha256={info['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

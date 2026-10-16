#!/usr/bin/env python3
"""P7V: pin the advection units (ADVWND, ADVECT, ZFIND, PUFFDZ) of the vendor.

`ZFIND` (calpuff.for L18381-18419) finds the layer containing a height, `ADVWND`
(L2438-2538) averages the wind over the puff's layer, `ADVECT` (L2540-2765) is the
advective-wind dispatch for METFM 1-5 and `PUFFDZ` (L2882-3005) computes the
puff's vertical extent. All four are extracted whole and compiled unmodified;
POWLAW (METFM 2/3) and XTPRF (METFM 4/5) are off the locked deck's path and are
hard-failing stubs in the oracle.

`--stage DIR` writes the extracted vendor units, the hand-written oracle driver
and every vendor `*.puf` include into DIR.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil

VENDOR_SUBDIR = "engine/vendor/src/CALPUFF_v7.2.1_L150618"
VENDOR_SOURCE = "calpuff.for"

UNITS = ("zfind", "advwnd", "advect", "puffdz")

END_KEYWORDS = {"do", "if", "where", "select", "selectcase", "type", "block", "module", "program",
                "subroutine", "function", "associate", "forall", "critical", "enum", "interface",
                "team", "parallel"}
HEADER = re.compile(r"^\s{0,6}(?:real|integer|logical|double\s+precision)?\s*"
                    r"(?:function|subroutine)\s+([a-z0-9_]+)\s*\(?", re.IGNORECASE)
TERMINATOR = re.compile(r"^      end(?![a-zA-Z])\s*(\S.*)?$", re.IGNORECASE)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def headers(lines: list[str]) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for index, line in enumerate(lines):
        match = HEADER.match(line)
        if match:
            found.setdefault(match.group(1).lower(), []).append(index)
    return found


def find_span(lines: list[str], name: str, found: dict[str, list[int]]) -> tuple[int, int]:
    hits = found.get(name, [])
    if len(hits) != 1:
        raise SystemExit(f"P7V: unit {name} has {len(hits)} header matches, expected one")
    start = hits[0]
    for index in range(start + 1, len(lines)):
        match = TERMINATOR.match(lines[index])
        if not match:
            continue
        remainder = (match.group(1) or "").strip().split()
        if remainder and remainder[0].lower() in END_KEYWORDS:
            continue
        return start, index
    raise SystemExit(f"P7V: unit {name} has no terminator")


def extract(vendor: pathlib.Path) -> tuple[dict, dict[str, str]]:
    raw = (vendor / VENDOR_SOURCE).read_bytes()
    lines = raw.decode("latin-1").splitlines()
    found = headers(lines)
    units: dict[str, dict] = {}
    spans: dict[str, str] = {}
    for name in UNITS:
        start, end = find_span(lines, name, found)
        body = "\n".join(lines[start:end + 1]) + "\n"
        units[name] = {
            "first_line": start + 1,
            "last_line": end + 1,
            "lines": end - start + 1,
            "sha256": sha256_bytes(body.encode("latin-1")),
            "calls": sorted({call.lower() for call in re.findall(r"\bcall\s+([a-z0-9_]+)", body,
                                                                re.IGNORECASE)}),
        }
        spans[name] = body
    manifest = {
        "gate": "P7V_ADVECTION_SOURCE_ANCHOR",
        "vendor_source": VENDOR_SOURCE,
        "vendor_source_sha256": sha256_bytes(raw),
        "located_by": "routine-header scan (identical to p7k/p7m)",
        "units": units,
        "ported": {"zfind": True, "advwnd": True, "advect": True, "puffdz": True},
        "not_ported": ["powlaw (METFM 2/3)", "xtprf (METFM 4/5)", "risewind", "puffdz's caller"],
        "deck_path": "METFM=1: ADVECT copies the cell's U/V profile and calls ADVWND -> ZFIND",
        "vendor_include_sha256": {
            path.name: sha256_bytes(path.read_bytes())
            for path in sorted(vendor.glob("*.puf"))
        },
        "not_modified": True,
    }
    return manifest, spans


def stage(vendor: pathlib.Path, output: pathlib.Path, manifest: dict,
          spans: dict[str, str]) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name in UNITS:
        (output / f"vendor_{name}.f").write_bytes(spans[name].encode("latin-1"))
    driver = pathlib.Path(__file__).with_name("p7v_oracle_driver.f")
    shutil.copy2(driver, output / driver.name)
    for include in manifest["vendor_include_sha256"]:
        shutil.copy2(vendor / include, output / include)
    (output / "p7v_source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=pathlib.Path,
                        default=pathlib.Path(__file__).resolve().parents[4])
    parser.add_argument("--manifest", type=pathlib.Path)
    parser.add_argument("--check", type=pathlib.Path)
    parser.add_argument("--stage", type=pathlib.Path)
    args = parser.parse_args()
    vendor = args.repo_root / VENDOR_SUBDIR
    manifest, spans = extract(vendor)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    if args.stage:
        stage(vendor, args.stage, manifest, spans)
        print(f"P7V_SOURCE_STAGE={args.stage}")
    if args.check:
        pinned = json.loads(args.check.read_text())
        if pinned != manifest:
            raise SystemExit("P7V advection source drift: re-audit before trusting the oracle")
        print("P7V_SOURCE_ANCHOR=PASS units=" + ",".join(sorted(manifest["units"])))
    print("P7V_VENDOR_SHA256=" + manifest["vendor_source_sha256"])
    for name, info in manifest["units"].items():
        print(f"P7V_UNIT {name:7s} lines={info['first_line']}-{info['last_line']} "
              f"sha256={info['sha256']} calls={','.join(info['calls'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

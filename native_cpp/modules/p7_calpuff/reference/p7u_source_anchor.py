#!/usr/bin/env python3
"""P7U: locate and pin the advection / step-integration units of the vendor.

This round locates the chain that advances a puff one step and pins every span and
call closure, so the next round starts from verified entry points:

  ADVWND  L2438-2538   vertically-averaged wind over the puff's layer
  ADVECT  L2540-2765   the advective-wind dispatch (METFM 1-5)
  PUFFDZ  L2882-3005   the puff's vertical extent (ZBOT/ZTOP) for the step
  ZFIND   L18381-18419 the met layer containing a height
  POWLAW  L33463-33516 the power-law wind profile (METFM 2/3)
  XTPRF   L33192-33461 the profile-data lookup (METFM 4/5)

plus the two *inline* pieces of COMP's step integration, pinned by content:

  comp_step_start  the start-of-step position and met-cell selection
  comp_step_wind   PUFFDZ + ADVECT + the rise-wind and calm adjustments

The instrumentation request recorded in the ledger names the exact subroutine,
line span and variables that a DGM-style probe must print for a real numerical
comparison of one puff step.

`--check` fails on any drift.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re

VENDOR_SUBDIR = "engine/vendor/src/CALPUFF_v7.2.1_L150618"
VENDOR_SOURCE = "calpuff.for"

UNITS = ("advwnd", "advect", "puffdz", "zfind", "powlaw", "xtprf")

INLINE_BLOCKS = (
    {
        "name": "comp_step_start",
        "enclosing": "comp",
        "start": r"^            xold=xpb\(ii\)\s*$",
        "end": r"^         endif\s*$",
        "end_count": 1,
    },
    {
        "name": "comp_step_wind",
        "enclosing": "comp",
        "start": r"^         call PUFFDZ\(ii,icode,lpuff,istab,ilayer,htmet,dpbl,\s*$",
        "end": r"^         endif\s*$",
        "end_count": 1,
    },
)

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


def enclosing_units(lines: list[str]) -> dict[int, str]:
    found = headers(lines)
    ordered = sorted((index, name) for name, hits in found.items() for index in hits)
    owner: dict[int, str] = {}
    current = "<none>"
    cursor = 0
    for index in range(len(lines)):
        while cursor < len(ordered) and ordered[cursor][0] <= index:
            current = ordered[cursor][1]
            cursor += 1
        owner[index] = current
    return owner


def find_span(lines: list[str], name: str, found: dict[str, list[int]]) -> tuple[int, int]:
    hits = found.get(name, [])
    if len(hits) != 1:
        raise SystemExit(f"P7U: unit {name} has {len(hits)} header matches, expected one")
    start = hits[0]
    for index in range(start + 1, len(lines)):
        match = TERMINATOR.match(lines[index])
        if not match:
            continue
        remainder = (match.group(1) or "").strip().split()
        if remainder and remainder[0].lower() in END_KEYWORDS:
            continue
        return start, index
    raise SystemExit(f"P7U: unit {name} has no terminator")


def locate_inline(lines: list[str], owner: dict[int, str], spec: dict) -> tuple[int, int]:
    starts = [index for index, line in enumerate(lines)
              if re.match(spec["start"], line) and owner[index] == spec["enclosing"]]
    if len(starts) != 1:
        raise SystemExit(f"P7U: inline block {spec['name']} has {len(starts)} starts inside "
                         f"{spec['enclosing']}, expected one")
    start = starts[0]
    ends = [index for index, line in enumerate(lines)
            if index > start and re.match(spec["end"], line) and owner[index] == spec["enclosing"]]
    if len(ends) < spec["end_count"]:
        raise SystemExit(f"P7U: inline block {spec['name']} has only {len(ends)} end anchors")
    return start, ends[spec["end_count"] - 1]


def extract(vendor: pathlib.Path) -> tuple[dict, dict[str, str]]:
    raw = (vendor / VENDOR_SOURCE).read_bytes()
    lines = raw.decode("latin-1").splitlines()
    found = headers(lines)
    owner = enclosing_units(lines)

    units: dict[str, dict] = {}
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

    inline: dict[str, dict] = {}
    for spec in INLINE_BLOCKS:
        start, end = locate_inline(lines, owner, spec)
        block = "\n".join(lines[start:end + 1]) + "\n"
        inline[spec["name"]] = {
            "enclosing_unit": spec["enclosing"],
            "first_line": start + 1,
            "last_line": end + 1,
            "lines": end - start + 1,
            "sha256": sha256_bytes(block.encode("latin-1")),
            "statements": [line.strip() for line in block.splitlines()
                           if line.strip() and not line.strip().lower().startswith("c")],
        }

    manifest = {
        "gate": "P7U_ADVECTION_STEP_SOURCE_LOCATION",
        "vendor_source": VENDOR_SOURCE,
        "vendor_source_sha256": sha256_bytes(raw),
        "located_by": "routine-header scan plus content anchors confined to the enclosing unit",
        "units": units,
        "inline": inline,
        "chain": ["PUFFDZ", "ADVECT", "ADVWND", "ZFIND"],
        "off_path": ["POWLAW (METFM 2/3)", "XTPRF (METFM 4/5)", "RISEWIND (rise-wind weighting)"],
        "ported": {},
        "not_ported": ["advect", "advwnd", "puffdz", "zfind", "powlaw", "xtprf",
                       "the inline step integration of COMP"],
        "note": ("The advective wind (ADVECT for METFM=1 -> ADVWND -> ZFIND) and the puff's "
                 "vertical extent (PUFFDZ) are located and pinned; porting them is the next "
                 "round's entry point, and the ledger records the exact instrumentation request "
                 "for the inline step integration."),
        "not_modified": True,
    }
    return manifest, {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=pathlib.Path,
                        default=pathlib.Path(__file__).resolve().parents[4])
    parser.add_argument("--manifest", type=pathlib.Path)
    parser.add_argument("--check", type=pathlib.Path)
    args = parser.parse_args()
    vendor = args.repo_root / VENDOR_SUBDIR
    manifest, _ = extract(vendor)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    if args.check:
        pinned = json.loads(args.check.read_text())
        if pinned != manifest:
            raise SystemExit("P7U advection source drift: re-audit before porting")
        print("P7U_SOURCE_ANCHOR=PASS units=" + ",".join(sorted(manifest["units"])) + " inline=" +
              ",".join(sorted(manifest["inline"])))
    print("P7U_VENDOR_SHA256=" + manifest["vendor_source_sha256"])
    for name, info in manifest["units"].items():
        print(f"P7U_UNIT {name:7s} lines={info['first_line']}-{info['last_line']} "
              f"sha256={info['sha256']} calls={','.join(info['calls'])}")
    for name, info in manifest["inline"].items():
        print(f"P7U_INLINE {name} lines={info['first_line']}-{info['last_line']} "
              f"sha256={info['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

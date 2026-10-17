#!/usr/bin/env python3
"""P7N: pin the Briggs plume-rise units (and the inline flux block) of the vendor.

Units are located with the same routine-header scan P7K/P7M use. The buoyancy and
momentum flux statements live *inline* in `points1` rather than in a routine, so
they are pinned here by content and staged inside a generated harness subroutine
that supplies only the declarations and the argument transfer: the extracted
statements themselves stay byte-identical.

`--stage DIR` writes `vendor_<unit>.f`, `vendor_inline_flux.f`, the hand-written
oracle driver and every vendor `*.puf` include into DIR.
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

UNITS = ("stktip", "prfin", "prm", "prb", "prfpp", "grise")

# The inline flux statements of POINTS1 (points2 uses a different spelling, so
# the `(i)` form below occurs exactly once in the file).
INLINE_FLUX = {
    "name": "points1_flux",
    "start": r"^      fluxb=\(2\.4516625\*diam\(i\)\*\*2\*exitw\(i\)/tstak\(i\)\)\*dtemp\s*$",
    "end": r"^      if\(fmfpt1\(i\)\.LT\.0\.5\) fluxm=0\.0\s*$",
    "enclosing": "points1",
}

END_KEYWORDS = {"do", "if", "where", "select", "selectcase", "type", "block", "module", "program",
                "subroutine", "function", "associate", "forall", "critical", "enum", "interface",
                "team", "parallel"}
HEADER = re.compile(r"^\s{0,6}(?:real|integer|logical|double\s+precision)?\s*"
                    r"(?:function|subroutine)\s+([a-z0-9_]+)\s*\(?", re.IGNORECASE)
TERMINATOR = re.compile(r"^      end(?![a-zA-Z])\s*(\S.*)?$", re.IGNORECASE)

FLUX_HARNESS_HEADER = """c-----------------------------------------------------------------------
      subroutine p7n_flux(diam_in,exitw_in,tstak_in,dtemp_in,temp_in,
     &                    fmfpt1_in,fluxb_out,fluxm_out)
c-----------------------------------------------------------------------
c --- GENERATED HARNESS (not vendor source). It wraps the VERBATIM POINTS1
c     flux statements extracted by reference/p7n_source_anchor.py: only the
c     declarations and the argument transfer are added, so the extracted
c     lines below are byte-identical to calpuff.for.
      real diam_in,exitw_in,tstak_in,dtemp_in,temp_in,fmfpt1_in
      real fluxb_out,fluxm_out
      real diam(1),exitw(1),tstak(1),fmfpt1(1)
      real dtemp,temp,fluxb,fluxm
      integer i
      i=1
      diam(1)=diam_in
      exitw(1)=exitw_in
      tstak(1)=tstak_in
      fmfpt1(1)=fmfpt1_in
      dtemp=dtemp_in
      temp=temp_in
"""

FLUX_HARNESS_FOOTER = """      fluxb_out=fluxb
      fluxm_out=fluxm
      return
      end
"""


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
        raise SystemExit(f"P7N: unit {name} has {len(hits)} header matches, expected one")
    start = hits[0]
    for index in range(start + 1, len(lines)):
        match = TERMINATOR.match(lines[index])
        if not match:
            continue
        remainder = (match.group(1) or "").strip().split()
        if remainder and remainder[0].lower() in END_KEYWORDS:
            continue
        return start, index
    raise SystemExit(f"P7N: unit {name} has no terminator")


def extract(vendor: pathlib.Path) -> tuple[dict, dict[str, str]]:
    raw = (vendor / VENDOR_SOURCE).read_bytes()
    lines = raw.decode("latin-1").splitlines()
    found = headers(lines)
    owner = enclosing_units(lines)
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
            "uses_common": sorted({include.lower() for include in
                                   re.findall(r"include\s+'([a-z0-9_.]+)'", body, re.IGNORECASE)}),
        }
        spans[name] = body

    start_matches = [index for index, line in enumerate(lines)
                     if re.match(INLINE_FLUX["start"], line)]
    end_matches = [index for index, line in enumerate(lines)
                   if re.match(INLINE_FLUX["end"], line)]
    if len(start_matches) != 1 or len(end_matches) != 1:
        raise SystemExit(f"P7N: inline flux block is not unique ({len(start_matches)} starts, "
                         f"{len(end_matches)} ends)")
    if owner[start_matches[0]] != INLINE_FLUX["enclosing"]:
        raise SystemExit("P7N: the inline flux block is no longer inside "
                         f"{INLINE_FLUX['enclosing']}")
    block = "\n".join(lines[start_matches[0]:end_matches[0] + 1]) + "\n"
    inline = {
        "name": INLINE_FLUX["name"],
        "enclosing_unit": INLINE_FLUX["enclosing"],
        "first_line": start_matches[0] + 1,
        "last_line": end_matches[0] + 1,
        "lines": end_matches[0] - start_matches[0] + 1,
        "sha256": sha256_bytes(block.encode("latin-1")),
        "statements": [line.strip() for line in block.splitlines()
                       if line.strip() and not line.strip().lower().startswith("c")],
    }
    harness = FLUX_HARNESS_HEADER + block + FLUX_HARNESS_FOOTER
    manifest = {
        "gate": "P7N_PLUME_RISE_SOURCE_ANCHOR",
        "vendor_source": VENDOR_SOURCE,
        "vendor_source_sha256": sha256_bytes(raw),
        "located_by": "routine-header scan (identical to p7k/p7m) plus a content anchor for the "
                      "inline POINTS1 flux block",
        "units": units,
        "inline": inline,
        "harness_sha256": sha256_bytes(harness.encode("latin-1")),
        "ported": {name: True for name in UNITS},
        "not_ported": ["prshear", "prfinsh", "prss", "prtab", "prbl", "intertab", "numrise",
                       "ptlaps", "prdw", "dwsigs"],
        "vendor_include_sha256": {
            path.name: sha256_bytes(path.read_bytes())
            for path in sorted(vendor.glob("*.puf"))
        },
        "not_modified": True,
    }
    spans["inline_flux"] = harness
    return manifest, spans


def stage(vendor: pathlib.Path, output: pathlib.Path, manifest: dict,
          spans: dict[str, str]) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name in UNITS:
        (output / f"vendor_{name}.f").write_bytes(spans[name].encode("latin-1"))
    (output / "vendor_inline_flux.f").write_bytes(spans["inline_flux"].encode("latin-1"))
    driver = pathlib.Path(__file__).with_name("p7n_oracle_driver.f")
    shutil.copy2(driver, output / driver.name)
    for include in manifest["vendor_include_sha256"]:
        shutil.copy2(vendor / include, output / include)
    (output / "p7n_source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


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
        print(f"P7N_SOURCE_STAGE={args.stage}")
    if args.check:
        pinned = json.loads(args.check.read_text())
        if pinned != manifest:
            raise SystemExit("P7N plume-rise source drift: re-audit before trusting the oracle")
        print("P7N_SOURCE_ANCHOR=PASS units=" + ",".join(sorted(manifest["units"])) +
              " inline=" + manifest["inline"]["name"])
    print("P7N_VENDOR_SHA256=" + manifest["vendor_source_sha256"])
    for name, info in manifest["units"].items():
        print(f"P7N_UNIT {name:7s} lines={info['first_line']}-{info['last_line']} "
              f"sha256={info['sha256']}")
    print(f"P7N_INLINE {manifest['inline']['name']} "
          f"lines={manifest['inline']['first_line']}-{manifest['inline']['last_line']} "
          f"sha256={manifest['inline']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

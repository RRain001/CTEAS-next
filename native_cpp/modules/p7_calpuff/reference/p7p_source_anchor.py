#!/usr/bin/env python3
"""P7P: pin SETPUF's step bookkeeping and SETCSIG from the vendor source.

`SETPUF` (calpuff.for L48198-48757) is the per-step puff update. Two of its
pieces are *inline* and are pinned here by content inside their enclosing unit:
the distance/travel-time/calm block (L48373-48399) and the state-update block
(gravitational settling + the total distance/time counters + the end-of-step
position, L48706-48723). They are staged inside generated harness subroutines
that add only declarations and the argument transfer, so the extracted statements
stay byte-identical. `SETCSIG` (L52504-52619) is a routine and is extracted whole.

`--stage DIR` writes the extracted vendor units, the generated harnesses, the
hand-written oracle driver and every vendor `*.puf` include into DIR.
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

UNITS = ("setcsig",)

INLINE_BLOCKS = (
    {
        "name": "setpuf_step",
        "enclosing": "setpuf",
        "start": r"^      xttb1=xtotb\(ii\)\s*$",
        "end": r"^      endif\s*$",
    },
    {
        "name": "setpuf_update",
        "enclosing": "setpuf",
        "start": r"^      vsetl=vgrav\(1,1\)\s*$",
        "end": r"^      zpb\(ii\)=ze1\s*$",
    },
)

# Statements that pin the semantics this round does NOT port, verified by line.
PINNED_STATEMENTS = (
    ("setpuf", "tmtotb(ii)=tmtotb(ii)+tsamp"),
    ("setpuf", "xtotb(ii)=xtotb(ii)+distm"),
    ("setpuf", "zpb(ii)=ze1"),
)

END_KEYWORDS = {"do", "if", "where", "select", "selectcase", "type", "block", "module", "program",
                "subroutine", "function", "associate", "forall", "critical", "enum", "interface",
                "team", "parallel"}
HEADER = re.compile(r"^\s{0,6}(?:real|integer|logical|double\s+precision)?\s*"
                    r"(?:function|subroutine)\s+([a-z0-9_]+)\s*\(?", re.IGNORECASE)
TERMINATOR = re.compile(r"^      end(?![a-zA-Z])\s*(\S.*)?$", re.IGNORECASE)

STEP_HARNESS_HEADER = """c-----------------------------------------------------------------------
      subroutine p7p_step(xtotbin,tmtotbin,distm,tsamp,dm2km,ws,wscalm,
     &                    idw0in,xfinalin,idoptyin,idoptzin,idopty_o,
     &                    idoptz_o,
     &                    xttb1_o,xtte1_o,tb1_o,te1_o,dmidkm_o,tmid_o,
     &                    uavg_o,ukps_o,lcalm_o,idw0_o,xfinal_o)
c-----------------------------------------------------------------------
c --- GENERATED HARNESS (not vendor source). It wraps the VERBATIM SETPUF
c     step-bookkeeping statements extracted by reference/p7p_source_anchor.py.
      include 'params.puf'
      include 'puff.puf'
      real xtotbin,tmtotbin,distm,tsamp,dm2km,ws,wscalm,xfinalin
      integer idw0in,idoptyin,idoptzin,idopty_o,idoptz_o,idw0_o
      real xttb1_o,xtte1_o,tb1_o,te1_o,dmidkm_o,tmid_o,uavg_o,ukps_o
      real xfinal_o
      logical lcalm_o
      integer idopty,idoptz,ii
      real xttb1,xtte1,tb1,te1,dmidkm,tmid,uavg,ukps,zero
      logical lcalm
      zero=0.0
      ii=1
      idopty=idoptyin
      idoptz=idoptzin
      xtotb(1)=xtotbin
      tmtotb(1)=tmtotbin
      idw0(1)=idw0in
      xfinal(1)=xfinalin
"""

STEP_HARNESS_FOOTER = """      idopty_o=idopty
      idoptz_o=idoptz
      xttb1_o=xttb1
      xtte1_o=xtte1
      tb1_o=tb1
      te1_o=te1
      dmidkm_o=dmidkm
      tmid_o=tmid
      uavg_o=uavg
      ukps_o=ukps
      lcalm_o=lcalm
      idw0_o=idw0(1)
      xfinal_o=xfinal(1)
      return
      end
"""

UPDATE_HARNESS_HEADER = """c-----------------------------------------------------------------------
      subroutine p7p_update(ze1in,vgrav_in,mtilt,tsamp,distm,xtotbin,
     &                      tmtotbin,xnewin,ynewin,ze1_o,xtotb_o,
     &                      tmtotb_o,xpb_o,ypb_o,zpb_o)
c-----------------------------------------------------------------------
c --- GENERATED HARNESS (not vendor source). It wraps the VERBATIM SETPUF
c     state-update statements extracted by reference/p7p_source_anchor.py.
      include 'params.puf'
      include 'puff.puf'
      real ze1in,vgrav_in,tsamp,distm,xtotbin,tmtotbin,xnewin,ynewin
      real ze1_o,xtotb_o,tmtotb_o,xpb_o,ypb_o,zpb_o
      real vgrav(1,1),ze1,xnew,ynew,vsetl
      integer mtilt,ii
      ii=1
      ze1=ze1in
      vgrav(1,1)=vgrav_in
      xnew=xnewin
      ynew=ynewin
      xtotb(1)=xtotbin
      tmtotb(1)=tmtotbin
"""

UPDATE_HARNESS_FOOTER = """      ze1_o=ze1
      xtotb_o=xtotb(1)
      tmtotb_o=tmtotb(1)
      xpb_o=xpb(1)
      ypb_o=ypb(1)
      zpb_o=zpb(1)
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
        raise SystemExit(f"P7P: unit {name} has {len(hits)} header matches, expected one")
    start = hits[0]
    for index in range(start + 1, len(lines)):
        match = TERMINATOR.match(lines[index])
        if not match:
            continue
        remainder = (match.group(1) or "").strip().split()
        if remainder and remainder[0].lower() in END_KEYWORDS:
            continue
        return start, index
    raise SystemExit(f"P7P: unit {name} has no terminator")


def locate_inline(lines: list[str], owner: dict[int, str], spec: dict) -> tuple[int, int]:
    starts = [index for index, line in enumerate(lines)
              if re.match(spec["start"], line) and owner[index] == spec["enclosing"]]
    if len(starts) != 1:
        raise SystemExit(f"P7P: inline block {spec['name']} has {len(starts)} starts inside "
                         f"{spec['enclosing']}, expected one")
    start = starts[0]
    ends = [index for index, line in enumerate(lines)
            if index > start and re.match(spec["end"], line) and owner[index] == spec["enclosing"]]
    if not ends:
        raise SystemExit(f"P7P: inline block {spec['name']} has no end anchor after its start")
    return start, min(ends)


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
        }
        spans[name] = body

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
        if spec["name"] == "setpuf_step":
            spans["inline_step"] = STEP_HARNESS_HEADER + block + STEP_HARNESS_FOOTER
        else:
            spans["inline_update"] = UPDATE_HARNESS_HEADER + block + UPDATE_HARNESS_FOOTER

    pinned: list[dict] = []
    for unit, statement in PINNED_STATEMENTS:
        matches = [index for index, line in enumerate(lines)
                   if line.strip() == statement.strip() and owner[index] == unit]
        if len(matches) != 1:
            raise SystemExit(f"P7P: statement {statement!r} is not unique inside {unit}")
        pinned.append({"unit": unit, "line": matches[0] + 1, "statement": statement.strip()})

    manifest = {
        "gate": "P7P_SETPUF_STEP_SOURCE_ANCHOR",
        "vendor_source": VENDOR_SOURCE,
        "vendor_source_sha256": sha256_bytes(raw),
        "located_by": "routine-header scan plus content anchors confined to the enclosing unit",
        "units": units,
        "inline": inline,
        "pinned_statements": pinned,
        "harness_sha256": {
            "inline_step": sha256_bytes(spans["inline_step"].encode("latin-1")),
            "inline_update": sha256_bytes(spans["inline_update"].encode("latin-1")),
        },
        "ported": {"setcsig": True, "setpuf_step": True, "setpuf_update": True},
        "not_ported": ["setpuf (sigma update, rise table, MCTADJ=2, PRIME wake)",
                       "ctadj2", "wake_tab", "heftran", "tauly", "setslg", "comp"],
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
    (output / "vendor_inline_step.f").write_bytes(spans["inline_step"].encode("latin-1"))
    (output / "vendor_inline_update.f").write_bytes(spans["inline_update"].encode("latin-1"))
    driver = pathlib.Path(__file__).with_name("p7p_oracle_driver.f")
    shutil.copy2(driver, output / driver.name)
    for include in manifest["vendor_include_sha256"]:
        shutil.copy2(vendor / include, output / include)
    (output / "p7p_source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


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
        print(f"P7P_SOURCE_STAGE={args.stage}")
    if args.check:
        pinned = json.loads(args.check.read_text())
        if pinned != manifest:
            raise SystemExit("P7P SETPUF source drift: re-audit before trusting the oracle")
        print("P7P_SOURCE_ANCHOR=PASS units=" + ",".join(sorted(manifest["units"])) + " inline=" +
              ",".join(sorted(manifest["inline"])))
    print("P7P_VENDOR_SHA256=" + manifest["vendor_source_sha256"])
    for name, info in manifest["units"].items():
        print(f"P7P_UNIT {name:7s} lines={info['first_line']}-{info['last_line']} "
              f"sha256={info['sha256']}")
    for name, info in manifest["inline"].items():
        print(f"P7P_INLINE {name} lines={info['first_line']}-{info['last_line']} "
              f"sha256={info['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

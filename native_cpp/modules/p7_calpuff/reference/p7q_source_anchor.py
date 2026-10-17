#!/usr/bin/env python3
"""P7Q: pin SETPUF's sigma update (non-PRIME branch) from the vendor source.

Three contiguous blocks of `SETPUF` (calpuff.for L48198-48757) are pinned by
content inside their enclosing unit and staged inside generated harness
subroutines that add only declarations and the argument transfer, so the
extracted statements stay byte-identical:

  setpuf_sigma    L48505-48536  begin/mid/end SIGTY and SIGTZ with their virtuals
  setpuf_sigma_y  L48570-48604  sigma-y precision adjustment, store, BID
                                quadrature and the calm minimum
  setpuf_sigma_z  L48635-48667  the same for sigma-z

The PRIME wake branch (IDW0 3/4) and the MCTADJ=2 strain/walltrap adjustments
live outside these blocks and are NOT reconstructed.

`--stage DIR` writes the generated harnesses, the hand-written oracle driver and
every vendor `*.puf` include into DIR.
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

INLINE_BLOCKS = (
    {
        "name": "setpuf_sigma",
        "enclosing": "setpuf",
        "start": r"^      if\(iprime\.EQ\.0\) then\s*$",
        "end": r"^      endif\s*$",
        "end_count": 1,
    },
    {
        "name": "setpuf_sigma_y",
        "enclosing": "setpuf",
        "start": r"^      if\(syb1\.GT\.sym1\) sym1=syb1\s*$",
        "end": r"^      endif\s*$",
        "end_count": 2,
    },
    {
        "name": "setpuf_sigma_z",
        "enclosing": "setpuf",
        "start": r"^         if\(szb1\.GT\.szm1\) szm1=szb1\s*$",
        "end": r"^         endif\s*$",
        "end_count": 2,
    },
)

# Statements that pin the pieces this round does NOT port, verified by line.
PINNED_STATEMENTS = (
    ("setpuf", "call WAKE_TAB(istype,isnum,iqstep,idw0(ipnum),xttb1,"),
    ("setpuf", "call walltrap(ldbhr,syb1,sym1,zpb(ii),xpb(ii),ypb(ii),"),
    ("setpuf", "call ctadj2(r,zpb(ii),xpb(ii),ypb(ii),xmid,ymid,"),
    ("setpuf", "sigyb(ii)=sye1"),
    ("setpuf", "sigzb(ii)=sze1"),
)

END_KEYWORDS = {"do", "if", "where", "select", "selectcase", "type", "block", "module", "program",
                "subroutine", "function", "associate", "forall", "critical", "enum", "interface",
                "team", "parallel"}
HEADER = re.compile(r"^\s{0,6}(?:real|integer|logical|double\s+precision)?\s*"
                    r"(?:function|subroutine)\s+([a-z0-9_]+)\s*\(?", re.IGNORECASE)
TERMINATOR = re.compile(r"^      end(?![a-zA-Z])\s*(\S.*)?$", re.IGNORECASE)

SIGMA_HARNESS_HEADER = """c-----------------------------------------------------------------------
      subroutine p7q_sigma(sigyb_in,sigzb_in,zpuff,tmid,dmidkm,icode,
     &                     syb1_o,sym1_o,sye1_o,vtyb1_o,vtym1_o,vtye1_o,
     &                     vdyb1_o,vdym1_o,vdye1_o,szb1_o,szm1_o,sze1_o,
     &                     vtzb1_o,vtzm1_o,vtze1_o,vdzb1_o,vdzm1_o,
     &                     vdze1_o)
c-----------------------------------------------------------------------
c --- GENERATED HARNESS (not vendor source). It wraps the VERBATIM SETPUF
c     sigma begin/mid/end statements extracted by
c     reference/p7q_source_anchor.py.
      include 'params.puf'
      include 'puff.puf'
      real sigyb_in,sigzb_in,zpuff,tmid,dmidkm
      integer icode
      real syb1_o,sym1_o,sye1_o,vtyb1_o,vtym1_o,vtye1_o
      real vdyb1_o,vdym1_o,vdye1_o,szb1_o,szm1_o,sze1_o
      real vtzb1_o,vtzm1_o,vtze1_o,vdzb1_o,vdzm1_o,vdze1_o
      real syb1,sym1,sye1,vtyb1,vtym1,vtye1,vdyb1,vdym1,vdye1
      real szb1,szm1,sze1,vtzb1,vtzm1,vtze1,vdzb1,vdzm1,vdze1
      real tm,dm,te,de,zero
      integer iprime,ii
      zero=0.0
      ii=1
      iprime=0
      sigyb(1)=sigyb_in
      sigzb(1)=sigzb_in
      zpb(1)=zpuff
c --- The vendor leaves the sigma-z virtuals untouched for a puff that is not
c     Gaussian in the vertical, so they are undefined (stale) in that case; the
c     harness pre-zeroes them to make the comparison well defined.
      vtzb1=0.0
      vtzm1=0.0
      vtze1=0.0
      vdzb1=0.0
      vdzm1=0.0
      vdze1=0.0
"""

SIGMA_HARNESS_FOOTER = """      syb1_o=syb1
      sym1_o=sym1
      sye1_o=sye1
      vtyb1_o=vtyb1
      vtym1_o=vtym1
      vtye1_o=vtye1
      vdyb1_o=vdyb1
      vdym1_o=vdym1
      vdye1_o=vdye1
      szb1_o=szb1
      szm1_o=szm1
      sze1_o=sze1
      vtzb1_o=vtzb1
      vtzm1_o=vtzm1
      vtze1_o=vtze1
      vdzb1_o=vdzb1
      vdzm1_o=vdzm1
      vdze1_o=vdze1
      return
      end
"""

SIGMA_Y_HARNESS_HEADER = """c-----------------------------------------------------------------------
      subroutine p7q_sigma_y(syb1io,sym1io,sye1io,bidfnl_in,sy0sq,lcalm,
     &                       sysq_o,sigyb_o,sy0_o)
c-----------------------------------------------------------------------
c --- GENERATED HARNESS (not vendor source). It wraps the VERBATIM SETPUF
c     sigma-y adjustment statements extracted by
c     reference/p7q_source_anchor.py.
      include 'params.puf'
      include 'puff.puf'
      real syb1io,sym1io,sye1io,bidfnl_in,sy0sq,sysq_o,sigyb_o,sy0_o
      logical lcalm
      real syb1,sym1,sye1,sysq,zero
      integer ii
      zero=0.0
      ii=1
      syb1=syb1io
      sym1=sym1io
      sye1=sye1io
      bidfnl(1)=bidfnl_in
      sy0(1)=0.0
"""

SIGMA_Y_HARNESS_FOOTER = """      syb1io=syb1
      sym1io=sym1
      sye1io=sye1
      sysq_o=sysq
      sigyb_o=sigyb(1)
      sy0_o=sy0(1)
      return
      end
"""

SIGMA_Z_HARNESS_HEADER = """c-----------------------------------------------------------------------
      subroutine p7q_sigma_z(szb1io,szm1io,sze1io,bidfnl_in,lcalm,
     &                       sigzb_o,sz0_o)
c-----------------------------------------------------------------------
c --- GENERATED HARNESS (not vendor source). It wraps the VERBATIM SETPUF
c     sigma-z adjustment statements extracted by
c     reference/p7q_source_anchor.py.
      include 'params.puf'
      include 'puff.puf'
      real szb1io,szm1io,sze1io,bidfnl_in,sigzb_o,sz0_o
      logical lcalm
      real szb1,szm1,sze1
      integer ii
      ii=1
      szb1=szb1io
      szm1=szm1io
      sze1=sze1io
      bidfnl(1)=bidfnl_in
      sz0(1)=0.0
"""

SIGMA_Z_HARNESS_FOOTER = """      szb1io=szb1
      szm1io=szm1
      sze1io=sze1
      sigzb_o=sigzb(1)
      sz0_o=sz0(1)
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


def locate_inline(lines: list[str], owner: dict[int, str], spec: dict) -> tuple[int, int]:
    starts = [index for index, line in enumerate(lines)
              if re.match(spec["start"], line) and owner[index] == spec["enclosing"]]
    if len(starts) != 1:
        raise SystemExit(f"P7Q: inline block {spec['name']} has {len(starts)} starts inside "
                         f"{spec['enclosing']}, expected one")
    start = starts[0]
    ends = [index for index, line in enumerate(lines)
            if index > start and re.match(spec["end"], line) and owner[index] == spec["enclosing"]]
    if len(ends) < spec["end_count"]:
        raise SystemExit(f"P7Q: inline block {spec['name']} has only {len(ends)} end anchors")
    return start, ends[spec["end_count"] - 1]


def extract(vendor: pathlib.Path) -> tuple[dict, dict[str, str]]:
    raw = (vendor / VENDOR_SOURCE).read_bytes()
    lines = raw.decode("latin-1").splitlines()
    found = headers(lines)
    owner = enclosing_units(lines)

    inline: dict[str, dict] = {}
    spans: dict[str, str] = {}
    headers_by_name = {
        "setpuf_sigma": (SIGMA_HARNESS_HEADER, SIGMA_HARNESS_FOOTER, "inline_sigma"),
        "setpuf_sigma_y": (SIGMA_Y_HARNESS_HEADER, SIGMA_Y_HARNESS_FOOTER, "inline_sigma_y"),
        "setpuf_sigma_z": (SIGMA_Z_HARNESS_HEADER, SIGMA_Z_HARNESS_FOOTER, "inline_sigma_z"),
    }
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
        harness_header, harness_footer, key = headers_by_name[spec["name"]]
        spans[key] = harness_header + block + harness_footer

    pinned: list[dict] = []
    for unit, statement in PINNED_STATEMENTS:
        matches = [index for index, line in enumerate(lines)
                   if line.strip() == statement.strip() and owner[index] == unit]
        if len(matches) != 1:
            raise SystemExit(f"P7Q: statement {statement!r} is not unique inside {unit}")
        pinned.append({"unit": unit, "line": matches[0] + 1, "statement": statement.strip()})

    manifest = {
        "gate": "P7Q_SETPUF_SIGMA_SOURCE_ANCHOR",
        "vendor_source": VENDOR_SOURCE,
        "vendor_source_sha256": sha256_bytes(raw),
        "located_by": "content anchors confined to the enclosing unit",
        "inline": inline,
        "pinned_statements": pinned,
        "harness_sha256": {key: sha256_bytes(spans[key].encode("latin-1"))
                           for key in ("inline_sigma", "inline_sigma_y", "inline_sigma_z")},
        "ported": {"setpuf_sigma": True, "setpuf_sigma_y": True, "setpuf_sigma_z": True},
        "not_ported": ["WAKE_TAB (PRIME wake branch)", "walltrap (MCTADJ=2 valley)",
                       "ctadj2 (MCTADJ=2 strain)", "HEFTRAN (MHFTSZ=1)",
                       "the PRIME cavity/tabulated branches of SETPUF"],
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
    (output / "vendor_inline_sigma.f").write_bytes(spans["inline_sigma"].encode("latin-1"))
    (output / "vendor_inline_sigma_y.f").write_bytes(spans["inline_sigma_y"].encode("latin-1"))
    (output / "vendor_inline_sigma_z.f").write_bytes(spans["inline_sigma_z"].encode("latin-1"))
    driver = pathlib.Path(__file__).with_name("p7q_oracle_driver.f")
    shutil.copy2(driver, output / driver.name)
    for include in manifest["vendor_include_sha256"]:
        shutil.copy2(vendor / include, output / include)
    (output / "p7q_source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


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
        print(f"P7Q_SOURCE_STAGE={args.stage}")
    if args.check:
        pinned = json.loads(args.check.read_text())
        if pinned != manifest:
            raise SystemExit("P7Q sigma-update source drift: re-audit before trusting the oracle")
        print("P7Q_SOURCE_ANCHOR=PASS inline=" + ",".join(sorted(manifest["inline"])))
    print("P7Q_VENDOR_SHA256=" + manifest["vendor_source_sha256"])
    for name, info in manifest["inline"].items():
        print(f"P7Q_INLINE {name} lines={info['first_line']}-{info['last_line']} "
              f"sha256={info['sha256']}")
    for entry in manifest["pinned_statements"]:
        print(f"P7Q_PINNED {entry['unit']} line={entry['line']} statement={entry['statement']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

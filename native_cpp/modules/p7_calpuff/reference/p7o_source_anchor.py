#!/usr/bin/env python3
"""P7O: pin the CALPUFF release-scheduler units of the vendor source.

The release scheduler of the locked deck's constant point source lives in
`points1`: the number of puffs released per hour and their emission duration, the
release-time state of each new puff, and (in the routine `INJECT`) the initial
mass split between the mixed layer and the layer above. Two of those pieces are
*inline* in `points1`, so they are pinned by content within their enclosing unit
and staged inside generated harness subroutines that add only declarations and the
argument transfer: the extracted statements stay byte-identical.

The manifest also records the puff-age semantics with their exact line numbers:
`SWAP(i,0)` zeroes `TMTOTB` at release and `SETPUF` increments it by TSAMP every
step, so the age chain is machine-checked even though `SETPUF`'s state update is
not part of this round.

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

UNITS = ("inject",)

# Inline blocks, each anchored by content and confined to one enclosing unit.
INLINE_BLOCKS = (
    {
        "name": "points1_cadence",
        "enclosing": "points1",
        "start": r"^      npnew=wsnew\*xtmp1\(md\)\+1\s*$",
        "end": r"^      dt=dthr/float\(npnew\)\s*$",
    },
    {
        "name": "points1_release_state",
        "enclosing": "points1",
        "start": r"^         xpb\(np\)=xpt1grd\(i\)\s*$",
        "end": r"^         isrctyp\(np\)=itype\s*$",
    },
)

# Puff-age semantics: (unit, exact statement) pairs, verified by line.
AGE_STATEMENTS = (
    ("swap", "tmtotb(i)    =zero"),
    ("setpuf", "tmtotb(ii)=tmtotb(ii)+tsamp"),
)

END_KEYWORDS = {"do", "if", "where", "select", "selectcase", "type", "block", "module", "program",
                "subroutine", "function", "associate", "forall", "critical", "enum", "interface",
                "team", "parallel"}
HEADER = re.compile(r"^\s{0,6}(?:real|integer|logical|double\s+precision)?\s*"
                    r"(?:function|subroutine)\s+([a-z0-9_]+)\s*\(?", re.IGNORECASE)
TERMINATOR = re.compile(r"^      end(?![a-zA-Z])\s*(\S.*)?$", re.IGNORECASE)

CADENCE_HARNESS_HEADER = """c-----------------------------------------------------------------------
      subroutine p7o_cadence(wsn,xt1,mxn,dhr,npn,dto,npt)
c-----------------------------------------------------------------------
c --- GENERATED HARNESS (not vendor source). It wraps the VERBATIM POINTS1
c     release-cadence statements extracted by reference/p7o_source_anchor.py.
      real wsn,xt1,dhr,dto
      integer mxn,npn,npt
      real wsnew,dthr,xtmp1(1),dt
      integer md,mxnew,npnew,newpt1(1),i,newpuf,npuffs,mxpuff,np
      logical lcav,lprm
      external rolldn
      md=1
      xtmp1(1)=xt1
      wsnew=wsn
      mxnew=mxn
      dthr=dhr
      i=1
      newpuf=0
      npuffs=0
      mxpuff=1000000
      np=0
      lcav=.FALSE.
      lprm=.FALSE.
"""

CADENCE_HARNESS_FOOTER = """      npn=npnew
      dto=dt
      npt=newpt1(1)
      return
      end
"""

RELEASE_STATE_HARNESS_HEADER = """c-----------------------------------------------------------------------
      subroutine p7o_release_state(vin)
c-----------------------------------------------------------------------
c --- GENERATED HARNESS (not vendor source). It wraps the VERBATIM POINTS1
c     release-time puff-state statements extracted by
c     reference/p7o_source_anchor.py. The results are read back from /PUFF/.
c     v(1..39) = xpt1grd ypt1grd elstak sysrc szsrc heff xf bidsq fluxb fluxm
c                xfinb xfinm zfinb zfinm tipdw htstak exitw diam dt ws istab
c                sqrts iru tsigv tsigw el plx idw hb hw heff2 zly rinit
c                xshift syini szini j i itype
      include 'params.puf'
      include 'puff.puf'
      include 'slug.puf'
      real vin(39)
      real xpt1grd(1),ypt1grd(1),elstak(1),htstak(1),exitw(1),diam(1)
      real sysrc,szsrc,heff,xf,bidsq,fluxb,fluxm,xfinb,xfinm,zfinb,zfinm
      real tipdw,dt,ws,tsigv,tsigw,el,plx,hb,hw,heff2,zly,rinit,xshift
      real syini,szini
      real sqrts
      integer istab,iru,idw,j,i,itype,np
      xpt1grd(1)=vin(1)
      ypt1grd(1)=vin(2)
      elstak(1)=vin(3)
      sysrc=vin(4)
      szsrc=vin(5)
      heff=vin(6)
      xf=vin(7)
      bidsq=vin(8)
      fluxb=vin(9)
      fluxm=vin(10)
      xfinb=vin(11)
      xfinm=vin(12)
      zfinb=vin(13)
      zfinm=vin(14)
      tipdw=vin(15)
      htstak(1)=vin(16)
      exitw(1)=vin(17)
      diam(1)=vin(18)
      dt=vin(19)
      ws=vin(20)
      istab=INT(vin(21))
      sqrts=vin(22)
      iru=INT(vin(23))
      tsigv=vin(24)
      tsigw=vin(25)
      el=vin(26)
      plx=vin(27)
      idw=INT(vin(28))
      hb=vin(29)
      hw=vin(30)
      heff2=vin(31)
      zly=vin(32)
      rinit=vin(33)
      xshift=vin(34)
      syini=vin(35)
      szini=vin(36)
      j=INT(vin(37))
      i=INT(vin(38))
      itype=INT(vin(39))
      np=1
"""

RELEASE_STATE_HARNESS_FOOTER = """      return
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
        raise SystemExit(f"P7O: unit {name} has {len(hits)} header matches, expected one")
    start = hits[0]
    for index in range(start + 1, len(lines)):
        match = TERMINATOR.match(lines[index])
        if not match:
            continue
        remainder = (match.group(1) or "").strip().split()
        if remainder and remainder[0].lower() in END_KEYWORDS:
            continue
        return start, index
    raise SystemExit(f"P7O: unit {name} has no terminator")


def locate_inline(lines: list[str], owner: dict[int, str], spec: dict) -> tuple[int, int]:
    starts = [index for index, line in enumerate(lines) if re.match(spec["start"], line)]
    ends = [index for index, line in enumerate(lines) if re.match(spec["end"], line)]
    starts = [index for index in starts if owner[index] == spec["enclosing"]]
    if len(starts) != 1:
        raise SystemExit(f"P7O: inline block {spec['name']} has {len(starts)} starts inside "
                         f"{spec['enclosing']}, expected one")
    start = starts[0]
    # The end anchor may legitimately occur again later in the same unit (the
    # PRIME cavity block repeats the identity statements); the first one after
    # the start delimits this block.
    following = [index for index in ends if index > start and owner[index] == spec["enclosing"]]
    if not following:
        raise SystemExit(f"P7O: inline block {spec['name']} has no end anchor after its start")
    return start, min(following)


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
        if spec["name"] == "points1_cadence":
            spans["inline_cadence"] = CADENCE_HARNESS_HEADER + block + CADENCE_HARNESS_FOOTER
        else:
            spans["inline_release_state"] = (RELEASE_STATE_HARNESS_HEADER + block +
                                             RELEASE_STATE_HARNESS_FOOTER)

    age: list[dict] = []
    for unit, statement in AGE_STATEMENTS:
        matches = [index for index, line in enumerate(lines)
                   if line.strip() == statement.strip() and owner[index] == unit]
        if len(matches) != 1:
            raise SystemExit(f"P7O: age statement {statement!r} is not unique inside {unit}")
        age.append({"unit": unit, "line": matches[0] + 1, "statement": statement.strip()})

    manifest = {
        "gate": "P7O_RELEASE_SCHEDULER_SOURCE_ANCHOR",
        "vendor_source": VENDOR_SOURCE,
        "vendor_source_sha256": sha256_bytes(raw),
        "located_by": "routine-header scan plus content anchors confined to the enclosing unit",
        "units": units,
        "inline": inline,
        "puff_age": {
            "statements": age,
            "note": ("SWAP(i,0) zeroes TMTOTB when a puff is created (release age 0) and SETPUF "
                     "adds TSAMP every step, so the age of a puff released during the current "
                     "step is 0 and grows by the sampling step. SETPUF's full state update "
                     "(distances, sigmas, rise table, gravitational settling) is NOT part of "
                     "this round."),
        },
        "harness_sha256": {
            "inline_cadence": sha256_bytes(spans["inline_cadence"].encode("latin-1")),
            "inline_release_state": sha256_bytes(spans["inline_release_state"].encode("latin-1")),
        },
        "ported": {"inject": True, "points1_cadence": True, "points1_release_state": True,
                   "puff_age_rule": True},
        "not_ported": ["setpuf", "swap", "rolldn", "rlsmet", "inject2", "ptlaps"],
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
    (output / "vendor_inline_cadence.f").write_bytes(spans["inline_cadence"].encode("latin-1"))
    (output / "vendor_inline_release_state.f").write_bytes(
        spans["inline_release_state"].encode("latin-1"))
    driver = pathlib.Path(__file__).with_name("p7o_oracle_driver.f")
    shutil.copy2(driver, output / driver.name)
    for include in manifest["vendor_include_sha256"]:
        shutil.copy2(vendor / include, output / include)
    (output / "p7o_source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


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
        print(f"P7O_SOURCE_STAGE={args.stage}")
    if args.check:
        pinned = json.loads(args.check.read_text())
        if pinned != manifest:
            raise SystemExit("P7O release-scheduler source drift: re-audit before trusting the "
                             "oracle")
        print("P7O_SOURCE_ANCHOR=PASS units=" + ",".join(sorted(manifest["units"])) + " inline=" +
              ",".join(sorted(manifest["inline"])))
    print("P7O_VENDOR_SHA256=" + manifest["vendor_source_sha256"])
    for name, info in manifest["units"].items():
        print(f"P7O_UNIT {name:7s} lines={info['first_line']}-{info['last_line']} "
              f"sha256={info['sha256']}")
    for name, info in manifest["inline"].items():
        print(f"P7O_INLINE {name} lines={info['first_line']}-{info['last_line']} "
              f"sha256={info['sha256']}")
    for entry in manifest["puff_age"]["statements"]:
        print(f"P7O_AGE {entry['unit']} line={entry['line']} statement={entry['statement']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

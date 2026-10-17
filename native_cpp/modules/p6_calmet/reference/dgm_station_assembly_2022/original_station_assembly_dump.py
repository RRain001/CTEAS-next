#!/usr/bin/env python3
"""Original CALMET 6.5.0 station-assembly dump (write-only) — DGM round 4.

P6D's round-17 request (PR #23) is: for hours 17, 18, 41, 42, 47, 48 dump

    (a) the surface station column as it enters the analysis, and
        `US(1,1)/VS(1,1)` after DIAGI's anemometer-to-`ZMID(1)` adjustment,
    (b) `UDAT/VDAT` after `RDUPN` for all nine levels,
    (c) `UG/VG` at the existing kpt 8,

so that the surface observation assembly, the upper-air low-level interpolation
and the analysis weights can be separated. Level 1 is the observed surface wind,
so no SIMILT is involved there and the EL/ZII tables cannot move it; the two
level-1 fields differ in *spatial pattern* (station cell agreement ~1.2e-04,
worst cell 1.567e-03).

This tool implements (a) and (b) as **write-only** dumps of the unmodified
original; (c) is served by slicing the existing round-2 fields dump
(`native_cpp/modules/p6_calmet/reference/dgm_p6d_requests_2022/`). The
instrumented run must reproduce `MET.DAT` byte for byte.

Three insertion points:

    kpt=1  PREPDI  L13906  after the surface observations are converted to U/V
                           (the column as it enters the analysis; only level 1
                           is populated, the rest carry the EDIT missing value)
    kpt=2  DIAGNO  L5958   after the per-station loop (the adjusted column:
                           the similarity-theory profile fills levels 1..nz)
    kpt=3  COMP    L4392   after the AA VERTAV/FACET block: the RDUPN AA/BB
                           sounding columns and the VERTAV nine-level averages

Array index order is recorded per field, because it is the trap P6D hit on
`STDAT1(K,L)`: the `/UPMET/` sounding arrays are **station-major**
(`uaa(mxus,mxlev)`, element `(iu,k)`), while `VERTAV`'s outputs and `/D1/`'s
`US/VS` are **level-major** (`uaveaa(mxnz,mxus)`, element `(k,iu)`).

Record layout (little endian, fixed 2112 bytes):

    int32[16]   kpt, packed YYYYJJJHH, seconds, nssta, nusta, npsta, nz,
                nlaa, nlbb, nsurf, iu, l, spare*4
    float32[512] slot table in FLOAT_TABLE below
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path

# --- pinned provenance -----------------------------------------------------
ORIGINAL_CALMET_SHA256 = "430381b4fb87f15127e20b13cc3e99be8a0e0fccf1d5821110af7f980558d134"
ORIGINAL_CALUTILS_SHA256 = "1e1fbad6444dcebbcaefed3f5f9a65e5ab0569d45fdf12ea973ca613b8d7cad1"
TARGET_MET_DAT_SHA256 = "b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30"
MET_INP_SHA256 = "94b6d34639abb3f54719577298c49b6939c9c6eec5b3755c79dddfaa01edc671"

COMMON_FFLAGS = ("-std=legacy", "-ffixed-line-length-none", "-fno-automatic",
                 "-fno-align-commons", "-fallow-argument-mismatch", "-O0")

# point -> (vendor line, that line, the line before it, the line after it)
ANCHORS = {
    1: (13906, "10    continue",
        "      end if",
        "c"),
    2: (5958, "   70 CONTINUE",
        "      END IF",
        "   91 CONTINUE"),
    3: (4392, "      endif",
        "         call facet(iu,tzaa,zlaa,nlaa,nzp1,zface,tzgraa(1,iu))",
        ""),
    4: (4423, "c ---    beta2 is defined but never used  (remove from calling list 070113) ",
        "      if (noobs.ne.2)then",
        "         call prepdi(ws,wd,tempk,uaveaa,uavebb,vaveaa,vavebb,"),
}

CALLS = {
    1: "      call dgmsurfin(us,vs)\n",
    2: "      call dgmsurfadj()\n",
    3: "      call dgmsound(uaveaa,uavebb,vaveaa,vavebb,iu)\n",
    4: "         call dgmsoundhr(uaveaa,uavebb,vaveaa,vavebb)\n",
}

WHEN = {
    1: "PREPDI: the surface station column as it enters the analysis (level 1 "
       "only; the rest are the EDIT missing value)",
    2: "DIAGNO: the same column after the per-station anemometer-to-ZMID(1) "
       "adjustment / similarity-theory extrapolation",
    3: "COMP: the RDUPN AA/BB sounding columns and the VERTAV nine-level "
       "averages (fires only when a new sounding is read)",
    4: "COMP: immediately before the PREPDI call - the same columns as the "
       "analysis consumes them this hour (fires every hour)",
}

INT_TABLE = [
    ("kpt", 1, "record type: 1 entering column, 2 adjusted column, 3 soundings "
               "after a new RDUPN read, 4 soundings as PREPDI consumes them"),
    ("packed", 2, "current timestep beginning time, packed YYYYJJJHH "
                  "(/GEN/ ndathrb)"),
    ("seconds", 3, "current timestep beginning seconds (/GEN/ nsecb)"),
    ("nssta", 4, "number of surface stations"),
    ("nusta", 5, "number of upper-air stations"),
    ("npsta", 6, "number of precipitation stations"),
    ("nz", 7, "number of model layers"),
    ("nlaa", 8, "AA sounding level count (kpt=3)"),
    ("nlbb", 9, "BB sounding level count (kpt=3)"),
    ("nsurf", 10, "nssta + nowsta (kpt=2)"),
    ("iu", 11, "upper-air station index of the dump (kpt=3)"),
    ("l", 12, "surface station index of the dump (kpt=1,2)"),
    ("justa", 13, "kpt=4: /UPMET/ justa(1), the AA/BB ordering flag; 0 else"),
    ("ntzaa", 14, "kpt=4: /UPMET/ ntzaa(1), the AA sounding time YYYYJJJHH"),
    ("ntzbb", 15, "kpt=4: /UPMET/ ntzbb(1), the BB sounding time YYYYJJJHH"),
    ("jusdt", 16, "kpt=4: /UPMET/ jusdt(1), the AA/BB separation in seconds"),
]

FLOAT_TABLE = [
    ("US_ENTER_1..nz", 0, "m/s", "kpt=1: /D1/ US(k,1) as PREPDI leaves it - the "
                                "observed surface wind at anemometer height at "
                                "k=1, EDIT (missing) above; level-major (k, station)"),
    ("VS_ENTER_1..nz", 9, "m/s", "kpt=1: the V counterpart"),
    ("US_ADJUSTED_1..nz", 18, "m/s", "kpt=2: /D1/ US(k,1) after the station loop "
                                     "(anemometer-to-ZMID(1) / similarity profile)"),
    ("VS_ADJUSTED_1..nz", 27, "m/s", "kpt=2: the V counterpart"),
    ("ZLAA_1..99", 36, "m", "kpt=3: /UPMET/ zlaa(iu,k) - AA sounding heights "
                            "(station-major array: element (iu,k))"),
    ("UAA_1..99", 135, "m/s", "kpt=3: /UPMET/ uaa(iu,k) - AA sounding U"),
    ("VAA_1..99", 234, "m/s", "kpt=3: /UPMET/ vaa(iu,k) - AA sounding V"),
    ("ZLBB_1..99", 333, "m", "kpt=3: /UPMET/ zlbb(iu,k) - BB sounding heights"),
    ("UBB_1..99", 432, "m/s", "kpt=3: /UPMET/ ubb(iu,k) - BB sounding U"),
    ("VBB_1..99", 531, "m/s", "kpt=3: /UPMET/ vbb(iu,k) - BB sounding V"),
    ("UAVERAA_1..nz", 630, "m/s", "kpt=3: VERTAV output uaveaa(k,iu) - the AA "
                                  "sounding averaged over each model layer; "
                                  "level-major (k, station)"),
    ("VAVERAA_1..nz", 639, "m/s", "kpt=3: VERTAV output vaveaa(k,iu)"),
    ("UAVERBB_1..nz", 648, "m/s", "kpt=3: VERTAV output uavebb(k,iu)"),
    ("VAVERBB_1..nz", 657, "m/s", "kpt=3: VERTAV output vavebb(k,iu)"),
    ("spare_666..1023", 666, "0", "reserved, always 0"),
]

INT_SLOTS, FLOAT_SLOTS = 16, 1024
RECORD_BYTES = 4 * (INT_SLOTS + FLOAT_SLOTS)

HELPERS = """
c ---------------------------------------------------------------------
c --- DGM TRACK ROUND 4 (P6D request): write-only dump of the station
c --- observation assembly and the upper-air columns. Present only in the
c --- temporary instrumented copy; the vendor tree is untouched.
c --- Record layout is documented in
c --- native_cpp/modules/p6_calmet/reference/dgm_station_assembly_2022/
c --- original_station_assembly_dump.py
c ---------------------------------------------------------------------
      subroutine dgmsurfin(us,vs)
c --- PREPDI: the surface column as it enters the analysis
      include 'params.met'
      real us(mxnz,mxwnd),vs(mxnz,mxwnd)
      include 'gen.met'
      include 'grid.met'
      include 'met1.met'
      common /dgmrec/ irec(16), rrec(1024)
      common /dgmlog/ ldgm
      logical ldgm
      integer k
      if(.not.ldgm)then
         open(94,file='dgm_station.bin',form='unformatted',
     1        access='stream',status='replace')
         ldgm=.true.
      endif
      do 10 k=1,1024
         rrec(k)=0.0
   10 continue
      do 20 k=1,16
         irec(k)=0
   20 continue
      irec(1)=1
      irec(2)=ndathrb
      irec(3)=nsecb
      irec(4)=nssta
      irec(5)=nusta
      irec(6)=npsta
      irec(7)=nz
      irec(12)=1
      do 30 k=1,nz
         rrec(k)=us(k,1)
         rrec(9+k)=vs(k,1)
   30 continue
      write(94) irec
      write(94) rrec
      return
      end

      subroutine dgmsurfadj()
c --- DIAGNO: the same column after the anemometer-to-ZMID(1) adjustment
      include 'params.met'
      include 'gen.met'
      include 'grid.met'
      include 'met1.met'
      include 'd1.met'
      common /dgmrec/ irec(16), rrec(1024)
      common /dgmlog/ ldgm
      logical ldgm
      integer k
      if(.not.ldgm)then
         open(94,file='dgm_station.bin',form='unformatted',
     1        access='stream',status='replace')
         ldgm=.true.
      endif
      do 10 k=1,1024
         rrec(k)=0.0
   10 continue
      do 20 k=1,16
         irec(k)=0
   20 continue
      irec(1)=2
      irec(2)=ndathrb
      irec(3)=nsecb
      irec(4)=nssta
      irec(5)=nusta
      irec(6)=npsta
      irec(7)=nz
      irec(10)=nssta
      irec(12)=1
      do 30 k=1,nz
         rrec(18+k)=us(k,1)
         rrec(27+k)=vs(k,1)
   30 continue
      write(94) irec
      write(94) rrec
      return
      end

      subroutine dgmsound(uaveaa,uavebb,vaveaa,vavebb,iu)
c --- COMP: the RDUPN AA/BB columns and the VERTAV nine-level averages
      include 'params.met'
      real uaveaa(mxnz,mxus),uavebb(mxnz,mxus)
      real vaveaa(mxnz,mxus),vavebb(mxnz,mxus)
      integer iu
      include 'gen.met'
      include 'grid.met'
      include 'upmet.met'
      common /dgmrec/ irec(16), rrec(1024)
      common /dgmlog/ ldgm
      logical ldgm
      integer k
      if(.not.ldgm)then
         open(94,file='dgm_station.bin',form='unformatted',
     1        access='stream',status='replace')
         ldgm=.true.
      endif
      do 10 k=1,1024
         rrec(k)=0.0
   10 continue
      do 20 k=1,16
         irec(k)=0
   20 continue
      irec(1)=3
      irec(2)=ndathrb
      irec(3)=nsecb
      irec(4)=nssta
      irec(5)=nusta
      irec(6)=npsta
      irec(7)=nz
      irec(8)=nlaa(iu)
      irec(9)=nlbb(iu)
      irec(11)=iu
      do 30 k=1,mxlev
         rrec(36+k)=zlaa(iu,k)
         rrec(135+k)=uaa(iu,k)
         rrec(234+k)=vaa(iu,k)
         rrec(333+k)=zlbb(iu,k)
         rrec(432+k)=ubb(iu,k)
         rrec(531+k)=vbb(iu,k)
   30 continue
      do 40 k=1,nz
         rrec(630+k)=uaveaa(k,iu)
         rrec(639+k)=vaveaa(k,iu)
         rrec(648+k)=uavebb(k,iu)
         rrec(657+k)=vavebb(k,iu)
   40 continue
      write(94) irec
      write(94) rrec
      return
      end

      subroutine dgmsoundhr(uaveaa,uavebb,vaveaa,vavebb)
c --- COMP: the upper-air columns as the analysis consumes them this hour
      include 'params.met'
      real uaveaa(mxnz,mxus),uavebb(mxnz,mxus)
      real vaveaa(mxnz,mxus),vavebb(mxnz,mxus)
      include 'gen.met'
      include 'grid.met'
      include 'upmet.met'
      common /dgmrec/ irec(16), rrec(1024)
      common /dgmlog/ ldgm
      logical ldgm
      integer k
      if(.not.ldgm)then
         open(94,file='dgm_station.bin',form='unformatted',
     1        access='stream',status='replace')
         ldgm=.true.
      endif
      do 10 k=1,1024
         rrec(k)=0.0
   10 continue
      do 20 k=1,16
         irec(k)=0
   20 continue
      irec(1)=4
      irec(2)=ndathrb
      irec(3)=nsecb
      irec(4)=nssta
      irec(5)=nusta
      irec(6)=npsta
      irec(7)=nz
      irec(8)=nlaa(1)
      irec(9)=nlbb(1)
      irec(11)=1
      irec(13)=justa(1)
      irec(14)=ntzaa(1)
      irec(15)=ntzbb(1)
      irec(16)=jusdt(1)
      do 30 k=1,mxlev
         rrec(36+k)=zlaa(1,k)
         rrec(135+k)=uaa(1,k)
         rrec(234+k)=vaa(1,k)
         rrec(333+k)=zlbb(1,k)
         rrec(432+k)=ubb(1,k)
         rrec(531+k)=vbb(1,k)
   30 continue
      do 40 k=1,nz
         rrec(630+k)=uaveaa(k,1)
         rrec(639+k)=vaveaa(k,1)
         rrec(648+k)=uavebb(k,1)
         rrec(657+k)=vavebb(k,1)
   40 continue
      write(94) irec
      write(94) rrec
      return
      end
"""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def instrument(vendor_dir: Path, out_dir: Path) -> dict:
    source = vendor_dir / "calmet.for"
    actual = sha256_file(source)
    if actual != ORIGINAL_CALMET_SHA256:
        raise SystemExit(f"vendor calmet.for SHA256 drift: {actual}")
    calutils = vendor_dir / "calutils.for"
    calutils_actual = sha256_file(calutils)
    if calutils_actual != ORIGINAL_CALUTILS_SHA256:
        raise SystemExit(f"vendor calutils.for SHA256 drift: {calutils_actual}")

    lines = source.read_text(encoding="latin-1").splitlines(keepends=True)
    for kpt, (line_no, expected, before, after) in ANCHORS.items():
        got = lines[line_no - 1].rstrip("\r\n")
        prev = lines[line_no - 2].rstrip("\r\n") if line_no > 1 else ""
        nxt = lines[line_no].rstrip("\r\n") if line_no < len(lines) else ""
        if got != expected or prev != before or nxt != after:
            raise SystemExit(
                f"anchor drift at kpt {kpt} line {line_no}: got {got!r} "
                f"between {prev!r} and {nxt!r}")

    insertions = {}
    for kpt, (line_no, *_rest) in ANCHORS.items():
        insertions[line_no] = (
            f"c --- DGM write-only station-assembly dump (kpt {kpt}: "
            f"{WHEN[kpt]})\n" + CALLS[kpt])

    body = "".join(line + insertions.get(index, "")
                   for index, line in enumerate(lines, 1))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "calmet_instrumented.for"
    target.write_text(body + HELPERS, encoding="latin-1")

    segments = {
        "prepdi_station_conversion": (13868, 13907),
        "diagno_station_loop": (5797, 5959),
        "comp_vertav_aa": (4379, 4393),
        "comp_prepdi_call": (4416, 4427),
    }
    report = {
        "status": "ORIGINAL_CALMET_WRITE_ONLY_STATION_ASSEMBLY_INSTRUMENTED",
        "why": ("P6D's round-17 request: separate the surface observation "
                "assembly, the upper-air low-level interpolation and the "
                "analysis weights; level 1 of U/V is the observed surface wind "
                "and CALMET.DAT exposes only the analysed result"),
        "request_source": ("P6D PR #23, round 17 (Instrumentation request, DGM "
                           "format)"),
        "no_vendor_source_edits": True,
        "vendor_source_sha256": {"calmet.for": actual,
                                 "calutils.for": calutils_actual},
        "instrumented_sha256": {
            "calmet_instrumented.for": sha256_file(target)},
        "helper_subroutines": {
            "DGMSURFIN, DGMSURFADJ, DGMSOUND": {
                "vendor_lines": len(lines) + 1,
                "sha256": sha256_bytes(HELPERS.encode("latin-1")),
                "unit": 94,
                "output_file": "dgm_station.bin",
                "record_bytes": RECORD_BYTES,
                "writes_only": True,
            },
        },
        "points": [
            {
                "kpt": kpt,
                "vendor_line": line_no,
                "when": WHEN[kpt],
                "inserted_text_sha256": sha256_bytes(
                    insertions[line_no].encode("latin-1")),
            }
            for kpt, (line_no, *_rest) in sorted(ANCHORS.items())
        ],
        "source_segments": {
            name: {"vendor_lines": [first, last],
                   "sha256": sha256_bytes(
                       "".join(lines[first - 1:last]).encode("latin-1"))}
            for name, (first, last) in segments.items()
        },
        "record_layout": {
            "header": "int32[16]",
            "payload": "float32[512]",
            "record_bytes": RECORD_BYTES,
            "header_dtype": "int32 little endian",
            "field_dtype": "float32 little endian",
            "ints": [name for name, _s, _m in INT_TABLE],
            "float_slots": [name for name, _s, _u, _m in FLOAT_TABLE],
        },
        "index_order": {
            "UPMET sounding arrays": "station-major: uaa(mxus,mxlev), element "
                                     "(iu,k) - level varies fastest",
            "VERTAV outputs": "level-major: uaveaa(mxnz,mxus), element (k,iu) - "
                              "station varies fastest",
            "D1 US/VS": "level-major: us(mxnz,mxwnd), element (k,l)",
        },
    }
    (out_dir / "dgm-instrumentation.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


def _build(compiler: str, source: Path, include_dir: Path,
           target: Path) -> list[str]:
    command = [compiler, *COMMON_FFLAGS, f"-I{include_dir}", str(source),
               "-o", str(target)]
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    subprocess.run(command, check=True, cwd=str(target.parent))
    target.chmod(0o755)
    return command


def _alias_tree(vendor_dir: Path, alias_dir: Path) -> Path:
    alias_dir.mkdir(parents=True, exist_ok=True)
    for item in vendor_dir.iterdir():
        if not item.is_file():
            continue
        link = alias_dir / item.name.lower()
        if not link.exists():
            link.symlink_to(item)
    return alias_dir


def _stage_case(case_dir: Path, root: Path) -> dict:
    mapping = {
        "geo/makegeo/geo.dat": case_dir / "geo/makegeo/geo.dat",
        "met/surface/final/surf.dat": case_dir / "met/surface/final/surf.dat",
        "met/upperair/final/up_58424.dat":
            case_dir / "met/upperair/final/up_58424.dat",
        "run/met/met.inp": case_dir / "run/met/met.inp",
    }
    staged = {}
    for relative, source in mapping.items():
        if not source.is_file():
            raise SystemExit(f"missing frozen case input: {source}")
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        staged[relative] = {"sha256": sha256_file(source),
                            "bytes": source.stat().st_size}
    if staged["run/met/met.inp"]["sha256"] != MET_INP_SHA256:
        raise SystemExit("met.inp SHA256 drift")
    return staged


def _run(binary: Path, run_dir: Path) -> dict:
    meta = run_dir / "met.dat"
    for stale in (meta, run_dir / "met.lst", run_dir / "met_runtime.log",
                  run_dir / "dgm_station.bin"):
        if stale.exists():
            stale.unlink()
    log = run_dir / "met_runtime.log"
    with log.open("w") as handle:
        proc = subprocess.run([str(binary), "met.inp"], cwd=str(run_dir),
                              stdout=handle, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        raise SystemExit(f"met.x failed with {proc.returncode}; see {log}")
    if not meta.is_file():
        raise SystemExit(f"met.x produced no met.dat; see {log}")
    return {"command": [str(binary), "met.inp"], "cwd": str(run_dir),
            "returncode": proc.returncode,
            "met_dat_sha256": sha256_file(meta),
            "met_dat_bytes": meta.stat().st_size}


def audit(args: argparse.Namespace) -> dict:
    vendor = args.vendor.resolve()
    case = args.case.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    instrumentation = instrument(vendor, out)
    alias = _alias_tree(vendor, out / "include-alias")

    original_x = out / "bin" / "met-original.x"
    instrumented_x = out / "bin" / "met-instrumented.x"
    original_command = _build(args.compiler, vendor / "calmet.for", alias,
                              original_x)
    instrumented_command = _build(args.compiler, out / "calmet_instrumented.for",
                                  alias, instrumented_x)

    staging = out / "case"
    if staging.exists():
        shutil.rmtree(staging)
    staged = _stage_case(case, staging)
    run_dir = staging / "run" / "met"

    original_run = _run(original_x, run_dir)
    if (run_dir / "dgm_station.bin").exists():
        raise SystemExit("the untouched original wrote a dump file: the "
                         "baseline binary is not the untouched source")
    instrumented_run = _run(instrumented_x, run_dir)
    dump = run_dir / "dgm_station.bin"
    if not dump.is_file():
        raise SystemExit("the instrumented run wrote no dgm_station.bin")

    compiler_version = subprocess.run([args.compiler, "--version"],
                                      capture_output=True, text=True,
                                      check=True).stdout.splitlines()[0]
    identical = original_run["met_dat_sha256"] == instrumented_run["met_dat_sha256"]
    matches_target = instrumented_run["met_dat_sha256"] == TARGET_MET_DAT_SHA256
    evidence = {
        "status": ("ORIGINAL_MET_DAT_IDENTICAL" if identical
                   else "INSTRUMENTATION_CHANGED_MET_DAT"),
        "compiler": args.compiler,
        "compiler_version": compiler_version,
        "common_flags": list(COMMON_FFLAGS),
        "build_commands": {"original": original_command,
                           "instrumented": instrumented_command},
        "case": {"path": str(case), "inputs": staged},
        "runs": {"original": original_run, "instrumented": instrumented_run},
        "dump": {"bytes": dump.stat().st_size, "sha256": sha256_file(dump),
                 "records": dump.stat().st_size // RECORD_BYTES},
        "met_dat_identical": identical,
        "met_dat_matches_frozen_reference": matches_target,
        "frozen_reference_sha256": TARGET_MET_DAT_SHA256,
        "instrumentation": instrumentation,
    }
    (out / "dgm-audit.json").write_text(json.dumps(evidence, indent=2) + "\n")
    if not identical:
        raise SystemExit("instrumentation is not write-only: MET.DAT changed")
    if not matches_target:
        print(f"WARNING: MET.DAT {instrumented_run['met_dat_sha256']} does not "
              f"match the frozen reference {TARGET_MET_DAT_SHA256}")
    print(json.dumps({k: evidence[k] for k in
                      ("status", "met_dat_identical",
                       "met_dat_matches_frozen_reference", "dump")}, indent=2))
    return evidence


def _read_records(path: Path):
    blob = path.read_bytes()
    if len(blob) % RECORD_BYTES:
        raise SystemExit(f"dump size {len(blob)} is not a multiple of "
                         f"{RECORD_BYTES}")
    records = []
    for offset in range(0, len(blob), RECORD_BYTES):
        ints = struct.unpack_from(f"<{INT_SLOTS}i", blob, offset)
        floats = struct.unpack_from(f"<{FLOAT_SLOTS}f", blob,
                                    offset + 4 * INT_SLOTS)
        record = {"header": {name: ints[slot - 1]
                             for name, slot, _m in INT_TABLE},
                  "floats": floats, "byte_offset": offset}
        records.append(record)
    return records


def metadata(args: argparse.Namespace) -> dict:
    dump = args.dump.resolve()
    records = _read_records(dump)
    by_kpt = {}
    for record in records:
        by_kpt.setdefault(record["header"]["kpt"], []).append(record)
    for kpt, rows in by_kpt.items():
        labels = [row["header"]["packed"] for row in rows]
        if labels != sorted(labels):
            raise SystemExit(f"kpt {kpt} hour labels are not ordered")

    nz = records[0]["header"]["nz"]
    wanted = args.hours
    table = []
    for kpt in sorted(by_kpt):
        for row in by_kpt[kpt]:
            head = row["header"]
            if wanted and head["packed"] not in wanted:
                continue
            floats = row["floats"]
            entry = {"kpt": kpt, "packed": head["packed"],
                     "seconds": head["seconds"], "nz": head["nz"],
                     "nlaa": head["nlaa"], "nlbb": head["nlbb"],
                     "justa": head["justa"], "ntzaa": head["ntzaa"],
                     "ntzbb": head["ntzbb"], "jusdt": head["jusdt"],
                     "iu": head["iu"], "l": head["l"],
                     "byte_offset": row["byte_offset"]}
            if kpt == 1:
                entry["US_ENTER"] = list(floats[0:nz])
                entry["VS_ENTER"] = list(floats[9:9 + nz])
            elif kpt == 2:
                entry["US_ADJUSTED"] = list(floats[18:18 + nz])
                entry["VS_ADJUSTED"] = list(floats[27:27 + nz])
            else:
                entry["justa"] = head["justa"]
                entry["ntzaa"] = head["ntzaa"]
                entry["ntzbb"] = head["ntzbb"]
                entry["jusdt"] = head["jusdt"]
                entry["ZLAA"] = list(floats[36:36 + head["nlaa"]])
                entry["UAA"] = list(floats[135:135 + head["nlaa"]])
                entry["VAA"] = list(floats[234:234 + head["nlaa"]])
                entry["ZLBB"] = list(floats[333:333 + head["nlbb"]])
                entry["UBB"] = list(floats[432:432 + head["nlbb"]])
                entry["VBB"] = list(floats[531:531 + head["nlbb"]])
                entry["UAVERAA"] = list(floats[630:630 + nz])
                entry["VAVERAA"] = list(floats[639:639 + nz])
                entry["UAVERBB"] = list(floats[648:648 + nz])
                entry["VAVERBB"] = list(floats[657:657 + nz])
            table.append(entry)

    hours = sorted({row["header"]["packed"] for row in records})
    payload = {
        "what": ("the original CALMET 6.5.0 surface-station observation "
                 "assembly and upper-air columns for the frozen Hefei 2022 "
                 "case, exported by write-only instrumentation"),
        "why": ("P6D's round-17 request: level 1 of U/V is the observed surface "
                "wind, so no SIMILT is involved and the EL/ZII tables cannot "
                "move it; separating the assembly, the UA low-level "
                "interpolation and the analysis weights needs the values "
                "before CALMET analyses them"),
        "source": {
            "vendor_file": "engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for",
            "vendor_sha256": ORIGINAL_CALMET_SHA256,
            "request": "P6D PR #23, round 17",
            "insertion_points": {
                str(kpt): {"vendor_line": line_no, "when": WHEN[kpt],
                           "routine": {1: "PREPDI", 2: "DIAGNO", 3: "COMP",
                                       4: "COMP"}[kpt]}
                for kpt, (line_no, *_rest) in sorted(ANCHORS.items())
            },
            "write_only": "see dgm-audit.json (MET.DAT byte identical)",
        },
        "binary": {
            "path": str(dump), "bytes": dump.stat().st_size,
            "sha256": sha256_file(dump),
            "record_bytes": RECORD_BYTES, "records": len(records),
            "hours": len(hours),
            "header": f"int32[{INT_SLOTS}]",
            "payload": f"float32[{FLOAT_SLOTS}]",
            "byte_order": "little endian",
            "order": "records are ordered by insertion point, then timestep; "
                     "each record carries its own (kpt, packed) key",
        },
        "ints": {name: {"slot": slot, "meaning": meaning}
                 for name, slot, meaning in INT_TABLE},
        "fields": {name: {"slot": slot, "units": units, "meaning": meaning}
                   for name, slot, units, meaning in FLOAT_TABLE},
        "index_order": {
            "UPMET sounding arrays (ZLAA/UAA/VAA/ZLBB/UBB/VBB)": "station-major: "
                "element (iu,k) - the level index varies fastest",
            "VERTAV outputs (UAVERAA/VAVERAA/UAVERBB/VAVERBB)": "level-major: "
                "element (k,iu) - the station index varies fastest",
            "D1 US/VS (US_ENTER, US_ADJUSTED)": "level-major: element (k,l)",
        },
        "missing_sentinel": {
            "applied": False,
            "note": ("CALMET uses EDIT (=9999.) internally for missing wind "
                     "components; kpt=1 records show it above level 1, and the "
                     "sounding arrays may carry 9999.9 for missing levels. The "
                     "dump writes the raw values, so a reader must treat "
                     ">=9998. as missing rather than as a physical value."),
            "calmet_missing": 9999.0,
        },
        "time": {"label": "packed YYYYJJJHH beginning time (/GEN/ ndathrb) plus "
                          "seconds (/GEN/ nsecb)",
                 "hours": hours},
        "requested_hours": wanted,
        "table": table,
    }
    path = args.out / "dgm_station.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({
        "metadata": str(path), "metadata_sha256": sha256_file(path),
        "dump_sha256": payload["binary"]["sha256"],
        "records": len(records), "hours": len(hours),
        "requested_rows": len(table),
    }, indent=2))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)

    one = sub.add_parser("instrument", help="write the instrumented copy")
    one.add_argument("--vendor", type=Path, required=True)
    one.add_argument("--out", type=Path, required=True)

    two = sub.add_parser("audit", help="build, run and prove write-only")
    two.add_argument("--vendor", type=Path, required=True)
    two.add_argument("--case", type=Path, required=True)
    two.add_argument("--out", type=Path, required=True)
    two.add_argument("--compiler", default="/usr/bin/gfortran-11")

    three = sub.add_parser("metadata", help="dump + metadata JSON")
    three.add_argument("--dump", type=Path, required=True)
    three.add_argument("--out", type=Path, required=True)
    three.add_argument("--hours", type=int, nargs="*", default=[],
                       help="packed YYYYJJJHH labels to tabulate "
                            "(default: all hours in the dump)")

    args = parser.parse_args()
    if args.mode == "instrument":
        instrument(args.vendor.resolve(), args.out.resolve())
    elif args.mode == "audit":
        audit(args)
    else:
        args.out.mkdir(parents=True, exist_ok=True)
        metadata(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

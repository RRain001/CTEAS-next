#!/usr/bin/env python3
"""Original CALPUFF 7.2.1 puff-step dump (write-only instrumentation) — DGM round 3.

P7U located and pinned the advection / step-integration chain of the original
CALPUFF (`ADVWND`, `ADVECT`, `PUFFDZ`, `ZFIND`, `POWLAW`, `XTPRF` and the inline
step code of `COMP`) and recorded an eight-item instrumentation request
(`docs/reconstruction_cpp/P7_EXECUTION_LEDGER.md`, P7U section;
`native_cpp/modules/p7_calpuff/reference/p7u_source_anchor.json`). This tool
implements that request as **write-only** dumps: the vendor tree is never
modified, and the instrumented run must reproduce `puff.con` byte for byte.

Eight insertion points inside `subroutine comp` (vendor lines):

    item 1  L10473  start-of-step puff state (ii, icode, xold, yold, zold)
    item 2  L10487  the met cell and parameters of the step
    item 3  L10495  PUFFDZ's return (ztop, zbot)
    item 4  L10499  ADVECT's return (uadv, vadv)
    item 5  L10528  after the rise-wind and calm adjustments
    item 6  L10347  the sampling-step cadence (nsam, nsstr, xsami, tsamp, ...)
    item 8a L10939  SETPUF entry (stored puff state + the /CURRENT/ carry-over)
    item 7+8b L10942 SETPUF return, the end-of-step position, and the record

Each point calls a small helper that stores its values into the /DGMSTEP/
common; the last one (`DGMEMIT`) writes one fixed-width record to
`dgm_puffstep.bin` (unit 94) with the current packed time from /DATEHR/.

Record layout (little endian, 352 bytes):

    int32[24]  kpt, packed YYYYJJJHH, seconds, ii, icode, ixs, iys, mdoms,
               istab, ilayer, nsam, nsstr, iold, istype, ipno, mdstep,
               ksam, lcalm, nspec, lpuff, islug, icode2, spare, spare
    float32[64]  see FIELD_TABLE below

`audit` compiles the untouched original and the instrumented copy with one
compiler and one flag set, runs both on the frozen 2022 case with identical
inputs, and requires the two produced `puff.con` files to hash identically (and
to equal the frozen reference). `metadata` turns the dump into JSON metadata and
a committed slice (hour 1, all puffs) plus the byte offset of every hour.
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
ORIGINAL_CALPUFF_SHA256 = "da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568"
MODULES_SHA256 = "115ab7c7e50701a454852106d7c7536d75f1975f66a87a616b4835c5bea353b6"
TARGET_PUFF_CON_SHA256 = "0d51bdb68ff1a5798048bc41067107d3ffe10dc6222f25336df856bcbf48ba10"
PUFF_INP_SHA256 = "cf5cca70cb75b1aac92f86fdc100500e901a8b904d056c73b2330175793532bc"
MET_DAT_SHA256 = "b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30"

# The frozen reference capture's CALPUFF recipe.
PUFF_FFLAGS = ("-std=legacy", "-ffixed-line-length-72", "-fno-automatic",
               "-fno-align-commons", "-fallow-argument-mismatch", "-O0",
               "-fdec-format-defaults")

# The eight points of the P7U request, keyed by the request's item.
# value = (vendor line, that line, the line before it, the line after it)
ANCHORS = {
    "item6_sampling_cadence": (
        10347, "         reftsamp=tsamp",
        "c ---    sampling step interval to a reference variable.",
        "         tleft=0.0"),
    "item1_start_of_step": (
        10473, "         endif",
        "            zold=0.5*(zpb(ii)+zpe(ii))",
        "c"),
    "item2_cell_parameters": (
        10487, "         z0m=z0(ixs,iys,mdoms)",
        "         el=xmonin(ixs,iys,mdoms)",
        "c"),
    "item3_puffdz_return": (
        10495, "     &               ztop,zbot)",
        "         call PUFFDZ(ii,icode,lpuff,istab,ilayer,htmet,dpbl,",
        "c"),
    "item4_advect_return": (
        10499, "     &               zbot,ztop,uadv,vadv)",
        "         call ADVECT(ldb,ixs,iys,mdoms,z0m,el,dpbl,istab,ht0(ii),",
        "c ---    Compute corresponding speed and direction"),
    "item5_after_adjustments": (
        10528, "         endif",
        "            lcalm=.FALSE.",
        "c"),
    "item8a_setpuf_entry": (
        10939, "c ---       Compute puff position and sigmas, and update stored data.",
        "c ---       NOW PUFFS",
        "            call SETPUF(ii,tsamp,distm,jdstab,el,tsigv,tsigw,bvf,ws,"),
    "item7_setpuf_return": (
        10942, "     &                  uavg,lcalm)",
        "     &                  dpbl,xnew,ynew,iru,ixmet,iymet,idmet,ldb,",
        "c"),
}

CALLS = {
    "item6_sampling_cadence": (
        "         call dgmstep6(nsam,nsstr,iold,istype,ipno,xsami,tsamp,\n"
        "     &                reftsamp,wsvar)\n"),
    "item1_start_of_step":
        "         call dgmstep1(ii,icode,xold,yold,zold)\n",
    "item2_cell_parameters":
        "         call dgmstep2(ixs,iys,mdoms,istab,dpbl,el,z0m)\n",
    "item3_puffdz_return":
        "         call dgmstep3(ilayer,htmet,ztop,zbot)\n",
    "item4_advect_return":
        "         call dgmstep4(uadv,vadv)\n",
    "item5_after_adjustments":
        "         call dgmstep5(ws,lcalm,uadv,vadv)\n",
    "item8a_setpuf_entry":
        "            call dgmstep8e(ii)\n",
    "item7_setpuf_return": (
        "            call dgmemit(ii,ksam,lcalm,lpuff,lslug,xnew,ynew,distm,\n"
        "     &                   tleft,tsampsum,mdstep,tsamp)\n"),
}

WHEN = {
    "item6_sampling_cadence": "the sampling-step cadence of this puff (nsam, "
                              "nsstr, xsami, tsamp, reftsamp, iold, istype, "
                              "ipno, wsvar)",
    "item1_start_of_step": "the start-of-step puff state (the comparison's "
                           "initial condition)",
    "item2_cell_parameters": "the met cell and parameters the step uses",
    "item3_puffdz_return": "the averaging layer bounds from PUFFDZ",
    "item4_advect_return": "the advective wind from ADVECT (METFM=1 -> ADVWND)",
    "item5_after_adjustments": "the effective transport speed after RISEWIND "
                               "and the calm treatment",
    "item8a_setpuf_entry": "SETPUF entry: the stored puff state and the "
                           "/CURRENT/ values carried over from the previous puff",
    "item7_setpuf_return": "SETPUF return and the end-of-step puff position; "
                           "this call writes the record",
}

# int32 slots of the record (index in the Fortran /DGMSTEP/ istep array)
INT_TABLE = [
    ("kpt", 1, "record type, always 1"),
    ("packed", 2, "current timestep beginning time, packed YYYYJJJHH "
                  "(/DATEHR/ ndathrb)"),
    ("seconds", 3, "current timestep beginning seconds (/DATEHR/ nsecb)"),
    ("ii", 4, "puff index"),
    ("icode", 5, "puff/slug state code"),
    ("ixs", 6, "met cell i at the start of the step"),
    ("iys", 7, "met cell j at the start of the step"),
    ("mdoms", 8, "met domain of the start cell"),
    ("istab", 9, "PG stability class at the start cell"),
    ("ilayer", 10, "starting met layer index (ilayer1)"),
    ("nsam", 11, "number of sampling substeps for this puff"),
    ("nsstr", 12, "first sampling substep index"),
    ("iold", 13, "1 = old puff, 0 = new puff, 2 = road slug"),
    ("istype", 14, "source type"),
    ("ipno", 15, "source/stack number"),
    ("mdstep", 16, "met domain used for the step size"),
    ("ksam", 17, "current sampling substep index"),
    ("lcalm", 18, "1 when the calm treatment was applied, else 0"),
    ("nspec", 19, "number of modelled species"),
    ("lpuff", 20, "1 for a Gaussian puff, 0 for a slug"),
    ("islug", 21, "1 for a slug, 0 for a puff"),
    ("isrcnum", 22, "source index of the puff"),
    ("spare1", 23, "reserved, always 0"),
    ("spare2", 24, "reserved, always 0"),
]

# float32 slots: (name, index in the Fortran rstep array, units, meaning)
FLOAT_TABLE = [
    ("xold", 1, "grid units (cells of the outermost met grid; 1 cell = 100 m here)",
     "start-of-step puff x"),
    ("yold", 2, "grid units (cells of the outermost met grid; 1 cell = 100 m here)",
     "start-of-step puff y"),
    ("zold", 3, "m",
     "start-of-step puff height above sea level"),
    ("dpbl", 4, "m",
     "mixing height at the start cell (clamped)"),
    ("el", 5, "m",
     "Monin-Obukhov length at the start cell"),
    ("z0m", 6, "m",
     "roughness length at the start cell"),
    ("htmet", 7, "m",
     "puff height used by PUFFDZ (zold)"),
    ("ztop", 8, "m",
     "top of the averaging layer (PUFFDZ return)"),
    ("zbot", 9, "m",
     "bottom of the averaging layer (PUFFDZ return)"),
    ("uadv_advect", 10, "m/s",
     "ADVECT return u"),
    ("vadv_advect", 11, "m/s",
     "ADVECT return v"),
    ("ws", 12, "m/s",
     "speed after the rise-wind and calm adjustments"),
    ("uadv_adjusted", 13, "m/s",
     "u after the adjustments (transport u)"),
    ("vadv_adjusted", 14, "m/s",
     "v after the adjustments (transport v)"),
    ("lcalm_f", 15, "0/1",
     "lcalm as a float"),
    ("xsami", 16, "1",
     "reciprocal of the number of sampling steps (set for old puffs; carried over for new puffs)"),
    ("tsamp", 17, "s",
     "sampling step length at the cadence point (before any subsampling split)"),
    ("reftsamp", 18, "s",
     "reference sampling step interval"),
    ("wsvar", 19, "m/s",
     "wind speed used for variable sampling (new puffs)"),
    ("xtotb_in", 20, "m",
     "total travel distance of the puff before SETPUF"),
    ("tmtotb_in", 21, "s",
     "total travel time of the puff before SETPUF"),
    ("sigyb_in", 22, "m",
     "stored sigma-y before SETPUF"),
    ("sigzb_in", 23, "m",
     "stored sigma-z before SETPUF (after any vertical divergence adjustment of this substep)"),
    ("xpb_in", 24, "grid units (cells of the outermost met grid; 1 cell = 100 m here)",
     "stored puff x before SETPUF"),
    ("ypb_in", 25, "grid units (cells of the outermost met grid; 1 cell = 100 m here)",
     "stored puff y before SETPUF"),
    ("zpb_in", 26, "m",
     "stored puff z before SETPUF"),
    ("xb1_in", 27, "grid units (cells of the outermost met grid; 1 cell = 100 m here)",
     "/CURRENT/ xb1 entering SETPUF (carried over from the previous puff)"),
    ("yb1_in", 28, "grid units (cells of the outermost met grid; 1 cell = 100 m here)",
     "/CURRENT/ yb1 entering SETPUF"),
    ("zb1_in", 29, "m",
     "/CURRENT/ zb1 entering SETPUF"),
    ("xe1_in", 30, "grid units (cells of the outermost met grid; 1 cell = 100 m here)",
     "/CURRENT/ xe1 entering SETPUF"),
    ("ye1_in", 31, "grid units (cells of the outermost met grid; 1 cell = 100 m here)",
     "/CURRENT/ ye1 entering SETPUF"),
    ("ze1_in", 32, "m",
     "/CURRENT/ ze1 entering SETPUF"),
    ("syb1_in", 33, "m",
     "/CURRENT/ syb1 entering SETPUF"),
    ("sym1_in", 34, "m",
     "/CURRENT/ sym1 entering SETPUF"),
    ("sye1_in", 35, "m",
     "/CURRENT/ sye1 entering SETPUF"),
    ("szb1_in", 36, "m",
     "/CURRENT/ szb1 entering SETPUF"),
    ("szm1_in", 37, "m",
     "/CURRENT/ szm1 entering SETPUF"),
    ("sze1_in", 38, "m",
     "/CURRENT/ sze1 entering SETPUF"),
    ("xnew", 39, "grid units (cells of the outermost met grid; 1 cell = 100 m here)",
     "end-of-step puff x before SETPUF stores it"),
    ("ynew", 40, "grid units (cells of the outermost met grid; 1 cell = 100 m here)",
     "end-of-step puff y"),
    ("xtotb_out", 41, "m",
     "total travel distance after SETPUF"),
    ("tmtotb_out", 42, "s",
     "total travel time after SETPUF"),
    ("sigyb_out", 43, "m",
     "stored sigma-y after SETPUF (start of next step)"),
    ("sigzb_out", 44, "m",
     "stored sigma-z after SETPUF (start of next step)"),
    ("xpb_out", 45, "grid units (cells of the outermost met grid; 1 cell = 100 m here)",
     "stored puff x after SETPUF"),
    ("ypb_out", 46, "grid units (cells of the outermost met grid; 1 cell = 100 m here)",
     "stored puff y after SETPUF"),
    ("zpb_out", 47, "m",
     "stored puff z after SETPUF (CALPUFF has no `znew`; the vertical end position is the internal `ze1`, and this is the stored result)"),
    ("xb1_out", 48, "grid units (cells of the outermost met grid; 1 cell = 100 m here)",
     "/CURRENT/ xb1 after SETPUF"),
    ("yb1_out", 49, "grid units (cells of the outermost met grid; 1 cell = 100 m here)",
     "/CURRENT/ yb1 after SETPUF"),
    ("zb1_out", 50, "m",
     "/CURRENT/ zb1 after SETPUF"),
    ("xe1_out", 51, "grid units (cells of the outermost met grid; 1 cell = 100 m here)",
     "/CURRENT/ xe1 after SETPUF"),
    ("ye1_out", 52, "grid units (cells of the outermost met grid; 1 cell = 100 m here)",
     "/CURRENT/ ye1 after SETPUF"),
    ("ze1_out", 53, "m",
     "/CURRENT/ ze1 after SETPUF (the vertical end position)"),
    ("syb1_out", 54, "m",
     "/CURRENT/ syb1 after SETPUF"),
    ("sym1_out", 55, "m",
     "/CURRENT/ sym1 after SETPUF"),
    ("sye1_out", 56, "m",
     "/CURRENT/ sye1 after SETPUF"),
    ("szb1_out", 57, "m",
     "/CURRENT/ szb1 after SETPUF"),
    ("szm1_out", 58, "m",
     "/CURRENT/ szm1 after SETPUF"),
    ("sze1_out", 59, "m",
     "/CURRENT/ sze1 after SETPUF"),
    ("distm", 60, "m",
     "distance travelled during this substep"),
    ("tleft", 61, "s",
     "time left in the sampling step"),
    ("tsampsum", 62, "s",
     "sampling time accumulated before this substep"),
    ("tsamp_effective", 63, "s",
     "sampling substep length actually used by this step (the `tsamp` variable at the SETPUF call)"),
    ("spare_f2", 64, "0",
     "reserved, always 0"),
]


INT_SLOTS, FLOAT_SLOTS = 24, 64
RECORD_BYTES = 4 * (INT_SLOTS + FLOAT_SLOTS)

HELPERS = """
c ---------------------------------------------------------------------
c --- DGM TRACK ROUND 3 (P7U request): write-only dump of the puff-step
c --- advection chain. Present only in the temporary instrumented copy of
c --- this file; the vendor tree is untouched. Record layout is documented
c --- in native_cpp/modules/p7_calpuff/reference/dgm_p7_advection_2022/
c --- original_puff_step_dump.py
c ---------------------------------------------------------------------
      subroutine dgmstep1(ii,icode,xold,yold,zold)
      integer ii,icode
      real xold,yold,zold
      common /dgmstep/ istep(24), rstep(64)
      istep(4)=ii
      istep(5)=icode
      rstep(1)=xold
      rstep(2)=yold
      rstep(3)=zold
      return
      end

      subroutine dgmstep2(ixs,iys,mdoms,istab,dpbl,el,z0m)
      integer ixs,iys,mdoms,istab
      real dpbl,el,z0m
      common /dgmstep/ istep(24), rstep(64)
      istep(6)=ixs
      istep(7)=iys
      istep(8)=mdoms
      istep(9)=istab
      rstep(4)=dpbl
      rstep(5)=el
      rstep(6)=z0m
      return
      end

      subroutine dgmstep3(ilayer,htmet,ztop,zbot)
      integer ilayer
      real htmet,ztop,zbot
      common /dgmstep/ istep(24), rstep(64)
      istep(10)=ilayer
      rstep(7)=htmet
      rstep(8)=ztop
      rstep(9)=zbot
      return
      end

      subroutine dgmstep4(uadv,vadv)
      real uadv,vadv
      common /dgmstep/ istep(24), rstep(64)
      rstep(10)=uadv
      rstep(11)=vadv
      return
      end

      subroutine dgmstep5(ws,lcalm,uadv,vadv)
      real ws,uadv,vadv
      logical lcalm
      common /dgmstep/ istep(24), rstep(64)
      rstep(12)=ws
      rstep(13)=uadv
      rstep(14)=vadv
      rstep(15)=0.0
      if(lcalm) rstep(15)=1.0
      return
      end

      subroutine dgmstep6(nsam,nsstr,iold,istype,ipno,xsami,tsamp,
     1                    reftsamp,wsvar)
      integer nsam,nsstr,iold,istype,ipno
      real xsami,tsamp,reftsamp,wsvar
      common /dgmstep/ istep(24), rstep(64)
      istep(11)=nsam
      istep(12)=nsstr
      istep(13)=iold
      istep(14)=istype
      istep(15)=ipno
      rstep(16)=xsami
      rstep(17)=tsamp
      rstep(18)=reftsamp
      rstep(19)=wsvar
      return
      end

      subroutine dgmstep8e(ii)
c --- SETPUF entry: the stored puff state and the /CURRENT/ carry-over
      include 'params.puf'
      integer ii
      common /dgmstep/ istep(24), rstep(64)
      include 'puff.puf'
      include 'current.puf'
      rstep(20)=xtotb(ii)
      rstep(21)=tmtotb(ii)
      rstep(22)=sigyb(ii)
      rstep(23)=sigzb(ii)
      rstep(24)=xpb(ii)
      rstep(25)=ypb(ii)
      rstep(26)=zpb(ii)
      rstep(27)=xb1
      rstep(28)=yb1
      rstep(29)=zb1
      rstep(30)=xe1
      rstep(31)=ye1
      rstep(32)=ze1
      rstep(33)=syb1
      rstep(34)=sym1
      rstep(35)=sye1
      rstep(36)=szb1
      rstep(37)=szm1
      rstep(38)=sze1
      return
      end

      subroutine dgmemit(ii,ksam,lcalm,lpuff,lslug,xnew,ynew,distm,
     1                   tleft,tsampsum,mdstep,tsampe)
c --- SETPUF return and end-of-step position: write one record
      include 'params.puf'
      integer ii,ksam,mdstep
      real xnew,ynew,distm,tleft,tsampsum,tsampe
      logical lcalm,lpuff,lslug,ldgm
      save ldgm
      data ldgm/.false./
      common /dgmstep/ istep(24), rstep(64)
      include 'datehr.puf'
      include 'gen.puf'
      include 'flags.puf'
      include 'puff.puf'
      include 'current.puf'
c
      if(.not.ldgm)then
         open(94,file='dgm_puffstep.bin',form='unformatted',
     1        access='stream',status='replace')
         ldgm=.true.
      endif
c
      rstep(39)=xnew
      rstep(40)=ynew
      rstep(41)=xtotb(ii)
      rstep(42)=tmtotb(ii)
      rstep(43)=sigyb(ii)
      rstep(44)=sigzb(ii)
      rstep(45)=xpb(ii)
      rstep(46)=ypb(ii)
      rstep(47)=zpb(ii)
      rstep(48)=xb1
      rstep(49)=yb1
      rstep(50)=zb1
      rstep(51)=xe1
      rstep(52)=ye1
      rstep(53)=ze1
      rstep(54)=syb1
      rstep(55)=sym1
      rstep(56)=sye1
      rstep(57)=szb1
      rstep(58)=szm1
      rstep(59)=sze1
      rstep(60)=distm
      rstep(61)=tleft
      rstep(62)=tsampsum
      rstep(63)=tsampe
      rstep(64)=0.0
c
      istep(1)=1
      istep(2)=ndathrb
      istep(3)=nsecb
      istep(16)=mdstep
      istep(17)=ksam
      istep(18)=0
      if(lcalm) istep(18)=1
      istep(19)=nspec
      istep(20)=0
      if(lpuff) istep(20)=1
      istep(21)=0
      if(lslug) istep(21)=1
      istep(22)=isrcnum(ii)
      istep(23)=0
      istep(24)=0
c
      write(94) istep
      write(94) rstep
c
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
    """Write the instrumented copy and the insertion report."""
    source = vendor_dir / "calpuff.for"
    actual = sha256_file(source)
    if actual != ORIGINAL_CALPUFF_SHA256:
        raise SystemExit(f"vendor calpuff.for SHA256 drift: {actual}")
    modules = vendor_dir / "modules.for"
    modules_actual = sha256_file(modules)
    if modules_actual != MODULES_SHA256:
        raise SystemExit(f"vendor modules.for SHA256 drift: {modules_actual}")

    # The vendor source is not valid UTF-8 (a Windows-1252 byte in a
    # comment); latin-1 round-trips every byte unchanged.
    lines = source.read_text(encoding='latin-1').splitlines(keepends=True)
    for key, (line_no, expected, before, after) in ANCHORS.items():
        got = lines[line_no - 1].rstrip("\r\n")
        prev = lines[line_no - 2].rstrip("\r\n") if line_no > 1 else ""
        nxt = lines[line_no].rstrip("\r\n") if line_no < len(lines) else ""
        if got != expected or prev != before or nxt != after:
            raise SystemExit(
                f"anchor drift at {key} line {line_no}: got {got!r} between "
                f"{prev!r} and {nxt!r}")

    insertions = {}
    for key, (line_no, *_rest) in ANCHORS.items():
        insertions[line_no] = (
            f"c --- DGM write-only puff-step dump: {key}\n" + CALLS[key])

    body = "".join(line + insertions.get(index, "")
                   for index, line in enumerate(lines, 1))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "calpuff_instrumented.for"
    target.write_text(body + HELPERS, encoding='latin-1')

    segments = {
        "comp_sampling_cadence": (10335, 10353),
        "comp_step_start": (10460, 10490),
        "comp_step_wind": (10492, 10535),
        "comp_setpuf_call": (10936, 10943),
    }
    report = {
        "status": "ORIGINAL_CALPUFF_WRITE_ONLY_PUFF_STEP_INSTRUMENTED",
        "why": ("P7U located the advection / step-integration chain and asked "
                "for the observable variables at named lines so the port can "
                "be diffed value by value; CALPUFF writes none of them to "
                "puff.con"),
        "request_source": {
            "anchor_json": "native_cpp/modules/p7_calpuff/reference/"
                           "p7u_source_anchor.json",
            "ledger": "docs/reconstruction_cpp/P7_EXECUTION_LEDGER.md (P7U)",
        },
        "no_vendor_source_edits": True,
        "vendor_source_sha256": {
            "calpuff.for": actual,
            "modules.for": modules_actual,
        },
        "instrumented_sha256": {
            "calpuff_instrumented.for": sha256_file(target),
        },
        "helper_subroutines": {
            "DGMSTEP1..DGMSTEP6, DGMSTEP8E, DGMEMIT": {
                "vendor_lines": len(lines) + 1,
                "sha256": sha256_bytes(HELPERS.encode('latin-1')),
                "unit": 94,
                "output_file": "dgm_puffstep.bin",
                "record_bytes": RECORD_BYTES,
                "writes_only": True,
            },
        },
        "points": [
            {
                "item": key,
                "vendor_line": line_no,
                "when": WHEN[key],
                "inserted_text_sha256": sha256_bytes(
                    insertions[line_no].encode('latin-1')),
            }
            for key, (line_no, *_rest) in sorted(ANCHORS.items(),
                                                 key=lambda kv: kv[1][0])
        ],
        "source_segments": {
            name: {"vendor_lines": [first, last],
                   "sha256": sha256_bytes(
                       "".join(lines[first - 1:last]).encode('latin-1'))}
            for name, (first, last) in segments.items()
        },
        "record_layout": {
            "header": "int32[24]",
            "payload": "float32[64]",
            "record_bytes": RECORD_BYTES,
            "header_dtype": "int32 little endian",
            "field_dtype": "float32 little endian",
            "ints": [name for name, _slot, _meaning in INT_TABLE],
            "floats": [name for name, _slot, _units, _meaning in FLOAT_TABLE],
        },
    }
    (out_dir / "dgm-instrumentation.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


def _build(compiler: str, modules: Path, source: Path, include_dir: Path,
           target: Path) -> list[str]:
    command = [compiler, *PUFF_FFLAGS, f"-I{include_dir}", str(modules),
               str(source), "-o", str(target)]
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
        "run/puff/puff.inp": (case_dir / "run/puff/puff.inp", PUFF_INP_SHA256),
        "deliverables/met/met.dat": (case_dir / "deliverables/met/met.dat",
                                     MET_DAT_SHA256),
    }
    staged = {}
    for relative, (source, expected) in mapping.items():
        if not source.is_file():
            raise SystemExit(f"missing frozen case input: {source}")
        actual = sha256_file(source)
        if actual != expected:
            raise SystemExit(f"{relative} SHA256 drift: {actual}")
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            destination.unlink()
        shutil.copy2(source, destination)
        staged[relative] = {"sha256": actual, "bytes": source.stat().st_size}
    return staged


def _run(binary: Path, run_dir: Path) -> dict:
    outputs = ("puff.con", "puff.lst", "puff.dry", "puff.wet", "puff.vis")
    for name in outputs + ("dgm_puffstep.bin", "puff_runtime.log"):
        stale = run_dir / name
        if stale.exists():
            stale.unlink()
    log = run_dir / "puff_runtime.log"
    with log.open("w") as handle:
        proc = subprocess.run([str(binary), "puff.inp"], cwd=str(run_dir),
                              stdout=handle, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        raise SystemExit(f"puff.x failed with {proc.returncode}; see {log}")
    con = run_dir / "puff.con"
    if not con.is_file():
        raise SystemExit(f"puff.x produced no puff.con; see {log}")
    return {
        "command": [str(binary), "puff.inp"],
        "cwd": str(run_dir),
        "returncode": proc.returncode,
        "puff_con_sha256": sha256_file(con),
        "puff_con_bytes": con.stat().st_size,
    }


def audit(args: argparse.Namespace) -> dict:
    vendor = args.vendor.resolve()
    case = args.case.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    instrumentation = instrument(vendor, out)
    alias = _alias_tree(vendor, out / "include-alias")
    modules = vendor / "modules.for"

    original_x = out / "bin" / "puff-original.x"
    instrumented_x = out / "bin" / "puff-instrumented.x"
    original_command = _build(args.compiler, modules, vendor / "calpuff.for",
                              alias, original_x)
    instrumented_command = _build(args.compiler, modules,
                                  out / "calpuff_instrumented.for", alias,
                                  instrumented_x)

    staging = out / "case"
    if staging.exists():
        shutil.rmtree(staging)
    staged = _stage_case(case, staging)
    run_dir = staging / "run" / "puff"

    original_run = _run(original_x, run_dir)
    if (run_dir / "dgm_puffstep.bin").exists():
        raise SystemExit("the untouched original wrote a dump file: the "
                         "baseline binary is not the untouched source")
    instrumented_run = _run(instrumented_x, run_dir)
    dump = run_dir / "dgm_puffstep.bin"
    if not dump.is_file():
        raise SystemExit("the instrumented run wrote no dgm_puffstep.bin")

    compiler_version = subprocess.run([args.compiler, "--version"],
                                      capture_output=True, text=True,
                                      check=True).stdout.splitlines()[0]
    identical = original_run["puff_con_sha256"] == instrumented_run["puff_con_sha256"]
    matches_target = instrumented_run["puff_con_sha256"] == TARGET_PUFF_CON_SHA256
    evidence = {
        "status": ("ORIGINAL_PUFF_CON_IDENTICAL" if identical
                   else "INSTRUMENTATION_CHANGED_PUFF_CON"),
        "compiler": args.compiler,
        "compiler_version": compiler_version,
        "flags": list(PUFF_FFLAGS),
        "include_handling": "lower-case symlink alias tree per vendor directory",
        "build_commands": {"original": original_command,
                           "instrumented": instrumented_command},
        "case": {"path": str(case), "inputs": staged},
        "runs": {"original": original_run, "instrumented": instrumented_run},
        "dump": {"bytes": dump.stat().st_size, "sha256": sha256_file(dump),
                 "records": dump.stat().st_size // RECORD_BYTES},
        "puff_con_identical": identical,
        "puff_con_matches_frozen_reference": matches_target,
        "frozen_reference_sha256": TARGET_PUFF_CON_SHA256,
        "instrumentation": instrumentation,
    }
    (out / "dgm-audit.json").write_text(json.dumps(evidence, indent=2) + "\n")
    if not identical:
        raise SystemExit("instrumentation is not write-only: puff.con changed")
    if not matches_target:
        print(f"WARNING: puff.con {instrumented_run['puff_con_sha256']} does not "
              f"match the frozen reference {TARGET_PUFF_CON_SHA256}")
    print(json.dumps({k: evidence[k] for k in
                      ("status", "puff_con_identical",
                       "puff_con_matches_frozen_reference", "dump")}, indent=2))
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
        record = {name: ints[slot - 1] for name, slot, _m in INT_TABLE}
        record.update({name: floats[slot - 1]
                       for name, slot, _u, _m in FLOAT_TABLE})
        record["byte_offset"] = offset
        records.append(record)
    return records


def metadata(args: argparse.Namespace) -> dict:
    dump = args.dump.resolve()
    records = _read_records(dump)
    if not records:
        raise SystemExit("empty dump")
    hours = {}
    for record in records:
        hours.setdefault(record["packed"], []).append(record)
    packed = list(hours)
    if packed != sorted(packed):
        raise SystemExit("hour labels are not ordered in the dump")
    for label, rows in hours.items():
        for row in rows:
            if row["kpt"] != 1:
                raise SystemExit(f"unexpected record type {row['kpt']}")

    hour_table = []
    for label in packed:
        rows = hours[label]
        hour_table.append({
            "packed": label,
            "seconds": rows[0]["seconds"],
            "records": len(rows),
            "first_byte_offset": rows[0]["byte_offset"],
            "last_byte_offset": rows[-1]["byte_offset"],
            "first_puff": min(row["ii"] for row in rows),
            "last_puff": max(row["ii"] for row in rows),
        })

    slice_label = args.slice_hour
    if slice_label not in hours:
        raise SystemExit(f"hour {slice_label} is not in the dump "
                         f"(labels: {packed[0]}..{packed[-1]})")
    rows = hours[slice_label]
    slice_path = args.out / f"dgm_puffstep_hour{slice_label}.bin"
    with dump.open("rb") as source, slice_path.open("wb") as sink:
        source.seek(rows[0]["byte_offset"])
        sink.write(source.read(RECORD_BYTES * len(rows)))

    stats = {}
    for name, _slot, _units, _meaning in FLOAT_TABLE:
        values = [row[name] for row in rows]
        stats[name] = {"min": min(values), "max": max(values),
                       "mean": sum(values) / len(values)}

    payload = {
        "what": ("the original CALPUFF 7.2.1 puff-step advection state for the "
                 "frozen Hefei 2022 case, exported by write-only "
                 "instrumentation of the unmodified vendor source"),
        "why": ("P7U pinned the advection chain and asked for the observable "
                "variables at named lines; none of them appears in puff.con"),
        "source": {
            "vendor_file": "engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for",
            "vendor_sha256": ORIGINAL_CALPUFF_SHA256,
            "subroutine": "COMP",
            "request": "native_cpp/modules/p7_calpuff/reference/"
                       "p7u_source_anchor.json and the P7U ledger section",
            "insertion_points": {
                key: {"vendor_line": line_no, "when": WHEN[key]}
                for key, (line_no, *_rest) in sorted(ANCHORS.items(),
                                                     key=lambda kv: kv[1][0])
            },
            "write_only": ("both the untouched original and the instrumented "
                           "copy were compiled and run on identical inputs; "
                           "puff.con must hash identically (dgm-audit.json)"),
        },
        "binary": {
            "path": str(dump),
            "bytes": dump.stat().st_size,
            "sha256": sha256_file(dump),
            "record_bytes": RECORD_BYTES,
            "records": len(records),
            "hours": len(hours),
            "header": f"int32[{INT_SLOTS}]",
            "payload": f"float32[{FLOAT_SLOTS}]",
            "byte_order": "little endian",
            "order": "records are ordered by timestep, then puff index, then "
                     "sampling substep; each record carries its own key "
                     "(packed, ii, ksam)",
        },
        "ints": {name: {"slot": slot, "meaning": meaning}
                 for name, slot, meaning in INT_TABLE},
        "fields": {name: {"slot": slot, "units": units, "meaning": meaning}
                   for name, slot, units, meaning in FLOAT_TABLE},
        "missing_sentinel": {
            "applied": False,
            "note": ("no value is missing at these points; CALPUFF's own "
                     "missing markers are not used in these arrays, so a "
                     "reader must not special-case any value"),
        },
        "time": {
            "label": "packed YYYYJJJHH beginning time of the met timestep "
                     "(/DATEHR/ ndathrb) plus its seconds (/DATEHR/ nsecb)",
            "hour_table": hour_table,
        },
        "slice": {
            "path": str(slice_path),
            "bytes": slice_path.stat().st_size,
            "sha256": sha256_file(slice_path),
            "hour": slice_label,
            "records": len(rows),
            "note": "byte-identical records copied out of the full dump",
        },
        "slice_statistics": stats,
    }
    path = args.out / "dgm_puffstep.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({
        "metadata": str(path), "metadata_sha256": sha256_file(path),
        "dump_sha256": payload["binary"]["sha256"],
        "records": len(records), "hours": len(hours),
        "slice": str(slice_path), "slice_sha256": payload["slice"]["sha256"],
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

    three = sub.add_parser("metadata", help="dump + metadata JSON + slice")
    three.add_argument("--dump", type=Path, required=True)
    three.add_argument("--out", type=Path, required=True)
    three.add_argument("--slice-hour", type=int, required=True,
                       help="packed YYYYJJJHH of the hour to commit")

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

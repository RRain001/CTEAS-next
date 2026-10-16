#!/usr/bin/env python3
"""Write-only original CALPUFF H-3 CALCPF intermediate trace for Hefei hour 1.

The original vendor source is SHA pinned, untouched, compiled from a temporary
instrumented copy. Frozen puff.con and 143-hour COMP DGM hashes must match.
Only first-hour grid receptor (ISAMP=19, JSAMP=50), species IPOL=1 are traced.
A diagnostic trace is an oracle of original data, NOT a native parity claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import original_puff_step_dump as original

DGM_SHA = "cbbdaa29c6222e6ca6aefe9f605ad13e7dd6d258f6ad243afcac07cb578108c6"
RECORD = struct.Struct("<3i13f")
# This is the exact original CALCPF L4304 statement, checked byte-for-byte.
CALCPF_ANCHOR = "                  conc=vdpvd(ipol)*xtemp*(qold(ipol)*t1+qnew(ipol)*t2)"
CALL = """                  call dgmrecv(isamp,jsamp,ipol,syrec,szrec,zpr,
     &                 zrpole,f1,xi1,xi2,t1,t2,qold(ipol),
     &                 qnew(ipol),xtemp,conc)
                  call dgmrecvfrac(isamp,jsamp,ipol,frec)
"""

# Helpers are appended AFTER all original modules; no COMMON values are
# mutated except the new isolated /DGMRECUR/ diagnostic counter.
EXTRA_HELPERS = """
c ---- Write-only receiver-stage provenance, original first hour only.
      subroutine dgmreceiverstep(ii,ksam)
      integer ii,ksam,step_count,dgmseq,dgmid,dgmksam
      common /dgmrecur/ dgmseq,dgmid,dgmksam
      save step_count
      data step_count/0/
      step_count=step_count+1
      dgmseq=step_count
      dgmid=ii
      dgmksam=ksam
      return
      end
      subroutine dgmrecv(isamp,jsamp,ipol,syrec,szrec,zpr,
     &                   zrpole,f1,xi1,xi2,t1,t2,qold,qnew,
     &                   xtemp,conc)
      integer isamp,jsamp,ipol,dgmseq,dgmid,dgmksam
      real syrec,szrec,zpr,zrpole,f1,xi1,xi2,t1,t2
      real qold,qnew,xtemp,conc
      common /dgmrecur/ dgmseq,dgmid,dgmksam
      logical first
      save first
      data first/.true./
      if(dgmseq.gt.1275) return
      if(isamp.ne.19.or.jsamp.ne.50.or.ipol.ne.1) return
      if(first)then
        open(unit=97,file='dgm_calcpf_h3_19_50.bin',
     &       form='unformatted',access='stream',
     &       status='replace')
        first=.false.
      endif
      write(97) dgmseq,dgmid,dgmksam,
     &          syrec,szrec,zpr,zrpole,f1,xi1,xi2,t1,t2,
     &          qold,qnew,xtemp,conc
      return
      end
      subroutine dgmrecvfrac(isamp,jsamp,ipol,frac)
      integer isamp,jsamp,ipol,dgmseq,dgmid,dgmksam
      real frac
      common /dgmrecur/ dgmseq,dgmid,dgmksam
      if(dgmseq.gt.1275) return
      if(isamp.ne.19.or.jsamp.ne.50.or.ipol.ne.1) return
      write(97) dgmseq,dgmid,dgmksam,frac
      return
      end
"""
FIELD_NAMES = ("syrec", "szrec", "zpr", "zrpole", "f1", "xi1", "xi2",
               "t1", "t2", "qold", "qnew", "xtemp", "conc")

# Seven exact, source-ordered SETPUF checkpoints at the first real H9 calm
# vertical-sigma mismatch (global DGM #16426, puff 588). These are inserted
# only in a throwaway compiled vendor copy. Binary output is read-only, and
# the complete unmodified original puff.con/DGM hashes MUST remain exact.
H9_Z_TRACE_NAME = "dgm_h9_puff588_setpuf_z.bin"
H9_MET_TRACE_NAME = "dgm_h9_puff588_setpuf_met.bin"
H9_MET_RECORD = struct.Struct("<3i3f")
H9_SIGMA_TRACE_NAME = "dgm_h9_puff588_csigma.bin"
H9_SIGMA_RECORD = struct.Struct("<3i4f")
H9_Z_RECORD = struct.Struct("<3i8f")
H9_Z_HELPERS = """
c --- Write-only exact H9 vertical SETPUF source state, no state mutation
      subroutine dgmh9z(ii,phase,szb,szm,sze,vzb,vzm,vze,tm,te)
      include 'params.puf'
      include 'datehr.puf'
      integer ii,phase
      real szb,szm,sze,vzb,vzm,vze,tm,te
      logical ldgm
      save ldgm
      data ldgm/.false./
      if(ii.ne.588.or.ndathrb.ne.202200108) return
      if(.not.ldgm)then
         open(1917,file='dgm_h9_puff588_setpuf_z.bin',
     &        access='stream',form='unformatted',status='replace')
         ldgm=.true.
      endif
      write(1917) phase,ii,ndathrb,szb,szm,sze,vzb,vzm,vze,tm,te
      return
      end
"""
H9_MET_HELPERS = """
c --- Original H9 actual input to SETPUF from COMP/TURBSET, write only
      subroutine dgmh9met(ii,jdstab,tsigv,tsigw,el)
      include 'params.puf'
      include 'datehr.puf'
      integer ii,jdstab
      real tsigv,tsigw,el
      logical ldgm
      save ldgm
      data ldgm/.false./
      if(ii.ne.588.or.ndathrb.ne.202200108) return
      if(.not.ldgm)then
         open(1918,file='dgm_h9_puff588_setpuf_met.bin',
     &        access='stream',form='unformatted',status='replace')
         ldgm=.true.
      endif
      write(1918) ii,jdstab,ndathrb,tsigv,tsigw,el
      return
      end
"""
H9_SIGMA_HELPERS = """
c --- Capture ACTUAL original /CSIGMA/ values consumed by SIGTZ,
c --- not the zero SETPUF entry formal parameters for MDISP3.
      subroutine dgmh9csigma(ii)
      include 'params.puf'
      include 'datehr.puf'
      include 'csigma.puf'
      integer ii
      logical ldgm
      save ldgm
      data ldgm/.false./
      if(ii.ne.588.or.ndathrb.ne.202200108) return
      if(.not.ldgm)then
         open(1919,file='dgm_h9_puff588_csigma.bin',
     &        access='stream',form='unformatted',status='replace')
         ldgm=.true.
      endif
      write(1919) ii,idoptzs,ndathrb,tsigws,els,tzisdr,uavgs
      return
      end
"""
# Read-only original PUFRECS -> SIGTZ real H9 first receptor discrepancy:
# global DGM 16476, puff594 KSAM5, original sampling grid (21,1).
# Captured from the actual /CSIGMA/ after SETCSIG, not synthesized by C++.
H9_RECSIG_NAME = "dgm_h9_puff594_receptor21_1_sigtz.bin"
H9_RECSIG_RECORD = struct.Struct("<4i16f")
H9_RECFLOOR_NAME = "dgm_h9_puff594_receptor21_1_szfloor.bin"
H9_RECFLOOR_RECORD = struct.Struct("<3i5f")
H9_RECSIG_HELPERS = """
      subroutine dgmh9recvzt(x,y,vtz,vdz,zb1,szar,frac,
     &                addbid,vtzb,vtze,vdzb,vdze)
      include 'params.puf'
      include 'grid.puf'
      include 'csigma.puf'
      integer dgmseq,dgmid,dgmksam
      real x,y,vtz,vdz,zb1,szar,frac,addbid
      real vtzb,vtze,vdzb,vdze,tx,ty
      logical ldgm
      common /dgmrecur/ dgmseq,dgmid,dgmksam
      save ldgm
      data ldgm/.false./
      if(dgmseq.ne.16476.or.dgmid.ne.594.or.dgmksam.ne.5) return
      tx=(float(ibsamp)-0.5)*dgrid+20.0*delsam
      ty=(float(jbsamp)-0.5)*dgrid
      if(x.ne.tx.or.y.ne.ty) return
      if(.not.ldgm)then
         open(1921,file='dgm_h9_puff594_receptor21_1_sigtz.bin',
     &        access='stream',form='unformatted',status='replace')
         ldgm=.true.
      endif
      write(1921) dgmseq,dgmid,dgmksam,idoptzs,
     &       x,y,vtz,vdz,zb1,szar,frac,addbid,
     &       vtzb,vtze,vdzb,vdze,tsigws,els,tzisdr,uavgs
      return
      end
      subroutine dgmh9recvfloor(x,y,szar,addbid,sz0p,szr)
      include 'params.puf'
      include 'grid.puf'
      integer dgmseq,dgmid,dgmksam
      real x,y,szar,addbid,sz0p,szr,rawsz
      logical ldgm
      common /dgmrecur/ dgmseq,dgmid,dgmksam
      save ldgm
      data ldgm/.false./
      if(dgmseq.ne.16476.or.dgmid.ne.594.or.dgmksam.ne.5) return
      if(x.ne.((float(ibsamp)-0.5)*dgrid+20.0*delsam)) return
      if(y.ne.((float(jbsamp)-0.5)*dgrid)) return
      if(.not.ldgm)then
         open(1922,file='dgm_h9_puff594_receptor21_1_szfloor.bin',
     &        access='stream',form='unformatted',status='replace')
         ldgm=.true.
      endif
      rawsz=szar
      if(addbid.gt.0.0) rawsz=sqrt(szar**2+addbid)
      write(1922) dgmseq,dgmid,dgmksam,szar,addbid,rawsz,sz0p,szr
      return
      end
"""

# Isolate the THREE actual REAL4 ZRPOLE residual events at receiver (42,11).
# Original PUFRECS MCTADJ2 L5333-5359, after ZRPOLE is fully computed.
# This trace is write-only in a temporary instrumented original source copy.
H9_MCTADJ2_TRACE_NAME = "dgm_h9_mctadj2_receptor42_11.bin"
H9_MCTADJ2_RECORD = struct.Struct("<3i12f")
H9_MCTADJ2_LABELS = (
    "x","y","eltop","uavg","bvf","dsel","ze","dsh",
    "zrterr","zdiff","z","zrpole")
H9_MCTADJ2_HELPERS = """
c --- Original REAL4 terrain operands for exactly three H9 CALCPF events.
      subroutine dgmh9mctadj2(x,y,eltop,uavg,bvf,dsel,
     &                        ze,dsh,zrterr,zdiff,z,zrpole)
      include 'params.puf'
      include 'grid.puf'
      integer dgmseq,dgmid,dgmksam
      real x,y,eltop,uavg,bvf,dsel,ze,dsh,zrterr,zdiff,z,zrpole
      real tx,ty
      common /dgmrecur/ dgmseq,dgmid,dgmksam
      logical opened
      save opened
      data opened/.false./
      if(dgmseq.ne.16480.and.dgmseq.ne.16486.and.
     &   dgmseq.ne.16495) return
      tx=(float(ibsamp)-0.5)*dgrid+41.0*delsam
      ty=(float(jbsamp)-0.5)*dgrid+10.0*delsam
      if(x.ne.tx.or.y.ne.ty) return
      if(.not.opened)then
         open(1933,file='dgm_h9_mctadj2_receptor42_11.bin',
     &        form='unformatted',access='stream',status='replace')
         opened=.true.
      endif
      write(1933) dgmseq,dgmid,dgmksam,x,y,eltop,
     &            uavg,bvf,dsel,ze,dsh,zrterr,zdiff,z,zrpole
      return
      end
"""


def add_h9_mctadj2_trace(source: str) -> str:
    begin=source.lower().find("      subroutine pufrecs(")
    end=source.lower().find("      subroutine calcsl(",begin)
    if begin<0 or end<=begin:
        raise AssertionError("original PUFRECS scope changed")
    original=source[begin:end]
    # Match the terminal terrain branch and insert AFTER the entire
    # if(dsh.EQ.0.0) block. Never instrument unrelated MCTADJ users.
    anchor=("                  zrpole=z+dsh\n"
            "               endif\n"
            "            endif\n")
    if original.count(anchor)!=1:
        raise AssertionError("original PUFRECS MCTADJ2 terminal branch drifted")
    call=("             call dgmh9mctadj2(x,y,eltop,uavg,bvf,dsel,\n"
          "     &                           ze,dsh,zrterr,zdiff,z,zrpole)\n")
    original=original.replace(anchor,anchor+call)
    return source[:begin]+original+source[end:]+H9_MCTADJ2_HELPERS


def audit_h9_mctadj2_trace(path: Path, out: Path) -> None:
    if not path.is_file() or path.stat().st_size % H9_MCTADJ2_RECORD.size:
        raise AssertionError("original H9 MCTADJ2 trace missing/misaligned")
    samples=[]
    with path.open("rb") as fh:
        while block:=fh.read(H9_MCTADJ2_RECORD.size):
            seq,puff,ksam,*vals=H9_MCTADJ2_RECORD.unpack(block)
            if not all(math.isfinite(v) for v in vals):
                raise AssertionError("source H9 MCTADJ2 nonfinite operand")
            samples.append((seq,puff,ksam,vals))
    # MCTADJ2 trace is inside the original BVF>0 branch. A CALCPF
    # receptor contribution does NOT imply that branch was entered.
    # Preserve observed source keys and report missing ones explicitly;
    # never create an invented third source observation.
    requested=((16480,596,2),(16486,597,6),(16495,598,7))
    observed=tuple(row[:3] for row in samples)
    if not observed or any(key not in requested for key in observed) or (
        tuple(key for key in requested if key in observed)!=observed):
        raise AssertionError(f"unexpected H9 MCTADJ2 source physical keys: {observed}")
    missing=tuple(key for key in requested if key not in observed)
    print(f"P7_ORIGINAL_H9_MCTADJ2_COVERAGE"
          f" OBSERVED={observed} MISSING={missing}"
          " ABSENT_KEY_IS_NOT_ZERO_OR_PARITY")
    entries=[]
    for seq,puff,ksam,vals in samples:
        values=dict(zip(H9_MCTADJ2_LABELS,vals))
        bits={k:f"0x{struct.unpack('<I',struct.pack('<f',v))[0]:08x}"
              for k,v in values.items()}
        entries.append({"seq":seq,"puff":puff,"ksam":ksam,
                        "operands":values,"real4_bits":bits})
        print(f"P7_ORIGINAL_H9_MCTADJ2_TERRAIN"
              f" STEP={seq} PUFF={puff} KSAM={ksam}"
              + " ".join(f" {k.upper()}={v:.10g} BIT_{k.upper()}={bits[k]}"
                         for k,v in values.items())
              + " VENDOR_UNMODIFIED=YES NATIVE_PARITY=NOT_CLAIMED")
    out.write_text(json.dumps({
        "status":"ORIGINAL_H9_SOURCE_ONLY",
        "scope":"original PUFRECS MCTADJ2 (42,11), 3 REAL4 events",
        "events":entries,
        "requested_keys":requested,
        "observed_keys":observed,
        "missing_keys":missing,
        "coverage":"PARTIAL_SOURCE_ONLY" if missing else "FULL_SOURCE_ONLY",
        "trace_sha256":original.sha256_file(path),
        "vendor_source_sha256":original.ORIGINAL_CALPUFF_SHA256,
        "native_state_injected":False
    },indent=2)+"\n")


def add_h9_receptor_sigtz_trace(source: str) -> str:
    anchor = "            call sigtz(dum0,vdz,vtz,zb1,szar,dum1,dum2)"
    if source.count(anchor + "\n") != 1:
        raise AssertionError("H9 source PUFRECS SIGTZ anchor missing/drifted")
    call = ("            call dgmh9recvzt(x,y,vtz,vdz,zb1,szar,frac,\n"
            "     &                           addbid,vtzb1,vtze1,\n"
            "     &                           vdzb1,vdze1)\n")
    source=source.replace(anchor + "\n", anchor + "\n" + call)
    # The original also has an identical SZ0 floor in another routine
    # (calpuff.for L7099). Instrument ONLY PUFRECS L5272.
    begin=source.lower().find("      subroutine pufrecs(")
    end=source.lower().find("      subroutine calcsl(",begin)
    if begin<0 or end<begin:
        raise AssertionError("original PUFRECS/CALCSL boundaries changed")
    routine=source[begin:end]
    floor_anchor="      if(szr .LT. sz0(ipnum)) szr=sz0(ipnum)"
    if routine.count(floor_anchor + "\n") != 1:
        raise AssertionError("H9 PUFRECS unique SZ0 floor changed")
    floor_call=("      call dgmh9recvfloor(x,y,szar,addbid,\n"
                "     &                       sz0(ipnum),szr)\n")
    routine=routine.replace(floor_anchor + "\n",
                            floor_anchor + "\n" + floor_call)
    return source[:begin]+routine+source[end:]+H9_RECSIG_HELPERS


def audit_h9_receptor_floor(path: Path, out: Path) -> None:
    if not path.is_file() or path.stat().st_size != H9_RECFLOOR_RECORD.size:
        raise AssertionError("original H9 receptor SZ0 floor trace missing/misaligned")
    step,puff,ksam,szar,addbid,rawsz,sz0p,szr = H9_RECFLOOR_RECORD.unpack(
        path.read_bytes())
    if (step,puff,ksam)!=(16476,594,5):
        raise AssertionError("original H9 receptor SZ0 floor step key changed")
    def bits(v: float) -> str:
        return f"0x{struct.unpack('<I',struct.pack('<f',v))[0]:08x}"
    print("P7_ORIGINAL_H9_RECEPTOR_SZ0_FLOOR=SOURCE_ONLY"
          f" STEP={step} PUFF={puff} KSAM={ksam}"
          f" SZAR={szar:.10g} ADDBID={addbid:.10g}"
          f" RAW_SQRT={rawsz:.10g} SZ0={sz0p:.10g} SZREC={szr:.10g}"
          f" BIT_RAW={bits(rawsz)} BIT_SZ0={bits(sz0p)} BIT_SZREC={bits(szr)}"
          " UNMODIFIED_OUTPUT=YES")
    out.write_text(json.dumps({
        "status":"SOURCE_ONLY_NOT_NATIVE_PARITY",
        "step":step,"puff":puff,"ksam":ksam,
        "szar":szar,"addbid":addbid,"pre_floor_sz":rawsz,
        "sz0":sz0p,"post_floor_szrec":szr,
        "bits":{"pre_floor":bits(rawsz),"sz0":bits(sz0p),"szrec":bits(szr)},
        "sha256":original.sha256_file(path),
        "native_state_injected":False
    },indent=2)+"\n")


def audit_h9_receptor_sigtz(path: Path, out: Path) -> None:
    if not path.is_file() or path.stat().st_size != H9_RECSIG_RECORD.size:
        raise AssertionError("H9 original same-step PUFRECS SIGTZ trace missing/misaligned")
    rec = H9_RECSIG_RECORD.unpack(path.read_bytes())
    seq,puff,ksam,idopt,*values = rec
    if (seq,puff,ksam,idopt) != (16476,594,5,1):
        raise AssertionError("H9 original CALCPF receptor SIGTZ key/option changed")
    labels = ("x","y","vtz","vdz","zb1","szar","frac","addbid",
              "vtzb","vtze","vdzb","vdze","sigw","el","tzisdr","uavg")
    data = dict(zip(labels,values))
    if struct.unpack("<I",struct.pack("<f",data["frac"]))[0] != 0x3F000000:
        raise AssertionError("original H9 PUFRECS FRAC is not exactly 0.5")
    print("P7_ORIGINAL_H9_RECEPTOR_SIGTZ_SOURCE=PASS"
          f" GLOBAL_STEP={seq} PUFF={puff} KSAM={ksam} IDOPTZ={idopt}"
          + " ".join(f" {k.upper()}={v:.10g}" for k,v in data.items())
          + " ORIGINAL_VENDOR_OUTPUT_UNCHANGED=YES"
          " NATIVE_PARITY=NOT_CLAIMED")
    out.write_text(json.dumps({
        "scope":"original H9 PUFRECS receptor (21,1) source-only SIGTZ",
        "key":{"global_step":seq,"puff":puff,"ksam":ksam,"idoptz":idopt},
        "inputs":data, "source_sha256":original.ORIGINAL_CALPUFF_SHA256,
        "binary_sha256":original.sha256_file(path),
        "native_state_injected":False
    },indent=2)+"\n")

# The H9 first post-SZ0 mass residual is original puff598, KSAM8.
# Capture every original substep for this puff, without injecting any state.
H9_PUFF598_MASS_NAME = "dgm_h9_puff598_mass.bin"
H9_PUFF598_MASS_RECORD = struct.Struct("<3i5f")
H9_PUFF598_MASS_HELPERS = """
      subroutine dgmh9p598mass(qold,qnew,frac,vd,tsamp)
      integer dgmseq,dgmid,dgmksam
      real qold,qnew,frac,vd,tsamp
      logical ldgm
      common /dgmrecur/ dgmseq,dgmid,dgmksam
      save ldgm
      data ldgm/.false./
      if(dgmid.ne.598.or.dgmseq.lt.16420.or.dgmseq.gt.16679)
     &   return
      if(.not.ldgm)then
         open(1923,file='dgm_h9_puff598_mass.bin',
     &        access='stream',form='unformatted',status='replace')
         ldgm=.true.
      endif
      write(1923) dgmseq,dgmid,dgmksam,qold,qnew,frac,vd,tsamp
      return
      end
"""

def add_h9_puff598_mass_trace(source: str) -> str:
    anchor="            qnew(ipl)=qm(ipl,ii)"
    if source.count(anchor + "\n") != 1:
        raise AssertionError("source COMP QNEW after DRY anchor drift")
    call=("            if(ipl.eq.1) call dgmh9p598mass(\n"
          "     &                  qold(ipl),qnew(ipl),\n"
          "     &                  fracdry(ipl),vd(ipl),tsamp)\n")
    return source.replace(anchor + "\n",anchor + "\n"+call) + H9_PUFF598_MASS_HELPERS


def audit_h9_puff598_mass(path: Path, out: Path) -> None:
    if not path.is_file() or path.stat().st_size % H9_PUFF598_MASS_RECORD.size:
        raise AssertionError("original H9 puff598 mass trace absent/misaligned")
    rows=[]
    with path.open("rb") as fp:
        while block:=fp.read(H9_PUFF598_MASS_RECORD.size):
            seq,puff,ksam,*numbers=H9_PUFF598_MASS_RECORD.unpack(block)
            if not (16420<=seq<=16679 and puff==598 and 1<=ksam<=99):
                raise AssertionError("H9 puff598 original mass key corrupted")
            if rows and seq<=rows[-1][0]:
                raise AssertionError("H9 puff598 mass steps not chronological")
            rows.append((seq,ksam,numbers))
    if len(rows)<8:
        raise AssertionError("original puff598 mass trace is missing KSAM8 history")
    print("P7_ORIGINAL_H9_PUFF598_MASS_TRACE=SOURCE_ONLY"
          f" RECORDS={len(rows)} FIRST_STEP={rows[0][0]}"
          f" LAST_STEP={rows[-1][0]} UNMODIFIED_PUFF_CON=YES")
    for seq,ksam,v in rows[:12]:
        print(f"P7_ORIGINAL_H9_PUFF598_MASS STEP={seq} KSAM={ksam}"
              f" QOLD={v[0]:.10g} QNEW={v[1]:.10g}"
              f" FRACDRY={v[2]:.10g} VD={v[3]:.10g}"
              f" TSAMP={v[4]:.10g}")
    out.write_text(json.dumps({
        "scope":"original CALPUFF H9 puff598 source mass history",
        "status":"SOURCE_ONLY_NO_NATIVE_INJECTION",
        "count":len(rows),
        "rows":[{"step":i,"ksam":k,"qold":v[0],"qnew":v[1],
                 "fracdry":v[2],"vd":v[3],"tsamp":v[4]}
                for i,k,v in rows],
        "sha256":original.sha256_file(path)
    },indent=2)+"\n")


# Vendor VCBAR inputs and result, independently observed after the last
# VCOUP call and before DRY applies the Gaussian removal fraction.
H9_PUFF598_VCBAR_NAME = "dgm_h9_puff598_vcbar.bin"
H9_PUFF598_VCBAR_REC = struct.Struct("<3i7f")
H9_PUFF598_VCBAR_HELPERS = """
      subroutine dgmh9p598vbar(ip,f1,zb,ze,szb,szm,sze,lid)
      integer ip,dgmseq,dgmid,dgmksam
      real f1,zb,ze,szb,szm,sze,lid
      logical ldgm
      common /dgmrecur/ dgmseq,dgmid,dgmksam
      save ldgm
      data ldgm/.false./
      if(ip.ne.598.or.dgmseq.lt.16420.or.dgmseq.gt.16679)
     &   return
      if(.not.ldgm)then
         open(1924,file='dgm_h9_puff598_vcbar.bin',
     &        access='stream',form='unformatted',status='replace')
         ldgm=.true.
      endif
      write(1924) dgmseq,ip,dgmksam,f1,zb,ze,szb,szm,sze,lid
      return
      end
"""

def add_h9_puff598_vcbar_trace(source: str) -> str:
    anchor="            vcbar=vcbar+third*vcoup(icode,zgr,zp,sze1,hlid,hlidmax)"
    if source.count(anchor+"\n")!=1:
        raise AssertionError("original VCBAR final Gaussian VCOUP anchor drift")
    call=("            call dgmh9p598vbar(ip,vcbar,zb1,ze1,\n"
          "     &                           szb1,szm1,sze1,hlid)\n")
    return (source.replace(anchor+"\n",anchor+"\n"+call)
            +H9_PUFF598_VCBAR_HELPERS)


def audit_h9_puff598_vcbar(path: Path, out: Path) -> None:
    if not path.is_file() or path.stat().st_size%H9_PUFF598_VCBAR_REC.size:
        raise AssertionError("original H9 puff598 VCBAR trace missing/malformed")
    rows=[]
    with path.open("rb") as inp:
        while raw:=inp.read(H9_PUFF598_VCBAR_REC.size):
            seq,puff,ksam,*vals=H9_PUFF598_VCBAR_REC.unpack(raw)
            if not (16420<=seq<=16679 and puff==598 and 1<=ksam<=99):
                raise AssertionError("original H9 puff598 VCBAR key malformed")
            if rows and seq<=rows[-1]["seq"]:
                raise AssertionError("original H9 puff598 VCBAR order broken")
            fields=("vcbar","zb","ze","szb","szm","sze","lid")
            rows.append({"seq":seq,"ksam":ksam,**dict(zip(fields,vals))})
    if len(rows)!=8:
        raise AssertionError(f"original puff598 VCBAR records {len(rows)} not 8")
    for entry in rows:
        print("P7_ORIGINAL_H9_PUFF598_VCBAR=SOURCE_ONLY"
              + " ".join(f" {k.upper()}={v:.10g}" for k,v in entry.items()))
    out.write_text(json.dumps({
        "scope":"original H9 puff598 VCBAR input/output",
        "status":"SOURCE_ONLY_NOT_NATIVE_PARITY",
        "rows":rows,"sha256":original.sha256_file(path),
        "native_state_injected":False
    },indent=2)+"\n")


H9_Z_ANCHORS = (
    # Original SETPUF calpuff.for L48526-48534, BEFORE terrain or clipping.
    ("            call sigtz(sigzb(ii),zero,zero,zpb(ii),szb1,vtzb1,vdzb1)",
     1, "szb1,szm1,sze1,vtzb1,zero,zero,zero,zero"),
    ("            call sigtz(zero,dm,tm,zpb(ii),szm1,vtzm1,vdzm1)",
     2, "szb1,szm1,sze1,vtzb1,vtzm1,zero,tm,zero"),
    ("            call sigtz(zero,de,te,zpb(ii),sze1,vtze1,vdze1)",
     3, "szb1,szm1,sze1,vtzb1,vtzm1,vtze1,tm,te"),
    # Original SETPUF CTADJ2 state, after inverse-time correction.
    ("            call sigtz(szadj,zero,zero,zpb(ii),szm1,vtzm1,vdzm1)",
     4, "szb1,szm1,sze1,vtzb1,vtzm1,vtze1,tm,te"),
    ("            call sigtz(szadj,zero,zero,zpb(ii),sze1,vtze1,vdze1)",
     5, "szb1,szm1,sze1,vtzb1,vtzm1,vtze1,tm,te"),
    # Original SETPUF L48635-48639 monotonicity/stored sigma transition.
    ("         if(szm1.GT.sze1) sze1=szm1",
     6, "szb1,szm1,sze1,vtzb1,vtzm1,vtze1,tm,te"),
    ("         sigzb(ii)=sze1",
     7, "szb1,szm1,sze1,vtzb1,vtzm1,vtze1,tm,te"),
)

def add_h9_setpuf_trace(source: str) -> str:
    # Verify every exact Fortran statement once; abort instead of installing
    # the diagnostic in an unrelated SIGTZ call.
    for anchor, phase, fields in H9_Z_ANCHORS:
        if source.count(anchor + "\n") != 1:
            raise AssertionError(
                f"source SETPUF H9 trace anchor drift phase={phase} {anchor!r}")
        parts=fields.split(",")
        statement=(
            f"            call dgmh9z(ii,{phase},"
            + ",".join(parts[:4]) + ",\n"
            + "     &                " + ",".join(parts[4:]) + ")\n"
        )
        if phase==1:
            # SETPUF receives JDSTAB/TSIGV/TSIGW/EL as *call arguments*.
            # Record these BEFORE the first inversion; do not infer them
            # from COMP IPGT or from the original post-step DGM output.
            met_call=("            call dgmh9met(ii,jdstab,tsigv,tsigw,el)\n"
                      "            call dgmh9csigma(ii)\n")
            source=source.replace(anchor + "\n",
                                  met_call+anchor + "\n" + statement)
        else:
            source=source.replace(anchor + "\n",anchor + "\n" + statement)
    return source + H9_Z_HELPERS + H9_MET_HELPERS + H9_SIGMA_HELPERS

def audit_h9_csigma_trace(path: Path, out: Path) -> None:
    if not path.is_file() or path.stat().st_size % H9_SIGMA_RECORD.size:
        raise AssertionError("original H9 /CSIGMA/ data missing/misaligned")
    rows=[]
    with path.open("rb") as inp:
        while raw:=inp.read(H9_SIGMA_RECORD.size):
            ii,idoptzs,packed,tsigws,els,tzisdr,uavgs=H9_SIGMA_RECORD.unpack(raw)
            if ii!=588 or packed!=202200108:
                raise AssertionError("original source /CSIGMA/ trace key mismatch")
            rows.append((idoptzs,tsigws,els,tzisdr,uavgs))
    if not rows:
        raise AssertionError("no original H9 /CSIGMA/ source state")
    for idoptzs,tsigws,els,tzisdr,uavgs in rows[:5]:
        print("P7_ORIGINAL_H9_EFFECTIVE_CSIGMA=SOURCE_ONLY"
              f" IDOPTZS={idoptzs} TSIGWS={tsigws:.10g}"
              f" ELS={els:.10g} TZISDR={tzisdr:.10g}"
              f" UAVGS={uavgs:.10g}"
              " NATIVE_CSIGMA_PARITY=OPEN")
    out.write_text(json.dumps({
        "scope":"original effective H9 /CSIGMA/ consumed by SIGTZ",
        "values":rows,"source_sha256":original.ORIGINAL_CALPUFF_SHA256,
        "trace_sha256":original.sha256_file(path),
        "native_solver_inputs_unchanged":True
    },indent=2)+"\n")

def audit_h9_met_trace(path: Path, out: Path) -> None:
    if not path.is_file() or path.stat().st_size % H9_MET_RECORD.size:
        raise AssertionError("original H9 SETPUF met input trace missing/misaligned")
    rows=[]
    with path.open("rb") as handle:
        while raw:=handle.read(H9_MET_RECORD.size):
            ii,jdstab,packed,tsigv,tsigw,el=H9_MET_RECORD.unpack(raw)
            # Original's JDSTAB is captured before imposing the native
            # SWMIN index contract. It may be an upstream regime code,
            # a valid sentinel, or a mismatched source type; print first.
            if ii!=588 or packed!=202200108:
                raise AssertionError(
                    f"bad original SETPUF trace identity ii={ii}"
                    f" packed={packed} jdstab_raw={jdstab}"
                    f" sigw={tsigw:.9g} el={el:.9g}")
            rows.append((jdstab,tsigv,tsigw,el))
    if not rows:
        raise AssertionError("no original H9 SETPUF incoming met rows")
    for jdstab,tsigv,tsigw,el in rows[:5]:
        print(f"P7_ORIGINAL_H9_SETPUF_TURBSET_INPUT=SOURCE_ONLY"
              f" JDSTAB={jdstab} TSIGV={tsigv:.10g}"
              f" TSIGW={tsigw:.10g} EL={el:.10g}"
              " NATIVE_PHYSICS_PARITY=OPEN")
    out.write_text(json.dumps({
        "scope":"vendor original H9 puff588 SETPUF call-input meteorology",
        "rows":rows,"sha256":original.sha256_file(path),
        "original_vendor_modified":False,
        "native_state_injected":False},indent=2)+"\n")

def audit_h9_setpuf_trace(path: Path, out: Path) -> None:
    if not path.is_file() or path.stat().st_size % H9_Z_RECORD.size:
        raise AssertionError("original H9 SETPUF trace missing/misaligned")
    rows=[]
    with path.open("rb") as handle:
        while raw:=handle.read(H9_Z_RECORD.size):
            phase,ii,packed,*values=H9_Z_RECORD.unpack(raw)
            if ii!=588 or packed!=202200108 or phase not in range(1,8):
                raise AssertionError("invalid source H9 SETPUF trace identity")
            rows.append((phase,values))
    if len(rows)<7 or [r[0] for r in rows[:7]]!=list(range(1,8)):
        raise AssertionError("source H9 puff588 phase order not complete")
    labels=("SZB","SZM","SZE","VTZB","VTZM","VTZE","TM","TE")
    def r4bits(x: float) -> str:
        return f"0x{struct.unpack('<I',struct.pack('<f',x))[0]:08x}"
    for phase,values in rows[:7]:
        print(
            f"P7_ORIGINAL_H9_SETPUF_Z_PHASE={phase} PUFF=588 "
            + " ".join(f"{label}={value:.10g} BIT_{label}={r4bits(value)}"
                       for label,value in zip(labels,values)))
    out.write_text(json.dumps({
        "status": "ORIGINAL_H9_SOURCE_ONLY", "phase_order": list(range(1,8)),
        "record_count": len(rows),
        "record_bytes": H9_Z_RECORD.size,
        "binary_sha256": original.sha256_file(path),
        "first_complete_step": [
            {"phase":phase, **{k:v for k,v in zip(labels,values)}}
            for phase,values in rows[:7]
        ],
        "native_state_injected": False,
        "vendor_source_unchanged": True
    },indent=2)+"\n")
    print(f"P7_ORIGINAL_H9_SETPUF_Z_TRACE=PASS ROWS={len(rows)}"
          " STAGES=1,2,3,4,5,6,7"
          " ORIGINAL_PUFF_CON_AND_DGM=UNCHANGED"
          " NATIVE_H9_PARITY=OPEN")



def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vendor", type=Path, required=True)
    ap.add_argument("--case", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--compiler", default="gfortran-11")
    ap.add_argument("--hour", type=int, choices=(1, 2, 4, 9), default=1)
    ap.add_argument("--receptor-i", type=int, default=None)
    ap.add_argument("--receptor-j", type=int, default=None)
    ap.add_argument("--trace-h9-setpuf", action="store_true")
    ap.add_argument(
        "--allow-no-receptor-events", action="store_true",
        help="H9 source-only diagnostic: record an absent CALCPF receiver trace "
             "without claiming sampled receptor parity; corrupt traces still fail",
    )
    args = ap.parse_args()
    vendor, case, out = (p.resolve() for p in (args.vendor, args.case, args.out))
    defaults = {1:(19,50), 2:(25,28), 4:(47,13), 9:(13,1)}
    di,dj=defaults[args.hour]
    ix = args.receptor_i if args.receptor_i is not None else di
    jy = args.receptor_j if args.receptor_j is not None else dj
    if not (1 <= ix <= 50 and 1 <= jy <= 50):
        raise ValueError("Hefei original receptor coordinates outside frozen grid")
    first_seq, final_seq = {1:(1,1275),2:(1276,3517),4:(5424,7555),9:(16420,16679)}[args.hour]
    last_puff = {1:54,2:137,4:272,9:618}[args.hour]
    trace_name = (f"dgm_calcpf_h3_{ix}_{jy}.bin" if args.hour == 1 else
                  f"dgm_calcpf_h3_{ix}_{jy}_hour{args.hour}.bin")
    source_helpers = (EXTRA_HELPERS
        .replace("if(dgmseq.gt.1275) return",
                 f"if(dgmseq.lt.{first_seq}.or.dgmseq.gt.{final_seq}) return")
        .replace("if(isamp.ne.19.or.jsamp.ne.50.or.ipol.ne.1) return",
                 f"if(isamp.ne.{ix}.or.jsamp.ne.{jy}.or.ipol.ne.1) return")
        .replace("dgm_calcpf_h3_19_50.bin",trace_name))
    if source_helpers.count(f"if(dgmseq.lt.{first_seq}.or.dgmseq.gt.{final_seq}) return") != 2 or \
       source_helpers.count(f"if(isamp.ne.{ix}.or.jsamp.ne.{jy}.or.ipol.ne.1) return") != 2:
        raise AssertionError("original receiver instrumentation guards not exact")
    # Avoid write-only Fortran I/O unit aliasing between diagnostic helpers.
    # A collision silently overwrites other traces and can masquerade as a
    # physical mismatch without changing the frozen vendor puff.con output.
    helpers=(EXTRA_HELPERS,H9_Z_HELPERS,H9_MET_HELPERS,H9_SIGMA_HELPERS,
             H9_RECSIG_HELPERS,H9_MCTADJ2_HELPERS,
             H9_PUFF598_MASS_HELPERS,H9_PUFF598_VCBAR_HELPERS)
    open_units=[]
    for helper in helpers:
        open_units.extend(int(u) for u in re.findall(
            r"(?im)^\s*open\((\d+),",helper))
    if len(open_units)!=len(set(open_units)):
        raise AssertionError(f"original diagnostic Fortran I/O unit collision: {open_units}")
    print(f"P7_ORIGINAL_WRITE_ONLY_FORTRAN_UNIT_CONFLICT=NONE UNITS={sorted(open_units)}")
    # The base extraction records original source assertions at each COMP
    # insertion and independently pins both original Fortran source hashes.
    original.CALLS["item7_setpuf_return"] += (
        "            call dgmreceiverstep(ii,ksam)\n"
    )
    original.instrument(vendor, out)
    instrumented = out / "calpuff_instrumented.for"
    source = instrumented.read_text(encoding="latin-1")
    if source.count(CALCPF_ANCHOR) != 1:
        raise AssertionError("original CALCPF mass-weighting anchor changed")
    source = source.replace(CALCPF_ANCHOR + "\n",
                            CALCPF_ANCHOR + "\n" + CALL)
    if args.trace_h9_setpuf:
        source=add_h9_setpuf_trace(source)
        source=add_h9_receptor_sigtz_trace(source)
        source=add_h9_mctadj2_trace(source)
        source=add_h9_puff598_mass_trace(source)
        source=add_h9_puff598_vcbar_trace(source)
    instrumented.write_text(source + source_helpers, encoding="latin-1")

    alias = original._alias_tree(vendor, out / "include-alias")
    executable = out / "bin" / "puff-h3-receiver.x"
    original._build(args.compiler, vendor / "modules.for", instrumented,
                    alias, executable)
    staged = out / "case"
    original._stage_case(case, staged)
    run = staged / "run" / "puff"
    try:
        result = original._run(executable, run)
    except SystemExit:
        vendor_log = run / "puff_runtime.log"
        if vendor_log.exists():
            print("P7_ORIGINAL_CALCPF_INSTRUMENTED_VENDOR_RUNTIME_TAIL_BEGIN",
                  file=sys.stderr)
            print(vendor_log.read_text(errors="replace")[-8000:],
                  file=sys.stderr)
            print("P7_ORIGINAL_CALCPF_INSTRUMENTED_VENDOR_RUNTIME_TAIL_END",
                  file=sys.stderr)
        raise
    if result["puff_con_sha256"] != original.TARGET_PUFF_CON_SHA256:
        raise AssertionError(
            "original CALPUFF receiver instrumentation changed puff.con: "
            + result["puff_con_sha256"])
    dgm = run / "dgm_puffstep.bin"
    if original.sha256_file(dgm) != DGM_SHA or dgm.stat().st_size != 254687 * 352:
        raise AssertionError("original 143h DGM changed under CALCPF instrumentation")
    if args.trace_h9_setpuf:
        audit_h9_mctadj2_trace(
            run / H9_MCTADJ2_TRACE_NAME,
            out / "original-h9-mctadj2-receptor42-11.json")
        audit_h9_puff598_vcbar(run / H9_PUFF598_VCBAR_NAME,
                              out / "original-h9-puff598-vcbar.json")
        audit_h9_puff598_mass(run / H9_PUFF598_MASS_NAME,
                             out / "original-h9-puff598-mass.json")
        audit_h9_receptor_floor(
            run / H9_RECFLOOR_NAME,
            out / "original-h9-puff594-receptor21-1-szfloor.json")
        audit_h9_receptor_sigtz(
            run / H9_RECSIG_NAME,
            out / "original-h9-puff594-receptor21-1-sigtz.json")
        audit_h9_setpuf_trace(run / H9_Z_TRACE_NAME,
                             out / "original-h9-puff588-setpuf-z.json")
        audit_h9_met_trace(run / H9_MET_TRACE_NAME,
                           out / "original-h9-puff588-setpuf-met.json")
        audit_h9_csigma_trace(run / H9_SIGMA_TRACE_NAME,
                             out / "original-h9-puff588-effective-csigma.json")
    trace = run / trace_name
    # A receptor may have no contributing CALCPF events in a selected hour.
    # That is not the same as a malformed diagnostic file, and it does NOT
    # establish zero concentration or native numerical equivalence.
    if trace.is_file() and trace.stat().st_size % (RECORD.size + 16):
        raise AssertionError("misaligned original CALCPF H3 trace")
    if not trace.is_file() or trace.stat().st_size == 0:
        if not (args.allow_no_receptor_events and args.hour == 9):
            raise AssertionError("missing or empty original CALCPF H3 trace")
        audit = {
            "scope": f"original CALPUFF hour {args.hour} H3 receptor ({ix},{jy}), source-only",
            "status": "NO_CALCPF_RECEIVER_EVENTS_RECORDED",
            "vendor_sha256": original.ORIGINAL_CALPUFF_SHA256,
            "frozen_puff_con_sha256": result["puff_con_sha256"],
            "frozen_dgm_sha256": original.sha256_file(dgm),
            "records": 0,
            "trace_path": None,
            "numeric_native_parity": "NOT_CLAIMED",
            "original_hourly_receptor_concentration": "NOT_CHECKED",
        }
        (out / f"original-calcpf-h3-{ix}-{jy}-hour{args.hour}.json").write_text(
            json.dumps(audit, indent=2) + "\n")
        print("P7_ORIGINAL_H3_CALCPF_RECEIVER_NO_EVENTS=SOURCE_ONLY"
              f" HOUR={args.hour} RECEPTOR_I={ix} RECEPTOR_J={jy}"
              " RECORDS=0 ORIGINAL_PUFF_CON_AND_DGM=UNCHANGED"
              " NATIVE_PARITY=NOT_CLAIMED")
        return
    samples = []
    with trace.open("rb") as fd:
        while chunk := fd.read(RECORD.size):
            if len(chunk) != RECORD.size:
                raise AssertionError("truncated H-3 receptor record")
            fraction_block = fd.read(16)
            if len(fraction_block) != 16:
                raise AssertionError("missing paired PUFRECS fraction record")
            seq, puff, ksam, *values = RECORD.unpack(chunk)
            vseq, vid, vksam, frec = struct.unpack("<3if",fraction_block)
            if (seq,puff,ksam)!=(vseq,vid,vksam):
                raise AssertionError("original CALCPF stage/virtual identity mismatch")
            if not (first_seq <= seq <= final_seq and 1 <= puff <= last_puff and
                    1 <= ksam <= 99 and all(math.isfinite(x) for x in values+[frec])):
                raise AssertionError("original CALCPF key or value corrupted")
            samples.append((seq, puff, ksam, values))
            if len(samples) <= 8:
                print(f"P7_VENDOR_H3_PUFRECS_FRAC SEQ={vseq}"
                      f" II={vid} KSAM={vksam} FRAC={frec:.9g}")
    if not samples:
        raise AssertionError("original first-hour H3 hotspot never sampled")
    if any(a[0] >= b[0] for a, b in zip(samples, samples[1:])):
        raise AssertionError("original receiver substep trace order incorrect")
    total = sum(v[12] for _, _, _, v in samples)
    audit = {
        "scope": f"original CALPUFF hour {args.hour} H3 receptor ({ix},{jy}), source-only",
        "vendor_sha256": original.ORIGINAL_CALPUFF_SHA256,
        "frozen_puff_con_sha256": result["puff_con_sha256"],
        "frozen_dgm_sha256": original.sha256_file(dgm),
        "records": len(samples),
        "record_bytes": RECORD.size,
        "trace_sha256": original.sha256_file(trace),
        "trace_path": str(trace),
        "projection_fraction_layout": "paired 3i13f CALCPF stage + 3i1f original FREC in unit97 stream",
        "first_receptor_contribution": {
            "seq": samples[0][0], "puff": samples[0][1],
            "ksam": samples[0][2],
            **dict(zip(FIELD_NAMES, samples[0][3])),
        },
        "trace_contribution_sum": total,
        "numeric_native_parity": "NOT_CLAIMED",
    }
    (out / (f"original-calcpf-h3-19-50.json" if args.hour==1 and ix==19 and jy==50 else
            f"original-calcpf-h3-{ix}-{jy}-hour{args.hour}.json")).write_text(
        json.dumps(audit, indent=2) + "\n")
    print("P7_ORIGINAL_H3_CALCPF_RECEIVER_ORACLE=PASS"
          f" HOUR={args.hour} RECEPTOR_I={ix} RECEPTOR_J={jy}"
          f" SAMPLES={len(samples)}"
          f" FIRST_STEP={samples[0][0]}"
          f" SOURCE_CONC_SUM={total:.9g}"
          " CONCENTRATION_REFERENCE_UNCHANGED=YES"
          " FULL_DGM_REFERENCE_UNCHANGED=YES"
          " NATIVE_PUFRECS_STAGE_PARITY=OPEN")
    for seq, puff, ksam, values in samples[:12]:
        print(f"P7_VENDOR_H3_CALCPF_FIRST_STEPS"
              f" SEQ={seq} II={puff} KSAM={ksam} "
              + " ".join(f"{name}={value:.9g}"
                         for name, value in zip(FIELD_NAMES, values)))


if __name__ == "__main__":
    main()

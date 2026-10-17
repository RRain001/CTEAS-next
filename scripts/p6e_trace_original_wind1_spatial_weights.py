#!/usr/bin/env python3
"""Original CALMET v6.5.0 WIND1 first-hour two-station RSQWT forensic.

Write-only source insertion immediately after WIND1's RSQWT normalization.
Compare its literal REAL*4 grid weights with the live C++ producer's separately
recorded normalized RSQWT. The frozen original CALMET.DAT SHA-256 must match.
This is NOT a new physics approximation and does NOT change tolerance gates.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"native_cpp/modules/p6_calmet/reference"))
import original_internal_state_dump as oracle

NX=NY=50
RECORD="<2i2f"
REC_BYTES=struct.calcsize(RECORD)
FIELDS={"surface":"wind1_rsqwt_surface_2022-01-01_01.f32",
        "upper":"wind1_rsqwt_upper_2022-01-01_01.f32",
        "vvw_surface1":"wind1_vvw_surface1_2022-01-01_01.f32",
        "vvw_upper1":"wind1_vvw_upper1_2022-01-01_01.f32",
        "vvw_before_surface1":"wind1_vvw_before_surface1_2022-01-01_01.f32",
        "vvw_before_upper1":"wind1_vvw_before_upper1_2022-01-01_01.f32"}
SOURCE_ROUTINE=r"""
c --- Write-only first-hour WIND1 normalized station weights, 50x50x2.
c --- No assignments to any source CALMET physical model variables.
      subroutine p6e_rsquwt_first(i,j,nstat,rsqwt)
      include 'params.met'
      include 'grid.met'
      integer i,j,nstat
      real rsqwt(mxwnd)
      logical done,opened
      save done,opened
      data done/.false./,opened/.false./
      if(done)return
      if(nstat.ne.2) stop 'P6E_FORENSIC_BAD_WIND1_NSTAT'
      if(.not.opened)then
        open(97,file='p6e_wind1_rsqwt_first.bin',
     1       form='unformatted',access='stream',status='replace')
        opened=.true.
      endif
      write(97) i,j,rsqwt(1),rsqwt(2)
      if(i.eq.nx.and.j.eq.ny)then
        close(97)
        done=.true.
      endif
      return
      end
c --- Write-only final first-layer WIND1 weights after BIAS/upper-missing
c --- reallocation, before barrier and wind accumulation.
      subroutine p6e_vvw_first(i,j,nstat,vvw)
      include 'params.met'
      include 'grid.met'
      integer i,j,nstat
      real vvw(mxnz,mxwnd)
      logical done,opened
      save done,opened
      data done/.false./,opened/.false./
      if(done)return
      if(nstat.ne.2) stop 'P6E_FORENSIC_BAD_VVW_NSTAT'
      if(.not.opened)then
        open(96,file='p6e_wind1_vvw_first.bin',
     1       form='unformatted',access='stream',status='replace')
        opened=.true.
      endif
      write(96) i,j,vvw(1,1),vvw(1,2)
      if(i.eq.nx.and.j.eq.ny)then
        close(96)
        done=.true.
      endif
      return
      end
c --- Stage probe directly before original upper-missing VVW redistribution.
      subroutine p6e_vvw_before_first(i,j,nstat,vvw)
      include 'params.met'
      include 'grid.met'
      integer i,j,nstat
      real vvw(mxnz,mxwnd)
      logical done,opened
      save done,opened
      data done/.false./,opened/.false./
      if(done)return
      if(nstat.ne.2)stop 'P6E_FORENSIC_BAD_PREVVW_NSTAT'
      if(.not.opened)then
        open(98,file='p6e_wind1_vvw_before_first.bin',
     1       form='unformatted',access='stream',status='replace')
        opened=.true.
      endif
      write(98) i,j,vvw(1,1),vvw(1,2)
      if(i.eq.nx.and.j.eq.ny)then
        close(98)
        done=.true.
      endif
      return
      end
"""

def checksum(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def patched(original:Path,target:Path):
    if checksum(original)!=oracle.ORIGINAL_CALMET_SHA256:
        raise ValueError("upstream CALMET Fortran checksum drift")
    lines=original.read_text().splitlines(keepends=True)
    if (lines[36250].strip().lower()!="end do" or
        "rsqwt(l)=rsqwt(l)*sumwt" not in lines[36249].replace(" ","").lower()):
        raise ValueError("WIND1 source RSQWT normalization anchor changed")
    if lines[36347].strip().replace(" ","").lower()!="if(nbar.le.0)goto91":
        raise ValueError("original WIND1 VVW redistribution anchor changed")
    # In descending original source order: pre-VVW then post-VVW, then RSQWT.
    if "do 222 k=1,nz" not in lines[36325].strip().lower():
        raise ValueError("original upper missing-data redistribution anchor changed")
    lines.insert(36347,"      call p6e_vvw_first(i,j,nstat,vvw)\n")
    lines.insert(36325,"      call p6e_vvw_before_first(i,j,nstat,vvw)\n")
    lines.insert(36251,"      call p6e_rsquwt_first(i,j,nstat,rsqwt)\n")
    target.write_text("".join(lines)+SOURCE_ROUTINE)

def original_weights(path:Path):
    raw=path.read_bytes()
    if len(raw)!=NX*NY*REC_BYTES:
        raise ValueError(f"source WIND1 first-hour weight size {len(raw)} != {NX*NY*REC_BYTES}")
    actual={}
    for offset in range(0,len(raw),REC_BYTES):
        i,j,s,u=struct.unpack_from(RECORD,raw,offset)
        if not(1<=i<=NX and 1<=j<=NY) or (i,j) in actual:
            raise ValueError(f"source WIND1 RSQWT spatial index invalid/duplicate: {(i,j)}")
        actual[(i,j)]=(s,u)
    if len(actual)!=NX*NY:
        raise ValueError("original WIND1 RSQWT missing grid cells")
    return actual

def read_native(path:Path):
    raw=path.read_bytes()
    if len(raw)!=NX*NY*4:
        raise ValueError(f"native normalized REAL4 weight size mismatch {path}")
    return struct.unpack("<2500f",raw)

def compare(source,candidate:Path):
    native={k:read_native(candidate/v) for k,v in FIELDS.items()}
    result={k:{"first_nonzero":None,"nonzero":0,"max_abs":0.0,"sum_squared":0.0,
               "max_ulps":0} for k in FIELDS}
    for j in range(1,NY+1):
        for i in range(1,NX+1):
            index=(j-1)*NX+(i-1)
            for field,col,phase in (("surface",0,"rsqwt"),
                                    ("upper",1,"rsqwt"),
                                    ("vvw_surface1",0,"vvw"),
                                    ("vvw_upper1",1,"vvw"),
                                    ("vvw_before_surface1",0,"vvw_before"),
                                    ("vvw_before_upper1",1,"vvw_before")):
                ref=source[phase][(i,j)][col];test=native[field][index]
                if not(math.isfinite(ref) and math.isfinite(test)):
                    raise ValueError("nonfinite WIND1 source/native normalized weights")
                delta=abs(ref-test)
                result[field]["sum_squared"]+=delta*delta
                result[field]["max_abs"]=max(result[field]["max_abs"],delta)
                if delta!=0.0:
                    result[field]["nonzero"]+=1
                    if result[field]["first_nonzero"] is None:
                        result[field]["first_nonzero"]={
                            "i":i,"j":j,"original":ref,"native":test,"abs":delta}
                # Positive normalized weights have monotonic uint32 bit order.
                bits=lambda x:struct.unpack("<I",struct.pack("<f",x))[0]
                result[field]["max_ulps"]=max(
                    result[field]["max_ulps"],abs(bits(ref)-bits(test)))
    for x in result.values():
        x["rms"]=math.sqrt(x.pop("sum_squared")/(NX*NY))
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--vendor",type=Path,required=True)
    p.add_argument("--case",type=Path,required=True)
    p.add_argument("--native-diagno",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--compiler",default="gfortran-11")
    args=p.parse_args()
    vendor=args.vendor.resolve()
    if checksum(vendor/"calutils.for")!=oracle.ORIGINAL_CALUTILS_SHA256:
        raise ValueError("original CALMET support source changed")
    work=args.out.resolve().parent/"p6e-original-rsqwt"
    work.mkdir(parents=True,exist_ok=True)
    edited=work/"calmet_instrumented.for"
    patched(vendor/"calmet.for",edited)
    includes=oracle._alias_tree(vendor,work/"includes")
    exe=work/"bin/original-calmet-rsqwt.x"
    oracle._build(args.compiler,edited,includes,exe)
    staged=work/"case"
    if staged.exists():shutil.rmtree(staged)
    oracle._stage_case(args.case.resolve(),staged)
    run_dir=staged/"run/met"
    source_run=oracle._run(exe,run_dir)
    if source_run["met_dat_sha256"]!=oracle.TARGET_MET_DAT_SHA256:
        raise ValueError("forensic insert changed frozen original CALMET.DAT")
    source=run_dir/"p6e_wind1_rsqwt_first.bin"
    vvw=run_dir/"p6e_wind1_vvw_first.bin"
    pre_vvw=run_dir/"p6e_wind1_vvw_before_first.bin"
    if not source.is_file():raise FileNotFoundError(source)
    if not vvw.is_file():raise FileNotFoundError(vvw)
    if not pre_vvw.is_file():raise FileNotFoundError(pre_vvw)
    fields=compare({"rsqwt":original_weights(source),
                    "vvw":original_weights(vvw),
                    "vvw_before":original_weights(pre_vvw)},
                   args.native_diagno.resolve())
    if all(v["nonzero"]==0 for v in fields.values()):
        status="MATCH_ALL_WEIGHT_BITS"
    elif fields["surface"]["nonzero"]==0 and fields["upper"]["nonzero"]==0:
        status=("MATCH_BEFORE_MISSING_REBALANCE_BUT_FINAL_VVW_DRIFT" if
                not fields["vvw_before_surface1"]["nonzero"] and
                not fields["vvw_before_upper1"]["nonzero"]
                else "VVW_PRE_REBALANCE_DRIFT")

    else:
        status="REAL4_RSQWT_DRIFT"
    report={
        "status":status,"scope":"original and native first-hour WIND1 RSQWT and final layer-one VVW",
        "hours_compared":1,"grid":[NX,NY],"stations":2,
        "fields":fields,
        "source_calmet_sha256":oracle.ORIGINAL_CALMET_SHA256,
        "source_modified_sha256":checksum(edited),
        "source_weight_trace_sha256":checksum(source),
        "source_reweighted_vvw_trace_sha256":checksum(vvw),
        "source_before_reweight_vvw_trace_sha256":checksum(pre_vvw),
        "frozen_met_sha256":source_run["met_dat_sha256"],
        "weight_was_never_read_back_into_native":True,
        "full_p6e_science":"NOT_CLAIMED"
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()

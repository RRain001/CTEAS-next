#!/usr/bin/env python3
"""Forensic 143-hour original CALMET INTER2 layer-1 first-divergence gate.

The original vendor calmet.for is never edited: a SHA-pinned write-only copy
takes surface/upper US/VS(1,:) just before INTER2 output, and U/V level one
immediately after both INTER2 calls. Original MET.DAT must remain bitwise
identical to the frozen 2022 reference. Native P6D station and INTER2 fields
are independent. This is DIAGNOSTIC, not complete native P6D acceptance.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"native_cpp/modules/p6_calmet/reference"))
import original_internal_state_dump as vendor_audit

NX=NY=50
NH=143
PLANE=2500
HEADER="<5i4f"
H_SIZE=struct.calcsize(HEADER)
REC_SIZE=H_SIZE+4*PLANE*4
SLOPE_HEADER='<5i'
SLOPE_RECORD=struct.calcsize(SLOPE_HEADER)+2*PLANE*4
# This helper only READS original COMMON state, then writes its own file;
# it does not modify the original arrays, calls, or output stream.
HELPER=r"""
c --- P6D source-locked write-only layer-1 INTER2 chain trace
      subroutine dgmfirstlayer1
      include 'params.met'
      include 'gen.met'
      include 'grid.met'
      include 'd1.met'
      integer i,j
      logical opened
      save opened
      data opened/.false./
      if(.not.opened)then
         open(94,file='dgm_inter2_layer1.bin',
     1        form='unformatted',access='stream',status='replace')
         opened=.true.
      endif
      write(94) 12,ndathrb,nsecb,nx,ny
      write(94) us(1,1),vs(1,1),us(1,2),vs(1,2)
      write(94) ((u(i,j,1),i=1,nx),j=1,ny)
      write(94) ((v(i,j,1),i=1,nx),j=1,ny)
c --- Before INTER2: the corrected FRADJ+SLOPE first-guess UG/VG.
      write(94) ((ug(i,j,1),i=1,nx),j=1,ny)
      write(94) ((vg(i,j,1),i=1,nx),j=1,ny)
      return
      end
c --- Independent source pre/post SLOPE wind stage. Write-only, does
c --- not change COMMON arrays or frozen original CALMET.DAT bytes.
      subroutine dgmfirstlayer1wind(stage)
      include 'params.met'
      include 'gen.met'
      include 'grid.met'
      include 'd1.met'
      integer i,j,stage
      logical opened
      save opened
      data opened/.false./
      if(.not.opened)then
         open(95,file='dgm_slope_layer1.bin',
     1        form='unformatted',access='stream',status='replace')
         opened=.true.
      endif
      write(95) stage,ndathrb,nsecb,nx,ny
      write(95) ((ug(i,j,1),i=1,nx),j=1,ny)
      write(95) ((vg(i,j,1),i=1,nx),j=1,ny)
      return
      end
c --- Write-only neutral SIMILT station profile, at WIND1's own local
c --- USTMP/VSTMP before spatial 1/r^2 weighting. No model arrays changed.
      subroutine dgmwind1neutral(ustmp,vstmp)
      include 'params.met'
      include 'gen.met'
      include 'grid.met'
      real ustmp(mxnz,mxwnd),vstmp(mxnz,mxwnd)
      integer k
      logical opened
      save opened
      data opened/.false./
      if(.not.opened)then
         open(93,file='dgm_wind1_neutral.bin',
     1        form='unformatted',access='stream',status='replace')
         opened=.true.
      endif
      write(93) 15,ndathrb,nsecb,nz
      write(93) (ustmp(k,1),k=1,nz)
      write(93) (vstmp(k,1),k=1,nz)
      return
      end
"""
STATION_COLS=("surface_u","surface_v","upper_u","upper_v")
TOL={
    "surface_u":(2.e-5,1.e-5),"surface_v":(2.e-5,1.e-5),
    "upper_u":(2.e-5,1.e-5),"upper_v":(2.e-5,1.e-5),
    "wind1_u":(1.e-4,1.e-5),"wind1_v":(1.e-4,1.e-5),
    "before_slope_u":(1.e-4,1.e-5),"before_slope_v":(1.e-4,1.e-5),
    "after_slope_u":(1.e-4,1.e-5),"after_slope_v":(1.e-4,1.e-5),
    "pre_inter2_u":(1.e-4,1.e-5),"pre_inter2_v":(1.e-4,1.e-5),
    "inter2_u":(1.e-4,1.e-5),"inter2_v":(1.e-4,1.e-5)
}
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def label(hour):
    return (dt.datetime(2022,1,1)+dt.timedelta(hours=hour)).strftime("%Y-%m-%d_%H")
def patch_vendor(original,target):
    if digest(original)!=vendor_audit.ORIGINAL_CALMET_SHA256:
        raise RuntimeError("unaltered original calmet.for provenance drift")
    lines=original.read_text().splitlines(keepends=True)
    if (lines[6054].strip()!="CALL INTER2(US,NWIND,UTMXST,UTMYST," or
        lines[6058].strip()!="CALL INTER2(VS,NWIND,UTMXST,UTMYST," or
        lines[6071].strip()!="ENDIF" or
        "Lake breeze region" not in lines[6075]):
        raise RuntimeError("original INTER2 call-order insertion anchors changed")
    if ("if (ISLOPE.EQ.1)CALL SLOPE" not in lines[5721] or
        "300 CONTINUE" not in lines[5731] or
        lines[5589].strip().lower() != "call wind1"):
        raise RuntimeError("original slope-phase insertion anchors changed")
    # The original WIND1 station profile is captured after the vertical
    # extrapolation loop, before any 1/r^2 grid interpolation.
    if "666" not in lines[36198] or "continue" not in lines[36198].lower():
        raise RuntimeError("original WIND1 station profile source anchor changed")
    # Insert in reverse source-order so original line indices remain fixed.
    lines.insert(36199,"      call dgmwind1neutral(ustmp,vstmp)\n")
    # Before the SLOPE call and after the UG/VG+=USLOPE/VSLOPE loop.
    lines.insert(6072,"      call dgmfirstlayer1\n")
    lines.insert(5732,"      call dgmfirstlayer1wind(14)\n")
    lines.insert(5721,"      call dgmfirstlayer1wind(13)\n")
    # First wind first-guess is recorded after original WIND1 and before
    # WINDBC/TOPOF2/FRADJ/SLOPE; this discriminates source of any new drift.
    lines.insert(5590,"      call dgmfirstlayer1wind(11)\n")
    target.write_text("".join(lines)+HELPER)
def read_orig(path):
    raw=path.read_bytes()
    if len(raw)!=NH*REC_SIZE:
        raise RuntimeError(f"original layer-1 record count/shape mismatch: {len(raw)}")
    for h in range(NH):
        begin=h*REC_SIZE
        kind,packed,second,nx,ny,*station=struct.unpack_from(HEADER,raw,begin)
        time=dt.datetime(2022,1,1)+dt.timedelta(hours=h)
        stamp=time.year*100000+time.timetuple().tm_yday*100+time.hour
        if (kind,packed,second,nx,ny)!=(12,stamp,0,NX,NY):
            raise RuntimeError(f"source INTER2 sequence/size/hour mismatch {h+1}")
        u=struct.unpack_from("<2500f",raw,begin+H_SIZE)
        v=struct.unpack_from("<2500f",raw,begin+H_SIZE+PLANE*4)
        ug=struct.unpack_from("<2500f",raw,begin+H_SIZE+2*PLANE*4)
        vg=struct.unpack_from("<2500f",raw,begin+H_SIZE+3*PLANE*4)
        yield dict(zip(STATION_COLS,station))|{
            "inter2_u":u,"inter2_v":v,
            "pre_inter2_u":ug,"pre_inter2_v":vg}
def read_slope_original(path):
    raw=path.read_bytes()
    if len(raw)!=NH*3*SLOPE_RECORD:
        raise RuntimeError(f"original WIND1/pre/post-SLOPE record count drift: {len(raw)}")
    result=[]
    for h in range(NH):
        fields={}
        for pass_idx,kind in enumerate((11,13,14)):
            start=(3*h+pass_idx)*SLOPE_RECORD
            marker,packed,second,nx,ny=struct.unpack_from(SLOPE_HEADER,raw,start)
            time=dt.datetime(2022,1,1)+dt.timedelta(hours=h)
            stamp=time.year*100000+time.timetuple().tm_yday*100+time.hour
            if (marker,packed,second,nx,ny)!=(kind,stamp,0,NX,NY):
                raise RuntimeError(f"original SLOPE phase/hour/shape mismatch: hour {h+1} stage {kind}")
            pos=start+struct.calcsize(SLOPE_HEADER)
            prefix=("wind1_" if kind==11 else
                    "before_slope_" if kind==13 else "after_slope_")
            fields[prefix+"u"]=struct.unpack_from("<2500f",raw,pos)
            fields[prefix+"v"]=struct.unpack_from("<2500f",raw,pos+PLANE*4)
        result.append(fields)
    return result

def read_native_grid(path):
    raw=path.read_bytes()
    if len(raw)!=9*PLANE*4:
        raise RuntimeError(f"native INTER2 3D field shape drift: {path}")
    return struct.unpack_from("<2500f",raw)
def read_wind1_neutral_source(path):
    raw=path.read_bytes()
    record_bytes=16+18*4
    if len(raw)!=NH*record_bytes:
        raise RuntimeError(f"original 143h WIND1 neutral profile shape mismatch: {len(raw)}")
    result=[]
    for h in range(NH):
        start=h*record_bytes
        kind,packed,second,nz=struct.unpack_from("<4i",raw,start)
        time=dt.datetime(2022,1,1)+dt.timedelta(hours=h)
        stamp=time.year*100000+time.timetuple().tm_yday*100+time.hour
        if (kind,packed,second,nz)!=(15,stamp,0,9):
            raise RuntimeError(f"original WIND1 station profile time/header drift {h+1}")
        result.append(struct.unpack_from("<18f",raw,start+16))
    return result

def compare_wind1_neutral_source(original_file,native_dir,require_neutral):
    paths=[native_dir/f"wind1_neutral_profile_{label(h)}.f32" for h in range(1,NH+1)]
    count=sum(p.is_file() for p in paths)
    if count==0 and not require_neutral:
        return {"status":"NOT_CAPTURED_IN_LEGACY_NATIVE_ARTIFACT"}
    if count!=NH:
        raise RuntimeError(f"missing source-vs-native WIND1 neutral profile trace: {count}/{NH}")
    originals=read_wind1_neutral_source(original_file)
    stats={part:{"nonzero":0,"max_abs":0.,"rms":0.,"first_nonzero":None}
           for part in ("u","v")}
    for h,(original,path) in enumerate(zip(originals,paths),1):
        raw=path.read_bytes()
        if len(raw)!=18*4:
            raise RuntimeError(f"native WIND1 neutral profile float32 shape drift {path}")
        actual=struct.unpack("<18f",raw)
        for k,(ref,val) in enumerate(zip(original,actual)):
            if not math.isfinite(ref) or not math.isfinite(val):
                raise RuntimeError(f"nonfinite WIND1 neutral profile hour {h}")
            key="u" if k<9 else "v"
            layer=(k%9)+1
            delta=abs(ref-val)
            st=stats[key]
            st["rms"]+=delta*delta
            st["max_abs"]=max(st["max_abs"],delta)
            if delta:
                st["nonzero"]+=1
                if st["first_nonzero"] is None:
                    st["first_nonzero"]={"hour":h,"level":layer,
                                         "original":ref,"native":val,"abs":delta}
    for st in stats.values():
        st["rms"]=math.sqrt(st["rms"]/(NH*9))
    return {"status":"COMPARED_143H_WRITE_ONLY_SOURCE",
            "source_trace_sha256":digest(original_file),
            "fields":stats,"hours":NH,"levels":9,
            "no_original_input_into_native":True}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--vendor",type=Path,required=True)
    ap.add_argument("--case",type=Path,required=True)
    ap.add_argument("--candidate",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--compiler",default="gfortran-11")
    ap.add_argument("--require-parity",action="store_true")
    ap.add_argument("--require-neutral-profile",action="store_true")
    a=ap.parse_args()
    vendor=a.vendor.resolve();case=a.case.resolve();native=a.candidate.resolve()
    if digest(vendor/"calutils.for")!=vendor_audit.ORIGINAL_CALUTILS_SHA256:
        raise RuntimeError("original CALMET calutils.for checksum drift")
    work=a.out.resolve().parent/"firstlayer-fortran"
    work.mkdir(parents=True,exist_ok=True)
    trace_source=work/"calmet_firstlayer.for"
    patch_vendor(vendor/"calmet.for",trace_source)
    alias=vendor_audit._alias_tree(vendor,work/"includes")
    exe=work/"bin"/"met-original-with-firstlayer-writeonly.x"
    vendor_audit._build(a.compiler,trace_source,alias,exe)
    staged=work/"case"
    if staged.exists():
        shutil.rmtree(staged)
    vendor_audit._stage_case(case,staged)
    run_dir=staged/"run/met"
    result=vendor_audit._run(exe,run_dir)
    if result["met_dat_sha256"]!=vendor_audit.TARGET_MET_DAT_SHA256:
        raise RuntimeError("write-only original instrumentation changed frozen MET.DAT bytes")
    source=run_dir/"dgm_inter2_layer1.bin"
    if not source.is_file():
        raise RuntimeError("original INTER2 first-layer trace absent")
    slope_source=run_dir/"dgm_slope_layer1.bin"
    if not slope_source.is_file():
        raise RuntimeError("original pre/post-SLOPE first-layer trace absent")
    orig_slopes=read_slope_original(slope_source)
    original_neutral=run_dir/"dgm_wind1_neutral.bin"
    if not original_neutral.is_file():
        raise RuntimeError("original WIND1 neutral source capture absent")
    neutral_report=compare_wind1_neutral_source(
        original_neutral,native,a.require_neutral_profile)
    with (native/"station_inter2_layer1.csv").open(newline="") as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=NH or list(rows[0])!=["hour_end",*STATION_COLS]:
        raise RuntimeError("native first-layer station input stream mismatch")
    stats={k:{"compared":0,"exceedances":0,"max_abs":0.,
              "first_exceedance":None,"worst":None,"hour_exceedances":{},
              "source_and_native_both_missing":0,
              "nonzero_values":0,"first_nonzero":None,
              "sum_squared_difference":0.0}
           for k in TOL}
    for h,orig in enumerate(read_orig(source),1):
        orig.update(orig_slopes[h-1])
        actual_row=rows[h-1]
        if actual_row["hour_end"]!=label(h):
            raise RuntimeError("native station INTER2 hour-end label drift")
        for field in TOL:
            reference=orig[field]
            native_name=(field.replace("pre_inter2_","slope_corrected_")
                          .replace("after_slope_","slope_corrected_")
                          if field.startswith(("pre_inter2_","after_slope_")) else field)
            if field.startswith("before_slope_"):
                comp=field[len("before_slope_"):]
                # In this coupled second pass FRADJ may be inactive, in which
                # case WIND1 is the exact prior stage. Never use the source
                # field to supply the native stage.
                correction=native/f"fradj_corrected_{comp}_{label(h)}.f32"
                native_name=("fradj_corrected_" if correction.is_file()
                             else "wind1_")+comp
            got=(struct.unpack("<f",struct.pack("<f",float(actual_row[field])))[0]
                 if field in STATION_COLS else
                 read_native_grid(native/f"{native_name}_{label(h)}.f32"))
            rr=(reference,) if field in STATION_COLS else reference
            nn=(got,) if field in STATION_COLS else got
            abstol,reltol=TOL[field]
            st=stats[field]
            for n,(ref,val) in enumerate(zip(rr,nn)):
                if not(math.isfinite(ref) and math.isfinite(val)):
                    raise RuntimeError(f"nonfinite source/candidate {field} hour {h}")
                # The original sets EDIT=999, EDITL=900 (calmet.for L5185).
                # This C++ selected case represents invalid upper-layer
                # observations as 999999 with editl=999998. Both are missing:
                # INTER2 excludes each by its own EDITL. Compare their
                # missingness semantics, not the raw sentinel magnitudes.
                st["compared"]+=1
                if field.startswith("upper_") and ref>=900. and val>=999998.:
                    st["source_and_native_both_missing"]+=1
                    continue
                delta=abs(ref-val)
                if delta != 0.0:
                    st["nonzero_values"]+=1
                    st["sum_squared_difference"]+=delta*delta
                    if st["first_nonzero"] is None:
                        st["first_nonzero"]={"hour":h,"cell":n+1,"i":n%NX+1,
                                            "j":n//NX+1,"original":ref,
                                            "native":val,"abs":delta}
                if delta>st["max_abs"]:
                    st["max_abs"]=delta
                    st["worst"]={"hour":h,"i":n%NX+1,"j":n//NX+1,
                                 "original":ref,"native":val,"abs":delta}
                if delta>abstol+reltol*abs(ref):
                    st["exceedances"]+=1
                    st["hour_exceedances"][str(h)]=st["hour_exceedances"].get(str(h),0)+1
                    if st["first_exceedance"] is None:
                        st["first_exceedance"]={"hour":h,"i":n%NX+1,"j":n//NX+1,
                                                "original":ref,"native":val,"abs":delta}
    for field,st in stats.items():
        if st["compared"]!=(NH if field in STATION_COLS else NH*PLANE):
            raise RuntimeError(f"incomplete native original INTER2 field {field}")
    failed=[k for k,v in stats.items() if v["exceedances"]]
    stage_priority=("surface_u","surface_v","upper_u","upper_v",
                    "wind1_u","wind1_v",
                    "before_slope_u","before_slope_v",
                    "after_slope_u","after_slope_v",
                    "pre_inter2_u","pre_inter2_v","inter2_u","inter2_v")
    first_nonzero=min(
        (dict(stage=key,**stats[key]["first_nonzero"]) for key in stage_priority
         if stats[key]["first_nonzero"] is not None),
        key=lambda item:(item["hour"],stage_priority.index(item["stage"])),
        default=None)
    for record in stats.values():
        compared_valid=record["compared"]-record["source_and_native_both_missing"]
        record["rms_difference"]=math.sqrt(
            record.pop("sum_squared_difference")/compared_valid) if compared_valid else 0.
    report={
        "status":"PASS_FIRST_LAYER_INTER2_SOURCE_143H" if not failed else
                 "FAIL_FIRST_LAYER_INTER2_SOURCE_143H",
        "first_failing_fields":failed,
        "first_nonzero_source_stage":first_nonzero,
        "note":"exact nonzero source drift is diagnostic, not an independent tolerance failure; source parity uses unchanged thresholds",
        "first_failing_hour":min((v["first_exceedance"]["hour"] for v in stats.values()
                                  if v["first_exceedance"]),default=None),
        "source_instrumented_sha256":digest(trace_source),
        "source_original_sha256":vendor_audit.ORIGINAL_CALMET_SHA256,
        "frozen_met_dat_sha256":result["met_dat_sha256"],
        "trace_file_sha256":digest(source),
        "original_pre_post_slope_trace_sha256":digest(slope_source),
        "wind1_neutral_profile_source_check":neutral_report,
        "no_original_intermediate_injected_into_native":True,
        "levels_compared":[1],"hours":NH,"grid":[NX,NY],
        "stage":"DIAGNO original after-WIND1 UG/VG, pre-SLOPE UG/VG, post-SLOPE UG/VG, post-INTER2 U/V + station US/VS layer1",
        "missing_data_policy":"Original EDITL=900, EDIT=999 vs native EDITL=999998, EDIT=999999: both invalid upper-layer values compare as semantically missing; no numeric acceptance claim for missing data",
        "fields":stats,"tolerances":TOL,
        "full_143h_UVW_pass":False}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print("WIND1_NEUTRAL_PROFILE_SOURCE_CHECK",json.dumps(neutral_report))
    print(json.dumps({"status":report["status"],
                      "first_failing_hour":report["first_failing_hour"],
                      "summary":{k:{"max_abs":v["max_abs"],"exceedances":v["exceedances"],
                                     "first":v["first_exceedance"],"worst":v["worst"],
                                     "hour_exceedances":v["hour_exceedances"],
                                     "nonzero_values":v["nonzero_values"],
                                     "first_nonzero":v["first_nonzero"],
                                     "rms_difference":v["rms_difference"]}
                                 for k,v in stats.items()}},indent=2))
    if a.require_parity and failed:
        raise SystemExit(1)
if __name__=="__main__":
    main()
#!/usr/bin/env python3
"""Pinned vendor COMP WATER→LAND MIXHT→AVEMIX six-hour state provenance.

Write-only original Fortran scratch instrumentation. No source equations,
station inputs, full original MET output or native execution are changed.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from hashlib import sha256
import json,math,struct,subprocess,tempfile
from pathlib import Path

BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
NX,NY,NH=82,85,6
NC=NX*NY
NAME="s4r1c8e-original-comp-stages.bin"
HEAD=struct.Struct("<5i")
PLANE=struct.Struct("<"+str(2*NC)+"f")
ROW=HEAD.size+PLANE.size
STAGES=(1,2,3)
PINS={
    4691:"      if (itprog .eq. 0) then",
    4692:"        call mixht(el,ustar,qh,nx,ny,rho,nhrzb,nearu,iupt,",
    4693:"     1             ilandu,iwat1,iwat2,ldbhr,imixh,zi,ziconv)",
    4700:"",
    4715:"         call avemix(nx,ny,mnmdav,hafang,dgrid,u(1,1,ilevzi),",
    4716:"     1    v(1,1,ilevzi),zi,ziconv)",
    4717:"      endif",
    4719:"c",
}
def sha(p:Path)->str:return sha256(p.read_bytes()).hexdigest()
def pinned(path:Path)->list[str]:
    blob=subprocess.run(["git","hash-object",str(path)],
                        check=True,text=True,capture_output=True).stdout.strip()
    if blob!=BLOB:raise ValueError("original CALMET vendor blob drift")
    rows=path.read_text().splitlines(keepends=True)
    for ln,expected in PINS.items():
        if expected and rows[ln-1].rstrip("\n")!=expected:
            raise ValueError(f"original MIXHT/AVEMIX source line {ln} drift")
    return rows
def card(stage:int)->str:
    return (
        "      open(unit=89,file='s4r1c8e-original-comp-stages.bin',\n"
        "     1 form='unformatted',access='stream',status='unknown',\n"
        "     2 position='append')\n"
        f"      write(89) 58,nhrze,{stage},nx,ny\n"
        "      write(89) ((zi(i,j),i=1,nx),j=1,ny)\n"
        "      write(89) ((ziconv(i,j),i=1,nx),j=1,ny)\n"
        "      close(unit=89)\n"
    )
def prepare(vendor:Path,destination:Path,receipt:Path)->None:
    rows=pinned(vendor)
    # L4691: previous COMP/WATER state immediately before LAND MIXHT.
    # L4701: LAND MIXHT finished, AVEMIX not entered.
    # L4719: AVEMIX completed, before next stage.
    inserts={4691:card(1),4701:card(2),4719:card(3)}
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text("".join(inserts.get(i,"")+x
                                   for i,x in enumerate(rows,1)))
    receipt.parent.mkdir(parents=True,exist_ok=True)
    receipt.write_text(json.dumps({
        "status":"PREPARED_SHA_PINNED_WRITE_ONLY_COMP_STAGE_SNAPSHOTS",
        "source_vendor_git_blob":BLOB,
        "source_vendor_sha256":sha(vendor),
        "instrumented_scratch_sha256":sha(destination),
        "at_original_line_before":{"before_land_mixht":4691,
                                   "after_land_mixht":4701,
                                   "after_avemix":4719},
        "source_physics_changed":False,
        "native_mixht_avemix_accepted":False,
    },indent=2,sort_keys=True)+"\n")
    print("S4R1C8E_ORIGINAL_COMP_STAGE_SOURCE_PIN=PASS")
def decode(path:Path):
    raw=path.read_bytes()
    if len(raw)!=NH*len(STAGES)*ROW:
        raise ValueError("original COMP stage source record count/size invalid")
    data={}
    for hour in range(2,8):
        for stage in STAGES:
            off=((hour-2)*len(STAGES)+stage-1)*ROW
            head=HEAD.unpack_from(raw,off)
            if head!=(58,hour,stage,NX,NY):
                raise ValueError(f"original COMP stage clock/order wrong {head}")
            vals=PLANE.unpack_from(raw,off+HEAD.size)
            if not all(math.isfinite(x) and 0<=x<=100000 for x in vals):
                raise ValueError("original COMP ZI/ZICONV nonfinite/negative")
            data[hour,stage]=(vals[:NC],vals[NC:])
    return data
def verify(vendor:Path,geo:Path,pristine:Path,scratch:Path,trace:Path,report:Path)->None:
    pinned(vendor)
    if sha(pristine)!=sha(scratch):
        raise ValueError("original COMP stage trace changed six-hour 45-field MET bytes")
    from native_cpp.reference.compare_p3_makegeo_dynamic import parse_geo
    grid=parse_geo(geo,nx=NX,ny=NY,zone=50,hem="N",
                   x0=426.590,y0=3464.125,dx=1.)
    water={k for k,v in enumerate(grid["category"]) if 50<=int(v)<=55}
    if len(water)!=63:raise ValueError("original 63 WATER GEO cells not reproduced")
    data=decode(trace)
    # MIXHT is LAND-only. It must not mutate pre-existing selected
    # neutral WATER ZI/ZICONV; AVEMIX, however, averages the entire grid.
    water_transition=0
    land_transition=0
    mean_stage={}
    for h in range(2,8):
        prior=data[h,1]
        land=data[h,2]
        avg=data[h,3]
        for i in range(NC):
            for col in range(2):
                if i in water and land[col][i]!=prior[col][i]:
                    water_transition+=1
                if i not in water and land[col][i]!=prior[col][i]:
                    land_transition+=1
        mean_stage[str(h)]={
            "pre_land_mixht":sum(prior[0])/NC,
            "post_land_mixht_pre_avemix":sum(land[0])/NC,
            "post_avemix":sum(avg[0])/NC,
            "water_post_avemix_zi_changed":sum(
                avg[0][i]!=land[0][i] for i in water),
        }
    if water_transition:
        raise ValueError("original LAND MIXHT altered WATER state before AVEMIX")
    if not land_transition:
        raise ValueError("original LAND MIXHT changed zero cells in six hours")
    report.parent.mkdir(parents=True,exist_ok=True)
    result={
        "status":"PASS_ORIGINAL_NOAA_WATER_TO_LAND_MIXHT_TO_AVEMIX_SOURCE_ONLY",
        "vendor_git_blob":BLOB,"original_trace_sha256":sha(trace),
        "original_pristine_sha256":sha(pristine),
        "original_scratch_sha256":sha(scratch),
        "original_6h_45_met_byte_identical":True,
        "source_hour_numbers":[2,3,4,5,6,7],
        "stage_order":[1,2,3],
        "original_water_cells":len(water),"original_land_cells":NC-len(water),
        "original_water_changes_from_land_mixht":water_transition,
        "original_land_changed_component_cells_by_mixht":land_transition,
        "stage_summary":mean_stage,
        "native_g53_water_pre_avemix_comparison":"NOT_RUN",
        "native_land_mixht_avemix":"NOT_ACCEPTED",
        "native_g26_45fields":"NOT_ACCEPTED",
        "p7":"NOT_ACCEPTED",
    }
    report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("S4R1C8E_ORIGINAL_COMP_6H_STAGE_CHAIN=PASS_SOURCE_ONLY")
    print("S4R1C8E_ORIGINAL_6H45_MET=BYTE_IDENTICAL")
    print("S4R1C8E_WATER_UNCHANGED_BY_LAND_MIXHT=PASS")
    print("S4R1C8E_LAND_MIXHT_CHANGED_COMPONENTS="+str(land_transition))
    print("S4R1C8E_G26_P7=NOT_ACCEPTED")
def selftest()->None:
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/NAME
        with p.open("wb") as f:
            for h in range(2,8):
                for st in STAGES:
                    f.write(HEAD.pack(58,h,st,NX,NY))
                    f.write(PLANE.pack(*([100.]*2*NC)))
        assert len(decode(p))==18
        corrupted=bytearray(p.read_bytes())
        corrupted[8]=8
        p.write_bytes(corrupted)
        try:decode(p)
        except ValueError:pass
        else:raise AssertionError("accepted forged stage identity")
    print("S4R1C8E_ORIGINAL_STAGE_SCHEMA_NEGATIVE=PASS")
def main()->None:
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    for cmd,keys in (("prepare",("vendor","destination","receipt")),
                     ("verify",("vendor","geo","pristine","scratch","trace","report"))):
        q=sub.add_parser(cmd)
        for k in keys:q.add_argument("--"+k,type=Path,required=True)
    sub.add_parser("selftest")
    a=p.parse_args()
    if a.mode=="prepare":prepare(a.vendor,a.destination,a.receipt)
    elif a.mode=="verify":verify(a.vendor,a.geo,a.pristine,a.scratch,a.trace,a.report)
    else:selftest()
if __name__=="__main__":main()

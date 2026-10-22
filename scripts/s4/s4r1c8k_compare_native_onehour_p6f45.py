#!/usr/bin/env python3
"""Independent original-vs-native genuine NOAA one-hour P6F CALMET.DAT gate.

Original untouched six-hour weather file is consumed AFTER original-free
native G59 output. The existing frozen P6F serializer owns binary layout,
this external audit checks source clocks, 45 labels, all static provenance,
43 REAL4 numerical tolerances and two exact INTEGER4 fields.
"""
from __future__ import annotations
import argparse,json,math,struct
from pathlib import Path
from scripts.s4.s4r1c8i_compare_noaa_43_real_p6f import (
    NX,NY,NZ,NC,F32,INT,LABELS,REAL_LABELS,
    original_hour,fortran_records,sha,tol
)
def layout(path:Path,expected_hours:int):
    records=fortran_records(path.read_bytes())
    if len(records)<10 or len(records[0])!=96 or (
        records[0][:16].decode("ascii").strip()!="CALMET.DAT"
        or records[0][16:32].decode("ascii").strip()!="2.1"):
        raise ValueError("G59 invalid native/original CALMET.DAT declaration")
    (ncomment,)=struct.unpack("<i",records[1])
    if not 0<=ncomment<=10000:
        raise ValueError("G59 CALMET comments count invalid")
    ctl=records[ncomment+2]
    if len(ctl)!=176:raise ValueError("G59 original P6F header control absent")
    irlg,irtype,nx,ny,nz=struct.unpack_from("<5i",ctl,48)
    iwfcod,nss,nus,nps=struct.unpack_from("<4i",ctl,80)
    if (irlg,irtype,nx,ny,nz,iwfcod,nss,nus,nps)!=(
            expected_hours,1,NX,NY,NZ,1,2,1,0):
        raise ValueError("G59 original P6F geometry or source-station mismatch")
    statics=[]
    hourly=[]
    for r in records[ncomment+3:]:
        if len(r)<24:raise ValueError("G59 truncated original P6F field")
        label=r[:8].decode("ascii")
        times=struct.unpack_from("<4i",r,8)
        if times[0]==0 and times[2]==0:
            if hourly:raise ValueError("G59 static field after hourly output")
            statics.append(r)
        else:
            if len(r)!=24+4*NC:
                raise ValueError("G59 hourly REAL4/INT4 extent invalid")
            hourly.append((label,times,r[24:]))
    if len(hourly)!=45*expected_hours:
        raise ValueError("G59 expected 45 original fields in each source hour")
    groups=[hourly[i:i+45] for i in range(0,len(hourly),45)]
    for g in groups:
        if [x[0] for x in g]!=LABELS:
            raise ValueError("G59 original OUTHR physical field order shifted")
        if len({x[1] for x in g})!=1:
            raise ValueError("G59 nonhomogeneous original same-hour clock")
        clock=g[0][1]
        if clock[0]!=clock[2] or clock[1]!=0 or clock[3]!=3600:
            raise ValueError("G59 original hour seconds/original OUTHR interval wrong")
    if groups[0][0][1][0]!=202215201:
        raise ValueError("G59 first genuine NOAA model hour shifted")
    return {"statics":statics,"groups":groups,"metadata":(ncomment,irlg)}
def compare(original:Path,native:Path,native_log:Path,
            accepted43:Path,accepted2:Path,report:Path):
    proof43=json.loads(accepted43.read_text())
    proof2=json.loads(accepted2.read_text())
    if(proof43.get("status")!="PASS_SOURCE_SCOPED_REAL_NOAA_NATIVE_P6F_43_REAL_FIELDS"
       or proof43.get("above_tolerance")!=0
       or proof43.get("original_full_six_hour_met_sha256")!=sha(original)
       or proof2.get("status")!="PASS_SOURCE_SCOPED_REAL_NOAA_TWO_P6F_INTEGERS"
       or proof2.get("not_equal")!=0
       or proof2.get("source_unmodified_original_6h_met_sha256")!=sha(original)):
        raise ValueError("G59 previous original-native real/integer science gates missing")
    native_marker=native_log.read_text()
    if("S4R1C8K_REAL_NOAA_NATIVE_P6F_45FILE=PRODUCED_UNVERIFIED" not in native_marker
       or "FORTRAN_HOURLY_INJECTION=FALSE" not in native_marker
       or "G14_SIXHOUR_P7=NOT_ACCEPTED" not in native_marker):
        raise ValueError("G59 native physical 45 output source not proven")
    source=layout(original,6)
    candidate=layout(native,1)
    source_static=source["statics"]
    candidate_static=candidate["statics"]
    if len(source_static)!=len(candidate_static):
        raise ValueError("G59 complete original static field inventory differs")
    static_fail=[]
    for a,b in zip(source_static,candidate_static,strict=True):
        if a[:8]!=b[:8] or len(a)!=len(b) or a[8:]!=b[8:]:
            static_fail.append(a[:8].decode("ascii",errors="replace"))
    if static_fail:
        raise ValueError("G59 source native statics differ from untouched original: "+
                         ",".join(static_fail[:12]))
    ref=source["groups"][0]
    cand=candidate["groups"][0]
    bad=0;fields={}
    samples=[]
    for (label,clock,raw),(other,other_clock,native_raw) in zip(
            ref,cand,strict=True):
        if label!=other or clock!=other_clock:
            raise ValueError("G59 source original hourly label/clock mismatch")
        if label in ("IPGT    ","IRH     "):
            original_values=INT.unpack(raw);native_values=INT.unpack(native_raw)
        else:
            original_values=F32.unpack(raw);native_values=F32.unpack(native_raw)
        above=0;maximum=0.
        for i,(a,b) in enumerate(zip(original_values,native_values,strict=True)):
            if label in ("IPGT    ","IRH     "):
                different=(a!=b);d=abs(a-b)
            else:
                if not math.isfinite(a) or not math.isfinite(b):
                    raise ValueError("G59 nonfinite original/native 45 real")
                d=abs(a-b)
                different=d>tol(label,a,b)
            if different:
                above+=1
                if len(samples)<25:
                    samples.append({"label":label,"i":i%NX+1,"j":i//NX+1,
                                    "original":a,"native":b,"delta":d})
            maximum=max(maximum,d)
        fields[label.strip()]={"n":NC,"above_tolerance":above,"max_abs":maximum}
        bad+=above
    verdict={
        "status":("PASS_SCOPED_NATIVE_NOAA_45_RECORD_FIRSTHOUR_FILE" if bad==0 else
                  "FAIL_NATIVE_NOAA_ONE_HOUR_P6F_45_FIELD_NUMERIC"),
        "source_original_sixhour_sha256":sha(original),
        "native_firsthour_p6f_sha256":sha(native),
        "source_only_original_output_injected":False,
        "native_legal_p6f_2_1_file":True,
        "source_static_fields":len(source_static),
        "source_static_fields_byte_identical":True,
        "hourly_fields":45,
        "firsthour_values_checked":45*NC,
        "real_values_checked":43*NC,"integer_values_checked":2*NC,
        "above_frozen_tolerance":bad,
        "fields":fields,"sample_failures":samples,
        "actual_g14_six_hour_causal":"NOT_ACCEPTED",
        "P6_full":"NOT_ACCEPTED","P7":"NOT_ACCEPTED",
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(verdict,indent=2,sort_keys=True)+"\n")
    print("S4R1C8K_NATIVE_REAL_NOAA_P6F45="+verdict["status"])
    print("S4R1C8K_45_RECORD_ABOVE_TOLERANCE="+str(bad))
    print("S4R1C8K_G14_SIXHOUR_P7=NOT_ACCEPTED")
    return bad==0
def main():
    p=argparse.ArgumentParser()
    for k in ("original","native","native-log","accepted43","accepted2","report"):
        p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args()
    if not compare(a.original,a.native,a.native_log,a.accepted43,a.accepted2,a.report):
        raise SystemExit(3)
if __name__=="__main__":main()

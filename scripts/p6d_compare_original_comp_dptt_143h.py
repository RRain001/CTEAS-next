#!/usr/bin/env python3
"""Read-only REAL*4 full-grid 143h CALMET COMP /TJMP/ DPTT parity bisection.

Original point 2: DPTT immediately before COMP MIXHT, after station
STHEOR->ELUSTR2->MIXHTST has had an opportunity to modify /TJMP/.
Original point 3: DPTT immediately after COMP MIXHT, before AVEMIX.
Native candidate is generated from P6D wind, P6D station ELUSTR2 flux
and P6E MIXHT state without injecting any original meteorological field.
"""
import argparse,hashlib,json,math,struct
from pathlib import Path

SOURCE_SHA="e6b8ab309f81ddc3015dc750272eeb2ee8289a2d34563b364884d9e443be6ece"
NC=2500
SHAPE=143*NC
COUNTS={1:5,2:2,3:3,4:2,5:2}
TOL=(0.002,1.e-5)
STATION=25+25*50
def src_decode(path):
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=SOURCE_SHA:
        raise RuntimeError("original COMP source-provenance SHA drift")
    offset=0
    point2=[];point3=[]
    for hour in range(1,144):
        for kind,columns in COUNTS.items():
            if offset+32>len(data):
                raise RuntimeError("truncated original COMP header")
            stamp=struct.unpack_from("<8i",data,offset)
            if (stamp[0],stamp[1],stamp[6],stamp[7])!=(kind,hour,50,50):
                raise RuntimeError(f"original record hour/order/shape drift {hour}/{kind}")
            offset+=32
            if kind in (2,3):
                column=1 if kind==2 else 2
                arr=struct.unpack_from("<2500f",data,offset+column*NC*4)
                if kind==2:point2.extend(arr)
                else:point3.extend(arr)
            offset+=columns*NC*4
    if offset!=len(data) or len(point2)!=SHAPE or len(point3)!=SHAPE:
        raise RuntimeError("source truncated/surplus COMP hours")
    return {"PRE_MIXHT_DPTT_K":point2,"POST_MIXHT_DPTT_K":point3}
def read_native(prefix):
    meta=json.loads(Path(str(prefix)+".state.json").read_text())
    if meta.get("producer")!="p6e_calmet_dat21 emit-realcase" or "dptt" not in meta.get("fields",[]):
        raise RuntimeError("native COMP provenance missing")
    ret={}
    for field,fname in (("PRE_MIXHT_DPTT_K",".pre_mixht.dptt.f32"),
                        ("POST_MIXHT_DPTT_K",".dptt.f32")):
        data=Path(str(prefix)+fname).read_bytes()
        if len(data)!=SHAPE*4:raise RuntimeError(f"native COMP DPTT shape drift {field}")
        ret[field]=struct.unpack("<357500f",data)
    return ret,meta
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--native-prefix",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--require-parity",action="store_true")
    args=p.parse_args()
    source=src_decode(args.source)
    native,meta=read_native(args.native_prefix)
    stats={}
    for field,reference in source.items():
        current=native[field]
        info={"all":{"max_abs":0.0,"first_exceedance":None,"exceedances":0,"compared":0},
              "station":{"max_abs":0.0,"first_exceedance":None,"exceedances":0,"compared":0},
              "non_station":{"max_abs":0.0,"first_exceedance":None,"exceedances":0,"compared":0}}
        for ix,(a,b) in enumerate(zip(reference,current)):
            if not math.isfinite(a) or not math.isfinite(b):
                raise RuntimeError(f"nonfinite DPTT at record {ix}")
            h=ix//NC+1
            station=ix%NC==STATION
            e=abs(a-b)
            for group in ("all","station" if station else "non_station"):
                st=info[group];st["compared"]+=1;st["max_abs"]=max(st["max_abs"],e)
                if e>TOL[0]+TOL[1]*abs(a):
                    st["exceedances"]+=1
                    if st["first_exceedance"] is None:
                        st["first_exceedance"]={"hour":h,"i":ix%50+1,
                                               "j":ix//50%50+1,
                                               "original":a,"native":b,"error":e}
        stats[field]=info
    status="PASS_NATIVE_COMP_DPTT" if all(s["all"]["exceedances"]==0 for s in stats.values()) else "FAIL_NATIVE_COMP_DPTT"
    report={"status":status,"hours":143,"source_sha256":SOURCE_SHA,
            "native_station_flux_source":meta.get("station_flux_source"),
            "native_mutation":meta.get("station_dptt_mutation"),
            "original_reference_injected_into_native":False,
            "full_UVW_pass":False,"tolerance_absolute_k":TOL[0],
            "tolerance_relative":TOL[1],"fields":stats}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if args.require_parity and status!="PASS_NATIVE_COMP_DPTT":
        raise SystemExit(1)
if __name__=="__main__":main()

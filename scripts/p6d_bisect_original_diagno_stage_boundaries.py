#!/usr/bin/env python3
"""Pin the FIRST stage where original DIAGNO deviates from autonomous C++.

The six original DIAGNO snapshots (points 7,8,9,10) were instrumented
write-only on unmodified original CALMET 6.5.0; their binary is SHA-locked.
No reference values are inputs to the native pipeline. Diagnostic, not a
replacement for full 143h WFACE and U/V source acceptance.
"""
import argparse,datetime as dt,json,math
from pathlib import Path
from p6d_probe_selected_source_u_v_w_post_elustr import (
    SAMPLE_HOURS,read_source,read_candidate,NX,NY,NZ,GRID,VOLUME,FACES
)

STAGES={
    "pre_slope_u":(2e-4,0.),
    "pre_slope_v":(2e-4,0.),
    "slope_inc_u":(2e-4,0.),
    "slope_inc_v":(2e-4,0.),
    "post_slope_u":(2e-4,0.),
    "post_slope_v":(2e-4,0.),
    "final_u":(1e-4,1e-5),
    "final_v":(1e-4,1e-5),
    "final_w":(1e-5,1e-5),
}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--candidate",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--require-all-stages",action="store_true")
    a=ap.parse_args()
    original=read_source(a.source)
    states={k:{"compared":0,"exceedances":0,"max_abs":0.,
               "sum_sq":0.,"first_exceedance":None,"worst":None,
               "levels_with_exceedances":{}} for k in STAGES}
    for hour in SAMPLE_HOURS:
        label=(dt.datetime(2022,1,1)+dt.timedelta(hours=hour)).strftime("%Y-%m-%d_%H")
        orig=original[hour]
        wind_u=read_candidate(a.candidate/f"wind1_u_{label}.f32",VOLUME)
        wind_v=read_candidate(a.candidate/f"wind1_v_{label}.f32",VOLUME)
        pre_u_file=a.candidate/f"fradj_corrected_u_{label}.f32"
        pre_v_file=a.candidate/f"fradj_corrected_v_{label}.f32"
        if pre_u_file.is_file()!=pre_v_file.is_file():
            raise RuntimeError("incomplete native pre-SLOPE FRADJ pair")
        pre_u=read_candidate(pre_u_file,VOLUME) if pre_u_file.is_file() else wind_u
        pre_v=read_candidate(pre_v_file,VOLUME) if pre_v_file.is_file() else wind_v
        post_u=read_candidate(a.candidate/f"slope_corrected_u_{label}.f32",VOLUME)
        post_v=read_candidate(a.candidate/f"slope_corrected_v_{label}.f32",VOLUME)
        final_u=read_candidate(a.candidate/f"blend_u_{label}.f32",VOLUME)
        final_v=read_candidate(a.candidate/f"blend_v_{label}.f32",VOLUME)
        final_w=read_candidate(a.candidate/f"w_face_{label}.f32",FACES)
        native={
            "pre_slope_u":pre_u,"pre_slope_v":pre_v,
            "slope_inc_u":(a-b for a,b in zip(post_u,pre_u)),
            "slope_inc_v":(a-b for a,b in zip(post_v,pre_v)),
            "post_slope_u":post_u,"post_slope_v":post_v,
            "final_u":final_u,"final_v":final_v,"final_w":final_w}
        source={
            "pre_slope_u":orig[8][0],"pre_slope_v":orig[8][1],
            "slope_inc_u":orig[7][0],"slope_inc_v":orig[7][1],
            "post_slope_u":orig[9][0],"post_slope_v":orig[9][1],
            "final_u":orig[10][2],"final_v":orig[10][3],"final_w":orig[10][1]}
        for name,(abs_lim,rel_lim) in STAGES.items():
            ref=source[name];cand=native[name]
            st=states[name];got=0
            for i,(x,y) in enumerate(zip(ref,cand)):
                got+=1;dif=abs(x-y);st["compared"]+=1;st["sum_sq"]+=dif*dif
                level=i//GRID+1
                detail={"hour":hour,"hour_end":label,"level":level,
                        "i":i%NX+1,"j":i//NX%NY+1,
                        "original":x,"native":y,"error":dif}
                if dif>st["max_abs"]:
                    st["max_abs"]=dif;st["worst"]=detail
                if dif>abs_lim+rel_lim*abs(x):
                    st["exceedances"]+=1
                    key=str(level)
                    st["levels_with_exceedances"][key]=st["levels_with_exceedances"].get(key,0)+1
                    if st["first_exceedance"] is None:st["first_exceedance"]=detail
            expected=FACES if name=="final_w" else VOLUME
            if got!=expected:raise RuntimeError(f"incomplete stage sample {hour}/{name}")
    for st in states.values():st["rms"]=math.sqrt(st.pop("sum_sq")/st["compared"])
    first=next((name for name in STAGES if states[name]["exceedances"]),None)
    report={
        "status":"PASS_ALL_SELECTED_DIAGNO_BOUNDARIES" if first is None else "FAIL_SELECTED_DIAGNO_BOUNDARIES",
        "first_failing_boundary_in_source_order":first,
        "first_failing_stage_interpretation":"stage 8 prior to slope / stage 7 slope contribution / stage 9 after slope / stage 10 final U/V/W; stage 10 includes INTER2 and SMOOTH/DIVCEL/W",
        "source_original_injected_into_native":False,
        "source_reference_sha256":"972af841552f7a0eda6b02b221b6b2a808c61806054e634c617425d9ca9babdf",
        "selected_hours":SAMPLE_HOURS,"grid":[NX,NY,NZ],
        "tolerances":{k:{"absolute":v[0],"relative":v[1]} for k,v in STAGES.items()},
        "stages":states,"full_143h_UVW_PASSED":False}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"first_failing_boundary":first,
        "summary":{k:{"max_abs":v["max_abs"],"exceedances":v["exceedances"],
                       "first_exceedance":v["first_exceedance"],"worst":v["worst"]}
                   for k,v in states.items()}},indent=2))
    if a.require_all_stages and first is not None:raise SystemExit(1)
if __name__=="__main__":main()
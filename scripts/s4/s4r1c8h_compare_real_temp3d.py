#!/usr/bin/env python3
"""Independent first-hour native G56 full TEMP3D vs original write-only trace.

The native program is executed before reading original physical outputs.
Fixed original-vs-native tolerance 2e-4 K on all 62,730 cell-level values.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
from scripts.s4.s4r1c8h_original_comp_temp3d import NX,NY,NZ,NC,FIELD,decode,sha
TOL_K=2e-4
def compare(original:Path,receipt:Path,native:Path,native_log:Path,report:Path):
    o=json.loads(receipt.read_text())
    if(o.get("status")!="PASS_SOURCE_ONLY_ORIGINAL_NOAA_6H_TEMP3D" or
       o.get("trace_sha256")!=sha(original) or
       o.get("sixhour_original_met_byte_identical") is not True or
       o.get("sixhour_float_counts")!=[NC]*6):
        raise ValueError("G56 requires authentic original six-hour TEMP3D science")
    t=native_log.read_text()
    if("S4R1C8H_NATIVE_REAL_NOAA_TEMP3D=PRODUCED_UNVERIFIED" not in t or
       "ORIGINAL_PHYSICS_OUTPUT_INJECTED=FALSE" not in t):
        raise ValueError("G56 original-independent native TEMP3D source unavailable")
    if native.stat().st_size!=FIELD.size:
        raise ValueError("G56 candidate real 3D float shape invalid")
    ref=decode(original)[0]
    predicted=FIELD.unpack(native.read_bytes())
    if not all(math.isfinite(v) and 180<=v<=350 for v in predicted):
        raise ValueError("G56 native TEMP3D nonfinite or nonphysical")
    above=0
    max_abs=-1.
    worst=None
    mean=0.
    samples=[]
    per_layer=[]
    nxy=NX*NY
    for k in range(NZ):
        maxk=0.
        badk=0
        for idx in range(k*nxy,(k+1)*nxy):
            a,b=ref[idx],predicted[idx]
            d=abs(a-b)
            mean+=d
            maxk=max(maxk,d)
            if d>max_abs:
                max_abs=d
                worst={"k":k+1,"i":idx%nxy%NX+1,
                       "j":idx%nxy//NX+1,"original_k":a,
                       "native_k":b,"abs_residual_k":d}
            if d>TOL_K:
                above+=1;badk+=1
                if len(samples)<16:
                    samples.append({"k":k+1,"i":idx%nxy%NX+1,
                                    "j":idx%nxy//NX+1,"original":a,
                                    "native":b,"delta":d})
        per_layer.append({"level":k+1,"max_abs_k":maxk,"above_tolerance":badk})
    result={
        "status":("PASS_SCOPED_REAL_NOAA_FIRSTHOUR_NATIVE_TEMP3D" if above==0 else
                  "FAIL_REAL_NOAA_NATIVE_TEMP3D_PARITY"),
        "source_scope":"FIRSTHOUR_2SS1US_MIXED_63WATER_NATIVE_FULLGRID_TEMP3D",
        "original_6h45_met_byte_identical":True,
        "original_trace_sha256":sha(original),
        "native_candidate_sha256":sha(native),
        "original_intermediate_inputs_in_native":False,
        "float_compared":NC,"grid":[NX,NY,NZ],
        "abs_tolerance_k":TOL_K,"above_tolerance":above,
        "max_abs_residual_k":max_abs,"mean_abs_residual_k":mean/NC,
        "worst":worst,"per_level":per_layer,"first_exceedances":samples,
        "native_45field_g26":"NOT_ACCEPTED",
        "native_6h_causal":"NOT_ACCEPTED","p7":"NOT_ACCEPTED",
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("S4R1C8H_NATIVE_REAL_NOAA_TEMP3D="+result["status"])
    print("S4R1C8H_ABOVE_TOLERANCE="+str(above))
    print("S4R1C8H_TEMP3D_MAX_K="+str(max_abs))
    print("S4R1C8H_G26_P7=NOT_ACCEPTED")
    return above==0
def main():
    p=argparse.ArgumentParser()
    for k in ("original","receipt","native","native-log","report"):
        p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args()
    if not compare(a.original,a.receipt,a.native,a.native_log,a.report):
        raise SystemExit(3)
if __name__=="__main__":main()

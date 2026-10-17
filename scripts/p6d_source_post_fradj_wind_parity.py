#!/usr/bin/env python3
"""Compare original CALMET pre-SLOPE post-FRADJ U/V against native first-level
stage inputs for every Hefei 2022 hour. Forensic-only: no tolerance relaxation.
Source point 8 is the original DIAGNO UG/VG immediately before SLOPE addition;
the native write-only fradj_corrected_u/v files are from exactly this stage.
"""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,struct,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"native_cpp/modules/p6_calmet/reference"))
import original_internal_state_dump as dgm

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda:f.read(1048576),b""):h.update(part)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    for name in ("original-dir","candidate","out"):
        ap.add_argument("--"+name,required=True,type=Path)
    args=ap.parse_args()
    provenance=json.loads((args.original_dir/"dgm-audit.json").read_text())
    if (provenance.get("status")!="ORIGINAL_MET_DAT_IDENTICAL"
        or provenance.get("frozen_reference_sha256")!=dgm.TARGET_MET_DAT_SHA256):
        raise RuntimeError("source original MET.DAT provenance not accepted")
    blob=args.original_dir/"case"/"run"/"met"/"dgm_fields.bin"
    if not blob.exists():raise RuntimeError("missing source original point-8 dump")
    records=[r for r in dgm._walk_dump(blob) if r["kpt"]==8]
    if len(records)!=143:raise RuntimeError(f"expected 143 post-FRADJ source states, got {len(records)}")
    nx=ny=50;cells=nx*ny
    output={
        "status":"FORENSIC_ONLY_NO_PHYSICS_CHANGE",
        "source_original_MET_DAT_byte_identical":True,
        "original_dump_sha256":sha(blob),
        "source_stage":"DIAGNO DGMFLD point 8, post-FRADJ pre-SLOPE UG/VG",
        "native_stage":"P6D fradj_corrected_u/v before second SURFVAR",
        "threshold_mps":0.0,
        "fields":{},
        "worst_slope_qh_cell":[23,29],
        "source_vs_native_at_qh_worst":None,
    }
    for component in ("u","v"):
        exceeding=0;worst=None;maximum=0.0;exact=0;hour_counts={}
        with blob.open("rb") as original:
            for hour,rec in enumerate(records):
                if (rec["nx"],rec["ny"],rec["nz"])!=(nx,ny,9):
                    raise RuntimeError("unexpected 143h source grid")
                expected_start=dt.datetime(2022,1,1)+dt.timedelta(hours=hour)
                packed=expected_start.year*100000+expected_start.timetuple().tm_yday*100+expected_start.hour
                if rec["packed"]!=packed or rec["seconds"]!=0:
                    raise RuntimeError("original source clock misalignment")
                offset=rec["offset"]+32+(0 if component=="u" else cells*9*4)
                original.seek(offset)
                reference=struct.unpack("<2500f",original.read(cells*4))
                label=(expected_start+dt.timedelta(hours=1)).strftime("%Y-%m-%d_%H")
                folder=args.candidate/f"hour_{hour:03d}"/"diagno"
                if not folder.is_dir():folder=args.candidate
                cand_file=folder/f"fradj_corrected_{component}_{label}.f32"
                raw=cand_file.read_bytes()
                if len(raw)!=cells*9*4:raise RuntimeError(f"bad native FRADJ field {cand_file}")
                vals=struct.unpack_from("<2500f",raw,0)
                if hour==131:
                    idx=(29-1)*nx+(23-1)
                    if output["source_vs_native_at_qh_worst"] is None:
                        output["source_vs_native_at_qh_worst"]={"hour_end":label}
                    output["source_vs_native_at_qh_worst"][component]={
                        "reference":reference[idx],"native":vals[idx],
                        "difference":vals[idx]-reference[idx]}
                for idx,(a,b) in enumerate(zip(reference,vals)):
                    if a==b:exact+=1;continue
                    exceeding+=1
                    hour_counts[label]=hour_counts.get(label,0)+1
                    delta=abs(a-b)
                    if delta>maximum:
                        maximum=delta
                        worst={"hour_end":label,"i":idx%50+1,"j":idx//50+1,
                               "reference":a,"candidate":b,"abs_error":delta}
        output["fields"][component]={
            "samples":143*cells,"exact_equal":exact,"non_bitwise_equal":exceeding,
            "max_abs_difference_mps":maximum,"worst":worst,
            "hours_with_any_difference":len(hour_counts),
            "first_hours":list(hour_counts.items())[:20]}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps({k:v for k,v in output.items() if k!="original_dump_sha256"},indent=2))
if __name__=="__main__":main()

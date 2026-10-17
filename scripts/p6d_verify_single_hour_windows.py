#!/usr/bin/env python3
"""P6D actual executable 1-hour vs 143-hour production route equivalence.

Reads optional real native P6E COMP ZI/ZICONV/DPTT history; at hour n
the single-hour DIAGNO producer may read state from n-1 only.
Compares all actual per-hour P6D float32 artifacts, byte-for-byte, not a
source-instrumented original scientific wind comparison. G2/G3 remain open.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import sys

HOURS = (0, 5, 11, 142)


def digest(p: pathlib.Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1048576),b""):
            h.update(block)
    return h.hexdigest()


def run(cmd: list[object], logfile: pathlib.Path) -> None:
    p=subprocess.run([str(v) for v in cmd],capture_output=True,text=True)
    logfile.write_text(p.stdout+"\n"+p.stderr)
    if p.returncode:
        raise RuntimeError(f"producer failed at {logfile}: {p.stderr[-1300:]}")


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--case",required=True,type=pathlib.Path)
    p.add_argument("--p6d",required=True,type=pathlib.Path)
    p.add_argument("--work",required=True,type=pathlib.Path)
    p.add_argument("--comp-state-prefix",default=None,type=pathlib.Path)
    a=p.parse_args()
    a.work.mkdir(parents=True,exist_ok=True)
    base=a.work/"whole_143h"
    base.mkdir(exist_ok=True)
    cmd=[a.p6d,"--case",a.case,"--out",base,"--hours","143"]
    if a.comp_state_prefix:
        cmd+=["--comp-state-prefix",a.comp_state_prefix]
    run(cmd,a.work/"baseline.log")
    results=[]
    for hour in HOURS:
        label=(dt.datetime(2022,1,1)+dt.timedelta(hours=hour+1)).strftime("%Y-%m-%d_%H")
        out=a.work/f"single_{hour:03d}"
        out.mkdir(exist_ok=True)
        sub=[a.p6d,"--case",a.case,"--out",out,
             "--first-hour",str(hour),"--hours","1"]
        if a.comp_state_prefix:
            sub+=["--comp-state-prefix",a.comp_state_prefix]
        run(sub,a.work/f"single_{hour:03d}.log")
        produced=(out/"produced_hours.txt").read_text().strip().splitlines()
        if len(produced)!=1 or produced[0]!=label:
            raise RuntimeError(f"hour={hour}: wrong produced_hours index {produced}")
        meta=json.loads((out/"metadata.json").read_text())
        if meta["first_hour_zero_based"]!=hour or meta["hourly_labels"]!=1:
            raise RuntimeError(f"hour={hour}: invalid source time metadata")
        candidates=sorted(base.glob(f"*_{label}.f32"))
        files={c.name: c for c in candidates}
        for required in ("blend_u_","blend_v_","w_face_","wind1_u_","wind1_v_"):
            if not any(name.startswith(required) for name in files):
                raise RuntimeError(f"hour={hour}: baseline lacks {required} field")
        missing=[]; mismatches=[]
        for name,ref in files.items():
            got=out/name
            if not got.is_file():
                missing.append(name)
            elif digest(ref)!=digest(got):
                mismatches.append(name)
        extras=[c.name for c in out.glob(f"*_{label}.f32") if c.name not in files]
        results.append({"hour_index_zero_based":hour,
                        "label":label,"physical_planes_checked":len(files),
                        "missing":missing,"extra":extras,
                        "byte_mismatches":mismatches})
        if missing or mismatches or extras:
            raise RuntimeError(f"single-hour P6D failed h={hour}, missing={missing[:5]}, diff={mismatches[:5]}, extra={extras[:5]}")
    report={"status":"PASS_NATIVE_P6D_SINGLE_HOUR_WINDOWS",
            "cases":results,"comp_history_mode":"NATIVE_P6E_PREVIOUS_HOUR" if a.comp_state_prefix else "UNCOUPLED",
            "original_single_pass_diagno_comp":"NOT_YET_IMPLEMENTED",
            "full_original_uvw_numeric_parity":"NOT_PASS"}
    (a.work/"p6d_single_hour_evidence.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    return 0


if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print(f"FAIL_NATIVE_P6D_HOUR_WINDOW: {e}",file=sys.stderr)
        sys.exit(3)

#!/usr/bin/env python3
"""Read-only, non-physics P6 control-file study-gate audit.

Parses *active* CALMET !KEY = VALUE! terms, never rewrites original files,
never constructs missing meteorological data. Prints JSON with blockers.
A legacy sample is expected to be BLOCKED, NOT a reference run.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

KEY_RE = re.compile(r"!\s*([A-Z][A-Z0-9_]*)\s*=\s*([^!]*)!",re.I)
NUMERIC = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[EDed][+-]?[0-9]+)?$")
ALLOWED = {
    "GEODAT","SRFDAT","METDAT","NUSTA","NOWSTA","NM3D","NSSTA","NPSTA",
    "IBYR","IBMO","IBDY","IBHR","IBSEC","IEYR","IEMO","IEDY","IEHR","IESEC",
    "ABTZ","NSECDT","IRTYPE","ITEST","PMAP","DATUM","IUTMZN","UTMHEM",
    "NX","NY","NZ","DGRIDKM","XORIGKM","YORIGKM","ZFACE","NOOBS",
    "IFORMS","IFORMP","IWFCOD","IFRADJ","IKINE","ISLOPE","IOBR",
    "IPROG","IGFMET","IEXTRP","IRHPROG","ITPROG","LSAVE","IFORMO",
}

def parse(path:Path)->dict[str,str]:
    controls={}
    for index,line in enumerate(path.read_text(encoding="utf8",errors="strict").splitlines(),1):
        for m in KEY_RE.finditer(line):
            key=m.group(1).upper()
            if key not in ALLOWED:continue
            value=m.group(2).strip()
            if key in controls:raise ValueError(f"duplicate active {key} at line {index}")
            controls[key]=value
    return controls

def as_number(controls,key):
    text=controls[key]
    if not NUMERIC.fullmatch(text):raise ValueError(f"{key} is not one scalar number")
    val=float(text.replace("D","E").replace("d","e"))
    if not math.isfinite(val):raise ValueError(f"{key} nonfinite")
    return val

def integer(controls,key):
    v=as_number(controls,key)
    if not v.is_integer():raise ValueError(f"{key} not an integer")
    return int(v)

def audit(path:Path):
    c=parse(path)
    expected={
        "IBYR":2022,"IBMO":1,"IBDY":1,"IBHR":0,"IBSEC":0,
        "IEYR":2022,"IEMO":1,"IEDY":6,"IEHR":23,"IESEC":0,
        "NX":50,"NY":50,"NZ":9,"IUTMZN":50,"NSECDT":3600,
        "NOOBS":0,"IPROG":0,"IWFCOD":1,"IRTYPE":1,
    }
    mismatches=[]
    for k,v in expected.items():
        try:actual=integer(c,k)
        except (KeyError,ValueError) as e:
            mismatches.append({"key":k,"error":str(e)})
            continue
        if actual!=v:mismatches.append({"key":k,"actual":actual,"required":v})
    required_text={"PMAP":"UTM","DATUM":"WGS-84","UTMHEM":"N","ABTZ":"UTC+0000"}
    for k,v in required_text.items():
        val=c.get(k)
        if val!=v:mismatches.append({"key":k,"actual":val,"required":v})
    try:
        if abs(as_number(c,"DGRIDKM")-0.1)>1e-12:
            mismatches.append({"key":"DGRIDKM","actual":c["DGRIDKM"],"required":0.1})
    except (KeyError,ValueError) as e:mismatches.append({"key":"DGRIDKM","error":str(e)})
    face_expected=[0.,20.,40.,80.,160.,320.,640.,1200.,2000.,3000.]
    try:
        faces=[float(v.strip()) for v in c["ZFACE"].split(",") if v.strip()]
        if len(faces)!=10 or any(not math.isfinite(v) for v in faces):
            raise ValueError("expected ten finite ZFACE values")
        if any(abs(a-b)>1e-9 for a,b in zip(faces,face_expected)):
            mismatches.append({"key":"ZFACE","actual":faces,"required":face_expected})
    except (KeyError,ValueError) as e:mismatches.append({"key":"ZFACE","error":str(e)})
    observations={
        "NUSTA":c.get("NUSTA"),"NSSTA":c.get("NSSTA"),
        "NPSTA":c.get("NPSTA"),
        "IFORMS":c.get("IFORMS"),"IFORMP":c.get("IFORMP"),
        "surface_and_upper_data_validated":False,
        "precipitation_source_validated":False,
    }
    # A parsed file cannot prove its paths exist, its station metadata are
    # meaningful, or its data and physics match original CALMET.
    status=("CONTROL_VALUES_PROVISIONALLY_MATCH_STUDY_NOT_RUNNABLE"
            if not mismatches else "BUNDLED_OR_UNFROZEN_CONTROLS_NOT_HEFEI_READY")
    return {
        "status":status,
        "control_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
        "study_grid_match":not mismatches,
        "control_mismatches":mismatches,
        "external_forcing_gate":"BLOCKED_UNTIL_P4_P5_AND_PRECIP_FORTRAN_VALIDATION",
        "station_and_format_issues":observations,
        "note":"Read-only metadata audit; NOT an original CALMET execution or Fortran-equivalence check.",
    }

def main():
    a=argparse.ArgumentParser()
    a.add_argument("input",type=Path)
    a.add_argument("--expect-not-ready",action="store_true",
                   help="Fail test if legacy example accidentally appears Hefei ready")
    args=a.parse_args()
    result=audit(args.input)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if args.expect_not_ready:
        return 0 if result["control_mismatches"] else 1
    return 0 if result["study_grid_match"] else 2

if __name__=="__main__":
    try:raise SystemExit(main())
    except (OSError,KeyError,ValueError) as exc:
        print(f"P6_CONTROL_AUDIT_FAIL: {exc}",file=sys.stderr)
        raise SystemExit(1)

#!/usr/bin/env python3
"""C2 real 2SS/2US 143h original CALPUFF A/C runs with an admissible source.

The frozen 2022 stack lies inside the southwest EDGE of the enlarged 12x12
10-km domain. The first source-preserving G36 read-compatibility test produced
all-zero H-3. For a genuinely falsifiable dispersion test, move ONLY the
point-source XY to the middle cell of the SAME 2024 domain for BOTH runs.
No change to original vendor code, release rate, stack configuration, or
turbulence/deposition/chemistry controls.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
import shutil
import sys
import tempfile

def load_named(path: Path, name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise ValueError(f"missing pinned module: {path}")
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for opt in ("pr63_root","original_met","native_met","out"):
        p.add_argument("--"+opt.replace("_","-"),type=Path,required=True)
    a=p.parse_args()
    a.pr63_root=a.pr63_root.resolve()
    for path in (a.original_met,a.native_met):
        if not path.is_file() or not path.stat().st_size:
            raise ValueError("missing accepted G35 original/native MET.DAT")
    a.out.mkdir(parents=True,exist_ok=True)
    scripts=a.pr63_root/"native_cpp/modules/p6_calmet/reference"
    sys.path.insert(0,str(scripts))
    g36=load_named(scripts/"g36a_run_original_calpuff_multisite.py","p6_g36a_source")
    legacy=load_named(a.pr63_root/"native_cpp/modules/p6_calmet/p6f/tests/verify_original_calpuff_reads_written_calmet.py","p6_vendor_calpuff")
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import compare_p7_hourly_concentrations as fields

    control_path=a.pr63_root/"project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.inp"
    source=control_path.read_bytes()
    if g36.git_blob(source)!=g36.SOURCE_CONTROL_GIT_BLOB:
        raise ValueError("pinned original 2022 source deck SHA changed")
    orig_control=g36.make_control(source.decode("latin-1"))
    assert g36.control_value(orig_control,"NX")=="12"
    assert g36.control_value(orig_control,"NY")=="12"
    assert float(g36.control_value(orig_control,"DGRIDKM"))==10.
    x0=float(g36.control_value(orig_control,"XORIGKM"))
    y0=float(g36.control_value(orig_control,"YORIGKM"))
    grid_km=10.
    # Chosen to be away from all four open boundaries and shared by A/C.
    x,y=x0+5.5*grid_km,y0+5.5*grid_km
    old=g36.control_value(orig_control,"X")
    tokens=[t.strip() for t in old.split(",")]
    if len(tokens)!=10:raise ValueError("unexpected pinned original 10-value point source")
    old_x,old_y=float(tokens[0]),float(tokens[1])
    if not (x0<=x<x0+12*grid_km and y0<=y<y0+12*grid_km):
        raise ValueError("new source not inside 2SS/2US domain")
    tokens[:2]=[f"{x:.3f}",f"{y:.3f}"]
    control=g36.put_control(orig_control,"X",", ".join(tokens))
    for key in ("MWET","MDRY","METFM","NPT1","MCTADJ","MDISP","MTRANS","MXSAM"):
        if g36.control_value(control,key)!=g36.control_value(orig_control,key):
            raise ValueError(f"physical control {key} changed")
    for met in (a.original_met,a.native_met):
        check=g36.layout(met.resolve(),met.name)
        if check["intervals"]!=143:
            raise ValueError("C2 MET is not 143 uninterrupted hours")
        if g36.time_bounds(check["control"])!=(g36.EXPECTED_START,g36.EXPECTED_END):
            raise ValueError("C2 weather UTC window drifted")

    test_control=a.out/"C2-source-inside-multistation-domain.inp"
    test_control.write_text(control,encoding="latin-1")
    ledger={
        "scope":"P7_C2_VENDOR_A_C_WITH_NONZERO_INTERNAL_SOURCE",
        "p6_pr63_sha":"7a13cc6a2f2d7b4c99e18b8866043a0319733454",
        "vendor_puff_control_source_blob":g36.SOURCE_CONTROL_GIT_BLOB,
        "new_control_sha256":fields.sha256(test_control),
        "original_point_xy_km":[old_x,old_y],
        "controlled_internal_point_xy_km":[x,y],
        "origin_xy_km":[x0,y0],
        "nx":12,"ny":12,"grid_km":10,"hours":143,
        "source_changes":"ONLY point-source x/y position to internal domain; all other X source operands and physics controls untouched",
        "P7_native_B_D":"NOT_RUN",
    }
    with tempfile.TemporaryDirectory(prefix="p7-c2-vendor-") as tmp:
        root=Path(tmp)
        build=legacy.build_original(a.pr63_root/"engine/vendor/src/CALPUFF_v7.2.1_L150618","gfortran",root/"build")
        ledger["vendor_binary_sha256"]=build["binary_sha256"]
        for arm,met in (("A",a.original_met),("C",a.native_met)):
            stage=root/arm
            stage.mkdir()
            working=legacy.stage(stage,test_control,met.read_bytes())
            running=legacy.execute(working,Path(build["binary_path"]),900)
            if running["returncode"]!=0 or not running["listing"].is_file() or not running["concentration"].is_file():
                raise ValueError(f"vendor {arm} did not finish with listing+CONC and zero exit")
            listing=running["listing"].read_text(errors="replace")
            m=re.search(
                r"LAST PERIOD PROCESSED ENDS AT:\s*"
                r"Year:\s*(\d+)\s*Month:\s*(\d+)\s*Day:\s*(\d+)\s*"
                r"Julian day:\s*\d+\s*Hour:\s*(\d+)\s*Second:\s*(\d+)",
                listing,re.I)
            if not m or g36.stamp(*(int(v) for v in m.groups()))!=g36.EXPECTED_END:
                raise ValueError(f"vendor {arm} did not complete genuine 143h 2024 run")
            dest=a.out/f"{arm}-original-calpuff.con"
            shutil.copyfile(running["concentration"],dest)
            ledger[arm]={
                "input_met_sha256":fields.sha256(met),
                "puff_con_sha256":fields.sha256(dest),
                "original_vendor_hours":143,
            }
    a_field=fields.read_fields(a.out/"A-original-calpuff.con",12,12,143)
    c_field=fields.read_fields(a.out/"C-original-calpuff.con",12,12,143)
    paired=fields.compare(a_field,c_field,12,12)
    paired["controlled_source"]={"x_km":x,"y_km":y}
    (a.out/"C2-A-vs-C-science.json").write_text(json.dumps(paired,indent=2)+"\n")
    (a.out/"C2-vendor-source-provenance.json").write_text(json.dumps(ledger,indent=2)+"\n")
    print(f"P7_C2_CONTROLLED_SOURCE=PASS OLD_XY={old_x},{old_y}"
          f" NEW_XY={x},{y} EACH_VENDOR_HOURS=143")
    print(f"P7_C2_VENDOR_PAIR=PASS H3_NONZERO_A={a_field['nonzero_values']}"
          f" H3_NONZERO_C={c_field['nonzero_values']}"
          f" REAL4_MATCH={paired['matching_real4']}/{paired['values']}"
          f" MAX_ABS={paired['max_absolute_difference_bq_m3']}")
    print("P7_C2_FOUR_ARM_SCIENCE=OPEN REQUIRES_SAME_MET_NATIVE_P7_B_AND_D")
    return 0

if __name__=="__main__":
    try:raise SystemExit(main())
    except (OSError,ValueError,RuntimeError,AssertionError) as exc:
        print("P7_C2_VENDOR_NONZERO_BLOCKED: "+str(exc),file=sys.stderr)
        raise SystemExit(1)

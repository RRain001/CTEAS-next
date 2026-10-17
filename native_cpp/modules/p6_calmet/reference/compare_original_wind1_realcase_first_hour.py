#!/usr/bin/env python3
"""First-hour real-case WIND1 oracle from *unchanged* calmet.for.

Purpose: split real-case source/observation/driver parity from complete DIAGNO.
The input fixture is produced by P6D, with true met.inp SS1/US1 coordinates,
SS1 anemometer height, station-cell GEO Z0, and unmodified UP/SURF data.
We then compile the original WIND1+SIMILT source in a separate Fortran driver,
compare against C++ selected WIND1 on exactly the same fixture, and verify
P6D's written float32 first-guess fields match that selected driver.

A PASS HERE IS NOT 143-hour full 3-D diagnostic-wind acceptance. In particular
the P6D station profile could still differ from the original PREPDI output,
and this test cannot validate INTER2/SMOOTH/DIVCEL/W or MIXHT.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import subprocess
from pathlib import Path

from compare_original_wind1_firstguess import (
    DRIVER, TOLERANCE, NX, NY, NZ, compare, extract, run
)


def execute(*argv: object, timeout: int = 240) -> None:
    proc = subprocess.run([str(x) for x in argv], capture_output=True,
                          text=True, timeout=timeout)
    if proc.returncode:
        raise RuntimeError(
            f"command {argv} failed (rc={proc.returncode}): "
            + proc.stdout[-1200:] + "\n" + proc.stderr[-2200:])


def compare_float32_field(original_path: Path, field_dir: Path, hour: str):
    lines=original_path.read_text().splitlines()
    expected=NX*NY*NZ
    if len(lines)!=expected:
        raise RuntimeError(f"Original WIND1 lines: {len(lines)} != {expected}")
    raw=[]
    for tag in ("wind1_u","wind1_v"):
        path=field_dir/f"{tag}_{hour}.f32"
        blob=path.read_bytes()
        if len(blob)!=expected*4:
            raise RuntimeError(f"{path} size {len(blob)} != {expected*4}")
        raw.append([v[0] for v in struct.iter_unpack("<f",blob)])
    errors=[];max_abs=0.
    for offset,line in enumerate(lines):
        t=line.split()
        assert len(t)==5
        i=offset%NX+1;j=(offset//NX)%NY+1;k=offset//(NX*NY)+1
        if tuple(map(int,t[:3]))!=(i,j,k):
            raise RuntimeError("Fortran WIND1 field array ordering differs")
        for component in range(2):
            want=float(t[component+3])
            have=raw[component][offset]
            if not math.isfinite(want) or not math.isfinite(have):
                raise RuntimeError("nonfinite original/C++ WIND1 array")
            error=abs(want-have)
            max_abs=max(max_abs,error)
            if error>TOLERANCE and len(errors)<20:
                errors.append({"i":i,"j":j,"k":k,
                               "component":"U" if component==0 else "V",
                               "original":want,"p6d":have,"max_abs":error})
    return {"status":"PASS" if not errors else "FAIL",
            "max_abs_error_mps":max_abs,
            "first_errors":errors,
            "components_compared":2*expected}


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--vendor",required=True,type=Path)
    p.add_argument("--case",required=True,type=Path)
    p.add_argument("--p6d",required=True,type=Path)
    p.add_argument("--cpp",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--fortran",default="gfortran")
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    fixture=a.out/"fixtures"
    fields=a.out/"p6d_fields"
    fixture.mkdir(exist_ok=True)
    fields.mkdir(exist_ok=True)

    execute(a.p6d,"--case",a.case,"--hours",1,
            "--fixtures",fixture,"--out",fields)
    inp=list(fixture.glob("wind1_driver_*.inp"))
    if len(inp)!=1:
        raise RuntimeError(f"expected one real-case WIND1 fixture, found {len(inp)}")
    hour=inp[0].stem.removeprefix("wind1_driver_")
    fortran_files=extract(a.vendor,a.out)
    driver=a.out/"driver.for"
    driver.write_text(DRIVER,encoding="utf-8")
    original=a.out/"original_wind1"
    execute(a.fortran,"-std=legacy","-O0","-fno-automatic",
            "-ffixed-line-length-none","-fallow-argument-mismatch",
            "-I"+str(a.vendor),*fortran_files,driver,"-o",original)

    original_out=a.out/"real_hour.fortran.txt"
    cpp_out=a.out/"real_hour.cpp.txt"
    run(original,inp[0],original_out)
    run(a.cpp,inp[0],cpp_out)
    selected=compare(original_out,cpp_out,"hefei_real_hour")
    emitted=compare_float32_field(original_out,fields,hour)
    ok=selected["status"]=="PASS" and emitted["status"]=="PASS"
    result={
      "status":"PASS_ORIGINAL_REALCASE_HOUR1_SELECTED_WIND1" if ok else "FAIL",
      "hour_label":hour,
      "input_source":"frozen met.inp SS1/US1 + SURF.DAT + UP.DAT + GEO.DAT",
      "comparison_tolerance_mps":TOLERANCE,
      "selected_original_vs_cpp":selected,
      "original_vs_p6d_float32_emitted":emitted,
      "scope":"one real hour WIND1+SIMILT source-scoped first guess only; "
              "NOT complete DIAGNO/143h field equivalence"
    }
    (a.out/"first_hour_wind1_parity.json").write_text(
        json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    if not ok:
        raise SystemExit(1)


if __name__=="__main__":
    main()

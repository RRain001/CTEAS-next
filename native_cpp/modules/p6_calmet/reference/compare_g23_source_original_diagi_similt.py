#!/usr/bin/env python3
"""Literal vendor SIMILT/PSIUD on source-file G23 STHEOR/MIXHTST station
inputs, compared to C++ capped DIAGI profiles. Selected 2SS+2US 1h only.

Reuses untouched vendor Fortran numeric routines, never a second C++
copy or a canonic neutral G20 station profile.  Upstream full original
ELUSTR2/MIXHTST is NOT independently validated by this test.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import tempfile
from pathlib import Path

from compare_original_similt_profile import (
    DRIVER, TOL_MPS, original_sources, VENDOR_BLOB,
)

ROOT = Path(__file__).resolve().parents[4]
VENDOR = ROOT / "engine/vendor/src/CALMET_v6.5.0_L150223"


def dynamic_source_driver() -> str:
    # SIMILT uses original READCF ZFACE, never the separate older
    # 50x50 synthetic 20/40/80m probe geometry. Override only driver
    # I/O; original SIMILT/PSIUD numerical statements remain verbatim.
    first = "      close(10)\n      if(iex.ne.-4)stop 72"
    second = (
        "      read(10,*) (zface(k),k=1,nz+1)\n"
        "      do k=1,nz\n"
        "        zmid(k)=0.5*(zface(k+1)+zface(k))\n"
        "      enddo\n"
        "      close(10)\n"
        "      if(iex.ne.-4)stop 72"
    )
    if DRIVER.count(first) != 1:
        raise ValueError("G23 original SIMILT driver source anchor drift")
    return DRIVER.replace(first, second)


def input_guard(path: Path) -> dict:
    lines = path.read_text().splitlines()
    if len(lines) != 2:
        raise ValueError("G23 source DIAGI SIMILT needs original met.inp zface")
    parts = lines[0].split()
    if len(parts) != 10:
        raise ValueError("G23 exact source STHEOR SIMILT scalar arguments missing")
    lat, anem, z0, u, v, el, zi, zimin = map(float, parts[:8])
    extrap, psi = map(int, parts[8:])
    if extrap != -4 or psi != 0 or not all(
        math.isfinite(x) for x in [lat,anem,z0,u,v,el,zi,zimin]
    ) or not (0 < lat <= 90) or anem <= z0 or z0 <= 0 or zi <= 0 or (
        el == 0 or zimin <= 0
    ):
        raise ValueError("G23 source original DIAGI outside validated SIMILT branch")
    faces = [float(s) for s in lines[1].split()]
    if len(faces) != 10 or any(b <= a for a,b in zip(faces,faces[1:])):
        raise ValueError("G23 source READCF zface absent/invalid")
    return {"latitude_deg":lat,"el_m":el,"zi_m":zi,
            "zimin_m":zimin,"zface_m":faces}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-prefix", type=Path, required=True)
    parser.add_argument("--mode", choices=("Debug","Release"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    source_inputs=[]
    for i in range(1,3):
        path=Path(str(args.source_prefix)+f".s{i}.input")
        source_inputs.append(input_guard(path))

    with Path(str(args.source_prefix)+".native.csv").open(newline="") as f:
        native=list(csv.DictReader(f))
    if len(native) != 18:
        raise ValueError("G23 source SIMILT C++ station profile CSV count !=18")
    for ordinal in range(1,3):
        rows=native[(ordinal-1)*9:ordinal*9]
        if any(int(r["surface_ordinal"])!=ordinal or
               int(r["k_1based"])!=j+1 for j,r in enumerate(rows)):
            raise ValueError("G23 source DIAGI station ordinal/layer order changed")

    with tempfile.TemporaryDirectory(prefix="g23-original-diagi-similt-") as tmp:
        root=Path(tmp)
        similt,psiud=original_sources(VENDOR,root)
        original_driver=root/"g23_selected_station_similt.for"
        original_driver.write_text(dynamic_source_driver())
        executable=root/"original_g23_similt"
        opt="-O0" if args.mode=="Debug" else "-O2"
        subprocess.run(
            ["gfortran",opt,"-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-fallow-argument-mismatch",
             "-I"+str(VENDOR),str(similt["file"]),str(psiud["file"]),
             str(original_driver),"-o",str(executable)],
            check=True,capture_output=True,text=True,
        )
        results=[]
        errors=[]
        maximum=0.0
        compared=0
        for ordinal in range(1,3):
            inp=Path(str(args.source_prefix)+f".s{ordinal}.input")
            reference=root/f"source_station_{ordinal}.ref"
            process=subprocess.run(
                [str(executable),str(inp),str(reference)],
                check=False,capture_output=True,text=True,
            )
            if process.returncode:
                raise RuntimeError(
                    f"G23 literal vendor SIMILT S{ordinal} failed "
                    f"{process.returncode}: {process.stderr[-1400:]} "
                    f"{process.stdout[-900:]}")
            lines=reference.read_text().splitlines()
            if len(lines)!=10:
                raise ValueError("G23 original station SIMILT profile format incorrect")
            filled=int(lines[0].strip())
            cpprows=native[(ordinal-1)*9:ordinal*9]
            cppfilled=int(cpprows[0]["levels_filled"])
            if filled!=cppfilled or filled<1 or filled>9:
                errors.append(["levels_filled",ordinal,filled,cppfilled])
            for k in range(9):
                parts=lines[k+1].split()
                if len(parts)!=3 or int(parts[0])!=k+1:
                    raise ValueError("G23 original SIMILT 1-based layer incorrect")
                if k>=min(filled,cppfilled):
                    continue
                for field,index in (("u_mps_real4",1),("v_mps_real4",2)):
                    ref=float(parts[index])
                    cpp=float(cpprows[k][field])
                    if not all(math.isfinite(x) for x in [ref,cpp]):
                        raise ValueError("G23 original DIAGI SIMILT nonfinite")
                    delta=abs(ref-cpp)
                    maximum=max(maximum,delta)
                    compared+=1
                    if delta>TOL_MPS:
                        errors.append([ordinal,k+1,field,ref,cpp,delta])
            results.append({
                "ordinal":ordinal,
                "surface_id":int(cpprows[0]["surface_id"]),
                "upper_id":int(cpprows[0]["upper_id"]),
                "vendor_filled":filled,"cpp_filled":cppfilled,
                "source_input":source_inputs[ordinal-1],
            })
    evidence={
        "scope":"G23 actual source-file station STHEOR MIXHTST derived DIAGI SIMILT profile",
        "weather":"synthetic observation values in original CALMET files",
        "fortran_vendor_blob":VENDOR_BLOB,
        "vendor_similt_sha256":similt["sha256"],
        "vendor_psiud_sha256":psiud["sha256"],
        "mode":args.mode,"stations":results,"uv_compared":compared,
        "max_abs_delta_mps":maximum,
        "unchanged_original_similt_tolerance_mps":TOL_MPS,
        "mismatches":errors[:12],
        "full_original_stheor_elustr2_mixhtst_recomputed":False,
        "full_multistation_45field_pass":False,
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(evidence,indent=2)+"\n")
    if errors or compared==0:
        raise AssertionError(
            f"G23 original vendor source DIAGI SIMILT mismatches: "
            f"{errors[:8]} compared={compared} max={maximum:.9g}")
    print(
        "PASS_P6G_G23_LITERAL_ORIGINAL_DIAGI_SIMILT "
        f"mode={args.mode} stations=2 uv_compared={compared} "
        f"max_abs_delta={maximum:.9g} "
        "UPSTREAM_STHEOR_MIXHTST_VENDOR_PARITY=NOT_ACCEPTED"
    )


if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""Forensic AVETMP original-vs-C++ with IDENTICAL byte-for-byte REAL*4 winds.

Inputs are real WIND1 wind fields from the existing autonomous C++ producer;
the uniform observed temperature is explicitly controlled and identical.
The program tests the scalar math independently of meteorological input
preparation and NEVER changes accepted P6D/P6E physical kernels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import subprocess
import tempfile
from pathlib import Path

ORIGINAL_SHA256 = "430381b4fb87f15127e20b13cc3e99be8a0e0fccf1d5821110af7f980558d134"
FORTRAN = """
      program avetmp_replay
      include 'params.met'
      real u(mxnx,mxny),v(mxnx,mxny),zt(mxnx,mxny),t
      integer nx,ny,i,j
      nx=50
      ny=50
      open(31,file='wind.bin',form='unformatted',
     1     access='stream',status='old')
      read(31)u,v,t
      close(31)
      do i=1,nx
         do j=1,ny
            zt(i,j)=t
         enddo
      enddo
      call avetmp(nx,ny,1,30.,100.,u,v,zt)
      open(32,file='fortran.bin',form='unformatted',
     1     access='stream',status='replace')
      write(32)zt
      close(32)
      end
"""
CPP = r"""
#include "cteas/p6e/avetmp.hpp"
#include <fstream>
#include <vector>
#include <stdexcept>
#include <cstddef>
int main() {
    std::ifstream in("wind.bin",std::ios::binary);
    if(!in)throw std::runtime_error("missing wind");
    cteas::p6e::AvetmpInput a;
    a.nx=50;a.ny=50;a.dgrid_m=100.f;a.hafang_deg=30.f;a.mnmdav=1;
    a.u_ms.resize(2500);a.v_ms.resize(2500);
    in.read(reinterpret_cast<char*>(a.u_ms.data()),10000);
    in.read(reinterpret_cast<char*>(a.v_ms.data()),10000);
    float t=0.f;
    in.read(reinterpret_cast<char*>(&t),4);
    if(!in)throw std::runtime_error("short source input");
    a.temperature_k.assign(2500,t);
    const auto out=cteas::p6e::avetmp(a);
    std::ofstream f("cpp.bin",std::ios::binary);
    f.write(reinterpret_cast<const char*>(out.data()),10000);
    if(!f)throw std::runtime_error("cannot emit C++ output");
}
"""

def run(cmd, cwd: Path):
    p=subprocess.run([str(x) for x in cmd],cwd=cwd,check=True,
                     text=True,capture_output=True)
    if p.stdout or p.stderr:
        print("COMMAND",cmd,"STDOUT",p.stdout[-2000:],"STDERR",p.stderr[-2000:])

def values(file: Path) -> tuple[float,...]:
    raw=file.read_bytes()
    if len(raw)!=10000:raise RuntimeError("wrong AVETMP output length")
    return struct.unpack("<2500f",raw)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--vendor",type=Path,required=True)
    ap.add_argument("--candidate",type=Path,required=True)
    ap.add_argument("--cpp-include",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--gfortran",default="gfortran-11")
    ap.add_argument("--gxx",default="g++-12")
    ap.add_argument("--hours",default="2022-01-01_19,2022-01-06_12")
    ap.add_argument("--temperatures",default="273.15,290.5")
    args=ap.parse_args()
    raw=args.vendor.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ORIGINAL_SHA256:
        raise RuntimeError("original source not frozen")
    from sys import path as sys_path
    sys_path.insert(0,str(Path(__file__).resolve().parents[1]/
                         "native_cpp/modules/p6_calmet/p6e/reference"))
    from compare_original_avetmp import extract
    routine,source_lines=extract(raw)
    reports=[]
    with tempfile.TemporaryDirectory(prefix="p6d-avetmp-realwind-") as directory:
        root=Path(directory)
        (root/"params.met").write_text(
            "      integer mxnx,mxny,io6\n"
            "      parameter(mxnx=50,mxny=50,io6=6)\n")
        (root/"original.for").write_text(routine)
        (root/"driver.for").write_text(FORTRAN)
        (root/"cpp.cpp").write_text(CPP)
        run([args.gfortran,"-O0","-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-I"+str(root),
             "driver.for","original.for","-o","original"],root)
        run([args.gxx,"-O3","-std=c++20","-ffp-contract=off",
             "-I"+str(args.cpp_include.resolve()),"cpp.cpp","-o","cpp"],root)
        for label in args.hours.split(","):
            wind_u=args.candidate/f"wind1_u_{label}.f32"
            wind_v=args.candidate/f"wind1_v_{label}.f32"
            uu,vv=wind_u.read_bytes(),wind_v.read_bytes()
            if len(uu)<10000 or len(vv)<10000:
                raise RuntimeError("missing or short real WIND1 fields: "+label)
            for tempstr in args.temperatures.split(","):
                scalar=struct.unpack("<f",struct.pack("<f",float(tempstr)))[0]
                payload=uu[:10000]+vv[:10000]+struct.pack("<f",scalar)
                (root/"wind.bin").write_bytes(payload)
                run([root/"original"],root)
                run([root/"cpp"],root)
                a,b=values(root/"fortran.bin"),values(root/"cpp.bin")
                diffs=[abs(x-y) for x,y in zip(a,b)]
                worst=max(range(2500),key=diffs.__getitem__)
                target=(19-1)*50+(12-1)
                reports.append({
                    "hour":label,"uniform_temperature_K":scalar,
                    "same_input_SHA256":hashlib.sha256(payload).hexdigest(),
                    "max_abs_difference_K":diffs[worst],
                    "exceedances_at_strict_1e-4_K":sum(d>1e-4 for d in diffs),
                    "worst":{"i":worst%50+1,"j":worst//50+1,
                             "fortran_K":a[worst],"cpp_K":b[worst]},
                    "Jan1_19_prior_worst_cell":{"i":12,"j":19,
                             "fortran_K":a[target],"cpp_K":b[target],
                             "abs_difference_K":diffs[target]}
                })
    result={
        "status":"FORENSIC_ONLY_DO_NOT_PROMOTE_FINAL_ACCEPTANCE",
        "original_vendor_sha256":ORIGINAL_SHA256,
        "original_unmodified_AVETMP_source_lines":source_lines,
        "same_real4_wind_for_fortran_and_cpp":True,
        "grid":[50,50],"controls":{"MNMDAV":1,"HAFANG":30,"DGRID":100},
        "samples":reports}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__":
    main()

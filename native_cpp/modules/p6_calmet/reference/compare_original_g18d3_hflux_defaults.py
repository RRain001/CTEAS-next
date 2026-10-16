#!/usr/bin/env python3
"""G18D3: strict original CALMET 6.5.0 BLOCK DATA HFLUX default parity.

Extract the literal vendor DATA statements and literal SETCOM HC3P1
assignment, compile in REAL*4 gfortran and compare bit patterns to the
actual G18D3 native HFLUX coefficients. No hand-authored reference values.
"""
import argparse
import json
import pathlib
import re
import struct
import subprocess
import tempfile


def extract_vendor(vendor: str) -> str:
    lines=vendor.splitlines()
    def one(pattern: str) -> str:
        found=[line for line in lines if re.fullmatch(pattern,line,re.I)]
        if len(found)!=1:
            raise RuntimeError(f"Expected one literal Fortran source: {pattern}; found {len(found)}")
        return found[0]
    first=one(r"\s{6}data\s+ha1/990\./,\s*ha2/-30\./,\s*hb1/-0\.75/,\s*hb2/3\.4/\s*")
    second=one(r"\s{6}data\s+hc1/5\.31e-13/,\s*hc2/60\./,\s*hc3/0\.12/\s*")
    computed=one(r"\s{6}hc3p1=hc3\+1\.0\s*")
    return ("      program original_hflux_default\n"
            "      real ha1,ha2,hb1,hb2,hc1,hc2,hc3,hc3p1\n"
            +first+"\n"+second+"\n"+computed+"\n"
            "      write(*,'(ES26.17)') ha1,ha2,hb1,hb2,hc1,hc2,hc3p1\n"
            "      end\n")


def bits(text: str) -> list[bytes]:
    data=[float(line.replace("D","E")) for line in text.splitlines() if line.strip()]
    if len(data)!=7:
        raise AssertionError(f"source HFLUX expected exactly seven entries, got {len(data)}")
    return [struct.pack("<f",v) for v in data]


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--vendor",type=pathlib.Path,required=True)
    p.add_argument("--cpp",type=pathlib.Path,required=True)
    p.add_argument("--gfortran",default="gfortran")
    p.add_argument("--out",type=pathlib.Path,required=True)
    a=p.parse_args()
    program=extract_vendor(a.vendor.read_text(encoding="latin-1"))
    with tempfile.TemporaryDirectory(prefix="g18d3-hflux-") as directory:
        root=pathlib.Path(directory)
        src=root/"original_hflux.f"
        exe=root/"original_hflux"
        src.write_text(program,encoding="ascii")
        subprocess.run([a.gfortran,"-O0","-ffixed-line-length-none",
                        str(src),"-o",str(exe)],
                       check=True,text=True,capture_output=True)
        original=bits(subprocess.run([str(exe)],check=True,
                          capture_output=True,text=True).stdout)
        actual=bits(subprocess.run([str(a.cpp)],check=True,
                          capture_output=True,text=True).stdout)
        for k,(native,source) in enumerate(zip(actual,original)):
            if native!=source:
                raise AssertionError(f"HFLUX default REAL4 vendor mismatch at {k}: "
                                     f"C++={native.hex()}, vendor={source.hex()}")
    result={"status":"PASS_G18D3_LITERAL_VENDOR_HFLUX_REAL4_DEFAULTS",
            "default_fields":["HA1","HA2","HB1","HB2","HC1","HC2","HC3P1"],
            "values_checked":7,"tolerance":"exact REAL4 bits, zero exceptions",
            "scope":"BLOCK DATA defaults with pinned met.inp no override",
            "not_accepted":"full source CALMET multi-SS/US HEATFX/COMP hour"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(result["status"])


if __name__=="__main__":
    main()

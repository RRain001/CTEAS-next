#!/usr/bin/env python3
"""Strict original vendor VMASS numerical parity, real original source.

Extracts the *unchanged original* VMASS Fortran routine and all original
.puf declarations. Compiles it under gfortran-11 with a tiny read-only driver,
then checks each resulting REAL*4 physical state against standalone C++.
No copied formula or oracle-fed native solver state is used in this comparison.
"""
from __future__ import annotations
import argparse
import hashlib
import itertools
import math
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from collections import Counter

PIN="da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568"
ARGS={"ii","mfact0","nspec","istab","dpbl","icode","hlid"}
def f32(x):
    return struct.unpack("<f",struct.pack("<f",x))[0]

def records():
    rows=[]
    # All original puff/slug vertical codes 1-6,11-16 with mixed, upper and
    # two-layer mass. Distinct code/lid/stability transitions, tilt options.
    for code,stab,pbl,old,zmax,sigma,pattern in itertools.product(
        (1,2,3,4,5,6,11,12,13,14,15,16),
        (4,6),(70,100,110,150,250),
        (90,140),(200,300),(2,40,200),
        ((60,40,20,10),(60,0,20,0),(0,40,0,10))):
        # Keep one compact but comprehensive deterministic oracle matrix.
        # Slugs use separate ZPE and SIGZE, and tilt shifts wellmixed limit.
        values=(code,stab,(1 if (code+stab)%3==0 else 0),
                pbl,100,(110 if code>=11 else 100),
                sigma,(sigma*1.5 if code>=11 else sigma),
                old,zmax,*pattern)
        rows.append((len(rows)+1,*values))
    return rows

def signature(text):
    # Vendor fixed-form continuation lines are joined without altering
    # original source written to the compiler.
    lines=text.splitlines()
    prefix=" ".join(l[6:72].lstrip("& ") for l in lines[:10]
                    if len(l)>=7 and l[0] not in "cC*!")
    m=re.search(r"\bsubroutine\s+vmass\s*\(([^)]+)\)",prefix,re.I)
    if not m:
        raise RuntimeError("original VMASS declaration could not be parsed")
    args=[x.strip().lower() for x in m.group(1).split(",")]
    if set(args)!=ARGS or len(args)!=len(ARGS):
        raise RuntimeError("VMASS original Fortran argument contract changed: "+repr(args))
    return args

def driver(args):
    call=", ".join(args)
    # Fixed-form 72-column lines. The only source-physics routine compiled
    # is extracted verbatim from the original vendor CALPUFF source.
    return f"""      program p7_vmass_reference
      include 'params.puf'
      include 'flags.puf'
      include 'puff.puf'
      include 'slug.puf'
      integer ii,mfact0,nspec,istab,icode,icase,ios
      real dpbl,hlid
 10   continue
      read(*,*,iostat=ios) icase,icode,istab,mtilt,dpbl,
     & zpb(1),zpe(1),sigzb(1),sigze(1),ziold(1),zimax(1),
     & qm(1,1),qu(1,1),qm(2,1),qu(2,1)
      if(ios.ne.0) goto 999
      ii=1
      nspec=2
      mfact0=0
      if(icode.ge.11) mfact0=10
      call vmass({call})
      write(*,'(i8,1x,i3,7(1x,es24.16))') icase,icode,
     & hlid,ziold(1),zimax(1),qm(1,1),qu(1,1),
     & qm(2,1),qu(2,1)
      goto 10
 999  continue
      end
"""

def parse(out):
    records={}
    for line in out.splitlines():
        sp=line.split()
        if len(sp)!=9:continue
        try:
            key=int(sp[0]);code=int(sp[1])
            values=[f32(float(v.replace("D","E"))) for v in sp[2:]]
        except (ValueError,OverflowError):continue
        if key in records:raise ValueError(f"duplicate output case {key}")
        records[key]=(code,values)
    return records

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--native",required=True,type=Path)
    ap.add_argument("--vendor",required=True,type=Path)
    ap.add_argument("--fortran",default="gfortran-11")
    opts=ap.parse_args()
    raw=opts.vendor.joinpath("calpuff.for").read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PIN:raise RuntimeError("original CALPUFF SHA drift")
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"reference"))
    import p7v_source_anchor as ref
    lines=raw.decode("latin-1").splitlines()
    start,end=ref.find_span(lines,"vmass",ref.headers(lines))
    vmass="\n".join(lines[start:end+1])+"\n"
    args=signature(vmass)
    rows=records()
    payload="\n".join(" ".join(str(v) for v in row) for row in rows)+"\n"
    native=subprocess.run([str(opts.native)],input=payload,text=True,
                          capture_output=True,check=True)
    cpp=parse(native.stdout)
    if len(cpp)!=len(rows):raise ValueError("native output case coverage incomplete")
    if not shutil.which(opts.fortran):raise RuntimeError("gfortran compiler REQUIRED")
    with tempfile.TemporaryDirectory(prefix="p7-vmass-fortran-") as d:
        stage=Path(d)
        (stage/"vmass_original.f").write_bytes(vmass.encode("latin-1"))
        (stage/"oracle_driver.f").write_text(driver(args))
        for inc in opts.vendor.glob("*.puf"):
            shutil.copy2(inc,stage/inc.name)
        cmd=[opts.fortran,"-O0","-std=legacy","-ffixed-line-length-72",
             "-fallow-argument-mismatch","-fno-automatic",
             "-I"+str(stage),"-o",str(stage/"oracle"),
             str(stage/"vmass_original.f"),str(stage/"oracle_driver.f")]
        built=subprocess.run(cmd,capture_output=True,text=True)
        if built.returncode:
            raise RuntimeError("original VMASS compiler failed: "+built.stderr[-3000:])
        fortran=subprocess.run([str(stage/"oracle")],input=payload,text=True,
                               capture_output=True,cwd=stage)
        if fortran.returncode:
            raise RuntimeError("original VMASS failed: "+fortran.stderr[-1000:])
        wanted=parse(fortran.stdout)
    if len(wanted)!=len(rows):
        raise RuntimeError(f"original VMASS returned {len(wanted)}/{len(rows)} records")
    mismatch=[]
    mismatched_bits=0
    by_code=Counter()
    for key in sorted(wanted):
        expected=wanted[key]
        got=cpp.get(key)
        if got is None:raise RuntimeError(f"native missing case {key}")
        by_code[rows[key-1][1]]+=1
        for field,(a,b) in enumerate(zip(expected[1],got[1])):
            if struct.pack("<f",a)!=struct.pack("<f",b):
                mismatched_bits+=1
                if len(mismatch)<12:
                    mismatch.append({"case":key,"field":field,
                        "source_code":rows[key-1][1],
                        "fortran":a,"native":b,"inputs":rows[key-1]})
        if expected[0]!=got[0]:
            mismatched_bits+=1
            if len(mismatch)<12:
                mismatch.append({"case":key,"code_expected":expected[0],
                    "code_native":got[0],"inputs":rows[key-1]})
    if mismatch:
        raise RuntimeError("ORIGINAL_VMASS_FIRST_DIVERGENCES "+
                           repr(mismatch)+"; mismatched_fields="+str(mismatched_bits))
    print("P7_NATIVE_VMASS_ORIGINAL_FORTRAN=PASS"
          f" CASES={len(rows)} CODES={len(by_code)} FIELDS_PER_CASE=8"
          " EXACT_REAL4_BITS=TRUE"
          " ORIGINAL_VENDOR_VMASS_UNMODIFIED=TRUE")
    print("P7_NATIVE_VMASS_WHOLE_COMP_143H=NOT_YET_VALIDATED")

if __name__=="__main__":
    try:main()
    except (OSError,RuntimeError,ValueError,subprocess.CalledProcessError) as e:
        print("P7_NATIVE_VMASS_ORIGINAL_FORTRAN=FAIL "+str(e),file=sys.stderr)
        sys.exit(1)

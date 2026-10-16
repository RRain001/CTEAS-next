#!/usr/bin/env python3
"""Independent original Fortran vs native C++ G11 TERSET→FRADJ→SLOPE.

Literal original CALMET 6.5.0 TERSET/FRADJ/SLOPE routines compiled from the
unchanged vendored source. Input: 12x12x9, 10km, nonflat original-format
synthetic terrain and synthetic thermal fields, source-selected ISURFT=-1.
This verifies the *joined terrain stage*, not the whole CALMET/P6E model.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import subprocess
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
VENDOR=ROOT/"engine/vendor/src/CALMET_v6.5.0_L150223"
CALMET=VENDOR/"calmet.for"
CPP=ROOT/"native_cpp/modules/p6_calmet/tests/p6g_g11_original_terrain_probe.cpp"
INCLUDE=ROOT/"native_cpp/modules/p6_calmet/include"
SOURCE_BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
FORTRAN_DRIVER="""      program p6g11terrain
      include 'params.met'
      include 'grid.met'
      include 'metgrd.met'
      include 'geo.met'
      include 'd6.met'
      real topo(mxnx,mxny),highest(mxnx,mxny)
      real gam(mxnx,mxny),sfct(mxnx,mxny)
      real u(mxnx,mxny,mxnz),v(mxnx,mxny,mxnz)
      real du(mxnx,mxny,mxnz),dv(mxnx,mxny,mxnz)
      real terrad,critfn,tinf
      nx=12
      ny=12
      nz=9
      dx=10000.
      dy=10000.
      iwr=0
      iwat1=50
      iwat2=55
      isurft=-1
      tinf=285.
      critfn=10.
      terrad=35.
      zface(1)=0.
      zface(2)=20.
      zface(3)=40.
      zface(4)=80.
      zface(5)=160.
      zface(6)=320.
      zface(7)=640.
      zface(8)=1200.
      zface(9)=2000.
      zface(10)=3000.
      do k=1,nz
         dz(k)=zface(k+1)-zface(k)
      enddo
      do j=1,ny
         do i=1,nx
            topo(i,j)=100.+250.*(i-1)+150.*(j-1)
            gam(i,j)=0.002
            sfct(i,j)=280.
            qh(i,j)=-120.
            ilandu(i,j)=20
            if(i.eq.4.and.j.eq.4)ilandu(i,j)=50
            disthmax(i,j)=0.
            disthmin(i,j)=0.
            do k=1,nz
               u(i,j,k)=3.
               v(i,j,k)=1.
            enddo
         enddo
      enddo
      call terset(topo,highest,terrad)
      call fradj(u,v,topo,gam,isurft,tinf,sfct,critfn,
     1           zface,highest)
      call slope(du,dv,topo,isurft,tinf,sfct,highest)
      do k=1,nz
         do j=1,ny
            do i=1,nx
               u(i,j,k)=u(i,j,k)+du(i,j,k)
               v(i,j,k)=v(i,j,k)+dv(i,j,k)
               write(*,'(A,3(1X,I3),2(1X,ES17.9))')
     1              'GRID',i,j,k,u(i,j,k),v(i,j,k)
            enddo
         enddo
      enddo
      end
c -- Original physical subroutines remain unmodified. Stubbed auxiliaries
c -- are diagnostics/zero-initialisation helpers from original SLOPE harness.
      subroutine xmit(n,val,a)
      real val,a(*)
      do i=1,iabs(n)
         a(i)=val
      enddo
      end
      subroutine wndlpt(a)
      real a(*)
      return
      end
"""


def original_chunks(directory: Path)->tuple[list[Path],str]:
    source=CALMET.read_bytes()
    got=hashlib.sha1(f"blob {len(source)}\\0".encode().replace(b"\\0",b"\0")+source).hexdigest()
    if got!=SOURCE_BLOB:
        raise ValueError("CALMET vendor original source SHA drift: "+got)
    rows=source.decode("latin-1").splitlines(keepends=True)
    def start(name):
        found=[i for i,row in enumerate(rows)
               if row.lower().startswith(f"      subroutine {name}(")]
        if len(found)!=1:
            raise ValueError("CALMET original "+name+" anchor ambiguous")
        return found[0]
    parts=[]
    for name,end in (("terset","topof2"),("fradj","gride")):
        i=start(name);j=start(end)
        if j<=i:raise ValueError("CALMET "+name+" original range drift")
        p=directory/(name+".for")
        p.write_text("".join(rows[i:j]),encoding="latin-1")
        parts.append(p)
    i=start("slope")
    j=next((k for k in range(i+1,len(rows))
            if rows[k].lower().startswith("      subroutine ")),None)
    if j is None:raise ValueError("CALMET original SLOPE terminator absent")
    p=directory/"slope.for"
    p.write_text("".join(rows[i:j]),encoding="latin-1")
    parts.append(p)
    return parts,hashlib.sha256(source).hexdigest()


def rows_from(text: str)->dict[tuple[int,int,int],tuple[float,float]]:
    out={}
    for line in text.splitlines():
        row=line.strip().split()
        if not row or row[0]!="GRID":
            continue
        if len(row)!=6:
            raise ValueError("G11 malformed source U/V row: "+line)
        key=tuple(int(q) for q in row[1:4])
        if key in out:
            raise ValueError("G11 duplicate source U/V cell")
        values=tuple(float(q.replace("D","E")) for q in row[4:])
        if not all(math.isfinite(q) for q in values):
            raise ValueError("G11 nonfinite source U/V")
        out[key]=values
    if len(out)!=12*12*9:
        raise ValueError(f"G11 wrong 10km 3D source cell count: {len(out)}")
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=("Debug","Release"),required=True)
    args=ap.parse_args()
    opt="-O0" if args.mode=="Debug" else "-O2"
    with tempfile.TemporaryDirectory(prefix="p6g-g11-vendor-") as directory:
        temp=Path(directory)
        files,original_sha=original_chunks(temp)
        driver=temp/"original_g11_terrain.for"
        driver.write_text(FORTRAN_DRIVER)
        original=temp/"vendor_terrain"
        native=temp/"g11_native"
        subprocess.run(["gfortran",opt,"-std=legacy","-fno-automatic",
                        "-ffixed-line-length-none","-I"+str(VENDOR),
                        *[str(p) for p in files],str(driver),"-o",str(original)],
                       check=True)
        subprocess.run(["g++","-std=c++20",opt,"-Wall","-Wextra","-Wpedantic",
                        "-Werror","-I",str(INCLUDE),str(CPP),"-o",str(native)],
                       check=True)
        f=subprocess.run([str(original)],capture_output=True,text=True,check=True)
        c=subprocess.run([str(native)],capture_output=True,text=True,check=True)
        original_rows=rows_from(f.stdout)
        native_rows=rows_from(c.stdout)
        if original_rows.keys()!=native_rows.keys():
            raise ValueError("G11 original and native spatial indices differ")
        highest=0.
        failures=[]
        adjusted=0
        for index in original_rows:
            for i,(a,b) in enumerate(zip(original_rows[index],native_rows[index])):
                delta=abs(a-b)
                highest=max(highest,delta)
                if abs(a-(3.0 if i==0 else 1.0))>1.e-4:
                    adjusted+=1
                if delta>2e-4 and len(failures)<10:
                    failures.append((index,i,a,b,delta))
        if adjusted==0:
            raise AssertionError("G11 original Fortran terrain source generated no nontrivial corrections")
        if failures:
            raise AssertionError(
                f"G11 original CALMET TERSET→FRADJ→SLOPE failed: "
                f"max_abs={highest:.9g}; failures={failures}")
        print("PASS_G11_ORIGINAL_FORTRAN_TERRAIN_COMBINED "
              f"mode={args.mode} grid=12x12x9 spacing_km=10 "
              f"uv_compared={2*len(original_rows)} "
              f"original_adjusted_components={adjusted} "
              f"max_abs_delta={highest:.9g} original_sha256={original_sha}")
        print(c.stderr.strip())


if __name__=="__main__":
    main()

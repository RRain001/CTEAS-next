#!/usr/bin/env python3
"""Numerically compare unmodified CALMET TERSET→FRADJ against independent C++.

Only original Fortran subroutines are extracted verbatim from CALMET 6.5.0;
this is not a Python reimplementation of either physical equation. Tested
together with the exact 2022 P3 GEO.DAT terrain and analytic case grids.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,subprocess
from pathlib import Path
from native_cpp.modules.p6_calmet.reference.compare_original_terset import real_terrain

DRIVER="""      program testfr
      include 'params.met'
      include 'grid.met'
      include 'd6.met'
      real topo(mxnx,mxny),highest(mxnx,mxny)
      real gam(mxnx,mxny),sfct(mxnx,mxny)
      real u(mxnx,mxny,mxnz),v(mxnx,mxny,mxnz)
      real terrad,critfn,tinf
      character*256 fin,fout,arg
      call get_command_argument(1,fin)
      call get_command_argument(2,fout)
      call get_command_argument(3,arg)
      read(arg,*) terrad
      call get_command_argument(4,arg)
      read(arg,*) critfn
      call get_command_argument(5,arg)
      read(arg,*) isurft
      nx=50
      ny=50
      nz=9
      dx=100.0
      dy=100.0
      tinf=285.0
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
      open(10,file=trim(fin),status='old')
      do j=1,ny
        read(10,*) (topo(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (gam(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (sfct(i,j),i=1,nx)
      enddo
      do k=1,nz
        do j=1,ny
          read(10,*) (u(i,j,k),i=1,nx)
        enddo
      enddo
      do k=1,nz
        do j=1,ny
          read(10,*) (v(i,j,k),i=1,nx)
        enddo
      enddo
      close(10)
      do j=1,ny
        do i=1,nx
          disthmax(i,j)=0.
          disthmin(i,j)=0.
        enddo
      enddo
      call terset(topo,highest,terrad)
      call fradj(u,v,topo,gam,isurft,tinf,sfct,critfn,
     1           zface,highest)
      open(11,file=trim(fout),status='replace')
      do k=1,nz
        do j=1,ny
          do i=1,nx
            write(11,'(3(I4,1X),2(ES22.13E3,1X))')
     1        i,j,k,u(i,j,k),v(i,j,k)
          enddo
        enddo
      enddo
      close(11)
      end
"""

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(argv,timeout=90):
    p=subprocess.run(list(map(str,argv)),timeout=timeout,text=True,capture_output=True)
    if p.returncode:raise RuntimeError(f"failed: {argv} rc={p.returncode} out={p.stdout[-1600:]} err={p.stderr[-2500:]}")
def extract(src,start,end,out):
    a=src.read_text().splitlines(keepends=True)
    lo=[i for i,x in enumerate(a) if x.lower().startswith(f"      subroutine {start}(")]
    hi=[i for i,x in enumerate(a) if x.lower().startswith(f"      subroutine {end}(")]
    if len(lo)!=1 or len(hi)!=1 or not lo[0]<hi[0]:
        raise RuntimeError("CALMET Fortran source anchors not unique")
    text="".join(a[lo[0]:hi[0]])
    out.write_text(text)
    return {"source_first_line":lo[0]+1,"source_last_line":hi[0],
            "extracted_sha256":sha(out)}

def grids(actual):
    flat=[80.0]*2500
    hill=[100.0+160*math.exp(-((i-21)**2+(j-24)**2)/90.0)
          for j in range(50) for i in range(50)]
    ridge=[105+65*math.sin(i*.13)+25*math.cos(j*.17)+3*((i+j)%5)
           for j in range(50) for i in range(50)]
    yield "flat_calm_no_adjust",flat,[0.006]*2500,[285.0]*2500,"calm",1.0,-1
    yield "ridge_stable_weak_wind",ridge,[0.006]*2500,[280+2*math.sin(i*.13) for j in range(50) for i in range(50)],"weak",1.0,-1
    yield "hill_stable_weak_wind",hill,[0.006]*2500,[285.0]*2500,"weak",1.0,-1
    yield "hill_unstable_no_adjust",hill,[-0.015]*2500,[285.0]*2500,"weak",1.0,-1
    yield "hill_high_speed_no_adjust",hill,[0.006]*2500,[285.0]*2500,"strong",1.0,-1
    yield "hill_domain_temperature",hill,[0.006]*2500,[276+3*math.cos(j*.04) for j in range(50) for i in range(50)],"weak",1.0,1
    yield "original_p3_terrain_2022",actual,[0.006]*2500,[285.0]*2500,"weak",1.0,-1

def initial_winds(mode):
    u,v=[],[]
    for k in range(9):
        for j in range(50):
            for i in range(50):
                if mode=="calm":
                    x,y=0.0,0.0
                elif mode=="strong":
                    x,y=15.0,5.0
                else:
                    x=1.1+0.4*math.sin(j*.29+k*.17)
                    y=0.7+0.3*math.cos(i*.24-k*.12)
                u.append(x);v.append(y)
    return u,v

def write_case(file,terrain,gamma,temp,u,v):
    if any(len(x)!=n for x,n in [(terrain,2500),(gamma,2500),
                                  (temp,2500),(u,22500),(v,22500)]):
        raise ValueError("FRADJ input shape bad")
    with file.open("w") as f:
        for field in (terrain,gamma,temp,u,v):
            for j in range(0,len(field),50):
                f.write(" ".join(f"{v:.8f}" for v in field[j:j+50])+"\n")

def compare(ref,modern,raw_u,raw_v):
    a=[list(map(float,x.split())) for x in ref.read_text().splitlines()]
    with modern.open(newline="") as f:b=list(csv.DictReader(f))
    if len(a)!=22500 or len(b)!=22500:raise RuntimeError("expect 22500 original and C++ FRADJ rows")
    tolerances={"u_mps":0.0002,"v_mps":0.0002}
    maxerr={"u_mps":0.0,"v_mps":0.0}
    changes=0
    mismatch=[]
    for n,(ra,rb) in enumerate(zip(a,b)):
        i,j,k=n%50+1,n//50%50+1,n//2500+1
        if len(ra)!=5 or tuple(map(int,ra[:3]))!=(i,j,k) or\
           (int(rb["i"]),int(rb["j"]),int(rb["k"]))!=(i,j,k):
            raise ValueError("FRADJ original or C++ row order mismatch")
        for col,name,raw in [(3,"u_mps",raw_u[n]),(4,"v_mps",raw_v[n])]:
            orig,cand=ra[col],float(rb[name])
            if not math.isfinite(orig) or not math.isfinite(cand):
                raise ValueError("nonfinite FRADJ output")
            if abs(orig-raw)>0.001:changes+=1
            err=abs(orig-cand)
            maxerr[name]=max(err,maxerr[name])
            if err>tolerances[name] and len(mismatch)<20:
                mismatch.append({"i":i,"j":j,"k":k,"field":name,
                                 "orig":orig,"modern":cand,"err":err})
    return {"status":"PASS" if not mismatch else "FAIL",
            "compared_components":45000,
            "original_adjusted_components":changes,
            "max_abs_errors":maxerr,
            "predeclared_tolerances":tolerances,
            "first_mismatches":mismatch}

def main():
    pa=argparse.ArgumentParser()
    for key in ("vendor","geo","cpp","out"):
        pa.add_argument("--"+key,required=True,type=Path)
    arg=pa.parse_args()
    arg.out.mkdir(parents=True,exist_ok=True)
    original=arg.vendor/"calmet.for"
    paths=[]
    for name,after in [("terset","topof2"),("fradj","gride")]:
        dest=arg.out/(name+"_original.for")
        paths.append(extract(original,name,after,dest))
    driver=arg.out/"fradj_fortran_driver.for";driver.write_text(DRIVER)
    binary=arg.out/"original_fradj"
    run(["gfortran","-O0","-std=legacy","-fno-automatic",
         "-ffixed-line-length-none","-I"+str(arg.vendor),
         arg.out/"terset_original.for",arg.out/"fradj_original.for",
         driver,"-o",binary],timeout=65)
    report={"scope":"Original CALMET TERSET+FRADJ only (not complete diagnostic wind)",
            "original_calmet_sha256":sha(original),
            "original_subroutines":paths,"cpp_cases":{},"total_compared_components":0}
    for name,topo,gamma,temp,wind_mode,crit,isurft in grids(real_terrain(arg.geo)):
        raw_u,raw_v=initial_winds(wind_mode)
        input_file=arg.out/(name+".input")
        fortran_file=arg.out/(name+".fortran")
        cpp_file=arg.out/(name+".cpp.csv")
        write_case(input_file,topo,gamma,temp,raw_u,raw_v)
        run([binary,input_file,fortran_file,"15",str(crit),str(isurft)])
        run([arg.cpp,input_file,cpp_file,"15",str(crit),str(isurft)])
        results=compare(fortran_file,cpp_file,raw_u,raw_v)
        report["cpp_cases"][name]={"input_sha256":sha(input_file),
                "original_sha256":sha(fortran_file),**results}
        report["total_compared_components"]+=results["compared_components"]
    report["status"]="PASS_ORIGINAL_CALMET_FRADJ_FORTRAN_PARITY" if all(
        v["status"]=="PASS" for v in report["cpp_cases"].values()) else "FAIL"
    if not any(v["original_adjusted_components"]>0 for k,v in report["cpp_cases"].items()
               if "weak" in k or "ridge" in k):
        report["status"]="FAIL_NO_ACTUAL_FROUDE_ADJUSTMENTS_IN_TESTS"
    (arg.out/"p6d-fradj-parity.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if report["status"]!="PASS_ORIGINAL_CALMET_FRADJ_FORTRAN_PARITY":
        raise SystemExit(1)
if __name__=="__main__":
    main()

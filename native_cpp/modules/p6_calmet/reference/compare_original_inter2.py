#!/usr/bin/env python3
"""CALMET 6.5.0 literal unchanged INTER2 against C++ selected I3DCTW=1 path.
Only NOOBS=0, IPROG=0, NBAR=0. Synthetic scenarios, NOT real 2022 U/V/W.
"""
import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
NX=NY=50
NZ=9
NC=NX*NY
ABS_TOL_MPS=2e-4

DRIVER="""      program inter2verify
      include 'params.met'
      include 'wtgrd.met'
      include 'wparm.met'
      include 'grid.met'
      include 'mm4hdo.met'
      include 'd3.met'
      include 'd4.met'
      include 'd6.met'
      real stdat(mxnz,mxwnd),xst(mxwnd),yst(mxwnd)
      real rs(mxwnd),work(mxwnd)
      integer ist(mxwnd),nintrp(mxnz)
      real output(mxnx,mxny,mxnz),fg(mxnx,mxny,mxnz)
      real pdat(mxnxp,mxnyp,mxnz)
      integer lu(mxnx,mxny),lvflag,nst,nostations
      character*256 infile,outfile
      call get_command_argument(1,infile)
      call get_command_argument(2,outfile)
      nx=50
      ny=50
      nz=9
      dx=100.
      dy=100.
      iwr=0
      iprog=0
      nbar=0
      kbar=0
      noobs=0
      iwat1=50
      iwat2=55
      open(10,file=trim(infile),status='old')
      read(10,*) nst,lvflag,rmin,rmax1,rmax2,rmax3,
     1           r1,r2,edit,editl
      lvary=lvflag.ne.0
      read(10,*) (nintrp(k),k=1,nz)
      read(10,*) (xst(l),l=1,nst)
      read(10,*) (yst(l),l=1,nst)
      do j=1,ny
        read(10,*) (lu(i,j),i=1,nx)
      enddo
      do k=1,nz
        read(10,*) (stdat(k,l),l=1,nst)
      enddo
      do k=1,nz
        do j=1,ny
          read(10,*) (fg(i,j,k),i=1,nx)
        enddo
      enddo
      do k=1,nz
        do j=1,ny
          read(10,*) (wo(i,j,k),i=1,nx)
        enddo
      enddo
      close(10)
      call xmit(-mxnx*mxny*mxnz,0.,output)
      call inter2(stdat,nst,xst,yst,
     1           nintrp,rs,ist,work,output,fg,lu,
     2           iwat1,iwat2,pdat,noobs)
      open(11,file=trim(outfile),status='replace')
      do k=1,nz
        do j=1,ny
          do i=1,nx
            write(11,'(3(I4,1X),ES22.13E3)')
     1      i,j,k,output(i,j,k)
          enddo
        enddo
      enddo
      close(11)
      end
c --- Unreachable only when unsupported NBAR>0; fail before that branch.
      subroutine barier(x,y,xs,ys,ok)
      real x,y,xs,ys,ok
      ok=1.
      end
"""

def run(args):
    p=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=140)
    if p.returncode:
        raise RuntimeError(f"{args} rc={p.returncode} stdout={p.stdout[-900:]} stderr={p.stderr[-2300:]}")

def extract_original(vendor,output):
    raw=(vendor/"calmet.for").read_bytes()
    git_sha=hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()
    if git_sha!=BLOB:raise RuntimeError("original source unexpectedly changed "+git_sha)
    lines=raw.decode().splitlines(keepends=True)
    def location(name):
        a=[i for i,x in enumerate(lines)
           if x.lower().startswith(f"      subroutine {name}(")]
        if len(a)!=1:raise RuntimeError("invalid original Fortran source anchor "+name)
        return a[0]
    sources=[]
    for name,next_name,anchor in (
        ("inter2","interb",8124),
        ("fminf","fradj",7256),
        ("xmit","outpc1",36951)):
        a,b=location(name),location(next_name)
        if a+1!=anchor or b<=a:raise RuntimeError("original source line drift "+name)
        file=output/(name+"_original.for")
        file.write_text("".join(lines[a:b]))
        sources.append((file,{"subroutine":name,"start_line":a+1,
                              "end_line":b,"sha256":hashlib.sha256(file.read_bytes()).hexdigest()}))
    return sources

def cases():
    for name,nst,lvary in (
        ("well_inside_all",4,False),
        ("missing_levels_land_water",4,False),
        ("lvary_radius_fallback",3,True),
        ("equal_station_distances_and_zero_weight",2,True)):
        xst,yst=[],[]
        # Deliberately varied positions near the 5km square edges.
        xy=[(0.05,0.05),(4.95,4.95),(2.1,1.7),(3.6,3.9)]
        xst=[x for x,_ in xy[:nst]]
        yst=[y for _,y in xy[:nst]]
        data=[]
        for k in range(NZ):
            for l in range(nst):
                v=2.5+0.5*l+0.13*k
                if name=="missing_levels_land_water" and l%2==0 and k%3==1:
                    v=999999.
                data.append(v)
        if name=="equal_station_distances_and_zero_weight":
            xst=[0.0,0.1]
            yst=[0.0,0.1]
        grid=[];weight=[];lu=[]
        for j in range(NY):
            for i in range(NX):
                lu.append(52 if name=="missing_levels_land_water" and i<20 else 10)
        for k in range(NZ):
            for j in range(NY):
                for i in range(NX):
                    grid.append(1.1+0.02*i-0.01*j+0.1*k)
                    weight.append(0.0 if name=="equal_station_distances_and_zero_weight" and j%3==0 else
                                  0.55+0.05*((k+i)%6))
        radii=[0.05,12,12,12,0.6,1.5]
        if name=="lvary_radius_fallback":radii=[0.05,0.1,0.1,0.1,0.6,1.5]
        if name=="equal_station_distances_and_zero_weight":radii=[0.05,1,1,1,0.6,1.5]
        nintrp=[min(nst,2 if k%2==0 else 3) for k in range(NZ)]
        yield name,nst,lvary,radii,nintrp,xst,yst,lu,data,grid,weight

def write_input(path,case):
    name,nst,lvary,radii,nintrp,xst,yst,lu,data,grid,weight=case
    with path.open("w") as f:
        f.write(f"{nst} {int(lvary)} "+ " ".join(map(str,radii))+
                " 999999 999998\n")
        f.write(" ".join(map(str,nintrp))+"\n")
        f.write(" ".join(map(str,xst))+"\n")
        f.write(" ".join(map(str,yst))+"\n")
        for arr,width in ((lu,NX),(data,nst),(grid,NX),(weight,NX)):
            for n in range(0,len(arr),width):
                f.write(" ".join(str(int(x)) if arr is lu else f"{x:.8f}"
                                 for x in arr[n:n+width])+"\n")

def compare(original,modern,first_guess):
    a=[line.split() for line in original.read_text().splitlines()]
    with modern.open(newline="") as f:
        b=list(csv.DictReader(f))
    if len(a)!=NC*NZ or len(b)!=NC*NZ:
        raise RuntimeError("INTER2 grid dimensions mismatch")
    max_err=0.;mismatches=[];nonzero_blends=0
    for n,(r,c) in enumerate(zip(a,b)):
        idx=(n%NX+1,(n//NX)%NY+1,n//NC+1)
        if len(r)!=4 or tuple(map(int,r[:3]))!=idx or (
            int(c["i"]),int(c["j"]),int(c["k"]))!=idx:
            raise RuntimeError(f"INTER2 grid order mismatch {idx}")
        x,y=float(r[3]),float(c["component_mps"])
        if not(math.isfinite(x) and math.isfinite(y)):
            raise RuntimeError(f"INTER2 nonfinite output {idx}, reference={x},cpp={y}")
        nonzero_blends+=abs(x-first_guess[n])>1e-5
        err=abs(x-y);max_err=max(max_err,err)
        if err>ABS_TOL_MPS and len(mismatches)<12:
            mismatches.append({"ijk":idx,"original":x,"cpp":y,"abs_error":err})
    return {"status":"PASS" if not mismatches else "FAIL",
            "components_compared":NC*NZ,"nontrivial_obs_blends":nonzero_blends,
            "max_abs_error_mps":max_err,"first_mismatches":mismatches}

def main():
    p=argparse.ArgumentParser()
    for key in ("vendor","cpp","out"):p.add_argument("--"+key,type=Path,required=True)
    arg=p.parse_args();arg.out.mkdir(parents=True,exist_ok=True)
    sources=extract_original(arg.vendor,arg.out)
    driver=arg.out/"inter2_original_driver.for";driver.write_text(DRIVER)
    binary=arg.out/"original_inter2"
    run(["gfortran","-O0","-std=legacy","-fno-automatic",
         "-ffixed-line-length-none","-fallow-argument-mismatch",
         "-I"+str(arg.vendor),
         *[p for p,_ in sources],driver,"-o",binary])
    result={}
    for case in cases():
        name=case[0]
        inp=arg.out/(name+".input")
        ref=arg.out/(name+".original")
        modern=arg.out/(name+".modern.csv")
        write_input(inp,case)
        run([binary,inp,ref]);run([arg.cpp,inp,modern])
        result[name]=compare(ref,modern,case[-2])
    ok=all(x["status"]=="PASS" for x in result.values()) and all(
        x["nontrivial_obs_blends"]>0 for x in result.values())
    report={"status":"PASS_ORIGINAL_INTER2_SELECTED_IPROG0" if ok else "FAIL",
            "scope":"Only original INTER2 observation blending, synthetic 50x50x9, not actual 2022 WIND1 or full DIAGNO",
            "original_vendor_git_blob":BLOB,
            "source_extractions":[x[1] for x in sources],
            "predeclared_abs_tolerance_mps":ABS_TOL_MPS,
            "components_compared":sum(x["components_compared"] for x in result.values()),
            "cases":result}
    (arg.out/"p6d-original-inter2-parity.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if not ok:raise SystemExit(1)

if __name__=="__main__":main()

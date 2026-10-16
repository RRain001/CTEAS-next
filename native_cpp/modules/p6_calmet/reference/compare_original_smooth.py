#!/usr/bin/env python3
"""Independent unchanged original Fortran CALMET SMOOTH versus C++ source parity."""
import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

ORIGINAL_BLOB = "437f43bb7f0e51a1919e56664663e1a046986ed0"
ABS_TOL_MPS = 2.0e-4
NX=NY=50
NZ=9
N=NX*NY

DRIVER = """      program testsmooth
      include 'params.met'
      include 'grid.met'
      include 'breez.met'
      real u(mxnx,mxny,mxnz),v(mxnx,mxny,mxnz)
      real ub(mxny,2,mxnz),vb(mxnx,2,mxnz)
      integer nsmth(mxnz),side
      character*256 infile,outfile
      call get_command_argument(1,infile)
      call get_command_argument(2,outfile)
      nx=50
      ny=50
      nz=9
      llbreze=.false.
      nbox=0
      open(10,file=trim(infile),status='old')
      read(10,*) (nsmth(k),k=1,nz)
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
      do k=1,nz
        do side=1,2
          read(10,*) (ub(j,side,k),j=1,ny)
        enddo
      enddo
      do k=1,nz
        do side=1,2
          read(10,*) (vb(i,side,k),i=1,nx)
        enddo
      enddo
      close(10)
      call smooth(u,v,ub,vb,nsmth)
      open(11,file=trim(outfile),status='replace')
      do k=1,nz
        do j=1,ny
          do i=1,nx
            write(11,'(3(I4,1X),2(ES22.13E3,1X))')
     1          i,j,k,u(i,j,k),v(i,j,k)
          enddo
        enddo
      enddo
      close(11)
      end
c --- Only reached if unsupported LLBREZE is enabled; selected=false.
      subroutine box(ibx,x,y,ok)
      real x,y,ok
      ok=0.
      return
      end
"""

def run(cmd):
    p=subprocess.run([str(x) for x in cmd],capture_output=True,
                     text=True,timeout=120)
    if p.returncode:
        raise RuntimeError(f"failed {cmd}, rc={p.returncode}, stdout={p.stdout[-800:]}, stderr={p.stderr[-1600:]}")

def extract(vendor,out):
    source=(vendor/"calmet.for").read_bytes()
    git_sha=hashlib.sha1(f"blob {len(source)}\0".encode()+source).hexdigest()
    if git_sha!=ORIGINAL_BLOB:
        raise RuntimeError(f"vendor source version mismatch {git_sha}")
    lines=source.decode().splitlines(keepends=True)
    def anchor(name):
        hits=[i for i,line in enumerate(lines)
              if line.lower().startswith(f"      subroutine {name}(")]
        if len(hits)!=1:raise ValueError(f"missing/ambiguous source anchor {name}")
        return hits[0]
    a,b=anchor("smooth"),anchor("cloud3")
    if a+1!=30606 or b<=a:raise ValueError("original CALMET SMOOTH source drift")
    f=out/"literal_smooth_original.for"
    f.write_text("".join(lines[a:b]))
    return f,{"git_blob":git_sha,"first_line":a+1,"last_line":b,
              "extracted_sha256":hashlib.sha256(f.read_bytes()).hexdigest(),
              "lake_breeze":"excluded_false"}

def cases():
    for name,passes in (
        ("zero_passes",[0]*NZ),
        ("one_pass_each",[1]*NZ),
        ("variable_passes",[0,1,2,3,0,1,2,1,0]),
        ("asymmetric_edges",[2]*NZ)):
        u=[];v=[];ub=[];vb=[]
        for k in range(NZ):
            for j in range(NY):
                for i in range(NX):
                    if name=="zero_passes":
                        x=2.5;y=-1.0
                    else:
                        x=1.9+0.12*math.sin(i*.17+j*.21+k*.13)+0.007*i
                        y=-0.7+0.09*math.cos(i*.11-j*.15+k*.2)-0.009*j
                        if name=="asymmetric_edges" and i==25 and j==21:
                            x+=5.0;y-=3.0
                    u.append(x);v.append(y)
        for k in range(NZ):
            for side in range(2):
                for j in range(NY):
                    val=(0.2 if side==0 else 5.1) + 0.03*math.sin(j*.12+k*.08)
                    ub.append(val)
        for k in range(NZ):
            for side in range(2):
                for i in range(NX):
                    val=(3.2 if side==0 else -2.5) + 0.02*math.cos(i*.13+k*.17)
                    vb.append(val)
        yield name,passes,[u,v,ub,vb]

def write_input(path,passes,fields):
    u,v,ub,vb=fields
    if [len(x) for x in fields]!=[22500,22500,900,900]:raise ValueError("wrong SMOOTH fields")
    with path.open("w") as f:
        f.write(" ".join(map(str,passes))+"\n")
        for array,width in ((u,NX),(v,NX),(ub,NY),(vb,NX)):
            for off in range(0,len(array),width):
                f.write(" ".join(f"{x:.9f}" for x in array[off:off+width])+"\n")

def compare(original,modern,input_u,input_v):
    raw=[line.split() for line in original.read_text().splitlines()]
    with modern.open(newline="") as f:cpp=list(csv.DictReader(f))
    if len(raw)!=N*NZ or len(cpp)!=N*NZ:
        raise RuntimeError("SMOOTH output count incorrect")
    maxima={"u":0.,"v":0.};different=0
    mismatches=[]
    for row,(o,c) in enumerate(zip(raw,cpp)):
        index=(row%NX+1,(row//NX)%NY+1,row//N+1)
        if len(o)!=5 or tuple(map(int,o[:3]))!=index or (
            int(c["i"]),int(c["j"]),int(c["k"]))!=index:
            raise RuntimeError("original/C++ SMOOTH row ordering mismatch")
        for name,col,field in (("u",3,"u_mps"),("v",4,"v_mps")):
            x,y=float(o[col]),float(c[field])
            if not(math.isfinite(x) and math.isfinite(y)):
                raise RuntimeError("nonfinite original/C++ SMOOTH output")
            error=abs(x-y)
            maxima[name]=max(maxima[name],error)
            if error>ABS_TOL_MPS and len(mismatches)<20:
                mismatches.append({"cell":index,"field":name,"fortran":x,
                                   "cpp":y,"abs_error":error})
        different+=abs(float(o[3])-input_u[row])>1e-5 or abs(float(o[4])-input_v[row])>1e-5
    return {"status":"PASS" if not mismatches else "FAIL",
            "comparisons":N*NZ*2,"original_changed_cells":different,
            "max_abs_errors_mps":maxima,"first_mismatches":mismatches}

def main():
    p=argparse.ArgumentParser()
    for key in ("vendor","cpp","out"):
        p.add_argument("--"+key,required=True,type=Path)
    arg=p.parse_args()
    arg.out.mkdir(parents=True,exist_ok=True)
    original,source=extract(arg.vendor,arg.out)
    driver=arg.out/"smooth_fortran_driver.for"
    driver.write_text(DRIVER)
    binary=arg.out/"original_smooth"
    run(["gfortran","-O0","-std=legacy","-fno-automatic",
         "-ffixed-line-length-none","-I"+str(arg.vendor),
         original,driver,"-o",binary])
    results={}
    for name,passes,fields in cases():
        inp=arg.out/(name+".input")
        fo=arg.out/(name+".fortran")
        co=arg.out/(name+".cpp.csv")
        write_input(inp,passes,fields)
        run([binary,inp,fo]);run([arg.cpp,inp,co])
        results[name]=compare(fo,co,fields[0],fields[1])
    ok=all(x["status"]=="PASS" for x in results.values()) and all(
        results[x]["original_changed_cells"]>0 for x in
        ("one_pass_each","variable_passes","asymmetric_edges")) and (
        results["zero_passes"]["original_changed_cells"]==0)
    report={"status":"PASS_ORIGINAL_SMOOTH_SELECTED_NO_LAKE_BREEZE" if ok else "FAIL",
            "source":source,"predeclared_abs_tolerance_mps":ABS_TOL_MPS,
            "total_compared_components":sum(x["comparisons"] for x in results.values()),
            "scope":"original SMOOTH only, not DIAGNO/143-hour actual U/V/W",
            "cases":results}
    (arg.out/"p6d-smooth-parity.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if not ok:raise SystemExit(1)

if __name__=="__main__": main()

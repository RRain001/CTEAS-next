#!/usr/bin/env python3
"""Original CALMET 6.5.0 DIVCEL exact-subroutine vs C++ numerical audit.
Explicit bound conditions, layer-face W and per-layer DIVMAX; no MINIM claim.
"""
import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

SOURCE_BLOB = "437f43bb7f0e51a1919e56664663e1a046986ed0"
ABS_TOL_S_INV = 1e-6
NX, NY, NZ = 50, 50, 9
N = NX*NY
DZ = [20.,20.,40.,80.,160.,320.,560.,800.,1000.]

DRIVER = """      program divdriver
      include 'params.met'
      include 'grid.met'
      real u(mxnx,mxny,mxnz),v(mxnx,mxny,mxnz)
      real w(mxnx,mxny,mxnzp1),div(mxnx,mxny,mxnz)
      real ub(mxny,2,mxnz),vb(mxnx,2,mxnz),divmax
      character*256 infile,outfile,maxfile
      call get_command_argument(1,infile)
      call get_command_argument(2,outfile)
      call get_command_argument(3,maxfile)
      nx=50
      ny=50
      nz=9
      dx=100.
      dy=100.
      open(10,file=trim(infile),status='old')
      read(10,*) (dz(k),k=1,nz)
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
      do k=1,nz+1
        do j=1,ny
          read(10,*) (w(i,j,k),i=1,nx)
        enddo
      enddo
      do k=1,nz
        do b=1,2
          read(10,*) (ub(j,b,k),j=1,ny)
        enddo
      enddo
      do k=1,nz
        do b=1,2
          read(10,*) (vb(i,b,k),i=1,nx)
        enddo
      enddo
      close(10)
      open(12,file=trim(maxfile),status='replace')
      do k=1,nz
        divmax=-1.e9
        call divcel(u,v,w,div,ub,vb,divmax,k)
        write(12,'(I4,1X,ES22.13E3)') k,divmax
      enddo
      close(12)
      open(11,file=trim(outfile),status='replace')
      do k=1,nz
        do j=1,ny
          do i=1,nx
            write(11,'(3(I4,1X),ES22.13E3)') i,j,k,div(i,j,k)
          enddo
        enddo
      enddo
      close(11)
      end
"""

def run(args):
    p=subprocess.run([str(x) for x in args],text=True,capture_output=True,timeout=90)
    if p.returncode:
        raise RuntimeError(f"failed {args}, rc={p.returncode}, stdout={p.stdout[-800:]}, stderr={p.stderr[-1600:]}")

def extract(vendor,out):
    src=(vendor/"calmet.for").read_bytes()
    git_sha=hashlib.sha1(f"blob {len(src)}\0".encode()+src).hexdigest()
    if git_sha != SOURCE_BLOB:raise RuntimeError("Original CALMET source blob drift "+git_sha)
    lines=src.decode().splitlines(keepends=True)
    def index(name):
        hits=[i for i,x in enumerate(lines) if x.lower().startswith(f"      subroutine {name}(")]
        if len(hits)!=1:raise ValueError(f"ambiguous Fortran subroutine {name}: {hits}")
        return hits[0]
    a,b=index("divcel"),index("divpr")
    if a+1!=6246 or b<=a:raise ValueError("Unexpected DIVCEL source positioning")
    f=out/"literal_divcel.for"
    f.write_text("".join(lines[a:b]))
    return f, {"source_blob":git_sha, "first_line":a+1,"last_line":b,
               "subroutine_sha256":hashlib.sha256(f.read_bytes()).hexdigest()}

def cases():
    for name in ("zero","analytic_horizontal","vertical_shear","boundary_only"):
        u=[];v=[];w=[];ub=[];vb=[]
        for k in range(NZ):
            for j in range(NY):
                for i in range(NX):
                    if name=="zero" or name=="boundary_only":x,y=0.,0.
                    elif name=="analytic_horizontal":x,y=0.07*i,-0.03*j
                    else:
                        x=2.5+0.9*math.sin(i*.22+j*.08+k*.3)
                        y=1.7+0.6*math.cos(j*.19-i*.11+k*.21)
                    u.append(x);v.append(y)
        for k in range(NZ+1):
            for j in range(NY):
                for i in range(NX):
                    w.append((0.2*k if name=="vertical_shear" else
                             0.1*k if name=="analytic_horizontal" else 0.)+
                             (0.03*math.sin(i*.15+j*.06+k*.1)
                              if name=="vertical_shear" else 0.))
        for k in range(NZ):
            for side in range(2):
                for j in range(NY):
                    if name=="boundary_only":
                        val=(-5.0 if side==0 else 8.0)+0.01*j
                    elif name=="analytic_horizontal":
                        val=-0.07 if side==0 else 0.07*NX
                    elif name=="vertical_shear":
                        val=2.0+0.3*math.sin(k+j*.16+side)
                    else:val=0.
                    ub.append(val)
        for k in range(NZ):
            for side in range(2):
                for i in range(NX):
                    if name=="boundary_only":
                        val=(-4.0 if side==0 else 6.0)-0.015*i
                    elif name=="analytic_horizontal":
                        val=0.03 if side==0 else -0.03*NY
                    elif name=="vertical_shear":
                        val=1.5+0.4*math.cos(k+i*.12+side)
                    else:val=0.
                    vb.append(val)
        yield name,[DZ,u,v,w,ub,vb]

def write_case(path,fields):
    dz,u,v,w,ub,vb=fields
    if [len(x) for x in fields]!=[NZ,N*NZ,N*NZ,N*(NZ+1),NY*2*NZ,NX*2*NZ]:
        raise ValueError("wrong 3d field sizes")
    with path.open("w") as f:
        f.write(" ".join(f"{x:.9f}" for x in dz)+"\n")
        for arr,width in ((u,NX),(v,NX),(w,NX),(ub,NY),(vb,NX)):
            for i in range(0,len(arr),width):
                f.write(" ".join(f"{x:.9f}" for x in arr[i:i+width])+"\n")

def compare(fo,co,fm,cm):
    original=[x.split() for x in fo.read_text().splitlines()]
    with co.open(newline="") as f:candidate=list(csv.DictReader(f))
    if len(original)!=N*NZ or len(candidate)!=N*NZ:raise ValueError("3d divergence row mismatch")
    peak=0.;bad=[];active=0
    for n,(a,b) in enumerate(zip(original,candidate)):
        i,j,k=n%NX+1,(n//NX)%NY+1,n//N+1
        if len(a)!=4 or tuple(map(int,a[:3]))!=(i,j,k) or (
          int(b["i"]),int(b["j"]),int(b["k"]))!=(i,j,k):
            raise ValueError("divergence row order mismatch")
        x,y=float(a[3]),float(b["div_per_s"])
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError("invalid divergence values")
        if abs(x)>1e-7:active+=1
        e=abs(x-y);peak=max(peak,e)
        if e>ABS_TOL_S_INV and len(bad)<12:bad.append({"i":i,"j":j,"k":k,"error":e})
    amax=[list(map(float,x.split())) for x in fm.read_text().splitlines()]
    bmax=[list(map(float,x.split())) for x in cm.read_text().splitlines()]
    if len(amax)!=NZ or len(bmax)!=NZ:raise ValueError("wrong DIVMAX layer count")
    for k,(a,b) in enumerate(zip(amax,bmax),1):
        if len(a)!=2 or len(b)!=2 or int(a[0])!=k or int(b[0])!=k:
            raise ValueError("DIVMAX layer mismatch")
        x,y=a[1],b[1]
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("nonfinite DIVMAX")
        e=abs(x-y);peak=max(peak,e)
        if e>ABS_TOL_S_INV and len(bad)<12:bad.append({"k":k,"field":"DIVMAX","error":e})
    return {"status":"FAIL" if bad else "PASS","divergence_cells":N*NZ,
            "layer_maxima":NZ,"active_original_cells":active,
            "max_abs_error_s_inv":peak,"first_mismatches":bad}

def main():
    p=argparse.ArgumentParser()
    for key in ("vendor","cpp","out"):p.add_argument("--"+key,type=Path,required=True)
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    sub,source=extract(args.vendor,args.out)
    driver=args.out/"divcel_driver.for";driver.write_text(DRIVER)
    binary=args.out/"original_divcel"
    run(["gfortran","-O0","-std=legacy","-fno-automatic",
         "-ffixed-line-length-none","-I"+str(args.vendor),
         sub,driver,"-o",binary])
    result={}
    for name,fields in cases():
        data=args.out/(name+".input")
        fo=args.out/(name+".fortran")
        co=args.out/(name+".cpp.csv")
        fm=args.out/(name+".original.max")
        cm=args.out/(name+".cpp.max")
        write_case(data,fields)
        run([binary,data,fo,fm]);run([args.cpp,data,co,cm])
        result[name]=compare(fo,co,fm,cm)
    okay=all(v["status"]=="PASS" for v in result.values()) and all(
        result[x]["active_original_cells"]>0
        for x in ("analytic_horizontal","vertical_shear","boundary_only"))
    report={"status":"PASS_ORIGINAL_DIVCEL_ISOLATED" if okay else "FAIL",
            "source":source,"abs_tolerance_s_inv":ABS_TOL_S_INV,
            "scope":"DIVCEL divergence diagnostic only, not MINIM, real 2022 hourly or full P6D",
            "cases":result}
    (args.out/"p6d-divcel-parity.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if not okay:raise SystemExit(1)
if __name__=="__main__":main()

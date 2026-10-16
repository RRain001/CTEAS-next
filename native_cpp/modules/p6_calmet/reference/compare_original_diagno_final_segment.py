#!/usr/bin/env python3
"""Numerical parity: unmodified original DIAGNO source L6119–6148 and
unchanged original SMOOTH, DIVCEL, WINDBC versus C++ selected execution.
Selected path IOBR=0 and no lake breeze, synthetic 50x50x9 inputs.
"""
import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

SOURCE_BLOB = "437f43bb7f0e51a1919e56664663e1a046986ed0"
TOL_WIND_MPS = 2e-4
TOL_DIV_PER_S = 1e-6
NX=NY=50
NZ=9
N=NX*NY
DZ=(20.,20.,40.,80.,160.,320.,560.,800.,1000.)

DRIVER_HEAD = """      program diagsegment
      include 'params.met'
      include 'grid.met'
      include 'breez.met'
      real u(mxnx,mxny,mxnz),v(mxnx,mxny,mxnz)
      real w(mxnx,mxny,mxnzp1),div(mxnx,mxny,mxnz)
      real ub(mxny,2,mxnz),vb(mxnx,2,mxnz)
      real zero,divmax
      integer nsmth(mxnz),side
      character*256 infile,outfile,boundfile
      call get_command_argument(1,infile)
      call get_command_argument(2,outfile)
      call get_command_argument(3,boundfile)
      nx=50
      ny=50
      nz=9
      dx=100.
      dy=100.
      zero=0.
      llbreze=.false.
      nbox=0
      open(10,file=trim(infile),status='old')
      read(10,*) (dz(k),k=1,nz)
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
c --- LITERAL ORIGINAL DIAGNO SOURCE L6119–L6148 BEGINS BELOW:
"""
DRIVER_TAIL = """c --- LITERAL ORIGINAL DIAGNO SOURCE L6119–L6148 ENDS ABOVE.
      open(11,file=trim(outfile),status='replace')
      do k=1,nz
        do j=1,ny
          do i=1,nx
            write(11,'(3(I4,1X),5(ES22.13E3,1X))')
     1          i,j,k,u(i,j,k),v(i,j,k),div(i,j,k),
     2          w(i,j,k),w(i,j,k+1)
          enddo
        enddo
      enddo
      close(11)
      open(12,file=trim(boundfile),status='replace')
      do k=1,nz
        do side=1,2
          do j=1,ny
            write(12,'(A1,3(I4,1X),ES22.13E3)')
     1           'U',k,side,j,ub(j,side,k)
          enddo
          do i=1,nx
            write(12,'(A1,3(I4,1X),ES22.13E3)')
     1           'V',k,side,i,vb(i,side,k)
          enddo
        enddo
      enddo
      close(12)
      end
c --- Test harness supports only .FALSE. lake breeze, no vendor change.
      subroutine box(ibx,x,y,ok)
      real x,y,ok
      ok=0.
      end
c --- External XMIT initializes full COMMON-size W array as original.
      subroutine xmit(n,val,a)
      integer n
      real val,a(*)
      do i=1,iabs(n)
        a(i)=val
      enddo
      end
"""

def run(command):
    p=subprocess.run([str(x) for x in command],capture_output=True,text=True,
                     timeout=160)
    if p.returncode:raise RuntimeError(
        f"failed {command} rc={p.returncode} stdout={p.stdout[-1000:]} stderr={p.stderr[-2200:]}")

def original_source(vendor,out):
    raw=(vendor/"calmet.for").read_bytes()
    sha=hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()
    if sha!=SOURCE_BLOB:raise RuntimeError("original CALMET source drift "+sha)
    lines=raw.decode().splitlines(keepends=True)
    def start(name):
        found=[i for i,s in enumerate(lines)
               if s.lower().startswith(f"      subroutine {name}(")]
        if len(found)!=1:raise RuntimeError("source anchor ambiguous "+name)
        return found[0]
    part=[]
    for name,after,expected in (
        ("smooth","cloud3",30606),
        ("divcel","divpr",6246),
        ("windbc","windpr",36404)):
        a,b=start(name),start(after)
        if a+1!=expected or b<=a:raise RuntimeError("subroutine source drift "+name)
        path=out/(name+"_original.for")
        path.write_text("".join(lines[a:b]))
        part.append((path,{"name":name,"first_line":a+1,"last_line":b,
                          "sha256":hashlib.sha256(path.read_bytes()).hexdigest()}))
    if "      CALL SMOOTH(U,V,UB,VB,NSMTH)" not in lines[6118]:
        raise RuntimeError("DIAGNO selected SMOOTH hook mismatch")
    block="".join(lines[6119-1:6148])
    if ("      CALL WINDBC(U,V,UB,VB,K)" not in block or
        "      CALL DIVCEL(U,V,W,DIV,UB,VB,DIVMAX,K)" not in block):
        raise RuntimeError("DIAGNO selected W segment unexpected calls")
    return part,block,{
        "git_blob":sha,"literal_diagno_lines":[6119,6148],
        "diagno_segment_sha256":hashlib.sha256(block.encode()).hexdigest()}

def cases():
    for name,passes in (
        ("calm_zero",[0]*NZ),
        ("flat_nonzero_divergence",[0]*NZ),
        ("layer_selective_smooth",[0,1,2,1,0,1,2,3,0]),
        ("rough_winds_and_boundaries",[2]*NZ)):
        u=[];v=[];ub=[];vb=[]
        for k in range(NZ):
            for j in range(NY):
                for i in range(NX):
                    if name=="calm_zero":
                        x=0.;y=0.
                    elif name=="flat_nonzero_divergence":
                        x=0.04*i;y=-0.02*j
                    else:
                        x=2.5+0.2*math.sin(i*.19+j*.13+k*.21)+0.005*i
                        y=1.2-0.3*math.cos(i*.17-j*.11-k*.14)-0.008*j
                    u.append(x);v.append(y)
        for k in range(NZ):
            for side in range(2):
                for j in range(NY):
                    if name=="calm_zero":x=0.
                    elif name=="rough_winds_and_boundaries":x=(-1. if side==0 else 9.)+0.01*j
                    else:x=(-0.1 if side==0 else 1.)+0.02*j
                    ub.append(x)
        for k in range(NZ):
            for side in range(2):
                for i in range(NX):
                    if name=="calm_zero":x=0.
                    elif name=="rough_winds_and_boundaries":x=(3. if side==0 else -7.)-0.02*i
                    else:x=(0.3 if side==0 else -0.5)+0.01*i
                    vb.append(x)
        yield name,passes,[u,v,ub,vb]

def write_case(path,passes,fields):
    u,v,ub,vb=fields
    if [len(x) for x in fields]!=[22500,22500,900,900]:
        raise ValueError("wrong DIAGNO selected source dimensions")
    with path.open("w") as f:
        f.write(" ".join(f"{x:.9f}" for x in DZ)+"\n")
        f.write(" ".join(map(str,passes))+"\n")
        for array,width in ((u,NX),(v,NX),(ub,NY),(vb,NX)):
            for off in range(0,len(array),width):
                f.write(" ".join(f"{x:.9f}" for x in array[off:off+width])+"\n")

def compare(fwind,cwind,fb,cb):
    a=[line.split() for line in fwind.read_text().splitlines()]
    with cwind.open(newline="") as f:b=list(csv.DictReader(f))
    if len(a)!=22500 or len(b)!=22500:raise ValueError("output row count")
    bad=[];max_errors={"u":0.,"v":0.,"div":0.,"w_below":0.,"w_above":0.}
    nonzero_w=0
    for n,(r,c) in enumerate(zip(a,b)):
        idx=(n%NX+1,(n//NX)%NY+1,n//N+1)
        if len(r)!=8 or tuple(map(int,r[:3]))!=idx or(
           int(c["i"]),int(c["j"]),int(c["k"]))!=idx:
            raise ValueError("Fortran/C++ DIAGNO segment index mismatch")
        for field,pos in (("u",3),("v",4),("div",5),("w_below",6),("w_above",7)):
            orig,cand=float(r[pos]),float(c[field])
            if not (math.isfinite(orig) and math.isfinite(cand)):
                raise ValueError(f"nonfinite DIAGNO source field {field} at {idx}: original={orig!r}, cpp={cand!r}")
            tol=TOL_DIV_PER_S if field=="div" else TOL_WIND_MPS
            err=abs(orig-cand)
            max_errors[field]=max(max_errors[field],err)
            if err>tol and len(bad)<20:
                bad.append({"field":field,"i_j_k":idx,"error":err})
        nonzero_w+=abs(float(r[7]))>1e-6
    a_b=[line.split() for line in fb.read_text().splitlines()]
    b_b=[line.split() for line in cb.read_text().splitlines()]
    if len(a_b)!=1800 or len(b_b)!=1800:raise ValueError("boundary count mismatch")
    bc_err=0.
    for n,(a,c) in enumerate(zip(a_b,b_b)):
        if len(a)!=5 or len(c)!=5 or a[:4]!=c[:4]:
            raise ValueError(f"boundary identity/order mismatch row {n}")
        orig,cand=float(a[4]),float(c[4])
        if not(math.isfinite(orig) and math.isfinite(cand)):
            raise ValueError("nonfinite boundary")
        err=abs(orig-cand)
        bc_err=max(bc_err,err)
        if err>TOL_WIND_MPS and len(bad)<20:bad.append({"boundary_row":n,"error":err})
    return {"status":"PASS" if not bad else "FAIL",
            "uv_div_w_comparisons":N*NZ*5,
            "boundary_comparisons":len(a_b),"nonzero_original_w_cells":nonzero_w,
            "max_field_abs_error":max_errors,"max_boundary_error_mps":bc_err,
            "first_mismatches":bad}

def main():
    p=argparse.ArgumentParser()
    for key in ("vendor","cpp","out"):
        p.add_argument("--"+key,required=True,type=Path)
    arg=p.parse_args();arg.out.mkdir(parents=True,exist_ok=True)
    routines,block,source=original_source(arg.vendor,arg.out)
    driver=arg.out/"original_diagno_segment.for"
    driver.write_text(DRIVER_HEAD+block+DRIVER_TAIL)
    binary=arg.out/"original_diagno_segment"
    run(["gfortran","-O0","-std=legacy","-fno-automatic",
         "-ffixed-line-length-none","-I"+str(arg.vendor),
         *[path for path,_ in routines],driver,"-o",binary])
    results={}
    for name,passes,fields in cases():
        f=arg.out/(name+".input")
        fortran=arg.out/(name+".fortran")
        modern=arg.out/(name+".cpp.csv")
        fb=arg.out/(name+".fortran.bound")
        cb=arg.out/(name+".cpp.bound")
        write_case(f,passes,fields)
        run([binary,f,fortran,fb]);run([arg.cpp,f,modern,cb])
        results[name]=compare(fortran,modern,fb,cb)
    success=all(r["status"]=="PASS" for r in results.values()) and all(
        results[k]["nonzero_original_w_cells"]>0 for k in
        ("flat_nonzero_divergence","layer_selective_smooth","rough_winds_and_boundaries")) and (
        results["calm_zero"]["nonzero_original_w_cells"]==0)
    report={"status":"PASS_DIAGNO_SELECTED_SMOOTH_DIVCEL_W_SEGMENT" if success else "FAIL",
            "scope":"original-source DIAGNO L6119-6148 selected non-IOBR, no lake breeze; not full diagnostic P6D",
            "original":source,
            "source_routines":[ref for _,ref in routines],
            "wind_abs_tol_mps":TOL_WIND_MPS,
            "div_abs_tol_s_inv":TOL_DIV_PER_S,
            "total_uv_div_w_compared":sum(r["uv_div_w_comparisons"] for r in results.values()),
            "total_boundaries_compared":sum(r["boundary_comparisons"] for r in results.values()),
            "cases":results}
    (arg.out/"p6d-final-segment-parity.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if not success:raise SystemExit(1)
if __name__=="__main__":main()

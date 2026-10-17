#!/usr/bin/env python3
"""Independent CALMET 6.5.0 literal MINIM+DIVCEL+WINDBC source parity.
Does not assess complete diagnostic wind, nor represent actual 2022 forcing.
"""
import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

SOURCE_SHA="437f43bb7f0e51a1919e56664663e1a046986ed0"
TOL_WIND=2e-4
TOL_DIV=1e-6
NX=NY=50
NZ=9
N=NX*NY
DZ=(20.,20.,40.,80.,160.,320.,560.,800.,1000.)

DRIVER="""      program minreference
      include 'params.met'
      include 'grid.met'
      include 'd6.met'
      real u(mxnx,mxny,mxnz),v(mxnx,mxny,mxnz)
      real w(mxnx,mxny,mxnzp1),div(mxnx,mxny,mxnz)
      real ub(mxny,2,mxnz),vb(mxnx,2,mxnz)
      real divlim
      integer s
      character*256 infile,outfile,boundfile
      call get_command_argument(1,infile)
      call get_command_argument(2,outfile)
      call get_command_argument(3,boundfile)
      nx=50
      ny=50
      nz=9
      dx=100.
      dy=100.
      iwr=0
      open(10,file=trim(infile),status='old')
      read(10,*) niter,divlim
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
        do s=1,2
          read(10,*) (ub(j,s,k),j=1,ny)
        enddo
      enddo
      do k=1,nz
        do s=1,2
          read(10,*) (vb(i,s,k),i=1,nx)
        enddo
      enddo
      close(10)
      call minim(u,v,w,ub,vb,div,niter,divlim)
      open(11,file=trim(outfile),status='replace')
      do k=1,nz
        do j=1,ny
          do i=1,nx
            write(11,'(3(I4,1X),3(ES22.13E3,1X))')
     1           i,j,k,u(i,j,k),v(i,j,k),div(i,j,k)
          enddo
        enddo
      enddo
      close(11)
      open(12,file=trim(boundfile),status='replace')
      do k=1,nz
        do s=1,2
          do j=1,ny
            write(12,'(A1,3(I4,1X),ES22.13E3)')
     1            'U',k,s,j,ub(j,s,k)
          enddo
          do i=1,nx
            write(12,'(A1,3(I4,1X),ES22.13E3)')
     1            'V',k,s,i,vb(i,s,k)
          enddo
        enddo
      enddo
      close(12)
      end
"""

def run(cmd):
    r=subprocess.run([str(x) for x in cmd],capture_output=True,text=True,timeout=150)
    if r.returncode:
        raise RuntimeError(f"{cmd} rc={r.returncode} out={r.stdout[-1500:]} err={r.stderr[-1600:]}")

def extract(vendor,out):
    src=(vendor/"calmet.for").read_bytes()
    digest=hashlib.sha1(f"blob {len(src)}\0".encode()+src).hexdigest()
    if digest!=SOURCE_SHA:raise ValueError("original vendor CALMET blob drift "+digest)
    lines=src.decode().splitlines(keepends=True)
    def start(name):
        matches=[i for i,x in enumerate(lines)
                 if x.lower().startswith(f"      subroutine {name}(")]
        if len(matches)!=1:raise ValueError("ambiguous "+name)
        return matches[0]
    source=[]
    for name,next_name,expected in (("divcel","divpr",6246),
                                    ("minim","missfc",9645),
                                    ("windbc","windpr",36404)):
        a,b=start(name),start(next_name)
        if a+1!=expected or b<=a:raise ValueError("original source location drift")
        path=out/(name+"_original.for")
        path.write_text("".join(lines[a:b]))
        source.append((path,{"name":name,"first_line":a+1,"last_line":b,
                            "sha256":hashlib.sha256(path.read_bytes()).hexdigest()}))
    return source

def cases():
    for name in ("calm_skip","horizontal_shear","vertical_divergence","edge_forcing"):
        u=[];v=[];w=[];ub=[];vb=[]
        for k in range(NZ):
            for j in range(NY):
                for i in range(NX):
                    if name=="calm_skip" or name=="vertical_divergence":
                        x,y=0.,0.
                    elif name=="horizontal_shear":
                        x=1.2+0.018*i+0.03*math.sin(j*.18+k*.29)
                        y=-0.5+0.016*j-0.02*math.cos(i*.14)
                    else:
                        x=0.7+0.008*i
                        y=0.4-0.009*j
                    u.append(x);v.append(y)
        for k in range(NZ+1):
            for j in range(NY):
                for i in range(NX):
                    if name=="vertical_divergence":
                        x=0.07*k
                    elif name=="horizontal_shear":
                        x=0.011*k + 0.001*math.sin(i*.1+j*.05+k)
                    elif name=="edge_forcing":
                        x=0.006*k
                    else:
                        x=0.
                    w.append(x)
        for k in range(NZ):
            for side in range(2):
                for j in range(NY):
                    ub.append(((-0.9 if side==0 else 1.1) if
                               name=="edge_forcing" else 0.2*side) +
                              (0.0 if name in ("calm_skip","vertical_divergence")
                               else 0.002*j))
        for k in range(NZ):
            for side in range(2):
                for i in range(NX):
                    vb.append(((-1.2 if side==0 else 0.9) if
                               name=="edge_forcing" else -0.15*side) +
                              (0.0 if name in ("calm_skip","vertical_divergence")
                               else 0.001*i))
        # avoid fabricated negative signed divergence acceptance condition
        if name=="calm_skip":
            ub=[0.]*len(ub);vb=[0.]*len(vb)
        yield name, [u,v,w,ub,vb], (0 if name=="calm_skip" else 2), 1e-7

def write_case(path,arrays,niter,divlim):
    u,v,w,ub,vb=arrays
    if list(map(len,arrays))!=[N*NZ,N*NZ,N*(NZ+1),NY*2*NZ,NX*2*NZ]:
        raise ValueError("MINIM input sizes")
    with path.open("w") as f:
        f.write(f"{niter} {divlim:.9f}\n")
        f.write(" ".join(f"{x:.9f}" for x in DZ)+"\n")
        for arr,width in ((u,NX),(v,NX),(w,NX),(ub,NY),(vb,NX)):
            for n in range(0,len(arr),width):
                f.write(" ".join(f"{x:.9f}" for x in arr[n:n+width])+"\n")

def compare(a,b,fa,fb,u0,v0):
    orig=[x.split() for x in a.read_text().splitlines()]
    with b.open(newline="") as f:cpp=list(csv.DictReader(f))
    if len(orig)!=N*NZ or len(cpp)!=N*NZ:raise ValueError("MINIM output rows")
    bad=[];errors={"u":0.,"v":0.,"div":0.};changed=0
    for n,(o,c) in enumerate(zip(orig,cpp)):
        index=(n%NX+1,(n//NX)%NY+1,n//N+1)
        if len(o)!=6 or tuple(map(int,o[:3]))!=index or(
            int(c["i"]),int(c["j"]),int(c["k"]))!=index:
            raise ValueError("MINIM Fortran/C++ row order")
        for name,col,expected,tol in (("u",3,"u_mps",TOL_WIND),
                                      ("v",4,"v_mps",TOL_WIND),
                                      ("div",5,"div_per_s",TOL_DIV)):
            x,y=float(o[col]),float(c[expected])
            if not(math.isfinite(x) and math.isfinite(y)):
                raise ValueError("nonfinite MINIM output")
            e=abs(x-y);errors[name]=max(errors[name],e)
            if e>tol and len(bad)<10:
                bad.append({"cell":index,"field":name,"err":e})
        changed+=(abs(float(o[3])-u0[n])>1e-5 or abs(float(o[4])-v0[n])>1e-5)
    af=[line.split() for line in fa.read_text().splitlines()]
    bf=[line.split() for line in fb.read_text().splitlines()]
    if len(af)!=1800 or len(bf)!=1800:raise ValueError("MINIM boundary count")
    max_boundary=0.
    for n,(o,c) in enumerate(zip(af,bf)):
        if len(o)!=5 or len(c)!=5 or o[:4]!=c[:4]:
            raise ValueError(f"MINIM boundary order mismatch {n}")
        x,y=float(o[4]),float(c[4])
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("nonfinite boundary wind")
        e=abs(x-y);max_boundary=max(max_boundary,e)
        if e>TOL_WIND and len(bad)<10:
            bad.append({"boundary":o[:4],"err":e})
    return {"status":"PASS" if not bad else "FAIL",
            "uvdiv_components":3*N*NZ,"boundary_components":len(af),
            "original_changed_cells":changed,"max_abs_errors":errors,
            "max_boundary_error_mps":max_boundary,"first_mismatches":bad}

def main():
    p=argparse.ArgumentParser()
    for key in ("vendor","cpp","out"):p.add_argument("--"+key,type=Path,required=True)
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    originals=extract(args.vendor,args.out)
    driver=args.out/"minim_driver.for";driver.write_text(DRIVER)
    binary=args.out/"original_minim"
    run(["gfortran","-O0","-std=legacy","-fno-automatic",
         "-ffixed-line-length-none","-I"+str(args.vendor),
         *[x[0] for x in originals],driver,"-o",binary])
    results={}
    for name,fields,niter,divlim in cases():
        inp=args.out/(name+".input")
        fo=args.out/(name+".fortran")
        co=args.out/(name+".cpp.csv")
        fb=args.out/(name+".fortran.bound")
        cb=args.out/(name+".cpp.bound")
        write_case(inp,fields,niter,divlim)
        run([binary,inp,fo,fb]);run([args.cpp,inp,co,cb])
        results[name]=compare(fo,co,fb,cb,fields[0],fields[1])
    ok=all(x["status"]=="PASS" for x in results.values()) and any(
      results[n]["original_changed_cells"]>0 for n in
      ("horizontal_shear","vertical_divergence","edge_forcing"))
    report={"status":"PASS_ORIGINAL_MINIM_ISOLATED" if ok else "FAIL",
            "source_blob":SOURCE_SHA,"original_subroutines":[x[1] for x in originals],
            "tol_wind_mps":TOL_WIND,"tol_div_s_inv":TOL_DIV,
            "scope":"MINIM+DIVCEL+WINDBC isolated, not 2022 full DIAGNO",
            "cases":results}
    (args.out/"p6d-minim-parity.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if not ok:raise SystemExit(1)

if __name__=="__main__":main()

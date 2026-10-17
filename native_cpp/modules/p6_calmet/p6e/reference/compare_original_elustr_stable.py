#!/usr/bin/env python3
"""Unmodified CALMET ELUSTR stable path (no daytime PSIU calls) vs C++.
30 cases × 20 cells × (qh,ustar,Monin Obukhov length) = 1800 numbers.
"""
import argparse,json,math,hashlib,subprocess,tempfile
from pathlib import Path
BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
NX,NY,NS,CASES=5,4,4,30
ABS_QH=0.001
ABS_USTAR=0.00003
ABS_L=0.04
REL=0.00005
PARAMS="""      integer mxnx,mxny,mxss
      parameter(mxnx=5,mxny=4,mxss=4)
"""
DRIVER="""      program stable_elustr_driver
      include 'params.met'
      real z0(mxnx,mxny),u(mxnx,mxny),v(mxnx,mxny)
      real rho(mxnx,mxny),temp(mxnx,mxny),cloud(mxnx,mxny)
      real qh(mxnx,mxny),ustar(mxnx,mxny),el(mxnx,mxny)
      integer land(mxnx,mxny),near(mxnx,mxny),icc(mxss)
      integer cases,nx,ny,ns,c,i,j,s,mode,wl,wh
      real zm
      read(*,*)cases,nx,ny,ns
      if(nx.ne.5.or.ny.ne.4.or.ns.ne.4)stop 13
      do c=1,cases
        read(*,*)mode,wl,wh,zm
        do s=1,ns
          read(*,*)icc(s)
        enddo
        do i=1,nx
          do j=1,ny
            read(*,*)z0(i,j),u(i,j),v(i,j),rho(i,j),temp(i,j),
     1               cloud(i,j),land(i,j),near(i,j),qh(i,j)
            ustar(i,j)=-7777.
            el(i,j)=-7777.
          enddo
        enddo
        call elustr(z0,u,v,zm,near,rho,temp,icc,land,
     1              wl,wh,nx,ny,mode,cloud,0,qh,ustar,el)
        do i=1,nx
          do j=1,ny
            write(*,'(3(I6,1X),3(ES24.14E3,1X))')
     1          c,i,j,qh(i,j),ustar(i,j),el(i,j)
          enddo
        enddo
      enddo
      end
      real*8 function psiud(x)
      real*8 x
      stop 75
      end
      real function psiuc(z,l,n)
      real z,l
      integer n
      stop 76
      end
"""
def run(args,inp=None):
    return subprocess.run([str(x) for x in args],input=inp,text=True,
        capture_output=True,check=True).stdout
def original(src):
    lines=src.decode("utf-8").splitlines(keepends=True)
    a=[i for i,v in enumerate(lines) if v.lower().startswith("      subroutine elustr(")]
    b=[i for i,v in enumerate(lines) if v.lower().startswith("      subroutine elustr2(")]
    if len(a)!=1 or len(b)!=1 or not 220<b[0]-a[0]<280:
        raise RuntimeError("ELUSTR original bounds changed")
    return "".join(lines[a[0]:b[0]]),[a[0]+1,b[0]]
def fixture():
    winds=(0.0,0.002,0.1,0.48,0.52,1.2,3.0,6.0,12.0)
    temps=(270.,278.,285.,294.,301.,310.)
    rough=(0.01,0.025,0.08,0.14,0.4,0.8)
    clouds=(0.,0.1,0.4,0.5,0.8,1.)
    lines=[f"{CASES} {NX} {NY} {NS}"];water=0
    for c in range(CASES):
        lines.append(f"{1+c%4} 50 60 10.0")
        for s in range(NS):lines.append(str((s*3+c)%11))
        for i in range(NX):
            for j in range(NY):
                k=i+2*j+c
                land=55 if (i+j+2*c)%9==0 else 12
                water+=land==55
                lines.append(
                    f"{rough[k%len(rough)]} "
                    f"{winds[k%len(winds)]} "
                    f"{winds[(2*i+j+c)%len(winds)]/2:.7f} "
                    f"{1.05+0.04*((i+j+c)%8):.7f} "
                    f"{temps[(i+3*j+c)%len(temps)]:.7f} "
                    f"{clouds[(3*i+j+c)%len(clouds)]:.7f} "
                    f"{land} {1+(i+j+c)%NS} -0.1"
                )
    return "\n".join(lines)+"\n",water
def parse(output):
    rows=[]
    for line in output.splitlines():
        s=line.split()
        if len(s)!=6:raise ValueError("bad ELUSTR row")
        row=(tuple(map(int,s[:3])),tuple(map(float,s[3:])))
        if not all(map(math.isfinite,row[1])):raise ValueError("ELUSTR nonfinite")
        rows.append(row)
    if len(rows)!=CASES*NX*NY:raise ValueError("ELUSTR wrong count")
    return rows
def main():
    p=argparse.ArgumentParser()
    for opt in ("vendor","cpp","out"):p.add_argument("--"+opt,required=True,type=Path)
    a=p.parse_args()
    raw=a.vendor.read_bytes()
    sha=run(["git","hash-object",a.vendor]).strip()
    if sha!=BLOB:raise ValueError("vendor original source changed")
    src,loc=original(raw)
    input_text,water_count=fixture()
    with tempfile.TemporaryDirectory(prefix="p6e-stable-elustr-") as tmp:
        d=Path(tmp)
        for name,body in (("params.met",PARAMS),("elustr.for",src),("driver.for",DRIVER)):
            (d/name).write_text(body)
        run(["gfortran","-O0","-std=legacy","-fno-automatic",
            "-ffixed-line-length-none","-I"+str(d),
            d/"elustr.for",d/"driver.for","-o",d/"reference"])
        ref=parse(run([d/"reference"],input_text))
    got=parse(run([a.cpp],input_text))
    thresholds=(ABS_QH,ABS_USTAR,ABS_L)
    mismatch=[];count=0;maxerrors=[0.,0.,0.];actualwater=0
    for (key,f),(kk,v) in zip(ref,got):
        if key!=kk:raise ValueError("ELUSTR ordering mismatch")
        if f[1]==-7777.:
            # Fortran emits QH=-0.1 REAL*4 to 14 decimals whereas C++
            # exports 11 decimals. Comparing parsed decimals by == falsely
            # rejects the same underlying binary32 value (~1e-13 output
            # formatting delta). Preserve exact water USTAR/L sentinels and
            # compare QH only within its frozen *serialization* tolerance.
            actualwater+=1
            WATER_QH_PRINT_ABS=5.e-12
            sentinel_ok=(f[1]==v[1] and f[2]==v[2] and
                         abs(f[0]-v[0])<=WATER_QH_PRINT_ABS)
            if not sentinel_ok:
                count+=1
                if len(mismatch)<20:
                    mismatch.append({"cell":key,"original":f,"cpp":v,
                        "water_qh_serialization_tolerance":WATER_QH_PRINT_ABS})
            continue
        if f[0]>=0 or f[1]<0.05 or f[2]<=0:
            raise ValueError("ELUSTR wrong stable physics state")
        for t in range(3):
            error=abs(f[t]-v[t]);maxerrors[t]=max(maxerrors[t],error)
            if error>thresholds[t]+REL*abs(f[t]):
                count+=1
                if len(mismatch)<20:mismatch.append({"cell":key,"field":t,
                                            "original":f[t],"cpp":v[t],"error":error})
    if actualwater!=water_count:raise ValueError("ELUSTR water denominator mismatch")
    result={"status":"PASS" if not count else "FAIL",
            "cases":CASES,"grid_cells":len(ref),"compared_scalars":3*len(ref),
            "water_cells":water_count,"stable_land_cells":len(ref)-water_count,
            "water_qh_print_tolerance":5.e-12,
            "water_ustar_and_L_sentinel_exact":True,
            "max_abs_errors_qh_ustar_L":maxerrors,
            "frozen_abs_tolerances":[ABS_QH,ABS_USTAR,ABS_L],
            "frozen_relative_tolerance":REL,
            "mismatch_count":count,"first_mismatches":mismatch,
            "vendor_git_blob":sha,"vendor_sha256":hashlib.sha256(raw).hexdigest(),
            "original_source_lines":loc,
            "scope":"ELUSTR QH<0 stable land path only, no daytime PSIU, no 2022 COMP coupling"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if count:raise SystemExit(1)
if __name__=="__main__":main()

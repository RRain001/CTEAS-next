#!/usr/bin/env python3
"""Literal CALMET SIMILT L30097-30370 + PSIUD L35629-35672 against the C++
source-scoped port. Covers the neutral WIND1 route (EL=ZI=ZIMINI=10000), the
stable and unstable DIAGI station-column route (EL from the surface fluxes,
ZII=amax1(ZIMECH,ZICONV), ZIMINI=deck ZIMIN), the Monin-Obukhov clamp at 5*z0,
the mixing-height cutoff, and both hemispheres. IPSIFCN=1 (PSIUC/COARE) is out
of scope and fails closed on the C++ side.
"""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

VENDOR_BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
TOL_MPS=2e-4

DRIVER="""      program testsimilt
      include 'params.met'
      include 'grid.met'
      include 'met1.met'
      include 'ovrwat.met'
      real us(mxnz,mxwnd),vs(mxnz,mxwnd)
      real zz,rough,u0,v0,latitude
      real el,zi,zmini
      integer iex,ips,filled
      character*256 input,output
      call get_command_argument(1,input)
      call get_command_argument(2,output)
      nx=50
      ny=50
      nz=9
      nzp1=10
      nssta=1
      nowsta=0
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
        zmid(k)=0.5*(zface(k+1)+zface(k))
      enddo
      open(10,file=trim(input),status='old')
      read(10,*) latitude,zz,rough,u0,v0,el,zi,zmini,iex,ips
      close(10)
      if(iex.ne.-4)stop 72
      xslat(1)=latitude
      do k=1,nz
        us(k,1)=999999.
        vs(k,1)=999999.
      enddo
      us(1,1)=u0
      vs(1,1)=v0
      call similt(zz,el,rough,zi,1,ips,us,vs,zmini)
c --- count the levels SIMILT actually wrote (the original exits above the
c --- mixing height and leaves the rest untouched)
      filled=0
      do k=1,nz
        if(us(k,1).lt.999998..and.vs(k,1).lt.999998.)filled=k
      enddo
      open(11,file=trim(output),status='replace')
      write(11,'(I5)')filled
      do k=1,nz
        write(11,'(I5,2ES22.13E3)')k,us(k,1),vs(k,1)
      enddo
      close(11)
      end
      real function psiuc(z,l,m)
      real z,l
      integer m
      stop 79
      end
"""

SCENES=[
    # name, latitude, anemometer, z0, u, v, EL, ZI, ZIMINI, IPSIFCN
    ("wind1_neutral_route",31.939774,10.,.1,3.,4.,10000.,10000.,10000.,0),
    ("unstable_mixed",31.939774,10.,.1,3.,4.,-30.,1000.,50.,0),
    ("stable_night",31.939774,10.,.1,3.,4.,30.,200.,50.,0),
    ("strongly_unstable",31.9,10.,.1,5.,-2.,-5.,800.,50.,0),
    ("very_stable",31.9,10.,.1,2.,1.,5.,150.,50.,0),
    ("el_clamped_low",31.9,10.,.1,3.,1.,-0.05,600.,50.,0),
    ("el_clamped_high",31.9,10.,.1,3.,1.,0.05,600.,50.,0),
    ("cutoff_at_second_face",31.9,10.,.1,3.,1.,-30.,19.,50.,0),
    ("cutoff_minimum_only",31.9,10.,.1,3.,1.,-30.,0.5,50.,0),
    ("southern_hemisphere",-30.,10.,.1,3.,4.,-30.,1000.,50.,0),
    ("southern_neutral",-30.,10.,.1,3.,4.,10000.,10000.,10000.,0),
    ("rough_rural",31.9,10.,1.,1.5,2.7,-60.,700.,50.,0),
    ("low_roughness",31.9,10.,.0001,5.3,1.2,120.,900.,50.,0),
    ("tall_anemometer",31.9,35.,.2,12.,-8.,-15.,1200.,50.,0),
    ("eastward_calm_ish",31.9,10.,.03,5.,0.,-45.,500.,50.,0),
]

def run(args):
    p=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=100)
    if p.returncode:
        raise RuntimeError(f"command={args} exit={p.returncode} stdout={p.stdout[-800:]} stderr={p.stderr[-1800:]}")

def original_sources(vendor,out):
    b=(vendor/"calmet.for").read_bytes()
    found=hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()
    if found!=VENDOR_BLOB:raise ValueError(f"original CALMET blob drift {found}")
    lines=b.decode().splitlines(keepends=True)
    def block(name,following,first,last):
        a=next(i for i,s in enumerate(lines) if s.lower().startswith("      subroutine "+name+"("))
        end=next(i for i,s in enumerate(lines) if s.lower().startswith("      subroutine "+following+"("))
        if a+1!=first or end+1!=last:
            raise ValueError(f"original {name} source location drift {a+1}/{end+1}")
        dest=out/(name+"_original.for")
        dest.write_text("".join(lines[a:end]))
        return {"file":dest,"start_line":a+1,"end_line":end,
                "sha256":hashlib.sha256(dest.read_bytes()).hexdigest()}
    similt=block("similt","slope",30097,30372)
    a=next(i for i,s in enumerate(lines) if s.lower().startswith("      function psiud("))
    end=next(i for i,s in enumerate(lines) if s.lower().startswith("      function psitd("))
    if a+1!=35629 or end+1!=35674:
        raise ValueError(f"original psiud source location drift {a+1}/{end+1}")
    psiud=out/"psiud_original.for"
    psiud.write_text("".join(lines[a:end]))
    psiud={"file":psiud,"start_line":a+1,"end_line":end,
           "sha256":hashlib.sha256(psiud.read_bytes()).hexdigest()}
    return similt,psiud

def main():
    p=argparse.ArgumentParser()
    for key in ("vendor","cpp","out"):
        p.add_argument("--"+key,type=Path,required=True)
    args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    similt,psiud=original_sources(args.vendor,args.out)
    driver=args.out/"driver.for";driver.write_text(DRIVER)
    binary=args.out/"original_similt_profile"
    run(["gfortran","-std=legacy","-O0","-fno-automatic",
         "-ffixed-line-length-none","-fallow-argument-mismatch",
         "-I"+str(args.vendor),similt["file"],psiud["file"],driver,"-o",binary])
    comparisons=0
    maximum=0.
    errors=[]
    cases=[]
    for scene in SCENES:
        name,lat,zan,z0,u,v,el,zi,zmini,ips=scene
        inp=args.out/(name+".in")
        inp.write_text(f"{lat} {zan} {z0} {u} {v} {el} {zi} {zmini} -4 {ips}\n"
                       "0 20 40 80 160 320 640 1200 2000 3000\n")
        ref=args.out/(name+".orig")
        cpp=args.out/(name+".cpp")
        run([binary,inp,ref]);run([args.cpp,inp,cpp])
        original_rows=ref.read_text().splitlines()
        modern_rows=cpp.read_text().splitlines()
        if len(original_rows)!=10 or len(modern_rows)!=10:
            raise ValueError(f"{name}: unexpected output shape")
        ref_filled=int(original_rows[0].split()[0])
        cpp_filled=int(modern_rows[0].split()[0])
        if ref_filled!=cpp_filled:
            errors.append(dict(scene=name,field="levels_filled",
                               original=ref_filled,cpp=cpp_filled))
        max_case=0.
        for k in range(9):
            a=original_rows[k+1].split()
            b=modern_rows[k+1].split()
            if len(a)!=3 or len(b)!=3 or int(a[0])!=k+1 or int(b[0])!=k+1:
                raise ValueError(f"{name}: layer/index mismatch at {k+1}")
            if k>=ref_filled:
                # Levels above the cutoff keep the original sentinel in both
                # implementations; they carry no profile to compare.
                continue
            for comp,(x,y) in enumerate(zip(a[1:],b[1:])):
                r,m=float(x),float(y)
                if not(math.isfinite(r) and math.isfinite(m)):
                    raise ValueError(f"{name}: nonfinite at {k+1}")
                e=abs(r-m)
                comparisons+=1
                maximum=max(maximum,e)
                max_case=max(max_case,e)
                if e>TOL_MPS:
                    errors.append(dict(scene=name,layer=k+1,component="UV"[comp],
                                       original=r,cpp=m,error=e))
        cases.append({"scene":name,"levels_filled":ref_filled,
                      "components_compared":2*ref_filled,
                      "max_abs_error_mps":max_case})
    report={"status":"PASS_SIMILT_PROFILE_ORIGINAL" if not errors else "FAIL",
            "scope":"SIMILT L30097-L30370 with PSIUD L35629-L35672 (IPSIFCN=0), overland station, "
                    "neutral/stable/unstable EL, mixing-height cutoff, both hemispheres; "
                    "IPSIFCN=1 (PSIUC/COARE) and overwater stations are out of scope and fail closed",
            "vendor_blob_sha":VENDOR_BLOB,
            "fortran_similt_sha256":similt["sha256"],
            "fortran_similt_lines":[similt["start_line"],similt["end_line"]],
            "fortran_psiud_sha256":psiud["sha256"],
            "fortran_psiud_lines":[psiud["start_line"],psiud["end_line"]],
            "tolerance_mps":TOL_MPS,
            "scenes":len(SCENES),"components_compared":comparisons,
            "max_abs_error_mps":maximum,"cases":cases,"first_mismatches":errors[:12]}
    (args.out/"p6d-similt-profile-parity.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if errors:raise SystemExit(1)

if __name__=="__main__":main()

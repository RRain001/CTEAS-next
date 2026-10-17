#!/usr/bin/env python3
"""Unmodified CALMET WIND1+SIMILT versus C++ selected two-station first guess.

Scope: one land SURF station, one upper station, no overwater, NBAR=0,
IEXTRP=-4, original DIAGNO EDIT=999 and EDITL=900, NZ=9. All 50x50x9 U/V values per case are compared. This does
not qualify multi-station WIND1 or complete 2022 DIAGNO meteorology.
"""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

SOURCE_SHA = "437f43bb7f0e51a1919e56664663e1a046986ed0"
TOLERANCE = 2e-4
NX = NY = 50
NZ = 9

DRIVER = r"""      program originalwind1
      include 'params.met'
      include 'grid.met'
      include 'wparm.met'
      include 'met1.met'
      include 'd1.met'
      include 'd3.met'
      include 'd4.met'
      include 'ovrwat.met'
      include 'geo.met'
      real sx,sy,ux,uy,wu,wv,zrough,latitude,height
      integer calm
      character*256 infile,outfile
      call get_command_argument(1,infile)
      call get_command_argument(2,outfile)
      nx=50
      ny=50
      nz=9
      nzp1=10
      dgrid=100.
      dx=100.
      dy=100.
      nssta=1
      nowsta=0
      nusta=1
      iextrp=-4
      ipsifcn=0
      nbar=0
      kbar=0
      iwat1=50
      iwat2=55
      edit=999.
      editl=900.
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
        cellzc(k)=zmid(k)
      enddo
      open(10,file=trim(infile),status='old')
      read(10,*) sx,sy,ux,uy,wu,wv,zrough,latitude,height,calm
      icalm=calm
      read(10,*) (bias(k),k=1,nz)
      do k=1,nz
        read(10,*) us(k,2),vs(k,2)
      enddo
      close(10)
      xssta(1)=sx
      yssta(1)=sy
      xusta(1)=ux
      yusta(1)=uy
      xslat(1)=latitude
      zanem(1)=height
      zlogsta(1)=1.
      ist(1)=int(sx/dgrid+1.)
      jst(1)=int(sy/dgrid+1.)
      do j=1,ny
        do i=1,nx
          ilandu(i,j)=10
          z0(i,j)=zrough
        enddo
      enddo
      us(1,1)=wu
      vs(1,1)=wv
      do k=2,nz
        us(k,1)=999.
        vs(k,1)=999.
      enddo
      call wind1
      open(11,file=trim(outfile),status='replace')
      do k=1,nz
        do j=1,ny
          do i=1,nx
            write(11,'(3(I5,1X),2(ES22.13E3,1X))')
     1       i,j,k,ug(i,j,k),vg(i,j,k)
          enddo
        enddo
      enddo
      close(11)
      end
c The selected control does not enable barrier or nonneutral PSI calls.
      subroutine barier(x,y,xst,yst,ok)
      real x,y,xst,yst,ok
      stop 81
      end
      double precision function psiud(r)
      double precision r
      stop 82
      end
      real function psiuc(z,l,m)
      real z,l
      integer m
      stop 83
      end
"""

def run(*argv):
    proc=subprocess.run([str(x) for x in argv],
                        capture_output=True,text=True,timeout=180)
    if proc.returncode:
        raise RuntimeError(
            f"command={argv} rc={proc.returncode} stdout={proc.stdout[-900:]} "
            f"stderr={proc.stderr[-1800:]}"
        )

def extract(vendor, directory):
    raw=(vendor/"calmet.for").read_bytes()
    sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    if sha != SOURCE_SHA:
        raise RuntimeError("Original frozen CALMET source blob mismatch: "+sha)
    lines=raw.decode().splitlines(keepends=True)
    def anchor(name):
        found=[n for n,line in enumerate(lines)
               if line.lower().startswith("      subroutine "+name)]
        if len(found)!=1:
            raise RuntimeError("Original subroutine not unique: "+name)
        return found[0]
    blocks=[
        ("wind1","windbc",35829,36404),
        ("similt","slope",30097,30372)
    ]
    paths=[]
    for name,following,expected,after in blocks:
        start=anchor(name)
        end=anchor(following)
        if start+1!=expected or end+1!=after:
            raise RuntimeError("Original source anchors drifted: "+name)
        path=directory/(name+"_source.for")
        path.write_text("".join(lines[start:end]))
        paths.append(path)
    return paths

def scenes():
    basics=[
        ("unbiased",3.,4.,0,[0.]*NZ,[]),
        ("upper_bias",3.,4.,0,[0.2,0.4,0.6,0.8,1.,0.2,0.4,0.6,0.8],[]),
        ("surface_bias",-2.,4.,0,[-0.2,-0.4,-0.6,-0.8,-1.,-0.2,-0.4,-0.6,-0.8],[]),
        ("upper_missing_layer",2.4,-3.2,0,[0.]*NZ,[2,6]),
        ("calm_icalm0",0.,0.,0,[0.]*NZ,[]),
        ("calm_icalm1",0.,0.,1,[0.]*NZ,[])
    ]
    for name,u,v,icalm,bias,missing in basics:
        upper=[(1.5+0.17*k,-3.1+0.11*k) for k in range(NZ)]
        for k in missing:
            upper[k]=(999.,999.)
        yield dict(name=name,surface_x=900.,surface_y=1600.,
                   upper_x=4100.,upper_y=3500.,u=u,v=v,
                   roughness=0.1,latitude=31.939774,height=10.,
                   icalm=icalm,bias=bias,upper=upper)

def write_case(path, case):
    with path.open("w") as f:
        f.write(" ".join(map(str,(
            case["surface_x"],case["surface_y"],case["upper_x"],
            case["upper_y"],case["u"],case["v"],
            case["roughness"],case["latitude"],case["height"],
            case["icalm"])))+"\n")
        f.write(" ".join(map(str,case["bias"]))+"\n")
        for u,v in case["upper"]:
            f.write(f"{u} {v}\n")

def compare(a,b,scene):
    original=a.read_text().splitlines()
    modern=b.read_text().splitlines()
    required=NX*NY*NZ
    if len(original)!=required or len(modern)!=required:
        raise RuntimeError(f"{scene}: wrong dimensions {len(original)}/{len(modern)}")
    errors=[]
    largest=0.
    compared=0
    for n,(ra,rb) in enumerate(zip(original,modern)):
        aa=ra.split()
        bb=rb.split()
        idx=(n%NX+1,(n//NX)%NY+1,n//(NX*NY)+1)
        if len(aa)!=5 or len(bb)!=5 or tuple(map(int,aa[:3]))!=idx or tuple(map(int,bb[:3]))!=idx:
            raise RuntimeError(f"{scene}: grid/field sequence mismatch at {idx}")
        for component in (3,4):
            x=float(aa[component]);y=float(bb[component])
            if not math.isfinite(x) or not math.isfinite(y):
                raise RuntimeError(f"{scene}: nonfinite field at {idx}")
            error=abs(x-y)
            largest=max(largest,error)
            compared+=1
            if error>TOLERANCE and len(errors)<12:
                errors.append(dict(cell=idx,component="U" if component==3 else "V",
                                   original=x,cpp=y,absolute_error=error))
    return dict(status="PASS" if not errors else "FAIL",
                components_compared=compared,max_abs_error_mps=largest,
                first_errors=errors)

def main():
    parser=argparse.ArgumentParser()
    for name in ("vendor","cpp","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    sources=extract(args.vendor,args.out)
    driver=args.out/"driver.for"
    driver.write_text(DRIVER)
    original=args.out/"original_wind1"
    run("gfortran","-std=legacy","-O0","-fno-automatic",
        "-ffixed-line-length-none","-fallow-argument-mismatch",
        "-I"+str(args.vendor),*sources,driver,"-o",original)
    results={}
    for scene in scenes():
        inp=args.out/(scene["name"]+".inp")
        ref=args.out/(scene["name"]+".fortran.txt")
        cpp=args.out/(scene["name"]+".cpp.txt")
        write_case(inp,scene)
        run(original,inp,ref)
        run(args.cpp,inp,cpp)
        results[scene["name"]]=compare(ref,cpp,scene["name"])
    ok=all(v["status"]=="PASS" for v in results.values())
    report={
        "status":"PASS_SELECTED_WIND1_FIRSTGUESS" if ok else "FAIL",
        "original_calmet_blob":SOURCE_SHA,
        "scope":"WIND1 1 land + 1 upper, IEXTRP=-4, NBAR=0, 50x50x9 synthetic; NOT real 2022 full DIAGNO",
        "tolerance_mps":TOLERANCE,
        "scenes":len(results),
        "components_compared":sum(r["components_compared"] for r in results.values()),
        "max_abs_error_mps":max(r["max_abs_error_mps"] for r in results.values()),
        "cases":results
    }
    path=args.out/"p6d8b-wind1-firstguess-parity.json"
    path.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if not ok:
        raise SystemExit(1)

if __name__=="__main__":
    main()
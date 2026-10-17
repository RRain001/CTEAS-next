#!/usr/bin/env python3
"""Independent original-format Fortran GEO.DAT input read vs P6 C++ READGE path.

The FORTRAN driver uses READGE's exact selected-case list-directed input
order and FILLGEO's IOPT=2 gridded path, as audited from vendor calmet.for
L27911-27993, L28154-28214, L28210-28390, L7088-7093. It is a separate
Fortran input-format comparator, NOT the complete original READGE routine
with QA scratch/printed output. Original CALMET.DAT header/static grids
were independently decoded in P6B, but it does not expose all 8 fields.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,subprocess
from pathlib import Path

DRIVER=r"""      program readge_8field_selected
      implicit none
      integer nx,ny,ncomment,nlu,iwat1,iwat2,zone,iopt
      integer i,j,k,n,ilandu(50,50),ilucat(14)
      real xorig,yorig,dx,dy,htfac
      real elev(50,50),z0(50,50),alb(50,50)
      real bow(50,50),hcg(50,50),qf(50,50),lai(50,50)
      character*16 dataset,dataver
      character*64 datamod
      character*80 comment
      character*8 pmap,datum
      character*12 daten
      character*4 hem,xyunit
      character*256 inp,out
      call get_command_argument(1,inp)
      call get_command_argument(2,out)
      open(10,file=trim(inp),status='old')
      read(10,'(2a16,a64)')dataset,dataver,datamod
      if(dataset.ne.'GEO.DAT')stop 1
      if(dataver.ne.'2.1')stop 2
      read(10,'(i4)')ncomment
      if(ncomment.lt.0.or.ncomment.gt.10000)stop 3
      do i=1,ncomment
        read(10,'(a80)')comment
      enddo
      read(10,'(a8)')pmap
      read(10,'(i4,a4)')zone,hem
      read(10,'(a8,a12)')datum,daten
      read(10,'(2i8,4f12.3)')nx,ny,xorig,yorig,dx,dy
      read(10,'(a4)')xyunit
      if(pmap.ne.'UTM')stop 4
      if(zone.ne.50.or.hem.ne.'N')stop 5
      if(datum.ne.'WGS-84')stop 6
      if(xyunit.ne.'KM')stop 7
      if(nx.ne.50.or.ny.ne.50)stop 8
      if(abs(dx-.1).gt.0.000001)stop 9
      read(10,*)iopt
      if(iopt.ne.1)stop 10
      read(10,*)nlu,iwat1,iwat2
      if(nlu.ne.14.or.iwat1.ne.50.or.iwat2.ne.55)stop 11
      read(10,*)(ilucat(n),n=1,nlu)
      do j=ny,1,-1
        read(10,*)(ilandu(n,j),n=1,nx)
      enddo
      read(10,*)htfac
      if(htfac.ne.1.0)stop 12
      do j=ny,1,-1
        read(10,*)(elev(n,j),n=1,nx)
      enddo
      read(10,*)iopt
      if(iopt.ne.2)stop 13
      do j=ny,1,-1
        read(10,*)(z0(n,j),n=1,nx)
      enddo
      read(10,*)iopt
      if(iopt.ne.2)stop 14
      do j=ny,1,-1
        read(10,*)(alb(n,j),n=1,nx)
      enddo
      read(10,*)iopt
      if(iopt.ne.2)stop 15
      do j=ny,1,-1
        read(10,*)(bow(n,j),n=1,nx)
      enddo
      read(10,*)iopt
      if(iopt.ne.2)stop 16
      do j=ny,1,-1
        read(10,*)(hcg(n,j),n=1,nx)
      enddo
      read(10,*)iopt
      if(iopt.ne.2)stop 17
      do j=ny,1,-1
        read(10,*)(qf(n,j),n=1,nx)
      enddo
      read(10,*)iopt
      if(iopt.ne.2)stop 18
      do j=ny,1,-1
        read(10,*)(lai(n,j),n=1,nx)
      enddo
      close(10)
      open(11,file=trim(out),status='replace')
      do j=1,ny
        do i=1,nx
          write(11,'(3(I5,1X),7(ES22.13E3,1X))')
     1    i,j,ilandu(i,j),elev(i,j),z0(i,j),alb(i,j),
     2    bow(i,j),hcg(i,j),qf(i,j),lai(i,j)
        enddo
      enddo
      close(11)
      end
"""

def sha(path:Path):return hashlib.sha256(path.read_bytes()).hexdigest()

def check_source(vendor:Path):
    lines=(vendor/"calmet.for").read_text().splitlines()
    required=[
        "      read(iogeo,*)iopt(1)",
        "          read(iogeo,*)nlu,iwat1,iwat2",
        "          read(iogeo,*)(ilucat(n),n=1,nlu)",
        "       read(iogeo,*)(ilandu(n,j),n=1,nx)",
        "       read(iogeo,*)(elev(n,j),n=1,nx)",
        "       read(iogeo,*)iopt(2)",
        "       read(iogeo,*)iopt(3)",
        "       read(iogeo,*)iopt(4)",
        "       read(iogeo,*)iopt(5)",
        "       read(iogeo,*)iopt(6)",
        "       read(iogeo,*)iopt(7)",
        "          read(iogeo,*)(var(n,j),n=1,nx)",
    ]
    anchors={}
    for line in required:
        hits=[k+1 for k,s in enumerate(lines) if s.strip()==line.strip()]
        if len(hits)!=1:raise RuntimeError(f"original READGE/FILLGEO source line missing or ambiguous: {line!r}: {hits}")
        anchors[line.strip()]=hits[0]
    return {"calmet_source_sha256":sha(vendor/"calmet.for"),"READGE_and_FILLGEO_lines":anchors}

def run(args):
    p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError(f"execution failed rc={p.returncode}: {args}\nstderr={p.stderr[-2000:]}\nstdout={p.stdout[-1000:]}")

def check(ref:Path,candidate:Path):
    original=[line.split() for line in ref.read_text().splitlines()]
    with candidate.open(newline="") as fp:modern=list(csv.DictReader(fp))
    if len(original)!=2500 or len(modern)!=2500:
        raise ValueError("invalid 50x50 GEO comparison row count")
    names=["landuse","elevation_m","z0_m","albedo","bowen","hcg","qf","lai"]
    error={name:0.0 for name in names[1:]}
    failures=[]
    for n,(f,c) in enumerate(zip(original,modern)):
        i=n%50+1;j=n//50+1
        if len(f)!=10 or (int(f[0]),int(f[1]))!=(i,j) or\
           (int(c["i"]),int(c["j"]))!=(i,j):
            raise ValueError(f"original/C++ grid ordering error at {n}")
        if int(f[2])!=int(c["landuse"]):
            failures.append({"i":i,"j":j,"field":"landuse"})
        for column,name in enumerate(names[1:],3):
            a,b=float(f[column]),float(c[name])
            if not math.isfinite(a) or not math.isfinite(b):
                raise ValueError("nonfinite GEO reference")
            d=abs(a-b)
            error[name]=max(error[name],d)
            if d>1.e-5 and len(failures)<20:
                failures.append({"i":i,"j":j,"field":name,"original":a,
                                 "cpp":b,"abs_error":d})
    return {"status":"PASS" if not failures else "FAIL",
            "cells":2500,"compared_fields":20000,
            "source_format_abs_tolerance":1.e-5,
            "max_absolute_field_errors":error,
            "first_mismatches":failures[:20]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--vendor",required=True,type=Path)
    ap.add_argument("--geo",required=True,type=Path)
    ap.add_argument("--cpp",required=True,type=Path)
    ap.add_argument("--origin-x",required=True,type=float)
    ap.add_argument("--origin-y",required=True,type=float)
    ap.add_argument("--out",required=True,type=Path)
    a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    text=a.out/"fortran_readge_selected_driver.for"
    text.write_text(DRIVER)
    binary=a.out/"fortran_readge_selected"
    run(["gfortran","-std=legacy","-O0","-ffixed-line-length-none",
         text,"-o",binary])
    original=a.out/"reference_fortran_fields.txt"
    modern=a.out/"candidate_cpp_fields.csv"
    run([binary,a.geo,original])
    run([a.cpp,a.geo,modern,str(a.origin_x),str(a.origin_y)])
    cmp=check(original,modern)
    output={**cmp,"source_audit":check_source(a.vendor),
            "original_geo_sha256":sha(a.geo),
            "original_fortran_reader_driver_sha256":sha(text),
            "comparison_type":"Independent native Fortran list-directed GEO read following original READGE/FILLGEO source; not original full READGE routine",
            "scientific_limits":"Only selected GEO.DAT gridded static fields, no SURF/UP observations or complete CALMET physics"}
    (a.out/"p6c-readge-8field-parity.json").write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps(output,indent=2))
    if cmp["status"]!="PASS":raise SystemExit(1)
if __name__=="__main__":main()

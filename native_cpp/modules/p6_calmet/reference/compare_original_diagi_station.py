#!/usr/bin/env python3
"""Original CALMET DIAGI station/height mapping parity for P6C, no weather needed.

References exact original code slices from CALMET 6.5.0 DIAGI
L5097-5117, L5123-5145, L5163-5182 and READCF's ZMID calculation.
Source copied verbatim into the compiled independent Fortran driver,
without patching the vendor file. This is a *subsection* comparison only:
not yet full DIAGI/SETCOM/RDHDU/weather station flow equivalence.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,subprocess
from pathlib import Path

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def cut(lines,first,last,max_len=55):
    start=[i for i,l in enumerate(lines) if l.rstrip()==first]
    if len(start)!=1:raise RuntimeError(f"original CALMET slice start not unique: {first}")
    ix=start[0]
    final=[i for i in range(ix,min(len(lines),ix+max_len)) if lines[i].rstrip()==last]
    if not final:raise RuntimeError(f"original CALMET slice end missing: {last}")
    # The outer original IF contains nested IFs whose ENDIF text matches.
    # Our maximum source window ends before the next source block, so the
    # last matching ENDIF is the original outer closing statement.
    end=final[-1]
    return ix+1,end+1,"\n".join(lines[ix:end+1])+"\n"

HEADER=r"""      program originaldiagist
      include 'params.met'
      real xssta(mxss),yssta(mxss),xusta(mxus),yusta(mxus)
      real zanem(mxss),z0(mxnx,mxny),zlogsta(mxss)
      real utmxst(mxwnd),utmyst(mxwnd)
      real dgrid,dx,dy,zface(mxnzp1),zmid(mxnz)
      real cellzc(mxnz)
      real xlnzo,xlnz1,xlnz2
      integer ist(mxwnd),jst(mxwnd),iiup(mxus),jjup(mxus)
      integer idiopt(5),iupt,iiupt,jjupt
      character*4 namst(mxwnd),csnam(mxss),cunam(mxus)
      character*256 inp,out
      call get_command_argument(1,inp)
      call get_command_argument(2,out)
      open(10,file=trim(inp),status='old')
      read(10,*) nssta,nusta
      nx=50
      ny=50
      nz=9
      dx=100.
      dy=100.
      dgrid=100.
      noobs=0
      nowsta=0
      iupt=0
      idiopt(2)=0
      read(10,*) (zface(i),i=1,nz+1)
      do j=1,ny
        read(10,*) (z0(i,j),i=1,nx)
      enddo
      do n=1,nssta
        read(10,*) xssta(n),yssta(n),zanem(n)
        csnam(n)='SS'
      enddo
      do n=1,nusta
        read(10,*) xusta(n),yusta(n)
        cunam(n)='US'
      enddo
      close(10)
      do i=1,nz
"""
FOOTER=r"""      enddo
      cellzc(1)=zmid(1)
"""
OUT=r"""      open(11,file=trim(out),status='replace')
      do n=1,nssta
        isc=max(1,min(nx,ist(n)))
        jsc=max(1,min(ny,jst(n)))
        write(11,'(A,1X,I4,2(1X,ES22.13E3),6(1X,I6),
     1            1X,ES22.13E3)')
     2    'S',n,utmxst(n),utmyst(n),
     3    ist(n),jst(n),isc,jsc,0,0,zlogsta(n)
      enddo
      do n=1,nusta
        ii=nssta+n
        write(11,'(A,1X,I4,2(1X,ES22.13E3),6(1X,I6),
     1            1X,ES22.13E3)')
     2    'U',n,utmxst(ii),utmyst(ii),
     3    ist(ii),jst(ii),0,0,iiup(n),jjup(n),0.0
      enddo
      close(11)
      end
"""

def build_source(vendor:Path,output:Path):
    source=vendor/"calmet.for"
    lines=source.read_text().splitlines()
    first=next(i for i,l in enumerate(lines) if l.startswith("      subroutine diagi("))
    last=next(i for i,l in enumerate(lines) if l.startswith("      subroutine diagno("))
    diagi=lines[first:last]
    one=cut(diagi,"      if(idiopt(2).eq.0 .and. noobs.eq.0)then",
            "      endif",24)
    two=cut(diagi,"      if (noobs.lt.2) then","      end if",32)
    three=cut(diagi,"      do n=1,nssta","      end do",24)
    midpoint=[(i,l) for i,l in enumerate(lines)
              if l.rstrip()=="      zmid(i)=0.5*(zface(i+1)+zface(i))"]
    if len(midpoint)!=1:raise RuntimeError("original midpoint formula not uniquely identified")
    # Do not change whitespace/capitalization in extracted calculation lines.
    body=HEADER+midpoint[0][1]+"\n"+FOOTER+one[2]+two[2]+three[2]+OUT
    output.write_text(body)
    return {"vendor_sha256":sha(source),
            "original_DIAGI_upper_lines":[first+one[0],first+one[1]],
            "original_DIAGI_station_lines":[first+two[0],first+two[1]],
            "original_DIAGI_roughness_lines":[first+three[0],first+three[1]],
            "original_ZMID_source_line":midpoint[0][0]+1,
            "compiled_source_sha256":sha(output)}

def fixtures():
    xys=[(0,0,10),(.01,4999.5,8),(-250,-350,10),
         (5100,2500,15),(50,50,6),(2500,2500,12),
         (4999,4999,20),(1234.567,987.654,11)]
    u=[(0,0),(50,50),(5000,5000),(-151,5300),
       (2500,2500),(-3100,-3700)]
    faces=(0,20,40,80,160,320,640,1200,2000,3000)
    for tag,scale in [("varying_roughness",1.0),("high_roughness",3.0),
                      ("low_roughness",.1)]:
        rough=[(0.03 + 0.004*(i%13)+0.002*(j%17))*scale
               for j in range(50) for i in range(50)]
        yield tag,xys,u,faces,rough

def write_fixture(path,stations,upper,faces,rough):
    with path.open("w") as f:
        f.write(f"{len(stations)} {len(upper)}\n")
        f.write(" ".join(str(v) for v in faces)+"\n")
        for j in range(50):
            f.write(" ".join(f"{v:.8f}" for v in rough[j*50:(j+1)*50])+"\n")
        for x,y,h in stations:f.write(f"{x:.8f} {y:.8f} {h:.8f}\n")
        for x,y in upper:f.write(f"{x:.8f} {y:.8f}\n")

def compare(fortran,cpp):
    a=[line.split() for line in fortran.read_text().splitlines()]
    with cpp.open(newline="") as f:b=list(csv.DictReader(f))
    if len(a)!=len(b):raise ValueError("Fortran/C++ station record length mismatch")
    max_float=0.0;failures=[]
    for n,(ra,rb) in enumerate(zip(a,b)):
        if len(ra)!=11:raise ValueError(f"original output not 11 columns {n}: {ra}")
        if ra[0]!=rb["kind"] or int(ra[1])!=int(rb["n"]):
            failures.append({"n":n,"type":"identity mismatch"})
            continue
        for i,key in enumerate(("ist","jst","isc","jsc","iiup","jjup"),4):
            if int(ra[i])!=int(rb[key]):
                failures.append({"n":n,"field":key,"original":int(ra[i]),"modern":int(rb[key])})
        for i,key,tol in ((2,"x_km",1e-5),(3,"y_km",1e-5),(10,"zlogsta",2e-5)):
            diff=abs(float(ra[i])-float(rb[key]))
            if not math.isfinite(diff):raise ValueError("nonfinite station QA field")
            max_float=max(diff,max_float)
            if diff>tol:
                failures.append({"n":n,"field":key,"original":float(ra[i]),
                                 "modern":float(rb[key]),"error":diff,"tol":tol})
    return {"status":"PASS" if not failures else "FAIL",
            "records":len(b),"checked_fields":len(b)*9,
            "max_absolute_numeric_diff":max_float,
            "first_errors":failures[:20]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--vendor",required=True,type=Path)
    parser.add_argument("--cpp",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    a=parser.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    driver=a.out/"original_diagi_station.for"
    evidence=build_source(a.vendor,driver)
    binary=a.out/"original_diagi_station"
    command=["gfortran","-O0","-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-I"+str(a.vendor),
             driver,"-o",binary]
    p=subprocess.run(command,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(f"Fortran source compile failed: {p.stderr}")
    result={"source":evidence,"source_warning":"selected original DIAGI source subsections; not full DIAGI flow",
            "cases":{}}
    for tag,sta,up,faces,rough in fixtures():
        inp=a.out/(tag+".txt")
        reference=a.out/(tag+".original")
        candidate=a.out/(tag+".cpp.csv")
        write_fixture(inp,sta,up,faces,rough)
        for argv in ([binary,inp,reference],[a.cpp,inp,candidate]):
            x=subprocess.run(list(map(str,argv)),text=True,capture_output=True)
            if x.returncode:raise RuntimeError(f"run {argv[0]} failed: {x.stderr} {x.stdout}")
        result["cases"][tag]={**compare(reference,candidate),
                              "input_sha256":sha(inp)}
    result["status"]="PASS_CALMET_DIAGI_STATION_SUBSECTION_PARITY" if all(
        c["status"]=="PASS" for c in result["cases"].values()) else "FAIL"
    result["checked_fields"]=sum(c["checked_fields"] for c in result["cases"].values())
    (a.out/"p6c_station_fortran_parity.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if result["status"].startswith("FAIL"):raise SystemExit(1)
if __name__=="__main__":main()

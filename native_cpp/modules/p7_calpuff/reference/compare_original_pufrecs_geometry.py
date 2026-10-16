#!/usr/bin/env python3
"""Compile unmodified CALPUFF SLGFRAC and exact PUFRECS L4950/L4961-4985
source statements into a REAL4 Fortran oracle. Compare against independent
native C++ port at the binary float32 bit level.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--vendor",type=Path,required=True)
    p.add_argument("--probe",type=Path,required=True)
    p.add_argument("--compiler",default="gfortran")
    a=p.parse_args()
    source=a.vendor.read_text(encoding="latin-1").splitlines(True)
    original="".join(source[7122:7205])
    if not original.lstrip().lower().startswith("subroutine slgfrac("):
        raise AssertionError("SLGFRAC vendor source anchor changed")
    geom="".join(source[4960:4985])
    # Source-anchored terrain gate: emit *original* PUFFCT2 and the
    # MCTADJ=2 caller, not an independently invented terrain algorithm.
    import re
    anchors=[i for i,line in enumerate(source)
             if re.match(r"^\s{6}subroutine\s+puffct2\s*\(",line,re.I)]
    if len(anchors)!=1:
        raise AssertionError(f"original PUFFCT2 anchor changed: {anchors}")
    start=anchors[0]
    tail=next((i for i in range(start+1,min(start+700,len(source)))
               if re.match(r"^\s{6}end\s*$",source[i],re.I)),None)
    if tail is None:
        raise AssertionError("PUFFCT2 vendor routine END not found")
    print(f"P7_VENDOR_PUFFCT2_SOURCE_SPAN={start+1}-{tail+1}")
    for i in range(start,tail+1):
        print(f"P7_VENDOR_PUFFCT2_RAW LINE={i+1} TEXT={source[i].rstrip()!r}")
    ctadj_calls=[i for i,line in enumerate(source) if
                 line.lstrip().lower().startswith("call ctadj2(")]
    print("P7_VENDOR_CTADJ2_CALL_SITES="+str([i+1 for i in ctadj_calls]))
    for callsite in ctadj_calls:
        for i in range(max(0,callsite-22),min(len(source),callsite+48)):
            print(f"P7_VENDOR_CTADJ2_CONTEXT LINE={i+1} TEXT={source[i].rstrip()!r}")
    for i in range(5319,5376):
        print(f"P7_VENDOR_MCTADJ2_PUFRECS_RAW LINE={i+1} TEXT={source[i].rstrip()!r}")
    if "frac=AMAX1(" not in geom or "xtt1 = xttb1+xr1" not in geom:
        raise AssertionError("PUFRECS FCLIP/front geometry source changed")
    # Direct vendor statements inserted literally; no formula retyping.
    subroutine = """
      subroutine geom(x,y,x1,y1,x2,y2,syb1,sye1,fclip,
     &                xttb1,uavg,lclip,frac,xr1,xtt1,trec,
     &                rhoa,rhoc,sfrac,xbe1,rxbe1)
      logical lclip
      call slgfrac(x,y,x1,y1,x2,y2,xr1,yr1,frac,xbe1,rxbe1)
      rhoa=xr1
      rhoc=yr1
      sfrac=frac
""" + geom + """
      return
      end
"""
    if not all(s in subroutine.lower() for s in
               ("frac=amax1", "frac=amin1", "xtt1", "trec")):
        raise AssertionError("missing original PUFRECS geometry statements")
    driver = """
      program testgeom
      implicit none
      real x,y,x1,y1,x2,y2,syb,sye,fclip,xttb,uavg
      real frac,xr1,xtt1,trec,rhoa,rhoc,sfrac,len,inv
      real slgalong,slgacross,slgfracval,slglen,slginv
      integer i,clip,stat
      logical lclip
      do
       read(*,*,iostat=stat) x,y,x1,y1,x2,y2,syb,sye,
     &                        fclip,xttb,uavg,clip
       if(stat.ne.0) exit
       lclip=clip.ne.0
       call slgfrac(x,y,x1,y1,x2,y2,slgalong,slgacross,
     &              slgfracval,slglen,slginv)
       call geom(x,y,x1,y1,x2,y2,syb,sye,fclip,xttb,uavg,
     &           lclip,frac,xr1,xtt1,trec,rhoa,rhoc,sfrac,len,inv)
       write(*,'(9(Z8.8,1X))') transfer(slgalong,0),
     &   transfer(slgacross,0),transfer(slgfracval,0),
     &   transfer(slglen,0),transfer(slginv,0),
     &   transfer(frac,0),transfer(xr1,0),
     &   transfer(xtt1,0),transfer(trec,0)
      end do
      end
"""
    cases=[
        (50,1,100,0,0,0,10,20,1,100,2,0),
        (200,0,100,0,0,0,10,20,1,100,2,1),
        (-500,0,100,0,0,0,10,20,1,30,3,0),
        (0.5,0.5,0.5,0,0,0,10,20,1,20,2,0),
        (0.5,0.5,1,0,0,0,10,20,1,20,2,0),
        (0,0,0,0,0,0,10,20,1,20,2,0),
        (3,4,4,3,-4,-3,10,20,1,150,2,1),
        (3,4,4,3,-4,-3,10,20,1,150,2,0),
        (0,0,-100,50,100,-50,30,10,2,100,3,1),
        (100,50,-100,50,100,-50,30,10,2,100,3,0),
        (1,0,100,0,0,0,10,20,0,0,5,1),
        (150,0,100,0,0,0,10,20,2,120,5,1),
        (-25,-30,-1,-2,-30,-50,3,8,1,100,2,0),
        (0,2,1,2,0,2,1,1,0,10,1,1),
        (0.4,-0.2,0.2,0.3,-0.2,0.0,4,9,0.7,50,3,1),
        (0.4,-0.2,0.2,0.3,-0.2,0.0,4,9,0.7,50,3,0),
    ]
    inputs="".join(" ".join(str(v) for v in case)+"\n" for case in cases)
    with tempfile.TemporaryDirectory(prefix="p7-pufrecs-geom-") as d:
        tmp=Path(d)
        f=tmp/"vendor_geom.for"
        f.write_text(original+"\n"+subroutine+"\n"+driver,encoding="latin-1")
        exe=tmp/"vendor_geom"
        subprocess.run([a.compiler,"-O0","-ffixed-line-length-none",
                        str(f),"-o",str(exe)],
                       check=True,capture_output=True,text=True)
        def call(args):
            result=subprocess.run(args,input=inputs,text=True,
                                  capture_output=True,check=True)
            return [line.upper().strip().split() for line in result.stdout.splitlines()]
        vendor=call([str(exe)])
        native=call([str(a.probe)])
    if len(vendor)!=len(cases) or len(native)!=len(cases):
        raise AssertionError("wrong PUFRECS oracle row count")
    for index,(lhs,rhs) in enumerate(zip(vendor,native)):
        if lhs!=rhs:
            details=[(j,l,r) for j,(l,r) in enumerate(zip(lhs,rhs)) if l!=r]
            raise AssertionError(
                f"PUFRECS_GEOMETRY_FIRST_DIFF_CASE={index+1} "
                f"input={cases[index]} float_words_diff={details}")
    print(f"P7_ORIGINAL_SLGFRAC_PUFRECS_GEOMETRY_REAL4=PASS CASES={len(cases)} "
          "FLOAT_WORDS=9 BITWISE_EXACT=YES FCLIP=ORIGINAL_FORTRAN")


if __name__=="__main__":
    main()

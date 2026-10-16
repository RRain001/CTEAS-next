#!/usr/bin/env python3
"""G18D6 independent REAL*4 original CALMET SETCOM NEARU station parity.

Original compiled body includes the *literal* SETCOM upper-station
nearest-gridpoint Fortran loops and original DATA RMAX cap (not a
hand-written equivalent implementation).
"""
import argparse
import json
import pathlib
import re
import subprocess
import tempfile


def literal_vendor_source(content: str) -> str:
    lower=content.lower()
    sub=lower.find("      subroutine setcom(")
    if sub<0:
        raise RuntimeError("original CALMET SETCOM not found")
    data_re=re.search(r"(?mi)^\s{6}data rmax/1\.e37/,ldate/\.false\./\s*$",
                      content[sub:sub+20000])
    if not data_re:
        raise RuntimeError("original CALMET SETCOM RMAX DATA not found")
    dataline=data_re.group(0)
    begin=lower.find("      if(nusta.le.0)go to 121",sub)
    end=lower.find("120   continue",begin)
    if begin<0 or end<begin or end-begin>2500:
        raise RuntimeError("original NEARU REAL4 selection loop not found")
    body=content[begin:end+len("120   continue")]
    collapsed=re.sub(r"\s+","",body.lower())
    for required in (
        "xgdpt=(float(i)-0.5)*dgrid",
        "ygdpt=(float(j)-0.5)*dgrid",
        "dmin2=rmax",
        "dist2=(xusta(k)-xgdpt)**2+(yusta(k)-ygdpt)**2",
        "if(dist2.lt.dmin2)then",
        "nearu(i,j)=ksv",
    ):
        if re.sub(r"\s+","",required.lower()) not in collapsed:
            raise RuntimeError(f"vendor NEARU source changed: {required}")
    prolog="""      program literal_source_nearu
      implicit none
      integer nx,ny,nusta,io6,i,j,k,ksv
      integer nearu(64,64)
      real xusta(8),yusta(8),dgrid
      real xgdpt,ygdpt,dmin2,dist2,rmax
      logical ldate
"""
    prolog+=dataline+"\n"
    prolog+="""      io6=6
      read(*,*) nx,ny,nusta,dgrid
      if(nx.lt.2.or.ny.lt.2.or.nx.gt.64.or.ny.gt.64.or.
     &   nusta.lt.1.or.nusta.gt.8) stop 90
      do k=1,nusta
         read(*,*) xusta(k),yusta(k)
      enddo
"""
    epilog="""121   continue
 18   format('INVALID NEARU I/J/KSV=',3I8,1X,A5)
      do j=1,ny
      do i=1,nx
         write(*,'(I0)') nearu(i,j)
      enddo
      enddo
      end
"""
    return prolog+body+"\n"+epilog


def cases():
    yield (2,2,1,10000.,[(12000.,17000.)])
    yield (12,12,2,10000.,[(20000.,20000.),(50000.,50000.)])
    yield (12,12,2,10000.,[(20000.,20000.),(20000.,20000.)])
    yield (12,12,2,10000.,[(5000.,5000.),(15000.,5000.)])
    yield (12,12,2,10000.,[(10000.,10000.),(100000.,100000.)])
    yield (12,12,3,10000.,[(5000.,5000.),(55000.,55000.),(115000.,115000.)])
    yield (12,12,4,5000.,[(5000.,5000.),(20000.,5000.),(5000.,30000.),(30000.,30000.)])
    yield (17,13,4,5000.,[(10000.,10000.),(60000.,50000.),(40000.,20000.),(60000.,50000.)])
    yield (31,25,6,10000.,[(float(i*30000+5000),float((i%3)*30000+5000)) for i in range(6)])
    yield (50,50,6,10000.,[(float(i*70000+5000),float((i%4)*110000+5000)) for i in range(6)])
    yield (12,12,2,20000.,[(-200000.,-100000.),(1000000.,750000.)])
    yield (5,5,3,10000.,[(25000.,25000.),(25000.,25000.),(25000.,25000.)])
    yield (64,64,8,5000.,[(float(i*45000+2500),float((i%4)*65000+2500)) for i in range(8)])


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--vendor",type=pathlib.Path,required=True)
    p.add_argument("--cpp",type=pathlib.Path,required=True)
    p.add_argument("--gfortran",default="gfortran")
    p.add_argument("--out",type=pathlib.Path,required=True)
    a=p.parse_args()
    source=literal_vendor_source(a.vendor.read_text(encoding="latin-1"))
    with tempfile.TemporaryDirectory(prefix="g18d6-original-nearu-") as d:
        root=pathlib.Path(d);src=root/"setcom_nearu.f";exe=root/"setcom_nearu"
        src.write_text(source,encoding="ascii")
        subprocess.run([a.gfortran,"-O0","-ffixed-line-length-none",
                        str(src),"-o",str(exe)],
                       check=True,text=True,capture_output=True)
        compared=0
        for index,(nx,ny,nsta,spacing,sites) in enumerate(cases()):
            inp=f"{nx} {ny} {nsta} {spacing}\n"+"".join(
                f"{x} {y}\n" for x,y in sites)
            def rows(cmd):
                data=subprocess.run(cmd,input=inp,text=True,
                                    capture_output=True,check=True).stdout
                numbers=[int(v) for v in data.split()]
                if len(numbers)!=nx*ny:
                    raise AssertionError(f"NEARU wrong grid shape case={index}")
                return numbers
            vendor=rows([str(exe)])
            native=rows([str(a.cpp)])
            if native!=vendor:
                for k,(v,c) in enumerate(zip(vendor,native)):
                    if v!=c:
                        raise AssertionError(
                            f"NEARU exact original vendor mismatch case={index} "
                            f"i={k%nx+1} j={k//nx+1} vendor={v} cpp={c}")
            compared+=nx*ny
    result={"status":"PASS_G18D6_LITERAL_VENDOR_SET COM_NEARU_REAL4",
            "cases":index+1,"compared_cells":compared,
            "tolerance":"exact 1-based ordinal equality, no loosened tolerance",
            "scope":"selected NOOBS=0 source SETCOM up to 8 upper stations",
            "not_accepted":"complete CALMET 17-stage multi-station hourly physics"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(result["status"],result["cases"],result["compared_cells"])


if __name__=="__main__":
    main()

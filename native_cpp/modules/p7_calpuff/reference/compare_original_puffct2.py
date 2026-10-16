#!/usr/bin/env python3
"""Bitwise compare native C++ PUFFCT2 against unmodified original CALPUFF
L21068-21095 body, built with a test-only local /CURRENT/ state mapping.
No frozen DGM/meteorological oracle state drives C++ production code.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--vendor",type=Path,required=True)
    parser.add_argument("--probe",type=Path,required=True)
    args=parser.parse_args()
    source=args.vendor.read_text(encoding="latin-1").splitlines(True)
    if "subroutine puffct2(frac,xr1,yr1,zpr)" not in source[21034].lower():
        raise AssertionError("unmodified original PUFFCT2 routine moved")
    statements="".join(source[21067:21095])
    for anchor in ("xr1=xb1+frac*(xe1-xb1)",
                   "if(lup1) then",
                   "if(fracz1.LE.zero) then",
                   "if(fracz1.GE.one) then",
                   "zpr=zb1+AMAX1(zero,(frac-fracz1))*zjump"):
        if anchor.lower() not in statements.lower():
            raise AssertionError("PUFFCT2 original body changed: "+anchor)
    # Inject only minimal COMMON declarations. All computational statements
    # (and DATA one/zero, original branch ordering) are lifted verbatim.
    common="""      real xb1,yb1,zb1,xe1,ye1,ze1,fracz1
      logical lup1
      common /p7puffct2/ xb1,yb1,zb1,xe1,ye1,ze1,fracz1,lup1
"""
    routine="""      subroutine puffct2(frac,xr1,yr1,zpr)
"""+common+statements+"""      end
"""
    driver="""      program testpuffct2
      implicit none
      real frac,xb1,yb1,zb1,xe1,ye1,ze1,fracz1
      real xr1,yr1,zpr
      integer flag,stat
      logical lup1
      common /p7puffct2/ xb1,yb1,zb1,xe1,ye1,ze1,fracz1,lup1
      do
        read(*,*,iostat=stat) frac,xb1,yb1,zb1,xe1,ye1,
     &                        ze1,fracz1,flag
        if(stat.ne.0) exit
        lup1=flag.ne.0
        call puffct2(frac,xr1,yr1,zpr)
        write(*,'(3(Z8.8,1X))') transfer(xr1,0),
     &       transfer(yr1,0),transfer(zpr,0)
      end do
      end
"""
    cases=[
        (0.2,100,200,50,200,300,20,0.4,1),
        (0.8,100,200,50,200,300,20,0.4,1),
        (0.2,100,200,50,200,300,20,0.4,0),
        (0.7,100,200,50,200,300,20,0.4,0),
        (0.0,100,200,50,200,300,20,0,1),
        (0.0,100,200,50,200,300,20,0,0),
        (1.0,100,200,50,200,300,20,1,1),
        (1.0,100,200,50,200,300,20,1,0),
        (-0.3,100,200,50,200,300,20,0.4,1),
        (1.3,100,200,50,200,300,20,0.4,1),
        (-0.3,100,200,50,200,300,20,0.4,0),
        (1.3,100,200,50,200,300,20,0.4,0),
        (0.5,1,2,200,1,2,50,-0.2,1),
        (0.5,1,2,200,1,2,50,-0.2,0),
        (0.5,1,2,200,1,2,50,1.2,1),
        (0.5,1,2,200,1,2,50,1.2,0),
        (0.3333,500.1,200.2,34.1,501.9,210.4,36.6,0.222,1),
        (0.75,-513.5,378.1,49.3,-510.4,390.0,59.6,0.75,0),
        (0.25,0,0,0,0,0,0,0.5,1),
        (1.8,9000.25,-200.5,6.5,8000.75,400.5,9.2,0.1,0),
    ]
    inp="".join(" ".join(str(v) for v in line)+"\n" for line in cases)
    with tempfile.TemporaryDirectory(prefix="p7-puffct2-original-") as folder:
        path=Path(folder)
        f=path/"original_puffct2.f"
        f.write_text(routine+driver,encoding="latin-1")
        exe=path/"puffct2_vendor"
        subprocess.run(["gfortran","-O0","-ffixed-line-length-none",
                        str(f),"-o",str(exe)],
                       capture_output=True,text=True,check=True)
        def invoke(binary):
            result=subprocess.run([str(binary)],input=inp,text=True,
                                  capture_output=True,check=True)
            return [row.strip().upper().split() for row in result.stdout.splitlines()]
        vendor=invoke(exe)
        native=invoke(args.probe)
    if len(vendor)!=len(cases) or len(native)!=len(cases):
        raise AssertionError("PUFFCT2 oracle/native row-count mismatch")
    for i,(v,n) in enumerate(zip(vendor,native),start=1):
        if v!=n:
            raise AssertionError(
                f"PUFFCT2_VENDOR_FIRST_DIFF_CASE={i} inputs={cases[i-1]}"
                f" original_float32_words={v} native_float32_words={n}")
    print("P7_ORIGINAL_PUFFCT2_REAL4=PASS "
          f"CASES={len(cases)} WORDS={len(cases)*3} BITWISE_EXACT=YES "
          "ORIGINAL_SOURCE=L21035-21096 MCTADJ2_CORE_ONLY=YES "
          "NATIVE_CTADJ2_STATE_INTEGRATION=NOT_YET_ACCEPTED")


if __name__=="__main__":
    main()

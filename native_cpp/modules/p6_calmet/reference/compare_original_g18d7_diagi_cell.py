#!/usr/bin/env python3
"""G18D7 DIAGI site-grid index: actual CALMET Fortran REAL*4 source parity.

Compile unmodified original DIAGI assignments and DIAGNO clamp lines
directly extracted from calmet.for, then compare indexed cell ordinals
to the production C++ helper. Fixture and oracle are independent.
"""
import argparse
import json
import pathlib
import struct
import subprocess
import tempfile


def vendor_lines(path):
    content=path.read_text(encoding="latin-1").splitlines()
    dia=content.index(next(line for line in content if
        line.lower().startswith("      subroutine diagi(")))
    assignments=[]
    for desired in ("ist(i)=xssta(i) / dx + 1",
                    "jst(i)=yssta(i) / dy + 1"):
        matched=[line for line in content[dia:dia+850]
                 if line.strip().lower()==desired]
        if len(matched)!=1:
            raise RuntimeError("DIAGI literal source missing or nonunique "+desired)
        assignments.append(matched[0])
    # DIAGNO called STHEOR after these *source* clamps.
    wanted=("ig = max0(1,ig)","ig = min0(ig,nx)",
            "jg = max0(1,jg)","jg = min0(jg,ny)")
    clamps=[]
    for i in range(5000,min(10000,len(content)-4)):
        block=content[i:i+4]
        if tuple(line.strip().lower() for line in block)==wanted:
            clamps=block
            break
    if not clamps:
        raise RuntimeError("Original STHEOR DIAGNO station cell clamp not found")
    # Same dgrid controls dx/dy in the original DIAGI.
    source="""      program g18d7_diagi
      implicit none
      integer ncases,n, i, nx,ny,ig,jg,ist(1),jst(1)
      real dx,dy,xssta(1),yssta(1)
      read(*,*) ncases
      i=1
      do n=1,ncases
         read(*,*) nx,ny,dx,xssta(1),yssta(1)
         dy=dx
"""
    source+="\n".join(assignments)+"\n"
    source+="""         ig=ist(i)
         jg=jst(i)
"""
    source+="\n".join(clamps)+"\n"
    source+="""         write(*,'(I0,1X,I0)') ig,jg
      enddo
      end
"""
    return source


def prev_float32(x):
    raw=struct.unpack("<I",struct.pack("<f",float(x)))[0]
    if raw==0:
        return 0.0
    return struct.unpack("<f",struct.pack("<I",raw-1))[0]


def cases():
    seen=set()
    for nx,ny in ((12,12),(17,13),(64,64)):
        for spacing in (100.,1000.,5000.,10000.,20000.):
            for k in (0,1,2,nx//2,nx-2):
                x_options=(0.,prev_float32((k+1)*spacing),
                           k*spacing,(k+0.5)*spacing)
                y_options=(0.,prev_float32(spacing),
                           min(2.25*spacing,(ny-0.5)*spacing))
                for x in x_options:
                    for y in y_options:
                        if not (0.<=x<nx*spacing and 0.<=y<ny*spacing):
                            continue
                        record=(nx,ny,spacing,x,y)
                        if record not in seen:
                            seen.add(record)
                            yield record


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--vendor",type=pathlib.Path,required=True)
    p.add_argument("--cpp",type=pathlib.Path,required=True)
    p.add_argument("--gfortran",default="gfortran")
    p.add_argument("--out",type=pathlib.Path,required=True)
    a=p.parse_args()
    samples=list(cases())
    inp=str(len(samples))+"\n"+"".join(
        f"{nx} {ny} {dx:.8f} {x:.12f} {y:.12f}\n"
        for nx,ny,dx,x,y in samples)
    with tempfile.TemporaryDirectory(prefix="g18d7-vendor-diagi-") as d:
        root=pathlib.Path(d);src=root/"original_diagi.f";exe=root/"original_diagi"
        src.write_text(vendor_lines(a.vendor),encoding="ascii")
        subprocess.run([a.gfortran,"-O0","-ffixed-line-length-none",
                        str(src),"-o",str(exe)],
                       check=True,capture_output=True,text=True)
        def run(executable):
            result=subprocess.run([str(executable)],input=inp,text=True,
                                  capture_output=True,check=True)
            pairs=[tuple(map(int,line.split())) for line in result.stdout.splitlines()]
            if len(pairs)!=len(samples) or any(len(p)!=2 for p in pairs):
                raise AssertionError("G18D7 oracle and C++ record count not equal")
            return pairs
        vendor=run(exe)
        cpp=run(a.cpp)
    for i,(reference,native) in enumerate(zip(vendor,cpp)):
        if reference!=native:
            raise AssertionError(
                f"G18D7 literal CALMET DIAGI index mismatch case={i} "
                f"geom={samples[i]} vendor={reference} cpp={native}")
    report={"status":"PASS_G18D7_LITERAL_VENDOR_DIAGI_REAL4_STHEOR_CELL",
            "cases":len(samples),"tolerance":"exact ordinal equality",
            "vendor_source":"literal DIAGI IST/JST and DIAGNO STHEOR clamps",
            "scope":"in-domain surface stations, 3 grid sizes and 5 DGRID resolutions",
            "not_accepted":"17-stage multi-site production physical acceptance"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(report["status"],report["cases"])


if __name__=="__main__":
    main()

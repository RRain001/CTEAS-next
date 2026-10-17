#!/usr/bin/env python3
"""Independent original-CALMET TERSET vs C++ numerical parity.

Compiles the exact original TERSET subroutine *extracted, not modified* from
the vendor CALMET 6.5.0 source, with its unmodified PARAMS.MET and GRID.MET.
The reference is not an independently rewritten Python algorithm.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,random,subprocess
from pathlib import Path

DRIVER="""      program testter
      include 'params.met'
      include 'grid.met'
      real topo(mxnx,mxny),hmax(mxnx,mxny),terrad
      character*256 fin,fout,arg
      call get_command_argument(1,fin)
      call get_command_argument(2,fout)
      call get_command_argument(3,arg)
      read(arg,*) terrad
      nx=50
      ny=50
      nz=9
      dx=100.0
      dy=100.0
      open(10,file=trim(fin),status='old')
      do j=1,ny
        read(10,*) (topo(i,j),i=1,nx)
      enddo
      close(10)
      do j=1,ny
        do i=1,nx
          disthmax(i,j)=0.0
          disthmin(i,j)=0.0
        enddo
      enddo
      call terset(topo,hmax,terrad)
      open(11,file=trim(fout),status='replace')
      do j=1,ny
        do i=1,nx
          write(11,'(2(I4,1X),4(ES22.13E3,1X))')
     1       i,j,hmax(i,j),hmin(i,j),disthmax(i,j),
     2       disthmin(i,j)
        enddo
      enddo
      close(11)
      end
"""

def sha(path:Path):return hashlib.sha256(path.read_bytes()).hexdigest()
def external(args,timeout=90):
    p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"command rc={p.returncode} {args} stderr={p.stderr[-3000:]} stdout={p.stdout[-1000:]}")
    return p

def extract_terset(source:Path,dest:Path):
    lines=source.read_text().splitlines(keepends=True)
    starts=[i for i,l in enumerate(lines) if l.lower().startswith("      subroutine terset(")]
    if len(starts)!=1:raise RuntimeError("Original CALMET TERSET declaration not uniquely found")
    start=starts[0]
    end=next((i for i in range(start+1,len(lines)) if lines[i].lower().startswith("      subroutine topof2(")),None)
    if end is None or not 80<=end-start<=140:raise RuntimeError("Unexpected original TERSET code boundaries")
    original="".join(lines[start:end])
    dest.write_text(original)
    if "include 'params.met'" not in original or "include 'grid.met'" not in original:
        raise RuntimeError("Missing expected original include declarations")
    return {"original_calmet_file_sha256":sha(source),
            "exact_extracted_terset_sha256":sha(dest),
            "original_terset_first_line":start+1,
            "original_terset_after_last_line":end}

def real_terrain(path:Path):
    lines=path.read_text().splitlines()
    marker=lambda s:[i for i,line in enumerate(lines) if s in line]
    a,b=marker("TERRAIN heights"),marker("gridded z0 field")
    if len(a)!=1 or len(b)!=1 or b[0]<=a[0]:
        raise ValueError("GEO.DAT terrain/z0 boundaries missing")
    heights=[float(s) for row in lines[a[0]+1:b[0]] for s in row.replace(","," ").split()]
    if len(heights)!=2500 or not all(math.isfinite(x) for x in heights):
        raise ValueError(f"unexpected P3 real terrain count {len(heights)}")
    # GEO.DAT in north-to-south order, Fortran internal (i,j) south-to-north.
    return [heights[(49-j)*50+i] for j in range(50) for i in range(50)]

def grids(actual):
    yield "flat_15km",[57.0]*2500,15.0
    isolated=[67.0]*2500;isolated[0]=1024.0;isolated[-1]=-42.0
    yield "single_extrema_15km",isolated,15.0
    yield "single_extrema_0p12km",isolated,0.12
    vary=[float(150+13*math.sin(i*.19)+12*math.cos(j*.14)+4*((i+j)%7)) for j in range(50) for i in range(50)]
    yield "spatially_varying_1km",vary,1.0
    yield "spatially_varying_15km",vary,15.0
    yield "actual_original_p3_terrain_15km",actual,15.0

def save_height(path:Path,values):
    with path.open("w") as f:
        for j in range(50):
            f.write(" ".join(f"{v:.8f}" for v in values[j*50:(j+1)*50])+"\n")

def compare(fortran_file:Path,cpp_file:Path):
    a=[list(map(float,line.split())) for line in fortran_file.read_text().splitlines()]
    with cpp_file.open(newline="") as f:b=list(csv.DictReader(f))
    if len(a)!=2500 or len(b)!=2500:raise ValueError("expected 2500 original and C++ TERSET rows")
    max_abs={key:0.0 for key in ["hmax_m","hmin_m","disthmax_m","disthmin_m"]}
    worse=[]
    tol={"hmax_m":0.00002,"hmin_m":0.00002,
         "disthmax_m":0.01,"disthmin_m":0.01}
    for n,(orig,out) in enumerate(zip(a,b)):
        if len(orig)!=6 or tuple(map(int,orig[:2]))!=(n%50+1,n//50+1):
            raise ValueError("Fortran original terrain index mismatch")
        if (int(out["i"]),int(out["j"]))!=(n%50+1,n//50+1):
            raise ValueError("C++ terrain index mismatch")
        for m,key in enumerate(max_abs,2):
            ref,candidate=orig[m],float(out[key])
            if not math.isfinite(ref) or not math.isfinite(candidate):
                raise ValueError("nonfinite terrain compare field")
            err=abs(ref-candidate)
            max_abs[key]=max(max_abs[key],err)
            if err>tol[key] and len(worse)<20:
                worse.append({"i":n%50+1,"j":n//50+1,"field":key,
                              "original":ref,"cpp":candidate,"abs_error":err})
    return {"status":"PASS" if not worse else "FAIL",
            "compared_fields":10000,
            "max_abs_error":max_abs,"predeclared_tolerance":tol,
            "first_mismatches":worse}

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--vendor",required=True,type=Path)
    pa.add_argument("--geo",required=True,type=Path)
    pa.add_argument("--cpp",required=True,type=Path)
    pa.add_argument("--output",required=True,type=Path)
    args=pa.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    original_source=args.vendor/"calmet.for"
    orig=args.output/"original_terset.for"
    source_provenance=extract_terset(original_source,orig)
    drive=args.output/"terset_fortran_driver.for"
    drive.write_text(DRIVER)
    binary=args.output/"terset_original"
    external(["gfortran","-O0","-std=legacy","-ffixed-line-length-none",
              "-fno-automatic","-I"+str(args.vendor),orig,drive,"-o",binary],timeout=70)
    result={"reference_source":source_provenance,"compiled_driver_sha256":sha(drive),
            "p3_geo_sha256":sha(args.geo),"cases":{},"total_compared_fields":0,
            "scope":"Original TERSET subroutine only; not full CALMET wind, Froude or slope adjustment"}
    for key,terrain,radius in grids(real_terrain(args.geo)):
        inp=args.output/(key+".txt")
        ref=args.output/(key+".original.txt")
        got=args.output/(key+".cpp.csv")
        save_height(inp,terrain)
        external([binary,inp,ref,str(radius)])
        external([args.cpp,inp,got,"100",str(radius)])
        comparison=compare(ref,got)
        result["cases"][key]={
            "radius_km":radius,
            "input_sha256":sha(inp),
            "original_output_sha256":sha(ref),
            "cpp_output_sha256":sha(got),**comparison}
        result["total_compared_fields"]+=comparison["compared_fields"]
    result["status"]="PASS_ORIGINAL_CALMET_TERSET_FORTRAN_PARITY" if all(
        c["status"]=="PASS" for c in result["cases"].values()) else "FAIL"
    (args.output/"p6c-terset-parity.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if result["status"]!="PASS_ORIGINAL_CALMET_TERSET_FORTRAN_PARITY":
        raise SystemExit(1)
if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""G27: unmodified vendor CALMET SETCOM original 2US NEARU parity.

Inputs are true G19 source-format synthetic GEO + station coordinates
exported BEFORE candidate map calculation. Original SETCOM L29718-29896
computes its own NEARU; compares every 12x12 gridpoint to G18B3
source-deck C++ map. Does not certify MIXHT/COMP/P6F or all 45 fields.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path

from compare_original_similt_profile import VENDOR_BLOB

ROOT = Path(__file__).resolve().parents[4]
VENDOR = ROOT / "engine/vendor/src/CALMET_v6.5.0_L150223"

DRIVER = """      program g27_source_setcom_nearu
      include 'params.met'
      include 'gen.met'
      include 'grid.met'
      include 'met1.met'
      integer nr,nc,layer,ns,ordinal
      character*256 input
      call get_command_argument(1,input)
      open(10,file=trim(input),status='old')
      read(10,*)nr,nc,layer,ns,dgrid
      if(nr.ne.12.or.nc.ne.12.or.layer.ne.9.or.
     1 ns.ne.2.or.dgrid.ne.10000.)stop 81
      nx=nr
      ny=nc
      nz=layer
      nusta=ns
      nssta=0
      npsta=0
      irtype=0
      read(10,*)(zface(k),k=1,nz+1)
      do k=1,nusta
        read(10,*)ordinal,xusta(k),yusta(k)
        if(ordinal.le.0)stop 82
      enddo
      close(10)
      call setcom(.false.)
      do j=1,ny
        do i=1,nx
          write(*,'(A,3(1X,I5))') 'NEARU',i,j,nearu(i,j)
        enddo
      enddo
      end
c --- Original OUT is only called if LDB=true (explicitly false).
      subroutine out(dummy,ival,idev,icode,ldate,message,nx,ny)
      real dummy(*)
      integer ival(*),idev,icode,nx,ny
      logical ldate
      character*(*) message
      stop 97
      end
"""


def original_setcom(work: Path) -> tuple[Path, dict]:
    src=VENDOR/"calmet.for"
    b=src.read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
    if blob!=VENDOR_BLOB:
        raise RuntimeError("G27 pinned original vendor calmet.for changed")
    lines=b.decode().splitlines(keepends=True)
    start=[i for i,x in enumerate(lines)
           if x.lower().startswith("      subroutine setcom(")]
    end=[i for i,x in enumerate(lines)
         if x.lower().startswith("      subroutine setup(")]
    if len(start)!=1 or len(end)!=1 or start[0]+1!=29718 or (
        end[0]+1!=29898 or end[0]<=start[0]):
        raise RuntimeError("G27 original SETCOM literal subroutine boundary changed")
    dst=work/"literal_original_setcom.for"
    dst.write_text("".join(lines[start[0]:end[0]]))
    return dst,{
        "vendor_blob":blob,
        "literal_setcom_lines":[start[0]+1,end[0]-1],
        "literal_setcom_sha256":hashlib.sha256(dst.read_bytes()).hexdigest(),
    }


def source_guard(path: Path) -> dict:
    rows=path.read_text().splitlines()
    if len(rows)!=4:
        raise ValueError("G27 SETCOM original source input malformed")
    dims=rows[0].split()
    if len(dims)!=5:
        raise ValueError("G27 source dimension count malformed")
    nx,ny,nz,nus=[int(x) for x in dims[:4]]
    grid=float(dims[4])
    if (nx,ny,nz,nus)!=(12,12,9,2) or grid!=10000.:
        raise ValueError("G27 unsupported original source domain")
    z=[float(x) for x in rows[1].split()]
    if len(z)!=10 or any(not math.isfinite(x) for x in z) or (
        any(x>=y for x,y in zip(z,z[1:]))):
        raise ValueError("G27 source ZFACE invalid")
    stations=[]
    for row in rows[2:]:
        v=row.split()
        if len(v)!=3:raise ValueError("G27 source upper station fields missing")
        station_id=int(v[0])
        x,y=map(float,v[1:])
        if station_id<=0 or not math.isfinite(x) or not math.isfinite(y) or (
            x<0 or y<0 or x>=nx*grid or y>=ny*grid):
            raise ValueError("G27 SETCOM true source station outside selected domain")
        stations.append((station_id,x,y))
    if stations[0][0]==stations[1][0]:
        raise ValueError("G27 source upper IDs duplicated")
    return {"nx":nx,"ny":ny,"zfaces_m":z,"upper_stations":stations}


def candidates(path:Path,source:dict)->dict:
    with path.open(newline="") as f:
        data=list(csv.DictReader(f))
    if len(data)!=144:
        raise ValueError("G27 C++ NEARU 144 cell output absent")
    result={}
    for row in data:
        i,j,ordinal,id_=tuple(int(row[k]) for k in (
            "i","j","upper_ordinal","upper_station_id"))
        key=(i,j)
        if key in result or not 1<=i<=12 or not 1<=j<=12 or not 1<=ordinal<=2:
            raise ValueError("G27 native duplicate or invalid grid/station choice")
        if id_!=source["upper_stations"][ordinal-1][0]:
            raise ValueError("G27 C++ upper station ID/ordinal mismatch")
        result[key]=ordinal
    return result


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-prefix",type=Path,required=True)
    parser.add_argument("--mode",choices=("Debug","Release"),required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    src=source_guard(Path(str(args.source_prefix)+".source.input"))
    cpp=candidates(Path(str(args.source_prefix)+".native.csv"),src)
    with tempfile.TemporaryDirectory(prefix="p6g-g27-literal-setcom-") as tmp:
        root=Path(tmp)
        literal,meta=original_setcom(root)
        driver=root/"vendor_nearu_driver.for"
        driver.write_text(DRIVER)
        exe=root/"original_setcom"
        opt="-O0" if args.mode=="Debug" else "-O2"
        comp=subprocess.run([
            "gfortran",opt,"-std=legacy","-fno-automatic",
            "-ffixed-line-length-none","-fallow-argument-mismatch",
            "-I"+str(VENDOR),str(literal),str(driver),"-o",str(exe)
        ],capture_output=True,text=True)
        if comp.returncode:
            raise RuntimeError("G27 unmodified SETCOM build failed: "+comp.stderr[-5000:])
        original=subprocess.run([
            str(exe),str(args.source_prefix)+".source.input"
        ],capture_output=True,text=True)
        if original.returncode:
            raise RuntimeError(
                "G27 original SETCOM runtime failed: "+original.stderr[-1500:]+
                original.stdout[-1500:])
    ref={}
    for line in original.stdout.splitlines():
        if not line.startswith("NEARU"):continue
        v=line.split()
        if len(v)!=4:raise ValueError("G27 original Fortran NEARU malformed")
        i,j,station=[int(x) for x in v[1:]]
        key=(i,j)
        if key in ref or not (1<=i<=12 and 1<=j<=12 and 1<=station<=2):
            raise ValueError("G27 original Fortran NEARU identity malformed")
        ref[key]=station
    if len(ref)!=144 or set(cpp)!=set(ref):
        raise AssertionError("G27 literal original SETCOM did not calculate all 144 sites")
    errors=[(i,j,ref[i,j],cpp[i,j]) for i,j in sorted(ref)
            if ref[i,j]!=cpp[i,j]]
    counts={str(i):sum(v==i for v in ref.values()) for i in (1,2)}
    evidence={
        "scope":"original CALMET 6.5.0 literal SETCOM NEARU 2 upper sites",
        "input":"actual G19 original-format synthetic GEO/UP station positions",
        "original_source":meta,
        "mode":args.mode,
        "source":src,
        "grid_cells":len(ref),"original_station_cell_counts":counts,
        "original_2_station_branches_visited":all(int(x)>0 for x in counts.values()),
        "differences":errors[:30],
        "all_144_exact":not errors,
        "full_multistation_comp_original":False,
        "full_multistation_45_field":False,
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(evidence,indent=2)+"\n")
    if errors or not evidence["original_2_station_branches_visited"]:
        raise AssertionError(
            f"G27 original 2US SETCOM mismatch or trivial one-station: {errors[:10]} "+
            str(counts))
    print(f"PASS_P6G_G27_LITERAL_ORIGINAL_SETCOM_NEARU mode={args.mode} "
          f"cells={len(ref)} original_station_counts={counts} "
          "MAX_ORDINAL_DIFFERENCE=0 ORIGINAL_MULTISTATION_COMP=NOT_ACCEPTED")


if __name__=="__main__":
    main()

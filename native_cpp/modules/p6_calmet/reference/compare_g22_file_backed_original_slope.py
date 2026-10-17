#!/usr/bin/env python3
"""G22 literal original CALMET TERSET+SLOPE parity from file-derived HEATFX/ELUSTR.

Selected one-hour 2SS+2US source formatted SYNTHETIC weather, NOT original
Fortran complete multistation preprocess or 45-field acceptance. Original
SLOPE receives real G22 after-ELUSTR QH and second-SURFVAR TEMP2D, plus the
native FRADJ output; the unmodified vendor Fortran calculates SLOPE U/V.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import tempfile
from pathlib import Path

from compare_g11_original_terrain_10km import VENDOR, original_chunks, rows_from
from compare_g21_file_backed_original_fradj import candidate_rows

DRIVER = """      program g22_original_source_slope
      include 'params.met'
      include 'grid.met'
      include 'metgrd.met'
      include 'geo.met'
      include 'd6.met'
      real topo(mxnx,mxny),highest(mxnx,mxny)
      real sfct(mxnx,mxny)
      real u(mxnx,mxny,mxnz),v(mxnx,mxny,mxnz)
      real du(mxnx,mxny,mxnz),dv(mxnx,mxny,mxnz)
      real terrad,tinf
      integer nr,nc,nl,iw1,iw2,mode
      open(unit=10,file='g22_stage.dat',status='old')
      read(10,*) nr,nc,nl,dx,dy,terrad,tinf,iw1,iw2,mode
      if(nr.ne.12.or.nc.ne.12.or.nl.ne.9) stop 91
      if(dx.ne.10000..or.dy.ne.10000..or.mode.ne.-1) stop 92
      nx=nr
      ny=nc
      nz=nl
      iwr=0
      isurft=mode
      iwat1=iw1
      iwat2=iw2
      read(10,*) (zface(k),k=1,nz+1)
      do k=1,nz
        dz(k)=zface(k+1)-zface(k)
      enddo
      do j=1,ny
        do i=1,nx
          read(10,*) topo(i,j),sfct(i,j),qh(i,j),ilandu(i,j)
        enddo
      enddo
      do k=1,nz
        do j=1,ny
          do i=1,nx
            read(10,*) u(i,j,k),v(i,j,k)
          enddo
        enddo
      enddo
      close(10)
      call terset(topo,highest,terrad)
      call slope(du,dv,topo,isurft,tinf,sfct,highest)
      do k=1,nz
        do j=1,ny
          do i=1,nx
            u(i,j,k)=u(i,j,k)+du(i,j,k)
            v(i,j,k)=v(i,j,k)+dv(i,j,k)
            write(*,'(A,3(1X,I3),2(1X,ES17.9))')
     1           'GRID',i,j,k,u(i,j,k),v(i,j,k)
          enddo
        enddo
      enddo
      end
      subroutine xmit(n,val,a)
      real val,a(*)
      do i=1,iabs(n)
        a(i)=val
      enddo
      end
      subroutine wndlpt(a)
      real a(*)
      return
      end
"""


def stage_input(path: Path) -> tuple[dict, list[tuple[float, float]]]:
    lines=path.read_text().splitlines()
    if len(lines)!=2+144+1296:
        raise ValueError("G22 original SLOPE source file shape invalid")
    tokens=lines[0].split()
    if len(tokens)!=10:
        raise ValueError("G22 original SLOPE scalar controls missing")
    nx,ny,nz=map(int,tokens[:3])
    dx,dy,terrad,t0=map(float,tokens[3:7])
    iw1,iw2,isurft=map(int,tokens[7:])
    if (nx,ny,nz)!=(12,12,9) or (dx,dy)!=(10000.,10000.) or (
        isurft!=-1 or iw1>iw2 or terrad<0
    ) or not all(map(math.isfinite,(terrad,t0))):
        raise ValueError("G22 original SLOPE unsupported READCF")
    zface=[float(v) for v in lines[1].split()]
    if len(zface)!=10 or any(b<=a for a,b in zip(zface,zface[1:])) or (
        not all(map(math.isfinite,zface))
    ):
        raise ValueError("G22 original ZFACE invalid")
    heat=[]
    for line in lines[2:146]:
        values=line.split()
        if len(values)!=4:
            raise ValueError("G22 GEO/QH/TEMP2D/landuse missing")
        topo,temp,qh=map(float,values[:3])
        land=int(values[3])
        if not all(map(math.isfinite,(topo,temp,qh))) or not 180<=temp<=350 or (
            iw1<=land<=iw2
        ):
            raise ValueError("G22 original all-land temperature/heat branch invalid")
        heat.append(qh)
    first=[]
    for line in lines[146:]:
        uv=tuple(float(v) for v in line.split())
        if len(uv)!=2 or not all(map(math.isfinite,uv)):
            raise ValueError("G22 FRADJ-derived source wind input invalid")
        first.append(uv)
    return {"cells":1296,"source_terrad_km":terrad,
            "min_qh_wm2":min(heat),"max_qh_wm2":max(heat)},first


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("Debug","Release"),required=True)
    parser.add_argument("--source-stage",type=Path,required=True)
    parser.add_argument("--candidate",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--require-nontrivial",action="store_true")
    args=parser.parse_args()
    metadata,fradj_wind=stage_input(args.source_stage)
    with tempfile.TemporaryDirectory(prefix="g22-original-vendor-slope-") as tmp:
        root=Path(tmp)
        chunks,sha=original_chunks(root)
        (root/"g22_stage.dat").write_bytes(args.source_stage.read_bytes())
        (root/"g22_original.f").write_text(DRIVER)
        exe=root/"vendor_slope"
        opt="-O0" if args.mode=="Debug" else "-O2"
        subprocess.run(["gfortran",opt,"-std=legacy","-fno-automatic",
                        "-ffixed-line-length-none","-I"+str(VENDOR),
                        str(chunks[0]),str(chunks[2]),str(root/"g22_original.f"),
                        "-o",str(exe)],check=True)
        res=subprocess.run([str(exe)],cwd=root,capture_output=True,
                           text=True,check=True)
        original=rows_from(res.stdout)
    candidate=candidate_rows(args.candidate)
    if original.keys()!=candidate.keys():
        raise ValueError("G22 original Fortran/native SLOPE coordinates differ")
    maximum=0.
    failures=[]
    changed=0
    for key in sorted(original):
        i,j,k=key
        pos=(k-1)*144+(j-1)*12+(i-1)
        for part,reference,actual,first in zip(
                ("U","V"),original[key],candidate[key],fradj_wind[pos]):
            error=abs(reference-actual)
            maximum=max(maximum,error)
            if error>2e-4:
                failures.append((key,part,reference,actual,error))
            if abs(actual-first)>1e-5:
                changed+=1
    if args.require_nontrivial and changed==0:
        raise AssertionError(
            "G22 steep-source SLOPE returned identity U/V; "
            "literal Fortran parity must exercise nonzero correction")
    evidence={"scope":"source 2SS+2US G22 after-ELUSTR QH and SLOPE first hour",
              "source":"synthetic weather in original-format files",
              "fortran_sha256":sha,"mode":args.mode,
              "compared_u_v":len(original)*2,
              "slope_modified_u_v":changed,
              "nontrivial_correction_required":args.require_nontrivial,
              "max_abs_error_mps":maximum,
              "unchanged_g11_tolerance_mps":2e-4,
              "qh_min_max_wm2":[metadata["min_qh_wm2"],metadata["max_qh_wm2"]],
              "failed_components":failures[:10],
              "upstream_original_Fortran_HEATFX_ELUSTR_parity":False,
              "full_45_field_original_multistation_parity":False}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(evidence,indent=2)+"\n")
    if failures:
        raise AssertionError(
            f"G22 SLOPE literal Fortran mismatch count={len(failures)} "
            f"max_abs={maximum:.9g} samples={failures[:3]}")
    print("PASS_P6G_G22_LITERAL_ORIGINAL_SLOPE "
          f"mode={args.mode} uv={2*len(original)} "
          f"slope_changed_uv={changed} max_abs_delta={maximum:.9g} "
          f"vendor_sha256={sha} complete_model=NOT_ACCEPTED")


if __name__=="__main__":
    main()

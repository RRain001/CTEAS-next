"""#54 forensic-only original pixel lineage probe, never a scientific solver.

Make a scratch diagnostic copy of pinned original TERREL FORTRAN (original
source/normal verifier untouched), trace original LOADTIFF -> GLOBE -> CELLIND
pixel coordinates/indices and contrast with the native GDAL/PROJ algorithm.
Only bounded aggregate diagnostics are written to Actions metadata.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json
import math
import shutil

class CoordinateProbeError(ValueError):
    pass

OPEN_ANCHOR="      open(unit=500,file='numpts.dat')"
POINT_ANCHOR="            call SAVEELEV(xdist,ydist,dels,elev)"
TRACE_OPEN="      open(unit=501,file='p1_original_coords.txt',status='new')"
TRACE_POINT="""            call cellind(xdist,ydist,dels,ixprobe,iyprobe,
     &                       ixpprobe,iypprobe)
            write(501,*) i,j,ixprobe,iyprobe,xdist,ydist"""
TRACE_CLOSE="      close(501)"


def diagnostic_copy(original:Path,dest:Path)->None:
    if dest.exists() or dest.is_symlink():
        raise CoordinateProbeError("diagnostic source must not overwrite evidence")
    content=original.read_text(encoding="latin-1")
    if content.count(OPEN_ANCHOR)!=1 or content.count(POINT_ANCHOR)!=1:
        raise CoordinateProbeError("historical original pixel-hook anchors changed")
    if TRACE_OPEN in content or TRACE_POINT in content:
        raise CoordinateProbeError("original source is already instrumented")
    content=content.replace(OPEN_ANCHOR,OPEN_ANCHOR+"\n"+TRACE_OPEN,1)
    content=content.replace(POINT_ANCHOR,TRACE_POINT+"\n"+POINT_ANCHOR,1)
    # Unit 501 is automatically closed when original exits. Any duplicate
    # pixel hooks, missing original call or source modification fail closed.
    if content.count(POINT_ANCHOR)!=1 or content.count(TRACE_OPEN)!=1:
        raise CoordinateProbeError("invalid forensic TERREL source hook")
    dest.write_text(content,encoding="latin-1")


def _cell_index(east_m:float,north_m:float,grid:dict)->tuple[int,int]:
    """Mirror native C++ REAL*4 xllm/scale/CELLIND, not the original trace."""
    import numpy as np
    f=np.float32
    xll=f(f(float(grid["xrefkm"]))*f(1000.0))
    yll=f(f(float(grid["yrefkm"]))*f(1000.0))
    scale=f(f(1.0)/f(float(grid["dgridkm"])*1000.0))
    xi=f(f(f(east_m)-xll)*scale)
    yi=f(f(f(north_m)-yll)*scale)
    # Native truncation toward zero plus +1 for nonnegative indices.
    def idx(a,n):
        if not math.isfinite(float(a)) or a < -1 or a>=n:
            return 0
        out=int(a)+(1 if a>=0 else 0)
        return out if 1<=out<=n else 0
    return idx(xi,grid["nx"]),idx(yi,grid["ny"])


def diagnose_trace(*,trace:Path,selected_tif:Path,grid:dict,
                   max_records:int=250_000)->dict:
    import numpy as np
    import rasterio
    from pyproj import Transformer

    if max_records<=0 or max_records>250_000:
        raise CoordinateProbeError("invalid trace record limit")
    zone=grid["zone"]
    if type(zone) is not int or not 1<=zone<=60 or grid["hemisphere"] not in ("N","S"):
        raise CoordinateProbeError("invalid projection reference")
    with rasterio.open(selected_tif) as source:
        if source.crs.to_epsg()!=4326:
            raise CoordinateProbeError("trace requires WGS84 GeoTIFF")
        tf=source.transform
        if tf.b != 0 or tf.d != 0:
            raise CoordinateProbeError("trace requires north-up source")
        xorg=np.float32(tf.c+tf.a*0.5)
        yorg=np.float32(tf.f+tf.e*0.5)
        ddx=np.float32(tf.a)
        ddy=np.float32(tf.e)
        width,height=source.width,source.height
    epsg=(32700 if grid["hemisphere"]=="S" else 32600)+zone
    proj=Transformer.from_crs("EPSG:4326",f"EPSG:{epsg}",always_xy=True)
    raw_factor=float(np.float32(0.001))
    total=coordinate_disagreements=cell_disagreements=0
    all_offsets_x=[];all_offsets_y=[]
    grid_shift=Counter()
    first_disagree=[]
    max_e=max_n=0.
    max_pixel_err=0.
    with trace.open(encoding="utf-8",errors="strict") as f:
        for line in f:
            if not line.strip():
                continue
            total+=1
            if total>max_records:
                raise CoordinateProbeError("original pixel trace exceeds bounded rows")
            parts=line.split()
            if len(parts)!=6:
                raise CoordinateProbeError("unexpected original pixel trace shape")
            try:
                i,j,ix,iy=map(int,parts[:4])
                old_x,old_y=map(lambda v:float(v.replace("D","E")),parts[4:])
            except (ValueError,OverflowError) as exc:
                raise CoordinateProbeError("malformed original pixel coordinates") from exc
            if not (1<=i<=width and 1<=j<=height) or not all(
                  math.isfinite(v) for v in (old_x,old_y)):
                raise CoordinateProbeError("forensic index/coordinate not finite or out of bounds")
            lon=float(np.float32(xorg+np.float32(i-1)*ddx))
            lat=float(np.float32(yorg+np.float32(j-1)*ddy))
            xm,ym=proj.transform(lon,lat)
            # Original native path: projected metre * REAL*4 0.001,
            # rounded to REAL*4 kilometres, then * REAL*4 1000.
            native_x=float(np.float32(np.float32(xm*raw_factor)*np.float32(1000.0)))
            native_y=float(np.float32(np.float32(ym*raw_factor)*np.float32(1000.0)))
            dx=old_x-native_x;dy=old_y-native_y
            max_e=max(max_e,abs(dx));max_n=max(max_n,abs(dy))
            if dx or dy:coordinate_disagreements+=1
            native_i,native_j=_cell_index(native_x,native_y,grid)
            if (ix,iy)!=(native_i,native_j):
                cell_disagreements+=1
                diffx=ix-native_i;diffy=iy-native_j
                grid_shift[("E_W" if diffx else "NO_E_W",
                            "N_S" if diffy else "NO_N_S")]+=1
                if len(first_disagree)<20:
                    first_disagree.append({
                      "original_grid_indices":[ix,iy],
                      "proj_proxy_grid_indices":[native_i,native_j],
                      "original_minus_proj_east_m":round(dx,6),
                      "original_minus_proj_north_m":round(dy,6),
                    })
            all_offsets_x.append(abs(dx));all_offsets_y.append(abs(dy))
    if total==0:
        raise CoordinateProbeError("empty independent original pixel trace")
    def percentile(vals,p):
        vals=sorted(vals)
        return round(vals[min(len(vals)-1,math.floor((len(vals)-1)*p))],6)
    return {
      "schema_version":"p1-original-pixel-coordinate-proxy-v1",
      "status":"DIAGNOSTIC_ONLY_NOT_SCIENCE_ACCEPTED",
      "trace_records":total,
      "coordinate_records_differ_from_proj_proxy":coordinate_disagreements,
      "original_vs_proj_proxy_cell_mismatches":cell_disagreements,
      "max_abs_easting_difference_m":round(max_e,6),
      "max_abs_northing_difference_m":round(max_n,6),
      "p95_abs_easting_difference_m":percentile(all_offsets_x,.95),
      "p95_abs_northing_difference_m":percentile(all_offsets_y,.95),
      "cell_mismatch_axes":{"/".join(k):v for k,v in grid_shift.items()},
      "first20_differences":first_disagree,
      "original_source_used":"CTEAS_PINNED_TERREL_SCRATCH_INSTRUMENTED_COPY",
      "native_comparison_basis":"GDAL_PROJ_PYPROJ_FLOAT32_PROXY_NOT_INSTRUMENTED_CXX",
      "pixel_trace_artifact_uploaded":False,
      "science_acceptance":"NOT_ACCEPTED"
    }


def execute_original_diagnostic(*,checkout:Path,vendor:Path,selected:Path,
                                grid:dict,workspace:Path)->dict:
    """A separate scratch copy; must not change original production evidence."""
    import sys
    from scripts.s2g.p1_original_actions_replay import _invoke,prepare_control
    forensic=workspace/"forensic_pixel_probe"
    forensic.mkdir(exist_ok=False)
    patched=forensic/"terrel_forensic_only.for"
    diagnostic_copy(vendor/"terrel.for",patched)
    aliases=workspace/"original_build/aliases"
    if not aliases.is_dir():
        raise CoordinateProbeError("original compiler include aliases not staged")
    exe=forensic/"terrel-debug.x"
    args=["gfortran","-std=legacy","-fno-automatic","-fno-align-commons",
          "-fallow-argument-mismatch","-O0","-ffixed-line-length-none",
          "-I"+str(aliases),"-I"+str(vendor),str(patched),
          "-o",str(exe)]
    compiled=_invoke(args,cwd=forensic,seconds=180,logprefix=forensic/"compile-debug")
    if compiled["returncode"]!=0 or not exe.is_file():
        raise CoordinateProbeError("instrumented independent source compilation failed")
    ctrl=prepare_control(vendor,checkout,forensic,selected,grid)
    original_dir=ctrl.parent
    out=_invoke([str(exe),ctrl.name],cwd=original_dir,seconds=300,
                logprefix=forensic/"run-debug")
    trace=original_dir/"p1_original_coords.txt"
    if out["returncode"]!=0 or not trace.is_file():
        raise CoordinateProbeError("forensic-only original execution failed")
    return diagnose_trace(trace=trace,selected_tif=selected,grid=grid)

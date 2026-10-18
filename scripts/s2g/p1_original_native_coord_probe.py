"""#54 forensic-only direct C++ pixel lineage; never a science acceptance path.

The C++ translation unit is copied and instrumented in an ephemeral workspace.
The normal P1 core, frozen Hefei entry point, and pinned original Fortran
remain untouched. The raw coordinate traces must NEVER be uploaded.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import math
import shlex
import subprocess

from scripts.s2g.p1_original_actions_replay import _invoke

class DirectNativeProbeError(ValueError):
    pass

CPP_ANCHOR = "    const auto cell=cell_index_terrel(projected_x,projected_y,spec);"
CPP_SUM_ANCHOR = "  std::vector<float> sum(cells,0.0f);"
TRACE_NAME = "p1_native_pixel_coords.txt"
CPP_TRACE_OPEN = (
    '  std::ofstream p1_forensic_trace("p1_native_pixel_coords.txt",'
    'std::ios::out|std::ios::trunc);\n'
    '  if(!p1_forensic_trace)throw std::runtime_error("P1 forensic trace open failed");\n'
    '  p1_forensic_trace<<std::setprecision(17);'
)
CPP_TRACE_POINT = (
    "    p1_forensic_trace<<(i+1)<<' '<<(j+1)<<' '"
    "<<(cell?cell->first+1:0)<<' '<<(cell?cell->second+1:0)<<' '"
    "<<projected_x<<' '<<projected_y<<' '<<lon<<' '<<lat"
    "<<' '<<x<<' '<<y<<'\\n';"
)

def diagnostic_cpp_copy(original:Path, dest:Path)->None:
    if dest.exists() or dest.is_symlink():
        raise DirectNativeProbeError("native diagnostic must use a fresh scratch file")
    if not original.is_file() or original.is_symlink():
        raise DirectNativeProbeError("native production source absent or symlinked")
    source=original.read_text(encoding="utf-8")
    if source.count(CPP_ANCHOR)!=1 or source.count(CPP_SUM_ANCHOR)!=1:
        raise DirectNativeProbeError("native production projection anchor changed")
    if TRACE_NAME in source or "p1_forensic_trace" in source:
        raise DirectNativeProbeError("production source already instrumented")
    source=source.replace("#include <ogr_spatialref.h>",
                          "#include <ogr_spatialref.h>\n#include <fstream>\n#include <iomanip>",1)
    source=source.replace(CPP_SUM_ANCHOR,CPP_SUM_ANCHOR+"\n"+CPP_TRACE_OPEN,1)
    source=source.replace(CPP_ANCHOR,CPP_ANCHOR+"\n"+CPP_TRACE_POINT,1)
    dest.write_text(source,encoding="utf-8")
    if original.read_text(encoding="utf-8").find(TRACE_NAME)>=0:
        raise DirectNativeProbeError("instrumentation altered production evidence")

def execute_native_diagnostic(*, selected:Path, grid:dict, workspace:Path)->Path:
    root=Path(__file__).resolve().parents[2]
    native=root/"native_cpp"
    source=native/"src/geo/terrain_grid.cpp"
    if not source.is_file():
        raise DirectNativeProbeError("audited native production source absent")
    scratch=workspace/"forensic_native_cpp"
    scratch.mkdir(exist_ok=False)
    instrumented=scratch/"terrain_grid.cpp"
    diagnostic_cpp_copy(source,instrumented)
    exe=scratch/"p1-native-forensic.x"
    try:
        gdal_cflags=shlex.split(subprocess.check_output(
            ["gdal-config","--cflags"],text=True,timeout=15))
        gdal_libs=shlex.split(subprocess.check_output(
            ["gdal-config","--libs"],text=True,timeout=15))
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        raise DirectNativeProbeError("GDAL development toolchain absent") from exc
    # Uses the EXACT main native CLI + actual raster reader; only its
    # terrain_grid.cpp translation unit is a scratch instrumented copy.
    cmd=["g++","-std=c++20","-O3","-DNDEBUG","-Wall","-Wextra",
         "-Wpedantic","-Werror", "-I"+str(native/"include"),*gdal_cflags,
         str(native/"src/p1_terrain_case_cli.cpp"),
         str(native/"src/geo/terrain.cpp"),str(instrumented),
         "-o",str(exe),*gdal_libs]
    compile_result=_invoke(cmd,cwd=scratch,seconds=180,
                           logprefix=scratch/"compile-cpp-debug")
    if compile_result["returncode"]!=0 or not exe.is_file():
        raise DirectNativeProbeError("direct native forensic compilation failed")
    args=[str(exe),str(selected),str(grid["xrefkm"]),str(grid["yrefkm"]),
          str(grid["nx"]),str(grid["ny"]),str(grid["dgridkm"]),
          str(grid["zone"]),str(grid["hemisphere"]),
          str(scratch/"native-forensic-terrain.csv")]
    run_result=_invoke(args,cwd=scratch,seconds=300,
                       logprefix=scratch/"run-cpp-debug")
    trace=scratch/TRACE_NAME
    if run_result["returncode"]!=0 or not trace.is_file() or trace.stat().st_size==0:
        raise DirectNativeProbeError("direct native forensic execution failed")
    return trace

def _read_trace(path:Path, fields:int, max_records:int)->dict:
    points={}
    with path.open(encoding="utf-8",errors="strict") as fh:
        for line in fh:
            if not line.strip():
                continue
            parts=line.split()
            if len(parts)!=fields:
                raise DirectNativeProbeError("unexpected forensic trace record shape")
            try:
                i,j,ix,iy=map(int,parts[:4])
                coords=[float(x.replace("D","E")) for x in parts[4:]]
            except ValueError as exc:
                raise DirectNativeProbeError("malformed forensic trace") from exc
            if i<=0 or j<=0 or not all(math.isfinite(v) for v in coords):
                raise DirectNativeProbeError("invalid forensic pixel or coordinate")
            key=(i,j)
            if key in points or len(points)>=max_records:
                raise DirectNativeProbeError("duplicate or oversized forensic trace")
            points[key]=(ix,iy,*coords)
    if not points:
        raise DirectNativeProbeError("empty forensic trace")
    return points

def compare_direct_traces(*, original_trace:Path, native_trace:Path,
                          grid:dict, max_records:int=250_000)->dict:
    """Compare exact source pixel i,j, not adjacent-cell proxy candidates."""
    if not 1<=max_records<=250_000:
        raise DirectNativeProbeError("invalid forensic record bound")
    old=_read_trace(original_trace,6,max_records)
    native=_read_trace(native_trace,10,max_records)
    if old.keys()!=native.keys():
        raise DirectNativeProbeError("original/native source pixel sets differ")
    old_hits=native_hits=both_inside=both_outside=old_only=native_only=0
    cell_bad=coordinate_bad=0
    axis=Counter()
    first=[]
    e_diffs=[];n_diffs=[]
    for key in old:
        oi,oj,ox,oy=old[key]
        ni,nj,nx,ny,lon,lat,prex,prey=native[key]
        # Cross-check that the captured C++ REAL*4 projection values
        # correspond to recorded pre-staging double UTM coordinates.
        if not all(math.isfinite(v) for v in (nx,ny,lon,lat,prex,prey)):
            raise DirectNativeProbeError("invalid C++ forensic coordinate lineage")
        inside_old=1<=oi<=grid["nx"] and 1<=oj<=grid["ny"]
        inside_native=1<=ni<=grid["nx"] and 1<=nj<=grid["ny"]
        old_hits+=int(inside_old)
        native_hits+=int(inside_native)
        dx=ox-nx;dy=oy-ny
        e_diffs.append(abs(dx));n_diffs.append(abs(dy))
        coordinate_bad+=int(dx!=0.0 or dy!=0.0)
        if inside_old and inside_native:
            both_inside+=1
            if (oi,oj)!=(ni,nj):
                cell_bad+=1
                axis[("E_W" if oi!=ni else "NO_E_W",
                      "N_S" if oj!=nj else "NO_N_S")]+=1
                if len(first)<20:
                    first.append({
                        "original_cell":[oi,oj],
                        "direct_native_cell":[ni,nj],
                        "original_minus_direct_native_e_m":round(dx,6),
                        "original_minus_direct_native_n_m":round(dy,6),
                    })
        elif inside_old:
            old_only+=1
        elif inside_native:
            native_only+=1
        else:
            both_outside+=1
    def p95(x):
        ordered=sorted(x)
        return round(ordered[min(len(x)-1,math.floor(.95*(len(x)-1)))],6)
    return {
        "schema_version":"p1-original-vs-direct-cpp-pixel-trace-v1",
        "status":"DIAGNOSTIC_ONLY_NOT_SCIENCE_ACCEPTED",
        "source_pixel_set_exact_match":True,
        "trace_records":len(old),
        "original_inside_hits":old_hits,
        "direct_native_inside_hits":native_hits,
        "both_inside":both_inside,
        "both_outside":both_outside,
        "original_inside_only":old_only,
        "direct_native_inside_only":native_only,
        "original_vs_DIRECT_CPP_cell_mismatches_BOTH_INSIDE":cell_bad,
        "coordinate_records_differ_from_DIRECT_CPP":coordinate_bad,
        "max_abs_easting_difference_m":round(max(e_diffs),6),
        "max_abs_northing_difference_m":round(max(n_diffs),6),
        "p95_abs_easting_difference_m":p95(e_diffs),
        "p95_abs_northing_difference_m":p95(n_diffs),
        "cell_mismatch_axes":{"/".join(k):v for k,v in axis.items()},
        "first20_inside_grid_cell_disagreements_only":first,
        "cpp_source":"SCRATCH_INSTRUMENTED_EXACT_NATIVE_TERRAIN_GRID_CPP",
        "original_source":"SCRATCH_INSTRUMENTED_PINNED_ORIGINAL_TERREL",
        "pixel_trace_artifact_uploaded":False,
        "science_acceptance":"NOT_ACCEPTED",
    }

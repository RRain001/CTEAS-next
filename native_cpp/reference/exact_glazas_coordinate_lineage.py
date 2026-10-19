#!/usr/bin/env python3
"""Issue53 isolated, original-source-derived *diagnostic* coordinate lineage.

The unmodified frozen CTGPROC and its unmodified LFINAL=F hits remain the ONLY
original numerical oracle. An additional source-hash-checked derivative adds
one independent WRITE statement in the GLOBAL branch, recording the exact
Fortran (source pixel, mesh sample, LAEA xy, GLOBE UTM xy). Its original
qamesh.dat and LU.DAT MUST be bit-identical to unmodified original QA before
any lineage is reported. The derivative is never installed or redistributed.
"""
from __future__ import annotations
import csv
import math
from pathlib import Path
from native_cpp.reference.validate_p2_glazas_original import (
    CTGPROC_ORIGINAL_SOURCE_SHA256, file_sha, require,
)
from native_cpp.reference.diagnose_glazas_mesh_coordinates import (
    fortran_original_cell, f32, inside_margin,
)

HEADER_GEN=["source_i","source_j","mesh_i","mesh_j","usgs_category",
            "x_km","y_km","assigned_i","assigned_j"]
HEADER_DIRECT=["source_i","source_j","mesh_i","mesh_j","usgs_category",
               "laea_x_km","laea_y_km","x_km","y_km",
               "assigned_i","assigned_j"]
OPEN_MARKER="      cproji='LAZA    '"
WRITE_MARKER="                  if(LQA) write(40,*) xgrid,ygrid"
CLOSE_MARKER="      lucatx=52\n      call GMERGE(ngrid,ngtmp,lucatx)\n      goto 1999"
BEGIN_SECTION="c --- GLOBAL Format Data"
END_SECTION="c --- New Zealand Generic Format Data"

def instrument_global_only(source:str)->str:
    """Patch exactly one GLOBAL QA block; unrelated projection branches untouched."""
    begin=source.find(BEGIN_SECTION)
    end=source.find(END_SECTION,begin+1)
    require(begin>=0 and end>begin,"INDEXED_ORIGINAL_SECTION_NOT_FOUND")
    section=source[begin:end]
    for marker in (OPEN_MARKER,WRITE_MARKER,CLOSE_MARKER):
        require(section.count(marker)==1,"INDEXED_ORIGINAL_PATCH_DRIFT")
    section=section.replace(
        OPEN_MARKER,
        "      if(LQA) open(98,file='qaindexed.dat',\n"
        "     &             status='replace')\n"+OPEN_MARKER,
        1)
    section=section.replace(
        WRITE_MARKER,
        "                  if(LQA) then\n"
        "                    write(40,*) xgrid,ygrid\n"
        "                    write(98,*) i,j,imesh,jmesh,lucat,\n"
        "     &                  xmesh,ymesh,xgrid,ygrid\n"
        "                  endif",
        1)
    section=section.replace(
        CLOSE_MARKER,
        "      if(LQA) close(98)\n"+CLOSE_MARKER,
        1)
    require(section.count("write(98,*)")==1 and
            section.count("open(98,")==1 and
            section.count("close(98)")==1,
            "INDEXED_ORIGINAL_INSTRUMENT_COUNT_INVALID")
    return source[:begin]+section+source[end:]

def create_pinned_instrumented_source(vendor:Path,dest:Path)->str:
    require(vendor.is_file() and not vendor.is_symlink(),
            "INDEXED_ORIGINAL_SOURCE_UNAVAILABLE")
    require(file_sha(vendor)==CTGPROC_ORIGINAL_SOURCE_SHA256,
            "INDEXED_ORIGINAL_SOURCE_SHA_DRIFT")
    source=vendor.read_text(encoding="latin1")
    dest.write_text(instrument_global_only(source),encoding="latin1")
    return file_sha(dest)

def _key(row:dict)->tuple[int,int,int,int]:
    return (int(row["source_i"]),int(row["source_j"]),
            int(row["mesh_i"]),int(row["mesh_j"]))

def _floats(parts)->list[float]:
    xy=[float(x.replace("D","E").replace("d","e")) for x in parts]
    require(all(math.isfinite(x) for x in xy),"INDEXED_QA_NONFINITE")
    return xy

def read_original(indexed:Path,unchanged_qamesh:Path)->dict:
    """Keep line-by-line proof that indexing did not alter existing QA xy."""
    require(indexed.is_file() and unchanged_qamesh.is_file(),
            "INDEXED_ORIGINAL_QA_FILES_MISSING")
    result={}
    total=0
    with indexed.open(encoding="ascii") as fp, unchanged_qamesh.open(
            encoding="ascii") as qp:
        for line in fp:
            total+=1
            require(total<=3000000,"INDEXED_ORIGINAL_QA_TOO_LARGE")
            v=line.split()
            require(len(v)==9,"INDEXED_ORIGINAL_QA_BAD_ROW")
            ids=[]
            for value in v[:5]:
                try:
                    iv=int(value)
                except ValueError:
                    require(False,"INDEXED_ORIGINAL_QA_BAD_ID")
                require(1<=iv<=13000,"INDEXED_ORIGINAL_QA_ID_RANGE")
                ids.append(iv)
            nums=_floats(v[5:])
            unmodified=qp.readline().split()
            require(len(unmodified)==2,"INDEXED_QAMESH_LENGTH_DISAGREES")
            ux,uy=_floats(unmodified)
            # Each stream WRITE references the exact same REAL*4 values.
            require(f32(ux)==f32(nums[2]) and f32(uy)==f32(nums[3]),
                    "INDEXED_QAMESH_VALUES_DISAGREE")
            k=tuple(ids[:4])
            require(k not in result,"INDEXED_ORIGINAL_QA_DUPLICATE_KEY")
            if inside_margin(nums[2],nums[3]):
                result[k]=dict(category=ids[4],laea_x=nums[0],
                               laea_y=nums[1],x=nums[2],y=nums[3])
        require(not qp.readline(),"INDEXED_QAMESH_EXTRA_ROWS")
    require(total>0,"INDEXED_ORIGINAL_NO_POINTS")
    return {"rows":result,"total":total}

def read_native(path:Path,expected_header:list[str],expected_sha:str)->dict:
    require(path.is_file() and not path.is_symlink() and file_sha(path)==expected_sha,
            "INDEXED_NATIVE_TRACE_SHA_OR_FILE")
    result={}
    with path.open(newline="",encoding="utf-8") as fp:
        rd=csv.DictReader(fp)
        require(rd.fieldnames==expected_header,"INDEXED_NATIVE_HEADER")
        for row in rd:
            require(len(result)<3000000,"INDEXED_NATIVE_LIMIT")
            k=_key(row)
            require(k not in result,"INDEXED_NATIVE_DUPLICATE")
            xy=[row["x_km"],row["y_km"]]
            if not all(math.isfinite(v) for v in _floats(xy)):
                require(False,"INDEXED_NATIVE_COORD")
            data=dict(category=int(row["usgs_category"]),x=float(xy[0]),
                      y=float(xy[1]),cell=(int(row["assigned_i"]),
                                           int(row["assigned_j"])))
            if "laea_x_km" in row:
                data["laea_x"]=float(row["laea_x_km"])
                data["laea_y"]=float(row["laea_y_km"])
                _floats([row["laea_x_km"],row["laea_y_km"]])
            result[k]=data
    return result

def summarize_lineage(original:dict,gen:dict,direct:dict)->dict:
    shared=set(original)&set(gen)&set(direct)
    require(shared,"INDEXED_ORIGINAL_NO_COMMON_POINTS")
    max_gen=max_direct=max_laea=0.0
    coord_bin_gen=coord_bin_direct=0
    within_gen=within_direct=0
    examples=[]
    for k in sorted(shared):
        o=original[k];g=gen[k];d=direct[k]
        require(o["category"]==g["category"]==d["category"],
                "INDEXED_LU_CATEGORY_CHANGED")
        od=(o["x"],o["y"])
        og=fortran_original_cell(*od)
        gen_distance=math.hypot(g["x"]-od[0],g["y"]-od[1])*1000
        direct_distance=math.hypot(d["x"]-od[0],d["y"]-od[1])*1000
        laea_distance=math.hypot(d["laea_x"]-o["laea_x"],
                                 d["laea_y"]-o["laea_y"])*1000
        max_gen=max(max_gen,gen_distance)
        max_direct=max(max_direct,direct_distance)
        max_laea=max(max_laea,laea_distance)
        dg=og!=g["cell"];dd=og!=d["cell"]
        coord_bin_gen+=dg;coord_bin_direct+=dd
        if not dg:within_gen+=1
        if not dd:within_direct+=1
        if (dg or dd or laea_distance>=.01) and len(examples)<40:
            examples.append({
                "source_i":k[0],"source_j":k[1],
                "mesh_i":k[2],"mesh_j":k[3],
                "class":o["category"],
                "original_laea_km":[o["laea_x"],o["laea_y"]],
                "candidate_laea_km":[d["laea_x"],d["laea_y"]],
                "original_utm_km":list(od),
                "gen_utm_km":[g["x"],g["y"]],
                "direct_utm_km":[d["x"],d["y"]],
                "original_cell":list(og),
                "gen_cell":list(g["cell"]),
                "direct_cell":list(d["cell"]),
                "laea_coordinate_delta_m":round(laea_distance,6),
                "gen_coordinate_delta_m":round(gen_distance,6),
                "direct_coordinate_delta_m":round(direct_distance,6),
            })
    return {
        "status":"DIAGNOSTIC_ONLY_NOT_ORIGINAL_NUMERIC_ACCEPTANCE",
        "method":"sha_pinned_isolated_indexed_fortran_global_real4_join",
        "original_near_grid_points":len(original),
        "native_gen_points":len(gen),
        "native_direct_points":len(direct),
        "same_source_sample_key_matches":len(shared),
        "original_samples_absent_in_gen":len(set(original)-set(gen)),
        "original_samples_absent_in_direct":len(set(original)-set(direct)),
        "max_original_to_gen_utm_offset_m":round(max_gen,6),
        "max_original_to_direct_utm_offset_m":round(max_direct,6),
        "max_original_to_direct_source_laea_offset_m":round(max_laea,6),
        "gen_cell_bin_disagreements_on_shared_keys":coord_bin_gen,
        "direct_cell_bin_disagreements_on_shared_keys":coord_bin_direct,
        "gen_cell_bin_matches_on_shared_keys":within_gen,
        "direct_cell_bin_matches_on_shared_keys":within_direct,
        "first_40_coordinate_or_bin_disagreements":examples,
        "warning":"Instrumented original is used ONLY for stage-lineage QA; unmodified original LU.DAT remains numerical oracle.",
    }

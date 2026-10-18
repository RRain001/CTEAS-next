#!/usr/bin/env python3
"""Non-authoritative original Fortran qamesh.dat vs native GLCC mesh-point audit.

This locates projected-coordinate and REAL*4 binning discrepancies.
Only authentic original CTGPROC LFINAL=T/F integer and fraction comparison is
a scientific PASS gate; QA point matching is diagnostic, not a substitute.
"""
from __future__ import annotations
import csv
import math
from pathlib import Path
import re
import struct
from native_cpp.reference.validate_p2_glazas_original import GateError,require

HEADER=["source_i","source_j","mesh_i","mesh_j","usgs_category","x_km","y_km","assigned_i","assigned_j"]
X0,Y0,STEP,NX,NY=510.885,3531.269,0.100,50,50

def f32(x:float)->float:
    return struct.unpack("<f",struct.pack("<f",x))[0]

def fortran_original_cell(x:float,y:float)->tuple[int,int]:
    # LUGRID: DELX=REAL4(X - XORIGIN), I=DELX/DGRID (truncation),
    # then I=I+1 iff DELX >= 0. Sign and round before integer conversion.
    def index(value,ref):
        delta=f32(f32(value)-f32(ref))
        raw=f32(delta/f32(STEP))
        return int(raw)+(1 if delta>=0 else 0)
    return index(x,X0),index(y,Y0)

def inside_margin(x:float,y:float)->bool:
    return X0-.03<=x<=X0+NX*STEP+.03 and Y0-.03<=y<=Y0+NY*STEP+.03

def load_native(path:Path)->list[dict]:
    result=[]
    with path.open(newline="",encoding="utf-8") as fp:
        reader=csv.DictReader(fp)
        require(reader.fieldnames==HEADER,"NATIVE_QA_HEADER_UNEXPECTED")
        for row in reader:
            require(len(result)<3000000,"NATIVE_QA_TOO_MANY_POINTS")
            r={k:int(row[k]) for k in ("source_i","source_j","mesh_i","mesh_j","usgs_category","assigned_i","assigned_j")}
            r.update(x=float(row["x_km"]),y=float(row["y_km"]))
            require(math.isfinite(r["x"]) and math.isfinite(r["y"]),"NONFINITE_NATIVE_QA_POINT")
            if inside_margin(r["x"],r["y"]):
                result.append(r)
    return result

def load_fortran(path:Path)->list[tuple[float,float]]:
    out=[]
    with path.open(encoding="ascii",errors="strict") as fp:
        for raw in fp:
            require(len(out)<3000000,"ORIGINAL_QA_TOO_MANY_POINTS")
            spl=raw.split()
            require(len(spl)==2,"ORIGINAL_QA_MALFORMED_POSITION")
            x,y=map(lambda t:float(t.replace("D","E").replace("d","e")),spl)
            require(math.isfinite(x) and math.isfinite(y),"ORIGINAL_QA_NONFINITE_POINT")
            if inside_margin(x,y):
                out.append((x,y))
    return out

def summarize(original_points:list[tuple[float,float]],native_points:list[dict],
              *,match_radius_m:float=15.0)->dict:
    require(0<match_radius_m<=20.0,"QA_MATCH_RADIUS_INVALID")
    # Grid sub-points are separated by ~50m. A 15m matching radius avoids
    # conflating neighboring actual samples while tolerating different transforms.
    bucket_km=.02
    buckets:dict[tuple[int,int],list[int]]={}
    for i,p in enumerate(native_points):
        key=(math.floor(p["x"]/bucket_km),math.floor(p["y"]/bucket_km))
        buckets.setdefault(key,[]).append(i)
    seen=set();unmatched=0;bad_bins=[];max_displacement=0.0
    for xo,yo in original_points:
        bx=math.floor(xo/bucket_km);by=math.floor(yo/bucket_km)
        best_i=None;best_sq=(match_radius_m/1000.0)**2
        for delta_x in (-1,0,1):
            for delta_y in (-1,0,1):
                for i in buckets.get((bx+delta_x,by+delta_y),()):
                    if i in seen:continue
                    p=native_points[i]
                    dd=(p["x"]-xo)**2+(p["y"]-yo)**2
                    if dd<best_sq:
                        best_sq=dd;best_i=i
        if best_i is None:
            unmatched+=1;continue
        seen.add(best_i)
        p=native_points[best_i]
        distance_m=math.sqrt(best_sq)*1000.
        max_displacement=max(distance_m,max_displacement)
        orig_bin=fortran_original_cell(xo,yo)
        native_bin=(p["assigned_i"],p["assigned_j"])
        if orig_bin!=native_bin:
            if len(bad_bins)<50:
                bad_bins.append({
                    "source_i":p["source_i"],"source_j":p["source_j"],
                    "mesh_i":p["mesh_i"],"mesh_j":p["mesh_j"],
                    "usgs_category":p["usgs_category"],
                    "original_projected_km":[xo,yo],
                    "native_projected_km":[p["x"],p["y"]],
                    "original_grid_cell":list(orig_bin),
                    "native_grid_cell":list(native_bin),
                    "distance_m":round(distance_m,6),
                    "distance_to_nearest_x_gridline_original_m":round(
                        abs((xo-X0)/STEP-round((xo-X0)/STEP))*100.,6),
                    "distance_to_nearest_y_gridline_original_m":round(
                        abs((yo-Y0)/STEP-round((yo-Y0)/STEP))*100.,6),
                })
    return {
      "status":"DIAGNOSTIC_ONLY_NOT_SCIENTIFIC_ORACLE",
      "method":"nearest_projected_mesh_point_with_f32_fortran_bin",
      "match_radius_m":match_radius_m,
      "original_qa_candidate_points":len(original_points),
      "native_qa_candidate_points":len(native_points),
      "matched_points":len(seen),
      "unmatched_original_points":unmatched,
      "unmatched_native_points":len(native_points)-len(seen),
      "max_matched_projected_offset_m":round(max_displacement,6),
      "coordinate_cell_assignment_disagreements_first_50":bad_bins,
      "coordinate_cell_assignment_disagreements_in_first_50":len(bad_bins),
      "warning":"Counts may differ if source-window filtering differs; this diagnostic cannot grant original parity."
    }

def audit(original_path:Path,native_path:Path)->dict:
    require(original_path.is_file() and native_path.is_file(),"DIAGNOSTIC_FILES_MISSING")
    return summarize(load_fortran(original_path),load_native(native_path))

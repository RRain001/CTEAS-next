#!/usr/bin/env python3
"""#160 C4 independent same-GeoTIFF GLAZAS 10x10 integer HIT oracle.

Independent implementation: Python/NumPy source-pixel broadcast and
Shapely GEOS point-in-polygon; C++ uses explicit nested source loops and
original REAL*4 COASTRD/PNPOLY. Both are compared over 40,000 x 38 exact
integers; any GEOS-vs-REAL4 shoreline boundary discrepancy fails closed.
No P2-B EXACT_AREA, P3 parameter physics, or historical GLCC oracle reuse.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import numpy as np
from osgeo import gdal, osr

POLICY_SHA="a5fa157f57feb1aa160dd96d920a22d267fea78c5828c6040fa95e86536544ed"
WOLSONG_TIFF_SHA="2a1a208c5386735692d788066f730c7391e87f0981e7b9ad099442af2e217711"
BLN_SHA="67da93d441e7defe3eb46627ed9ce896c0a91ffd89fd5e4363d834d8108e11f9"
METHOD="P2_C_GLC30M_SOURCE_SUBPOINT_GLAZAS_LUGRID_R4_HITS_V1"
CLASS_IDS=(11,12,13,14,15,16,17,21,22,23,24,31,32,33,41,42,43,51,52,
           53,54,55,61,62,71,72,73,74,75,76,77,81,82,83,84,85,91,92)
INDEX={v:i for i,v in enumerate(CLASS_IDS)}
SOURCE_CODES=(10,11,12,20,51,52,61,62,71,72,81,82,91,92,120,121,122,
              130,140,150,152,153,181,182,183,184,185,186,187,190,200,
              201,202,210,220)
GRIDS={
    "inland":(32650,503385.,3523769.),
    "wolsong":(32652,533215.,3942629.),
}
def require(ok,why):
    if not ok:
        raise ValueError("P2C30M_INDEPENDENT_"+why)

def hashfile(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for buf in iter(lambda:f.read(1024*1024),b""):
            h.update(buf)
    return h.hexdigest()

def regular(path:Path)->bool:
    return path.is_file() and not path.is_symlink()

def policy_map(path:Path):
    require(regular(path) and hashfile(path)==POLICY_SHA,"USER_POLICY_SOURCE_SHA")
    j=json.loads(path.read_text())
    require(j["schema"]=="cteas.p2b.glc35_usgs38_user_selected_mapping.v1" and
            j["decision"]=="USER_SELECTED_34_FIXED_CLASSES_AND_GLC210_L1_LAND_TO_52_SEA_TO_55" and
            j["production_authorized"] is False,"POLICY_ID_STATUS")
    fixed={int(o["glc_code"]):int(o["usgs_code"]) for o in j["fixed_classes"]}
    require(len(fixed)==34 and len(j["fixed_classes"])==34 and
            sorted((*fixed,210))==list(SOURCE_CODES) and
            fixed[52]==42 and fixed[183]==77 and fixed[184]==77 and
            all(o in INDEX for o in fixed.values()),"POLICY_FIXED_CODES_DRIFT")
    c=j["conditional_classes"]
    require(len(c)==1 and c[0]["glc_code"]==210 and
            [u["usgs_code"] for u in c[0]["outcomes"]]==[52,55],
            "POLICY_WATER_52_55")
    return fixed

def independent_coast_geometry(bln:Path):
    """Read genuine original Full COASTRD BLN as geometry, not C++ classifier."""
    from shapely.geometry import Polygon
    from shapely import prepare
    require(regular(bln) and hashfile(bln)==BLN_SHA,
            "AUTHENTIC_FULL_ORIGINAL_BLN_SHA")
    lines=bln.read_text().splitlines()
    poly=[]
    cursor=0
    while cursor<len(lines):
        parts=re.fullmatch(r'\s*(\d+)\s*,\s*([01])\s*,\s*"([0-4])\s*,\s*(\d+)\s*,\s*(-?\d+)\s*"\s*',
                           lines[cursor])
        require(parts is not None,"BLN_BAD_HEADER")
        n=int(parts[1]);level=int(parts[3])
        require(n>=4 and cursor+n<len(lines)+1 and level==1,
                "BLN_MUST_BE_FULL_L1_ONLY")
        coords=[]
        for text in lines[cursor+1:cursor+1+n]:
            xy=text.split(",")
            require(len(xy)==2,"BLN_BAD_VERTEX")
            coords.append(tuple(float(np.float32(float(x))) for x in xy))
        cursor+=1+n
        require(coords[0]==coords[-1],"BLN_POLYGON_NOT_CLOSED")
        p=Polygon(coords)
        # Original COASTEXT clipping can yield a self-touching polygon.
        # CTGPROC PNPOLY accepts its frozen *ring* rather than requiring
        # a GEOS-valid polygon. Keep original vertex order unchanged;
        # independently evaluate as GEOS predicate and require zero HITS
        # difference, never silently buffer(0) or repair geometry.
        require(p.area>0 and len(coords)>=4,"BLN_EMPTY_GEOMETRY")
        poly.append(p)
    require(len(poly)==1,"WOLSONG_REVIEWED_SINGLE_L1_POLYGON")
    # Prepared GEOS point membership differs algorithmically from REAL*4
    # PNPOLY and is independently compared without tolerance.
    prepare(poly[0])
    return poly[0]

def load_source(tif:Path,sha:str,epsg:int,x0:float,y0:float,nx:int=200,ny:int=200,dx_km:float=.1):
    require(regular(tif) and hashfile(tif)==sha,"ACTUAL_SOURCE_SHA_DRIFT")
    ds=gdal.Open(str(tif),gdal.GA_ReadOnly)
    require(ds is not None and ds.RasterCount==1,"SINGLE_BAND_GLC")
    band=ds.GetRasterBand(1)
    require(band.DataType==gdal.GDT_Byte,"SOURCE_UINT8_REQUIRED")
    sr=osr.SpatialReference()
    require(sr.ImportFromEPSG(epsg)==0,"EXPECTED_CRS_UNAVAILABLE")
    actual=osr.SpatialReference(wkt=ds.GetProjection())
    require(bool(actual.IsSame(sr)),"TIF_CRS_DRIFT")
    gt=ds.GetGeoTransform()
    require(gt[1]==30. and gt[2]==gt[4]==0. and gt[5]==-30.,
            "SOURCE_NOT_NORTH_UP_30M")
    require(gt[0]<=x0 and gt[3]>=y0+ny*dx_km*1000 and
            gt[0]+ds.RasterXSize*30>=x0+nx*dx_km*1000 and
            gt[3]-ds.RasterYSize*30<=y0,
            "NOT_FULL_REQUESTED_GRID_COVERAGE")
    pixels=band.ReadAsArray()
    mask=band.GetMaskBand().ReadAsArray()!=0
    require(pixels.shape==mask.shape and pixels.ndim==2 and
            pixels.dtype==np.uint8,"PIXEL_MASK_SHAPE")
    return pixels,mask,gt

def independently_compute(tif:Path,sha:str,site:str,policy:dict,coast:Path|None,
                          grid:tuple|None=None):
    epsg,x0,y0,nx,ny,dx_km=(grid if grid is not None else (*GRIDS[site],200,200,.1))
    require(isinstance(nx,int) and isinstance(ny,int) and 1<=nx<=500 and
            1<=ny<=500 and nx*ny<=250000 and
            epsg in (32650,32652) and
            all(math.isfinite(v) for v in (x0,y0,dx_km)) and
            dx_km>0 and dx_km<=1.,
            "S2E_GRID_OUTSIDE_ORACLE_BUDGET_OR_SELECTED_UTM")
    a,mask,gt=load_source(tif,sha,epsg,x0,y0,nx,ny,dx_km)
    coastline=None
    if site=="wolsong":
        require(coast is not None,"COAST_BNL_REQUIRED")
        coastline=independent_coast_geometry(coast)
    else:
        require(coast is None,"INLAND_FORBIDS_SHORELINE")
    from shapely import contains_xy
    hit_grid=np.zeros((nx*ny,38),dtype=np.uint32)
    raw_hist=Counter()
    used_hist=Counter()
    eligible=missing_pixels=masked_pixels=outside=0
    landwater=seawater=0
    width=a.shape[1]
    im=np.arange(10,dtype=np.float64)
    jm=np.arange(10,dtype=np.float64)
    cols=np.arange(width,dtype=np.float64)
    # 30m pixel x source subpixel centers, independently broadcast per row.
    x_m=gt[0]+30.*(cols[:,None,None]+(im[None,:,None]+.5)/10.)
    x_m=np.broadcast_to(x_m,(width,10,10)).ravel()
    one_milli=float(np.float32(0.001))
    float_spacing=np.float32(dx_km)
    fx0=np.float32(x0/1000.)
    fy0=np.float32(y0/1000.)
    cx=np.float32(x_m*one_milli)
    dx=np.float32(cx-fx0)
    ix=np.trunc(np.float32(dx/float_spacing)).astype(np.int32)+(dx>=0)
    for row in range(a.shape[0]):
        valid=mask[row] & (a[row]!=0) & (a[row]!=250)
        masked_pixels+=int((~mask[row]).sum())
        missing_pixels+=int((mask[row]&((a[row]==0)|(a[row]==250))).sum())
        unknown=set(map(int,np.unique(a[row][valid])))-set(SOURCE_CODES)
        require(not unknown,"UNRECOGNIZED_VALID_CLASS")
        counts=Counter(map(int,a[row][valid]))
        raw_hist.update(counts)
        eligible+=int(valid.sum())*100
        # Index source pixel then its 10x10 subpoints in GLAZAS order.
        v=np.repeat(valid,100)
        if not v.any():continue
        codes=np.repeat(a[row],100)
        ym=gt[3]-30.*(row+(jm+.5)/10.)
        y3=np.broadcast_to(ym[None,None,:],(width,10,10)).ravel()
        cy=np.float32(y3*one_milli)
        dy=np.float32(cy-fy0)
        jy=np.trunc(np.float32(dy/float_spacing)).astype(np.int32)+(dy>=0)
        inside=v&(ix>=1)&(ix<=nx)&(jy>=1)&(jy<=ny)
        outside+=int(v.sum()-inside.sum())
        if not inside.any():continue
        used=codes[inside]
        used_hist.update(map(int,used))
        cells=(jy[inside]-1)*nx+(ix[inside]-1)
        classids=np.array([INDEX.get(policy.get(int(u),-1),-1) if u!=210 else INDEX[52]
                           for u in used],dtype=np.int16)
        waters=used==210
        if np.any(waters):
            if coastline is not None:
                # Independent GEOS predicate evaluated on exactly the R4
                # model coordinates, unlike C++ original R4 ray crossings.
                lands=contains_xy(coastline,cx[inside][waters],cy[inside][waters])
                classids[np.flatnonzero(waters)[~lands]]=INDEX[55]
                landwater+=int(np.sum(lands))
                seawater+=int(np.sum(~lands))
            else:
                landwater+=int(waters.sum())
        require(bool(np.all(classids>=0)),"INVALID_MAPPED_OUTPUT_CATEGORY")
        np.add.at(hit_grid,(cells,classids),1)
    require(eligible==outside+int(hit_grid.sum()),
            "TOTAL_PIXEL_MESH_SAMPLE_CONSERVATION")
    require(int(hit_grid[:,INDEX[52]].sum())>=landwater and
            int(hit_grid[:,INDEX[55]].sum())==seawater,
            "52_55_POINT_WATER_SPLIT_ACCOUNTING")
    return hit_grid,{"eligible_valid_subsamples":eligible,
                     "outside_model_hits":outside,"included_hits":int(hit_grid.sum()),
                     "masked_pixels":masked_pixels,"nodata_pixels":missing_pixels,
                     "source_pixel_histogram":dict(raw_hist),
                     "included_sample_histogram":dict(used_hist),
                     "water52_hits":landwater,"water55_hits":seawater}

def compare(produced:Path,counts:np.ndarray,statistics:dict,site:str,policy_file:Path,
            raster:Path,data_sha:str,coast:Path|None,out:Path,
            grid:tuple|None=None):
    epsg,x0,y0,nx,ny,dx_km=(grid if grid is not None else (*GRIDS[site],200,200,.1))
    require(counts.shape==(nx*ny,38),"INDEPENDENT_GRID_SHAPE")
    manifest=json.loads((produced/"p2c_glc30m_manifest.json").read_text())
    require(manifest.get("method")==METHOD and
            manifest.get("mapping_policy_sha256")==POLICY_SHA and
            manifest.get("site")==site and
            manifest.get("data_sha256")==data_sha and
            manifest.get("utm_epsg")==epsg and
            manifest.get("classes")==38 and manifest.get("nx")==nx and
            manifest.get("ny")==ny and manifest.get("mesh")==10 and
            abs(float(manifest.get("xrefkm",-1))-x0/1000.)<1e-8 and
            abs(float(manifest.get("yrefkm",-1))-y0/1000.)<1e-8 and
            abs(float(manifest.get("dgridkm",-1))-dx_km)<1e-9,
            "PRODUCER_MANIFEST_SCOPE")
    require(regular(produced/"hits.csv") and
            regular(produced/"lu.dat") and
            manifest["hits_csv_sha256"]==hashfile(produced/"hits.csv") and
            manifest["lu_dat_sha256"]==hashfile(produced/"lu.dat"),
            "NATIVE_OUTPUT_SHA")
    for key,v in statistics.items():
        if key.endswith("_histogram"):
            expected={str(k):n for k,n in v.items()}
            require(manifest[key]==expected,"SOURCE_HISTOGRAM_DRIFT_"+key)
        else:
            mk={"eligible_valid_subsamples":None,"outside_model_hits":"outside_hits",
                "included_hits":"included_hits","water52_hits":"water52_hits",
                "water55_hits":"water55_hits"}.get(key,key)
            if mk:require(manifest.get(mk)==v,"MANIFEST_COUNTER_DRIFT_"+key)
    errors=0
    different_cells=0
    first=[]
    with (produced/"hits.csv").open(newline="") as f:
        reader=csv.reader(f)
        require(next(reader,None)==["i","j","samples"]+
                [f"cat{c}" for c in CLASS_IDS],"HITS_COLUMNS")
        for idx,expected in enumerate(counts):
            row=next(reader,None)
            require(row is not None and len(row)==41 and
                    all(re.fullmatch(r"\d+",v) for v in row),"HITS_NONINTEGER_ROW")
            values=list(map(int,row))
            require(values[:2]==[idx%nx+1,idx//nx+1] and
                    sum(values[3:])==values[2],"HITS_GRID_ORDER_CONSERVATION")
            native=np.array(values[3:],dtype=np.uint32)
            unequal=np.flatnonzero(expected!=native)
            if len(unequal):
                errors+=len(unequal);different_cells+=1
                for k in unequal[:max(0,20-len(first))]:
                    first.append({"i":idx%nx+1,"j":idx//nx+1,
                                  "category":CLASS_IDS[k],
                                  "reference":int(expected[k]),
                                  "native":int(native[k])})
        require(next(reader,None) is None,"HITS_EXTRA_ROWS")
    # Original SVGRID F6.3 and row/header contract is independently read,
    # not inferred from the native HITS csv or the original GLCC parser.
    f6_err=missing_err=0
    with (produced/"lu.dat").open() as f:
        lines=[f.readline().rstrip("\r\n") for _ in range(11)]
        require(lines[0].split()[:2]==["LU.DAT","2.1"] and
                lines[4:6]==["FRACTION","UTM"] and
                lines[6].strip()==str(epsg%100)+"N" and
                lines[7].startswith("WGS-84"),
                "LU_HEADER_VERSION_PROJECTION")
        meta=lines[8].split()
        require(len(meta)==7 and int(meta[0])==nx and int(meta[1])==ny and
                abs(float(meta[2])-x0/1000.)<1e-8 and
                abs(float(meta[3])-y0/1000.)<1e-8 and
                abs(float(meta[4])-dx_km)<1e-9 and abs(float(meta[5])-dx_km)<1e-9 and
                int(meta[6])==38,"LU_HEADER_GRID_AND_UNITS")
        require(tuple(map(int,lines[10].split()))==CLASS_IDS,"LU_HEADER_USGS38_ORDER")
        for idx,n in enumerate(counts):
            line=f.readline().rstrip("\r\n")
            require(len(line)>=238 and
                    int(line[:5])==idx%nx+1 and int(line[5:10])==idx//nx+1,
                    "LU_ROW_FIXED_POSITION")
            total=int(n.sum())
            expected_flag="Missing" if total==0 else "."
            if line[238:].strip()!=expected_flag:missing_err+=1
            for k,hit in enumerate(n):
                actual=line[10+6*k:16+6*k].strip()
                require(re.fullmatch(r"(?:0|1)?\.\d{3}",actual),"NOT_F6_3_FIELD")
                expected=(f"{float(np.float32(np.float32(hit)/np.float32(total))):.3f}"
                          if total else "0.000")
                if float(actual)!=float(expected):f6_err+=1
        require(f.readline()=="","LU_EXTRA_ROWS")
    require(not out.exists() and not out.is_symlink(),"REPORT_ALREADY_EXISTS")
    accepted=(errors==different_cells==f6_err==missing_err==0)
    report={"status":(f"P2C_30M_SAME_SOURCE_INDEPENDENT_{nx*ny}X38_HITS_PASS_SCOPED"
                      if accepted else "P2C_30M_INDEPENDENT_INTEGER_OR_F63_MISMATCH"),
            "site":site,"grid":{"utm_epsg":epsg,"nx":nx,"ny":ny,
                                  "xrefkm":x0/1000.,"yrefkm":y0/1000.,
                                  "dgridkm":dx_km},
             "method":METHOD,"native_file_sha256":hashfile(produced/"lu.dat"),
            "native_hits_sha256":hashfile(produced/"hits.csv"),
            "source_sha256":hashfile(raster),"mapping_policy_sha256":hashfile(policy_file),
            "original_full_l1_bln_sha256":hashfile(coast) if coast else None,
            "independent_oracle":"PYTHON_NUMPY_BROADCAST_AND_GEOS_POINT_CONTAINS",
            "integer_fields_compared":nx*ny*38,"integer_mismatches":errors,
            "cells_with_mismatches":different_cells,
            "F6_3_fields_compared":nx*ny*38,"F6_3_mismatches":f6_err,
            "missing_flag_mismatches":missing_err,
            "included_hits":statistics["included_hits"],
            "nonempty_cells":int(np.count_nonzero(counts.sum(axis=1))),
            "missing_cells":int(np.count_nonzero(counts.sum(axis=1)==0)),
            "water52_hits":statistics["water52_hits"],
            "water55_hits":statistics["water55_hits"],
            "first_20_integer_differences":first,
            "p3_parameters":"OUT_OF_SCOPE_ISSUE46"}
    out.write_text(json.dumps(report,indent=2)+"\n")
    require(accepted,"ZERO_INTEGER_AND_F6_3_REQUIRED")
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--site",choices=GRIDS,required=True)
    p.add_argument("--tif",type=Path,required=True)
    p.add_argument("--data-sha256",required=True)
    p.add_argument("--policy",type=Path,required=True)
    p.add_argument("--coast-bln",type=Path)
    p.add_argument("--utm-epsg",type=int)
    p.add_argument("--xrefkm",type=float)
    p.add_argument("--yrefkm",type=float)
    p.add_argument("--nx",type=int)
    p.add_argument("--ny",type=int)
    p.add_argument("--dgridkm",type=float)
    p.add_argument("--native",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    try:
        require(len(a.data_sha256)==64 and
                (a.site=="wolsong" and a.data_sha256==WOLSONG_TIFF_SHA or
                 a.site=="inland"),"CASE_SOURCE_SHA_SCOPE")
        policy=policy_map(a.policy)
        base=(*GRIDS[a.site],200,200,.1)
        opts=(a.utm_epsg,a.xrefkm,a.yrefkm,a.nx,a.ny,a.dgridkm)
        grid=tuple(base[i] if value is None else
                   value*(1000 if i in (1,2) else 1)
                   for i,value in enumerate(opts))
        require(grid[0]==base[0] and 1<=grid[3]*grid[4]<=250000,
                "S2E_ORACLE_SOURCE_UTM_GRID_BUDGET")
        result,summary=independently_compute(a.tif,a.data_sha256,
                                               a.site,policy,a.coast_bln,grid)
        report=compare(a.native,result,summary,a.site,a.policy,a.tif,
                       a.data_sha256,a.coast_bln,a.report,grid)
        print(json.dumps({k:report[k] for k in
            ("status","integer_fields_compared","integer_mismatches",
             "F6_3_mismatches","missing_flag_mismatches","included_hits")}))
        return 0
    except (ValueError,OSError,KeyError,RuntimeError) as exc:
        print(f"P2C_REFERENCE_FAIL_CLOSED:{type(exc).__name__}:{str(exc)[:240]}",
              file=sys.stderr)
        return 2
if __name__=="__main__":
    raise SystemExit(main())

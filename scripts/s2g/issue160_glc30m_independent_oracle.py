#!/usr/bin/env python3
"""Issue #160 independent 30m P2-C all-cell/all-class integer HITS oracle.

Separate from C++ point sampler: rasterize the authentic Full L1 polygon
onto the native *3 metre* subpoint lattice and use independent NumPy
vector arithmetic for original-style REAL*4 1-based binning. Compare
40,000×38 integer counts AND all 38 printed F6.3 fractions + Missing.
Never reuse the C++ HITS or a P2-B source-area overlap as the oracle.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import numpy as np
from osgeo import gdal, ogr, osr

CATS=(11,12,13,14,15,16,17,21,22,23,24,31,32,33,41,42,43,
      51,52,53,54,55,61,62,71,72,73,74,75,76,77,81,82,83,84,85,91,92)
EXPECTED_TIF="2a1a208c5386735692d788066f730c7391e87f0981e7b9ad099442af2e217711"
EXPECTED_FULL_L1="121435427911ea80624802e0f352d777eaf6ba6966ca5f07e687650e95329fd9"
GRID=(533215.,3942629.,100.,200,200)
MESH=10
K=38
CELLS=40000

def need(ok,why):
    if not ok:
        raise ValueError("P2C30M_ORACLE_"+why)

def sha(path:Path)->str:
    need(path.is_file() and not path.is_symlink(),"SOURCE_NOT_REGULAR_"+path.name)
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()

def policy_file(path:Path)->dict[int,int]:
    p=json.loads(path.read_text())
    need(p["schema"]=="cteas.p2b.glc35_usgs38_user_selected_mapping.v1" and
         p["decision"]=="USER_SELECTED_34_FIXED_CLASSES_AND_GLC210_L1_LAND_TO_52_SEA_TO_55" and
         len(p["fixed_classes"])==34 and len(p["conditional_classes"])==1 and
         p["conditional_classes"][0]["glc_code"]==210 and
         [v["usgs_code"] for v in p["conditional_classes"][0]["outcomes"]]==[52,55] and
         p["source_authentication"]["selected_resolution"]=="f",
         "USER_SELECTED_POLICY_NOT_FROZEN")
    raw={i["glc_code"]:i["usgs_code"] for i in p["fixed_classes"]}
    need(len(raw)==34 and 210 not in raw and set(raw.values())<=set(CATS) and
         raw[52]==42 and raw[183]==raw[184]==77,
         "SOURCE_MAPPING_MISMATCH")
    return raw

def model_crs()->osr.SpatialReference:
    s=osr.SpatialReference()
    need(s.ImportFromEPSG(32652)==0,"UTM52")
    s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return s

def independent_l1_raster(tif:gdal.Dataset, shp:Path)->gdal.Dataset:
    source=ogr.Open(str(shp))
    need(source is not None and source.GetLayerCount()>0,
         "GSHHG_SHP_OPEN")
    layer=source.GetLayer(0)
    proj=model_crs()
    from_crs=layer.GetSpatialRef()
    need(from_crs is not None,"GSHHG_SHP_CRS")
    from_crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    to_geographic=osr.CoordinateTransformation(proj,from_crs)
    # This bounds the *unmodified* official Full f L1 feature set.
    x0,y0,dx,nx,ny=GRID
    corners=[to_geographic.TransformPoint(x,y) for x in
             (x0-100.,x0+nx*dx+100.) for y in
             (y0-100.,y0+ny*dx+100.)]
    xs=[c[0] for c in corners];ys=[c[1] for c in corners]
    layer.SetSpatialFilterRect(min(xs),min(ys),max(xs),max(ys))
    to_utm=osr.CoordinateTransformation(from_crs,proj)
    mem_driver=ogr.GetDriverByName("Memory")
    vector=mem_driver.CreateDataSource("p2c-independent-l1")
    projected=vector.CreateLayer("L1",srs=proj,geom_type=ogr.wkbUnknown)
    n=0
    for feat in layer:
        geom=feat.GetGeometryRef()
        if geom is None:continue
        geom=geom.Clone()
        need(geom.Transform(to_utm)==0,"GSHHG_L1_REPROJECT")
        add=ogr.Feature(projected.GetLayerDefn())
        add.SetGeometry(geom)
        need(projected.CreateFeature(add)==0,"GSHHG_L1_MEMORY_FEATURE")
        n+=1
    need(n>0,"GSHHG_L1_NONEMPTY_LAND_REQUIRED")
    pixel=3.
    width=tif.RasterXSize*MESH
    height=tif.RasterYSize*MESH
    gt=tif.GetGeoTransform()
    mem=gdal.GetDriverByName("MEM")
    out=mem.Create("",width,height,1,gdal.GDT_Byte)
    need(out is not None and out.SetGeoTransform((gt[0],pixel,0.,gt[3],0.,-pixel))==0,
         "GSHHG_L1_RASTER_GRID")
    out.SetProjection(proj.ExportToWkt())
    err=gdal.RasterizeLayer(out,[1],projected,burn_values=[1])
    need(err==0,"GSHHG_L1_INDEPENDENT_RASTERIZATION")
    # Retain parents until GDAL has completed actual raster output creation.
    source=None;vector=None
    return out

def lut_and_class_id(mapping:dict[int,int])->tuple[np.ndarray,np.ndarray]:
    lookup=np.full(256,-1,dtype=np.int16)
    for raw,usgs in mapping.items():lookup[raw]=usgs
    lookup[210]=210
    index=np.full(256,-1,dtype=np.int16)
    for k,usgs in enumerate(CATS):index[usgs]=k
    return lookup,index

def independent_integer_counts(tif:gdal.Dataset,shore:gdal.Dataset,
                               mapping:dict[int,int])->tuple[np.ndarray,dict]:
    gt=tif.GetGeoTransform()
    need(tuple(round(v,8) for v in [gt[1],gt[2],gt[4],gt[5]])==
         (30.,0.,0.,-30.),"SOURCE_30M_GEOTRANSFORM")
    need(tif.RasterCount==1 and tif.RasterXSize<=2048 and tif.RasterYSize<=2048,
         "SOURCE_FORMAT")
    w,h=tif.RasterXSize,tif.RasterYSize
    src=tif.GetRasterBand(1)
    need(src.DataType==gdal.GDT_Byte,"SOURCE_CLASS_BYTE_REQUIRED")
    raw=src.ReadAsArray()
    mask=src.GetMaskBand().ReadAsArray()
    need(raw is not None and mask is not None,"SOURCE_READ")
    sub=3.
    x0,y0,dx,nx,ny=GRID
    need(gt[0]<=x0 and gt[0]+30*w>=x0+dx*nx and
         gt[3]>=y0+dx*ny and gt[3]-30*h<=y0,
         "FULL_20KM_COVERAGE_REQUIRED")
    fixed,index=lut_and_class_id(mapping)
    # Original GLOBE results: UTM metres x REAL*4 XMULTO = REAL*4 km,
    # LUGRID index = trunc(REAL*4(delta)/REAL*4(step))+sign.
    f001=float(np.float32(.001))
    fdx=np.float32(dx/1000)
    fx0=np.float32(x0/1000)
    fy0=np.float32(y0/1000)
    xmetres=gt[0]+(np.arange(w*MESH,dtype=np.float64)+.5)*sub
    fx=np.float32(xmetres*f001)
    vx=np.float32(fx-fx0)
    ix=np.trunc(np.float32(vx/fdx)).astype(np.int64)+(vx>=0).astype(np.int64)
    col=np.arange(w*MESH)//MESH
    counts=np.zeros((CELLS,K),dtype=np.int64)
    valid_total=outside=invalid=water52=water55=0
    chunk_cells=[];chunk_class=[]
    nsource_invalid=0
    for row in range(h):
        values=raw[row,:]
        masked=mask[row,:]
        invalid_pixels=(values==0)|(values==250)|(masked==0)
        nsource_invalid+=int(invalid_pixels.sum())
        need(np.all((fixed[values]>=0)|invalid_pixels),
             "UNKNOWN_SOURCE_GLC_CODE")
        classes=fixed[values[col]].copy()
        invalid_sub=invalid_pixels[col]
        for j in range(MESH):
            subrow=row*MESH+j
            ypos=gt[3]-(subrow+.5)*sub
            fy=np.float32(float(ypos)*f001)
            vy=np.float32(fy-fy0)
            jy=int(np.trunc(np.float32(vy/fdx)))+(1 if vy>=0 else 0)
            inside=(ix>=1)&(ix<=nx)&(jy>=1)&(jy<=ny)
            outside+=int((~inside).sum())
            invalid+=int((inside&invalid_sub).sum())
            good=inside&(~invalid_sub)
            if not np.any(good):continue
            water=good&(classes==210)
            mapped=classes.copy()
            if np.any(water):
                land=shore.GetRasterBand(1).ReadAsArray(
                    0,subrow,w*MESH,1).reshape(-1)!=0
                mapped[water&land]=52
                mapped[water&(~land)]=55
                water52+=int(np.count_nonzero(water&land))
                water55+=int(np.count_nonzero(water&(~land)))
            klass=index[mapped[good]]
            need(np.all(klass>=0),"MAPPED_TO_UNKNOWN_USGS_CATEGORY")
            cells=(jy-1)*nx+(ix[good]-1)
            chunk_cells.append(cells)
            chunk_class.append(klass.astype(np.int64))
            valid_total+=int(np.count_nonzero(good))
        if row%20==19 or row==h-1:
            if chunk_cells:
                cells=np.concatenate(chunk_cells)
                categories=np.concatenate(chunk_class)
                flat=cells*K+categories
                counts+=np.bincount(flat,minlength=CELLS*K).reshape(CELLS,K)
                chunk_cells.clear();chunk_class.clear()
    n_all=w*h*MESH*MESH
    need(valid_total+outside+invalid==n_all and
         int(counts.sum())==valid_total,"SOURCE_POINT_CONSERVATION")
    sums=counts.sum(axis=1)
    return counts,{"source_pixels":w*h,
                   "invalid_source_pixels":nsource_invalid,
                   "generated_subpoints":n_all,
                   "invalid_subpoints":invalid,
                   "outside_subpoints":outside,
                   "included_subpoints":valid_total,
                   "water52_hits":water52,"water55_hits":water55,
                   "missing_cells":int((sums==0).sum())}

def compare_native(output:Path, counts:np.ndarray, stats:dict)->dict:
    meta=json.loads((output/"sampling_manifest.json").read_text())
    need(meta["method"]=="P2_C_GLC30M_ORIGINAL_STYLE_POINT_SAMPLING" and
         meta["site"]=="wolsong" and meta["epsg"]==32652 and
         meta["nx"]==meta["ny"]==200 and meta["mesh"]==10,
         "NATIVE_MANIFEST_GRID")
    need(meta["tif_sha256"]==EXPECTED_TIF and
         meta["full_l1_shp_sha256"]==EXPECTED_FULL_L1,
         "NATIVE_MANIFEST_SOURCE_HASH")
    for k,v in stats.items():
        need(meta[k]==v,"NATIVE_STATS_"+k)
    for name,key in (("lu.dat","lu_dat_sha256"),
                     ("hits.csv","hits_csv_sha256")):
        need(sha(output/name)==meta[key],"NATIVE_SHA_"+name)
    discrepancies=0; f63_errors=0; flag_errors=0
    first=[]
    with (output/"hits.csv").open(newline="") as h, \
         (output/"lu.dat").open() as f:
        hr=csv.reader(h)
        need(next(hr)==["i","j","samples"]+[f"cat{x}" for x in CATS],
             "NATIVE_CSV_HEADER_38")
        header=[f.readline().rstrip("\r\n") for _ in range(11)]
        need(header[0].split()[:2]==["LU.DAT","2.1"] and
             header[4].strip()=="FRACTION" and header[5].strip()=="UTM" and
             header[6].strip()=="52N" and "WGS-84" in header[7],
             "P3_LU_V21_UTM52N_FORMAT")
        shape=header[8].split()
        need(len(shape)>=7 and tuple(int(x) for x in shape[:2])==(200,200) and
             abs(float(shape[2])-533.215)<1e-9 and
             abs(float(shape[3])-3942.629)<1e-9 and
             abs(float(shape[4])-.1)<1e-9 and
             int(shape[6])==K,
             "P3_200X200_100M_HEADER")
        need(tuple(int(x) for x in header[10].split())==CATS,
             "P3_USGS_38_ORDER")
        for i in range(CELLS):
            row=next(hr,None)
            line=f.readline().rstrip("\r\n")
            need(row is not None and len(row)==41 and
                 len(line)>=10+K*6,"LU_NATIVE_ALL_ROWS")
            need(int(row[0])==i%200+1 and int(row[1])==i//200+1 and
                 int(line[:5])==i%200+1 and int(line[5:10])==i//200+1,
                 "P3_ROW_COLUMN_ORDER")
            n=counts[i]
            got=np.array([int(x) for x in row[3:]],dtype=np.int64)
            if int(row[2])!=int(n.sum()) or np.any(got!=n):
                bad=np.flatnonzero(got!=n)
                discrepancies+=int(len(bad))
                if len(first)<12:
                    first.append({"i":i%200+1,"j":i//200+1,
                                  "kind":"HITS","categories":[int(CATS[k]) for k in bad[:8]]})
            marks=line[10+K*6:].strip()
            expected_flag="Missing" if n.sum()==0 else "."
            if marks!=expected_flag:flag_errors+=1
            for k in range(K):
                token=line[10+6*k:16+6*k].strip()
                need(re.fullmatch(r"(?:0|1)?\.\d{3}",token) is not None,
                     "P3_F63_TOKEN_SYNTAX")
                expected=float(n[k])/float(n.sum()) if n.sum() else 0.
                displayed=float(token)
                # Differences <= 0.0005 are only decimal-print noise.
                if abs(displayed-expected)>0.000500001:
                    f63_errors+=1
                    if len(first)<12:
                        first.append({"i":i%200+1,"j":i//200+1,
                                      "kind":"F6.3","usgs":CATS[k],
                                      "displayed":displayed,"reference":expected})
        need(next(hr,None) is None and f.readline()=="" ,
             "P3_EXTRA_OR_MISSING_RECORDS")
    ok=(discrepancies==f63_errors==flag_errors==0)
    return {"status":("P2C_WOLSONG_30M_INDEPENDENT_POINT_HITS_ZERO_DIFF_PASS"
                      if ok else "P2C_WOLSONG_30M_INDEPENDENT_SCIENTIFIC_MISMATCH"),
            "grid_cells":CELLS,
            "classes":K,
            "integer_fields_compared":CELLS*K,
            "integer_mismatches":discrepancies,
            "F6_3_fields_compared":CELLS*K,
            "fraction_tolerance_exceeded":f63_errors,
            "missing_flag_mismatches":flag_errors,
            "p3_lu_v21_format_only":"PASS" if ok else "FAIL",
            "p3_actual_makegeo_runtime":"NOT_RUN_ISSUE46",
            "reference":stats,
            "first_12_differences":first}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tif",type=Path,required=True)
    p.add_argument("--full-l1",type=Path,required=True)
    p.add_argument("--policy",type=Path,required=True)
    p.add_argument("--native",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    try:
        need(not a.report.exists(),"REPORT_OVERWRITE_FORBIDDEN")
        need(sha(a.tif)==EXPECTED_TIF and sha(a.full_l1)==EXPECTED_FULL_L1,
             "CANONICAL_INPUT_REQUIRED")
        mapping=policy_file(a.policy)
        tif=gdal.Open(str(a.tif),gdal.GA_ReadOnly)
        need(tif is not None and tif.GetProjectionRef()!="" and
             model_crs().IsSame(osr.SpatialReference(wkt=tif.GetProjectionRef())),
             "SOURCE_PROJECTION")
        l1=independent_l1_raster(tif,a.full_l1)
        counts,stats=independent_integer_counts(tif,l1,mapping)
        result=compare_native(a.native,counts,stats)
        result.update({"glc30m_tif_sha256":EXPECTED_TIF,
                       "gshhg_full_l1_shp_sha256":EXPECTED_FULL_L1,
                       "mapping_json_sha256":sha(a.policy),
                       "native_lu_sha256":sha(a.native/"lu.dat"),
                       "native_hits_sha256":sha(a.native/"hits.csv"),
                       "original_GLCC_historical_mapping":"UNCHANGED",
                       "p2b_exact_area_v1":"UNCHANGED"})
        a.report.write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps({"status":result["status"],
                          "int_mismatches":result["integer_mismatches"],
                          "F6_3_above_print_tolerance":result["fraction_tolerance_exceeded"],
                          "reference":stats},sort_keys=True))
        need(result["status"].endswith("PASS"),"ORACLE_ZERO_DIFF_NOT_ACCEPTED")
        return 0
    except (ValueError,KeyError,OSError,TypeError,IndexError) as exc:
        print(f"P2C30M_INDEPENDENT_ORACLE_FAIL_CLOSED:{exc}",file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())

"""#42 S3-B1: authentic SRTM native-P1 bounded lossless source window.

This is only a physical pixel-preserving crop of a separately SHA-pinned
original WGS84 90m GeoTIFF. It never interpolates heights, reprojects pixels,
replaces missing data or relaxes P1 model-grid precision/capacity. The large
parent source is left unchanged. This operation is NOT an original TERREL
scientific-parity reference or S5 removal of native capacity limits.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window, from_bounds

from native_cpp.orchestration.case_admission import admit_case, verify_immutable
from native_cpp.orchestration.plan import ContractError
from scripts.s2g.p1_terrain_source import case_bbox

def need(value,reason):
    if not value:
        raise ContractError("S3_HUOSHAN_TRUE_SOURCE_WINDOW_BLOCKED: "+reason)

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()

def crop(case_yaml:Path,source:Path,expected_sha:str,target:Path,manifest:Path)->dict:
    case=admit_case(case_yaml)
    root=case.case_path.parent
    need(source.is_file() and not source.is_symlink() and
         len(expected_sha)==64 and
         all(ch in "0123456789abcdef" for ch in expected_sha) and
         sha(source)==expected_sha,"original source TIFF bytes or SHA not authentic")
    need(target==root/"inputs/p1_srtm90_source_window.tif" and
         manifest==root/"inputs/p1_srtm90_source_window.json",
         "cropped TIFF must be inside independent accepted case source directory")
    need(not target.exists() and not manifest.exists() and
         not target.is_symlink() and not manifest.is_symlink() and
         not target.parent.is_symlink(),"source output is not fresh independent stage")
    bbox=case_bbox(case.grid_path,buffer_m=1000)
    with rasterio.open(source) as raster:
        need(raster.count==1 and raster.crs==rasterio.crs.CRS.from_epsg(4326) and
             raster.dtypes[0]=="int16" and
             abs(raster.transform.a-(1./1200.))<1e-8 and
             abs(raster.transform.e+(1./1200.))<1e-8 and
             raster.transform.b==raster.transform.d==0,
             "source is not same underlying 3arcsec WGS84 native int16 raster")
        need(raster.bounds.left<=bbox["west"] and
             raster.bounds.right>=bbox["east"] and
             raster.bounds.bottom<=bbox["south"] and
             raster.bounds.top>=bbox["north"],
             "authenticated parent source does not cover buffered Huoshan grid")
        box=from_bounds(bbox["west"],bbox["south"],bbox["east"],bbox["north"],
                        transform=raster.transform)
        x0=max(0,math.floor(box.col_off)-2)
        y0=max(0,math.floor(box.row_off)-2)
        x1=min(raster.width,math.ceil(box.col_off+box.width)+2)
        y1=min(raster.height,math.ceil(box.row_off+box.height)+2)
        n=(x1-x0)*(y1-y0)
        need(0<n<=5_000_000 and x1>x0 and y1>y0,
             "cropped true source exceeds P1 bounded raster pixel budget")
        window=Window(x0,y0,x1-x0,y1-y0)
        heights=raster.read(1,window=window)
        source_mask=raster.read_masks(1,window=window)
        transform=raster.window_transform(window)
        need(heights.shape==(y1-y0,x1-x0) and np.count_nonzero(source_mask)>0,
             "real source window empty or missing actual original pixels")
        target.parent.mkdir(parents=True,exist_ok=True)
        with rasterio.open(target,"w",driver="GTiff",width=x1-x0,
                           height=y1-y0,count=1,dtype="int16",
                           crs=raster.crs,transform=transform,nodata=raster.nodata,
                           compress="deflate") as out:
            out.write(heights,1)
        # Ground crop identity in the *actual* source pixel values, including
        # nodata/mask and original geographic pixel lattice. No interpolation.
        with rasterio.open(target) as check:
            need(check.crs==raster.crs and
                 check.transform.almost_equals(transform) and
                 check.nodata==raster.nodata and check.count==1 and
                 np.array_equal(check.read(1),heights) and
                 np.array_equal(check.read_masks(1),source_mask),
                 "cropped TIFF is not bit-identical physical source pixels/mask")
    verify_immutable(case)
    need(sha(source)==expected_sha,"parent source changed during cropping")
    proof={
       "schema":"cteas.s3.original_raster_native_window_no_resample.v1",
       "status":"TRUE_SOURCE_WINDOW_PIXEL_IDENTITY_PASS_NOT_P1_SCIENCE",
       "case_name":case.case_name,
       "case_yaml_sha256":case.case_sha256,
       "grid_cmn_sha256":case.grid_sha256,
       "research_time_sha256":case.time_sha256,
       "parent_original_tif_sha256":expected_sha,
       "parent_original_byte_size":source.stat().st_size,
       "window_integer_col_row_width_height":[int(x0),int(y0),int(x1-x0),int(y1-y0)],
       "source_resampling":"NONE_INTEGER_SOURCE_PIXEL_WINDOW_ONLY",
       "source_crs":"EPSG:4326",
       "source_resolution_degrees":"1/1200",
       "valid_source_pixels":int(np.count_nonzero(source_mask)),
       "window_pixel_count":int(n),
       "cropped_source_sha256":sha(target),
       "cropped_source_byte_size":target.stat().st_size,
       "native_p1_original_science":"NOT_RUN",
       "newsite_same_case_p1_p2_p3":"NOT_RUN",
       "s3_five_product_stack":"NOT_ACCEPTED",
    }
    with manifest.open("x",encoding="utf-8") as f:
        json.dump(proof,f,sort_keys=True,indent=2)
        f.write("\n")
    return proof

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--case-yaml",type=Path,required=True)
    p.add_argument("--original-tif",type=Path,required=True)
    p.add_argument("--original-sha256",required=True)
    p.add_argument("--cropped-tif",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True)
    a=p.parse_args()
    try:
        j=crop(a.case_yaml,a.original_tif,a.original_sha256,
               a.cropped_tif,a.manifest)
        print(json.dumps({"status":j["status"],
                          "cropped_source_sha256":j["cropped_source_sha256"],
                          "window_pixel_count":j["window_pixel_count"]}))
        return 0
    except (ContractError,OSError,ValueError,RuntimeError) as ex:
        print(json.dumps({"status":"S3_TRUE_SOURCE_CROP_BLOCKED",
                          "exception_type":type(ex).__name__}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())

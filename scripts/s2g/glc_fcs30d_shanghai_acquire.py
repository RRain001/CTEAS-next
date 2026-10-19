#!/usr/bin/env python3
"""Shanghai Dongtan candidate real 2022 GLC_FCS30D 30 m coastal crop.

Download mode needs owner-authenticated Google Earth Engine, ONLY on user's machine.
Verify mode is offline. No coastline classification, sea interpolation or model claim here.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile

import numpy as np
import rasterio
from pyproj import Transformer
from scripts.s2g.glc_fcs30d_acquire import ASSET, CLASSES, FILL, sha

ROOT=Path(__file__).resolve().parents[2]
DEFAULT=ROOT/"data/landcover/glc_fcs30d/v1_2022/shanghai_dongtan"
NAME="shanghai_dongtan_2022_30m.tif"
ZONE=32651
NX=NY=50
STEP=100.
X0=400655.
Y0=3485184.
BUFFER=60.
YEAR=2022
BAND="b23"
REGION_NAME="Shanghai Dongtan coastal-candidate grid, Yangtze Estuary"
META_FIELDS=("region","epsg","nx","ny","step_m","x0_m","y0_m",
             "wgs84_corners","buffered_utm_bounds_m","asset_path",
             "band","year","source_version")
BASE={"region":REGION_NAME,"epsg":ZONE,"nx":NX,"ny":NY,"step_m":STEP,
      "x0_m":X0,"y0_m":Y0,"asset_path":ASSET,"band":BAND,"year":YEAR,
      "source_version":"v1-community-gee"}
GRID=[X0,Y0,X0+NX*STEP,Y0+NY*STEP]
BUFFERED=[GRID[0]-BUFFER,GRID[1]-BUFFER,GRID[2]+BUFFER,GRID[3]+BUFFER]
TR=Transformer.from_crs(ZONE,4326,always_xy=True)
def corners(bounds):
    x1,y1,x2,y2=bounds
    return [[float(lon),float(lat)] for lon,lat in
        (TR.transform(x1,y1),TR.transform(x2,y1),
         TR.transform(x2,y2),TR.transform(x1,y2))]
BASE.update({"wgs84_corners":corners(GRID),
             "buffered_utm_bounds_m":BUFFERED})

def inspect(tif:Path)->dict:
    if not tif.is_file() or not (0<tif.stat().st_size<32*1024*1024):
        raise ValueError("REAL_GLC_TIFF_MISSING_OR_OVERSIZE")
    with rasterio.open(tif) as ds:
        t=ds.transform
        if ds.driver!="GTiff" or ds.count!=1 or ds.crs is None or ds.crs.to_epsg()!=ZONE:
            raise ValueError("REAL_GLC_MUST_BE_SINGLE_BAND_UTM51N")
        if not np.issubdtype(np.dtype(ds.dtypes[0]),np.integer):
            raise ValueError("REAL_GLC_NOT_INTEGER_CLASSES")
        if not np.allclose([t.a,t.b,t.d,t.e],[30,0,0,-30],atol=1e-8,rtol=0):
            raise ValueError("REAL_GLC_30M_NORTH_UP_REQUIRED")
        bounds=[ds.bounds.left,ds.bounds.bottom,ds.bounds.right,ds.bounds.top]
        if not (bounds[0]<=GRID[0] and bounds[1]<=GRID[1] and
                bounds[2]>=GRID[2] and bounds[3]>=GRID[3]):
            raise ValueError("REAL_GLC_NOT_COVERING_5KM_MODEL_GRID")
        a=ds.read(1)
        unknown=set(map(int,np.unique(a)))-(CLASSES|FILL)
        if unknown:raise ValueError("REAL_GLC_UNKNOWN_CLASSES")
        mask=(ds.read_masks(1)==0)|np.isin(a,list(FILL))
        cols,rows=np.meshgrid(np.arange(ds.width),np.arange(ds.height))
        cx=t.c+(cols+.5)*t.a
        cy=t.f+(rows+.5)*t.e
        within=(cx>=GRID[0])&(cx<GRID[2])&(cy>=GRID[1])&(cy<GRID[3])
        if not np.any(within):raise ValueError("REAL_GLC_EMPTY_GRID")
        invalid_inside=int(np.count_nonzero(mask&within))
        total_inside=int(np.count_nonzero(within))
        counts={str(int(v)):int(n) for v,n in zip(*np.unique(a[~mask],return_counts=True))}
        glc210_inside=int(np.count_nonzero((a==210)&(~mask)&within))
        return {"sha256":sha(tif),"size_bytes":tif.stat().st_size,
            "crs":ds.crs.to_string(),"bounds_utm_m":bounds,
            "width":ds.width,"height":ds.height,
            "resolution":[t.a,-t.e],"nodata":ds.nodata,
            "modelgrid_centers_count":total_inside,
            "modelgrid_nodata_or_fill_centers":invalid_inside,
            "modelgrid_source_coverage_ok":invalid_inside==0,
            "glc210_source_centers_inside_grid":glc210_inside,
            "glc210_coverage_ok":glc210_inside>0,
            "all_source_class_histogram":counts,
            "pixel_sha256":hashlib.sha256(a.tobytes()).hexdigest(),
            "sea_side_glc210_status":"NOT_DETERMINED_REQUIRES_REAL_GSHHS_FULL_INTERSECTION",
            "land_side_glc210_status":"NOT_DETERMINED_REQUIRES_REAL_GSHHS_FULL_INTERSECTION",
            "coastal_area_science":"NOT_RUN"}

def verify(dest:Path)->dict:
    meta=json.loads((dest/"metadata.json").read_text())
    for field in META_FIELDS:
        if meta[field]!=BASE[field]:raise ValueError("SHANGHAI_SITE_PROVENANCE_DRIFT:"+field)
    r=inspect(dest/NAME)
    for key,value in r.items():
        if meta[key]!=value:raise ValueError("SHANGHAI_RASTER_SHA_OR_COVERAGE_DRIFT:"+key)
    if meta.get("license")!="CC-BY-4.0":
        raise ValueError("SHANGHAI_SOURCE_LICENSE_MISSING")
    return r

def acquire(dest:Path)->dict:
    if dest.exists():raise ValueError("DESTINATION_EXISTS_REFUSE_OVERWRITE")
    import ee
    import requests
    ee.Initialize(project="cteas-earthengine") # authenticated by user, not in CI
    region=ee.Geometry.Rectangle(BUFFERED,proj="EPSG:32651",geodesic=False)
    col=ee.ImageCollection(ASSET).filterBounds(region).sort("system:index",True)
    ids=col.aggregate_array("system:id").getInfo()
    if not ids:raise ValueError("NO_REAL_GLC2022_SOURCE_TILE")
    image=col.mosaic().select(BAND)
    def download(path):
        try:
            url=image.getDownloadURL({"region":region,"crs":"EPSG:32651",
                                      "scale":30,"format":"GEO_TIFF","filePerBand":False})
            total=0
            with requests.get(url,stream=True,timeout=(30,180)) as response:
                response.raise_for_status()
                with path.open("xb") as f:
                    for block in response.iter_content(65536):
                        total+=len(block)
                        if total>32*1024*1024:raise ValueError("GLC_DOWNLOAD_EXCEEDS_32MB")
                        if block:f.write(block)
        except Exception:
            raise RuntimeError("EARTH_ENGINE_REAL_GLC_DOWNLOAD_FAILED_NO_URL_LOGGED") from None
    with tempfile.TemporaryDirectory(prefix="cteas-shanghai-glc-") as scratch:
        first=Path(scratch)/"first.tif"
        second=Path(scratch)/"second.tif"
        download(first);r1=inspect(first)
        download(second);r2=inspect(second)
        with rasterio.open(first) as a,rasterio.open(second) as b:
            same=np.array_equal(a.read(1),b.read(1)) and np.array_equal(a.read_masks(1),b.read_masks(1))
        if not same or any(r1[k]!=r2[k] for k in ("bounds_utm_m","crs","all_source_class_histogram","pixel_sha256")):
            raise ValueError("SHANGHAI_REPEATED_SOURCE_DOWNLOAD_DIFFERS")
        dest.mkdir(parents=True)
        (dest/NAME).write_bytes(first.read_bytes())
        meta={**BASE,**r1,"image_ids":ids,
            "mosaic_order":"system:index ascending; last valid pixel wins",
            "resampling":"nearest neighbour categoricals",
            "license":"CC-BY-4.0",
            "source_catalog":"https://gee-community-catalog.org/projects/glc_fcs/",
            "zenodo_version_note":"community-GEE v1; do not substitute newer v2 without validation",
            "download_utc":datetime.now(timezone.utc).isoformat(),
            "repeat_download":{"pixels_equal":True,"second_sha256":r2["sha256"]},
            "script_sha256":sha(Path(__file__)),
            "science_status":"SOURCE_ONLY_NO_ORIGINAL_MAKEGEO_NO_COASTAL_PASS"}
        (dest/"metadata.json").write_text(json.dumps(meta,indent=2)+"\n")
        (dest/"ATTRIBUTION.md").write_text(
          "# Shanghai Dongtan GLC_FCS30D 2022 source\\n\\n"
          "Liu, Zhang and colleagues, GLC_FCS30D 30m annual land-cover dataset. "
          "Zenodo DOI: 10.5281/zenodo.8239305. Community Earth Engine annual asset "
          "projects/sat-io/open-datasets/GLC-FCS30D/annual, band b23. "
          "CC BY 4.0; cite source authors. "
          "Raw crop is unmodified categorical nearest-neighbour data.\\n")
    return verify(dest)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("download","verify"))
    p.add_argument("--directory",type=Path,default=DEFAULT)
    a=p.parse_args()
    try:
        r=acquire(a.directory) if a.mode=="download" else verify(a.directory)
        print(json.dumps(r,indent=2,sort_keys=True))
    except Exception as exc:
        print("SHANGHAI_GLC_FAIL_CLOSED:"+type(exc).__name__,file=sys.stderr)
        return 1
    return 0
if __name__=="__main__":
    raise SystemExit(main())

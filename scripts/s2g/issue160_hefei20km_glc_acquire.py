#!/usr/bin/env python3
"""#160 C4 local/user-authenticated real 20km Hefei 2022 GLC-FCS30D source.

NOT an Actions/anonymous source download. It cannot claim acquisition before
authenticated Earth Engine yields two independently verified actual GeoTIFFs.
Historic Hefei 5km pixels are never stretched or reused as 20km coverage.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import tempfile
import numpy as np
import rasterio
from scripts.s2g.glc_fcs30d_acquire import ASSET,CLASSES,FILL

ROOT=Path(__file__).resolve().parents[2]
DEFAULT=ROOT/"data/landcover/glc_fcs30d/v1_2022/hefei20km"
NAME="hefei_2022_30m_20km.tif"
EPSG=32650
X0,Y0=503385.,3523769.
N=200
DX=100.
BUFFER=60.
BOUNDS=(X0,Y0,X0+N*DX,Y0+N*DX)
REQUEST=(BOUNDS[0]-BUFFER,BOUNDS[1]-BUFFER,
         BOUNDS[2]+BUFFER,BOUNDS[3]+BUFFER)
BAND="b23"
YEAR=2022
VERSION="issue160-c4-real-source-v1"
MAX_DOWNLOAD=32*1024*1024

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):
            h.update(b)
    return h.hexdigest()

def inspect(p:Path)->dict:
    if not p.is_file() or p.is_symlink() or not (0<p.stat().st_size<=MAX_DOWNLOAD):
        raise ValueError("HEFEI20KM_SOURCE_NOT_A_REAL_BOUNDED_TIF")
    with rasterio.open(p) as ds:
        t=ds.transform
        if ds.count!=1 or ds.crs.to_epsg()!=EPSG or ds.driver!="GTiff" or \
           ds.dtypes[0]!="uint8" or \
           not np.allclose([t.a,t.b,t.d,t.e],[30.,0.,0.,-30.],
                           rtol=0,atol=1e-8):
            raise ValueError("HEFEI20KM_GLC2022_UTM50N_30M_CATEGORICAL_REQUIRED")
        extent=[float(ds.bounds.left),float(ds.bounds.bottom),
                float(ds.bounds.right),float(ds.bounds.top)]
        if not (extent[0]<=BOUNDS[0] and extent[1]<=BOUNDS[1] and
                extent[2]>=BOUNDS[2] and extent[3]>=BOUNDS[3]):
            raise ValueError("HEFEI20KM_OLD_5KM_OR_INCOMPLETE_SOURCE_REJECTED")
        data=ds.read(1)
        if not set(np.unique(data).tolist())<=(CLASSES|FILL):
            raise ValueError("HEFEI20KM_UNKNOWN_GLC_SOURCE_CATEGORY")
        invalid=(ds.read_masks(1)==0)|np.isin(data,list(FILL))
        xlo=t.c+np.arange(ds.width)*t.a
        xhi=xlo+t.a
        yhi=t.f+np.arange(ds.height)*t.e
        ylo=yhi+t.e
        xover=np.maximum(0.,np.minimum(xhi,BOUNDS[2])-np.maximum(xlo,BOUNDS[0]))
        yover=np.maximum(0.,np.minimum(yhi,BOUNDS[3])-np.maximum(ylo,BOUNDS[1]))
        overlap=yover[:,None]*xover[None,:]
        total=float(overlap.sum())
        invalid_area=float(overlap[invalid].sum())
        if abs(total-400000000.)>.1 or invalid_area>1e-8:
            raise ValueError("HEFEI20KM_GRID_HAS_MISSING_OR_UNCOVERED_SOURCE")
        vals,cnts=np.unique(data[~invalid],return_counts=True)
        return {"sha256":sha(p),
                "size_bytes":p.stat().st_size,
                "width":ds.width,"height":ds.height,
                "crs":ds.crs.to_string(),
                "transform":list(t)[:6],
                "bounds_utm_m":extent,
                "nodata":ds.nodata,
                "dtype":ds.dtypes[0],
                "valid_model_area_m2":total,
                "invalid_model_area_m2":invalid_area,
                "pixel_sha256":hashlib.sha256(data.tobytes()).hexdigest(),
                "class_histogram":{str(int(v)):int(n) for v,n in zip(vals,cnts)}}

def verify(dest:Path)->dict:
    meta=json.loads((dest/"metadata.json").read_text())
    expect={"status":"HEFEI_20KM_2022_GLC30M_REAL_SOURCE_VERIFIED",
            "asset_path":ASSET,"source_band":BAND,"year":YEAR,
            "grid_epsg":EPSG,"grid_utm_bounds_m":list(BOUNDS),
            "requested_bounds_with_60m_buffer_m":list(REQUEST),
            "site":"hefei","license":"CC-BY-4.0","version":VERSION}
    for key,val in expect.items():
        if meta.get(key)!=val:raise ValueError("HEFEI20KM_METADATA_DRIFT:"+key)
    info=inspect(dest/NAME)
    for key,val in info.items():
        if meta.get(key)!=val:raise ValueError("HEFEI20KM_SHA_OR_COVERAGE_DRIFT:"+key)
    if not meta.get("repeat_download",{}).get("pixels_equal") or \
       not meta["repeat_download"].get("transform_equal"):
        raise ValueError("HEFEI20KM_REPEATED_SOURCE_VERIFICATION_REQUIRED")
    return info

def acquire(dest:Path,project:str)->dict:
    import ee
    import requests
    if dest.exists() or dest.is_symlink():
        raise ValueError("HEFEI20KM_DO_NOT_OVERWRITE_EXISTING_SOURCE")
    if not project:raise ValueError("EARTH_ENGINE_PROJECT_REQUIRED")
    ee.Initialize(project=project)  # only user-authenticated local invocation
    region=ee.Geometry.Rectangle(list(REQUEST),proj="EPSG:32650",geodesic=False)
    collection=ee.ImageCollection(ASSET).filterBounds(region).sort("system:index",True)
    ids=collection.aggregate_array("system:id").getInfo()
    if not ids:raise ValueError("HEFEI20KM_GEE_NO_SOURCE_TILE")
    image=collection.mosaic().select(BAND)
    def download(path:Path):
        try:
            signed=image.getDownloadURL({
                "region":region,"crs":"EPSG:32650","scale":30,
                "format":"GEO_TIFF","filePerBand":False})
            with requests.get(signed,stream=True,timeout=(30,180)) as resp:
                resp.raise_for_status()
                total=0
                with path.open("xb") as f:
                    for chunk in resp.iter_content(1<<16):
                        if not chunk:continue
                        total+=len(chunk)
                        if total>MAX_DOWNLOAD:
                            raise RuntimeError("HEFEI20KM_OVERSIZE_REQUIRES_TILED_DOWNLOAD")
                        f.write(chunk)
        except Exception:
            # Google signed download URLs and authentication are confidential.
            raise RuntimeError("HEFEI20KM_EARTH_ENGINE_DOWNLOAD_FAILED_NO_URL_LOGGED") from None
    with tempfile.TemporaryDirectory(prefix="cteas-issue160-hefei20km-") as tmp:
        a,b=Path(tmp)/"first.tif",Path(tmp)/"second.tif"
        download(a)
        info=inspect(a)
        download(b)
        info2=inspect(b)
        with rasterio.open(a) as aa,rasterio.open(b) as bb:
            equal=np.array_equal(aa.read(1),bb.read(1)) and \
                  np.array_equal(aa.read_masks(1),bb.read_masks(1))
        if not equal or info["transform"]!=info2["transform"] or \
           info["pixel_sha256"]!=info2["pixel_sha256"]:
            raise ValueError("HEFEI20KM_REPEATED_SOURCE_MISMATCH")
        dest.mkdir(parents=True)
        (dest/NAME).write_bytes(a.read_bytes())
        meta={**info,"status":"HEFEI_20KM_2022_GLC30M_REAL_SOURCE_VERIFIED",
              "site":"hefei","grid_epsg":EPSG,
              "grid_utm_bounds_m":list(BOUNDS),
              "requested_bounds_with_60m_buffer_m":list(REQUEST),
              "asset_path":ASSET,"source_band":BAND,
              "year":YEAR,"license":"CC-BY-4.0","version":VERSION,
              "image_ids":ids,
              "source":"GLC_FCS30D annual 2022 b23 community EE catalog",
              "doi":"10.5281/zenodo.8239305",
              "mosaic_order":"system:index ascending; last valid source pixel",
              "download_utc":datetime.now(timezone.utc).isoformat(),
              "resampling":"nearest-neighbor categorical; no source relabeling",
              "repeat_download":{"pixels_equal":True,
                                 "transform_equal":True,
                                 "second_sha256":info2["sha256"]},
              "original_glcc_mapping_modified":False,
              "p2c_sampling_science":"NOT_RUN"}
        (dest/"metadata.json").write_text(json.dumps(meta,indent=2)+"\n")
        (dest/"ATTRIBUTION.md").write_text(
            "# GLC-FCS30D 2022 b23 Hefei full 20 km source\n\n"
            "GLC_FCS30D community annual collection. Data CC BY 4.0; "
            "DOI 10.5281/zenodo.8239305.\n"
            "The source is unmodified categorical data, not P2-C model output.\n")
    return verify(dest)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=["download","verify","geometry"])
    p.add_argument("--directory",type=Path,default=DEFAULT)
    p.add_argument("--ee-project",default="cteas-earthengine")
    a=p.parse_args()
    try:
        if a.mode=="geometry":
            print(json.dumps({"site":"hefei","epsg":EPSG,
                              "model_bounds_m":BOUNDS,
                              "request_bounds_m":REQUEST},indent=2))
            return
        result=(acquire(a.directory,a.ee_project) if a.mode=="download"
                else verify(a.directory))
        print(json.dumps(result,indent=2))
    except Exception as exc:
        # no signed URL/token or third-party raw response in the log
        p.exit(2,"ISSUE160_HEFEI20KM_SOURCE_FAIL_CLOSED:"+type(exc).__name__+"\n")

if __name__=="__main__":
    main()

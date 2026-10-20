#!/usr/bin/env python3
"""#160 C4 exact Hefei 20x20 km GLC_FCS30D 2022 30m source acquisition.

The old 172x172 Hefei 5km raster is explicitly NOT a valid input.
Online Earth Engine authentication/project must already be configured by
the operator; credentials, URLs and original image bytes are never logged.
The two download attempts must be pixel/metadata-identical. This utility
does not manufacture a 20km source from the old 5km crop.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path
import tempfile
import numpy as np
import rasterio
from pyproj import Transformer
from scripts.s2g.glc_fcs30d_acquire import CLASSES,FILL,ASSET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"data/landcover/glc_fcs30d/v1_2022/hefei20km"
NAME="hefei_2022_30m_20km.tif"
CENTER=(117.141610855,31.939774444)
EPSG=32650
X0=503385.
Y0=3523769.
D=100.
N=200
BUFFER=60.

def require(ok,reason):
    if not ok:raise ValueError("P2C_HEFEI20KM_"+reason)

def sha(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()

def geometry():
    utm=Transformer.from_crs(4326,EPSG,always_xy=True)
    center_x,center_y=utm.transform(*CENTER)
    require(round(center_x-10000.)==X0 and
            round(center_y-10000.)==Y0 and
            abs(X0+10000.-center_x)<=.5 and
            abs(Y0+10000.-center_y)<=.5,
            "FROZEN_CENTER_UTM_1M_ROUNDING")
    grid=[X0,Y0,X0+N*D,Y0+N*D]
    bbox=[grid[0]-BUFFER,grid[1]-BUFFER,
          grid[2]+BUFFER,grid[3]+BUFFER]
    to_geo=Transformer.from_crs(EPSG,4326,always_xy=True)
    def corners(q):
        p=((q[0],q[1]),(q[2],q[1]),(q[2],q[3]),
           (q[0],q[3]),(q[0],q[1]))
        return [list(to_geo.transform(*xy)) for xy in p]
    return {"site":"HEFEI_20KM_INLAND_2022_P2C",
            "utm_epsg":EPSG,"nx":N,"ny":N,"step_m":D,
            "xrefkm":"503.385","yrefkm":"3523.769",
            "center_wgs84_lon":CENTER[0],"center_wgs84_lat":CENTER[1],
            "center_offset_east_m":X0+10000.-center_x,
            "center_offset_north_m":Y0+10000.-center_y,
            "model_bounds_utm_m":grid,"buffer_m":BUFFER,
            "buffer_bounds_utm_m":bbox,
            "buffer_corners_wgs84":corners(bbox)}

def inspect(source:Path,geom:dict):
    require(source.is_file() and not source.is_symlink() and
            0<source.stat().st_size<64*1024*1024,
            "MISSING_OR_INVALID_SIZE_TIFF")
    with rasterio.open(source) as d:
        require(d.driver=="GTiff" and d.count==1 and
                d.crs is not None and d.crs.to_epsg()==EPSG and
                d.dtypes[0]=="uint8","TIFF_FORMAT_CRS_DTYPE")
        a,b,c,d0,e,f=d.transform[:6]
        require(a==30. and b==0 and d0==0 and e==-30.,
                "NORTH_UP_30M_AFFINE")
        bounds=d.bounds
        q=geom["buffer_bounds_utm_m"]
        require(bounds.left<=q[0] and bounds.bottom<=q[1] and
                bounds.right>=q[2] and bounds.top>=q[3],
                "FULL_20KM_PLUS_BUFFER_COVERAGE")
        data=d.read(1)
        valid=(d.read_masks(1)!=0)&~np.isin(data,list(FILL))
        bad=set(map(int,np.unique(data[valid])))-CLASSES
        require(not bad and valid.any(),"UNEXPECTED_CLASS_OR_NO_VALID_PIXELS")
        vals,n=np.unique(data[valid],return_counts=True)
        return {"crs":d.crs.to_string(),"pixel_resolution_m":[a,-e],
                "transform":list(d.transform)[:6],
                "bounds":[bounds.left,bounds.bottom,bounds.right,bounds.top],
                "width":d.width,"height":d.height,
                "dtype":d.dtypes[0],"nodata":d.nodata,
                "valid_pixel_count":int(valid.sum()),
                "nodata_or_fill_count":int((~valid).sum()),
                "classes_histogram":{str(int(v)):int(count) for v,count in zip(vals,n)},
                "source_glc210_pixel_count":int((valid&(data==210)).sum()),
                "pixel_sha256":hashlib.sha256(data.tobytes()).hexdigest(),
                "sha256":sha(source),"size_bytes":source.stat().st_size}

def acquire(directory:Path,project:str):
    require(not directory.exists() and not directory.is_symlink(),
            "DESTINATION_ALREADY_EXISTS")
    require(bool(project.strip()),"EXPLICIT_EARTH_ENGINE_PROJECT_REQUIRED")
    import ee,requests
    g=geometry()
    ee.Initialize(project=project)
    region=ee.Geometry.Rectangle(g["buffer_bounds_utm_m"],proj="EPSG:32650",geodesic=False)
    images=ee.ImageCollection(ASSET).filterBounds(region).sort("system:index",True)
    ids=images.aggregate_array("system:id").getInfo()
    require(bool(ids),"NO_INTERSECTING_GLC_ASSET")
    source=images.mosaic().select("b23")
    def get(path):
        try:
            url=source.getDownloadURL(
                {"region":region,"crs":"EPSG:32650","scale":30,
                 "format":"GEO_TIFF","filePerBand":False})
            with requests.get(url,stream=True,timeout=(30,240)) as resp:
                require(resp.status_code==200,"DOWNLOAD_HTTP_NOT_200")
                size=0
                with path.open("xb") as out:
                    for block in resp.iter_content(65536):
                        size+=len(block)
                        require(size<=64*1024*1024,"DOWNLOAD_OVERSIZE")
                        out.write(block)
        except Exception:
            # Cloud signed URLs are never printed, even on failure.
            raise RuntimeError("P2C_HEFEI20KM_EE_DOWNLOAD_FAILED") from None
    with tempfile.TemporaryDirectory(prefix="p2c-hefei20km-") as temp:
        a,b=Path(temp)/"first.tif",Path(temp)/"second.tif"
        get(a);info=inspect(a,g)
        get(b);other=inspect(b,g)
        with rasterio.open(a) as ra,rasterio.open(b) as rb:
            same_pixels=(np.array_equal(ra.read(1),rb.read(1)) and
                         np.array_equal(ra.read_masks(1),rb.read_masks(1)))
        require(same_pixels and info==other,"REPEAT_SOURCE_NONDETERMINISM")
        metadata={**g,**info,
                  "year":2022,"band":"b23","source":ASSET,
                  "image_ids":ids,"mosaic_order":"system:index ascending; last valid pixel wins",
                  "license":"CC-BY-4.0","doi":"10.5281/zenodo.8239305",
                  "repeat_download":{"pixels_equal":same_pixels,
                                     "metadata_equal":info==other,
                                     "second_sha256":other["sha256"]},
                  "acquired_utc":datetime.now(timezone.utc).isoformat(),
                  "acquisition_script_sha256":sha(Path(__file__)),
                  "dependencies":{k:importlib.metadata.version(k)
                                   for k in ("earthengine-api","numpy","rasterio","pyproj","requests")},
                  "p2c_original_sampling":"NOT_RUN",
                  "independent_integer_hits":"NOT_RUN"}
        directory.mkdir(parents=True)
        (directory/NAME).write_bytes(a.read_bytes())
        (directory/"metadata.json").write_text(json.dumps(metadata,indent=2)+"\n")
    return verify(directory)

def verify(directory:Path):
    g=geometry()
    metadata=json.loads((directory/"metadata.json").read_text())
    for key,v in g.items():require(metadata.get(key)==v,"GEOMETRY_DRIFT_"+key)
    actual=inspect(directory/NAME,g)
    for key,v in actual.items():require(metadata.get(key)==v,"SOURCE_DRIFT_"+key)
    require(metadata.get("year")==2022 and metadata.get("band")=="b23" and
            metadata.get("source")==ASSET and
            metadata.get("repeat_download",{}).get("pixels_equal") is True and
            metadata.get("repeat_download",{}).get("metadata_equal") is True,
            "UNVERIFIED_SOURCE_PROVENANCE")
    return {"gate":"HEFEI_20KM_GLC_FCS30D_2022_SOURCE_VERIFIED",
            "sha256":actual["sha256"],
            "width":actual["width"],"height":actual["height"],
            "water210_source_pixels":actual["source_glc210_pixel_count"],
            "actual_source_science":"SOURCE_ONLY_NOT_P2C_SCIENCE"}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("command",choices=("geometry","acquire","verify"))
    p.add_argument("--project",default="")
    p.add_argument("--directory",type=Path,default=OUT)
    a=p.parse_args()
    try:
        result=(geometry() if a.command=="geometry" else
                acquire(a.directory,a.project) if a.command=="acquire" else
                verify(a.directory))
        print(json.dumps(result,indent=2))
        return 0
    except (ValueError,OSError,RuntimeError) as exc:
        print(f"P2C_HEFEI20KM_FAIL_CLOSED:{exc}",file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())

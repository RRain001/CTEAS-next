"""#54 D2: strict byte + spatial admission for six already documented SRTM90m tiles.

This is NOT CGIAR product-version/licence/vertical-datum certification, and
never downloads, copies, uncompresses or executes P1 on DEM data.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

from scripts.s2g.p1_terrain_source import case_bbox, check_raster, P1SourceError

TILE_SIZE=72_096_675
WIDTH=HEIGHT=6000
ANGULAR_STEP=1/1200
# These are exact source-vs-upload hashes recorded by the owner on 2026-10-18.
# They prove byte identity with those supplied files, NOT their provider/version.
APPROVED={
 "srtm_59_06.tif":("b125fb513b951fcee4c78c8c94696eab9fea70808415565021f09945eed5f1bc",110,115,30,35),
 "srtm_59_07.tif":("f4e462c5d6019d3d5ced317c1db9bcd3252772878fd3493bf2c08ebfbf2054b1",110,115,25,30),
 "srtm_60_06.tif":("913a082c79df74ff4189fec9d94b678618b395a6fb0a64ee94e14c532362eae4",115,120,30,35),
 "srtm_60_07.tif":("5f159eea3fde8b085160f046572447941b1f1f55a1c4b1bb07c5780e81e82931",115,120,25,30),
 "srtm_61_06.tif":("99487ab48089698bc2087356221b6282ed33319674d2356b2f02e49e1f5473cf",120,125,30,35),
 "srtm_61_07.tif":("a0d97c11e2d53b8c78a05ac8488a6dadd603c27f32e32c493a7e08a928222acd",120,125,25,30),
}
MAX_LON=(110.0,125.0)
MAX_LAT=(25.0,35.0)
EPS=1e-9

class D2AssetError(ValueError):
    pass

def required_names(box:dict)->list[str]:
    vals=[box.get(k) for k in ("west","east","south","north")]
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in vals):
        raise D2AssetError("invalid geographic footprint")
    west,east,south,north=vals
    if west>=east or south>=north:
        raise D2AssetError("invalid geographic footprint")
    if (west<MAX_LON[0]-EPS or east>MAX_LON[1]+EPS or
        south<MAX_LAT[0]-EPS or north>MAX_LAT[1]+EPS):
        raise D2AssetError("buffered case exceeds verified six-tile coverage")
    needed=[]
    for name,(_,left,right,bottom,top) in APPROVED.items():
        if min(east,right)-max(west,left)>EPS and min(north,top)-max(south,bottom)>EPS:
            needed.append(name)
    if not needed:
        raise D2AssetError("no approved 90m tile intersects this grid")
    return sorted(needed)

def admit(grid:Path, directory:Path, *,buffer_m:float=500.0)->dict:
    if directory.is_symlink() or not directory.is_dir():
        raise D2AssetError("SRTM directory must be an independent real directory")
    box=case_bbox(grid,buffer_m)
    needed=required_names(box)
    verified=[]
    for name in needed:
        path=directory/name
        if path.is_symlink() or not path.is_file():
            raise D2AssetError("expected real 90m TIFF absent or symlinked: "+name)
        size=path.stat().st_size
        if size==133 or size<512:
            raise D2AssetError("Git LFS pointer or truncated file: "+name)
        if size!=TILE_SIZE:
            raise D2AssetError("unexpected supplied 90m tile size: "+name)
        props=check_raster(path)
        sha,left,right,bottom,top=APPROVED[name]
        if props["sha256"]!=sha or props["bytes"]!=TILE_SIZE:
            raise D2AssetError("owner-supplied tile SHA mismatch: "+name)
        if props["width"]!=WIDTH or props["height"]!=HEIGHT:
            raise D2AssetError("tile dimensions differ from owner metadata: "+name)
        if any(abs(s-ANGULAR_STEP)>1e-10 for s in props["resolution_degrees"]):
            raise D2AssetError("tile pixel angle is not 3 arc-seconds: "+name)
        if any(abs(a-b)>1e-8 for a,b in zip(props["bounds"],(left,bottom,right,top))):
            raise D2AssetError("tile WGS84 bounds differ from supplied metadata: "+name)
        verified.append({"name":name,"sha256":props["sha256"],"bytes":size,
                         "nodata_sentinel":props["nodata"],"bounds":props["bounds"]})
    return {
      "schema_version":"p1-90m-six-tile-owner-byte-admission-v1",
      "status":"P1_A_OWNER_SUPPLIED_TIFF_BYTES_AND_GEOMETRY_VERIFIED_ONLY",
      "required_tiles":verified,
      "case_bbox_wgs84":box,
      "source_product_version":"NOT_AUTHENTICATED",
      "vertical_datum_and_elevation_units":"NOT_AUTHENTICATED",
      "redistribution_rights":"NOT_ESTABLISHED_BY_THIS_CHECK",
      "case_dem_voids":"NOT_CHECKED_MOSAIC_ADAPTER_REQUIRED",
      "native_p1":"NOT_RUN",
      "original_terrel_parity":"NOT_RUN",
      "science_acceptance":"NOT_ACCEPTED"
    }

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--grid",required=True,type=Path)
    p.add_argument("--tif-dir",required=True,type=Path)
    p.add_argument("--buffer-m",type=float,default=500.0)
    p.add_argument("--report",required=True,type=Path)
    a=p.parse_args(argv)
    try:
        if a.report.exists() or a.report.is_symlink():
            raise D2AssetError("report exists; evidence must not be overwritten")
        result=admit(a.grid,a.tif_dir,buffer_m=a.buffer_m)
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        print(json.dumps({"status":result["status"],"required_tile_count":len(result["required_tiles"]),
                          "science_acceptance":result["science_acceptance"]}))
        return 0
    except (D2AssetError,P1SourceError,OSError,ValueError) as e:
        print(json.dumps({"status":"BLOCKED_REAL_90M_ADMISSION","reason":type(e).__name__,
                          "science_acceptance":"NOT_ACCEPTED"}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())

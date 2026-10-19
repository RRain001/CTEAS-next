#!/usr/bin/env python3
"""Issue #119 Wolsong coastal P2-B source acquisition and *independent* shoreline gate.

Coast diagnostics use authentic GSHHS Full L1 geometry, without requiring GLC.
Earth Engine downloads are explicitly local/user-authenticated; never CI credentials.
Neither check is a P2/P3 numerical science acceptance.
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

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "data/landcover/glc_fcs30d/v1_2022/wolsong"
NAME = "wolsong_2022_30m.tif"
EPSG = 32652
X0, Y0 = 533215., 3942629.
NX = NY = 200
STEP = 100.
YEAR, BAND = 2022, "b23"
BUFFER = 60.
GRID = [X0, Y0, X0 + NX * STEP, Y0 + NY * STEP]
BUFFERED = [GRID[0]-BUFFER, GRID[1]-BUFFER, GRID[2]+BUFFER, GRID[3]+BUFFER]
TOTAL_AREA = float(NX * NY) * STEP * STEP
TRAN = Transformer.from_crs(EPSG, 4326, always_xy=True)
BASE = {
    "region": "Wolsong coastal-candidate 20km grid, South Korea",
    "epsg": EPSG, "x0_m": X0, "y0_m": Y0, "nx": NX, "ny": NY,
    "step_m": STEP, "year": YEAR, "band": BAND, "asset_path": ASSET,
    "source_version": "v1-community-gee",
    "representative_site_wgs84_lat_lon": [35.716670, 129.477780],
    "stack_location_status": "UNVERIFIED_REPRESENTATIVE_SITE_NOT_EXACT_STACK",
}

def corners(bounds):
    x0, y0, x1, y1 = bounds
    return [list(TRAN.transform(x, y)) for x, y in
            ((x0,y0),(x1,y0),(x1,y1),(x0,y1))]

BASE.update({
    "wgs84_corners": corners(GRID),
    "buffered_utm_bounds_m": BUFFERED,
})

def inspect(tif: Path) -> dict:
    """Every *positive-area* source-pixel overlap must have a valid GLC class."""
    if not tif.is_file() or not 0 < tif.stat().st_size < 32 * 1024 * 1024:
        raise ValueError("WOLSONG_GLC_TIFF_MISSING_OR_OVERSIZE")
    with rasterio.open(tif) as ds:
        t = ds.transform
        if ds.driver != "GTiff" or ds.count != 1 or ds.crs is None or ds.crs.to_epsg() != EPSG:
            raise ValueError("WOLSONG_GLC_SINGLE_BAND_UTM52N_REQUIRED")
        if not np.issubdtype(np.dtype(ds.dtypes[0]), np.integer):
            raise ValueError("WOLSONG_GLC_INTEGER_CLASSES_REQUIRED")
        if not np.allclose([t.a,t.b,t.d,t.e], [30,0,0,-30], rtol=0, atol=1e-8):
            raise ValueError("WOLSONG_GLC_30M_NORTH_UP_REQUIRED")
        bbox = [ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top]
        if not (bbox[0] <= GRID[0] and bbox[1] <= GRID[1] and
                bbox[2] >= GRID[2] and bbox[3] >= GRID[3]):
            raise ValueError("WOLSONG_GLC_DOMAIN_NOT_COVERED")
        data = ds.read(1)
        if not set(map(int, np.unique(data))) <= CLASSES | FILL:
            raise ValueError("WOLSONG_GLC_UNKNOWN_CATEGORY")
        invalid = (ds.read_masks(1) == 0) | np.isin(data, list(FILL))
        # Explicit exact positive-area overlap (30m is not a divisor of 100m).
        xlo = t.c + np.arange(ds.width) * t.a
        xhi = xlo + t.a
        yhi = t.f - np.arange(ds.height) * (-t.e)
        ylo = yhi + t.e
        xover = np.maximum(0., np.minimum(xhi, GRID[2])-np.maximum(xlo, GRID[0]))
        yover = np.maximum(0., np.minimum(yhi, GRID[3])-np.maximum(ylo, GRID[1]))
        area = yover[:, None] * xover[None, :]
        if abs(float(area.sum())-TOTAL_AREA) > 0.02:
            raise ValueError("WOLSONG_GLC_SOURCE_AREA_NOT_COVERED")
        missing = float(area[invalid].sum())
        if missing > 1e-7:
            raise ValueError("WOLSONG_GLC_MASK_OR_FILL_INTERSECTS_MODEL_GRID")
        water = float(area[data == 210].sum())
        return {
            "sha256": sha(tif), "size_bytes": tif.stat().st_size,
            "crs": ds.crs.to_string(), "width": ds.width, "height": ds.height,
            "bounds_utm_m": bbox, "transform": list(t)[:6],
            "pixel_resolution": [t.a,-t.e], "dtype": ds.dtypes[0],
            "nodata": ds.nodata, "modelgrid_valid_source_area_m2": float(area.sum()),
            "modelgrid_invalid_source_area_m2": missing,
            "modelgrid_intersecting_pixels": int(np.count_nonzero(area > 0)),
            "modelgrid_glc210_source_area_m2": water,
            "modelgrid_coverage_ok": missing == 0.,
            "glc210_coverage_ok": water > 0.,
            "pixel_sha256": hashlib.sha256(data.tobytes()).hexdigest(),
            "source_only_status": "REAL_GLC_SOURCE_NOT_COASTAL_SCIENCE",
        }

def _same_wgs84_corners(actual, expected) -> bool:
    """Allow only projection roundoff across PROJ versions (1e-7 degree, ~1 cm).

    The metric UTM grid and source identifiers remain exact. Never relax
    geographic coordinate ordering, numeric validity, or actual location drift.
    """
    return (
        isinstance(actual, list) and len(actual) == len(expected) == 4
        and all(
            isinstance(pair, list) and len(pair) == len(reference) == 2
            and all(
                type(found) in (int, float)
                and math.isfinite(found)
                and abs(found - original) <= 1e-7
                for found, original in zip(pair, reference)
            )
            for pair, reference in zip(actual, expected)
        )
    )

def verify(directory: Path) -> dict:
    meta = json.loads((directory/"metadata.json").read_text(encoding="utf-8"))
    for key, value in BASE.items():
        if key == "wgs84_corners":
            if not _same_wgs84_corners(meta.get(key), value):
                raise ValueError("WOLSONG_GRID_OR_SOURCE_PROVENANCE_DRIFT:" + key)
        elif meta.get(key) != value:
            raise ValueError("WOLSONG_GRID_OR_SOURCE_PROVENANCE_DRIFT:" + key)
    info = inspect(directory/NAME)
    for key, value in info.items():
        if meta.get(key) != value:
            raise ValueError("WOLSONG_RASTER_SHA_OR_COVERAGE_DRIFT:" + key)
    if meta.get("license") != "CC-BY-4.0" or not meta.get("repeat_download",{}).get("pixels_equal"):
        raise ValueError("WOLSONG_GLC_SOURCE_PROVENANCE_INCOMPLETE")
    return info

def acquire(directory: Path, ee_project: str) -> dict:
    if directory.exists():
        raise ValueError("WOLSONG_DESTINATION_EXISTS_REFUSE_OVERWRITE")
    import ee
    import requests
    ee.Initialize(project=ee_project)  # Must be authenticated on user's machine.
    region = ee.Geometry.Rectangle(BUFFERED, proj="EPSG:32652", geodesic=False)
    col = ee.ImageCollection(ASSET).filterBounds(region).sort("system:index", True)
    ids = col.aggregate_array("system:id").getInfo()
    if not ids:
        raise ValueError("WOLSONG_NO_GLC2022_SOURCE_TILE")
    image = col.mosaic().select(BAND)
    def download(target: Path):
        try:
            url = image.getDownloadURL({
                "region": region, "crs": "EPSG:32652", "scale": 30,
                "format": "GEO_TIFF", "filePerBand": False,
            })
            n = 0
            with requests.get(url, stream=True, timeout=(30,180)) as response:
                response.raise_for_status()
                with target.open("xb") as stream:
                    for chunk in response.iter_content(65536):
                        n += len(chunk)
                        if n > 32*1024*1024:
                            raise ValueError("WOLSONG_DOWNLOAD_EXCEEDS_32MB")
                        if chunk:
                            stream.write(chunk)
        except Exception:
            # Do not expose authenticated Google URLs or remote error responses.
            raise RuntimeError("WOLSONG_EARTH_ENGINE_DOWNLOAD_FAILED_NO_URL_LOGGED") from None
    with tempfile.TemporaryDirectory(prefix="cteas-wolsong-glc-") as tmp:
        first, second = Path(tmp)/"first.tif", Path(tmp)/"second.tif"
        download(first)
        a = inspect(first)
        download(second)
        b = inspect(second)
        with rasterio.open(first) as aa, rasterio.open(second) as bb:
            same = np.array_equal(aa.read(1),bb.read(1)) and np.array_equal(aa.read_masks(1),bb.read_masks(1))
        if not same or any(a[k] != b[k] for k in
                           ("crs","transform","pixel_sha256","modelgrid_glc210_source_area_m2")):
            raise ValueError("WOLSONG_GLC_REPEAT_ACQUISITION_DIFFERS")
        directory.mkdir(parents=True)
        (directory/NAME).write_bytes(first.read_bytes())
        meta = {
            **BASE, **a, "image_ids": ids, "mosaic_order": "system:index ascending; last valid pixel wins",
            "resampling": "nearest neighbour; categorical, no class replacement",
            "license": "CC-BY-4.0",
            "source_catalog": "https://gee-community-catalog.org/projects/glc_fcs/",
            "doi": "10.5281/zenodo.8239305",
            "repeat_download": {"pixels_equal": True, "second_sha256": b["sha256"]},
            "download_utc": datetime.now(timezone.utc).isoformat(),
            "script_sha256_at_download": sha(Path(__file__)),
            "coastal_science": "NOT_RUN",
        }
        (directory/"metadata.json").write_text(json.dumps(meta,indent=2)+"\n",encoding="utf-8")
        (directory/"ATTRIBUTION.md").write_text(
            "# Wolsong GLC_FCS30D 2022 source\n\nOriginal 2022 annual b23 from "
            "projects/sat-io/open-datasets/GLC-FCS30D/annual; source "
            "DOI 10.5281/zenodo.8239305; CC BY 4.0. Crop is not manually "
            "reclassified. Not a validated land/sea result.\n",encoding="utf-8")
    return verify(directory)

def coast_diagnostic(shp: Path) -> dict:
    """Union clipped Full L1 land polygons before computing land area; log failure evidence."""
    from osgeo import ogr, osr
    if shp.name != "GSHHS_f_L1.shp" or not shp.is_file():
        raise ValueError("WOLSONG_REQUIRES_GSHHS_FULL_L1")
    ds = ogr.Open(str(shp))
    if ds is None or ds.GetLayerCount() != 1:
        raise ValueError("WOLSONG_GSHHG_OPEN_FAILED")
    layer = ds.GetLayer(0)
    source = layer.GetSpatialRef()
    target = osr.SpatialReference()
    target.ImportFromEPSG(4326)
    target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if source is None or not bool(source.IsSame(target)):
        raise ValueError("WOLSONG_GSHHG_WGS84_REQUIRED")
    projected = osr.SpatialReference()
    projected.ImportFromEPSG(EPSG)
    projected.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    tr = osr.CoordinateTransformation(target, projected)
    lonlat = corners(GRID)
    layer.SetSpatialFilterRect(min(v[0] for v in lonlat)-.1,
                               min(v[1] for v in lonlat)-.1,
                               max(v[0] for v in lonlat)+.1,
                               max(v[1] for v in lonlat)+.1)
    x0,y0,x1,y1 = GRID
    domain = ogr.CreateGeometryFromWkt(
        f"POLYGON(({x0} {y0},{x1} {y0},{x1} {y1},{x0} {y1},{x0} {y0}))")
    union = None
    n_selected = n_intersects = 0
    preunion = 0.
    layer.ResetReading()
    for feat in layer:
        n_selected += 1
        fg = feat.GetGeometryRef()
        if fg is None or not fg.IsValid() or ogr.GT_Flatten(fg.GetGeometryType()) not in (ogr.wkbPolygon,ogr.wkbMultiPolygon):
            raise ValueError("WOLSONG_INVALID_GSHHG_GEOMETRY")
        g = fg.Clone()
        if g.Transform(tr) != 0:
            raise ValueError("WOLSONG_GSHHG_REPROJECTION_FAILED")
        clip = g.Intersection(domain)
        if clip is None:
            raise ValueError("WOLSONG_GSHHG_CLIP_FAILED")
        if clip.IsEmpty():
            continue
        n_intersects += 1
        preunion += clip.GetArea()
        union = clip if union is None else union.Union(clip)
        if union is None or not union.IsValid():
            raise ValueError("WOLSONG_GSHHG_UNION_FAILED")
    land = 0. if union is None else float(union.GetArea())
    if not -1e-5 <= land <= TOTAL_AREA+1e-5:
        status = "INVALID_LAND_AREA"
    elif n_selected == 0:
        status = "NO_GSHHG_FEATURES_SELECTED_CHECK_SPATIAL_FILTER"
    elif land <= 100.:
        status = "NO_LAND_WITHIN_DOMAIN"
    elif TOTAL_AREA-land <= 100.:
        status = "NO_SEA_WITHIN_DOMAIN"
    else:
        status = "CROSSES_COAST"
    return {
        "status": status, "real_source_validation": "CALLER_MUST_VERIFY_GSHHG_ZIP_AND_SIDECARS",
        "site": "Wolsong", "epsg": EPSG, "grid_utm_m": GRID,
        "grid_cell_count": NX*NY, "domain_area_m2": TOTAL_AREA,
        "selected_polygon_count": n_selected, "intersecting_polygon_count": n_intersects,
        "sum_clipped_polygon_area_before_union_m2": preunion,
        "union_land_area_m2": land, "sea_area_m2": TOTAL_AREA-land,
        "union_overlap_double_count_m2": preunion-land,
        "study_bbox_lonlat": [min(v[0] for v in lonlat),min(v[1] for v in lonlat),
                             max(v[0] for v in lonlat),max(v[1] for v in lonlat)],
        "source_shp_sha256": sha(shp),
        "p2b_52_55_sci_status": "NOT_RUN",
    }

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("download","verify","coast"))
    p.add_argument("--directory",type=Path,default=DEFAULT)
    p.add_argument("--ee-project",default="cteas-earthengine")
    p.add_argument("--gshhs-shp",type=Path)
    p.add_argument("--report",type=Path)
    args = p.parse_args()
    try:
        if args.mode == "coast":
            if args.gshhs_shp is None:
                raise ValueError("WOLSONG_GSHHG_PATH_REQUIRED")
            result = coast_diagnostic(args.gshhs_shp)
            if args.report:
                args.report.parent.mkdir(parents=True,exist_ok=True)
                args.report.write_text(json.dumps(result,indent=2)+"\n")
            print(json.dumps(result,sort_keys=True),flush=True)
            return 0 if result["status"]=="CROSSES_COAST" else 2
        result = acquire(args.directory,args.ee_project) if args.mode=="download" else verify(args.directory)
        print(json.dumps(result,sort_keys=True))
        return 0
    except Exception as exc:
        print("WOLSONG_P2B_FAIL_CLOSED:"+type(exc).__name__+":"+str(exc)[:100],file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())

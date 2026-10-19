#!/usr/bin/env python3
"""P1 source admission: multiple local WGS84 GeoTIFFs OR OpenTopography SRTMGL1/SRTMGL3.

No P1 physics is executed: current native P1 still has a frozen Hefei-only
50x50 / UTM50N solver. This entry point provides one audited GeoTIFF that
future dynamic native P1 can consume, not a scientific acceptance claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import urllib.error
import urllib.parse
import urllib.request

import numpy as np
import rasterio
from affine import Affine
from rasterio.crs import CRS
from rasterio.merge import merge
from rasterio.windows import Window, from_bounds, bounds as window_bounds

from engine.run_met.station_grid import load_strict_utm_grid
from rasterio.warp import transform as project_coords

BASE = "https://portal.opentopography.org/API/globaldem"
DATASET = "SRTMGL1"  # Historic API default; existing callers remain 30m.
DEM_PRODUCTS = {
    "SRTMGL1": {"arcsec": 1.0, "max_area_km2": 450_000.0, "filename": "srtmgl1_30m.tif"},
    "SRTMGL3": {"arcsec": 3.0, "max_area_km2": 4_050_000.0, "filename": "srtmgl3_90m.tif"},
}
# Official *dataset-level* provenance, not a per-tile cryptographic
# authentication. EPSG:4326 is horizontal; EPSG:5773 is EGM96 geoid height,
# NOT WGS84 ellipsoidal height. Source pixels are never vertically converted.
SRTMGL3_OFFICIAL_DOCUMENTATION = {
    "provider": "OpenTopography",
    "provider_product": "SRTM_GL3",
    "provider_collection_id": "OT.042013.4326.1",
    "provider_collection_uri":
        "https://portal.opentopography.org/datasetMetadata?otCollectionID=OT.042013.4326.1",
    "nasa_product_family": "SRTMGL3.003",
    "nasa_product_doi": "10.5067/MEASURES/SRTM/SRTMGL3.003",
    "nasa_product_uri": "https://doi.org/10.5067/MEASURES/SRTM/SRTMGL3.003",
    "source_horizontal_crs": "EPSG:4326",
    "declared_vertical_crs": "EPSG:5773",
    "declared_vertical_datum": "EGM96 geoid",
    "declared_vertical_units": "m",
    "vertical_reference_uri":
        "https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm",
    "evidence_level": "OFFICIAL_COLLECTION_METADATA_ONLY",
    "tile_matches_independent_nasa_granule": False,
    "tile_independent_published_checksum_verified": False,
    "tiff_embedded_vertical_crs_verified": False,
    "vertical_conversion_applied": False,
}

SECRET_ENV = "OPENTOPOGRAPHY_API_KEY"
MAX_AREA_KM2 = 450_000.0  # Legacy 30m contract.
MAX_RESPONSE_BYTES = 500_000_000
MAX_OUTPUT_PIXELS = 30_000_000


class P1SourceError(ValueError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as src:
        for block in iter(lambda: src.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def case_bbox(grid_path: Path, buffer_m: float = 500.0) -> dict[str, float]:
    if not math.isfinite(buffer_m) or not 0 <= buffer_m <= 10_000:
        raise P1SourceError("P1 terrain buffer must be between 0 and 10,000 meters")
    if grid_path.is_symlink():
        raise P1SourceError("P1 grid.cmn cannot be a symlink")
    grid = load_strict_utm_grid(grid_path, context="P1 source")
    x0, y0 = grid.xrefkm * 1000, grid.yrefkm * 1000
    x1 = x0 + grid.nx * grid.dgridkm * 1000
    y1 = y0 + grid.ny * grid.dgridkm * 1000
    xs, ys = [], []
    # Densify the perimeter rather than just four corners; curved UTM
    # edge projection must not undercut the geographic raster footprint.
    for k in range(11):
        t = k / 10
        xs.extend((x0 + t * (x1-x0), x0 + t * (x1-x0), x0, x1))
        ys.extend((y0, y1, y0 + t * (y1-y0), y0 + t * (y1-y0)))
    utm = f"EPSG:{32600 + grid.iutmzn if grid.lsohem == 'N' else 32700 + grid.iutmzn}"
    lons, lats = project_coords(utm, "EPSG:4326", xs, ys)
    if any(not math.isfinite(v) for v in [*lons, *lats]):
        raise P1SourceError("nonfinite WGS84 projected bbox")
    south, north = min(lats), max(lats)
    west, east = min(lons), max(lons)
    # Explicit geodetic margin, conservative at higher latitudes.
    dlat = buffer_m / 110_500
    coslat = math.cos(math.radians(max(abs(south), abs(north)) + dlat))
    if coslat < .1:
        raise P1SourceError("near-pole WGS84 bbox outside supported P1 region")
    dlon = buffer_m / (111_000 * coslat)
    box = dict(west=west-dlon, east=east+dlon, south=south-dlat, north=north+dlat)
    if (box["west"] < -180 or box["east"] > 180 or
            box["south"] < -90 or box["north"] > 90 or
            box["west"] >= box["east"] or box["south"] >= box["north"]):
        raise P1SourceError("invalid/antimeridian-crossing P1 case bbox")
    return box


def _expected_output_pixels(bbox: dict[str, float], approx_arcsec: float = 1.0) -> int:
    dx = (bbox["east"]-bbox["west"]) * 3600 / approx_arcsec
    dy = (bbox["north"]-bbox["south"]) * 3600 / approx_arcsec
    return math.ceil(dx+2) * math.ceil(dy+2)


def check_raster(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise P1SourceError("P1 local GeoTIFF must exist and not be a symlink")
    try:
        with rasterio.open(path) as ds:
            if (ds.driver != "GTiff" or ds.count != 1 or
                    ds.dtypes[0] != "int16" or ds.crs != CRS.from_epsg(4326)):
                raise P1SourceError(
                    "P1 native reader requires single-band Int16 WGS84 EPSG:4326 GeoTIFF")
            tr = ds.transform
            if (tr.a <= 0 or tr.e >= 0 or
                    abs(tr.b) > 1e-12 or abs(tr.d) > 1e-12 or
                    not all(math.isfinite(x) for x in tuple(tr)[:6])):
                raise P1SourceError("rotated/south-up/nonfinite GeoTIFF source unsupported")
            if (ds.nodata is None or not math.isfinite(ds.nodata) or
                    not -32768 <= ds.nodata <= 32767 or
                    ds.nodata != int(ds.nodata)):
                raise P1SourceError("P1 source missing valid int16 NoData metadata")
            if not -180 <= ds.bounds.left < ds.bounds.right <= 180 or not -90 <= ds.bounds.bottom < ds.bounds.top <= 90:
                raise P1SourceError("P1 source geographic bounds invalid")
            return {"path": str(path.absolute()), "sha256": sha256(path),
                    "bytes": path.stat().st_size, "width": ds.width, "height": ds.height,
                    "resolution_degrees": [tr.a, abs(tr.e)], "bounds": list(ds.bounds),
                    "nodata": int(ds.nodata)}
    except (rasterio.errors.RasterioError, OSError) as exc:
        # Avoid embedding arbitrary paths containing credentials in errors.
        raise P1SourceError("P1 GeoTIFF corrupt or unreadable") from None


def _covers_box(ds, bbox: dict[str, float]) -> bool:
    b = ds.bounds
    tol = 1e-8
    return (b.left <= bbox["west"] + tol and b.right >= bbox["east"] - tol
            and b.bottom <= bbox["south"] + tol and b.top >= bbox["north"] - tol)


def _source_list(tifs: list[Path], directory: Path | None) -> list[Path]:
    chosen = list(tifs)
    if directory is not None:
        if not directory.is_dir() or directory.is_symlink():
            raise P1SourceError("--tif-dir must be a real directory")
        chosen.extend(sorted(directory.glob("*.tif")))
        chosen.extend(sorted(directory.glob("*.tiff")))
    paths = sorted({p.absolute() for p in chosen})
    if not paths:
        raise P1SourceError("local P1 requires one or more --tif files or --tif-dir")
    if len(paths) > 200:
        raise P1SourceError("more than 200 input TIFs; split source staging")
    return paths


def _same_source_lattice(reference, source) -> bool:
    r, s = reference.transform, source.transform
    if abs(r.a-s.a) > 1e-10 or abs(r.e-s.e) > 1e-10:
        return False
    return (abs((s.c-r.c)/r.a - round((s.c-r.c)/r.a)) < 1e-5 and
            abs((s.f-r.f)/r.e - round((s.f-r.f)/r.e)) < 1e-5)


def _copy_equal_only(merged_data, new_data, merged_mask, new_mask, **kwargs):
    del kwargs
    both = ~merged_mask & ~new_mask
    if np.any(merged_data[both] != new_data[both]):
        raise P1SourceError("overlapping local source GeoTIFF pixels disagree")
    use = merged_mask & ~new_mask
    merged_data[use] = new_data[use]


def _build_local_mosaic(paths: list[Path], bbox: dict, destination: Path,
                        *, max_pixels: int) -> None:
    sources = []
    try:
        for path in paths:
            sources.append(rasterio.open(path))
        ref = sources[0]
        for src in sources[1:]:
            if not _same_source_lattice(ref, src):
                raise P1SourceError(
                    "multi-TIFF P1 requires same WGS84 pixel spacing/alignment; no silent resampling")
            if src.nodata != ref.nodata:
                raise P1SourceError("multi-TIFF P1 requires same NoData sentinel")
        floating = from_bounds(bbox["west"],bbox["south"],bbox["east"],bbox["north"],ref.transform)
        col0, row0 = math.floor(floating.col_off), math.floor(floating.row_off)
        col1, row1 = math.ceil(floating.col_off+floating.width), math.ceil(floating.row_off+floating.height)
        width,height = col1-col0,row1-row0
        if width < 1 or height < 1 or width * height > max_pixels:
            raise P1SourceError("local P1 mosaic would exceed allowed pixel memory budget")
        footprint = Window(col0,row0,width,height)
        region = window_bounds(footprint,ref.transform)
        data, tr = merge(sources, bounds=region, res=(ref.res[0],ref.res[1]),
                         nodata=ref.nodata, method=_copy_equal_only,
                         masked=False, mem_limit=128)
        profile = ref.profile.copy()
        profile.update(driver="GTiff",width=data.shape[2],height=data.shape[1],
                       transform=tr,compress="deflate",tiled=False,count=1)
        with rasterio.open(destination, "w", **profile) as dst:
            dst.write(data)
    finally:
        for src in sources:
            src.close()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        del req,fp,code,msg,headers,newurl
        raise P1SourceError("OpenTopography unexpected redirect refused (API key protected)")


def _download_api(bbox: dict, dest: Path, key: str, *, max_bytes: int,
                  timeout: int = 150, dem: str = DATASET) -> None:
    if dem not in DEM_PRODUCTS:
        raise P1SourceError("unsupported OpenTopography DEM product")
    params = {"demtype": dem, **bbox, "outputFormat":"GTiff","API_Key":key}
    # Query string contains the user secret. NEVER log or preserve the URL.
    url = BASE + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"Accept":"image/tiff",
                                                   "User-Agent":"CTEAS-next-P1-input-only"})
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as incoming, dest.open("wb") as output:
            size = 0
            while True:
                buf = incoming.read(1024*1024)
                if not buf:
                    break
                size += len(buf)
                if size > max_bytes:
                    raise P1SourceError("OpenTopography exceeds configured byte budget")
                output.write(buf)
    except P1SourceError:
        raise
    except urllib.error.HTTPError as exc:
        # Classify only a *small, fixed vocabulary* in the provider's error
        # body. Never persist, echo or rethrow the raw response: servers may
        # include request URLs or API keys in error pages.
        try:
            response=(exc.read(8192) or b"").decode("utf-8",errors="replace").lower()
        except (OSError,ValueError):
            response=""
        if any(s in response for s in (
            "invalid api key", "invalid key", "api key is invalid",
            "apikey is not valid", "api key not valid", "unauthorized key")):
            category="API_KEY_REJECTED"
        elif any(s in response for s in (
            "rate limit", "daily limit", "quota exceeded",
            "too many requests", "request limit")):
            category="QUOTA_OR_RATE_LIMIT"
        elif any(s in response for s in (
            "invalid bounding", "invalid bbox", "bounding box",
            "request area", "area is too", "requested area")):
            category="REQUEST_BBOX_REJECTED"
        elif any(s in response for s in (
            "not available", "dataset not found", "invalid demtype",
            "unsupported dataset")):
            category="DATASET_UNAVAILABLE"
        else:
            category="UNCLASSIFIED_PROVIDER_REJECTION"
        raise P1SourceError(
            f"OpenTopography HTTP {exc.code} [{category}]; key, URL and provider body withheld"
        ) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise P1SourceError("OpenTopography network/IO error (request URL withheld)") from None
    if dest.stat().st_size < 512:
        raise P1SourceError("OpenTopography returned empty/non-TIFF response")


def prepare(grid: Path, output_dir: Path, source: str, *, tifs: list[Path] | None = None,
            tif_dir: Path | None = None, buffer_m: float = 500,
            max_pixels: int = MAX_OUTPUT_PIXELS, max_bytes: int = MAX_RESPONSE_BYTES,
            allow_nodata: bool = False,
            allow_public_bulk_fallback: bool = False,
            dem: str = DATASET) -> dict:
    if output_dir.exists() or output_dir.is_symlink():
        raise P1SourceError("P1 output directory already exists; no overwrite of source/case")
    if max_pixels < 1 or max_bytes < 512:
        raise P1SourceError("P1 byte/pixel resource limits invalid")
    bbox = case_bbox(grid, buffer_m)
    if source not in ("local", "opentopography"):
        raise P1SourceError("P1 source must be local or opentopography")
    if dem not in DEM_PRODUCTS:
        raise P1SourceError("P1 DEM product must be SRTMGL1 or SRTMGL3")
    if source == "local" and dem != DATASET:
        raise P1SourceError("--dem is only supported for OpenTopography; local TIFF source is unchanged")
    product = DEM_PRODUCTS[dem]
    if allow_public_bulk_fallback and source != "opentopography":
        raise P1SourceError("public SRTM bulk recovery belongs only to route B")
    if source == "opentopography":
        if tifs or tif_dir:
            raise P1SourceError("API source must not silently mix local TIF inputs")
        if bbox["south"] < -56 or bbox["north"] > 60:
            raise P1SourceError("SRTM available only ~56S..60N, no DEM substitute")
        area = (111.32**2 * (bbox["north"]-bbox["south"]) *
                (bbox["east"]-bbox["west"]) *
                math.cos(math.radians((bbox["south"]+bbox["north"])/2)))
        if area <= 0 or area > product["max_area_km2"]:
            raise P1SourceError("OpenTopography selected DEM exceeds product-specific API area limit")
        if _expected_output_pixels(bbox, approx_arcsec=product["arcsec"]) > max_pixels:
            raise P1SourceError("selected DEM case pixels exceed input staging memory budget")
        secret = os.environ.get(SECRET_ENV, "").strip()
        if not secret:
            raise P1SourceError("OPENTOPOGRAPHY_API_KEY is not configured")
    else:
        paths = _source_list(tifs or [], tif_dir)
        originals = [check_raster(p) for p in paths]
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(exist_ok=False)
    try:
        source_transport="opentopography_globaldem_api" if source=="opentopography" else "user_local"
        bulk_used=False
        if source == "opentopography":
            selected = output_dir / product["filename"]
            try:
                _download_api(bbox, selected, secret, max_bytes=max_bytes, dem=dem)
            except P1SourceError as exc:
                # Opt-in transport, SAME requested product, only HTTP 406.
                # Never silently switch resolution or change P1 physics.
                if (not allow_public_bulk_fallback or
                        not str(exc).startswith(
                            "OpenTopography HTTP 406 [UNCLASSIFIED_PROVIDER_REJECTION]")):
                    raise
                if selected.exists():
                    selected.unlink()
                from scripts.s2g.p1_opentopo_bulk import fetch_and_crop
                originals=fetch_and_crop(
                    bbox,output_dir/f"{dem.lower()}_bulk_tiles",selected,
                    max_pixels=max_pixels,max_bytes=max_bytes,dem=dem)
                source_transport="opentopography_official_public_s3_bulk"
                bulk_used=True
            else:
                originals = [check_raster(selected)]
        elif len(paths) == 1:
            selected = paths[0]  # direct source, no redundant crop/copy
        else:
            selected = output_dir / "p1_local_mosaic.tif"
            _build_local_mosaic(paths, bbox, selected, max_pixels=max_pixels)
        derived = check_raster(selected)
        if source == "opentopography":
            expected_degrees = product["arcsec"] / 3600.0
            if any(abs(v - expected_degrees) > 1e-9 for v in derived["resolution_degrees"]):
                raise P1SourceError("OpenTopography returned resolution inconsistent with requested DEM")
        with rasterio.open(selected) as ds:
            if not _covers_box(ds,bbox):
                raise P1SourceError("P1 source mosaic/DEM does not cover buffered case bbox")
            b = from_bounds(bbox["west"],bbox["south"],bbox["east"],bbox["north"],ds.transform)
            c0,r0 = math.floor(b.col_off), math.floor(b.row_off)
            c1,r1 = math.ceil(b.col_off+b.width), math.ceil(b.row_off+b.height)
            if (c1-c0) * (r1-r0) > max_pixels:
                raise P1SourceError("P1 source case window exceeds pixel memory budget")
            masked = ds.read(1,window=Window(c0,r0,c1-c0,r1-r0),masked=True)
            nodata_count=int(np.count_nonzero(np.ma.getmaskarray(masked)))
            valid=int(masked.size-nodata_count)
            if not valid:
                raise P1SourceError("P1 case DEM has no valid elevation pixels")
            if nodata_count and not allow_nodata:
                raise P1SourceError(
                    f"P1 DEM has {nodata_count} NoData pixels in buffered case; "
                    "use --allow-nodata only after documenting void handling")
        report = {
            "status":"P1_TERRAIN_SOURCE_VERIFIED_NATIVE_NUMERICS_NOT_RUN",
            "mode":source,"case_grid":str(grid.absolute()),
            "dataset":dem if source == "opentopography" else "USER_PROVIDED_GEOTIFF",
            "requested_resolution_arcsec":product["arcsec"] if source == "opentopography" else None,
            "transport":source_transport,
            "public_bulk_opt_in":bool(allow_public_bulk_fallback),
            "bulk_recovery_used":bulk_used,
            "api_key_logged":False,"download_request_url_logged":False,
            "source_tifs":originals,"selected_tif":str(selected.absolute()),
            "selected_tif_sha256":derived["sha256"],
            "selected_tif_properties":derived,
            "mosaic_created":(source=="local" and len(paths)>1) or bulk_used,
            "bbox_wgs84":bbox,"bbox_buffer_m":buffer_m,
            "case_window_valid_pixels":valid,
            "case_window_nodata_pixels":nodata_count,
            "nodata_allowed_explicitly":allow_nodata,
            "p1_native_science":"NOT_RUN_FROZEN_HEFEI_CLI",
            "p3_geo_dat":"NOT_RUN","p6_p7":"NOT_RUN",
            "ready_for_generic_P1_physics":False,
        }
        # Source documentation is an explicit scoped assertion, not proof
        # that public S3 GeoTIFF bytes equal an authenticated NASA granule.
        if source == "opentopography" and dem == "SRTMGL3":
            report["official_dataset_documentation"] = dict(SRTMGL3_OFFICIAL_DOCUMENTATION)
            report["source_product_version_authenticated"] = False
            report["height_vertical_datum_authenticated"] = False
        (output_dir/"p1_source_manifest.json").write_text(
            json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        return report
    except Exception:
        shutil.rmtree(output_dir)
        raise


def main(argv: list[str] | None = None) -> int:
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--grid",required=True,type=Path)
    cli.add_argument("--out-dir",required=True,type=Path)
    modes=cli.add_mutually_exclusive_group(required=True)
    modes.add_argument("--local",action="store_true",help="Use explicitly specified real GeoTIFFs")
    modes.add_argument("--opentopography",action="store_true",help="Download selected original SRTMGL1 (30m) or SRTMGL3 (90m) using env secret")
    cli.add_argument("--dem",choices=tuple(DEM_PRODUCTS),default=DATASET,
                     help="OpenTopography product (default SRTMGL1, preserving old cases)")
    cli.add_argument("--tif",type=Path,action="append",default=[],help="Repeat for multiple local TIFs")
    cli.add_argument("--tif-dir",type=Path,help="Scan local directory for *.tif or *.tiff")
    cli.add_argument("--buffer-m",type=float,default=500)
    cli.add_argument("--max-pixels",type=int,default=MAX_OUTPUT_PIXELS)
    cli.add_argument("--allow-nodata",action="store_true")
    cli.add_argument("--allow-public-srtmgl1-bulk-fallback",
                     "--allow-public-srtm-bulk-fallback",
                     dest="allow_public_bulk_fallback",action="store_true",
                     help="Opt in to official OpenTopography S3 for same selected DEM on API HTTP 406")
    opts=cli.parse_args(argv)
    try:
        result=prepare(opts.grid,opts.out_dir,
                       "local" if opts.local else "opentopography",
                       tifs=opts.tif,tif_dir=opts.tif_dir,buffer_m=opts.buffer_m,
                       max_pixels=opts.max_pixels,allow_nodata=opts.allow_nodata,
                       allow_public_bulk_fallback=opts.allow_public_bulk_fallback,
                       dem=opts.dem)
    except (P1SourceError,ValueError,OSError,rasterio.errors.RasterioError):
        # No exception text from transport or urllib can leak API keys.
        print(json.dumps({"status":"BLOCKED_P1_TERRAIN_SOURCE",
                          "diagnostic":"source, geometry, network or validation failed; "
                                       "inspect local metadata without printing API request URL",
                          "P1_NATIVE":"NOT_RUN"}))
        return 2
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())

"""Read-only Wolsong SRTM audit; outputs must be outside the checkout.

No downloading, DEM substitution, filling, reprojection or P1 admission changes.
Native-point diagnostics reproduce terrain_grid.cpp REAL*4 stages independently.
Install numpy, rasterio, pyproj, shapely, fiona in an external environment.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
import subprocess

import fiona
import numpy as np
import pyproj
import rasterio
import shapely
from pyproj import Transformer
from shapely.geometry import box, shape
from shapely.ops import unary_union
from shapely.strtree import STRtree

from scripts.s2g.gshhg_v237_cache import verify

ROOT = Path(__file__).resolve().parents[2]
X0, Y0, NX, NY, STEP = 533215., 3942629., 200, 200, 100.
BOUNDS = (X0, Y0, X0 + NX*STEP, Y0 + NY*STEP)
URLS = {
    "gl1": "https://opentopography.s3.sdsc.edu/raster/SRTM_GL1/SRTM_GL1_srtm/N35E129.tif",
    "gl3": "https://opentopography.s3.sdsc.edu/raster/SRTM_GL3/SRTM_GL3_srtm/North/North_30_60/N35E129.tif",
}
TO_UTM = Transformer.from_crs(4326, 32652, always_xy=True)
TO_GEO = Transformer.from_crs(32652, 4326, always_xy=True)
F = np.float32


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def histogram(a: np.ndarray) -> dict[str, int]:
    values, counts = np.unique(a, return_counts=True)
    return {str(int(v)): int(n) for v, n in zip(values, counts)}


def stats(a: np.ndarray, nodata: int) -> dict:
    missing = a == nodata
    valid = a[~missing]
    other = valid[valid != 0]
    return {
        "total": int(a.size), "valid": int(valid.size),
        "nodata": int(missing.sum()), "zero": int((valid == 0).sum()),
        "zero_pct_valid": float(100*(valid == 0).sum()/valid.size) if valid.size else None,
        "nodata_pct_total": float(100*missing.sum()/a.size) if a.size else None,
        "other": int(other.size),
        "other_min_max_m": [int(other.min()), int(other.max())] if other.size else None,
        "other_quantiles_m": np.quantile(other, [0, .25, .5, .75, .95, 1]).tolist() if other.size else [],
        "other_histogram": histogram(other),
    }


def coastline(cache: Path):
    provenance = verify(cache)
    geographic = TO_GEO.transform_bounds(*BOUNDS, densify_pts=41)
    polygons = []
    with fiona.open(cache/"GSHHS_f_L1/GSHHS_f_L1.shp") as src:
        if pyproj.CRS(src.crs).to_epsg() != 4326:
            raise ValueError("GSHHG requires WGS84")
        w, s, e, n = geographic
        for feature in src.filter(bbox=(w-.05, s-.05, e+.05, n+.05)):
            p = shapely.transform(shape(feature["geometry"]), TO_UTM.transform, interleaved=False)
            if not p.is_valid:
                raise ValueError("Invalid GSHHG geometry; no silent repair")
            polygons.append(p)
    if not polygons:
        raise ValueError("No real coastline selected")
    land = unary_union(polygons)
    shapely.prepare(land)
    domain = box(*BOUNDS)
    land_area = land.intersection(domain).area
    if not 0 < land_area < domain.area:
        raise ValueError("Domain must cross real GSHHG coastline")
    return land, {"provenance": provenance, "selected_polygons": len(polygons),
                  "land_m2": land_area, "ocean_m2": domain.area-land_area,
                  "domain_m2": domain.area}


def p1_coordinates(t, rows, cols):
    # Separate float32 tiepoint + half-spacing, then float32 index arithmetic.
    lon0 = F(F(t.c) + F(t.a)/F(2))
    lat0 = F(F(t.f) + F(t.e)/F(2))
    lon = lon0 + cols.astype("float32")*F(t.a)
    lat = lat0 + rows.astype("float32")*F(t.e)
    x, y = TO_UTM.transform(lon.astype("float64"), lat.astype("float64"))
    x = (x*float(F(.001))).astype("float32")*F(1000)
    y = (y*float(F(.001))).astype("float32")*F(1000)
    xi = (x-F(F(X0/1000)*F(1000)))*F(F(1)/F(STEP))
    yi = (y-F(F(Y0/1000)*F(1000)))*F(F(1)/F(STEP))
    # Original INT truncates towards zero; reject negative xi/yi after CELLIND.
    ii = np.trunc(xi).astype("int64") + (xi >= 0) - 1
    jj = np.trunc(yi).astype("int64") + (yi >= 0) - 1
    keep = (xi >= -1) & (yi >= -1) & (xi < NX) & (yi < NY)
    keep &= (ii >= 0) & (jj >= 0) & (ii < NX) & (jj < NY)
    return keep, ii, jj


def audit(label: str, tif: Path, land, out: Path, binary: Path | None) -> dict:
    # Spatially index TRUE boundary segments; clipping does not add box edges.
    boundary = land.boundary.intersection(box(X0-30000, Y0-30000,
                                              BOUNDS[2]+30000, BOUNDS[3]+30000))
    segments = []
    for line in shapely.get_parts(boundary):
        coords = shapely.get_coordinates(line)
        segments.extend(shapely.linestrings(np.stack([coords[:-1], coords[1:]], axis=1)))
    tree = STRtree(segments)
    with rasterio.open(tif) as ds:
        a = ds.read(1)
        if ds.crs.to_epsg() != 4326 or ds.dtypes != ("int16",) or ds.count != 1:
            raise ValueError("Expected original int16 single-band geographic WGS84 TIFF")
        if ds.nodata is None or not np.isfinite(ds.nodata) or ds.nodata != int(ds.nodata):
            raise ValueError("Missing or non-integer NoData metadata")
        nodata = int(ds.nodata)
        expected = 1/3600 if label == "gl1" else 3/3600
        if abs(ds.transform.a-expected) > 1e-12 or abs(ds.transform.e+expected) > 1e-12:
            raise ValueError("Unexpected product resolution")
        if ds.transform.b != 0 or ds.transform.d != 0:
            raise ValueError("Rotated source not supported")
        metadata = {"url": URLS[label], "sha256": sha(tif), "bytes": tif.stat().st_size,
                    "crs": ds.crs.to_string(), "shape": list(a.shape),
                    "resolution_degrees": list(ds.res), "dtype": ds.dtypes[0],
                    "nodata_metadata": nodata, "tags": ds.tags(),
                    "transform": list(ds.transform)[:6], "bounds": list(ds.bounds),
                    "whole_tile_nodata_count": int((a == nodata).sum()),
                    "whole_tile_mask_invalid_count": int((ds.read_masks(1) == 0).sum())}
        # Broad spatial window includes all potentially selected REAL*4 points.
        # Both diagnostics keep ORIGINAL tile row/column indices and tiepoint.
        w, s, e, n = TO_GEO.transform_bounds(*BOUNDS, densify_pts=41)
        if not (ds.bounds.left <= w < e <= ds.bounds.right and ds.bounds.bottom <= s < n <= ds.bounds.top):
            raise ValueError("Original TIFF does not cover the whole model domain")
        r0 = max(0, int(np.floor((n+.005-ds.transform.f)/ds.transform.e))-2)
        r1 = min(ds.height, int(np.ceil((s-.005-ds.transform.f)/ds.transform.e))+2)
        c0 = max(0, int(np.floor((w-.005-ds.transform.c)/ds.transform.a))-2)
        c1 = min(ds.width, int(np.ceil((e+.005-ds.transform.c)/ds.transform.a))+2)
        rr, cc = np.meshgrid(np.arange(r0, r1), np.arange(c0, c1), indexing="ij")
        geographic_lon = ds.transform.c+(cc+.5)*ds.transform.a
        geographic_lat = ds.transform.f+(rr+.5)*ds.transform.e
        nearby = (geographic_lon > w-.005) & (geographic_lon < e+.005)
        nearby &= (geographic_lat > s-.005) & (geographic_lat < n+.005)
        rows, cols = rr[nearby], cc[nearby]
        values = a[rows, cols]
        lon, lat = geographic_lon[nearby], geographic_lat[nearby]
        x, y = TO_UTM.transform(lon, lat)
        inside = (x >= X0) & (x < BOUNDS[2]) & (y >= Y0) & (y < BOUNDS[3])
        points = shapely.points(x, y)
        is_land = shapely.covers(land, points)
        nearest, measured_distance = tree.query_nearest(points, return_distance=True, all_matches=False)
        distance = np.empty(len(points))
        distance[nearest[0]] = measured_distance
        # Every point is within 28.3km of a coastline crossing the 20km box;
        # discarded boundary outside its 30km buffer cannot be nearest.
        groups = {"land": inside & is_land, "ocean": inside & ~is_land,
                  "coastal_all_le150m": inside & (distance <= 150),
                  "coastal_land_le150m": inside & is_land & (distance <= 150),
                  "coastal_ocean_le150m": inside & ~is_land & (distance <= 150),
                  "offshore_ocean_gt150m": inside & ~is_land & (distance > 150)}
        raw = {name: stats(values[mask], nodata) for name, mask in groups.items()}
        # Exhaustive location evidence stays outside checkout; report includes examples.
        anomaly = inside & (((~is_land) & (values != 0)) | (values == nodata))
        locations = []
        for k in np.flatnonzero(anomaly):
            locations.append({"row_0based": int(rows[k]), "col_0based": int(cols[k]),
                              "lon": float(lon[k]), "lat": float(lat[k]),
                              "utm_x_m": float(x[k]), "utm_y_m": float(y[k]),
                              "elevation_m": int(values[k]), "coast_distance_m": float(distance[k]),
                              "land": bool(is_land[k])})
        locpath = out/f"{label}_anomalies.csv"
        fields = ["row_0based", "col_0based", "lon", "lat", "utm_x_m", "utm_y_m",
                  "elevation_m", "coast_distance_m", "land"]
        with locpath.open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(locations)
        keep, ii, jj = p1_coordinates(ds.transform, rows, cols)
        offset = jj[keep]*NX+ii[keep]
        heights = values[keep]
        missing = heights == nodata
        count = np.bincount(offset, minlength=NX*NY)
        voids = np.bincount(offset[missing], minlength=NX*NY)
        total = np.zeros(NX*NY, dtype="float32")
        np.add.at(total, offset[~missing], heights[~missing].astype("float32"))
        mean = np.full(NX*NY, np.nan, dtype="float32")
        complete = (count > 0) & (voids == 0)
        mean[complete] = total[complete]/count[complete].astype("float32")
        csvpath = out/f"{label}_independent_cells.csv"
        with csvpath.open("x", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["i", "j", "samples", "nodata_samples", "complete_mean_m"])
            for k in range(NX*NY):
                writer.writerow([k % NX+1, k//NX+1, int(count[k]), int(voids[k]),
                                 float(mean[k]) if complete[k] else "BLOCKED"])
        model_centers = shapely.points(X0+(np.arange(NX*NY) % NX+.5)*STEP,
                                      Y0+(np.arange(NX*NY)//NX+.5)*STEP)
        ocean_cell = ~shapely.covers(land, model_centers)
        grid = {"total_cells": NX*NY, "samples": int(count.sum()),
                "sample_count_histogram": histogram(count), "empty_cells": int((count == 0).sum()),
                "nodata_samples": int(voids.sum()), "cells_with_nodata": int((voids > 0).sum()),
                "complete_cells": int(complete.sum()),
                "mean_min_max_m": [float(mean[complete].min()), float(mean[complete].max())] if complete.any() else [],
                "zero_mean_cells": int((mean == 0).sum()),
                "negative_mean_cells": int((mean < 0).sum()),
                "ocean_center_cells": int(ocean_cell.sum()),
                "ocean_center_positive_mean_cells": int((ocean_cell & (mean > 0)).sum()),
                "geometric_vs_p1_selected_point_symmetric_difference": int((inside != keep).sum()),
                "per_cell_csv_sha256": sha(csvpath)}
        native = {"status": "NOT_RUN", "reason": "No native binary supplied"}
        if binary:
            native_output = out/f"{label}_native.csv"
            command = [str(binary), str(tif), "533.215", "3942.629", "200", "200", ".100", "52", "N", str(native_output)]
            run = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
            native = {"exit_code": run.returncode, "stdout": run.stdout.strip(),
                      "stderr": run.stderr.strip(), "binary_sha256": sha(binary),
                      "status": ("EXECUTION_FAILED" if run.returncode < 0 else
                                 "REJECTED" if run.returncode else "PRODUCED_UNVERIFIED")}
            if not run.returncode:
                actual = np.genfromtxt(native_output, delimiter=",", names=True)
                if len(actual) != NX*NY:
                    raise ValueError("Native P1 incomplete output")
                native.update({"rows": len(actual), "csv_sha256": sha(native_output),
                               "index_mismatches": int(((actual["i"] != np.arange(NX*NY) % NX+1) |
                                                       (actual["j"] != np.arange(NX*NY)//NX+1)).sum()),
                               "count_mismatches": int((actual["hits"] != count).sum()),
                               "max_abs_mean_difference_m": float(np.max(abs(actual["elevation_m"]-mean)))})
        far = [p for p in locations if not p["land"] and p["coast_distance_m"] > 150]
        return {"source": metadata, "raw": raw, "grid": grid, "native": native,
                "anomalies_count": len(locations), "anomalies_csv_sha256": sha(locpath),
                "highest_ocean_examples": sorted([p for p in locations if not p["land"]],
                                                key=lambda p: p["elevation_m"], reverse=True)[:10],
                "farthest_offshore_examples": sorted(far, key=lambda p: p["coast_distance_m"], reverse=True)[:10]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gl1", type=Path, required=True)
    p.add_argument("--gl3", type=Path, required=True)
    p.add_argument("--gshhg-cache", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--native", type=Path)
    args = p.parse_args()
    if args.out.resolve().is_relative_to(ROOT) or args.out.exists():
        raise ValueError("Use a fresh evidence directory outside checkout")
    args.out.mkdir(parents=True)
    land, coast = coastline(args.gshhg_cache)
    result = {"status": "REAL_SOURCE_DIAGNOSTIC_NOT_SCIENCE_ACCEPTANCE",
              "grid": {"epsg": 32652, "bounds_m": BOUNDS, "nx": NX, "ny": NY, "step_m": STEP,
                       "xrefkm": "533.215", "yrefkm": "3942.629"},
              "coast": coast, "script_sha256": sha(Path(__file__)),
              "software": {"python": platform.python_version(), "numpy": np.__version__,
                           "rasterio": rasterio.__version__, "gdal": rasterio.__gdal_version__,
                           "pyproj": pyproj.__version__, "proj": pyproj.proj_version_str,
                           "shapely": shapely.__version__, "fiona": fiona.__version__}}
    for label in URLS:
        result[label] = audit(label, getattr(args, label), land, args.out, args.native)
    (args.out/"summary.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print(json.dumps({k: {"ocean": result[k]["raw"]["ocean"], "grid": result[k]["grid"],
                         "native": result[k]["native"]} for k in URLS}, indent=2))


if __name__ == "__main__":
    main()

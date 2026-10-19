#!/usr/bin/env python3
"""Issue #119: independent, bounded Wolsong 52/55 mixed-cell coastline diagnostics.

Read-only audit. Never recode the production TIFF, shoreline, or LU.DAT.
GSHHG f/h geometry difference is a sensitivity measure, NOT 2022 shoreline truth.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from osgeo import ogr, osr

from scripts.s2g import p2b_wolsong_case as case

AREA = case.STEP * case.STEP
EXPECTED_GLC_SHA = "2a1a208c5386735692d788066f730c7391e87f0981e7b9ad099442af2e217711"
EXPECTED_FULL_SHA = "121435427911ea80624802e0f352d777eaf6ba6966ca5f07e687650e95329fd9"


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def square(x0: float, y0: float, x1: float, y1: float):
    assert x1 > x0 and y1 > y0
    ring = ogr.Geometry(ogr.wkbLinearRing)
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)):
        ring.AddPoint_2D(x, y)
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    return poly


def land_union(shp: Path, resolution: str):
    if shp.name != f"GSHHS_{resolution}_L1.shp":
        raise ValueError("SHORELINE_RESOLUTION_OR_LEVEL_MISMATCH")
    ds = ogr.Open(str(shp))
    if ds is None or ds.GetLayerCount() != 1:
        raise ValueError("GSHHG_SHAPEFILE_UNAVAILABLE")
    layer = ds.GetLayer(0)
    geo = osr.SpatialReference()
    geo.ImportFromEPSG(4326)
    geo.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    utm = osr.SpatialReference()
    utm.ImportFromEPSG(case.EPSG)
    utm.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    source = layer.GetSpatialRef()
    if source is None or not source.IsSame(geo):
        raise ValueError("GSHHG_CRS_DRIFT")
    transform = osr.CoordinateTransformation(geo, utm)
    corners = case.corners(case.GRID)
    layer.SetSpatialFilterRect(
        min(p[0] for p in corners) - .1,
        min(p[1] for p in corners) - .1,
        max(p[0] for p in corners) + .1,
        max(p[1] for p in corners) + .1)
    domain = square(*case.GRID)
    result = None
    intersections = 0
    layer.ResetReading()
    for feat in layer:
        geom = feat.GetGeometryRef()
        if geom is None or not geom.IsValid():
            raise ValueError("GSHHG_INVALID_GEOMETRY")
        piece = geom.Clone()
        if piece.Transform(transform) != 0:
            raise ValueError("GSHHG_REPROJECTION_FAILED")
        piece = piece.Intersection(domain)
        if piece is None:
            raise ValueError("GSHHG_CLIP_FAILED")
        if piece.IsEmpty():
            continue
        intersections += 1
        result = piece if result is None else result.Union(piece)
        if result is None or not result.IsValid():
            raise ValueError("GSHHG_UNION_FAILED")
    if result is None:
        raise ValueError("WOLSONG_EXPECTED_COAST_NOT_FOUND")
    del ds
    return result, intersections


def read_mixed_lu(path: Path):
    """Parse all 40,000 rows, retain both-water positive displayed fractions."""
    lines = path.read_text().splitlines()
    if len(lines) != 40011:
        raise ValueError("LU_ROWS_NOT_40000")
    if "LU.DAT" not in lines[0] or "2.1" not in lines[0]:
        raise ValueError("LU_HEADER_INVALID")
    categories = [int(x) for x in lines[10].split()]
    if len(categories) != 38 or 52 not in categories or 55 not in categories:
        raise ValueError("LU_USGS38_HEADER_INVALID")
    k52, k55 = categories.index(52), categories.index(55)
    mixed, with52 = [], []
    for cell, line in enumerate(lines[11:]):
        fields = line.split()
        if len(fields) != 41 or fields[-1] != ".":
            raise ValueError("LU_ROW_FORMAT_INVALID")
        i, j = int(fields[0]), int(fields[1])
        if i != cell % 200 + 1 or j != cell // 200 + 1:
            raise ValueError("LU_ROW_GRID_ORDER")
        fractions = [float(x) for x in fields[2:-1]]
        if not all(math.isfinite(x) and 0 <= x <= 1 for x in fractions):
            raise ValueError("LU_INVALID_FRACTION")
        if abs(sum(fractions) - 1) > .02:
            raise ValueError("LU_FRACTIONS_NOT_CLOSED")
        row = {"i": i, "j": j, "f52": fractions[k52], "f55": fractions[k55]}
        if row["f52"] > 0:
            with52.append(row)
        if row["f52"] > 0 and row["f55"] > 0:
            mixed.append(row)
    return mixed, with52


def land_piece_area(land, piece):
    if not land.Intersects(piece):
        return 0.
    inter = land.Intersection(piece)
    if inter is None or not inter.IsValid():
        raise ValueError("COAST_WATER_INTERSECTION_INVALID")
    a = inter.GetArea()
    if not math.isfinite(a) or a < -1e-7 or a > piece.GetArea() + 1e-7:
        raise ValueError("WATER_AREA_OUTSIDE_PIXEL")
    return max(0., min(piece.GetArea(), a))


def cell_water_split(ds, data: np.ndarray, i: int, j: int, full, high):
    """Independently re-intersect only source GLC210 footprint inside this model cell."""
    x0 = case.X0 + (i - 1) * case.STEP
    y0 = case.Y0 + (j - 1) * case.STEP
    x1, y1 = x0 + case.STEP, y0 + case.STEP
    t = ds.transform
    sx, sy = t.a, -t.e
    c0 = max(0, math.floor((x0 - t.c) / sx))
    c1 = min(ds.width, math.ceil((x1 - t.c) / sx))
    r0 = max(0, math.floor((t.f - y1) / sy))
    r1 = min(ds.height, math.ceil((t.f - y0) / sy))
    total = lf = lh = 0.
    water_pixels = 0
    for r in range(r0, r1):
        for c in range(c0, c1):
            if int(data[r, c]) != 210:
                continue
            px0, px1 = max(x0, t.c + c * sx), min(x1, t.c + (c + 1) * sx)
            py0, py1 = max(y0, t.f - (r + 1) * sy), min(y1, t.f - r * sy)
            if px1 <= px0 or py1 <= py0:
                continue
            patch = square(px0, py0, px1, py1)
            total += patch.GetArea()
            lf += land_piece_area(full, patch)
            lh += land_piece_area(high, patch)
            water_pixels += 1
    return total, lf, lh, water_pixels


def audit(tif: Path, lu: Path, f: Path, h: Path, out: Path) -> dict:
    if digest(tif) != EXPECTED_GLC_SHA or digest(f) != EXPECTED_FULL_SHA:
        raise ValueError("SOURCE_SHA256_PIN_DRIFT")
    if not h.is_file() or h.stat().st_size == 0:
        raise ValueError("GSHHG_HIGH_L1_NOT_FROM_VERIFIED_ARCHIVE")
    out.mkdir(parents=True, exist_ok=False)
    mixed, with52 = read_mixed_lu(lu)
    if len(mixed) != 222:
        raise ValueError(f"FROZEN_MIXED_CELL_COUNT_CHANGED:{len(mixed)}")
    full, n_f = land_union(f, "f")
    high, n_h = land_union(h, "h")
    land_f, land_h = full.GetArea(), high.GetArea()
    if not (0 < land_f < case.TOTAL_AREA and 0 < land_h < case.TOTAL_AREA):
        raise ValueError("SHORELINE_AREA_INVALID")
    per_cell = []
    with rasterio.open(tif) as ds:
        if ds.crs.to_epsg() != case.EPSG or ds.count != 1 or ds.res != (30, 30):
            raise ValueError("GLC_GRID_DRIFT")
        data = ds.read(1)
        for row in mixed:
            i, j = row["i"], row["j"]
            total, f52, h52, n = cell_water_split(ds, data, i, j, full, high)
            f55 = total - f52
            if abs(f52 / AREA - row["f52"]) > .000501 or abs(f55 / AREA - row["f55"]) > .000501:
                raise ValueError(f"INDEPENDENT_MIXED_WATER_SPLIT_MISMATCH:{i},{j}")
            x0, y0 = case.X0 + (i - 1) * case.STEP, case.Y0 + (j - 1) * case.STEP
            cell = square(x0, y0, x0 + case.STEP, y0 + case.STEP)
            a_f, a_h = land_piece_area(full, cell), land_piece_area(high, cell)
            if not (1e-7 < a_f < AREA - 1e-7):
                raise ValueError(f"MIXED_CELL_MISSING_REAL_COAST:{i},{j}")
            per_cell.append({
                **row, "x_center_m": x0 + 50, "y_center_m": y0 + 50,
                "glc210_area_m2": total, "glc210_pixels_intersecting": n,
                "independent_f_52_m2": f52, "independent_f_55_m2": f55,
                "independent_h_52_m2": h52, "independent_h_55_m2": total - h52,
                "abs_f_vs_h_water52_m2": abs(f52 - h52),
                "full_land_cell_m2": a_f, "high_land_cell_m2": a_h,
                "abs_f_vs_h_land_cell_m2": abs(a_f - a_h),
            })
    if not per_cell:
        raise ValueError("NO_REAL_MIXED_CELLS")
    with (out / "mixed_52_55_cells.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(per_cell[0]))
        writer.writeheader()
        writer.writerows(per_cell)
    changes = sorted(v["abs_f_vs_h_water52_m2"] for v in per_cell)
    delta_land = sorted(v["abs_f_vs_h_land_cell_m2"] for v in per_cell)
    report = {
        "status": "MIXED_52_55_REAL_GEOMETRY_CROSSCHECK_PASS_SCOPED",
        "truth_scope": "SOURCE_GEOMETRY_CONSISTENCY_ONLY_NOT_REAL_2022_SHORELINE_VALIDATION",
        "glc2022_sha256": digest(tif), "gshhg_full_l1_sha256": digest(f),
        "gshhg_high_l1_sha256": digest(h), "lu_dat_sha256": digest(lu),
        "area_m2": case.TOTAL_AREA, "mixed_cells": len(per_cell),
        "cells_with_printed_52": len(with52),
        "full_intersecting_polygons": n_f, "high_intersecting_polygons": n_h,
        "gshhg_f_land_area_m2": land_f, "gshhg_h_land_area_m2": land_h,
        "gshhg_full_high_land_area_delta_m2": land_h - land_f,
        "mixed_cells_f_h_changed_more_than_5m2": sum(d > 5 for d in changes),
        "mixed_cells_f_h_water52_area_diff_p95_m2": changes[math.ceil(.95 * len(changes)) - 1],
        "mixed_cells_f_h_water52_area_diff_max_m2": changes[-1],
        "mixed_cells_f_h_water52_area_diff_sum_abs_m2": sum(changes),
        "mixed_cells_f_h_land_area_diff_max_m2": delta_land[-1],
        "method": "Independent OGR GEOS intersections for each GLC210 source pixel overlap in the 222 printed mixed LU cells",
        "shoreline_date_warning": "2017-era GSHHG 2.3.7 against GLC_FCS30D 2022; no independent 2022 observed coastline supplied",
        "p2b_exact_area_freeze": "PENDING_SHORELINE_TEMPORAL_ORACLE_AND_POLICY_TOLERANCE",
        "p3_original_parity": "NOT_RUN",
    }
    (out / "mixed_52_55_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tif", type=Path, required=True)
    p.add_argument("--lu-dat", type=Path, required=True)
    p.add_argument("--full-shp", type=Path, required=True)
    p.add_argument("--high-shp", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    try:
        print(json.dumps(audit(args.tif, args.lu_dat, args.full_shp, args.high_shp, args.out), sort_keys=True))
        return 0
    except (OSError, ValueError, AssertionError) as exc:
        print(f"WOLSONG_MIXED_AUDIT_FAIL_CLOSED:{type(exc).__name__}:{str(exc)[:150]}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

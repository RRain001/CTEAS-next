#!/usr/bin/env python3
"""S2-G1B-B3: extract genuine Eurasian GLCC 2.0 source for an arbitrary UTM case.

SOURCE ONLY: this builds original CTGPROC-compatible GENERIC.LANDUSE 1.0
points, NOT native P2 category fractions or native P3 GEO.DAT science.

Source is the root-level eausgs2_0la.img Git LFS object. Its 156 MB,
13,000 x 12,000 raw uint8 layout, sphere/Lambert projection and category
translation are frozen to original CTEAS crop_terrain_landuse_data.py.
No SRTM dataset, local original Fortran binary, extra water class or
synthesized land cover is used. Every run explicitly verifies the input SHA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
from rasterio.warp import transform as crs_transform

from engine.preprocess.ctgproc.auto_select_landuse_to_ctgproc import parse_grid_cmn
from scripts.crop_terrain_landuse_data import (
    GLCC_CELL_KM, GLCC_NX, GLCC_NY, GLCC_TO_USGS92,
    GLCC_XORG_KM, GLCC_YORG_KM, LANDUSE_DATUM,
    USGS92_STANDARD, laea_forward, read_glcc_block, write_generic_points,
    write_landuse_laea_tif,
)

REPO = Path(__file__).resolve().parents[2]
SOURCE_DEFAULT = REPO / "eausgs2_0la.img"
SOURCE_SHA256 = "4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a"
SOURCE_BYTES = 156_000_000


class LanduseSourceError(ValueError):
    pass


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def validate_source(path: Path, sha256: str = SOURCE_SHA256) -> dict:
    """Never interpret LFS pointer text, short or modified imagery as GLCC."""
    if path.is_symlink() or not path.is_file():
        raise LanduseSourceError("real GLCC source missing/symlink: git lfs pull --include=eausgs2_0la.img")
    size = path.stat().st_size
    if size != SOURCE_BYTES:
        raise LanduseSourceError(
            f"GLCC uint8 raster must be exactly {SOURCE_BYTES} bytes, found {size}; "
            "LFS pointer or wrong region/product is not a raster")
    actual_sha = digest(path)
    if actual_sha != sha256:
        raise LanduseSourceError(
            f"GLCC original data SHA256 mismatch: expected {sha256}, found {actual_sha}")
    return {"original_sha256": actual_sha, "original_size_bytes": size}


def grid_window(grid, buffer_km: float) -> tuple[dict, str, dict]:
    """True WGS84 UTM case box -> Lambert GLCC source pixel subset.

    Compute entire rectangular case footprint (corners+edge midpoints)
    rather than a guessed center-radius square; conservatively extend in
    Lambert km to include all possible cut pixels and mesh fractions.
    """
    if (grid.imap != "UTM" or grid.lsohem not in ("N", "S")
            or not 1 <= grid.iutmzn <= 60):
        raise LanduseSourceError("P2 GLCC source requires valid WGS84 UTM case")
    if grid.datum not in ("WGS-84", "WGS84"):
        raise LanduseSourceError("unsupported grid datum for selected WGS84 UTM transform")
    if (grid.nx <= 0 or grid.ny <= 0 or
            not math.isfinite(grid.dgridkm) or grid.dgridkm <= 0 or
            not math.isfinite(grid.xrefkm) or not math.isfinite(grid.yrefkm)):
        raise LanduseSourceError("invalid grid dimensions, origin or spacing")
    if not math.isfinite(buffer_km) or buffer_km < 0.5:
        raise LanduseSourceError("GLCC border buffer must be >=0.5 km")
    # As in the original IGRID=1 grid convention: XREFKM/YREFKM denotes
    # southwest corner of the numerical domain, not a station location.
    x0, y0 = grid.xrefkm, grid.yrefkm
    x1 = x0 + grid.nx * grid.dgridkm
    y1 = y0 + grid.ny * grid.dgridkm
    xs = [x0, (x0+x1)/2, x1]
    ys = [y0, (y0+y1)/2, y1]
    pts = [(x, y) for x in xs for y in ys]
    epsg = 32600 + grid.iutmzn if grid.lsohem == "N" else 32700 + grid.iutmzn
    utm = f"EPSG:{epsg}"
    lons, lats = crs_transform(utm, "EPSG:4326",
                               [p[0]*1000 for p in pts],
                               [p[1]*1000 for p in pts])
    if any(not math.isfinite(x) for x in (*lons, *lats)):
        raise LanduseSourceError("invalid UTM projected WGS84 coordinates")
    if max(lons)-min(lons) >= 180:
        raise LanduseSourceError("antimeridian-crossing window requires separate tiles")
    coords = [laea_forward(lon, lat) for lon, lat in zip(lons, lats)]
    if any(not math.isfinite(v) for xy in coords for v in xy):
        raise LanduseSourceError("GLCC Lambert projection is undefined for case")
    minx, maxx = min(v[0] for v in coords)-buffer_km, max(v[0] for v in coords)+buffer_km
    miny, maxy = min(v[1] for v in coords)-buffer_km, max(v[1] for v in coords)+buffer_km
    # Only actual source pixels are admissible; never crop by silently
    # clamping and pretending out-of-region GLCC zeroes represent water.
    raw_i0 = math.floor((minx - GLCC_XORG_KM) / GLCC_CELL_KM) + 1
    raw_i1 = math.ceil((maxx - GLCC_XORG_KM) / GLCC_CELL_KM)
    raw_j0 = math.floor((miny - GLCC_YORG_KM) / GLCC_CELL_KM) + 1
    raw_j1 = math.ceil((maxy - GLCC_YORG_KM) / GLCC_CELL_KM)
    if (raw_i0 < 1 or raw_i1 > GLCC_NX or raw_j0 < 1
            or raw_j1 > GLCC_NY or raw_i0 > raw_i1 or raw_j0 > raw_j1):
        raise LanduseSourceError(
            "research domain extends beyond the supplied Eurasia GLCC imagery; "
            "provide another regional IMG before permitting P2")
    win = {
        "i0": raw_i0, "i1": raw_i1, "j0": raw_j0, "j1": raw_j1,
        "laea_bounds_km": [minx, miny, maxx, maxy],
        "utm_box_3x3": pts,
    }
    meta = {
        "epsg": epsg, "nx": grid.nx, "ny": grid.ny,
        "dgridkm": grid.dgridkm, "xrefkm": grid.xrefkm, "yrefkm": grid.yrefkm,
        "lons_bounds": [min(lons), max(lons)],
        "lats_bounds": [min(lats), max(lats)],
    }
    return win, utm, meta


def _require_original_grid_origin(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="strict")
    for key in ("XREFKM", "YREFKM"):
        matches = re.findall(r"!\s*" + key + r"\s*=\s*([^!]+)!", text, re.I)
        if len(matches) != 1 or re.fullmatch(r"-?\d+\.\d{3}", matches[0].strip()) is None:
            raise LanduseSourceError(f"{key} must be unique km value with exactly 3 decimals")


def prepare(
    grid_cmn: Path, source: Path, out_dir: Path, mesh_cells: int = 20,
    buffer_km: float = 1.5, preview_tif: bool = False, dry_run: bool = False,
    max_points: int = 3_000_000, expected_sha: str = SOURCE_SHA256,
) -> dict:
    if mesh_cells < 1 or max_points < 1:
        raise LanduseSourceError("mesh and output record budget must be positive")
    if out_dir.exists() or out_dir.is_symlink():
        raise LanduseSourceError("output directory must not exist; source extraction never overwrites")
    if grid_cmn.is_symlink() or not grid_cmn.is_file():
        raise LanduseSourceError("real case grid.cmn missing or symlink")
    _require_original_grid_origin(grid_cmn)
    grid = parse_grid_cmn(grid_cmn)
    win, utm, gridmeta = grid_window(grid, buffer_km)
    authority = validate_source(source, expected_sha)
    block = read_glcc_block(source, win)
    classes, counts = np.unique(block, return_counts=True)
    if any(int(x) > 24 for x in classes):
        raise LanduseSourceError("GLCC source contains unknown class outside 0..24")
    eligible = int(np.count_nonzero(block))
    if eligible < 1:
        raise LanduseSourceError(
            "no classified pixels in selected regional imagery; refuse blank or open-sea P2")
    num_points = eligible * mesh_cells * mesh_cells
    if num_points > max_points:
        raise LanduseSourceError(
            f"GLCC output would contain {num_points} points; exceeds "
            f"explicit {max_points} record budget. Reduce mesh or split domain.")
    mask = {str(int(x)): int(n) for x, n in zip(classes, counts)}
    result = {
        "status": "P2_GLCC_SOURCE_WINDOW_VERIFIED_P2_NATIVE_PHYSICS_NOT_RUN",
        "source": str(source), **authority,
        "window": win, "grid": gridmeta,
        "raw_class_counts": mask,
        "source_original_class_ids": list(range(1, 25)),
        "calmet_category_ids": list(USGS92_STANDARD),
        "source_water_class": 16,
        "water_class_translated": GLCC_TO_USGS92[15],
        "missing_source_class": 0,
        "classified_pixels": eligible,
        "output_points_estimated": num_points,
        "mesh_cells": mesh_cells, "buffer_km": buffer_km,
        "source_projection": "GLCC Eurasia LAEA sphere R=6370997 lat0=45 lon0=100",
        "generic_datum": LANDUSE_DATUM,
        "legacy_mesh_sampling_does_not_increase_source_resolution": True,
        "original_1992_1993_landcover_not_2022": True,
        "native_P2_lu_dat": "NOT_RUN",
        "native_P3_geo_dat": "NOT_RUN",
        "native_P6": "NOT_RUN",
        "ready": False,
    }
    if dry_run:
        return result
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    # The original crop uses the identical 24->USGS38 lookup and Lambert
    # subpixel sampling; no nearest-neighbor resampling is invented.
    out_dir.mkdir(exist_ok=False)
    try:
        generic = out_dir / "glcc.generic.txt"
        stats = write_generic_points(block, win, generic, mesh_cells, False)
        if stats["points"] != num_points:
            raise LanduseSourceError("GENERIC point output mismatch with original source class count")
        result["generic"] = {
            "relative_path": generic.name, "sha256": digest(generic),
            "size_bytes": generic.stat().st_size,
            "mapped_valid_cells": stats["cells"],
            "n_points": stats["points"],
        }
        if preview_tif:
            tif = out_dir / "glcc_source_preview_laea.tif"
            write_landuse_laea_tif(block, win, tif, False)
            result["preview_geotiff"] = {
                "relative_path": tif.name, "sha256": digest(tif),
            }
        meta = out_dir / "glcc_source_manifest.json"
        meta.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
        return result
    except Exception:
        # Never leave a misleading partly produced case source that
        # downstream P2 could mistake for accepted scientific input.
        import shutil
        shutil.rmtree(out_dir)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--landuse-file", type=Path, default=SOURCE_DEFAULT)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--mesh-cells", type=int, default=20)
    parser.add_argument("--buffer-km", type=float, default=1.5)
    parser.add_argument("--max-points", type=int, default=3_000_000)
    parser.add_argument("--preview-tif", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = prepare(args.grid, args.landuse_file, args.out_dir,
                         mesh_cells=args.mesh_cells, buffer_km=args.buffer_km,
                         preview_tif=args.preview_tif, dry_run=args.dry_run,
                         max_points=args.max_points)
    except (LanduseSourceError, OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({
            "status": "BLOCKED_P2_REAL_GLCC_SOURCE",
            "error": str(exc), "native_P2_P3_P6": "NOT_RUN"}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

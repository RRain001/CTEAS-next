"""Single numerical-footprint authority for P4 IGRA and P5 NOAA selection.

The published grid.cmn southwest UTM origin is authoritative. center_location
is geographic case metadata, NOT a substitute for this origin. No network I/O.
"""
from __future__ import annotations

import math
from pathlib import Path

from engine.run_met.common import GridDef, lon_lat_to_utm_km, parse_grid_cmn


def load_strict_utm_grid(path: Path, *, context: str = "P4/P5") -> GridDef:
    grid = parse_grid_cmn(context.lower(), path=path)
    if (grid.imap != "UTM" or grid.datum != "WGS-84" or
            grid.lsohem not in ("N", "S") or not 1 <= grid.iutmzn <= 60):
        raise ValueError(f"{context} station selection requires WGS-84 UTM zone/hemisphere")
    if (not all(math.isfinite(x) for x in (grid.xrefkm, grid.yrefkm, grid.dgridkm)) or
            grid.dgridkm <= 0 or grid.nx <= 0 or grid.ny <= 0):
        raise ValueError(f"{context} grid.cmn contains invalid numerical grid geometry")
    return grid


def utm_bounds_km(grid: GridDef) -> tuple[float, float, float, float]:
    return (grid.xrefkm, grid.xrefkm + grid.nx * grid.dgridkm,
            grid.yrefkm, grid.yrefkm + grid.ny * grid.dgridkm)


def contains_projected_utm_km(x: float, y: float, grid: GridDef) -> bool:
    """Closed edges, including corners; epsilon = 1e-10 km for roundoff only."""
    if not (math.isfinite(x) and math.isfinite(y)):
        return False
    xmin, xmax, ymin, ymax = utm_bounds_km(grid)
    eps_km = 1e-10
    return xmin - eps_km <= x <= xmax + eps_km and ymin - eps_km <= y <= ymax + eps_km


def lon_lat_in_utm_grid(lon: float, lat: float, grid: GridDef) -> bool:
    """Project to the GRID's zone, not the station's nominal UTM zone."""
    try:
        x, y = lon_lat_to_utm_km(lon, lat, grid.iutmzn, grid.lsohem == "N")
    except ValueError:
        return False
    return contains_projected_utm_km(x, y, grid)

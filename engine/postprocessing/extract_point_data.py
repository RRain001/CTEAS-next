#!/usr/bin/env python
from __future__ import annotations

import argparse
import struct
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Tuple

import numpy as np

from engine.core.paths import current_project_path
from engine.core.runtime_names import MET_INP, PUFF_CON

DEFAULT_CONC_FILE = current_project_path("run", "puff", PUFF_CON)
DEFAULT_MET_INP = current_project_path("run", "met", MET_INP)
DEFAULT_OUTPUT_CSV = current_project_path("run", "puff", "postprocessing", "point_timeseries.csv")
CONC_UNIT = "Bq/m³"


@dataclass
class GridSpec:
    nx: int
    ny: int
    dgrid_km: float
    xorig_km: float
    yorig_km: float


@dataclass
class RunWindow:
    start: datetime
    end: datetime


@dataclass
class TimeRecord:
    start: datetime
    end: datetime
    data_offset: int


def _extract_calmet_key(text: str, key: str, cast):
    marker = f"! {key}"
    for line in text.splitlines():
        if marker in line and "=" in line:
            val = line.split("=", 1)[1].split("!", 1)[0].strip()
            return cast(val)
    raise ValueError(f"Cannot find {key} in CALMET.INP")


def parse_calmet_grid(calmet_inp: Path) -> GridSpec:
    text = calmet_inp.read_text(encoding="utf-8", errors="ignore")
    return GridSpec(
        nx=_extract_calmet_key(text, "NX", int),
        ny=_extract_calmet_key(text, "NY", int),
        dgrid_km=_extract_calmet_key(text, "DGRIDKM", float),
        xorig_km=_extract_calmet_key(text, "XORIGKM", float),
        yorig_km=_extract_calmet_key(text, "YORIGKM", float),
    )


def parse_calmet_run_window(calmet_inp: Path) -> RunWindow:
    text = calmet_inp.read_text(encoding="utf-8", errors="ignore")
    ibyr = _extract_calmet_key(text, "IBYR", int)
    ibmo = _extract_calmet_key(text, "IBMO", int)
    ibdy = _extract_calmet_key(text, "IBDY", int)
    ibhr = _extract_calmet_key(text, "IBHR", int)
    ibsec = _extract_calmet_key(text, "IBSEC", int)

    ieyr = _extract_calmet_key(text, "IEYR", int)
    iemo = _extract_calmet_key(text, "IEMO", int)
    iedy = _extract_calmet_key(text, "IEDY", int)
    iehr = _extract_calmet_key(text, "IEHR", int)
    iesec = _extract_calmet_key(text, "IESEC", int)

    return RunWindow(
        start=datetime(ibyr, ibmo, ibdy, ibhr, 0, ibsec),
        end=datetime(ieyr, iemo, iedy, iehr, 0, iesec),
    )


def _read_fortran_record(f) -> tuple[int, int]:
    """Return (payload_offset, payload_length), file points to payload start after return."""
    head = f.read(4)
    if len(head) == 0:
        return -1, -1
    if len(head) < 4:
        raise EOFError("Unexpected EOF while reading Fortran record header")
    (nbytes,) = struct.unpack("<i", head)
    if nbytes < 0:
        raise ValueError(f"Invalid record length: {nbytes}")
    payload_offset = f.tell()
    return payload_offset, nbytes


def _finish_fortran_record(f, payload_offset: int, nbytes: int) -> None:
    f.seek(payload_offset + nbytes)
    tail = f.read(4)
    if len(tail) < 4:
        raise EOFError("Unexpected EOF while reading Fortran record tail")
    (end_nbytes,) = struct.unpack("<i", tail)
    if end_nbytes != nbytes:
        raise ValueError(f"Fortran record marker mismatch: {nbytes} != {end_nbytes}")


def _decode_time_record(payload: bytes) -> tuple[datetime, datetime] | None:
    if len(payload) != 32:
        return None
    vals = struct.unpack("<8i", payload)
    y1, d1, h1, s1, y2, d2, h2, s2 = vals
    if not (1900 <= y1 <= 2200 and 1900 <= y2 <= 2200):
        return None
    if not (1 <= d1 <= 366 and 1 <= d2 <= 366):
        return None
    if not (0 <= h1 <= 23 and 0 <= h2 <= 24):
        return None
    if not (0 <= s1 < 3600 and 0 <= s2 < 3600):
        return None

    start = datetime(y1, 1, 1) + timedelta(days=d1 - 1, hours=h1, seconds=s1)
    end = datetime(y2, 1, 1) + timedelta(days=d2 - 1, hours=h2, seconds=s2)
    return start, end


def index_time_records(conc_file: Path, nx: int, ny: int) -> list[TimeRecord]:
    expected_data_len = 15 + nx * ny * 4
    records: list[TimeRecord] = []

    pending_time: tuple[datetime, datetime] | None = None
    saw_meta_after_time = False

    with conc_file.open("rb") as f:
        while True:
            payload_offset, nbytes = _read_fortran_record(f)
            if nbytes < 0:
                break

            if nbytes == 32:
                payload = f.read(32)
                _finish_fortran_record(f, payload_offset, nbytes)
                decoded = _decode_time_record(payload)
                if decoded is not None:
                    pending_time = decoded
                    saw_meta_after_time = False
                elif pending_time is not None:
                    saw_meta_after_time = True
                continue

            if nbytes == expected_data_len and pending_time is not None and saw_meta_after_time:
                records.append(
                    TimeRecord(
                        start=pending_time[0],
                        end=pending_time[1],
                        data_offset=payload_offset,
                    )
                )
                _finish_fortran_record(f, payload_offset, nbytes)
                pending_time = None
                saw_meta_after_time = False
                continue

            _finish_fortran_record(f, payload_offset, nbytes)

    if not records:
        raise RuntimeError("No timestep data records found. Please verify CONC.DAT and grid size.")
    return records


def load_concentration_at_offset(conc_file: Path, offset: int, nx: int, ny: int) -> np.ndarray:
    n = 15 + nx * ny * 4
    with conc_file.open("rb") as f:
        f.seek(offset)
        payload = f.read(n)
    if len(payload) != n:
        raise RuntimeError("Cannot read full concentration payload")

    arr = np.frombuffer(payload[15:], dtype="<f4")
    if arr.size != nx * ny:
        raise RuntimeError(f"Unexpected concentration array size: {arr.size}")
    return arr.reshape(ny, nx)


def write_time_series_csv(output_csv: Path, time_series: List[Tuple[datetime, float]]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["datetime", "concentration", "unit"])
        for dt, conc in time_series:
            writer.writerow([dt.strftime("%Y-%m-%d %H:%M:%S"), f"{conc:.6e}", CONC_UNIT])


def bilinear_interpolation(x: float, y: float, x_grid: np.ndarray, y_grid: np.ndarray, z: np.ndarray) -> float:
    """
    Perform bilinear interpolation to get value at point (x, y).
    
    Args:
        x, y: Coordinates of the point
        x_grid: 1D array of x coordinates (km)
        y_grid: 1D array of y coordinates (km)
        z: 2D array of concentrations (ny x nx)
    
    Returns:
        Interpolated concentration value
    """
    # Find indices for interpolation
    i = np.searchsorted(x_grid, x) - 1
    j = np.searchsorted(y_grid, y) - 1
    
    # Handle boundary conditions
    i = max(0, min(i, len(x_grid) - 2))
    j = max(0, min(j, len(y_grid) - 2))
    
    x1, x2 = x_grid[i], x_grid[i + 1]
    y1, y2 = y_grid[j], y_grid[j + 1]
    
    # Get values at the four corners
    z11 = z[j, i]
    z21 = z[j, i + 1]
    z12 = z[j + 1, i]
    z22 = z[j + 1, i + 1]
    
    # Bilinear interpolation
    if x2 == x1 or y2 == y1:
        # Fallback to nearest neighbor if grid is degenerate
        return z[j, i]
    
    # Interpolate in x direction
    z1 = z11 + (z21 - z11) * (x - x1) / (x2 - x1)
    z2 = z12 + (z22 - z12) * (x - x1) / (x2 - x1)
    
    # Interpolate in y direction
    result = z1 + (z2 - z1) * (y - y1) / (y2 - y1)
    
    return float(result)


def extract_point_time_series(
    conc_file: Path,
    calmet_inp: Path,
    point_x_km: float,
    point_y_km: float,
    output_csv: Path,
    use_interpolation: bool = True,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> List[Tuple[datetime, float]]:
    """
    Extract time series of concentrations at a specific point.
    
    Args:
        conc_file: Path to CONC.DAT file
        calmet_inp: Path to CALMET.INP for grid metadata
        point_x_km: X coordinate of the point in km
        point_y_km: Y coordinate of the point in km
        output_csv: Path to output CSV file
        use_interpolation: If True, use bilinear interpolation; if False, use nearest grid cell
    
    Returns:
        List of (datetime, concentration) tuples
    """
    # Parse grid information
    grid = parse_calmet_grid(calmet_inp)
    window = parse_calmet_run_window(calmet_inp)
    
    print(f"Grid: nx={grid.nx}, ny={grid.ny}, dgrid={grid.dgrid_km} km")
    print(f"Grid origin: ({grid.xorig_km}, {grid.yorig_km}) km")
    print(f"Point coordinates: ({point_x_km}, {point_y_km}) km")
    
    # Generate grid coordinates
    x_coords = grid.xorig_km + np.arange(grid.nx) * grid.dgrid_km
    y_coords = grid.yorig_km + np.arange(grid.ny) * grid.dgrid_km
    
    # Check if point is within grid bounds
    x_min, x_max = x_coords[0], x_coords[-1]
    y_min, y_max = y_coords[0], y_coords[-1]
    
    if not (x_min <= point_x_km <= x_max and y_min <= point_y_km <= y_max):
        print(f"WARNING: Point is outside grid bounds!")
        print(f"  X range: [{x_min}, {x_max}] km")
        print(f"  Y range: [{y_min}, {y_max}] km")
        print(f"  Point: ({point_x_km}, {point_y_km}) km")
        print("  Concentrations will be set to 0 for out-of-bounds points")
        return []
    
    # Find nearest grid cell for reference
    nearest_x_idx = np.argmin(np.abs(x_coords - point_x_km))
    nearest_y_idx = np.argmin(np.abs(y_coords - point_y_km))
    nearest_x = x_coords[nearest_x_idx]
    nearest_y = y_coords[nearest_y_idx]
    
    print(f"Nearest grid cell center: ({nearest_x:.3f}, {nearest_y:.3f}) km")
    print(f"Distance from point: {np.sqrt((point_x_km - nearest_x)**2 + (point_y_km - nearest_y)**2):.3f} km")
    print(f"Using {'bilinear interpolation' if use_interpolation else 'nearest grid cell'} method")
    
    # Index all time records in CONC.DAT
    print("\nIndexing concentration file...")
    records = index_time_records(conc_file, grid.nx, grid.ny)
    print(f"Found {len(records)} timesteps")
    print(f"Time range: {records[0].start} to {records[-1].end}")
    
    # Extract time series
    print("\nExtracting time series...")
    time_series = []
    
    for i, rec in enumerate(records):
        if start_time is not None and rec.start < start_time:
            continue
        if end_time is not None and rec.start > end_time:
            continue
        if (i + 1) % 100 == 0:
            print(f"  Processing timestep {i+1}/{len(records)}...")
        
        # Load concentration grid
        conc_grid = load_concentration_at_offset(conc_file, rec.data_offset, grid.nx, grid.ny)
        
        # Get concentration at point
        if use_interpolation:
            conc_value = bilinear_interpolation(point_x_km, point_y_km, x_coords, y_coords, conc_grid)
        else:
            # Nearest grid cell
            conc_value = conc_grid[nearest_y_idx, nearest_x_idx]
        
        time_series.append((rec.start, conc_value))
    
    print(f"\nSaving to {output_csv}...")
    write_time_series_csv(output_csv, time_series)
    if not time_series:
        print("No concentration records matched the requested point/time filters.")
        return time_series
    
    # Print statistics
    conc_values = [c for _, c in time_series]
    print("\nStatistics:")
    print(f"  Number of records: {len(time_series)}")
    print(f"  Mean concentration: {np.mean(conc_values):.6e} {CONC_UNIT}")
    print(f"  Max concentration: {np.max(conc_values):.6e} {CONC_UNIT}")
    print(f"  Min concentration: {np.min(conc_values):.6e} {CONC_UNIT}")
    print(f"  Std deviation: {np.std(conc_values):.6e} {CONC_UNIT}")
    
    # Find max concentration time
    max_idx = np.argmax(conc_values)
    print(f"  Peak time: {time_series[max_idx][0]} with {conc_values[max_idx]:.6e} {CONC_UNIT}")
    
    return time_series


def main():
    parser = argparse.ArgumentParser(
        description="Extract time series of concentrations at a specific point from PUFF puff.con"
    )
    parser.add_argument(
        "--conc-file",
        type=Path,
        default=DEFAULT_CONC_FILE,
        help="Path to PUFF puff.con (binary)",
    )
    parser.add_argument(
        "--met-inp",
        "--calmet-inp",
        dest="met_inp",
        type=Path,
        default=DEFAULT_MET_INP,
        help="Path to MET input file for grid metadata",
    )
    parser.add_argument(
        "--x",
        type=float,
        required=True,
        help="X coordinate of the point in km (e.g., 513.385)",
    )
    parser.add_argument(
        "--y",
        type=float,
        required=True,
        help="Y coordinate of the point in km (e.g., 3533.769)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_CSV,
        help="Output CSV file path",
    )
    parser.add_argument(
        "--no-interpolation",
        action="store_true",
        help="Disable bilinear interpolation, use nearest grid cell instead",
    )
    parser.add_argument(
        "--start-time",
        type=str,
        help="Optional start time filter (format: 'YYYY-MM-DD HH:MM')",
    )
    parser.add_argument(
        "--end-time",
        type=str,
        help="Optional end time filter (format: 'YYYY-MM-DD HH:MM')",
    )
    
    args = parser.parse_args()
    start_time = datetime.strptime(args.start_time, "%Y-%m-%d %H:%M") if args.start_time else None
    end_time = datetime.strptime(args.end_time, "%Y-%m-%d %H:%M") if args.end_time else None
    
    extract_point_time_series(
        conc_file=args.conc_file,
        calmet_inp=args.met_inp,
        point_x_km=args.x,
        point_y_km=args.y,
        output_csv=args.output,
        use_interpolation=not args.no_interpolation,
        start_time=start_time,
        end_time=end_time,
    )
    
    print("\nDone!")


if __name__ == "__main__":
    main()

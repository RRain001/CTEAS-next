#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from engine.core.paths import TEMPLATE_FILES, case_paths, load_case_config, resolve_case_name

TEMPLATE_INP = TEMPLATE_FILES["met"]

WGS84_A = 6378137.0
WGS84_F = 1 / 298.257223563
K0 = 0.9996


@dataclass
class GridDef:
    imap: str
    iutmzn: int
    lsohem: str
    datum: str
    xrefkm: float
    yrefkm: float
    nx: int
    ny: int
    dgridkm: float
    nz: int
    zfaces: list[float]


def load_case_config_with_name(case_name: str | None = None) -> tuple[str, dict[str, Any]]:
    resolved_case = resolve_case_name(case_name)
    return resolved_case, load_case_config(resolved_case)


def parse_research_time(case_name: str, path: Path | None = None) -> tuple[datetime, datetime]:
    if path is None:
        cfg = load_case_config(case_name)
        paths = case_paths(cfg, case_name, required=["grid_dir"])
        path = paths["grid_dir"] / "research_time"
    text = path.read_text(encoding="utf-8", errors="ignore")
    m_begin = re.search(r"BEGIN\s*:\s*(\d{8}-\d{6})", text)
    m_end = re.search(r"END\s*:\s*(\d{8}-\d{6})", text)
    if not m_begin or not m_end:
        raise ValueError(f"Cannot parse BEGIN/END from: {path}")
    begin = datetime.strptime(m_begin.group(1), "%Y%m%d-%H%M%S")
    end = datetime.strptime(m_end.group(1), "%Y%m%d-%H%M%S")
    if end < begin:
        raise ValueError(f"END earlier than BEGIN in: {path}")
    return begin, end


def parse_grid_cmn(case_name: str, path: Path | None = None) -> GridDef:
    if path is None:
        cfg = load_case_config(case_name)
        paths = case_paths(cfg, case_name, required=["grid_dir"])
        path = paths["grid_dir"] / "grid.cmn"

    kv: dict[str, str] = {}
    zfaces: list[float] = []
    pattern = re.compile(r"^\s*[!*]\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*[!*]\s*$")

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = pattern.match(line)
        if not m:
            continue
        key = m.group(1).strip().upper()
        value = m.group(2).strip()
        if key == "ZFACE":
            try:
                zfaces.append(float(value))
            except ValueError:
                continue
        else:
            kv[key] = value

    required = ["IMAP", "IUTMZN", "LSOHEM", "DATUM", "XREFKM", "YREFKM", "NX", "NY", "DGRIDKM", "NZ"]
    missing = [k for k in required if k not in kv]
    if missing:
        raise ValueError(f"Missing keys in {path}: {', '.join(missing)}")

    nz = int(float(kv["NZ"]))
    if len(zfaces) != nz + 1:
        raise ValueError(f"Expected {nz + 1} ZFACE values in {path}, found {len(zfaces)}")

    return GridDef(
        imap=kv["IMAP"].upper(),
        iutmzn=int(float(kv["IUTMZN"])),
        lsohem=kv["LSOHEM"].upper(),
        datum=kv["DATUM"].upper(),
        xrefkm=float(kv["XREFKM"]),
        yrefkm=float(kv["YREFKM"]),
        nx=int(float(kv["NX"])),
        ny=int(float(kv["NY"])),
        dgridkm=float(kv["DGRIDKM"]),
        nz=nz,
        zfaces=zfaces,
    )


def find_upperair_files(path: Path) -> list[Path]:
    files = sorted(path.glob("up_*.dat"))
    if not files:
        raise FileNotFoundError(f"No final UP.DAT files found in: {path}")
    return files


def lon_lat_to_utm_km(lon: float, lat: float, zone: int, northern: bool) -> tuple[float, float]:
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"Longitude out of range: {lon}")
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Latitude out of range: {lat}")
    if not (-80.0 <= lat <= 84.0):
        raise ValueError(f"Latitude out of UTM range: {lat}")

    lon0 = (zone - 1) * 6 - 180 + 3
    e2 = WGS84_F * (2 - WGS84_F)
    ep2 = e2 / (1 - e2)

    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    lon0_rad = math.radians(lon0)

    sin_lat = math.sin(lat_rad)
    cos_lat = math.cos(lat_rad)
    tan_lat = math.tan(lat_rad)

    n = WGS84_A / math.sqrt(1 - e2 * sin_lat * sin_lat)
    t = tan_lat * tan_lat
    c = ep2 * cos_lat * cos_lat
    a = cos_lat * (lon_rad - lon0_rad)

    m = WGS84_A * (
        (1 - e2 / 4 - 3 * e2 * e2 / 64 - 5 * e2**3 / 256) * lat_rad
        - (3 * e2 / 8 + 3 * e2 * e2 / 32 + 45 * e2**3 / 1024) * math.sin(2 * lat_rad)
        + (15 * e2 * e2 / 256 + 45 * e2**3 / 1024) * math.sin(4 * lat_rad)
        - (35 * e2**3 / 3072) * math.sin(6 * lat_rad)
    )

    easting = K0 * n * (
        a
        + (1 - t + c) * a**3 / 6
        + (5 - 18 * t + t * t + 72 * c - 58 * ep2) * a**5 / 120
    ) + 500000.0

    northing = K0 * (
        m
        + n
        * tan_lat
        * (
            a * a / 2
            + (5 - t + 9 * c + 4 * c * c) * a**4 / 24
            + (61 - 58 * t + t * t + 600 * c - 330 * ep2) * a**6 / 720
        )
    )

    if not northern:
        northing += 10000000.0

    return easting / 1000.0, northing / 1000.0


def short_station_name(raw_name: str | None, station_id: str, width: int = 4) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", (raw_name or "").upper())
    if len(cleaned) >= width:
        return cleaned[:width]
    fallback = (cleaned + station_id)[-width:]
    return fallback.rjust(width, "0")

#!/usr/bin/env python3
"""Case-driven configurator for center_location, grid.cmn and research_time."""

from __future__ import annotations

import math
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from engine.core.paths import VENDOR_SRC_DIR, current_project_path

PROJECT_GRID_DIR = current_project_path("grid")
SOURCE_GRID_DIR = VENDOR_SRC_DIR / "grid"
CASE_YAML = current_project_path("case.yaml")

GRID_CMN = PROJECT_GRID_DIR / "grid.cmn"
CENTER_LOCATION = PROJECT_GRID_DIR / "center_location"
RESEARCH_TIME = PROJECT_GRID_DIR / "research_time"
SOURCE_GRID_CMN = SOURCE_GRID_DIR / "grid.cmn"
SOURCE_CENTER_LOCATION = SOURCE_GRID_DIR / "center_location"
SOURCE_RESEARCH_TIME = SOURCE_GRID_DIR / "research_time"

DEFAULT_ZFACES_9 = [0, 20, 40, 80, 160, 320, 640, 1200, 2000, 3000]

# WGS-84 ellipsoid constants
WGS84_A = 6378137.0
WGS84_F = 1 / 298.257223563
K0 = 0.9996


def load_case_config() -> dict[str, Any]:
    if not CASE_YAML.exists():
        raise FileNotFoundError(f"case.yaml not found: {CASE_YAML}")
    return yaml.safe_load(CASE_YAML.read_text(encoding="utf-8")) or {}


def _as_float(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid preprocess field {field}: {value}") from exc


def _as_int(value: Any, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid preprocess field {field}: {value}") from exc


def load_preprocess_grid_config(config: dict[str, Any]) -> dict[str, Any]:
    pre = config.get("preprocess") or {}
    grid = pre.get("grid") or {}
    center = grid.get("center") or {}
    domain = grid.get("domain") or {}
    research = pre.get("research_time") or {}

    lon = _as_float(center.get("longitude"), "preprocess.grid.center.longitude")
    lat = _as_float(center.get("latitude"), "preprocess.grid.center.latitude")
    length_km = _as_float(domain.get("length_km"), "preprocess.grid.domain.length_km")
    width_km = _as_float(domain.get("width_km"), "preprocess.grid.domain.width_km")
    dgrid_km = _as_float(grid.get("resolution_km"), "preprocess.grid.resolution_km")
    nz = _as_int(grid.get("nz", 9), "preprocess.grid.nz")

    begin_text = str(research.get("begin") or "").strip()
    end_text = str(research.get("end") or "").strip()
    time_pat = re.compile(r"^\d{8}-\d{6}$")
    if not time_pat.fullmatch(begin_text):
        raise ValueError("preprocess.research_time.begin must match YYYYMMDD-HHMMSS")
    if not time_pat.fullmatch(end_text):
        raise ValueError("preprocess.research_time.end must match YYYYMMDD-HHMMSS")

    begin_dt = datetime.strptime(begin_text, "%Y%m%d-%H%M%S")
    end_dt = datetime.strptime(end_text, "%Y%m%d-%H%M%S")
    if begin_dt > end_dt:
        raise ValueError("preprocess.research_time.begin must be <= end")

    if length_km <= 0 or width_km <= 0:
        raise ValueError("preprocess.grid.domain.length_km and width_km must be > 0")
    if dgrid_km <= 0:
        raise ValueError("preprocess.grid.resolution_km must be > 0")
    if nz <= 0:
        raise ValueError("preprocess.grid.nz must be > 0")

    return {
        "longitude": lon,
        "latitude": lat,
        "length_km": length_km,
        "width_km": width_km,
        "dgrid_km": dgrid_km,
        "nz": nz,
        "begin_text": begin_text,
        "end_text": end_text,
    }


def validate_lon_lat(lon: float, lat: float) -> None:
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"经度超范围: {lon}, 必须在 [-180, 180]")
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"纬度超范围: {lat}, 必须在 [-90, 90]")


def lon_lat_label(lon: float, lat: float):
    ew = "E" if lon >= 0 else "W"
    ns = "N" if lat >= 0 else "S"
    hemisphere = "N" if lat >= 0 else "S"
    return ew, ns, hemisphere


def utm_zone_number(lon: float, lat: float) -> int:
    zone = int((lon + 180) / 6) + 1

    if 56 <= lat < 64 and 3 <= lon < 12:
        zone = 32

    if 72 <= lat <= 84:
        if 0 <= lon < 9:
            zone = 31
        elif 9 <= lon < 21:
            zone = 33
        elif 21 <= lon < 33:
            zone = 35
        elif 33 <= lon < 42:
            zone = 37
    return zone


def lon_lat_to_utm(lon: float, lat: float):
    validate_lon_lat(lon, lat)
    if not (-80.0 <= lat <= 84.0):
        raise ValueError("UTM 常规适用纬度为 [-80, 84], 当前点超出范围")

    zone = utm_zone_number(lon, lat)
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

    if lat < 0:
        northing += 10000000.0

    return zone, easting, northing


def convert_lon_lat(lon: float, lat: float):
    validate_lon_lat(lon, lat)
    ew, ns, hemisphere = lon_lat_label(lon, lat)
    zone, x_m, y_m = lon_lat_to_utm(lon, lat)
    return {
        "ew": ew,
        "ns": ns,
        "hemisphere": hemisphere,
        "zone": zone,
        "x_km": x_m / 1000.0,
        "y_km": y_m / 1000.0,
    }


def replace_key_line(line: str, key: str, value: str) -> str:
    p = re.compile(rf"^(\s*!)\s*{re.escape(key)}\s*=\s*.*?!\s*$")
    if p.match(line):
        return f"! {key} =  {value}       !"
    return line


def sync_grid_templates_from_source() -> None:
    PROJECT_GRID_DIR.mkdir(parents=True, exist_ok=True)
    if not SOURCE_GRID_CMN.exists():
        raise FileNotFoundError(f"未找到 source 模板: {SOURCE_GRID_CMN}")
    shutil.copyfile(SOURCE_GRID_CMN, GRID_CMN)

    if not CENTER_LOCATION.exists() and SOURCE_CENTER_LOCATION.exists():
        shutil.copyfile(SOURCE_CENTER_LOCATION, CENTER_LOCATION)
    if not RESEARCH_TIME.exists() and SOURCE_RESEARCH_TIME.exists():
        shutil.copyfile(SOURCE_RESEARCH_TIME, RESEARCH_TIME)


def canonical_grid_origin_km(value: float) -> float:
    """Three decimal places in km (one-metre origin grid) are authoritative.

    Conversion from geographical coordinates may retain full precision for
    geodetic uses, but the *computational* P1/P2/P3/6 origin is quantized
    exactly once before sampling, never only formatted for grid.cmn.
    """
    if not math.isfinite(value):
        raise ValueError("GRID_ORIGIN_PRECISION: nonfinite UTM grid origin")
    return float(f"{value:.3f}")


def update_grid_file(
    zone: int,
    hemisphere: str,
    xref_km: float,
    yref_km: float,
    dgrid_km: float,
    nx: int,
    ny: int,
    nz: int,
) -> None:
    if (xref_km != canonical_grid_origin_km(xref_km)
            or yref_km != canonical_grid_origin_km(yref_km)):
        raise ValueError(
            "GRID_ORIGIN_PRECISION: grid.cmn may only receive already-quantized "
            "3-decimal-km origin coordinates")
    if not GRID_CMN.exists():
        raise FileNotFoundError(f"未找到文件: {GRID_CMN}")

    lines = GRID_CMN.read_text(encoding="utf-8").splitlines()
    out: list[str] = []

    zface_start = False
    zface_written = False
    for line in lines:
        stripped = line.strip()

        line = replace_key_line(line, "IUTMZN", str(zone))
        line = replace_key_line(line, "LSOHEM", hemisphere)
        line = replace_key_line(line, "XREFKM", f"{xref_km:.3f}")
        line = replace_key_line(line, "YREFKM", f"{yref_km:.3f}")
        line = replace_key_line(line, "DGRIDKM", f"{dgrid_km:g}")
        line = replace_key_line(line, "NX", str(nx))
        line = replace_key_line(line, "NY", str(ny))
        line = replace_key_line(line, "NZ", str(nz))

        if stripped.startswith("! ZFACE"):
            zface_start = True
            if not zface_written:
                if nz == 9:
                    values = DEFAULT_ZFACES_9
                else:
                    values = [0.0]
                    step = 20.0
                    for _ in range(nz):
                        values.append(values[-1] + step)
                        step *= 2.0
                for z in values:
                    ztxt = str(int(z)) if float(z).is_integer() else f"{z:.1f}"
                    out.append(f"! ZFACE =  {ztxt}        !")
                zface_written = True
            continue

        if zface_start and stripped.startswith("! ZFACE"):
            continue

        out.append(line)

    GRID_CMN.write_text("\n".join(out) + "\n", encoding="utf-8")


def update_center_location(lon: float, lat: float) -> None:
    CENTER_LOCATION.write_text(f"longitude:{lon}\nlatitude:{lat}\n", encoding="utf-8")


def update_research_time(begin_text: str, end_text: str) -> None:
    RESEARCH_TIME.write_text(f"BEGIN:{begin_text}\nEND:{end_text}\n", encoding="utf-8")


def main() -> int:
    sync_grid_templates_from_source()

    config = load_case_config()
    cfg = load_preprocess_grid_config(config)

    lon = cfg["longitude"]
    lat = cfg["latitude"]
    length_km = cfg["length_km"]
    width_km = cfg["width_km"]
    dgrid_km = cfg["dgrid_km"]
    nz = cfg["nz"]

    conv = convert_lon_lat(lon, lat)
    zone = int(conv["zone"])
    hemi = str(conv["hemisphere"])
    x_center_km = float(conv["x_km"])
    y_center_km = float(conv["y_km"])

    xref_km = canonical_grid_origin_km(x_center_km - length_km / 2.0)
    yref_km = canonical_grid_origin_km(y_center_km - width_km / 2.0)
    nx = math.ceil(length_km / dgrid_km)
    ny = math.ceil(width_km / dgrid_km)

    update_center_location(lon, lat)
    update_grid_file(
        zone=zone,
        hemisphere=hemi,
        xref_km=xref_km,
        yref_km=yref_km,
        dgrid_km=dgrid_km,
        nx=nx,
        ny=ny,
        nz=nz,
    )
    update_research_time(cfg["begin_text"], cfg["end_text"])

    print("配置完成 (case.yaml 驱动):")
    print(f"- UTM分区={zone}, 半球={hemi}")
    print(f"- 研究区域左下角(X,Y) km: {xref_km:.3f}, {yref_km:.3f}")
    print(f"- 网格分辨率(km): {dgrid_km:g}; NX={nx}, NY={ny}, NZ={nz}")
    print(f"- 研究时间范围: {cfg['begin_text']} -> {cfg['end_text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

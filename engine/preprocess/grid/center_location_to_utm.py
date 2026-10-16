#!/usr/bin/env python3
"""Library module: convert lon/lat (decimal degrees) to UTM on WGS-84.

Primary API:
- convert_lon_lat(lon, lat) -> dict
  Returns zone, hemisphere, E/W, N/S, and X/Y in km.

This module can also run standalone for quick manual check.
"""

from __future__ import annotations

import math
import argparse
from typing import Dict, Tuple


# WGS-84 ellipsoid
WGS84_A = 6378137.0
WGS84_F = 1 / 298.257223563
K0 = 0.9996
def validate_lon_lat(lon: float, lat: float) -> None:
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"经度超范围: {lon}，必须在 [-180, 180]")
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"纬度超范围: {lat}，必须在 [-90, 90]")


def lon_lat_label(lon: float, lat: float) -> Tuple[str, str, str]:
    ew = "E" if lon >= 0 else "W"
    ns = "N" if lat >= 0 else "S"
    hemisphere = "N" if lat >= 0 else "S"
    return ew, ns, hemisphere


def utm_zone_number(lon: float, lat: float) -> int:
    """Compute UTM zone with standard Norway/Svalbard exceptions."""
    zone = int((lon + 180) / 6) + 1

    # Norway exception
    if 56 <= lat < 64 and 3 <= lon < 12:
        zone = 32

    # Svalbard exceptions
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


def lon_lat_to_utm(lon: float, lat: float) -> Tuple[int, float, float]:
    """
    Convert lon/lat (degrees) to UTM.
    Return: (zone, easting_m, northing_m)
    """
    validate_lon_lat(lon, lat)

    # UTM valid latitude range is about [-80, 84]
    if not (-80.0 <= lat <= 84.0):
        raise ValueError("UTM 常规适用纬度为 [-80, 84]，当前点超出范围")

    zone = utm_zone_number(lon, lat)
    lon0 = (zone - 1) * 6 - 180 + 3  # central meridian

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


def convert_lon_lat(lon: float, lat: float) -> Dict[str, float | str]:
    """High-level conversion API for callers."""
    validate_lon_lat(lon, lat)
    ew, ns, hemisphere = lon_lat_label(lon, lat)
    zone, x_m, y_m = lon_lat_to_utm(lon, lat)
    return {
        "longitude": lon,
        "latitude": lat,
        "ew": ew,
        "ns": ns,
        "hemisphere": hemisphere,
        "zone": zone,
        "x_m": x_m,
        "y_m": y_m,
        "x_km": x_m / 1000.0,
        "y_km": y_m / 1000.0,
        "datum": "WGS-84",
    }


def format_result(result: Dict[str, float | str]) -> str:
    return (
        "UTM Output:\n"
        f"  longitude = {float(result['longitude']):.6f} ({result['ew']})\n"
        f"  latitude  = {float(result['latitude']):.6f} ({result['ns']})\n"
        f"  datum     = {result['datum']}\n"
        f"  zone      = {result['zone']}\n"
        f"  hemisphere= {result['hemisphere']}\n"
        f"  X (km)    = {float(result['x_km']):.3f}\n"
        f"  Y (km)    = {float(result['y_km']):.3f}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert lon/lat to UTM (WGS-84).")
    parser.add_argument("--lon", type=float, required=True, help="Longitude in decimal degrees")
    parser.add_argument("--lat", type=float, required=True, help="Latitude in decimal degrees")
    args = parser.parse_args()
    lon = args.lon
    lat = args.lat
    result = convert_lon_lat(lon, lat)
    print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

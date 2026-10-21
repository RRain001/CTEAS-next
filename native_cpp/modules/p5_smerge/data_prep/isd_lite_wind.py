"""NOAA ISD-Lite wind-only source and strict hourly parser (P5).

NOAA format: 12 whitespace-separated integer fields.  Direction field 8
(zero-based 7) in degrees and speed field 9 (zero-based 8) in tenths of m/s.
Missing: -9999. Calm: speed=0, direction=0. Wind from north: 360 degrees.
Other meteorological fields in this file MUST NOT be used for P5.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import gzip
import hashlib
from pathlib import Path
from urllib import error, request

# NOAA/NCEI retired the legacy ISD-Lite HTTPS endpoint in July 2026.
# Exact genuine NOAA NODD gzip verified in S4G Actions; this is source
# transport only and DOES NOT change observation parsing or fill policy.
BASE_URL = "https://noaa-isd-pds.s3.amazonaws.com/isd-lite/data"


@dataclass(frozen=True)
class LiteWind:
    direction_deg: float | None
    speed_mps: float | None
    source_direction_code: int
    source_speed_code: int
    flags: tuple[str, ...]


def filename(station_id: str, year: int) -> str:
    if not (len(station_id) == 11 and station_id.isalnum()):
        raise ValueError(f"invalid NOAA USAF-WBAN station id: {station_id}")
    return f"{station_id[:6]}-{station_id[6:]}-{year}.gz"


def source_url(station_id: str, year: int) -> str:
    return f"{BASE_URL}/{year}/{filename(station_id, year)}"


def download_lite_one(year: int, station_id: str, directory: Path,
                      timeout: int = 60) -> tuple[bool, str, bool]:
    """Obtain same-station/year ISD-Lite. No fallback to full-ISD WND."""
    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / filename(station_id, year)
    if dest.is_file():
        try:
            parse_lite_winds(dest, year, station_id)
            return True, f"valid cache {dest}", True
        except (ValueError, OSError, EOFError, gzip.BadGzipFile):
            # Source may have been interrupted; refetch, never use bad cache.
            dest.unlink(missing_ok=True)
    try:
        req = request.Request(source_url(station_id, year), headers={
            "User-Agent": "CTEAS-P5-ISD-Lite-wind-only/1.0"})
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read()
        if not body.startswith(b"\x1f\x8b"):
            raise ValueError("NOAA ISD-Lite source is not gzip")
        temporary = dest.with_suffix(".part")
        temporary.write_bytes(body)
        try:
            parse_lite_winds(temporary, year, station_id, validate_filename=False)
            temporary.replace(dest)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return True, str(dest), False
    except (error.HTTPError, error.URLError, TimeoutError, OSError, ValueError,
            EOFError, gzip.BadGzipFile) as exc:
        return False, str(exc), False


def parse_lite_winds(path: Path, year: int, station_id: str | None = None,
                     validate_filename: bool = True) -> dict[datetime, LiteWind]:
    """Parse strictly, fail closed on malformed dates/codes or duplicate hours."""
    if validate_filename and station_id is not None and path.name != filename(station_id, year):
        raise ValueError(f"ISD-Lite station/year file identity mismatch: {path.name}")
    result: dict[datetime, LiteWind] = {}
    with gzip.open(path, "rt", encoding="ascii") as source:
        for number, line in enumerate(source, start=1):
            tokens = line.split()
            if len(tokens) != 12:
                raise ValueError(f"ISD-Lite unexpected 12-column format line {number}: {tokens!r}")
            try:
                values = [int(x) for x in tokens]
                y, month, day, hour = values[:4]
                instant = datetime(y, month, day, hour)
            except ValueError as exc:
                raise ValueError(f"ISD-Lite invalid date/number line {number}") from exc
            if y != year:
                raise ValueError(f"ISD-Lite wrong year line {number}: {y} vs {year}")
            if instant in result:
                raise ValueError(f"ISD-Lite repeated hour {instant.isoformat()}")
            direct_code, speed_code = values[7], values[8]
            if direct_code != -9999 and not 0 <= direct_code <= 360:
                raise ValueError(f"ISD-Lite invalid wind direction {direct_code}")
            if speed_code != -9999 and not 0 <= speed_code <= 9000:
                raise ValueError(f"ISD-Lite invalid wind speed code {speed_code}")
            direction = float(direct_code) if direct_code != -9999 else None
            speed = speed_code / 10.0 if speed_code != -9999 else None
            flags: list[str] = []
            if speed == 0.0:
                # Do not destroy the source distinction: (0,0) is standard
                # calm and (360,0) is the user's second accepted calm code.
                # Stage 1 normalizes BOTH to (0,0); provenance stays intact.
                if direction == 360.0:
                    flags.append("CALM_360_ZERO_NORMALIZE_IN_CLEANING")
                elif direction != 0.0:
                    flags.append("ZERO_SPEED_NONCALM_BEARING_INVALID")
            elif speed is not None and speed > 0 and direction == 0.0:
                flags.append("NONZERO_SPEED_DIRECTION_ZERO_INVALID")
                direction = None
            if direction is None and speed is None:
                flags.append("BOTH_WIND_FIELDS_MISSING")
            elif direction is None:
                flags.append("WIND_DIRECTION_MISSING")
            elif speed is None:
                flags.append("WIND_SPEED_MISSING")
            result[instant] = LiteWind(direction, speed, direct_code,
                                       speed_code, tuple(flags))
    if not result:
        raise ValueError(f"ISD-Lite empty or not an observation source: {path}")
    return result


def lite_time_coverage(path: Path, year: int, station_id: str) -> tuple[int, int]:
    from calendar import isleap
    entries = parse_lite_winds(path, year, station_id)
    return len(entries), (8784 if isleap(year) else 8760)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for data in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()

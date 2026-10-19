#!/usr/bin/env python3
"""#123 D6-A: audit authentic GSHHS Full binary polygon headers near Wolsong.

This is an over-inclusive HEADER/bounding-box screen, not original COASTEXT
polygon extraction, projection, clipping, BLN, or scientific parity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct

from scripts.s2g import issue123_gshhg_binary_full as upstream

# Wolsong frozen #119: EPSG:32652, XREFKM=533.215, YREFKM=3942.629,
# DGRIDKM=.100, NX=200, NY=200. Broad envelope is intentionally larger
# than the nine-point WGS84 inverse-UTM range; diagnostic, NOT COASTEXT.
WOLSONG_LON = (129.30, 129.66)
WOLSONG_LAT = (35.56, 35.88)
WOLSONG_XREFKM = 533.215
WOLSONG_YREFKM = 3942.629
HEADER = struct.Struct(">11i")
MAX_POLYGONS = 2_000_000
MAX_POINTS_PER_POLYGON = 5_000_000
MAX_REPORTED_CANDIDATES = 64
STATUS = "D6A_AUTHENTIC_FULL_BINARY_HEADER_SCREEN_NOT_COASTEXT"


def parse_header(raw: bytes) -> dict:
    if len(raw) != HEADER.size:
        raise ValueError("D6A_TRUNCATED_POLYGON_HEADER")
    values = HEADER.unpack(raw)
    ident, npts, packed, west, east, south, north, area = values[:8]
    flag = packed & 0xffffffff
    level, version = flag & 255, (flag >> 8) & 255
    source = (flag >> 24) & 1
    if (ident < 0 or not 3 <= npts <= MAX_POINTS_PER_POLYGON or
            level not in (1, 2, 3, 4) or not 10 <= version <= 30 or
            not -360_000_000 <= west <= 360_000_000 or
            not -360_000_000 <= east <= 360_000_000 or
            not -90_000_000 <= south <= north <= 90_000_000):
        raise ValueError("D6A_INVALID_OR_INCOMPATIBLE_POLYGON_HEADER")
    return {"id": ident, "points": npts, "level": level,
            "version": version, "source_bit": source,
            "area": area, "west": west / 1e6, "east": east / 1e6,
            "south": south / 1e6, "north": north / 1e6}


def overlaps_diagnostic_box(h: dict) -> bool:
    if h["north"] < WOLSONG_LAT[0] or h["south"] > WOLSONG_LAT[1]:
        return False
    w, e = h["west"], h["east"]
    # Dateline / Greenwich-straddling polygons are retained conservatively.
    if w > e:
        return True
    # GSHHS may encode east longitudes on either [-180,180] or [0,360].
    return any(a <= e and b >= w for a, b in (
        WOLSONG_LON, (WOLSONG_LON[0] - 360, WOLSONG_LON[1] - 360)))


def scan_binary(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("D6A_AUTHENTIC_BINARY_FILE_REQUIRED")
    size = path.stat().st_size
    if size < HEADER.size:
        raise ValueError("D6A_AUTHENTIC_BINARY_TOO_SMALL")
    count, eligible, zero_area, candidates = 0, 0, 0, 0
    versions: dict[str, int] = {}
    levels: dict[str, int] = {}
    selected: list[dict] = []
    with path.open("rb") as source:
        while source.tell() < size:
            if count >= MAX_POLYGONS:
                raise ValueError("D6A_POLYGON_COUNT_BUDGET_EXCEEDED")
            h = parse_header(source.read(HEADER.size))
            end = source.tell() + h["points"] * 8
            if end > size:
                raise ValueError("D6A_TRUNCATED_POLYGON_POINTS")
            source.seek(end)
            count += 1
            levels[str(h["level"])] = levels.get(str(h["level"]), 0) + 1
            versions[str(h["version"])] = versions.get(str(h["version"]), 0) + 1
            if h["area"] == 0:
                zero_area += 1
            elif overlaps_diagnostic_box(h):
                candidates += 1
                if len(selected) < MAX_REPORTED_CANDIDATES:
                    selected.append(h)
            if h["area"] != 0:
                eligible += 1
    if count == 0 or candidates == 0:
        raise ValueError("D6A_EMPTY_OR_NO_WOLSONG_BBOX_CANDIDATES")
    return {"polygon_count": count, "nonzero_area_count": eligible,
            "zero_area_count": zero_area, "candidate_bbox_count": candidates,
            "candidate_sample": selected, "level_counts": levels,
            "header_version_counts": versions, "scanned_bytes": size}


def report(cache: Path) -> dict:
    # Verify authentic release SHA, exact member bytes and manifest from D5.
    source = upstream.verify(cache)
    data = scan_binary(cache / upstream.BINARY)
    if data["scanned_bytes"] != source["binary_size"]:
        raise ValueError("D6A_SOURCE_SIZE_MISMATCH")
    return {"status": STATUS, "case": "WOLSONG_2022",
            "grid": {"epsg": 32652, "xrefkm": WOLSONG_XREFKM,
                     "yrefkm": WOLSONG_YREFKM, "nx": 200, "ny": 200,
                     "dgridkm": 0.1},
            "diagnostic_bbox_lon": list(WOLSONG_LON),
            "diagnostic_bbox_lat": list(WOLSONG_LAT),
            "bbox_method": "BROAD_HEADER_ONLY_NOT_ORIGINAL_COASTEXT",
            "original_archive_sha256": source["archive_sha256"],
            "source_binary_sha256": source["binary_sha256"],
            **data, "original_coastext_bln": "NOT_RUN",
            "original_iptype_exact_parity": "NOT_RUN",
            "original_38class_hits_lu_parity": "NOT_RUN"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.is_symlink() or args.out.exists():
        parser.error("D6A_OUTPUT_MUST_BE_NEW_AND_NOT_SYMLINK")
    try:
        evidence = report(args.cache)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
        print(json.dumps({k: evidence[k] for k in (
            "status", "polygon_count", "candidate_bbox_count",
            "original_coastext_bln")}, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"D6A_FAIL_CLOSED:{type(exc).__name__}:{str(exc)[:160]}\n")


if __name__ == "__main__":
    raise SystemExit(main())

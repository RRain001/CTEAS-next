#!/usr/bin/env python3
"""Issue #84: manually authorized real NOAA source reconnaissance, NOT P5 science parity.

Only NOAA original ISD CSV + ISD-Lite gzip are downloaded. This does not
synthesize hours, choose an authoritative P5 station list, run SMERGE or
publish weather or source archives. The existing selector remains authority.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

from engine.run_met.station_grid import load_strict_utm_grid
from native_cpp.modules.p5_smerge.data_prep import download_isd_by_grid as full
from native_cpp.modules.p5_smerge.data_prep import isd_lite_wind as lite

ROOT = Path(__file__).resolve().parents[2]
WOLSONG = {
    "name": "wolsong_20km_2022_frozen_p2b_grid",
    "utm_zone": 52, "xrefkm": "533.215", "yrefkm": "3942.629",
    "nx": 200, "ny": 200, "dgridkm": "0.100",
    "lat": 35.716670, "lon": 129.477780,
    "authority": "CTEAS-next Issue #119 (representative source, not exact stack)",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def make_frozen_grid(path: Path) -> None:
    """Use #119's explicit quantized UTM origin; never recompute from lat/lon."""
    p = WOLSONG
    rows = [
        "! IMAP = UTM !", f"! IUTMZN = {p['utm_zone']} !",
        "! LSOHEM = N !", "! DATUM = WGS-84 !",
        f"! XREFKM = {p['xrefkm']} !", f"! YREFKM = {p['yrefkm']} !",
        f"! DGRIDKM = {p['dgridkm']} !", f"! NX = {p['nx']} !",
        f"! NY = {p['ny']} !", "! NZ = 9 !",
    ]
    rows += [f"! ZFACE = {z} !" for z in
             (0, 20, 40, 80, 160, 320, 640, 1200, 2000, 3000)]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def feb29_hours_full(path: Path, year: int, sid: str) -> int | None:
    if year != 2024:
        return None
    found: set[int] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if (row.get("STATION") or "").strip() != sid:
                raise ValueError("full ISD station identity changed")
            date = row.get("DATE", "").replace("Z", "+00:00")
            try:
                moment = datetime.fromisoformat(date)
            except ValueError:
                continue
            if moment.tzinfo is not None:
                moment = moment.astimezone(timezone.utc)
            if (moment.year, moment.month, moment.day) == (2024, 2, 29):
                found.add(moment.hour)
    return len(found)


def inspect_one(station, year: int, raw_root: Path) -> dict:
    sid = station.sid
    csv_path = raw_root / f"{sid}-{year}.csv"
    lite_dir = raw_root / "isd_lite"
    gz_path = lite_dir / lite.filename(sid, year)
    a, reason_a, _ = full.download_one(year, sid, raw_root, timeout=75)
    b, reason_b, _ = lite.download_lite_one(year, sid, lite_dir, timeout=75)
    outcome = {
        "year": year, "station_id": sid,
        "full_source_url": full.station_url(year, sid),
        "lite_source_url": lite.source_url(sid, year),
        "full_download_ok": bool(a), "lite_download_ok": bool(b),
        "full_error": None if a else reason_a[:300],
        "lite_error": None if b else reason_b[:300],
        "calendar_hours": full.expected_hours_in_year(year),
        "original_full_hours": None, "original_lite_hours": None,
        "full_sha256": None, "lite_sha256": None,
        "feb29_full_hours": None, "feb29_lite_hours": None,
        "both_raw_coverage_gt_90_percent": False,
    }
    if a:
        n, hours = full.original_coverage(csv_path, year, sid)
        outcome["original_full_hours"] = n
        outcome["full_sha256"] = sha256(csv_path)
        outcome["feb29_full_hours"] = feb29_hours_full(csv_path, year, sid)
        assert hours == outcome["calendar_hours"]
    if b:
        n, hours = lite.lite_time_coverage(gz_path, year, sid)
        outcome["original_lite_hours"] = n
        outcome["lite_sha256"] = sha256(gz_path)
        if year == 2024:
            moments = lite.parse_lite_winds(gz_path, year, sid)
            outcome["feb29_lite_hours"] = sum(
                d.month == 2 and d.day == 29 for d in moments
            )
        assert hours == outcome["calendar_hours"]
    if a and b:
        h = outcome["calendar_hours"]
        outcome["both_raw_coverage_gt_90_percent"] = (
            outcome["original_full_hours"] / h > .90
            and outcome["original_lite_hours"] / h > .90
        )
    return outcome


def run(years: list[int], max_nearest: int) -> dict:
    if len(set(years)) != len(years) or not years or any(y not in (2022, 2023, 2024) for y in years):
        raise ValueError("year list must be unique and within 2022,2023,2024")
    if max_nearest < 0 or max_nearest > 12:
        raise ValueError("max_nearest must be between 0 and 12")
    history_file = ROOT / "engine/resources/isd/isd-history.txt"
    with tempfile.TemporaryDirectory(prefix="cteas-issue84-noaa-") as temporary:
        scratch = Path(temporary)
        grid_file = scratch / "grid.cmn"
        make_frozen_grid(grid_file)
        grid = load_strict_utm_grid(grid_file, context="Issue84 Wolsong frozen source screen")
        stations = full.parse_history_txt(history_file)
        first = datetime(min(years), 1, 1)
        last = datetime(max(years), 12, 31, 23)
        catalog = [s for s in stations if full.covers_interval(s.begin, s.end, first, last)]
        inside = sorted((s for s in catalog if full.station_in_utm_grid(s, grid)),
                        key=lambda s: s.sid)
        outside = sorted((s for s in catalog if not full.station_in_utm_grid(s, grid)),
                         key=lambda s: (
                             full.haversine_km(WOLSONG["lat"], WOLSONG["lon"], s.lat, s.lon),
                             s.sid,
                         ))
        if len(inside) > 20:
            raise ValueError("unexpected >20 catalog in-domain candidates; manual review required")
        candidates = inside + outside[:max_nearest]
        source = scratch / "noaa_originals"
        source.mkdir()
        records: list[dict] = []
        for station in candidates:
            station_rec = {
                "sid": station.sid, "name": station.name, "country": station.country,
                "source_lat": station.lat, "source_lon": station.lon,
                "inside_frozen_utm_grid": station in inside,
                "distance_to_representative_km": round(full.haversine_km(
                    WOLSONG["lat"], WOLSONG["lon"], station.lat, station.lon), 3),
                "yearly_originals": [],
            }
            for year in years:
                station_rec["yearly_originals"].append(inspect_one(station, year, source))
            records.append(station_rec)
        ranking = {}
        for year in years:
            eligible = [
                (s, next(y for y in s["yearly_originals"] if y["year"] == year))
                for s in records if s["inside_frozen_utm_grid"]
            ]
            eligible = [(s, y) for s, y in eligible
                        if y["original_lite_hours"] is not None
                        and y["original_full_hours"] is not None]
            eligible.sort(key=lambda v: (
                -v[1]["original_lite_hours"], -v[1]["original_full_hours"], v[0]["sid"]))
            ranking[str(year)] = eligible[0][0]["sid"] if eligible else None
        failures = [f"{s['sid']}/{y['year']}" for s in records
                    for y in s["yearly_originals"]
                    if not y["full_download_ok"] or not y["lite_download_ok"]]
        return {
            "schema": "ISSUE84_REAL_NOAA_SOURCE_SCREEN_V1",
            "status": ("SOURCE_SCREEN_NO_CANDIDATES" if not records else
                       "SOURCE_SCREEN_PARTIAL" if failures else
                       "SOURCE_SCREEN_COMPLETE_METADATA_ONLY"),
            "science_acceptance": False,
            "original_smerge_executed": False, "native_cpp_smerge_executed": False,
            "station_selector_executed": False, "p5_original_parity": "NOT_RUN",
            "p5_to_g19": "NOT_RUN", "wet_deposition": "NOT_RUN",
            "site": WOLSONG, "grid_cmn_sha256": sha256(grid_file),
            "isd_history_sha256": sha256(history_file), "years": years,
            "calendar_hours_by_year": {str(y): full.expected_hours_in_year(y) for y in years},
            "catalog_in_domain_count": len(inside),
            "catalog_in_domain_sids": [s.sid for s in inside],
            "nearest_offdomain_candidates_screened": max_nearest,
            "note": (
                "Catalog screening is not authoritative station selection. "
                "A real 0/1/N case needs a separately admitted site and complete "
                "original P5 selector+producer+Fortran/C++ parity. "
                "Rank change is a hypothesis only, not observed primary switching."
            ),
            "screened_indomain_rank_by_year_not_verified_primary": ranking,
            "download_or_validation_failures": failures, "stations": records,
            "original_noaa_archives_redistributed": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", default="2023,2024")
    parser.add_argument("--max-nearest", type=int, default=6)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    years = [int(x.strip()) for x in args.years.split(",")]
    evidence = run(years, args.max_nearest)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("ISSUE84_NOAA_SCREEN=" + evidence["status"])
    print("ISSUE84_P5_SCIENCE=NOT_RUN")
    print("ISSUE84_METADATA=" + str(args.out))
    return 0 if evidence["status"] == "SOURCE_SCREEN_COMPLETE_METADATA_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())

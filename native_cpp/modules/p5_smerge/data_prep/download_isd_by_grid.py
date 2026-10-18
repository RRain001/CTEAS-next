#!/usr/bin/env python3
"""
Download ISD global-hourly station CSVs using the actual CALMET UTM grid.

The numerical grid's SW corner, projection, spacing and dimensions come
exclusively from grid.cmn (the P1/P2/P3/P6 authority), NOT from a geographic
latitude/longitude rectangle centred on center_location. The latter is only
source metadata. Apply strict projected station geometry before download;
annual NOAA coverage and fallback policies remain unchanged.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
from urllib import error, request

from engine.core.paths import current_project_path, engine_path
from engine.run_met.common import GridDef, lon_lat_to_utm_km, parse_grid_cmn

CASE_ROOT = current_project_path()

DEFAULT_CENTER = CASE_ROOT / "grid" / "center_location"
DEFAULT_GRID = CASE_ROOT / "grid" / "grid.cmn"
DEFAULT_HISTORY = engine_path("resources", "isd", "isd-history.txt")
DEFAULT_RESEARCH_TIME = CASE_ROOT / "grid" / "research_time"
DEFAULT_OUT_DIR = CASE_ROOT / "met" / "surface" / "isd_raw"
BASE_URL = "https://noaa-global-hourly-pds.s3.amazonaws.com"


@dataclass
class Station:
    sid: str
    lat: float
    lon: float
    elev: float
    name: str
    country: str
    begin: str
    end: str


def parse_center(path: Path) -> tuple[float, float]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    m_lon = re.search(r"longitude\s*:\s*([+-]?\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    m_lat = re.search(r"latitude\s*:\s*([+-]?\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
    if not m_lon or not m_lat:
        raise ValueError(f"Cannot parse longitude/latitude from: {path}")
    return float(m_lon.group(1)), float(m_lat.group(1))


# Backwards-compatible exported functions; P4 and P5 share one geometry kernel.
from engine.run_met.station_grid import (
    load_strict_utm_grid, utm_bounds_km as _utm_bounds_km,
    contains_projected_utm_km as _contains_projected_utm_km,
    lon_lat_in_utm_grid,
)


def load_utm_grid(path: Path) -> GridDef:
    return load_strict_utm_grid(path, context="P5")


def utm_bounds_km(grid: GridDef) -> tuple[float, float, float, float]:
    return _utm_bounds_km(grid)


def contains_projected_utm_km(x: float, y: float, grid: GridDef) -> bool:
    return _contains_projected_utm_km(x, y, grid)


def station_in_utm_grid(st: Station, grid: GridDef) -> bool:
    # Preserve the P5 projection seam for independent source and zone tests.
    # Bounds and projection convention are identical to the shared P4 kernel.
    try:
        x, y = lon_lat_to_utm_km(st.lon, st.lat, grid.iutmzn, grid.lsohem == "N")
    except ValueError:
        return False
    return contains_projected_utm_km(x, y, grid)


def parse_history_txt(path: Path) -> list[Station]:
    stations: list[Station] = []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    data_started = False
    for line in lines:
        s = line.strip()
        if not data_started:
            if s.startswith("USAF") and "WBAN" in s and "BEGIN" in s and "END" in s:
                data_started = True
            continue
        if not s:
            continue
        try:
            # NOAA ISD history fixed-width first (more reliable for station names)
            usaf = line[0:6].strip()
            wban = line[7:12].strip()
            name = line[13:43].strip()
            country = line[43:46].strip() or "UNK"
            lat = float(line[57:64].strip())
            lon = float(line[65:73].strip())
            elev = float(line[74:81].strip())
            begin = line[82:90].strip()
            end = line[91:99].strip()
            if not usaf or not wban or not begin or not end:
                raise ValueError("fixed-width parse fallback")

            sid = f"{usaf}{wban}"
            stations.append(
                Station(
                    sid=sid,
                    lat=lat,
                    lon=lon,
                    elev=elev,
                    name=name,
                    country=country,
                    begin=begin,
                    end=end,
                )
            )
        except Exception:
            # fallback split parse
            parts = s.split()
            if len(parts) < 9:
                continue
            try:
                usaf = parts[0]
                wban = parts[1]
                sid = f"{usaf}{wban}"
                lat = float(parts[-5])
                lon = float(parts[-4])
                elev = float(parts[-3])
                begin = parts[-2]
                end = parts[-1]
                country = parts[3] if len(parts) > 4 else "UNK"
                name = " ".join(parts[2:-7]).strip() if len(parts) > 9 else ""
                stations.append(
                    Station(
                        sid=sid,
                        lat=lat,
                        lon=lon,
                        elev=elev,
                        name=name,
                        country=country,
                        begin=begin,
                        end=end,
                    )
                )
            except Exception:
                continue
    return stations


def parse_research_time(path: Path) -> tuple[datetime, datetime]:
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


def covers_interval(begin: str, end: str, first: datetime, last: datetime) -> bool:
    """Station-history coverage for the exact requested period, inclusive."""
    if not (re.fullmatch(r"\d{8}", begin or "") and re.fullmatch(r"\d{8}", end or "")):
        return False
    return begin <= first.strftime("%Y%m%d") and end >= last.strftime("%Y%m%d")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dl = math.radians(lat2 - lat1)
    do = math.radians(lon2 - lon1)
    a = math.sin(dl / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(
        math.radians(lat2)
    ) * math.sin(do / 2) ** 2
    return 6371.0088 * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0, 1 - a)))


def read_stack_position(args: argparse.Namespace) -> tuple[float, float] | None:
    """Never silently equate model domain center with the release-stack location."""
    if (args.stack_lat is None) != (args.stack_lon is None):
        raise ValueError("both --stack-lat and --stack-lon are required")
    if args.stack_lat is not None:
        lat, lon = args.stack_lat, args.stack_lon
    elif args.stack_file and args.stack_file.is_file():
        lon, lat = parse_center(args.stack_file)
    else:
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("stack latitude/longitude outside valid range")
    return lat, lon


def station_url(year: int, sid: str) -> str:
    return f"{BASE_URL}/{year}/{sid}.csv"


def expected_hours_in_year(year: int) -> int:
    leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    return 8784 if leap else 8760


REQUIRED_NOAA_FIELDS = {"STATION", "DATE", "WND", "TMP", "DEW", "SLP"}


def original_coverage(csv_path: Path, year: int, station_id: str | None = None) -> tuple[int, int]:
    """Count unique UTC source hours BEFORE all filling, not the final 8760 rows."""
    times: set[datetime] = set()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not REQUIRED_NOAA_FIELDS.issubset(reader.fieldnames):
            raise ValueError(f"NOAA schema mismatch: {reader.fieldnames}")
        for row in reader:
            if station_id is not None and (row.get("STATION") or "").strip() != station_id:
                raise ValueError(f"NOAA STATION mismatch expected {station_id}")
            raw = (row.get("DATE") or "").strip()
            if not raw:
                continue
            try:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                continue
            # NOAA Global Hourly timestamps are UTC; normalize aware timestamps.
            if parsed.tzinfo is not None:
                from datetime import timezone
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            if parsed.year == year:
                times.add(parsed.replace(minute=0, second=0, microsecond=0))
    return len(times), expected_hours_in_year(year)


def validate_time_completeness(csv_path: Path, year: int, station_id: str | None = None) -> tuple[bool, str]:
    """Explicit >=80% annual *raw time* coverage. 2022: >=7008 of 8760."""
    try:
        found, expected = original_coverage(csv_path, year, station_id)
    except (OSError, ValueError) as exc:
        return False, str(exc)
    ratio = found / expected
    accepted = found >= math.ceil(expected * 0.8 - 1e-10)
    return accepted, f"source_unique_hours={found}/{expected}; coverage={ratio:.4%}; >=80%={'PASS' if accepted else 'FAIL'}"


def download_one(year: int, sid: str, out_dir: Path, timeout: int) -> tuple[bool, str, bool]:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{sid}-{year}.csv"
    url = station_url(year, sid)
    if out_file.exists() and out_file.stat().st_size > 0:
        try:
            original_coverage(out_file, year, sid)  # validate all cached NOAA identity/schema
        except (OSError, ValueError) as exc:
            return False, f"invalid cached source {out_file}: {exc}", True
        return True, f"已存在, 跳过：{out_file}", True
    try:
        with request.urlopen(url, timeout=timeout) as resp:
            data = resp.read()
        # The former NCEI endpoint retired in July 2026 and can return
        # 200-OK HTML. Reject anything other than the expected station CSV.
        try:
            header = next(csv.reader([data.split(b"\n", 1)[0].decode("utf-8-sig")]))
        except (UnicodeDecodeError, csv.Error, StopIteration) as exc:
            raise ValueError("NOAA Global Hourly response is not CSV") from exc
        required = REQUIRED_NOAA_FIELDS
        if not required.issubset(header):
            raise ValueError(f"NOAA Global Hourly CSV headers absent: {header[:8]!r}")
        if len(data) < 256:
            raise ValueError("NOAA Global Hourly CSV response suspiciously short")
        out_file.write_bytes(data)
        try:
            original_coverage(out_file, year, sid)
        except (OSError, ValueError) as exc:
            out_file.unlink(missing_ok=True)
            raise ValueError(f"Downloaded NOAA CSV identity/schema mismatch: {exc}") from exc
        return True, str(out_file), False
    except error.HTTPError as e:
        return False, f"HTTP {e.code}", False
    except Exception as e:
        return False, str(e), False


def main() -> int:
    ap = argparse.ArgumentParser(description="P5 scoped NOAA source selection and download")
    ap.add_argument("--year", type=int, help="target calendar year, else research_time years")
    ap.add_argument("--center-file", type=Path, default=DEFAULT_CENTER)
    ap.add_argument("--grid-file", type=Path, default=DEFAULT_GRID)
    ap.add_argument("--research-time-file", type=Path, default=DEFAULT_RESEARCH_TIME)
    ap.add_argument("--history-file", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--stack-lat", type=float, default=None)
    ap.add_argument("--stack-lon", type=float, default=None)
    ap.add_argument("--stack-file", type=Path,
                    default=CASE_ROOT / "grid" / "stack_location")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--max-stations", type=int, default=0,
                    help="legacy argument; only 0 is accepted (all in-domain stations)")
    ap.add_argument("--offline", action="store_true",
                    help="D2-A: use only archived original ISD and ISD-Lite; NEVER network")
    args = ap.parse_args()
    if args.max_stations != 0:
        ap.error("--max-stations must be 0: never truncate in-domain stations")
    if args.year is not None and not 1901 <= args.year <= 2100:
        ap.error("invalid target year")
    if args.retries < 1:
        ap.error("--retries must be >=1")
    research_start, research_end = parse_research_time(args.research_time_file)
    if args.year is not None:
        years = [args.year]
    else:
        years = list(range(research_start.year, research_end.year + 1))
    # Validate that geographic centre metadata is present, but never use it
    # to construct the numerical domain: grid.cmn owns the SW corner.
    center_lon, center_lat = parse_center(args.center_file)
    grid = load_utm_grid(args.grid_file)
    bounds = utm_bounds_km(grid)
    stack = read_stack_position(args)
    stations = parse_history_txt(args.history_file)
    if not stations:
        raise SystemExit("NOAA history is empty or invalid")
    from .station_identity import numeric_station_ids
    import json

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for year in years:
        first = max(research_start, datetime(year, 1, 1))
        last = min(research_end, datetime(year, 12, 31, 23, 59, 59))
        if first > last:
            if args.year is not None:
                first, last = datetime(year, 1, 1), datetime(year, 12, 31, 23, 59, 59)
            else:
                continue
        eligible = [st for st in stations if covers_interval(st.begin, st.end, first, last)]
        in_domain = sorted((st for st in eligible if station_in_utm_grid(st, grid)), key=lambda st: st.sid)
        mode = "OBSERVED" if in_domain else "VIRTUAL_RELOCATED"
        if mode == "VIRTUAL_RELOCATED" and stack is None:
            raise SystemExit("No stations inside research domain: --stack-lat/--stack-lon "
                             "or grid/stack_location required for nearest-station fallback")
        if mode == "VIRTUAL_RELOCATED":
            ordered = sorted(eligible, key=lambda st: (
                haversine_km(stack[0], stack[1], st.lat, st.lon), st.sid))
        else:
            ordered = in_domain
        if not ordered:
            raise SystemExit(f"No station history covers target period {first} -> {last}")

        accepted: list[Station] = []
        decisions = []
        from .isd_lite_wind import (download_lite_one, lite_time_coverage,
                                    filename as lite_filename, source_url as lite_source_url,
                                    sha256_file)
        lite_dir = args.out_dir / "isd_lite"
        accepted_lite: dict[str, dict] = {}
        coverage: dict[str, tuple[int, int, int]] = {}
        for st in ordered:
            success = False
            detail = ""
            if args.offline:
                candidate = args.out_dir / f"{st.sid}-{year}.csv"
                # Never silently skip a closer external station lacking an
                # archived source: it may be the nearest qualified fallback.
                if candidate.is_symlink() or not candidate.is_file():
                    raise SystemExit(
                        f"P5_OFFLINE_UNRESOLVED_CANDIDATE year={year} sid={st.sid}: "
                        "full-ISD archive missing; no network, no silent skip"
                    )
                try:
                    original_coverage(candidate, year, st.sid)
                except (ValueError, OSError) as exc:
                    raise SystemExit(f"P5_OFFLINE_INVALID_FULL_ISD {candidate}: {exc}") from exc
                success, detail = True, f"offline verified cache {candidate}"
            else:
                for attempt in range(args.retries):
                    success, detail, _ = download_one(year, st.sid, args.out_dir, args.timeout)
                    if success:
                        break
            full_count, expected = (0, expected_hours_in_year(year))
            if success:
                try:
                    full_count, expected = original_coverage(
                        args.out_dir / f"{st.sid}-{year}.csv", year, st.sid)
                    msg = f"full_ISD_source_hours={full_count}/{expected}; coverage={full_count/expected:.4%}"
                except (ValueError, OSError) as exc:
                    success = False
                    msg = f"invalid full ISD source: {exc}"
            else:
                msg = f"full ISD download failed: {detail}"
            lite_ok, lite_msg, lite_count = False, "ISD-Lite not attempted", 0
            if success and (mode == "OBSERVED" or full_count * 10 > 9 * expected):
                if args.offline:
                    candidate_lite = lite_dir / lite_filename(st.sid, year)
                    if candidate_lite.is_symlink() or not candidate_lite.is_file():
                        raise SystemExit(
                            f"P5_OFFLINE_UNRESOLVED_CANDIDATE year={year} sid={st.sid}: "
                            "ISD-Lite archive missing; no network, no silent skip"
                        )
                    lite_ok, lite_msg = True, "offline existing ISD-Lite archive"
                else:
                    for attempt in range(args.retries):
                        lite_ok, lite_msg, _ = download_lite_one(
                            year, st.sid, lite_dir, args.timeout)
                        if lite_ok:
                            break
                if lite_ok:
                    lite_file = lite_dir / lite_filename(st.sid, year)
                    try:
                        lite_count, lite_expected = lite_time_coverage(lite_file, year, st.sid)
                        if lite_expected != expected:
                            raise ValueError("full ISD and ISD-Lite calendar denominators disagree")
                        lite_msg = (f"original_ISD_Lite_hours={lite_count}/{expected}; "
                                    f"coverage={lite_count/expected:.4%}")
                    except (ValueError, OSError, EOFError) as exc:
                        lite_ok, lite_msg = False, f"invalid ISD-Lite source: {exc}"
            if success and mode == "VIRTUAL_RELOCATED" and full_count * 10 <= 9 * expected:
                lite_msg = "not downloaded: full ISD original coverage <=90% strict external gate"
            # No in-domain observations: strict > 90% for BOTH source files
            # in the exact calendar year. 90.000% is NOT sufficient.
            strict_external_pass = (
                full_count * 10 > 9 * expected and
                lite_count * 10 > 9 * expected)
            selected = success and lite_ok and (
                mode == "OBSERVED" or strict_external_pass)
            distance = haversine_km(stack[0], stack[1], st.lat, st.lon) if stack else None
            decisions.append({
                "sid": st.sid, "distance_to_stack_km": distance,
                "full_isd_download_success": success, "raw_annual_coverage": msg,
                "isd_lite_wind_download_success": lite_ok,
                "isd_lite_wind_original_hour_coverage": lite_msg,
                "full_isd_source_hours": full_count,
                "isd_lite_source_hours": lite_count,
                "expected_calendar_hours": expected,
                "strict_external_gt90_both_sources": strict_external_pass,
                "selected": selected,
            })
            print(f"candidate year={year} sid={st.sid} mode={mode} "
                  f"full_ISD={msg} wind_ISD_Lite={lite_msg} "
                  f"external_gt90_both={strict_external_pass}", flush=True)
            if selected:
                accepted.append(st)
                coverage[st.sid] = (lite_count, full_count, expected)
                accepted_lite[st.sid] = {
                    "url": lite_source_url(st.sid, year),
                    "filename": lite_filename(st.sid, year),
                    "sha256": sha256_file(lite_dir / lite_filename(st.sid, year)),
                    "original_hours": lite_count,
                    "expected_hours": expected,
                    "coverage_fraction": lite_count / expected,
                }
                if mode == "VIRTUAL_RELOCATED":
                    break
            elif mode == "OBSERVED":
                # One or more physical stations must have both raw NOAA
                # products, but NO raw-hour threshold is imposed.
                print(f"ERROR in-domain station {st.sid}: raw={msg}, lite={lite_msg}")

        # Only ONE reference station receives complete fill and calm
        # replacement. With >=2 physical stations, choose the highest raw
        # ISD-Lite annual coverage; tie-break full-ISD coverage, then station
        # ID for deterministic outcomes. Redo selection every calendar year.
        primary = (sorted(accepted, key=lambda st: (
            -coverage[st.sid][0], -coverage[st.sid][1], st.sid))[0]
            if accepted else None)
        station_selection_case = (
            "EXTERNAL_SINGLE_VIRTUAL" if mode == "VIRTUAL_RELOCATED" else
            "IN_DOMAIN_SINGLE" if len(in_domain) == 1 else
            "IN_DOMAIN_MULTIPLE")
        report = args.out_dir / f"download_report_{year}.json"
        report.write_text(json.dumps({
            "year": year, "mode": mode,
            "selection_geometry": "STRICT_WGS84_UTM_GRID_CMN_SW_CORNER_CLOSED_EDGES",
            "utm_zone": grid.iutmzn, "utm_hemisphere": grid.lsohem,
            "utm_bounds_km": bounds, "utm_grid_shape": [grid.nx, grid.ny],
            "utm_grid_spacing_km": grid.dgridkm,
            "center_location_metadata_lonlat": [center_lon, center_lat],
            "stack_latlon": stack, "candidates": decisions,
            "source_coverage_rule": "no in-domain: nearest station with >90% unique original UTC hours in BOTH ISD and ISD-Lite, per calendar year; any in-domain station: no coverage threshold",
            "station_selection_case": station_selection_case,
            "primary_sid": primary.sid if primary else None,
            "primary_selection_metric": "ISD_LITE_UNIQUE_ORIGINAL_HOURS_THEN_FULL_ISD",
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if not accepted or (mode == "OBSERVED" and len(accepted) != len(in_domain)):
            raise SystemExit(f"P5 source selection failed for {year}; see {report}")
        aliases = numeric_station_ids([s.sid for s in accepted])
        manifest_rows = []
        for st in accepted:
            lat, lon = (st.lat, st.lon) if mode == "OBSERVED" else stack
            lc, fc, expected = coverage[st.sid]
            treatment = ("COMPLETE_FILL_AND_CALM_REPLACE" if st.sid == primary.sid
                         else "RAW_SPARSE_STANDARDIZE_ONLY")
            manifest_rows.append({
                "sid": st.sid, "name": st.name, "country": st.country,
                "begin": st.begin, "end": st.end, "lat": lat, "lon": lon,
                "elev": st.elev, "source_lat": st.lat, "source_lon": st.lon,
                "source_elev": st.elev, "ifstn": aliases[st.sid],
                "relocated": mode == "VIRTUAL_RELOCATED",
                "raw_annual_coverage": f"{fc}/{expected}={fc/expected:.4%}",
                "full_isd_raw_hours": fc,
                "isd_lite_raw_hours": lc,
                "expected_hours": expected,
                "full_isd_coverage": fc / expected,
                "isd_lite_coverage": lc / expected,
                "wind_treatment": treatment,
                "wind_data_source": "NOAA_ISD_LITE",
                "wind_isd_lite": accepted_lite[st.sid]
            })
        manifest = args.out_dir / f"station_selection_{year}.json"
        manifest.write_text(json.dumps({
            "year": year, "mode": mode,
            "selection_geometry": "STRICT_WGS84_UTM_GRID_CMN_SW_CORNER_CLOSED_EDGES",
            "utm_zone": grid.iutmzn, "utm_hemisphere": grid.lsohem,
            "utm_bounds_km": bounds,
            "station_selection_case": station_selection_case,
            "primary_sid": primary.sid,
            "external_raw_coverage_rule": "STRICT_GREATER_THAN_90_PERCENT_BOTH_SOURCES",
            "stations": manifest_rows
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        listing = args.out_dir / f"surf_station_list_{year}.txt"
        with listing.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=[
                "sid", "name", "lat", "lon", "elev", "country", "begin", "end",
                "source_lat", "source_lon", "source_elev", "ifstn", "relocated"
            ], extrasaction="ignore")
            writer.writeheader()
            writer.writerows(manifest_rows)
        print(f"P5_SELECTED year={year} mode={mode} station_count={len(accepted)} "
              f"stations={','.join(st.sid for st in accepted)} manifest={manifest}", flush=True)

    # IDs must remain stable ACROSS YEARS even if the set of physical NOAA
    # stations changes from year to year. Reconcile only after all annual
    # selections are complete; otherwise a duplicate USAF may be resolved
    # differently in different years, corrupting SMERGE IFSTN mapping.
    if len(years) > 1:
        manifests = [args.out_dir / f"station_selection_{year}.json" for year in years]
        payloads = [json.loads(p.read_text(encoding="utf-8")) for p in manifests]
        selected_sids = sorted({
            row["sid"] for payload in payloads for row in payload["stations"]
        })
        aliases_across_years = numeric_station_ids(selected_sids)
        for year, manifest, payload in zip(years, manifests, payloads):
            for row in payload["stations"]:
                row["ifstn"] = aliases_across_years[row["sid"]]
            payload["alias_scope"] = "ALL_SELECTED_STATION_IDENTITIES_ACROSS_RESEARCH_YEARS"
            manifest.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",
                                encoding="utf-8")
            listing = args.out_dir / f"surf_station_list_{year}.txt"
            with listing.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "sid", "name", "lat", "lon", "elev", "country",
                    "begin", "end", "source_lat", "source_lon",
                    "source_elev", "ifstn", "relocated"], extrasaction="ignore")
                writer.writeheader()
                writer.writerows(payload["stations"])
        print(f"P5_YEARLY_ALIAS_RECONCILIATION=PASS years={years} "
              f"unique_station_ids={len(selected_sids)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

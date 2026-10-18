import argparse
import json
import csv
import math
import re
import urllib.request
import zipfile
from pathlib import Path

from engine.core.paths import current_project_path, engine_path
from engine.run_met.station_grid import load_strict_utm_grid, lon_lat_in_utm_grid

DATA_ROOT = current_project_path("met", "upperair")


def parse_center(center_path: Path):
    text = center_path.read_text(encoding='utf-8', errors='ignore')
    lon_m = re.search(r'longitude\s*:\s*([-+]?\d+(?:\.\d+)?)', text)
    lat_m = re.search(r'latitude\s*:\s*([-+]?\d+(?:\.\d+)?)', text)
    if not lon_m or not lat_m:
        raise ValueError('center_location 格式无法解析 longitude/latitude')
    return float(lat_m.group(1)), float(lon_m.group(1))


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def load_station_list(station_list_path: Path):
    stations = []
    with station_list_path.open('r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                stn_id = line[0:11].strip()
                lat = float(line[12:20].strip())
                lon = float(line[21:30].strip())
                elev = float(line[31:37].strip())
                name = line[41:71].strip()
                fst = int(line[72:76].strip())
                lst = int(line[77:81].strip())
            except ValueError:
                continue
            stations.append({'id': stn_id, 'name': name, 'lat': lat, 'lon': lon, 'elev_m': elev, 'first_year': fst, 'last_year': lst})
    return stations


def filter_by_year(stations, year):
    return [s for s in stations if s['first_year'] <= year <= s['last_year']]


def print_station_list(title, rows):
    print(title)
    for i, s in enumerate(rows, 1):
        print(
            f"  [{i}] id={s['id']}, 站点名称={s['name']}, lat={s['lat']:.4f}, lon={s['lon']:.4f}, "
            f"数据可用范围={s['first_year']}-{s['last_year']}, 与中心点距离={s.get('dist_km',0):.1f}km"
        )


def choose_multi_from_list(rows):
    return rows[:]


def choose_one_from_list(rows):
    if not rows:
        raise ValueError("No candidate stations available")
    return rows[0]


def download_igra_data(station_id: str, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_name = f'{station_id}-data.txt.zip'
    txt_name = f'{station_id}-data.txt'
    zip_path = out_dir / zip_name
    txt_path = out_dir / txt_name
    if txt_path.exists() and txt_path.stat().st_size > 0:
        print(f'[已存在跳过下载] {txt_path.name}')
        return txt_path, True, None
    url = f'https://www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/access/data-por/{zip_name}'
    print(f'开始下载: {station_id}', end=' ')

    last_err = None
    for i in range(1, 11):
        try:
            urllib.request.urlretrieve(url, zip_path)
            last_err = None
            break
        except Exception as e:
            last_err = str(e)
            print(f'[重试] {station_id} 第{i}次下载失败: {last_err}')
    if last_err is not None:
        print(f'[失败] {station_id} 连续10次下载失败')
        print(f'手动下载链接: {url}')
        print(f'手动保存路径: {txt_path}')
        return None, False, {'url': url, 'save_path': str(txt_path), 'error': last_err}

    with zipfile.ZipFile(zip_path, 'r') as zf:
        members = zf.namelist()
        target = txt_name if txt_name in members else members[0]
        zf.extract(target, path=out_dir)
        extracted = out_dir / target
    if extracted.name != txt_name:
        extracted.rename(txt_path)
    for member in members:
        p = out_dir / member
        if p.exists() and p.is_file() and p.name != txt_name:
            p.unlink()
    if zip_path.exists():
        zip_path.unlink()
    print('[完成下载]')
    return txt_path, False, None


def candidate_groups(stations, center_lat, center_lon, grid, year):
    """Use the published P1/P3/P6 UTM grid and annually eligible IGRA stations."""
    inside, outside, seen = [], [], set()
    for station in filter_by_year(stations, year):
        if station["id"] in seen:
            continue
        seen.add(station["id"])
        row = dict(station)
        row["dist_km"] = haversine_km(center_lat, center_lon,
                                       station["lat"], station["lon"])
        in_grid = lon_lat_in_utm_grid(station["lon"], station["lat"], grid)
        (inside if in_grid else outside).append(row)
    inside.sort(key=lambda item: (item["dist_km"], item["id"]))
    outside.sort(key=lambda item: (item["dist_km"], item["id"]))
    return inside, outside


def coverage_passes(valid_original_slots: int, expected_slots: int) -> bool:
    """Strict >80%; exact 80% is rejected."""
    return expected_slots > 0 and valid_original_slots * 5 > expected_slots * 4


def main():
    parser = argparse.ArgumentParser(description="P4 IGRA yearly >80% original 00/12 UTC sounding QA and station selection")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--pstop", type=float, default=500.0)
    parser.add_argument("--station-id", type=str, help="Explicit station (still subject to >80% gate)")
    parser.add_argument("--auto-select-all", action="store_true",
                        help="Legacy argument; in-domain qualifying stations are always all selected")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--case-root", type=Path, help="Explicit staged case, not project/current")
    parser.add_argument("--upperair-root", type=Path, help="Isolated P4 output root")
    parser.add_argument("--offline-archive-root", type=Path, help="Read-only extracted IGRA data-por archive; never network")
    args = parser.parse_args()
    if not 1900 <= args.year <= 2100 or not 0 < args.pstop <= 1500:
        parser.error("invalid year or pstop")

    if any((args.case_root, args.upperair_root, args.offline_archive_root)) and not all((args.case_root, args.upperair_root, args.offline_archive_root)):
        parser.error("isolated P4 requires --case-root, --upperair-root and --offline-archive-root together")
    from native_cpp.modules.p4_read62.data_prep.parse_igra_to_csv import observed_year_coverage

    case = args.case_root if args.case_root else current_project_path()
    center_lat, center_lon = parse_center(case / "grid" / "center_location")
    grid = load_strict_utm_grid(case / "grid" / "grid.cmn", context="P4")
    all_stations = load_station_list(engine_path("resources", "igra", "igra2-station-list.txt"))
    in_domain, out_domain = candidate_groups(all_stations, center_lat, center_lon,
                                              grid, args.year)
    if args.station_id:
        matches = [s for s in filter_by_year(all_stations, args.year) if s["id"] == args.station_id]
        if not matches:
            raise SystemExit(f"Requested station not available in {args.year}: {args.station_id}")
        station = matches[0]
        row = {**station, "dist_km": haversine_km(center_lat, center_lon,
                                                  station["lat"], station["lon"])}
        if lon_lat_in_utm_grid(station["lon"], station["lat"], grid):
            in_domain, out_domain = [row], []
        else:
            in_domain, out_domain = [], [row]

    year_dir = (args.upperair_root if args.upperair_root else DATA_ROOT) / str(args.year)
    year_dir.mkdir(parents=True, exist_ok=True)
    selected_file = year_dir / "upperair_station_used_list.txt"
    audit_file = year_dir / "p4_station_selection_audit.json"
    audit = {
        "year": args.year, "pstop_hpa": args.pstop,
        "coverage_rule": "strictly >80% valid original 00/12 UTC, before cloning",
        "chimney_assumption": "center_location is chimney in the configured case",
        "chimney_lat": center_lat, "chimney_lon": center_lon,
        "selection_geometry": "STRICT_WGS84_UTM_GRID_CMN_SW_CORNER_CLOSED_EDGES",
        "utm_zone": grid.iutmzn, "utm_hemisphere": grid.lsohem,
        "utm_origin_km": [grid.xrefkm, grid.yrefkm],
        "utm_grid_shape": [grid.nx, grid.ny],
        "utm_grid_spacing_km": grid.dgridkm,
        "in_domain_candidates": len(in_domain),
        "outside_candidates": len(out_domain),
        "checked": [], "selected": [],
    }
    selected = []

    def assess(station, category):
        if args.offline_archive_root:
            from native_cpp.modules.p4_read62.data_prep.p4_case_d1 import offline_igra
            raw, reused, error = offline_igra(args.offline_archive_root, station["id"], args.year)
        else:
            raw, reused, error = download_igra_data(station["id"], year_dir)
        record = {
            "station_id": station["id"], "category": category,
            "distance_km": station["dist_km"],
            "source_lat": station["lat"], "source_lon": station["lon"],
            "raw_file_reused": reused,
        }
        if raw is None:
            record["status"], record["reason"] = "DOWNLOAD_FAILED", str(error)
            audit["checked"].append(record)
            return None
        try:
            if args.offline_archive_root:
                from native_cpp.modules.p4_read62.data_prep.p4_case_d1 import sha256_file
                record["raw_sha256"] = sha256_file(raw)
            qc = observed_year_coverage(raw, station["id"], args.year,
                                        station["elev_m"], args.pstop)
            record.update(qc)
            if args.offline_archive_root and sha256_file(raw) != record["raw_sha256"]:
                raise ValueError("NOAA raw archive changed during original coverage QA")
            if not coverage_passes(qc["valid_original_slots"], qc["expected_slots"]):
                record["status"] = "REJECTED_COVERAGE_NOT_GT80"
                audit["checked"].append(record)
                return None
        except Exception as exc:
            record["status"] = "REJECTED_PARSE_OR_QA"
            record["reason"] = f"{type(exc).__name__}: {exc}"
            audit["checked"].append(record)
            return None
        record["status"] = "ACCEPTED"
        audit["checked"].append(record)
        return station, raw, record

    # Case 1: retain ALL qualifying in-domain stations with original positions.
    for station in in_domain:
        check = assess(station, "IN_DOMAIN")
        if check is not None:
            selected.append((*check, "OBSERVED"))

    # Case 2: none qualified inside; select exactly ONE eligible outside proxy.
    if not selected:
        for station in out_domain:
            check = assess(station, "OUTSIDE")
            if check is not None:
                selected = [(*check, "VIRTUAL_RELOCATED")]
                break

    with selected_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "lat", "lon", "elev_m", "year", "raw_txt",
                         "source_lat", "source_lon", "site_type",
                         "valid_original_slots", "expected_slots", "raw_coverage", "distance_km"])
        for station, raw, info, kind in selected:
            proxy = kind == "VIRTUAL_RELOCATED"
            effective_lat = center_lat if proxy else station["lat"]
            effective_lon = center_lon if proxy else station["lon"]
            writer.writerow([station["id"], station["name"], effective_lat, effective_lon,
                             station["elev_m"], args.year, str(raw),
                             station["lat"], station["lon"], kind,
                             info["valid_original_slots"], info["expected_slots"],
                             f'{info["coverage"]:.8f}', f'{station["dist_km"]:.6f}'])
            audit["selected"].append({
                "id": station["id"], "site_type": kind,
                "source_lat": station["lat"], "source_lon": station["lon"],
                "effective_lat": effective_lat, "effective_lon": effective_lon,
                "source_elev_m": station["elev_m"],
                "valid_original_slots": info["valid_original_slots"],
                "coverage": info["coverage"],
                **({"raw_sha256": info["raw_sha256"],
                    "original_utc_slots": info["original_utc_slots"]}
                   if args.offline_archive_root else {}),
            })
    audit_file.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    print("P4_YEARLY_SELECTION " + json.dumps(
        {"year": args.year, "selected": audit["selected"], "checked": len(audit["checked"])},
        ensure_ascii=False))
    if not selected:
        print(f"P4_NO_STATION_GT80 year={args.year}; see {audit_file}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

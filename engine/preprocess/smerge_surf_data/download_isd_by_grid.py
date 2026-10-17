#!/usr/bin/env python3
"""
Download ISD global-hourly station CSVs by study-area bounds.

Workflow:
1) Read center point from center_location (longitude/latitude).
2) Read grid size from grid.cmn (DGRIDKM, NX, NY).
3) Build lat/lon bounding box from center and grid span.
4) Filter stations in isd_station_list.txt that:
   - are inside bbox
   - have data in target year based on BEGIN/END.
5) Download station files from:
   https://www.ncei.noaa.gov/data/global-hourly/access/{year}/{station_id}.csv
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

CASE_ROOT = current_project_path()

DEFAULT_CENTER = CASE_ROOT / "grid" / "center_location"
DEFAULT_GRID = CASE_ROOT / "grid" / "grid.cmn"
DEFAULT_HISTORY = engine_path("resources", "isd", "isd-history.txt")
DEFAULT_RESEARCH_TIME = CASE_ROOT / "grid" / "research_time"
DEFAULT_OUT_DIR = CASE_ROOT / "met" / "surface" / "isd_raw"
BASE_URL = "https://www.ncei.noaa.gov/data/global-hourly/access"


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


def parse_grid(path: Path) -> tuple[float, int, int]:
    text = path.read_text(encoding="utf-8", errors="ignore")

    def find_num(key: str) -> str:
        m = re.search(rf"!\s*{re.escape(key)}\s*=\s*([^\s!]+)", text, flags=re.IGNORECASE)
        if not m:
            raise ValueError(f"Cannot find {key} in {path}")
        return m.group(1)

    dgrid_km = float(find_num("DGRIDKM"))
    nx = int(float(find_num("NX")))
    ny = int(float(find_num("NY")))
    return dgrid_km, nx, ny


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


def build_bbox(center_lon: float, center_lat: float, dgrid_km: float, nx: int, ny: int) -> tuple[float, float, float, float]:
    # Treat center_location as center of study area.
    half_w_km = dgrid_km * nx / 2.0
    half_h_km = dgrid_km * ny / 2.0

    dlat = half_h_km / 111.32
    cos_lat = math.cos(math.radians(center_lat))
    if abs(cos_lat) < 1e-8:
        dlon = 180.0
    else:
        dlon = half_w_km / (111.32 * cos_lat)

    min_lon = center_lon - dlon
    max_lon = center_lon + dlon
    min_lat = center_lat - dlat
    max_lat = center_lat + dlat
    return min_lon, max_lon, min_lat, max_lat


def in_year_range(begin: str, end: str, year: int) -> bool:
    if not (re.fullmatch(r"\d{8}", begin or "") and re.fullmatch(r"\d{8}", end or "")):
        return False
    y_start = int(begin[:4])
    y_end = int(end[:4])
    return y_start <= year <= y_end


def inside_bbox(st: Station, min_lon: float, max_lon: float, min_lat: float, max_lat: float) -> bool:
    return min_lon <= st.lon <= max_lon and min_lat <= st.lat <= max_lat


def station_url(year: int, sid: str) -> str:
    return f"{BASE_URL}/{year}/{sid}.csv"


def expected_hours_in_year(year: int) -> int:
    leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    return 8784 if leap else 8760


def validate_time_completeness(csv_path: Path, year: int) -> tuple[bool, str]:
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return False, "文件不存在或为空"

    times: set[datetime] = set()
    try:
        with csv_path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or "DATE" not in reader.fieldnames:
                return False, "缺少 DATE 列"
            for row in reader:
                ds = (row.get("DATE") or "").strip()
                if not ds:
                    continue
                try:
                    dt = datetime.fromisoformat(ds.replace("Z", ""))
                except Exception:
                    continue
                if dt.year == year:
                    times.add(dt.replace(minute=0, second=0, microsecond=0))
    except Exception as e:
        return False, f"读取失败: {e}"

    if not times:
        return False, "目标年份无有效时间记录"

    expected = expected_hours_in_year(year)
    unique_n = len(times)
    tmin = min(times)
    tmax = max(times)
    ordered = sorted(times)
    year_start = datetime(year, 1, 1, 0, 0, 0)
    # 用户规则：只要首尾覆盖全年即可判为可用
    covers_year = (tmin == year_start and tmax.month == 12 and tmax.day == 31)
    msg = (
        f"首时次={tmin}, 末时次={tmax},"
        f"{'覆盖全年' if covers_year else '未覆盖全年'},"
        f"实有{unique_n}/{expected}小时, 数据{'可用' if covers_year else '可能不可用'}。"
    )
    return covers_year, msg


def download_one(year: int, sid: str, out_dir: Path, timeout: int) -> tuple[bool, str, bool]:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{sid}-{year}.csv"
    url = station_url(year, sid)
    if out_file.exists() and out_file.stat().st_size > 0:
        return True, f"已存在, 跳过：{out_file}", True
    try:
        with request.urlopen(url, timeout=timeout) as resp:
            data = resp.read()
        out_file.write_bytes(data)
        return True, str(out_file), False
    except error.HTTPError as e:
        return False, f"HTTP {e.code}", False
    except Exception as e:
        return False, str(e), False


def main() -> int:
    ap = argparse.ArgumentParser(description="Download ISD station data by grid study area.")
    ap.add_argument("--year", type=int, required=False, help="Target year, e.g. 2023 (override research_time)")
    ap.add_argument("--center-file", type=Path, default=DEFAULT_CENTER)
    ap.add_argument("--grid-file", type=Path, default=DEFAULT_GRID)
    ap.add_argument("--research-time-file", type=Path, default=DEFAULT_RESEARCH_TIME)
    ap.add_argument("--history-file", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="输出目录；默认 project/current/met/surface/isd_raw")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--retries", type=int, default=10, help="单站下载失败后的重试次数")
    ap.add_argument("--max-stations", type=int, default=0, help="0 means no limit.")
    args = ap.parse_args()

    if args.year is not None and (args.year < 1901 or args.year > 2025):
        raise SystemExit("年份必须在 [1901, 2025] 范围内")
    if args.year is not None:
        years = [args.year]
        begin_dt = datetime(args.year, 1, 1, 0, 0, 0)
        end_dt = datetime(args.year, 12, 31, 23, 0, 0)
    else:
        begin_dt, end_dt = parse_research_time(args.research_time_file)
        years = list(range(begin_dt.year, end_dt.year + 1))

    center_lon, center_lat = parse_center(args.center_file)
    dgrid_km, nx, ny = parse_grid(args.grid_file)
    min_lon, max_lon, min_lat, max_lat = build_bbox(center_lon, center_lat, dgrid_km, nx, ny)

    stations = parse_history_txt(args.history_file)
    print(f"中心点识别: 经度: {center_lon} E, 纬度: {center_lat} N")
    print(f"网格分辨率(km): {dgrid_km:g}; X方向网格数量: {nx}, Y方向网格数量: {ny}")
    print(f"研究空间范围: 经度范围: [{min_lon:.4f}, {max_lon:.4f}] 纬度范围: [{min_lat:.4f}, {max_lat:.4f}]")
    print(f"研究时间范围: 起始时间: {begin_dt}, 结束时间: {end_dt}, 目标年份: {years}")

    target_dir = args.out_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    total_ok = 0
    total_fail = 0
    for year in years:
        in_scope = [
            s for s in stations
            if inside_bbox(s, min_lon, max_lon, min_lat, max_lat) and in_year_range(s.begin, s.end, year)
        ]
        # SMERGE/SURF.DAT/CALMET 的站点编号是整数(平台站号取 isd-history 的 6 位 USAF),
        # 因此 USAF 含字母的站点无法进入后续流程,在此显式排除并记录,避免整套预处理后失败。
        selected, excluded = [], []
        for s in in_scope:
            usaf, wban = s.sid[:6], s.sid[6:]
            if re.fullmatch(r"[0-9]{6}", usaf):
                selected.append(s)
            else:
                excluded.append(s)
        if excluded:
            print(f"\n==== 跳过 {len(excluded)} 个站点(USAF 非 6 位数字,SMERGE/CALMET 需要整数站号) ====")
            for s in excluded[:20]:
                print(f"  {s.sid}  {s.name}  USAF={s.sid[:6]!r}")
            with (target_dir / f"excluded_stations_{year}.txt").open("w", encoding="utf-8") as ef:
                ef.write("sid,usaf,wban,name,lat,lon,elev,reason\n")
                for s in excluded:
                    ef.write(f"{s.sid},{s.sid[:6]},{s.sid[6:]},{s.name},{s.lat},{s.lon},{s.elev},"
                             "USAF_NOT_NUMERIC\n")
        selected = sorted(selected, key=lambda s: s.sid)
        if args.max_stations > 0:
            selected = selected[: args.max_stations]

        print(f"\n==== 下载年份 {year}, 站点数={len(selected)} ====")
        if selected:
            for st in selected[:20]:
                print(f"  {st.sid}  {st.name}  ({st.lat:.4f},{st.lon:.4f})  BEGIN={st.begin} END={st.end}")

        report = target_dir / f"download_report_{year}.txt"
        station_list_file = target_dir / f"surf_station_list_{year}.txt"
        with station_list_file.open("w", encoding="utf-8") as sf:
            sf.write("sid,name,lat,lon,elev,country,begin,end\n")
            for st in selected:
                sf.write(
                    f"{st.sid},{st.name},{st.lat},{st.lon},{st.elev},{st.country},{st.begin},{st.end}\n"
                )

        ok = 0
        fail = 0
        manual_links: list[tuple[str, str]] = []
        with report.open("w", encoding="utf-8") as rep:
            rep.write("sid,status,detail,name,country,begin,end,lat,lon,elev\n")
            for st in selected:
                success = False
                detail = ""
                skipped_existing = False
                for i in range(1, args.retries + 1):
                    success, detail, skipped_existing = download_one(year, st.sid, target_dir, args.timeout)
                    if success:
                        out_file = target_dir / f"{st.sid}-{year}.csv"
                        display_name = out_file.name
                        if skipped_existing:
                            print(f"[已存在跳过下载] {display_name}")
                        elif i == 1:
                            pass
                        else:
                            pass
                        break
                    print(f"[重试] {st.sid} 第{i}次下载失败, 继续尝试:")

                if success:
                    ok += 1
                    status = "ok"
                    out_file = target_dir / f"{st.sid}-{year}.csv"
                    full, vmsg = validate_time_completeness(out_file, year)
                    print(f"[成功下载] {out_file.name} [对时间长度检测] {vmsg}")
                    if not full:
                        status = "incomplete"
                else:
                    fail += 1
                    status = "fail"
                    url = station_url(year, st.sid)
                    manual_links.append((st.sid, url))
                    detail = f"{detail} | manual_url={url}"
                rep.write(
                    f"{st.sid},{status},{detail},{st.name},{st.country},{st.begin},{st.end},{st.lat},{st.lon},{st.elev}\n"
                )
                if not success:
                    print(f"[失败] {st.sid} 最终失败，建议手动下载：{url}")

        total_ok += ok
        total_fail += fail
        print(f"年份 {year} 下载完成：成功={ok}，失败={fail}")
        print(f"数据保存路径: {target_dir}")
        print(f"站点清单：{station_list_file}")
        print(f"报告文件：{report}")
        if manual_links:
            print("以下站点请手动下载：")
            for sid, url in manual_links:
                print(f"  {sid}: {url}")

    print(f"\n地面气象数据全部下载完成。成功={total_ok}，失败={total_fail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

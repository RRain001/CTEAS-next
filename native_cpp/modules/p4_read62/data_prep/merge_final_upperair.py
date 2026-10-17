#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime, timedelta
from pathlib import Path

from engine.core.paths import current_project_path

CASE_ROOT = current_project_path()
UPPERAIR_ROOT = CASE_ROOT / "met" / "upperair"
RESEARCH_TIME_FILE = CASE_ROOT / "grid" / "research_time"
HEADER_LINES = 7
FINAL_STATIONS_CSV = UPPERAIR_ROOT / "final" / "stations.csv"
MAX_CALMET_LEVELS = 99


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


def update_header_line(line: str, begin_dt: datetime, end_dt: datetime) -> str:
    parts = line.split()
    if len(parts) < 11:
        raise ValueError(f"Unexpected UP.DAT header line: {line!r}")

    pstop = parts[8]
    tail_1 = parts[9]
    tail_2 = parts[10]
    begin_jday = begin_dt.timetuple().tm_yday
    end_jday = end_dt.timetuple().tm_yday

    return (
        f"{begin_dt.year:6d}"
        f"{begin_jday:5d}"
        f"{begin_dt.hour:5d}"
        f"{begin_dt.second:5d}"
        f"{end_dt.year:5d}"
        f"{end_jday:5d}"
        f"{end_dt.hour:5d}"
        f"{end_dt.second:5d}"
        f"{pstop:>5}"
        f"{tail_1:>5}"
        f"{tail_2:>5}"
    )


def format_sounding_header(tokens: list[str], mlev: int, istop: int) -> str:
    if len(tokens) < 14:
        raise ValueError(f"Unexpected sounding header tokens: {tokens!r}")
    return (
        f"   {tokens[0]:<4}"
        f"  {tokens[1]:>8}"
        f"    {int(tokens[2]):4d}{int(tokens[3]):4d}{int(tokens[4]):3d}{int(tokens[5]):3d}{int(tokens[6]):5d}"
        f"    {int(tokens[7]):4d}{int(tokens[8]):4d}{int(tokens[9]):3d}{int(tokens[10]):3d}{int(tokens[11]):5d}"
        f"{mlev:5d}   {istop:5d}"
    )


def clone_sounding_header_to_next_12h(header_line: str) -> str:
    tokens = header_line.split()
    if len(tokens) < 14 or tokens[0] != "6201":
        raise ValueError(f"Unexpected sounding header: {header_line!r}")

    y1, mo1, d1, h1, s1 = map(int, tokens[2:7])
    y2, mo2, d2, h2, s2 = map(int, tokens[7:12])
    dt_begin = datetime(y1, mo1, d1, h1, 0, s1) + timedelta(hours=12)
    dt_end = datetime(y2, mo2, d2, h2, 0, s2) + timedelta(hours=12)

    tokens[2] = f"{dt_begin.year}"
    tokens[3] = f"{dt_begin.month}"
    tokens[4] = f"{dt_begin.day}"
    tokens[5] = f"{dt_begin.hour}"
    tokens[6] = f"{dt_begin.second}"
    tokens[7] = f"{dt_end.year}"
    tokens[8] = f"{dt_end.month}"
    tokens[9] = f"{dt_end.day}"
    tokens[10] = f"{dt_end.hour}"
    tokens[11] = f"{dt_end.second}"
    return format_sounding_header(tokens, int(tokens[12]), int(tokens[13]))


def parse_level_groups(line: str) -> list[tuple[float, float, float, int, int]]:
    num = r"[+-]?\d+(?:\.\d*)?"
    groups = re.findall(rf"({num})\s*/\s*({num})\s*/\s*({num})\s*/\s*([+-]?\d+)\s*/\s*([+-]?\d+)", line)
    out: list[tuple[float, float, float, int, int]] = []
    for pres, height, temp, wd, ws in groups:
        out.append((float(pres), float(height), float(temp), int(wd), int(ws)))
    return out


def format_level_group(group: tuple[float, float, float, int, int]) -> str:
    pres, height, temp, wd, ws = group
    return f"   {pres:6.1f}/{height:5.0f}/{temp:5.1f}/{wd:3d}/{ws:3d}"


def normalize_updat_records(lines: list[str], station_id: str, source_path: Path) -> tuple[list[str], int]:
    out_lines = lines[:HEADER_LINES]
    idx = HEADER_LINES
    clipped_soundings = 0

    while idx < len(lines):
        header_line = lines[idx]
        idx += 1
        if not header_line.strip():
            continue

        tokens = header_line.split()
        if len(tokens) < 14 or tokens[0] != "6201":
            raise ValueError(f"Unexpected sounding header in {source_path}: {header_line!r}")

        expected_levels = int(tokens[-1])
        levels: list[tuple[float, float, float, int, int]] = []
        while idx < len(lines) and len(levels) < expected_levels:
            data_line = lines[idx]
            idx += 1
            if data_line.strip().startswith("->->->"):
                continue
            groups = parse_level_groups(data_line)
            if not groups:
                raise ValueError(
                    f"Could not parse sounding levels for station {station_id} "
                    f"in {source_path} near header {header_line!r}"
                )
            levels.extend(groups)

        if len(levels) < expected_levels:
            raise ValueError(
                f"Truncated sounding for station {station_id} in {source_path}: "
                f"expected {expected_levels} levels, parsed {len(levels)}"
            )

        levels = levels[:expected_levels]
        trimmed_levels = levels[:MAX_CALMET_LEVELS]
        if len(trimmed_levels) < len(levels):
            clipped_soundings += 1

        new_count = len(trimmed_levels)
        out_lines.append(format_sounding_header(tokens, new_count, new_count))
        for start in range(0, new_count, 4):
            chunk = trimmed_levels[start:start + 4]
            out_lines.append("".join(format_level_group(group) for group in chunk))

    return out_lines, clipped_soundings


def append_one_boundary_sounding(lines: list[str]) -> list[str]:
    if len(lines) <= HEADER_LINES:
        return lines

    i = len(lines) - 1
    while i >= HEADER_LINES and not lines[i].strip():
        i -= 1
    if i < HEADER_LINES:
        return lines

    last_data_rev: list[str] = []
    while i >= HEADER_LINES:
        line = lines[i]
        if line.split()[:1] == ["6201"]:
            break
        if line.strip().startswith("->->->"):
            i -= 1
            continue
        last_data_rev.append(line)
        i -= 1

    if i < HEADER_LINES:
        raise ValueError("Cannot locate last sounding header to append boundary record")

    last_header = lines[i]
    last_data = list(reversed(last_data_rev))
    new_header = clone_sounding_header_to_next_12h(last_header)
    return lines + [new_header] + last_data


def collect_station_files(years: list[int]) -> dict[str, list[Path]]:
    station_files: dict[str, list[Path]] = {}
    pat = re.compile(r"^up_(\d{5})_(\d{4})\.dat$")

    for year in years:
        year_dir = UPPERAIR_ROOT / str(year) / "fsl_data"
        if not year_dir.exists():
            continue
        for path in sorted(year_dir.glob("up_*.dat")):
            m = pat.match(path.name)
            if not m:
                continue
            station_id = m.group(1)
            station_files.setdefault(station_id, []).append(path)
    return station_files


def collect_station_metadata(years: list[int]) -> dict[str, dict[str, str]]:
    station_meta: dict[str, dict[str, str]] = {}
    for year in years:
        list_path = UPPERAIR_ROOT / str(year) / "upperair_station_used_list.txt"
        if not list_path.exists():
            continue
        with list_path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                station_key = row["id"].strip()
                station_id = station_key[-5:]
                station_meta.setdefault(
                    station_id,
                    {
                        "station_name": row["name"].strip(),
                        "lat": row["lat"].strip(),
                        "lon": row["lon"].strip(),
                        "elev_m": row["elev_m"].strip(),
                    },
                )
    return station_meta


def write_station_metadata_csv(final_dir: Path, station_meta: dict[str, dict[str, str]]) -> None:
    final_dir.mkdir(parents=True, exist_ok=True)
    with FINAL_STATIONS_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["station_id", "station_name", "lat", "lon", "elev_m", "tz_hour", "source_file"],
        )
        writer.writeheader()
        for station_id, meta in sorted(station_meta.items()):
            writer.writerow(
                {
                    "station_id": station_id,
                    "station_name": meta["station_name"],
                    "lat": meta["lat"],
                    "lon": meta["lon"],
                    "elev_m": meta["elev_m"],
                    "tz_hour": "0",
                    "source_file": f"met/upperair/final/up_{station_id}.dat",
                }
            )


def merge_station_files(station_id: str, paths: list[Path], begin_dt: datetime, end_dt: datetime, output_dir: Path) -> Path:
    if not paths:
        raise ValueError(f"No input files for station {station_id}")

    merged_lines: list[str] = []
    clipped_soundings = 0
    for idx, path in enumerate(sorted(paths)):
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if len(lines) < HEADER_LINES:
            raise ValueError(f"UP.DAT too short: {path}")
        normalized_lines, clipped = normalize_updat_records(lines, station_id, path)
        clipped_soundings += clipped
        if idx == 0:
            normalized_lines[5] = update_header_line(normalized_lines[5], begin_dt, end_dt)
            merged_lines.extend(normalized_lines)
        else:
            merged_lines.extend(normalized_lines[HEADER_LINES:])

    merged_lines = append_one_boundary_sounding(merged_lines)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"up_{station_id}.dat"
    out_path.write_text("\n".join(merged_lines) + "\n", encoding="utf-8")
    _ = clipped_soundings
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge yearly READ62 UP.DAT files into final CALMET-ready files")
    args = ap.parse_args()
    _ = args

    begin_dt, end_dt = parse_research_time(RESEARCH_TIME_FILE)
    years = list(range(begin_dt.year, end_dt.year + 1))
    final_dir = UPPERAIR_ROOT / "final"
    station_files = collect_station_files(years)
    station_meta = collect_station_metadata(years)
    if not station_files:
        print(f"未找到年度 UP.DAT 文件: {UPPERAIR_ROOT}")
        return 1

    merged_count = 0
    for station_id, paths in sorted(station_files.items()):
        out_path = merge_station_files(station_id, paths, begin_dt, end_dt, final_dir)
        merged_count += 1
        print(f"[{station_id}] 合并 {len(paths)} 年数据 -> {out_path}")

    missing_meta = sorted(set(station_files) - set(station_meta))
    if missing_meta:
        raise RuntimeError(f"Missing upperair station metadata for: {', '.join(missing_meta)}")
    write_station_metadata_csv(final_dir, station_meta)

    _ = merged_count
    print(f"输出路径: {final_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

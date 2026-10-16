#!/usr/bin/env python3
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from engine.core.paths import current_project_path

CASE_ROOT = current_project_path()

INPUT_DIR = CASE_ROOT / "met" / "surface" / "isd2smerge_and_fill"
OUTPUT_DIR = CASE_ROOT / "met" / "surface" / "isd2smerge_cleaned"
RESEARCH_TIME_FILE = CASE_ROOT / "grid" / "research_time"

FILLED_PATTERN = re.compile(r"^([0-9A-Za-z]{6})-([0-9A-Za-z]{5})-(\d{4})_filled\.csv$")


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


def read_station_csv(path: Path) -> tuple[list[str], list[str], pd.DataFrame]:
    with path.open("r", encoding="utf-8") as f:
        header_lines = [f.readline().rstrip("\n") for _ in range(3)]
    columns = [x.strip() for x in header_lines[2].split(",")]
    df = pd.read_csv(path, skiprows=3, header=None, names=columns)
    return header_lines, columns, df


def add_datetime(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    hour_val = (pd.to_numeric(out["Hour"], errors="coerce").fillna(0).astype(int) // 100).astype(int)
    out["Datetime"] = pd.to_datetime(
        {
            "year": pd.to_numeric(out["Year"], errors="coerce").fillna(0).astype(int),
            "month": pd.to_numeric(out["Month"], errors="coerce").fillna(1).astype(int),
            "day": pd.to_numeric(out["Day"], errors="coerce").fillna(1).astype(int),
            "hour": hour_val,
        },
        errors="coerce",
    )
    out = out.dropna(subset=["Datetime"]).copy()
    return out


def save_csv(path: Path, header_lines: list[str], columns: list[str], df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        for line in header_lines:
            f.write(line + "\n")
        df.to_csv(f, index=False, header=False, columns=columns)


def main() -> int:
    begin_dt, end_dt = parse_research_time(RESEARCH_TIME_FILE)

    if not INPUT_DIR.exists():
        print(f"输入目录不存在: {INPUT_DIR}")
        return 1

    station_files: dict[str, list[Path]] = {}
    for p in sorted(INPUT_DIR.iterdir()):
        if not p.is_file():
            continue
        m = FILLED_PATTERN.match(p.name)
        if not m:
            continue
        station_key = f"{m.group(1)}-{m.group(2)}"
        station_files.setdefault(station_key, []).append(p)

    if not station_files:
        print(f"未找到匹配的已插值文件: {INPUT_DIR}")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for station_key, files in sorted(station_files.items()):
        merged_parts = []
        header_lines = None
        columns = None

        for fp in sorted(files):
            h, c, df = read_station_csv(fp)
            if header_lines is None:
                header_lines = h
                columns = c
            df = add_datetime(df)
            merged_parts.append(df)

        if not merged_parts:
            continue

        merged = pd.concat(merged_parts, ignore_index=True)
        merged = merged.sort_values("Datetime")
        merged = merged.drop_duplicates(subset=["Datetime"], keep="last")

        clipped = merged[(merged["Datetime"] >= begin_dt) & (merged["Datetime"] <= end_dt)].copy()
        if clipped.empty:
            print(f"[{station_key}] 裁剪到研究时段后为空, 跳过")
            continue

        clipped["Year"] = clipped["Datetime"].dt.year.astype(int)
        clipped["Month"] = clipped["Datetime"].dt.month.astype(int)
        clipped["Day"] = clipped["Datetime"].dt.day.astype(int)
        clipped["Hour"] = (clipped["Datetime"].dt.hour.astype(int) * 100).astype(int)

        out_path = OUTPUT_DIR / f"{station_key}.csv"
        save_csv(out_path, header_lines or [], columns or [], clipped)

    print(f"任务完成, 数据保存路径: {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

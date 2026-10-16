#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from engine.core.paths import TUTORIAL_ROOT, current_project_path, engine_path

SCRIPT_DIR = engine_path("preprocess", "read62_upperair_data")
CASE_ROOT = current_project_path()
CASE_YAML = CASE_ROOT / "case.yaml"
RESEARCH_TIME_FILE = CASE_ROOT / "grid" / "research_time"
UPPERAIR_ROOT = CASE_ROOT / "met" / "upperair"


def load_case_config() -> dict[str, Any]:
    if not CASE_YAML.exists():
        raise FileNotFoundError(f"case.yaml not found: {CASE_YAML}")
    return yaml.safe_load(CASE_YAML.read_text(encoding="utf-8")) or {}


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


def run_step(title: str, cmd: list[str]) -> None:
    print(f"\n=== [{title}] 开始 ===")
    subprocess.run(cmd, cwd=str(TUTORIAL_ROOT), check=True)
    print(f"=== [{title}] 完成 ===")


def module_cmd(python_bin: str, relative_script: str, *args: str) -> list[str]:
    module_name = ".".join(("engine", "preprocess", *Path(relative_script).with_suffix("").parts))
    return [python_bin, "-m", module_name, *args]


def read_selected_station_id(year: int) -> str | None:
    selected_file = UPPERAIR_ROOT / str(year) / "upperair_station_used_list.txt"
    if not selected_file.exists():
        return None
    with selected_file.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = (row.get("id") or "").strip()
            if sid:
                return sid
    return None


def upperair_cfg(config: dict[str, Any]) -> dict[str, Any]:
    return (config.get("preprocess") or {}).get("upperair") or {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Run upperair pipeline sequentially by research_time years")
    ap.add_argument("--python", default=sys.executable, help="Python interpreter")
    ap.add_argument("--pstop", type=float, default=None, help="PSTOP for parse/read62")
    ap.add_argument("--skip-download", action="store_true", help="Skip IGRA download step")
    args = ap.parse_args()

    config = load_case_config()
    upper = upperair_cfg(config)

    begin_dt, end_dt = parse_research_time(RESEARCH_TIME_FILE)
    years = list(range(begin_dt.year, end_dt.year + 1))
    py = args.python

    if args.pstop is not None:
        pstop = float(args.pstop)
    elif upper.get("pstop_hpa") is not None:
        pstop = float(upper["pstop_hpa"])
    else:
        pstop = float((config.get("settings") or {}).get("pstop_hpa_default", 500.0))

    skip_download = bool(args.skip_download or bool(upper.get("skip_download", False)))
    configured_station_id = str(upper.get("station_id", "") or "").strip() or None
    auto_select_all = bool(upper.get("auto_select_all", True))

    print(f"研究时间范围: {begin_dt} -> {end_dt}")
    print(f"目标年份: {years}")
    print(f"PSTOP(hPa): {pstop}")

    selected_station_id: str | None = configured_station_id

    for year in years:
        print(f"\n######## Year {year} ########")

        if not skip_download:
            if selected_station_id:
                run_step(
                    f"{year} 下载IGRA",
                    module_cmd(py, "read62_upperair_data/download_igra.py", "--year", str(year), "--station-id", selected_station_id, "--yes"),
                )
            elif auto_select_all:
                run_step(
                    f"{year} 下载IGRA",
                    module_cmd(py, "read62_upperair_data/download_igra.py", "--year", str(year), "--auto-select-all", "--yes"),
                )
                selected_station_id = read_selected_station_id(year)
                if selected_station_id:
                    print(f"后续年份将复用站点: {selected_station_id}")
            else:
                print("警告: auto_select_all=false 且未配置 station_id，自动回退为 auto_select_all=true")
                run_step(
                    f"{year} 下载IGRA",
                    module_cmd(py, "read62_upperair_data/download_igra.py", "--year", str(year), "--auto-select-all", "--yes"),
                )
                selected_station_id = read_selected_station_id(year)
                if selected_station_id:
                    print(f"后续年份将复用站点: {selected_station_id}")

        run_step(
            f"{year} 解析IGRA到CSV",
            module_cmd(py, "read62_upperair_data/parse_igra_to_csv.py", "--year", str(year), "--pstop", str(pstop), "--yes"),
        )

        run_step(
            f"{year} 转换CSV到FSL",
            module_cmd(py, "read62_upperair_data/read.py", "--year", str(year)),
        )

        run_step(
            f"{year} 执行READ62",
            module_cmd(py, "read62_upperair_data/run_read62.py", "--year", str(year), "--pstop", str(pstop)),
        )

    run_step("合并最终UP.DAT", module_cmd(py, "read62_upperair_data/merge_final_upperair.py"))

    print("\n高空气象数据处理完毕!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

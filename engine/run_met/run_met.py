#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from engine.core.paths import BIN_ROOT, VENDOR_BIN_DIR, case_dir, resolve_executable
from engine.core.runtime_names import MET_DAT, MET_INP, MET_LST, MET_RUNTIME_LOG
from engine.core.runner import run_binary

from .common import case_paths, load_case_config_with_name, parse_research_time
from .prepare_met import render_met_inp


RUNTIME_LOG = MET_RUNTIME_LOG


def parse_inp_assignment(inp_text: str, key: str) -> str | None:
    m = re.search(rf"!\s*{re.escape(key)}\s*=\s*([^!]+?)\s*!", inp_text, flags=re.IGNORECASE)
    return m.group(1).strip() if m else None


def resolve_from_workdir(work_dir: Path, path_str: str | None, fallback: str) -> Path:
    path = Path(path_str or fallback)
    if path.is_absolute():
        return path
    return Path(os.path.abspath(work_dir / path))


def find_keywords(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    return [kw for kw in keywords if kw.lower() in lower]


def find_patterns(text: str, patterns: list[str]) -> list[str]:
    found: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            found.append(pattern)
    return found


def size_to_mbs(size_bytes: int) -> int:
    # Keep display style aligned with existing logs: integer "Mbs".
    if size_bytes <= 0:
        return 0
    return max(1, int(round(size_bytes / 1000000.0)))


def prepare_output_path(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        path.unlink()


def sync_deliverable(case_name: str, source: Path, relative_dir: str) -> None:
    if not source.exists():
        return
    dest = case_dir(case_name) / "deliverables" / relative_dir / source.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)


def main() -> int:
    ap = argparse.ArgumentParser(description="Render and run MET for the current case")
    ap.add_argument("--case", help="Case name under project/cases; defaults to project/current")
    ap.add_argument("--skip-prepare", action="store_true", help="Skip input rendering and use existing met.inp")
    args = ap.parse_args()

    case_name, config = load_case_config_with_name(args.case)
    work_dir = case_paths(config, case_name, required=["run_met_dir"])["run_met_dir"]
    work_dir.mkdir(parents=True, exist_ok=True)
    inp_path = work_dir / MET_INP

    if not args.skip_prepare:
        rendered, _summary = render_met_inp(case_name, config, work_dir)
        inp_path.write_text(rendered, encoding="utf-8")

    try:
        resolve_executable("met")
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        return 1
    if not inp_path.exists():
        print(f"[ERROR] met.inp not found: {inp_path}")
        return 1

    inp_text = inp_path.read_text(encoding="utf-8", errors="ignore")
    metlst = resolve_from_workdir(work_dir, parse_inp_assignment(inp_text, "METLST"), MET_LST)
    metdat = resolve_from_workdir(work_dir, parse_inp_assignment(inp_text, "METDAT"), MET_DAT)
    runtime_log = work_dir / RUNTIME_LOG
    prepare_output_path(metlst)
    prepare_output_path(metdat)
    if runtime_log.exists():
        runtime_log.unlink()

    begin_dt, end_dt = parse_research_time(case_name)
    start_time = datetime.now()
    print(f"[INFO] 计算时间: {begin_dt} -> {end_dt}")
    print(f"[INFO] 工作目录: {work_dir}")
    print(f"[INFO] 风场数据: {metdat}")
    print(f"[INFO] 运行记录: {metlst}")
    print(f"[INFO] 运行日志: {runtime_log}")
    print()
    print("[INFO] 可通过 met.lst 查询报错原因")
    print("[INFO] 可通过 met_runtime.log 查询实时进程")
    print("[INFO] 计算中, 请耐心等待...")

    with runtime_log.open("w", encoding="utf-8") as logf:
        proc = run_binary(
            "met",
            cwd=work_dir,
            stdout=logf,
            stderr=subprocess.STDOUT,
            text=True,
            bin_root=BIN_ROOT,
            legacy_bin_root=VENDOR_BIN_DIR,
        )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    _ = (end_time, duration, proc.returncode)

    runtime_text = runtime_log.read_text(encoding="utf-8", errors="ignore") if runtime_log.exists() else ""
    metlst_text = metlst.read_text(encoding="utf-8", errors="ignore") if metlst.exists() else ""
    combined = runtime_text + "\n" + metlst_text

    err_patterns = [
        r"^\s*ERROR IN SUBR\.",
        r"\bFATAL\b",
        r"\bABORT\b",
        r"segmentation fault",
        r"forrtl:\s*severe",
        r"cannot open",
    ]
    warn_keywords = ["warning"]
    found_err = find_patterns(combined, err_patterns)
    found_warn = find_keywords(combined, warn_keywords)

    metlst_exists = metlst.exists()
    metdat_exists = metdat.exists()
    metlst_size = metlst.stat().st_size if metlst_exists else 0
    metdat_size = metdat.stat().st_size if metdat_exists else 0

    if metlst_exists:
        sync_deliverable(case_name, metlst, "met")
    if metdat_exists:
        sync_deliverable(case_name, metdat, "met")

    print(f"[CHECK] 运行记录生成: {metlst_exists}, 大小: {size_to_mbs(metlst_size)} Mbs")
    print(f"[CHECK] 风场文件生成: {metdat_exists}, 大小: {size_to_mbs(metdat_size)} Mbs")
    #if found_warn:
    #    print(f"[CHECK] 警告关键词: {', '.join(found_warn)}")
    if found_err:
        print(f"[CHECK] 错误关键词: {', '.join(found_err)}")

    ok = proc.returncode == 0 and metlst_exists and metdat_exists and metdat_size > 0 and not found_err
    if ok:
        print("[RESULT] 诊断风场计算完毕")
        return 0

    print("[RESULT] 诊断风场计算失败或结果异常")
    print(f"[INFO] 请检查: {runtime_log}")
    print(f"[INFO] 请检查: {metlst}")
    return 2


if __name__ == "__main__":
    sys.exit(main())

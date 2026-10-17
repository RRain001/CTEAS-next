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
from engine.core.runtime_names import (
    MET_DAT,
    PUFF_CON,
    PUFF_DRY,
    PUFF_INP,
    PUFF_LST,
    PUFF_RUNTIME_LOG,
    PUFF_VIS,
    PUFF_WET,
)
from engine.core.runner import run_binary

from .common import case_paths, load_case_config_with_name, parse_research_time
from .prepare_puff import render_puff_inp


RUNTIME_LOG = PUFF_RUNTIME_LOG


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


def ensure_metdat(work_dir: Path, metdat: Path, met_dir: Path) -> None:
    if metdat.exists():
        return
    fallback = met_dir / MET_DAT
    if not fallback.exists():
        return
    metdat.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(fallback, metdat)


def pick_existing_output(primary: Path) -> Path:
    if primary.exists():
        return primary
    alt_upper = primary.with_name(primary.name.upper())
    if alt_upper.exists():
        return alt_upper
    alt_lower = primary.with_name(primary.name.lower())
    if alt_lower.exists():
        return alt_lower
    return primary


def size_to_mbs(size_bytes: int) -> int:
    # Keep display style aligned with existing logs: integer "Mbs".
    return int(round(size_bytes / 1000000.0))


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
    ap = argparse.ArgumentParser(description="Render and run PUFF for the current case")
    ap.add_argument("--case", help="Case name under project/cases; defaults to project/current")
    ap.add_argument("--skip-prepare", action="store_true", help="Skip input rendering and use existing puff.inp")
    args = ap.parse_args()

    case_name, config = load_case_config_with_name(args.case)
    paths = case_paths(config, case_name, required=["run_met_dir", "run_puff_dir"])
    work_dir = paths["run_puff_dir"]
    met_dir = paths["run_met_dir"]
    work_dir.mkdir(parents=True, exist_ok=True)
    inp_path = work_dir / PUFF_INP

    if not args.skip_prepare:
        rendered, _summary = render_puff_inp(case_name, config, work_dir)
        inp_path.write_text(rendered, encoding="utf-8")

    try:
        resolve_executable("puff")
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        return 1
    if not inp_path.exists():
        print(f"[ERROR] puff.inp not found: {inp_path}")
        return 1

    inp_text = inp_path.read_text(encoding="utf-8", errors="ignore")
    metdat = resolve_from_workdir(work_dir, parse_inp_assignment(inp_text, "METDAT"), MET_DAT)
    puflst = resolve_from_workdir(work_dir, parse_inp_assignment(inp_text, "PUFLST"), PUFF_LST)
    condat = resolve_from_workdir(work_dir, parse_inp_assignment(inp_text, "CONDAT"), PUFF_CON)
    drydat = resolve_from_workdir(work_dir, parse_inp_assignment(inp_text, "DFDAT"), PUFF_DRY)
    wetdat = resolve_from_workdir(work_dir, parse_inp_assignment(inp_text, "WFDAT"), PUFF_WET)
    visdat = resolve_from_workdir(work_dir, parse_inp_assignment(inp_text, "VISDAT"), PUFF_VIS)
    runtime_log = work_dir / RUNTIME_LOG

    ensure_metdat(work_dir, metdat, met_dir)
    if not metdat.exists():
        print(f"[ERROR] METDAT not found: {metdat}")
        print(f"[HINT] expected MET output at: {met_dir / MET_DAT}")
        return 1
    prepare_output_path(puflst)
    prepare_output_path(condat)

    if runtime_log.exists():
        runtime_log.unlink()

    begin_dt, end_dt = parse_research_time(case_name)
    start_time = datetime.now()
    print(f"[INFO] 计算时间: {begin_dt} -> {end_dt}")
    print(f"[INFO] 工作目录: {work_dir}")
    print(f"[INFO] 气象数据: {metdat}")
    print(f"[INFO] 运行记录: {puflst}")
    print(f"[INFO] 浓度文件: {condat}")
    print(f"[INFO] 运行日志: {runtime_log}")
    print()
    print("[INFO] 可通过 puff.lst 查询报错原因")
    print("[INFO] 可通过 puff_runtime.log 查询实时进程")
    print("[INFO] 计算中, 请耐心等待...")

    with runtime_log.open("w", encoding="utf-8") as logf:
        proc = run_binary(
            "puff",
            cwd=work_dir,
            stdout=logf,
            stderr=subprocess.STDOUT,
            text=True,
            bin_root=BIN_ROOT,
            legacy_bin_root=VENDOR_BIN_DIR,
        )

    puflst = pick_existing_output(puflst)
    condat = pick_existing_output(condat)
    drydat = pick_existing_output(drydat)
    wetdat = pick_existing_output(wetdat)
    visdat = pick_existing_output(visdat)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    _ = (end_time, duration, proc.returncode)

    runtime_text = runtime_log.read_text(encoding="utf-8", errors="ignore") if runtime_log.exists() else ""
    puflst_text = puflst.read_text(encoding="utf-8", errors="ignore") if puflst.exists() else ""
    combined = runtime_text + "\n" + puflst_text

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

    puflst_exists = puflst.exists()
    condat_exists = condat.exists()
    puflst_size = puflst.stat().st_size if puflst_exists else 0
    condat_size = condat.stat().st_size if condat_exists else 0

    if puflst_exists:
        sync_deliverable(case_name, puflst, "puff")
    if condat_exists:
        sync_deliverable(case_name, condat, "puff")
    for optional_output in (drydat, wetdat, visdat):
        if optional_output.exists():
            sync_deliverable(case_name, optional_output, "puff")

    print(f"[CHECK] 运行记录生成: {puflst_exists}, 大小: {size_to_mbs(puflst_size)} Mbs")
    print(f"[CHECK] 浓度文件生成: {condat_exists}, 大小: {size_to_mbs(condat_size)} Mbs")
    # if found_warn:
    #    print(f"[CHECK] 警告关键词: {', '.join(found_warn)}")
    if found_err:
        print(f"[CHECK] 错误关键词: {', '.join(found_err)}")

    ok = proc.returncode == 0 and puflst_exists and condat_exists and condat_size > 0 and not found_err
    if ok:
        print("[RESULT] 烟团模型计算完毕")
        return 0

    print("[RESULT] 烟团模型计算失败或结果异常")
    print(f"[INFO] 请检查: {runtime_log}")
    print(f"[INFO] 请检查: {puflst}")
    return 2


if __name__ == "__main__":
    sys.exit(main())

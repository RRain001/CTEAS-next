#!/usr/bin/env python3
"""Sync MAKEGEO input with current grid/files and optionally run MAKEGEO."""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass

from engine.core.paths import current_project_path, executable_path, resolve_executable

CASE_ROOT = current_project_path()

DEFAULT_LUDAT = str(CASE_ROOT / "geo" / "ctgproc" / "lu.dat")
DEFAULT_TERRDAT = str(CASE_ROOT / "geo" / "terrel" / "terrel.dat")

TARGET_KEYS = [
    "PMAP",
    "IUTMZN",
    "UTMHEM",
    "DATUM",
    "XREFKM",
    "YREFKM",
    "NX",
    "NY",
    "DGRIDKM",
]


@dataclass
class GridDef:
    imap: str
    iutmzn: int
    lsohem: str
    datum: str
    xrefkm: float
    yrefkm: float
    nx: int
    ny: int
    dgridkm: float


def parse_grid_cmn(path: pathlib.Path) -> GridDef:
    text = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    kv: dict[str, str] = {}
    pattern = re.compile(r"^\s*[!*]\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*[!*]\s*$")
    for line in text:
        m = pattern.match(line)
        if m:
            kv[m.group(1).strip().upper()] = m.group(2).strip()

    required = ["IMAP", "IUTMZN", "LSOHEM", "DATUM", "XREFKM", "YREFKM", "NX", "NY", "DGRIDKM"]
    missing = [k for k in required if k not in kv]
    if missing:
        raise ValueError(f"Missing keys in {path}: {', '.join(missing)}")

    return GridDef(
        imap=kv["IMAP"].upper(),
        iutmzn=int(float(kv["IUTMZN"])),
        lsohem=kv["LSOHEM"].upper(),
        datum=kv["DATUM"].upper(),
        xrefkm=float(kv["XREFKM"]),
        yrefkm=float(kv["YREFKM"]),
        nx=int(float(kv["NX"])),
        ny=int(float(kv["NY"])),
        dgridkm=float(kv["DGRIDKM"]),
    )


def grid_to_makegeo_values(grid: GridDef) -> dict[str, str]:
    def fmt_num(v: float) -> str:
        return str(int(v)) if float(v).is_integer() else f"{v}"

    return {
        "PMAP": grid.imap,
        "IUTMZN": str(grid.iutmzn),
        "UTMHEM": grid.lsohem,
        "DATUM": grid.datum,
        "XREFKM": fmt_num(grid.xrefkm),
        "YREFKM": fmt_num(grid.yrefkm),
        "NX": str(grid.nx),
        "NY": str(grid.ny),
        "DGRIDKM": fmt_num(grid.dgridkm),
    }


def sync_makegeo_projection_grid(lines: list[str], new_values: dict[str, str]) -> list[tuple[int, str, str, str]]:
    changed: list[tuple[int, str, str, str]] = []
    found: set[str] = set()
    patterns = {key: re.compile(rf"(!\s*{re.escape(key)}\s*=\s*)([^!]*?)(\s*!)") for key in TARGET_KEYS}

    for idx, line in enumerate(lines):
        for key in TARGET_KEYS:
            if key in found:
                continue
            m = patterns[key].search(line)
            if not m:
                continue
            old_value = m.group(2).strip()
            new_value = new_values[key]
            lines[idx] = line[: m.start()] + f"{m.group(1)}{new_value}{m.group(3)}" + line[m.end() :]
            changed.append((idx + 1, key, old_value, new_value))
            found.add(key)
            break

    missing = [k for k in TARGET_KEYS if k not in found]
    if missing:
        raise ValueError(f"Missing target keys in makegeo.inp: {', '.join(missing)}")
    return changed


def replace_named_value(lines: list[str], name: str, value: str) -> tuple[int, str]:
    pat = re.compile(rf"(!\s*{re.escape(name)}\s*=\s*)([^!]*?)(\s*!)")
    for i, line in enumerate(lines):
        m = pat.search(line)
        if m:
            old = m.group(2).strip()
            lines[i] = line[: m.start()] + f"{m.group(1)}{value}{m.group(3)}" + line[m.end() :]
            return i + 1, old
    raise ValueError(f"Could not locate {name} in makegeo.inp")


def resolve_file(path_str: str, label: str) -> pathlib.Path:
    p = pathlib.Path(path_str).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"{label} not found: {p}")
    return p


def update_makegeo(
    makegeo_path: pathlib.Path,
    grid: GridDef,
    ludat: pathlib.Path,
    terrdat: pathlib.Path,
    dry_run: bool,
) -> tuple[list[tuple[int, str, str, str]], list[tuple[int, str, str, str]]]:
    makegeo_path = makegeo_path.resolve()
    lines = makegeo_path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)

    sync_changes = sync_makegeo_projection_grid(lines, grid_to_makegeo_values(grid))
    file_changes: list[tuple[int, str, str, str]] = []

    ludat_rel = os.path.relpath(ludat, start=makegeo_path.parent)
    terrdat_rel = os.path.relpath(terrdat, start=makegeo_path.parent)
    line_no, old = replace_named_value(lines, "LUDAT", ludat_rel)
    file_changes.append((line_no, "LUDAT", old, ludat_rel))
    line_no, old = replace_named_value(lines, "TERRDAT", terrdat_rel)
    file_changes.append((line_no, "TERRDAT", old, terrdat_rel))

    if dry_run:
        print("[dry-run] 预览完成: 将同步参数并更新 LUDAT/TERRDAT 路径")
        return sync_changes, file_changes

    makegeo_path.write_text("".join(lines), encoding="utf-8")
    return sync_changes, file_changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--grid",
        default=str(CASE_ROOT / "grid" / "grid.cmn"),
        help="Path to grid.cmn",
    )
    parser.add_argument(
        "--makegeo",
        default=str(CASE_ROOT / "geo" / "makegeo" / "makegeo.inp"),
        help="Path to makegeo.inp",
    )
    parser.add_argument(
        "--ludat",
        default=DEFAULT_LUDAT,
        help="Path to LU.DAT from CTGPROC",
    )
    parser.add_argument(
        "--terrdat",
        default=DEFAULT_TERRDAT,
        help="Path to TERR.DAT from TERREL",
    )
    parser.add_argument(
        "--makegeo-bin",
        default=str(executable_path("makegeo", platform="linux-x86_64")),
        help="Path to MAKEGEO executable",
    )
    parser.add_argument(
        "--no-run-makegeo",
        action="store_true",
        help="Only update makegeo.inp; do not run makegeo.x",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview updates without file write")
    args = parser.parse_args()

    grid = parse_grid_cmn(pathlib.Path(args.grid).resolve())
    makegeo_path = pathlib.Path(args.makegeo).resolve()
    ludat = resolve_file(args.ludat, "LU.DAT")
    terrdat = resolve_file(args.terrdat, "TERR.DAT")

    sync_changes, file_changes = update_makegeo(
        makegeo_path=makegeo_path,
        grid=grid,
        ludat=ludat,
        terrdat=terrdat,
        dry_run=args.dry_run,
    )

    _ = (sync_changes, file_changes)

    if args.dry_run:
        print("[dry-run] 跳过 MAKEGEO 执行")
        return 0

    if args.no_run_makegeo:
        print("已跳过 MAKEGEO 执行(--no-run-makegeo)")
        return 0

    makegeo_bin = pathlib.Path(args.makegeo_bin).resolve()
    if args.makegeo_bin == str(executable_path("makegeo", platform="linux-x86_64")):
        makegeo_bin = resolve_executable("makegeo")
    elif not makegeo_bin.exists():
        raise FileNotFoundError(f"MAKEGEO executable not found: {makegeo_bin}")

    proc = subprocess.run(
        [str(makegeo_bin), makegeo_path.name],
        cwd=str(makegeo_path.parent),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        raise subprocess.CalledProcessError(proc.returncode, [str(makegeo_bin), makegeo_path.name])
    print(f"合并完成, 输出文件位置: {makegeo_path.parent}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise

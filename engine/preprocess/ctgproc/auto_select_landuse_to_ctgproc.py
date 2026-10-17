#!/usr/bin/env python3
"""Select landuse file and update/run CTGPROC.

Reads grid definition from grid.cmn, syncs projection/grid keys in ctgproc.inp,
updates NDBF and Subgroup (0b) landuse list, then optionally runs ctgproc.x.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass

from engine.core.paths import TUTORIAL_ROOT, current_project_path, executable_path, resolve_executable, tutorial_path

CASE_ROOT = current_project_path()
DEFAULT_LANDUSE_FILE = str(
    tutorial_path("calpuff_terrain_and_landuse_data", "eurasia_asia_landuse", "eausgs2_0la.img")
)


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


def grid_to_ctg_values(grid: GridDef) -> dict[str, str]:
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


def sync_ctg_projection_grid(lines: list[str], new_values: dict[str, str]) -> list[tuple[int, str, str, str]]:
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
        raise ValueError(f"Missing target keys in ctgproc.inp: {', '.join(missing)}")
    return changed


def parse_lcfiles_setting(ctgproc_path: pathlib.Path) -> bool:
    text = ctgproc_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    pat = re.compile(r"!\s*LCFILES\s*=\s*([TF])\s*!", re.IGNORECASE)
    for line in text:
        m = pat.search(line)
        if m:
            return m.group(1).upper() == "T"
    return True


def ensure_lowercase_visible(path: pathlib.Path) -> pathlib.Path:
    """Ensure a lower-cased view of a path is reachable on case-sensitive filesystems."""
    path = path.resolve()
    lowered = pathlib.Path(str(path).lower())
    if lowered.exists():
        return lowered
    if not path.exists() or lowered == path:
        return path

    try:
        path.relative_to(TUTORIAL_ROOT)
        return path
    except ValueError:
        pass

    actual_parts = path.parts
    lowered_parts = lowered.parts
    actual_cursor = pathlib.Path(actual_parts[0])
    lowered_cursor = pathlib.Path(lowered_parts[0])

    # Create the first missing lower-case alias at each differing path segment.
    for actual_part, lowered_part in zip(actual_parts[1:-1], lowered_parts[1:-1]):
        actual_cursor /= actual_part
        lowered_cursor /= lowered_part
        if lowered_cursor.exists() or actual_part == lowered_part:
            continue
        if not lowered_cursor.parent.exists():
            continue
        try:
            lowered_cursor.symlink_to(actual_cursor)
        except OSError:
            return path

    if lowered.exists():
        return lowered
    return path


def resolve_landuse_file(landuse_file_arg: str) -> pathlib.Path:
    p = pathlib.Path(landuse_file_arg).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Landuse file not found: {p}")
    return p


def read_generic_landuse_header(path: pathlib.Path) -> tuple[str, str] | None:
    """Read projection and datum from a ``GENERIC.LANDUSE 1.0`` header.

    Field order mirrors the reads in the GENERIC branch of ctgproc.for:
    dataset/version/modifier (2a16,a64) -> number of comment lines -> comments ->
    projection (a8) -> datum (a8) + date (a12) -> coordinate units (a4).

    Returns (projection, datum) or None when the file is not a GENERIC.LANDUSE file.
    """
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None
    if not lines or not lines[0].upper().startswith("GENERIC.LANDUSE"):
        return None

    idx = 1
    try:
        ncomment = int(lines[idx].split()[0])
    except (IndexError, ValueError):
        raise ValueError(f"无法解析 GENERIC 文件头的注释行数: {path}")
    idx += 1 + ncomment
    if idx + 1 >= len(lines):
        raise ValueError(f"GENERIC 文件头不完整: {path}")

    projection = lines[idx][:8].strip().upper()
    datum = lines[idx + 1][:8].strip().upper()
    if not projection or not datum:
        raise ValueError(f"无法解析 GENERIC 文件头的投影/datum: {path}")
    if projection != "LL":
        raise ValueError(f"GENERIC 文件投影必须为 LL，实际为 {projection}: {path}")
    return projection, datum


def sync_dnzgen(lines: list[str], datum: str) -> tuple[int, str, str] | None:
    """Set ``DNZGEN`` in Subgroup (0c) to the datum of a GENERIC landuse file.

    ctgproc.x resolves the coordinates of GENERIC point files with the DNZGEN
    datum-region string (see ``call GLOBE(...,dnzgen,...)`` in the GENERIC branch
    of ctgproc.for), not with the datum written in the file header, so both must
    agree or the points are placed with the wrong datum.
    """
    pat = re.compile(r"(!\s*DNZGEN\s*=\s*)([^!]*?)(\s*!)")
    for i, line in enumerate(lines):
        m = pat.search(line)
        if not m:
            continue
        old_value = m.group(2).strip()
        if old_value.upper() == datum.upper():
            return None
        lines[i] = line[: m.start()] + f"{m.group(1)}{datum}{m.group(3)}" + line[m.end() :]
        return (i + 1, "DNZGEN", old_value, datum)
    raise ValueError("Could not locate DNZGEN in ctgproc.inp")


def relative_to_case_dir(target: pathlib.Path, base_dir: pathlib.Path) -> str:
    try:
        rel_to_root = target.relative_to(TUTORIAL_ROOT)
        canonical = tutorial_path(*rel_to_root.parts)
        return os.path.relpath(canonical, start=base_dir)
    except ValueError:
        pass

    lower_root = pathlib.Path(str(TUTORIAL_ROOT).lower())
    try:
        rel_to_root = target.relative_to(lower_root)
        canonical = tutorial_path(*rel_to_root.parts)
        return os.path.relpath(canonical, start=base_dir)
    except ValueError:
        return os.path.relpath(target, start=base_dir)


def update_ctgproc(
    ctgproc_path: pathlib.Path,
    grid: GridDef,
    landuse_file: pathlib.Path,
    lulc_type: str,
    dry_run: bool,
    generic_datum: str | None = None,
) -> tuple[list[tuple[int, str, str, str]], int]:
    ctgproc_path = ctgproc_path.resolve()
    lines = ctgproc_path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)

    sync_changes = sync_ctg_projection_grid(lines, grid_to_ctg_values(grid))

    if generic_datum:
        dnzgen_change = sync_dnzgen(lines, generic_datum)
        if dnzgen_change:
            sync_changes.append(dnzgen_change)

    ndbf_pat = re.compile(r"(!\s*NDBF\s*=\s*)([^!]*?)(\s*!)")
    ndbf_done = False
    for i, line in enumerate(lines):
        m = ndbf_pat.search(line)
        if m:
            lines[i] = line[: m.start()] + f"{m.group(1)}1{m.group(3)}" + line[m.end() :]
            ndbf_done = True
            break
    if not ndbf_done:
        raise ValueError("Could not locate NDBF in ctgproc.inp")

    b_start = None
    g1_start = None
    for i, line in enumerate(lines):
        if "Subgroup (0b)" in line:
            b_start = i
        if b_start is not None and "INPUT GROUP: 1" in line:
            g1_start = i
            break
    if b_start is None or g1_start is None or g1_start <= b_start:
        raise ValueError("Could not locate Subgroup (0b)/INPUT GROUP: 1 boundaries")

    block = lines[b_start:g1_start]

    db_line_pat = re.compile(r"^\s*\d+\s*!\s*([A-Z0-9]+)\s*=", re.IGNORECASE)
    block_wo_data = [line for line in block if not db_line_pat.match(line)]

    anchor = None
    anchor_pat = re.compile(rf"\(\s*{re.escape(lulc_type.upper())}\s*\)")
    for i, line in enumerate(block_wo_data):
        if anchor_pat.search(line):
            anchor = i
    if anchor is None:
        raise ValueError(f"Could not find anchor ({lulc_type}) in Subgroup (0b)")

    sep_pat = re.compile(r"^\s*-{5,}\s*$")
    insert_at = None
    for i in range(anchor + 1, len(block_wo_data)):
        if sep_pat.match(block_wo_data[i]):
            insert_at = i
            break
    if insert_at is None:
        insert_at = anchor + 1

    rel_landuse = pathlib.Path(relative_to_case_dir(landuse_file, ctgproc_path.parent))
    insert_line = f"1 !{lulc_type.upper()} = {rel_landuse} !    !END!\n"
    new_block = block_wo_data[:insert_at] + [insert_line] + block_wo_data[insert_at:]
    rebuilt = lines[:b_start] + new_block + lines[g1_start:]

    if dry_run:
        print("[dry-run] 预览完成: 将同步参数并更新土地利用文件记录")
        return sync_changes, 1

    ctgproc_path.write_text("".join(rebuilt), encoding="utf-8")
    return sync_changes, 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--grid",
        default=str(CASE_ROOT / "grid" / "grid.cmn"),
        help="Path to grid.cmn",
    )
    parser.add_argument(
        "--ctgproc",
        default=str(CASE_ROOT / "geo" / "ctgproc" / "ctgproc.inp"),
        help="Path to ctgproc.inp",
    )
    parser.add_argument(
        "--landuse-file",
        default=DEFAULT_LANDUSE_FILE,
        help="Single landuse .img file path",
    )
    parser.add_argument(
        "--lulc-type",
        default="GLAZAS",
        help="LULC type keyword for Subgroup (0b), e.g., GLAZAS (.img) or GEN (GENERIC.LANDUSE point file)",
    )
    parser.add_argument(
        "--force-lowercase-path",
        action="store_true",
        help="Force writing lower-case landuse path regardless of LCFILES setting",
    )
    parser.add_argument(
        "--ctgproc-bin",
        default=str(executable_path("ctgproc", platform="linux-x86_64")),
        help="Path to CTGPROC executable",
    )
    parser.add_argument(
        "--no-run-ctgproc",
        action="store_true",
        help="Only update ctgproc.inp; do not run ctgproc.x",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview updates without file write")
    args = parser.parse_args()

    grid = parse_grid_cmn(pathlib.Path(args.grid).resolve())
    ctgproc_path = pathlib.Path(args.ctgproc).resolve()
    lcfiles_lower = parse_lcfiles_setting(ctgproc_path)
    landuse_file = resolve_landuse_file(args.landuse_file)
    if lcfiles_lower or args.force_lowercase_path:
        landuse_file = ensure_lowercase_visible(landuse_file)

    generic_header = read_generic_landuse_header(landuse_file)
    lulc_type = args.lulc_type.upper()
    if generic_header is not None and lulc_type != "GEN":
        raise SystemExit(
            f"{landuse_file} 是 GENERIC.LANDUSE 点文件, 请加 --lulc-type GEN (当前为 {lulc_type})"
        )
    if generic_header is None and lulc_type == "GEN":
        raise SystemExit(
            f"--lulc-type GEN 需要 GENERIC.LANDUSE 1.0 格式文件, 但 {landuse_file} 不是"
        )
    generic_datum = generic_header[1] if generic_header else None
    print(f"已选择的土地利用文件: {landuse_file}")
    if generic_datum:
        print(f"GENERIC 点文件输入 datum: {generic_datum} (将同步到 DNZGEN)")

    sync_changes, _ = update_ctgproc(
        ctgproc_path,
        grid,
        landuse_file,
        lulc_type,
        dry_run=args.dry_run,
        generic_datum=generic_datum,
    )
    print("已同步 CTGPROC 投影/网格参数:")
    for line_no, key, old, new in sync_changes:
        print(f"  第{line_no}行: {key}: {old} -> {new}")

    if args.dry_run:
        print("[dry-run] 跳过 CTGPROC 执行")
        return 0

    if args.no_run_ctgproc:
        print("已跳过 CTGPROC 执行(--no-run-ctgproc)")
        return 0

    ctgproc_bin = pathlib.Path(args.ctgproc_bin).resolve()
    ctgproc_inp = pathlib.Path(args.ctgproc).resolve()
    if args.ctgproc_bin == str(executable_path("ctgproc", platform="linux-x86_64")):
        ctgproc_bin = resolve_executable("ctgproc")
    elif not ctgproc_bin.exists():
        raise FileNotFoundError(f"CTGPROC executable not found: {ctgproc_bin}")

    proc = subprocess.run(
        [str(ctgproc_bin), ctgproc_inp.name],
        cwd=str(ctgproc_inp.parent),
        capture_output=True,
        text=True,
    )
    lines = (proc.stdout or "").splitlines()
    for i, line in enumerate(lines):
        if "Processing:" in line:
            print(f"\n  正在处理土地利用数据:{line.split('Processing:', 1)[1]}")
            if i + 1 < len(lines):
                path_line = lines[i + 1].rstrip()
                if path_line.strip():
                    print(path_line)
            break
    if proc.returncode != 0:
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        raise subprocess.CalledProcessError(proc.returncode, [str(ctgproc_bin), ctgproc_inp.name])
    print(f"\n土地利用数据创建完成, 输出文件位置: {ctgproc_inp.parent}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise

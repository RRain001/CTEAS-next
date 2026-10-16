#!/usr/bin/env python3
"""Auto-generate and update smerge.inp from *_filled.csv station files.

Behavior:
1) Scan INPUT_DIR for files like `<USAF>-<WBAN>.csv` (e.g. 583210-99999.csv)
2) Extract the 6-char USAF and 5-char WBAN from the filename
3) Lookup XELEV from isd-history.txt by the exact 6-char USAF code
   - XELEV: ELEV(M) field, round half up to integer meters
4) If XELEV is not found, default to 10
5) Write suggested sections to OUTPUT_TXT
6) Directly update SMERGE_INP

IFSTN(SMERGE/SURF.DAT 站号)取 USAF 前 5 位;同一案例内两个站映射到同一
5 位站号时显式失败,不静默合并或丢站。
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
import re
from datetime import datetime
from typing import Dict, List, Tuple
from decimal import Decimal, ROUND_HALF_UP

from engine.core.paths import current_project_path, engine_path

CASE_ROOT = current_project_path()

INPUT_DIR = CASE_ROOT / 'met' / 'surface' / 'isd2smerge_ready'
OUTPUT_DIR = CASE_ROOT / 'run' / 'smerge'
SMERGE_INP = OUTPUT_DIR / 'smerge.inp'
ISD_HISTORY = engine_path("resources", "isd", "isd-history.txt")
OUTPUT_TXT = OUTPUT_DIR / 'smerge_manual_sections.txt'

FILLED_PATTERN = re.compile(r'^([0-9A-Za-z]{6})-([0-9A-Za-z]{5})\.csv$')


def _round_half_up_to_int(x: float) -> int:
    return int(Decimal(str(x)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def parse_history_elevations(path: Path) -> Dict[str, int]:
    """Return mapping USAF(6-digit/alnum) -> XELEV (int meters) from isd-history.txt."""
    mapping: Dict[str, float] = {}
    lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    data_started = False
    for raw in lines:
        line = raw.strip()
        if not data_started:
            if line.startswith('USAF') and 'WBAN' in line and 'ELEV(M)' in line and 'BEGIN' in line and 'END' in line:
                data_started = True
            continue
        if not line:
            continue
        parts = line.split()
        # data row has at least:
        # USAF WBAN ... LAT LON ELEV BEGIN END
        if len(parts) < 8:
            continue
        usaf = parts[0]
        if not re.fullmatch(r'[0-9A-Za-z]{6}', usaf):
            continue
        sid = usaf
        elev_str = parts[-3]
        try:
            elev_val = float(elev_str)
        except ValueError:
            continue
        mapping[sid] = _round_half_up_to_int(elev_val)
    return mapping


def discover_filled_files(input_dir: Path) -> List[Tuple[str, str, Path]]:
    """Find `<USAF>-<WBAN>.csv` files and return (usaf, wban, path)."""
    records: List[Tuple[str, str, Path]] = []
    for p in sorted(input_dir.iterdir()):
        if not p.is_file():
            continue
        m = FILLED_PATTERN.match(p.name)
        if not m:
            continue
        records.append((m.group(1), m.group(2), p))
    return records


def fmt_elev(value: int) -> str:
    return str(int(value))


def resolve_ifstn(filled: List[Tuple[str, str, Path]]) -> Dict[str, str]:
    """站点编号(IFSTN)= isd-history.txt 中的 6 位 USAF,原样使用。

    SMERGE 以整数读取并写入 SURF.DAT(支持超过 5 位),CALMET 的 met.inp /
    SURF.DAT 站号同样按整数处理(SURF.DAT 文本输出为 i8),因此不再截取前 5 位,
    583210 与 583211 这类站点可以共存而不会撞号。
    """
    mapping: Dict[str, str] = {}
    owner: Dict[str, str] = {}
    for usaf, wban, _path in filled:
        key = f"{usaf}-{wban}"
        if not re.fullmatch(r"[0-9]{6}", usaf):
            raise ValueError(
                f"站点 {key} 的 USAF {usaf!r} 不是 6 位数字;SMERGE/SURF.DAT 需要整数站号,"
                "请在案例中排除该站或改用可整除的站号约定。"
            )
        if usaf in owner and owner[usaf] != key:
            raise ValueError(
                f"站号冲突: 站点 {owner[usaf]} 与 {key} 的 USAF 相同({usaf});"
                "SMERGE/SURF.DAT 无法区分。请在案例中只保留其中一个站。"
            )
        owner.setdefault(usaf, key)
        mapping[key] = usaf
    return mapping


def build_station_blocks(
    filled: List[Tuple[str, str, Path]],
    elev_map: Dict[str, int],
) -> Tuple[List[str], List[str]]:
    """Build Group-0b station blocks and return (lines, missing_station_ids)."""
    lines: List[str] = []
    missing: List[str] = []
    ifstn_map = resolve_ifstn(filled)
    for usaf, wban, fpath in filled:
        key = f"{usaf}-{wban}"
        ifstn = ifstn_map[key]
        xelev = elev_map.get(usaf)
        if xelev is None:
            missing.append(key)
            xelev_str = '10'
        else:
            xelev_str = fmt_elev(xelev)

        lines.append(f'     !SFCMET = {os.path.relpath(fpath, start=OUTPUT_DIR)} !')
        lines.append(f'     !IFSTN = {ifstn} !')
        lines.append(f'     !XELEV = {xelev_str} !')
        lines.append('     !ASTZ = UTC+0000 !   !END!')
        lines.append('')
    return lines, missing


def build_sections(filled: List[Tuple[str, str, Path]], elev_map: Dict[str, int]) -> str:
    lines: List[str] = []
    lines.append('===== Suggested replacements for SMERGE.INP =====')
    lines.append('')
    lines.append('INPUT GROUP 0a (paths + station count):')
    lines.append(f'! NFF = {len(filled)} !')
    lines.append('! PREVDAT = * !')
    lines.append('! SURFDAT = surf.dat !')
    lines.append('! RUNLST = smerge.lst !')
    lines.append('! LCFILES = T !')
    lines.append('')
    lines.append('INPUT GROUP 0b (repeat this 4-line block for each station):')

    station_lines, missing = build_station_blocks(filled, elev_map)
    lines.extend(station_lines)

    if missing:
        lines.append('WARNING: XELEV not found in isd-history.txt for station IDs:')
        lines.append(', '.join(missing))
        lines.append('Defaulted XELEV to 10 for these stations.')
        lines.append('')

    lines.append('Optional check for Group 1:')
    lines.append('! ABTZ = UTC+0000 !')

    return '\n'.join(lines) + '\n'


def detect_time_range_from_wdir(csv_path: Path) -> Tuple[datetime, datetime]:
    """Detect start/end datetime from wind-direction data rows in one filled CSV."""
    with csv_path.open('r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        # 3-line header format
        _ = next(reader, None)
        _ = next(reader, None)
        col_row = next(reader, None)
        if not col_row:
            raise RuntimeError(f'Invalid CSV header: {csv_path}')

        cols = [x.strip() for x in col_row]
        idx = {name: i for i, name in enumerate(cols)}
        required = ['Year', 'Month', 'Day', 'Hour']
        for r in required:
            if r not in idx:
                raise RuntimeError(f'Missing column "{r}" in {csv_path.name}')

        # Prefer generic column name "deg", fallback to "Wdir10m"
        wdir_col = 'deg' if 'deg' in idx else ('Wdir10m' if 'Wdir10m' in idx else None)
        if not wdir_col:
            raise RuntimeError(f'Missing wind direction column ("deg"/"Wdir10m") in {csv_path.name}')

        min_dt = None
        max_dt = None
        for row in reader:
            if not row:
                continue
            try:
                wdir = float(row[idx[wdir_col]])
            except Exception:
                continue

            # treat 9999 as missing
            if wdir == 9999:
                continue

            try:
                y = int(float(row[idx['Year']]))
                m = int(float(row[idx['Month']]))
                d = int(float(row[idx['Day']]))
                h = int(float(row[idx['Hour']])) // 100
                dt = datetime(y, m, d, h, 0, 0)
            except Exception:
                continue

            if min_dt is None or dt < min_dt:
                min_dt = dt
            if max_dt is None or dt > max_dt:
                max_dt = dt

    if min_dt is None or max_dt is None:
        raise RuntimeError(f'No valid wind-direction timestamps found in {csv_path.name}')
    return min_dt, max_dt


def detect_global_period(filled: List[Tuple[str, str, Path]]) -> Tuple[datetime, datetime]:
    """Detect global start/end from all filled station files based on wind direction."""
    starts: List[datetime] = []
    ends: List[datetime] = []
    for _usaf, _wban, fpath in filled:
        st, ed = detect_time_range_from_wdir(fpath)
        starts.append(st)
        ends.append(ed)
    return min(starts), max(ends)


def replace_assignment_line(line: str, key: str, value: str) -> str:
    pattern = re.compile(rf'!\s*{re.escape(key)}\s*=\s*[^!]*!')
    if pattern.search(line):
        return pattern.sub(f'! {key} = {value} !', line)
    return line


def update_smerge_inp(
    smerge_path: Path,
    nff: int,
    station_block_lines: List[str],
    start_dt: datetime,
    end_dt: datetime,
) -> None:
    if not smerge_path.exists():
        raise FileNotFoundError(f'smerge.inp not found: {smerge_path}')

    original = smerge_path.read_text(encoding='utf-8')

    lines = original.splitlines()

    # Group 0a key assignments
    for i, line in enumerate(lines):
        line = replace_assignment_line(line, 'NFF', str(nff))
        line = replace_assignment_line(line, 'SURFDAT', 'surf.dat')
        line = replace_assignment_line(line, 'RUNLST', 'smerge.lst')
        line = replace_assignment_line(line, 'LCFILES', 'T')
        # Group 1 processing period
        line = replace_assignment_line(line, 'IBYR', str(start_dt.year))
        line = replace_assignment_line(line, 'IBMO', str(start_dt.month))
        line = replace_assignment_line(line, 'IBDY', str(start_dt.day))
        line = replace_assignment_line(line, 'IBHR', str(start_dt.hour))
        line = replace_assignment_line(line, 'IBSEC', str(start_dt.second))
        line = replace_assignment_line(line, 'IEYR', str(end_dt.year))
        line = replace_assignment_line(line, 'IEMO', str(end_dt.month))
        line = replace_assignment_line(line, 'IEDY', str(end_dt.day))
        line = replace_assignment_line(line, 'IEHR', str(end_dt.hour))
        line = replace_assignment_line(line, 'IESEC', str(end_dt.second))
        line = replace_assignment_line(line, 'ABTZ', 'UTC+0000')
        lines[i] = line

    # Locate Group 0b section
    start = None
    end = None
    for i, line in enumerate(lines):
        if 'Subgroup (0b)' in line:
            start = i
            break
    for i, line in enumerate(lines):
        if 'INPUT GROUP: 1' in line:
            end = i
            break
    if start is None or end is None or end <= start:
        raise RuntimeError('Cannot locate Group 0b section in smerge.inp')

    # Insert generated station blocks before the dashed line preceding Group 1
    insert_idx = end
    for i in range(start, end):
        if lines[i].strip().startswith('-----------------------------------------------------------------------------'):
            insert_idx = i
            break

    # Remove existing station block lines and excessive blank lines in 0b section
    kept = []
    for i, line in enumerate(lines):
        if start <= i < insert_idx:
            stripped = line.strip()
            if (
                stripped.startswith('!SFCMET')
                or stripped.startswith('!IFSTN')
                or stripped.startswith('!XELEV')
                or stripped.startswith('!ASTZ')
            ):
                continue
            # keep at most one separator blank in this subsection
            if stripped == '':
                continue
        kept.append(line)
    lines = kept

    # Recompute insert index after deletions
    start = next(i for i, line in enumerate(lines) if 'Subgroup (0b)' in line)
    end = next(i for i, line in enumerate(lines) if 'INPUT GROUP: 1' in line)
    insert_idx = end
    for i in range(start, end):
        if lines[i].strip().startswith('-----------------------------------------------------------------------------'):
            insert_idx = i
            break

    # Keep a fixed visual spacing before injected 0b station blocks
    injected = []
    # Preserve template-like spacing in subgroup 0b
    injected.extend(['', '', '', ''])
    injected.extend(station_block_lines)
    if injected and injected[-1] != '':
        injected.append('')

    lines = lines[:insert_idx] + injected + lines[insert_idx:]

    smerge_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    if not INPUT_DIR.exists():
        print(f'Input directory not found: {INPUT_DIR}')
        return 1
    if not OUTPUT_DIR.exists():
        print(f'Output directory not found: {OUTPUT_DIR}')
        return 1
    if not ISD_HISTORY.exists():
        print(f'ISD history file not found: {ISD_HISTORY}')
        return 1
    if not SMERGE_INP.exists():
        print(f'smerge.inp not found: {SMERGE_INP}')
        return 1

    filled = discover_filled_files(INPUT_DIR)
    if not filled:
        print(f'No *_filled.csv files found in: {INPUT_DIR}')
        return 1

    elev_map = parse_history_elevations(ISD_HISTORY)
    station_block_lines, _missing = build_station_blocks(filled, elev_map)
    content = build_sections(filled, elev_map)

    OUTPUT_TXT.write_text(content, encoding='utf-8')
    start_dt, end_dt = detect_global_period(filled)
    print(f'数据符合研究时间范围: {start_dt} -> {end_dt} (UTC+0000)')

    update_smerge_inp(SMERGE_INP, len(filled), station_block_lines, start_dt, end_dt)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

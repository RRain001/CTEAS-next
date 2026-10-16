#!/usr/bin/env python3
"""Select SRTM GeoTIFF files covering CALPUFF grid domain and write TERREL 0b list.

Reads grid definition from grid.cmn (UTM case), computes domain bbox in lon/lat,
selects intersecting calpuff_terrain_and_landuse_data/china_srtm/srtm_XX_YY.tif files, then updates:
  - NTDF in Subgroup (0a)
  - GEOTIFF file list in Subgroup (0b)
"""

from __future__ import annotations

import argparse
import math
import os
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass

from engine.core.paths import current_project_path, executable_path, resolve_executable, tutorial_path

CASE_ROOT = current_project_path()


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


@dataclass
class BBox:
    lon_min: float
    lat_min: float
    lon_max: float
    lat_max: float

    def intersects(self, other: "BBox") -> bool:
        return not (
            self.lon_max <= other.lon_min
            or self.lon_min >= other.lon_max
            or self.lat_max <= other.lat_min
            or self.lat_min >= other.lat_max
        )


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


def grid_bbox_wgs84(grid: GridDef, igrid: int) -> BBox:
    if grid.imap != "UTM":
        raise ValueError(f"Only UTM is supported right now, got IMAP={grid.imap}")
    if igrid not in (1, 2):
        raise ValueError(f"IGRID must be 1 or 2 for Cartesian grid, got {igrid}")

    dx_m = grid.dgridkm * 1000.0
    x0 = grid.xrefkm * 1000.0
    y0 = grid.yrefkm * 1000.0

    if igrid == 1:
        x_min = x0
        y_min = y0
        x_max = x0 + grid.nx * dx_m
        y_max = y0 + grid.ny * dx_m
    else:
        x_min = x0 - 0.5 * dx_m
        y_min = y0 - 0.5 * dx_m
        x_max = x0 + (grid.nx - 0.5) * dx_m
        y_max = y0 + (grid.ny - 0.5) * dx_m

    pts = [
        (x_min, y_min),
        (x_max, y_min),
        (x_min, y_max),
        (x_max, y_max),
    ]
    lonlats = [utm_to_wgs84_lonlat(x, y, grid.iutmzn, grid.lsohem == "N") for x, y in pts]
    lons = [p[0] for p in lonlats]
    lats = [p[1] for p in lonlats]

    return BBox(
        lon_min=min(lons),
        lat_min=min(lats),
        lon_max=max(lons),
        lat_max=max(lats),
    )


def cgiar_tile_bbox(x_idx: int, y_idx: int) -> BBox:
    lon_min = -180.0 + (x_idx - 1) * 5.0
    lon_max = lon_min + 5.0
    lat_max = 60.0 - (y_idx - 1) * 5.0
    lat_min = lat_max - 5.0
    return BBox(lon_min=lon_min, lon_max=lon_max, lat_min=lat_min, lat_max=lat_max)


def utm_to_wgs84_lonlat(easting_m: float, northing_m: float, zone: int, northern: bool) -> tuple[float, float]:
    """Convert UTM (WGS84) to lon/lat degrees without external deps."""
    # WGS84 ellipsoid
    a = 6378137.0
    e = 0.08181919084262149
    e2 = e * e
    e1sq = e2 / (1.0 - e2)
    k0 = 0.9996

    x = easting_m - 500000.0
    y = northing_m if northern else northing_m - 10000000.0

    m = y / k0
    mu = m / (a * (1.0 - e2 / 4.0 - 3.0 * e2 * e2 / 64.0 - 5.0 * e2 * e2 * e2 / 256.0))

    e1 = (1.0 - math.sqrt(1.0 - e2)) / (1.0 + math.sqrt(1.0 - e2))
    j1 = 3.0 * e1 / 2.0 - 27.0 * e1**3 / 32.0
    j2 = 21.0 * e1 * e1 / 16.0 - 55.0 * e1**4 / 32.0
    j3 = 151.0 * e1**3 / 96.0
    j4 = 1097.0 * e1**4 / 512.0
    fp = mu + j1 * math.sin(2.0 * mu) + j2 * math.sin(4.0 * mu) + j3 * math.sin(6.0 * mu) + j4 * math.sin(8.0 * mu)

    sin_fp = math.sin(fp)
    cos_fp = math.cos(fp)
    tan_fp = math.tan(fp)

    c1 = e1sq * cos_fp * cos_fp
    t1 = tan_fp * tan_fp
    n1 = a / math.sqrt(1.0 - e2 * sin_fp * sin_fp)
    r1 = a * (1.0 - e2) / ((1.0 - e2 * sin_fp * sin_fp) ** 1.5)
    d = x / (n1 * k0)

    lat = fp - (n1 * tan_fp / r1) * (
        d * d / 2.0
        - (5.0 + 3.0 * t1 + 10.0 * c1 - 4.0 * c1 * c1 - 9.0 * e1sq) * d**4 / 24.0
        + (61.0 + 90.0 * t1 + 298.0 * c1 + 45.0 * t1 * t1 - 252.0 * e1sq - 3.0 * c1 * c1) * d**6 / 720.0
    )

    lon0 = math.radians((zone - 1) * 6 - 180 + 3)
    lon = lon0 + (
        d - (1.0 + 2.0 * t1 + c1) * d**3 / 6.0 + (5.0 - 2.0 * c1 + 28.0 * t1 - 3.0 * c1 * c1 + 8.0 * e1sq + 24.0 * t1 * t1) * d**5 / 120.0
    ) / cos_fp

    return math.degrees(lon), math.degrees(lat)


def read_bbox_sidecar(tif_path: pathlib.Path) -> "BBox | None":
    """Read the ``<name>.bbox`` companion file of a cropped tile.

    Cropped tiles cover only a small part of the 5x5 degree nominal sheet, so the
    nominal CIGAR bounds cannot be used to decide whether a file covers a domain.
    Returns None when the companion file is missing or unparsable.
    """
    sidecar = tif_path.with_suffix(".bbox")
    if not sidecar.is_file():
        return None
    for line in sidecar.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            lon_min, lat_min, lon_max, lat_max = (float(v) for v in parts[:4])
        except ValueError:
            continue
        return BBox(lon_min=lon_min, lat_min=lat_min, lon_max=lon_max, lat_max=lat_max)
    return None


def pick_tiles(srtm_dir: pathlib.Path, domain: BBox) -> list[pathlib.Path]:
    picked: list[tuple[int, int, str, pathlib.Path]] = []
    pat = re.compile(r"^srtm_(\d{2})_(\d{2})", re.IGNORECASE)
    for p in sorted(srtm_dir.glob("srtm_*.tif")):
        m = pat.match(p.name)
        if not m:
            continue
        x_idx = int(m.group(1))
        y_idx = int(m.group(2))
        coverage = read_bbox_sidecar(p) or cgiar_tile_bbox(x_idx, y_idx)
        if coverage.intersects(domain):
            picked.append((x_idx, y_idx, p.name.lower(), p))

    picked.sort(key=lambda t: (t[0], t[1], t[2]))
    return [p for _, _, _, p in picked]


def grid_to_terrel_values(grid: GridDef) -> dict[str, str]:
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


def sync_terrel_projection_grid(lines: list[str], new_values: dict[str, str]) -> list[tuple[int, str, str, str]]:
    """Replace first '! KEY = ... !' occurrence for TARGET_KEYS."""
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
        raise ValueError(f"Missing target keys in terrel.inp: {', '.join(missing)}")
    return changed


def update_terrel(
    terrel_path: pathlib.Path, grid: GridDef, tif_paths: list[pathlib.Path], dry_run: bool
) -> tuple[list[tuple[int, str, str, str]], int]:
    terrel_path = terrel_path.resolve()
    lines = terrel_path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)

    # Merge functionality from sync_terrel_from_grid.py
    sync_changes = sync_terrel_projection_grid(lines, grid_to_terrel_values(grid))

    # Update NTDF
    ntdf_pat = re.compile(r"(!\s*NTDF\s*=\s*)([^!]*?)(\s*!)")
    ntdf_done = False
    for i, line in enumerate(lines):
        m = ntdf_pat.search(line)
        if m:
            lines[i] = line[: m.start()] + f"{m.group(1)}{len(tif_paths)}{m.group(3)}" + line[m.end() :]
            ntdf_done = True
            break
    if not ntdf_done:
        raise ValueError("Could not locate NTDF in terrel.inp")

    # Locate Subgroup (0b) block boundaries
    b_start = None
    c_start = None
    for i, line in enumerate(lines):
        if "Subgroup (0b)" in line:
            b_start = i
        if b_start is not None and "Subgroup (0c)" in line:
            c_start = i
            break
    if b_start is None or c_start is None or c_start <= b_start:
        raise ValueError("Could not locate Subgroup (0b)/(0c) boundaries")

    block = lines[b_start:c_start]

    # Remove existing numbered GEOTIFF entries inside 0b.
    geotif_line = re.compile(r"^\s*\d+\s*!GEOTIFF\s*=", re.IGNORECASE)
    block_wo_data = [line for line in block if not geotif_line.match(line)]

    # Insert new list after the "(GEOTIFF)  designates GEOTIFF data files" line.
    anchor = None
    for i, line in enumerate(block_wo_data):
        if "(GEOTIFF)" in line and "designates GEOTIFF" in line:
            anchor = i
    if anchor is None:
        raise ValueError("Could not find GEOTIFF anchor line in Subgroup (0b)")

    # Prefer inserting before the next section separator after anchor.
    insert_at = None
    sep_pat = re.compile(r"^\s*-{5,}\s*$")
    for i in range(anchor + 1, len(block_wo_data)):
        if sep_pat.match(block_wo_data[i]):
            insert_at = i
            break
    if insert_at is None:
        insert_at = anchor + 1

    insert_lines = [
        f"{i} !GEOTIFF = {os.path.relpath(p, start=terrel_path.parent)} !    !END!\n"
        for i, p in enumerate(tif_paths, start=1)
    ]
    new_block = block_wo_data[:insert_at] + insert_lines + block_wo_data[insert_at:]
    rebuilt = lines[:b_start] + new_block + lines[c_start:]

    if dry_run:
        print(f"[dry-run] 预览完成: 将同步参数并写入 {len(tif_paths)} 条 GEOTIFF 记录")
        return sync_changes, len(tif_paths)

    terrel_path.write_text("".join(rebuilt), encoding="utf-8")
    return sync_changes, len(tif_paths)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--grid",
        default=str(CASE_ROOT / "grid" / "grid.cmn"),
        help="Path to grid.cmn",
    )
    parser.add_argument(
        "--terrel",
        default=str(CASE_ROOT / "geo" / "terrel" / "terrel.inp"),
        help="Path to terrel.inp",
    )
    parser.add_argument(
        "--srtm-dir",
        default=str(tutorial_path("calpuff_terrain_and_landuse_data", "china_srtm")),
        help="Directory containing srtm_XX_YY.tif",
    )
    parser.add_argument(
        "--terrel-bin",
        default=str(executable_path("terrel", platform="linux-x86_64")),
        help="Path to TERREL executable",
    )
    parser.add_argument(
        "--no-run-terrel",
        action="store_true",
        help="Only update terrel.inp; do not run terrel.x",
    )
    parser.add_argument(
        "--igrid",
        type=int,
        default=1,
        help="Grid type convention for XREF/YREF: 1=corner of cell(1,1), 2=center of cell(1,1)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview selection without file write")
    args = parser.parse_args()

    grid = parse_grid_cmn(pathlib.Path(args.grid).resolve())
    domain = grid_bbox_wgs84(grid, args.igrid)
    tifs = pick_tiles(pathlib.Path(args.srtm_dir).resolve(), domain)
    if not tifs:
        print("未找到与研究区域相交的 tif 文件, 请检查网格或 srtm 数据目录", file=sys.stderr)
        return 2

    print(
        "研究区域 WGS84 边界: "
        f"经度[{domain.lon_min:.6f}, {domain.lon_max:.6f}], "
        f"纬度[{domain.lat_min:.6f}, {domain.lat_max:.6f}]"
    )
    print(f"已选择 tif 文件数量: {len(tifs)}")
    for p in tifs:
        print(f"  {p}")

    sync_changes, n_tifs = update_terrel(pathlib.Path(args.terrel).resolve(), grid, tifs, dry_run=args.dry_run)
    print("已同步投影/网格参数:")
    for line_no, key, old, new in sync_changes:
        print(f"  第{line_no}行: {key}: {old} -> {new}")
    print(f"已更新地形文件列表数量: {n_tifs}")
    print(f"地形数据文件较大, 正在加载, 请耐心等待1~2分钟!")

    if args.dry_run:
        print("[dry-run] 跳过 TERREL 执行")
        return 0

    if args.no_run_terrel:
        print("已跳过 TERREL 执行(--no-run-terrel)")
        return 0

    terrel_bin = pathlib.Path(args.terrel_bin).resolve()
    terrel_inp = pathlib.Path(args.terrel).resolve()
    if args.terrel_bin == str(executable_path("terrel", platform="linux-x86_64")):
        terrel_bin = resolve_executable("terrel")
    elif not terrel_bin.exists():
        raise FileNotFoundError(f"TERREL executable not found: {terrel_bin}")

    proc = subprocess.run(
        [str(terrel_bin), terrel_inp.name],
        cwd=str(terrel_inp.parent),
        capture_output=True,
        text=True,
    )
    out = proc.stdout or ""
    lines = out.splitlines()
    for i, line in enumerate(lines):
        if "Processing data file" in line:
            print("\n 正在处理地形数据文件: ")
            for j in range(i + 1, len(lines)):
                candidate = lines[j].rstrip()
                if candidate.strip():
                    print(candidate)
                    break
    if proc.returncode != 0:
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        raise subprocess.CalledProcessError(proc.returncode, [str(terrel_bin), terrel_inp.name])
    print(f"地形数据文件创建完成, 输出文件位置: {terrel_inp.parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

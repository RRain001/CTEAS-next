#!/usr/bin/env python3
"""裁剪 CALPUFF 地形（SRTM GeoTIFF）与土地利用（USGS GLCC GLAZAS）数据。

用途
----
把体积很大的基础数据目录 ``calpuff_terrain_and_landuse_data/`` 中，
与某个研究站点相关的一小块地形与土地利用数据裁剪出来，
输出到体积很小、可以纳入 Git 的目录
（约定放在 ``calpuff_terrain_and_landuse_data_crop/<site>/``）。
源数据目录本身不做任何修改。

研究范围是"以站点为中心的正方形"：``--study-side-km`` 为边长，
``--margin-km`` 为四周额外余量，实际裁剪半宽 = 边长/2 + 余量。

两类数据的裁剪方式不同，原因见下。

地形（SRTM GeoTIFF）
--------------------
``china_srtm/srtm_XX_YY.tif`` 为 CIAT-CSI SRTM v4.1，5°×5° 分幅、3 弧秒
（0.0008333°）GeoTIFF，文件自带 WGS84 地理参考；TERREL 直接按文件内的
tie-point/pixel-scale/GeoKey 读取。因此地形就是普通窗口裁剪：
按像素边界向外取整，写一个新的 GeoTIFF（未压缩、条带存储，与源文件一致），
并附带 ``<name>.bbox`` 旁文件记录真实覆盖范围，供
``auto_select_srtm_to_terrel.py`` 精确挑选（源分幅文件没有该旁文件，
仍按 5°×5° 名义分幅范围判断，行为不变）。

土地利用（USGS GLCC 1 km GLAZAS）
---------------------------------
``eurasia_asia_landuse/eausgs2_0la.img`` 是 USGS GLCC 1 km 栅格：Lambert 方位
等积投影（LAZA，球半径 6370997 m，中心 45°N/100°E，原点 x=-8000 km、
y=-5499 km、格距 1 km），固定尺寸 13000×12000，无文件头。
CTGPROC 的 ``GLAZAS`` 读取按固定行列计算直接访问记录号
（``ctgproc.for`` 中 nxia/nyia/dxia/xorga/yorga/rlata/rlona 表），
且不允许在输入文件中改写尺寸或原点，所以它无法直接读取"尺寸变小的裁剪栅格"。

因此土地利用裁剪输出两份互相一致的成果：

1. ``*_laea.tif``：原始 LAZA 投影下的逐像元裁剪（用于查看/核对，不参与管线）；
2. ``*.generic.txt``：同样这些像元，写成 CTGPROC 支持的
   ``GENERIC.LANDUSE 1.0`` 点格式（每行 ``LU 经度 纬度``）。
   像元类别先按 GLAZAS 的换算表 ``itab`` 转成 USGS-92 类别号
   （与 GLAZAS 路径喂给 LUGRID 的类别号一致），
   再在每个 1 km 像元内按 ``--mesh-cells``（默认 20，即 50 m）取
   mesh×mesh 个子网格点。

   点文件等价性：CTGPROC 的 GLAZAS 分支会按 ``MESHGLAZ`` 在 1 km 像元内
   细分取点，GENERIC 分支则直接使用文件里给出的点（GENERIC 分支不使用
   MESHGLAZ）。所以 ``--mesh-cells`` 与 ``ctgproc.inp`` 的 ``MESHGLAZ``
   取相同数值时，本点文件与全量数据走 GLAZAS 路径的结果逐格一致。

注意：GENERIC 点文件按其 *坐标* 解释，而 ctgproc.x 在 GENERIC 分支里使用
``DNZGEN`` 作为输入坐标的 datum（见 ``ctgproc.for`` 中
``call GLOBE(...,dnzgen,...)``），并非文件头里的 datum。
本工具在文件头写 ``ESR-S``（与 GLAZAS 输入的 ``DUSGSLA`` 默认值一致，
即 GLCC 数据的球面坐标），使用本工具产出的点文件时，
``ctgproc.inp`` 需要把 ``DNZGEN`` 一并设为 ``ESR-S``
（``auto_select_landuse_to_ctgproc.py`` 会从文件头自动同步该项）。

依赖
----
需要 ``rasterio``（读写 GeoTIFF/ERDAS IMG）。它不是 CTEAS 运行期依赖，
仅数据准备时需要，例如：``uv pip install rasterio``。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform as warp_transform
from rasterio.windows import Window, from_bounds

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_SRTM_DIR = REPO_ROOT / "calpuff_terrain_and_landuse_data" / "china_srtm"
DEFAULT_LANDUSE = (
    REPO_ROOT
    / "calpuff_terrain_and_landuse_data"
    / "eurasia_asia_landuse"
    / "eausgs2_0la.img"
)

# --- USGS GLCC "GLAZAS" 栅格参数，取自 ctgproc.for 中
#     nxia/nyia/dxia/dyia/xorga/yorga/rlata/rlona 的第 4 组（Eurasia - Asia）
GLCC_NX = 13000
GLCC_NY = 12000
GLCC_CELL_KM = 1.0
GLCC_XORG_KM = -8000.0
GLCC_YORG_KM = -5499.0
GLCC_LAT0 = 45.0
GLCC_LON0 = 100.0
GLCC_SPHERE_M = 6370997.0

# --- GLAZAS 编码 -> USGS-92 类别号，取自 ctgproc.for 的 "data itab"
GLCC_TO_USGS92 = (
    16, 21, 21, 21, 21, 21, 31, 32, 33, 33,
    41, 41, 42, 42, 43, 52, 62, 61,
    77, 82, 81, 85, 83, 91,
)

# --- 标准 USGS-92 类别清单（38 类），由 ctgproc.for 的 lumap 非零项确定；
#     GENERIC 文件头必须给出该清单，ctgproc 才会按 USGS-38 方式处理
USGS92_STANDARD = (
    11, 12, 13, 14, 15, 16, 17, 21, 22, 23, 24, 31, 32, 33, 41, 42, 43,
    51, 52, 53, 54, 55, 61, 62, 71, 72, 73, 74, 75, 76, 77, 81, 82, 83,
    84, 85, 91, 92,
)

LANDUSE_DATUM = "ESR-S"


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def laea_inverse(x_km: float, y_km: float) -> tuple[float, float]:
    """GCTP PJ11Z0 逆变换：LAZA(km) -> 经度/纬度(deg)，球半径 6370997 m。"""
    x = x_km * 1000.0
    y = y_km * 1000.0
    rho = math.hypot(x, y)
    if rho == 0.0:
        return GLCC_LON0, GLCC_LAT0
    z = 2.0 * math.asin(min(1.0, rho / (2.0 * GLCC_SPHERE_M)))
    sin_z, cos_z = math.sin(z), math.cos(z)
    sin_p0 = math.sin(math.radians(GLCC_LAT0))
    cos_p0 = math.cos(math.radians(GLCC_LAT0))
    lat = math.asin(cos_z * sin_p0 + y * sin_z * cos_p0 / rho)
    con = cos_z - sin_p0 * math.sin(lat)
    lon = math.radians(GLCC_LON0) + math.atan2(x * sin_z * cos_p0, con * rho)
    return math.degrees(lon), math.degrees(lat)


def laea_forward(lon: float, lat: float) -> tuple[float, float]:
    """GCTP PJ11Z0 正变换：经度/纬度(deg) -> LAZA(km)。"""
    lon_r = math.radians(lon)
    lat_r = math.radians(lat)
    sin_p0 = math.sin(math.radians(GLCC_LAT0))
    cos_p0 = math.cos(math.radians(GLCC_LAT0))
    g = sin_p0 * math.sin(lat_r) + cos_p0 * math.cos(lat_r) * math.cos(lon_r - math.radians(GLCC_LON0))
    ksp = math.sqrt(2.0 / (1.0 + g))
    x = GLCC_SPHERE_M * ksp * math.cos(lat_r) * math.sin(lon_r - math.radians(GLCC_LON0))
    y = GLCC_SPHERE_M * ksp * (
        cos_p0 * math.sin(lat_r) - sin_p0 * math.cos(lat_r) * math.cos(lon_r - math.radians(GLCC_LON0))
    )
    return x / 1000.0, y / 1000.0


def utm_epsg(lon: float, lat: float) -> int:
    zone = int((lon + 180.0) // 6.0) + 1
    return (32600 if lat >= 0 else 32700) + zone


def utm_box_points(center_e: float, center_n: float, half_km: float) -> list[tuple[float, float]]:
    """研究范围方框在 UTM 平面上的角点与边中点（含中心）。"""
    xs = (center_e - half_km, center_e, center_e + half_km)
    ys = (center_n - half_km, center_n, center_n + half_km)
    return [(x, y) for x in xs for y in ys]


def cgiar_tile_bounds(x_idx: int, y_idx: int) -> tuple[float, float, float, float]:
    """CIAT-CSI SRTM 5°×5° 分幅的名义范围 (lon_min, lat_min, lon_max, lat_max)。"""
    lon_min = -180.0 + (x_idx - 1) * 5.0
    lat_max = 60.0 - (y_idx - 1) * 5.0
    return lon_min, lat_max - 5.0, lon_min + 5.0, lat_max


def read_bbox_sidecar(tif_path: pathlib.Path) -> tuple[float, float, float, float] | None:
    """读取 ``<name>.bbox`` 旁文件：忽略 # 注释，取第一行 4 个浮点数。"""
    sidecar = tif_path.with_suffix(".bbox")
    if not sidecar.exists():
        return None
    for line in sidecar.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 4:
            lon_min, lat_min, lon_max, lat_max = (float(v) for v in parts[:4])
            return lon_min, lat_min, lon_max, lat_max
    return None


def pick_srtm_tiles(srtm_dir: pathlib.Path, bbox: tuple[float, float, float, float]) -> list[pathlib.Path]:
    """挑出与研究范围相交的 SRTM 分幅/裁剪文件（优先用 .bbox 旁文件）。"""
    lon_min, lat_min, lon_max, lat_max = bbox
    picked = []
    for path in sorted(srtm_dir.glob("srtm_*.tif")):
        stem = path.stem
        actual = read_bbox_sidecar(path)
        if actual is None:
            try:
                x_idx = int(stem.split("_")[1])
                y_idx = int(stem.split("_")[2])
            except (IndexError, ValueError):
                continue
            actual = cgiar_tile_bounds(x_idx, y_idx)
        a_lon_min, a_lat_min, a_lon_max, a_lat_max = actual
        if a_lon_min <= lon_max and a_lon_max >= lon_min and a_lat_min <= lat_max and a_lat_max >= lat_min:
            picked.append(path)
    return picked


def crop_terrain_tile(src_path: pathlib.Path, bbox: tuple[float, float, float, float], out_dir: pathlib.Path,
                      tag: str, dry_run: bool) -> dict:
    lon_min, lat_min, lon_max, lat_max = bbox
    with rasterio.open(src_path) as src:
        win = from_bounds(lon_min, lat_min, lon_max, lat_max, src.transform)
        col0 = max(0, math.floor(win.col_off))
        row0 = max(0, math.floor(win.row_off))
        col1 = min(src.width, math.ceil(win.col_off + win.width))
        row1 = min(src.height, math.ceil(win.row_off + win.height))
        if col1 <= col0 or row1 <= row0:
            raise SystemExit(f"研究范围不在分幅 {src_path.name} 内")
        window = Window(col0, row0, col1 - col0, row1 - row0)
        data = src.read(1, window=window)
        transform = src.window_transform(window)
        profile = src.profile.copy()
        profile.pop("blockxsize", None)
        profile.pop("blockysize", None)
        profile.update(
            width=window.width,
            height=window.height,
            transform=transform,
            tiled=False,
            compress=None,
            photometric="MINISBLACK",
            interleave="band",
            BIGTIFF="NO",
        )
        out_path = out_dir / f"{src_path.stem}_{tag}{src_path.suffix}"
        tile_bounds = rasterio.transform.array_bounds(window.height, window.width, transform)[0:4]
        meta = {
            "source": str(src_path),
            "source_sha256": sha256(src_path),
            "output": str(out_path),
            "window": {"col_off": col0, "row_off": row0, "width": window.width, "height": window.height},
            "dtype": src.dtypes[0],
            "nodata": src.nodata,
            "pixel_deg": src.res[0],
            "bounds_wgs84": [tile_bounds[0], tile_bounds[1], tile_bounds[2], tile_bounds[3]],
        }
        if dry_run:
            return meta

        dst = rasterio.open(out_path, "w", **profile)
        try:
            dst.write(data, 1)
            tags = dict(src.tags())
            tags["AREA_OR_POINT"] = "Area"
            dst.update_tags(**tags)
        finally:
            dst.close()

        # 旁文件：真实覆盖范围，供 auto_select_srtm_to_terrel.py 精确挑选
        sidecar = out_path.with_suffix(".bbox")
        west, south, east, north = tile_bounds
        sidecar.write_text(
            "# WGS84 覆盖范围（十进制度）：lon_min lat_min lon_max lat_max\n"
            f"{west:.7f} {south:.7f} {east:.7f} {north:.7f}\n"
        )

    # 自检：裁剪结果必须与源逐像元一致
    with rasterio.open(src_path) as src, rasterio.open(out_path) as dst:
        assert dst.width == meta["window"]["width"] and dst.height == meta["window"]["height"]
        assert dst.crs == src.crs
        assert dst.transform.almost_equals(transform)
        ref = src.read(1, window=window)
        got = dst.read(1)
        if not np.array_equal(ref, got):
            raise SystemExit(f"地形裁剪自检失败：{out_path} 与源数据不一致")
    meta["sha256"] = sha256(out_path)
    meta["bytes"] = out_path.stat().st_size
    return meta


def landuse_window(utm_crs: str, center_e: float, center_n: float, half_km: float,
                   buffer_km: float) -> dict:
    """由研究范围方框定出需要的 GLCC 像元行列范围（含缓冲）。"""
    pts = utm_box_points(center_e, center_n, half_km)
    e, n = warp_transform(utm_crs, "EPSG:4326", [p[0] * 1000 for p in pts], [p[1] * 1000 for p in pts])
    xs, ys = [], []
    for lon, lat in zip(e, n):
        x, y = laea_forward(lon, lat)
        xs.append(x)
        ys.append(y)
    x_min, x_max = min(xs) - buffer_km, max(xs) + buffer_km
    y_min, y_max = min(ys) - buffer_km, max(ys) + buffer_km
    i0 = max(1, math.floor((x_min - GLCC_XORG_KM) / GLCC_CELL_KM) + 1)
    i1 = min(GLCC_NX, math.ceil((x_max - GLCC_XORG_KM) / GLCC_CELL_KM))
    j0 = max(1, math.floor((y_min - GLCC_YORG_KM) / GLCC_CELL_KM) + 1)
    j1 = min(GLCC_NY, math.ceil((y_max - GLCC_YORG_KM) / GLCC_CELL_KM))
    return {
        "i0": i0, "i1": i1, "j0": j0, "j1": j1,
        "laea_bounds_km": [x_min, y_min, x_max, y_max],
        "utm_box_corners": pts,
    }


def read_glcc_block(img_path: pathlib.Path, win: dict) -> np.ndarray:
    """按行直接读取 GLCC 原始栅格（13000×12000 uint8，文件内北在上）。"""
    i0, i1, j0, j1 = win["i0"], win["i1"], win["j0"], win["j1"]
    ncols = i1 - i0 + 1
    nrows = j1 - j0 + 1
    block = np.zeros((nrows, ncols), dtype=np.uint8)
    with img_path.open("rb") as fh:
        for row in range(nrows):
            j = j1 - row  # 文件第 0 行对应最北（j 最大）的像元行
            offset = (GLCC_NY - j) * GLCC_NX + (i0 - 1)
            fh.seek(offset)
            chunk = fh.read(ncols)
            if len(chunk) != ncols:
                raise SystemExit(f"GLCC 数据读取越界：row={row} j={j}")
            block[row, :] = np.frombuffer(chunk, dtype=np.uint8)
    return block


def write_landuse_laea_tif(block: np.ndarray, win: dict, out_path: pathlib.Path, dry_run: bool) -> None:
    i0 = win["i0"]
    x_left = GLCC_XORG_KM + (i0 - 1) * GLCC_CELL_KM - GLCC_CELL_KM / 2.0
    y_top = GLCC_YORG_KM + (win["j1"] - 1) * GLCC_CELL_KM + GLCC_CELL_KM / 2.0
    transform = from_origin(x_left, y_top, GLCC_CELL_KM, GLCC_CELL_KM)  # 坐标为 km
    crs = (
        f"+proj=laea +lat_0={GLCC_LAT0} +lon_0={GLCC_LON0} +x_0=0 +y_0=0 "
        f"+a={GLCC_SPHERE_M} +b={GLCC_SPHERE_M} +units=km +no_defs +type=crs"
    )
    if dry_run:
        return
    profile = {
        "driver": "GTiff",
        "width": block.shape[1],
        "height": block.shape[0],
        "count": 1,
        "dtype": "uint8",
        "nodata": 0,
        "crs": crs,
        "transform": transform,
        "tiled": False,
        "compress": None,
        "photometric": "MINISBLACK",
        "interleave": "band",
        "BIGTIFF": "NO",
    }
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(block, 1)
        dst.update_tags(AREA_OR_POINT="Area", UNITS="USGS-92 land use category (0 = water/no data)")


def write_generic_points(block: np.ndarray, win: dict, out_path: pathlib.Path, mesh: int, dry_run: bool) -> dict:
    """把裁剪出的 GLCC 像元写成 CTGPROC 的 GENERIC.LANDUSE 1.0 点文件。"""
    header = [
        "GENERIC.LANDUSE 1.0".ljust(96),
        "1",
        "LU, Longitude, Latitude. Cropped USGS GLCC (GLAZAS) data, categories are USGS-92.",
        "LL".ljust(8),
        f"{LANDUSE_DATUM.ljust(8)}{'':12}",
        "DEG",
        str(len(USGS92_STANDARD)),
        " ".join(str(v) for v in USGS92_STANDARD),
    ]
    n_points = 0
    n_cells = 0
    skipped = 0
    sub = GLCC_CELL_KM / mesh
    lines: list[str] = []
    for row in range(block.shape[0]):
        j = win["j1"] - row
        for col in range(block.shape[1]):
            raw = int(block[row, col])
            if raw < 1 or raw > len(GLCC_TO_USGS92):
                # 与 GLAZAS 路径一致：无类别（0，含水）像元按缺测跳过
                skipped += 1
                continue
            lucat = GLCC_TO_USGS92[raw - 1]
            i = win["i0"] + col
            xc = GLCC_XORG_KM + (i - 1) * GLCC_CELL_KM
            yc = GLCC_YORG_KM + (j - 1) * GLCC_CELL_KM
            n_cells += 1
            for im in range(mesh):
                x = xc - GLCC_CELL_KM / 2.0 + (im + 0.5) * sub
                for jm in range(mesh):
                    y = yc - GLCC_CELL_KM / 2.0 + (jm + 0.5) * sub
                    lon, lat = laea_inverse(x, y)
                    lines.append(f"{lucat} {lon:.7f} {lat:.7f}")
                    n_points += 1
    if not dry_run:
        out_path.write_text("\n".join(header + lines) + "\n")
    return {
        "output": str(out_path),
        "cells": n_cells,
        "cells_skipped_no_data": skipped,
        "mesh_cells": mesh,
        "mesh_km": sub,
        "points": n_points,
        "categories": len(USGS92_STANDARD),
        "datum": LANDUSE_DATUM,
        "generator": "scripts/crop_terrain_landuse_data.py",
    }


def write_readme(out_root: pathlib.Path, meta: dict) -> None:
    terrain = meta["terrain"][0] if meta["terrain"] else None
    landuse_generic = meta["landuse"]["generic"]["output"]
    mesh = meta["landuse"]["generic"]["mesh_cells"]
    lines = [
        f"# 地形/土地利用裁剪数据：{meta['tag']}",
        "",
        f"- 站点中心：{meta['center']['lat']:.9f}N, {meta['center']['lon']:.9f}E",
        f"- 研究范围：以站点为中心的 {meta['study_side_km']} km × {meta['study_side_km']} km 正方形",
        f"- 裁剪范围：半宽 {meta['half_width_km']} km（研究范围半宽 "
        f"{meta['study_side_km'] / 2} km + 余量 {meta['margin_km']} km），"
        f"UTM {meta['utm_crs']} 平面、中心 {meta['center']['utm_e']:.3f} / {meta['center']['utm_n']:.3f} km",
        f"- WGS84 范围：lon {meta['bbox_wgs84'][0]:.5f}..{meta['bbox_wgs84'][2]:.5f}, "
        f"lat {meta['bbox_wgs84'][1]:.5f}..{meta['bbox_wgs84'][3]:.5f}",
        "",
        "## 文件",
        "",
        "| 文件 | 说明 |",
        "| --- | --- |",
    ]
    if terrain:
        lines.append(
            f"| `{pathlib.Path(terrain['output']).name}` | SRTM 3 弧秒地形裁剪，"
            f"{terrain['window']['width']}×{terrain['window']['height']} 像元，WGS84 GeoTIFF |"
        )
        lines.append(
            f"| `{pathlib.Path(terrain['output']).with_suffix('.bbox').name}` | 上表文件的真实覆盖范围，"
            "供 `auto_select_srtm_to_terrel.py` 精确挑选 |"
        )
    lines += [
        f"| `{pathlib.Path(landuse_generic).name}` | 土地利用点文件（CTGPROC `GEN` 输入，"
        f"{meta['landuse']['generic']['cells']} 个 1 km 像元 × {mesh}×{mesh} 细分网格，"
        f"点距 {meta['landuse']['generic']['mesh_km'] * 1000:.0f} m） |",
        f"| `{pathlib.Path(meta['landuse']['laea_tif']).name}` | 同范围 LAZA 投影逐像元栅格，"
        "仅用于查看核对 |",
        f"| `{pathlib.Path(meta['manifest']).name}` | 生成参数、窗口、校验和 |",
        "",
        "## 使用",
        "",
        "```bash",
        "# 地形（TERREL）",
        "python3 -m engine.preprocess.terrel.auto_select_srtm_to_terrel \\",
        f"  --srtm-dir {pathlib.Path(terrain['output']).parent if terrain else 'china_srtm'}",
        "",
        "# 土地利用（CTGPROC）",
        "python3 -m engine.preprocess.ctgproc.auto_select_landuse_to_ctgproc \\",
        f"  --landuse-file {landuse_generic} --lulc-type GEN",
        "```",
        "",
        "土地利用点文件的坐标按 GLCC 数据的球面 datum（`ESR-S`）解释："
        "`ctgproc.inp` 中的 `DNZGEN` 必须同步为文件头中的 datum，"
        "`auto_select_landuse_to_ctgproc.py` 会自动读取并同步。",
        "",
        f"点文件按 {meta['landuse']['generic']['mesh_km'] * 1000:.0f} m 间距采样（mesh {mesh}）。"
        "GENERIC 分支不使用 `MESHGLAZ`，点密度即采样密度；"
        f"若要与全量数据在 `MESHGLAZ = N` 下的结果逐格一致，用 `--mesh-cells N`（N={mesh} 即当前密度）重新生成。",
        "",
        f"由 `scripts/crop_terrain_landuse_data.py` 生成，源数据 sha256 见 `{pathlib.Path(meta['manifest']).name}`。",
        "",
    ]
    (out_root / "README.md").write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="裁剪站点附近的地形（SRTM）与土地利用（GLCC/GLAZAS）数据",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--center-lat", type=float, required=True, help="站点纬度（十进制度，北正）")
    parser.add_argument("--center-lon", type=float, required=True, help="站点经度（十进制度，东正）")
    parser.add_argument("--study-side-km", type=float, default=5.0,
                        help="研究范围边长（km，以站点为中心的正方形）")
    parser.add_argument("--margin-km", type=float, default=1.0, help="研究范围四周额外余量（km）")
    parser.add_argument("--tag", required=True, help="输出文件后缀/站点标识，如 hefei_5km")
    parser.add_argument("--out-dir", type=pathlib.Path, required=True, help="输出目录")
    parser.add_argument("--srtm-dir", type=pathlib.Path, default=DEFAULT_SRTM_DIR)
    parser.add_argument("--landuse-file", type=pathlib.Path, default=DEFAULT_LANDUSE)
    parser.add_argument("--landuse-buffer-km", type=float, default=1.5,
                        help="土地利用向裁剪范围外扩的缓冲（km，需 ≥0.5 以保证边界像元完整）")
    parser.add_argument("--mesh-cells", type=int, default=20,
                        help="每个 1 km 像元的细分网格数（与 ctgproc.inp 的 MESHGLAZ 对应，默认 20 即 50 m）")
    parser.add_argument("--dry-run", action="store_true", help="只计算窗口与统计，不写文件")
    args = parser.parse_args()

    utm_crs = f"EPSG:{utm_epsg(args.center_lon, args.center_lat)}"
    half = args.study_side_km / 2.0 + args.margin_km
    center_e, center_n = warp_transform("EPSG:4326", utm_crs, [args.center_lon], [args.center_lat])
    center_e, center_n = float(center_e[0]) / 1000.0, float(center_n[0]) / 1000.0
    corners = utm_box_points(center_e, center_n, half)
    e, n = warp_transform(
        utm_crs, "EPSG:4326",
        [p[0] * 1000 for p in corners], [p[1] * 1000 for p in corners],
    )
    bbox = (min(e), min(n), max(e), max(n))

    terrain_dir = args.out_dir / DEFAULT_SRTM_DIR.name
    landuse_dir = args.out_dir / DEFAULT_LANDUSE.parent.name
    if not args.dry_run:
        terrain_dir.mkdir(parents=True, exist_ok=True)
        landuse_dir.mkdir(parents=True, exist_ok=True)

    terrain_tiles = pick_srtm_tiles(args.srtm_dir, bbox)
    if not terrain_tiles:
        raise SystemExit(f"在 {args.srtm_dir} 中找不到覆盖研究范围的地形数据")
    terrain_meta = []
    for tile in terrain_tiles:
        meta = crop_terrain_tile(tile, bbox, terrain_dir, args.tag, args.dry_run)
        terrain_meta.append(meta)
        print(f"[terrain] {tile.name} -> {pathlib.Path(meta['output']).name} "
              f"{meta['window']['width']}x{meta['window']['height']} px")

    win = landuse_window(utm_crs, center_e, center_n, half, args.landuse_buffer_km)
    block = read_glcc_block(args.landuse_file, win)
    print(f"[landuse] GLCC 窗口 i={win['i0']}..{win['i1']} j={win['j0']}..{win['j1']} "
          f"({block.shape[1]}x{block.shape[0]} 像元)")

    stem = args.landuse_file.stem
    laea_tif = landuse_dir / f"{stem}_{args.tag}.tif"
    generic_txt = landuse_dir / f"{stem}_{args.tag}.generic.txt"
    write_landuse_laea_tif(block, win, laea_tif, args.dry_run)
    generic_meta = write_generic_points(block, win, generic_txt, args.mesh_cells, args.dry_run)
    print(f"[landuse] {generic_meta['cells']} 个有效像元（跳过缺测 {generic_meta['cells_skipped_no_data']} 个）"
          f" -> {generic_meta['points']} 个点")

    manifest = {
        "tag": args.tag,
        "center": {"lat": args.center_lat, "lon": args.center_lon, "utm_e": center_e, "utm_n": center_n},
        "utm_crs": utm_crs,
        "study_side_km": args.study_side_km,
        "margin_km": args.margin_km,
        "half_width_km": half,
        "bbox_wgs84": list(bbox),
        "srtm_dir": str(args.srtm_dir),
        "landuse_file": str(args.landuse_file),
        "landuse_window": win,
        "terrain": terrain_meta,
        "landuse": {"laea_tif": str(laea_tif), "generic": generic_meta},
    }
    if args.dry_run:
        print("[dry-run] 未写入任何文件")
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0

    manifest["landuse"]["laea_tif_sha256"] = sha256(laea_tif)
    manifest["landuse"]["laea_tif_bytes"] = laea_tif.stat().st_size
    generic_meta["sha256"] = sha256(generic_txt)
    generic_meta["bytes"] = generic_txt.stat().st_size
    manifest["manifest"] = str(args.out_dir / "crop_info.json")
    (args.out_dir / "crop_info.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    write_readme(args.out_dir, manifest)

    total = sum(int(m.get("bytes", 0)) for m in terrain_meta)
    total += manifest["landuse"]["laea_tif_bytes"] + generic_meta["bytes"]
    print(f"[done] 输出目录 {args.out_dir}，合计 {total / 1024:.1f} KiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

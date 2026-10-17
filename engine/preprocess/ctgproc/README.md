# CTGPROC 自动配置与执行说明

本目录提供一个脚本，用于基于 `grid.cmn` 自动更新 `ctgproc.inp` 的必要参数，并执行 CTGPROC 生成 `lu.dat`。

## 脚本

- [auto_select_landuse_to_ctgproc.py](./engine/preprocess/ctgproc/auto_select_landuse_to_ctgproc.py)

## 固定土地利用数据

当前默认直接使用单一土地利用文件（亚洲/欧洲覆盖）：

- `./calpuff_terrain_and_landuse_data/eurasia_asia_landuse/eausgs2_0la.img`

不再做目录扫描和自动挑选多文件。

## 会自动同步/修改的内容

脚本会从 `./project/current/grid/grid.cmn` 同步以下参数到 `ctgproc.inp`：

- `PMAP`
- `IUTMZN`
- `UTMHEM`
- `DATUM`
- `XREFKM`
- `YREFKM`
- `NX`
- `NY`
- `DGRIDKM`

同时会更新：

- `NDBF = 1`
- `Subgroup (0b)` 中的 `1 !GLAZAS = ... !    !END!`

## 与副本文件对比后的必要改动结论

相对于 `ctgproc - 副本.inp`，当前 `ctgproc.inp` 仅有以下必要差异：

- `GLAZAS` 路径改为本机可用 Linux 路径
- `XREFKM: 433.385 -> 493.384`
- `YREFKM: 3453.769 -> 3513.683`
- `NX: 160 -> 40`
- `NY: 160 -> 40`

其余关键控制项保持不变（如 `PMAP/IUTMZN/UTMHEM/DATUM/DGRIDKM/LCFILES/LFINAL/LPREV/MESH*`）。

## 运行方式

在任意目录执行：

```bash
python3 -m engine.preprocess.ctgproc.auto_select_landuse_to_ctgproc
```

执行后会在 `./project/current/geo/ctgproc/` 生成或更新：

- `ctgproc.inp`
- `ctgproc.lst`
- `lu.dat`

## 常用参数

只预览修改，不写文件、不运行 CTGPROC：

```bash
python3 -m engine.preprocess.ctgproc.auto_select_landuse_to_ctgproc --dry-run
```

只更新 `ctgproc.inp`，不执行 `ctgproc.x`：

```bash
python3 -m engine.preprocess.ctgproc.auto_select_landuse_to_ctgproc --no-run-ctgproc
```

覆盖默认土地利用文件：

```bash
python3 -m engine.preprocess.ctgproc.auto_select_landuse_to_ctgproc \
  --landuse-file /path/to/your_landuse.img
```

## 使用站点裁剪数据（GENERIC 点文件）

`calpuff_terrain_and_landuse_data_crop/<站点>/` 下的土地利用裁剪件是
`GENERIC.LANDUSE 1.0` 点文件（原因见 `docs/terrain_landuse_crop.md`），
必须用 `--lulc-type GEN`：

```bash
python3 -m engine.preprocess.ctgproc.auto_select_landuse_to_ctgproc \
  --landuse-file calpuff_terrain_and_landuse_data_crop/hefei_5km/eurasia_asia_landuse/eausgs2_0la_hefei_5km.generic.txt \
  --lulc-type GEN
```

- 脚本会校验文件类型：GENERIC 文件不加 `--lulc-type GEN`（或反过来）会直接报错退出。
- 脚本会读取 GENERIC 文件头的 datum，并同步 `ctgproc.inp` 的 `DNZGEN`
  （ctgproc 的 GENERIC 分支用 `DNZGEN` 解释点坐标，而不是文件头里的 datum）。
- `GEN` 分支不使用 `MESHGLAZ`：采样密度由点文件的点距决定
  （当前 hefei_5km 裁剪件为 50 m）。

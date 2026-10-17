# TERREL 自动化说明

本目录提供一个自动化脚本，用于：

1. 从 `grid.cmn` 同步关键网格参数到 `terrel.inp`
2. 根据研究域自动筛选覆盖范围内的 SRTM GeoTIFF
3. 回写 `terrel.inp` 的 `NTDF` 和 `Subgroup (0b)` 文件列表
4. 自动执行 `terrel.x terrel.inp` 生成 `terrel.dat`

---

## 脚本

- `auto_select_srtm_to_terrel.py`

---

## 默认输入输出路径

- 网格文件：`./project/current/grid/grid.cmn`
- 控制文件：`./project/current/geo/terrel/terrel.inp`
- 地形目录：`./calpuff_terrain_and_landuse_data/china_srtm`
- TERREL 程序：`./bin/<platform>/terrel.x`

输出文件（TERREL 运行后）：

- `terrel.dat`
- `terrel.lst`
- `terrel.sav`
- `qaterr.grd`

---

## 一键运行

```bash
python3 -m engine.preprocess.terrel.auto_select_srtm_to_terrel
```

---

## 常用参数

仅预览，不写文件、不运行 TERREL：

```bash
python3 -m engine.preprocess.terrel.auto_select_srtm_to_terrel --dry-run
```

只更新 `terrel.inp`，不执行 `terrel.x`：

```bash
python3 -m engine.preprocess.terrel.auto_select_srtm_to_terrel --no-run-terrel
```

指定非默认路径：

```bash
python3 -m engine.preprocess.terrel.auto_select_srtm_to_terrel \
  --grid /path/to/grid.cmn \
  --terrel /path/to/terrel.inp \
  --srtm-dir /path/to/tif_dir \
  --terrel-bin /path/to/terrel.x
```

如果网格是 `IGRID=2`（`XREF/YREF` 为 cell(1,1)中心）：

```bash
python3 -m engine.preprocess.terrel.auto_select_srtm_to_terrel --igrid 2
```

---

## 脚本会同步的参数

从 `grid.cmn` -> `terrel.inp`：

- `IMAP` -> `PMAP`
- `IUTMZN` -> `IUTMZN`
- `LSOHEM` -> `UTMHEM`
- `DATUM` -> `DATUM`
- `XREFKM` -> `XREFKM`
- `YREFKM` -> `YREFKM`
- `NX` -> `NX`
- `NY` -> `NY`
- `DGRIDKM` -> `DGRIDKM`

---

## 备份说明

脚本写入 `terrel.inp` 前会自动备份：

- `terrel.inp.bak.select_tif`

---

## 依赖

- Python 3（标准库即可）
- 不依赖 `pyproj` / GDAL Python 包

---

## 注意事项

- 当前脚本按 UTM 投影处理（`IMAP=UTM`）。
- `srtm_XX_YY.tif` 文件名需符合 CGIAR 命名规则。
- `terrel.x` 执行目录为 `terrel.inp` 所在目录。

## 使用站点裁剪数据

`calpuff_terrain_and_landuse_data_crop/<站点>/china_srtm/` 下的裁剪件命名形如
`srtm_60_06_<站点>.tif`，并附带 `<name>.bbox` 旁文件记录真实覆盖范围。
挑选脚本对存在旁文件的 tif 按**旁文件范围**判断是否覆盖研究域，
对没有旁文件的全量分幅仍按 5°×5° 名义范围判断，因此两种目录都能直接用：

```bash
python3 -m engine.preprocess.terrel.auto_select_srtm_to_terrel \
  --srtm-dir calpuff_terrain_and_landuse_data_crop/hefei_5km/china_srtm
```

说明见 `docs/terrain_landuse_crop.md`。  

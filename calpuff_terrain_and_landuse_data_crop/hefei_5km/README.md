# 地形/土地利用裁剪数据：hefei_5km

- 站点中心：31.939774444N, 117.141610855E
- 研究范围：以站点为中心的 5.0 km × 5.0 km 正方形
- 裁剪范围：半宽 3.5 km（研究范围半宽 2.5 km + 余量 1.0 km），UTM EPSG:32650 平面、中心 513.385 / 3533.769 km
- WGS84 范围：lon 117.10454..117.17870, lat 31.90815..31.97139

## 文件

| 文件 | 说明 |
| --- | --- |
| `srtm_60_06_hefei_5km.tif` | SRTM 3 弧秒地形裁剪，90×77 像元，WGS84 GeoTIFF |
| `srtm_60_06_hefei_5km.bbox` | 上表文件的真实覆盖范围，供 `auto_select_srtm_to_terrel.py` 精确挑选 |
| `eausgs2_0la_hefei_5km.generic.txt` | 土地利用点文件（CTGPROC `GEN` 输入，144 个 1 km 像元 × 20×20 细分网格，点距 50 m） |
| `eausgs2_0la_hefei_5km.tif` | 同范围 LAZA 投影逐像元栅格，仅用于查看核对 |
| `crop_info.json` | 生成参数、窗口、校验和 |

## 使用

```bash
# 地形（TERREL）
python3 -m engine.preprocess.terrel.auto_select_srtm_to_terrel \
  --srtm-dir calpuff_terrain_and_landuse_data_crop/hefei_5km/china_srtm

# 土地利用（CTGPROC）
python3 -m engine.preprocess.ctgproc.auto_select_landuse_to_ctgproc \
  --landuse-file calpuff_terrain_and_landuse_data_crop/hefei_5km/eurasia_asia_landuse/eausgs2_0la_hefei_5km.generic.txt --lulc-type GEN
```

土地利用点文件的坐标按 GLCC 数据的球面 datum（`ESR-S`）解释：`ctgproc.inp` 中的 `DNZGEN` 必须同步为文件头中的 datum，`auto_select_landuse_to_ctgproc.py` 会自动读取并同步。

点文件按 50 m 间距采样（mesh 20）。GENERIC 分支不使用 `MESHGLAZ`，点密度即采样密度；若要与全量数据在 `MESHGLAZ = N` 下的结果逐格一致，用 `--mesh-cells N`（N=20 即当前密度）重新生成。

由 `scripts/crop_terrain_landuse_data.py` 生成，源数据 sha256 见 `crop_info.json`。

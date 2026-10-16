# 地形与土地利用裁剪数据

## 目的

`calpuff_terrain_and_landuse_data/` 体积过大（土地利用影像 156 MB、每个 SRTM 分幅 72 MB），
已被 Git 忽略（见 `docs/git_tracking_plan.md`）。
为了让某个具体案例在不下载全量数据的情况下也能跑通地形与土地利用前处理，
本仓库另存一份"以研究站点为中心"的小体积裁剪数据：

```text
calpuff_terrain_and_landuse_data_crop/<站点>/
```

裁剪数据是对源数据的**只读派生**，源目录内容不变、仍按原样忽略。

## 已入库：hefei_5km

| 项目 | 值 |
| --- | --- |
| 站点（烟囱） | 31.939774444°N, 117.141610855°E（UTM 50N 513.385 / 3533.769 km） |
| 研究范围 | 以烟囱为中心的 5 km × 5 km 正方形（50 m 网格即 100×100） |
| 裁剪范围 | 半宽 3.5 km ＝ 研究范围半宽 2.5 km + 四周余量 1 km |
| WGS84 范围 | lon 117.10454°..117.17870°，lat 31.90815°..31.97139°（约 7.0 × 7.0 km） |
| 数据量 | 约 1.5 MB（其中土地利用点文件 1.46 MB） |

文件：

| 文件 | 说明 |
| --- | --- |
| `china_srtm/srtm_60_06_hefei_5km.tif` | SRTM 3 弧秒地形裁剪，90×77 像元，未压缩 WGS84 GeoTIFF（与源文件同结构） |
| `china_srtm/srtm_60_06_hefei_5km.bbox` | 该 GeoTIFF 的真实覆盖范围，供挑选脚本精确判断 |
| `eurasia_asia_landuse/eausgs2_0la_hefei_5km.generic.txt` | 土地利用点文件，CTGPROC 的 `GEN` 输入（144 个 1 km 像元，20×20 细分，点距 50 m） |
| `eurasia_asia_landuse/eausgs2_0la_hefei_5km.tif` | 同范围 LAZA 投影逐像元栅格，仅用于查看核对，不参与管线 |
| `crop_info.json` | 生成参数、像元窗口、源文件与产物的 sha256 |
| `README.md` | 由脚本生成的同内容摘要 |

## 为什么土地利用不是"普通栅格裁剪"

- 地形：`srtm_XX_YY.tif` 自带地理参考，TERREL 按文件内 tie-point/pixel-scale/GeoKey 读取，
  因此按研究范围开窗裁剪即可，输出仍是一个正常的 GeoTIFF。
- 土地利用：`eausgs2_0la.img` 是**无文件头的定尺寸裸栅格**（USGS GLCC 1 km，
  Lambert 方位等积投影，球半径 6370997 m、中心 45°N/100°E、原点 x=-8000/y=-5499 km，
  固定 13000×12000）。CTGPROC 的 `GLAZAS` 分支按"固定行列 → 直接访问记录号"读取
  （`ctgproc.for` 中 nxia/nyia/dxia/xorga/yorga/rlata/rlona 表），
  输入文件里无处声明尺寸或原点，所以**尺寸变小的栅格裁剪件它读不了**。

因此土地利用裁剪件以 CTGPROC 支持的 `GENERIC.LANDUSE 1.0` 点格式（每行 `LU 经度 纬度`）给出：

- 类别号先按 GLAZAS 的 `itab` 表换算成 USGS-92 类别号（与 GLAZAS 路径喂给 `LUGRID` 的编号一致）；
- 文件头列出标准 38 类 USGS 清单，使 CTGPROC 走 `lucattype=1 / lusgs38=T`，与 GLAZAS 路径行为一致；
- 每个 1 km 像元按 20×20 子网格（50 m）取点；`GEN` 分支不使用 `MESHGLAZ`，
  **点密度即采样密度**；
- 与 GLAZAS 路径一样跳过无类别（0，含水）像元。

## 生成方式

```bash
uv pip install rasterio            # 仅数据准备需要，非运行期依赖
python3 scripts/crop_terrain_landuse_data.py \
  --center-lat 31.939774444 --center-lon 117.141610855 \
  --study-side-km 5 --margin-km 1 \
  --tag hefei_5km \
  --out-dir calpuff_terrain_and_landuse_data_crop/hefei_5km
```

脚本会自检"地形裁剪件与源逐像元一致"，并写出 `crop_info.json`（含源与产物的 sha256）。

## 使用方式

```bash
# 地形（TERREL）：--srtm-dir 指向裁剪目录，脚本按 .bbox 旁文件精确挑选
python3 -m engine.preprocess.terrel.auto_select_srtm_to_terrel \
  --srtm-dir calpuff_terrain_and_landuse_data_crop/hefei_5km/china_srtm

# 土地利用（CTGPROC）：GENERIC 点文件必须用 --lulc-type GEN，
# 脚本会读取文件头的 datum 并同步 ctgproc.inp 的 DNZGEN
python3 -m engine.preprocess.ctgproc.auto_select_landuse_to_ctgproc \
  --landuse-file calpuff_terrain_and_landuse_data_crop/hefei_5km/eurasia_asia_landuse/eausgs2_0la_hefei_5km.generic.txt \
  --lulc-type GEN
```

脚本会在 `terrel.inp` / `ctgproc.inp` 中写入相对路径（形如
`../../../../calpuff_terrain_and_landuse_data_crop/...`）。

## 等价性验证（本机实测）

验证方法：用 `gfortran`（Homebrew GCC 16.2.0，编译参数与
`docker/fortran/Dockerfile` 一致）在本机编译 `terrel.for` / `ctgproc.for`，
对同一个 5 km / 50 m（100×100）网格分别用**全量数据**与**裁剪数据**运行后比较输出。

| 项目 | 结果 |
| --- | --- |
| 地形：两版都取到 DEM 的网格 | 数值**完全相同**（最大差 0.00 m） |
| 地形：空缺位置 | 10000 格中 26 格不同（0.26%，一个像元在相邻 50 m 格间归属不同） |
| 土地利用 `lu.dat` | 10000 格中 8 格不同（0.08%，均为类别 21 的"有/无数据"互换），其余逐格一致 |
| 土地利用：有效像元 | 全量 280 格无数据 vs 裁剪 282 格无数据 |

上述少量差异来自 CTGPROC/TERREL 自身用 REAL*4 计算像元位置
（`xc = xorg + dxi*(i-1)`，单精度，误差约 0.4 m）：换个原点就换了一组舍入，
贴近网格边界的像元可能落到相邻格。它与数据本身无关，
量级也远小于 1 km 土地利用像元；两版结果与独立双精度复算的偏差同量级。

复现要点：土地利用对比时全量数据的 `MESHGLAZ` 需设为 20（与裁剪件 20×20 点阵一致）。

## 注意事项

1. **路径长度上限 132 字符**：CTGPROC/TERREL 的输入文件名缓冲为 132 字符，
   案例目录按 `project/current/geo/<tool>/` 布局时上述相对路径约 114 字符，可用；
   若站点目录名或文件名过长会触发 `Array bounds exceeded`。
2. **点密度与 `MESHGLAZ`**：`GEN` 分支不使用 `MESHGLAZ`，采样密度由点文件决定。
   默认 20×20（50 m）对应 50 m 研究网格；若要与全量数据在某个 `MESHGLAZ=N` 下
   的结果一致，用 `--mesh-cells N` 重新生成。
3. **`DNZGEN` 必须与文件头 datum 一致**：GENERIC 分支用 `DNZGEN`（而非文件头）
   解释点坐标（见 `ctgproc.for` 的 `call GLOBE(...,dnzgen,...)`）。
   裁剪件文件头为 `ESR-S`（GLCC 数据球面坐标），`auto_select_landuse_to_ctgproc.py`
   会自动同步 `DNZGEN`；手工编辑 `ctgproc.inp` 时不要漏掉这一项。
4. **50 m 网格 + 3 弧秒 DEM 会有大量地形空缺**：SRTM 3 弧秒像元约 85 m，
   50 m 网格单元只有约 35% 概率包含一个像元中心，
   实测 10000 个网格中 6544 格为空缺（`-999`），全量数据同样如此。
   需要 50 m 网格的完整地形时应改用 1 弧秒 DEM（本仓库未包含），或放宽网格间距。
5. 裁剪件只覆盖表中所列范围；把研究域移出该范围需按「生成方式」一节的命令用新的
   `--center-lat/--center-lon/--study-side-km/--tag` 再生成一份。

# 合肥周边六幅 SRTM 地形数据

## 来源与用途

2026-10-18 按项目所有者明确要求，从原 CTEAS 项目目录
`/Users/rain/Documents/Doctor/Topic/CTEAS/calpuff_terrain_and_landuse_data/china_srtm/`
逐文件复制以下六幅 TIFF，并通过 Git LFS 纳入本项目。源文件未修改，未重采样、拼接或裁剪。

这组数据用于准备以 **31.939774444°N、117.141610855°E** 为中心、边长 **600 km**（中心向各方向约 300 km）的地形输入。准备数量为 **六幅**，不能将前四幅视为已证明完整覆盖。

## 文件与空间范围

以下范围根据本次直接读取的 GeoTIFF 标签计算：

| 文件 | 经度范围 | 纬度范围 |
| --- | --- | --- |
| [srtm_59_06.tif](srtm_59_06.tif) | 110°E～115°E | 30°N～35°N |
| [srtm_59_07.tif](srtm_59_07.tif) | 110°E～115°E | 25°N～30°N |
| [srtm_60_06.tif](srtm_60_06.tif) | 115°E～120°E | 30°N～35°N |
| [srtm_60_07.tif](srtm_60_07.tif) | 115°E～120°E | 25°N～30°N |
| [srtm_61_06.tif](srtm_61_06.tif) | 120°E～125°E | 30°N～35°N |
| [srtm_61_07.tif](srtm_61_07.tif) | 120°E～125°E | 25°N～30°N |

六幅外边界合计覆盖 **110°E～125°E、25°N～35°N**。加入 61 列两幅是为了涵盖 120°E 以东的候选区域。

**600 km 正方形的精确经纬度边界取决于计算投影、网格朝向和原点。** 本次没有建立或运行新场址网格，因此上述是地形数据准备范围，不是对任意投影下 600 km 网格覆盖的验收。正式使用前应以生成的网格边界复核分幅覆盖，并检查 NoData。计算 UTM 原点须遵循项目三位小数 km（1 m）规定。

## 文件实测属性

六幅均为：

- GeoTIFF，**6000 × 6000** 像元，单波段。
- 16 位有符号整数（GeoTIFF SampleFormat=2、BitsPerSample=16）。
- 地理坐标系 **EPSG:4326 / WGS84**，RasterPixelIsArea。
- 角分辨率 **1/1200° = 3 角秒**；通常称约 90 m SRTM，地面东西向像元长度随纬度变化。
- 每幅 **72,096,675 字节**；六幅合计 **432,580,050 字节**（约 412.54 MiB）。

本次检查读取 TIFF/GeoTIFF 标签并对所有文件计算 SHA-256，未解码全部高程像元，未核验高程单位、垂直基准、NoData 分布、产品版本或官方发布校验值。不能单凭文件名确认具体 CGIAR 产品版本。

## 逐文件 SHA-256

源文件和副本已逐一比对，全部一致。

| 文件 | SHA-256 |
| --- | --- |
| `srtm_59_06.tif` | `b125fb513b951fcee4c78c8c94696eab9fea70808415565021f09945eed5f1bc` |
| `srtm_59_07.tif` | `f4e462c5d6019d3c5ced317c1db9bcd3252772878fd3493bf2c08ebfbf2054b1` |
| `srtm_60_06.tif` | `913a082c79df74ff4189fec9d94b678618b395a6fb0a64ee94e14c532362eae4` |
| `srtm_60_07.tif` | `5f159eea3fde8b085160f046572447941b1f1f55a1c4b1bb07c5780e81e82931` |
| `srtm_61_06.tif` | `99487ab48089698bc2087356221b6282ed33319674d2356b2f02e49e1f5473cf` |
| `srtm_61_07.tif` | `a0d97c11e2d53b8c78a05ac8488a6dadd603c27f32e32c493a7e08a928222acd` |

## Git LFS 下载与使用

安装 Git LFS 后，在仓库根目录执行：

```sh
git lfs install --local
git lfs pull --include="calpuff_terrain_and_landuse_data/china_srtm/*.tif"
shasum -a 256 calpuff_terrain_and_landuse_data/china_srtm/*.tif
```

约百字节的 LFS 指针文本不是地形栅格。下载后应按上表复核大小与哈希。本次仅纳入数据，不修改运行配置，不代表传统 TERREL 或 native P1 已完成这六幅数据的集成验收。

## 来源与分发边界

仓库原有 `docs/migration/THIRD_PARTY_ASSETS.md` 将 CGIAR/CIAT 地形列为外部依赖，并记录公开再分发授权尚未建立。本次所有者明确要求上传这六份本地文件，构成这一具体文件集合的仓库跟踪例外；这不构成第三方版权许可或已完成权利审查的证明，也不改变其他地形裁剪件及 vendor 源码的排除策略。后续使用及再分发应遵守实际来源对应的条款。

本次未运行地形预处理、模型或科学验证。

# eausgs2_0la.img 数据说明

这个文件是 **USGS 全球土地覆盖特征数据库（GLCC）2.0 的欧亚大陆土地利用分类数据，采用针对亚洲优化的 Lambert 方位等积投影，名义分辨率为 1 km**。它是 CTEAS 传统 CTGPROC 流程的 `GLAZAS` 土地利用输入。

## 1. 文件本身

| 项目 | 信息 |
| --- | --- |
| 文件 | `eausgs2_0la.img`（本项目根目录） |
| 实际大小 | **156,000,000 字节**，约 156 MB / 148.77 MiB |
| 栅格尺寸 | **13,000 列 × 12,000 行** |
| 像元总数 | 156,000,000 |
| 波段 | 单波段 |
| 数据类型 | 无符号 8 位整数，`uint8` |
| 存储形式 | **无文件头的原始二进制栅格**，每个像元占 1 字节 |
| 像元内容 | 土地覆盖类别编号 |
| 空间分辨率 | 1,000 m × 1,000 m |

文件大小恰好等于 `13000 × 12000 × 1`，与产品规格一致。但尚未与官方校验值比对，因此不能仅据此证明下载内容与官方发布文件完全一致。

**`.img` 在这里是裸栅格扩展名**，文件内部没有完整的投影、尺寸和分类说明。本次只复制了 `.img`，没有配套头文件，因此普通 GIS 软件不能仅靠这个文件自动识别空间位置。产品格式参考：[USGS 官方数据说明](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-land-cover-products-global-land-cover-characterization-glcc)。

## 2. 数据年代与含义

GLCC 主要基于 **1992 年 4 月至 1993 年 3 月的 1 km AVHRR 遥感资料**制作。`2_0` 表示产品修订版本，不能理解为 2000 年土地利用数据。官方网页的发布日期也不是影像观测年代。参考：[USGS 欧亚大陆技术说明](https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/atoms/files/EurasiaLandCoverCharacteristicsDataBaseReadmeVersion2.pdf)。

因此，这是一份代表**早期 1990 年代地表覆盖状况**的历史分类资料。对城市扩张明显的地区，用它描述近年的建成区、农田和水体分布会有时间差。

## 3. 投影和空间范围

| 参数 | 数值 |
| --- | --- |
| 投影 | Lambert Azimuthal Equal Area，Lambert 方位等积投影 |
| 中心经度 | 100°E |
| 中心纬度 | 45°N |
| 球体半径 | 6,370,997 m |
| 假东距 / 假北距 | 0 / 0 m |
| 坐标单位 | 米 |
| 左上像元中心 | X = −8,000,000；Y = 6,500,000 |
| 右下像元中心 | X = 4,999,000；Y = −5,499,000 |

上述为产品的**像元中心坐标**。据此推算，栅格外边界为：

```text
左：−8,000,500 m       右： 4,999,500 m
下：−5,499,500 m       上： 6,500,500 m
```

对应的 PROJ 表达式可写为：

```text
+proj=laea +lat_0=45 +lon_0=100 +x_0=0 +y_0=0 +a=6370997 +b=6370997 +units=m +no_defs
```

该坐标系采用球体模型。导入 GIS 时必须正确指定它，再按需转换到 WGS84。矩形数据框还包含外围填充值，不能把整个矩形都理解为有效欧亚大陆覆盖区。参考：[官方投影参数](https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/atoms/files/EurasiaLandCoverCharacteristicsDataBaseReadmeVersion2.pdf)。

## 4. 土地利用分类

该文件使用 **USGS Land Use/Land Cover，Modified Level 2 的 24 类体系**。像元存的是下表的整数；这些整数是类别标签，不能当连续数值求平均。参考：[官方分类图例](https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/atoms/files/EurasiaLandCoverCharacteristicsDataBaseReadmeVersion2.pdf)。

| 像元值 | 类别 | 像元值 | 类别 |
| --- | --- | --- | --- |
| 1 | 城市和建成区 | 13 | 常绿阔叶林 |
| 2 | 旱地农田和牧草地 | 14 | 常绿针叶林 |
| 3 | 灌溉农田和牧草地 | 15 | 混交林 |
| 4 | 旱地／灌溉混合农田和牧草地 | 16 | 水体 |
| 5 | 农田／草地镶嵌 | 17 | 草本湿地 |
| 6 | 农田／林地镶嵌 | 18 | 林木湿地 |
| 7 | 草地 | 19 | 裸地或稀疏植被 |
| 8 | 灌丛 | 20 | 草本苔原 |
| 9 | 灌丛／草地混合 | 21 | 林木苔原 |
| 10 | 稀树草原 | 22 | 混合苔原 |
| 11 | 落叶阔叶林 | 23 | 裸地苔原 |
| 12 | 落叶针叶林 | 24 | 积雪或冰 |

## 5. 本地文件的实际统计

2026-10-18 完整扫描副本的所有字节，得到：

| 检查项 | 结果 |
| --- | --- |
| 实际出现的值 | 0，以及 1–24 中除 4、20 外的类别 |
| 非零类别数 | 22 类 |
| 值为 0 的像元 | 50,132,049，约 **32.14%** |
| 值为 16（水体）的像元 | 55,301,841，约 **35.45%** |
| 值为 1（建成区）的像元 | 136,409，约 **0.087%** |
| 超过 24 的异常值 | 未发现 |

其中 **0 不在上述 24 类图例内，应作为背景／无分类值处理**；它与水体类别 16 必须分开。上述百分比以整个矩形文件为分母，包含外围背景和大量水域，不能作为中国或某个研究区的土地利用比例。

文件的 SHA-256 为：

```text
4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a
```

## 6. 在 CTEAS 项目中的使用

以下使用说明来自用户提供的原 CTEAS 项目核对记录；本次未重新审计源码，也未执行 CTGPROC 或 native P2 验收。

原项目的 [CTGPROC 源码](/Users/rain/Documents/Doctor/Topic/CTEAS/engine/vendor/src/CTGPROC_v7.0.0_L150211/ctgproc.for:1882)硬编码了这份亚洲栅格的尺寸、原点和格距。处理流程为：

```text
原始 24 类栅格 → CTGPROC 类别转换与网格统计 → 后续地表参数处理
```

- **原始类别号和 CTGPROC 内部类别号不同。** 例如原始 `16` 是水体，经原项目转换表映射为 `52`。
- **不能把裁小后的二进制文件继续交给 `GLAZAS` 读取。** 它仍会按完整的 13,000 × 12,000 布局寻址。原项目的[裁剪脚本](/Users/rain/Documents/Doctor/Topic/CTEAS/scripts/crop_terrain_landuse_data.py:27)通过 `GENERIC.LANDUSE 1.0` 点文件输入裁剪区域，并同步球面 datum `ESR-S`。
- 脚本中的 50 m 细分点只是对原有 1 km 像元进行取样，**不会增加土地利用信息的真实分辨率**。
- 本项目是选定路径的部分 C++20 重构。将数据放到根目录本身不代表 native P2 已接入此文件，也不改变现有配置或科学验收范围。

主要限制是数据年代较早、1 km 像元难以刻画厂区及城市细节，以及用户提供的产品说明指出 GLCC 2.0 尚未完成正式精度评估。它适合复现既有 CALPUFF 数据流程；用于现代场址评价时，应另外核对研究区的现实地表状况。参考：[USGS 版本与精度说明](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-land-cover-products-global-land-cover-characterization-glcc)。

## 7. 本次复制与验证记录

- 日期：2026-10-18。
- 来源：`/Users/rain/Documents/Doctor/Topic/CTEAS/calpuff_terrain_and_landuse_data/eurasia_asia_landuse/eausgs2_0la.img`。
- 目标：本项目根目录 `eausgs2_0la.img`。
- 已实测：源文件与副本 SHA-256 相同；副本大小及完整类别统计与上文一致。
- 产品年代、投影、分类与原项目读取流程依据用户提供的说明保留；本次未重新联网核对官方文档，未验证官方校验值。
- 本次复制数据并新建说明，未修改源数据，未运行模型。按用户要求，数据副本通过 Git LFS 跟踪并上传远端。

## 8. Git LFS 获取方式

该文件为 156,000,000 字节，使用 Git LFS 保存。首次克隆前安装 Git LFS；已有克隆可执行：

```sh
git lfs install --local
git lfs pull --include="eausgs2_0la.img"
shasum -a 256 eausgs2_0la.img
```

若只得到约百字节的文本指针，表示 LFS 数据尚未下载，不能作为栅格输入。下载后应核对本说明记录的大小和 SHA-256。

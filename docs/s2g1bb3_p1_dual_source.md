# CTEAS-next P1：双地形数据入口（源码输入阶段）

P1 固定保留 **两条互斥入口**；二者最终统一为经完整性检查的 **WGS84 EPSG:4326、单波段 Int16、带 NoData 的 GeoTIFF**。第三条默认回退、假地形、自动改变数据源均不允许。

1. **用户本地 TIFF**：`--local --tif a.tif --tif b.tif ...`，或 `--local --tif-dir /data/srtm/`（扫描 .tif/.tiff）。**只指定一个**覆盖全计算域的 GeoTIFF 时，直接读取原文件、不产生裁剪副本。多个文件要求投影、Int16 类型、像元分辨率、像元格网对齐、NoData 值兼容；在隔离输出目录合并为 `p1_local_mosaic.tif`，仅保留当前计算域加缓冲的范围。重叠区若像元高程不一致即阻断；缺测、覆盖不足、文件损坏或坐标不一致即报错，不进行默默插值或假补齐。
2. **OpenTopography 原生 SRTM 30 m / 90 m**：`--opentopography --dem SRTMGL1`（1 弧秒，约 30 m）或 `--opentopography --dem SRTMGL3`（3 弧秒，约 90 m）。同一 `grid.cmn` 推导带 500 m 缓冲的 WGS84 bbox，调用官方 `GET https://portal.opentopography.org/API/globaldem`，`outputFormat=GTiff`；原有 `--opentopography` 不带 `--dem` 时仍默认 SRTMGL1，以保持旧案例兼容。API Key 从环境变量 **`OPENTOPOGRAPHY_API_KEY`** 读取，不进入日志/请求 URL 输出/仓库。两者是用户明确指定的**同一自动下载入口的两种产品**；API 失败不得静默从 30 m 切换到 90 m，或从 90 m 切换到 30 m，也不能换 NASADEM/CGIAR。若用户显式允许 406 公共 S3 备用通道，只恢复同一个所选产品。

源入口：`scripts/s2g/p1_terrain_source.py`。

```bash
# 入口 A：用户指定多份 TIFF，可以重复传 --tif
python3 -m scripts.s2g.p1_terrain_source \
  --grid /scratch/case/grid/grid.cmn \
  --local \
  --tif /data/srtm/tile01.tif \
  --tif /data/srtm/tile02.tif \
  --out-dir /scratch/case/p1_terrain_source

# 入口 A：整目录本地多 TIFF
python3 -m scripts.s2g.p1_terrain_source \
  --grid /scratch/case/grid/grid.cmn \
  --local --tif-dir /data/srtm \
  --out-dir /scratch/case/p1_terrain_source

# 入口 B1：OpenTopography SRTMGL1 30 m（--dem 省略时默认此项）
# 在本地通过受保护的环境变量配置 key；GitHub Actions 使用 repository secret
python3 -m scripts.s2g.p1_terrain_source \
  --grid /scratch/case/grid/grid.cmn \
  --opentopography --dem SRTMGL1 \
  --out-dir /scratch/case/p1_source_30m

# 入口 B2：同一自动下载入口，原生 SRTMGL3 90 m
python3 -m scripts.s2g.p1_terrain_source \
  --grid /scratch/case/grid/grid.cmn \
  --opentopography --dem SRTMGL3 \
  --out-dir /scratch/case/p1_source_90m
```

**输出**：`p1_source_manifest.json`，包含原始文件列表、SHA256、坐标/分辨率、缓冲 bbox、NoData 和有效像元计数、最终交付 TIFF 路径及 SHA。单文件不会复制原文件；本地多文件按需合并。API 模式分别保存 `srtmgl1_30m.tif` 或 `srtmgl3_90m.tif`，记录实际所选数据产品及请求弧秒数，但不会保存完整请求 URL 或密钥。

**严格规则**：任何入口均需真正覆盖 `grid.cmn` 的计算域及默认 500 m 缓冲；默认发现 NoData 即阻断，可显式加 `--allow-nodata` 继续进入待处理数据源阶段，但必须在后续 P1 科学验收中说明 void、水域与高程缺测策略；不实施秘密的 void fill。新场址若在 SRTM 约 56°S—60°N 以外则阻断 API 入口。OpenTopography 官方 SRTMGL1 30 m 查询面积上限 **450,000 km²**，SRTMGL3 90 m 为 **4,050,000 km²**；两者均受实际像元数/下载字节/备用下载最多9个瓦片的更严格预算约束，本阶段也配置保守的内存/下载上限，超限返回错误而不是静默拆分或截断。多场址/大区域将另行增加可审核分片下载功能。

**验收边界**：这只是 **P1 地形文件输入层**。当前 `native_cpp/src/p1_terrain_cli.cpp` 仍是冻结合肥 **UTM50N、50×50@100m、单 TIFF** 数值内核。多 TIFF 已在输入层合并为原生 P1 将来可以读取的单 TIFF，**尚未执行新场址 P1 数值计算、原版 TERREL 对照或 P3 GEO.DAT**。在这些独立验收前，状态为 `P1_TERRAIN_SOURCE_VERIFIED_NATIVE_NUMERICS_NOT_RUN`，不得标称 P1 完整重构。

**测试策略**：普通 PR CI 仅运行本地**合成 GeoTIFF**和模拟下载接口的 Python 测试，不使用真实 API Key，也不触发 P6/P7。既有真实 SRTMGL1 下载工作流 `.github/workflows/s2g1bb3-p1-dual-source.yml` 仍按原有 `workflow_dispatch` 手动触发；新增 SRTMGL3 仅加入离线软件测试，真实下载与独立原版比对须另行手动验收，使用 `secrets.OPENTOPOGRAPHY_API_KEY`，在非合肥 NOAA 测试域运行，并仅上传**无密钥的 SHA 元数据**。API 使用政策、速率限制、最大面积以官方 [OpenTopography Developers](https://opentopography.org/developers) 为准。SRTMGL1 30 m、NASA SRTMGL3 90 m 与老合肥 CGIAR-CSI 90 m 并非同一个数值基准，不能相互冒充；冻结合肥历史结果不改。

后续事项：[G1B-B3 Issue #46](https://github.com/RRain001/CTEAS-next/issues/46)：将动态 UTM `grid.cmn` 注入原生 C++ P1 数值内核，并对来自 A/B 的真实高程逐格进行 TERREL 数值对照，之后才允许接入 P3 `GEO.DAT`。

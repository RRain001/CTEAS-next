# #54 P1 双路线案例参数化：本地 SRTM90m 多TIFF / 自动获取 SRTM30m

来源：https://github.com/RRain001/CTEAS-next/issues/54
抓取日期：2026-10-18；远端更新时间：2026-10-18T07:57:31Z

## 用户确认：本Issue仅做P1两数据路线的**案例参数化**（2026-10-18）
沿用P1目前已选定的**地形采样/数值统计方法**；只解除“合肥50×50@100m、UTM50N、固定原点、固定数据路径”软件限制，让可配置研究范围、UTM/三位小数km原点、NX/NY/DGRIDKM及用户指定数据路径驱动同一原生内核。数据仅两入口：A本地用户指定**多张SRTM 90m TIFF**（复用已合并PR #49）；B按场址下载/缓存**SRTMGL1 30m TIFF**（仍复用PR #49）。两入口允许因数据分辨率不同产生不同TERREL，但不得随意改动高程统计方法来伪造“通用”。**不要求新增其他DEM产品、插值选项、非选定原版P1物理分支**。烟囱/源项、研究时段属于案例配置；P1只取地形所需空间网格信息，源项排放率变化不影响P1计算。

## 定位、上游成果与职责
本 Issue 是 **P1 原生 C++ 数值处理 + 两种 SRTM 地形输入路线的独立验收**，是 [#46](https://github.com/RRain001/CTEAS-next/issues/46) 的前置任务；[#46] 只负责通用 P3 和真正新场址 P1/P2/P3 联合执行，**不要在两处重复实现 P1 内核**。P2 的两条土地利用路线由 [#53](https://github.com/RRain001/CTEAS-next/issues/53) 负责。

**已完成的输入层不要重新开发**：[PR #49](https://github.com/RRain001/CTEAS-next/pull/49) 已合并 `scripts/s2g/p1_terrain_source.py`、`docs/s2g1bb3_p1_dual_source.md` 和合成数据测试。已有 `--local --tif ...` / `--tif-dir ...` 以及 `--opentopography`，目前都输出经审计的 WGS84 单波段 Int16 GeoTIFF + `p1_source_manifest.json`。此阶段是 **PASS_SCOPED_SOURCE_ADAPTER**，不代表新网格 P1 物理数值 PASS。当前 `native_cpp/src/p1_terrain_cli.cpp` 仍只支持 Hefei UTM50N、50×50@100m、单 TIFF；通用化、数值验收均未完成。

## 用户确认的 P1 两条且仅两条地形路线

### P1-A：用户指定目录/路径，读取 **SRTM 90 m** 多张 GeoTIFF
- 用户通过 `--tif /path/tile1.tif --tif /path/tile2.tif ...` 或 `--tif-dir /path` 自行提供有再使用权的真实 **SRTM 3 arc-second（中低纬约90m）** 地形，重点复用当前仓库已有的 `srtm_*.tif`/用户服务器存储；程序不得自行改数据源或自动把缺失文件换成30m。
- **产品版本须明确并记录**：历史合肥使用 CGIAR-CSI SRTM v4.x ~90m；CGIAR、NASA SRTMGL3、其他填洼/高程基准不可默认视为同一产品。地理坐标中的3角秒不等于全球恒定90.000m；检验实际 CRS、像元尺寸、格网对齐、垂直单位/基准、NoData、来源、SHA。
- 直接复用 PR #49 的多 TIFF 处理（无重采样的兼容文件拼接；交叠不一致时报错，缺测/覆盖不足不得静默修补；单文件可直接用）。应允许任意**用户指定且有实际文件**的目录路径，不能写死合肥路径或强迫把用户文件提交 GitHub。
- 合法受许可限制的 CGIAR 地形**只从用户授权服务器/受保护数据卷挂载**，不用公开仓库或 Actions artifact 再发布未经授权的二进制数据。
- 使用相同原始 SRTM90m 输入与原版 TERREL 数值对照；保留冻结合肥 CGIAR 90m 科学回归以及已有 P1 检查；若没有原版独立运行，严守 `NOT_ACCEPTED` 门槛。

### P1-B：按研究区自动下载 **SRTM 30 m** GeoTIFF
- 直接复用 PR #49 的 `--opentopography` 入口（OpenTopography `demtype=SRTMGL1`，名义1 arc-second/约30m，`grid.cmn`+500m安全缓冲推导WGS84 bbox）；不重写新的 API 下载程序。
- `OPENTOPOGRAPHY_API_KEY` 仅来自环境变量/受保护 secrets，不得泄露 URL、key、下载时令牌、响应正文；Docker 运行可以使用持久化数据卷和已下载 TIFF。禁止静默转成SRTM90m、其他DEM或伪造海拔。SRTM 原始覆盖纬度约56S–60N，超出范围、API配额/速率/面积失败需明确报错。
- **分离 API 源获取验收和 P1 数值验收**：真实下载可在用户环境或现有手动 `workflow_dispatch` 下载任务进行（按现有安全策略），但原生 P1 的纯离线测试**必须可用已经缓存的 TIFF / 合成 fixture 完成**，不要求每次 Actions 连网或配置API密钥；当前没有经证明的 SRTM30m 真数据时不能冒称真实下载/30m 物理验收通过。
- 用同源30m TIFF 做原版与原生 P1 对照；**禁止**要求用30m结果逐像元复现历史90m的 TERRAIN/TERREL 值。可报告两套地形的差异及对 P3 地表高度的影响，注明物理数据源不同。

## P1 原生 C++ 实现契约
- 两条路线在 source admission 后共享 **一个明确的 GeoTIFF→P1 数值内核**，读 `grid.cmn`（WGS84/UTM，动态UTM分区/半球与NX/NY/DGRIDKM，`XREFKM/YREFKM`严格3位小数 km）和选定的 TIFF，输出各格点高程/有效点数/NoData/覆盖统计，生成可供 [#46] 通用 P3 使用的中间层或标准 `TERREL.DAT` 契约。严格控制坐标、像元中心/网格原点、原版采样/插值/平均、边界规则、输出顺序与F8.1精度；确定数字回归差异须能独立解释。
- 尽量复用 `native_cpp/src/geo/terrain.cpp`、`native_cpp/src/p1_terrain_cli.cpp` 和现有 GDAL 工具；新增通用 CLI 不能破坏冻结 Hefei 旧入口。输入检查保持单波段Int16/WGS84/明确NoData约束，除非提出证据充分的新格式支持；禁止随意以 bilinear 代替经核验的原版高程统计算法。
- **本 Issue 不实现 P2 土地利用、不负责 P3 参数计算或 GEO.DAT 最终联合生成**；两路线只到达统一、可审查的 P1 输出数据契约。与 #46 协作确定动态网格的 `TERREL.DAT` I/O 和 provenance 格式。

## 开发分阶段与验收
- [ ] **P1-D0 设计审计**：盘点 #49 source 输入、原版 TERREL 和现有 P1 hard-code，列出两路线 P1-A(本地90m)/P1-B(API30m)、统一内核、IO 和真实/模拟测试矩阵。提交 Draft PR 或 design docs，先交 ChatGPT 审核，避免未经审计的物理改写。
- [ ] **P1-D1 动态网格内核**：支持任意经审查的 WGS84 UTM `grid.cmn`，保留老 Hefei 回归；只产出原生 P1 高程字段/TERREL契约。
- [ ] **P1-D2 本地90m多文件端到端**：用用户提供/授权的多张同源 SRTM90m TIFF 跑原生 P1，逐格与独立原版同源 TERREL 比较，覆盖重叠、边缘与NoData负向测试。没有真实可读文件时标 `BLOCKED_REAL_ASSETS`，不得用 mock 当真实。
- [ ] **P1-D3 下载30m输入的离线 P1 物理验收**：使用事先由 #49 入口或用户本地获取的真实 SRTMGL1 GeoTIFF，离线跑原生 P1 和同源原版对照；没有真实下载时标 `P1_B_REAL_SOURCE_NOT_RUN`，不可拿模拟下载代替。
- [ ] **P1-D4 双路线独立审计报告**：区分 `P1_A_90M_LOCAL`、`P1_B_30M_DOWNLOAD` 的数据获取、物理字段、同源原版数值比对、缺测和许可、Sci gate；输出可交 #46 的 P1 契约和来源元数据。两路线的物理验收不能相互替代。

## CI、Docker 与权限
- 普通 GitHub PR CI 只跑小规模 C++ / 合成 GeoTIFF 离线测试；真实API下载不得在普通PR CI自动运行。**全部科学重放/大数据测试仅由明确的 `workflow_dispatch` 手动触发**，尊重仓库现有策略。
- P1-A 本地路径与 Docker volume 要可配置；P1-B 下载凭据始终与模型运行分离，下载完的数据应可复制、缓存、离线复用；两种数据同场址必须留清楚版本/高程基准，不可暗中切换。
- 不改变 #49 已接受的 source-only 结论，不改历史 SRTM90m/CALMET 科学基准，不新增第三条默认数据路线；尚未做的更大范围、不同DEM产品需另行科学审查。

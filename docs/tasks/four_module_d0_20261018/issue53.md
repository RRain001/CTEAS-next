# #53 P2 双路线案例参数化：GLCC 1km 直读 / GLC_FCS30D 30m 离线读取

来源：https://github.com/RRain001/CTEAS-next/issues/53
抓取日期：2026-10-18；远端更新时间：2026-10-18T07:57:28Z

## 用户确认：本Issue仅做P2两数据路线的**案例参数化**（2026-10-18）
P2的既有**选定处理方法及输出原版LU合同保持不变**；仅允许更换研究区/格网原点、UTM、NX/NY/DGRIDKM及源数据目录，不再限定合肥50×50@100m。两个**已确定的数据源入口**：A原始欧亚GLCC 1km直读且保持原版CTGPROC同源数值规则；B读取Mac脚本已下载并合并[#52](https://github.com/RRain001/CTEAS-next/pull/52)的GLC_FCS30D 30m真实GeoTIFF并正确计算土地类别面积比例和映射。B的类别映射必须有来源审查，但**不要求新增别的CTGPROC原版物理算法、土地利用数据产品或重做GEE下载器**。P3/MAKEGEO公式由[#46](https://github.com/RRain001/CTEAS-next/issues/46)保持原选定方法。研究时间、排放率不是P2的土地覆盖计算输入，不因源项改变而重算或更换分类方法；仅在案例元数据中传递需要的烟囱坐标。

## 独立职责（2026-10-18 去重修订）
**本 Issue #53 仅负责原生 C++ P2 的两条土地覆盖数据读取、原始类别/面积比例计算、分类映射审计，以及统一的 P2→P3 输出接口。**

- **P1 两条地形路线及 P1 原生高程计算**统一由 [#54](https://github.com/RRain001/CTEAS-next/issues/54) 负责。
- **P3 任意网格通用化、MAKEGEO 地表参数计算、最终 `GEO.DAT` 输出以及真实新场址 P1/P2/P3 联合科学验收**均由 [#46](https://github.com/RRain001/CTEAS-next/issues/46) 负责，#53 **不另行重构 P3、也不重复实现 `GEO.DAT` 生产器**。
- 上层集成：[ #46 → #42 → #40 → #36 ]。Codex 对 P2 只执行本 Issue，不应在 #46 平行另起 P2 代码。
- 来源获取层已完成：[PR #48](https://github.com/RRain001/CTEAS-next/pull/48) 提供 GLCC Python source-only 提取，[PR #52](https://github.com/RRain001/CTEAS-next/pull/52) 提供 GLC_FCS30D 2022 下载/真实 GeoTIFF/本地验证。**不要重新开发或再次运行 GLC 的 Earth Engine 下载任务**。

## P2-A：GLCC 1 km 欧亚原始裸栅格直读（历史同源等价）
- 输入 Git LFS `eausgs2_0la.img`，156,000,000 bytes，13000×12000 `uint8` **headerless**，原始24类，0=背景/无分类；历史1992–1993年。SHA256 `4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a`。投影与像元中心位置参照 `eausgs2_0la.md`：Lambert 方位等积球面 `a=b=6370997`、中心经度100纬度45、1km格网。不得当普通GeoTIFF读或误将0当水体。
- **由 C++ 直接读取原始 .img 研究区像元**，不必先运行 Python GEN 提取；保留已存在的 `scripts/s2g/real_glcc_landuse_from_grid.py`/GEN 路径作独立对照。GLCC原始24类→历史USGS-92 38类的映射与CTGPROC空间采样/Fortran REAL*4 边界必须有出处且在同源对照中复现，不可任意替换为面积相交算法造成虚假“原版等价”。
- 支持由 `grid.cmn` 决定的WGS84 UTM分区/半球、动态NX/NY/步长、3位小数km精度原点；冻结合肥50×50@100m回归不得破坏。
- 验收：同源 `LU.DAT` 38类、2500格、原版显示精度预声明绝对容差≤0.0005及原始点数检查；若未实际读取156MB真实LFS则只能 `PASS_SOFTWARE`，不能宣称 `PASS_REAL_GLCC`。原版比对需独立资料/运行证据。

## P2-B：GLC_FCS30D 2022 30 m 离线GeoTIFF
- **输入直接固定为已提交的真实数据**：`data/landcover/glc_fcs30d/v1_2022/hefei/hefei_2022_30m.tif`，EPSG:32650、172×172、30m、12个实际类别、NoData/fill 0%，SHA256 `340d224d961c88637363be9616302bdf6b955b4921144edc814b875ef9798473`。source/许可/日期/类别直方图详见同目录 `metadata.json` 与 `ATTRIBUTION.md`。
- **本地数据获取已验收：所有本 Issue 的开发、Docker、GitHub Actions 单元测试均只读取此文件，不调用 Earth Engine、不需 Google OAuth/OIDC 或 Secrets。**
- C++/GDAL 校验单波段整数分类、GeoTIFF投影/变换、栅格覆盖、mask/NoData、合法35类编码、数据SHA、混合水陆处理。GLC 35类标签绝对不能直接视为GLCC/USGS 38类。
- 对每个 CALMET 模型网格，用同一平面坐标系的真实矩形/多边形**面积相交**计算 `f[k]=Σarea(cell∩pixel_k)/Σarea(valid cell∩pixels)`；30m对100m非整除，不得用像元中心次数直接充当面积比例，不得对分类码做双线性插值。严审边界零碎像元、混合区、水体分界、NoData、未覆盖区域以及面积守恒/总和为1。保留每个网格的原始GLC类面积比例与有效覆盖量。
- 把GLC分类映射到历史MAKEGEO输入体系前，先提交**有证据和物理理由的35类候选映射表**及此次出现的12类逐项检视；湿地、建成区、镶嵌等歧义标记 `P2_MAPPING_REVIEW_REQUIRED`，等待 ChatGPT 科学审查。不可伪装成已接受参数。记录原始比例、映射后比例、丢失/合并信息和数据源变化。

## 统一 P2 交付契约，供 #46 的 P3 使用
- 两路线均输出标准字段/类序/网格坐标/面积或点数统计、来源及SHA的 **P2 fractions contract**，可转换到已审计 `LU.DAT` v2.1 输入格式（或经双方批准的等价合同），并保留原始数据源类别分布以供复核。
- 必须分别保留 `P2_A_GLCC` 和 `P2_B_GLC_FCS30D` 两组证据及状态，不要求1990年代1km与2022年30m结果数值相等；`P3` 的历史参数规则/38→14类表由 #46 自己验收，不要在 #53 产生第二个P3实现。
- 不修改原版GLCC文件、合肥冻结源案例、已合并PR #48/#52的下载器，也不碰P6/P7物理代码。

## 执行顺序与停止关卡
1. [ ] **P2-D0 设计及映射审计**：给出两源CLI/API、统一fractions/类别与映射方案、源投影/边界/数值方法、P3所需契约，创建 Draft PR 标记 `P2_MAPPING_REVIEW_REQUIRED` 供 ChatGPT 审核（先不要自行批准歧义映射）。
2. [ ] **P2-D1 GLCC .img 原生直读**：复用现有GEN提取结果作独立对照，真实LFS验收与synthetic分开。
3. [ ] **P2-D2 GLC GeoTIFF 面积相交**：完全离线用已提交的真实30m测试文件 + 合成边界/mask fixture 验证面积占比、守恒及负向测试。
4. [ ] **P2-D3 交付统一 P2 fractions→LU.DAT 接口**：依据获审映射输出类别比例、header/行序、SHA与源元数据；**到此停止，不在本Issue开发通用P3或生产最终GEO.DAT**；移交 #46。
5. [ ] 提交两路线的来源、真实/合成数据门槛、误差、许可和耗时报告。不要把 `PASS_SOURCE` 冒充 `PASS_SCIENCE`。

## CI 和Docker
- 轻量、无凭据的C++/Python离线单测可以在正常PR中运行；任何完整科学重验/真实156MB Git LFS场景/跨模块长时测试只能通过明确授权的 `workflow_dispatch` 手动触发。LFS pointer或缺少真实文件时 fail closed，不能把 synthetic 写成真数据验收。
- Docker仅需要挂载真实源文件或读取镜像外的数据缓存；在模型计算阶段禁止自动联网下载。

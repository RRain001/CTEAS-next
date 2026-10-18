# #56 P5 SMERGE 案例参数化：沿用既定 ISD/ISD-Lite→SURF.DAT 流程

来源：https://github.com/RRain001/CTEAS-next/issues/56
抓取日期：2026-10-18；远端更新时间：2026-10-18T07:57:36Z

## 用户澄清：P5 只做案例参数化，不扩 SMERGE 算法（2026-10-18）
**保持选定 NOAA ISD/ISD-Lite→既有风/非风清洗填补→C++ SMERGE→SURF.DAT 处理路径不变**，包括 JDAT=8 / IOFORM=2 / IOPACK=0 / LPREV=F / LPCALC=F / UTC、年度主辅站选择、原始覆盖/缺测/静风及风向插值规则。这里只解决用户修改研究区域/烟囱中心后的既有算法自动选站、新`grid.cmn`对应源位置和站点索引、研究起止时段（包括跨年）、场址隔离输入输出目录、原版兼容SURF.DAT与元数据。**不要求新增站点选择策略、NOAA产品、气象插值分支、其他SMERGE控制选项**。已有多站多年的C++处理不重写；不得写死Hefei、固定站点、2022/2023或六月24h验收窗口；P5不因源项排放率变化重算气象数据。

## 专项职责：P5 SMERGE 通用化（2026-10-18）
父任务 [#42](https://github.com/RRain001/CTEAS-next/issues/42) 的 **P5 独占开发入口**。P1[#54](https://github.com/RRain001/CTEAS-next/issues/54)、P2[#53](https://github.com/RRain001/CTEAS-next/issues/53)、P3[#46](https://github.com/RRain001/CTEAS-next/issues/46)、P4[#55](https://github.com/RRain001/CTEAS-next/issues/55)。本Issue不重复 P1–P4 的原生开发，也不把 G19/P6 拿来作为P5代码职责。

### 已有成果，必须继承
- `native_cpp/modules/p5_smerge/p5_surf_main.cpp` 是独立 C++20 `SMERGE` 原版兼容 `SURF.DAT` 写入器，已有独立原版比较限定于 **JDAT=8, IOFORM=2, IOPACK=0, LPREV=F, LPCALC=F, UTC** 路径；已有原生多站/跨年 17,519h 原版字节等价报告，参见 `docs/reconstruction_cpp/P5_SMERGE_IMPLEMENTATION_STATUS.md`。多站解析、逐小时拼接和气象缺测规则已实现，不重写为平行第二套。
- `native_cpp/modules/p5_smerge/data_prep/` 已实现NOAA **ISD完整非风要素+ISD-Lite风** 双源读取、逐年原始UTC观测覆盖检验、多个域内站、主站/稀疏辅站及无域内站虚拟站选择，风向环形插值/静风与缺测持有逻辑；多站情况下主站按原始ISD-Lite覆盖率决定并逐年重选。0域内：最近一个原ISD和Lite原始coverage均严格**>90%**；站点原始位置与虚拟生效位置分开保存，站点名/IFSTN跨年稳定。已通过的科学算法不得擅自改变。
- [PR #47](https://github.com/RRain001/CTEAS-next/pull/47) 已在真实Huosh​an/Luogang 2022/2023 NO​AA数据上生成非合肥站的原生 `SURF.DAT` 并单独通过独立C++ P6源读取，**仅source/input scoped**；`scripts/s2g/real_noaa_native_p5_surf.py` 对两站/六月24小时场景冻结，不是通用新场址调度器。
- 目前 `data_prep/prepare_inputs.py` 及若干脚本仍依赖 `project/current` 与默认全局路径；多站写出器不等于任意场址一键执行已验收。

### 待做 P5 通用化与数值科学关卡
- [ ] **P5-D0 代码审计/接口设计**：盘点所有 `current_project_path`、冻结场址/日期/站点数、研究时段、控制文件格式及P6 G19数据契约；Draft PR先交独立审查。
- [ ] **P5-D1 独立工作空间**：接受明确 `case.yaml/grid.cmn/research_time`、可配置数据输入及输出目录、原始NOAA/归档文件；动态执行已有逐年选站+原始ISD+Lite准备+GENERIC输入+原生C++ SMERGE `SURF.DAT`，禁止覆盖 `project/current`、冻结合肥结果或其他场址，不为方便改写旧选站规则。
- [ ] **P5-D2 动态站点/跨年与缺测**：0/1/N 域内地面站、至少一有效外部候选时允许一虚拟站；不设人为最大固定站点数（以原SMERGE格式、内存和受支持路径为界）；验证跨年、闰年、全小时区间、主辅站切换、站点ID/IFSTN映射、ISD与Lite年度源覆盖、前值持有/静风/缺测等既有策略的合法运行。对无合格站、无真实数据、跨年身份冲突、时间不完整严格fail-closed。
- [ ] **P5-D3 原版同源对照**：复用已完成Hefei 2022/2023参考及PR #47的真正非合肥源；基于同一 `SMERGE.INP` 和同一逐时GENERIC输入与独立原版 SMERGE `SURF.DAT` 按记录精度/字节对照，重点真实多站、不同采样时段、非固定网格和年度名单；不能仅用2站2年已通过例子代替全场址通用验收。仅选定JDAT8 IOFORM2等原版参数分支得到科学声明。
- [ ] **P5-D4 交付P5→#42合同**：每站 source/effective坐标、年度coverage、primary/aux/virtual角色、IFSTN稳定编号、来源SHA、逐时有效覆盖及缺失统计、原版兼容 `SURF.DAT` SHA、对应动态 `met.inp` 所需索引。父任务#42独立组装P1–P5与G19输入校验；P6风场逐时计算由#40执行。

### 约束/验收报告
- 不能把历史 `PASS_REAL_NOAA_TWO_STATION_TWO_YEAR_BYTE_PARITY` 误说是新通用执行入口所有场址皆PASS；另列 `P5_SOURCE_SELECTION`、`P5_NATIVE_SURF`、`P5_GENERIC_CASE_EXECUTION`、`P5_ORIGINAL_PARITY` 和 `P5_TO_G19`。
- 普通PR CI仅用已有真实档案/小合成fixture离线测试；新NOAA联网和真正多年原版对照仅明确的手动 `workflow_dispatch`。不在CI为证明通用性而随意改数据、造第二站或将风向插值规则简化为算术均值。
- 不扩大到SMERGE其他JDAT、IOFORM、时区、打包等没有同源独立验收的原版选项；这属于未来物理选项矩阵。

依赖：`#55(P4) ∥ #56(P5) ∥ #54(P1) ∥ #53(P2) ∥ #46(P3) → #42(P1–P5通用新场址输入联合) → #40(P6科学) → #36(总)`。

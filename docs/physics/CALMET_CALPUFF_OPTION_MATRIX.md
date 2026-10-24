# CALMET/CALPUFF 原版物理选项矩阵（初版，源头可追溯）

> **性质：范围台账，而非通用物理验收证书。** 冻结输入版本为原 `RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13`；本矩阵依据该提交的原版控制卡、`CTEAS-next` 2022 合肥冻结案例、C++ 文件和已有 P6/P7 审计记录建立。当前源树为 `CTEAS-next`，但**矩阵不声明此次提交已经重新运行任何科学计算**。更新日：2026-10-17。

**原版源码在哪里：** [固定版本 CALMET 6.5.0](https://github.com/RRain001/CTEAS/blob/dfad99a78ed84d655e21411c9d25eb0d2583bf13/engine/vendor/src/CALMET_v6.5.0_L150223)（`calmet.for`、`calmet.inp`）与 [固定版本 CALPUFF 7.2.1](https://github.com/RRain001/CTEAS/blob/dfad99a78ed84d655e21411c9d25eb0d2583bf13/engine/vendor/src/CALPUFF_v7.2.1_L150618)（`calpuff.for`、`calpuff.inp`）。原版路径在 **CTEAS** 而非 CTEAS-next。读取、定位与恢复方法见 [VENDOR_SOURCE_LOCATOR.md](VENDOR_SOURCE_LOCATOR.md)；不复制第三方源码或 SRTM 裁剪。

## 范围和状态口径

- 每行控制值来自 **2022 合肥冻结案例** `project/cases/hefei5km_2022_reference_case_20261011/run/{met/met.inp,puff/puff.inp}`，**不把这些值视为 CALMET/CALPUFF 原版软件的全部默认选择**。
- **已选分支**：C++ 存在与该物理分支相关的实现，并有原 CTEAS 限定案例/组件级历史审计；**不能推导它对所有设置通用，亦不等同于新仓库 C1/C2 已 PASS**。
- **组件/控制**：能解析、审计或计算一部分公式，但并非已确认通用运行路径。**当前案例未激活**：选项可能被读取但未经过真实激活后的科学等价性验收；不等于原版没有实现，也不等于 C++ 缺少任何相关组件。
- 原版 `fortran_entry` 是**定位线索而非自动提取的完整调用图**；表中标注“入口待源审”时不得据此编写无核验的对应代码。需要以锁定 `calmet.for/calpuff.for` 原文和输入控制卡逐项复核实际分支。
- **历史科学证据与新仓库科学证据分离**：原 CTEAS 在 2022 C1 和 2024 C2 的 143h 限定对照有历史 PASS；`CTEAS-next` 中对应科学重跑仍须查看 [Issue #6](https://github.com/RRain001/CTEAS-next/issues/6) 的新运行、来源 SHA、真实数值日志，不能沿用历史 PASS 标签。C2 的合成格式站网必须单独以其生成的 `met.inp/puff.inp` 核对所选选项。
- 本表 `P0` / `P1` / `P2` 是**未来评估优先级**，非验收状态；P0 代表用户关心且科学外推风险较高的功能（湿沉降、地形修正、其他扩散/抬升、干沉降）。

## CALMET — P6（18 项）

| 编号 | 物理功能 / 控制选择（2022 冻结） | 原版 Fortran 入口线索 | C++ 实现入口 | 当前范围及缺口 | 优先级 |
|---|---|---|---|---|---|
| CALMET-01 | 输入气象/观测 · `NOOBS=0` | calmet.for :: READCF / surface-upper observation path（入口待源审） | [`p6g_unified_hourly.hpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p6_calmet/include/cteas/p6/p6g_unified_hourly.hpp) | 已选分支；NOOBS=1/2、无观测模式和预报输入接口未验收 | P2 |
| CALMET-02 | 观测站配置 · `NSSTA=1` | calmet.for :: READCF / PREPDI | [`p6g_g34b_six_hour_selected_gate_main.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p6_calmet/src/p6g_g34b_six_hour_selected_gate_main.cpp) | 已选分支；任意站数/几何/缺测/站点切换未验收 | P1 |
| CALMET-03 | 降水气象 · `NPSTA=0` | calmet.for :: precipitation-station/READCF pipeline（入口待源审） | (no validated native precipitation adapter) | 当前案例未激活；NPSTA>0 降水站模板/降水时间与空间映射/湿沉降接口尚未验收 | P0 |
| CALMET-04 | 云量输入 · `ICLOUD=0` | calmet.for :: cloud input/output path（入口待源审） | [`p6g_observed_thermal_hour.hpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p6_calmet/include/cteas/p6/p6g_observed_thermal_hour.hpp) | 组件/控制；ICLOUD=1..4 及湿清除依赖云雨场未验收 | P2 |
| CALMET-05 | 风场大类 · `IWFCOD=1` | calmet.for :: DIAGNO / COMP (COMP→DIAGNO approx L4511) | [`p6g_unified_hourly.hpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p6_calmet/include/cteas/p6/p6g_unified_hourly.hpp) | 已选分支；IWFCOD=0 不可由已选诊断分支推断为支持 | P1 |
| CALMET-06 | 地形动力 · `IFRADJ=1` | calmet.for :: FRADJ (DIAGNO call approx L5643) | [`froude_adjust.hpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p6_calmet/include/cteas/p6/froude_adjust.hpp) | 已选分支；其他地形/站点/GAMMA 输入的物理覆盖未验收 | P1 |
| CALMET-07 | 地形动力 · `IKINE=0` | calmet.for :: DIAGNO / kinematic wind path（入口待源审） | [`realcase_wind_field_main.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p6_calmet/src/realcase_wind_field_main.cpp) | 当前案例未激活；IKINE=1 真实风场与原版对照未验收 | P1 |
| CALMET-08 | 垂直风修正 · `IOBR=0` | calmet.for :: DIAGNO / O'Brien vertical path（入口待源审） | [`diagno_obrien_minim.hpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p6_calmet/include/cteas/p6/diagno_obrien_minim.hpp) | 当前案例未激活；IOBR=1 原版科学对照未验收 | P2 |
| CALMET-09 | 地形热力 · `ISLOPE=1` | calmet.for :: SLOPE (DIAGNO call approx L5722) | [`slope_flow.hpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p6_calmet/include/cteas/p6/slope_flow.hpp) | 已选分支；不同地形热通量和分支切换未验收 | P1 |
| CALMET-10 | 地面风外推 · `IEXTRP=-4` | calmet.for :: PREPDI / SIMILT / WIND1 | [`wind1_selected_firstguess.hpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p6_calmet/include/cteas/p6/wind1_selected_firstguess.hpp) | 已选分支；IEXTRP=1,2,3,4,-1,-2,-3 及其他站网不视为验收 | P1 |
| CALMET-11 | 预报风输入 · `IPROG=0` | calmet.for :: PREPDI / prognostic input（入口待源审） | [`realcase_wind_field_main.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p6_calmet/src/realcase_wind_field_main.cpp) | 当前案例未激活；IPROG>0 预报场插值和独立性尚未验收 | P2 |
| CALMET-12 | 站网客观分析 · `RMAX1=100.` | calmet.for :: INTER2 / weighted station blending | [`p6g_multi_wind1_firstguess.hpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p6_calmet/include/cteas/p6/p6g_multi_wind1_firstguess.hpp) | 已选分支；任意站点加权/海陆选择/可变半径配置尚未验收 | P2 |
| CALMET-13 | 地形影响范围 · `TERRAD=15.` | calmet.for :: TERSET / DIAGI | [`terrain_envelope.hpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p6_calmet/include/cteas/p6/terrain_envelope.hpp) | 已选分支；其他 TERRAD/域尺度及复杂地形组合未验收 | P2 |
| CALMET-14 | 上空稳定度 · `IUPT=-1` | calmet.for :: CGAMMA / PREPDI | [`p6g_g18b9_original_gamma_controls.hpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p6_calmet/include/cteas/p6/p6g_g18b9_original_gamma_controls.hpp) | 已选分支；只接受限定 IUPT/IDIOPT2=0，其他路径须独立核验 | P2 |
| CALMET-15 | 混合层高度 · `IMIXH=1` | calmet.for :: MIXHT / MIXHTST | [`p6g_g18a_selected_comp_mixht.hpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p6_calmet/include/cteas/p6/p6g_g18a_selected_comp_mixht.hpp) | 已选分支；IMIXH=-1/2/-2 及海面混合层未验收 | P1 |
| CALMET-16 | 混合层平滑 · `IAVEZI=1` | calmet.for :: AVEMIX (COMP approx L4715) | [`p6g_g18c1_avemix.hpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p6_calmet/include/cteas/p6/p6g_g18c1_avemix.hpp) | 已选分支；跨网格尺度/不同平均策略未验收 | P2 |
| CALMET-17 | 温度场平均 · `IAVET=1` | calmet.for :: SURFVAR / TEMP3D | [`p6g_g17b4_iavet_two_pass.hpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p6_calmet/include/cteas/p6/p6g_g17b4_iavet_two_pass.hpp) | 已选分支；真实 NOAA 第二小时 G26B TEMP3D stage15 同 SHA 源原生 62,730 REAL4 数值已 PASS_SCOPED（S4-R1c9e，Actions 39918760666）；S4-R1c9f 第16阶段 P6F 预提交候选仍 NOT_RUN，不代表原版 Fortran 第二小时等价；IAVET=0 和广义气象强迫未验收 | P2 |
| CALMET-18 | 输出数据接口 · `CALMET.DAT 2.1=selected` | calmet.for :: COMP / output writer | [``](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p6_calmet/p6f/) | 已选分支；S4-R1c9h Ubuntu 原版 NOAA 第二小时 313650 数值对照超差 0（LOCAL_PASS_SCOPED）；GitHub exact-SHA/独立审查、第二小时提交和 3–6 小时仍 NOT_ACCEPTED；格式正确不等于所有备选计算分支都有科学等价性 | P1 |

### 2026-10-24 S4-R1c9w：新增第四小时限定对照（并非生产验收）

对于本矩阵 CALMET-09（ISLOPE=1）、CALMET-17（IAVET=1）以及 CALMET-02（缺测站点内生补缺），真实 NOAA 2SS/1US、82×85×9 第四小时的 G22/SURFVAR/HEATFX/AIRDEN/ELUSTR/SLOPE 已取得 **181,220/181,220 REAL4 原版/原生限定对照，0 个冻结阈值超差，156,712 逐位一致**。原版每小时 `COMP→MISSFC→DIAGNO` 的第四小时缺测非风变量仅在测试专用副本里由 G43 源等价补缺；原始 P5 观测不改，WATER 63/63 的 USTAR 与 EL 历史传递逐位吻合。详见 [S4-R1c9w 私有源审与限定数值验收说明](../plans/ISSUE40_S4R1C9W_NOAA_HOUR4_G22_STAGE3_6_20261024.md)。**此证据只覆盖第四小时的第 0–6 阶段，G23/G24、COMP、P6F、第四小时 G14 提交以及后续小时均未验收，独立科学审查 NOT_RUN；不修改上表选项的通用生产验收状态。**

## CALPUFF — P7（24 项）

| 编号 | 物理功能 / 控制选择（2022 冻结） | 原版 Fortran 入口线索 | C++ 实现入口 | 当前范围及缺口 | 优先级 |
|---|---|---|---|---|---|
| CALPUFF-01 | 气象输入 · `METFM=1` | calpuff.for :: meteorology ingestion / COMP（入口待源审） | [`calmet21.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/calmet21.cpp) | 已选分支；METFM=2..5 未验收 | P1 |
| CALPUFF-02 | 垂直浓度分布 · `MGAUSS=1` | calpuff.for :: SETPUF / concentration kernels | [`control.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/control.cpp) | 已选分支；MGAUSS=0 均匀分布未独立验收 | P1 |
| CALPUFF-03 | 地形修正 · `MCTADJ=2` | calpuff.for :: PUFFCT2 / PUFRECS (L21035–21096; L5321–5375) | [`original_puffct2.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/original_puffct2.cpp) | 已选分支；MCTADJ=0/1/3 尚未达到完整源到受体科学对照 | P0 |
| CALPUFF-04 | 复杂地形子格 · `MCTSG=0` | calpuff.for :: complex-terrain subgrid path（入口待源审） | [`ctsg.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/ctsg.cpp) | 当前案例未激活；MCTSG=1 源-受体链未验收; 仅存在 CTSG 组件不足以支持 | P1 |
| CALPUFF-05 | 近场细长烟团 · `MSLUG=0` | calpuff.for :: SLUG path（入口待源审） | (not audited as general native execution mode) | 当前案例未激活；MSLUG=1 未验收 | P2 |
| CALPUFF-06 | 过渡烟羽抬升 · `MTRANS=1` | calpuff.for :: RISEWIND / GRISE / PRM (PRM L47001–47079) | [`original_comp_rise.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/original_comp_rise.cpp) | 已选分支；MTRANS=0 单独切换与跨源型行为未验收 | P1 |
| CALPUFF-07 | 烟羽抬升方法 · `MRISE=1` | calpuff.for :: GRISE / PRFIN | [`plume_rise.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/plume_rise.cpp) | 已选分支；MRISE=2 与指定建筑下洗场景不视为已验收 | P0 |
| CALPUFF-08 | 烟囱出口下洗 · `MTIP=1` | calpuff.for :: plume-rise/downwash branch（入口待源审） | [`original_point_prfin.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/original_point_prfin.cpp) | 组件/控制；开关单独覆盖、不同源几何与压力条件未验收 | P1 |
| CALPUFF-09 | 建筑下洗 · `MBDW=1` | calpuff.for :: source building-downwash branch（入口待源审） | [`original_point_prfin.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/original_point_prfin.cpp) | 组件/控制；MBDW=2 PRIME/有效建筑影响参数组合未验收 | P1 |
| CALPUFF-10 | 高层风切变 · `MSHEAR=0` | calpuff.for :: modified Briggs plume-rise shear（入口待源审） | [`plume_rise.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/plume_rise.cpp) | 当前案例未激活；MSHEAR=1 未验收 | P2 |
| CALPUFF-11 | 烟团拆分 · `MSPLIT=0` | calpuff.for :: puff splitting / COMP（入口待源审） | [`original_motion_lifecycle.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/original_motion_lifecycle.cpp) | 当前案例未激活；MSPLIT=1 生命周期和质量守恒未验收 | P1 |
| CALPUFF-12 | 化学转化 · `MCHEM=0` | calpuff.for :: chemical-transformation modules（入口待源审） | [`control.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/control.cpp) | 当前案例未激活；MCHEM>0 化学机制/第二种组分/反应未验收 | P2 |
| CALPUFF-13 | 湿清除 · `MWET=0` | calpuff.for :: wet removal / precipitation-input branch (exact entry not audited)（入口待源审） | (no accepted native wet-removal solver) | 当前案例未激活；MWET=1 必须先核实 CALMET NPSTA/降水站格式+时间/单位+无雨/有雨测试和沉降通量 | P0 |
| CALPUFF-14 | 干沉降 · `MDRY=1` | calpuff.for :: DRY / VDCOMP (DRY L26052–26291) | [`dry_deposition.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/dry_deposition.cpp) | 已选分支；其他物种/沉降方法、MDRY=0 切换和植被气象配置未验收 | P0 |
| CALPUFF-15 | 扩散参数化 · `MDISP=3` | calpuff.for :: SIGTY / SIGTZ / diffusion kernels | [`dispersion.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/dispersion.cpp) | 已选分支；C++ require_supported_dispersion_option 显式拒绝 MDISP!=3 | P0 |
| CALPUFF-16 | 湍流后备方案 · `MDISP2=3` | calpuff.for :: turbulence-based sigma alternatives（入口待源审） | [`dispersion.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/dispersion.cpp) | 当前案例未激活；MDISP=1/5 及后备方案未验收 | P2 |
| CALPUFF-17 | 湍流观测选择 · `MTURBVW=3` | calpuff.for :: turbulence-observation sigma logic（入口待源审） | [`dispersion.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/dispersion.cpp) | 当前案例未激活；实测湍流与风场关联未验收 | P2 |
| CALPUFF-18 | 粗糙度扩散修正 · `MROUGH=0` | calpuff.for :: sigma roughness correction（入口待源审） | [`dispersion.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/dispersion.cpp) | 组件/控制；完整 MROUGH=1 与格点 z0 物理耦合未验收 | P1 |
| CALPUFF-19 | 混合层穿透 · `MPARTL=1` | calpuff.for :: plume-penetration / GRISE（入口待源审） | [`plume_rise.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/plume_rise.cpp) | 组件/控制；单独激活条件/MPARTL=0 转换与多源场景未验收 | P1 |
| CALPUFF-20 | 粒子沉降倾斜 · `MTILT=0` | calpuff.for :: particle settling / tilt path（入口待源审） | [`dry_deposition.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/dry_deposition.cpp) | 当前案例未激活；MTILT=1 粒径/气溶胶物理未验收 | P2 |
| CALPUFF-21 | 湍流时标 · `MTAULY=0` | calpuff.for :: turbulence timescale/sigma（入口待源审） | [`dispersion.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/dispersion.cpp) | 当前案例未激活；相关 MDISP 分支未验收 | P2 |
| CALPUFF-22 | 对流 PDF · `MPDF=0` | calpuff.for :: convective PDF option（入口待源审） | (native general PDF not audited) | 当前案例未激活；MPDF>0 未验收 | P2 |
| CALPUFF-23 | 背景浓度边界 · `MBCON=0` | calpuff.for :: background boundary condition（入口待源审） | (native boundary-condition mode not audited) | 当前案例未激活；MBCON>0 未验收 | P2 |
| CALPUFF-24 | 源贡献输出 · `MSOURCE=0` | calpuff.for :: source contribution bookkeeping（入口待源审） | [`case_ledger.cpp`](https://github.com/RRain001/CTEAS-next/blob/main/native_cpp/modules/p7_calpuff/src/case_ledger.cpp) | 当前案例未激活；替代源贡献输出/多源账本未验收 | P2 |

## 下一阶段应优先做的差距包

1. **湿沉降闭环（P0）**：先在原 CTEAS 固定版本中核实 `NPSTA` 降水站输入的*格式、单位、缺测码、时区、时间步和空间映射*；真实原版短案例执行“无雨→有雨”，再建立 CALMET 气象/降水 → CALPUFF `MWET=1` → 沉降量、烟团质量、受体浓度的 C++ 独立数值对照。**当前 `NPSTA=0, MWET=0`，一律 NOT_ACCEPTED**。
2. **地形/建筑（P0/P1）**：按 `IWFCOD/IFRADJ/IKINE/IOBR/ISLOPE` 与 `MCTADJ/MCTSG/MBDW` 分别建立最小激活案例及组合案例；尤其不能将 `MBDW=1` 控制字段出现当成实际发生了建筑下洗。
3. **烟羽抬升（P0/P1）**：分开审计 `MRISE=1/2`、`MTRANS`、`MTIP`、`MSHEAR` 的原版分支条件和有效释放高度，并跟踪真实烟团质量与时间历史。
4. **扩散（P0）**：当前 `MDISP=3` 的 PG rural/MP urban 与 `MDISP=1/2/4/5` 不等价。每一种备选形式要有独立原版气象输入、σy/σz 中间量及受体场对照，不能用单元测试或 `MDISP2` 参数被解析代替物理证明。

## 维护和验收契约

- 机器可读源：[CALMET_CALPUFF_OPTION_MATRIX.csv](CALMET_CALPUFF_OPTION_MATRIX.csv)；每条包括 `original_control_source`、`fortran_entry`、`fortran_locator_grade`、`cpp_entry`、`cpp_status`、`upstream_evidence`、`cteas_next_scientific_verdict`、`unaccepted`、`next_priority`。
- 每次扩展物理选项：**定位原版控制/入口 → 记录旧代码及 C++ 源码 SHA → 写输入合同与激活条件 → 最小原版基准 → C++ 比较/守恒/负例 → 完整 C1/C2 新 run → 独立审查**；独立科学验收前不得将 `NOT_YET_REVIEWED` 改为 `PASS_SCOPED`。
- 对于没有在原版源代码中逐行核验过的 Fortran 入口，先按 `fortran_locator_grade=source audit needed for exact routine and line anchor` 留待审查，禁止捏造行号。
- 原版源码、第三方许可边界和凭据不应进入本 CSV、文档、CI 构建上下文或重构库 Git 历史；保持对老仓库的固定提交依赖与 SHA256 检查。

**参考证据**：[迁移科学范围](../migration/SCIENTIFIC_RERUN_PLAN.md) · [第三方资产决策](../migration/THIRD_PARTY_ASSETS.md) · [P7 已选干态验收](../reconstruction_cpp/P7_PHASE_STATUS_20261015.md) · [C1/C2 四臂科学对照](../reconstruction_cpp/P7_C1_C2_CALMET_TO_CALPUFF_INTEGRATION_20261015.md) · [P6 原版调用图](../reconstruction_cpp/P6D_CALLGRAPH_COMPLETENESS_AUDIT_20261013.md)

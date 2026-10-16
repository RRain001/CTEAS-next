# CTEAS P4/P5 重构交接索引（2026-10-11）

本文件是**跨分支索引**，不是第二份可冲突的技术规范。功能完成程度以对应阶段状态文档为准：

- **[P4 READ62 详细清单（P4 独立分支）](https://github.com/RRain001/CTEAS/blob/codex/cteas-p4-read62-reference/docs/reconstruction_cpp/P4_READ62_IMPLEMENTATION_STATUS.md)**：原版 Python/Fortran 模块映射、已实现功能、未支持控制项、原版数值等价证据。
- **[P5 SMERGE 详细清单（P5 独立分支）](P5_SMERGE_IMPLEMENTATION_STATUS.md)**：原始地面气象数据下载和筛选、主站/次站处理、GENERIC 输入接口、**原生 C++20 SURF.DAT 写出器及字节等价证据**、原版 CALMET 验证和非目标格式差距。
- [P5 气象资料和静风政策](../../native_cpp/modules/p5_smerge/data_prep/ISD_LITE_HYBRID_WIND_POLICY.md)。
- [**P5 真实两站、连续两年（2022–2023）原生/原版独立字节等价验收报告**](P5_REAL_MULTISTATION_MULTIYEAR_REFERENCE_2026-10-11.md)。
- [原始主计划](PROGRAM_MASTER_PLAN.md)只记录 P1–P7 的长期任务边界；不要将早期日期和状态当作最新阶段资格。

## 实现等级与验收

| 阶段 | 已经通过的独立验收 | 不可错误宣称 |
| --- | --- | --- |
| P4 | 限定 `JDAT=2, IFMT=1, PSTOP=500` 的 C++20 `UP.DAT` 全年与原版 READ62 **212,885 个数值字段和文件字节等价**；逐年 IGRA 站点选择/ FSL/最终 CALMET 输入连通 | 不能说完全复制 READ62 的所有 `JDAT/IFMT`、替代探空、缺测层剔除、顶底层修正及各种控制组合 |
| P5 | 独立 C++20 `JDAT=8 GENERIC` 输入、**IOFORM=2 格式化 SURF.DAT 写出**，合肥六日 **13,841字节**与原版一致，且**真实合肥＋霍山两站2022–2023连续两年2,663,153字节逐字节完全一致**；六日原版 CALMET已实际读取原生输出 PASS | 不可声称 IOFORM=1、IOPACK=1、LPREV=T 或其他 JDAT 已实现；不等于诊断风场物理独立验证 |
| P4+P5 → 原 CALMET | 2022年合肥六日、100 m、50×50 原版 CALMET 兼容性 smoke PASS | 不等于 C++ P6 的诊断风场、原版 CALMET 的完整气象物理精度验证 |

## 责任边界：原代码 → 当前实现

| 功能 | 原始权威模块 | 独立实现/作用 |
| --- | --- | --- |
| 探空站、IGRA 下载、探空清洗、FSL | `engine/preprocess/read62_upperair_data/{download_igra,parse_igra_to_csv,read}.py` | P4 `native_cpp/modules/p4_read62/data_prep/` 对应修改后的**独立 Python 拷贝** |
| READ62 数值与 `UP.DAT` | `engine/vendor/src/READ62_v5.661_L110225/READ62.FOR` (`COMP/WRHD`) | P4 `native_cpp/include/cteas/met_input/{p4_read62,p4_updat}.hpp` 和 `p4_read62_main.cpp` 独立 **C++20** |
| 探空年合并和最终站点表 | `engine/preprocess/read62_upperair_data/merge_final_upperair.py` | P4 按原算法复制；`run_cpp_pipeline.py` 调用 |
| 地面站历史、ISD 数据转换与选站 | `engine/preprocess/smerge_surf_data/{download_isd_by_grid,isd_to_smerge_and_fill}.py` | P5 `native_cpp/modules/p5_smerge/data_prep/` 修改后的 Python；新增 `isd_lite_wind.py` |
| 主站缺测、静风，次站稀疏规范 | `engine/preprocess/smerge_surf_data/interpolate.py`；原 SMERGE `RDWRITS JDAT=8` | P5 `wind_policy_v2.py`, `sparse_station_policy.py`, `interpolate.py`；符合最新用户规则 |
| 研究时段拼接，站点别名/控制文件 | `engine/preprocess/smerge_surf_data/{clean_merge_filled_by_research_time,generate_smerge_input_sections}.py` | P5 同名 scoped Python + `station_identity.py` |
| C++ SMERGE 输入读取 | `engine/vendor/src/SMERGE_v5.7.0_L121203/SMERGE.FOR` (`RDWRITS`) | P5 `native_cpp/include/cteas/met_input/p5_smerge.hpp` 仅解析与逐时合并 |
| `SURF.DAT` 与原版运行日志 | `SMERGE.FOR` (`RDWRITS/WRS/WRHD/RDS/PACKS`) | **由原生 C++20 `native_cpp/modules/p5_smerge/p5_surf_main.cpp` 独立写出**，限定 JDAT8/IOFORM2 逐字节等价；原版 Fortran 只作为独立参考 |
| `MET.DAT` | `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for` | 已通过原版 CALMET 直接消费原生 C++ SURF.DAT 的兼容性测试；独立 P6 属另一分支 |

## 必须持续执行的规则

- P4 外部探空站门槛是年度 **>80% 有效原始 00/12 UTC 廓线**；P5 外部地面站门槛是年度 **>90% 原始整小时记录（完整 ISD、ISD-Lite 各自满足）**。两种分母和有效性判定不同。
- P5 域内仅一站不设覆盖率门槛；多站每年选原始覆盖率最高的**一个主站**完整补缺并处理静风，其余站不补时间轴、不补任何变量、不做静风插值。
- **“18:00→20:00 缺少19:00”纯属示例**。次站可以缺失任何小时、连续任意小时、跨午夜/跨日/跨月，不得插入原始不存在的整点。源记录存在但风场无效则该小时保留，风向风速统一写 `9999,9999`；原始静风统一 `0,0`。原版 SMERGE 的**临时 EOF 结束占位记录**是仅用于兼容 Fortran 读取的独立副本，不允许回写正式次站原始时刻序列。
- 任何原始源码或旧脚本请直接到 `engine/preprocess/`、`engine/vendor/src/` 查，不要从 scoped 修改版反推“原版”。
- 两 PR 均 **Open / Ready for Review，尚未合并**：P4 [#6](https://github.com/RRain001/CTEAS/pull/6)，P5 [#7](https://github.com/RRain001/CTEAS/pull/7)。不要因为文档落盘就自动合并任何 PR。

## 可重复审计的 CI

- [P4 原版 READ62 数值与字节等价](https://github.com/RRain001/CTEAS/actions/runs/38061364090)
- [P5 真实 NOAA 地面数据捕获](https://github.com/RRain001/CTEAS/actions/runs/38108309205)
- [P5 C++/Python 单元及规范检查](https://github.com/RRain001/CTEAS/actions/runs/38109473510)（新增任意长度间隔测试）
- [P4+P5 经原版 SMERGE/CALMET 运行](https://github.com/RRain001/CTEAS/actions/runs/38108309198)
- [P5 2022—2023真实两站、17,519个小时段、逐字节等价](https://github.com/RRain001/CTEAS/actions/runs/38111753787)；两站不属于同一5km物理研究域，仅验证软件数据链与数值格式。

**下一阶段工作归属：** P4 其他控制项需建立独立参考；P5 实际使用的原生 C++ `SURF.DAT` writer 已按原版字节等价验收，真实两站两年全年文件等价已完成；下一步优先真实同5km区域多站、自然年度主站变更及更广覆盖率/气象条件的比对。未支持的原版二进制打包/LPREV/其他 JDAT 控制项须单独实现与验收。

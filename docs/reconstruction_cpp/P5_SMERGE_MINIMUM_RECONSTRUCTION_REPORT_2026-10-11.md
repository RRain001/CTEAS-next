# P5 SMERGE 最小重构验收与结果报告

- **审计日期：**2026-10-11
- **仓库：**`RRain001/CTEAS`
- **开发分支：**`codex/cteas-p5-smerge-reference`
- **Pull Request：**[#7](https://github.com/RRain001/CTEAS/pull/7)，基于 `codex/cpp20-p1-p2-foundation-20261010`，保持 Open / Ready for Review，**未合并**。
- **结论：**`P5_MINIMUM_RECONSTRUCTION=PASS`，仅对下面定义的实际生产案例控制组合成立。**独立原生 C++20 `SURF.DAT` 写出器已实现，并有同输入、原版 SMERGE 的完整文件逐字节等价证据。** 不等于复制了 SMERGE 5.7.0 全部输入/格式/续算分支。

## 1. 最小重构的验收边界

| 控制或输入项 | 已验收的范围 |
| --- | --- |
| `JDAT` | **8**：GENERIC v2.0，12列地面气象输入 |
| `IOFORM`、`IOPACK` | **2、0**：文本型 `SURF.DAT`，非二进制/非打包 |
| `LPREV`、`LPCALC` | **F、F**：不续算旧 `SURF.DAT`，不额外估算站压 |
| `ABTZ`、`ASTZ` | **UTC+0000**，整小时输入；秒参数为0 |
| 站点与时间 | `smerge.inp` 中的站序和站号；对所请求小时逐时输出；任意缺失原始整点按实际时间对齐，不对次站创建补值记录 |
| 数据来源 | 完整 ISD 供应风以外的气象项；ISD-Lite 供应风向和风速；经过当前 P5 既定清洗与选站流程生成 GENERIC |
| 输出 | 完整的 SMERGE v2.1 格式化 `SURF.DAT`：文件头、时区、起止时、站点号、每小时起止时、各站8个字段、缺测编码 |

原版 SMERGE v2.1 的 `IBYR/IBMO/IBDY/IBHR` 是显式**起始**时刻，内部转换为首个结束小时；例如 `2022-01-01 00:00 — 2022-01-01 03:00` 对应 **3个**逐小时区间，不是4个。新 C++ 写出器已经按原版实现，禁止因索引误解造成一小时偏移。

## 2. 已实现功能及与原版源代码的对应

| 实现功能 | 当前代码 | 原版依据 |
| --- | --- | --- |
| ISD、ISD-Lite 下载、站点覆盖率、逐年筛选 | `native_cpp/modules/p5_smerge/data_prep/download_isd_by_grid.py`、`isd_lite_wind.py`、`station_identity.py` | `engine/preprocess/smerge_surf_data/download_isd_by_grid.py`；新增官方 ISD-Lite 风场输入 |
| 主站全时次缺测填充、原始静风替换 | `data_prep/wind_policy_v2.py`、`interpolate.py` | `engine/preprocess/smerge_surf_data/interpolate.py`（需求驱动的独立扩展） |
| 次站原始时间轴稀疏保留、静风归一和 `9999` | `data_prep/sparse_station_policy.py`、`interpolate.py` | `engine/preprocess/smerge_surf_data/interpolate.py`；原版 `SMERGE.FOR` 的 `RDWRITS` |
| GENERIC、UTC 整小时、站号与字段解析 | `native_cpp/include/cteas/met_input/p5_smerge.hpp` | `SMERGE.FOR` 的 `COMP`、`RDWRITS` (`JDAT=8`) |
| **原生 C++ 完整文本 `SURF.DAT`** | **`native_cpp/modules/p5_smerge/p5_surf_main.cpp`**、同目录 `CMakeLists.txt` | `SMERGE.FOR` 的 `READCF`、`RDWRITS`、`WRHD`、`WRS` |
| 正式输出发布、站点表、既有云量兜底 | `data_prep/run_smerge_and_monitor.py --native-cpp-bin` | 原有同名脚本；最终 `met/surface/final/{surf.dat,stations.csv}` 接口 |
| P5 一键准备与可选原生输出 | `data_prep/prepare_inputs.py --execute --native-cpp-bin` | `engine/preprocess/smerge_surf_data/run_isd_surface_pipeline.py` 等旧流程 |
| 原版数据与独立 C++ 结果检验 | `.github/workflows/p5-native-surf-parity.yml`、`p4-p5-original-calmet-integration.yml` | 原版 Fortran `SMERGE_v5.7.0_L121203`、`CALMET_v6.5.0_L150223`（两者均未改动） |

**重要区别：**这次 C++ 程序实质性构造每个输出气象记录，不调用原版 SMERGE，也不是将原版输出文件复制/改名。原版 Fortran 仅用于测试时的独立参考计算。数据前处理继续使用隔离后的 Python 脚本，不能称为“整个 P5 所有环节均已 C++ 化”。

## 3. 逐项验收证据

| Gate | 证据与规模 | 结果 |
| --- | --- | --- |
| A. C++20 独立构建和输入合同 | 严格编译警告 `-Werror`、GENERIC格式/站号/单位/缺测/UTC输入契约；Debug/Release断言不关闭 | **PASS** |
| B. 两站合成数据对照原版 SMERGE | 含真实静风、稀疏整点、风矢量无效、温度缺测、雨雪编码及小数气象值；原版与 C++ 分别输出 **721字节、17行**，差异0 | **BYTE_PARITY PASS**；[CI](https://github.com/RRain001/CTEAS/actions/runs/38111038381) |
| C. 合肥2022真实数据同输入对照 | 2022-01-01 00Z—2022-01-06 23Z；原版与 C++ 输出均为 **13,841字节、293行**；所有文件字节一致 | **BYTE_PARITY PASS**；[CI](https://github.com/RRain001/CTEAS/actions/runs/38111038279) |
| D. CALMET 消费 C++ 文件 | 未改动 CALMET v6.5.0；50×50、100m；读取**原生 C++生成并发布的** `SURF.DAT`，输出 `MET.DAT` 64,762,556字节 | **PASS**；[CI](https://github.com/RRain001/CTEAS/actions/runs/38111038279) |
| E. 稀疏双站与原版对照 | 保留实际次站时间缺口；原版 SMERGE 临时副本为避免 EOF 使用末时刻占位；**C++ 直接读取正式稀疏源，无该占位记录**；生成文件与原版一致 | **BYTE_PARITY PASS**；`P5_NATIVE_SPARSE_NO_SENTINEL_BYTE_PARITY=PASS`；[CI](https://github.com/RRain001/CTEAS/actions/runs/38111038279) |
| F. CALMET 消费原生稀疏双站文件 | 未改动 CALMET 再次读取新 C++ 发布的双站结果，产出模型文件且无致命错误 | **PASS**；`P5_NATIVE_SURFDAT_ORIGINAL_CALMET_SPARSE_MULTISTATION=PASS`；[CI](https://github.com/RRain001/CTEAS/actions/runs/38111038279) |
| G. 不支持模式严禁误运行 | `JDAT=5`、`IOFORM=1`、`IOPACK=1`、`LPREV=T`、`LPCALC=T`、非UTC `ABTZ` 均明确拒绝 | **FAIL-CLOSED PASS**；[CI](https://github.com/RRain001/CTEAS/actions/runs/38111038381) |

第 E 项只证明**合成稀疏次站**的原始时间对齐和字节兼容；不应解释为“已验证所有真实地区、所有时间跨度的多站气象物理效果”。

### H. 追加验收：真实多站、跨年全时段独立数值验证

[2022—2023年真实合肥＋霍山完整报告](P5_REAL_MULTISTATION_MULTIYEAR_REFERENCE_2026-10-11.md)和[独立 CI #38111753787](https://github.com/RRain001/CTEAS/actions/runs/38111753787)已通过，属于本报告初版发布后的**新增证据**：

| 检验对象 | 结果 |
| --- | --- |
| 官方原始数据 | 两站、两年，4份完整 ISD + 4份 ISD-Lite，真实源内容和哈希留存 |
| 逐年覆盖率及角色 | 合肥2022：8692/8760，2023：8642/8760；霍山2022：2828/8760，2023：2729/8760；两年独立判定合肥为主站 |
| 主站处理 | 两个日历年各8760小时，逐时有完整非静风 |
| 次站处理 | 仅保留两年2828 + 2729 = **5557** 个实际存在的原始小时，缺失整点无补造 |
| 连续两年时间边界 | **PASS**，包含2022-12-31 23:00→2023-01-01 00:00 |
| 原版和原生 C++ 生成 `SURF.DAT` | **17,519 个小时区间、52,565行、2,663,153字节，两者逐字节完全相同** |
| 双文件 SHA-256 | `f6e80e8005d27208799c3881390ab705fc92edfccfdf7f55abccf08d870d5816`，完全一致 |

**重要边界：**霍山和合肥不在同一个5km研究域，本项属于使用真实来源的双站软件/格式回归，不能当作同域双站气象场物理校验。此外两个年份的覆盖率排名都没有反转，真实自然年度**切换主站身份**仍未发生；独立单元测试验证了切换决策代码。连续两年原版 CALMET 风场物理结果也不包含在本项中。此报告的`P5_MINIMUM_RECONSTRUCTION=PASS`不因此扩大到所有历史 SMERGE 模式。

## 4. 延续执行的选站/缺测/静风规则

1. 研究范围内无地面站：按烟囱距离递增选第一个全年完整 ISD 和 ISD-Lite 各自原始整点覆盖率**严格 >90%**的站，作为当年唯一虚拟站，下一年重新筛。
2. 域内恰一站：无原始覆盖率下限，全时次补齐、缺测/静风处理。
3. 域内多站：每年按原始 ISD-Lite 整点覆盖率选覆盖率最高的**唯一主站**完整处理；其余次站保持原始实际存在小时，不对缺失的整小时、连续多小时、多天、跨月缺口创建新记录；原始静风编码为(0,0)，不得插值；任一风分量无效则两者 `9999`，其他缺值 `9999`。
4. 原始有记录但风缺测与完全缺少原始小时应分开统计；覆盖率 = 年度**原始有记录的唯一UTC整点数** / 8760或闰年8784。
5. **“18点、20点有记录，19点缺失”只是一种示例。**任何时刻、任何长度的次站整点缺口都不能补时次。原版 Fortran 的 EOF 占位仅用于隔离的原版参考运行副本，不得写入正式次站 GENERIC；C++ 原生 writer 不需要该占位。

## 5. 未实现、尚待独立验证的部分

| 分类 | 尚未覆盖的能力 | 原代码参考 |
| --- | --- | --- |
| 历史格式 | `JDAT=1/2/3/5/6/7` 非GENERIC输入 | `SMERGE.FOR` `RDWRITS/READCF` |
| 输出模式 | `IOFORM=1`、`IOPACK=1` 的原版 Fortran unformatted/packed 文件及对应读取 | `SMERGE.FOR` `WRHD/WRS/PACKS/UNPCKS/RDS` |
| 续算 | `LPREV=T`、`PREV.DAT` 站点继承等 | `SMERGE.FOR` `RDHD/RDS/RDWRITS` |
| 其他控制参数 | `LPCALC=T`、非UTC `ASTZ/ABTZ`、非整小时秒及不支持组合 | `SMERGE.FOR` `READCF`、气压转换例程和时间变换 |
| 真实长案例剩余部分 | **已完成**真实两站、两年完整`SURF.DAT`字节等价；**尚未验证**真实同域多站、自然跨年更换主站及更广泛雨量/云量和长缺测气象物理敏感性 | [新增真实跨年报告](P5_REAL_MULTISTATION_MULTIYEAR_REFERENCE_2026-10-11.md)；同一独立 Fortran + C++ 比较机制 |
| 物理研究 | 缺测长期沿用、将静风人为替换为0.5m/s的结果敏感性和后续诊断风场质量 | P5数据政策；`CALMET calmet.for`，后续P6验收 |
| 全部旧程序附属输出 | 原版 SMERGE.LST/QA详表、天气特殊输出等的等价实现 | `SMERGE.FOR` `FIN/PCODES/QA` |

上述项目均不能由于`SURF.DAT`最小验收通过而自动标为完成。**最终结论是“实际使用的 P5 路径最小重构完成”，不是“全部 SMERGE 5.7.0 通用功能完整复刻”。**

## 6. 如何复验

从仓库根目录构建 C++20 独立输出程序：

```bash
cmake -S native_cpp/modules/p5_smerge -B /tmp/cteas-p5-native -DCMAKE_BUILD_TYPE=Debug
cmake --build /tmp/cteas-p5-native -j2
ctest --test-dir /tmp/cteas-p5-native --output-on-failure
```

若已有当次案例准备好的 `smerge.inp` 和 GENERIC：

```bash
python3 -m native_cpp.modules.p5_smerge.data_prep.run_smerge_and_monitor \
  --native-cpp-bin /tmp/cteas-p5-native/cteas_p5_smerge
```

或者执行包含 NOAA 准备、GENERIC 转换、SMERGE控制文件生成及原生发布的一键流程：

```bash
python3 -m native_cpp.modules.p5_smerge.data_prep.prepare_inputs \
  --execute --native-cpp-bin /tmp/cteas-p5-native/cteas_p5_smerge
```

调用前需设置正确的当前研究案例、提供其网格/研究时段及 NOAA 原始数据访问所需环境。上述命令**不调用原版 SMERGE 二进制**。原版 SMERGE 仅在对照测试 CI 中独立编译与运行。

## 7. Git/交付边界

- PR #7 是已有的 P5 交付 PR；**更新该 PR 的标题、描述、证据及本报告，不创建重复 PR**。
- 当前 `engine/preprocess/` 原始脚本、`engine/vendor/src/SMERGE_v5.7.0_L121203/`、`engine/vendor/src/CALMET_v6.5.0_L150223/` 源码均保持不变。
- 这份报告将 `P5_MINIMUM_RECONSTRUCTION=PASS` 与 `P5_FULL_LEGACY_REIMPLEMENTATION=FALSE` 严格区分。
- 更完整的功能索引见 [P5 实现状态表](P5_SMERGE_IMPLEMENTATION_STATUS.md)、[P4/P5 交接索引](P4_P5_HANDOFF_INDEX.md) 与 [ISD-Lite/风场处理规范](../../native_cpp/modules/p5_smerge/data_prep/ISD_LITE_HYBRID_WIND_POLICY.md)。

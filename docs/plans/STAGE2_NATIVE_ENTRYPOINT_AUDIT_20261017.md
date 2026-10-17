# S2-2A：CTEAS-next 原生 P1–P7 入口审计与集成缺口（2026-10-17）

**类型：** 只读源码审计 / 生产接口设计。**并未运行新案例，也未更改任何物理程序。**
**依据：** `main@1b0abf54960b032691f7c836fb641bb53ffefbd6`，主路线 [四阶段计划](CTEAS_NEXT_FOUR_STAGE_PLAN_20261017.md)，跟踪 [Issue #16](https://github.com/RRain001/CTEAS-next/issues/16)。
**本文基准时刻：** 此段是初始 S2-2A 审计的历史门槛。S1 后来已在 G5 暂缓的获批范围内通过（[Actions #39021059327](https://github.com/RRain001/CTEAS-next/actions/runs/39021059327)）；最新 S2-2B P1–P3 结果见本文第 7 节。未验收的 `engine/gui_g5/pipeline.py` 阶段继续 fail-closed。

## 1. 已存在的入口与真实产品性质

| 模块 | 代码/可运行入口 | 实际输入→输出 | 判断 |
|---|---|---|---|
| P1 TERREL | `native_cpp/src/p1_terrain_cli.cpp`：`cteas_p1_terrain SRTM_TIF X0_KM Y0_KM OUTPUT_CSV` | GeoTIFF + UTM50N 原点 → 50×50、100m 地形 **CSV** | **SCOPED_REFERENCE_CLI**；不是完整原版格式 `TERREL.DAT` 写出接口 |
| P2 CTGPROC | `native_cpp/src/p2_gen_fraction_cli.cpp`：`p2_gen_fraction GEN_FILE X0_KM Y0_KM OUT_CSV` | GEN + UTM50N 原点 → 50×50 土地利用比例 **CSV** | **SCOPED_REFERENCE_CLI**；不是完整原版格式 `LU.DAT` 写出接口 |
| P3 MAKEGEO | `native_cpp/src/p3_makegeo_cli.cpp`：`cteas_p3_makegeo MAKEGEO.INP LU.DAT TERREL.DAT OUTPUT.CSV [GEO.DAT]` | **原版格式** LU/TERREL 文件 + 控制卡 → 数值 CSV、可选 `GEO.DAT` | **SCOPED_NATIVE_WRITER**；强制 UTM 50N、50×50@100m、38→14 类和已选控制分支 |
| P4 READ62 | `native_cpp.modules.p4_read62.data_prep.run_cpp_pipeline` + `cteas_p4_read62` | IGRA → Python 清洗/FSL → C++ `UP.DAT` → 复制的原版 Python 合并器 | **SCOPED_NATIVE_FORTRAN_REPLACEMENT**；不是全 C++ 原始数据处理；默认 dry-run，`--execute` 才写文件 |
| P5 SMERGE | `native_cpp.modules.p5_smerge.data_prep.prepare_inputs` + `cteas_p5_smerge` | NOAA/ISD 预处理 → GENERIC → C++ `SURF.DAT` | **SCOPED_NATIVE_FORTRAN_REPLACEMENT**；`--native-cpp-bin` + `--execute` 才走选定原生路径 |
| P6 CALMET | `native_cpp/modules/p6_calmet/src/native_hourly_driver_main.cpp`（`cteas_p6_native_hourly_driver`）及 `realcase_wind_field_main.cpp` | 2022 合肥冻结 GEO/SURF/UP + P6D/P6E/CGAMMA/BRIDGE 子程序 → 选定原生 MET、逐小时 manifest | **FROZEN_CASE_SCIENCE_DRIVER**；当前仍限制小时数 ≤143、绑定 `up_58424.dat`、50×50×9 等假设，非任意案例 runner |
| P7 CALPUFF | `native_cpp/modules/p7_calpuff/` 下的多个真实 COMP/采样/写出库与 `tests/original_hefei_*_tests.cpp`；`cteas_p7_native_met_hours` | 同 MET 的选定物理路径可在真实科学验证驱动中生成浓度；`native_met_hours` **只解析/检查 MET** | **SCOPED_SCIENCE_TEST_DRIVER**；缺少受控、独立、正式对外的 P7 全小时浓度生产 CLI |

**关键结论：** P1/P2 的 CSV **不能直接作为 P3 的 `TERREL.DAT` / `LU.DAT` 输入**。项目已有 P1–P3 分模块科学参考验证，但缺一个被证明同源一致、同头运行的 **P1/P2 完整原版格式写盘→P3读取** 集成通路。先评估已存在的其他 P1/P2 库或写盘路径；若没有，不得把对照 CSV 重命名为原版文件。P6/P7 的长期内部状态也不能简单按“每小时重新执行测试”拼接。

## 2. 与 GUI 的隔离规则

`engine/gui_g5/pipeline.py` 当前：
- 只允许严格受控的 `surface` 原生调用，依赖 `CTEAS_G5_P5_BIN`；其余 `preprocess/upperair/met/puff/all` 维持 **BLOCKED**。
- `stage_readiness()` 检查 case 名、`project/current` 选择、`case.yaml`、UTM 坐标及时间；`resume` 对未验证阶段拒绝。
- `engine.orchestrator.cli` / `engine.run_met.run_met` / `engine.run_puff.run_puff` 属于 Legacy 路径，不得以任何方式作为 G5 隐式回退。
- 两套 GUI Workbench **本阶段不修改**；优先实现无 GUI 的 native-only CLI 及只读 dry-run。

## 3. 入口/格式不一致清单与下一行动

| ID | 阻断点 | 必须先做的工作 | 实测准出证据 |
|---|---|---|---|
| G2A-01 | P1/P2 只证明网格数值 CSV，P3 要求原版格式 `TERREL.DAT/LU.DAT` | 查找已有原生 writer 或在不改物理算法前提下新增严格序列化 adapter；验证头、字段、行列方向、UTM zone/mask、源数据 SHA | 同冻结输入的完整原版格式字节/数值检查、恶意/截断负例 |
| G2A-02 | P3 严格 50×50、100m、UTM50N 及固定土地利用类 | 将物理覆盖写入 `supported_case` 合同；越界错误禁止执行 | 非50×50、跨UTM、未知土地类别 fail-closed 测试 |
| G2A-03 | P4 原始气象 Python 清洗/merge 有源/effective 站坐标与缺测处理 | 封装为显式 provenance 的原生 READ62 数值执行 adapter，禁止原版 Fortran 后端 | `UP.DAT`/站点合并时间轴/文件长度、字段 SHA + 双/多站负例 |
| G2A-04 | P5 需要明确烟囱位置、站网、降水缺失语义 | 原生 C++ SMERGE 受控调用 + `SURF.DAT` station metadata 一致性 | 同输入格式、时间、字节记录及缺失状态核验 |
| G2A-05 | P6 hourly driver 绑定 2022 58424/50×50×9 与源参考角色 | 首先接收 `CaseDescriptor`，明确 `MET.DAT` 不可来自旧 Fortran；逐小时状态和 input authority 分开；避免从原版参考偷读完整动态值 | 同 SHA 2022 限定 143h & 状态回滚验收；不称任意时长/多站 |
| G2A-06 | P7 对照 `tests` 驱动不等于正式 CLI | 在已有 source/COMP/ROLLDN/PFSAMP/WROUT1 原生路径之上设计生产 adapter；真正管理跨小时 state 和完整浓度输出 | 相同 MET 的非零 H-3 REAL4 分母、文件/时间记录数及原版对照；未支持分支拒绝 |
| G2A-07 | `case.yaml` / `grid/*.cmn` / 原版 INP 各含网格、时间、源项定义 | 定义一个权威控制来源并生成/验证与 legacy INP 等价的只读 manifest；冲突即拒绝 | 控件冲突、站点坐标、UTC 端点、排放量单位和文件缺失负例 |
| G2A-08 | 参考文件路径与运行结果混用 | 分离 read-only `fixtures` 与 `work/<run-id>`、`out`，哈希锁定所有输入，产物原子发布；禁止覆盖参考 | 两次重跑产物哈希、失败后事务回滚、非零退出码 |

**S2 的第一个可开发任务不是直接调用 `all`，而是 G2A-01（P1/P2→P3 原版格式接口）和 G2A-07（统一 case/source contract）。** 两者完成后再排 P4/P5→P6→P7 接口。

## 4. 建议的最小 API（仅设计草案）

```text
CaseDescriptor:
  case_id, source_root, case_yaml_sha256,
  crs, grid(nx,ny,nz,resolution,zface,utm_zone), utc_interval,
  stack, emissions, station_policy, accepted_physics_options

StageDescriptor:
  stage_id, native_executable, argv, supported_case_predicate,
  required_inputs(path,sha256,format,units,time_axis),
  declared_outputs(path,format,units,time_axis)

ExecutionPlan:
  source_sha, dependency_graph(P1/P2 -> P3; P4/P5 -> P6; P3 -> P6; P6 -> P7),
  ordered_stages, dry_run=true, allow_legacy_fallback=false

StageResult:
  status=NOT_RUN|BLOCKED|PASS_SOFTWARE|FAIL,
  exit_code, stdout/stderr hashes, input/output SHA256,
  completed_hours, record_count, first_error

RunManifest:
  physical_option_matrix_revision, provenance, source/vendor identity,
  accepted_scope, validation_status, outputs, failure_or_rollback_state
```

禁止在 `StageResult` 上用 `PASS_SOFTWARE` 冒充 `PASS_REFERENCE` 或 `PASS_SCOPED`。**首个实现应只支持读取/校验/打印 Plan**，没有外部程序执行或数据下载；科学内核、旧 GUI、配置阈值都不改。

## 5. 下一批最小 PR（S1 软件回归通过后才能解锁运行）

- **S2-2A1:** Schema/manifest/dry-run CLI，仅静态校验与负例单元测试。未接受的场址一律拒绝；不启用 `G5 all`。
- **S2-2B:** 已有原生 P1/P2 → 原版兼容 `TERREL/LU` writer → P3 `GEO.DAT` 连通。
- **S2-2C:** P4/P5 → P6 选定 2022 场景状态协调及输出校验。2024 C2 合成站网作为**额外独立扩展门**，不能自动通过。
- **S2-2D:** P7 生产 adapter 与真实 source clock、CON 格式和连续跨小时状态。冻结对照、输出完整性、非零浓度与误差审计。
- **S2-2E:** 只在经过端到端实测科学验收的配置上解除 G5 对应 BLOCKED 项；其余分支保持 fail-closed。

## 6. 本次结论

`S2_2A_ENTRYPOINT_AUDIT=COMPLETE_STATIC`；`S2_NATIVE_P1_P7_GENERAL_PIPELINE=BLOCKED`；
`S1_PR13_SOFTWARE_REGRESSION=NOT_RUN`；`C1=C2=PASS_SCOPED`（仅原独立 143h 验收提交）。
没有新的科学计算、生产运行或普适物理选项验收。

## 7. S2-2B 后续实施与同源科学验收（2026-10-17）

**结果：`S2_P1_P2_P3_NATIVE_CHAIN=PASS_SCOPED`，不是全场址/全选项 P1–P3 PASS，更不是 P1–P7 全流程验收。**

- **实现：** [PR #23](https://github.com/RRain001/CTEAS-next/pull/23)，合并后 `main@b7245363108ee280f32decd0fde00e49f0b67da1`。独立 C++20 `native_cpp/p3/p12_native_dat_adapter.cpp` 将真实 C++ P1/P2 CSV 严格写出 `TERREL.DAT 2.0`（北→南地形）与 `LU.DAT 2.1`（南→北 38 类）供**未经修改的** P3 `cteas_p3_makegeo` 使用。缺测、行列错误、类别/比例损坏或覆盖原文件都会拒绝。P3 CMake 已注册独立 `cteas_p12_p3_scoped_file_contract` CTest；[格式门 #39024141606](https://github.com/RRain001/CTEAS-next/actions/runs/39024141606) `PASS_SOFTWARE`。
- **实际原生 P2：** [Actions #39024361165](https://github.com/RRain001/CTEAS-next/actions/runs/39024361165) 从本仓库固定 `GENERIC.LANDUSE` 执行 C++ P2，比较 95,000 个原版展示值，**0 mismatch**；用该真正原生 P2 与冻结原版 P1 `TERREL.DAT` 执行 P3，20,000 个展示字段均通过（此步是明确的**混合输入验证**）。
- **独立同源原版重跑：** [Actions #39025117223](https://github.com/RRain001/CTEAS-next/actions/runs/39025117223) `SUCCESS`；从 `RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13` 在**临时 runner** 取原版 TERREL 7.0.0、CTGPROC 7.0.0、MAKEGEO 3.2 并实际重新运行，另用本仓库 `main@b7245363108ee280f32decd0fde00e49f0b67da1` 重新编译/执行 C++ P1、P2、P3，逐级采用**相同源数据**和经过 SHA256 校验的 `SRTM c4211914fce527d2ad41ecac1e668d7faa2904bbbfd9135868ee83ef0d32123f`、`GEN bd937d99fb13b49ac6185c080359bef050afe76fc63945ac53b7d676547d43dc`。全部物理选项维持 50×50@100m、UTM50N/WGS84、无雪单输入源的限定配置。

| 独立比较 | 分母 | 实际结果 |
| --- | ---: | --- |
| P1 TERREL 已显示地形高度 | 2,500 | **0 mismatch**；严格未舍入 REAL4 均值审计 `PASS_SCOPED` |
| P2 CTGPROC 已显示分类比例 | 95,000 | **0 mismatch**；原版/原生有效采样计数审计 `PASS` |
| P3 MAKEGEO `GEO.DAT` 展示字段 | 20,000 | **0 mismatch**；`PASS_SCOPED` |
| 原版对照头/输入 | 2,500 TERREL + 2,500×38 LU | 新生成原版兼容输入均可由未经修改的 P3 读取；格式/异常路径 CTest PASS |

**重要基准区分：** 一次试验 [#39024659472](https://github.com/RRain001/CTEAS-next/actions/runs/39024659472) 把新原生 P1 与 2022 长期冻结目录下的另一份 `TERREL.DAT`（SHA256 `b35d48762e1e060dcf9236a6edd90f2fd8b8bd5a819f5ecd92cc94be03e9175e`）比较，发现 18 个高度显示值不同并在 P3 产生 36 个字段差异；该测试**不能**升级为 PASS，其数据来源/控制差异应另行追溯。与之相反，在**同源、重新执行原版**的门 `#39025117223` 中，原版 `TERREL.DAT` SHA256 `d74a5a1045ea4cf25e120099196a3962ab012aaebdf37354ec8264fad0e27678` 与新 C++ 算法对照没有超差。不得通过更换容差、改写原冻结文件或掩盖失败来混淆这两个独立基准。之前临时诊断的“32 m 未舍入最大误差”存在行索引错误，不作为有效统计值使用。

**保留限制：** 新 writer 固定于已验收的合肥 50×50 配置，不是任意分辨率/投影/输入格式执行器；G5 未测试且未解锁；P4/P5→P6→P7 原生调度与多站/其他物理选项仍未完成。原版源码和 TIFF 仅在短命 CI 工作目录恢复，**没有**加入当前 Git、Docker 或公开发布文件；本次上传的只包含审计 JSON。Actions 二进制产物和源再现的长期保存另由 [Issue #18](https://github.com/RRain001/CTEAS-next/issues/18) 跟踪，摘要不等于原始数据归档。

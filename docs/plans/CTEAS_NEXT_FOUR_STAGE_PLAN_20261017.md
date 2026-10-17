# CTEAS-next 四阶段实施与验收路线（2026-10-17）

**文档权威性：** 本文是 CTEAS-next 自 2026-10-17 起的工程实施计划；`docs/reconstruction_cpp/PROGRAM_MASTER_PLAN.md` 是项目总入口，已完成的实验历史仍可在 Git 旧提交中查阅。**状态是计划及实测证据的分离记录，不是未来完成承诺。**

## 0. 当前基线与不可变原则

- GitHub：`RRain001/CTEAS-next`；制定计划时 `main=e06db8ff5f448a1dd2186935ca0fa671a1e4f9e8`（PR #12 已合并）；[PR #13](https://github.com/RRain001/CTEAS-next/pull/13) 基于此提交，head `0d0cb09012b6cacd7f6f3a406b865e3b2a38c671`，待软件回归验收，未合并。
- [PR #11](https://github.com/RRain001/CTEAS-next/pull/11) 已合并科学验收报告；[Issue #6](https://github.com/RRain001/CTEAS-next/issues/6) 已针对 **143h C1/C2 限定范围**关闭。
- C1（2022 单站 143h）：`PASS_SCOPED`；原版 CALMET 的气象输入是冻结参考，而非本次重新运行原版 CALMET；同气象输入 P7 H-3 REAL4 浓度逐位相同。证据：[Actions #39001955056](https://github.com/RRain001/CTEAS-next/actions/runs/39001955056)。
- C2（2024 人工构造的 2 地面站/2 高空站 143h）：`PASS_SCOPED`；原版与原生 CALMET 均实际运行，6,435 个 field-hour 比较无超限；P7 同气象输入 H-3 REAL4 值逐位相同。该案例不是独立实测气象验证；整个 `puff.con` 文件**不**声明逐字节一致。证据：[Actions #39012460127](https://github.com/RRain001/CTEAS-next/actions/runs/39012460127)。
- **全部 CALMET/CALPUFF 选项**仍为 `NOT_READY`：湿沉降 `MWET>0`、降水站/时空适配、其他地形修正/烟羽抬升/扩散选项均未取得通用科学认证。以 `docs/physics/CALMET_CALPUFF_OPTION_MATRIX.{md,csv}` 为物理选项台账。
- `engine/gui_g5/pipeline.py` 当前仅有已准入的 `surface` 通用原生执行；`preprocess`、`upperair`、`met`、`puff`、`all` 仍 fail-closed。旧 `engine.orchestrator.cli` 不是 G5 原生后端。两个 PySide6 GUI 保留，**本轮不重构 GUI**。
- `RRain001/CTEAS` 的原版源码和历史数据**不是**自动取得再发布许可的证明；vendor/受限制地形不得复制进公开 Git 仓库、公开 Actions 产物和 Docker。保留授权恢复、SHA256 校验与原版源码版本锁定。
- 统一实行：每个阶段一个可复核的独立 PR/Issue；先列出入口/物理选项/验收分母，再写代码；不更改科学阈值、不从旧模型静默回退、不通过删除检查产生假 PASS；不通过 CI/科学数据就标 `BLOCKED` 或 `NOT_RUN`。

## 总体依赖和阶段状态

| 阶段 | 核心交付物 | 依赖 | 截至制订计划时的事实状态 | 关闭标准 |
| --- | --- | --- | --- | --- |
| **S1 / Repo Stabilization** | PR #13 路径/冻结数据回归、Ubuntu/CTest、Python/G5、Docker | PR #12 已合并 | **IN_PROGRESS; REGRESSION_NOT_RUN** | PR #13 实际测试通过并合并；归档 SHA/日志/输出分母 |
| **S2 / Native P1–P7 Execution** | 可复用的**选定物理范围** P1→P7 单案例原生执行链、清单/错误/恢复接口 | S1 | **DESIGN_NOT_STARTED** | 在准入配置上，从 `case.yaml` 至浓度产物可运行/可重跑；无需旧版 Fortran 执行回退，独立物理验证 |
| **S3 / Verified Fixture Externalization** | 可验证按需恢复的冻结基准、独立许可/数据存储、精简 checkout | S1 且 S2 核心科学依赖明确 | **NOT_STARTED** | SHA/文件长度/原版路径一致，离线/缺数据 fail-closed，CI 测试通过；不损害可复现性 |
| **S4 / Physics-option Expansion** | 降水数据契约、湿沉降及其他选择分支逐项验证 | S2 的基准执行链 | **NOT_STARTED** | 每一物理选项有输入模板、原版同输入对照、质量守恒及独立审计；选项矩阵逐行更新 |

> **顺序：** S1 先关闭；S2 可以开展**设计审计**但不得绕过 S1 直接宣称运行验收；S3 在确定恢复依赖后推进；S4 以 S2 真实完整的选定配置为前提。四阶段是工程计划，不把旧 C1/C2 科学结论升级成全选项 PASS。

## S1：PR #13 回归验收与仓库收口

### 已实施
- PR #12 清理 162 条历史/过时文件并合并到 `main@e06db8ff`。
- PR #13 清理 284 条多余路径，源树静态审计 `PASS_STATIC`；去掉 `deliverables/` 的重复 `MET.DAT`/`puff.con` 与历史中间输出/日志/研究记录。
- PR #13 中仍保留 P6F/P7 CTest 和科学工作流需要的 **2022 冻结 `run/met/met.dat`、`run/puff/puff.{con,lst}`、输入卡及 2023 `run/met/met.dat`**；P6F CMake 和 `scripts/local_gate.py` 中删除旧 `deliverables/puff/` 路径后指向相同 Git blob 的 `run/puff/`。

### 必须执行的回归门槛（在 PR #13 **同一个 head SHA** 上）
1. **Git/静态预检**：确认 PR #13 只有预期删除与参考路径改写；比较保留/删除的冻结参考 blob、验证 sha256、检查 CMake/脚本/Actions 输入没有悬空路径；两套 GUI 的源码 SHA 与旧 `main` 一致，4 条 Actions 工作流仍不变。
2. **Ubuntu nine-suite**（有 GCC12/GFortran11/GDAL 的主机）：`python3 scripts/migration/validate_ubuntu.py --portable --out /tmp/cteas-pr13-ubuntu --jobs 2`；保留逐 suite configure/build/CTest/未运行项清单、退出码。由于原版 vendor 不随仓库分发，显式 `NOT_RUN` 的外部专有科学项不能算 PASS。
3. **Python/G5 回归**：`python3 scripts/migration/validate_python.py --portable --out /tmp/cteas-pr13-python`；保留测试计数和结果。G5 必须继续拒绝 `all/met/puff` 等未支持路径，绝不回退旧模型。
4. **Docker AMD64**：`docker build --file docker/cpp/Dockerfile --target verification --tag cteas-next:pr13-verify .`（需 BuildKit、联网获取受控基础镜像）；查看 `CONTAINER_CPP_PORTABLE=PASS`、`CONTAINER_PYTHON_PORTABLE=PASS` 和 `CONTAINER_G5_OFFSCREEN_AND_FAIL_CLOSED=PASS_SOFTWARE`。ARM64 可追加平台适配测试，但不得将未运行标 PASS。
5. **冻结基准一致性**：明确 2022 `run/met/met.dat` SHA256 = `b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30`；2022 `run/puff/puff.con` SHA256 = `0d51bdb68ff1a5798048bc41067107d3ffe10dc6222f25336df856bcbf48ba10`。凡发生静态引用/恢复异常，先整改后验收。
6. **独立 PR 审核**：记录完整 Action Run ID（或 Ubuntu 本地报告、所用 commit SHA、命令、结果），确保 `PR13=PASS_SOFTWARE` 后才合并。**不因本次仅移除历史文件而自动重复完整 143h C1/C2**；如果发现真实科学输入变动则需重新评估重跑必要性。

**当前发现/障碍：** `PR #13@0d0cb090` 的 GitHub check-runs 返回 **0**，现有 Ubuntu/Docker Workflows 仅支持手动触发；旧代码 SHA 上的成功历史不是 PR #13 验收结果。当前连接没有可用的 Actions workflow_dispatch 操作，需由具有运行权限的工作环境手动触发或在本地 Ubuntu 执行上述命令；没有执行结果就保持 `REGRESSION_NOT_RUN`、不合并。

**S1 Done 定义：** Ubuntu+Python/G5 全通过，Docker AMD64 验证通过（或有批准的明确环境豁免）、冻结数据哈希与引用验证通过、验收证据回写 PR #13、合并 main 后新 SHA 静态检查。此门以前不得标 S1 PASS。

## S2：搭建选定范围原生 P1–P7 执行链（先契约后代码）

### 2A. 本次可立即开始的架构/入口审计
- 读取 `native_cpp/` P1–P3 CLI，`native_cpp/modules/p4_read62/data_prep/run_cpp_pipeline.py`、P5 `prepare_inputs` 和 `cteas_p5_smerge`、P6 `cteas_p6_native_hourly_driver` 与 143h 源链、P7 原生全小时 source/COMP 执行入口。**区分 reference/test oracle 与真正支持 CLI**，不得用对照测试包装成通用生产执行器。
- 提取输入/输出契约：`case.yaml` 与 grid/stack/research_time；`GEO.DAT`、`SURF.DAT`、`UP*.DAT`、`MET.DAT`、`puff.inp`、`puff.con` 的单位、格式、字节序、空间/时间轴、站点选择、缺测、上/下游异常状态、SHA。
- 固定第一版支持边界：选择一套与已测条件对应的场址/模式（例如 Hefei 冻结参数），确认其真实 P1–P7 **原生**执行；不把 2024 合成站网自动泛化成任意站数，也不开放湿沉降或未审物理选项。
- 使用独立 `NativeStageDescriptor` / `CaseDescriptor` / `ExecutionPlan` / `StageResult` / `RunManifest` 约定记录命令、输入哈希、输出路径与哈希、支持物理选项、启动/退出/重试状态。接口须有 `dry-run`，默认 fail-closed、输出写入新工作目录并原子发布。

### 2B. 分批实现/测试
1. **PR 2A（契约）**：入口清单、case/schema 规则、stage graph/输入输出合同、错误代码和静态检验单元测试。此步不改物理算法、不启用 G5 `all`。
2. **PR 2B（P1–P5 连接）**：统一调用现有已验证的 C++ P1–P3 和 P4/P5 原生写盘入口；分离数据下载、读取缓存、输入制备、数值执行，防止旧 Python orchestrator 静默调用 Fortran。可在已有字段/站数上做 dry-run 和合成/真实案例 smoke。
3. **PR 2C（P6 接口）**：将**已验证选定来源链**接入 run coordinator，处理小时序列、严格 DIM/站数/模式准入、`MET.DAT` 输出哈希、跨小时状态/失败后不污染后续执行。不得以 143h 验收推断任意长度或多站通用。
4. **PR 2D（P7 接口及统一端到端）**：接入已验证原生 P7 状态推进，生成完整 `puff.con` 和运行清单，检查非零浓度、真实时刻、记录数、结果重跑一致性、同气象原版对照。**禁止**从旧版 `engine.run_met/run_puff` 偷偷执行。
5. **PR 2E（可用性）**：在经过真正端到端验收的**明确支持组合**上逐项解除 `engine/gui_g5/pipeline.py` 相应 fail-closed 条目；不碰大 GUI workbench 双份重构。超出支持范围继续拒绝，结果/验收范围必须标注。

### S2 最终门槛
- 一条命令从受支持案例 YAML→P1–P5→P6→P7 产生 `MET.DAT`、`puff.con`、SHA/运行清单，且**不能调用原版物理后端**。
- 在与原版同输入且物理选项明确的实测/冻结案例上完成独立数值复核；把 P6 与 P7 同一 source SHA、状态迁移、质量与浓度验收量写进报告。超过某输入/配置支持范围必须 fail-closed。
- G5 可以运行的不代表任意场址通用，必须逐项扩展案例准入边界。

## S3：大案例数据按需恢复与真正瘦身

**先完成依赖登记，再迁移，不再以“它们在旧 CTEAS 中存在”为理由直接删除当前科学基准。**

1. 为所有被 CMake、C1/C2 Actions、`scripts/local_gate.py`、GUI/数据准备引用的冻结文件产出机器可读 `fixture_manifest`（相对路径、长度、SHA256、来源固定 CTEAS commit、源文件授权状态、使用者）。
2. 提供 `restore --case --verify --offline` 工具（默认只校验/不修改；显式恢复，写入隔离缓存；本地复用缓存；源站无效/网络失败/许可不满足均 fail-closed）。不能把第三方受限资产转传公开 GitHub Release/Artifacts。
3. 通过两种环境验证：新 clone + 已授权资产访问可以无歧义恢复；离线缓存且校验正确可以完整复用。相同版本在 CMake/C1/C2 的预检下 SHA/字节数一致。
4. 先迁移历史运行成果到受控长期存储（原始 `MET.DAT`、A/B/C/D `puff.con` 和完整时间/站点/源项/编译器元数据）。短期 GitHub Actions artifacts 到期时间 **2026-10-31**；不把仅有哈希的报告当原始二进制文件。
5. 只有**恢复/比较门槛通过并证明仓库外长期保留**，才另开 PR 删除现有 2022 参考 `MET.DAT`、`puff.con` 与 2023 大基准或原始气象文件。更新 CMake test prerequisites、Actions 恢复步骤、Docker 构建上下文；运行软件/科学回归。
6. 区分 **checkout 大小下降** 与 **Git 历史体积下降**。普通 PR 不重写 `main` 历史；若未来真要缩小 clone 包体积，需独立制定新仓库/带版本锚点迁移，不能强推覆写既有已验收提交。

**S3 Done：** 完整、受控、可溯源的机器可读文件清单 + 恢复器 + 离线/网络/损坏/缺失负例测试 + 实际长存储访问验证 + 所有使用者重新验收，无受限源码/数据泄漏。

## S4：物理选项逐项扩展与独立科学验证

按 `docs/physics/CALMET_CALPUFF_OPTION_MATRIX.csv` 逐行建立 **控件→原版代码入口→C++ 实现→输入模板→同输入比较→接受范围** 的闭环。

### 优先物理增量
1. **降水及湿沉降 P0**：先从锁定的 CALMET/CALPUFF 原版控制卡确定 `NPSTA>0`、`MWET>0` 的真实气象/降水文件模板、单位、缺测/小时归属/空间站网格式。**模板未证实前不得写假格式或以无雨数据宣布通过。** 再在 C++ 编写降水读取/湿清除，校验 0 降水、间歇雨、强降水、跨小时/站点边界、干湿过程并行和质量闭合。
2. **地形及边界层选项**：原版分支开关、特定地形测试、数值稳定性与适用距离；不能将已选修正推广为所有选项。
3. **烟羽抬升、稳定度、扩散及源项分支**：不同抬升/扩散/干沉降/释放时间/源型等逐选项验收；明确 `puff.con` 数组或二进制逐字节验收条件。
4. **综合与独立实测验证**：选定受监测场址/气象数据与原版同输入的可复核证据，单独区分**代码一致性**与**现实预测有效性**。新原版对照不能只比较零浓度。

每个物理 PR 必须提供旧/新源 SHA、原版 Fortran 实际执行证明、案例控制参数、数值分母/单位/差异分布、质量守恒与负例，及对应矩阵行更新。现有 C1/C2 仍做防回归，不扩大其科学覆盖；新选项只升级其自身验收标签。

**S4 Done：** 优先选项具有独立可重复实测和原版校核，矩阵状态准确；未实现和未验收项明确暴露、默认 fail-closed。**永远不因某一组选项 PASS 而宣布全 CALMET/CALPUFF 重构已完成。**

## 近期执行队列与责任界限

1. **立即：** 记录 S1 的 PR #13 head SHA，对其触发有权限的 Ubuntu/Python/G5 与 Docker software verification；取得可核验日志并回写 PR。当前本会话不能执行 GitHub Actions workflow_dispatch，报告中必须保持 `NOT_RUN`。
2. **可以并行的文档工作：** 完成 S2 2A “原生入口与 I/O 契约审计”、建立设计 Issue、记录 Stage 2 实验设计；不修改物理结果、不解锁 G5。
3. **S1 PASS 后：** 审核合并 PR #13，进入 S2 2B/2C/2D/2E 实现验证链。
4. **S2 成功后：** 实施 S3 的按需恢复（尤其及时解决 G3 原始文件长期保存）；之后逐一开展 S4 物理功能分支。

更新规则：每次对阶段状态的修改必须附带 **PR/commit、实际执行命令、日志或 Actions 链接、通过/未运行/失败数目和下一 blocker**。此计划不授权自动合并未验收的 PR、不授权公开第三方资产、不授权昂贵 143h 科学工作流在每次普通提交时执行。

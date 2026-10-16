# P6 CALMET A→G 顺序执行与验收台账

日期：2026-10-11。适用范围：合肥 2022-01-01 00:00 UTC 至 2022-01-06 23:00 UTC **144 个时间标签/143 个实际一小时时段**；5×5 km、50×50、100 m、9 层、UTM50N/WGS84。原版 CALMET 6.5.0 Level 150223。用户指令：**严格 P6A → P6B → P6C → P6D → P6E → P6F → P6G，先验收当前完整阶段，再进入下一阶段。**

**截至本轮原版独立验收（2026-10-11）最新有效门槛：P6A PASS；P6B PASS；P6C PASS_SCOPED_HEFEI_2022_OBSERVATIONS；P6D IN_PROGRESS / SOURCE_KERNELS_AND_SELECTED_DIAGNO_W_SEGMENT_PASS / FULL_2022_UVW_NOT_PASS；P6E/P6F/P6G 未通过整阶段验收（**P6F 写出器子项已实现：对 2022 冻结参考逐字节等价、E22/P7 双解码器交叉可读、未改动原版 CALPUFF 7.2.1 读取其产物跑通 143 时段；字段物理数值仍未验收**）；P6_CALPUFF_READY=FALSE。** 前文分期记录中标注的 P6C PARTIAL/HOLD 均为此前阶段的历史状态，不再代表最新结论。降水输入另行保持不合格，不能据此宣称湿沉降可用。详见 [P6C RDSN/CGAMMA 原版运行时最终审计](P6C_RDSN_CGAMMA_2022_AUDIT.md) 和 [CI #38113874913](https://github.com/RRain001/CTEAS/actions/runs/38113874913)。



### 2026-10-11 P6D8 WIND1 完成选定路径原版验收（覆盖此前 D6/D7 状态）

- **D7 中性 SIMILT**：[独立 CI #38123117424](https://github.com/RRain001/CTEAS/actions/runs/38123117424)，20/20 CTests、216/216 原版 U/V PASS，最大绝对误差 4.800071451427357e-11 m/s；PR #19 已合并。
- **D8A 真实格式逐小时观测适配器**：[CI #38124817807](https://github.com/RRain001/CTEAS/actions/runs/38124817807) 21/21 CTests、216/216 原版 SIMILT 对照 PASS；SURF/PREPDI 时次、有效掩码和站点身份显式检查；[PR #21](https://github.com/RRain001/CTEAS/pull/21) 已合并。
- **D8B WIND1 原版选定首猜三维风场**：[独立 CI #38125704104](https://github.com/RRain001/CTEAS/actions/runs/38125704104) 22/22 CTests PASS，六组人工场景 × 50×50×9×U/V = **270,000/270,000 分量 PASS**，原版比较器报告最大绝对误差 0.0 m/s，预注册阈值 2e-4 m/s；[PR #22](https://github.com/RRain001/CTEAS/pull/22) 已合并。原版 WIND1 L35829–36402、SIMILT L30097–30370，源 Git blob SHA 固定；细节见 [D8 专项审计](P6D8_WIND1_SELECTED_FIRST_GUESS_AUDIT.md)。
- **P6D 专属 Runner 与源码验证链**：[PR #20](https://github.com/RRain001/CTEAS/pull/20) 已合并；六个专项原版数值工作流最终同一 SHA 6/6 CI SUCCESS。使用 `lhy-desktop`、GitHub REST SHA-1 逐文件校验后备与 Job 独立 CMake 构建路径，解决 github.com:443 间歇失联及旧缓存交叉污染。

**D8B 是单地面站 + 单探空站、50×50×9、IEXTRP=-4、NBAR=0 的首猜网格风场独立原版数值等价，不是完整 DIAGNO。** D9 必须根据原版 DIAGNO 执行次序集成 WIND1→WINDBC→FRADJ→HEATFX/ELUSTR→SLOPE→INTER2→SMOOTH→DIVCEL→W；需确认各节点可用的实际原版气象驱动与边界条件，且与独立 P6E 地表物理子任务保持接口隔离。D10 再逐一验证真实 2022 年 1h/6h/143h 分层 U/V/W。**正式门槛保持 P6D=IN_PROGRESS、P6D_FULL_2022_UVW=NOT_PASS、P6_CALPUFF_READY=FALSE、P6_WET_FORCING_VALIDATED=FALSE**；不能根据上述人工场景 PASS 自动宣称全部 P6 通过。

### 2026-10-11 P6D6 INTER2 selected-path 原版对照 PASS（新增）

[独立原版 CI #38121613553](https://github.com/RRain001/CTEAS/actions/runs/38121613553) 在专用 Linux/X64 self-hosted Runner 上成功运行：C++20 / Fortran 11.4 独立编译，**19/19 CTests、4 组 50×50×9 原版 INTER2 U-component 90,000 次数值比较 PASS**，最大绝对差 `9.536745997351659e-7 m/s`（预设门槛 `2e-4 m/s`），没有超容差项；原始 vendor Fortran SHA 不变。支持范围仅原版 `IWFCOD=1, IPROG=0, NBAR=0, NOOBS=0` 下的 `INTER2` 观测-初始场融合，包括显式 LVARY 选项。来源：[专项审计](P6D_INTER2_SELECTED_ORIGINAL_AUDIT.md) / [PR #16](https://github.com/RRain001/CTEAS/pull/16)。

**P6D D6 原版内核已验收，但尚欠 WIND1/SIMILT、完整 DIAGNO 与 1h/6h/143h 2022 真实 U/V/W 对照，故 P6D_FULL_2022_UVW 仍为 NOT_PASS。** 本段覆盖下文仅涉及 INTER2 尚未验收的历史描述。

### 2026-10-11 P6D 原版数值验收：内核与选定连续计算片段（最新）

独立原版 Fortran 数值 CI：[SLOPE](https://github.com/RRain001/CTEAS/actions/runs/38113822845)、[DIVCEL](https://github.com/RRain001/CTEAS/actions/runs/38115350648)、[MINIM/WINDBC](https://github.com/RRain001/CTEAS/actions/runs/38115632414)、[SMOOTH](https://github.com/RRain001/CTEAS/actions/runs/38115873780)、[DIAGNO 最终风场片段](https://github.com/RRain001/CTEAS/actions/runs/38116193083)。固定原版 CALMET 6.5.0 的源 blob 437f43bb7f0e51a1919e56664663e1a046986ed0，原版源文件未被修改。独立源码提取、编译和验证均通过；已核对非零风场、原版边界、分层记录顺序以及预设容差。

DIAGNO L6119–6148 的选定片段完整通过 SMOOTH→全层 DIVCEL→由下往上 W 积分→WINDBC 的原版原位程序顺序对照：18/18 CTest、450,000 个 U/V/DIV/W 数值和 7,200 个边界分量无超限项；最大 W 差异约 5.1e-11 m/s。MINIM 在选定控制 IKINE=0 / IOBR=0 下不会实际执行，仅保留为独立原版分支验证。

严格门槛：这些人工输入/源码片段 PASS **不能**替代原版真实 2022 气象驱动下的 WIND1/SIMILT/INTER2、FRADJ/SLOPE 组合以及 1h/6h/143h 最终 U/V/W 验证。P6D_FULL=NOT_PASS；P6_CALPUFF_READY=FALSE；湿降水驱动 NPSTA=0、IPCODE 143/143 缺测单独保持不合格。
## 0. 执行纪律

1. P6A 与 P6B 已有独立 PASS 证据，无需重复设计；每次 CI 应维护不回退。实际观测数据选取与气象质量合格不能仅由原版 CALMET 正常终止来推出。
2. P6C 必须达到 **COMPLETE** 才允许开始 **P6D 的整阶段集成**。之前已经单独开发、并通过原版 Fortran 对照的 `FRADJ` 是 **预先完成的独立子程序**，保留代码和证据，但绝不据此将 P6D 标为 PASS。原则上不再新增 P6D 完整流水线，直到 P6C 验收完成。
3. P6E、P6F、P6G 各自保留独立数值门槛和 PR 审查证据；**不把模拟成功、记录字段对齐或近似数值相符互相替代**。
4. 原版 `engine/vendor/src/**`、P1/P2/P3/P4/P5 各自分支及公共基础 `60b7b1d` 不允许被 P6 写入。P6 原版参考链对 P3/P4/P5 使用冻结 SHA。
5. 当前主线以 `NOOBS=0`, `IWFCOD=1`, `IPROG=0`, `IRTYPE=1`, `IFRADJ=1`, `ISLOPE=1`, `IEXTRP=-4` 的真实 2022 合肥案例为目标。未经真实控制确认的可选历史参数均不能偷偷启用。原版 `NPSTA=0` 允许风和微气象参考跑通，**但不具备后续湿沉降的有效雨量驱动**。P6 与 P7 的降水/WET 验证分别单列。

## 1. 阶段台账

| 阶段 | 当前正式阶段状态 | 已固化的证据 | 下一次完整验收必须满足 |
|---|---|---|---|
| **P6A** 程序架构/输入与时间契约 | **PASS_SOFTWARE_CONTRACTS** | C++20 `-Werror` CTest，50×50/100m/9 层、显式观测有效性、时区和输入源门槛；旧样例 `CALMET.INP` 拒绝 | 保持回归，接口不得静默变化 |
| **P6B** 原版实算基准 | **PASS_ORIGINAL_REFERENCE_DRY_MICROMET** | [源 SHA 锁定独立原版 CI](https://github.com/RRain001/CTEAS/actions/runs/38107162904)；`MET.DAT` 64,762,556 bytes、SHA256 `968b2dd24f0eb4ad428709b52a154d9022e8c7e37a4be3fb9498e3d7e756d04e`；7,562 顺序记录、143 时段×45 字段 | 来源冻结、输出格式解码持续 PASS；降水基准另列，不要求用虚构雨量冒充 |
| **P6C** 几何、观测预处理 | **PASS_SCOPED_HEFEI_2022_OBSERVATIONS** | 既有 TERSET/DIAGI、GEO 20,000、SURF 1,144、UP 6,280、VERTAV 234、PREPDI 2,574、FACET 130；[COMP+RDSN 143h 真实运行时](https://github.com/RRain001/CTEAS/actions/runs/38113500059) AA/BB 286 个时次、RDSN 1,144 个输入值、858 时间字段、0 差异；[CGAMMA 143h 原版实时调用](https://github.com/RRain001/CTEAS/actions/runs/38113874913) 86/51/6 三分支 PASS，最大误差 5.0E-11 K/m；原版 MET.DAT 插桩前后 SHA 相同 | 本阶段**仅**验收固定 2022 一地面虚拟站、一探空站、GEO/SURF/UP 与 143h 观测输入的选定配置；其他格式、多站与缺测回填分支未纳入支持范围。雨量另列不合格，不妨碍无雨诊断风场开发 |
| **P6D** 三维诊断风场 | **IN_PROGRESS / VERIFIED_KERNELS_AND_SELECTED_W_SEGMENT / FULL_NOT_PASS** | 原版 FRADJ（既有）；[SLOPE PR #9](https://github.com/RRain001/CTEAS/pull/9) 270,000 U/V；[DIVCEL PR #12](https://github.com/RRain001/CTEAS/pull/12) 90,000 散度+36 峰值；[MINIM/WINDBC PR #13](https://github.com/RRain001/CTEAS/pull/13) 270,000 U/V/DIV+7,200 边界；[SMOOTH PR #14](https://github.com/RRain001/CTEAS/pull/14) 180,000 U/V；[DIAGNO W 片段 PR #15](https://github.com/RRain001/CTEAS/pull/15) 450,000 U/V/DIV/W+7,200 边界；全部合并到 P6 开发分支，仅证明指定原版源码片段的人工场景数值等价 | 尚缺真实 2022 观测驱动 WIND1/SIMILT/INTER2、FRADJ/SLOPE 和 DIAGNO 全路径集成，以及原版 1h、6h、143h 逐层 U/V/W、掩码和散度对照；不得宣称 P6D 完成 |
| **P6E** 地表与边界层 | **NOT_STARTED** | P6B 原版包含微气象字段格式，不代表 C++ 物理 PASS | `SOLAR`、`HEATFX`、`ELUSTR`、`MIXHT`、`TEMP3D`、`SURFVAR`、云量/RH/稳定度/混合层高度/地表参数全字段独立对照；白天、夜间、低风与稳/不稳定 |
| **P6F** `CALMET.DAT` 写出 | **WRITER_IMPLEMENTED / BYTE_IDENTITY_2022_PASS / ORIGINAL_CALPUFF_READS_IT / FIELD_VALUES_NOT_ACCEPTED** | 独立 C++ 写出器新子模块 `native_cpp/modules/p6_calmet/p6f`（库 + CLI `roundtrip`/`check`/`emit-fixture`/`write-from-p6d`）：冻结 2022 `met.dat` 重写后逐字节相同、SHA-256 仍为 `b1823cda…`；E22 契约读取器 6,435 个字段记录逐格一致；P7 独立解码器报告与原始文件完全相同；**未改动原版 CALPUFF 7.2.1 由 tracked vendor 源重建后读取本写出器产物，143 时段跑通，case A 的 `puff.con` 与仓库原版参考逐字节相同**；`write-from-p6d` 直连 P6D 真实 U/V/W 数组（143h，含验证状态闸门）；见 [P6F 审计](P6F_CALMET_DAT21_WRITER_AUDIT.md) | 用重建后的 P6D/P6E 场逐值对照原版（P6G）；写出合法文件/逐字节自证/原版可读都不等于数值正确；`IRTYPE=0` 无冻结参考，`NPSTA=-1` 仍拒绝，P6D `blend_*` 默认拒绝 |
| **P6G** 全链条科研验收 | **IN_PROGRESS / FIRST_END_TO_END_VERDICTS_RECORDED / P6F_P6D_MAPPING_DEFECT_FIXED / RERUN_ON_CURRENT_MAIN** | 2026-10-12 首次把三段串成一条可复现链路（`scripts/run_p6_end_to_end.py`：P6D 产出器 → P6F `write-from-p6d` → E15 观测桥 → P6E `emit-realcase` → 逐字段对照），两种口径（A 重建风场 / B 原版风场）各 45 字段判定齐备，A−B 差值单列；**发现并修复 P6F `p6d_fields.cpp` 的 U/V/W 平面索引置换缺陷**（P6D 平面为层主序 `i+nx*(j+ny*k)`，旧代码按 `cell*nz+level` 读取，静默置换整场；修复前 U-LEV1 对原版最大差 6.689 m/s，修复后 1.518e-03 m/s）；[PR #27](https://github.com/RRain001/CTEAS/pull/27)；见 [P6G 记录](P6G_END_TO_END_20261012.md)。合入后在当前 main `3be69bb` 复跑：A **11 PASS / 7 FAIL / 27 分母 0**、B **12 PASS / 6 FAIL / 27 分母 0**、A−B **15 PASS / 3 FAIL / 27 分母 0**（`T-LEV 2..9` 已产出；`T-LEV 5/6/7` 与 `ZI`/`WSTAR` 的超差归因于 P6E 而非风场） | 站点代表性/雨量/扩散结果仍未纳入；A 口径仍有 4 个字段超容差（USTAR/ZI/EL/WSTAR，当前 main 另加 T-LEV 5/6/7），其中 ZI/WSTAR/T-LEV 5..7 的主体误差已归因于 P6E 而非风场；P6D U/V 仍缺 SMOOTH/DIVCEL/WINDBC 与 FRADJ（GAMMA）段 |

### 2026-10-11 P6F `CALMET.DAT` 2.1 C++ 写出器：布局与逐字节证据 PASS（字段数值门槛仍开放）

- 新子模块 `native_cpp/modules/p6_calmet/p6f/`（分支 `codex/p6f-calmet-dat21-writer-20261011`）：库 `cteas::p6f` + CLI `cteas_p6f_calmet_dat21_writer`（`roundtrip` / `check` / `emit-fixture`）。布局依据未改动原版 `OUTHD` L12448–L12537、`OUTHR` L13067–L13237、`WRTR1D/WRTR2D/WRTI2D` L36734–L36881、`map.met` L5–L7，与 P7 读取器、P6E E22 契约互不共享代码。
- **逐字节自证**：读取 2022 冻结 `met.dat`（64,762,556 B、SHA-256 `b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30`、7,562 条记录、1,114 条注释、143 时段×45 字段）→ 以显式字段数组重新序列化 → 与冻结文件逐字节相同、输出 SHA-256 不变。该 CTest fail-closed 注册：冻结参考或 P7 解码器缺失时 CMake configure 直接失败，不会静默跳过。
- **交叉可读**：① E22 契约读取器 `cteas::p6e::read_calmet_dat21` 重读重写后的真实案例，6,435 个字段记录逐格逐位一致（并反向验证 P6F 可读 E22 写出的文件）；② P7 独立解码器 `original_decode_calmet_hourly.py` 对重写文件报告 `PASS_ORIGINAL_CALMET_EXPLICIT_TIME_AND_FIELD_LAYOUT`，且报告与冻结原始文件完全相同（含其自算 SHA-256）。
- **独立清点**：CTest 内 Python 记录遍历（记录框架、1,114×132 B 注释、176 B 控制块、十条静态记录的零时钟字、OUTHR 顺序、时间标签与 3600 s 区间、XMISS 对齐计数）与写出器 `check` 报告的逐字段分母/缺测数完全一致；冻结文件的小时字段不含 `XMISS`（0/16,087,500 单元），缺测路径由合成夹具覆盖。
- **fail-closed**：维数/站点数/静态记录长度不符、OUTHR 顺序错位、整数-实数类别不符、区间≠3600 s、时间不连续、声明运行窗口与正文不符、`NPSTA=0` 时出现 `RMM/IPCODE`、缺字段、非有限值、`ZICONV/DPTT/QH/USTAROLD` 等无文件表示的内部量，一律报错而非静默修补；负例（截断、记录标记损坏、标签损坏、静态时钟非零、区间秒数损坏）在 CTest 中必须失败。
- **未达成**：写出器只保证布局、时间语义、单位、掩码与“数值逐字节不丢失”，**不保证重建 2022 场的物理数值正确**；P6F 整阶段门槛中的“物理值正确”仍需 P6G 用 P6D/P6E 场与原版逐值对照。支持模式仅 `IRTYPE=1`/`IWFCOD=1`/`NPSTA>=0`；`IRTYPE=0` 与 `NPSTA=-1` 不支持（fail-closed）。
- **交付与门槛**：[PR #26](https://github.com/RRain001/CTEAS/pull/26)（base `main`）；权威本地门 `python3 scripts/local_gate.py --track p6f` → `LOCAL_GATE_P6F=PASS`（CTest + 原版 CALPUFF 读取专步，g++-12 Debug）。
- **第二轮：原版 P7 读取（v2.1 硬性条款）**：`tests/verify_original_calpuff_reads_written_calmet.py` 用 tracked vendor 源与仓库自身参考编译参数重建**未改动**的原版 CALPUFF 7.2.1（报告内固定编译器/SHA-256），在临时目录跑四种情形：A) 逐字节等价文件 → 143 时段跑通，`puff.con` 与仓库原版参考**逐字节相同**、`puff.lst` 仅差两行时钟；B) 只改数值（风×1.25、ZI×1.5、TEMPK+5 K，结构与时间标签不变）→ 143 时段跑通、时间窗回显不变、浓度变化且有限非负（均值 0.032848→0.029406、峰值 5.1697→4.6693）；C) `write-from-p6d` 吃 P6D 真实 U/V/W（143h）→ 143 时段跑通、浓度有限非负；D) 截断文件 → 原版中止（`Error termination`），不会误判为成功。
- **第二轮：P6D→P6F 入口**：一条命令 `cteas_p6f_calmet_dat21_writer write-from-p6d --fields <p6d-dir> --variant wind1 --w-field w_face --statics-from <合法 CALMET.DAT> [--irtype 1 --met-fields-from <合法 CALMET.DAT>] --out <CALMET.DAT>`；从 `metadata.json` 读 dims/layout/dtype/byte_order/zface/sentinel/hour_label，W 为"层顶面"（P6D face k+1 → `WFACE(k)`），静态记录/站点表/投影块来自 `--statics-from`；P6D 标记 `NOT_SOURCE_VERIFIED` 的 `blend_*` 默认 fail-closed，`w_face_*` 的 FRADJ pending 状态写入报告。
- **第二轮：P6D 真实产物重核**：以 P6D 重产目录 `/home/lhy/build/p6d/rw12`（producer head `84ca905e8`、目录树 SHA-256 `5bffb988…`、`blend.verification=PASS_REALCASE_BLEND_ORIGINAL_INTER2`，最坏 4.22e-05 m/s）重跑案例 C（`--variant blend`）：143 时段、浓度有限非负（均值 0.030696、峰值 7.5911、非零 52,403）。此前 `rw11` 的 metadata 仍写 `NOT_SOURCE_VERIFIED`，适配器据数据**拒绝** `blend`（fail-closed 在真实 metadata 上得到验证），机制为数据驱动、无需改码。
- **第二轮：P6D 变体重核（最终）**：以 P6D 推荐目录 `/home/lhy/build/p6d/rw17`（closed DIAGNO `blend_*`，1,865 文件、143 标签、目录树 SHA-256 `7d34bcc9…`、metadata `a36acd86…`；`blend.verification=PARTIAL_LEVELS_8_9_PASS_LEVELS_1_7_NEUTRAL_SIMILT_GAP`）跑案例 C：143 时段、浓度有限非负（均值 0.030236、峰值 5.2611、非零 31,701）；`inter2_*`（pre-tail，verdict `PASS_REALCASE_BLEND_ORIGINAL_INTER2`）作为诊断变体同样可写出；`windbc_*`（拼接边界，非网格场）明确拒绝。适配器只对生产者标注 `NOT_SOURCE_VERIFIED` 的变体 fail-closed，其余 verdict（含 partial/MIXING_HEIGHT_NOT_SUPPLIED）原样记入报告、不擅自升级为通过。
- **第二轮：关闭的开放项**：① XMISS 真实规模往返（50×50×9×143、167,310 个哨兵值、逐字段独立计数一致、P7 解码器接受、NaN 被拒）；② `ILANDU` 语义明确（原样写出不做范围拒绝；冻结案例 2,500 格全部 category 20 而 `NLU=14`，`check` 报告 `ilandu_max=20`/`ilandu_over_nlu_cells=2500` 并由独立扫描交叉核对）；③ `IRTYPE=0` 已实现（OUTHR L13160–L13180 依据，合成往返 + 独立结构核对）且 `NPSTA=-1` 按明确语义拒绝（MM5 降水掩码语义未实现）。

## 2. 新增 P6C 站点几何子模块：原版真实源码依据

- 原版 `engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for`: `DIAGI` **L5097–5117** 为探空站参考网格索引 `IIUP,JJUP`，按 `XUSTA/DGRID+1.5` 赋给 Fortran INTEGER，再收敛到 1–NX/NY；**L5123–5145** 为地面/探空站风场内部坐标 `IST,JST,UTMXST,UTMYST`；**L5163–5182** 为地面站粗糙度格网边界钳制及 `ZLOGSTA` 对数廓线高度系数。`READCF` **L29766** 的 `ZMID=0.5(ZFACE(k+1)+ZFACE(k))` 提供第一层中心高度（10 m）。
- 这里存在**两种不同的映射规则**：探空站参考格点用“+1.5 后取整并钳制”；地面/探空风站内部格点用“+1 后取整”，**原版没有对 IST/JST 全局钳制**，仅为选择 `z0` 网格执行边界钳制。研究域外的站点仍有物理位置，不能凭空放进 5×5 km。
- 现代源码：`native_cpp/modules/p6_calmet/include/cteas/p6/station_geometry.hpp`、CLI `cteas_p6_stations`、`p6_station_geometry_tests.cpp`。
- 独立验证 `compare_original_diagi_station.py` **从原版 calmet.for 提取不改变的实际 Fortran 行**，编译为原版源码片段驱动，与 C++20 跑相同人工场景。三组不同粗糙度、内站/外站/半格点/边界/不同风速计高度共 **42 条站记录，378 个对照字段**；最大浮点绝对差 `4.791997909592283×10^-10`，无不合格项。**这证明列出的 DIAGI 片段数值一致，不代表完整 DIAGI 真实气象执行一致**。
- 最新证据：[P6C DIAGI station source code parity CI PASS](https://github.com/RRain001/CTEAS/actions/runs/38107845203)（包含四项 CTest 的通过和 Fortran 片段编译/比较证据）。
- 本阶段实现会对非法坐标、非有限数、粗糙度零或风速计高度接近粗糙度造成零对数分母采取 fail-closed。原版不一定主动报错；此安全提升不宣称完全相同的错误行为。

## 3. P6C 下一验收工作包（顺序）

已通过 `C-READGE` 的 8 字段选定格式原生 Fortran 逐值对照；`C-MET-READ` 中 **2022 SURF.DAT 及 2022 UP.DAT v2.1 对应原版 RDSN/RDUPN 的选定格式和逐层 U/V 转换均已 PASS**；但 **原版 `PREPDI` 的选定 143h 时间插值数值已 PASS，但完整原版 `COMP` AA/BB 逐小时状态机仍未通过**；接下来依次推进 `C-HEIGHT-TIME`（`ZFACE`、`ZMID`、站高、探空层与时区端点一致性）再做 `C-INTEGRATION`（同一份原版输入的观测场比较和缺测统计）。**只有四项齐备且经独立 Fortran 片段或完整执行验证，才由 P6C → P6D。**

**最终门槛声明：`P6A=PASS`, `P6B=PASS`, `P6C=PARTIAL`, `P6D=INTEGRATION_HOLD`, `P6E=HOLD`, `P6F=HOLD`, `P6G=HOLD`, `P6_CALPUFF_READY=FALSE`。**

### P6C 新增 2022 真实读取证据（2026-10-11）

详见 [P6C_READGE_SURFACE_2022_AUDIT.md](P6C_READGE_SURFACE_2022_AUDIT.md)：[READGE 20,000 数值 PASS](https://github.com/RRain001/CTEAS/actions/runs/38109436038)；[SURF.DAT 原生 Fortran 1,144 数值、429 站/时值 PASS，且原版 P6 重新运行 PASS](https://github.com/RRain001/CTEAS/actions/runs/38109730617)。2022 SURF 缺测统计：风矢量 0/143、云量 0/143、**降水代码 143/143 缺测**。格式数值 PASS 不表示天气源数据正确，也不表示降水有效。C-MET-UP 选定格式和 U/V 转换已完成；真实 2022 AA/BB 时次、垂直插值及完整原版观测场比较仍是 P6C 的硬性阻塞。

### 2022 探空 RDHDU→RDUPN 路径纠正及实测对照

[探空读取独立审计](P6C_UPDAT_RDUPN_2022_AUDIT.md)；[真实 2022 Fortran/C++ 13 sounding / 785 levels / 6,280 numeric fields PASS](https://github.com/RRain001/CTEAS/actions/runs/38110557735)。原版 `calmet.for` 的 `COMP` 分派表明 v2.1 使用 **`RDUPN`**，而旧版 `RDUP` 不适用此案例。实际标记：`UPDAT_SELECTED_FORMAT_PASS`，`UPDAT_ORIGINAL_CONVERSION_PASS`，`UPDAT_AA_BB_TIME_INTERPOLATION_NOT_READY`；仍然不允许跳至 P6D 整阶段实现。

### P6C 实测 VERTAV / PREPDI / FACET 温度层面最新结果

[原始 CALMET Fortran 2022 单元对照 CI](https://github.com/RRain001/CTEAS/actions/runs/38111692047) 对 `VERTAV` 的 234 个层平均 U/V（原版完整子程序提取），`PREPDI` 的 2,574 个分层逐时 U/V（原版指定时间插值源码片段与独立时次索引），`FACET+INTP` 的 130 个模型层界面温度（原版两个完整子程序提取）均 PASS。详见 [P6C_VERTAV_PREPDI_FACET_2022_AUDIT.md](P6C_VERTAV_PREPDI_FACET_2022_AUDIT.md)。注意：这并不证明 `COMP` 的全部状态机，也不能取代微气象模块和 P6D 诊断风场。正式标记维持 `P6C_PARTIAL`、`P6D–G_HOLD`。

### P6C 2026-10-11 真实 COMP 双缓冲 + 三源联合输入进展（保持整阶段 PARTIAL）

本次新增 `comp_buffered_timeline.hpp`、`comp_joint_main.cpp`、`check_joint_observation_2022.py`、`original_comp_runtime_trace.py`，以及软件测试与原版独立验证。详细审计 [P6C_COMP_JOINT_2022_AUDIT.md](P6C_COMP_JOINT_2022_AUDIT.md)。

- [原版 Fortran 143 时段 COMP 双缓冲运行状态 PASS](https://github.com/RRain001/CTEAS/actions/runs/38112842109)：286 个物理 AA/BB 探空时次，429 个时间/秒相关检查，11 次 `JUSTA/JORDER` 切换与 C++ 一致，0 mismatches；临时插桩前后原版 MET.DAT SHA256 相同。没有修改 vendor Fortran 原文件。
- [真实三源联合场候选链与原版数值核验 PASS](https://github.com/RRain001/CTEAS/actions/runs/38112477819)：GEO 50×50、SURF 143 小时、UP 13 探空；1/6/143 时段，143×9×2=2,574 U/V 与 5,148 个 AA/BB 层面温度关联值通过，地面站/时间/云量/温度/风有效性掩码一致。最大 U/V 误差约 `5e-10 m/s`。
- **原版 `MAXSEP=14 h`** 是 `calmet.for` 的 `data maxsep/14/` 固定常量（L3654），不是 CALMET.INP 的可配置 24h。已纠正原生默认限制，测试 15 h 缺测 fail-closed；频率严格检查原版 `abs(IUPSEC)<NSECDT && IUPSEC != 0`。
- 仍欠原版 `RDSN/CGAMMA` 联动及完整观测掩码/输入场执行状态验收。不能因 COMP 状态 PASS 就认定 `P6C_COMPLETE=TRUE`，也不能开始 P6D 整阶段。
- P5 SURF 的降水 `IPCODE=9999` **143/143 缺测**；原版 `NPSTA=0`。`P6_WET_FORCING_VALIDATED=FALSE`、`P7_WET_DEPOSITION_VALIDATED=FALSE` 独立保持。

### P6C 正式选定配置验收结论（覆盖前面的分期 PARTIAL 状态）

独立证据：[原版真实 143h RDSN/COMP PASS](https://github.com/RRain001/CTEAS/actions/runs/38113500059)；[原版真实 143h CGAMMA 与完整 P6B 回归 PASS](https://github.com/RRain001/CTEAS/actions/runs/38113874913)；[专项最终报告](P6C_RDSN_CGAMMA_2022_AUDIT.md)。通过了 1h→6h→143h 地形、地面观测、探空原始字段与垂直/时间风温插值源对照；`COMP` 物理 AA/BB 286 个时次、`RDSN` 1,144 个原版实际地面气象值、858 个时间关联值及 143 个 `CGAMMA` 直减率均为 **0 超限项**。温度直减率三路径样本为普通插值 86、当时次干绝热 51、先前对流记忆修正 6。插桩前后原版 `MET.DAT` SHA256 严格相等。

**决策：`P6C_SELECTED_CASE=PASS_SCOPED_HEFEI_2022_OBSERVATIONS`，P6D 的完整三维诊断风场集成可以开始，但绝不把已经 PASS 的孤立 `FRADJ` 误称为 P6D 完成。** P6E–P6G 仍未验收，`P6_CALPUFF_READY=FALSE`。湿驱动方面，真实 SURF `IPCODE=9999` 143/143、`NPSTA=0`：`P6_WET_FORCING_VALIDATED=FALSE`，`P7_WET_DEPOSITION_VALIDATED=FALSE`，与 P6C 选定配置通过彼此独立。

### DGM 原版内部状态导出：写只插桩重跑（2026-10-12）

详见 [DGM_INTERNAL_STATE_DUMP_20261012.md](DGM_INTERNAL_STATE_DUMP_20261012.md)。用与冻结案例**完全相同的输入**，对**未修改**的原版 CALMET 6.5.0 加**只写**插桩（`subroutine comp` 内 5 个点 + 文件末尾追加 `DGMSTATE`，vendor `calmet.for` sha256 `430381b4…` 未变），同一编译器同一组 flag 编译两份二进制并各自跑完 **143 个一小时区间**：**插桩前后 `MET.DAT` SHA256 同为 `b1823cda…`，且等于冻结参考**（未插桩那份不产生任何 dump 文件，否则 fail-closed）。

导出 `CALMET.DAT` 不记录的内部状态：整网 50×50 逐小时 `ZICONV`/`DPTT`/`ZI`/`QH`/`USTAR`/`EL`/`RHO`/`TEMP2D`/`WSTAR`（`dgm_state.bin` sha256 `e6b8ab30…`，715 条记录 = 143 小时 × 5 点；元数据与台站 3×3 邻域另附）。dump 第 4/5 点的 `ZI`/`WSTAR` 与冻结 `met.dat` 自身字段**逐格完全相等（143×2,500 格最大绝对差 0.0）**，证明 dump 就是产生冻结参考的同一内部状态。

结论：P6E 的三处残差**不在 `QH`**（台站 3×3 内 `QH` 相对跨度约 1e-4），而在 `DPTT` 记忆——`DIAGNO`→`STHEOR`→`ELUSTR2`→`MIXHTST` 先为地面站所在格单独刷新 `DPTT`（经 `/TJMP/` 直写），随后整网 `MIXHT` 再使用它；其余各格进入 `MIXHT` 时携带的是**上一小时**的 `DPTT`。用 dump 自身数值代入原版 `MIXHMC` 公式，可把台站格与邻格的 pre-`AVEMIX` `ZICONV` 复现到 1e-4 m（第 6 小时 985.4585 / 1222.6009 / 1006.5546 全中；把台站格的“新” `DPTT` 代进邻格也会得到同样的凸起）。`AVEMIX` 再把 1222.60 m 平滑为冻结文件中的 1036.44 m，`WSTAR` 与 `T-LEV 5–7` 同源。本节只记录该证据，不改变既有 `P6E=HOLD` 等阶段结论。

### DGM 第二轮：P6D 两项请求的原版内部状态（2026-10-12）

详见 [DGM_P6D_INTERNAL_STATE_REQUESTS_20261012.md](DGM_P6D_INTERNAL_STATE_REQUESTS_20261012.md)。仍为**只写**插桩、同一冻结输入、143 区间重跑：插桩前后 `MET.DAT` 同为 `b1823cda…` 且等于冻结参考，未插桩那份不产生任何 dump（否则 fail-closed）；第一轮 `dgm_state.bin` 逐字节复现（`e6b8ab30…`）。

**请求 1（`similt` 拿到的 `zii`）**：插桩点在 **`ELUSTR2`**（`calmet.for` L6893，`call similt` 之前；链路为 `COMP`→`DIAGNO`→`STHEOR`→`ELUSTR2`→`MIXHTST`，不是 `DIAGI`）。143 条逐时记录含 `zii`、该例程输入与进入时的 `ZI/ZICONV`；与第一轮第 4 点 `ZI`（上一小时 AVEMIX 后）**最大绝对差 0.0** 交叉验证通过。结论：`zii` 一般**不等于**网格 `ZI`——按 `zface(k) <= amax1(zii+0.001,zimini)`（`ZFACE=0,20,40,80,160,320,640,1200,2000,3000`，`ZIMIN=50`）计算，**143 小时中有 50 小时层数不同**；P6D 指的 nh 82（2022-01-04 09:00 UTC，`QQH=-30.17 W/m²`）处网格 `ZI=659.966 m` 而 `zii=153.341 m`，层数 6→3；最大偏差是 nh 10（网格 1009.95 m vs `zii=50.0`）。

**请求 2（`SLOPE`/`DIVCEL` 前后整网场）**：插桩点 7/8/9/10 分别位于 `DIAGNO` L5723（`SLOPE` 后）、L5726（加法前）、L5732（加法后）、L6148（`DIVCEL` 与 `W` 积分后，另加 `U/V`）。六个小时（1/2/3/81/82/83）已入库，其余 137 小时留在构建机并附全部记录偏移。结论：**`USLOPE/VSLOPE` 在第 2–9 层恰为 0**（仅第 1 层非零，≤0.0687 m/s），故坡流加法不可能产生第 3 层倾斜；第 10 点的 `U/V` 与冻结 `met.dat` 的 `U-LEV/V-LEV` **逐格完全相等（0.0）**；P6D 引用的 `U-LEV 3` 倾斜（去均值 spread 0.0106、`dU/di=-1.30e-05`、`dU/dj=+3.78e-05`）正是第 1 小时，而同一小时第 8/9 点的 `UG` **在加法之前就已带有该倾斜**（`-1.466e-05 / +4.263e-05`，spread 0.0238）——倾斜源自初始场，`ADJUST`+`SMOOTH`+`DIVCEL` 只是把它从 0.0238 压到 0.0106（第 82/83 小时反而增强）。本节只记录证据，不改变既有阶段结论。

### DGM 第四轮：地面观测装配与高空列导出（P6D 第 17 轮请求，2026-10-12）

详见 [DGM_STATION_ASSEMBLY_20261012.md](DGM_STATION_ASSEMBLY_20261012.md)。按 P6D 在 PR #23 第 17 轮写明的请求逐条实现：**只写**插桩（`PREPDI` L13906 / `DIAGNO` L5958 / `COMP` L4392 与 L4423 共 4 点 + 文件末尾 4 个子程序，vendor `calmet.for` sha256 `430381b4…` 未变），同一编译器同一组 flag 编译两份二进制并各跑完 **143 小时**：**插桩前后 `MET.DAT` SHA256 同为 `b1823cda…`，且等于冻结参考**（未插桩那份不产生任何 dump，否则 fail-closed）。

产物 `dgm_station.bin`（sha256 `87935090…`，1,813,760 字节 = **436 条 × 4,160 字节**：`int32[16]` 头 + `float32[1024]`）覆盖 (a) 进入分析前的地面站列（`US_ENTER/VS_ENTER`，仅第 1 层有值）与 `DIAGNO` 逐站调整后的列（`US_ADJUSTED/VS_ADJUSTED`）、(b) `RDUPN` 的 AA/BB 探空列（高度/U/V，最多 99 层）与 `VERTAV` 的 9 层平均（`UAVERAA/VAVERAA/UAVERBB/VAVERBB`，含 `justa/ntzaa/ntzbb/jusdt` 时次上下文）；请求 (c) 的 `UG/VG` 由第二轮已审计 dump（`e32b4388…`）切出同样 6 小时（`ugvg_p6d_hours/`，sha256 `b2bc3cfe…`）。请求的 6 小时（P6D 索引 17/18/41/42/47/48 = UTC 2022-01-01_18/19、2022-01-02_18/19、2022-01-03_00/01 = packed `202200118/119/218/219/300/301`）在文件中；dump 覆盖全部 143 小时。

**结论**：第 1 层"风速计高度→`ZMID(1)`"调整**不改变**该层风速——143 小时中插桩前后第 1 层最大差 **9.54e-06 m/s**（本 deck 风速计高度 10 m 恰等于 `ZMID(1)`=(0+20)/2=10 m，中性对数因子为 1），故第 1 层残差不可能来自观测装配或该调整，只能来自分析权重（`INTER2`/`ADJUST`），与 P6D 判断一致。调整后的列在混合层顶以上保持 `EDIT` 缺测（如 `202200118` 仅 2 层、`202200301` 有 5 层有效）。

**层序/站序校验**（Main 特别要求）：`/UPMET/` 探空数组为**站主序**（`uaa(mxus,mxlev)`，元素 `(iu,k)`，upmet.met L5-6），而 `VERTAV` 输出与 `/D1/` `US/VS`、`INTER2` 的 `STDAT1(mxnz,*)` 为**层主序**（`calmet.for` L3612-3613 / L32290 / d1.met L12 / L8226）。数值校验：用与原件相同算法（插入格面 + 梯形积分，L32317-32399）重算的 `VERTAV` 层平均与 dump **全部 2,574 个层平均**（143 小时 × 2 探空 × 9 层）最大绝对差 **1.73e-04 m/s**；探空高度列在 143 小时内**零处非单调**；`justa` 与 `ntzaa/ntzbb` 自洽（`202200118`：AA=202200200、BB=202200112、`justa=-1`）。本节只记录证据，不改变既有阶段结论。

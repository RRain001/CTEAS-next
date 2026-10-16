# P7 以 CALPUFF 原版执行顺序为准的实现盘点（2026-10-12）

本文件是 **功能与数值验收盘点**，不是宣称整套 CALPUFF 重构完成的报告。原版基准为 `engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for` SHA256 `da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568`。

## 1. 数量口径：核心计算程序、已接线驱动、最终验收不能混算

`native_cpp/modules/p7_calpuff/src` 有 39 个 .cpp（含独立 probe、诊断 CLI）；其中约 **24 个是实用模块/工具实现**，并非 24 个原版 CALPUFF 主流程阶段。已通过的 58 项 CTest（上一版完整跑）以及 P7O–P7X 若干 Fortran 单元对照，主要证明局部代码、局部公式和特定案例输入，**不能把 58/58 写成 CALPUFF 功能 100% 完成**。

| 功能群 | C++ 目前情况 | 独立对照情况 | 端到端情况 |
| --- | --- | --- | --- |
| 控制文件、精度契约、Fortran records、CALMET21 气象数据 | 已有实现 | 2022 真 MET.DAT 及 REAL*4 网格检验 PASS | 是输入保障，不是整个求解器 |
| 经纬度预处理→puff.inp→MET.DAT 的网格/点源 | 已有审计及 QA REAL*4 接口 | 2500 网格受体与 1 个源的原版 QA PASS | 内部 `XPT1GRD/YPT1GRD` 另需校验 |
| P7O 释放调度、INJECT、初始 COMMON 状态 | 有独立模块及 Fortran harness | 有独立数值测试；最近将内存状态强制 REAL*4 并加严格 oracle | 尚无完整点源/烟团调度器 |
| P7N/P7W 抬升、RISEWIND | 有局部模块 | 原版局部对照 | 未接到原版 COMP 整体循环 |
| P7V/P7X 平流、单烟团采样与位置步进 | 有局部模块 | 数值对照及 DGM 元素试验 | 未接到 143 h 多烟团统一状态循环 |
| P7D/P7Q sigma 扩散与更新 | 有局部模块 | 已有原版单元对照 | 不等于 `SETPUF` 全部状态闭合 |
| P7R/S/T 地形、P7H/I/M 地形耦合和 CTSG | 有局部模块 | 存在独立 Fortran 对照 | 完整时空 receptor source loop 未接线 |
| P7F 干沉降 | 有局部模块 | 干沉降独立检验 | 未完成所有 puff-state/输出耦合 |
| P7E 受体与 `CONC.DAT` 结构 | 有结构解析/采样模块 | 结构测试 | **未实现等价 `WROUT1/AVET` 全写出链** |
| P7C `PuffTransport` | 早期绝对 UTM 米坐标 + double 插值原型 | 自身 smoke/质量守恒通过 | **不是原版 CALPUFF COMP 算法，不得作为权威驱动** |
| 2022 原版 Fortran 143 h 运行 | Fortran 已运行且退出码 0 | `puff.con` 约 1.896 MB | 只是 **原版参考值**；C++ 未建立数值等价 |

**整体计算可交付性：完整 143 小时 C++ 原版等价求解器 = 未完成。** 不用单一完成百分比误导；若以“初始内部状态、1h、6h、143h、`WROUT1/AVET` 和浓度数值”6 个整阶段验收来数，当前尚无这 6 个阶段全部达成的 C++ 全流程证明。本轮仅推进第 1 阶段的源端内部 XY 和 COMP 逐步顺序契约。

## 2. `calpuff.for` 内同一个 COMP 采样子步的原版顺序

以下顺序由仓库已冻结的 **写出式原版 Fortran 插桩** `dgm_puffstep.json`、`original_puff_step_dump.py`、P7X 原版 inline span 确立：

| 顺序 | 原版 `calpuff.for` 行 | 动作 |
| --- | --- | --- |
| 1 | 10347 | 新旧烟团 sampling cadence |
| 2 | 10473 | 读取 `XPB/YPB/ZPB` 旧烟团/slug 状态 |
| 3 | 10487 | `GETCELL` 相关气象格点/粗糙度/稳定度输入 |
| 4 | 10495 | `PUFFDZ` 给出 `ZTOP/ZBOT` |
| 5 | 10499 | `ADVECT` 取该层 `UADV/VADV` |
| 6 | 10528 | `RISEWIND` 与静风调整完成 |
| 7 | 10548–10582 | 取子步 `TSAMP`，含 `XSAMLEN` 限制 |
| 8 | 10607–10619 | `DISTM, DXMOLD/DYMOLD, XNEW/YNEW` |
| 9 | 10942 | `SETPUF` 提交当前步状态 |

**限制：** 这张表只说明原版 COMP 单烟团计算子步的先后次序，不代表已经审计完整主程序从读取、`POINTS1`、`COMP`、receptor concentration 到 `WROUT1/AVET` 的所有跨子程序调用/条件分支。每个计算内核被实际调用后才允许推进 `VendorSubstepOrder` 状态机；仅完成状态机顺序测试不能声称完成主求解器。

## 3. 本轮新增的 fail-closed 验收

- `vendor_order.hpp`：C++ `VendorSubstepOrder`，严格拒绝错误次序、重复步骤、遗漏 `SETPUF` 以及不完整阶段结束；它是以后唯一允许的新集成调度层的基础，不调用旧 P7C RK2 模型。
- `tests/vendor_order_tests.cpp`：测试正确走通多子步/每类错误次序拒绝。
- `reference/audit_vendor_order_and_dgm.py`：实际读取 **Latin-1 原版 `calpuff.for`**，逐行校验 DGM 已冻结 COMP 插桩位置和源 SHA；再验证独立插桩不改变原版 `puff.con` 哈希，核对 DGM 首小时和 143 小时元数据连续/记录数。
- `tests/initial_dgm_oracle_tests.cpp`：在真实 `puff.inp` 中的 **原始 REAL*4 计算边界**内，将 `(X−XORIGKM)/DGRIDKM` 得到的源点相对网格坐标与冻结 **首小时 1275 条原版 DGM 记录**中“新烟团首次采样子步”的 `XOLD/YOLD`、`XPB/YPB` 比较；C++ `new_puff_state` 写入值需要等于同一原版内部坐标。高度由 DGM 原版值输入，只检查存储，因此**不代表抬升高度求解器等价**。
- 新增独立 Runner Job `original-execution-order`，使用通用 `[self-hosted,Linux,X64]`，并且 Fail Closed：任一冻结原版输入缺失、CTest 没注册、实际有差异，都不显示 PASS。

## 4. 1h/6h/143h 与输出闭合的准确路线

原版完整 DGM 已捕获 **143 小时、254,687 个子步记录、每条 352 字节**，基准 SHA256 `cbbdaa29c6222e6ca6aefe9f605ad13e7dd6d258f6ad243afcac07cb578108c6`；首小时有 1275 条、448800 字节切片（Git 内已冻结 SHA256 `b51d20d3cd1085902342d5b6d6b2f34c4a84c96d4966b63a2b1231c126087c89`）。未提交的 **完整 89.65 MB 原版 DGM** 需从原始捕获或同配方重新生成后按 SHA 严格校验，用作全部子步数值参照，不能凭目录中的 JSON 统计量推算 C++ 历史轨迹。

1. **第 0 道：** 本轮首小时源端内部 XY 和 COMP 顺序的 CTest/CI 必须真实 PASS；失败则先修源端精度或阶段次序。
2. **第 1 道（1h）：** 连接原版 `POINTS1→COMP` 单源/多烟团逐步求解，逐子步对比上述 DGM 记录的 `XOLD/YOLD/ZOLD`、`UADV/VADV`、`TSAMP`、`XNEW/YNEW`、`SIGYB/SIGZB`、`QM/QU` 等状态；不得用独立的 P7C RK2 原型冒充。
3. **第 2 道（6h）：** 扩展到前 6 个连续小时；必须逐步核对 `ROLLDN/SWAP` 及新旧烟团数组更新、小时边界、旧烟团状态。
4. **第 3 道（143h）：** 对整段 143 小时全量原版 DGM 进行逐条对照，报告 `total cases`、不匹配数、最大绝对/相对/ULP 偏差、首个不匹配小时与烟团索引，不能只给“PASS”文字。
5. **第 4 道（输出）：** 原版 `WROUT1` 所需文件头、数组排列、种类与累积浓度的 `AVET` 条件以及物种、受体、时间平均处理，先对照原版 Fortran 源码条件分支，后写对应 C++ 输出，比较所有结构记录和有效浓度数值。
6. **最终：** 比较整套 C++ `puff.con` 与 Fortran 原版数值；报告变量级差异、最大误差、质量守恒、时间索引；确认完整合肥 2022 冻结控制文件与 MET.DAT 的原版数值等价后，才可让 P7 PR 离开 Draft。

`MWET=0` 为此次冻结案例的明确范围。此前约定的降水/湿沉降仍单列为后续验收，不能偷算作当前 P7 整体通过。

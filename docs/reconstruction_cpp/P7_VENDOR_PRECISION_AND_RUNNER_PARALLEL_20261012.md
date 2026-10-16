# P7 原版数值精度和自托管 Runner 并行验收 (2026-10-12)

状态：**实现已提交，新增 CI 必须实际通过后才能宣布精度验收完成**。本文件的分组不替代后续 P7 whole-case / puff.con 原版数值等价验收。

## 原版数值类型原则

权威源包括 `engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for`、`pt1.puf`、`puff.puf`、实际 Fortran 编译器和 `native_cpp/modules/p7_calpuff/reference/build_original_calpuff.py` 中的原版编译参数。

- 默认 `REAL`（未声明其他 kind）：使用原版编译环境的四字节 `REAL*4`，C++ 内部对应 `VendorDefaultReal = float`。
- 显式 `DOUBLE PRECISION`、`REAL*8`：保留八字节，对应 `VendorExplicitDouble = double`。不能因为部分变量采用双精度就将所有 CALPUFF 浮点过程提升至双精度，也不能将显式双精度变量强制转换为单精度。
- COMMON BLOCK `/PT1/` 中的 `XPT1GRD`、`YPT1GRD`、`HTSTAK`、`QSTAK` 与 `/PUFF/` 中的 `XPB`、`YPB`、`ZPB`、`QM`、`QU`：在原版包含文件里使用默认 REAL；相应 C++ COMMON 对应 `VendorPointCommonReal`、`VendorPuffCommonReal`。
- 原版默认 `INTEGER` 为四字节，对应 `VendorDefaultInteger = std::int32_t`。
- 公开 C++ 测试 / 探针结构体中部分字段目前仍以 `double` 表示输入或报告值。移入原版计算链时须先将参数转换到对应的 Fortran 变量精度，确保计算顺序/运算节点和原版一致。**不能把诊断接口的 `double` 视为原版计算精度证据**。
- P7C `PuffTransport` 是独立的绝对 UTM 米坐标原型，其双精度插值/积分与原版相对网格单位烟团推进 **不能划等号**。原版路径应使用 P7O/V/P/X 等已采用 `REAL*4` 内核的实现，继续由 vendor 对照门禁约束。

`original_precision.hpp` 提供统一的**类型命名与校验**，不是“自定义统一双精度”。原版文件及 CASE 冻结文件未修改。

## 有证据的类型验收

`reference/audit_original_precision.py` 使用原版固定格式第 1–72 列扫描源程序的 POINTS1、INJECT、ADVECT、COMP、SETPUF 子程序，记录其中的显式双精度、四字节类型声明及 `IMPLICIT` 规则；检查两个 COMMON 包含文件中的变量；再用原版 `build_original_calpuff.py` 的相同 `FLAGS` 编译、执行一个独立的 Fortran `storage_size` 探针，核对默认 REAL、显式 REAL*4、双精度和整数存储字节数，并以 JSON 保存机器证据。如果原版脚本新增全局浮点提升选项，必须 fail closed。

`tests/original_precision_contract_tests.cpp` 提供 C++ 编译期别名检查，并以合肥冻结案例 `puff.inp`/MET 网格单精度舍入过程检测 `3533.76904296875` 与 `3533.769287109375` km 两个不同的原版边界值，阻止“所有坐标同一双精度精算”式回归。

验收规则：必须同时得到 Fortran 类型探针 PASS、C++ 精度契约 PASS 和原版 QA / `MET.DAT` 网格数值验收 PASS，才可关闭输入级类型边界。进一步还需原版 XPT1GRD 内部状态、1h/6h/143h 烟团过程和 CONC.DAT 数值等价验收，当前尚未以此宣告完成。

## Runner 并行方案与隔离

新增 `.github/workflows/p7-precision-and-parallel.yml`，`runs-on: [self-hosted, Linux, X64]`，按不可变提交分发以下**五个独立 Job**：

1. `precision-kind-audit`：原版 Fortran 类型声明、真实编译探针及 C++ 类型测试。
2. `source-parity-shards (release-transport)`：P7O/P7P/P7V。
3. `source-parity-shards (dispersion-rise)`：P7D/P7N/P7Q。
4. `source-parity-shards (terrain)`：P7R/P7S/P7T。
5. `source-parity-shards (sampling)`：P7E/P7H/P7I/P7M。

这些模块具有独立原版 source parity 测试；分组仅编译各自必需的 C++ 目标，不再让全部物理模块挤占单一串行 Job。结合原有 `p7-coordinate-qa` 和 `p7-scoped`，在具备兼容标签的空闲 Runner 下，可以让多个 Job 同时运行。

**物理资源限制：** 不应把 16 个 Runner 实例当作 16 台独立计算机。矩阵当前 `max-parallel=4`、各 lane `cmake --build --parallel 1`；每个 Job 都记录 `RUNNER_NAME`、`hostname`，便于检查是否实际在多台主机运行。P7 原版整体 reference / 2022 输入计算仍沿用 `lhy-desktop-3` 以避免对一个未审计的通用 runner 假定 Fortran 计算环境稳定。P6 工作流未修改。GitHub App 无仓库 Runner 管理读取权限，因此本次不声称已列举 16 个 Runner 的精确标签或负载。

为确保总体验收不被轻量 Job 掩盖，完整 `p7-scoped` 也会执行 Fortran 精度审计，不能跳过精度门禁。历史 2023 和合肥 2022 参考验收仍需 separate original run 和明确的浓度数值判定。

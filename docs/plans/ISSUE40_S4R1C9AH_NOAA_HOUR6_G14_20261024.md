# S4 R1c9ah：真实 NOAA 第六小时 17 阶段与 G14 原子提交的受限科学对照（2026-10-24）

## 案例与验收边界

Issue #40，唯一 Draft PR #308。目标为 2022-06-01 06:00–07:00 UTC，第六小时；82×85×9，2SS/1US，63 个 WATER 网格。使用 Ubuntu 私有固定六小时 CALMET 6.5.0 Fortran trace 和原版 MET.DAT 作为**只读独立数值参考**；原版字节**没有**进入原生 C++ 模型输入。本轮未重新执行原版 Fortran 六小时，复用既有哈希锁定的独立原版产物并在比较器中核验。所有原版、原生科学二进制和日志留在 Ubuntu 本地 `local-science`，不得提交公开仓库。

固定 met.inp、GEO、SURF、UP 输入 SHA256：
- met.inp `c5e6b02ac623a3f7d11b464deca657cd26285605753ef185bcc215257dee9744`
- GEO.DAT `5feaa58e5835576b3ae2c03a51e955114d620a7aeb710ded58a9f999695f602a`
- SURF.DAT `6a3f45eebdba8c7b783b5b89d5e1b3a7eecf2ce71f7fdaa814e7a54f04a9f655`
- UP.DAT `a4e99dabe6ed246643bb298c3d883c8cde8a5dd07aaa346952f7e096d325ad00`
- 原版 6h MET.DAT `a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14`

原生 GCC 12 / Release fresh build SHA256 `c4fd115f7e7d3656ed2dcecb87fc2a07d1f4ca535a535f67889d611b126df038`；源码基线为 `4ad34cfd67039773b5244761092377ceb6a0782e` 加本批未提交改动，**不是** frozen exact-SHA full 的证据。

## 本轮复算与原版独立数值比较

| 第六小时阶段 | 比较 REAL4/字段值 | 位级一致 | 冻结容差超差 | 结论 |
|---|---:|---:|---:|---|
| G26A/G22 stage3–6 | 181,220 | 155,599 | 0 | PASS_SCOPED |
| G23/G24 stage7–11 | 446,080 | 390,135 | 0 | PASS_SCOPED |
| G26B stage12 | 48,790 | 36,098 | 0 | PASS_SCOPED |
| G26B stage12–15 | 132,430 | 94,068 | 0 | PASS_SCOPED |
| P6F stage16 precommit | 313,650 | 248,915 | 0 | PASS_SCOPED |
| G14 commit candidate stage16 | 313,650 | 248,915 | 0 | PASS_SCOPED |

第六小时 G14 opt-in 执行实际退出 `0`，独立检查了失败回滚、fresh actor 正向提交和站点时钟发布；原生提交输出与未发布 P6F 候选 **逐字节相等**，SHA256 `66d7a47b9c4f57950fb7939d81c8c2dbc864665a838f701c7e5935584348427c`。所有阶段保留早先冻结的原版比较容差，未调整阈值。`G22/G23/G24/G26B/P6F` 的原版 trace 比较是科研测试数据证明，**不授权**默认通用生产执行器运行超过已接受小时；不将程序自检或本报告冒称为他人的独立科学审核。

软件层本轮 GCC 12 编译目标 `cteas_p6g_g65_noaa_firsthour_atomic` 成功，`cteas_p6g_g14_unified_hourly_tests` 的指定 CTest 1/1 PASS，第六小时 Python 对照器及拒绝测试 27/27 PASS；`git diff --check` 成功。开发工作树尚未冻结时这些仅为定向 DEV_ONLY；项目规定的 `cteas_native_full.py` exact-SHA 软件 full、GitHub `ubuntu-native-full`、第三方/非 Bot 同 SHA 科学审核尚 **NOT_RUN**。

## 仍未完成

- 通用可配置 P6 唯一生产执行器需在 C1、C2、真实 NOAA 第六小时及第二组场址/选项对照验证；科研 opt-in 的 G65 运行不是生产准入。
- S4-P7 尚未开展新场址真实 CALPUFF 7.2.1 源项/受体/扩散同输入对照；湿沉降等未覆盖物理选项不得宣称等价。
- S4 exact-SHA Ubuntu native full、GitHub required checks、他人独立科学审查均按真实执行结果另行记录；正式 Docker full 与双架构镜像交付在 S5 之后。
- PR #308 必须保持 Draft，不添加 `science-validated` / `merge-verified`，不自动合并，直到适用准入真正满足。

本地完整证据：`/home/lhy/dev/CTEAS-next/local-science/s4-r1c9ah-hour6-reverify-20261024/`（私有）；JSON 分项结果、源/原生 SHA256、G14 日志和退出码均保留。

# S4 R1c9af–ag：第五小时 COMP/P6F/G14 源物理验证（2026-10-24）

## 范围
Issue #40、唯一 Draft PR #308。Ubuntu 工作树 /home/lhy/dev/CTEAS-next/worktrees/s4-integration。真实 NOAA 2022-06-01 六小时 82×85×9 / 2SS+1US / 63 WATER；原版 CALMET 6.5.0 冻结输出与原生 C++ 分离读取。此任务不能授权通用 P6/P7，也不能把第五小时预提交当作 G14 正式发布。

## 本轮新实现
- 仅扩展第五小时 hour_index=4 显式 opt-in 的 G52/G53/G63 水陆分区、G26B stages12–15 和 G64 P6F stage16，重用既有已验证数学/物理内核，不放宽默认生产 guard。
- 当前第五小时同一真实 G14 frame 的 G26A 0–11 阶段与 G26B 12–15 / P6F stage16 保持同源因果状态；预提交之前 G14 已提交小时数和站点时钟不改变。
- 第五小时 G14 采用全新 actor 做失败回滚、字节一致验证、站点时钟 preflight、正向提交和第六小时只读 preview 检查。此项结果必须以原生实际命令退出码为依据。

## 固定数据 SHA256
- met.inp: c5e6b02ac623a3f7d11b464deca657cd26285605753ef185bcc215257dee9744
- GEO: 5feaa58e5835576b3ae2c03a51e955114d620a7aeb710ded58a9f999695f602a
- SURF: 6a3f45eebdba8c7b783b5b89d5e1b3a7eecf2ce71f7fdaa814e7a54f04a9f655
- UP: a4e99dabe6ed246643bb298c3d883c8cde8a5dd07aaa346952f7e096d325ad00
- 原版 COMP 六小时 trace: 4851f7be2d19df7a6e5e2cf5d73653c282cfea579b9c0b2444365a842d27a02e
- 原版 MET.DAT 六小时: a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14
- 上述原版数据属于此前锁定运行证据，本轮没有新运行 Fortran。任何原版私有输入/输出均只留 Ubuntu，不提交 GitHub。

## 已独立比较的实际数据

| NOAA 第五小时阶段 | 比较总数 | 位级一致 | 超出冻结容差 | 科学状态 |
|---|---:|---:|---:|---|
| G26B MIXHT stage12 | 48790 REAL4 | 40683 | 0 | PASS_SCOPED |
| G26B COMP stage12–15 MIXHT/AVEMIX/WSTARR/TEMP3D | 132430 REAL4 | 116752 | 0 | PASS_SCOPED |
| G64 P6F stage16 单小时 CALMET.DAT 45 字段预提交 | 313650 (45×6970) | 248716 | 0 | PASS_SCOPED_PRECOMMIT |

原生真实数据 SHA256（顺序 stage12、stage12–15、P6F）：b609063b08d8f0d34262b8b4bae8b9b52b26a14d979bdb78a448f7ff8b716bb4、61ce5810e92dc455fb7436fa6035356c5fc2a6740904f9b74591299d48fd3c6b、ef845b3beaa750e540ab6c0682c778e63121169187a3c6eeeb648b632b6e38f1。

独立原版比较 JSON SHA256（同顺序）：fe656deeccdcb890ed83ef54985bfb517a7ff8b39b1c46bf4a3f4140c954e55e、b0df0b8545e46d3a3894a952b515187311f6a7ee61a33415435d4db1cc2d584f、66472b91b04ea161049852cc268567db1122acb3a990f2e2b18fc80a81f2be46。

所有原始二进制/JSON/运行日志位于 Ubuntu 私有目录 /home/lhy/dev/CTEAS-next/local-science/s4-r1c9af-hour5-native-comp-20261024/，未上传公开仓库。

## G14 原子事务与第六小时继承
G14_TRANSACTION_STATUS: PASS_SCOPED_TRANSACTION_ONLY
- Ubuntu 原生 GCC12（没有运行 Docker）第五小时新 G14 二进制 SHA256 e4f1917a466dd93c9a5a7195300365e3d2d9f55e1ff903ac733446cdb6a94014。
- 实际命令 exit=0；源输出位于 /home/lhy/dev/CTEAS-next/local-science/s4-r1c9af-hour5-native-g14-20261024/。先在同一真正第四小时 G14 已提交历史上故意失败回滚；确认 completed_hours=4、ZI/ZICONV/DPTT、原生站点时钟无变化；然后用全新 Actor 完整重跑 17 stage，检验源 P6F 字节相同，再正向提交到 completed_hours=5，站点时钟发布。
- 正向提交时写出的第五小时 P6F 候选 SHA256 ef845b3beaa750e540ab6c0682c778e63121169187a3c6eeeb648b632b6e38f1，与前面经独立 Fortran 原版 313650/313650 验证的预提交候选严格同 SHA，绝没有将原版数据喂给 C++。
- 失败回滚、正向提交及第六小时只读预览三个独立真实输出字段均 PASS；第六小时 preview 继承第五小时的 ZI/ZICONV/DPTT、正确时钟和 committed memory，但第六小时17个物理计算阶段仍 NOT_RUN。
- 此项仅为第五小时 G14 受限研究模式，不等于一般生产 P6 接受，不代替真实同 SHA 独立科学审核。

## 后续和新软件规则
- 本轮使用 Ubuntu 原生 GCC12 编译、局部 CTest/定向 Python 单测与原版数值比较。无 Docker full；S4/S5 正式软件审查按 docs/ci/S4_S5_NATIVE_POST_S5_DOCKER_POLICY_20261024.md 使用冻结 SHA 的 ubuntu-native-full；正式 Docker 交付放在 S5 之后。
- 当前研究 worktree 还不是科学发布候选 exact SHA。独立科学审查 NOT_RUN、通用 P6 NOT_ACCEPTED、P7 NOT_RUN、S4 全验收 NOT_ACCEPTED。
- 下一阶段：完整原生第六小时 G14，45 字段原版比较；统一生产 P6 执行器在 C1/C2/非合肥及另一配置上重验，然后 P7 原版 CALPUFF。

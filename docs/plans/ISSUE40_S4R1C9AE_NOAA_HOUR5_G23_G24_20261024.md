# S4-R1c9ae: NOAA 第五小时 G23/G24 风尾数值独立对照

## 范围和来源
- Issue #40 OPEN，PR #308 Draft；此分支仅为原版选定模式的 test-only 验证，**不代表生产 P6 准入**。
- 2022-06-01 NOAA 02–08 UTC，82x85x9、2SS/1US、63 WATER；第五小时结束于 UTC06，hour_index=4，所有 1–4 小时均采用原生 G14 因果状态提交。
- 原版 CALMET 6.5.0 source SHA256 835c351d780c0200be721c2d9cbb8dc45b3a8fcd4cb8815fc47bbd26a56a7b23。原版 6h stage90/100/110 风尾轨迹 SHA256 755fe44499ac8a53f3f959f29cdb28c1515ba6da1d719f198a78813fe9016995：R1c9p 已验证 instrumented 原版 MET.DAT 与未改原版完全一致。本次复用锁定的原版轨迹，**未重新运行 Fortran**。
- 同源输入 SHA256：met.inp c5e6b02ac623a3f7d11b464deca657cd26285605753ef185bcc215257dee9744；GEO 5feaa58e5835576b3ae2c03a51e955114d620a7aeb710ded58a9f999695f602a；SURF 6a3f45eebdba8c7b783b5b89d5e1b3a7eecf2ce71f7fdaa814e7a54f04a9f655；UP a4e99dabe6ed246643bb298c3d883c8cde8a5dd07aaa346952f7e096d325ad00。

## 新代码和受限计算
- G23 添加第五小时 opt-in，检查真实 hour_index、P5 风有效站数、三维格网及前一小时状态，互斥拒绝其他小时 trial。
- G26A/G65 在同一个原生 G14 frame 上，直接从第四小时正向提交后的因果状态计算第五小时 G22→G23/G24 stages7–11；输出 INTER2、SMOOTH、DIVCEL/W stage90/100/110 二进制科学 trace。
- 同时保留 G66 脱离路径与原生 live G22 的字节一致性断言、station clock 与 committed ZI/ZICONV/DPTT 不变。原版 trace 只进入 Python 独立 comparator，不进入 C++。
- 只有显式第五小时 test-only CLI 能开启，默认 G22/G23/G24 科学生产门禁继续 fail-closed。第五小时 G14 没有提交。

## 2026-10-24 Ubuntu 实际试验
- 私有输出：/home/lhy/dev/CTEAS-next/local-science/s4-r1c9ae-hour5-native-windtail-20261024-run01。
- GCC12 Docker DEV_ONLY run dev-20261024T033036-74a04da3：G65/G14 targets 构建 PASS，G14 CTest 1/1 PASS，退出 0；二进制 SHA256 480dfa6d0c3715c3652bfc91793ea72b90c2a1643fb1019e5f5f3e0a602e7218。
- 真正 NOAA G65 第五小时 stage11 源码本机执行退出 0，native trace SHA256 d5591905881261d688b04dfa633cfc87a3cfae873ed2ee3da515cd72a9b7eca1。
- 同源独立比较器按原冻结 2e-4 m/s 风速绝对阈值：**446080/446080 REAL4，0 超差，360924 bitwise equal**；状态 PASS_SCOPED_HOUR5_G23_G24_STAGE90_100_110。独立 JSON 报告 SHA256 728f69c3e7b2dbae68e62f9a4208d992d0c7e841f0129a50f8a678917040ac11，仅保留 Ubuntu。
- S4 Python 123/123 PASS；compileall PASS，Git diff --check PASS。初版测试路径导入错误已修复后重测；直接脚本运行缺 PYTHONPATH 曾失败，正确 python3 -m scripts.s4.s4r1c9ae_compare_hour5_windtail 已真实 0 退出。
- 当前研发 HEAD 为 WIP 时的 Git dirty 状态；不借用旧 SHA 的 Docker full/正式科学 CI 身份。

## 继续开发和验收限制
- 第五小时 COMP stages12–15、P6F stage16 独立原版 45 字段、G14 原子回滚与正向提交：NOT_RUN。
- 第六小时 17 阶段、统一生产 P6 C1/C2/新场址、P7 与 P1–P7、独立科学审查：NOT_RUN/NOT_ACCEPTED。
- 继续同一个 S4 功能批次研发；不得为本微步骤新增 PR、不得降低容差，也不得把 test-only 变成未验证生产入口。

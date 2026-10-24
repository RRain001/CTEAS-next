# CTEAS-next S4/S5 原生验收与 S5 后 Docker 交付政策（2026-10-24）

本政策经用户授权；优先于以前要求在 S4/S5 每个研发 PR 强制执行 Docker full 的历史说明。仅适用于 CTEAS-next，不改变 cufotri/cteasFOAM 的验收规则。

## 阶段职责

| 阶段 | 强制完成 | 延后 |
| --- | --- | --- |
| S4（Issue #40/#36） | Ubuntu 原生软件编译/测试、真实同源原版 CALMET/CALPUFF 数值比较、连续状态/质量守恒、同一生产可执行文件 C1/C2/新场址、冻结 SHA 原生完整软件测试、独立科学审查和 GitHub 必需检查 | 正式 Docker 交付与跨架构验收 |
| S5（Issue #161） | 原生回归、规模容量、内存、分块和性能负载、冻结 SHA 原生完整软件测试、适用独立审查和 GitHub 必需检查 | 正式 Docker 交付与跨架构验收 |
| S5 完成后 | 冻结发行 SHA，执行 Docker verification full、AMD64/ARM64 镜像、runtime 入口和受限用户验证、部署和产物 provenance、最终回归与发布记录 | 不得用原生 PASS 冒充 Docker PASS |

Docker 可以在开发期用于自愿的快速诊断，但不再是 S4/S5 的强制科研阶段门禁；它与原版物理科学验收是不同维度。研究 PR 仍不可仅凭定向 DEV_ONLY 小测试合并。

## Ubuntu 原生软件门禁（exact SHA）

只在完整功能批次冻结且工作树 clean 后，从 Ubuntu 当前 CTEAS-next 开发工作树运行：

    /home/lhy/dev/infra/s4-noaa-env/bin/python scripts/ci/cteas_native_full.py run --worktree "$PWD" --output-root /home/lhy/dev/reports/cteas-native-full --jobs 8

脚本要求 Python 3.11+ 和原生 GCC 12。当前 Ubuntu Python 3.11 环境位于 `/home/lhy/dev/infra/s4-noaa-env`，需实际具备适配的 `GDAL==3.4.1`、`rasterio==1.4.4`、`pyproj==3.7.2`、PyYAML 等 S2G 依赖。不能把系统默认 GCC 9/Python 3.10 作为受检工具链。

该脚本执行 11 个强制步骤：native_cpp CMake Release 编译、CTest、S4 Python；另在**同一冻结 SHA** 中独立构建 `native_cpp/p1` 和 `native_cpp/p3` 并分别运行 CTest，给 S2G 全部 Python 测试提供编译产物（`P1_CASE_BINARY`、`P2_D3_GLCC`、`P12_OLD_ADAPTER`、`P2_GLCC_TEST_DRIVER`、`P2_GEN_CLI`）；最后执行 S2G Python。禁止通过缺省路径、预留历史二进制或跳过测试伪造软件 full。

日志和 manifest 记录所有步骤、环境中的受检二进制路径、命令、SHA256 和退出码，`verify` 校对每一步固定命令与环境配置。成功仅代表原生软件 PASS_SOFTWARE_SCOPED；缺依赖或任何失败均不可发布成功状态。

逐项复核：

    python3 scripts/ci/cteas_native_full.py verify /home/lhy/dev/reports/cteas-native-full/<run-id>/manifest.json --expect-sha <40-char-SHA>

当同一 SHA 已推到 GitHub PR 后，先进行无写操作审计：

    python3 scripts/ci/cteas_native_full.py publish <manifest.json> --pr 308 --dry-run

确认通过，移除 --dry-run 才向精确 PR HEAD 发布 ubuntu-native-full 成功 commit status。S5 使用实际目标 PR 编号。软件证据为 PASS_SOFTWARE_SCOPED；scientific_acceptance 仍 NOT_RUN，docker_delivery 仍 DEFERRED_UNTIL_POST_S5。代码工作树变更、SHA 漂移、少测一步、失败退出、日志被改、未执行时，不得发布。

## GitHub 准入和禁止绕过的门禁

.github/workflows/pr-admission.yml 的 repository-admission 对源码 PR 接受精确当前 HEAD 上的任一有效软件成功状态：ubuntu-native-full 或旧的 ubuntu-docker-full。二者都不存在/失败时继续阻止合并。GitHub main 受保护的 repository-admission 和 scientific-admission 检查必须保留。

scientific-admission 未改动：科学源码/测试 PR 必须离开 Draft、具有真实独立审查支持的 science-validated，且另一个非 Bot 真实人员在当前 SHA 提交 APPROVED review。auto-merge-approved.yml 继续要求适用检查成功和由验证后添加的 merge-verified；不能因延期 Docker 添加任何科学通过或合并标签。

项目现有 .github/workflows/docker-portable.yml 继续保留手动入口，正式发布验收应在 S5 完成后执行并记录完整 SHA、构建镜像、测试和结果。发行门禁尚未运行时应明确为 NOT_RUN，而不是 PASS。

## 不变的科学职责

- S4：P6 原版逐时 45 字段、ZI/ZICONV/DPTT、AA/BB/CGAMMA、G14 正向/回滚、混合水陆面；P7 原版 CALPUFF 烟团质量和浓度，C1/C2 和新场址不同配置与独立科学审查。
- S5：延续且不得破坏 S4 科学阈值，另验动态规模/性能/内存和支持范围。
- 原版源码与真实私有数据仅在 Ubuntu 留存，禁止上传 GitHub 公共仓库。
- 历史受限 PASS_SCOPED 不自动升级为通用生产或 Docker 交付 PASS。

更新记录：2026-10-24 复现并修复 S2G 原生 full 的缺失编译产物、Ubuntu 默认 GCC9/Python3.10 与旧 P2-B 工作流契约。源码在 PR #308 受限科学试验分支提交；正式 exact-SHA full 结论须引用本次修复后具体 manifest，不能沿用先前失败或 DEV_ONLY 证据。S5 与最终 Docker 交付尚未运行。

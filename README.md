## 2026-10-24 S4-C 真 NOAA WATER 六小时原生 G14 与原版对照通过（最新）
- G65 第六小时原生完整17阶段actor不改数值公式与前5小时共享，同一参数化 S4B2/G14 `--selected-experimental --water-sixthhour-g14-trial-only --hours 6 --probe-prefix-hours 6`，真实82×85×9/2SS/1US/63 WATER NOAA输入，连续6小时102原生物理阶段、P6F 270字段、G14 ZI/ZICONV/DPTT/AA-BB-CGAMMA原子状态提交且要求完整窗口。hour6水面USTAR/EL仅来自hour5已提交**原生**P6F，G43只在detached模型副本中补原始COMP五个非风缺测量，真实P5风/降水观测不改；绝不将原版Fortran结果当数值求解器输入。
- 独立原版固定6h MET SHA `a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14` vs 新原生S4B2完整6h MET SHA `32d9f049b1739e1d568a0f7ba65bf9d3718d8bd1c1b7dcdb147c94d41a4753b3`：**270字段/1881900值、1508074逐位一致、冻结容差0超差**，hour1..6 逐小时位一致 298578/239527/231976/240362/248716/248915，六小时每小时各0超差；结果 `PASS_SCOPED_S4C_SHARED_SIXHOUR_FORTRAN_270`，仅固定一个NOAA场址/站点配置，非通用生产P6/P7验收。原版Fortran本轮没重跑，独立审计 `scripts/s4/s4c_compare_noaa_unified_threehour.py --native-hours 6` 仅后验只读原版。公开报告 `docs/plans/ISSUE40_S4C_SHARED_G65_SIXHOUR_G14_20261024.md`，私有JSON `/home/lhy/dev/reports/cteas-s4c-unified-20261024/s4c-shared-sixhour-vs-original.json`。
- 任务依然必须执行：新提交精确SHA源native full/verify/publish，旧commit软件status不能继承；之后同SHA C1/C2 143h、第二独立实际原版输入站点配置、原子rollback试验和真人非Bot科学审核。科学admission继续阻止合并，PR #308保持Draft，不加 science-validated/merge-verified、不合并；生产P6/P7仍NOT_ACCEPTED。

## 2026-10-24 S4-C 统一 S4B2/G14 真实 NOAA 第五小时 WATER 通过原版对照（最新）
- 已将 G65 原有第五小时完整17阶段原生 actor 不改数值公式移入共享头，S4B2 新专用研究 flag `--selected-experimental --water-fifthhour-g14-trial-only --hours 6 --probe-prefix-hours 5`，82×85×9/2SS/1US/63 WATER；同一 G14 真正完成前五小时 P6F、ZI/ZICONV/DPTT 与 AA/BB/CGAMMA 原子提交。hour5 WATER USTAR/EL 源自 **hour4 已提交的原生 P6F**，G43 五个非风 COMP 缺测只在 detached G14 模型输入内处理，原始 P5 wind/precip 未变，独立原版 MET.DAT 严禁作为原生物理输入。
- 固定只读原版 Fortran 6h MET SHA `a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14` vs 新统一 S4B2 5h MET SHA `41d505e8bc00701b506f6b566fdbe4c2ef3f2400fbc28b94b9130320d1b4cab9`，离线固定原版对照 **225字段/1568250 数值，1259159 逐位一致，冻结容差 0 超差**（hour1–5 逐时 298578/239527/231976/240362/248716 bitwise，每小时0超差）。同一最新二进制分别重算1/2/3/4h MET.DAT SHA 全部与此前代码逐位一致。原版 Fortran 本次未重新跑。仅 `PASS_SCOPED_S4C_SHARED_FIVEHOUR_FORTRAN_225`，不意味生产 P6/P7 科学入场。公开证据文档 `docs/plans/ISSUE40_S4C_SHARED_G65_FIVEHOUR_G14_20261024.md`，私有原生/原版对照 JSON `/home/lhy/dev/reports/cteas-s4c-unified-20261024/s4c-shared-fivehour-vs-original.json`。
- 新增 fifthhour 研究 opt-in 互斥与负向测试：P6 模块定向 CTest7/7 PASS，已有同一 third/fourth/fifth-hour CLI 负向脚本及3–6h外部科学读数比较器继续复用。最终代码冻结新 exact SHA 后必须运行 Ubuntu native full/verify/publish；旧SHA软件门禁不可继承。下一步仅第六小时 G65 actor接入现有G14、原生hour5 P6F WATER历史、G43非风源和 Fortran 270字段对照，再C1/C2 143h、第二独立场址/配置、非Bot审核。科学入场仍阻止 PR #308 合并；PR Draft、无 science-validated/merge-verified，不合并。

## 2026-10-24 S4-C 真 NOAA WATER 第四小时已接入统一 S4B2/G14（最新）
- 与 G65 科研原版复用**同一个第四小时 17 阶段 native actor**，仅允许显式 `--selected-experimental --water-fourthhour-g14-trial-only --hours 6 --probe-prefix-hours 4`、82×85×9/2SS/1US/63 WATER，跨小时真正从 hour3 原生 P6F `USTAR/EL` 提取下一小时水面历史，继承 G14 ZI/ZICONV/DPTT、原生 station clocks，G43 仅在第四小时 detached 模型源补原始 CALMET COMP 的五个非风缺测，保持原始 P5 风/降水不变。默认 G26/P6 生产模式不开放。
- 只读锁定 Fortran 6h MET SHA `a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14` vs 新统一 S4B2 4h MET SHA `412aabb4dfa0ef02af80a70a5ba0dca63fb15ac541ded53a0bb43b484e93177d`：独立**180字段/1254600 数值，1010443 逐位一致，冻结容差超差 0**，四小时逐小时超差均0；用最新二进制重算 1h、2h、3h 原生 MET 输出 SHA 均与旧版完全一致。原版 Fortran 本轮未重跑，且未作为求解器数值输入。仅固定真实 NOAA 四小时 `PASS_SCOPED_S4C_SHARED_FOURHOUR_FORTRAN_180`，不等于通用生产 P6 科学验收。科研报告 `docs/plans/ISSUE40_S4C_SHARED_G65_FOURHOUR_G14_20261024.md`；私有证据 `/home/lhy/dev/reports/cteas-s4c-unified-20261024/s4c-shared-fourhour-vs-original.json`。
- 同一独立比较器增加 `--native-hours 3|4|5|6` 而不复制脚本；第三/第四小时共享 research CLI 负向验证代码（P6 专项 6/6 CTest PASS）且保护提交/模式边界。此轮须在源代码新 clean SHA 上 native full/verify/publish 后才能声明 GitHub 软件通过；下一步第五、第六小时、最新SHA C1/C2 143h、第二独立配置和非 Bot 科学审查，P7 尚阻塞，PR #308 Draft 不加科学合并标签、不合并。

## 2026-10-24 S4-C 统一 S4B2/G14 第三小时 WATER 原版对照通过（最新）
- S4-C 同一参数化 S4B2 新研究专用选项 `--water-thirdhour-g14-trial-only --hours 6 --probe-prefix-hours 3`，复用 G65 三小时原生完整17阶段 actor，第二小时**已提交的原生 P6F** 提取 USTAR/EL 真实 WATER 前态并检查 source clock，G14 ZI/ZICONV/DPTT 跨小时原子传递。G43 第三小时真实观测非风缺测仅限 detached COMP 源修复，不改原始 P5 风/降水，原版 Fortran MET.DAT 不输入求解器。各科研开关与生产 G26 独立并持续 fail-closed。
- NOAA 原版固定六小时只读 SHA `a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14`，新 S4B2 三小时 MET SHA `a80edb2467807635c2c1ea6e285533c6981f4469e41fc4dcf0031a2a035b1989`，独立逐字段对照 **135字段/940950数值，770081逐位一致，冻结容差0超差**，每小时超差均0；既有 1h/2h 输出 SHA 新程序重跑完全不变。原版 Fortran 本轮没有重跑。结果 `PASS_SCOPED_S4C_SHARED_THREEHOUR_FORTRAN_135`，仅针对固定 82×85×9/2SS/1US/63 WATER NOAA 三小时案例。公开说明 `docs/plans/ISSUE40_S4C_SHARED_G65_THREEHOUR_G14_20261024.md`，私有 JSON/原生文件 `/home/lhy/dev/reports/cteas-s4c-unified-20261024/`，严禁上传原始 Fortran 源码/数据/输出。
- 新增 thirdhour 显式 opt-in、错误输入/开关互斥负向模块 CTest（5/5 PASS）及独立 Python SHA/损坏/输出覆盖防护测试（3/3 PASS）。本次代码新 SHA 冻结完成后需运行 Ubuntu exact-SHA 正式 native full/verify/publish；旧提交 software success 不自动继承。后续 hour4 继续 G65 原生 P6F 水面历史和 G43 模型内部五非风补缺，之后 hours5/6、C1/C2 143h 与第二独立场址、非 Bot 科学审查。生产 P6/P7、科学入场未完成，PR #308 保持 Draft，不合并。

## 2026-10-24 S4-C 统一可配置 S4B2 第二小时 WATER G14 原版对照通过（最新）
- G65 原生第二小时完整 17 阶段 actor 未改公式，提取至与第一小时共同的共享头；同一 S4B2/G14 执行器新增 **严格研究-only** `--water-secondhour-g14-trial-only --hours 6 --probe-prefix-hours 2`，真 NOAA 82×85×9、2SS/1US、63 WATER，首小时原子提交的 ZI/ZICONV/DPTT 和 station clocks 直接传递第二小时，不改原始 P5 风/降水，不利用 Fortran MET.DAT 回填求解器。
- 原版 Fortran 固定6h MET SHA `a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14` 对独立原生 S4B2 2h MET SHA `30eb55977283f7b9c09a4002e9781d32e1d58af30ac408e15959d8c928d9f0f3`：**90字段/627300值、538105逐位一致、冻结容差0超差**；小时1/2分别 298578/239527 bitwise。首小时独立重跑 output SHA 与上版完全一致，确保首小时无回归。本轮原版 Fortran 未重新跑。私有报告 `/home/lhy/dev/reports/cteas-s4c-unified-20261024/s4c-shared-twohour-vs-original.json`，源码报告 `docs/plans/ISSUE40_S4C_SHARED_G65_TWOHOUR_G14_20261024.md`。结果仅 `PASS_SCOPED_S4C_SHARED_TWOHOUR_FORTRAN_90`，**不等于第三至六小时/C1/C2/生产P6/P7通过**。
- 增加禁止不带 opt-in/非2h/混用旧 WATER-only 标志的模块 CTest 4/4 PASS、独立 Python 对照安全测试。当前研发改动须以新提交 clean exact SHA 正式 native software full、verify、PR HEAD 一致后才可发布软件 success；PR #308 继续 Draft、science-admission 缺非 Bot 审核不得合并。下一步小时3 用前2h G14 原生 P6F 状态 G66 的水面历史、G43 小时3 的站点非风补缺，统一 G14 继续核原版。

## 2026-10-24 S4-C 同一 S4B2 完成真实 NOAA 第一小时 G14/P6F 原版对照（最新）
- 将 G65 的 **原样** `G65RealNoaaFirstHourActor` 提取为共享头，原 G65 research CLI 与统一 S4B2 都使用该物理 actor；新 S4B2 `--selected-experimental --water-firsthour-g14-trial-only --hours 6 --probe-prefix-hours 1 --out ...` 必须真实 G41/G43 水陆来源、2SS/1US、82×85、63 WATER 与完整 6h 观测时钟，只运行第一小时 17 原生阶段和 G14 原子提交。其它生产与默认 all-land Guard 完全保留。
- Ubuntu 私有真实 NOAA 2022-06-01 01–02 UTC first-hour native `MET.DAT` 与只读固定原版 Fortran 6h 文件独立对照：45 字段 ×6970 网格=313650 数值，298578 逐位一致，冻结阈值 **0 超差**；本轮原版 Fortran 未重新运行。代码科学报告 `docs/plans/ISSUE40_S4C_SHARED_G65_FIRSTHOUR_G14_20261024.md`，私有文件/对照 JSON `/home/lhy/dev/reports/cteas-s4c-unified-20261024/`。这是 `PASS_SCOPED_S4C_UNIFIED_FIRSTHOUR_FORTRAN_45`，**不意味着 hours2–6、生产 P6/P7 与跨案例已被验收**。
- 新增水面第一小时显式 opt-in 负向 CTest、原版对比 SHA/来源隔离 Python 测试；未修改任何数值方程、固定容差或独立评审门槛。下一步接 G65 hour2 的 P6F 原生历史、G43 每小时补缺、跨小时 G14/时钟验证，然后 hours3–6、C1/C2 与第二场址。当前源码有新增变更时，旧提交的软件 full 不可自动继承；在 clean 新 SHA 软件 full/PR status 核验后同步新证据。

## 2026-10-24 S4-C 统一 P6 WATER 来源预检（非物理阶段验收）
- S4B2 `--selected-experimental --water-source-preflight-only` 在同一可配置入口调用 G19/G38/G14 真实源码入场、六小时 UTC/站点时钟，接受 NOAA 82×85×9、2SS/1US、63 WATER，报告 `PASS_SOURCE_ONLY`，但**不**计算 G26/G26B/P6F、不写 CALMET.DAT、不解除 G65 研究模式，`PRODUCTION_ADMISSION=NOT_ACCEPTED`。现有 S4B2 默认模式对含 WATER 数据仍正确拒绝 `G18D3 all-land HFLUX default branch only`。
- 增加 CTest 测试选项互斥/无输出/缺失输入 fail-closed；私有实测路径 `/home/lhy/dev/reports/cteas-s4c-unified-20261024/`，文件身份 SHA 与后续物理改造缺口记录在 `docs/plans/ISSUE40_S4C_WATER_SOURCE_PREFLIGHT_20261024.md`。完整软件 full 仅在本次提交 clean 冻结后有效，旧 HEAD 的 `ubuntu-native-full` success **不能继承到新 SHA**。

## 2026-10-24 S4 软件全量门禁修复候选（未冻结时为 DEV_ONLY）
- 修复 `scripts/ci/cteas_native_full.py`，使用 GCC12 / Python3.11+，在同一提交下额外构建并 CTest P1/P3 独立 CMake，然后用其真实二进制执行全量 S2G Python；manifest 强制验证二进制环境路径、命令、日志、SHA。
- 已本地预检 S2G 190 tests：188 PASS / 2 原有 skip，0 fail/error；P1 CTest 3/3，P3 CTest 1/1。修复已退役 P2-B workflow 检查、仅限 WGS84 浮点投影舍入误差（1e-12 deg；UTM 网格/文件 SHA 不变）、P1 scratch GCC12。
- 必须先在 clean committed exact SHA 执行完整 native full，通过后才可向 GitHub PR #308 头 SHA 发布 `ubuntu-native-full`；此节不是科学 P6/P7 通用验收，独立科学审查仍 NOT_RUN。`docs/ci/S4_S5_NATIVE_POST_S5_DOCKER_POLICY_20261024.md` 为执行细则。

## 2026-10-24 最新：S4 第六小时真实 NOAA 科研限定验收（覆盖下文第五小时状态）
- 第六小时 82×85×9 / 2SS+1US / 63 WATER：G22 181220、风场尾段 446080、COMP stage12–15 132430、P6F 45 字段 313650，原版/原生冻结容差 0 超差；G14 新 actor 回滚与正向提交实测退出 0，候选 P6F 字节一致。详情：`docs/plans/ISSUE40_S4R1C9AH_NOAA_HOUR6_G14_20261024.md`。
- 仅 PASS_SCOPED、研究 opt-in。可配置生产 P6、P7、exact-SHA Ubuntu 原生 full、独立科学审查和 GitHub 研究准入仍 NOT_ACCEPTED/NOT_RUN。PR #308 保持 Draft，正式 Docker full 延至 S5 后。

## 2026-10-24 最新 S4 科学进度（比下方原第五小时 G22 的历史文字更新）
- 第五小时真实 NOAA 82×85×9、2SS/1US、63 WATER：G26B COMP stage12–15 与原版比较 132430/132430 在冻结公差内、0 超差；原生 G64 P6F 45 字段 313650/313650，0 超差，当前记录在 docs/plans/ISSUE40_S4R1C9AF_AG_NOAA_HOUR5_COMP_P6F_G14_20261024.md。
- 第五小时真实 G14 fresh actor 故意失败回滚、正向提交、站点时钟发布全部原生退出 0；正向提交 P6F 文件 SHA256 与独立原版对照过的 stage16 候选完全一致，第六小时 preview 继承 ZI/ZICONV/DPTT 通过。
- **全部是 PASS_SCOPED**：第六小时完整 17 阶段/45 字段、本代码统一可配置生产 P6 C1/C2/非合肥重验、P7、独立科学审查和 S4 正式 full 尚 NOT_RUN/NOT_ACCEPTED。研究 #308 保持 Draft。Ubuntu 原生编译/测试、无 Docker full，正式 Docker 交付延至 S5 后。

## 2026-10-24 新版 S4/S5 与 Docker 验收规则
- S4：Ubuntu 原生 full 软件与 Fortran/C++ 科学验证；S5：原生规模/性能与科学回归；S5 完成后正式 Docker full、AMD64/ARM64 和运行镜像交付。旧的 S4/S5 每研究 PR 强制 Docker full 流程已取消，但独立科学审查及正式原生软件 full 不可跳过。
- 唯一具体执行合同：docs/ci/S4_S5_NATIVE_POST_S5_DOCKER_POLICY_20261024.md。新状态 ubuntu-native-full 只能来自干净的 exact SHA、scripts/ci/cteas_native_full.py 的全部固定步骤 PASS。GitHub repository-admission 兼容原 ubuntu-docker-full，scientific-admission/auto-merge/required checks 原样保留。
- S4 仍使用 Ubuntu /home/lhy/dev/CTEAS-next/worktrees/s4-integration，PR #308 仍 Draft；Docker 最终交付 NOT_RUN，新的原生 full 也尚未运行。

# CTEAS-next

## S4 开发状态与权威入口（2026-10-24）
- 主开发 worktree：/home/lhy/dev/CTEAS-next/worktrees/s4-integration；Git common-dir：/home/lhy/dev/CTEAS-next/repo-recovered-91a1fff8/.git。旧 repo/ 存在历史删除，不用于 S4。
- 仅保留 GitHub S4 集成 Draft PR #308：https://github.com/RRain001/CTEAS-next/pull/308。Ubuntu 集成完成本地测试后再推送；详情请阅读 docs/plans/S4_0_CONSOLIDATION_20261024.md。
- 独立原版：/home/lhy/CTEAS，只读。当前已有小时 3/4 的限定原版 45 字段科学证据，小时 5 G22 已限定通过；完整 P6/P7 科学验收仍 NOT_ACCEPTED。
- 后续完整功能批次：第五小时后续阶段→第六小时→通用生产 P6 C1/C2/新场址→新场址 P7。测试分为 L1 定向、L2 真正原版科学、L3 冻结 SHA 正式 Docker/独立审查。


CTEAS-next is a **partial, option-scoped C++20 reconstruction** of selected CALMET/CALPUFF physics pathways (P6/P7) and P1–P5 inputs. It is **not** a fully equivalent replacement for every original Fortran option.

## Entry points

| Area | Authoritative location | Current status |
| --- | --- | --- |
| C++ P1–P7 implementation and validation | `native_cpp/` | Selected branches only |
| Python legacy orchestration / GUI | `engine/` and `./calpuff-cli` | Legacy-compatible; **not a native P1–P7 driver** |
| Independent G5 native-only desktop and dispatch | `engine/gui_g5/` and `./cteas-g5gui` | Generic P6/P7/all **fail closed** |
| Native scientific reference and tests | `native_cpp/modules/{p4_read62,p5_smerge,p6_calmet,p7_calpuff}/` | Retain comparator and test source |
| Frozen reproducibility fixtures | `project/cases/` | Deliberately tracked exception; do not casually delete |
| Build, smoke checks, asset-restoration | `scripts/`, `scripts/migration/` | Current utilities only |
| Current CI and science reruns | `.github/workflows/` | Agent/CI-dispatchable and guarded automatic workflows |

For physics coverage and Fortran provenance, see `docs/physics/CALMET_CALPUFF_OPTION_MATRIX.md`, `docs/physics/CALMET_CALPUFF_OPTION_MATRIX.csv`, `docs/physics/VENDOR_SOURCE_LOCATOR.md` and `AGENTS.md`.

## Verified science (2026-10-17)

- **C1 (2022 1SS/1US, 143h)**: `PASS_SCOPED`. A/B and C/D H-3 REAL4 matching **357,500/357,500** each. The original CALMET MET input is frozen (original CALMET not freshly rerun).
- **C2 (2024 controlled 2SS/2US, 143h)**: `PASS_SCOPED`. Original/native CALMET: 143 × 45 field comparisons, zero frozen-tolerance exceedances. A/B and C/D H-3 REAL4 matching **20,592/20,592** each. This is controlled synthetic meteorology, not field-observed validation.
- Detailed audited evidence: [C1/C2 acceptance report](docs/science_acceptance/C1_C2_143H_RERUN_20261017.md), [C1](https://github.com/RRain001/CTEAS-next/actions/runs/39001955056), [C2](https://github.com/RRain001/CTEAS-next/actions/runs/39012460127). [Issue #6](https://github.com/RRain001/CTEAS-next/issues/6) was closed as **completed for the scoped cases**.
- **Whole-project scientific acceptance remains `NOT_READY`**. `MWET>0`/wet deposition and other untested plume rise, dispersion and terrain variants are **not accepted**.


## Managed Ubuntu development and merge gates (2026-10-23)

For the shared development host, first read `/home/lhy/dev/AGENTS.md`, `/home/lhy/dev/README.md` and this repository's `AGENTS.md`. Work from the actual GitHub PR HEAD in a clean isolated branch/worktree. Ubuntu Docker runs the primary software tests and exact-SHA numerical checks; GitHub provides the mandatory lightweight `repository-admission` / `scientific-admission` PR checks and selected additional CI. This host operates **Mihomo at `127.0.0.1:7897`**, with no MacBook proxy forwarding. These `/home/lhy/dev` commands are host-specific rather than prerequisites for independent clones.

```bash
/home/lhy/dev/bin/local-ci-build CTEAS-next
/home/lhy/dev/bin/local-ci smoke CTEAS-next --wait
/home/lhy/dev/bin/local-ci full CTEAS-next --wait
/home/lhy/dev/bin/local-ci scientific CTEAS-next --wait
```

The `local-ci` entry points currently require the repository's fixed `/home/lhy/dev/CTEAS-next/worktrees/local-docker-dev` checkout to contain the intended clean HEAD, and image/inputs/results must refer to that SHA. `full` is only the selected **software** suite; `scientific` can legitimately report `PARTIAL`/`NOT_RUN`. A source/test PR needs a verified `ubuntu-docker-full` commit status for its live SHA; the project also retains any applicable original-model, analytical, scientific or independent-review gates.

The `main` Ruleset requires PR review through `repository-admission` and `scientific-admission`. When every applicable check passes and any required independent scientific acceptance is documented, the agent adds `merge-verified` and GitHub's event-driven native auto-merge processes the PR. Draft, failed, pending, missing-data, stale-SHA or scientifically unaccepted changes remain blocked. Heavy scientific workflows can be agent-dispatched without manual GitHub UI interaction; they are **not** automatically PASS when skipped.

## Build and tests

Use Python >= 3.11. For local setup, run `./bootstrap_venv.sh`. The nine portable CMake suites and Python/G5 regression selection are maintained by:

```sh
python3 scripts/migration/validate_ubuntu.py --portable --out /tmp/cteas-next-ubuntu
python3 scripts/migration/validate_python.py --portable --out /tmp/cteas-next-python
```

The Ubuntu command requires the documented GCC, GFortran and GDAL toolchain. See `docs/deployment/CONTAINER.md` for the portable Docker verification image. Runs marked `PASS_SOFTWARE` are **not** scientific acceptance. Large scientific workflows are not blindly run for every push or PR; authorized agents and CI may dispatch them without the owner clicking Run workflow. See [Science workflow trigger policy](docs/ci/SCIENCE_TRIGGER_POLICY.md).

Original CALMET/CALPUFF vendor sources and restricted terrain must not be distributed in this public tree. An authorized local source checkout may restore and hash-check them using `scripts/migration/configure_external_assets.py`. Follow `docs/migration/THIRD_PARTY_ASSETS.md`.

## Cleanup and recovery

The 2026-10-17 repository slimming removed archived `.yml.disabled` workflows, one-off P6 forensic scripts, obsolete host-sync tools and obsolete structure snapshots from **current `main` only**. Historical contents remain available from the last pre-cleanup commit `2f1747434e4217a99b9b9c6fed4d413e90006bd5`:

```sh
git show 2f1747434e4217a99b9b9c6fed4d413e90006bd5:scripts/p6d_compare_native_cgamma_grid_143h.py
git ls-tree -r --name-only 2f1747434e4217a99b9b9c6fed4d413e90006bd5 docs/migration/historical-workflows/
```

See `docs/maintenance/REPOSITORY_CLEANUP_20261017.md`. The frozen `docs/migration/SOURCE_MANIFEST.json` records the **old migration snapshot**, not an assertion that every old path still exists in the slim current tree. For whole-snapshot verification, check out its original frozen commit in a separate worktree.

## Frozen cases after result pruning

Both case configurations, grids, raw meteorological input and current science baseline files are kept. Generated `project/cases/*/deliverables/`, captured run logs and obsolete diagnostic outputs were deleted from **current** Git checkout. Exceptions deliberately retained as **read-only scientific inputs** include the frozen 2022 `run/met/met.dat`, `run/puff/puff.con`, `run/puff/puff.lst`, the 2023 `run/met/met.dat`, and the original model input decks; CMake and C1/C2 science jobs still require these bytes. They are not dispensable without an explicit, hash-checked fixture restoration redesign.

Old complete cases and documents can be inspected at pre-cleanup Git commit `2f1747434e4217a99b9b9c6fed4d413e90006bd5` (the same content is in the older CTEAS source archive). **Deleting a path in a new commit does not erase historical Git objects or guarantee a smaller cloned .git history.** For actual history size reduction, use a separate approved repository migration rather than rewriting the accepted main history.

## P2 land-use producers (Issue #168 S1)

Supported paths: **P2-A** historical 1 km GLCC through the frozen original
CTGPROC sampling / historical 24-to-USGS38 mapping, and **P2-C** 2022
GLC_FCS30D 30 m through original-style `MESHGLAZ=10` source-pixel point
sampling to `LU.DAT v2.1` (`cteas_p2c_glc30m_sampling`). P2-B
`EXACT_AREA_V1` area-intersection production and its native CLI are retired.
Do not substitute an area-fraction product for point HITS. The frozen
`docs/plans/ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json` filename
and `cteas.p2b` schema are historical naming only: it remains the **required,
SHA-pinned P2-C modern class policy** and must not be renamed or edited.
The original-source audits and pre-retirement runs remain traceable in Git
history; P3 original MAKEGEO physics parity is not established by P2-C's
format-only LU.DAT contract.

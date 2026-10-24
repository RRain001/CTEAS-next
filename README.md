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

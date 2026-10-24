## 2026-10-24 最新阶段验收（优先于旧的 Ubuntu Docker/full 要求）
- 本仓库 S4 以 Ubuntu 原生软件全量测试、Fortran/C++ 独立原版科学验收、精确 SHA 和非 Bot 独立审查作为强制门禁。S5 以原生软件 full、规模/内存/性能回归及物理不退化为门禁。**正式 Docker full 和 AMD64/ARM64 容器交付验收延至 S5 完成之后**；Docker 快速调试自愿使用，不能替代真实物理/原生 full。
- 项目脚本 scripts/ci/cteas_native_full.py 只在干净冻结 HEAD 运行全 native_cpp CMake build/CTest 及 S4/S2G Python 单元测试，完整记录日志、命令、SHA，verify 成功后对 GitHub 当前 PR HEAD 发布 ubuntu-native-full（或沿用已有 ubuntu-docker-full）。没有正式原生 full 实际结果就保持 NOT_RUN，禁止把 DEV_ONLY 当软件门禁。
- GitHub repository-admission 支持 exact SHA 两种软件证据；scientific-admission 及 required checks、不变的 science-validated、他人非 Bot 同 SHA APPROVED review、Draft 和 merge-verified 自动合并防护仍有效。Docker 延期不降低原版数值容差、不放宽生产物理 guards、不授予 P6/P7 科学通过。
- 唯一权威文档 docs/ci/S4_S5_NATIVE_POST_S5_DOCKER_POLICY_20261024.md。本文下面 2026-10-23/24 提到 S4/S5 每阶段强制 Docker full、ubuntu-docker-full 唯一准入的内容仅为历史约定。只针对本仓库修改，与其他项目无关。

## S4-0 当前唯一开发基线（2026-10-24）
- Ubuntu 有效 S4 Git 主工作树：/home/lhy/dev/CTEAS-next/worktrees/s4-integration，分支 codex/s4-integration-20261024；实际 common-dir 是 repo-recovered-91a1fff8/.git。旧 /home/lhy/dev/CTEAS-next/repo 存在 210 项历史删除，禁止用于开发或 reset；/home/lhy/CTEAS-next 已删除。
- GitHub 集成 Draft PR #308 是唯一 PR；15 个祖先 Draft 已关闭但保留历史。经 Ubuntu 本地编译/定向测试及应有科学原版比对后，只能 fast-forward push 到 PR #308 现有远程 head，不能 force push/main push，不能为每个 G22/G23/G24 等中间阶段新增 PR。
- GitHub #308 的 workflow_dispatch 修复、当时 main 和七个本地 S4 提交已安全合并；旧 s4-r1c9u 的未提交工作（4 个修改+2 文件）已有本地独立备份，但旧实验 worktrees 不删除。详见 docs/plans/S4_0_CONSOLIDATION_20261024.md。
- 真实 NOAA 第三/第四小时限定 45 字段对照、G14 transaction 与第五小时 G22 已有历史 scoped 证据，绝不升级成统一生产科学通过。第五小时 G23/G24、COMP/P6F/G14、第六小时、通用 P6/P7、外部独立科学评审仍 NOT_ACCEPTED；科学容差、默认 fail-closed guards 和 restricted vendor 数据保护不变。
- L1 定向软件测试；L2 冻结源/输入和原版/C++ 数值独立对照；L3 clean exact SHA Ubuntu Docker full + GitHub required checks + 独立审查。未通过 L3 和科学门禁保持 Draft，不加 merge-verified。

# CTEAS-next agent instructions

## Owner's current CI and merge decision (2026-10-23)
- Keep automatic PR admission checks and scoped software CI; longer science workflows use reviewed, agent-triggered `workflow_dispatch` with exact-SHA evidence. Do not revive the canceled blanket manual-only PR #285; do not re-enable every heavyweight science workflow on PR/push.
- Develop and test candidates with Ubuntu Docker before opening/updating PRs; allow GitHub to auto-run its existing scoped CI on the exact PR HEAD without requiring the owner to click Run workflow.
- Once ALL applicable software tests, original-model/scientific parity, precise input/commit evidence, independent review and required GitHub checks have passed, transition the PR out of Draft and automatically squash merge or enable native GitHub auto-merge; explicit per-PR owner approval is no longer needed. Never activate merge for blocked, NOT_RUN, failed, pending, stale or scope-limited science claims. Enabling repository `allow_auto_merge` alone is not authorization to waive gates.



## Ubuntu Docker / GitHub admission (current deployment, 2026-10-23)
- On the managed Ubuntu host, read `/home/lhy/dev/AGENTS.md` and `/home/lhy/dev/README.md` **before** this repository guide; in other environments those absolute paths may not exist, so use the equivalent documented container and gate contracts. A new ChatGPT session must explicitly read the files, not assume they are automatically injected.
- Refresh remote Git refs and fetch the exact PR HEAD SHA; inspect clean worktrees and all existing tests. Use an isolated short-lived task branch/worktree, never commit directly to `main`, and never force-clean an accepted worktree. The Ubuntu working copy is under `/home/lhy/dev/CTEAS-next/worktrees/local-docker-dev`; the `local-ci` tool currently binds that path, so check the selected SHA before each run.
- Run real builds, focused smoke, scoped `full`, and admissible scientific checks on Ubuntu in Docker. Host entry points: `/home/lhy/dev/bin/local-ci-build`, `/home/lhy/dev/bin/local-ci`, `/home/lhy/dev/bin/local-ci-report`; follow `/home/lhy/dev/infra/local-ci/README.md` for flags and resource limits. A scoped software pass is not all-option or independent scientific acceptance.
- Ubuntu runs its **own Mihomo** HTTP(S) proxy at `127.0.0.1:7897`. Do not require a MacBook/Clash reverse tunnel. Docker daemon, BuildKit and the host-side buildx CLI need compatible proxy settings. Never commit proxy subscriptions, credentials or restricted data.
- The GitHub `main` Ruleset requires the always-running `repository-admission` and `scientific-admission` PR checks. For applicable source/test PRs, publish `ubuntu-docker-full` success **only** after verified `full` software evidence at the exact live PR SHA via `python3 /home/lhy/dev/bin/local-ci-publish-status CTEAS-next <pr> <full-run-id>`; retrigger admission when necessary. This status does not assert science PASS.
- Agents can dispatch longer workflows at a reviewed candidate SHA without asking the owner to click GitHub Actions. Record the run's actual SHA, inputs, checks and scientific conclusion. For science changes, obtain the project-specific external evidence and a genuinely independent, same-SHA human/non-bot APPROVED review as required; never manufacture a `science-validated` claim.
- Only after **all applicable** checks and any required source-specific scientific evidence and independent review succeed, and the current PR is non-Draft and conflict-free, may the agent add `merge-verified`. The trusted `pull_request_target` workflow enables GitHub native squash auto-merge; changing the SHA invalidates the old authorization. NOT_RUN, FAIL, pending, Draft and scientific-review blockers must stay unmerged. No hourly polling or manual-owner click is required.

## Scope and acceptance
- This is the **partial C++20** reconstruction of selected P1–P7 CALMET/CALPUFF pathways, **not** a whole-option Fortran replacement. Consult `README.md` and `docs/physics/CALMET_CALPUFF_OPTION_MATRIX.{md,csv}` before implementing or changing physics.
- C1 (2022 143h) and C2 (controlled synthetic 2024 143h) each **PASS_SCOPED**, as audited in `docs/science_acceptance/C1_C2_143H_RERUN_20261017.md`; Issue #6 is closed for these limited cases. **Full science acceptance NOT_READY.** Do not infer generic P6/P7 or `MWET>0` acceptance from these results.
- C1 original CALMET input was an SHA-locked frozen MET, not freshly rerun original Fortran CALMET. C2 is not independently measured atmospheric observations. Preserve these scientific qualifications.

## Mandatory UTM grid-origin precision (owner decision 2026-10-17)
- **For every current and future case, computational UTM `XREFKM` and `YREFKM` are in km at exactly THREE decimal places (0.001 km = 1 m). Do not increase their precision.** Geographic center latitude/longitude used for projection can retain their original precision, but must not be passed directly to P1/P2 sampling without first quantizing the computed UTM grid origin.
- Treat the generated `grid.cmn` numeric origin as authoritative and carry precisely those three-decimal values into P1/P2/P3, CALMET, manifests and any original comparator. Mere `:.3f` display formatting is insufficient if the computation secretly uses higher-precision floats.
- Frozen Hefei 2022 case: `XREFKM=510.885`, `YREFKM=3531.269`; currently selected P1/P2/P3 C++ CLI must fail closed on any other value or non-three-decimal spelling, not silently round. Future new geographic cases require their own reviewed profile but **the same 3-decimal-km precision**.
- A frozen `MET.DAT` is only an independent reference for an exactly matching GEO/UP/SURF/control input set. Never cross-compare a new GEO with an old-GEO MET or relax science tolerances.
- Evidence: [S2-2C root-cause report](docs/plans/STAGE2_2C_GEO_ORIGIN_ROOT_CAUSE_20261017.md); original 493 exceedances came from 18 terrain heights sampled differently at sub-meter-shifted grid origins. Both original/native 143h same-input comparisons pass when origins match.

## Source ownership and trusted scientific baseline
- Native C++ sources/tests: `native_cpp/`; Python legacy engine and GUI: `engine/`; G5 explicitly native-only authority: `engine/gui_g5/pipeline.py`, currently rejects generic P6/P7/all. Do **not** route G5 through `engine.orchestrator.cli` or legacy model executables.
- The unchanged original CALMET 6.5.0 Fortran source is at old `RRain001/CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13:engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for`; CALPUFF 7.2.1 at `engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for`. Follow `docs/physics/VENDOR_SOURCE_LOCATOR.md`.
- Never add external `engine/vendor/**`, restricted CGIAR/SRTM terrain or fonts to the public repository, Action artifacts, logs or Docker images. Restore only from authorized local sources via `scripts/migration/configure_external_assets.py` with hash checks; see `docs/migration/THIRD_PARTY_ASSETS.md`.
- New physics work requires option-specific code authority, frozen input/source provenance, original-versus-native comparison, first differences and an updated option matrix. **Never** silently relax numerical tolerances or fake a PASS from empty plumes.

## Files and runtime
- Preserve still-tracked `project/cases/**` raw inputs, input decks and hash-pinned reference baselines as a deliberate scientific migration exception. Duplicate `deliverables` and generated logs were pruned; do not recreate them as tracked artifacts. Do not commit new generated case outputs, raw downloaded station data, binaries, virtual environments, giant artifacts or unrestricted local `project/` workspaces.
- `docs/migration/SOURCE_MANIFEST.json` records the **frozen pre-cleanup migration export**. Its original content can be checked on the historical commit, not assumed to describe the lean current `main` tree.
- Previously archived 119 disabled workflows, one-off P6 scripts, redundant `deliverables/` and obsolete deployment helpers were removed from current head on 2026-10-17. Restore historical code from pre-cleanup `2f1747434e4217a99b9b9c6fed4d413e90006bd5` via `git show` only if an explicitly authorized scientific task requires it. See `docs/maintenance/REPOSITORY_CLEANUP_20261017.md`.
- Keep C++ work compatible with Ubuntu GCC/GFortran; packaging can target Linux AMD64/ARM64. Python minimum 3.11. `./bootstrap_venv.sh` sets up Python.
- Portable software tests: `scripts/migration/validate_ubuntu.py --portable` and `scripts/migration/validate_python.py --portable`, with `--out` **outside** the checkout. Active Actions workflows in `.github/workflows/` support authorized owner/agent/CI dispatch according to `docs/ci/SCIENCE_TRIGGER_POLICY.md`. The old requirement for owner-only UI/manual science triggers is revoked; retain trusted-main, source SHA and numerical acceptance gates. Do not launch all expensive 143h tests indiscriminately on every push or PR.
- Preserve existing supported legacy PySide6 entrypoints unless expressly migrating them. Current core GUI windows are still separate; do not casually conflate legacy and G5 execution.

## Project-wide science triggering (owner decision 2026-10-19)
- The former **user-manual-only science Actions requirement is revoked** throughout this project, including P1-P7, Wolsong #123, P3 and 143h workflows. Agents may initiate authorized workflow_dispatch via `.github/workflows/cteas-science-dispatcher.yml` and the owner-authenticated Issue comment route, or via supported GitHub Actions-write tools; individual event-triggered science pipelines may run automatically.
- Command on an open Issue: `/cteas run <approved-workflow.yml> [input=value ...]`. Do not claim a dispatch succeeded until GitHub reports it, or scientific PASS until the target run and evidence have been checked. Keep sensitive or destructive release/branch cleanup outside the science dispatcher.
- This current owner decision **supersedes manual-only language in older Issue discussions, historical workflows and plans** as an execution requirement; does not alter the published audit history, legal source constraints, SHA pins, physics options or scientific numerical thresholds.

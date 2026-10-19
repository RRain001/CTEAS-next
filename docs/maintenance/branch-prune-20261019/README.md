# CTEAS-next — reviewed second-pass remote branch cleanup (2026-10-19)

This is a **manual, one-time, exact-SHA cleanup cohort**. It does not change physics, tests, retained model binaries, or original input data. It does not execute a full scientific workflow.

## Outcome and provenance

- Original first-pass cleanup: [Actions #39246331535](https://github.com/RRain001/CTEAS-next/actions/runs/39246331535) — **97 deleted**, 27 remained at that instant.
- The second-pass roster contains **23 named refs**, pinned to the 40-character Git SHA reviewed on 2026-10-19.
- All **29 one-off .github/workflows and .github/science-triggers sources** (from 21 historical `automation/` branches) are retained as raw UTF-8 strings with Git blob SHA in these **nonexecuting JSON archives**:
  - [`science-sources.json`](maintenance/branch-prune-20261019/science-sources.json)
  - [`pr13-sources.json`](maintenance/branch-prune-20261019/pr13-sources.json)
  - [`s2a-sources.json`](maintenance/branch-prune-20261019/s2a-sources.json)
  - [`s2b-sources.json`](maintenance/branch-prune-20261019/s2b-sources.json)
  - [`s2c-sources.json`](maintenance/branch-prune-20261019/s2c-sources.json)
  - [`s2d-sources.json`](maintenance/branch-prune-20261019/s2d-sources.json)
- The persistent, machine-readable deletion roster is [`.github/maintenance/second-pass-20261019.json`](../../../.github/maintenance/second-pass-20261019.json).
- Key core files from S2-A/P3/P6/P7 and 3-decimal UTM GEO were independently compared by Git blob SHA against `main`. Their current versions are already on `main`; some historical branch-side tests are superseded by newer main-side tests. See [PR #21](https://github.com/RRain001/CTEAS-next/pull/21), [PR #23](https://github.com/RRain001/CTEAS-next/pull/23), [PR #27](https://github.com/RRain001/CTEAS-next/pull/27), [PR #28](https://github.com/RRain001/CTEAS-next/pull/28) and [PR #13](https://github.com/RRain001/CTEAS-next/pull/13).
- The Shanghai Dongtan `data/landcover/glc_fcs30d/v1_2022/shanghai_dongtan/` four entries, including TIFF Git blob `7f56845be612a2cb46d5b8badcebce3fc6d6eca5`, matched `main`. The previous maintenance workflow `maintenance-prune-branches.yml` matched `main` at Git blob `826e764f3e00b53b215829d7bb745e49020fcee0`.
- Historical workflow files are archived as **source/evidence**, not reactivated workflows. Historic Actions runs and numeric science reports remain separately referenced by the accepted PRs. The JSON archives are not replacements for full original-science replays.

## Reviewed branch roster

| Group | Branch | Pinned head |
|---|---|---|
| science | `automation/science/c1/20261017-001` | `6d705df3d16df2c9843a32e57393d374341076f3` |
| science | `automation/science/c2/20261017-001` | `cafc17e3462eef95ab5467039aec32d7de866dc6` |
| pr13 | `automation/validation/pr13-exact-head-20261017-001` | `5287245d5fa0c7d04406f68896647092e536f9cd` |
| pr13 | `automation/verification/pr13-native-20261017` | `9a79d305703786937d7e7bbbbe16f4641bb7b007` |
| s2a | `automation/verify-s2a1-20261017` | `5e8fba52564d20235b411bd926befe82b0bce5a1` |
| s2a | `automation/verify-s2a1-controls-20261017` | `94f5310057dd1662706f0ae8ecd34e9f155d3a5a` |
| s2b | `automation/verify-s2b-full-native-20261017` | `c9f65df9a3064ff8659e2325bc918fe3f47c9149` |
| s2b | `automation/verify-s2b-original-recapture-20261017` | `db9d8f7a5b8899ce1734654ce0d036b789b5c406` |
| s2b | `automation/verify-s2b-p12-p3-20261017` | `9f404a62809d708e3f4c82886a7d513fded7bacc` |
| s2b | `automation/verify-s2b-p12-p3-retest-20261017` | `0e79c6709a99c213b54ca0ba929454fd2050cfbc` |
| s2b | `automation/verify-s2b-real-native-p2-20261017` | `1192d13cf61379e70f916af7aa095cb9dcc79797` |
| s2c | `automation/verify-s2c-fresh-original-calmet-20261017` | `044848b4fd665e2ef1cfbffce1b6fcd09e981c4f` |
| s2c | `automation/verify-s2c-geo-fields-20261017` | `93f6394b5b19adb6831a88faa3f53ff29d06b6a3` |
| s2c | `automation/verify-s2c-geodata-diff-20261017` | `53eb41a0849d475873fffe0bbb0b43aef28fd122` |
| s2c | `automation/verify-s2c-native-handoff-20261017` | `64f78ef83fef3cbdff8233160ed5003a8d5a967b` |
| s2c | `automation/verify-s2c-real-p6-20261017` | `f724ccd5f64bde865c063d295396e5807c84c11e` |
| s2c | `automation/verify-s2c-rounded-geo-met-20261017` | `8498a63ee53e697fa4b225b202f82c6bae1b38f5` |
| s2c | `automation/verify-s2c-three-decimal-origin-20261017` | `c0de2c5fba1ab14a624ac8f8972a34079d9fb750` |
| s2d | `automation/verify-s2d-c2-final-admission-20261017` | `2f4f6b37806a8d63ee43076075efaa4fdd70980c` |
| s2d | `automation/verify-s2d-c2-pr28-20261017` | `3527b1cf5d8546eed6825980d00256c9a7eab8f4` |
| s2d | `automation/verify-s2d-p7-first-science-20261017` | `e1517ce253d944f0caaac4bad8359fa9a8cb89f5` |
| data | `codex/p1-p2-p4-p5-d0-audit` | `317006629263b23b52f77b1c48e477dd8096ab18` |
| maintenance | `maintenance/manual-reviewed-branch-prune-20261019` | `7c1b88713000bb1d82bb5a3e84b7f1038df51f63` |

## Operating instructions

1. Merge the maintenance PR after reviewing the manifest, source archives, and workflow safety checks. Do not dispatch from its feature branch.
2. Run [Manually review and prune obsolete branches](https://github.com/RRain001/CTEAS-next/actions/workflows/maintenance-prune-branches.yml) on `main` with `batch=second_pass_20261019`, `mode=preview`, `max_delete=200`. Confirm exactly 23 `CANDIDATE` entries and no changed/missing SHA or open PR. Download `branch-cleanup-report`.
3. Only after reviewing that fresh preview, run `batch=second_pass_20261019`, `mode=apply`, `confirmation=DELETE_SECOND_PASS_20261019`, `max_delete=200`.
4. Inspect the second report: exactly 23 `DELETED`, zero `FAILED`/`SKIP`, and independently query the live branch list. Any branch movement or new PR makes the apply preflight fail before deletion.
5. Keep using `batch=standard` for the original conservative clean-up rules; its original confirmation remains `DELETE_REVIEWED_BRANCHES`. Never confuse the two confirmations.

**Fail-closed rules:** The action only runs on `main` and only via `workflow_dispatch`. Second pass compares exact branch names **and** pinned 40-character head SHAs; excludes all branches outside the manifest, including ongoing #84/#123 work, `main` and independent #54 scratch. An archive must exist and pass its Git-blob SHA integrity check before apply. It also requires every pinned branch to exist, match its SHA, be unprotected, and have no open or closed-unmerged PR; each branch is queried again immediately before deletion. Any stale manifest must be reviewed and repinned in a new PR, never bypassed.

This does **not** permanently retain every independent historical Git commit: it deliberately retains branch-only one-shot CI sources (and a provenance map), with implementation code retained in `main`. Deleting refs may eventually make unreferenced commit objects unavailable on GitHub. Recover any additional branch-only materials before a future apply if needed.

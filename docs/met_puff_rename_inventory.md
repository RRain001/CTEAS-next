# MET/PUFF Rename Inventory

## Scope

本轮正式把项目自有运行文件族从 `calmet/calpuff` 收口到 `met/puff`：

- 物理二进制：
  - `calmet.x -> met.x`
  - `calpuff.x -> puff.x`
- 运行输入/输出文件：
  - `calmet.inp -> met.inp`
  - `calmet.lst -> met.lst`
  - `calmet.dat -> met.dat`
  - `calpuff.inp -> puff.inp`
  - `calpuff.lst -> puff.lst`
  - `calpuff.con -> puff.con`
  - `calpuff.dry -> puff.dry`
  - `calpuff.wet -> puff.wet`
  - `calpuff.vis -> puff.vis`
- 运行日志：
  - `calmet_runtime.log -> met_runtime.log`
  - `calpuff_runtime.log -> puff_runtime.log`
- 项目后处理入口：
  - `plot_calpuff_snapshot -> plot_puff_snapshot`
  - `plot_calpuff_animation -> plot_puff_animation`
  - `plot_calpuff_annual -> plot_puff_annual`
  - `plot_calpuff_seasonal -> plot_puff_seasonal`
  - `plot_daily_from_calpuff -> plot_daily_from_puff`
- CLI 参数：
  - 默认帮助文案改用 `--met-inp`
  - 兼容别名 `--calmet-inp` 仅短期保留
- 历史运行记录目录：
  - `runs/*_calmet -> runs/*_met`
  - `runs/*_calpuff -> runs/*_puff`

## Files Changed

- 运行链核心：
  - `engine/native/registry.py`
  - `engine/core/paths.py`
  - `engine/orchestrator/cli.py`
  - `engine/run_met/*`
  - `engine/run_puff/*`
- case/schema：
  - `engine/config/case.schema.yaml`
  - `engine/validators/case_schema.py`
  - `engine/preprocess/bin/new_case.py`
  - `engine/preprocess/bin/run_preprocessing_pipeline.py`
  - `project/cases/smoke5d/case.yaml`
  - `project/cases/smoke5d_docker_test/case.yaml`
- GUI/脚本：
  - `engine/gui/workbench.py`
  - `engine/gui/app.py`
  - `scripts/check_paths.py`
  - `scripts/test_native_backend.sh`
  - `scripts/test_linux_x86_64_runtime_in_docker.sh`
- 文档与项目元数据：
  - `docs/docker_linux_x86_64_runtime_test.md`
  - `docs/git_tracking_plan.md`
  - `docs/path_inventory.md`
  - `docs/project_structure_for_chatgpt.md`
  - `docs/regression_test_after_path_refactor.md`
  - `engine/run_met/README.md`
  - `engine/run_puff/README.md`
  - `pyproject.toml`

## Allowed Residual Matches

以下旧名保留是有意为之，不属于本轮遗漏：

- `allowed_upstream_binary_name`
  - `engine/vendor/src/CALMET_v6.5.0_L150223/*`
  - `engine/vendor/src/CALPUFF_v7.2.1_L150618/*`
  - 原因：这些是上游源码/脚本名称，不代表当前正式物理二进制名

- `allowed_template_or_output_filename`
  - `scripts/migrate_runtime_names_to_met_puff.py`
  - 原因：这是唯一官方升级脚本，脚本内必须显式列出旧名到新名的替换表

- `allowed_history_note`
  - `engine/run_met/log.md`
  - `engine/run_met/log copy.md`
  - `engine/run_met/并行计算的尝试.md`
  - `docs/refactor_logs/*`
  - 原因：这些是历史记录，不作为当前运行入口

- `allowed_binary_inventory_doc`
  - `docs/native_binaries.md`
  - `docs/native_binary_cleanup_report.md`
  - 原因：文档可同时记录当前正式名 `met.x` / `puff.x` 与历史旧名 `calmet.x` / `calpuff.x`

- `allowed_backward_alias`
  - `engine/orchestrator/cli.py` 中临时保留 `calmet -> met`、`calpuff -> puff`
  - 原因：兼容旧 CLI 调用，同时输出 deprecated 提示

## Remaining Actionable Matches

- 活跃代码、活跃脚本、活跃文档中，不应再把 `calmet.*` / `calpuff.*` 当正式运行文件名使用。
- 当前允许的活跃残留仅限：
  - vendor 上游模型源码/批处理文件名
  - 一次性迁移脚本中的旧名替换表
  - 历史日志与 `docs/refactor_logs/*`

## Runtime Mapping Fix

本轮继续完成了逻辑名和物理名的运行时收口：

- `engine.native.registry.NATIVE_PROGRAMS`
  - `met -> binary="met"`
  - `puff -> binary="puff"`
- `engine.core.platform_utils.get_binary_path()`
  - 现在会先查 registry，再解析到物理二进制路径
- `scripts/check_native_binaries.py`
  - 现在明确输出：
    - `met -> met.x OK`
    - `puff -> puff.x OK`
- 新增 `scripts/check_native_runner_mapping.py`
  - 用于直接验证：
    - `met resolves to .../bin/linux-x86_64/met.x`
    - `puff resolves to .../bin/linux-x86_64/puff.x`

## Runtime Path Fix

本轮同时修正了运行期文件路径口径：

- Docker 脚本已移除临时 workaround，且当前正式物理名已直接切换为：
  - `bin/<platform>/met.x`
  - `bin/<platform>/puff.x`
- MET 正式运行目录与文件名：
  - 目录：`run/met/`
  - 文件：`met.inp`、`met.lst`、`met.dat`
- PUFF 正式运行目录与文件名：
  - 目录：`run/puff/`
  - 文件：`puff.inp`、`puff.lst`、`puff.con`
- PUFF 的 `METDAT` 正式口径：
  - `../../deliverables/met/met.dat`

## Verification Update

2026-06-26 的 Docker `linux/amd64` runtime 复测结果：

- READ62：通过
- MET：通过
- PUFF：通过

说明：

- `run_met` 现在直接依赖正式物理名 `met.x`
- `run_puff` 现在直接依赖正式物理名 `puff.x`
- `run/met` 和 `run/puff` 已直接生成上游原始文件名产物
- `deliverables/met` 和 `deliverables/puff` 已同步得到新产物
- 历史遗留的 `deliverables/calmet` / `deliverables/calpuff` 仍存在，但本轮运行链路已不再依赖它们

## Verification Basis

- 改名前全量命中清单：
  - `docs/refactor_logs/before_met_puff_rename_matches.txt`
- 改名后残留清单：
  - `docs/refactor_logs/after_met_puff_rename_remaining_matches.txt`
- 残留项已经按上面的 `allowed_*` 类别人工解释。

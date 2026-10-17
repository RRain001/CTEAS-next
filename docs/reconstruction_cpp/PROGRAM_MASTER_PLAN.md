# CTEAS-next — P1–P7 C++20 重构总计划

**状态（2026-10-17）：`C1=PASS_SCOPED; C2=PASS_SCOPED; FULL_OPTION_SCIENCE=NOT_READY; G5_GENERIC_ALL=BLOCKED`.**

本文件是当前正式总计划入口；之前的 2026-10-10 草稿（包括“没有工作流”“科学参考尚未运行”）属于旧历史状态，不能用于判断今天的 CTEAS-next。需要查原文时可从此前 Git 历史获取。

## 当前执行权威

- **四阶段计划与实际门槛：** [CTEAS_NEXT_FOUR_STAGE_PLAN_20261017.md](../plans/CTEAS_NEXT_FOUR_STAGE_PLAN_20261017.md)。
- **当前物理覆盖与原版选择：** [CALMET_CALPUFF_OPTION_MATRIX.md](../physics/CALMET_CALPUFF_OPTION_MATRIX.md) + [CSV](../physics/CALMET_CALPUFF_OPTION_MATRIX.csv)。本矩阵是范围台账，不是全部选项的科学认证。
- **新仓库 C1/C2 真实 143h 验收：** [C1_C2_143H_RERUN_20261017.md](../science_acceptance/C1_C2_143H_RERUN_20261017.md)、[Issue #6](https://github.com/RRain001/CTEAS-next/issues/6)（仅限定验收关闭）。
- **原版 vendor 路径和许可规则：** [VENDOR_SOURCE_LOCATOR.md](../physics/VENDOR_SOURCE_LOCATOR.md)、[THIRD_PARTY_ASSETS.md](../migration/THIRD_PARTY_ASSETS.md)。
- **软件入口：** `native_cpp/` P1–P7；`engine/gui_g5/pipeline.py` 为 G5 独立原生执行权限；旧 `engine/orchestrator/cli.py` 是 Legacy，不得在 G5 失败时静默回退。

## 四阶段工程优先级

| 次序 | 阶段 | 当前重点及关闭门槛 |
|---|---|---|
| S1 | 收口整理与软件回归 | **DONE_SCOPED / PASS_SOFTWARE**：PR #13 已合并，九组 C++/CTest + P4/P5 Python 58/58 + Docker AMD64 native-only 通过；G5 按用户要求 `NOT_RUN`。证据 [Actions #39021059327](https://github.com/RRain001/CTEAS-next/actions/runs/39021059327)。 |
| S2 | 选定范围 P1–P7 原生链 | 先完成接口审计/manifest/dry-run，再集成 P1–P5、P6、P7；对已验收配置真正端到端通过后再解除相应 G5 fail-closed。 |
| S3 | 冻结基准按需恢复 | 建立文件级 SHA/来源/许可清单与严格恢复器，并成功证明原始输入和关键科学输出能长期读取；此后才删除余下的大文件。 |
| S4 | 扩展物理选项 | 降水/湿沉降为先，再地形/抬升/扩散等逐选项完成原版同输入与独立验证；未验证分支始终拒绝。 |

旧版 CALMET/CALPUFF 源码不可在公开仓库再分发；同一组合物理路径的 143h 一致性不是全模型、全场址通用性证明。两套 GUI 暂不重构。不将独立软件回归 PASS 当作 Fortran 同输入科学验收。

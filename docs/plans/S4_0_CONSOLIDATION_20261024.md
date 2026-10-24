# S4-0：统一开发基线与 S4 后续关键路径（2026-10-24）

## 1. 权威代码与版本
- Ubuntu 只有 /home/lhy/dev/CTEAS-next 是有效项目根；当前 Git common-dir 是 repo-recovered-91a1fff8/.git，唯一活跃 S4 worktree 是 worktrees/s4-integration，分支 codex/s4-integration-20261024。
- repo/ 为旧的缺文件 Git 工作区，约 210 项 tracked deletions：隔离，不允许 pull/reset/clean/删除，不承担 CI；待单独审计其有效数据。
- GitHub PR #308：https://github.com/RRain001/CTEAS-next/pull/308，目标 main，远程头 codex/s4-r1c9t-hour3-native-comp15-trial；原其他 15 个阶段 Draft 已关闭，历史保留。禁止对 Draft 或 main 直接合并。
- 基线整合：GitHub #308 f931d5d99364bb7d387cc17ca267ee6b0e8f6f53；当时 origin/main b2765a84c2d20286b3626d27a0843f99cd156a71；本地七提交 HEAD 78854f4b722e21de18d88d924a1bb57328318cbe。在新集成 worktree 依次使用正常无冲突 Git merge；文档前集成 HEAD a0c638c9d6e4d5158af26a1c39200547ea063f89。每轮开发均需重新核实实时 SHA。
- 本地保护：/home/lhy/dev/reports/cteas-s4-0-consolidation-20261024 含 s4-r1c9u 四个修改的 binary patch、两个 Python 测试的 tar、SHA256SUMS、X 七提交列表；备份 git refs/backup/s4-0-20261024/*。旧实验 worktrees 不删除、未审查前不覆盖。
- Workflow 合并策略：保留现行 main 的重型科学按需 workflow_dispatch，自动轻量 CI 和 required checks 均不允许关闭。所有代码从 Ubuntu 开发/提交/非强制推送更新唯一 PR #308。

## 2. 科学验收状态（历史 SHA 上的 scoped 证据，当前集成 HEAD 尚无 L3）
| Gate | 现有证据和限制 | 状态 |
| --- | --- | --- |
| C1/C2 143h | 冻结合肥和合成 C2 分别限定通过，不是同一可配置生产二进制 | PASS_SCOPED |
| NOAA 小时 2 | #295 的旧 HEAD 有 1397/313650 超差；后续 #296 修复 WATER ZICONV 得到 0 超差 | PASS_SCOPED（后续 HEAD） |
| NOAA 小时 3 | 原版独立 45 字段 313650/313650 冻结容差，scoped G14 正向/回滚，详见 R1c9v | PASS_SCOPED；独立审查 NOT_RUN |
| NOAA 小时 4 | 原版独立 P6F 313650/313650、0 超差，scoped G14 rollback/retry，详见 R1c9z/aa | PASS_SCOPED；独立审查 NOT_RUN |
| NOAA 小时 5 | G22 阶段比较 181220/181220，0 超差，stage 7–16 未验 | PARTIAL / NOT_ACCEPTED |
| NOAA 小时 6 | 完整 17 阶段、45 字段、跨小时状态 | NOT_RUN |
| 通用 P6 生产 | 同一执行器/二进制验收 C1、C2、非合肥和第二组配置 | NOT_ACCEPTED |
| 新场址 P7 / P1–P7 全链路 | 依赖合格 P6 MET.DAT，原版 CALPUFF 独立同输入 | NOT_RUN |
| 新集成 HEAD 正式 Docker full 和外部独立科学审查 | 旧 DEV_ONLY 或旧 SHA 不能继承 | NOT_RUN / NOT_ACCEPTED |

## 2026-10-24 S4-A 新增第五小时限定证据
- 原 s4-r1c9u 未跟踪的第三小时 45 字段独立比较器及对应测试，已逐字节核对后补入统一集成工作树（原工作树和独立备份仍保留）；加入后 S4 Python 定向测试 133/133 PASS。

- 第五小时 G23/G24 stage90/100/110：真实 NOAA 独立原版比较 446080/446080 REAL4 处于冻结 2e-4 m/s 内，0 超差，360924 bitwise；证据详见 docs/plans/ISSUE40_S4R1C9AE_NOAA_HOUR5_G23_G24_20261024.md。本门禁是 test-only PASS_SCOPED，非完整第五小时 P6 PASS。
- 下一步：COMP stages12–15、P6F stage16 45 字段及 G14 原子提交/回滚；再完整第六小时。此时 exact HEAD Docker full、独立科学审查均未运行。

## 3. 开发与测试关键路径
1. S4-0：核对、备份本地科学开发和未提交工作，合并最新 main、GitHub #308、所有需要的本地提交；审查遗留实验文件；更新规范和本计划；执行 L1 定向编译/测试，检查 fast-forward 及唯一活跃工作树，最后由 Ubuntu 推送 PR #308 的现有 head。
2. S4-A：第五小时同一真实 NOAA G14 状态中完成 G23/G24 stage7–11、COMP stage12–15、P6F stage16 45 字段同源原版独立数值比对、回滚与正向提交。保留所有生产拒绝 guard，失败时定位最早分叉而不是放宽容差。
3. S4-B：完成第六小时所有阶段与原版 45 字段，确认小时 1–6 连续历史、输出时序/物理状态与原版数值。
4. S4-C：同一可配置 P6 生产二进制重新通过 C1 1SS/1US、C2 2SS/2US、真实非合肥 2SS/1US 和额外受支持配置，完成完整独立科学门禁，再解锁 P7 新场址与 P1–P7 整体验收。
5. L1 受影响编译/单测，L2 完整功能级本机原版/C++ 比对，L3 clean exact SHA Docker full、GitHub required checks、独立科学审查。禁止每个诊断子阶段创建长期 Draft、绕过 guard 或原版数据回填。

## 4. 交接和限制
- C++ 只能用源驱动完整历史；原版 CALMET/CALPUFF 固定于只读 /home/lhy/CTEAS，源/输入/executable SHA、UTC、站点、网格和冻结阈值按每轮记录。禁止原版私有资产/气象/trace 上传公共 GitHub。
- S4-0 完成后才能投入 S4-A；即使 S4-0 的 L1 PASS，也不意味着 S4 或 PR #308 正式科学通过。不添加 science-validated / merge-verified。

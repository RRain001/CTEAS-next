# #54/#53/#55/#56 四线 D0 联合交接索引

日期：2026-10-18。初次源码审计基线：`82ca304ba10fee8613cf7b8a319abc1b242f0861`；合同对齐基线：`origin/main@c56d1660445d82649a096a4cedf10af7fdef8490`（PR #57 已合并）；工作分支：`codex/p1-p2-p4-p5-d0-audit`。

## 当前关卡

公共 B-0 交接边界已由 [PR #57](https://github.com/RRain001/CTEAS-next/pull/57) 合并冻结，权威文档为 [P1–P5 joint input gate](../s2g1bb_p1_p5_joint_input_gate.md)。此前“未看到B-0冻结证据”的结论已过时并撤回。四份D0已按此合同修订，提交独立审查；本轮不实施D1、不改物理算法、不宣布Issue完成。#42整体仍为 `DESIGN / BLOCKED_UPSTREAM`；公共合同合并不代表五模块联合源或科学验收通过。

| Issue | 独占审计报告 | 交付范围 |
|---|---|---|
| [#54 P1](https://github.com/RRain001/CTEAS-next/issues/54) | [P1 D0](ISSUE54_P1_D0_20261018.md) | 双DEM入口、同一采样内核、动态网格、TERREL合同 |
| [#53 P2](https://github.com/RRain001/CTEAS-next/issues/53) | [P2 D0](ISSUE53_P2_D0_20261018.md) | GLCC直读/GLC面积比例、候选35类映射、fractions合同 |
| [#55 P4](https://github.com/RRain001/CTEAS-next/issues/55) | [P4 D0](ISSUE55_P4_D0_20261018.md) | 显式案例、选站/年度身份、真实探空括号、UP合同 |
| [#56 P5](https://github.com/RRain001/CTEAS-next/issues/56) | [P5 D0](ISSUE56_P5_D0_20261018.md) | 显式案例、站序/跨年、SURF时钟和来源合同 |

初次任务边界与当时的远端Issue快照保存在 `docs/tasks/four_module_d0_20261018/`。实现人员不应根据不同Issue分别修改公共配置文件；模块实现应基于包含PR #57的main，复用site_plan/p6_g19_handoff；快照中的旧状态不覆盖已合并合同。

## 已冻结约束与剩余实现细节

以下依已合并合同区分既定要求与待审实现；不重新开放B-0，也不替代模块设计审查。

1. **权威及冲突处理**：复用case.yaml/grid.cmn/research_time；grid.cmn是数值网格权威，case字段与文件冲突时报错。现有case schema只验证基本键，不足以证明空间/时间一致性（`engine/validators/case_schema.py:24-65`）。明确路径相对于配置、case根或项目根的唯一规则，不让旧 `project/current` 字段指向新案例外部。
2. **精度与新profile准入**：UTM区、半球、WGS84、网格维度/步长、严格三位小数km原点要在计算入口统一校验；common parser直接float不是此项证明。现有冻结Hefei CLI拒绝规则保持；新地域通过单独经审查的通用入口/profile准入，不绕开旧入口。
3. **最少消费字段**：P1/P2/P3只消费空间/来源/产物；P4/P5消费空间/烟囱选站位置/UTC研究窗/归档。P6/P7源项与释放时序保留在公共case但不灌入地形气象计算。多源案例的选站位置实现仍需协调，不改变既有selector政策。
4. **三个时钟**：模型请求窗、气象支持记录窗、产品记录时间标签分开。research_time已明确为包含两端的整时UTC标签。P4需真实AA/BB探空，不能伪造未来条；P5内部包含端点输入与SURF完成小时标签的适配需证明覆盖请求标签并对照原版。
5. **跨年站身份和位置**：完整NOAA ID、WMO、IFSTN、年度角色、source/effective坐标、顺序和有效日期应可核验。变化无法由固定站头表达时先拒绝，不能默认第一年元数据代表全部年份，也不自动造第二站。
6. **文件与provenance**：TERREL/LU/UP/SURF格式沿用已有合同；按B-1输出evidence/p1.json至p5.json及g19.json/joint.json，记录grid/time/config/source/producer/output SHA、单位、行序、真实/合成标记及合同状态层级；具体JSON schema仍待模块审查。P2原始类别比例和映射后类别分开；P5 raw native与云回填发布层分开。
7. **隔离运行**：raw/archive只读；显式新建初始不存在且位于仓库工作树、project/current、冻结案例和生产者缓存之外的scratch，按B-1保存独立案例副本；拒绝逃出staged case的符号链接；缓存绑定case/grid/time/source/policy，缺源不回退旧合肥产物。所有写路径（含控制文件内输出）必须检查。

## 实现及合并边界

- 四模块只能改自己的代码和测试；公共配置/解析/manifest需要独立审查，不在模块PR夹带更改。
- P1/P2交付后由#46做P3和新GEO；本组不新增第二套MAKEGEO或GEO生产器。
- P4/P5保留已有科学算法和原生写入器，仅补案例参数/隔离调度/元数据守卫。
- 四条实现线各自保留独立验收矩阵；GLC映射未审查时维持`P2_MAPPING_REVIEW_REQUIRED`。真实source、software、original parity和science状态分别记录。
- 轻量离线测试可以本地运行；大数据/原版长科学重验按仓库要求只做授权手动workflow_dispatch。

## 本轮验证和限制

核对了远端Issue正文、#42讨论、README/AGENTS/物理矩阵及相关源码；主协调者复核了P1固定EPSG/NoData拒绝、P4末条克隆/首年元数据和P5时钟/全局路径等关键发现。审计报告中的历史PASS均标明继承范围，不是本轮重跑。

实际在/tmp以clang++ C++20及`-Wall -Wextra -Wpedantic -Werror`独立编译运行`native_cpp/tests/grid_origin_precision_tests.cpp`，输出`GRID_ORIGIN_PRECISION_THREE_DECIMAL_KM=PASS`。P4两组unittest缺PyYAML、P5三组unittest缺pandas，均在导入阶段失败，未执行测试方法。各模块自己的实际检查详见报告。没有新增科学结果、没有在线下载DEM/NOAA/GLC、没有改原始输入或执行P6/P7。

下一关是用户独立审查本Draft PR内的四份D0，特别是P2待审映射及模块实现细节；批准后按已合并B-0合同分别推进D1。交付分支为`codex/p1-p2-p4-p5-d0-audit`，PR只包含审计文档和初次任务快照。

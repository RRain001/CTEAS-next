# #54/#53/#55/#56 四线 D0 联合交接索引

日期：2026-10-18。审计基线：`origin/main@82ca304ba10fee8613cf7b8a319abc1b242f0861`；工作分支：`codex/p1-p2-p4-p5-d0-audit`。

## 当前关卡

用户授权并行负责四个模块，按“#42 B-0 → 四线实现 → #46 → #42联合 → #40 → #36”推进。本轮先交付四份D0，**公共接口尚未冻结，不实施D1、不改变物理算法、不宣布Issue完成**。#42远端正文B-0未勾选；已读取三条讨论，均是既有source成果/任务去重，没有看到B-0冻结证据。本结论仅限此次读取内容。

| Issue | 独占审计报告 | 交付范围 |
|---|---|---|
| [#54 P1](https://github.com/RRain001/CTEAS-next/issues/54) | [P1 D0](ISSUE54_P1_D0_20261018.md) | 双DEM入口、同一采样内核、动态网格、TERREL合同 |
| [#53 P2](https://github.com/RRain001/CTEAS-next/issues/53) | [P2 D0](ISSUE53_P2_D0_20261018.md) | GLCC直读/GLC面积比例、候选35类映射、fractions合同 |
| [#55 P4](https://github.com/RRain001/CTEAS-next/issues/55) | [P4 D0](ISSUE55_P4_D0_20261018.md) | 显式案例、选站/年度身份、真实探空括号、UP合同 |
| [#56 P5](https://github.com/RRain001/CTEAS-next/issues/56) | [P5 D0](ISSUE56_P5_D0_20261018.md) | 显式案例、站序/跨年、SURF时钟和来源合同 |

任务边界与此次远端Issue快照保存在 `docs/tasks/four_module_d0_20261018/`。实现人员不应根据不同Issue分别修改公共配置文件；批准后的模块分支应从同一B-0基线开始。

## 给 #42 B-0 的待决事项

以下均为建议，不代替 #42 的设计PR或用户批准。

1. **权威及冲突处理**：复用case.yaml/grid.cmn/research_time；grid.cmn是数值网格权威，case字段与文件冲突时报错。现有case schema只验证基本键，不足以证明空间/时间一致性（`engine/validators/case_schema.py:24-65`）。明确路径相对于配置、case根或项目根的唯一规则，不让旧 `project/current` 字段指向新案例外部。
2. **精度与新profile准入**：UTM区、半球、WGS84、网格维度/步长、严格三位小数km原点要在计算入口统一校验；common parser直接float不是此项证明。现有冻结Hefei CLI拒绝规则保持；新地域通过单独经审查的通用入口/profile准入，不绕开旧入口。
3. **最少消费字段**：P1/P2/P3只消费空间/来源/产物；P4/P5消费空间/烟囱选站位置/UTC研究窗/归档。P6/P7源项与释放时序保留在公共case但不灌入地形气象计算。多源案例用哪个位置选最近站由B-0明确。
4. **三个时钟**：模型请求窗、气象支持记录窗、产品记录时间标签分开。P4需真实AA/BB探空，不能伪造未来条；P5内部包含端点输入与SURF完成小时标签需严格转换并对照原版。不同模块不能各自假设END含义。
5. **跨年站身份和位置**：完整NOAA ID、WMO、IFSTN、年度角色、source/effective坐标、顺序和有效日期应可核验。变化无法由固定站头表达时先拒绝，不能默认第一年元数据代表全部年份，也不自动造第二站。
6. **文件与provenance**：TERREL/LU/UP/SURF格式沿用已有合同；新增旁车记录grid/time/config/source/producer/output SHA、单位、行序、真实/合成标记、状态层级。P2原始类别比例和映射后类别分开；P5 raw native与云回填发布层分开。
7. **隔离运行**：raw/archive只读；显式独立scratch，拒绝写project/current、冻结案例或其他任务输出；缓存绑定case/grid/time/source/policy，缺源不回退旧合肥产物。所有写路径（含控制文件内输出）必须检查。

## 实现及合并边界

- 四模块只能改自己的代码和测试；公共配置/解析/manifest需要独立审查，不在模块PR夹带更改。
- P1/P2交付后由#46做P3和新GEO；本组不新增第二套MAKEGEO或GEO生产器。
- P4/P5保留已有科学算法和原生写入器，仅补案例参数/隔离调度/元数据守卫。
- 四条实现线各自保留独立验收矩阵；GLC映射未审查时维持`P2_MAPPING_REVIEW_REQUIRED`。真实source、software、original parity和science状态分别记录。
- 轻量离线测试可以本地运行；大数据/原版长科学重验按仓库要求只做授权手动workflow_dispatch。

## 本轮验证和限制

核对了远端Issue正文、#42讨论、README/AGENTS/物理矩阵及相关源码；主协调者复核了P1固定EPSG/NoData拒绝、P4末条克隆/首年元数据和P5时钟/全局路径等关键发现。审计报告中的历史PASS均标明继承范围，不是本轮重跑。

实际在/tmp以clang++ C++20及`-Wall -Wextra -Wpedantic -Werror`独立编译运行`native_cpp/tests/grid_origin_precision_tests.cpp`，输出`GRID_ORIGIN_PRECISION_THREE_DECIMAL_KM=PASS`。P4两组unittest缺PyYAML、P5三组unittest缺pandas，均在导入阶段失败，未执行测试方法。各模块自己的实际检查详见报告。没有新增科学结果、没有在线下载DEM/NOAA/GLC、没有改原始输入或执行P6/P7。

下一关是用户统一审查四份D0，并与#42 B-0结果对齐；接口冻结后再分别实施D1。交付分支为`codex/p1-p2-p4-p5-d0-audit`，本次仅包含审计文档和任务快照；未创建PR。

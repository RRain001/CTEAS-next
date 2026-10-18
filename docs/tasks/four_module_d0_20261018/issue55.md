# #55 P4 READ62 案例参数化：沿用既定 IGRA→FSL→UP.DAT 流程

来源：https://github.com/RRain001/CTEAS-next/issues/55
抓取日期：2026-10-18；远端更新时间：2026-10-18T07:57:34Z

## 用户澄清：P4 只做案例参数化，不扩 READ62 算法（2026-10-18）
**保持当前选定 NOAA IGRA→FSL→C++ READ62→UP.DAT 处理路径不变**，包括已接受的 JDAT=2、IFMT=1、既定探空QA/层处理、>80%原始00/12站点门槛及域外虚拟站规则。这里只解决：用户调整烟囱/研究区域位置后根据**既有选站算法**自动选站、相应网格与研究时段/跨年、新场址隔离数据路径、独立工作目录、逐站原版兼容UP.DAT和元数据，不得写死旧合肥/Anqing/固定2022或143h案例。**不是**新增另种探空格式、站点选择政策、气象插值/修复算法、其他READ62物理控制选项，也不用让P4接收排放率进行气象重算。已有多站/跨年能力优先复用，只补消除旧场址绑定的接口/调度缺口。

## 专项职责：P4 READ62 通用化（2026-10-18）
父任务 [#42](https://github.com/RRain001/CTEAS-next/issues/42) 的 **P4 独占开发入口**。P1由[#54](https://github.com/RRain001/CTEAS-next/issues/54)、P2由[#53](https://github.com/RRain001/CTEAS-next/issues/53)、P3由[#46](https://github.com/RRain001/CTEAS-next/issues/46)、P5由[#56](https://github.com/RRain001/CTEAS-next/issues/56)负责；本Issue **不重新构建 P4 下载器、不开发 P5/P6、不对 P1-P3 改代码**。

### 已有成果，必须继承（不可重复开发/否定）
- 原生 `native_cpp/modules/p4_read62/p4_read62_main.cpp` 支持独立 C++ FSL→UP.DAT，既有审计为原 READ62 **JDAT=2 / IFMT=1 / PSTOP=500 hPa 等选定参数**全2022 Anqing 730 profiles、212885 P/Z/T/WD/WS字段原版数值/字节一致；**仅这套选项和既有证据有效**。见 `docs/reconstruction_cpp/P4_READ62_IMPLEMENTATION_STATUS.md`。
- `data_prep/download_igra.py` / `parse_igra_to_csv.py` / `read.py` / `prepare_inputs.py` / `run_cpp_pipeline.py` 已实现年度IGRA站点选择、原始00/12槽 coverage严格**>80%**、FSL准备和年度C++生产并使用既有Python合并流程；不重写已经通过的科学算法。零个合格域内站时，使用最近符合门槛的域外**虚拟**上空站，必须保留真实来源与有效位置；域内多个合格站均保留。
- [PR #44](https://github.com/RRain001/CTEAS-next/pull/44) 已在非合肥 Huoshan/Xinqiao 测试域使用真实 NOAA 2022/2023 Anqing 数据独立生产 UP.DAT、验过06小时与AA/BB括号；但脚本 `scripts/s2g/real_noaa_native_p4_up.py` 是**冻结具体站点/年份与窗口的验收场景**，不是任意场址的通用执行入口。

### 需要补足的通用化边界
- [ ] **P4-D0 代码/接口审计**：将“原生数值内核支持”与“Python调度支持任意场址/时间/站点”和“进入 CALMET G19 的真实上空源契约”分开验收。先盘点 `current_project_path/project/current` 全局状态、冻结站点WMO/时段/文件名假设、候选/选定站点ID和格式控制；Draft PR审查设计后动代码。
- [ ] **P4-D1 隔离场址运行**：从独立 `case.yaml/grid.cmn/research_time` + 真实NOAA（或离线归档）给定可显式选定输出工作目录，使用已实现的逐年选站、FSL→C++UP.DAT→最终CALMET UP；不得修改 `project/current`、冻结 Hefei 输入或别的场址，必须生成可复现的每站/每年来源SHA及筛选/转换元数据。
- [ ] **P4-D2 动态站点与时段**：1或多真实上空站；不同经纬度/UTM区/研究年/跨年窗口；支持年度站点名单变化的严格身份与日期映射，防止强制虚构第二上空站。验证 00/12 实际观测槽门槛、闰年分母、边界前后探空（AA/BB）、近邻域外虚拟站溯源及无合格站fail-closed。支持的JDAT/IFMT/缺测选项仍仅限经过原版数值比对的既有分支，不因“通用场址”而静默增加选项。
- [ ] **P4-D3 原版同源数值对照**：以至少冻结 Hefei Anqing 2022 及一个真实非合肥场址（已有#44的2022/2023可复用作为回归）逐站对照独立原版READ62，核对 FSL、UP.DAT 完整字节/字段、时区、头部、单位、站点ID/有效位置/原始位置与上下界探空；更多站点/组合按真实数据资格增加。已有通过的跨年6小时输入测试不能声称所有研究时段/源选项科学PASS。
- [ ] **P4-D4 移交合同**：输出和签名 `UP.DAT`、真实WMO、源坐标/有效坐标、站点数量、实际UTC起止和可用探空括号、源SHA/清洗SHA/输出SHA。父任务#42负责与P1–P3及P5合成一个新场址输入栈，并验收G19；本issue不启动P6逐时科学模拟。

### 不重做、不扩权
- 不再新建原版IGRA下载器/新探空算法、不重构P5。Open NOAA 获取可能联网，但**常规PR测试只能依赖仓库已有真实数据归档/小fixture，不能常规联网**。真实新增数据获取和全年独立原版比对走手动workflow_dispatch，始终留受控日志，不传出私密凭据。
- 不将选定READ62路径误称为全READ62重构：TD-6201 JDAT1、IFMT2、ISUB>0、LXTOP/LXSFC等仍为UNSUPPORTED，需后续独立物理选项矩阵。
- 状态分别标示 `P4_SOURCE_SELECTION`、`P4_NATIVE_UP`、`P4_GENERIC_CASE_EXECUTION`、`P4_ORIGINAL_PARITY`、`P4_TO_G19`，以真实证据提升；不以source-only或旧原版PASS替代新通用集成PASS。

依赖：`#55(P4) ∥ #56(P5) ∥ #54(P1) ∥ #53(P2) ∥ #46(P3) → #42(P1–P5通用新场址输入联合) → #40(P6科学) → #36(总)`。

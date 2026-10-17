# Ubuntu Migration Acceptance

执行日期：2026-07-01

## 结论

当前项目迁移到 Ubuntu 主机后，已经在本机完成一次全新的小案例冷启动验收。

验收结论：

- Python 虚拟环境可用
- `bin/linux-x86_64/*.x` 可解析并运行
- 地形处理可跑通
- 高空气象下载与处理可跑通
- 地面气象下载与处理可跑通
- 诊断风场计算可跑通
- 烟团模型计算可跑通

因此，针对 Linux x86_64 / Ubuntu 主机这一目标环境，当前迁移结果可视为“主流程可运行”。

## 验收案例

- 冷启动案例：`smoke5d_coldstart_20260701`
- 当前案例切换到：`project/current -> project/cases/smoke5d_coldstart_20260701`

该案例专门用于避免复用既有 `smoke5d` 数据目录，从空案例目录重新触发下载、前处理与主计算流程。

## 实际验证链路

按以下顺序完成实测：

1. 新建案例并切换当前案例
2. 地形前处理
   - `terrel.x`
   - `ctgproc.x`
   - `makegeo.x`
3. 高空气象冷启动下载与处理
   - IGRA 下载
   - 解析与转换
   - `read62.x`
4. 地面气象冷启动下载与处理
   - ISD 下载
   - 插值与清洗
   - SMERGE 输入转换
   - `smerge.x`
5. `met.x` 诊断风场
6. `puff.x` 烟团模型

## 关键产物

地形与前处理：

- `project/cases/smoke5d_coldstart_20260701/geo/makegeo/geo.dat`
- `project/cases/smoke5d_coldstart_20260701/geo/makegeo/qaterr.grd`
- `project/cases/smoke5d_coldstart_20260701/geo/ctgproc/lu.dat`

高空：

- `project/cases/smoke5d_coldstart_20260701/met/upperair/2023/CHM00058203-data.txt`
- `project/cases/smoke5d_coldstart_20260701/met/upperair/final/up_58203.dat`

地面：

- `project/cases/smoke5d_coldstart_20260701/met/surface/isd_raw/58321099999-2023.csv`
- `project/cases/smoke5d_coldstart_20260701/met/surface/final/surf.dat`
- `project/cases/smoke5d_coldstart_20260701/met/surface/final/stations.csv`

诊断风场与扩散：

- `project/cases/smoke5d_coldstart_20260701/run/met/met.dat`
- `project/cases/smoke5d_coldstart_20260701/run/met/met.lst`
- `project/cases/smoke5d_coldstart_20260701/run/puff/puff.con`
- `project/cases/smoke5d_coldstart_20260701/run/puff/puff.lst`

交付物：

- `project/cases/smoke5d_coldstart_20260701/deliverables/met/met.dat`
- `project/cases/smoke5d_coldstart_20260701/deliverables/puff/puff.con`

## 本轮修复的问题

为完成 Ubuntu 冷启动验收，本轮修复了 2 个真实问题：

1. `engine/preprocess/ctgproc/auto_select_landuse_to_ctgproc.py`
   - 修复 Linux 区分大小写环境下，土地利用路径大小写兼容逻辑错误尝试创建仓库外小写软链的问题
2. `engine/preprocess/smerge_surf_data/isd_to_smerge_and_fill.py`
   - 修复 `SCRIPT_DIR` 未定义，导致地面气象下载完成后在插值阶段崩溃的问题

此外，为让冷启动案例与现有 `puff` 模板保持一致，还把案例配置调整为：

- `puff.options.nspec: 2`
- `point_sources[0].emissions: [222222.0, 0.0]`

这属于案例配置与模板一致性调整，不属于迁移框架本身的路径问题。

## 验收边界

本次结论覆盖：

- Ubuntu / Linux x86_64 主机
- 当前仓库结构
- 当前 `bin/linux-x86_64/*.x`
- 当前 Python 依赖与 `./bootstrap_venv.sh` 方案

本次未覆盖：

- Windows 运行
- Linux ARM64 运行
- GUI 交互层逐页人工点击验收
- Docker 重新构建二进制

## 后续建议

若需要继续收尾，优先做这两项：

1. 把 `smoke5d_coldstart_20260701` 作为正式回归案例保留，或整理为可重复创建的 smoke test 流程
2. 再补一轮 `engine.orchestrator.cli run --case <case> --stage all --resume` 的编排入口验收，确认 CLI 总入口也能完整串联

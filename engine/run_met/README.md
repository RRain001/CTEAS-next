# run_met

本目录提供 MET 第一阶段自动化脚本：

- `prepare_met.py`
  - 从 `project/current` 和 `case.yaml` 渲染 `project/current/run/met/met.inp`
- `run_met.py`
  - 调用 `met.x`
  - 写运行日志并检查 `met.lst` / `met.dat`

## 输入契约

执行前，前处理必须已产出以下最终交付物：

- `project/current/geo/makegeo/geo.dat`
- `project/current/met/surface/final/surf.dat`
- `project/current/met/surface/final/stations.csv`
- `project/current/met/upperair/final/up_<station>.dat`

## 运行

仅生成 `met.inp`：

```bash
python3 -m engine.run_met.prepare_met --case smoke5d
```

生成并执行：

```bash
python3 -m engine.run_met.run_met --case smoke5d
```

## 配置

配置来源仅使用：

- `project/current/case.yaml`

当前支持的 `met` 配置骨架：

```yaml
met:
  station_selection:
    isurft_mode: spatial
    iupt_mode: spatial
    iupwnd_mode: spatial
  options:
    lcfiles: true
    irtype: 1
    lcalgrd: true
    lsave: true
    lprint: false
    noobs: 0
    npsta: 0
    icloud: 0
    iforms: 2
    iformp: 2
    iformc: 2
    iwfcod: 1
    ifradj: 1
    ikine: 0
    iobr: 0
```

默认代表站策略：

- `ISURFT = -1`
- `IUPT = -1`
- `IUPWND = -1`

## 输出

运行目录：

- `project/current/run/met`

主要产物：

- `met.inp`
- `met.lst`
- `met.dat`
- `met_runtime.log`

## `met.inp` 迁移规则（必须改 / 可选改）

以下规则来自对历史可运行样例与新样例的逐项对比，可作为跨案例迁移检查清单。

必须修改（换案例时）：

- 输入输出路径/文件名：`GEODAT`、`SRFDAT`、`UPDAT(各站)`、`METLST`、`METDAT`
- 模拟时段与时区：`IBYR/IBMO/IBDY/IBHR`、`IEYR/IEMO/IEDY/IEHR`、`ABTZ`
- 投影与网格：`IUTMZN`、`NX/NY`、`DGRIDKM`、`XORIGKM/YORIGKM`
- 站点数量与站点表：`NSSTA`、`NUSTA` 与 `SS1..`、`US1..`
- 垂向层：`NZ`、`ZFACE`
- 所有与 `NZ` 联动的数组长度：`BIAS`、`IUVOUT`、`IWOUT`、`ITOUT`、`NSMTH`、`NINTR2`、`FEXTR2`、`KBAR`
- 代表站索引合法性：`ISURFT` 必须在 `1..NSSTA`（或合法特殊值），`IUPT` 必须在 `1..NUSTA`（或合法特殊值）

可按需求调整（不属于每次必须改）：

- 物理/诊断方案开关和经验参数（多数可沿用）
- `LVARY`（插值策略）
- `ICOARE`（水面通量方案）
- `JWAT1/JWAT2`（仅当土地利用编码体系变化时需要调整）
- 调试/打印相关参数（如 `NN1/NN2`、`LPRINT` 等）

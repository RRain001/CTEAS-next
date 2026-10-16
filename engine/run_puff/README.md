# run_puff

本目录提供 PUFF 串行自动化脚本：

- `prepare_puff.py`
  - 读取案例中的 `puff_7.0.inp` 模板（优先 `project/current/run/puff`）
  - 自动写入 `METDAT` 为 `run/met/met.dat`
  - 保留模板中的源项配置（点源/面源等参数）
  - 生成 `project/current/run/puff/puff.inp`
- `run_puff.py`
  - 调用 `puff.x`
  - 自动检查并补齐 `METDAT`（若缺失则从 `run/met/met.dat` 复制）
  - 写运行日志并检查 `puff.lst` / `puff.con`

## 配置入口（case.yaml）

当前 PUFF 参数与点源数据统一从 `project/current/case.yaml` 读取。

示例结构：

```yaml
puff:
  options:
    lcfiles: true
    moz: 0
    metrun: 0
    source_mode: center_location
    nrec: 0
    nrgrp: 0
    nspec: 7
    nse: 4
    mchem: 0
    idry: 0
    iwet: 0
    ndecay: 1
    nspt1: 0
  point_sources:
    - name: STK1
      x_km: 340.5
      y_km: 4870.5
      stack_height_m: 40.0
      base_elev_m: 157.0
      stack_diameter_m: 3.0
      exit_velocity_mps: 5.0
      exit_temp_k: 355.0
      building_downwash_flag: 0.0
      zpltfm_m: 0.0
      fmfac: 1.0
      emissions: [10.0, 0.0, 4.0, 1.0, 0.0, 0.0, 10.0]
```

说明：
- 后续源项修改只需要改 `case.yaml` 的 `puff.point_sources`。
- `source_mode` 控制源项来源：
  - `center_location`（默认）：从 `project/current/grid/center_location` 读取经纬度，调用 `center_location_to_utm.py` 转换后写入 `X/Y`
  - `template_defaults`：使用模板示例点源参数（`P1`、`X=123.456`、`Y=1234.567`、`H=50m`、`Q=1.2345E05` 等）
  - `case_yaml`：使用 `puff.point_sources` 中定义的点源
- 默认 `ndecay: 1`，保留模板 `H-3 -> HE-3` 衰变示例；若不需要衰变请显式设置 `ndecay: 0`。
- `prepare_puff.py` 会自动同步网格/投影/时区参数，并把模板源项坐标按当前网格原点平移。
- `point_sources[*].emissions` 数组长度必须等于 `options.nspec`。
- 当前脚本不会自动重写模板中的 `CSPEC` 物种块；`options.nspec` 必须与模板 `CSPEC` 条目数一致。
- 若仅保留单一物种（如 `NSPEC=1` 且只设 `H-3`），必须设置 `ndecay: 0`。
  若 `ndecay > 0`，需要在物种中包含子代（例如 `HE-3`），否则会触发输入一致性错误。

## 运行

仅生成 `puff.inp`：

```bash
python3 -m engine.run_puff.prepare_puff --case smoke5d
```

生成并执行：

```bash
python3 -m engine.run_puff.run_puff --case smoke5d
```

## 串行流程记录

1. 前处理与 MET 完成，确保 `project/current/run/met/met.dat` 已存在。
2. 编辑 `project/current/case.yaml` 中 `puff.options` 和 `puff.point_sources`。
3. 执行 `prepare_puff.py`，生成 `project/current/run/puff/puff.inp`。
4. 执行 `run_puff.py` 串行计算，输出 `puff.con`、`puff.dry`、`puff.wet`、`puff.vis` 等结果。
5. 检查 `run/puff/puff.lst` 与 `run/puff/puff_runtime.log`。

## `puff.inp` 必改参数清单

跨案例迁移时，以下参数应视为必改项：

- 输入输出文件：`METDAT`、`PUFLST`、`CONDAT`（及需要时 `DFDAT/WFDAT/VISDAT`）
- 运行时段与时区：`METRUN`，以及 `METRUN=0` 时的 `IBYR/IBMO/IBDY/IBHR/IBMIN/IBSEC`、`IEYR/IEMO/IEDY/IEHR/IEMIN/IESEC`，`ABTZ`
- 网格与投影：`PMAP`、`IUTMZN`（或对应投影参数）、`NX/NY/NZ`、`DGRIDKM`、`XORIGKM/YORIGKM`、`ZFACE`
- 输出窗口与采样网格：`IBCOMP/JBCOMP/IECOMP/JECOMP`、`MESHDN/IESAMP/JESAMP`
- 物种体系：`NSPEC`、`NSE`、`CSPEC` 列表（数量与顺序必须一致）
- 化学/沉降总开关：`MCHEM`、`IDRY`、`IWET`
- 源项数量与内容：`NPT1/NAR1/NLIN1/NVOL1` 及各源参数块（坐标、几何、排放）
- 受体设置：`NREC`（非网格受体）及其坐标定义
- 压缩与输出格式：`LCOMPRS`、`IOUTU/IPRTU/IPTU`（按后处理链路需求匹配）

建议同步检查：

- `NSPEC` 与所有源项排放数组长度一致
- `METDAT` 的网格/层数与 `puff.inp` 网格定义一致
- `METRUN=1` 时，起止时间字段通常不参与控制，避免误以为已按时间截断

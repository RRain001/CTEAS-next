# 桌面 GUI 结果后处理接入计划

## 摘要

目标是在现有 PySide6 桌面 GUI 的“结果后处理”页面接入已有后处理能力。所有任务使用当前 case 的显式路径，输出统一写入：

```text
project/cases/<case>/run/puff/postprocessing/
```

任务日志统一写入：

```text
project/cases/<case>/runs/<timestamp>_post_<job>/
```

每个运行目录包含 `command.txt`、`stdout.log`、`stderr.log`、`run_meta.json`。

## 接入功能

1. 浓度空间图：`snapshot`、`annual`、`seasonal`
2. 年度动画：`mp4`、`gif`
3. 点位浓度提取：从 `puff.con` 提取点位时序 CSV
4. 日浓度曲线：从点位浓度时序生成日均浓度曲线 PNG
5. 风玫瑰图：默认从前处理地面气象 `surf.dat` 绘制站点风玫瑰，保留自定义 CSV 入口

## 实现规则

- 后处理脚本默认路径必须基于仓库根目录或显式传入的当前 case 路径，不再把脚本目录作为默认输出位置。
- GUI 调用空间图、动画、点位提取、日浓度曲线时显式传入：
  - `--conc-file <case>/run/puff/puff.con`
  - `--met-inp <case>/run/met/met.inp`
  - `--terrain-file <case>/geo/makegeo/qaterr.grd`
  - `--out` 或 `--output` 到当前 case 的 postprocessing 目录
- 地形文件缺失不阻止运行，只提示无地形底图。
- 日浓度曲线不再使用旧 CSV 的“cfd对应放大”列作为默认值，默认使用点位浓度提取出的真实 `puff.con` 浓度值。
- 点位浓度提取输出单位统一为 `Bq/m³`。
- 风玫瑰第一版默认解析 `met/surface/final/surf.dat`；自定义 CSV 模式保留列名参数。
- 不接入旧的 annual-dixing 实验脚本，它保留为历史实验实现。

## GUI 行为

- “结果后处理”页面改为按钮式功能选择（`QPushButton` + `QStackedWidget`），与”任务管理”页面风格一致。
- 功能选择按钮使用 `kind=”stage_picker”` 样式，宽度 90px（对齐”地形处理”按钮）。
- 操作按钮（运行/取消/恢复默认/打开输出目录/打开结果文件）位于功能选择按钮同行右侧，使用 `QGridLayout` 两行排布，与”任务管理”风格一致。
- 整个”结果后处理”页面包裹在 `QGroupBox(“结果后处理”)` 中（`#PostCard` 样式）。
- 每个功能面板内参数表单与预览区域左右排布（`QHBoxLayout`，比例 4:5）。
- 参数表单使用 `QFormLayout`（标签在左，输入框在右），与”参数配置”页面风格一致。
- 参数标签全部中文化：`vmin→最小值`、`vmax→最大值`、`threshold→阈值`、`cmap→色图`、`fps→帧率`、`stride→步长`、`max frames→最大帧数`、`CSV→CSV 文件`。
- “点位浓度”面板同时输出 `point_timeseries.csv` 和 `daily_concentration.png`，日浓度曲线不再作为独立功能。
- 风玫瑰数据源改为从 `project/current/met/surface/isd2smerge_ready` 选择 CSV 文件，不再使用 `surf.dat`。
- “日志查看”页面包裹在 `QGroupBox(“日志查看”)` 中（`#LogCard` 样式）。
- 后处理任务复用现有 `QProcess` 单任务机制。
- 后处理任务运行时禁止启动其他任务。
- GUI 侧提前拦截：
  - 缺失 `puff.con`
  - 缺失 `met.inp`
  - 缺失必要 CSV
  - `vmin >= vmax`
  - `scale=log` 且 `vmin <= 0`
  - 输出文件名为空
  - 点位坐标为空

## 测试计划

- `python3 -m py_compile` 覆盖修改过的 GUI 和后处理脚本。
- 最小 CLI 检查覆盖：
  - 空间图
  - 点位浓度提取
  - 日浓度曲线
  - 风玫瑰图
  - 动画参数解析或短帧运行
- GUI 启动检查：`./calpuff-cli desktopgui`。
- 错误路径检查：缺失输入或非法参数时 GUI 不启动任务并给出明确提示。

## 完成情况

已完成（含 GUI 布局和样式优化）。

### GUI 优化补充（2026-05-09）

在原有功能接入基础上，对"结果后处理"和"日志查看"页面进行了以下表现层优化：

- 功能选择按钮宽度从 118px 改为 90px，与"任务管理"的"地形处理"按钮一致。
- 参数标签全部中文化（vmin/最小值、vmax/最大值、threshold/阈值、cmap/色图、fps/帧率、stride/步长、max frames/最大帧数）。
- 参数表单从上下堆叠 3 列 `QGridLayout` 改为 `QFormLayout`（标签在左，输入框在右），与"参数配置"页面风格一致。
- 参数表单与预览区域从上下排布改为左右排布（`QHBoxLayout`，比例 4:5）。
- 操作按钮从各面板内部移至页面顶部，与功能选择按钮同行，`QGridLayout` 两行排布，与"任务管理"风格一致。
- 移除"查看日志"按钮。
- "结果后处理"页面包裹在 `QGroupBox("结果后处理")` 中。
- "日志查看"页面包裹在 `QGroupBox("日志查看")` 中。
- "日志查看"与"结果后处理"两页也接入与前 3 页一致的滚动容器和页面留白，恢复统一的浅灰背景框观感。
- 风玫瑰脚本默认列名从中文改为 `Month`/`deg`/`ms-1`，匹配 `isd2smerge_ready` CSV 格式。

### 已修改

- `engine/gui/workbench.py`
  - “结果后处理”页面改为按钮式功能选择（`QPushButton` + `QStackedWidget`），4 个功能面板：浓度空间图、年度动画、点位浓度、风玫瑰图。
  - 功能选择按钮宽度 90px，`kind=”stage_picker”` 样式，与”任务管理”的”地形处理”按钮一致。
  - 操作按钮（运行/取消/恢复默认/打开输出目录/打开结果文件）位于功能选择按钮同行右侧，`QGridLayout` 两行排布。
  - 整个页面包裹在 `QGroupBox(“结果后处理”)` 中，带自定义 `#PostCard` QSS 样式（浅灰蓝背景 + 深色边框）。
  - 参数表单 + 预览左右排布（`QHBoxLayout`，比例 4:5），参数使用 `QFormLayout`（标签在左，输入框在右）。
  - 所有参数标签中文化。
  - “日志查看”页面包裹在 `QGroupBox(“日志查看”)` 中，带自定义 `#LogCard` QSS 样式。
  - 后处理任务复用现有 `QProcess`、运行目录、日志和 `run_meta.json` 机制。
  - 后处理运行按钮执行期间会禁用，继续保持单任务策略。
- `engine/postprocessing/_core.py`
  - 空间图流程支持显式 `--terrain-file`。
  - 地形文件按显式参数、`puff.con` 同目录、case `geo/makegeo/qaterr.grd`、旧 `project/current` 兜底顺序查找。
- `engine/postprocessing/plot_puff_snapshot.py`
  - CLI 已把 `--terrain-file` 传入空间图核心流程。
- `engine/postprocessing/plot_puff_animation.py`
  - CLI 支持 `--terrain-file`。
  - 优先使用系统 `ffmpeg`，否则回退到 `.venv` 中的 `imageio-ffmpeg` 二进制。
  - gif 在缺少 `ffmpeg` 时仍可使用 Pillow writer 兜底。
- `engine/postprocessing/extract_point_data.py`
  - 默认路径改为 tutorial/project 路径。
  - 输出单位改为 `Bq/m³`。
  - 时间过滤改为先过滤再写唯一输出 CSV。
- `engine/postprocessing/plot_daily_concentration_fangda.py`
  - 改为通用点位时序 CSV 日均曲线绘图。
  - 默认列为 `concentration`，不再依赖“cfd对应放大”。
  - 已接入 `tutorial/Times New Roman.ttf`。
- `engine/postprocessing/plot_daily_from_puff.py`
  - 新增包装 CLI：先从 `puff.con` 提取点位时序，再绘制日均浓度曲线。
- `engine/postprocessing/plot_windrose_style.py`
  - 新增 CLI 参数。
  - 默认列名改为 `Month`/`deg`/`ms-1`，匹配 `isd2smerge_ready` 目录中 CSV 的真实列名。
  - 保留自定义 CSV 入口和 `--surf-dat` 兼容模式。
  - `load_data()` 自动识别 SMERGE 三行头格式（`GENERIC` 头，skiprows=2）。
  - 已接入 `tutorial/Times New Roman.ttf`。
- `calpuff-cli`
  - 启动时优先使用项目 `.venv/bin/python`，不存在时回退到系统 `python3`，使 `./calpuff-cli desktopgui` 能使用项目虚拟环境中的 PySide6。

### 验证结果

- 语法检查通过：
  - `python3 -c "compile(...)"` 覆盖修改过的 GUI 与后处理脚本。
- 浓度空间图最小命令通过：
  - 生成 `project/cases/test/run/puff/postprocessing/check_snapshot.png`。
- 点位浓度提取最小命令通过：
  - 生成 `check_point.csv`，单位为 `Bq/m³`。
- 日浓度曲线最小命令通过：
  - 从 `puff.con` 生成点位 CSV，再生成 `check_daily.png`。
- 风玫瑰最小命令通过：
  - 从 `project/cases/test/met/surface/final/surf.dat` 生成 `check_windrose.png`。
- 年度动画 gif 最小命令通过：
  - 在无 `ffmpeg` 环境下使用 Pillow 生成 `check_anim.gif`。
- 年度动画 mp4 最小命令通过：
  - 使用 `.venv` 中的 `imageio-ffmpeg` 生成 `check_anim.mp4`。
- GUI 启动探测通过：
  - `QT_QPA_PLATFORM=offscreen ./calpuff-cli desktopgui` 能进入事件循环；测试用 `timeout` 结束，退出码 124 是预期超时退出。

### 注意事项

- `.venv` 中现已安装 `imageio-ffmpeg`，mp4/gif 动画可以不依赖系统 `ffmpeg`。
- `Times New Roman.ttf` 已接入，但当前环境仍缺 `SimSun`、`KaiTi` 等中文字体，绘图命令会有中文字体告警；文件仍可生成。

# ISD 地面风场处理说明（smerge_surf_data）

本目录用于按项目研究时段自动下载 NOAA Global Hourly(ISD) 数据，完成转换、插值、清洗合并、SMERGE 配置更新与 SMERGE 运行，并发布 CALMET 直接使用的 `surf.dat`。

## 流程顺序
- 下载 -> 转换插值 -> 清洗合并 -> 格式转换 -> 更新 SMERGE 配置 -> 运行 SMERGE 并检查结果

## 目录与脚本
- `download_isd_by_grid.py`：按研究范围和 `research_time` 自动下载（跨年自动推导年份）
- `isd_to_smerge_and_fill.py`：将原始 ISD 转为 GENERIC CSV，并调用 `interpolate.py` 产出 `*_filled.csv`
- `clean_merge_filled_by_research_time.py`：按 `research_time` 裁剪并合并同站跨年数据
- `convert_cleaned_to_smerge_ready.py`：将清洗合并结果规范化为 SMERGE ready 文件
- `generate_smerge_input_sections.py`：更新 `run/smerge/smerge.inp` 的站点与时段配置
- `run_smerge_and_monitor.py`：运行 `smerge.x`，检查结果并发布最终 `surf.dat`
- `run_isd_surface_pipeline.py`：串行总脚本（一键跑完整流程）
- `isd-history.txt`：NOAA 站点历史清单

## 数据目录（基于 current case）
- 原始下载：`project/current/met/surface/isd_raw`
- 插值结果：`project/current/met/surface/isd2smerge_and_fill`
- 清洗合并：`project/current/met/surface/isd2smerge_cleaned`
- SMERGE 输入：`project/current/met/surface/isd2smerge_ready`
- 最终发布（供 CALMET 使用）：`project/current/met/surface/final`

## 一键串行执行（推荐）
```bash
.venv/bin/python -m engine.preprocess.smerge_surf_data.run_isd_surface_pipeline
```

跳过下载（仅重做后处理）：
```bash
.venv/bin/python -m engine.preprocess.smerge_surf_data.run_isd_surface_pipeline --skip-download
```

## 分步执行
1) 下载（按研究时段自动推导年份）：
```bash
.venv/bin/python -m engine.preprocess.smerge_surf_data.download_isd_by_grid
```

2) 转换并插值：
```bash
.venv/bin/python -m engine.preprocess.smerge_surf_data.isd_to_smerge_and_fill
```

3) 清洗并跨年合并（每站一个连续文件）：
```bash
.venv/bin/python -m engine.preprocess.smerge_surf_data.clean_merge_filled_by_research_time
```

4) 转换为 SMERGE ready：
```bash
.venv/bin/python -m engine.preprocess.smerge_surf_data.convert_cleaned_to_smerge_ready
```

5) 更新 SMERGE 输入段：
```bash
.venv/bin/python -m engine.preprocess.smerge_surf_data.generate_smerge_input_sections
```

6) 运行 SMERGE 并发布最终地面数据：
```bash
.venv/bin/python -m engine.preprocess.smerge_surf_data.run_smerge_and_monitor
```

## 备注
- 时间范围来源：`project/current/grid/research_time`。
- CALMET 使用的是 `project/current/met/surface/final/surf.dat`，不是 `run/smerge/surf.dat`。

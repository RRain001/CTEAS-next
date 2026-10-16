# 高空数据处理说明（read62_upperair_data）

本目录用于处理 IGRA 高空探空数据，并生成 READ62 可用输入与输出。

## 流程
按年份执行以下步骤：
1. 下载 IGRA 原始文本（`download_igra.py`）
2. 解析为每时次 CSV（`parse_igra_to_csv.py`）
3. 转换为 FSL 文本（`read.py`）
4. 执行 READ62（`run_read62.py`）

## 跨年处理
- 年份自动来自 `project/current/grid/research_time` 的 `BEGIN/END`。
- 当研究时段跨年时，会按年份逐年处理（例如 2023、2024）。
- 数据目录保持按年组织：`project/current/met/upperair/<year>/...`。

## 一键串行脚本（推荐）
```bash
python3 -m engine.preprocess.read62_upperair_data.run_upperair_pipeline
```

常用参数：
- `--pstop 500`：指定 PSTOP（默认 500）
- `--skip-download`：跳过下载，仅重做后续步骤
- `--python /path/to/python`：指定解释器

示例：
```bash
python3 -m engine.preprocess.read62_upperair_data.run_upperair_pipeline --pstop 500
python3 -m engine.preprocess.read62_upperair_data.run_upperair_pipeline --skip-download --pstop 500
```

## 新增非交互参数
- `download_igra.py`
  - `--auto-select-all`：自动选择候选站点全部
  - `--yes`：跳过下载前确认
- `parse_igra_to_csv.py`
  - `--pstop`：直接设置 PSTOP
  - `--yes`：非交互模式（不提示输入）

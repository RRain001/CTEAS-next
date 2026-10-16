# Run Desktop GUI

## 启动前准备

```bash
./bootstrap_venv.sh
```

要求：Python `>= 3.11`。`bootstrap_venv.sh` 会优先使用 `uv`，否则回退到
标准 `python -m venv` + `pip`。

## 启动 PySide6 桌面 GUI

```bash
python -m engine.ui.desktop.main
```

或：

```bash
./calpuff-cli desktopgui
```

当前受支持的 GUI 只有 PySide6 桌面 GUI。

## 迁移说明

旧的 `webgui` 和 `streamlitgui` 入口已经移除，调用时会返回明确错误。

- 桌面 GUI：`./calpuff-cli desktopgui`
- CLI 编排：`./calpuff-cli run --case <case> --stage <stage>`

## 启动 CLI 编排入口

```bash
./calpuff-cli
```

## native 路径解析

当前 native 程序从以下目录解析：

- `./bin/<platform>/`

相关模块：

- `./engine/core/platform_utils.py`
- `./engine/core/runner.py`
- `./engine/core/paths.py`

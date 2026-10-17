# Python Package Structure

当前项目已补充 `pyproject.toml`，保留 `requirements.txt` 兼容原工作流。

## 推荐安装方式

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## 可选开发安装

```bash
pip install -e .
```

## 当前入口

- CLI：`cteas` -> `engine.orchestrator.cli:main`
- 桌面 GUI：`cteas-desktop` -> `engine.ui.desktop.main:main`
